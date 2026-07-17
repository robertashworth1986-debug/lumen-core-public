from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

SUBMISSION_RECEIPT = SPRINT_DIR / "EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.json"
CDC_RECEIPT = SPRINT_DIR / "CDC_AI_ACQUISITION_RFI_ENGAGEMENT_RECEIPT_2026-07-16.json"
LANL_RECEIPT = SPRINT_DIR / "LANL_VISION_FOLLOWUP_ENGAGEMENT_RECEIPT_2026-07-16.json"
EPRI_TEMPLATE = SPRINT_DIR / "EPRI_OPEN_POWER_AI_MOU_RESPONSE_TEMPLATE_2026-07-16.md"
EPRI_RECEIPT = SPRINT_DIR / "EPRI_OPEN_POWER_AI_MOU_ENGAGEMENT_RECEIPT_2026-07-16.json"
NASHVILLE_MANIFEST = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json"
)
NASHVILLE_FACT_RESOLUTION = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json"
)

OUT_JSON = OUT_OPS / "external_engagement_response_register_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "external_engagement_response_register.json"
CANONICAL_JSON = SPRINT_DIR / "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json"
OUT_MD = SPRINT_DIR / "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.md"

PRIVATE_MARKERS = (
    "full legal name:",
    "signatory email:",
    "signatory telephone:",
    "meeting id",
    "passcode",
    "zoom.us",
    "client_secret",
    "refresh_token",
    "api_key",
    "private key",
)

