from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT = ROOT / "grant_submissions" / "funding_sprint_20260709"

EVENT_REGISTER = SPRINT / "OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json"
TEMPLATE_REGISTRY = SPRINT / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
EMAIL_RECONCILIATION = SPRINT / "EMAIL_ACTION_RECONCILIATION_2026-07-18.json"
PUBLIC_IDENTITY = ROOT / "docs" / "PUBLIC_VISIBILITY_AND_SOURCE_AUTHORITY_2026-06-20.md"
SEND_STATUS = SPRINT / "EPRI_OPAI_LOGO_RESPONSE_SEND_STATUS_2026-07-29.json"

JSON_OUT = SPRINT / "EPRI_OPAI_LOGO_RESPONSE_PACKET_2026-07-25.json"
MD_OUT = SPRINT / "EPRI_OPAI_LOGO_RESPONSE_PACKET_2026-07-25.md"

LANE_ID = "epri_open_power_ai_mou"
EXPECTED_TEMPLATE_ID = "REQUESTED_ASSET_DELIVERY_REPLY"
EXPECTED_DIMENSIONS = (1024, 1024)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PERMITTED_USE_MARKER = (
    "[[CONFIRM EXACT PERMITTED-USE BOUNDARY FROM FRESH FULL-THREAD CHECK]]"
)

ASSET_SPECS = (
    {
        "role": "dark_background_logo",
        "path": "dashboard/brand/lumencore_logo_on_dark_1024.png",
        "filename": "lumencore_logo_on_dark_1024.png",
        "intended_background": "dark",
    },
    {
        "role": "light_background_logo",
        "path": "dashboard/brand/lumencore_logo_on_light_1024.png",
        "filename": "lumencore_logo_on_light_1024.png",
        "intended_background": "light",
    },
)

