from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

CONCIERGE_JSON = OUT_OPS / "reviewer_concierge_packet_latest.json"
TRACTION_JSON = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
EMAIL_RECONCILIATION_JSON = (
    SPRINT_DIR / "EMAIL_ACTION_RECONCILIATION_2026-07-18.json"
)
FOLLOWUP_QUEUE_JSON = (
    SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
)
OFFICIAL_EVENTS_JSON = (
    SPRINT_DIR / "OFFICIAL_INBOUND_STATUS_EVENT_REGISTER_2026-07-25.json"
)
EXTERNAL_ENGAGEMENT_JSON = (
    OUT_OPS / "external_engagement_response_register_latest.json"
)
OUT_JSON = OUT_OPS / "human_action_docket_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "human_action_docket.json"
OUT_MD = SPRINT_DIR / "HUMAN_ACTION_DOCKET_2026-07-09.md"

OPERATIONAL_TIMEZONE = "America/Chicago"
NO_FINAL_ACTION = "Human approval is required before any send, upload, filing, certification, pricing, term acceptance, calendar edit, trading, or capital movement."

SENSITIVE_MARKERS = [
    "zoom.us",
    "meeting id",
    "password",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]

ACTION_OVERRIDES: dict[str, dict[str, Any]] = {
    "sam_registration_external_validation_watch": {
        "docket_action": "Check SAM status and watch for any DLA email; prepare Entity Administrator letter packet if required.",
        "action_due": "2026-07-13",
        "time_basis": "SAM confirmation says IRS validation can take two business days and DLA CAGE validation averages two business days after routing.",
        "action_type": "federal_registration_watch",
    },
    "lanl_vision_licensing_followup": {
        "docket_action": "Prepare concise licensing-fit note and technical questions for the named LANL POC return window.",
        "action_due": "2026-07-13",
        "time_basis": "LANL response says the main POC is out until next week.",
        "action_type": "lab_poc_followup",
    },
    "uspto_georgia_patents_route": {
        "docket_action": "Prepare Georgia PATENTS intake packet and counsel questions.",
        "action_due": "2026-07-10",
        "time_basis": "USPTO Pro Bono routed Tennessee inventors to Georgia PATENTS; patent timing must be verified by counsel.",
        "action_type": "licensed_counsel_review",
    },
    "protecnium_its_infrastructure_signal": {
        "docket_action": "Use as customer-discovery context for infrastructure/ITS buyers; reply only if Robert wants partner or market discovery.",
        "action_due": None,
        "time_basis": "LinkedIn InMail is a market signal, not a funding deadline.",
        "action_type": "customer_discovery_watch",
    },
    "evtit_blackdog_inkind": {
        "docket_action": "Prepare call packet and proof walkthrough.",
        "action_due": "2026-07-09",
        "time_basis": "Gmail invite received; exact event time is intentionally excluded from the public docket.",
        "action_type": "meeting_prep",
    },
    "lvlup_first_check": {
        "docket_action": "Hold investor brief and walkthrough ready; follow up only if reviewer asks or the under-one-week window passes.",
        "action_due": "2026-07-16",
        "time_basis": "Submitted July 9, 2026; one-week review watch window.",
        "action_type": "investor_watch",
    },
    "darpa_dice_full_submission": {
        "docket_action": "Build full-proposal compliance matrix and confirm controlling BAA instructions.",
        "action_due": "2026-07-12",
        "time_basis": "Internal sprint target so full proposal work does not wait for a last-minute gate.",
        "action_type": "federal_baa_build",
    },
    "nsf_project_pitch": {
        "docket_action": "Check the one-pending-pitch rule before any Project Pitch submit.",
        "action_due": None,
        "time_basis": "Rolling invitation gate; no artificial deadline assigned.",
        "action_type": "rolling_human_check",
    },
    "openai_api_continuity": {
        "docket_action": "Submit or refresh official API-continuity request if API availability is still a blocker.",
        "action_due": "2026-07-10",
        "time_basis": "Operational continuity support action; no public program deadline found.",
        "action_type": "vendor_route",
    },
    "openai_build_week_prooflock": {
        "docket_action": "Confirm model/session provenance, deploy the public demo, record the public video, and populate the Devpost draft without final submission.",
        "action_due": "2026-07-21",
        "time_basis": "Official final submission deadline is July 21, 2026 at 5:00 p.m. Pacific / 7:00 p.m. Central.",
        "action_type": "developer_challenge_build",
    },
    "patent_deadline_counsel": {
        "docket_action": "Monitor counsel replies and prepare filed-materials packet for licensed review.",
        "action_due": "2026-07-25",
        "time_basis": "Dossier email states a July 25, 2025 filing date; counsel must verify any actual legal deadline.",
        "action_type": "licensed_counsel_review",
    },
}

