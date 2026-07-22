from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MISSION_DIR = ROOT / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave"
ESCALATION = MISSION_DIR / "MISSIONWEAVE_JCP_SUPPORT_ESCALATION_2026-07-22.json"
OUT_JSON = MISSION_DIR / "MISSIONWEAVE_JCP_SUPPORT_SEND_RECEIPT_2026-07-22.json"
OUT_MD = MISSION_DIR / "MISSIONWEAVE_JCP_SUPPORT_SEND_RECEIPT_2026-07-22.md"

ESCALATION_SCHEMA = "lumencore.missionweave_jcp_support_escalation.v1"
PRIVATE_OBSERVATION_SCHEMA = (
    "lumencore.missionweave_jcp_support_gmail_sent_observation.private.v1"
)
PUBLIC_RECEIPT_SCHEMA = "lumencore.missionweave_jcp_support_send_receipt.v1"


class JcpSupportSendReceiptError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise JcpSupportSendReceiptError(f"JSON_READ_FAILED:{path.name}") from exc
    if not isinstance(value, dict):
        raise JcpSupportSendReceiptError(f"JSON_OBJECT_REQUIRED:{path.name}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_utc(value: str, field: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise JcpSupportSendReceiptError(f"INVALID_TIMESTAMP:{field}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise JcpSupportSendReceiptError(f"INVALID_TIMESTAMP:{field}")
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def require_sha256(value: Any, field: str) -> str:
    normalized = str(value or "").strip().upper()
    if len(normalized) != 64 or any(ch not in "0123456789ABCDEF" for ch in normalized):
        raise JcpSupportSendReceiptError(f"INVALID_SHA256:{field}")
    return normalized


def require_nonempty_private_id(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise JcpSupportSendReceiptError(f"PRIVATE_ID_REQUIRED:{field}")


def build_receipt(
    *,
    escalation: dict[str, Any],
    private_observation: dict[str, Any],
    private_observation_sha256: str,
    generated_utc: str,
) -> dict[str, Any]:
    if escalation.get("schema") != ESCALATION_SCHEMA:
        raise JcpSupportSendReceiptError("ESCALATION_SCHEMA_INVALID")
    draft = escalation.get("draft")
    action = escalation.get("action")
    deadline_block = escalation.get("deadline")
    if not isinstance(draft, dict) or not isinstance(action, dict):
        raise JcpSupportSendReceiptError("ESCALATION_CONTROLS_MISSING")
    if not isinstance(deadline_block, dict):
        raise JcpSupportSendReceiptError("ESCALATION_DEADLINE_MISSING")
    if draft.get("attachment_policy") != "NONE":
        raise JcpSupportSendReceiptError("ESCALATION_ATTACHMENT_POLICY_INVALID")

    request_identity = require_sha256(
        draft.get("outbound_request_identity_sha256"),
        "outbound_request_identity_sha256",
    )
    body_sha256 = require_sha256(draft.get("body_sha256"), "body_sha256")
    private_hash = require_sha256(
        private_observation_sha256,
        "private_observation_sha256",
    )

    if private_observation.get("schema") != PRIVATE_OBSERVATION_SCHEMA:
        raise JcpSupportSendReceiptError("PRIVATE_OBSERVATION_SCHEMA_INVALID")
    if private_observation.get("route_id") != escalation.get("route_id"):
        raise JcpSupportSendReceiptError("ROUTE_ID_MISMATCH")
    if private_observation.get("recipient", "").strip().lower() != str(
        draft.get("recipient", "")
    ).strip().lower():
        raise JcpSupportSendReceiptError("RECIPIENT_MISMATCH")
    if private_observation.get("subject", "").strip() != str(
        draft.get("subject", "")
    ).strip():
        raise JcpSupportSendReceiptError("SUBJECT_MISMATCH")
    if require_sha256(private_observation.get("body_sha256"), "observed_body") != body_sha256:
        raise JcpSupportSendReceiptError("BODY_HASH_MISMATCH")
    if require_sha256(
        private_observation.get("outbound_request_identity_sha256"),
        "observed_request_identity",
    ) != request_identity:
        raise JcpSupportSendReceiptError("REQUEST_IDENTITY_MISMATCH")
    if private_observation.get("attachment_count") != 0:
        raise JcpSupportSendReceiptError("ATTACHMENT_COUNT_NOT_ZERO")
    if private_observation.get("cc") not in ([], None):
        raise JcpSupportSendReceiptError("CC_NOT_EMPTY")
    if private_observation.get("bcc") not in ([], None):
        raise JcpSupportSendReceiptError("BCC_NOT_EMPTY")

    labels = private_observation.get("labels")
    if not isinstance(labels, list) or "SENT" not in labels or "DRAFT" in labels:
        raise JcpSupportSendReceiptError("GMAIL_SENT_STATE_INVALID")
    require_nonempty_private_id(private_observation.get("message_id"), "message_id")
    require_nonempty_private_id(private_observation.get("thread_id"), "thread_id")

    if private_observation.get("founder_review_confirmed") is not True:
        raise JcpSupportSendReceiptError("FOUNDER_REVIEW_NOT_CONFIRMED")
    if private_observation.get("action_time_human_unlock_confirmed") is not True:
        raise JcpSupportSendReceiptError("ACTION_TIME_HUMAN_UNLOCK_NOT_CONFIRMED")
    if private_observation.get("action_time_human_unlock_phrase") != action.get(
        "exact_human_unlock_phrase"
    ):
        raise JcpSupportSendReceiptError("ACTION_TIME_HUMAN_UNLOCK_PHRASE_MISMATCH")

    sent = parse_utc(str(private_observation.get("sent_utc", "")), "sent_utc")
    generated = parse_utc(generated_utc, "generated_utc")
    deadline = parse_utc(str(deadline_block.get("utc", "")), "deadline_utc")
    if sent >= deadline:
        raise JcpSupportSendReceiptError("SENT_AT_OR_AFTER_DEADLINE")
    if generated < sent:
        raise JcpSupportSendReceiptError("RECEIPT_GENERATED_BEFORE_SEND")

    return {
        "claim_boundary": (
            "This receipt proves only that a private Gmail observation matched the "
            "frozen no-attachment JCP support request and recorded it in SENT before "
            "the proposal deadline. It does not prove delivery, JCP response, JCP "
            "application submission, DD Form 2345 certification, SAM or SPRS "
            "compliance, DSIP submission, eligibility, acceptance, award, or funding."
        ),
        "controls": {
            "action_time_human_unlock_confirmed": True,
            "attachment_count_zero": True,
            "duplicate_send_allowed": False,
            "founder_review_confirmed": True,
            "gmail_message_id_exposed": False,
            "gmail_thread_id_exposed": False,
            "private_observation_hash_exposed": True,
            "private_observation_values_exposed": False,
            "request_identity_matched": True,
        },
        "delivery_state": "GMAIL_SENT_FOLDER_RECORDED",
        "generated_utc": iso_z(generated),
        "next_action": (
            "Monitor the existing JCP support thread and portal. Do not resend unless "
            "JCP explicitly requests a replacement."
        ),
        "outbound_request_identity_sha256": request_identity,
        "private_observation_sha256": private_hash,
        "route_id": escalation["route_id"],
        "schema": PUBLIC_RECEIPT_SCHEMA,
        "sent_utc": iso_z(sent),
    }


def render_markdown(receipt: dict[str, Any]) -> str:
    controls = receipt["controls"]
    checks = "\n".join(
        f"- [{'x' if value else ' '}] `{key}`"
        for key, value in controls.items()
        if key != "duplicate_send_allowed"
    )
    return f"""# MissionWeave JCP Support Send Receipt

**State:** `{receipt['delivery_state']}`

**Sent UTC:** `{receipt['sent_utc']}`

**Outbound request identity:** `{receipt['outbound_request_identity_sha256']}`

**Duplicate send allowed:** `false`

## Controls

{checks}

## Next Action

{receipt['next_action']}

## Claim Boundary

{receipt['claim_boundary']}
"""


def write_outputs(receipt: dict[str, Any], out_json: Path, out_md: Path) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(render_markdown(receipt), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture a privacy-safe JCP support SENT receipt from a private exact "
            "Gmail observation. This command never sends email."
        )
    )
    parser.add_argument("--private-sent-observation", type=Path, required=True)
    parser.add_argument("--as-of-utc", required=True)
    parser.add_argument("--escalation", type=Path, default=ESCALATION)
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=OUT_MD)
    args = parser.parse_args()

    receipt = build_receipt(
        escalation=read_json(args.escalation),
        private_observation=read_json(args.private_sent_observation),
        private_observation_sha256=sha256_file(args.private_sent_observation),
        generated_utc=args.as_of_utc,
    )
    write_outputs(receipt, args.out_json, args.out_md)
    print(json.dumps({
        "delivery_state": receipt["delivery_state"],
        "duplicate_send_allowed": False,
        "sent_utc": receipt["sent_utc"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
