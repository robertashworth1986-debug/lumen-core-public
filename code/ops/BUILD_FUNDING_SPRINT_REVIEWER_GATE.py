from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

OUT_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "funding_sprint_reviewer_gate.json"
OUT_MD = SPRINT_DIR / "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md"
CONFORMANCE_JSON = OUT_OPS / "submission_conformance_gate_latest.json"
GENERATED_MARKDOWN_OUTPUTS = {OUT_MD.name}

CONFORMANCE_SCHEMA = "lumencore.submission_conformance_gate.v1"
CONFORMANCE_PASS_STATUS = "SUBMISSION_CONFORMANCE_PASS_HUMAN_ACTION_REQUIRED"
LANE_CONFORMANCE_PASS_STATUS = "ARGUMENT_CONFORMANCE_PASS_HUMAN_ACTION_STILL_REQUIRED"
CONFORMANCE_MAX_AGE_HOURS = 24.0
CONFORMANCE_SOURCE_EVIDENCE_KEYS = (
    "registry",
    "traction",
    "near_deadline",
    "public_leads",
    "falcon_gap_map",
    "builder",
)
CLOSED_CONFORMANCE_STATUSES = {"CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"}
EXPIRED_CONFORMANCE_STATUSES = {
    "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED",
}
NO_GO_CONFORMANCE_STATUSES = {
    "TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY",
}
REQUIRED_ARGUMENT_CRITERIA = (
    "official_source_current",
    "mandatory_format_and_route",
    "program_objective_trace",
    "foundational_leap",
    "named_sota_baseline",
    "program_metric_trace",
    "mission_specific_experiment",
    "evidence_applicability",
    "team_compute_execution",
    "risk_transition_and_falsifier",
)

SECRET_PATTERNS = [
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"secret", re.I),
    re.compile(r"token", re.I),
    re.compile(r"password", re.I),
    re.compile(r"private key", re.I),
    re.compile(r"BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY"),
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"refresh_token", re.I),
    re.compile(r"client_secret", re.I),
]
SECURITY_CLEARANCE_CONTEXT = re.compile(
    r"(?:secret[_ -]clear(?:ance|ed)|\bsecret clearance\b|\bcleared personnel\b)",
    re.I,
)

RISKY_CLAIMS = [
    "field validated",
    "realized savings",
    "guaranteed award",
    "guaranteed returns",
    "certified assurance",
    "cmmc certified",
    "nuclear licensing authority",
    "medical efficacy",
    "airworthiness",
    "operational government deployment",
    "live profit",
    "risk-free",
    "autonomous trading system ready",
    "freedom to operate",
    "patented",
]

BOUNDARY_MARKERS = [
    "do not",
    "not ",
    "not a ",
    "not an ",
    "no ",
    "forbidden",
    "without",
    "unless",
    "boundary",
    "blocked",
    "claim boundary",
    "do-not-submit",
    "not authorized",
    "not claimed",
    "forbidden wording",
    "scan",
]

BOUNDARY_SECTION_MARKERS = [
    "do not use",
    "forbidden wording",
    "blocked language",
    "forbidden now",
    "do not claim",
    "not allowed as",
    "blocked:",
    "blocked language unless",
    "not allowed",
    "blocked until",
    "must_stop_before",
]