STATUS_ACTION_TYPES: dict[str, str] = {
    "DO_NOT_PRIME_SOLO": "park_partner_only",
    "PARTNER_ONLY": "partner_only",
    "PARTNER_INTRO_ONLY": "partner_intro_only",
    "ROUTE_ONLY_LOW_FIT": "agency_routing_watch",
    "SCOUT_TOPIC_MATCH": "topic_fit_check",
    "PHASE_I_TECH_VOLUME": "federal_contract_build",
    "RFI_RESPONSE_PREP": "federal_rfi_build",
    "DSIP_PACKAGE_PREP": "federal_sbir_build",
    "FULL_PROPOSAL_SPRINT": "federal_baa_build",
    "PITCH_READY_HUMAN_CHECK": "rolling_human_check",
    "HUMAN_FORM_READY": "vendor_route",
    "PRO_BONO_ROUTE_IDENTIFIED_HUMAN_ACTION_REQUIRED": "licensed_counsel_review",
    "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN": "developer_challenge_build",
    "URGENT_COUNSEL_WATCH": "licensed_counsel_review",
    "SUBMITTED_EXTERNAL_VALIDATION_PENDING": "federal_registration_watch",
    "WAITING_POC_RETURN": "lab_poc_followup",
    "CUSTOMER_DISCOVERY_SIGNAL_ONLY": "customer_discovery_watch",
    "WAITING_REVIEW": "investor_watch",
    "LIVE_MEETING_PREP": "meeting_prep",
}

