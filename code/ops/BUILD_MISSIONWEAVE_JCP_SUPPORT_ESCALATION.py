from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "missionweave_jcp_support_escalation_v1.json"
QUEUE = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
)
MISSION_DIR = (
    ROOT / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave"
)
OUT_JSON = MISSION_DIR / "MISSIONWEAVE_JCP_SUPPORT_ESCALATION_2026-07-22.json"
OUT_MD = MISSION_DIR / "MISSIONWEAVE_JCP_SUPPORT_ESCALATION_2026-07-22.md"

PACKET_SCHEMA = "lumencore.missionweave_jcp_support_escalation.v1"
CONFIG_SCHEMA = "lumencore.missionweave_jcp_support_escalation_config.v1"

REQUIRED_OPERATOR_OUTCOMES = {
    "official_application_receipt_obtained": (
        "PAUSE_AND_REVIEW_OFFICIAL_RECEIPT_BEFORE_DSIP"
    ),
    "official_support_requests_secure_details": (
        "PROVIDE_ONLY_THROUGH_OFFICIAL_SECURE_CHANNEL"
    ),
    "official_support_says_prerequisites_incomplete": (
        "STOP_NO_VOLUME_V_OR_FINAL_SUBMISSION"
    ),
    "portal_has_no_official_receipt_at_hard_stop": (
        "STOP_NO_VOLUME_V_OR_FINAL_SUBMISSION"
    ),
}


