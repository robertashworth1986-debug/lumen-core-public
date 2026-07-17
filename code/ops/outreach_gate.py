#!/usr/bin/env python3
"""Fail-closed preflight for LumenCore outreach.

This tool does not send email. It validates the shared outreach registry and
decides whether a proposed draft or send action is permitted by the current
human-approval and duplicate-prevention policy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCHEMA = "lumencore_outreach_registry.v1"
ALLOWED_STATUSES = {
    "ready_for_first_outbound",
    "action_required_draft_ready",
    "waiting_for_reply",
    "receipt_confirmed_waiting",
    "closed",
    "blocked",
}
ALLOWED_THREAD_MODES = {"new_thread_allowed", "existing_thread_only"}
ALLOWED_ACTORS = {"codex", "chatgpt", "human"}
ALLOWED_ACTIONS = {"draft", "send"}
ALLOWED_MODES = {"new", "reply"}
REQUIRED_CAMPAIGN_FIELDS = {
    "campaign_key",
    "organization",
    "status",
    "thread_mode",
    "outbound_sequence",
    "duplicate_detected",
    "duplicate_count",
    "inbound_since_last_outbound",
    "next_allowed_action",
    "outreach_id",
    "notes",
}


class RegistryError(ValueError):
    """Raised when the shared outreach registry is malformed."""


def load_registry(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RegistryError(f"cannot read registry: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RegistryError(f"invalid registry JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RegistryError("registry root must be an object")
    validate_registry(payload)
    return payload


def validate_registry(payload: dict[str, Any]) -> None:
    if payload.get("schema") != SCHEMA:
        raise RegistryError(f"schema must be {SCHEMA}")
    policy = payload.get("policy")
    if not isinstance(policy, dict):
        raise RegistryError("policy must be an object")
    required_policy = {
        "send_authority",
        "codex_send_allowed",
        "chatgpt_send_requires_explicit_action_time_approval",
        "default_cooldown_hours",
        "existing_thread_required_after_first_outbound",
        "gmail_sent_preflight_required",
        "draft_only_by_default",
    }
    missing_policy = sorted(required_policy - set(policy))
    if missing_policy:
        raise RegistryError(f"missing policy fields: {', '.join(missing_policy)}")
    if policy["codex_send_allowed"] is not False:
        raise RegistryError("policy.codex_send_allowed must remain false")
    if (
        not isinstance(policy["default_cooldown_hours"], int)
        or policy["default_cooldown_hours"] < 1
    ):
        raise RegistryError(
            "policy.default_cooldown_hours must be a positive integer"
        )

    campaigns = payload.get("campaigns")
    if not isinstance(campaigns, list) or not campaigns:
        raise RegistryError("campaigns must be a non-empty array")

    seen_keys: set[str] = set()
    seen_ids: set[str] = set()
    for index, campaign in enumerate(campaigns):
        if not isinstance(campaign, dict):
            raise RegistryError(f"campaigns[{index}] must be an object")
        missing = sorted(REQUIRED_CAMPAIGN_FIELDS - set(campaign))
        if missing:
            raise RegistryError(
                f"campaigns[{index}] missing fields: {', '.join(missing)}"
            )
        key = campaign["campaign_key"]
        outreach_id = campaign["outreach_id"]
        if not isinstance(key, str) or not key.strip():
            raise RegistryError(
                f"campaigns[{index}].campaign_key must be non-empty"
            )
        if key in seen_keys:
            raise RegistryError(f"duplicate campaign_key: {key}")
        seen_keys.add(key)
        if not isinstance(outreach_id, str) or not outreach_id.startswith("LC-"):
            raise RegistryError(
                f"campaigns[{index}].outreach_id must start with LC-"
            )
        if outreach_id in seen_ids:
            raise RegistryError(f"duplicate outreach_id: {outreach_id}")
        seen_ids.add(outreach_id)
        if campaign["status"] not in ALLOWED_STATUSES:
            raise RegistryError(
                f"campaigns[{index}].status is unsupported: "
                f"{campaign['status']}"
            )
        if campaign["thread_mode"] not in ALLOWED_THREAD_MODES:
            raise RegistryError(
                f"campaigns[{index}].thread_mode is unsupported"
            )
        if (
            not isinstance(campaign["outbound_sequence"], int)
            or campaign["outbound_sequence"] < 0
        ):
            raise RegistryError(
                f"campaigns[{index}].outbound_sequence must be a "
                "non-negative integer"
            )
        if not isinstance(campaign["duplicate_detected"], bool):
            raise RegistryError(
                f"campaigns[{index}].duplicate_detected must be boolean"
            )
        if (
            not isinstance(campaign["duplicate_count"], int)
            or campaign["duplicate_count"] < 0
        ):
            raise RegistryError(
                f"campaigns[{index}].duplicate_count must be a "
                "non-negative integer"
            )
        if campaign["duplicate_detected"] != (campaign["duplicate_count"] > 0):
            raise RegistryError(
                f"campaigns[{index}] duplicate flag/count are inconsistent"
            )
        if not isinstance(campaign["inbound_since_last_outbound"], bool):
            raise RegistryError(
                f"campaigns[{index}].inbound_since_last_outbound must be boolean"
            )


def campaign_by_key(
    registry: dict[str, Any], campaign_key: str
) -> dict[str, Any]:
    for campaign in registry["campaigns"]:
        if campaign["campaign_key"] == campaign_key:
            return campaign
    raise RegistryError(f"unknown campaign_key: {campaign_key}")


def evaluate(
    registry: dict[str, Any],
    campaign_key: str,
    *,
    actor: str,
    action: str,
    mode: str,
    explicit_approval: bool = False,
    gmail_preflight_complete: bool = False,
) -> dict[str, Any]:
    if actor not in ALLOWED_ACTORS:
        raise RegistryError(f"unsupported actor: {actor}")
    if action not in ALLOWED_ACTIONS:
        raise RegistryError(f"unsupported action: {action}")
    if mode not in ALLOWED_MODES:
        raise RegistryError(f"unsupported mode: {mode}")

    policy = registry["policy"]
    campaign = campaign_by_key(registry, campaign_key)
    reasons: list[str] = []
    required_steps: list[str] = []

    if campaign["thread_mode"] == "existing_thread_only" and mode != "reply":
        reasons.append("an existing thread is mandatory for this campaign")

    if campaign["duplicate_detected"] and mode == "new":
        reasons.append(
            "a prior duplicate exists; a new standalone message is prohibited"
        )

    if action == "draft":
        allowed = not reasons
        if campaign["status"] in {"closed", "blocked"}:
            allowed = False
            reasons.append(f"campaign status is {campaign['status']}")
        return {
            "allowed": allowed,
            "campaign_key": campaign_key,
            "action": action,
            "mode": mode,
            "actor": actor,
            "outreach_id": campaign["outreach_id"],
            "reason": (
                "; ".join(reasons)
                if reasons
                else "drafting is permitted; sending is not implied"
            ),
            "required_steps": [
                "keep the draft in the existing thread",
                "do not send without a separate action-time approval",
            ],
        }

    # Send path: fail closed.
    if actor == "codex":
        reasons.append("Codex is draft-only and may never send outreach")

    if (
        actor == "chatgpt"
        and policy["chatgpt_send_requires_explicit_action_time_approval"]
        and not explicit_approval
    ):
        reasons.append(
            "ChatGPT send requires explicit action-time approval from Robert"
        )

    if actor == "human" and not explicit_approval:
        reasons.append(
            "human send must still record explicit approval for the gate"
        )

    if policy["gmail_sent_preflight_required"] and not gmail_preflight_complete:
        reasons.append("Gmail sent-mail/thread preflight has not been recorded")

    status = campaign["status"]
    if status in {"waiting_for_reply", "receipt_confirmed_waiting"}:
        reasons.append(
            f"campaign status is {status}; wait for a substantive inbound reply"
        )
    elif status in {"closed", "blocked"}:
        reasons.append(f"campaign status is {status}")
    elif status == "action_required_draft_ready":
        if not campaign["inbound_since_last_outbound"]:
            reasons.append(
                "no inbound request exists to justify another outbound message"
            )
        if mode != "reply":
            reasons.append(
                "the requested action must be a reply in the existing thread"
            )
    elif status == "ready_for_first_outbound":
        if campaign["outbound_sequence"] != 0:
            reasons.append(
                "ready_for_first_outbound requires outbound_sequence 0"
            )

    if reasons:
        return {
            "allowed": False,
            "campaign_key": campaign_key,
            "action": action,
            "mode": mode,
            "actor": actor,
            "outreach_id": campaign["outreach_id"],
            "reason": "; ".join(dict.fromkeys(reasons)),
            "required_steps": required_steps,
        }

    required_steps.extend(
        [
            "send exactly one message",
            "include the outreach ID in the internal send record",
            "update the registry immediately after sending",
            "apply the Gmail Outreach Lock label and wait for inbound response",
        ]
    )
    return {
        "allowed": True,
        "campaign_key": campaign_key,
        "action": action,
        "mode": mode,
        "actor": actor,
        "outreach_id": campaign["outreach_id"],
        "reason": "all current duplicate-prevention and approval gates passed",
        "required_steps": required_steps,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    default_registry = (
        Path(__file__).resolve().parents[2]
        / "config"
        / "outreach_registry_v1.json"
    )
    parser.add_argument("--registry", type=Path, default=default_registry)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="validate the shared registry")

    check = subparsers.add_parser("check", help="evaluate one proposed action")
    check.add_argument("--campaign", required=True)
    check.add_argument("--actor", choices=sorted(ALLOWED_ACTORS), required=True)
    check.add_argument("--action", choices=sorted(ALLOWED_ACTIONS), required=True)
    check.add_argument("--mode", choices=sorted(ALLOWED_MODES), required=True)
    check.add_argument("--explicit-approval", action="store_true")
    check.add_argument("--gmail-preflight-complete", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        registry = load_registry(args.registry)
        if args.command == "validate":
            result = {
                "valid": True,
                "schema": registry["schema"],
                "campaign_count": len(registry["campaigns"]),
            }
            print(json.dumps(result, indent=2))
            return 0

        result = evaluate(
            registry,
            args.campaign,
            actor=args.actor,
            action=args.action,
            mode=args.mode,
            explicit_approval=args.explicit_approval,
            gmail_preflight_complete=args.gmail_preflight_complete,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["allowed"] else 2
    except RegistryError as exc:
        print(
            json.dumps({"valid": False, "error": str(exc)}, indent=2),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
