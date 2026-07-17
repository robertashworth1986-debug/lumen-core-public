from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BUILD_WEEK_DIR = ROOT / "grant_submissions" / "OPENAI_BUILD_WEEK_20260721"
SOURCE_RECEIPT = (
    BUILD_WEEK_DIR / "BUILD_WEEK_HANDOFF_SOURCE_RECEIPT_2026-07-17.json"
)
JSON_OUT = BUILD_WEEK_DIR / "BUILD_WEEK_HANDOFF_INTEGRITY_CONTROL_2026-07-17.json"
MD_OUT = BUILD_WEEK_DIR / "BUILD_WEEK_HANDOFF_INTEGRITY_CONTROL_2026-07-17.md"

EXPECTED_FILENAME = "LUMA_TO_CODEX_BUILD_WEEK_MASTER_HANDOFF_2026-07-17.md"
EXPECTED_RULE_COUNT = 10
CONTROL_BOUNDARY = (
    "Only the ten rules present in the message body are available. The missing handoff's "
    "Evidence Lattice design, later-work classification, bounded test shards, and exact "
    "judge-branch execution details must not be invented, approximated, or represented as read."
)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def artifact_status(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "present": True,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest().upper(),
    }


def build_payload() -> dict[str, Any]:
    receipt = read_json(SOURCE_RECEIPT)
    if receipt.get("schema") != "lumencore.build_week_handoff_source_receipt.v1":
        raise ValueError("Build Week handoff source receipt schema is invalid")

    handoff = receipt.get("referenced_handoff", {})
    local_search = receipt.get("bounded_local_search", {})
    rules = receipt.get("embedded_rules", [])
    if handoff.get("filename") != EXPECTED_FILENAME:
        raise ValueError("Build Week handoff filename changed")
    if handoff.get("stated_as_attached") is not True:
        raise ValueError("Source message did not state that the handoff was attached")
    if handoff.get("gmail_has_attachment") is not False:
        raise ValueError("Attachment state changed; refresh the source receipt")
    if handoff.get("gmail_attachment_count") != 0:
        raise ValueError("Attachment count changed; refresh the source receipt")
    if handoff.get("raw_mime_attachment_part_present") is not False:
        raise ValueError("Raw MIME attachment state changed; refresh the source receipt")
    if local_search.get("exact_filename_found") is not False:
        raise ValueError("The handoff was found locally; refresh and supersede this control")
    if local_search.get("exact_filename_match_count") != 0:
        raise ValueError("Local handoff match count changed; refresh the source receipt")
    if not isinstance(rules, list) or len(rules) != EXPECTED_RULE_COUNT:
        raise ValueError("Embedded Build Week rule set is incomplete")

    return {
        "schema": "lumencore.build_week_handoff_integrity_control.v1",
        "as_of_utc": receipt["observed_utc"],
        "status": "REFERENCED_HANDOFF_UNAVAILABLE_EXECUTION_SCOPE_BOUNDED",
        "referenced_filename": EXPECTED_FILENAME,
        "integrity_findings": {
            "message_stated_attachment": True,
            "gmail_attachment_present": False,
            "gmail_attachment_count": 0,
            "raw_mime_attachment_part_present": False,
            "bounded_local_exact_filename_found": False,
            "bounded_local_exact_filename_match_count": 0,
            "embedded_rule_count": len(rules),
            "full_handoff_body_available": False,
        },
        "available_authoritative_rules": rules,
        "unavailable_instruction_scope": [
            "Evidence Lattice visual design and acceptance criteria",
            "Identity of intentionally classified later local work",
            "Exact bounded repository shard list",
            "Any handoff-specific exclusions, file map, or completion criteria not quoted in the message body",
        ],
        "execution_control": {
            "may_execute_embedded_rules": True,
            "may_claim_full_handoff_read": False,
            "may_infer_missing_instructions": False,
            "may_merge_or_rebase_donor_branch_wholesale": False,
            "may_stage_all_paths": False,
            "may_send_email": False,
            "may_submit_devpost": False,
            "may_accept_legal_terms": False,
            "may_publish_video": False,
            "may_click_final_confirmation": False,
        },
        "recovery": {
            "required_action": (
                "Resend the named Markdown file as an actual attachment or place the exact file "
                "in an explicitly identified private handoff location, then refresh this receipt."
            ),
            "safe_continuation": (
                "Continue bounded repository work under the embedded rules and existing AGENTS.md "
                "controls, but hold the handoff-specific Evidence Lattice implementation."
            ),
        },
        "source_receipt": artifact_status(SOURCE_RECEIPT),
        "control_boundary": CONTROL_BOUNDARY,
        "claim_boundary": receipt["claim_boundary"],
    }


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema") != "lumencore.build_week_handoff_integrity_control.v1":
        raise ValueError("Build Week handoff control schema is invalid")
    if payload.get("status") != (
        "REFERENCED_HANDOFF_UNAVAILABLE_EXECUTION_SCOPE_BOUNDED"
    ):
        raise ValueError("Build Week handoff control status is invalid")
    findings = payload["integrity_findings"]
    if findings["gmail_attachment_present"] is not False:
        raise ValueError("Missing-attachment control cannot claim an attachment is present")
    if findings["full_handoff_body_available"] is not False:
        raise ValueError("Missing-attachment control cannot claim the full handoff is available")
    controls = payload["execution_control"]
    prohibited = (
        "may_claim_full_handoff_read",
        "may_infer_missing_instructions",
        "may_merge_or_rebase_donor_branch_wholesale",
        "may_stage_all_paths",
        "may_send_email",
        "may_submit_devpost",
        "may_accept_legal_terms",
        "may_publish_video",
        "may_click_final_confirmation",
    )
    if any(controls[name] for name in prohibited):
        raise ValueError("A fail-closed Build Week handoff control was weakened")
    rendered = json.dumps(payload, sort_keys=True).lower()
    for forbidden in (
        "@gmail.com",
        "message_id",
        "thread_id",
        "raw_mime_base64url",
        "c:\\users\\",
        "client_secret",
        "refresh_token",
        "api_key",
    ):
        if forbidden in rendered:
            raise ValueError(f"Public handoff control contains private marker: {forbidden}")