class JcpSupportEscalationError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JcpSupportEscalationError(f"JSON_READ_FAILED:{path.name}") from exc
    if not isinstance(value, dict):
        raise JcpSupportEscalationError(f"JSON_OBJECT_REQUIRED:{path.name}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise JcpSupportEscalationError("INVALID_AWARE_TIMESTAMP") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise JcpSupportEscalationError("INVALID_AWARE_TIMESTAMP")
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def require_config(config: dict[str, Any]) -> None:
    if config.get("schema") != CONFIG_SCHEMA:
        raise JcpSupportEscalationError("CONFIG_SCHEMA_INVALID")
    if config.get("attachment_policy") != "NONE":
        raise JcpSupportEscalationError("ATTACHMENTS_MUST_BE_DISABLED")
    if config.get("recipient") != "jcp-admin@dla.mil":
        raise JcpSupportEscalationError("RECIPIENT_NOT_CANONICAL")
    if config.get("topic") != "DLA26BZ03-NV011":
        raise JcpSupportEscalationError("TOPIC_INVALID")
    paragraphs = config.get("body_paragraphs")
    if not isinstance(paragraphs, list) or not paragraphs:
        raise JcpSupportEscalationError("BODY_PARAGRAPHS_REQUIRED")
    if any(not isinstance(item, str) or not item.strip() for item in paragraphs):
        raise JcpSupportEscalationError("BODY_PARAGRAPH_INVALID")
    require_official_support(config)
    require_operator_policy(config)


def require_official_support(config: dict[str, Any]) -> None:
    support = config.get("official_support")
    if not isinstance(support, dict):
        raise JcpSupportEscalationError("OFFICIAL_SUPPORT_REQUIRED")
    if support.get("availability") != "24/7/365":
        raise JcpSupportEscalationError("OFFICIAL_SUPPORT_AVAILABILITY_INVALID")
    if support.get("customer_interaction_center_phone") != "1-877-352-2255":
        raise JcpSupportEscalationError("OFFICIAL_SUPPORT_PHONE_INVALID")
    if support.get("jcp_email") != config.get("recipient"):
        raise JcpSupportEscalationError("OFFICIAL_SUPPORT_JCP_EMAIL_MISMATCH")
    source_url = support.get("source_url")
    if not isinstance(source_url, str):
        raise JcpSupportEscalationError("OFFICIAL_SUPPORT_SOURCE_INVALID")
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or parsed.hostname not in {"dla.mil", "www.dla.mil"}:
        raise JcpSupportEscalationError("OFFICIAL_SUPPORT_SOURCE_INVALID")
    parse_utc(str(support.get("verified_utc", "")))
    private_inputs = support.get("private_caller_inputs_required")
    if private_inputs != ["entity_name", "cage_or_ncage_code"]:
        raise JcpSupportEscalationError("PRIVATE_CALLER_INPUTS_INVALID")


def require_operator_policy(config: dict[str, Any]) -> None:
    policy = config.get("operator_policy")
    if not isinstance(policy, dict):
        raise JcpSupportEscalationError("OPERATOR_POLICY_REQUIRED")
    call_script = policy.get("call_script_paragraphs")
    if not isinstance(call_script, list) or not call_script:
        raise JcpSupportEscalationError("CALL_SCRIPT_REQUIRED")
    if any(not isinstance(item, str) or not item.strip() for item in call_script):
        raise JcpSupportEscalationError("CALL_SCRIPT_INVALID")
    script = "\n\n".join(call_script).lower()
    forbidden_literals = (
        "uei:",
        "cage code:",
        "password",
        "one-time code",
        "certified jcp",
    )
    if any(item in script for item in forbidden_literals):
        raise JcpSupportEscalationError("CALL_SCRIPT_CONTAINS_FORBIDDEN_LITERAL")
    deadline = parse_utc(config["deadline_utc"])
    hard_stop = parse_utc(str(policy.get("hard_stop_utc", "")))
    buffer_seconds = int((deadline - hard_stop).total_seconds())
    if buffer_seconds != 90 * 60:
        raise JcpSupportEscalationError("HARD_STOP_BUFFER_INVALID")
    if policy.get("outcomes") != REQUIRED_OPERATOR_OUTCOMES:
        raise JcpSupportEscalationError("OPERATOR_OUTCOMES_INVALID")
    prohibited = policy.get("prohibited_substitutes")
    if not isinstance(prohibited, list) or len(prohibited) < 3:
        raise JcpSupportEscalationError("PROHIBITED_SUBSTITUTES_REQUIRED")


def require_portal_receipt(receipt: dict[str, Any], config: dict[str, Any]) -> None:
    if receipt.get("schema") != config["portal_receipt_required_schema"]:
        raise JcpSupportEscalationError("PORTAL_RECEIPT_SCHEMA_INVALID")
    if receipt.get("status") != config["portal_receipt_required_status"]:
        raise JcpSupportEscalationError("PORTAL_RECEIPT_STATUS_INVALID")
    if receipt.get("topic") != config["topic"]:
        raise JcpSupportEscalationError("PORTAL_RECEIPT_TOPIC_MISMATCH")
    events = receipt.get("events")
    observations = receipt.get("portal_observations")
    if not isinstance(events, dict) or not isinstance(observations, dict):
        raise JcpSupportEscalationError("PORTAL_RECEIPT_FACTS_MISSING")
    required_events = {
        "organization_created_successfully": True,
        "jcp_application_submitted": False,
        "official_application_submission_receipt_available": False,
    }
    for key, expected in required_events.items():
        if events.get(key) is not expected:
            raise JcpSupportEscalationError(f"PORTAL_EVENT_INVALID:{key}")
    if observations.get("sam_status") != "N/A":
        raise JcpSupportEscalationError("PORTAL_SAM_STATUS_NOT_UNAVAILABLE")


def require_component_lane_hold(queue: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    actions = queue.get("actions")
    if not isinstance(actions, list):
        raise JcpSupportEscalationError("ACTION_QUEUE_INVALID")
    matches = [
        row
        for row in actions
        if isinstance(row, dict)
        and row.get("lane_id") == config["existing_component_lane_id"]
    ]
    if len(matches) != 1:
        raise JcpSupportEscalationError("COMPONENT_LANE_NOT_UNIQUE")
    lane = matches[0]
    if lane.get("action_state") != config["existing_component_lane_required_state"]:
        raise JcpSupportEscalationError("COMPONENT_LANE_NOT_HELD")
    if lane.get("send_now") is not False:
        raise JcpSupportEscalationError("COMPONENT_LANE_SEND_NOT_FALSE")
    if lane.get("recorded_proactive_send_count") != lane.get("max_proactive_sends"):
        raise JcpSupportEscalationError("COMPONENT_LANE_LIMIT_NOT_RECONCILED")
    return lane


def build_packet(
    *,
    config: dict[str, Any],
    queue: dict[str, Any],
    portal_receipt: dict[str, Any],
    portal_receipt_sha256: str,
    generated_utc: str,
    founder_review_confirmed: bool = False,
    fresh_duplicate_check_confirmed: bool = False,
    gmail_draft_created: bool = False,
) -> dict[str, Any]:
    require_config(config)
    require_portal_receipt(portal_receipt, config)
    if (
        len(portal_receipt_sha256) != 64
        or any(ch not in "0123456789ABCDEFabcdef" for ch in portal_receipt_sha256)
    ):
        raise JcpSupportEscalationError("PORTAL_RECEIPT_SHA256_INVALID")
    held_lane = require_component_lane_hold(queue, config)
    generated = parse_utc(generated_utc)
    deadline = parse_utc(config["deadline_utc"])
    seconds_remaining = max(0, int((deadline - generated).total_seconds()))

    body = "\n\n".join(config["body_paragraphs"])
    forbidden_literals = (
        "password",
        "one-time code",
        "otp:",
        "physical address",
        "uei:",
        "cage code:",
    )
    lowered_body = body.lower()
    if any(item in lowered_body for item in forbidden_literals):
        raise JcpSupportEscalationError("DRAFT_CONTAINS_FORBIDDEN_LITERAL")

    readiness = {
        "component_route_duplicate_block_preserved": True,
        "draft_contains_no_attachment": True,
        "fresh_duplicate_check_confirmed": bool(fresh_duplicate_check_confirmed),
        "founder_review_confirmed": bool(founder_review_confirmed),
        "gmail_draft_created": bool(gmail_draft_created),
        "portal_receipt_reconciled_privately": True,
    }
    action_time_ready = all(readiness.values())
    missing_readiness_controls = [
        key for key, passed in readiness.items() if not passed
    ]
    return {
        "action": {
            "action_time_ready": action_time_ready,
            "exact_human_unlock_phrase": config["exact_human_unlock_phrase"],
            "missing_readiness_controls": missing_readiness_controls,
            "send_authorized": False,
            "send_decision": (
                "READY_FOR_ACTION_TIME_HUMAN_UNLOCK_NOT_AUTHORIZED"
                if action_time_ready
                else "HOLD_MISSING_READINESS_CONTROLS_AND_HUMAN_UNLOCK"
            ),
            "send_performed": False,
        },
        "claim_boundary": (
            "This packet prepares one JCP portal-support request. It does not prove "
            "JCP application submission, DD Form 2345 certification, SAM or SPRS "
            "compliance, proposal submission, eligibility, or award status."
        ),
        "deadline": {
            "display": config["deadline_display"],
            "seconds_remaining_at_generation": seconds_remaining,
            "utc": iso_z(deadline),
        },
        "draft": {
            "attachment_policy": "NONE",
            "body": body,
            "mailbox_draft_created": bool(gmail_draft_created),
            "recipient": config["recipient"],
            "recipient_role": config["recipient_role"],
            "subject": config["subject"],
        },
        "existing_component_route": {
            "action_state": held_lane["action_state"],
            "lane_id": held_lane["lane_id"],
            "recorded_proactive_send_count": held_lane[
                "recorded_proactive_send_count"
            ],
            "send_now": False,
        },
        "generated_utc": iso_z(generated),
        "portal_evidence": {
            "application_submitted": False,
            "organization_created": True,
            "private_hash_redacted": True,
            "private_path_redacted": True,
            "private_receipt_hash_verified_locally": True,
            "private_values_redacted": True,
            "sam_status_available": False,
        },
        "official_support": {
            **config["official_support"],
            "private_caller_input_values_included": False,
        },
        "operator_policy": {
            "call_now": generated < deadline,
            "call_script": "\n\n".join(
                config["operator_policy"]["call_script_paragraphs"]
            ),
            "hard_stop_display": config["operator_policy"]["hard_stop_display"],
            "hard_stop_reason": config["operator_policy"]["hard_stop_reason"],
            "hard_stop_utc": iso_z(
                parse_utc(config["operator_policy"]["hard_stop_utc"])
            ),
            "outcomes": config["operator_policy"]["outcomes"],
            "prohibited_substitutes": config["operator_policy"][
                "prohibited_substitutes"
            ],
        },
        "proposal_workspace": config["proposal_workspace"],
        "readiness": readiness,
        "route_id": config["route_id"],
        "schema": PACKET_SCHEMA,
        "sensitive_information_policy": config["sensitive_information_policy"],
        "support_phone": config["support_phone"],
        "topic": config["topic"],
    }


def render_markdown(packet: dict[str, Any]) -> str:
    action = packet["action"]
    draft = packet["draft"]
    readiness = packet["readiness"]
    official_support = packet["official_support"]
    operator_policy = packet["operator_policy"]
    checks = "\n".join(
        f"- [{'x' if passed else ' '}] `{key}`"
        for key, passed in readiness.items()
    )
    return f"""# MissionWeave JCP Support Escalation

**State:** `{action['send_decision']}`

**Deadline:** {packet['deadline']['display']}

**Route:** `{packet['route_id']}`

**Send performed:** `false`

## Decision Controls

{checks}

The existing DSIP/component follow-up lane remains exhausted and must not be
reused. This is a separate JCP portal-support route. Even when every readiness
check is true, this builder never sends email and never sets `send_authorized`
to true. The action-time phrase is:

`{action['exact_human_unlock_phrase']}`

## Draft

**To:** {draft['recipient']}

**Subject:** {draft['subject']}

**Attachments:** None

{draft['body']}

## Claim Boundary

{packet['claim_boundary']}

## Call Now

The official DLA Customer Interaction Center is listed as available
`{official_support['availability']}`. Call `{official_support['customer_interaction_center_phone']}`
and have the entity name and CAGE/NCAGE code ready to provide privately when
the agent asks. Do not put either value in this public packet.

Official source: {official_support['source_url']}

### Script

{operator_policy['call_script']}

### Stop Rule

**Operator hard stop:** {operator_policy['hard_stop_display']}

{operator_policy['hard_stop_reason']} If no official application-submission
receipt exists at that point, do not upload a substitute, certify Volume V, or
submit the proposal as though JCP were complete.

Prohibited substitutes:

{chr(10).join(f'- {item}' for item in operator_policy['prohibited_substitutes'])}
"""


def write_outputs(packet: dict[str, Any], out_json: Path, out_md: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(packet, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(render_markdown(packet), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a bounded, no-attachment JCP portal-support escalation "
            "without sending email or authorizing external action."
        )
    )
    parser.add_argument("--portal-receipt", type=Path, required=True)
    parser.add_argument("--as-of-utc", required=True)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--queue", type=Path, default=QUEUE)
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=OUT_MD)
    parser.add_argument("--confirm-founder-review", action="store_true")
    parser.add_argument("--confirm-fresh-duplicate-check", action="store_true")
    parser.add_argument("--confirm-gmail-draft-created", action="store_true")
    args = parser.parse_args()

    portal_receipt = read_json(args.portal_receipt)
    packet = build_packet(
        config=read_json(args.config),
        queue=read_json(args.queue),
        portal_receipt=portal_receipt,
        portal_receipt_sha256=sha256_file(args.portal_receipt),
        generated_utc=args.as_of_utc,
        founder_review_confirmed=args.confirm_founder_review,
        fresh_duplicate_check_confirmed=args.confirm_fresh_duplicate_check,
        gmail_draft_created=args.confirm_gmail_draft_created,
    )
    write_outputs(packet, args.out_json, args.out_md)
    print(json.dumps({
        "action_time_ready": packet["action"]["action_time_ready"],
        "send_authorized": False,
        "send_performed": False,
        "status": packet["action"]["send_decision"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