DOCKET_ACTIONS_BY_TYPE: dict[str, str] = {
    "federal_contract_build": "Convert the current outline into a human-review package with compliance checklist, pricing stop, and source attachment check.",
    "federal_rfi_build": "Prepare a bounded response draft and verify official response instructions before send.",
    "federal_sbir_build": "Prepare technical volume, cost notes, and Firm PIN handoff checklist.",
    "federal_baa_build": "Build compliance matrix, technical narrative, and submission authority checklist.",
    "rolling_human_check": "Verify platform rules before any submit action.",
    "vendor_route": "Prepare official-form language and human billing/terms review.",
    "licensed_counsel_review": "Prepare counsel packet and do not expand public IP claims without licensed review.",
    "federal_registration_watch": "Monitor entity registration validations and respond to official requests only through human-approved channels.",
    "lab_poc_followup": "Prepare a concise tech-transfer follow-up packet for the named lab POC.",
    "customer_discovery_watch": "Use as market-context evidence; do not claim a customer or pilot.",
    "investor_watch": "Keep brief ready and avoid repeated follow-up until the stated review window passes or the reviewer asks.",
    "meeting_prep": "Prepare walkthrough, build-scope menu, proof links, and terms questions.",
    "agency_routing_watch": "Wait for routing response; do not prepare a prime bid.",
    "partner_only": "Find qualified partner before any response draft.",
    "partner_intro_only": "Use as strategic-intro material, not a solo proposal.",
    "park_partner_only": "Park as non-solo lane unless a qualified platform or prime partner leads.",
    "topic_fit_check": "Review official attachments and score topic fit before drafting.",
    "developer_challenge_build": "Complete public demo, video, model/session provenance, registration, and draft fields before human final review.",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def operational_today() -> date:
    return datetime.now(ZoneInfo(OPERATIONAL_TIMEZONE)).date()


def normalize_as_of_date(value: date | str | None) -> date:
    if value is None:
        return operational_today()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_first_iso_date(value: str) -> str | None:
    match = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", value or "")
    return match.group(0) if match else None


def days_until(value: str | None, *, current_date: date) -> int | None:
    if not value:
        return None
    return (date.fromisoformat(value) - current_date).days


def urgency_for(
    action_due: str | None,
    action_type: str,
    status: str,
    *,
    current_date: date,
) -> str:
    if status in {"DO_NOT_PRIME_SOLO", "PARTNER_ONLY", "PARTNER_INTRO_ONLY"}:
        return "PARKED_UNLESS_PARTNER"
    delta = days_until(action_due, current_date=current_date)
    if delta is None:
        return "ROLLING_OR_EVENT_GATED"
    if delta < 0:
        return "PAST_DATE_RECHECK"
    if delta <= 1:
        return "IMMEDIATE_24H"
    if delta <= 5:
        return "URGENT_5D"
    if delta <= 14:
        return "ACTIVE_14D"
    return "WATCHLIST"


def first_artifact(card: dict[str, Any]) -> str:
    for artifact in card.get("artifacts", []):
        if artifact.get("present"):
            return str(artifact.get("path", ""))
    return ""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def finalize_item(
    item: dict[str, Any],
    *,
    current_date: date,
    urgency_override: str | None = None,
) -> dict[str, Any]:
    action_due = item.get("action_due")
    item["days_until_action_due"] = days_until(
        action_due, current_date=current_date
    )
    item["urgency"] = urgency_override or urgency_for(
        action_due,
        str(item.get("action_type", "")),
        str(item.get("status", "")),
        current_date=current_date,
    )
    item["no_final_action_rule"] = NO_FINAL_ACTION
    item["docket_item_sha256"] = hashlib.sha256(
        json.dumps(item, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return item


def validate_current_action_sources(
    official_events: dict[str, Any],
    email_reconciliation: dict[str, Any],
    followup_queue: dict[str, Any],
    external_engagement: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    events = official_events.get("events", [])
    events_by_lane = {row.get("lane_id"): row for row in events}
    required_events = {
        "nashville_ec_takeoff_fall_2026",
        "nashville_ec_accelerator_info_sessions",
        "dla_amps_application_access",
        "login_gov_new_device_signin",
        "dla_dsip_topic_status",
        "epri_open_power_ai_mou_completed",
    }
    controls = official_events.get("controls", {})
    if (
        official_events.get("schema")
        != "lumencore.official_inbound_status_event_register.v1"
        or official_events.get("status")
        != "TWELVE_OFFICIAL_EVENTS_RECONCILED_NO_SEND"
        or official_events.get("event_count") != len(events)
        or len(events_by_lane) != len(events)
        or required_events - set(events_by_lane)
        or controls.get("builder_can_send_email") is not False
        or controls.get("message_bodies_omitted") is not True
        or controls.get("meeting_credentials_omitted") is not True
        or controls.get("private_mail_identifiers_omitted") is not True
    ):
        raise ValueError("Current official inbound action evidence is missing or unsafe")
    if any(
        row.get("action", {}).get("send_now") is not False
        or row.get("action", {}).get("email_reply_required") is not False
        for row in events
    ):
        raise ValueError("Official inbound register contains an outbound email action")

    source_receipt = email_reconciliation.get("source_evidence", {}).get(
        "official_inbound_status_event_register", {}
    )
    reconciliation_status = email_reconciliation.get("status")
    reconciliation_summary = email_reconciliation.get("summary", {})
    deadline_action_count = int(
        reconciliation_summary.get("deadline_action_required_count", 0)
    )
    if (
        email_reconciliation.get("schema")
        != "lumencore.email_action_reconciliation.v1"
        or reconciliation_status
        not in {
            "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION",
            "DEADLINE_ACTION_DUE_HUMAN_REVIEW",
        }
        or reconciliation_summary.get("send_now_count") != 0
        or (
            reconciliation_status == "DEADLINE_ACTION_DUE_HUMAN_REVIEW"
            and deadline_action_count < 1
        )
        or (
            reconciliation_status
            == "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION"
            and deadline_action_count != 0
        )
        or source_receipt.get("sha256") != sha256_file(OFFICIAL_EVENTS_JSON)
    ):
        raise ValueError("Email reconciliation does not bind the current inbound events")
    if (
        followup_queue.get("schema")
        != "lumencore.outreach_followup_action_queue.v1"
        or followup_queue.get("summary", {}).get("send_now_count") != 0
        or followup_queue.get("controls", {}).get("builder_can_send_email")
        is not False
        or followup_queue.get("controls", {}).get("final_send_performed")
        is not False
        or (
            reconciliation_status == "DEADLINE_ACTION_DUE_HUMAN_REVIEW"
            and (
                followup_queue.get("status")
                != "DEADLINE_ACTION_DUE_HUMAN_REVIEW"
                or int(
                    followup_queue.get("summary", {}).get(
                        "deadline_action_due_count", 0
                    )
                )
                < 1
            )
        )
    ):
        raise ValueError("Follow-up queue is missing or permits an unsafe send")
    if (
        external_engagement.get("schema")
        != "lumencore.external_engagement_response_register.v1"
        or external_engagement.get("status")
        != "CURRENT_RESPONSE_CONTROL_HUMAN_GATED"
        or external_engagement.get("summary", {}).get(
            "autonomous_external_send_allowed"
        )
        is not False
        or external_engagement.get("summary", {}).get(
            "autonomous_final_portal_submission_allowed"
        )
        is not False
    ):
        raise ValueError("External engagement register is missing or unsafe")
    return events_by_lane


def build_payload(as_of_date: date | str | None = None) -> dict[str, Any]:
    current_date = normalize_as_of_date(as_of_date)
    concierge = read_json(CONCIERGE_JSON)
    traction = read_json(TRACTION_JSON)
    gate = read_json(REVIEWER_GATE_JSON)
    email_reconciliation = read_json(EMAIL_RECONCILIATION_JSON)
    followup_queue = read_json(FOLLOWUP_QUEUE_JSON)
    official_events = read_json(OFFICIAL_EVENTS_JSON)
    external_engagement = read_json(EXTERNAL_ENGAGEMENT_JSON)
    events_by_lane = validate_current_action_sources(
        official_events,
        email_reconciliation,
        followup_queue,
        external_engagement,
    )
    cards = concierge.get("concierge_cards", [])
    cards = cards if isinstance(cards, list) else []

    docket_items = []
    for card in sorted(cards, key=lambda row: int(row.get("priority", 999))):
        lane_id = str(card.get("lane_id", ""))
        status = str(card.get("status", ""))
        action_type = ACTION_OVERRIDES.get(lane_id, {}).get(
            "action_type",
            STATUS_ACTION_TYPES.get(status, "human_review"),
        )
        action_due = ACTION_OVERRIDES.get(lane_id, {}).get(
            "action_due",
            parse_first_iso_date(str(card.get("deadline_or_gate", ""))),
        )
        docket_action = ACTION_OVERRIDES.get(lane_id, {}).get(
            "docket_action",
            DOCKET_ACTIONS_BY_TYPE.get(action_type, str(card.get("reviewer_action", ""))),
        )
        time_basis = ACTION_OVERRIDES.get(lane_id, {}).get(
            "time_basis",
            str(card.get("deadline_or_gate", "")),
        )
        item = {
            "lane_id": lane_id,
            "name": card.get("name", ""),
            "priority": int(card.get("priority", 999)),
            "channel": card.get("channel", ""),
            "status": status,
            "fit_score": card.get("fit_score", 0),
            "action_type": action_type,
            "action_due": action_due,
            "docket_action": docket_action,
            "time_basis": time_basis,
            "first_artifact": first_artifact(card),
            "artifact_present_count": card.get("artifact_present_count", 0),
            "artifact_missing_count": card.get("artifact_missing_count", 0),
            "decision_question": card.get("decision_question", ""),
            "human_gate": card.get("human_gate", ""),
            "claim_boundary": card.get("claim_boundary", ""),
        }
        docket_items.append(finalize_item(item, current_date=current_date))

    followup_by_lane = {
        row["lane_id"]: row for row in followup_queue.get("actions", [])
    }
    external_by_lane = {
        row["lane_id"]: row for row in external_engagement.get("records", [])
    }
    nashville = events_by_lane["nashville_ec_takeoff_fall_2026"]
    nashville_info = events_by_lane[
        "nashville_ec_accelerator_info_sessions"
    ]
    dsip = events_by_lane["dla_dsip_topic_status"]
    amps = events_by_lane["dla_amps_application_access"]
    login = events_by_lane["login_gov_new_device_signin"]
    epri_completion = events_by_lane["epri_open_power_ai_mou_completed"]
    lanl = followup_by_lane["lanl_vision_licensing_followup"]
    argos = followup_by_lane["argos_emi_teaming_inquiry"]
    argos_external = external_by_lane["argos_emi_teaming_inquiry"]
    sam_rotation = external_by_lane["sam_public_credential_rotation"]

    official_claim_boundary = official_events["claim_boundary"]
    current_items = [
        (
            {
                "lane_id": "argos_emi_teaming_inquiry",
                "name": "Argos teaming inquiry monitor",
                "priority": 12,
                "channel": "EMAIL_THREAD_MONITOR",
                "status": argos["action_state"],
                "fit_score": 0,
                "action_type": "inbound_only_monitor",
                "action_due": None,
                "docket_action": argos["next_action"],
                "time_basis": (
                    "The current privacy-safe mailbox reconciliation shows zero drafts, "
                    "one sent copy, zero inbound replies, and an exhausted proactive "
                    "outreach allowance."
                ),
                "first_artifact": rel(FOLLOWUP_QUEUE_JSON),
                "artifact_present_count": 1,
                "artifact_missing_count": 0,
                "decision_question": (
                    "Has a specific inbound reply arrived that requires a bounded "
                    "response?"
                ),
                "human_gate": (
                    "Human review remains required: do not resend. A future response "
                    "requires a specific inbound request and a fresh exact action-time "
                    "review."
                ),
                "claim_boundary": followup_queue["claim_boundary"],
                "government_deadline_utc": argos["deadline_utc"],
                "selected_template_id": argos["current_response_template_id"],
                "eligible_template_id": argos["eligible_template_id"],
                "current_draft_count": argos_external["current_draft_count"],
                "matching_sent_count": argos_external["matching_sent_count"],
                "matching_inbound_count": argos_external[
                    "matching_inbound_count"
                ],
                "prior_approval_binding_expired": argos_external[
                    "prior_approval_binding_expired"
                ],
                "attachment_count": argos_external["attachment_count"],
                "send_now": False,
            },
            "ROLLING_OR_EVENT_GATED",
        ),
        (
            {
                "lane_id": "nashville_ec_takeoff_fall_2026",
                "source_lane_id": nashville_info["lane_id"],
                "name": "Nashville EC Fall 2026 TakeOff onboarding",
                "priority": -10,
                "channel": "OFFICIAL_ONBOARDING_ROUTE",
                "status": nashville["status"],
                "fit_score": 0,
                "action_type": "cohort_onboarding",
                "action_due": nashville["action"]["deadline"][
                    "onboarding_form_and_participation_agreement_date"
                ],
                "docket_action": (
                    "Review and complete the official onboarding form and participation "
                    "agreement by July 31. Treat the August 14 deposit as a separate "
                    "founder-reviewed payment action."
                ),
                "time_basis": (
                    "The selection notice and later official information-session email "
                    "both state a July 31 onboarding date; neither message states an "
                    "exact deadline time or timezone."
                ),
                "first_artifact": rel(OFFICIAL_EVENTS_JSON),
                "artifact_present_count": 1,
                "artifact_missing_count": 0,
                "decision_question": (
                    "Are every onboarding answer, participation term, and financial "
                    "commitment truthful and acceptable before the founder acts?"
                ),
                "human_gate": (
                    "Human founder reviews all onboarding answers and agreement terms; "
                    "agreement acceptance and payment remain separate explicit actions."
                ),
                "claim_boundary": official_claim_boundary,
                "onboarding_deadline_reconfirmed": True,
                "deposit_date": nashville["action"]["deadline"]["deposit_date"],
                "deadline_time_and_timezone_explicit": False,
                "optional_info_sessions_offered": True,
                "optional_info_session_count": nashville_info["evidence"][
                    "session_count"
                ],
                "optional_info_session_timezone_explicit": nashville_info[
                    "evidence"
                ]["session_timezone_explicit"],
                "optional_info_session_selected": False,
                "info_session_attendance_required": False,
            },
            None,
        ),
        (
            {
                "lane_id": "login_gov_new_device_signin",
                "name": "Login.gov new-device sign-in review",
                "priority": -9,
                "channel": "AUTHENTICATED_ACCOUNT",
                "status": login["status"],
                "fit_score": 0,
                "action_type": "account_security_review",
                "action_due": None,
                "docket_action": (
                    "If the sign-in was yours, no action is needed. If it was not, "
                    "navigate directly to Login.gov and immediately reset the account "
                    "credentials and authentication methods without using any email "
                    "security link."
                ),
                "time_basis": (
                    "Official security notice observed; no email reply or email security "
                    "link is required."
                ),
                "first_artifact": rel(OFFICIAL_EVENTS_JSON),
                "artifact_present_count": 1,
                "artifact_missing_count": 0,
                "decision_question": "Was the reported sign-in yours?",
                "human_gate": (
                    "Human user confirms recognition directly; any security remediation "
                    "must occur by navigating to Login.gov directly."
                ),
                "claim_boundary": official_claim_boundary,
            },
            "IMMEDIATE_24H",
        ),
        (
            {
                "lane_id": "sam_public_credential_rotation",
                "name": "SAM.gov credential rotation",
                "priority": -8,
                "channel": "AUTHENTICATED_ACCOUNT",
                "status": sam_rotation["state"],
                "fit_score": 0,
                "action_type": "account_credential_rotation",
                "action_due": sam_rotation["deadline"],
                "docket_action": (
                    "Rotate the affected credential inside the authenticated official "
                    "account, then rerun the guarded local verifier without exposing the "
                    "replacement value."
                ),
                "time_basis": "The current engagement register marks this account action overdue.",
                "first_artifact": rel(EXTERNAL_ENGAGEMENT_JSON),
                "artifact_present_count": 1,
                "artifact_missing_count": 0,
                "decision_question": "Has a replacement credential been created and verified privately?",
                "human_gate": (
                    "Human account holder performs the authenticated rotation; no secret "
                    "value is copied into the public docket."
                ),
                "claim_boundary": sam_rotation["claim_boundary"],
            },
            "OVERDUE_ACTION",
        ),
        (
            {
                "lane_id": "dla_missionweave_sbir",
                "source_lane_id": "missionweave_dsip_proposal",
                "name": "DLA MissionWeave DSIP recorded-status verification",
                "priority": -7,
                "channel": "READ_ONLY_PORTAL",
                "status": dsip["status"],
                "fit_score": 0,
                "action_type": "read_only_portal_verification",
                "action_due": None,
                "docket_action": dsip["action"]["safest_next_action"],
                "time_basis": (
                    "DSIP Support states that the Past Proposals view, not a missing "
                    "confirmation email, is the authoritative status source."
                ),
                "first_artifact": rel(OFFICIAL_EVENTS_JSON),
                "artifact_present_count": 1,
                "artifact_missing_count": 0,
                "decision_question": "What exact status does the read-only Past Proposals view show?",
                "human_gate": (
                    "Human user performs one read-only portal check and preserves a "
                    "receipt; no edit, upload, certification, signature, or submission."
                ),
                "claim_boundary": official_claim_boundary,
            },
            "ROLLING_OR_EVENT_GATED",
        ),
        (
            {
                "lane_id": "dla_amps_application_access",
                "name": "DLA AMPS application-role verification",
                "priority": -6,
                "channel": "AUTHENTICATED_ACCOUNT",
                "status": amps["status"],
                "fit_score": 0,
                "action_type": "account_role_verification",
                "action_due": None,
                "docket_action": amps["action"]["safest_next_action"],
                "time_basis": (
                    "The account exists, but the exact DLA application and external-user "
                    "role remain unverified."
                ),
                "first_artifact": rel(OFFICIAL_EVENTS_JSON),
                "artifact_present_count": 1,
                "artifact_missing_count": 0,
                "decision_question": "Which exact application role has the sponsoring program confirmed?",
                "human_gate": (
                    "Human user verifies the exact application, role, approving official, "
                    "and truthful justification before requesting access."
                ),
                "claim_boundary": official_claim_boundary,
            },
            "ROLLING_OR_EVENT_GATED",
        ),
        (
            {
                "lane_id": "epri_open_power_ai_mou_completed",
                "name": "EPRI Open Power AI completed-MOU custody review",
                "priority": -5,
                "channel": "PRIVATE_DOCUMENT_CUSTODY",
                "status": epri_completion["status"],
                "fit_score": 0,
                "action_type": "private_agreement_obligation_review",
                "action_due": None,
                "docket_action": epri_completion["action"]["safest_next_action"],
                "time_basis": "All parties completed the MOU; no reply deadline was stated.",
                "first_artifact": rel(OFFICIAL_EVENTS_JSON),
                "artifact_present_count": 1,
                "artifact_missing_count": 0,
                "decision_question": "What dated onboarding obligations, if any, appear in the private agreement?",
                "human_gate": (
                    "Human founder reviews the private agreement and any obligations; "
                    "signing identifiers and document contents stay out of this docket."
                ),
                "claim_boundary": official_claim_boundary,
            },
            "ROLLING_OR_EVENT_GATED",
        ),
        (
            {
                "lane_id": "lanl_vision_licensing_followup",
                "name": "LANL VISION licensing follow-up",
                "priority": -4,
                "channel": "EMAIL_MONITOR_ONLY",
                "status": lanl["source_state"],
                "fit_score": 0,
                "action_type": "inbound_only_monitor",
                "action_due": None,
                "docket_action": lanl["next_action"],
                "time_basis": (
                    "The sealed follow-up ledger records the one permitted proactive "
                    "follow-up, so the allowance is exhausted."
                ),
                "first_artifact": rel(FOLLOWUP_QUEUE_JSON),
                "artifact_present_count": 1,
                "artifact_missing_count": 0,
                "decision_question": "Has a specific substantive inbound request arrived?",
                "human_gate": (
                    "Human review is required for any inbound response, NDA, licensing "
                    "term, export-control question, or disclosure."
                ),
                "claim_boundary": followup_queue["claim_boundary"],
            },
            "ROLLING_OR_EVENT_GATED",
        ),
    ]
    docket_by_lane = {item["lane_id"]: item for item in docket_items}
    for current_item, urgency_override in current_items:
        docket_by_lane[current_item["lane_id"]] = finalize_item(
            current_item,
            current_date=current_date,
            urgency_override=urgency_override,
        )
    docket_items = list(docket_by_lane.values())

    urgency_counts: dict[str, int] = {}
    action_type_counts: dict[str, int] = {}
    for item in docket_items:
        urgency_counts[item["urgency"]] = urgency_counts.get(item["urgency"], 0) + 1
        action_type_counts[item["action_type"]] = action_type_counts.get(item["action_type"], 0) + 1

    immediate = [
        item
        for item in docket_items
        if item["urgency"] in {"OVERDUE_ACTION", "IMMEDIATE_24H", "URGENT_5D"}
    ]
    immediate_ids = [item["lane_id"] for item in immediate]
    all_artifacts_present = all(int(item["artifact_missing_count"]) == 0 for item in docket_items)
    gate_summary = gate["summary"]
    submission_argument_gate_clear = bool(gate.get("reviewer_gate_clear"))
    reviewer_packaging_gate_clear = (
        bool(gate_summary.get("packaging_checks_clear"))
        and int(gate_summary["unsafe_secret_count"]) == 0
        and int(gate_summary["unsafe_claim_count"]) == 0
    )

    payload = {
        "generated_utc": now_utc(),
        "schema": "human_action_docket_v1",
        "current_date": current_date.isoformat(),
        "status": "HUMAN_ACTION_DOCKET_READY"
        if reviewer_packaging_gate_clear and all_artifacts_present
        else "HUMAN_ACTION_DOCKET_BLOCKED",
        "summary": {
            "lane_count": len(docket_items),
            "immediate_or_urgent_count": len(immediate),
            "immediate_or_urgent_lane_ids": immediate_ids,
            "all_artifacts_present": all_artifacts_present,
            "reviewer_packaging_gate_clear": reviewer_packaging_gate_clear,
            "submission_argument_gate_clear": submission_argument_gate_clear,
            "unsafe_secret_count": int(gate_summary["unsafe_secret_count"]),
            "unsafe_claim_count": int(gate_summary["unsafe_claim_count"]),
            "traction_lane_count": int(traction["summary"]["lane_count"]),
            "concierge_lane_count": int(concierge["summary"]["lane_count"]),
            "human_action_required": True,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "live_trading_allowed": False,
            "urgency_counts": dict(sorted(urgency_counts.items())),
            "action_type_counts": dict(sorted(action_type_counts.items())),
        },
        "docket_items": sorted(
            docket_items,
            key=lambda item: (
                {
                    "OVERDUE_ACTION": 0,
                    "IMMEDIATE_24H": 1,
                    "URGENT_5D": 2,
                    "ACTIVE_14D": 3,
                    "WATCHLIST": 4,
                    "ROLLING_OR_EVENT_GATED": 5,
                    "PARKED_UNLESS_PARTNER": 6,
                    "PAST_DATE_RECHECK": 7,
                }.get(item["urgency"], 9),
                item["days_until_action_due"] if item["days_until_action_due"] is not None else 999,
                int(item["priority"]),
            ),
        ),
        "source_ledgers": {
            "concierge": {
                "path": rel(CONCIERGE_JSON),
                "sha256": sha256_file(CONCIERGE_JSON),
            },
            "traction": {
                "path": rel(TRACTION_JSON),
                "sha256": sha256_file(TRACTION_JSON),
            },
            "reviewer_gate": {
                "path": rel(REVIEWER_GATE_JSON),
                "sha256": sha256_file(REVIEWER_GATE_JSON),
            },
            "email_reconciliation": {
                "path": rel(EMAIL_RECONCILIATION_JSON),
                "sha256": sha256_file(EMAIL_RECONCILIATION_JSON),
            },
            "followup_queue": {
                "path": rel(FOLLOWUP_QUEUE_JSON),
                "sha256": sha256_file(FOLLOWUP_QUEUE_JSON),
            },
            "official_events": {
                "path": rel(OFFICIAL_EVENTS_JSON),
                "sha256": sha256_file(OFFICIAL_EVENTS_JSON),
            },
            "external_engagement": {
                "path": rel(EXTERNAL_ENGAGEMENT_JSON),
                "sha256": sha256_file(EXTERNAL_ENGAGEMENT_JSON),
            },
        },
        "human_stop_rule": NO_FINAL_ACTION,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["docket_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# Human Action Docket - {payload['current_date']}",
        "",
        "Purpose: convert the reviewer concierge packet into a date-aware action board that makes the next human moves obvious without authorizing external action.",
        "",
        f"Current date for this docket: `{payload['current_date']}`.",
        "",
        "## Gate Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Lanes: `{summary['lane_count']}`",
        f"- Immediate or urgent lanes: `{summary['immediate_or_urgent_count']}`",
        f"- All artifacts present: `{str(summary['all_artifacts_present']).lower()}`",
        f"- Reviewer packaging gate clear: `{str(summary['reviewer_packaging_gate_clear']).lower()}`",
        f"- Submission argument gate clear: `{str(summary['submission_argument_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Docket SHA-256: `{payload['docket_sha256']}`",
        "",
        "## Immediate And Urgent Lanes",
        "",
    ]
    urgent = [
        item
        for item in payload["docket_items"]
        if item["urgency"] in {"OVERDUE_ACTION", "IMMEDIATE_24H", "URGENT_5D"}
    ]
    for item in urgent:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                f"- Lane ID: `{item['lane_id']}`",
                f"- Urgency: `{item['urgency']}`",
                f"- Action due: `{item['action_due']}`",
                f"- Days until due: `{item['days_until_action_due']}`",
                f"- Action: {item['docket_action']}",
                f"- Time basis: {item['time_basis']}",
                f"- First artifact: `{item['first_artifact']}`",
                f"- Human gate: {item['human_gate']}",
                f"- Claim boundary: {item['claim_boundary']}",
                f"- Item SHA-256: `{item['docket_item_sha256']}`",
                "",
            ]
        )
    lines.extend(["## Full Docket", ""])
    for item in payload["docket_items"]:
        lines.extend(
            [
                f"### {item['priority']}. {item['name']}",
                "",
                f"- Lane ID: `{item['lane_id']}`",
                f"- Channel: `{item['channel']}`",
                f"- Status: `{item['status']}`",
                f"- Action type: `{item['action_type']}`",
                f"- Urgency: `{item['urgency']}`",
                f"- Action due: `{item['action_due']}`",
                f"- Action: {item['docket_action']}",
                f"- First artifact: `{item['first_artifact']}`",
                f"- Decision question: {item['decision_question']}",
                f"- Human gate: {item['human_gate']}",
                f"- Claim boundary: {item['claim_boundary']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Human Stop Rule",
            "",
            payload["human_stop_rule"],
        ]
    )
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the date-aware, human-gated action docket."
    )
    parser.add_argument(
        "--as-of-date",
        help=(
            "Operational date in YYYY-MM-DD form. Defaults to today's date in "
            f"{OPERATIONAL_TIMEZONE}."
        ),
    )
    args = parser.parse_args()
    payload = build_payload(args.as_of_date)
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public docket markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "immediate_or_urgent": payload["summary"]["immediate_or_urgent_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
