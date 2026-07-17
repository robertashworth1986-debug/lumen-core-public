from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
BOARD_SCRIPT = ROOT / "code" / "ops" / "BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py"
OUT_JSON = ROOT / "out" / "ops" / "live_funding_portal_handoff_latest.json"
OUT_MD = SPRINT_DIR / f"LIVE_FUNDING_PORTAL_HANDOFF_{date.today().isoformat()}.md"

SENSITIVE_MARKERS = (
    "password",
    "meeting id",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key=",
    "sk-",
    "xox",
)
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_command_board(scan_date: date) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("near_deadline_board", BOARD_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the near-deadline command-board builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    payload = module.build_payload(scan_date=scan_date)
    if payload.get("schema") != "near_deadline_submission_command_board_v4":
        raise ValueError("Near-deadline command board is missing or stale")
    return payload


def lane_by_number(board: dict[str, Any], number: str) -> dict[str, Any]:
    for lane in board.get("lanes", []):
        if lane.get("opportunity_number") == number:
            return lane
    raise ValueError(f"Required portal lane is absent: {number}")


def queue_item(
    lane: dict[str, Any],
    *,
    priority: int,
    portal_url: str,
    next_safe_action: list[str],
    stop_conditions: list[str],
) -> dict[str, Any]:
    item = {
        "priority": priority,
        "opportunity_number": lane["opportunity_number"],
        "title": lane["title"],
        "deadline_date": lane["deadline_date"],
        "deadline_utc": lane.get("deadline_utc"),
        "official_deadline_text": lane.get("official_deadline_text"),
        "command": lane["command"],
        "portal_url": portal_url,
        "package_files": lane.get("package_files", []),
        "next_safe_action": next_safe_action,
        "stop_conditions": stop_conditions,
        "human_gate": lane.get("human_gate", []),
        "external_send_allowed_without_human": False,
        "final_submit_allowed_without_human": False,
        "source_lane_sha256": lane["lane_sha256"],
    }
    if "action_gate_status" in lane:
        item["action_gate"] = {
            "status": lane["action_gate_status"],
            "submission_ready_for_human_click": lane[
                "action_gate_submission_ready_for_human_click"
            ],
            "required_private_gate_count": lane[
                "action_gate_required_private_gate_count"
            ],
            "passed_private_gate_count": lane[
                "action_gate_passed_private_gate_count"
            ],
            "open_gate_count": lane["action_gate_open_gate_count"],
            "private_input_present": lane["action_gate_private_input_present"],
            "private_values_exposed": lane["action_gate_private_values_exposed"],
        }
        if "action_gate_private_capture_tool" in lane:
            item["action_gate"].update(
                {
                    "private_capture_tool": lane["action_gate_private_capture_tool"],
                    "private_capture_workflow": lane[
                        "action_gate_private_capture_workflow"
                    ],
                    "pre_submit_excludes_action_time_approval": lane[
                        "action_gate_pre_submit_excludes_action_time_approval"
                    ],
                    "credential_values_accepted": lane[
                        "action_gate_credential_values_accepted"
                    ],
                    "firm_pin_value_accepted": lane[
                        "action_gate_firm_pin_value_accepted"
                    ],
                }
            )
    if "deadline_support_status" in lane:
        item["deadline_support"] = {
            "status": lane["deadline_support_status"],
            "sent_utc": lane["deadline_support_sent_utc"],
            "do_not_duplicate_send": lane[
                "deadline_support_do_not_duplicate_send"
            ],
            "email_is_application": lane["deadline_support_email_is_application"],
        }
    return item


def build_payload(operational_date: date | None = None) -> dict[str, Any]:
    operational_date = operational_date or date.today()
    board = load_command_board(operational_date)

    nashville = lane_by_number(board, "NASHVILLE-EC-FALL-2026")
    missionweave = lane_by_number(board, "DLA26BZ03-NV011")
    nsf = lane_by_number(board, "26-510")
    erdc = lane_by_number(board, "W912HZ26SC005")
    launchtn = lane_by_number(board, "LAUNCHTN-3686-2026")

    queue = [
        queue_item(
            nashville,
            priority=1,
            portal_url=nashville["official_url"],
            next_safe_action=[
                "If this is the current signed-in page, inspect the visible application state before navigating anywhere.",
                "Run `python code/ops/CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py` and answer the six hidden prompts; require the ignored 11-answer fill map to validate without publishing values.",
                "Populate only the supported answers from that private map and reach the complete preview.",
                "Monitor the one deadline-support thread for the exact close time; do not resend it and do not treat it as an application.",
            ],
            stop_conditions=[
                "Any fee payment, financial-aid agreement, program terms, cohort acceptance, attestation, or final submission.",
                "Any portal answer that conflicts with the founder-confirmation artifact.",
            ],
        ),
        queue_item(
            missionweave,
            priority=2,
            portal_url=missionweave["secondary_url"],
            next_safe_action=[
                "Verify the live DSIP countdown, organization linkage, and generated proposal number.",
                "Use the proposal number through the existing builder, rerender Volume 2, regenerate the 15-file manifest, and require all hashes to pass.",
                "Run the hidden sectioned MissionWeave collector for identity, proposal, and compliance; it accepts no Firm PIN or credential and keeps action-time approval separate.",
                "Use the generated seven-volume checklist and require the public gate to move from 0/50 to 50/50 without exposing values.",
                "Populate Volumes 1-7 from the bounded package and reach the complete preview.",
            ],
            stop_conditions=[
                "Any unsupported legal-entity, SAM, UEI, CAGE, PI-employment, cost, award-history, ITAR/JCP, CMMC, foreign-affiliation, foreign-citizen, data-rights, or support-overlap representation.",
                "Fraud, Waste, and Abuse training certification, signature, attestation, or final DSIP submission.",
                "A live DSIP deadline that conflicts with the cross-source July 22, 2026 record.",
            ],
        ),
        queue_item(
            nsf,
            priority=5,
            portal_url=nsf["official_url"],
            next_safe_action=[
                "Confirm whether a Project Pitch, invitation, or proposal is already pending.",
                "If no pitch is pending, populate the four claim-bounded Project Pitch fields and reach final review.",
            ],
            stop_conditions=[
                "Any full-proposal workspace without a verified NSF invitation.",
                "Legal-company, PI-eligibility, certification, or final Project Pitch submission.",
            ],
        ),
        queue_item(
            erdc,
            priority=6,
            portal_url=erdc["secondary_url"],
            next_safe_action=[
                "Verify the live ERDCWERX questions, amendments, organization match, and current funding posture.",
                "Use the QA-passed technical PDF only after a private Phase II ROM is approved and inserted without entering the public repository.",
            ],
            stop_conditions=[
                "Any private price, rate, SAM legal fact, terms acceptance, certification, or final portal submission.",
                "Any representation that funding is currently available when the controlling source says it is not.",
            ],
        ),
        queue_item(
            launchtn,
            priority=7,
            portal_url=launchtn["official_url"],
            next_safe_action=[
                "Confirm the founder-controlled legal, Tennessee, employment, funding-history, pricing, and raise facts.",
                "Upload only the two hash-verified QA-passed attachments and reach the complete preview.",
            ],
            stop_conditions=[
                "Any unsupported eligibility, pricing, funding, legal, or employment answer.",
                "Terms acceptance, attestation, or final submission.",
            ],
        ),
    ]

    patent = board["operational_controls"]["patent_deadline_evidence"]
    sam = board["operational_controls"]["sam_public_key_rotation"]
    payload: dict[str, Any] = {
        "schema": "lumencore.live_funding_portal_handoff.v2",
        "generated_utc": now_utc(),
        "operational_date": operational_date.isoformat(),
        "status": "SESSION_BROWSER_RESERVED_FOR_USER_AUTHENTICATION",
        "source_command_board_sha256": board["command_board_sha256"],
        "browser_control": {
            "browser_scope": "CURRENT_CODEX_SESSION_IN_APP_BROWSER_ONLY",
            "resume_signal": "I'm in",
            "navigation_allowed_before_resume_signal": False,
            "inspect_current_page_before_navigation": True,
            "preserve_current_url": True,
            "browser_navigation_performed_by_builder": False,
            "credential_collection_allowed": False,
            "first_action_after_resume_signal": (
                "Inspect the current URL and visible page without navigating. Continue the "
                "current authenticated portal to its next safe preview before switching lanes."
            ),
        },
        "priority_rule": (
            "Preserve any authentication already in progress. Once authenticated, finish the "
            "current listed portal to its next safe preview; otherwise use deadline priority."
        ),
        "queue": queue,
        "account_maintenance": [
            {
                "priority": 3,
                "system": "USPTO Patent Center",
                "status": patent["status"],
                "portal_url": "https://patentcenter.uspto.gov/",
                "next_safe_action": (
                    "Download the six required official docket categories into the ignored "
                    "private capture folders, then run the redacted completeness check."
                ),
                "stop_conditions": [
                    "Do not infer the user-reported July 25 date from a payment acknowledgement.",
                    "Do not file, pay, sign, certify, or publish unpublished docket material.",
                ],
                "control_artifact": patent["control_artifact"],
                "private_capture_workflow": patent["private_capture_workflow"],
                "human_action_required": True,
            },
            {
                "priority": 4,
                "system": "SAM.gov public API credential rotation",
                "status": sam["status"],
                "portal_url": "https://sam.gov/profile/details",
                "next_safe_action": (
                    "Reveal the replacement only inside SAM.gov, paste it only into the "
                    "guarded hidden-input installer, and require changed-fingerprint plus "
                    "live authenticated verification."
                ),
                "stop_conditions": [
                    "Do not paste, log, publish, commit, mirror, or display the credential.",
                    "Do not describe entity registration as defective merely because key rotation is overdue.",
                ],
                "control_artifact": sam["control_artifact"],
                "private_installer": sam["private_installer"],
                "human_action_required": True,
            },
        ],
        "monitor_only": [
            "NASA, Army, and CDC responses are sent and receipt-backed; do not duplicate-send.",
            "FHWA has one active replacement outreach pending after the first listed route rejected delivery; do not reuse the rejected address, follow up before the recorded control date, or claim delivery or a partner.",
            "DOJ/BOP remains partner-only; do not send a solo quote.",
            "EPRI administrative onboarding was sent; monitor for a substantive response without claiming membership or endorsement.",
            "LANL follow-up was sent; monitor without duplicate transmission.",
        ],
        "global_stop_conditions": [
            "Any final submit, external send, signature, legal certification, pricing approval, fee payment, terms acceptance, or irreversible confirmation.",
            "Any unsupported claim of agency validation, award, customer deployment, realized savings, patent validity, field performance, CMMC status, or ITAR compliance.",
            "Any request to expose credentials, private identifiers, unpublished patent material, controlled technical data, or private cost rates in a public artifact.",
        ],
        "private_contact_data_included": False,
        "credentials_included": False,
        "browser_navigation_performed": False,
        "external_action_performed": False,
        "final_submit_allowed_without_human": False,
    }
    payload["handoff_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    control = payload["browser_control"]
    lines = [
        f"# Live Funding Portal Handoff - {payload['operational_date']}",
        "",
        "This handoff is generated from the authoritative near-deadline command board. It contains no private contact data or credentials.",
        "",
        "## Browser Control",
        "",
        f"- Status: `{payload['status']}`",
        f"- Scope: `{control['browser_scope']}`",
        f"- Resume signal: `{control['resume_signal']}`",
        f"- Navigation before resume signal: `{str(control['navigation_allowed_before_resume_signal']).lower()}`",
        f"- Inspect current page before navigation: `{str(control['inspect_current_page_before_navigation']).lower()}`",
        f"- First action after resume: {control['first_action_after_resume_signal']}",
        f"- Source command-board SHA-256: `{payload['source_command_board_sha256']}`",
        f"- Handoff SHA-256: `{payload['handoff_sha256']}`",
        "",
        "## Portal Queue",
        "",
    ]
    for item in sorted(payload["queue"], key=lambda row: row["priority"]):
        lines.extend(
            [
                f"### {item['priority']}. {item['opportunity_number']} - {item['title']}",
                "",
                f"- Command: `{item['command']}`",
                f"- Deadline: {item.get('official_deadline_text') or item['deadline_date']}",
                f"- Portal: {item['portal_url']}",
                "- Next safe action:",
            ]
        )
        for action in item["next_safe_action"]:
            lines.append(f"  - {action}")
        if item.get("action_gate"):
            gate = item["action_gate"]
            lines.extend(
                [
                    "- Action gate:",
                    f"  - Status: `{gate['status']}`",
                    f"  - Passed: `{gate['passed_private_gate_count']}/{gate['required_private_gate_count']}`",
                    f"  - Open: `{gate['open_gate_count']}`",
                    f"  - Private input present: `{str(gate['private_input_present']).lower()}`",
                    f"  - Private values exposed: `{str(gate['private_values_exposed']).lower()}`",
                    f"  - Ready for human click: `{str(gate['submission_ready_for_human_click']).lower()}`",
                ]
            )
        if item.get("deadline_support"):
            support = item["deadline_support"]
            lines.extend(
                [
                    "- Deadline-support email:",
                    f"  - Status: `{support['status']}`",
                    f"  - Sent UTC: `{support['sent_utc']}`",
                    f"  - Do not duplicate: `{str(support['do_not_duplicate_send']).lower()}`",
                    f"  - Email is application: `{str(support['email_is_application']).lower()}`",
                ]
            )
        lines.append("- Stop conditions:")
        for stop in item["stop_conditions"]:
            lines.append(f"  - {stop}")
        lines.append("- Human gates:")
        for gate in item["human_gate"]:
            lines.append(f"  - {gate}")
        lines.extend(
            [
                f"- External send without human: `{str(item['external_send_allowed_without_human']).lower()}`",
                f"- Final submit without human: `{str(item['final_submit_allowed_without_human']).lower()}`",
                f"- Source lane SHA-256: `{item['source_lane_sha256']}`",
                "",
            ]
        )

    lines.extend(["## Account Maintenance", ""])
    for item in sorted(payload["account_maintenance"], key=lambda row: row["priority"]):
        lines.extend(
            [
                f"### {item['priority']}. {item['system']}",
                "",
                f"- Status: `{item['status']}`",
                f"- Portal: {item['portal_url']}",
                f"- Next safe action: {item['next_safe_action']}",
                "- Stop conditions:",
            ]
        )
        for stop in item["stop_conditions"]:
            lines.append(f"  - {stop}")
        lines.append("")

    lines.extend(["## Monitor Only", ""])
    lines.extend(f"- {item}" for item in payload["monitor_only"])
    lines.extend(["", "## Global Stops", ""])
    lines.extend(f"- {item}" for item in payload["global_stop_conditions"])
    lines.extend(
        [
            "",
            f"- Private contact data included: `{str(payload['private_contact_data_included']).lower()}`",
            f"- Credentials included: `{str(payload['credentials_included']).lower()}`",
            f"- Browser navigation performed: `{str(payload['browser_navigation_performed']).lower()}`",
            f"- External action performed: `{str(payload['external_action_performed']).lower()}`",
            f"- Final submit without human: `{str(payload['final_submit_allowed_without_human']).lower()}`",
        ]
    )
    return "\n".join(lines) + "\n"


def public_safety_hits(text: str) -> list[str]:
    lowered = text.lower()
    hits = [marker for marker in SENSITIVE_MARKERS if marker in lowered]
    if EMAIL_PATTERN.search(text):
        hits.append("email_address")
    if PHONE_PATTERN.search(text):
        hits.append("phone_number")
    return sorted(set(hits))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    rendered = render_markdown(payload)
    safety_hits = public_safety_hits(rendered + json.dumps(payload, sort_keys=True))
    if safety_hits:
        raise SystemExit(f"Refusing to write public-unsafe handoff: {safety_hits}")
    write_json(OUT_JSON, payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(rendered, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "queue_items": len(payload["queue"]),
                "account_maintenance_items": len(payload["account_maintenance"]),
                "browser_navigation_performed": payload["browser_navigation_performed"],
                "markdown": OUT_MD.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
