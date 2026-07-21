from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

SAM_BOARD = OUT_OPS / "sam_rush_submission_board_latest.json"
GRANTS_RANKED = ROOT / "out" / "grants" / "grants_ranked_v2.json"
ZERO_FRICTION = OUT_OPS / "funding_reviewer_zero_friction_pack_latest.json"
GRANT_REVIEWER_CURATION = ROOT / "config" / "grant_reviewer_curation_v1.json"
GRANT_REVIEWER_FEED = DASHBOARD_DATA / "grant_reviewer_feed.json"
SUBMISSION_RECEIPT = SPRINT_DIR / "EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.json"
CDC_ENGAGEMENT_RECEIPT = (
    SPRINT_DIR / "CDC_AI_ACQUISITION_RFI_ENGAGEMENT_RECEIPT_2026-07-16.json"
)
DOJ_BOP_DECISION = (
    ROOT
    / "grant_submissions"
    / "DOJ_BOP_15BCMS26Q70000005"
    / "DOJ_BOP_15BCMS26Q70000005_GO_NO_GO_2026-07-16.md"
)
DOJ_BOP_SOURCE_MANIFEST = (
    ROOT
    / "grant_submissions"
    / "DOJ_BOP_15BCMS26Q70000005"
    / "DOJ_BOP_15BCMS26Q70000005_SOURCE_MANIFEST_2026-07-16.json"
)
NSF_PITCH_DIR = ROOT / "grant_submissions" / "NSF_Project_Pitch"
NSF_PORTAL_FIELDS = NSF_PITCH_DIR / "PROJECT_PITCH_PORTAL_FIELDS_2026-07-16.md"
NSF_ROUTING_MANIFEST = (
    NSF_PITCH_DIR / "NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-16.json"
)
NASHVILLE_EC_DIR = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026"
NASHVILLE_EC_FIELD_MAP = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_FALL_2026_PORTAL_FIELD_MAP_2026-07-16.md"
)
NASHVILLE_EC_MANIFEST = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json"
)
NASHVILLE_EC_FACT_RESOLUTION_JSON = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json"
)
NASHVILLE_EC_FACT_RESOLUTION_MD = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.md"
)
NASHVILLE_EC_PRIVATE_COLLECTOR = (
    ROOT / "code" / "ops" / "CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py"
)
NASHVILLE_EC_PRIVATE_VALIDATOR = (
    ROOT / "code" / "ops" / "VALIDATE_NASHVILLE_EC_PRIVATE_FACTS.py"
)
NASHVILLE_EC_PRIVATE_WORKFLOW = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_PRIVATE_FACT_CAPTURE_WORKFLOW_2026-07-17.md"
)
NASHVILLE_EC_PRIVATE_FILL_MAP = (
    NASHVILLE_EC_DIR / "private" / "nashville_ec_portal_fill_map.private.json"
)
NASHVILLE_EC_DEADLINE_RECEIPT = (
    SPRINT_DIR
    / "NASHVILLE_EC_DEADLINE_PRESERVATION_ENGAGEMENT_RECEIPT_2026-07-17.json"
)
NASHVILLE_EC_DEADLINE_RESPONSE_CONTROL = (
    SPRINT_DIR / "NASHVILLE_EC_DEADLINE_PRESERVATION_RESPONSE_CONTROL_2026-07-17.md"
)
NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION_2026-07-17.json"
)
NASHVILLE_EC_SUBMISSION_RECEIPT = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_SUBMISSION_RECEIPT_2026-07-17.json"
)
DARPA_SN_26_97_DIR = ROOT / "grant_submissions" / "DARPA_SN_26_97"
DARPA_SN_26_97_SUBMISSION_RECEIPT = (
    DARPA_SN_26_97_DIR / "DARPA_SN_26_97_SUBMISSION_RECEIPT_2026-07-17.json"
)
DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT = (
    SPRINT_DIR / "DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.json"
)
OPENAI_BUILD_WEEK_DIR = (
    ROOT / "grant_submissions" / "OPENAI_BUILD_WEEK_20260721"
)
OPENAI_BUILD_WEEK_READINESS = (
    OPENAI_BUILD_WEEK_DIR / "OPENAI_BUILD_WEEK_SUBMISSION_READINESS_2026-07-17.json"
)
OPENAI_BUILD_WEEK_DESCRIPTION = (
    OPENAI_BUILD_WEEK_DIR / "OPENAI_BUILD_WEEK_PROJECT_DESCRIPTION_DRAFT_2026-07-17.md"
)
OPENAI_BUILD_WEEK_DEMO_SCRIPT = (
    OPENAI_BUILD_WEEK_DIR / "OPENAI_BUILD_WEEK_DEMO_SCRIPT_2026-07-17.md"
)
OPENAI_BUILD_WEEK_REQUIREMENTS = (
    OPENAI_BUILD_WEEK_DIR / "OPENAI_BUILD_WEEK_REQUIREMENTS_RECEIPT_2026-07-17.json"
)
MISSIONWEAVE_DIR = (
    ROOT / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave"
)
MISSIONWEAVE_MANIFEST = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_PACKAGE_MANIFEST_2026-07-16.json"
)
MISSIONWEAVE_ASSEMBLY_MAP = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_ASSEMBLY_MAP_2026-07-16.md"
)
MISSIONWEAVE_VOLUME1 = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_VOLUME1_PUBLIC_TEXT_2026-07-16.md"
)
MISSIONWEAVE_VOLUME2_PDF = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.pdf"
)
MISSIONWEAVE_COST_INPUTS = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_VOLUME3_COST_INPUTS_2026-07-16.md"
)
MISSIONWEAVE_VOLUME5 = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_VOLUME5_WORKSHEET_2026-07-16.md"
)
MISSIONWEAVE_CLAIM_MATRIX = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_CLAIM_EVIDENCE_MATRIX_2026-07-16.md"
)
MISSIONWEAVE_ACTION_GATE = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
)
MISSIONWEAVE_ACTION_GATE_MD = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.md"
)
MISSIONWEAVE_PORTAL_CHECKLIST = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_PORTAL_CHECKLIST_2026-07-17.md"
)
MISSIONWEAVE_PRIVATE_CAPTURE_TOOL = (
    ROOT / "code" / "ops" / "CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py"
)
MISSIONWEAVE_PRIVATE_FINALIZER = (
    ROOT / "code" / "ops" / "FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py"
)
MISSIONWEAVE_PRIVATE_CAPTURE_WORKFLOW = (
    MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_PRIVATE_CAPTURE_WORKFLOW_2026-07-17.md"
)
MISSIONWEAVE_OFFICIAL_TOPIC = (
    MISSIONWEAVE_DIR
    / "source_attachments"
    / "DLA26BZ03_NV011_OFFICIAL_TOPIC_DETAILS.json"
)
MISSIONWEAVE_BAA = (
    MISSIONWEAVE_DIR
    / "source_attachments"
    / "DoW_2026_SBIR_BAA_RELEASE_3_AMENDMENT_2.pdf"
)
MISSIONWEAVE_COMPONENT_INSTRUCTIONS = (
    MISSIONWEAVE_DIR
    / "source_attachments"
    / "DLA_26BZ_RELEASE_3_COMPONENT_INSTRUCTIONS.pdf"
)
LAUNCHTN_3686_DIR = ROOT / "grant_submissions" / "LAUNCHTN_3686_PITCH_2026"
LAUNCHTN_3686_FIELD_MAP = (
    LAUNCHTN_3686_DIR / "LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-17.md"
)
LAUNCHTN_3686_MANIFEST = (
    LAUNCHTN_3686_DIR / "LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-17.json"
)
LAUNCHTN_3686_DECK = (
    LAUNCHTN_3686_DIR / "LUMENCORE_3686_PITCH_DECK_2026-07-17.pptx"
)
LAUNCHTN_3686_FINANCIAL_MODEL = (
    LAUNCHTN_3686_DIR / "LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx"
)
EXTERNAL_ENGAGEMENT_REGISTER = (
    SPRINT_DIR / "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json"
)
FHWA_PARTNER_OUTREACH_CONTROL = (
    SPRINT_DIR / "FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json"
)
FHWA_PARTNER_RESPONSE_CONTROL = (
    SPRINT_DIR / "FHWA_TSMO_PARTNER_RESPONSE_CONTROL_2026-07-17.md"
)
ERDC_SOLUTION_BRIEF_GATE = (
    SPRINT_DIR / "ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-17.json"
)
ERDC_ROM_GATE = SPRINT_DIR / "ERDC_SDC_PHASE2_ROM_GATE_2026-07-17.json"
ERDC_ROM_WORKFLOW = (
    SPRINT_DIR / "ERDC_SDC_PHASE2_ROM_APPROVAL_WORKFLOW_2026-07-17.md"
)
ERDC_SOURCE_MANIFEST = (
    SPRINT_DIR
    / "source_attachments"
    / "W912HZ26SC005"
    / "SOURCE_MANIFEST_2026-07-16.json"
)
ERDC_PUBLIC_DRAFT_PDF = (
    ROOT / "output" / "pdf" / "LumenCore_ERDC_SDC_Solution_Brief_PUBLIC_DRAFT_2026-07-17.pdf"
)
SAM_KEY_ROTATION_CONTROL = (
    SPRINT_DIR / "SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json"
)
PATENT_DEADLINE_CONTROL = (
    SPRINT_DIR / "PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json"
)
PATENT_PRIVATE_CAPTURE_WORKFLOW = (
    SPRINT_DIR / "PATENT_CENTER_PRIVATE_DOCKET_CAPTURE_WORKFLOW_2026-07-17.md"
)

NV061_DIR = ROOT / "grant_submissions" / "NV061_TrackCast"
NV061_CONCEPT = NV061_DIR / "NV061_CONCEPT_DRAFT.md"
NV061_READINESS = NV061_DIR / "NV061_READINESS.md"
NV063_DIR = ROOT / "grant_submissions" / "NV063_HarborSentinel"
NV063_PACKAGE_MANIFEST = NV063_DIR / "NV063_DSIP_PACKAGE_MANIFEST_2026-07-16.json"
NV063_READINESS = NV063_DIR / "NV063_READINESS.md"
NV065_DIR = ROOT / "grant_submissions" / "NV065_AdaptiveSensorManagement"
NV065_CONCEPT = NV065_DIR / "NV065_CONCEPT_DRAFT.md"
NV065_READINESS = NV065_DIR / "NV065_READINESS.md"

CURATED_NAVY_OPPORTUNITY_NUMBERS = (
    "DON26BZ03-NV061",
    "DON26BZ03-NV063",
    "DON26BZ03-NV065",
)
DEFAULT_SOURCE_TTL_HOURS = 24.0

OUT_JSON = OUT_OPS / "near_deadline_submission_command_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "near_deadline_submission_command_board.json"
SCAN_DATE = date.today()
OUT_MD = SPRINT_DIR / f"NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_{SCAN_DATE.isoformat()}.md"

STAGE_COMMANDS = {
    "STAGE_NOW",
    "STAGE_RFI_FEEDBACK",
    "BUILD_PRIMARY_VOLUME",
    "STAGE_PROJECT_PITCH",
    "STAGE_CONCEPT_PAPER",
    "STAGE_APPLICATION",
    "STAGE_DSIP_PROPOSAL",
}
NO_BID_COMMANDS = {
    "NO_BID_MISSED_PREREQUISITE",
    "NO_SOLO_SUBMIT_PARTNER_ONLY",
    "PARTNER_OR_NO_BID",
}
EXPIRED_COMMAND = "EXPIRED_NO_SUBMISSION"
FRESHNESS_BLOCKED_COMMAND = "REVERIFY_SOURCE_BEFORE_STAGE"

PORTAL_ONLY_LANES = {
    "nashville_ec_fall_2026_takeoff",
    "openai_build_week_prooflock_console",
    "launchtn_3686_pitch_2026",
}

