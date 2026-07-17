from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_JSON = SPRINT / "DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.json"
OUT_MD = SPRINT / "DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.md"

AGENCY_GUIDANCE_RECEIVED_UTC = "2026-07-17T18:34:56Z"
FORMAL_PACKAGE_SENT_UTC = "2026-07-17T19:27:49Z"
FORMAL_MESSAGE_ID_SHA256 = (
    "1c0f162c52724e1fbd5fa89de5da825e421a700c5d1c475a67b2c195d62283d8"
)
SUBJECT = "RE: DARPA-SN-26-97 - Non-Proprietary RFI Response - LumenCore"


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema": "lumencore.darpa_sn_26_97_public_submission_receipt.v1",
        "as_of_date": "2026-07-17",
        "status": "FORMAL_RFI_PACKAGE_SENT_AGENCY_RECEIPT_PENDING",
        "opportunity": {
            "notice_id": "DARPA-SN-26-97",
            "title": "Request for Information: Low Resource Computing",
            "agency": "Defense Advanced Research Projects Agency",
            "official_page": "https://www.darpa.mil/work-with-us/opportunities/darpa-sn-26-97",
            "deadline_date": "2026-07-17",
            "deadline_time_status": "NOT_ASSERTED_IN_THIS_RECEIPT",
            "timely_submission_claimed": False,
        },
        "thread_reconciliation": {
            "evidence_method": "CONNECTED_GMAIL_THREAD_READ",
            "initial_body_response_sent": True,
            "agency_guidance_received_utc": AGENCY_GUIDANCE_RECEIVED_UTC,
            "agency_guidance_summary": (
                "The agency welcomed a submission related to the RFI in line with the "
                "SAM.gov instructions."
            ),
            "formal_package_sent_utc": FORMAL_PACKAGE_SENT_UTC,
            "recipient_domain": "darpa.mil",
            "subject": SUBJECT,
            "subject_sha256": hashlib.sha256(SUBJECT.encode("utf-8")).hexdigest(),
            "message_id_sha256": FORMAL_MESSAGE_ID_SHA256,
            "gmail_sent_label_observed": True,
            "immediate_delivery_rejection_observed": False,
            "agency_receipt_after_formal_package_observed": False,
            "duplicate_send_allowed": False,
        },
        "attachments": [
            {
                "role": "technical_response_pdf",
                "bytes": 19202,
                "sha256": "afd15408da826d6b92cb8561ee049c975104bc975998a068cb1c1ee6aaf196da",
            },
            {
                "role": "required_one_slide_pdf",
                "bytes": 3588,
                "sha256": "29a154e28899b2062859ec7d9ebcef438fe430a352d4d57e889be04f276a0964",
            },
        ],
        "response_boundary": {
            "classification": "UNCLASSIFIED / NON-PROPRIETARY",
            "internal_synthetic_evidence_only": True,
            "independent_validation_claimed": False,
            "hardware_validation_claimed": False,
            "field_or_operational_performance_claimed": False,
            "award_or_workshop_invitation_claimed": False,
        },
        "send_control": {
            "send_now": False,
            "do_not_duplicate_send": True,
            "next_action": (
                "Monitor the existing agency thread for a receipt, clarification, or workshop "
                "invitation. Do not resend the package without a specific agency request."
            ),
        },
        "claim_boundary": (
            "This receipt proves only that Gmail recorded a formal two-attachment package as sent "
            "after the agency's same-day guidance and preserves the attachment hashes. It does not "
            "prove delivery acceptance, deadline compliance, technical evaluation, independent "
            "validation, workshop selection, funding, award, or operational performance."
        ),
    }
    payload["receipt_sha256"] = stable_hash(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema") != "lumencore.darpa_sn_26_97_public_submission_receipt.v1":
        raise ValueError("DARPA public submission receipt schema is invalid")
    if payload.get("status") != "FORMAL_RFI_PACKAGE_SENT_AGENCY_RECEIPT_PENDING":
        raise ValueError("DARPA public submission state is stale")
    attachments = payload.get("attachments", [])
    if len(attachments) != 2:
        raise ValueError("DARPA receipt must bind exactly two attachments")
    if any(not re.fullmatch(r"[0-9a-f]{64}", row.get("sha256", "")) for row in attachments):
        raise ValueError("DARPA attachment hash is invalid")
    if payload["opportunity"]["timely_submission_claimed"] is not False:
        raise ValueError("DARPA deadline compliance must remain unclaimed")
    if payload["thread_reconciliation"]["duplicate_send_allowed"] is not False:
        raise ValueError("DARPA duplicate-send guard is missing")
    expected = dict(payload)
    observed_hash = expected.pop("receipt_sha256", None)
    if observed_hash != stable_hash(expected):
        raise ValueError("DARPA public submission receipt hash mismatch")
    rendered = json.dumps(payload, sort_keys=True).lower()
    for forbidden in (
        "recipient_email",
        "sender_email",
        "sender_phone",
        "sender_address",
        "meeting id",
        "passcode",
        "client_secret",
        "api_key",
        "private key",
    ):
        if forbidden in rendered:
            raise ValueError(f"Private marker entered DARPA public receipt: {forbidden}")


def render_markdown(payload: dict[str, Any]) -> str:
    thread = payload["thread_reconciliation"]
    lines = [
        "# DARPA-SN-26-97 Public Submission Receipt",
        "",
        f"Status: `{payload['status']}`",
        f"Formal package sent UTC: `{thread['formal_package_sent_utc']}`",
        f"Attachment count: `{len(payload['attachments'])}`",
        "",
        "## Attachment Bindings",
        "",
    ]
    for row in payload["attachments"]:
        lines.append(
            f"- `{row['role']}`: bytes=`{row['bytes']}` sha256=`{row['sha256']}`"
        )
    lines.extend(
        [
            "",
            "## Next Action",
            "",
            payload["send_control"]["next_action"],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            f"Receipt SHA-256: `{payload['receipt_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    validate_payload(payload)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "attachments": len(payload["attachments"]),
                "receipt_sha256": payload["receipt_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