REGISTER_BOUNDARY = (
    "This register records bounded communication and portal-preparation states. It does not prove "
    "evaluation, selection, endorsement, independent validation, a pilot, funding, an award, a "
    "contract, deployment, realized savings, or technical performance."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def artifact_status(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "present": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else 0,
        "sha256": sha256_file(path) if path.is_file() else None,
    }


def submission_by_notice(receipt: dict[str, Any], notice_id: str) -> dict[str, Any]:
    for row in receipt.get("submissions", []):
        if isinstance(row, dict) and row.get("notice_id") == notice_id:
            return row
    raise ValueError(f"Missing verified submission receipt for {notice_id}")


def verify_attachment(receipt_row: dict[str, Any]) -> dict[str, Any]:
    attachment = receipt_row.get("attachment")
    if isinstance(attachment, dict):
        path_value = attachment.get("path")
        expected_hash = attachment.get("sha256")
        expected_bytes = attachment.get("bytes")
    else:
        path_value = attachment
        expected_hash = receipt_row.get("attachment_sha256")
        expected_bytes = receipt_row.get("attachment_bytes")

    path = ROOT / str(path_value)
    actual_hash = sha256_file(path)
    actual_bytes = path.stat().st_size
    return {
        "path": rel(path),
        "present": True,
        "expected_sha256": str(expected_hash).upper(),
        "actual_sha256": actual_hash,
        "sha256_match": actual_hash == str(expected_hash).upper(),
        "expected_bytes": int(expected_bytes),
        "actual_bytes": actual_bytes,
        "bytes_match": actual_bytes == int(expected_bytes),
    }


def lane_hash(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_payload(generated_utc: str | None = None) -> dict[str, Any]:
    submissions = read_json(SUBMISSION_RECEIPT)
    cdc = read_json(CDC_RECEIPT)
    lanl = read_json(LANL_RECEIPT)
    epri = read_json(EPRI_RECEIPT)
    nashville = read_json(NASHVILLE_MANIFEST)
    nashville_resolution = read_json(NASHVILLE_FACT_RESOLUTION)

    if nashville_resolution.get("status") != "SIX_FOUNDER_CONFIRMATIONS_REQUIRED":
        raise ValueError("Nashville EC human-fact resolution is missing or stale")

    nasa = submission_by_notice(submissions, "80TECH26RFI0020")
    army = submission_by_notice(submissions, "ACCAPGAIDPRFI4")

    records: list[dict[str, Any]] = [
        {
            "lane_id": "nashville_ec_takeoff_fall_2026",
            "organization": "Nashville Entrepreneur Center",
            "state": "PORTAL_PACKET_READY_HUMAN_FACTS_REQUIRED",
            "deadline": "2026-07-17",
            "decision": "COMPLETE_HUMAN_FACTS_AND_FINAL_PREVIEW",
            "response_channel": "PORTAL",
            "response_ready": True,
            "send_now": False,
            "do_not_duplicate_send": False,
            "action_gate": "Founder answers all six concise confirmation prompts, reviews the complete live portal preview plus any terms or fee, and authorizes final submission at action time.",
            "response_artifact": rel(NASHVILLE_FACT_RESOLUTION),
            "supporting_artifacts": [
                rel(NASHVILLE_MANIFEST),
                rel(NASHVILLE_FACT_RESOLUTION),
            ],
            "next_action": "Collect the six founder confirmations in the resolution artifact before the application closes; do not invent revenue, customers, demographics, founder history, investment, or debt.",
            "claim_boundary": nashville.get("claim_boundary"),
        },
        {
            "lane_id": "epri_open_power_ai_mou",
            "organization": "EPRI Open Power AI Consortium",
            "state": epri["acknowledgment"]["status"],
            "deadline": None,
            "decision": "MONITOR_FOR_MOU_NO_DUPLICATE",
            "response_channel": "EMAIL_REPLY",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_send_before": epri["acknowledgment"]["earliest_follow_up_date"],
            "action_gate": "Reply only when EPRI sends the MOU, requests a correction, or asks for additional onboarding information.",
            "response_artifact": rel(EPRI_RECEIPT),
            "supporting_artifacts": [rel(EPRI_TEMPLATE)],
            "next_action": "Monitor the existing thread for the DocuSign envelope or a clarification request; do not resend identity details.",
            "claim_boundary": epri["claim_boundary"],
        },
        {
            "lane_id": "cdc_ai_acquisition_rfi",
            "organization": "Centers for Disease Control and Prevention",
            "state": cdc["acknowledgment"]["status"],
            "deadline": "2026-07-30T21:00:00Z",
            "decision": "MONITOR_NO_REPLY_REQUIRED",
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": "Reply only if CDC asks for clarification, replacement material, or scheduling.",
            "response_artifact": rel(CDC_RECEIPT),
            "next_action": "Preserve the acknowledgment and monitor the existing thread; do not resend the response.",
            "claim_boundary": cdc["claim_boundary"],
        },
        {
            "lane_id": "lanl_vision_licensing_followup",
            "organization": "Los Alamos National Laboratory",
            "state": lanl["acknowledgment"]["status"],
            "deadline": None,
            "decision": "MONITOR_THEN_ONE_BOUNDED_FOLLOW_UP",
            "response_channel": "EMAIL",
            "response_ready": True,
            "send_now": False,
            "do_not_duplicate_send": True,
            "no_send_before": lanl["acknowledgment"]["earliest_follow_up_date"],
            "action_gate": "No follow-up before 2026-07-23 unless LANL replies first; any NDA, licensing term, export-control question, or disclosure remains human-reviewed.",
            "response_artifact": rel(LANL_RECEIPT),
            "next_action": "Wait for LANL. If no reply by July 23, use the single bounded follow-up template in this register.",
            "follow_up_template": {
                "subject": "Follow-up: LumenCore package for LANL VISION licensing discussion",
                "body": (
                    "Michael and Neil,\n\nI am following up on the bounded LumenCore package sent July 16. "
                    "Would a short Stage 0 diligence session be useful to decide whether a VISION evaluation or "
                    "licensing discussion is warranted? I am not asserting a license, LANL endorsement, field "
                    "validation, or production readiness. I would welcome your preferred next step and any "
                    "confidentiality or data-boundary requirements.\n\nBest regards,\nRobert Ashworth\nLumenCore"
                ),
            },
            "claim_boundary": lanl["claim_boundary"],
        },
        {
            "lane_id": "nasa_data_center_rfi",
            "organization": "NASA",
            "state": "SENT_VERIFIED_RESPONSE_PENDING",
            "deadline": "2026-07-17T21:00:00Z",
            "decision": "MONITOR_NO_DUPLICATE",
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": "Respond only to an agency clarification or replacement request.",
            "response_artifact": rel(SUBMISSION_RECEIPT),
            "next_action": "Retain the SENT receipt and attachment hash; do not resend before the deadline.",
            "claim_boundary": nasa["claim_boundary"],
        },
        {
            "lane_id": "army_aidp_draft_cfs_feedback",
            "organization": "U.S. Army",
            "state": "SENT_VERIFIED_RESPONSE_PENDING",
            "deadline": None,
            "decision": "MONITOR_NO_DUPLICATE",
            "response_channel": "EMAIL",
            "response_ready": False,
            "send_now": False,
            "do_not_duplicate_send": True,
            "action_gate": "Respond only to an agency clarification or replacement request.",
            "response_artifact": rel(SUBMISSION_RECEIPT),
            "next_action": "Retain the SENT receipt and attachment hash; monitor for agency feedback.",
            "claim_boundary": army["claim_boundary"],
        },
    ]

    for row in records:
        row["record_sha256"] = lane_hash(row)

    attachment_checks = {
        "army": verify_attachment(army),
        "nasa": verify_attachment(nasa),
        "cdc": verify_attachment(cdc["submission"]),
        "lanl": verify_attachment(lanl["submission"]),
    }
    all_attachment_checks_pass = all(
        check["sha256_match"] and check["bytes_match"]
        for check in attachment_checks.values()
    )
    if not all_attachment_checks_pass:
        raise ValueError("One or more engagement receipt attachments failed integrity verification")

    payload: dict[str, Any] = {
        "schema": "lumencore.external_engagement_response_register.v1",
        "generated_utc": generated_utc or now_utc(),
        "as_of_date": "2026-07-16",
        "status": "CURRENT_RESPONSE_CONTROL_HUMAN_GATED",
        "direct_answer": (
            "Finish the six-confirmation Nashville EC human-fact gate before July 17. The EPRI administrative "
            "reply was sent and is now monitor-only with CDC, LANL, NASA, and Army; duplicate sends would "
            "reduce credibility."
        ),
        "summary": {
            "record_count": len(records),
            "immediate_human_action_count": sum(
                1 for row in records if row["lane_id"] == "nashville_ec_takeoff_fall_2026"
            ),
            "monitor_only_count": sum(1 for row in records if str(row["decision"]).startswith("MONITOR")),
            "do_not_duplicate_send_count": sum(1 for row in records if row["do_not_duplicate_send"]),
            "verified_attachment_count": len(attachment_checks),
            "all_attachment_checks_pass": all_attachment_checks_pass,
            "autonomous_external_send_allowed": False,
            "autonomous_final_portal_submission_allowed": False,
        },
        "records": records,
        "attachment_checks": attachment_checks,
        "inbox_risk_filters": [
            {
                "pattern": "Paid third-party SAM renewal solicitation",
                "decision": "DO_NOT_TREAT_AS_OFFICIAL_SAM_NOTICE",
                "safe_action": "Verify registration status and renewal tasks only inside SAM.gov or through an official .gov notice.",
            },
            {
                "pattern": "Paid sponsor activation presented near a venture review",
                "decision": "DO_NOT_TREAT_AS_REQUIRED_FOR_FUND_REVIEW",
                "safe_action": "Keep sponsor purchases separate from investment or accelerator evaluation unless written terms prove otherwise.",
            },
        ],
        "source_artifacts": {
            "external_submission_receipt": artifact_status(SUBMISSION_RECEIPT),
            "cdc_engagement_receipt": artifact_status(CDC_RECEIPT),
            "lanl_engagement_receipt": artifact_status(LANL_RECEIPT),
            "epri_response_template": artifact_status(EPRI_TEMPLATE),
            "epri_engagement_receipt": artifact_status(EPRI_RECEIPT),
            "nashville_application_manifest": artifact_status(NASHVILLE_MANIFEST),
            "nashville_human_fact_resolution": artifact_status(NASHVILLE_FACT_RESOLUTION),
        },
        "claim_boundary": REGISTER_BOUNDARY,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "canonical_json": rel(CANONICAL_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["register_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# External Engagement Response Register - 2026-07-16",
        "",
        payload["direct_answer"],
        "",
        "## Control Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Engagement records: `{summary['record_count']}`",
        f"- Immediate human actions: `{summary['immediate_human_action_count']}`",
        f"- Monitor-only lanes: `{summary['monitor_only_count']}`",
        f"- Do-not-duplicate lanes: `{summary['do_not_duplicate_send_count']}`",
        f"- Verified attachments: `{summary['verified_attachment_count']}`",
        f"- All attachment checks pass: `{str(summary['all_attachment_checks_pass']).lower()}`",
        f"- Autonomous external send allowed: `{str(summary['autonomous_external_send_allowed']).lower()}`",
        f"- Autonomous final portal submit allowed: `{str(summary['autonomous_final_portal_submission_allowed']).lower()}`",
        f"- Register SHA-256: `{payload['register_sha256']}`",
        "",
        "## Response Queue",
        "",
        "| Organization | State | Decision | Deadline / Hold | Duplicate Send |",
        "|---|---|---|---|---:|",
    ]
    for row in payload["records"]:
        deadline = row.get("deadline") or row.get("no_send_before") or "None"
        lines.append(
            f"| {row['organization']} | `{row['state']}` | `{row['decision']}` | {deadline} | "
            f"`{str(row['do_not_duplicate_send']).lower()}` |"
        )

    for row in payload["records"]:
        lines.extend(
            [
                "",
                f"### {row['organization']}",
                "",
                f"- Lane: `{row['lane_id']}`",
                f"- State: `{row['state']}`",
                f"- Decision: `{row['decision']}`",
                f"- Response channel: `{row['response_channel']}`",
                f"- Response ready: `{str(row['response_ready']).lower()}`",
                f"- Send now: `{str(row['send_now']).lower()}`",
                f"- Action gate: {row['action_gate']}",
                f"- Next action: {row['next_action']}",
                f"- Response artifact: `{row['response_artifact']}`",
                f"- Claim boundary: {row['claim_boundary']}",
                f"- Record SHA-256: `{row['record_sha256']}`",
            ]
        )
        template = row.get("follow_up_template")
        if isinstance(template, dict):
            lines.extend(
                [
                    "",
                    f"**Held follow-up subject:** {template['subject']}",
                    "",
                    "```text",
                    template["body"],
                    "```",
                ]
            )

    lines.extend(["", "## Inbox Risk Filters", ""])
    for row in payload["inbox_risk_filters"]:
        lines.extend(
            [
                f"- **{row['pattern']}**: `{row['decision']}`",
                f"  Safe action: {row['safe_action']}",
            ]
        )

    lines.extend(["", "## Source Integrity", ""])
    for key, row in payload["source_artifacts"].items():
        lines.append(
            f"- `{key}`: present=`{str(row['present']).lower()}` bytes=`{row['bytes']}` sha256=`{row['sha256']}` path=`{row['path']}`"
        )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def ensure_public_safe(text: str) -> None:
    lowered = text.lower()
    hits = sorted(marker for marker in PRIVATE_MARKERS if marker in lowered)
    if hits:
        raise ValueError(f"Public response register contains prohibited private markers: {hits}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    ensure_public_safe(json.dumps(payload, sort_keys=True))
    ensure_public_safe(markdown)
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_json(CANONICAL_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "records": payload["summary"]["record_count"],
                "immediate_human_actions": payload["summary"]["immediate_human_action_count"],
                "do_not_duplicate": payload["summary"]["do_not_duplicate_send_count"],
                "all_attachment_checks_pass": payload["summary"]["all_attachment_checks_pass"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