SENSITIVE_MARKERS = [
    "password",
    "meeting id",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key=",
    "sk-",
    "xox",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_aware_datetime(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def utc_iso(value: str, *, field: str) -> str:
    return (
        parse_aware_datetime(value, field=field)
        .astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def optional_aware_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return parse_aware_datetime(str(value), field="source timestamp")
    except (TypeError, ValueError):
        return None


def source_timestamp(payload: dict[str, Any]) -> str | None:
    for key in (
        "generated_utc",
        "harvested_utc",
        "updated_utc",
        "timestamp_utc",
        "verified_utc",
    ):
        parsed = optional_aware_datetime(payload.get(key))
        if parsed is not None:
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return None


def freshness_descriptor(
    *,
    source: str,
    source_utc: Any,
    as_of: datetime,
    ttl_hours: float,
    explicit_fresh_until_utc: Any = None,
) -> dict[str, Any]:
    parsed = optional_aware_datetime(source_utc)
    explicit_fresh_until = optional_aware_datetime(explicit_fresh_until_utc)
    if parsed is None:
        return {
            "source": source,
            "source_utc": None,
            "age_hours": None,
            "ttl_hours": ttl_hours,
            "fresh_until_utc": None,
            "freshness_status": "UNDATED_REVERIFY_REQUIRED",
            "status": "UNDATED_REVERIFY_REQUIRED",
            "blocking": True,
            "reason": "The source has no valid timezone-aware timestamp.",
        }

    parsed = parsed.astimezone(timezone.utc)
    age_hours = round((as_of - parsed).total_seconds() / 3600.0, 3)
    fresh_until = explicit_fresh_until or (parsed + timedelta(hours=ttl_hours))
    if age_hours < -0.084:
        status = "FUTURE_TIMESTAMP_REVERIFY_REQUIRED"
        reason = "The source timestamp is later than the board as-of time."
        blocking = True
    elif as_of > fresh_until:
        status = "STALE_REVERIFY_REQUIRED"
        reason = "The source exceeded its TTL before the board as-of time."
        blocking = True
    else:
        status = "CURRENT_WITHIN_TTL"
        reason = "The source timestamp is within its TTL at the board as-of time."
        blocking = False

    return {
        "source": source,
        "source_utc": parsed.isoformat().replace("+00:00", "Z"),
        "age_hours": age_hours,
        "ttl_hours": ttl_hours,
        "fresh_until_utc": fresh_until.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "freshness_status": status,
        "status": status,
        "blocking": blocking,
        "reason": reason,
    }


def build_source_freshness(
    *,
    curation: dict[str, Any],
    reviewer_feed: dict[str, Any],
    sam_board: dict[str, Any],
    grants_ranked: dict[str, Any],
    zero_friction: dict[str, Any],
    as_of_utc: str,
) -> dict[str, Any]:
    as_of = parse_aware_datetime(as_of_utc, field="board as_of_utc").astimezone(
        timezone.utc
    )
    ttl_raw = curation.get("reviewer_feed_ttl_hours")
    ttl_valid = (
        isinstance(ttl_raw, (int, float))
        and not isinstance(ttl_raw, bool)
        and ttl_raw > 0
    )
    ttl_hours = float(ttl_raw) if ttl_valid else DEFAULT_SOURCE_TTL_HOURS

    feed_freshness = reviewer_feed.get("freshness", {})
    if not isinstance(feed_freshness, dict):
        feed_freshness = {}
    feed_ttl_raw = feed_freshness.get("ttl_hours")
    feed_ttl_valid = (
        isinstance(feed_ttl_raw, (int, float))
        and not isinstance(feed_ttl_raw, bool)
        and feed_ttl_raw > 0
    )
    feed_ttl_hours = float(feed_ttl_raw) if feed_ttl_valid else ttl_hours
    descriptors = {
        "grant_reviewer_curation": freshness_descriptor(
            source="grant_reviewer_curation",
            source_utc=curation.get("verified_utc"),
            as_of=as_of,
            ttl_hours=ttl_hours,
        ),
        "grant_reviewer_feed": freshness_descriptor(
            source="grant_reviewer_feed",
            source_utc=reviewer_feed.get("generated_utc"),
            as_of=as_of,
            ttl_hours=feed_ttl_hours,
            explicit_fresh_until_utc=feed_freshness.get("fresh_until_utc"),
        ),
        "sam_rush_board": freshness_descriptor(
            source="sam_rush_board",
            source_utc=source_timestamp(sam_board),
            as_of=as_of,
            ttl_hours=ttl_hours,
        ),
        "grants_ranked": freshness_descriptor(
            source="grants_ranked",
            source_utc=source_timestamp(grants_ranked),
            as_of=as_of,
            ttl_hours=ttl_hours,
        ),
        "zero_friction_pack": freshness_descriptor(
            source="zero_friction_pack",
            source_utc=source_timestamp(zero_friction),
            as_of=as_of,
            ttl_hours=ttl_hours,
        ),
    }
    if not feed_ttl_valid:
        descriptors["grant_reviewer_feed"].update(
            {
                "freshness_status": "INVALID_TTL_REVERIFY_REQUIRED",
                "status": "INVALID_TTL_REVERIFY_REQUIRED",
                "blocking": True,
                "reason": "The reviewer feed TTL is missing or invalid.",
            }
        )

    sam_health = reviewer_feed.get("source_health", {}).get("sam_gov", {})
    if not isinstance(sam_health, dict):
        sam_health = {}
    sam_live = freshness_descriptor(
        source="sam_live_discovery",
        source_utc=sam_health.get("harvested_utc"),
        as_of=as_of,
        ttl_hours=ttl_hours,
    )
    records = sam_health.get("records")
    zero_rows = not isinstance(records, int) or isinstance(records, bool) or records <= 0
    inconclusive = (
        zero_rows
        or sam_health.get("live_response_observed") is not True
        or sam_health.get("response_shape_valid") is not True
    )
    sam_live.update(
        {
            "records": (
                records
                if isinstance(records, int) and not isinstance(records, bool)
                else None
            ),
            "reported_status": sam_health.get("status") or "MISSING_SOURCE_HEALTH",
            "reported_http_status": sam_health.get("http_status"),
            "reported_freshness_status_at_feed_build": sam_health.get(
                "source_freshness_status"
            ),
            "zero_rows": zero_rows,
        }
    )
    if inconclusive:
        sam_live.update(
            {
                "status": "ZERO_ROW_SAM_RESPONSE_INCONCLUSIVE_BLOCKER"
                if zero_rows
                else "SAM_RESPONSE_INCONCLUSIVE_BLOCKER",
                "blocking": True,
                "reason": (
                    "The bounded SAM diagnostic returned zero usable rows; this does not prove "
                    "that no opportunities exist and cannot refresh a deadline or eligibility state."
                ),
            }
        )
    descriptors["sam_live_discovery"] = sam_live

    if not ttl_valid:
        descriptors["ttl_control"] = {
            "source": "ttl_control",
            "source_utc": None,
            "age_hours": None,
            "ttl_hours": ttl_hours,
            "fresh_until_utc": None,
            "freshness_status": "INVALID_TTL_REVERIFY_REQUIRED",
            "status": "INVALID_TTL_REVERIFY_REQUIRED",
            "blocking": True,
            "reason": "The curation TTL is missing or invalid; the default is display-only.",
        }

    blockers = [
        {
            "source": key,
            "status": row["status"],
            "freshness_status": row["freshness_status"],
            "reason": row["reason"],
        }
        for key, row in descriptors.items()
        if row["blocking"]
    ]
    return {
        "as_of_utc": as_of.isoformat().replace("+00:00", "Z"),
        "ttl_hours": ttl_hours,
        "ttl_control_valid": ttl_valid,
        "overall_status": (
            "BLOCKED_REVERIFY_REQUIRED" if blockers else "CURRENT_WITHIN_TTL"
        ),
        "submission_decisions_fail_closed": True,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "sources": descriptors,
        "claim_boundary": (
            "Freshness describes local snapshots only. A current timestamp does not prove "
            "eligibility, an unchanged deadline, portal state, or submission readiness; zero-row "
            "or inconclusive discovery responses never prove opportunity absence."
        ),
    }


def nashville_private_action_gate() -> dict[str, Any]:
    required_gate_count = 15
    ignore_rule = "grant_submissions/NASHVILLE_EC_FALL_2026/private/"
    ignored = ignore_rule in {
        line.strip()
        for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    if not ignored:
        raise ValueError("Nashville EC private capture target is not git-ignored")

    if not NASHVILLE_EC_PRIVATE_FILL_MAP.is_file():
        return {
            "status": "READY_FOR_HIDDEN_FOUNDER_INPUT",
            "submission_ready_for_human_click": False,
            "required_private_gate_count": required_gate_count,
            "passed_private_gate_count": 0,
            "open_gate_count": required_gate_count,
            "private_input_present": False,
            "private_values_exposed": False,
            "private_target_git_ignored": True,
            "required_founder_prompt_count": 6,
            "required_portal_answer_count": 11,
            "collector": rel(NASHVILLE_EC_PRIVATE_COLLECTOR),
            "workflow": rel(NASHVILLE_EC_PRIVATE_WORKFLOW),
        }

    try:
        private_map = read_json(NASHVILLE_EC_PRIVATE_FILL_MAP)
        final_gate = private_map.get("final_action_gate", {})
        valid = (
            private_map.get("schema")
            == "lumencore.nashville_ec_private_portal_fill_map.v1"
            and private_map.get("status") == "VALIDATED_PRIVATE_PORTAL_FILL_MAP"
            and private_map.get("private_portal_only") is True
            and private_map.get("public_repo_publish_allowed") is False
            and private_map.get("question_answer_count") == 11
            and final_gate.get("private_facts_validated") is True
        )
        if not valid:
            raise ValueError("invalid private fill map")
        passed_gate_count = 12 + sum(
            final_gate.get(key) is True
            for key in (
                "live_portal_preview_reviewed",
                "fee_and_terms_reviewed",
                "final_submission_authorized_at_action_time",
            )
        )
        ready = passed_gate_count == required_gate_count
        status = (
            "READY_FOR_HUMAN_FINAL_SUBMIT_CLICK"
            if ready
            else "PRIVATE_FACTS_VALIDATED_PORTAL_PREVIEW_REQUIRED"
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        passed_gate_count = 0
        ready = False
        status = "PRIVATE_FILL_MAP_INVALID_RECAPTURE_REQUIRED"

    return {
        "status": status,
        "submission_ready_for_human_click": ready,
        "required_private_gate_count": required_gate_count,
        "passed_private_gate_count": passed_gate_count,
        "open_gate_count": required_gate_count - passed_gate_count,
        "private_input_present": True,
        "private_values_exposed": False,
        "private_target_git_ignored": True,
        "required_founder_prompt_count": 6,
        "required_portal_answer_count": 11,
        "collector": rel(NASHVILLE_EC_PRIVATE_COLLECTOR),
        "workflow": rel(NASHVILLE_EC_PRIVATE_WORKFLOW),
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def deadline_bucket(days: int | None) -> str:
    if days is None:
        return "unknown"
    if days < 0:
        return "past_due"
    if days <= 2:
        return "48_hour_sprint"
    if days <= 7:
        return "seven_day_sprint"
    if days <= 14:
        return "two_week_sprint"
    if days <= 31:
        return "thirty_day_sprint"
    return "later"


def days_to_close(deadline_date: str, scan_date: date = SCAN_DATE) -> int:
    return (date.fromisoformat(deadline_date) - scan_date).days


def normalize_lane_deadlines(
    lanes: list[dict[str, Any]], scan_date: date = SCAN_DATE
) -> None:
    for lane in lanes:
        deadline_date = str(
            lane.get("deadline_date") or str(lane.get("deadline_utc") or "")[:10]
        )
        try:
            days = days_to_close(deadline_date, scan_date)
        except ValueError:
            deadline_date = ""
            days = None
        lane["deadline_date"] = deadline_date or None
        lane["days_to_close"] = days
        lane["days_to_close_from_scan_date"] = days
        lane["deadline_bucket"] = deadline_bucket(days)


def sam_lookup(sam_board: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("solicitation_number")): row
        for row in sam_board.get("opportunities", [])
        if row.get("solicitation_number")
    }


def grant_lookup(grants: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in grants.get("ranked", []):
        opp_num = str(row.get("opp_num") or "")
        if opp_num:
            rows[opp_num] = row
    return rows


def inspect_nv063_package() -> dict[str, Any]:
    manifest = read_json(NV063_PACKAGE_MANIFEST)
    errors: list[str] = []
    artifacts = manifest.get("artifacts")
    if manifest.get("schema") != "nv063_dsip_package_manifest_v1":
        errors.append("manifest_schema")
    if manifest.get("topic") != "DON26BZ03-NV063":
        errors.append("manifest_topic")
    if not isinstance(artifacts, list) or not artifacts:
        artifacts = []
        errors.append("manifest_artifacts")

    package_files = [rel(NV063_PACKAGE_MANIFEST), rel(NV063_READINESS)]
    root_resolved = ROOT.resolve()
    for item in artifacts:
        if not isinstance(item, dict):
            errors.append("invalid_artifact_record")
            continue
        declared = str(item.get("path") or "")
        if not declared:
            errors.append("missing_artifact_path")
            continue
        package_files.append(declared.replace("\\", "/"))
        candidate = (ROOT / declared).resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError:
            errors.append(f"outside_root:{declared}")
            continue
        if not candidate.is_file():
            errors.append(f"missing:{declared}")
            continue
        data = candidate.read_bytes()
        expected_sha = str(item.get("sha256") or "").lower()
        if len(data) != item.get("bytes") or hashlib.sha256(data).hexdigest() != expected_sha:
            errors.append(f"hash_or_size:{declared}")

    return {
        "manifest_status": manifest.get("status") or "MISSING_OR_INVALID_MANIFEST",
        "package_integrity_pass": not errors,
        "package_integrity_status": (
            "MANIFEST_HASHES_VERIFIED" if not errors else "MANIFEST_REVERIFY_REQUIRED"
        ),
        "manifest_integrity_errors": errors,
        "package_files": list(dict.fromkeys(package_files)),
    }


def build_curated_navy_lanes(
    curation: dict[str, Any],
    source_freshness: dict[str, Any],
    scan_date: date,
) -> list[dict[str, Any]]:
    if curation.get("schema") != "lumencore.grant_reviewer_curation.v1":
        raise ValueError("Grant reviewer curation control is missing or has the wrong schema")
    candidates = curation.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("Grant reviewer curation candidates are missing")

    by_number: dict[str, dict[str, Any]] = {}
    for row in candidates:
        if not isinstance(row, dict):
            continue
        number = str(row.get("opportunity_number") or "")
        if number in CURATED_NAVY_OPPORTUNITY_NUMBERS:
            if number in by_number:
                raise ValueError(f"Duplicate curated Navy lane: {number}")
            by_number[number] = row
    missing = sorted(set(CURATED_NAVY_OPPORTUNITY_NUMBERS) - set(by_number))
    if missing:
        raise ValueError(f"Required curated Navy lanes are absent: {', '.join(missing)}")

    nv063_package = inspect_nv063_package()
    local_material = {
        "DON26BZ03-NV061": {
            "package_status": "CONCEPT",
            "package_files": [rel(NV061_CONCEPT), rel(NV061_READINESS)],
            "package_integrity_status": "CONCEPT_FILES_PRESENT"
            if NV061_CONCEPT.is_file() and NV061_READINESS.is_file()
            else "CONCEPT_FILES_MISSING",
            "package_integrity_pass": NV061_CONCEPT.is_file()
            and NV061_READINESS.is_file(),
        },
        "DON26BZ03-NV063": {
            "package_status": "DEDICATED_PACKAGE",
            **nv063_package,
        },
        "DON26BZ03-NV065": {
            "package_status": "CONCEPT",
            "package_files": [rel(NV065_CONCEPT), rel(NV065_READINESS)],
            "package_integrity_status": "CONCEPT_FILES_PRESENT"
            if NV065_CONCEPT.is_file() and NV065_READINESS.is_file()
            else "CONCEPT_FILES_MISSING",
            "package_integrity_pass": NV065_CONCEPT.is_file()
            and NV065_READINESS.is_file(),
        },
    }
    rank_by_number = {
        "DON26BZ03-NV063": 1.76,
        "DON26BZ03-NV065": 1.77,
        "DON26BZ03-NV061": 1.78,
    }
    curation_freshness = source_freshness["sources"][
        "grant_reviewer_curation"
    ]
    lanes: list[dict[str, Any]] = []
    for number in sorted(rank_by_number, key=rank_by_number.get):
        candidate = by_number[number]
        verification = candidate.get("source_verification")
        if not isinstance(verification, dict):
            raise ValueError(f"Curated Navy lane {number} has no source verification")
        close_raw = candidate.get("close_date")
        close = optional_aware_datetime(close_raw)
        deadline_utc = (
            close.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            if close is not None
            else None
        )
        deadline_date: str | None = None
        if close_raw:
            try:
                deadline_date = date.fromisoformat(str(close_raw)[:10]).isoformat()
            except ValueError:
                deadline_date = None
        published_open = (
            deadline_date is not None
            and date.fromisoformat(deadline_date) >= scan_date
        )

        material = local_material[number]
        authority_status = str(verification.get("status") or "")
        authority_recheck = (
            "RECHECK_REQUIRED" in authority_status
            or "unofficial" in str(verification.get("authority_boundary") or "").lower()
        )
        blockers: list[str] = []
        if curation_freshness["blocking"]:
            blockers.append(
                "grant_reviewer_curation:"
                + str(curation_freshness["freshness_status"])
            )
        if authority_recheck:
            blockers.append("DSIP_CONTROLLING_NOTICE_RECHECK_REQUIRED")
        if not material["package_integrity_pass"]:
            blockers.append(str(material["package_integrity_status"]))

        harbor = number == "DON26BZ03-NV063"
        why_now = (
            "HarborSentinel remains urgent because the curation control publishes a near close and a "
            "dedicated local package exists. It is not ready: the controlling DSIP notice, eligibility, "
            "portal state, compliance facts, cost approval, and any manifest drift must be resolved before staging."
            if harbor
            else (
                "This curated Navy topic remains visible because its published window is near, but the "
                "local material is a concept rather than a dedicated submission package. The controlling "
                "DSIP notice and every eligibility, evidence, compliance, cost, and portal gate remain open."
            )
        )
        next_gate = str(candidate.get("next_gate") or "").strip()
        lanes.append(
            {
                "rank": rank_by_number[number],
                "lane_id": str(candidate.get("candidate_id") or number),
                "source_system": "Curated Navy topic mirror / DSIP controlling portal",
                "source_dependency_keys": ["grant_reviewer_curation"],
                "opportunity_number": number,
                "title": candidate.get("title"),
                "agency": candidate.get("agency"),
                "deadline_utc": deadline_utc,
                "deadline_date": deadline_date,
                "published_close_date": close_raw,
                "official_deadline_text": verification.get("deadline_text"),
                "deadline_semantics": (
                    "PUBLISHED_TOPIC_MIRROR_DATE_STALE_DSIP_REVERIFY_REQUIRED"
                    if curation_freshness["blocking"]
                    else "PUBLISHED_TOPIC_MIRROR_DATE_DSIP_REVERIFY_REQUIRED"
                ),
                "deadline_source": rel(GRANT_REVIEWER_CURATION),
                "deadline_currently_verified": False,
                "deadline_actionable": False,
                "published_window_open_by_recorded_dates": published_open,
                "published_window_actionable": False,
                "command": FRESHNESS_BLOCKED_COMMAND,
                "pre_freshness_command": "ASSEMBLE_DSIP_PROPOSAL"
                if harbor
                else "DEVELOP_CONCEPT",
                "eligibility_state": candidate.get("eligibility_status"),
                "eligibility_verified": False,
                "fit_state": candidate.get("submission_status"),
                "submission_status": candidate.get("submission_status"),
                "submission_route": candidate.get("submission_route") or "DSIP",
                "official_url": verification.get("official_update_url"),
                "secondary_url": candidate.get("source_url"),
                "source_authority_status": authority_status,
                "source_verified_utc": verification.get("verified_utc"),
                "source_age_hours": curation_freshness.get("age_hours"),
                "source_freshness_status": curation_freshness[
                    "freshness_status"
                ],
                "source_recheck_required": True,
                "source_data_current": False,
                "source_authority_boundary": verification.get(
                    "authority_boundary"
                ),
                "freshness_blockers": blockers,
                "package_status": material["package_status"],
                "package_integrity_status": material[
                    "package_integrity_status"
                ],
                "package_integrity_pass": material["package_integrity_pass"],
                "package_manifest_status": material.get("manifest_status"),
                "package_integrity_errors": material.get(
                    "manifest_integrity_errors", []
                ),
                "package_files": material["package_files"],
                "portal_status": "PORTAL_ONLY_UNVERIFIED",
                "portal_status_verified": False,
                "urgency_status": (
                    "URGENT_PUBLISHED_DEADLINE_REVERIFY_REQUIRED"
                    if published_open
                    else "PUBLISHED_WINDOW_NOT_ACTIONABLE_REVERIFY_REQUIRED"
                ),
                "readiness_status": "URGENT_NOT_READY" if harbor else "NOT_READY",
                "submission_ready": False,
                "submission_ready_for_human_action": False,
                "why_now": why_now,
                "today_work": [
                    "Recheck the complete active solicitation and live DSIP topic before relying on the published close.",
                    next_gate,
                ],
                "human_gate": [
                    "Robert verifies current DSIP organization and submitter authority from the live portal.",
                    "Robert verifies eligibility, representations, cost, attachments, and the final portal preview from current controlling instructions.",
                ],
                "claim_boundary": candidate.get("claim_boundary"),
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            }
        )
    return lanes


def classify_lane_status(lane: dict[str, Any]) -> None:
    command = str(lane.get("command") or "")
    material_command = str(lane.get("pre_freshness_command") or command)
    if not lane.get("package_status"):
        if command in NO_BID_COMMANDS:
            lane["package_status"] = "NO_BID"
        elif command == EXPIRED_COMMAND:
            lane["package_status"] = "EXPIRED"
        elif lane.get("lane_id") in PORTAL_ONLY_LANES:
            lane["package_status"] = "PORTAL_ONLY"
        elif material_command in {"STAGE_CONCEPT_PAPER", "STAGE_PROJECT_PITCH"}:
            lane["package_status"] = "CONCEPT"
        elif lane.get("package_files"):
            lane["package_status"] = "DEDICATED_PACKAGE"
        else:
            lane["package_status"] = "SOURCE_ONLY_NOTICE"

    if not lane.get("portal_status"):
        submission_status = str(lane.get("submission_status") or "")
        route = str(lane.get("submission_route") or "").lower()
        if submission_status == "PORTAL_SUBMISSION_CONFIRMED":
            lane["portal_status"] = "PORTAL_CONFIRMED_RECEIPT_BACKED"
            lane["portal_status_verified"] = True
        elif command in NO_BID_COMMANDS:
            lane["portal_status"] = "NO_PORTAL_ACTION_AUTHORIZED"
            lane["portal_status_verified"] = False
        elif any(
            marker in route
            for marker in ("portal", "dsip", "airtable", "devpost", "research.gov", "grants.gov", "sam.gov")
        ):
            lane["portal_status"] = "PORTAL_ONLY_UNVERIFIED"
            lane["portal_status_verified"] = False
        else:
            lane["portal_status"] = "NOT_APPLICABLE_OR_NOT_OBSERVED"
            lane["portal_status_verified"] = False

    lane.setdefault("submission_ready", False)
    lane.setdefault("submission_ready_for_human_action", False)
    if not lane.get("readiness_status"):
        if command == "SENT_VERIFIED":
            lane["readiness_status"] = "RECEIPT_BACKED_HISTORICAL_SEND"
        elif command in NO_BID_COMMANDS:
            lane["readiness_status"] = "NO_BID"
        elif command == EXPIRED_COMMAND:
            lane["readiness_status"] = "EXPIRED_NOT_READY"
        elif lane.get("freshness_blockers"):
            lane["readiness_status"] = "NOT_READY_FRESHNESS_BLOCKED"
        else:
            lane["readiness_status"] = "NOT_READY_HUMAN_GATED"


def apply_lane_freshness_controls(
    lanes: list[dict[str, Any]],
    source_freshness: dict[str, Any],
    sam_numbers: set[str],
    grant_numbers: set[str],
) -> None:
    descriptors = source_freshness["sources"]
    for lane in lanes:
        number = str(lane.get("opportunity_number") or "")
        source_system = str(lane.get("source_system") or "").lower()
        dependencies = list(lane.get("source_dependency_keys") or [])
        if number in sam_numbers or "sam.gov" in source_system:
            dependencies.extend(["sam_rush_board", "sam_live_discovery"])
        if number in grant_numbers:
            dependencies.append("grants_ranked")
        dependencies = list(dict.fromkeys(dependencies))
        lane["source_dependency_keys"] = dependencies

        existing_blockers = list(lane.get("freshness_blockers") or [])
        dependency_blockers = [
            f"{key}:{descriptors[key]['status']}"
            for key in dependencies
            if key in descriptors and descriptors[key]["blocking"]
        ]
        lane["freshness_blockers"] = list(
            dict.fromkeys([*existing_blockers, *dependency_blockers])
        )
        if dependencies:
            blocking = bool(lane["freshness_blockers"])
            lane["source_freshness_status"] = (
                "BLOCKED_REVERIFY_REQUIRED"
                if blocking
                else "CURRENT_WITHIN_TTL"
            )
            lane["source_data_current"] = not blocking
            if blocking:
                lane["deadline_currently_verified"] = False
                lane["deadline_actionable"] = False
                lane["eligibility_currently_verified"] = False
                if lane["command"] in STAGE_COMMANDS:
                    lane["pre_freshness_command"] = lane["command"]
                    lane["command"] = FRESHNESS_BLOCKED_COMMAND
                    lane["today_work"] = [
                        "Reverify the complete controlling notice and deadline before resuming package staging.",
                        *lane["today_work"],
                    ]
        else:
            lane.setdefault("source_freshness_status", "NO_TTL_FEED_DEPENDENCY")
            lane.setdefault("source_data_current", None)
            lane.setdefault("deadline_actionable", False)
            lane.setdefault("deadline_currently_verified", False)
        classify_lane_status(lane)


def base_sources() -> dict[str, Any]:
    sources = {}
    for key, path in {
        "sam_rush_board": SAM_BOARD,
        "grants_ranked": GRANTS_RANKED,
        "funding_reviewer_zero_friction_pack": ZERO_FRICTION,
        "grant_reviewer_curation": GRANT_REVIEWER_CURATION,
        "grant_reviewer_feed": GRANT_REVIEWER_FEED,
        "nv061_concept": NV061_CONCEPT,
        "nv061_readiness": NV061_READINESS,
        "nv063_package_manifest": NV063_PACKAGE_MANIFEST,
        "nv063_readiness": NV063_READINESS,
        "nv065_concept": NV065_CONCEPT,
        "nv065_readiness": NV065_READINESS,
        "external_submission_receipt": SUBMISSION_RECEIPT,
        "cdc_engagement_receipt": CDC_ENGAGEMENT_RECEIPT,
        "doj_bop_go_no_go": DOJ_BOP_DECISION,
        "doj_bop_source_manifest": DOJ_BOP_SOURCE_MANIFEST,
        "nsf_project_pitch_portal_fields": NSF_PORTAL_FIELDS,
        "nsf_project_pitch_routing_manifest": NSF_ROUTING_MANIFEST,
        "nashville_ec_portal_field_map": NASHVILLE_EC_FIELD_MAP,
        "nashville_ec_application_manifest": NASHVILLE_EC_MANIFEST,
        "nashville_ec_human_fact_resolution": NASHVILLE_EC_FACT_RESOLUTION_JSON,
        "nashville_ec_private_collector": NASHVILLE_EC_PRIVATE_COLLECTOR,
        "nashville_ec_private_validator": NASHVILLE_EC_PRIVATE_VALIDATOR,
        "nashville_ec_private_workflow": NASHVILLE_EC_PRIVATE_WORKFLOW,
        "nashville_ec_deadline_preservation_receipt": NASHVILLE_EC_DEADLINE_RECEIPT,
        "nashville_ec_deadline_response_control": NASHVILLE_EC_DEADLINE_RESPONSE_CONTROL,
        "nashville_ec_official_deadline_confirmation": NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION,
        "nashville_ec_submission_receipt": NASHVILLE_EC_SUBMISSION_RECEIPT,
        "darpa_sn_26_97_submission_receipt": DARPA_SN_26_97_SUBMISSION_RECEIPT,
        "darpa_sn_26_97_public_submission_receipt": (
            DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT
        ),
        "openai_build_week_submission_readiness": OPENAI_BUILD_WEEK_READINESS,
        "openai_build_week_project_description": OPENAI_BUILD_WEEK_DESCRIPTION,
        "openai_build_week_demo_script": OPENAI_BUILD_WEEK_DEMO_SCRIPT,
        "openai_build_week_requirements": OPENAI_BUILD_WEEK_REQUIREMENTS,
        "missionweave_dsip_package_manifest": MISSIONWEAVE_MANIFEST,
        "missionweave_dsip_assembly_map": MISSIONWEAVE_ASSEMBLY_MAP,
        "missionweave_volume2_pdf": MISSIONWEAVE_VOLUME2_PDF,
        "missionweave_dsip_action_gate": MISSIONWEAVE_ACTION_GATE,
        "missionweave_dsip_portal_checklist": MISSIONWEAVE_PORTAL_CHECKLIST,
        "missionweave_dsip_private_capture_tool": MISSIONWEAVE_PRIVATE_CAPTURE_TOOL,
        "missionweave_dsip_private_volume2_finalizer": MISSIONWEAVE_PRIVATE_FINALIZER,
        "missionweave_dsip_private_capture_workflow": MISSIONWEAVE_PRIVATE_CAPTURE_WORKFLOW,
        "missionweave_official_topic": MISSIONWEAVE_OFFICIAL_TOPIC,
        "missionweave_baa_amendment_2": MISSIONWEAVE_BAA,
        "missionweave_dla_component_instructions": MISSIONWEAVE_COMPONENT_INSTRUCTIONS,
        "launchtn_3686_portal_field_map": LAUNCHTN_3686_FIELD_MAP,
        "launchtn_3686_application_manifest": LAUNCHTN_3686_MANIFEST,
        "launchtn_3686_pitch_deck": LAUNCHTN_3686_DECK,
        "launchtn_3686_financial_model": LAUNCHTN_3686_FINANCIAL_MODEL,
        "external_engagement_response_register": EXTERNAL_ENGAGEMENT_REGISTER,
        "fhwa_partner_outreach_control": FHWA_PARTNER_OUTREACH_CONTROL,
        "fhwa_partner_response_control": FHWA_PARTNER_RESPONSE_CONTROL,
        "erdc_solution_brief_compliance_gate": ERDC_SOLUTION_BRIEF_GATE,
        "erdc_phase2_rom_gate": ERDC_ROM_GATE,
        "erdc_phase2_rom_workflow": ERDC_ROM_WORKFLOW,
        "erdc_source_manifest": ERDC_SOURCE_MANIFEST,
        "erdc_public_draft_pdf": ERDC_PUBLIC_DRAFT_PDF,
        "sam_public_key_rotation_control": SAM_KEY_ROTATION_CONTROL,
        "patent_deadline_evidence_control": PATENT_DEADLINE_CONTROL,
    }.items():
        if path.exists():
            data = path.read_bytes()
            sources[key] = {
                "path": rel(path),
                "present": True,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        else:
            sources[key] = {"path": rel(path), "present": False}
    return sources


def apply_submission_receipts(lanes: list[dict[str, Any]], receipt: dict[str, Any]) -> None:
    sent_by_notice = {
        str(row.get("notice_id")): row
        for row in receipt.get("submissions", [])
        if str(row.get("result", "")).startswith("SENT_")
    }
    for lane in lanes:
        sent = sent_by_notice.get(str(lane.get("opportunity_number")))
        if sent is None:
            continue
        lane["pre_send_command"] = lane["command"]
        lane["command"] = "SENT_VERIFIED"
        lane["submission_status"] = sent["result"]
        lane["sent_utc"] = sent["sent_utc"]
        lane["receipt_path"] = rel(SUBMISSION_RECEIPT)
        lane["receipt_attachment_sha256"] = sent["attachment_sha256"]
        lane["today_work"] = [
            "Monitor for an inbound response, amendment, or clarification request.",
            "Do not resend unless the agency requests a replacement or the receipt fails verification.",
        ]
        lane["human_gate"] = []


def apply_nashville_submission_receipt(
    lanes: list[dict[str, Any]], receipt: dict[str, Any]
) -> None:
    confirmation = receipt.get("confirmation_page", {})
    controls = receipt.get("submission_controls", {})
    evidence = receipt.get("private_evidence", {})
    deadline = parse_aware_datetime(
        str(receipt.get("deadline_local", "")), field="Nashville deadline_local"
    )
    observed = parse_aware_datetime(
        str(receipt.get("confirmation_observed_local", "")),
        field="Nashville confirmation_observed_local",
    )
    evidence_sha256 = str(evidence.get("sha256", ""))
    valid = (
        receipt.get("schema") == "lumencore.nashville_ec_submission_receipt.v1"
        and receipt.get("status") == "PORTAL_SUBMISSION_CONFIRMED"
        and receipt.get("form_id") == "261305765806056"
        and receipt.get("selected_program") == "TakeOff"
        and confirmation.get("title") == "Thank You"
        and confirmation.get("bounded_confirmation")
        == "We have received your application."
        and confirmation.get("expected_next_steps_by") == "2026-08-03"
        and observed <= deadline
        and controls.get("required_answers_ready_before_entry") == "30/30"
        and controls.get("founder_attestations_incorporated") == 11
        and controls.get("program_fee_commitment") is False
        and len(evidence_sha256) == 64
        and all(character in "0123456789abcdefABCDEF" for character in evidence_sha256)
    )
    if not valid:
        raise ValueError("Nashville EC portal-submission receipt is missing or stale")

    lane = next(
        (
            row
            for row in lanes
            if row.get("opportunity_number") == "NASHVILLE-EC-FALL-2026"
        ),
        None,
    )
    if lane is None:
        raise ValueError("Nashville EC command lane is missing")

    lane["pre_send_command"] = lane["command"]
    lane["command"] = "SENT_VERIFIED"
    lane["submission_status"] = receipt["status"]
    lane["sent_utc"] = utc_iso(
        receipt["confirmation_observed_local"],
        field="Nashville confirmation_observed_local",
    )
    lane["receipt_path"] = rel(NASHVILLE_EC_SUBMISSION_RECEIPT)
    lane["receipt_attachment_sha256"] = evidence_sha256
    lane["verification_scope"] = "PORTAL_CONFIRMATION_PAGE_OBSERVED"
    lane["eligibility_state"] = "APPLICATION_SUBMITTED_PORTAL_CONFIRMATION_OBSERVED"
    lane["action_gate_status"] = "PORTAL_SUBMISSION_CONFIRMED"
    lane["action_gate_submission_ready_for_human_click"] = False
    lane["action_gate_passed_private_gate_count"] = lane[
        "action_gate_required_private_gate_count"
    ]
    lane["action_gate_open_gate_count"] = 0
    lane["action_gate_private_input_present"] = True
    lane["package_files"] = [
        *lane["package_files"],
        rel(NASHVILLE_EC_SUBMISSION_RECEIPT),
    ]
    lane["why_now"] = (
        "The portal displayed the bounded confirmation that the application was received. "
        "Preserve the receipt and monitor for the stated next-step window; do not describe "
        "the application as selected, funded, endorsed, or accepted into a cohort."
    )
    lane["today_work"] = [
        "Monitor the existing email account for Nashville EC next steps through August 3, 2026.",
        "Do not duplicate the application or accept a fee, terms, or cohort seat without a separate decision.",
    ]
    lane["human_gate"] = []
    lane["claim_boundary"] = receipt.get("claim_boundary")


def build_darpa_submission_lane(
    receipt: dict[str, Any], public_receipt: dict[str, Any]
) -> dict[str, Any]:
    if (
        receipt.get("schema") != "lumencore.darpa_rfi_submission_receipt.v1"
        or receipt.get("status") != "EMAIL_SUBMISSION_SENT_BEFORE_DEADLINE"
        or receipt.get("notice_id") != "DARPA-SN-26-97"
    ):
        raise ValueError("DARPA-SN-26-97 submission receipt is missing or stale")
    if (
        public_receipt.get("schema")
        != "lumencore.darpa_sn_26_97_public_submission_receipt.v1"
        or public_receipt.get("status")
        != "FORMAL_RFI_PACKAGE_SENT_AGENCY_RESPONSE_RECEIVED_MONITOR_ONLY"
    ):
        raise ValueError("DARPA-SN-26-97 public submission receipt is missing or stale")
    public_thread = public_receipt.get("thread_reconciliation", {})
    if (
        public_thread.get("agency_thread_response_after_formal_package_observed")
        is not True
        or public_thread.get("explicit_attachment_receipt_confirmed") is not False
        or public_thread.get("specific_action_request_observed") is not False
        or public_thread.get("duplicate_send_allowed") is not False
    ):
        raise ValueError("DARPA-SN-26-97 agency response boundary is invalid")

    sent = parse_aware_datetime(str(receipt.get("sent", "")), field="DARPA sent")
    deadline = parse_aware_datetime(
        str(receipt.get("deadline", "")), field="DARPA deadline"
    )
    margin_seconds = int((deadline - sent).total_seconds())
    attachments = receipt.get("attachments", [])
    expected_names = {
        "LumenCore_DARPA_SN_26_97_One_Slide.private.pdf",
        "LumenCore_DARPA_SN_26_97_RFI_Response.private.pdf",
    }
    attachment_names = {str(item.get("name", "")) for item in attachments}
    attachment_records_valid = all(
        int(item.get("bytes", 0)) > 0
        and len(str(item.get("sha256", ""))) == 64
        and all(
            character in "0123456789abcdefABCDEF"
            for character in str(item.get("sha256", ""))
        )
        for item in attachments
    )
    if (
        margin_seconds <= 0
        or receipt.get("sent_before_deadline_seconds") != margin_seconds
        or len(attachments) != 2
        or attachment_names != expected_names
        or not attachment_records_valid
        or receipt.get("acknowledgment", {}).get("received") is not False
    ):
        raise ValueError("DARPA-SN-26-97 submission receipt failed reconciliation")

    return {
        "rank": 1.6,
        "lane_id": "darpa_sn_26_97_anticipatory_research_rfi",
        "source_system": "SAM.gov / Gmail sent-folder receipt",
        "opportunity_number": "DARPA-SN-26-97",
        "title": receipt.get("title", "Anticipatory Research Program RFI"),
        "agency": "Defense Advanced Research Projects Agency",
        "deadline_utc": utc_iso(receipt["deadline"], field="DARPA deadline"),
        "deadline_date": "2026-07-17",
        "official_deadline_text": "July 17, 2026 at 5:00 PM Eastern Time",
        "command": "SENT_VERIFIED",
        "eligibility_state": "NON_PROPRIETARY_RFI_RESPONSE_SENT_BEFORE_DEADLINE",
        "fit_state": "BOUNDED_RESEARCH_AND_MEASUREMENT_RESPONSE_DELIVERED",
        "submission_route": receipt.get("submission_channel"),
        "official_url": receipt.get("official_notice_url"),
        "package_files": [
            rel(DARPA_SN_26_97_SUBMISSION_RECEIPT),
            rel(
                DARPA_SN_26_97_DIR
                / "DARPA_SN_26_97_SUBMISSION_RECEIPT_2026-07-17.md"
            ),
            rel(DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT),
            rel(
                SPRINT_DIR
                / "DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.md"
            ),
        ],
        "why_now": (
            "The sent-folder record is before the stated deadline and both attachment hashes "
            "reconcile. DARPA later responded in the same thread with generic SAM.gov submission "
            "guidance, but did not explicitly confirm either attachment or request further action."
        ),
        "today_work": [
            "Record the agency thread response and monitor for a specific clarification, replacement request, or workshop invitation.",
            "Do not resend unless DARPA requests a replacement or additional material.",
        ],
        "human_gate": [],
        "external_send_allowed_without_human": False,
        "final_submit_allowed_without_human": False,
        "submission_status": receipt["status"],
        "sent_utc": utc_iso(receipt["sent"], field="DARPA sent"),
        "receipt_path": rel(DARPA_SN_26_97_SUBMISSION_RECEIPT),
        "receipt_attachment_sha256": stable_sha256(attachments),
        "verification_scope": receipt.get("evidence_state"),
        "acknowledgment_received": False,
        "agency_thread_response_received": True,
        "agency_thread_response_received_utc": public_thread[
            "agency_thread_response_received_utc"
        ],
        "explicit_attachment_receipt_confirmed": False,
        "specific_action_request_observed": False,
        "claim_boundary": public_receipt.get("claim_boundary"),
    }


def build_openai_build_week_lane(readiness: dict[str, Any]) -> dict[str, Any]:
    requirements = readiness.get("official_requirements", {})
    facts = requirements.get("facts", {})
    submission_period = facts.get("submission_period", {})
    counts = readiness.get("counts", {})
    project = readiness.get("project", {})
    control_errors: list[str] = []
    if readiness.get("schema") != "lumencore.openai_build_week_submission_readiness.v1":
        control_errors.append("schema")
    if readiness.get("status") != "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN":
        control_errors.append("status")
    if readiness.get("core_ready") is not True:
        control_errors.append("core_ready")
    if readiness.get("ready_for_final_submission") is not False:
        control_errors.append("ready_for_final_submission")
    if submission_period.get("deadline_central") != "2026-07-21T19:00:00-05:00":
        control_errors.append("deadline_central")
    if counts.get("gate_total") != counts.get("pass", 0) + counts.get("open", 0):
        control_errors.append("gate_count_reconciliation")
    if counts.get("fail") != 0:
        control_errors.append("failed_gate_count")

    integrity_errors: list[str] = []
    for item in readiness.get("app_artifacts", []):
        artifact = ROOT / str(item.get("path", ""))
        if not artifact.is_file():
            integrity_errors.append(f"missing:{item.get('path')}")
            continue
        data = artifact.read_bytes()
        if (
            len(data) != item.get("bytes")
            or hashlib.sha256(data).hexdigest() != item.get("sha256")
        ):
            integrity_errors.append(f"hash_or_size:{item.get('path')}")
    source_integrity_pass = not control_errors and not integrity_errors
    source_blockers = [
        *(f"control:{error}" for error in control_errors),
        *(f"artifact:{error}" for error in integrity_errors),
    ]

    outputs = readiness.get("outputs", {})
    return {
        "rank": 1.65,
        "lane_id": "openai_build_week_prooflock_console",
        "source_system": "OpenAI Build Week / Devpost",
        "opportunity_number": "OPENAI-BUILD-WEEK-2026",
        "title": "OpenAI Build Week - ProofLock Console",
        "agency": "OpenAI / Devpost",
        "deadline_utc": submission_period.get("deadline_utc"),
        "deadline_date": "2026-07-21",
        "official_deadline_text": "July 21, 2026 at 5:00 PM Pacific / 7:00 PM Central",
        "deadline_semantics": "OFFICIAL_RULES_DEADLINE_VERIFIED",
        "command": (
            "STAGE_APPLICATION"
            if source_integrity_pass
            else FRESHNESS_BLOCKED_COMMAND
        ),
        "pre_freshness_command": "STAGE_APPLICATION",
        "eligibility_state": (
            "CORE_PROJECT_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN"
            if source_integrity_pass
            else "SOURCE_INTEGRITY_RECONCILIATION_REQUIRED"
        ),
        "fit_state": (
            "DEVELOPER_TOOLS_WORKING_PROJECT_STRONG_FIT"
            if source_integrity_pass
            else "DEVELOPER_TOOLS_FIT_HELD_FOR_SOURCE_RECONCILIATION"
        ),
        "submission_route": "Devpost submission manager",
        "official_url": requirements.get("official_sources", {}).get("overview"),
        "secondary_url": requirements.get("official_sources", {}).get(
            "submission_manager"
        ),
        "package_files": [
            str(outputs.get("json")),
            str(outputs.get("markdown")),
            str(outputs.get("description_draft")),
            str(outputs.get("demo_script")),
            str(outputs.get("requirements_receipt")),
        ],
        "readiness_status": readiness.get("status"),
        "readiness_gate_total": counts.get("gate_total"),
        "readiness_gate_pass_count": counts.get("pass"),
        "readiness_gate_open_count": counts.get("open"),
        "public_demo_url": project.get("public_demo_url"),
        "youtube_demo_url": project.get("youtube_demo_url"),
        "feedback_session_id_present": bool(project.get("feedback_session_id")),
        "confirmed_model_present": bool(project.get("confirmed_model")),
        "scoped_tree": project.get("scoped_tree"),
        "source_integrity_pass": source_integrity_pass,
        "source_control_errors": control_errors,
        "source_artifact_errors": integrity_errors,
        "source_recheck_required": not source_integrity_pass,
        "freshness_blockers": source_blockers,
        "source_freshness_status": (
            "CURRENT_WITHIN_PINNED_ARTIFACT_SET"
            if source_integrity_pass
            else "BLOCKED_REVERIFY_REQUIRED"
        ),
        "source_data_current": source_integrity_pass,
        "deadline_actionable": source_integrity_pass,
        "deadline_currently_verified": True,
        "why_now": (
            "This is the nearest unresolved submission deadline. The readiness control and "
            "local app artifacts reconcile; the public demo, model label, /feedback Session "
            "ID, video, Devpost registration, and final review remain open."
            if source_integrity_pass
            else "This is the nearest unresolved submission deadline, but its readiness control "
            "does not reconcile to the current local app artifacts. Hold staging claims until "
            "the exact public commit, artifact manifest, and submission fields are refreshed."
        ),
        "today_work": (
            [
                "Deploy the self-contained console to a stable public URL and verify every sample artifact fetch.",
                "Capture the exact project-building model label and the /feedback Session ID without guessing.",
                "Record and privacy-review the bounded demonstration, keep it under three minutes with audio, and publish it to YouTube.",
                "Populate the Devpost draft and stop for publicity, IP, certification, and final-submit review.",
            ]
            if source_integrity_pass
            else [
                "Reconcile the readiness packet to the exact public ProofLock commit and artifact hashes.",
                "Regenerate the bounded submission receipt before relying on any core-ready statement.",
                "Keep deployment, publicity/IP acceptance, and final submit behind their existing human gates.",
            ]
        ),
        "human_gate": (
            [
                "Robert provides the exact model label and /feedback Session ID from the qualifying task.",
                "Robert reviews the public demo video, Devpost publicity/IP terms, certifications, and final submission.",
            ]
            if source_integrity_pass
            else [
                "A bounded operator reconciles the exact public commit and artifact receipt.",
                "Robert reviews the reconciled public demo, model/session provenance, publicity/IP terms, certifications, and final submission.",
            ]
        ),
        "external_send_allowed_without_human": False,
        "final_submit_allowed_without_human": False,
        "claim_boundary": readiness.get("claim_boundary"),
    }


def build_cdc_receipt_lane(receipt: dict[str, Any]) -> dict[str, Any] | None:
    opportunity = receipt.get("opportunity", {})
    submission = receipt.get("submission", {})
    acknowledgment = receipt.get("acknowledgment", {})
    if (
        receipt.get("schema") != "lumencore.external_engagement_receipt.v1"
        or opportunity.get("notice_id") != "75D301-26-RFI-73483"
        or acknowledgment.get("status") != "RECEIPT_CONFIRMED_FOLLOW_UP_PENDING"
    ):
        return None
    attachment = submission.get("attachment", {})
    return {
        "rank": 2.5,
        "lane_id": "cdc_ai_acquisition_rfi",
        "source_system": "SAM.gov / Gmail receipt",
        "opportunity_number": "75D301-26-RFI-73483",
        "title": opportunity.get(
            "title", "CDC Artificial Intelligence for Acquisition Support"
        ),
        "agency": opportunity.get(
            "agency", "Centers for Disease Control and Prevention"
        ),
        "deadline_utc": "2026-07-30T21:00:00Z",
        "deadline_date": "2026-07-30",
        "official_deadline_text": "July 30, 2026 at 5:00 PM Eastern Time",
        "command": "SENT_VERIFIED",
        "eligibility_state": "RFI_MARKET_RESEARCH_RESPONSE_RECEIVED",
        "fit_state": "BOUNDED_AI_ACQUISITION_EVIDENCE_RESPONSE_DELIVERED",
        "submission_route": "Email response per the official RFI instructions",
        "official_url": "https://sam.gov/opp/3b42d94270da435fa690c2fc5f26e157/view",
        "package_files": [
            "CDC_AI_ACQUISITION_RFI_75D301-26-RFI-73483_2026-07-15.md",
            "LumenCore_CDC_AI_Acquisition_RFI_75D301-26-RFI-73483_2026-07-15.pdf",
            CDC_ENGAGEMENT_RECEIPT.name,
        ],
        "why_now": (
            "CDC confirmed receipt and said it will follow up. Preserve the receipt and "
            "monitor; do not duplicate-send."
        ),
        "today_work": [
            "Monitor the existing Gmail thread for a CDC clarification or follow-up.",
            "Do not resend unless CDC asks for a replacement or additional material.",
        ],
        "human_gate": [],
        "external_send_allowed_without_human": False,
        "final_submit_allowed_without_human": False,
        "submission_status": acknowledgment["status"],
        "sent_utc": submission.get("sent_utc"),
        "receipt_path": rel(CDC_ENGAGEMENT_RECEIPT),
        "receipt_attachment_sha256": attachment.get("sha256"),
        "claim_boundary": receipt.get("claim_boundary"),
    }


def expire_closed_lanes(lanes: list[dict[str, Any]]) -> None:
    protected = {"SENT_VERIFIED", *NO_BID_COMMANDS, EXPIRED_COMMAND}
    for lane in lanes:
        if (
            lane["days_to_close"] is None
            or lane["days_to_close"] >= 0
            or lane["command"] in protected
        ):
            continue
        lane["pre_expiry_command"] = lane["command"]
        lane["command"] = EXPIRED_COMMAND
        lane["submission_status"] = "DEADLINE_PASSED_NO_VERIFIED_SEND"
        lane["why_now"] = (
            "The response deadline passed without a verified transmission receipt. "
            "This lane is archival and must not be represented as submitted."
        )
        lane["today_work"] = [
            "Archive the lane as missed; do not imply a submission occurred.",
            "Retain reusable public-safe material only for a future verified opportunity.",
        ]
        lane["human_gate"] = []


def build_command_lanes(
    sam_board: dict[str, Any],
    grants_ranked: dict[str, Any],
    submission_receipt: dict[str, Any] | None = None,
    cdc_engagement_receipt: dict[str, Any] | None = None,
    nashville_submission_receipt: dict[str, Any] | None = None,
    darpa_submission_receipt: dict[str, Any] | None = None,
    darpa_public_submission_receipt: dict[str, Any] | None = None,
    openai_build_week_readiness: dict[str, Any] | None = None,
    scan_date: date = SCAN_DATE,
    curation_control: dict[str, Any] | None = None,
    source_freshness: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    curation_control = curation_control or read_json(GRANT_REVIEWER_CURATION)
    if source_freshness is None:
        source_freshness = build_source_freshness(
            curation=curation_control,
            reviewer_feed=read_json(GRANT_REVIEWER_FEED),
            sam_board=sam_board,
            grants_ranked=grants_ranked,
            zero_friction=read_json(ZERO_FRICTION),
            as_of_utc=now_utc(),
        )
    nashville_gate = nashville_private_action_gate()
    nashville_deadline = read_json(NASHVILLE_EC_DEADLINE_RECEIPT)
    nashville_official_deadline = read_json(NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION)
    if (
        nashville_deadline.get("schema") != "lumencore.external_engagement_receipt.v1"
        or nashville_deadline.get("acknowledgment", {}).get("status")
        != "DEADLINE_PRESERVATION_QUERY_SENT_RESPONSE_PENDING"
    ):
        raise ValueError("Nashville EC deadline-preservation receipt is missing or stale")
    if (
        nashville_official_deadline.get("schema")
        != "lumencore.nashville_ec_official_deadline_confirmation.v1"
        or nashville_official_deadline.get("status")
        != "OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED"
    ):
        raise ValueError("Nashville EC official deadline confirmation is missing or stale")
    sam = sam_lookup(sam_board)
    grants = grant_lookup(grants_ranked)

    nasa = sam.get("80TECH26RFI0020", {})
    fhwa = sam.get("693JJ326R000012", {})
    erdc = sam.get("W912HZ26SC005", {})
    bop = sam.get("15BCMS26Q70000005", {})
    nsf = grants.get("26-510", {})
    nsf_routing = read_json(NSF_ROUTING_MANIFEST)
    nsf_full_proposal = nsf_routing.get("full_proposal", {})
    fhwa_outreach = read_json(FHWA_PARTNER_OUTREACH_CONTROL)
    fhwa_control_current = (
        fhwa_outreach.get("schema")
        == "lumencore.fhwa_tsmo_partner_outreach_control.v3"
        and fhwa_outreach.get("status")
        == "RESPONSE_LEAD_DECLINED_ADDITIONAL_PARTNER_TEAM_SET"
    )
    fhwa_target_contacted = (
        fhwa_control_current
        and fhwa_outreach.get("response_control", {}).get(
            "qualified_partner_evidence_present"
        )
        is False
        and fhwa_outreach.get("response_control", {}).get(
            "qualified_response_lead_referral_present"
        )
        is True
    )
    fhwa_route_closed = (
        fhwa_control_current
        and fhwa_outreach.get("response_control", {}).get("state")
        == "NO_GO_TEAM_SET_NO_ADDITIONAL_PARTNERS"
        and fhwa_outreach.get("delivery_reconciliation", {}).get(
            "team_set_decline_count"
        )
        == 1
    )
    erdc_solution_gate = read_json(ERDC_SOLUTION_BRIEF_GATE)
    if erdc_solution_gate.get("schema") != (
        "lumencore.erdc_sdc_solution_brief_compliance_gate.v1"
    ):
        raise ValueError("ERDC solution-brief compliance gate is missing or stale")
    erdc_rom_gate = read_json(ERDC_ROM_GATE)
    if erdc_rom_gate.get("schema") != "lumencore.erdc_sdc_phase2_rom_gate.v1":
        raise ValueError("ERDC Phase II ROM gate is missing or stale")
    erdc_technical_pass = (
        erdc_solution_gate.get("technical_document_checks_pass") is True
        and erdc_solution_gate.get("source_integrity", {}).get(
            "all_source_checks_pass"
        )
        is True
    )
    erdc_rom_ready = (
        erdc_rom_gate.get("approval", {}).get(
            "rom_ready_for_private_pdf_insertion"
        )
        is True
    )
    missionweave_manifest = read_json(MISSIONWEAVE_MANIFEST)
    if missionweave_manifest.get("schema") != (
        "missionweave_dsip_submission_package_manifest.v1"
    ):
        raise ValueError("MissionWeave DSIP package manifest is missing or stale")
    if missionweave_manifest.get("topic") != "DLA26BZ03-NV011":
        raise ValueError("MissionWeave DSIP package manifest has the wrong topic")
    if missionweave_manifest.get("deadline") != "2026-07-22T12:00:00-04:00":
        raise ValueError("MissionWeave DSIP package manifest has a stale deadline")
    missionweave_files = missionweave_manifest.get("files", [])
    if missionweave_manifest.get("file_count") != len(missionweave_files):
        raise ValueError("MissionWeave DSIP package manifest file count does not reconcile")
    missionweave_integrity_errors: list[str] = []
    for item in missionweave_files:
        package_path = MISSIONWEAVE_DIR / str(item.get("path", ""))
        if not package_path.is_file():
            missionweave_integrity_errors.append(f"missing:{item.get('path')}")
            continue
        data = package_path.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest().upper()
        if len(data) != item.get("bytes") or actual_sha256 != item.get("sha256"):
            missionweave_integrity_errors.append(f"hash_or_size:{item.get('path')}")
    if missionweave_integrity_errors:
        raise ValueError(
            "MissionWeave DSIP package manifest verification failed: "
            + ", ".join(missionweave_integrity_errors)
        )
    missionweave_action_gate = read_json(MISSIONWEAVE_ACTION_GATE)
    if missionweave_action_gate.get("schema") != (
        "lumencore.missionweave_dsip_action_gate.v1"
    ):
        raise ValueError("MissionWeave DSIP action gate is missing or stale")
    if missionweave_action_gate.get("topic") != "DLA26BZ03-NV011":
        raise ValueError("MissionWeave DSIP action gate has the wrong topic")
    if missionweave_action_gate.get("source_integrity", {}).get(
        "all_checks_pass"
    ) is not True:
        raise ValueError("MissionWeave DSIP action gate source integrity failed")
    missionweave_private_input = missionweave_action_gate.get("private_input", {})
    if missionweave_private_input.get("capture_tool") != rel(
        MISSIONWEAVE_PRIVATE_CAPTURE_TOOL
    ):
        raise ValueError("MissionWeave private capture tool is missing or stale")
    if missionweave_private_input.get("capture_workflow") != rel(
        MISSIONWEAVE_PRIVATE_CAPTURE_WORKFLOW
    ):
        raise ValueError("MissionWeave private capture workflow is missing or stale")
    if missionweave_private_input.get("private_volume2_finalizer") != rel(
        MISSIONWEAVE_PRIVATE_FINALIZER
    ):
        raise ValueError("MissionWeave private Volume 2 finalizer is missing or stale")
    if (
        missionweave_private_input.get("pre_submit_excludes_action_time_approval")
        is not True
        or missionweave_private_input.get("sha256_exposed") is not False
        or missionweave_private_input.get("credential_values_accepted") is not False
        or missionweave_private_input.get("firm_pin_value_accepted") is not False
        or missionweave_private_input.get("private_final_volume2_path_exposed")
        is not False
        or missionweave_private_input.get("private_final_volume2_sha256_exposed")
        is not False
    ):
        raise ValueError("MissionWeave private capture safety controls failed")
    missionweave_gate_summary = missionweave_action_gate.get("gate_summary", {})
    missionweave_unresolved_gates = missionweave_gate_summary.get(
        "unresolved_gates", []
    )
    if (
        not isinstance(missionweave_unresolved_gates, list)
        or any(not isinstance(gate, str) for gate in missionweave_unresolved_gates)
        or len(missionweave_unresolved_gates)
        != len(set(missionweave_unresolved_gates))
        or missionweave_gate_summary.get("open_gate_count")
        != len(missionweave_unresolved_gates)
        or missionweave_gate_summary.get("passed_private_gate_count", 0)
        + len(missionweave_unresolved_gates)
        != missionweave_gate_summary.get("required_private_gate_count")
    ):
        raise ValueError("MissionWeave open-gate accounting failed")

    missionweave_lifecycle = missionweave_action_gate.get("gate_lifecycle", {})
    missionweave_lifecycle_stages = missionweave_lifecycle.get("stages", {})
    if (
        missionweave_lifecycle.get("submission_readiness_logic_unchanged")
        is not True
        or missionweave_lifecycle.get("classification_can_clear_gate") is not False
        or missionweave_lifecycle.get("all_open_gates_classified_once") is not True
        or not isinstance(missionweave_lifecycle_stages, dict)
        or any(
            not isinstance(stage, dict)
            for stage in missionweave_lifecycle_stages.values()
        )
    ):
        raise ValueError("MissionWeave lifecycle controls failed")
    missionweave_lifecycle_open = [
        gate
        for stage in missionweave_lifecycle_stages.values()
        if isinstance(stage, dict)
        for gate in stage.get("open_gates", [])
    ]
    if (
        len(missionweave_lifecycle_open)
        != len(set(missionweave_lifecycle_open))
        or set(missionweave_lifecycle_open) != set(missionweave_unresolved_gates)
    ):
        raise ValueError("MissionWeave lifecycle open-gate projection failed")

    missionweave_founder_sequence = missionweave_action_gate.get(
        "founder_action_sequence", {}
    )
    missionweave_founder_steps = missionweave_founder_sequence.get(
        "ordered_steps", []
    )
    if (
        missionweave_founder_sequence.get("all_open_gates_covered_once") is not True
        or missionweave_founder_sequence.get("classification_can_clear_gate")
        is not False
        or missionweave_founder_sequence.get("final_submission_human_only")
        is not True
        or not isinstance(missionweave_founder_steps, list)
        or any(not isinstance(step, dict) for step in missionweave_founder_steps)
        or missionweave_founder_sequence.get("open_step_count")
        != len(missionweave_founder_steps)
    ):
        raise ValueError("MissionWeave founder action sequence controls failed")
    missionweave_sequenced_open = [
        gate
        for step in missionweave_founder_steps
        if isinstance(step, dict)
        for gate in step.get("open_gates", [])
    ]
    if (
        len(missionweave_sequenced_open)
        != len(set(missionweave_sequenced_open))
        or set(missionweave_sequenced_open) != set(missionweave_unresolved_gates)
    ):
        raise ValueError("MissionWeave founder sequence open-gate projection failed")
    missionweave_next_founder_step = (
        missionweave_founder_steps[0] if missionweave_founder_steps else None
    )
    missionweave_today_work = [
        f"{step['title']}: {step['instruction']}"
        for step in missionweave_founder_steps
    ] or [
        "No open action-gate steps remain; perform the fresh corporate review and final human submission check."
    ]
    missionweave_human_gate = list(
        dict.fromkeys(
            str(step["human_boundary"])
            for step in missionweave_founder_steps
        )
    ) or ["The founder performs the final certification and submit action."]
    hud = grants.get("PDR-2600-DC-029Q", {})
    hhs_child = grants.get("HHS-2026-ACF-ACYF-CA-0037", {})

    lanes: list[dict[str, Any]] = [
        {
            "rank": 1,
            "lane_id": "nasa_data_center_rfi",
            "source_system": "SAM.gov",
            "opportunity_number": "80TECH26RFI0020",
            "title": nasa.get("title", "Strategic Partnerships for NASA Data Center Infrastructure"),
            "agency": nasa.get("agency", "NASA IT Procurement Office"),
            "deadline_utc": nasa.get("deadline_utc", "2026-07-17T21:00:00Z"),
            "deadline_date": "2026-07-17",
            "command": "STAGE_NOW",
            "eligibility_state": "OPEN_RFI_RESPONSE",
            "fit_state": "STRONG_CAPABILITY_RESPONSE_FIT",
            "submission_route": nasa.get("submission_route", "Email response per RFI instructions"),
            "official_url": nasa.get("official_url", "https://sam.gov/opp/312af51a7fc14110b1239bdd32252213/view"),
            "package_files": nasa.get(
                "package_files",
                [
                    "NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md",
                    "NASA_DATA_CENTER_RFI_RESPONSE_STUB_2026-07-10.md",
                ],
            )
            + [
                "NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.md",
                "NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.pdf",
                "NASA_DATA_CENTER_RFI_EMAIL_DRAFT_2026-07-11.md",
            ],
            "why_now": "Fastest clean federal market-research lane: no pricing needed, response can be bounded to capability, proof-to-decision validation, and no agency-validation claims.",
            "today_work": [
                "Confirm official RFI email recipients, page cap, attachments, and amendments.",
                "Promote the NASA outline/stub into a reviewer-ready RFI response.",
                "Stage email subject/body and attachment list for human approval.",
            ],
            "human_gate": [
                "Robert approves final capability language and any past-performance statement.",
                "Robert approves the final email send.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 1.5,
            "lane_id": "nashville_ec_fall_2026_takeoff",
            "source_system": "Nashville Entrepreneur Center official site / Gmail newsletter",
            "opportunity_number": "NASHVILLE-EC-FALL-2026",
            "title": "Nashville Entrepreneur Center Fall 2026 Accelerators",
            "agency": "Nashville Entrepreneur Center",
            "deadline_utc": nashville_official_deadline["confirmation"][
                "operational_utc_deadline"
            ],
            "deadline_date": "2026-07-17",
            "official_deadline_text": (
                "The official Nashville Entrepreneur Center reply states that applications "
                "are open until 11:59 p.m. on July 17. The message does not name a timezone; "
                "America/Chicago is the explicit operational inference."
            ),
            "deadline_semantics": "OFFICIAL_REPLY_CONFIRMED_TIME_TIMEZONE_INFERRED_SUBMIT_EARLY",
            "command": "STAGE_APPLICATION",
            "eligibility_state": "MIDDLE_TENNESSEE_SOLO_FOUNDER_FIT_HUMAN_FACTS_UNVERIFIED",
            "fit_state": "STRONG_TAKEOFF_MVP_AND_CUSTOMER_VALIDATION_FIT",
            "submission_route": "Nashville Entrepreneur Center common accelerator application",
            "official_url": "https://ec.co/apply/",
            "secondary_url": "https://ec.co/accelerators/takeoff/",
            "package_files": [
                rel(NASHVILLE_EC_FIELD_MAP),
                rel(NASHVILLE_EC_MANIFEST),
                rel(NASHVILLE_EC_FACT_RESOLUTION_JSON),
                rel(NASHVILLE_EC_FACT_RESOLUTION_MD),
                rel(NASHVILLE_EC_PRIVATE_COLLECTOR),
                rel(NASHVILLE_EC_PRIVATE_VALIDATOR),
                rel(NASHVILLE_EC_PRIVATE_WORKFLOW),
                rel(NASHVILLE_EC_DEADLINE_RECEIPT),
                rel(NASHVILLE_EC_DEADLINE_RESPONSE_CONTROL),
                rel(NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION),
            ],
            "deadline_support_status": nashville_official_deadline["status"],
            "deadline_support_sent_utc": nashville_deadline["submission"][
                "sent_utc"
            ],
            "deadline_support_do_not_duplicate_send": not nashville_official_deadline[
                "application_state"
            ]["duplicate_deadline_query_allowed"],
            "deadline_support_email_is_application": False,
            "deadline_support_reply_required": nashville_official_deadline[
                "application_state"
            ]["reply_required"],
            "deadline_timezone_explicit_in_message": nashville_official_deadline[
                "confirmation"
            ]["timezone_explicit_in_message"],
            "operational_timezone": nashville_official_deadline["confirmation"][
                "operational_timezone"
            ],
            "action_gate_status": nashville_gate["status"],
            "action_gate_submission_ready_for_human_click": nashville_gate[
                "submission_ready_for_human_click"
            ],
            "action_gate_required_private_gate_count": nashville_gate[
                "required_private_gate_count"
            ],
            "action_gate_passed_private_gate_count": nashville_gate[
                "passed_private_gate_count"
            ],
            "action_gate_open_gate_count": nashville_gate["open_gate_count"],
            "action_gate_private_input_present": nashville_gate[
                "private_input_present"
            ],
            "action_gate_private_values_exposed": nashville_gate[
                "private_values_exposed"
            ],
            "private_capture_target_git_ignored": nashville_gate[
                "private_target_git_ignored"
            ],
            "private_capture_required_founder_prompt_count": nashville_gate[
                "required_founder_prompt_count"
            ],
            "private_capture_required_portal_answer_count": nashville_gate[
                "required_portal_answer_count"
            ],
            "private_capture_collector": nashville_gate["collector"],
            "private_capture_workflow": nashville_gate["workflow"],
            "why_now": (
                "This is the nearest legitimate local reviewer and commercialization route. "
                "TakeOff fits a Nashville-based solo founder with a working MVP and no "
                "claimed customers. The listed $500 program fee and $125 start payment are "
                "not authorized; the application should answer no on fee readiness and "
                "request financial aid before accepting terms."
            ),
            "today_work": [
                "Run the hidden-prompt founder-fact collector and require its ignored 11-answer fill map to validate.",
                "Paste the claim-bounded answers into the common application and select TakeOff.",
                "Use the confirmed 11:59 p.m. close as the outside bound and submit early; do not resend and do not treat the support reply as an application.",
                "Stop at final preview; do not accept a fee, terms, or cohort seat during application staging.",
            ],
            "human_gate": [
                "Robert answers all six prompts covering founder status, weekly hours, conversation count, revenue, founder investment, received funding, and business debt.",
                "Robert reviews the final portal preview and approves submission before the July 17 close.",
                "Any later program fee, financial-aid arrangement, terms, or cohort acceptance requires a separate decision.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 1.75,
            "lane_id": "dla_missionweave_dsip_phase1",
            "source_system": "DSIP / DLA / SBIR.gov",
            "opportunity_number": "DLA26BZ03-NV011",
            "title": "Digital Twin of the Organization for Enhanced Mission Readiness",
            "agency": "Defense Logistics Agency",
            "deadline_utc": "2026-07-22T16:00:00Z",
            "deadline_date": "2026-07-22",
            "official_deadline_text": (
                "July 22, 2026 at 12:00 p.m. Eastern Time. The SBIR.gov topic record "
                "and DLA Release 3 schedule agree on July 22, 2026; the downloaded "
                "Amendment 2 BAA schedule line prints July 22, 2025, an apparent "
                "internal year typo. Reconfirm the live DSIP countdown before submission."
            ),
            "deadline_semantics": (
                "CROSS_SOURCE_2026_DATE_CONFIRMED_BAA_YEAR_TYPO_RECHECK_DSIP"
            ),
            "deadline_source_discrepancy_present": True,
            "deadline_source_discrepancy": (
                "The local Amendment 2 BAA schedule says July 22, 2025 while the "
                "2026 topic record, DLA Release 3 schedule, and package sources say "
                "July 22, 2026."
            ),
            "command": "STAGE_DSIP_PROPOSAL",
            "eligibility_state": (
                "OPEN_PHASE_I_SMALL_BUSINESS_IDENTITY_PI_AND_REPRESENTATIONS_UNVERIFIED"
            ),
            "fit_state": (
                "STRONG_TOPIC_FIT_BOUNDED_SYNTHETIC_EVIDENCE_NO_DLA_VALIDATION_CLAIM"
            ),
            "submission_route": "Defense SBIR/STTR Innovation Portal (DSIP)",
            "official_url": "https://www.sbir.gov/topics/12778",
            "secondary_url": "https://www.dodsbirsttr.mil/",
            "package_manifest_state": missionweave_manifest.get("package_state"),
            "package_manifest_integrity_pass": True,
            "package_manifest_file_count": len(missionweave_files),
            "action_gate_status": missionweave_action_gate.get("status"),
            "action_gate_submission_ready_for_human_click": missionweave_action_gate.get(
                "submission_ready_for_human_click", False
            ),
            "action_gate_required_private_gate_count": missionweave_action_gate.get(
                "gate_summary", {}
            ).get("required_private_gate_count"),
            "action_gate_passed_private_gate_count": missionweave_action_gate.get(
                "gate_summary", {}
            ).get("passed_private_gate_count"),
            "action_gate_open_gate_count": missionweave_action_gate.get(
                "gate_summary", {}
            ).get("open_gate_count"),
            "action_gate_unresolved_gates": missionweave_unresolved_gates,
            "action_gate_lifecycle": missionweave_lifecycle,
            "action_gate_founder_action_sequence": missionweave_founder_sequence,
            "action_gate_next_founder_step": missionweave_next_founder_step,
            "action_gate_all_open_gates_classified_once": True,
            "action_gate_all_open_gates_sequenced_once": True,
            "action_gate_classification_can_clear_gate": False,
            "action_gate_final_submission_human_only": True,
            "action_gate_private_input_present": missionweave_action_gate.get(
                "private_input", {}
            ).get("present", False),
            "action_gate_private_values_exposed": missionweave_action_gate.get(
                "private_input", {}
            ).get("private_values_exposed", False),
            "action_gate_private_input_sha256_exposed": missionweave_private_input.get(
                "sha256_exposed", False
            ),
            "action_gate_private_capture_tool": missionweave_private_input.get(
                "capture_tool"
            ),
            "action_gate_private_volume2_finalizer": missionweave_private_input.get(
                "private_volume2_finalizer"
            ),
            "action_gate_private_capture_workflow": missionweave_private_input.get(
                "capture_workflow"
            ),
            "action_gate_private_final_volume2_present": missionweave_private_input.get(
                "private_final_volume2_present", False
            ),
            "action_gate_private_final_volume2_path_exposed": missionweave_private_input.get(
                "private_final_volume2_path_exposed", False
            ),
            "action_gate_private_final_volume2_sha256_exposed": missionweave_private_input.get(
                "private_final_volume2_sha256_exposed", False
            ),
            "action_gate_pre_submit_excludes_action_time_approval": missionweave_private_input.get(
                "pre_submit_excludes_action_time_approval"
            ),
            "action_gate_credential_values_accepted": missionweave_private_input.get(
                "credential_values_accepted"
            ),
            "action_gate_firm_pin_value_accepted": missionweave_private_input.get(
                "firm_pin_value_accepted"
            ),
            "phase1_duration_months": 6,
            "phase1_cost_ceiling_usd": 100000,
            "topic_phase1_max_duration_months": 12,
            "topic_phase1_max_cost_usd": 100000,
            "itar_flag": True,
            "projected_cmmc_level": "Level 2 (Self)",
            "package_files": [
                rel(MISSIONWEAVE_MANIFEST),
                rel(MISSIONWEAVE_ASSEMBLY_MAP),
                rel(MISSIONWEAVE_VOLUME1),
                rel(MISSIONWEAVE_VOLUME2_PDF),
                rel(MISSIONWEAVE_COST_INPUTS),
                rel(MISSIONWEAVE_VOLUME5),
                rel(MISSIONWEAVE_CLAIM_MATRIX),
                rel(MISSIONWEAVE_ACTION_GATE),
                rel(MISSIONWEAVE_PORTAL_CHECKLIST),
                rel(MISSIONWEAVE_PRIVATE_CAPTURE_TOOL),
                rel(MISSIONWEAVE_PRIVATE_FINALIZER),
                rel(MISSIONWEAVE_PRIVATE_CAPTURE_WORKFLOW),
            ],
            "why_now": (
                "This is the nearest complete federal Phase I proposal package. The "
                "15-file manifest verifies byte-for-byte, the technical candidate is "
                "claim-bounded, and the official topic fit is strong. It is not "
                f"submission-ready: the current public action gate is {missionweave_action_gate['gate_summary']['passed_private_gate_count']}/{missionweave_action_gate['gate_summary']['required_private_gate_count']}, and every remaining gate must be resolved "
                "without exposing identity, cost, ITAR, CMMC, award-history, foreign-"
                "affiliation, rights, preview, or certification values."
            ),
            "today_work": missionweave_today_work,
            "human_gate": missionweave_human_gate,
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 2,
            "lane_id": "launchtn_3686_pitch_2026",
            "source_system": "Launch Tennessee official 3686 Airtable application",
            "opportunity_number": "LAUNCHTN-3686-2026",
            "title": "3686 Pitch Competition 2026, presented by Amazon",
            "agency": "Launch Tennessee",
            "deadline_utc": "2026-08-14T04:59:00Z",
            "deadline_date": "2026-08-13",
            "official_deadline_text": "August 13, 2026 at 11:59 PM Central Daylight Time",
            "deadline_semantics": "VERIFIED_CDT_TIMESTAMP",
            "command": "STAGE_APPLICATION",
            "eligibility_state": "TENNESSEE_STARTUP_FIT_HUMAN_ATTESTATION_REQUIRED",
            "fit_state": "STRONG_WORKING_MVP_AND_COMMERCIALIZATION_FIT",
            "submission_route": "Launch Tennessee 3686 Airtable application",
            "official_url": "https://airtable.com/app6GRZNbU72OmaK1/pagudvfO1hH7SmzBl/form",
            "package_files": [
                rel(LAUNCHTN_3686_FIELD_MAP),
                rel(LAUNCHTN_3686_MANIFEST),
                rel(LAUNCHTN_3686_DECK),
                rel(LAUNCHTN_3686_FINANCIAL_MODEL),
            ],
            "why_now": (
                "The application-specific deck and formula-driven five-year model have passed visual, "
                "content, formula, and attachment-hash QA. The remaining gates are founder-controlled facts, "
                "Tennessee eligibility, pricing and raise approval, and the live final preview."
            ),
            "today_work": [
                "Confirm the 11 private, legal, employment, Tennessee-eligibility, funding-history, and pricing facts in the application manifest.",
                "Approve or revise the illustrative pricing ranges and $250,000 validation-bridge funding need.",
                "Upload only the two hash-verified QA-passed attachments and stop at the complete final preview.",
            ],
            "human_gate": [
                "Robert enters private contact and address facts only inside the authenticated portal.",
                "Robert verifies the legal entity, formation year, employee count, Tennessee eligibility, and prior LaunchTN capital history.",
                "Robert approves the pricing, funding assumptions, attachments, and final portal preview before submission.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 3,
            "lane_id": "fhwa_tsmo_data_initiative",
            "source_system": "SAM.gov",
            "opportunity_number": "693JJ326R000012",
            "title": fhwa.get("title", "Transportation Systems Management and Operations Data Initiative"),
            "agency": fhwa.get("agency", "Federal Highway Administration"),
            "deadline_utc": fhwa.get("deadline_utc", "2026-08-03T13:00:00Z"),
            "deadline_date": "2026-08-03",
            "command": "NO_SOLO_SUBMIT_PARTNER_ONLY",
            "eligibility_state": (
                "TEAM_SET_NO_ADDITIONAL_PARTNERS_ROUTE_CLOSED"
                if fhwa_route_closed
                else "QUALIFIED_RESPONSE_LEAD_REFERRED_PARTNER_CONFIRMATION_PENDING"
                if fhwa_target_contacted
                else "MANDATORY_CORPORATE_EXPERIENCE_PARTNER_REQUIRED"
            ),
            "fit_state": "STRONG_TECHNICAL_FIT_MANDATORY_CORPORATE_EXPERIENCE_MISSING",
            "submission_route": fhwa.get("submission_route", "SAM.gov / official solicitation instructions"),
            "official_url": fhwa.get("official_url", "https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view"),
            "package_files": fhwa.get(
                "package_files",
                [
                    "FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
                    "LUMENCORE_FHWA_TSMO_CAPABILITY_NOTE_693JJ326R000012_2026-07-09.pdf",
                    "FHWA_TSMO_PHASE1_SUBMISSION_STUB_2026-07-10.md",
                ],
            )
            + [
                "FHWA_TSMO_COMPLIANCE_MATRIX_DRAFT_2026-07-11.md",
                "FHWA_TSMO_QUALIFIED_TEAMING_REQUEST_2026-07-16.md",
                "FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json",
                "FHWA_TSMO_PARTNER_RESPONSE_CONTROL_2026-07-17.md",
            ],
            "why_now": (
                "LumenCore has a strong bounded technical fit, but the solicitation requires "
                "documented corporate TSMO data-processing experience that LumenCore cannot "
                "claim. The first official listed route rejected delivery; the replacement route "
                "replied and referred the request to the subject matter expert leading this "
                "response. That response lead then confirmed that the team was already set "
                "and would not add partners, so this outreach route is closed."
            ),
            "today_work": [
                "Close the Cambridge Systematics route without another reply or follow-up.",
                "Do not reuse the rejected address, claim a partner, or cite Cambridge Systematics experience.",
                "Reopen only if Cambridge Systematics initiates a future-opportunity discussion or a different qualified partner independently confirms interest.",
            ],
            "human_gate": [
                "A qualified organization confirms a role and documentable corporate experience in writing.",
                "Robert approves any teaming terms, Phase I claims, and final submission preview.",
            ],
            "partner_outreach_status": (
                fhwa_outreach.get("status") if fhwa_control_current else "CONTROL_STALE"
            ),
            "partner_outreach_delivery_failure_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("delivery_failure_count", 0),
            "partner_outreach_replacement_send_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("replacement_send_count", 0),
            "partner_outreach_confirmed_delivery_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("confirmed_delivery_count", 0),
            "partner_outreach_inbound_response_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("response_count", 0),
            "partner_outreach_referral_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("qualified_response_lead_referral_count", 0),
            "partner_outreach_acknowledgment_send_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("threaded_acknowledgment_send_count", 0),
            "partner_outreach_fit_check_confirmed_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("fit_check_confirmed_count", 0),
            "partner_outreach_team_set_decline_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("team_set_decline_count", 0),
            "qualified_partner_evidence_present": False,
            "no_follow_up_before": (
                fhwa_outreach.get("response_control", {}).get("no_follow_up_before")
                if fhwa_control_current
                else None
            ),
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 4,
            "lane_id": "nsf_sbir_project_pitch",
            "source_system": "NSF Seed Fund Project Pitch",
            "opportunity_number": "26-510",
            "title": nsf.get(
                "title",
                "NSF Small Business Innovation Research / Small Business Technology Transfer Programs Phase I",
            ),
            "agency": nsf.get("raw", {}).get("agency", "U.S. National Science Foundation"),
            "deadline_utc": None,
            "deadline_date": nsf_full_proposal.get(
                "next_planning_target", "2026-11-04"
            ),
            "deadline_date_semantics": (
                "INVITATION_CONTINGENT_PLANNING_TARGET_NOT_PROJECT_PITCH_DUE_DATE"
            ),
            "deadline_semantics": "PROJECT_PITCH_GATE_ROLLING_FULL_PROPOSAL_INVITATION_REQUIRED",
            "project_pitch_due_date": None,
            "listed_full_proposal_deadline_dates": nsf_full_proposal.get(
                "listed_deadlines", []
            ),
            "nearest_listed_full_proposal_deadline_date": nsf_full_proposal.get(
                "nearest_listed_deadline"
            ),
            "nearest_listed_deadline_reachable": nsf_full_proposal.get(
                "july_27_2026_reachable", False
            ),
            "full_proposal_planning_deadline_date": nsf_full_proposal.get(
                "next_planning_target", "2026-11-04"
            ),
            "full_proposal_submission_allowed": False,
            "invitation_verified": False,
            "portal_state_verified": False,
            "official_deadline_text": (
                "NSF 26-510 lists July 27 and November 4, 2026, then March 4 and "
                "July 7, 2027, as full-proposal deadlines. July 27 is not currently "
                "reachable because no official Project Pitch invitation was verified; "
                "November 4 is planning only."
            ),
            "command": "STAGE_PROJECT_PITCH",
            "eligibility_state": "PROJECT_PITCH_REQUIRED_INVITATION_NOT_VERIFIED",
            "fit_state": "STRONG_TRUSTWORTHY_AI_FIT_26_510_26_511_STAFF_CONFIRMATION_REQUIRED",
            "submission_route": (
                "NSF Seed Fund Project Pitch now; Research.gov full proposal only after "
                "an official invitation"
            ),
            "official_url": "https://seedfund.nsf.gov/project-pitch/",
            "secondary_url": "https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology/nsf26-510/solicitation",
            "alternate_url": "https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology-0/nsf26-511/solicitation",
            "package_files": [
                rel(NSF_PORTAL_FIELDS),
                rel(NSF_PITCH_DIR / "PROJECT_PITCH_PASTE_CHECK_2026-07-16.md"),
                rel(NSF_ROUTING_MANIFEST),
                rel(NSF_PITCH_DIR / "PROJECT_PITCH_READINESS.md"),
            ],
            "why_now": (
                "This is the strongest grants-side route, but the immediate action is the "
                "rolling Project Pitch. July 27 is an official full-proposal deadline but "
                "is currently inaccessible without a verified invitation. NSF 26-510 is "
                "the cleaner general deep-technology fit; use 26-511 only if NSF confirms "
                "the software-defined scientific-instrumentation framing."
            ),
            "today_work": [
                "Confirm in the Project Pitch portal that no pitch is pending and no invitation or full proposal is open.",
                "Paste the four locally counted, claim-bounded fields from the canonical portal packet.",
                "Stop at final review so the legal company facts and submission certification can be checked.",
            ],
            "human_gate": [
                "Robert confirms the legal company profile, PI eligibility, and portal status.",
                "Robert reviews the final portal preview and approves the Project Pitch submission.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 10,
            "lane_id": "hud_robotics_ai_home_construction",
            "source_system": "Grants.gov / HUD",
            "opportunity_number": "PDR-2600-DC-029Q",
            "title": hud.get(
                "title",
                "Mass Market Solutions for Leveraging Robotics and AI Technologies for Home Construction Demonstration",
            ),
            "agency": hud.get("raw", {}).get("agency", "Department of Housing and Urban Development"),
            "deadline_utc": "2026-07-14T03:59:59Z",
            "deadline_date": "2026-07-13",
            "official_deadline_text": "July 13, 2026 at 11:59:59 PM Eastern Time",
            "command": "ELIGIBILITY_AND_PARTNER_GATE",
            "eligibility_state": "BUSINESS_ELIGIBILITY_POSSIBLE_PROJECT_CAPACITY_UNPROVEN",
            "fit_state": "TITLE_MATCH_ONLY_NO_CONSTRUCTION_DEMONSTRATION_EVIDENCE",
            "submission_route": "Grants.gov Workspace package if eligibility and demonstration facts are supportable",
            "official_url": "https://www.grants.gov/search-results-detail/362360",
            "package_files": [
                "HUD_ROBOTICS_AI_EMERGENCY_ELIGIBILITY_GATE_2026-07-11.md",
                "NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-11.md",
                "FUNDING_REVIEWER_ZERO_FRICTION_PACK_2026-07-10.md",
            ],
            "why_now": "Deadline is closest and the title matches robotics/AI, but it likely needs a credible construction demonstration plan, budget, and project facts. Treat as emergency only if eligibility passes.",
            "today_work": [
                "Open Grants.gov package and confirm eligible applicant categories, required forms, and attachments.",
                "If eligible, draft a narrow AI/robotics validation-and-instrumentation demonstration narrative.",
                "Stop before budget, certifications, and final submission.",
            ],
            "human_gate": [
                "Robert confirms eligible applicant status and real project/demonstration facts.",
                "Robert approves all Grants.gov certifications and final submission.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 5,
            "lane_id": "erdc_sovereign_cloud_cso",
            "source_system": "SAM.gov / ERDCWERX",
            "opportunity_number": "W912HZ26SC005",
            "title": erdc.get("title", "Sovereign Defense Cloud for High-Performance Computing CSO"),
            "agency": erdc.get("agency", "ERDC Information Technology Laboratory / HPCMP"),
            "deadline_utc": erdc.get("deadline_utc", "2026-08-07T21:00:00Z"),
            "deadline_date": "2026-08-07",
            "official_deadline_text": "August 7, 2026 at 4:00 PM Central Time",
            "command": "STAGE_CONCEPT_PAPER",
            "eligibility_state": (
                "OPEN_CSO_TECHNICAL_DRAFT_PASS_PRIVATE_ROM_SAM_AND_PORTAL_GATES_OPEN"
                if erdc_technical_pass
                else "OPEN_CSO_TECHNICAL_DOCUMENT_REVIEW_REQUIRED"
            ),
            "fit_state": (
                "STRONG_MODULAR_EVIDENCE_CONTROL_PLANE_FIT_TECHNICAL_DOCUMENT_PASS"
                if erdc_technical_pass
                else "MODULAR_EVIDENCE_CONTROL_PLANE_FIT_NOT_YET_TECHNICALLY_CLEARED"
            ),
            "submission_route": erdc.get("submission_route", "ERDCWERX Commercial Solutions Opening portal"),
            "official_url": erdc.get("official_url", "https://sam.gov/opp/8e32f0dfcdee42eeb3b2b03819a6ed25/view"),
            "secondary_url": erdc.get("secondary_url", "https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/"),
            "package_files": [
                rel(ERDC_PUBLIC_DRAFT_PDF),
                rel(ERDC_SOLUTION_BRIEF_GATE),
                rel(ERDC_ROM_GATE),
                rel(ERDC_ROM_WORKFLOW),
                rel(ERDC_SOURCE_MANIFEST),
            ],
            "solution_brief_status": erdc_solution_gate.get("status"),
            "technical_document_checks_pass": erdc_technical_pass,
            "rom_gate_status": erdc_rom_gate.get("status"),
            "rom_private_input_present": erdc_rom_gate.get("private_input", {}).get(
                "present"
            )
            is True,
            "rom_ready_for_private_pdf_insertion": erdc_rom_ready,
            "funding_currently_available": erdc_solution_gate.get(
                "funding_currently_available"
            )
            is True,
            "why_now": (
                "A technically compliant public-safe five-page body now exists with verified official-source "
                "hashes. The remaining work is private Phase II-only price approval, exact SAM contract-record "
                "matching, and final portal review; the notice says funding is not currently available."
            ),
            "today_work": [
                "Use the ignored private ROM workflow to support each cost input and approve one Phase II-only estimated price.",
                "Insert the approved price and exact SAM-matched legal identity and address only into the private final copy.",
                "Recheck the live ERDCWERX questions, amendments, terms, and complete preview before final confirmation.",
            ],
            "human_gate": [
                "Robert approves the supported Phase II-only candidate price and timestamp.",
                "Robert verifies active SAM contract registration and exact legal entity and address match.",
                "Robert reviews the private final PDF, portal answers, terms, and final confirmation.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 6,
            "lane_id": "doj_bop_medical_claims_quote",
            "source_system": "SAM.gov",
            "opportunity_number": "15BCMS26Q70000005",
            "title": bop.get("title", "Historical Medical Claims Data Analysis"),
            "agency": bop.get("agency", "Federal Bureau of Prisons"),
            "deadline_utc": bop.get("deadline_utc", "2026-07-23T15:00:00Z"),
            "deadline_date": "2026-07-23",
            "official_deadline_text": "July 23, 2026 at 11:00 AM Eastern Time",
            "command": "NO_SOLO_SUBMIT_PARTNER_ONLY",
            "eligibility_state": "SMALL_BUSINESS_SET_ASIDE_SOLO_DELIVERY_GATES_NOT_MET",
            "fit_state": "ANALYTICS_COMPONENT_FIT_HIPAA_ATO_HSPD12_MEDICAL_CLAIMS_AND_FFP_GATES_OPEN",
            "submission_route": bop.get("submission_route", "Email quote per solicitation instructions"),
            "official_url": "https://sam.gov/opp/52680f2a89c241b3a055c35d816b7f20/view",
            "package_files": [
                "grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_SOURCE_MANIFEST_2026-07-16.json",
                "grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_GO_NO_GO_2026-07-16.md",
                "grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_PARTNER_OUTREACH_TEMPLATE_2026-07-16.md",
            ],
            "why_now": "Official-source review supports only a conditional partner route. LumenCore does not currently evidence the HIPAA officer, ATO/ISSO delivery capacity, screened personnel, medical-claims expertise, or firm-fixed-price delivery posture required for a responsible solo quote.",
            "today_work": [
                "Do not send a solo quote.",
                "Use the bounded partner template only if a qualified healthcare-claims and federal-security prime is identified.",
                "Require the partner to own compliance, staffing, pricing, and protected-data delivery commitments.",
            ],
            "human_gate": [
                "A qualified prime confirms HIPAA, ATO/ISSO, HSPD-12, medical-claims, and delivery responsibility in writing.",
                "Robert approves the partner outreach, role, price, representations, and any final quote.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 14,
            "lane_id": "hhs_predictive_analytics_child_welfare",
            "source_system": "Grants.gov",
            "opportunity_number": "HHS-2026-ACF-ACYF-CA-0037",
            "title": hhs_child.get("title", "Predictive Analytics in Child Welfare Demonstration Grants"),
            "agency": hhs_child.get("raw", {}).get("agency", "Administration for Children and Families"),
            "deadline_utc": "2026-07-14T03:59:00Z",
            "deadline_date": "2026-07-13",
            "command": "NO_SOLO_SUBMIT_PARTNER_ONLY",
            "eligibility_state": "INELIGIBLE_AS_SOLO_SMALL_BUSINESS",
            "fit_state": "PARTNER_ONLY_CHILD_WELFARE_DOMAIN",
            "submission_route": "Partner with eligible public/tribal child-welfare agency only",
            "official_url": "https://www.grants.gov/search-results-detail/361912",
            "package_files": [],
            "why_now": "The title is relevant, but it is not a safe solo submission lane unless an eligible agency partner controls the application.",
            "today_work": [
                "Do not spend the sprint here unless an eligible agency partner is already available.",
                "Keep as a future proof-to-pilot target for predictive analytics ethics and validation.",
            ],
            "human_gate": [
                "Eligible agency partner identified and approves participation.",
                "Robert approves partner outreach or subrecipient role.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
    ]

    lanes.extend(
        [
            {
                "rank": 2,
                "lane_id": "army_aidp_rfi4",
                "source_system": "SAM.gov",
                "opportunity_number": "ACCAPGAIDPRFI4",
                "title": "Army Intelligence Data Platform RFI #4",
                "agency": "U.S. Army Contracting Command - Aberdeen Proving Ground",
                "deadline_utc": "2026-07-15T21:00:00Z",
                "deadline_date": "2026-07-15",
                "official_deadline_text": "July 15, 2026 at 5:00 PM Eastern Time",
                "command": "STAGE_RFI_FEEDBACK",
                "eligibility_state": "OPEN_RFI_FEEDBACK_ATTACHMENT_ACCESS_REQUIRED",
                "fit_state": "STRONG_DATA_PLATFORM_AND_AUDITABILITY_FEEDBACK_FIT",
                "submission_route": "Email questions and feedback using the official spreadsheet attachment",
                "official_url": "https://sam.gov/workspace/contract/opp/3d72f2df3aaf459797c14cefb41fd235/view",
                "package_files": ["ARMY_AIDP_RFI4_PARTNER_NOTE_STUB_2026-07-10.md"],
                "why_now": "The Army is requesting structured feedback on a draft data-platform solution. LumenCore can contribute bounded comments on evidence provenance, replay, observability, and decision auditability without claiming to supply the entire platform.",
                "today_work": [
                    "Download the public instructions and questions-and-feedback spreadsheet.",
                    "Map only documented LumenCore capabilities to draft requirements.",
                    "Stage the completed feedback sheet and email for review.",
                ],
                "human_gate": [
                    "Robert approves every capability and past-performance statement.",
                    "Robert approves the final feedback email.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 7,
                "lane_id": "ustda_indo_pacific_digital_infrastructure",
                "source_system": "SAM.gov",
                "opportunity_number": "1131PL26R0049",
                "title": "Indo-Pacific Digital Infrastructure Project Scoping Services",
                "agency": "U.S. Trade and Development Agency",
                "deadline_utc": "2026-07-22T17:00:00Z",
                "deadline_date": "2026-07-22",
                "official_deadline_text": "July 22, 2026 at 1:00 PM Eastern Time",
                "command": "PRICE_PAST_PERFORMANCE_AND_CAPACITY_GATE",
                "eligibility_state": "TOTAL_SMALL_BUSINESS_SET_ASIDE_US_FIRM",
                "fit_state": "ADJACENT_DIGITAL_INFRASTRUCTURE_FIT_SCOPING_CAPACITY_UNPROVEN",
                "submission_route": "Proposal under the official RFP instructions",
                "official_url": "https://sam.gov/workspace/contract/opp/fdefc4a420e04049a6a768f744d040c9/view",
                "package_files": ["USTDA_INDO_PACIFIC_DIGITAL_INFRA_SCOPING_STUB_2026-07-10.md"],
                "why_now": "It is a total small-business set-aside and adjacent to digital-infrastructure evaluation, but the prime must prove project-scoping capacity, international delivery, price, and relevant past performance.",
                "today_work": [
                    "Review Sections B through E and the performance work statement.",
                    "Run a strict responsibility, staffing, travel, and past-performance gate.",
                    "Proceed only if every mandatory role and deliverable can be evidenced.",
                ],
                "human_gate": [
                    "Robert confirms staffing, international-delivery capacity, and past performance.",
                    "Robert approves price, representations, and final proposal submission.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 8,
                "lane_id": "acl_ai_assistive_rehabilitation_rerc",
                "source_system": "Grants.gov / Simpler.Grants.gov",
                "opportunity_number": "HHS-2026-ACL-NIDILRR-REGE-0212",
                "title": "RERC on AI-Driven Assistive and Rehabilitation Technologies",
                "agency": "Administration for Community Living",
                "deadline_utc": "2026-07-17T03:59:00Z",
                "deadline_date": "2026-07-16",
                "official_deadline_text": "July 16, 2026 at 11:59 PM Eastern Time",
                "command": "TECHNICAL_CAPACITY_AND_DOMAIN_GATE",
                "eligibility_state": "SMALL_BUSINESS_ELIGIBLE",
                "fit_state": "POTENTIAL_LUMA_SKIN_SUIT_FIT_NOT_YET_EVIDENCED_IN_REPOSITORY",
                "submission_route": "Grants.gov Workspace",
                "official_url": "https://simpler.grants.gov/opportunity/c08bbf7a-563b-4af4-a79b-b1cb7bdd71ad",
                "package_files": [],
                "why_now": "Small businesses are eligible and the topic could fit an assistive-technology lane, but this is a five-year research center award. No repository evidence currently proves the required rehabilitation domain, team, facilities, or evaluation plan.",
                "today_work": [
                    "Open the NOFO and extract all mandatory research-center and domain requirements.",
                    "Locate dated Luma Skin/Suit evidence, investigators, facilities, and disability-community participation.",
                    "Do not start portal certifications unless the capacity gate passes.",
                ],
                "human_gate": [
                    "Robert confirms the proposed technology, investigators, facilities, and community partners are real and available.",
                    "Robert approves all certifications and final submission.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 9,
                "lane_id": "usda_farm_business_benchmarking",
                "source_system": "Grants.gov / NIFA",
                "opportunity_number": "USDA-NIFA-KFBMB-32830",
                "title": "Farm Business Management and Benchmarking Competitive Grants Program",
                "agency": "USDA National Institute of Food and Agriculture",
                "deadline_utc": "2026-07-20T21:00:00Z",
                "deadline_date": "2026-07-20",
                "official_deadline_text": "July 20, 2026 at 5:00 PM Eastern Time",
                "command": "AGRICULTURE_PARTNER_AND_DATA_GATE",
                "eligibility_state": "PRIVATE_ORGANIZATIONS_AND_CORPORATIONS_ELIGIBLE",
                "fit_state": "BENCHMARKING_METHOD_FIT_FARM_NETWORK_AND_FINBIN_DELIVERY_UNPROVEN",
                "submission_route": "Grants.gov Workspace",
                "official_url": "https://simpler.grants.gov/opportunity/a6c41cc0-e597-45c5-8507-1037d8cf7360",
                "secondary_url": "https://www.nifa.usda.gov/grants/funding-opportunities/farm-business-management-benchmarking-competitive-grants-program",
                "package_files": [],
                "why_now": "LumenCore's measurement methods are adjacent and private corporations are eligible, but the program requires genuine farm-management delivery, partner associations, outreach, and required farm-data contributions.",
                "today_work": [
                    "Extract the mandatory partner, farm-record, outreach, and FINBIN requirements.",
                    "Stop unless real agriculture partners and qualifying farm records are already available.",
                ],
                "human_gate": [
                    "Robert confirms qualifying agriculture partners, farm records, and program-delivery capacity.",
                    "Robert approves the budget, certifications, and final submission.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 11,
                "lane_id": "fhwa_intersection_safety_prototyping",
                "source_system": "SAM.gov",
                "opportunity_number": "693JJ3-26-BAA-0004",
                "title": "Intersection Safety Systems Prototyping",
                "agency": "Federal Highway Administration",
                "deadline_utc": "2026-07-20T19:00:00Z",
                "deadline_date": "2026-07-20",
                "official_deadline_text": "July 20, 2026 at 3:00 PM Eastern Time",
                "command": "NO_SOLO_SUBMIT_PARTNER_ONLY",
                "eligibility_state": "OPEN_BAA_TEAM_COMPOSITION_REQUIRED",
                "fit_state": "STRONG_MEASUREMENT_FIT_TESTBED_AND_PUBLIC_SECTOR_PARTNERS_MISSING",
                "submission_route": "Email proposal per the BAA instructions",
                "official_url": "https://sam.gov/opp/a08fe6151b524fbd87e4c7ce8f6a4abb/view",
                "package_files": [],
                "why_now": "The measurement and data-fusion problem is relevant, but a compliant team needs a lead system developer, an access-controlled roadway testbed, and a public-sector partner with jurisdictional authority.",
                "today_work": [
                    "Treat as a teaming lane, not a solo proposal.",
                    "Stage a bounded validation work-package only if qualified partners are already identified.",
                ],
                "human_gate": [
                    "Qualified lead, testbed, and public-sector partners confirm participation.",
                    "Robert approves role, price, representations, and final proposal.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 12,
                "lane_id": "hhs_ai_power_user_pilot",
                "source_system": "SAM.gov",
                "opportunity_number": "7571TE26R00004",
                "title": "HHS AI Power User Advanced Models and Features Pilot",
                "agency": "Department of Health and Human Services",
                "deadline_utc": "2026-07-14T21:00:00Z",
                "deadline_date": "2026-07-14",
                "official_deadline_text": "July 14, 2026 at 5:00 PM Eastern Time",
                "command": "PARTNER_OR_NO_BID",
                "eligibility_state": "OPEN_SOLICITATION_NO_SET_ASIDE",
                "fit_state": "THEMATIC_MEASUREMENT_FIT_PRIME_DELIVERY_REQUIREMENTS_NOT_MET",
                "submission_route": "SAM.gov solicitation instructions",
                "official_url": "https://sam.gov/workspace/contract/opp/d60ae511937b410fa6f13473acbae762/view",
                "package_files": [],
                "why_now": "The baselining and auditability language is highly relevant, but the prime must provide an integrated enterprise model-access bundle for up to 1,000 users plus security, administration, reporting, and authorization-path artifacts. LumenCore should not represent that capacity without an eligible platform prime.",
                "today_work": [
                    "Do not submit as a solo prime.",
                    "Preserve the solicitation as market validation for LumenCore's measurement and persistent-validation architecture.",
                ],
                "human_gate": [
                    "A qualified enterprise AI platform prime requests a documented subcontract role.",
                    "Robert approves any teaming terms, price, and external response.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 13,
                "lane_id": "nsf_techaccess_ai_ready_america_round1",
                "source_system": "NSF / Research.gov",
                "opportunity_number": "26-508",
                "title": "TechAccess: AI-Ready America - State/Territory Coordination Hubs",
                "agency": "U.S. National Science Foundation",
                "deadline_utc": None,
                "deadline_date": "2026-07-16",
                "official_deadline_text": "July 16, 2026 at 5:00 PM submitting organization's local time",
                "command": "NO_BID_MISSED_PREREQUISITE",
                "eligibility_state": "ROUND_ONE_REQUIRED_LOI_DUE_JUNE_16_WAS_MISSED",
                "fit_state": "STRATEGIC_PARTNER_FIT_WATCH_ROUND_TWO",
                "submission_route": "Research.gov or Grants.gov after required Letter of Intent",
                "official_url": "https://www.nsf.gov/funding/opportunities/techaccess-ai-ready-america/nsf26-508/solicitation",
                "package_files": [],
                "why_now": "Round one cannot be pursued because the required June 16 Letter of Intent deadline passed. The January 15, 2027 round-two deadline remains a legitimate statewide consortium target.",
                "today_work": [
                    "Mark round one no-bid; do not waste portal time.",
                    "Start a round-two partner map with statewide conveners, workforce organizations, universities, and government stakeholders.",
                ],
                "human_gate": [
                    "Robert approves partner outreach for the round-two consortium.",
                    "An eligible lead institution and statewide partner structure are confirmed.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
        ]
    )

    lanes.extend(
        build_curated_navy_lanes(curation_control, source_freshness, scan_date)
    )

    cdc_lane = build_cdc_receipt_lane(cdc_engagement_receipt or {})
    if cdc_lane is not None:
        lanes.append(cdc_lane)

    lanes.append(
        build_darpa_submission_lane(
            darpa_submission_receipt or {}, darpa_public_submission_receipt or {}
        )
    )
    lanes.append(build_openai_build_week_lane(openai_build_week_readiness or {}))

    apply_submission_receipts(lanes, submission_receipt or {})
    apply_nashville_submission_receipt(
        lanes, nashville_submission_receipt or {}
    )
    normalize_lane_deadlines(lanes, scan_date)
    expire_closed_lanes(lanes)
    apply_lane_freshness_controls(
        lanes,
        source_freshness,
        set(sam),
        set(grants),
    )
    lanes.sort(key=lambda row: (float(row["rank"]), row["opportunity_number"]))
    for rank, lane in enumerate(lanes, start=1):
        lane["rank"] = rank
        lane["lane_sha256"] = stable_sha256(lane)
    return lanes


def describe_lane(row: dict[str, Any] | None) -> str:
    if row is None:
        return "No open lane is currently supported by the board."
    deadline = row.get("official_deadline_text") or row.get("deadline_utc")
    return (
        f"{row['opportunity_number']} {row['title']}, due {deadline}; "
        f"command {row['command']}; fit {row['fit_state']}."
    )


def build_payload(
    scan_date: date = SCAN_DATE,
    *,
    generated_utc: str | None = None,
    as_of_utc: str | None = None,
) -> dict[str, Any]:
    generated = utc_iso(generated_utc or now_utc(), field="generated_utc")
    board_as_of = utc_iso(as_of_utc or generated, field="as_of_utc")
    sam_board = read_json(SAM_BOARD)
    grants_ranked = read_json(GRANTS_RANKED)
    zero = read_json(ZERO_FRICTION)
    curation_control = read_json(GRANT_REVIEWER_CURATION)
    reviewer_feed = read_json(GRANT_REVIEWER_FEED)
    source_freshness = build_source_freshness(
        curation=curation_control,
        reviewer_feed=reviewer_feed,
        sam_board=sam_board,
        grants_ranked=grants_ranked,
        zero_friction=zero,
        as_of_utc=board_as_of,
    )
    submission_receipt = read_json(SUBMISSION_RECEIPT)
    cdc_engagement_receipt = read_json(CDC_ENGAGEMENT_RECEIPT)
    nashville_submission_receipt = read_json(NASHVILLE_EC_SUBMISSION_RECEIPT)
    darpa_submission_receipt = read_json(DARPA_SN_26_97_SUBMISSION_RECEIPT)
    darpa_public_submission_receipt = read_json(
        DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT
    )
    openai_build_week_readiness = read_json(OPENAI_BUILD_WEEK_READINESS)
    sam_rotation_control = read_json(SAM_KEY_ROTATION_CONTROL)
    if sam_rotation_control.get("schema") != "lumencore.sam_public_credential_rotation_control.v1":
        raise ValueError("SAM.gov API-key rotation control is missing or stale")
    sam_deadline_state = sam_rotation_control["deadline"]["state"]
    if sam_rotation_control["rotation_verified"]:
        sam_critical_action = (
            "SAM.gov public credential rotation is locally detected and live-API verified; preserve the "
            "private key boundary and continue monitoring client health."
        )
    elif sam_deadline_state == "PAST_DUE":
        sam_critical_action = (
            "SAM.gov public credential rotation became overdue after 2026-07-16. Use the guarded hidden-input "
            "installer immediately, then require changed-fingerprint and live-API verification. Entity "
            "registration remains active; credential rotation is a separate account-maintenance action."
        )
    elif sam_deadline_state == "DUE_TODAY":
        sam_critical_action = (
            "SAM.gov public credential rotation is due 2026-07-16. Use the guarded hidden-input installer "
            "today; entity registration remains active and credential rotation is a separate "
            "account-maintenance action."
        )
    else:
        sam_critical_action = (
            "SAM.gov public credential rotation is upcoming. Use the guarded hidden-input installer before "
            "the deadline and verify the replacement without exposing it."
        )
    patent_deadline_control = read_json(PATENT_DEADLINE_CONTROL)
    if patent_deadline_control.get("schema") != "lumencore.patent_deadline_evidence_control.v1":
        raise ValueError("Patent deadline evidence control is missing or stale")
    lanes = build_command_lanes(
        sam_board,
        grants_ranked,
        submission_receipt,
        cdc_engagement_receipt,
        nashville_submission_receipt,
        darpa_submission_receipt,
        darpa_public_submission_receipt,
        openai_build_week_readiness,
        scan_date,
        curation_control,
        source_freshness,
    )
    stage_now = [row for row in lanes if row["command"] in STAGE_COMMANDS]
    sent_verified = [row for row in lanes if row["command"] == "SENT_VERIFIED"]
    emergency_gate = [row for row in lanes if row["command"] == "ELIGIBILITY_AND_PARTNER_GATE"]
    no_bid = [row for row in lanes if row["command"] in NO_BID_COMMANDS]
    expired = [row for row in lanes if row["command"] == EXPIRED_COMMAND]
    human_gated = [row for row in lanes if row["human_gate"]]
    open_candidates = [
        row
        for row in lanes
        if row["days_to_close"] is not None
        and row["days_to_close"] >= 0
        and row["command"] not in {"SENT_VERIFIED", EXPIRED_COMMAND, *NO_BID_COMMANDS}
    ]
    closest_open = min(
        open_candidates,
        key=lambda row: (row["days_to_close"], row["rank"]),
        default=None,
    )
    closest_stage = min(
        stage_now,
        key=lambda row: (row["days_to_close"], row["rank"]),
        default=None,
    )
    missionweave_lane = next(
        row for row in lanes if row["lane_id"] == "dla_missionweave_dsip_phase1"
    )
    build_week_lane = next(
        row for row in lanes if row["lane_id"] == "openai_build_week_prooflock_console"
    )
    harbor_lane = next(
        row
        for row in lanes
        if row["opportunity_number"] == "DON26BZ03-NV063"
    )
    missionweave_gate_progress = (
        f"{missionweave_lane['action_gate_passed_private_gate_count']}/"
        f"{missionweave_lane['action_gate_required_private_gate_count']}"
    )
    package_status_counts = {
        status: sum(row["package_status"] == status for row in lanes)
        for status in sorted({str(row["package_status"]) for row in lanes})
    }
    lane_status_groups = {
        "dedicated_package": [
            row["opportunity_number"]
            for row in lanes
            if row["package_status"] == "DEDICATED_PACKAGE"
        ],
        "source_only_notice": [
            row["opportunity_number"]
            for row in lanes
            if row["package_status"] == "SOURCE_ONLY_NOTICE"
        ],
        "concept": [
            row["opportunity_number"]
            for row in lanes
            if row["package_status"] == "CONCEPT"
        ],
        "no_bid": [
            row["opportunity_number"]
            for row in lanes
            if row["package_status"] == "NO_BID"
        ],
        "portal_only": [
            row["opportunity_number"]
            for row in lanes
            if row["package_status"] == "PORTAL_ONLY"
            or row["portal_status"] == "PORTAL_ONLY_UNVERIFIED"
        ],
    }
    freshness_blocked = [row for row in lanes if row["freshness_blockers"]]
    sam_live_source = source_freshness["sources"]["sam_live_discovery"]
    if build_week_lane["source_integrity_pass"]:
        strongest_today_action = (
            "Finish the OpenAI Build Week external gates first: deploy and verify the public demo, "
            "capture the exact model label and /feedback Session ID, record the privacy-reviewed "
            "sub-three-minute video, and stage the Devpost preview before the July 21 7:00 p.m. "
            "Central close. "
            f"Its current readiness control has {build_week_lane['readiness_gate_pass_count']}/"
            f"{build_week_lane['readiness_gate_total']} gates passed and "
            f"{build_week_lane['readiness_gate_open_count']} open. "
        )
        fastest_low_friction_lane = (
            "OpenAI Build Week is the nearest unresolved low-friction reviewer route. "
            f"The pinned artifact set reconciles and {build_week_lane['readiness_gate_pass_count']}/"
            f"{build_week_lane['readiness_gate_total']} gates pass; the public demo, exact model "
            "label, /feedback Session ID, video, Devpost registration, and final review remain open. "
            "Nashville EC is no longer an open lane because its portal confirmation is receipt-backed."
        )
    else:
        strongest_today_action = (
            "Reconcile the OpenAI Build Week readiness packet to the exact public ProofLock commit "
            "and artifact manifest before relying on its core-ready state; then complete only the "
            "remaining model/session, video, terms-review, and final-submit gates before the July 21 "
            "7:00 p.m. Central close. "
        )
        fastest_low_friction_lane = (
            "OpenAI Build Week remains the nearest unresolved low-friction reviewer route, but its "
            "local readiness packet is held because the pinned app artifacts do not reconcile. "
            "Refresh the exact commit-bound receipt before staging or submission-readiness claims. "
            "Nashville EC is no longer an open lane because its portal confirmation is receipt-backed."
        )

    payload: dict[str, Any] = {
        "schema": "near_deadline_submission_command_board_v5",
        "generated_utc": generated,
        "as_of_utc": board_as_of,
        "scan_date": scan_date.isoformat(),
        "status": "NEAR_DEADLINE_COMMAND_BOARD_ACTIVE_FAIL_CLOSED_FRESHNESS_BLOCKERS",
        "source_ledgers": base_sources(),
        "source_freshness": source_freshness,
        "summary": {
            "lane_count": len(lanes),
            "curated_navy_lane_count": sum(
                row["opportunity_number"] in CURATED_NAVY_OPPORTUNITY_NUMBERS
                for row in lanes
            ),
            "stage_now_count": len(stage_now),
            "sent_verified_count": len(sent_verified),
            "emergency_eligibility_gate_count": len(emergency_gate),
            "no_bid_or_partner_only_count": len(no_bid),
            "expired_without_verified_send_count": len(expired),
            "human_gated_count": len(human_gated),
            "freshness_blocked_lane_count": len(freshness_blocked),
            "freshness_blocker_count": source_freshness["blocker_count"],
            "sam_zero_row_inconclusive_blocker": sam_live_source["zero_rows"],
            "build_week_source_integrity_pass": build_week_lane[
                "source_integrity_pass"
            ],
            "build_week_source_recheck_required": build_week_lane[
                "source_recheck_required"
            ],
            "build_week_source_blocker_count": len(
                build_week_lane["freshness_blockers"]
            ),
            "package_status_counts": package_status_counts,
            "harbor_status": (
                f"{harbor_lane['urgency_status']}; {harbor_lane['readiness_status']}; "
                f"{harbor_lane['package_status']}; {harbor_lane['portal_status']}"
            ),
            "strongest_today_action": (
                strongest_today_action
                +
                f"Then use the MissionWeave checklist to move its private action gate beyond {missionweave_gate_progress} while keeping the proposal number, final PDF identity, credentials, and action-time approval private for the July 22 noon Eastern close. "
                "HarborSentinel is urgent but not ready: retain its dedicated package while rechecking DSIP, freshness, package integrity, eligibility, compliance, cost, and portal gates. "
                "Nashville EC is portal-confirmed; DARPA was sent before deadline and later returned a generic procedural thread response without explicit attachment confirmation; NASA and Army are sent, and CDC acknowledged receipt. Separately rotate the overdue SAM.gov public API credential without exposing it and capture the complete Patent Center docket."
            ),
            "critical_same_day_infrastructure_action": sam_critical_action,
            "closest_deadline_lane": describe_lane(closest_open),
            "closest_stage_ready_lane": describe_lane(closest_stage),
            "best_grants_lane": (
                "DLA26BZ03-NV011 MissionWeave Phase I, due July 22, 2026 at noon Eastern: all 15 public package files are hash-verified and the 11-page neutral PDF passes format checks. "
                "The hidden sectioned collector captures DSIP identity, proposal, and compliance facts without accepting credentials, and the guarded private finalizer can rebuild and QA the assigned-header PDF without exposing its number, path, or hash; approval remains a separate action-time gate. "
                f"The current public action gate is {missionweave_gate_progress}, with unsupported portal and compliance facts still open. "
                "DON26BZ03-NV063 HarborSentinel remains an urgent dedicated-package lane, but it is explicitly not ready and its stale topic mirror cannot refresh the controlling deadline or eligibility. NSF 26-510 stays the next rolling Project Pitch route after its source is refreshed."
            ),
            "best_contract_lane": "693JJ326R000012 FHWA TSMO Data Initiative remains partner-only through 2026-08-03, but the Cambridge Systematics response lead confirmed its team is already set, so that outreach route is closed. No solo bid, no duplicate follow-up, and no partner claim; reopen only through a different qualified organization with written role and corporate-experience evidence.",
            "fastest_low_friction_lane": fastest_low_friction_lane,
            "all_final_actions_blocked_without_human": True,
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
            "pricing_allowed_without_human": False,
            "legal_certification_allowed_without_human": False,
        },
        "operational_controls": {
            "sam_public_key_rotation": {
                "status": sam_rotation_control["status"],
                "deadline_local": sam_rotation_control["deadline"]["date_local"],
                "deadline_state": sam_deadline_state,
                "aliases_consistent": sam_rotation_control["local_configuration"]["aliases_consistent"],
                "replacement_installation_detected": sam_rotation_control["local_configuration"]["replacement_installation_detected"],
                "api_probe": sam_rotation_control["api_probe"]["classification"],
                "rotation_verified": sam_rotation_control["rotation_verified"],
                "private_installer": sam_rotation_control["private_installer"]["path"],
                "control_artifact": rel(SAM_KEY_ROTATION_CONTROL),
                "human_action_required": True,
                "browser_navigation_performed": False,
            },
            "patent_deadline_evidence": {
                "status": patent_deadline_control["status"],
                "payment_acknowledgement_found": patent_deadline_control["public_evidence_summary"]["payment_acknowledgement_found"],
                "filing_receipt_found": patent_deadline_control["public_evidence_summary"]["filing_receipt_found"],
                "official_correspondence_found": patent_deadline_control["public_evidence_summary"]["official_correspondence_found"],
                "official_status_record_found": patent_deadline_control["public_evidence_summary"]["official_status_record_found"],
                "required_docket_role_count": patent_deadline_control["public_evidence_summary"]["required_docket_role_count"],
                "captured_required_docket_role_count": patent_deadline_control["public_evidence_summary"]["captured_required_docket_role_count"],
                "docket_capture_complete": patent_deadline_control["public_evidence_summary"]["docket_capture_complete"],
                "missing_required_docket_roles": patent_deadline_control["public_evidence_summary"]["missing_required_docket_roles"],
                "us_prosecution_deadline": patent_deadline_control["deadline_posture"]["us_prosecution_deadline"],
                "foreign_pct_priority": patent_deadline_control["deadline_posture"]["foreign_pct_priority"],
                "control_artifact": rel(PATENT_DEADLINE_CONTROL),
                "private_capture_workflow": rel(PATENT_PRIVATE_CAPTURE_WORKFLOW),
                "human_action_required": True,
                "browser_navigation_performed": False,
            },
        },
        "lanes": lanes,
        "lane_status_groups": lane_status_groups,
        "sent_verified": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "submission_status": row["submission_status"],
                "sent_utc": row["sent_utc"],
                "receipt_path": row["receipt_path"],
                "receipt_attachment_sha256": row["receipt_attachment_sha256"],
                "verification_scope": row.get("verification_scope"),
                "claim_boundary": row.get("claim_boundary"),
            }
            for row in sent_verified
        ],
        "stage_now": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "command": row["command"],
                "deadline_utc": row["deadline_utc"],
                "official_deadline_text": row.get("official_deadline_text"),
                "official_url": row["official_url"],
                "package_files": row["package_files"],
            }
            for row in stage_now
        ],
        "emergency_gate": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "command": row["command"],
                "deadline_utc": row["deadline_utc"],
                "official_url": row["official_url"],
                "human_gate": row["human_gate"],
            }
            for row in emergency_gate
        ],
        "no_bid_or_partner_only": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "command": row["command"],
                "deadline_date": row["deadline_date"],
                "eligibility_state": row["eligibility_state"],
                "fit_state": row["fit_state"],
                "package_status": row["package_status"],
                "portal_status": row["portal_status"],
                "official_url": row["official_url"],
            }
            for row in no_bid
        ],
        "expired_without_verified_send": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "deadline_date": row["deadline_date"],
                "pre_expiry_command": row.get("pre_expiry_command"),
                "submission_status": row.get("submission_status"),
                "official_url": row["official_url"],
            }
            for row in expired
        ],
        "freshness_blocked": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "pre_freshness_command": row.get("pre_freshness_command"),
                "command": row["command"],
                "source_freshness_status": row["source_freshness_status"],
                "freshness_blockers": row["freshness_blockers"],
                "deadline_actionable": row["deadline_actionable"],
                "submission_ready": row["submission_ready"],
            }
            for row in freshness_blocked
        ],
        "zero_friction_pack_status": (
            "STALE_REVERIFY_REQUIRED"
            if source_freshness["sources"]["zero_friction_pack"]["blocking"]
            else zero.get("status", "UNKNOWN")
        ),
        "zero_friction_pack_reported_status": zero.get("status", "UNKNOWN"),
        "submission_boundary": {
            "can_open_pages": True,
            "can_stage_drafts": True,
            "can_fill_nonfinal_routine_fields_after_user_login": True,
            "can_final_submit_without_human": False,
            "must_stop_before": [
                "final Grants.gov submit",
                "final SAM.gov submit",
                "final email send",
                "legal certification",
                "signature",
                "terms acceptance",
                "pricing or quote amount",
                "claim of agency validation, award, realized savings, or customer ROI",
            ],
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(
                SPRINT_DIR
                / f"NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_{scan_date.isoformat()}.md"
            ),
        },
    }
    payload["command_board_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# Near-Deadline Submission Command Board - {payload['scan_date']}",
        "",
        "This is the action board for getting the closest credible grants and federal contract responses fully staged.",
        "",
        f"Direct answer: HarborSentinel remains urgent but is not ready; its dedicated package stays visible while stale source, DSIP, package-integrity, eligibility, compliance, cost, and portal gates remain closed. Nashville EC is portal-confirmed; DARPA was sent before deadline with acknowledgment pending; NASA and Army are sent, and CDC acknowledged receipt. {summary['critical_same_day_infrastructure_action']} Finish the OpenAI Build Week public-demo, provenance, video, and Devpost preview gates before its July 21 close, then stage the hash-verified MissionWeave DSIP package for July 22 noon Eastern. Refresh NSF before resuming its rolling Project Pitch staging, close the declined Cambridge FHWA teaming route without another follow-up, and keep DOJ/BOP partner-only.",
        "",
        "## Control Line",
        "",
        f"- Status: `{payload['status']}`",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Freshness as-of UTC: `{payload['as_of_utc']}`",
        f"- Scan date: `{payload['scan_date']}`",
        f"- Lane count: `{summary['lane_count']}`",
        f"- Curated Navy lanes: `{summary['curated_navy_lane_count']}`",
        f"- Stage-now lanes: `{summary['stage_now_count']}`",
        f"- Sent and verified lanes: `{summary['sent_verified_count']}`",
        f"- Emergency eligibility gates: `{summary['emergency_eligibility_gate_count']}`",
        f"- No-bid or partner-only lanes: `{summary['no_bid_or_partner_only_count']}`",
        f"- Expired without verified send: `{summary['expired_without_verified_send_count']}`",
        f"- Human-gated lanes: `{summary['human_gated_count']}`",
        f"- Freshness-blocked lanes: `{summary['freshness_blocked_lane_count']}`",
        f"- SAM zero-row response is an inconclusive blocker: `{str(summary['sam_zero_row_inconclusive_blocker']).lower()}`",
        f"- Harbor status: `{summary['harbor_status']}`",
        f"- Package status counts: `{json.dumps(summary['package_status_counts'], sort_keys=True)}`",
        f"- Strongest today action: {summary['strongest_today_action']}",
        f"- Critical infrastructure action: {summary['critical_same_day_infrastructure_action']}",
        f"- Closest deadline lane: {summary['closest_deadline_lane']}",
        f"- Closest stage-ready lane: {summary['closest_stage_ready_lane']}",
        f"- Best grants lane: {summary['best_grants_lane']}",
        f"- Best contract lane: {summary['best_contract_lane']}",
        f"- Fastest low-friction lane: {summary['fastest_low_friction_lane']}",
        f"- Final submit without human: `{str(summary['final_submit_allowed_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Pricing without human: `{str(summary['pricing_allowed_without_human']).lower()}`",
        f"- Legal certification without human: `{str(summary['legal_certification_allowed_without_human']).lower()}`",
        f"- Command board SHA-256: `{payload['command_board_sha256']}`",
        "",
        "## Source Freshness",
        "",
        f"- Overall status: `{payload['source_freshness']['overall_status']}`",
        f"- TTL hours: `{payload['source_freshness']['ttl_hours']}`",
        f"- Fail closed: `{str(payload['source_freshness']['submission_decisions_fail_closed']).lower()}`",
        f"- Blockers: `{payload['source_freshness']['blocker_count']}`",
        f"- Boundary: {payload['source_freshness']['claim_boundary']}",
        "",
    ]
    for key, source in payload["source_freshness"]["sources"].items():
        lines.append(
            f"- `{key}`: status=`{source['status']}` freshness=`{source['freshness_status']}` "
            f"source_utc=`{source['source_utc']}` age_hours=`{source['age_hours']}` "
            f"blocking=`{str(source['blocking']).lower()}`"
        )
        if key == "sam_live_discovery":
            lines.append(
                f"  - SAM records: `{source['records']}`; reported diagnostic: "
                f"`{source['reported_status']}`; zero rows: `{str(source['zero_rows']).lower()}`"
            )
    lines.extend(
        [
        "",
        "## Operational Controls",
        "",
        ]
    )
    for key, control in payload["operational_controls"].items():
        lines.extend([f"### {key}", "", f"- Status: `{control['status']}`"])
        if key == "sam_public_key_rotation":
            lines.extend(
                [
                    f"- Deadline local: `{control['deadline_local']}`",
                    f"- Deadline state: `{control['deadline_state']}`",
                    f"- Aliases consistent: `{str(control['aliases_consistent']).lower()}`",
                    f"- Replacement installation detected: `{str(control['replacement_installation_detected']).lower()}`",
                    f"- API probe: `{control['api_probe']}`",
                    f"- Rotation verified: `{str(control['rotation_verified']).lower()}`",
                    f"- Guarded installer: `{control['private_installer']}`",
                ]
            )
        elif key == "patent_deadline_evidence":
            lines.extend(
                [
                    f"- Payment acknowledgement found: `{str(control['payment_acknowledgement_found']).lower()}`",
                    f"- Filing Receipt found: `{str(control['filing_receipt_found']).lower()}`",
                    f"- Official correspondence found: `{str(control['official_correspondence_found']).lower()}`",
                    f"- Official status record found: `{str(control['official_status_record_found']).lower()}`",
                    f"- Required docket categories captured: `{control['captured_required_docket_role_count']}/{control['required_docket_role_count']}`",
                    f"- Complete docket capture: `{str(control['docket_capture_complete']).lower()}`",
                    f"- Missing docket categories: `{', '.join(control['missing_required_docket_roles']) or 'none'}`",
                    f"- U.S. prosecution deadline: `{control['us_prosecution_deadline']}`",
                    f"- Foreign or PCT priority: `{control['foreign_pct_priority']}`",
                    f"- Private capture workflow: `{control['private_capture_workflow']}`",
                ]
            )
        lines.extend(
            [
                f"- Human action required: `{str(control['human_action_required']).lower()}`",
                f"- Browser navigation performed: `{str(control['browser_navigation_performed']).lower()}`",
                f"- Control artifact: `{control['control_artifact']}`",
                "",
            ]
        )
    lines.extend(
        [
        "## Sent And Verified",
        "",
        ]
    )
    for row in payload["sent_verified"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Status: `{row['submission_status']}`",
                f"- Sent UTC: `{row['sent_utc']}`",
                f"- Receipt: `{row['receipt_path']}`",
                f"- Receipt evidence SHA-256: `{row['receipt_attachment_sha256']}`",
                f"- Verification scope: `{row.get('verification_scope') or 'RECEIPT_RECORD_ONLY'}`",
                f"- Claim boundary: {row.get('claim_boundary') or 'The receipt proves only the recorded transmission state.'}",
                "",
            ]
        )

    lines.extend(["## Stage Now", ""])
    for row in payload["stage_now"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Command: `{row['command']}`",
                f"- Deadline UTC: `{row['deadline_utc']}`",
                f"- Official deadline: {row.get('official_deadline_text') or row['deadline_utc']}",
                f"- Official URL: {row['official_url']}",
                "- Package files:",
            ]
        )
        for file in row["package_files"]:
            lines.append(f"  - `{file}`")
        if row.get("action_gate_status"):
            lines.extend(
                [
                    f"- Action gate: `{row['action_gate_status']}`",
                    f"- Action gates passed: `{row['action_gate_passed_private_gate_count']}/{row['action_gate_required_private_gate_count']}`",
                    f"- Private input present: `{str(row['action_gate_private_input_present']).lower()}`",
                    f"- Private values exposed: `{str(row['action_gate_private_values_exposed']).lower()}`",
                    f"- Ready for human final click: `{str(row['action_gate_submission_ready_for_human_click']).lower()}`",
                ]
            )
        if row.get("action_gate_next_founder_step"):
            next_step = row["action_gate_next_founder_step"]
            lines.extend(
                [
                    f"- Next founder action: **{next_step['title']}**",
                    f"- Next-action evidence: {next_step['evidence_required']}",
                    "- Exact founder sequence:",
                ]
            )
            for index, step in enumerate(
                row["action_gate_founder_action_sequence"]["ordered_steps"],
                start=1,
            ):
                lines.append(f"  {index}. {step['title']}")
        lines.append("")

    lines.extend(["## Freshness Blocked", ""])
    for row in payload["freshness_blocked"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Command: `{row['command']}`",
                f"- Prior command: `{row.get('pre_freshness_command')}`",
                f"- Source freshness: `{row['source_freshness_status']}`",
                f"- Deadline actionable: `{str(row['deadline_actionable']).lower()}`",
                f"- Submission ready: `{str(row['submission_ready']).lower()}`",
                "- Blockers:",
            ]
        )
        for blocker in row["freshness_blockers"]:
            lines.append(f"  - `{blocker}`")
        lines.append("")

    lines.extend(["## Emergency Gate", ""])
    for row in payload["emergency_gate"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Command: `{row['command']}`",
                f"- Deadline UTC: `{row['deadline_utc']}`",
                f"- Official URL: {row['official_url']}",
                "- Human gate:",
            ]
        )
        for gate in row["human_gate"]:
            lines.append(f"  - {gate}")
        lines.append("")

    lines.extend(["## No-Bid Or Partner-Only", ""])
    for row in payload["no_bid_or_partner_only"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Command: `{row['command']}`",
                f"- Deadline date: `{row['deadline_date']}`",
                f"- Eligibility: `{row['eligibility_state']}`",
                f"- Fit: `{row['fit_state']}`",
                f"- Package status: `{row['package_status']}`",
                f"- Portal status: `{row['portal_status']}`",
                f"- Official URL: {row['official_url']}",
                "",
            ]
        )

    lines.extend(["## Expired Without Verified Send", ""])
    for row in payload["expired_without_verified_send"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Deadline date: `{row['deadline_date']}`",
                f"- Prior command: `{row['pre_expiry_command']}`",
                f"- Status: `{row['submission_status']}`",
                f"- Official URL: {row['official_url']}",
                "",
            ]
        )

    lines.extend(["## Full Lane Detail", ""])
    for lane in payload["lanes"]:
        lines.extend(
            [
                f"### {lane['rank']}. {lane['opportunity_number']} - {lane['title']}",
                "",
                f"- Source: `{lane['source_system']}`",
                f"- Agency: `{lane['agency']}`",
                f"- Deadline UTC: `{lane['deadline_utc']}`",
                f"- Official deadline: {lane.get('official_deadline_text') or lane['deadline_utc']}",
                f"- Days to close from scan date: `{lane['days_to_close']}`",
                f"- Deadline bucket: `{lane['deadline_bucket']}`",
                f"- Command: `{lane['command']}`",
                f"- Eligibility: `{lane['eligibility_state']}`",
                f"- Fit: `{lane['fit_state']}`",
                f"- Package status: `{lane['package_status']}`",
                f"- Portal status: `{lane['portal_status']}`",
                f"- Readiness: `{lane['readiness_status']}`",
                f"- Submission ready: `{str(lane['submission_ready']).lower()}`",
                f"- Source freshness: `{lane['source_freshness_status']}`",
                f"- Deadline actionable: `{str(lane['deadline_actionable']).lower()}`",
                f"- Route: {lane['submission_route']}",
                f"- Official URL: {lane['official_url']}",
            ]
        )
        if lane.get("secondary_url"):
            lines.append(f"- Secondary URL: {lane['secondary_url']}")
        if lane.get("deadline_date_semantics"):
            lines.append(
                f"- Deadline date semantics: `{lane['deadline_date_semantics']}`"
            )
        if lane.get("freshness_blockers"):
            lines.append("- Freshness blockers:")
            for blocker in lane["freshness_blockers"]:
                lines.append(f"  - `{blocker}`")
        if lane.get("source_authority_boundary"):
            lines.append(
                f"- Source authority boundary: {lane['source_authority_boundary']}"
            )
        if lane.get("claim_boundary"):
            lines.append(f"- Claim boundary: {lane['claim_boundary']}")
        lines.extend(
            [
                f"- Why now: {lane['why_now']}",
                "- Today work:",
            ]
        )
        for item in lane["today_work"]:
            lines.append(f"  - {item}")
        if lane["human_gate"]:
            lines.append("- Human gate:")
            for gate in lane["human_gate"]:
                lines.append(f"  - {gate}")
        if lane["package_files"]:
            lines.append("- Package files:")
            for file in lane["package_files"]:
                lines.append(f"  - `{file}`")
        if lane.get("action_gate_status"):
            lines.extend(
                [
                    f"- Action gate: `{lane['action_gate_status']}`",
                    f"- Action gates passed: `{lane['action_gate_passed_private_gate_count']}/{lane['action_gate_required_private_gate_count']}`",
                    f"- Action gates open: `{lane['action_gate_open_gate_count']}`",
                    f"- Private input present: `{str(lane['action_gate_private_input_present']).lower()}`",
                    f"- Private values exposed: `{str(lane['action_gate_private_values_exposed']).lower()}`",
                    f"- Ready for human final click: `{str(lane['action_gate_submission_ready_for_human_click']).lower()}`",
                ]
            )
        if lane.get("action_gate_next_founder_step"):
            next_step = lane["action_gate_next_founder_step"]
            lines.extend(
                [
                    f"- Next founder action: **{next_step['title']}**",
                    f"- Next-action evidence: {next_step['evidence_required']}",
                    f"- All open gates lifecycle-classified once: `{str(lane['action_gate_all_open_gates_classified_once']).lower()}`",
                    f"- All open gates action-sequenced once: `{str(lane['action_gate_all_open_gates_sequenced_once']).lower()}`",
                    f"- Classification can clear a gate: `{str(lane['action_gate_classification_can_clear_gate']).lower()}`",
                    "- Exact founder sequence:",
                ]
            )
            for index, step in enumerate(
                lane["action_gate_founder_action_sequence"]["ordered_steps"],
                start=1,
            ):
                lines.append(f"  {index}. {step['title']}")
        lines.extend(
            [
                f"- External send without human: `{str(lane['external_send_allowed_without_human']).lower()}`",
                f"- Final submit without human: `{str(lane['final_submit_allowed_without_human']).lower()}`",
                f"- Lane SHA-256: `{lane['lane_sha256']}`",
                "",
            ]
        )

    lines.extend(["## Submission Boundary", ""])
    boundary = payload["submission_boundary"]
    for key, value in boundary.items():
        if isinstance(value, list):
            lines.append(f"- {key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(["", "## Source Ledgers", ""])
    for key, source in payload["source_ledgers"].items():
        lines.append(f"- `{key}`: `{source.get('path')}` present=`{str(source.get('present')).lower()}` sha256=`{source.get('sha256', '')}`")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def output_paths(payload: dict[str, Any]) -> tuple[Path, Path, Path]:
    outputs = payload["outputs"]
    return (
        ROOT / str(outputs["json"]),
        ROOT / str(outputs["dashboard_json"]),
        ROOT / str(outputs["markdown"]),
    )


def serialized_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"


def write_outputs(payload: dict[str, Any], rendered: str) -> None:
    json_path, dashboard_path, markdown_path = output_paths(payload)
    write_text(json_path, serialized_payload(payload))
    write_text(dashboard_path, serialized_payload(payload))
    write_text(markdown_path, rendered)


def output_differences(payload: dict[str, Any], rendered: str) -> list[str]:
    expected_json = serialized_payload(payload)
    differences: list[str] = []
    json_path, dashboard_path, markdown_path = output_paths(payload)
    for path, expected in (
        (json_path, expected_json),
        (dashboard_path, expected_json),
        (markdown_path, rendered),
    ):
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            differences.append(f"stale:{rel(path)}")
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed near-deadline submission command board."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the published outputs do not match a stable rebuild.",
    )
    parser.add_argument("--scan-date", help="Override scan date (YYYY-MM-DD).")
    parser.add_argument("--generated-utc", help="Use a fixed generated timestamp.")
    parser.add_argument("--as-of-utc", help="Use a fixed source-freshness timestamp.")
    args = parser.parse_args()

    if args.check:
        if not OUT_JSON.is_file():
            raise FileNotFoundError(OUT_JSON)
        published = read_json(OUT_JSON)
        payload = build_payload(
            scan_date=date.fromisoformat(str(published["scan_date"])),
            generated_utc=str(published["generated_utc"]),
            as_of_utc=str(published.get("as_of_utc") or published["generated_utc"]),
        )
    else:
        payload = build_payload(
            scan_date=date.fromisoformat(args.scan_date) if args.scan_date else SCAN_DATE,
            generated_utc=args.generated_utc,
            as_of_utc=args.as_of_utc,
        )
    rendered = render_markdown(payload)
    hits = scan_sensitive_text(rendered)
    if hits:
        raise SystemExit(f"Refusing to write sensitive markers: {hits}")

    if args.check:
        differences = output_differences(payload, rendered)
        if differences:
            raise RuntimeError(", ".join(differences))
        print("near-deadline submission command board outputs are current")
        return 0

    write_outputs(payload, rendered)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "stage_now": payload["summary"]["stage_now_count"],
                "emergency_gates": payload["summary"]["emergency_eligibility_gate_count"],
                "freshness_blockers": payload["summary"]["freshness_blocker_count"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