CLAIM_BOUNDARY = (
    "This packet verifies local response evidence and two LumenCore PNG assets. "
    "It does not prove that the logo files were sent, received, accepted, "
    "published, or endorsed by EPRI or the Open Power AI Consortium, and it "
    "does not grant use beyond the boundary confirmed in the current thread."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_utc(value: str) -> str:
    candidate = value.strip()
    parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("generated UTC must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def source_receipt(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "file_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def find_lane(rows: Any, lane_id: str, label: str) -> dict[str, Any]:
    if not isinstance(rows, list):
        raise ValueError(f"{label} must be a list")
    matches = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("lane_id") == lane_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one {label} row for {lane_id}; found {len(matches)}"
        )
    return matches[0]


def read_public_identity(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    expected = {
        "sender_name": "Robert Ashworth",
        "organization_name": "LumenCore",
        "source_role": "Founder / independent builder",
        "sender_title": "Founder",
    }
    required_lines = {
        f"- Name: {expected['sender_name']}",
        f"- Project: {expected['organization_name']}",
        f"- Role: {expected['source_role']}",
    }
    missing = sorted(line for line in required_lines if line not in text)
    if missing:
        raise ValueError(
            "Public identity authority is missing expected values: "
            + ", ".join(missing)
        )
    return expected


def inspect_png(root: Path, spec: dict[str, str]) -> dict[str, Any]:
    path = root / Path(spec["path"])
    row: dict[str, Any] = {
        **spec,
        "exists": path.is_file(),
        "file_bytes": 0,
        "sha256": "",
        "png_signature_hex": "",
        "png_signature_valid": False,
        "ihdr_present": False,
        "width": 0,
        "height": 0,
        "expected_width": EXPECTED_DIMENSIONS[0],
        "expected_height": EXPECTED_DIMENSIONS[1],
        "exact_dimensions_valid": False,
        "ready": False,
        "blockers": [],
    }
    if not row["exists"]:
        row["blockers"].append("MISSING_ASSET")
        return row

    row["file_bytes"] = path.stat().st_size
    row["sha256"] = sha256_file(path)
    with path.open("rb") as handle:
        header = handle.read(24)

    row["png_signature_hex"] = header[:8].hex()
    row["png_signature_valid"] = (
        len(header) >= 8 and header[:8] == PNG_SIGNATURE
    )
    if not row["png_signature_valid"]:
        row["blockers"].append("INVALID_PNG_SIGNATURE")
        return row

    row["ihdr_present"] = len(header) == 24 and header[12:16] == b"IHDR"
    if not row["ihdr_present"]:
        row["blockers"].append("PNG_IHDR_NOT_FOUND")
        return row

    row["width"], row["height"] = struct.unpack(">II", header[16:24])
    row["exact_dimensions_valid"] = (
        row["width"],
        row["height"],
    ) == EXPECTED_DIMENSIONS
    if not row["exact_dimensions_valid"]:
        row["blockers"].append("UNEXPECTED_DIMENSIONS")
    if row["file_bytes"] <= 0:
        row["blockers"].append("ZERO_BYTE_ASSET")

    row["ready"] = not row["blockers"]
    return row


def validate_send_status(
    receipt: dict[str, Any],
    assets: list[dict[str, Any]],
) -> dict[str, bool]:
    dispatch = receipt.get("dispatch", {})
    mailbox = receipt.get("mailbox_observation", {})
    controls = receipt.get("controls", {})
    receipt_assets = dispatch.get("attachments", [])
    expected_assets = {
        asset["filename"]: {
            "file_bytes": asset["file_bytes"],
            "sha256": asset["sha256"].lower(),
        }
        for asset in assets
    }
    recorded_assets = {
        row.get("filename"): {
            "file_bytes": row.get("file_bytes"),
            "sha256": str(row.get("sha256", "")).lower(),
        }
        for row in receipt_assets
        if isinstance(row, dict)
    }
    return {
        "schema_matches": (
            receipt.get("schema")
            == "lumencore.epri_opai_logo_response_send_status.v1"
        ),
        "lane_matches": receipt.get("lane_id") == LANE_ID,
        "status_is_sent_once": (
            receipt.get("status") == "SENT_ONCE_POST_SEND_VERIFIED_NO_DUPLICATE"
        ),
        "post_send_copy_verified": (
            mailbox.get("post_send_sent_copy_verified") is True
        ),
        "one_matching_sent_copy": (
            mailbox.get("matching_logo_attachment_sent_count_after_send") == 1
        ),
        "attachment_count_matches": dispatch.get("attachment_count") == 2,
        "attachment_hashes_match": recorded_assets == expected_assets,
        "bcc_absent": dispatch.get("bcc_count") == 0,
        "single_send_only": controls.get("single_send_only") is True,
        "duplicate_send_prohibited": (
            controls.get("duplicate_send_prohibited") is True
        ),
        "gmail_identifiers_omitted": (
            mailbox.get("gmail_identifiers_omitted") is True
        ),
        "recipient_addresses_omitted": (
            mailbox.get("recipient_addresses_omitted") is True
        ),
    }


def normalize_reply_subject(source_subject: str) -> str:
    base = re.sub(r"^(?:\s*re:\s*)+", "", source_subject, flags=re.IGNORECASE)
    return f"Re: {base.strip()}"


def render_template(template: dict[str, Any], fields: dict[str, str]) -> dict[str, str]:
    required_fields = template.get("required_fields")
    if not isinstance(required_fields, list):
        raise ValueError("Template required_fields must be a list")
    missing = [
        field
        for field in required_fields
        if field not in fields and field not in {"recipient_email", "source_message_id"}
    ]
    if missing:
        raise ValueError(f"Missing template fields: {', '.join(sorted(missing))}")

    subject_template = str(template.get("subject", ""))
    body_template = str(template.get("body", ""))
    source_subject = fields["source_subject"]
    subject_fields = dict(fields)
    subject_fields["source_subject"] = re.sub(
        r"^(?:\s*re:\s*)+",
        "",
        source_subject,
        flags=re.IGNORECASE,
    ).strip()
    return {
        "subject": subject_template.format(**subject_fields),
        "body": body_template.format(**fields),
    }


def build_packet(
    *,
    root: Path = ROOT,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    sprint = root / "grant_submissions" / "funding_sprint_20260709"
    event_path = sprint / EVENT_REGISTER.name
    registry_path = sprint / TEMPLATE_REGISTRY.name
    reconciliation_path = sprint / EMAIL_RECONCILIATION.name
    identity_path = root / "docs" / PUBLIC_IDENTITY.name
    send_status_path = sprint / SEND_STATUS.name

    event_register = read_json_object(event_path)
    registry = read_json_object(registry_path)
    reconciliation = read_json_object(reconciliation_path)
    public_identity = read_public_identity(identity_path)

    event = find_lane(event_register.get("events"), LANE_ID, "event")
    lane = find_lane(reconciliation.get("lanes"), LANE_ID, "reconciliation")

    requested_template_id = (
        event.get("action", {}).get("selected_template_id")
        if isinstance(event.get("action"), dict)
        else None
    )
    templates = registry.get("templates")
    if not isinstance(templates, list):
        raise ValueError("Template registry templates must be a list")
    template_matches = [
        template
        for template in templates
        if isinstance(template, dict)
        and template.get("template_id") == requested_template_id
    ]
    template = template_matches[0] if len(template_matches) == 1 else None

    evidence = event.get("evidence", {})
    source = event.get("source", {})
    action = event.get("action", {})
    evidence_checks = {
        "lane_matches": event.get("lane_id") == LANE_ID,
        "light_and_dark_png_logos_explicitly_requested": (
            evidence.get("light_and_dark_png_logos_requested") is True
        ),
        "primary_contact_response_already_sent": (
            evidence.get("primary_contact_sent") is True
        ),
        "work_group_response_already_sent": (
            evidence.get("work_group_representatives_sent") is True
        ),
        "logo_permission_response_already_sent": (
            evidence.get("logo_permission_sent") is True
        ),
        "logo_files_recorded_unsent": evidence.get("logo_files_sent") is False,
        "prior_full_thread_read_recorded": source.get("full_thread_read") is True,
        "prior_thread_not_truncated": source.get("thread_truncated") is False,
        "reconciliation_state_matches": (
            lane.get("state")
            in {
                "ONBOARDING_RESPONSE_SENT_MRC_INVITE_RECEIVED_LOGO_FILES_PENDING",
                "MOU_COMPLETED_BY_ALL_PARTIES_PRIVATE_CUSTODY_REQUIRED",
            }
        ),
        "reconciliation_logo_files_recorded_unsent": (
            lane.get("canonical_logo_files_sent") is False
        ),
        "template_selection_matches": requested_template_id
        == EXPECTED_TEMPLATE_ID,
    }
    evidence_ready = all(evidence_checks.values())

    assets = [inspect_png(root, spec) for spec in ASSET_SPECS]
    assets_ready = len(assets) == 2 and all(asset["ready"] for asset in assets)
    send_status = (
        read_json_object(send_status_path) if send_status_path.is_file() else None
    )
    send_status_checks = (
        validate_send_status(send_status, assets)
        if send_status is not None
        else {}
    )
    send_status_valid = bool(send_status) and all(send_status_checks.values())

    template_match = {
        "requested_template_id": requested_template_id,
        "expected_template_id": EXPECTED_TEMPLATE_ID,
        "matching_template_exists": template is not None,
        "match_status": "MATCHED" if template is not None else "TEMPLATE_GAP",
        "template_gap": (
            None
            if template is not None
            else (
                "The response-template registry does not contain exactly one "
                f"{requested_template_id!r} template."
            )
        ),
        "attachment_policy": (
            template.get("attachment_policy") if template is not None else None
        ),
        "send_policy": template.get("send_policy") if template is not None else None,
        "private_render_only": (
            template.get("private_render_only") if template is not None else None
        ),
        "routing_values_embedded": False,
    }
    template_ready = (
        template is not None
        and template.get("template_id") == EXPECTED_TEMPLATE_ID
        and template.get("attachment_policy") == "EXPLICIT_REQUEST_ONLY"
        and template.get("send_policy") == "REPLY_AFTER_FACT_REVIEW"
        and template.get("private_render_only") is True
    )

    attachment_inventory = "; ".join(
        f"{asset['filename']} ({asset['intended_background']}-background PNG, "
        f"{asset['width']}x{asset['height']})"
        for asset in assets
    )
    fields = {
        "recipient_name": "Open Power AI team",
        "source_subject": str(source.get("subject", "")).strip(),
        "requested_asset_summary": (
            "the canonical LumenCore PNG logo pair for dark and light backgrounds"
        ),
        "attachment_inventory": attachment_inventory,
        "permitted_use_boundary": PERMITTED_USE_MARKER,
        "sender_name": public_identity["sender_name"],
        "sender_title": public_identity["sender_title"],
        "organization_name": public_identity["organization_name"],
    }
    rendered = (
        render_template(template, fields)
        if template is not None
        else {
            "subject": normalize_reply_subject(fields["source_subject"]),
            "body": "",
        }
    )

    missing_facts = [
        {
            "fact_id": "exact_permitted_use_boundary",
            "status": "MISSING_FROM_LOCAL_PUBLIC_SAFE_EVIDENCE",
            "resolution": (
                "Read the current full thread at action time and bind the exact "
                "permitted-use wording already authorized by the sender."
            ),
        },
        {
            "fact_id": "fresh_duplicate_state",
            "status": "ACTION_TIME_RECHECK_REQUIRED",
            "resolution": (
                "Confirm in the complete current thread that neither canonical "
                "logo file was sent after the recorded local event."
            ),
        },
    ]

    build_ok = (
        evidence_ready
        and assets_ready
        and template_ready
        and (send_status is None or send_status_valid)
    )
    if not build_ok:
        status = "PACKET_BLOCKED_LOCAL_EVIDENCE_ASSET_TEMPLATE_OR_RECEIPT_FAILURE"
    elif send_status_valid:
        status = "LOGO_PAIR_SENT_ONCE_POST_SEND_VERIFIED_DO_NOT_RESEND"
    else:
        status = "PACKET_READY_FOR_PRIVATE_ACTION_TIME_REVIEW_SEND_BLOCKED"
    generated = normalize_utc(generated_utc) if generated_utc else now_utc()

    source_evidence = {
        "official_inbound_status_event_register": source_receipt(
            event_path, root
        ),
        "outreach_response_template_registry": source_receipt(
            registry_path, root
        ),
        "email_action_reconciliation": source_receipt(
            reconciliation_path, root
        ),
        "public_identity_authority": source_receipt(identity_path, root),
    }
    if send_status is not None:
        source_evidence["send_status"] = source_receipt(send_status_path, root)

    packet: dict[str, Any] = {
        "schema": "lumencore.epri_opai_logo_response_packet.v1",
        "generated_utc": generated,
        "lane_id": LANE_ID,
        "organization": "EPRI Open Power AI Consortium",
        "status": status,
        "summary": {
            "builder_checks_pass": build_ok,
            "asset_count": len(assets),
            "ready_asset_count": sum(bool(asset["ready"]) for asset in assets),
            "prior_contact_work_group_and_permission_response_sent": True,
            "only_recorded_remaining_deliverable": (
                "None. The requested canonical logo pair was sent once."
                if send_status_valid
                else (
                    "The promised/requested canonical dark-background and "
                    "light-background PNG logo pair."
                )
            ),
            "send_authorized": False,
            "logo_pair_sent_verified": send_status_valid,
        },
        "source_evidence": source_evidence,
        "evidence_checks": evidence_checks,
        "send_status_checks": send_status_checks,
        "prior_response_state": {
            "onboarding_response_sent_utc": evidence.get(
                "onboarding_response_sent_utc"
            ),
            "primary_contact_sent": evidence.get("primary_contact_sent") is True,
            "work_group_representatives_sent": (
                evidence.get("work_group_representatives_sent") is True
            ),
            "logo_permission_sent": evidence.get("logo_permission_sent") is True,
            "logo_files_sent_in_recorded_state": send_status_valid,
            "repeat_prior_answers_in_reply": False,
        },
        "template_match": template_match,
        "assets": assets,
        "attachment_control": {
            "explicit_request_recorded": (
                evidence.get("light_and_dark_png_logos_requested") is True
            ),
            "attachment_count": 2 if assets_ready else 0,
            "attachment_allowlist": [
                asset["path"] for asset in assets if asset["ready"]
            ],
            "additional_attachments_allowed": False,
            "only_allowed_attachments": (
                "The two verified canonical LumenCore PNG logo files."
            ),
        },
        "bounded_reply": {
            "template_id": requested_template_id,
            "render_status": (
                "HISTORICAL_PRE_SEND_COPY_SUPERSEDED_BY_SEND_RECEIPT"
                if send_status_valid
                else (
                    "PREVIEW_BOUND_MISSING_PERMITTED_USE_CONFIRMATION"
                    if template is not None
                    else "BLOCKED_TEMPLATE_GAP"
                )
            ),
            "subject": rendered["subject"],
            "body": rendered["body"],
            "recipient_addresses_embedded": False,
            "routing_values_embedded": False,
            "send_or_draft_performed": send_status_valid,
        },
        "duplicate_send_decision": {
            "decision": (
                "BLOCK_SEND_ALREADY_SENT_ONCE"
                if send_status_valid
                else (
                    "BLOCK_SEND_UNTIL_FRESH_FULL_THREAD_CONFIRMS_LOGO_PAIR_UNSENT"
                )
            ),
            "recorded_logo_files_sent": send_status_valid,
            "do_not_repeat": [
                "primary contact facts",
                "work-group representative facts",
                "logo permission answer",
            ],
            "fresh_full_thread_check_required": not send_status_valid,
        },
        "missing_facts": [] if send_status_valid else missing_facts,
        "action_gates": {
            "fresh_full_thread_check_required": not send_status_valid,
            "exact_action_time_approval_required": not send_status_valid,
            "external_send_allowed_without_action_time_approval": False,
            "email_access_performed": send_status_valid,
            "email_draft_created": False,
            "email_sent": send_status_valid,
            "invitation_accepted": False,
            "meeting_credentials_used": False,
            "external_action_performed": send_status_valid,
        },
        "safest_next_action": (
            send_status.get("next_action")
            if send_status_valid
            else (
                "At action time, read the complete current EPRI onboarding "
                "thread, confirm the two canonical logos remain unsent, bind "
                "the exact permitted-use boundary, and obtain exact approval "
                "before attaching only the two allowlisted PNG files to the "
                "existing thread."
            )
        ),
        "claim_boundary": (
            send_status.get("claim_boundary")
            if send_status_valid
            else CLAIM_BOUNDARY
        ),
        "packet_hash_scope": (
            "SHA-256 of canonical JSON with packet_sha256 omitted."
        ),
    }
    packet["packet_sha256"] = canonical_sha256(packet)
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# EPRI Open Power AI Logo Response Packet",
        "",
        f"Generated UTC: `{packet['generated_utc']}`",
        "",
        f"Status: `{packet['status']}`",
        "",
        "## Response State",
        "",
        (
            "- Contact, work-group representative, and logo-permission response "
            "already sent: `true`"
        ),
        (
            "- Only recorded remaining deliverable: the promised/requested "
            f"`{packet['summary']['only_recorded_remaining_deliverable']}`"
        ),
        (
            "- Logo pair sent and verified: "
            f"`{str(packet['summary']['logo_pair_sent_verified']).lower()}`"
        ),
        (
            "- Send authorized: "
            f"`{str(packet['summary']['send_authorized']).lower()}`"
        ),
        "",
        "## Verified Assets",
        "",
        (
            "| Role | Path | PNG Signature | Exact Dimensions | Bytes | "
            "SHA-256 | Ready |"
        ),
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for asset in packet["assets"]:
        lines.append(
            f"| `{asset['role']}` | `{asset['path']}` | "
            f"`{asset['png_signature_hex']}` / "
            f"`{str(asset['png_signature_valid']).lower()}` | "
            f"`{asset['width']}x{asset['height']}` / "
            f"`{str(asset['exact_dimensions_valid']).lower()}` | "
            f"`{asset['file_bytes']}` | `{asset['sha256']}` | "
            f"`{str(asset['ready']).lower()}` |"
        )

    match = packet["template_match"]
    lines.extend(
        [
            "",
            "## Template Binding",
            "",
            f"- Requested template: `{match['requested_template_id']}`",
            f"- Match status: `{match['match_status']}`",
            f"- Attachment policy: `{match['attachment_policy']}`",
            f"- Send policy: `{match['send_policy']}`",
            f"- Template gap: `{match['template_gap']}`",
            "",
            "### Subject",
            "",
            packet["bounded_reply"]["subject"],
            "",
            "### Body",
            "",
            packet["bounded_reply"]["body"],
            "",
            "No recipient address or private routing value is embedded.",
            "",
            "## Duplicate And Action Gates",
            "",
            (
                "- Duplicate-send decision: "
                f"`{packet['duplicate_send_decision']['decision']}`"
            ),
            (
                "- Fresh full-thread check required: "
                f"`{str(packet['action_gates']['fresh_full_thread_check_required']).lower()}`"
            ),
            (
                "- Exact action-time approval required: "
                f"`{str(packet['action_gates']['exact_action_time_approval_required']).lower()}`"
            ),
            "- Additional attachments allowed: `false`",
            (
                "- Email sent: "
                f"`{str(packet['action_gates']['email_sent']).lower()}`"
            ),
            "- Invitation accepted or meeting credentials used: `false`",
            "",
            "## Missing Facts",
            "",
        ]
    )
    if packet["missing_facts"]:
        for fact in packet["missing_facts"]:
            lines.append(
                f"- `{fact['fact_id']}`: `{fact['status']}`. {fact['resolution']}"
            )
    else:
        lines.append("- None. The verified send receipt supersedes pre-send gates.")

    lines.extend(
        [
            "",
            "## Safest Next Action",
            "",
            packet["safest_next_action"],
            "",
            "## Claim Boundary",
            "",
            packet["claim_boundary"],
            "",
            f"Packet SHA-256: `{packet['packet_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_packet(
    packet: dict[str, Any],
    *,
    json_out: Path = JSON_OUT,
    md_out: Path = MD_OUT,
) -> None:
    json_out.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(render_markdown(packet), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the local-only EPRI Open Power AI logo response packet."
    )
    parser.add_argument(
        "--generated-utc",
        help="Optional timezone-aware generation time for reproducible builds.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = build_packet(generated_utc=args.generated_utc)
    write_packet(packet)
    print(
        json.dumps(
            {
                "status": packet["status"],
                "ready_asset_count": packet["summary"]["ready_asset_count"],
                "template_match": packet["template_match"]["match_status"],
                "send_authorized": packet["summary"]["send_authorized"],
                "packet_sha256": packet["packet_sha256"],
                "json": JSON_OUT.relative_to(ROOT).as_posix(),
                "markdown": MD_OUT.relative_to(ROOT).as_posix(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if packet["summary"]["builder_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