def render_markdown(payload: dict[str, Any]) -> str:
    findings = payload["integrity_findings"]
    controls = payload["execution_control"]
    lines = [
        "# Build Week Handoff Integrity Control",
        "",
        f"As of UTC: `{payload['as_of_utc']}`",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Finding",
        "",
        (
            f"The self-sent instruction message named `{payload['referenced_filename']}` as an "
            "attachment, but connected Gmail metadata and raw MIME show zero attachments. A "
            "bounded exact-filename search also found zero local matches."
        ),
        "",
        f"- Embedded rules available: `{findings['embedded_rule_count']}`",
        f"- Full handoff body available: `{str(findings['full_handoff_body_available']).lower()}`",
        f"- May claim full handoff read: `{str(controls['may_claim_full_handoff_read']).lower()}`",
        f"- May infer missing instructions: `{str(controls['may_infer_missing_instructions']).lower()}`",
        "",
        "## Available Rules",
        "",
    ]
    lines.extend(
        f"{index}. {rule}"
        for index, rule in enumerate(payload["available_authoritative_rules"], start=1)
    )
    lines.extend(
        [
            "",
            "## Unavailable Scope",
            "",
            *[f"- {item}" for item in payload["unavailable_instruction_scope"]],
            "",
            "## Recovery",
            "",
            f"- Required: {payload['recovery']['required_action']}",
            f"- Safe continuation: {payload['recovery']['safe_continuation']}",
            "",
            "## Control Boundary",
            "",
            payload["control_boundary"],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    validate_payload(payload)
    BUILD_WEEK_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    MD_OUT.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "embedded_rule_count": payload["integrity_findings"][
                    "embedded_rule_count"
                ],
                "json": JSON_OUT.relative_to(ROOT).as_posix(),
                "markdown": MD_OUT.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