ACTIVE_LANES = [
    {
        "lane": "DARPA DICE",
        "conformance_lane_id": "darpa_dice_full_submission",
        "deadline": "closed_official_decision",
        "source": "local_official_baa_and_decision_record",
        "artifact": "grant_submissions/DICE_HR001126S0010/LumenCore_DICE_Abstract_FINAL_CANDIDATE.docx",
        "next_gate": "Keep the route closed and reuse only the source-bound postmortem lessons.",
        "claim_boundary": "The package was received but was not selected for a full proposal.",
        "human_gate": "No reply or resubmission under the closed route.",
    },
    {
        "lane": "NASA Data Center Infrastructure RFI",
        "conformance_lane_id": "nasa_data_center_rfi",
        "deadline": "2026-07-17",
        "source": "receipt_backed_historical_send",
        "artifact": "grant_submissions/funding_sprint_20260709/NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md",
        "next_gate": "Monitor for a specific clarification or replacement request and do not resend.",
        "claim_boundary": "No NASA operational claim, energy-savings claim, or infrastructure deployment claim.",
        "human_gate": "Human approval before any requested replacement response.",
    },
    {
        "lane": "CDC AI for Acquisition Support RFI",
        "conformance_lane_id": "cdc_ai_acquisition_rfi",
        "deadline": "sent_receipt_acknowledged",
        "source": "receipt_backed_historical_send",
        "artifact": "grant_submissions/funding_sprint_20260709/CDC_AI_ACQUISITION_RFI_ARTIFACT_MANIFEST_2026-07-15.json",
        "next_gate": "Monitor for a clarification, replacement request, or scheduling message and do not resend.",
        "claim_boundary": "Receipt acknowledgment is not an award, endorsement, selection, or technical validation.",
        "human_gate": "Human approval before any requested replacement response.",
    },
    {
        "lane": "DLA MissionWeave DSIP SBIR",
        "conformance_lane_id": "dla_missionweave_sbir",
        "deadline": "2026-07-22T16:00:00Z",
        "source": "expired_official_topic_record",
        "artifact": "grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json",
        "next_gate": "Archive as expired without verified submission; do not revive the packet against a new topic without a new audit.",
        "claim_boundary": "No DSIP submission, receipt, DLA integration, certified readiness, or award is established.",
        "human_gate": "No submission action remains under the expired route.",
    },
    {
        "lane": "FHWA TSMO Data Initiative",
        "conformance_lane_id": "fhwa_tsmo_data_initiative",
        "deadline": "closed_partner_route",
        "source": "closed_cambridge_partner_route",
        "artifact": "grant_submissions/funding_sprint_20260709/FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
        "next_gate": "Do not revive the Cambridge route; reopen only through a different qualified organization with a written role.",
        "claim_boundary": "No FHWA field validation, safety benefit, or traffic operations deployment claim.",
        "human_gate": "Human approval before any new partner outreach or submission work.",
    },
    {
        "lane": "NSF SBIR/STTR Project Pitch",
        "conformance_lane_id": "nsf_project_pitch",
        "deadline": "rolling_invitation_gate",
        "source": "current_public_official_source_audit",
        "artifact": "grant_submissions/NSF_Project_Pitch/PROJECT_PITCH_PORTAL_FIELDS_2026-07-29.md",
        "next_gate": "Verify applicant facts, authenticated prompts, title limit, topic selection, and active portal state before final review.",
        "claim_boundary": "No current eligibility, invitation, submission availability, selection, or award is represented.",
        "human_gate": "Human approval before Project Pitch submit.",
    },
    {
        "lane": "ERDC Sovereign Defense Cloud CSO",
        "conformance_lane_id": "erdc_sovereign_cloud_cso",
        "deadline": "2026-08-07T21:00:00Z_local_record_recheck_required",
        "source": "current_official_cso_and_july_20_faq",
        "artifact": "grant_submissions/funding_sprint_20260709/ERDC_SDC_SOLUTION_BRIEF_COMPLIANCE_GATE_2026-07-29.json",
        "next_gate": "Approve the private Phase II-only ROM, verify SAM and contact facts, build and validate the private final PDF, and stop at the complete portal preview.",
        "claim_boundary": "Current-source public-draft conformance does not establish applicant eligibility, private-final readiness, technical merit, selection, funding, or award.",
        "human_gate": "Human approval before pricing, representations, certification, upload, or final submit.",
    },
    {
        "lane": "DARPA FALCON Direct to Phase II",
        "conformance_lane_id": "darpa_falcon_dpa26bz04_dv016",
        "deadline": "2026-08-19T16:00:00Z",
        "source": "local_official_faq_and_baa_attachments",
        "artifact": "grant_submissions/DPA26BZ04_DV016_FALCON/DPA26BZ04_DV016_GO_NO_GO_AND_DP2_GAP_MAP_2026-07-15.md",
        "next_gate": "Continue only the frozen evidence sprint until every technical, DP2, IP, execution, and independent-review gate closes.",
        "claim_boundary": "No hybrid superiority, external validation, agency approval, scholarly impact, enterprise scale, or DP2 eligibility is established.",
        "human_gate": "Human approval before any proposal assembly, certification, upload, or final submit.",
    },
    {
        "lane": "Launch Tennessee 3686 Pitch Competition",
        "conformance_lane_id": "launchtn_3686_pitch_2026",
        "deadline": "2026-08-14T04:59:00Z",
        "source": "dated_first_party_application_observation",
        "artifact": "grant_submissions/LAUNCHTN_3686_PITCH_2026/LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-29.md",
        "next_gate": "Recheck the first-party source, resolve applicant facts and terms, and complete the source-bound pitch review.",
        "claim_boundary": "No eligibility, submission, receipt, finalist status, prize, funding, selection, investment, or award is established.",
        "human_gate": "Human approval before attestations, disclosure choices, terms acceptance, or final submit.",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def integer_or_zero(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def parse_utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def repo_receipt_path(raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    try:
        resolved = candidate.resolve()
        resolved.relative_to(ROOT.resolve())
    except (OSError, ValueError):
        return None
    return resolved


def receipt_matches_current_file(receipt: Any) -> bool:
    if not isinstance(receipt, dict) or receipt.get("present") is not True:
        return False
    path = repo_receipt_path(receipt.get("path"))
    expected_sha256 = str(receipt.get("sha256") or "")
    if path is None or not path.is_file() or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        return False
    if sha256_file(path) != expected_sha256:
        return False
    expected_bytes = receipt.get("bytes")
    return expected_bytes is None or expected_bytes == path.stat().st_size


def hash_field_is_valid(payload: dict[str, Any], field: str) -> bool:
    supplied = str(payload.get(field) or "")
    if re.fullmatch(r"[0-9a-f]{64}", supplied) is None:
        return False
    seed = {key: value for key, value in payload.items() if key != field}
    return canonical_sha256(seed) == supplied


def load_submission_conformance(
    supplied_payload: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source = {
        "path": rel(CONFORMANCE_JSON),
        "present": False,
        "bytes": 0,
        "sha256": "",
        "in_memory_override": supplied_payload is not None,
    }
    errors: list[str] = []
    payload: dict[str, Any]
    if supplied_payload is not None:
        payload = supplied_payload
        source["present"] = True
    elif not CONFORMANCE_JSON.is_file():
        return {}, {
            **source,
            "document_valid": False,
            "validation_errors": ["submission_conformance_gate_missing"],
            "schema": None,
            "status": None,
            "gate_sha256_valid": False,
        }
    else:
        source.update(
            {
                "present": True,
                "bytes": CONFORMANCE_JSON.stat().st_size,
                "sha256": sha256_file(CONFORMANCE_JSON),
            }
        )
        try:
            loaded = json.loads(CONFORMANCE_JSON.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {}, {
                **source,
                "document_valid": False,
                "validation_errors": ["submission_conformance_gate_unreadable"],
                "schema": None,
                "status": None,
                "gate_sha256_valid": False,
            }
        if not isinstance(loaded, dict):
            return {}, {
                **source,
                "document_valid": False,
                "validation_errors": ["submission_conformance_gate_not_an_object"],
                "schema": None,
                "status": None,
                "gate_sha256_valid": False,
            }
        payload = loaded

    if payload.get("schema") != CONFORMANCE_SCHEMA:
        errors.append("submission_conformance_schema_mismatch")
    if payload.get("required_criteria") != list(REQUIRED_ARGUMENT_CRITERIA):
        errors.append("submission_conformance_required_criteria_mismatch")
    gate_hash_valid = hash_field_is_valid(payload, "gate_sha256")
    if not gate_hash_valid:
        errors.append("submission_conformance_gate_sha256_invalid")

    now = datetime.now(timezone.utc)
    for field in ("as_of_utc", "registry_as_of_utc"):
        observed = parse_utc(payload.get(field))
        if observed is None:
            errors.append(f"submission_conformance_{field}_invalid")
            continue
        age_hours = (now - observed).total_seconds() / 3600.0
        if age_hours < -(5.0 / 60.0):
            errors.append(f"submission_conformance_{field}_future")
        elif age_hours > CONFORMANCE_MAX_AGE_HOURS:
            errors.append(f"submission_conformance_{field}_stale")

    source_evidence = payload.get("source_evidence")
    if not isinstance(source_evidence, dict):
        errors.append("submission_conformance_source_evidence_missing")
    else:
        for key in CONFORMANCE_SOURCE_EVIDENCE_KEYS:
            if not receipt_matches_current_file(source_evidence.get(key)):
                errors.append(
                    f"submission_conformance_source_evidence_not_current:{key}"
                )

    lanes = payload.get("lanes")
    if not isinstance(lanes, list):
        errors.append("submission_conformance_lanes_missing")
        lanes = []
    by_id: dict[str, Any] = {}
    for row in lanes:
        if not isinstance(row, dict):
            errors.append("submission_conformance_lane_not_an_object")
            continue
        lane_id = row.get("lane_id")
        if not isinstance(lane_id, str) or not lane_id:
            errors.append("submission_conformance_lane_id_missing")
            continue
        if lane_id in by_id:
            errors.append(f"submission_conformance_duplicate_lane:{lane_id}")
            continue
        by_id[lane_id] = row

    return by_id, {
        **source,
        "document_valid": not errors,
        "validation_errors": errors,
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "gate_sha256_valid": gate_hash_valid,
        "all_current_lanes_covered": bool(
            isinstance(payload.get("summary"), dict)
            and payload["summary"].get("all_current_lanes_covered") is True
        ),
        "active_submission_candidate_count": sum(
            1
            for row in by_id.values()
            if row.get("submission_candidate_active") is True
            and row.get("technical_argument_required") is True
        ),
    }


def source_bound_argument_blockers(
    row: dict[str, Any],
    expected_candidate_path: str,
) -> list[str]:
    blockers: list[str] = []
    if row.get("submission_candidate_active") is not True:
        blockers.append("submission_candidate_not_active")
    if row.get("technical_argument_required") is not True:
        blockers.append("technical_argument_not_required")
    if row.get("status") != LANE_CONFORMANCE_PASS_STATUS:
        blockers.append("lane_conformance_status_not_pass")
    if row.get("argument_conformance_pass") is not True:
        blockers.append("argument_conformance_not_declared_pass")
    if not hash_field_is_valid(row, "lane_gate_sha256"):
        blockers.append("lane_conformance_sha256_invalid")

    criteria = row.get("criteria")
    by_id: dict[str, Any] = {}
    duplicate_ids: set[str] = set()
    if isinstance(criteria, list):
        for criterion in criteria:
            if not isinstance(criterion, dict):
                continue
            criterion_id = criterion.get("criterion_id")
            if isinstance(criterion_id, str):
                if criterion_id in by_id:
                    duplicate_ids.add(criterion_id)
                by_id[criterion_id] = criterion
    else:
        blockers.append("argument_criteria_missing")

    if duplicate_ids:
        blockers.append("duplicate_argument_criteria")
    for criterion_id in REQUIRED_ARGUMENT_CRITERIA:
        criterion = by_id.get(criterion_id)
        if criterion is None:
            blockers.append(f"criterion_missing:{criterion_id}")
            continue
        if criterion.get("state") != "PASS" or criterion.get("passed") is not True:
            blockers.append(f"criterion_not_pass:{criterion_id}")
        source_refs = criterion.get("source_refs")
        sources_current = (
            criterion.get("source_refs_all_present") is True
            and isinstance(source_refs, list)
            and bool(source_refs)
            and all(receipt_matches_current_file(ref) for ref in source_refs)
        )
        if not sources_current:
            blockers.append(f"criterion_sources_not_current:{criterion_id}")

    if row.get("criterion_count") != len(REQUIRED_ARGUMENT_CRITERIA):
        blockers.append("criterion_count_mismatch")
    if row.get("criterion_pass_count") != len(REQUIRED_ARGUMENT_CRITERIA):
        blockers.append("criterion_pass_count_incomplete")
    if any(
        row.get(field) != 0
        for field in (
            "criterion_partial_count",
            "criterion_fail_count",
            "criterion_unassessed_count",
        )
    ):
        blockers.append("nonpassing_criterion_count_present")

    candidate = row.get("candidate_artifact")
    if not receipt_matches_current_file(candidate):
        blockers.append("candidate_artifact_not_current")
    elif candidate.get("path") != expected_candidate_path:
        blockers.append("reviewer_card_artifact_not_conformance_candidate")
    if not receipt_matches_current_file(row.get("official_source")):
        blockers.append("official_source_not_current")

    red_team = row.get("independent_red_team_receipt")
    if not receipt_matches_current_file(red_team):
        blockers.append("independent_red_team_receipt_not_current")
    if not isinstance(red_team, dict) or red_team.get("passes") is not True:
        blockers.append("independent_red_team_not_passed")
    if isinstance(red_team, dict) and red_team.get("reviewer_relation") == "PRIMARY_DRAFTER_SELF_ATTESTED":
        blockers.append("independent_red_team_self_attested")

    if row.get("final_submission_allowed_without_human") is not False:
        blockers.append("human_submission_boundary_missing")
    if row.get("external_send_allowed_without_human") is not False:
        blockers.append("human_send_boundary_missing")
    return blockers


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def markdown_files() -> list[Path]:
    if not SPRINT_DIR.exists():
        return []
    return sorted(
        path
        for path in SPRINT_DIR.glob("*.md")
        if path.is_file() and path.name not in GENERATED_MARKDOWN_OUTPUTS
    )


def line_is_boundary(line: str) -> bool:
    lowered = line.lower()
    structured_false = re.search(r":\s*`?false`?\s*$", lowered) is not None
    structured_negative_true = re.search(r"_[a-z0-9]*not_[a-z0-9_]+:\s*`?true`?\s*$", lowered) is not None
    structured_not_established = (
        re.search(r"`?not_established`?\s*(?:-|:)", lowered) is not None
    )
    return (
        structured_false
        or structured_negative_true
        or structured_not_established
        or any(marker in lowered for marker in BOUNDARY_MARKERS)
    )


def line_opens_boundary_section(line: str) -> bool:
    lowered = line.strip().lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in BOUNDARY_SECTION_MARKERS)


def line_opens_nonboundary_section(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("#") and not line_opens_boundary_section(stripped)


def scan_files(files: list[Path]) -> dict[str, Any]:
    secret_hits = []
    risky_hits = []
    boundary_hits = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(errors="ignore").splitlines()
        boundary_section = False
        for lineno, line in enumerate(lines, start=1):
            if line_opens_boundary_section(line):
                boundary_section = True
            elif line_opens_nonboundary_section(line):
                boundary_section = False
            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    hit = {"file": rel(path), "line": lineno, "pattern": pattern.pattern, "text": line.strip()}
                    if SECURITY_CLEARANCE_CONTEXT.search(line):
                        boundary_hits.append(
                            hit
                            | {
                                "classification": (
                                    "noncredential_security_clearance_requirement"
                                )
                            }
                        )
                    elif line_is_boundary(line) or boundary_section:
                        boundary_hits.append(hit | {"classification": "boundary_language"})
                    else:
                        secret_hits.append(hit | {"classification": "unsafe_secret_pattern"})
            lowered = line.lower()
            for phrase in RISKY_CLAIMS:
                if phrase in lowered:
                    hit = {"file": rel(path), "line": lineno, "phrase": phrase, "text": line.strip()}
                    if line_is_boundary(line) or boundary_section:
                        boundary_hits.append(hit | {"classification": "blocked_or_boundary_claim_language"})
                    else:
                        risky_hits.append(hit | {"classification": "unsafe_claim_language"})
    return {
        "unsafe_secret_hits": secret_hits,
        "unsafe_claim_hits": risky_hits,
        "boundary_hits": boundary_hits,
        "unsafe_secret_count": len(secret_hits),
        "unsafe_claim_count": len(risky_hits),
        "boundary_hit_count": len(boundary_hits),
    }


def file_manifest(files: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in files:
        rows.append(
            {
                "path": rel(path),
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "classification": "public_safe_markdown_review_required",
            }
        )
    return rows


def proof_cards(
    manifest: list[dict[str, Any]],
    conformance_by_id: dict[str, Any],
    conformance_document_valid: bool,
) -> list[dict[str, Any]]:
    del manifest
    cards = []
    for lane in ACTIVE_LANES:
        artifact_path = repo_receipt_path(lane["artifact"])
        artifact_present = bool(artifact_path and artifact_path.is_file())
        artifact = (
            {
                "path": lane["artifact"],
                "bytes": artifact_path.stat().st_size,
                "sha256": sha256_file(artifact_path),
            }
            if artifact_present and artifact_path is not None
            else None
        )
        conformance_lane_id = lane["conformance_lane_id"]
        conformance = conformance_by_id.get(conformance_lane_id)
        conformance_status = (
            str(conformance.get("status"))
            if isinstance(conformance, dict) and conformance.get("status") is not None
            else None
        )
        expected_candidate_path = lane["artifact"]
        blockers: list[str]
        source_bound_pass = False

        if conformance is None:
            reviewer_posture = "blocked_missing_conformance_mapping"
            blockers = ["missing_lane_specific_conformance_mapping"]
        elif not conformance_document_valid:
            reviewer_posture = "blocked_invalid_conformance_document"
            blockers = ["submission_conformance_document_invalid"]
        elif conformance_status in CLOSED_CONFORMANCE_STATUSES:
            reviewer_posture = "closed_official_decision_postmortem_only"
            blockers = ["official_decision_closed_route"]
        elif conformance_status in EXPIRED_CONFORMANCE_STATUSES:
            reviewer_posture = "expired_no_verified_submission_reuse_blocked"
            blockers = ["expired_without_verified_submission"]
        elif conformance_status in NO_GO_CONFORMANCE_STATUSES:
            reviewer_posture = "technical_no_go_evidence_sprint_only"
            blockers = ["technical_no_go"]
        elif (
            conformance.get("submission_candidate_active") is True
            and conformance.get("technical_argument_required") is True
        ):
            blockers = source_bound_argument_blockers(
                conformance,
                expected_candidate_path,
            )
            source_bound_pass = not blockers
            reviewer_posture = (
                "argument_conformance_pass_human_action_still_required"
                if source_bound_pass
                else "blocked_source_bound_argument_conformance"
            )
        elif conformance_status == "MONITOR_ONLY_NO_DUPLICATE_SUBMISSION":
            reviewer_posture = "monitor_only_no_duplicate_submission"
            blockers = ["lane_is_monitor_only"]
        elif conformance_status == "NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE":
            reviewer_posture = "not_a_current_submission_route"
            blockers = ["lane_is_not_a_submission_route"]
        else:
            reviewer_posture = "blocked_before_active_submission_candidate"
            blockers = ["lane_not_an_active_conforming_submission_candidate"]

        reviewer_ready = artifact_present and source_bound_pass
        if not artifact_present:
            blockers = [*blockers, "reviewer_card_artifact_missing"]
        card_seed = {
            "lane": lane["lane"],
            "conformance_lane_id": conformance_lane_id,
            "deadline": lane["deadline"],
            "source": lane["source"],
            "artifact": lane["artifact"],
            "artifact_present": artifact_present,
            "artifact_sha256": artifact["sha256"] if artifact else "",
            "next_gate": lane["next_gate"],
            "claim_boundary": lane["claim_boundary"],
            "human_gate": lane["human_gate"],
            "conformance_mapping_found": conformance is not None,
            "conformance_status": conformance_status,
            "submission_candidate_active": bool(
                isinstance(conformance, dict)
                and conformance.get("submission_candidate_active") is True
            ),
            "technical_argument_required": bool(
                isinstance(conformance, dict)
                and conformance.get("technical_argument_required") is True
            ),
            "argument_conformance_declared_pass": bool(
                isinstance(conformance, dict)
                and conformance.get("argument_conformance_pass") is True
            ),
            "source_bound_argument_conformance_pass": source_bound_pass,
            "reviewer_ready": reviewer_ready,
            "reviewer_posture": reviewer_posture,
            "readiness_blockers": blockers,
            "criterion_pass_count": (
                integer_or_zero(conformance.get("criterion_pass_count"))
                if isinstance(conformance, dict)
                else 0
            ),
            "criterion_count": (
                integer_or_zero(conformance.get("criterion_count"))
                if isinstance(conformance, dict)
                else 0
            ),
        }
        card_seed["card_sha256"] = canonical_sha256(card_seed)
        cards.append(card_seed)
    return cards


def build_payload(
    conformance_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    files = markdown_files()
    manifest = file_manifest(files)
    scans = scan_files(files)
    conformance_by_id, conformance_meta = load_submission_conformance(
        conformance_payload
    )
    cards = proof_cards(
        manifest,
        conformance_by_id,
        bool(conformance_meta["document_valid"]),
    )
    all_cards_present = all(card["artifact_present"] for card in cards)
    packaging_checks_clear = (
        bool(files)
        and all_cards_present
        and scans["unsafe_secret_count"] == 0
        and scans["unsafe_claim_count"] == 0
    )
    card_lane_ids = {card["conformance_lane_id"] for card in cards}
    missing_mapping_lane_ids = sorted(
        card["conformance_lane_id"]
        for card in cards
        if not card["conformance_mapping_found"]
    )
    active_conformance_lane_ids = {
        lane_id
        for lane_id, row in conformance_by_id.items()
        if row.get("submission_candidate_active") is True
        and row.get("technical_argument_required") is True
    }
    unrepresented_active_lane_ids = sorted(
        active_conformance_lane_ids - card_lane_ids
    )
    active_cards = [
        card
        for card in cards
        if card["submission_candidate_active"]
        and card["technical_argument_required"]
    ]
    active_argument_pass_count = sum(
        1 for card in active_cards if card["reviewer_ready"]
    )
    conformance_coverage_clear = (
        conformance_meta["document_valid"]
        and conformance_meta["all_current_lanes_covered"]
        and not missing_mapping_lane_ids
        and not unrepresented_active_lane_ids
    )
    conformance_global_pass = (
        conformance_meta["status"] == CONFORMANCE_PASS_STATUS
    )
    active_argument_checks_clear = (
        bool(active_cards)
        and active_argument_pass_count == len(active_cards)
    )
    gate_clear = (
        packaging_checks_clear
        and conformance_coverage_clear
        and conformance_global_pass
        and active_argument_checks_clear
    )
    if not packaging_checks_clear:
        status = "REVIEWER_GATE_BLOCKED_PACKAGING_OR_LANGUAGE"
    elif not conformance_meta["document_valid"]:
        status = "REVIEWER_GATE_BLOCKED_INVALID_SUBMISSION_CONFORMANCE"
    elif not conformance_coverage_clear:
        status = "REVIEWER_GATE_BLOCKED_CONFORMANCE_COVERAGE"
    elif not active_cards:
        status = "REVIEWER_GATE_BLOCKED_NO_ACTIVE_TECHNICAL_CANDIDATE"
    elif not active_argument_checks_clear or not conformance_global_pass:
        status = "REVIEWER_GATE_BLOCKED_SOURCE_BOUND_ARGUMENT_CONFORMANCE"
    else:
        status = "REVIEWER_GATE_ARGUMENT_CLEAR_HUMAN_SUBMISSION_REQUIRED"

    payload = {
        "generated_utc": now_utc(),
        "schema": "funding_sprint_reviewer_gate_v2",
        "sprint_dir": rel(SPRINT_DIR),
        "reviewer_gate_clear": gate_clear,
        "status": status,
        "summary": {
            "markdown_file_count": len(files),
            "proof_card_count": len(cards),
            "all_cards_present": all_cards_present,
            "packaging_checks_clear": packaging_checks_clear,
            "unsafe_secret_count": scans["unsafe_secret_count"],
            "unsafe_claim_count": scans["unsafe_claim_count"],
            "boundary_hit_count": scans["boundary_hit_count"],
            "conformance_document_valid": conformance_meta["document_valid"],
            "conformance_global_status": conformance_meta["status"],
            "conformance_global_pass": conformance_global_pass,
            "conformance_coverage_clear": conformance_coverage_clear,
            "missing_conformance_mapping_count": len(missing_mapping_lane_ids),
            "unrepresented_active_conformance_lane_count": len(
                unrepresented_active_lane_ids
            ),
            "active_technical_candidate_count": len(active_cards),
            "active_argument_pass_count": active_argument_pass_count,
            "active_argument_blocked_count": (
                len(active_cards) - active_argument_pass_count
            ),
            "closed_route_count": sum(
                1
                for card in cards
                if card["conformance_status"] in CLOSED_CONFORMANCE_STATUSES
            ),
            "expired_route_count": sum(
                1
                for card in cards
                if card["conformance_status"] in EXPIRED_CONFORMANCE_STATUSES
            ),
            "technical_no_go_count": sum(
                1
                for card in cards
                if card["conformance_status"] in NO_GO_CONFORMANCE_STATUSES
            ),
            "autonomous_external_action_allowed": False,
            "live_trading_allowed": False,
            "final_submission_allowed_without_human": False,
        },
        "submission_conformance": {
            **conformance_meta,
            "missing_mapping_lane_ids": missing_mapping_lane_ids,
            "unrepresented_active_lane_ids": unrepresented_active_lane_ids,
            "required_argument_criteria": list(REQUIRED_ARGUMENT_CRITERIA),
            "stop_rule": (
                "Packaging, hashes, rendering, safe wording, and portal facts never "
                "establish reviewer readiness. Every active technical packet must match "
                "a current candidate artifact and pass all source-bound criteria plus a "
                "separate red-team receipt."
            ),
        },
        "claim_policy": {
            "allowed": [
                "proof-to-pilot AI infrastructure validation",
                "source provenance",
                "baseline-vs-candidate replay",
                "hash-verified public proof-feed deployment",
                "29-source inventory with 25 measured providers",
                "human-gated agency submission",
            ],
            "blocked": RISKY_CLAIMS,
        },
        "manifest": manifest,
        "proof_cards": cards,
        "scan": scans,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["gate_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Funding Sprint Reviewer Gate - 2026-07-09",
        "",
        "Purpose: machine-check the active funding sprint before agency, investor, or partner use.",
        "",
        (
            "Packaging checks and language scans are supporting controls only. They never "
            "establish reviewer readiness. An active technical packet must independently "
            "pass the source-bound submission conformance gate for the exact candidate "
            "artifact before this gate can clear."
        ),
        "",
        "## Gate Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Reviewer gate clear: `{str(payload['reviewer_gate_clear']).lower()}`",
        f"- Packaging checks clear: `{str(summary['packaging_checks_clear']).lower()}`",
        f"- Markdown files scanned: `{summary['markdown_file_count']}`",
        f"- Proof cards: `{summary['proof_card_count']}`",
        f"- Unsafe secret hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- Boundary/blocked-language hits: `{summary['boundary_hit_count']}`",
        f"- Submission conformance document valid: `{str(summary['conformance_document_valid']).lower()}`",
        f"- Submission conformance status: `{summary['conformance_global_status']}`",
        f"- Conformance coverage clear: `{str(summary['conformance_coverage_clear']).lower()}`",
        f"- Missing lane mappings: `{summary['missing_conformance_mapping_count']}`",
        f"- Unrepresented active conformance lanes: `{summary['unrepresented_active_conformance_lane_count']}`",
        f"- Active technical candidates: `{summary['active_technical_candidate_count']}`",
        f"- Active argument passes: `{summary['active_argument_pass_count']}`",
        f"- Active argument blocks: `{summary['active_argument_blocked_count']}`",
        f"- Closed routes: `{summary['closed_route_count']}`",
        f"- Expired routes without verified submission: `{summary['expired_route_count']}`",
        f"- Technical no-go lanes: `{summary['technical_no_go_count']}`",
        f"- Autonomous external action allowed: `{str(summary['autonomous_external_action_allowed']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Final submission without human allowed: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Gate SHA-256: `{payload['gate_sha256']}`",
        "",
        "## Submission Conformance Control",
        "",
        payload["submission_conformance"]["stop_rule"],
        "",
        f"- Source: `{payload['submission_conformance']['path']}`",
        f"- Source present: `{str(payload['submission_conformance']['present']).lower()}`",
        f"- Source SHA-256: `{payload['submission_conformance']['sha256']}`",
        f"- Source gate SHA-256 valid: `{str(payload['submission_conformance']['gate_sha256_valid']).lower()}`",
        (
            "- Validation errors: "
            + (
                ", ".join(
                    f"`{item}`"
                    for item in payload["submission_conformance"]["validation_errors"]
                )
                if payload["submission_conformance"]["validation_errors"]
                else "`none`"
            )
        ),
        "",
        "## Reviewer Proof Cards",
        "",
    ]
    for card in payload["proof_cards"]:
        lines.extend(
            [
                f"### {card['lane']}",
                "",
                f"- Conformance lane ID: `{card['conformance_lane_id']}`",
                f"- Deadline: `{card['deadline']}`",
                f"- Source: {card['source']}",
                f"- Artifact: `{card['artifact']}`",
                f"- Artifact present: `{str(card['artifact_present']).lower()}`",
                f"- Artifact SHA-256: `{card['artifact_sha256']}`",
                f"- Conformance mapping found: `{str(card['conformance_mapping_found']).lower()}`",
                f"- Conformance status: `{card['conformance_status']}`",
                f"- Active technical candidate: `{str(card['submission_candidate_active'] and card['technical_argument_required']).lower()}`",
                f"- Declared argument pass: `{str(card['argument_conformance_declared_pass']).lower()}`",
                f"- Source-bound argument pass: `{str(card['source_bound_argument_conformance_pass']).lower()}`",
                f"- Reviewer ready: `{str(card['reviewer_ready']).lower()}`",
                f"- Reviewer posture: `{card['reviewer_posture']}`",
                (
                    "- Readiness blockers: "
                    + (
                        ", ".join(f"`{item}`" for item in card["readiness_blockers"])
                        if card["readiness_blockers"]
                        else "`none`"
                    )
                ),
                f"- Argument criteria passed: `{card['criterion_pass_count']}/{card['criterion_count']}`",
                f"- Next gate: {card['next_gate']}",
                f"- Claim boundary: {card['claim_boundary']}",
                f"- Human gate: {card['human_gate']}",
                f"- Card SHA-256: `{card['card_sha256']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Claim Policy",
            "",
            "Allowed language:",
            "",
        ]
    )
    for item in payload["claim_policy"]["allowed"]:
        lines.append(f"- {item}")
    lines.extend(["", "Blocked language unless explicitly negated or bounded:", ""])
    for item in payload["claim_policy"]["blocked"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Scan Notes",
            "",
            "Boundary hits are expected when a file says not to use a risky phrase. They remain listed in JSON for audit, but they do not block the gate.",
            "",
            (
                "Any unsafe secret or claim hit blocks agency use until removed or "
                "rewritten as explicit boundary language. A clean scan does not cure "
                "missing objectives, novelty, named baselines, metrics, experiments, "
                "evidence applicability, execution evidence, or independent red-team review."
            ),
            "",
            "## Human Submission Rule",
            "",
            "No portal submission, email send, certification, affirmation, pricing, Firm PIN entry, IP filing, live trading, or capital movement is authorized by this gate.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(json.dumps({"status": payload["status"], "json": rel(OUT_JSON), "markdown": rel(OUT_MD)}, indent=2))


if __name__ == "__main__":
    main()
