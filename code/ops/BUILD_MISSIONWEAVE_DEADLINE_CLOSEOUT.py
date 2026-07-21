from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave"
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"

GATE_JSON = PACKAGE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
FOLLOWUP_QUEUE_JSON = (
    SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
)
COST_INPUTS = PACKAGE_DIR / "MISSIONWEAVE_DSIP_VOLUME3_COST_INPUTS_2026-07-16.md"
VOLUME5_WORKSHEET = PACKAGE_DIR / "MISSIONWEAVE_DSIP_VOLUME5_WORKSHEET_2026-07-16.md"
PORTAL_CHECKLIST = PACKAGE_DIR / "MISSIONWEAVE_DSIP_PORTAL_CHECKLIST_2026-07-17.md"
LIVE_DSIP_RECEIPT = (
    PACKAGE_DIR / "MISSIONWEAVE_DSIP_LIVE_STATUS_RECEIPT_2026-07-20.json"
)
SAM_REPS_RECEIPT = (
    PACKAGE_DIR / "MISSIONWEAVE_SAM_CURRENT_REPS_CERTS_RECEIPT_2026-07-20.json"
)
OUT_JSON = PACKAGE_DIR / "MISSIONWEAVE_DEADLINE_CLOSEOUT_2026-07-20.json"
OUT_MD = OUT_JSON.with_suffix(".md")
ACTION_GATE_BUILDER = ROOT / "code" / "ops" / "BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py"
PRIVATE_ACTION_INPUT = (
    PACKAGE_DIR / "private" / "MISSIONWEAVE_DSIP_ACTION.private.json"
)

SCHEMA = "lumencore.missionweave_deadline_closeout.v1"
GATE_SCHEMA = "lumencore.missionweave_dsip_action_gate.v1"
QUEUE_SCHEMA = "lumencore.outreach_followup_action_queue.v1"
LIVE_DSIP_RECEIPT_SCHEMA = "lumencore.missionweave_dsip_live_status_receipt.v1"
SAM_REPS_RECEIPT_SCHEMA = (
    "lumencore.missionweave_sam_current_reps_certs_receipt.v1"
)
TOPIC = "DLA26BZ03-NV011"
MISSIONWEAVE_LANE_ID = "missionweave_dsip_proposal"
EXPECTED_DEADLINE_UTC = "2026-07-22T16:00:00Z"
PORTAL_RECEIPT_MAX_AGE = timedelta(hours=6)

SUPPLEMENTAL_REVIEW_GAPS: tuple[dict[str, str], ...] = (
    {
        "id": "HUMAN_SUBJECTS_APPLICABILITY",
        "actor": "QUALIFIED_HUMAN_SUBJECTS_REVIEWER",
        "action": (
            "Determine whether Component feedback, process discovery, or personnel-related "
            "data activities constitute human-subjects research, or document a scope boundary "
            "that excludes those activities."
        ),
    },
    {
        "id": "ANIMAL_USE_APPLICABILITY",
        "actor": "FOUNDER_AND_QUALIFIED_COMPLIANCE_REVIEWER",
        "action": (
            "Confirm from the exact final scope whether animal use is inapplicable and make "
            "the proposal and portal answers agree."
        ),
    },
    {
        "id": "RECOMBINANT_DNA_APPLICABILITY",
        "actor": "FOUNDER_AND_QUALIFIED_COMPLIANCE_REVIEWER",
        "action": (
            "Confirm from the exact final scope whether recombinant-DNA work is inapplicable "
            "and make the proposal and portal answers agree."
        ),
    },
    {
        "id": "FASCSA_REASONABLE_INQUIRY",
        "actor": "CORPORATE_OFFICIAL_AND_SUPPLY_CHAIN_REVIEWER",
        "action": (
            "Perform and document the proposal-specific FASCSA reasonable inquiry before "
            "making the required representation."
        ),
    },
    {
        "id": "SUPPLY_CHAIN_CLAUSE_APPLICABILITY",
        "actor": "CORPORATE_OFFICIAL_AND_SUPPLY_CHAIN_REVIEWER",
        "action": (
            "Review the applicable covered-article and supply-chain clauses against the "
            "actual hardware, software, cloud, and service inputs."
        ),
    },
)


ACTION_DEFINITIONS: dict[str, dict[str, Any]] = {
    "DD2345_OR_JCP_APPLICATION_EVIDENCE": {
        "order": 10,
        "actor": "AUTHENTICATED_JCP_USER_AND_CORPORATE_OFFICIAL",
        "capture_section": "eligibility_and_compliance",
        "action": (
            "Retrieve the current certified DD Form 2345 or the official JCP "
            "application-submission evidence allowed by the live instructions."
        ),
        "evidence_required": (
            "A private portal-derived PDF and matching private receipt that satisfy "
            "the existing JCP evidence protocol; a checkbox or registration screen is "
            "not sufficient."
        ),
    },
    "DSIP_FIRM_PIN_AVAILABILITY": {
        "order": 20,
        "actor": "AUTHENTICATED_DSIP_USER",
        "capture_section": "identity",
        "action": (
            "Verify that the linked organization exposes a usable Firm PIN inside DSIP."
        ),
        "evidence_required": (
            "Record only the yes/no availability state in the ignored private input; "
            "never store or publish the PIN value."
        ),
    },
    "SAM_REPRESENTATIONS_CURRENT": {
        "order": 30,
        "actor": "AUTHENTICATED_SAM_USER_AND_CORPORATE_OFFICIAL",
        "capture_section": "identity",
        "action": (
            "Review the current SAM representations and certifications for the exact "
            "registered entity used by this proposal."
        ),
        "evidence_required": (
            "Current authenticated portal confirmation or a current official export; "
            "active registration alone does not clear this gate."
        ),
    },
    "CONFLICTS_AND_JOINT_VENTURE_STATUS": {
        "order": 40,
        "actor": "FOUNDER_AND_CORPORATE_OFFICIAL",
        "capture_section": "eligibility_and_compliance",
        "action": (
            "Review the current ownership, conflict, affiliate, and joint-venture facts "
            "and answer only from the actual entity structure."
        ),
        "evidence_required": (
            "A current founder factual answer reviewed against the proposal and entity "
            "records; no relationship may be inferred from family, school, or informal contacts."
        ),
    },
    "NO_DUPLICATE_COST_OR_DELIVERABLE": {
        "order": 45,
        "actor": "FOUNDER_AND_CORPORATE_OFFICIAL",
        "capture_section": "eligibility_and_compliance",
        "action": (
            "Reconcile MissionWeave against every live, pending, planned, and awarded "
            "effort before certifying that no duplicate cost, hour, or deliverable is requested."
        ),
        "evidence_required": (
            "Authoritative support reconciliation, a supportable 640-hour and cost basis, "
            "a reviewed rights position, and corporate review of the exact final preview."
        ),
    },
    "VOLUME3_COST_BASIS": {
        "order": 50,
        "actor": "CORPORATE_OFFICIAL_OR_QUALIFIED_COST_REVIEWER",
        "capture_section": "proposal",
        "action": (
            "Support the direct-labor rate, owner-compensation treatment, fringe, G&A "
            "base, travel, cloud, software, and equipment assumptions in Volume 3."
        ),
        "evidence_required": (
            "Rate and cost records plus a reviewed allowability and allocation basis. "
            "Correct formulas and a balanced workbook do not by themselves support the rates."
        ),
    },
    "CURRENT_CMMC_REQUIREMENTS_REVIEW": {
        "order": 60,
        "actor": "CORPORATE_OFFICIAL_AND_CYBER_REVIEWER",
        "capture_section": "eligibility_and_compliance",
        "action": (
            "Review the live solicitation and amendment language for the current Phase I "
            "CMMC requirement."
        ),
        "evidence_required": (
            "A dated review of the controlling live requirement; do not rely only on a "
            "historical amendment summary."
        ),
    },
    "ITAR_SCOPE_CONFIRMED": {
        "order": 75,
        "actor": "CORPORATE_OFFICIAL_AND_EXPORT_CONTROL_REVIEWER",
        "capture_section": "eligibility_and_compliance",
        "action": (
            "Confirm the ITAR-marked scope only after the official JCP evidence, controlled-data "
            "boundary, and Technology Control Plan decision are all current and documented."
        ),
        "evidence_required": (
            "Verified private JCP/DD Form 2345 evidence plus explicit control-plan and "
            "controlled-data-exclusion records; an isolated scope selection is insufficient."
        ),
    },
    "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION": {
        "order": 70,
        "actor": "CORPORATE_OFFICIAL_AND_CYBER_REVIEWER",
        "capture_section": "eligibility_and_compliance",
        "action": (
            "Document the supportable Phase I self-assessment position without claiming "
            "certification, compliance, or an accredited enclave."
        ),
        "evidence_required": (
            "The authoritative evidence packet state required by the action-gate builder; "
            "a founder checkbox or portal observation alone cannot clear this gate."
        ),
    },
    "TECHNOLOGY_CONTROL_PLAN_DECISION": {
        "order": 80,
        "actor": "CORPORATE_OFFICIAL_AND_EXPORT_CONTROL_REVIEWER",
        "capture_section": "eligibility_and_compliance",
        "action": (
            "Decide whether a Technology Control Plan is required for the actual proposed "
            "scope and document the decision."
        ),
        "evidence_required": (
            "A scope-specific export-control decision that preserves the prohibition on "
            "placing controlled technical data in the proposal."
        ),
    },
    "TECHNICAL_DATA_RIGHTS_ASSERTION": {
        "order": 85,
        "actor": "CORPORATE_OFFICIAL_OR_QUALIFIED_RIGHTS_REVIEWER",
        "capture_section": "eligibility_and_compliance",
        "action": (
            "Reconcile the proposed technical-data and software-rights assertion with the "
            "actual development-funding and final cost records."
        ),
        "evidence_required": (
            "A supported cost/funding basis and corporate review of the exact final package; "
            "the candidate Volume 2 table or a founder checkbox alone cannot clear this gate."
        ),
    },
    "VOLUME5_UPLOAD_SET": {
        "order": 90,
        "actor": "CORPORATE_OFFICIAL",
        "capture_section": "proposal",
        "action": (
            "Review the final Volume 5 upload set after the JCP, CMMC, rights, and control-plan "
            "decisions are resolved."
        ),
        "evidence_required": (
            "An explicit applicable/not-applicable decision for every conditional item in "
            "the Volume 5 worksheet and the exact final filenames selected in DSIP."
        ),
    },
    "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW": {
        "order": 100,
        "actor": "CORPORATE_OFFICIAL",
        "capture_section": "approval",
        "action": (
            "Review all seven volumes, every certification answer, the cost total, and the "
            "final upload set as one coherent proposal."
        ),
        "evidence_required": (
            "A current all-volume review after every upstream documentary and technical "
            "change is complete."
        ),
    },
    "COMPLETE_PORTAL_PREVIEW_REVIEW": {
        "order": 110,
        "actor": "AUTHENTICATED_DSIP_USER_AND_CORPORATE_OFFICIAL",
        "capture_section": "proposal",
        "action": (
            "Review the complete DSIP preview, including all fields, seven volumes, "
            "attachment names, cost total, certifications, and live countdown."
        ),
        "evidence_required": (
            "A complete review performed after the final upload set is frozen; partial-page "
            "inspection is insufficient."
        ),
    },
    "PORTAL_PREVIEW_RECEIPT_HASH": {
        "order": 120,
        "actor": "AUTHENTICATED_DSIP_USER",
        "capture_section": "proposal",
        "action": (
            "Save the private preview receipt and bind it to the current upload set."
        ),
        "evidence_required": (
            "A fresh private preview receipt hash, capture timestamp, and binding hash that "
            "match the current package within the action-gate freshness window."
        ),
    },
    "ACTION_TIME_APPROVAL_TIMESTAMP": {
        "order": 130,
        "actor": "FOUNDER_AND_CORPORATE_OFFICIAL",
        "capture_section": "approval",
        "action": (
            "Provide fresh approval only after reviewing the current bound portal preview."
        ),
        "evidence_required": (
            "A fresh approval timestamp and binding generated after the current preview; "
            "general or earlier approval is insufficient."
        ),
    },
    "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION": {
        "order": 140,
        "actor": "FOUNDER_AND_CORPORATE_OFFICIAL",
        "capture_section": "approval",
        "action": (
            "Authorize the final Government submission for this exact preview and upload set."
        ),
        "evidence_required": (
            "Recipient-specific, proposal-specific action-time authorization. The builder "
            "never clicks Submit and never signs on the founder's behalf."
        ),
    },
}


CLAIM_BOUNDARY = (
    "This closeout packet converts the current public action gate into an ordered human and "
    "portal worklist. It does not clear any private gate, certify cost support, establish "
    "CMMC or export-control status, prove JCP eligibility, authorize a Government submission, "
    "or establish receipt, acceptance, selection, funding, award, deployment, validation, or "
    "economic performance. It also does not establish completion of the separately listed "
    "human-subjects, animal-use, recombinant-DNA, FASCSA, or supply-chain applicability reviews."
)


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def parse_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError(f"Timezone required: {value}")
    return parsed.astimezone(timezone.utc)


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def verify_embedded_hash(payload: dict[str, Any], field: str) -> None:
    recorded = str(payload.get(field) or "").upper()
    unhashed = dict(payload)
    unhashed.pop(field, None)
    if recorded != stable_hash(unhashed):
        raise ValueError(f"Embedded hash mismatch: {field}")


def source_record(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Required source is missing or unsafe: {path}")
    return {
        "path": rel(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def rebuild_action_gate_truth(reference_utc: datetime) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "missionweave_dsip_action_gate_for_closeout", ACTION_GATE_BUILDER
    )
    if spec is None or spec.loader is None:
        raise ValueError("MissionWeave action-gate builder could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    private_path = module.validate_private_target(PRIVATE_ACTION_INPUT)
    if not private_path.is_file():
        raise ValueError("MissionWeave ignored private action input is missing")
    private_bytes = private_path.read_bytes()
    private_payload = json.loads(private_bytes.decode("utf-8"))
    return module.build_payload(
        private_payload,
        private_input_sha256=module.sha256_bytes(private_bytes),
        evaluated_utc=reference_utc,
    )


def validate_gate(
    gate: dict[str, Any], *, rebuilt_gate: dict[str, Any]
) -> list[str]:
    if gate.get("schema") != GATE_SCHEMA:
        raise ValueError("MissionWeave action gate schema is invalid")
    verify_embedded_hash(gate, "gate_sha256")
    if gate.get("topic") != TOPIC:
        raise ValueError("MissionWeave action gate topic is invalid")
    if gate.get("deadline", {}).get("expected_utc") != EXPECTED_DEADLINE_UTC:
        raise ValueError("MissionWeave deadline does not match the controlled deadline")
    summary = gate.get("gate_summary", {})
    unresolved = summary.get("unresolved_gates")
    if not isinstance(unresolved, list) or len(unresolved) != len(set(unresolved)):
        raise ValueError("MissionWeave unresolved gate list is invalid")
    if summary.get("open_gate_count") != len(unresolved):
        raise ValueError("MissionWeave open-gate count does not reconcile")
    required = summary.get("required_private_gate_count")
    passed = summary.get("passed_private_gate_count")
    if not isinstance(required, int) or not isinstance(passed, int):
        raise ValueError("MissionWeave gate counts are invalid")
    if passed + len(unresolved) != required:
        raise ValueError("MissionWeave passed/open gate counts do not reconcile")

    groups = summary.get("reconciliation_groups")
    if not isinstance(groups, dict) or "F_CLEARED_BY_EVIDENCE" not in groups:
        raise ValueError("MissionWeave reconciliation groups are invalid")
    grouped_gates: list[str] = []
    open_group_gates: list[str] = []
    cleared_group_gates: list[str] = []
    for group_id, group in groups.items():
        if not isinstance(group, dict) or set(group) != {"status", "count", "gates"}:
            raise ValueError("MissionWeave reconciliation group schema is invalid")
        gates = group.get("gates")
        if not isinstance(gates, list) or len(gates) != len(set(gates)):
            raise ValueError("MissionWeave reconciliation group gates are invalid")
        if group.get("count") != len(gates):
            raise ValueError("MissionWeave reconciliation group count is invalid")
        status = group.get("status")
        if group_id == "F_CLEARED_BY_EVIDENCE":
            if status != "CLEARED":
                raise ValueError("MissionWeave cleared-evidence group status is invalid")
            cleared_group_gates.extend(str(gate_id) for gate_id in gates)
        else:
            expected_status = "OPEN" if gates else "CLEAR"
            if status != expected_status:
                raise ValueError("MissionWeave open-group status is invalid")
            open_group_gates.extend(str(gate_id) for gate_id in gates)
        grouped_gates.extend(str(gate_id) for gate_id in gates)
    if len(grouped_gates) != len(set(grouped_gates)) or len(grouped_gates) != required:
        raise ValueError("MissionWeave reconciliation groups overlap or omit gates")
    if set(open_group_gates) != set(unresolved):
        raise ValueError("MissionWeave open groups do not match unresolved gates")
    if len(cleared_group_gates) != passed:
        raise ValueError("MissionWeave cleared group does not match passed count")
    expected_ready = not unresolved
    if gate.get("submission_ready_for_human_click") is not expected_ready:
        raise ValueError(
            "MissionWeave submission readiness does not reconcile with unresolved gates"
        )
    unknown = set(unresolved) - set(ACTION_DEFINITIONS)
    if unknown:
        raise ValueError("Missing closeout action definitions: " + ", ".join(sorted(unknown)))

    truth_fields = (
        "status",
        "submission_ready_for_human_click",
        "gate_summary",
        "private_fact_state",
        "private_volume3_artifact",
        "private_jcp_evidence",
        "cmmc_evidence_packet",
        "source_integrity",
    )
    if any(gate.get(field) != rebuilt_gate.get(field) for field in truth_fields):
        raise ValueError(
            "MissionWeave action gate does not match regenerated private-evidence truth"
        )
    return [str(gate_id) for gate_id in unresolved]


def validate_followup_queue(queue: dict[str, Any]) -> dict[str, Any]:
    if queue.get("schema") != QUEUE_SCHEMA:
        raise ValueError("Outreach follow-up queue schema is invalid")
    verify_embedded_hash(queue, "queue_sha256")
    lane = next(
        (
            row
            for row in queue.get("actions", [])
            if row.get("lane_id") == MISSIONWEAVE_LANE_ID
        ),
        None,
    )
    if lane is None:
        raise ValueError("MissionWeave follow-up lane is missing")
    if lane.get("deadline_utc") != EXPECTED_DEADLINE_UTC:
        raise ValueError("MissionWeave follow-up deadline drifted")
    if lane.get("action_state") != "FOLLOWUP_LIMIT_REACHED_NO_SEND":
        raise ValueError("MissionWeave follow-up lock is not exhausted")
    if lane.get("send_now") is not False:
        raise ValueError("MissionWeave follow-up queue exposed a send-now action")
    if lane.get("recorded_proactive_send_count") != lane.get("max_proactive_sends"):
        raise ValueError("MissionWeave proactive-send count does not match its limit")
    return lane


def validate_portal_receipts(
    dsip_receipt: dict[str, Any],
    sam_receipt: dict[str, Any],
    *,
    reference_utc: datetime,
) -> None:
    expected_dsip_keys = {
        "schema",
        "status",
        "observed_utc",
        "portal",
        "topic",
        "proposal_title",
        "proposal_state",
        "live_deadline_observation",
        "remaining_portal_actions",
        "private_evidence_binding",
        "redactions",
        "claim_boundary",
    }
    expected_sam_keys = {
        "schema",
        "status",
        "observed_utc",
        "portal",
        "observation",
        "private_evidence_binding",
        "redactions",
        "claim_boundary",
    }
    if set(dsip_receipt) != expected_dsip_keys:
        raise ValueError("MissionWeave live DSIP receipt schema drifted")
    if set(sam_receipt) != expected_sam_keys:
        raise ValueError("MissionWeave SAM receipt schema drifted")

    for label, receipt in (("DSIP", dsip_receipt), ("SAM", sam_receipt)):
        observed = parse_utc(str(receipt.get("observed_utc") or ""))
        age = reference_utc - observed
        if age < timedelta(0) or age > PORTAL_RECEIPT_MAX_AGE:
            raise ValueError(f"MissionWeave {label} receipt is not current")

    if dsip_receipt.get("schema") != LIVE_DSIP_RECEIPT_SCHEMA:
        raise ValueError("MissionWeave live DSIP receipt schema is invalid")
    if dsip_receipt.get("topic") != TOPIC:
        raise ValueError("MissionWeave live DSIP receipt topic is invalid")
    if "proposal_number" in dsip_receipt:
        raise ValueError("MissionWeave public DSIP receipt exposes a proposal identifier")
    if (
        dsip_receipt.get("live_deadline_observation", {}).get("deadline_utc")
        != EXPECTED_DEADLINE_UTC
    ):
        raise ValueError("MissionWeave live DSIP receipt deadline drifted")
    if any(dsip_receipt.get("redactions", {}).values()):
        raise ValueError("MissionWeave live DSIP receipt contains a redaction violation")
    dsip_binding = dsip_receipt.get("private_evidence_binding", {})
    if dsip_binding != {
        "private_receipt_recorded": True,
        "artifact_count": 2,
        "public_paths_or_hashes_disclosed": False,
    }:
        raise ValueError("MissionWeave live DSIP private-evidence binding is invalid")
    if "private_evidence" in dsip_receipt:
        raise ValueError("MissionWeave live DSIP receipt exposes private evidence details")

    if sam_receipt.get("schema") != SAM_REPS_RECEIPT_SCHEMA:
        raise ValueError("MissionWeave SAM receipt schema is invalid")
    if sam_receipt.get("status") != "AUTHENTICATED_CURRENT_RECORD_REPS_CERTS_OBSERVED":
        raise ValueError("MissionWeave SAM receipt status is invalid")
    if not sam_receipt.get("observation", {}).get(
        "current_representations_and_certifications_page_accessible"
    ):
        raise ValueError("MissionWeave SAM receipt lacks current-page confirmation")
    if any(sam_receipt.get("redactions", {}).values()):
        raise ValueError("MissionWeave SAM receipt contains a redaction violation")
    sam_binding = sam_receipt.get("private_evidence_binding", {})
    if sam_binding != {
        "private_receipt_recorded": True,
        "artifact_count": 1,
        "public_paths_or_hashes_disclosed": False,
    }:
        raise ValueError("MissionWeave SAM private-evidence binding is invalid")
    if "private_evidence" in sam_receipt:
        raise ValueError("MissionWeave SAM receipt exposes private evidence details")


def build_actions(unresolved: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for gate_id in unresolved:
        definition = ACTION_DEFINITIONS[gate_id]
        rows.append(
            {
                "gate_id": gate_id,
                "order": definition["order"],
                "actor": definition["actor"],
                "capture_section": definition["capture_section"],
                "action": definition["action"],
                "evidence_required": definition["evidence_required"],
                "gate_state_after_build": "OPEN",
                "automatic_clear_allowed": False,
            }
        )
    return sorted(rows, key=lambda row: (row["order"], row["gate_id"]))


def build_payload(
    *,
    generated_utc: str | None = None,
    gate_path: Path = GATE_JSON,
    followup_queue_path: Path = FOLLOWUP_QUEUE_JSON,
) -> dict[str, Any]:
    generated_at = (
        datetime.now(timezone.utc)
        if generated_utc is None
        else parse_utc(generated_utc)
    )
    deadline = parse_utc(EXPECTED_DEADLINE_UTC)
    seconds_remaining = int((deadline - generated_at).total_seconds())

    gate = read_json(gate_path)
    rebuilt_gate = rebuild_action_gate_truth(generated_at)
    unresolved = validate_gate(gate, rebuilt_gate=rebuilt_gate)
    queue = read_json(followup_queue_path)
    followup_lane = validate_followup_queue(queue)
    dsip_receipt = read_json(LIVE_DSIP_RECEIPT)
    sam_receipt = read_json(SAM_REPS_RECEIPT)
    validate_portal_receipts(
        dsip_receipt, sam_receipt, reference_utc=generated_at
    )
    actions = build_actions(unresolved)

    volume3 = gate.get("private_volume3_artifact", {})
    transport_checks = (
        "workbook_present",
        "receipt_present",
        "receipt_header_valid",
        "workbook_size_matches_receipt",
        "workbook_hash_matches_receipt",
        "formula_scan_clean",
        "export_reimport_verified",
        "financial_reconciliation_pass",
        "review_guardrails_preserved",
        "receipt_integrity_pass",
    )
    transport_pass = all(volume3.get(name) is True for name in transport_checks)
    cost_gate_open = "VOLUME3_COST_BASIS" in unresolved

    if seconds_remaining < 0:
        deadline_state = "EXPECTED_DEADLINE_PASSED_LIVE_PORTAL_CHECK_REQUIRED"
    elif seconds_remaining <= 24 * 60 * 60:
        deadline_state = "UNDER_24_HOURS"
    elif seconds_remaining <= 48 * 60 * 60:
        deadline_state = "UNDER_48_HOURS"
    else:
        deadline_state = "MORE_THAN_48_HOURS"

    supplemental_gaps = [dict(item, state="UNRESOLVED") for item in SUPPLEMENTAL_REVIEW_GAPS]
    ready_for_human_review = bool(
        not unresolved and not supplemental_gaps and seconds_remaining >= 0
    )
    status = (
        "READY_FOR_FRESH_HUMAN_FINAL_REVIEW"
        if ready_for_human_review
        else "FOUNDER_AND_PORTAL_CLOSEOUT_REQUIRED"
    )
    group_summary = gate.get("gate_summary", {}).get("reconciliation_groups", {})

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": utc_iso(generated_at),
        "topic": TOPIC,
        "status": status,
        "deadline": {
            "expected_utc": EXPECTED_DEADLINE_UTC,
            "expected_local": gate["deadline"]["expected_local"],
            "seconds_remaining_at_build": seconds_remaining,
            "state": deadline_state,
            "live_dsip_recheck_required": True,
            "internal_upload_preview_target": "2026-07-21T15:00:00-05:00",
            "founder_final_review_target": "2026-07-22T09:00:00-05:00",
        },
        "summary": {
            "required_gate_count": gate["gate_summary"]["required_private_gate_count"],
            "passed_gate_count": gate["gate_summary"]["passed_private_gate_count"],
            "open_gate_count": len(unresolved),
            "action_count": len(actions),
            "every_open_gate_has_one_action": len(actions) == len(unresolved),
            "known_supplemental_review_gap_count": len(supplemental_gaps),
            "submission_ready_for_human_click": ready_for_human_review,
            "external_email_due": False,
        },
        "reconciliation_groups": group_summary,
        "volume3_review_state": {
            "computation_and_export_transport_verified": transport_pass,
            "verified_checks": {
                name: bool(volume3.get(name)) for name in transport_checks
            },
            "official_ceiling_reconciled": bool(
                gate.get("private_fact_state", {}).get(
                    "volume3_total_matches_official_ceiling"
                )
            ),
            "cost_basis_support_gate_open": cost_gate_open,
            "distinction": (
                "Workbook arithmetic, formula scanning, export/reimport, and receipt integrity "
                "are verified. Labor-rate, owner-compensation, fringe, indirect-rate, travel, "
                "cloud, software, and equipment support remains a separate corporate-review gate."
            ),
        },
        "outreach_state": {
            "lane_id": MISSIONWEAVE_LANE_ID,
            "action_state": followup_lane["action_state"],
            "recorded_proactive_send_count": followup_lane[
                "recorded_proactive_send_count"
            ],
            "max_proactive_sends": followup_lane["max_proactive_sends"],
            "send_now": False,
            "duplicate_send_prohibited": True,
            "next_action": (
                "Monitor the existing thread and respond only to a specific inbound request."
            ),
        },
        "portal_state": {
            "dsip": {
                "observed_utc": dsip_receipt["observed_utc"],
                "completion_percent": dsip_receipt["proposal_state"][
                    "completion_percent"
                ],
                "volume_v_percent": dsip_receipt["proposal_state"][
                    "volume_percent"
                ]["V"],
                "certify_percent": dsip_receipt["proposal_state"][
                    "certify_percent"
                ],
            },
            "sam": {
                "observed_utc": sam_receipt["observed_utc"],
                "active_current_registration_observed": True,
                "current_far_dfars_reps_certs_page_observed": True,
                "individual_answer_accuracy_certified_by_builder": False,
            },
            "jcp": {
                "authenticated_documentary_evidence_observed": False,
                "state": "AUTHENTICATION_CODE_REQUIRED",
            },
        },
        "ordered_actions": actions,
        "supplemental_applicability_review": {
            "status": "QUALIFIED_REVIEW_REQUIRED_BEFORE_SUBMISSION",
            "automatic_clear_allowed": False,
            "items": supplemental_gaps,
        },
        "capture_commands": {
            "identity": (
                "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py "
                "--section identity"
            ),
            "eligibility_and_compliance": (
                "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py "
                "--section eligibility_and_compliance"
            ),
            "proposal": (
                "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py "
                "--section proposal"
            ),
            "approval": (
                "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py "
                "--section approval"
            ),
            "rebuild_gate": (
                "python code/ops/BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py "
                "--private-input <IGNORED_PRIVATE_INPUT>"
            ),
        },
        "controls": {
            "builder_changed_private_gate_state": False,
            "builder_read_credentials": False,
            "builder_navigated_browser": False,
            "builder_sent_email": False,
            "builder_uploaded_files": False,
            "builder_signed_or_certified": False,
            "builder_clicked_final_submit": False,
            "action_time_human_unlock_required": True,
            "private_paths_or_hashes_exposed": False,
            "unresolved_gate_automatic_clear_allowed": False,
        },
        "source_evidence": {
            "action_gate": source_record(gate_path),
            "followup_queue": source_record(followup_queue_path),
            "cost_inputs": source_record(COST_INPUTS),
            "volume5_worksheet": source_record(VOLUME5_WORKSHEET),
            "portal_checklist": source_record(PORTAL_CHECKLIST),
            "live_dsip_receipt": source_record(LIVE_DSIP_RECEIPT),
            "sam_reps_certs_receipt": source_record(SAM_REPS_RECEIPT),
        },
        "outputs": {"json": rel(OUT_JSON), "markdown": rel(OUT_MD)},
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["closeout_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    deadline = payload["deadline"]
    cost = payload["volume3_review_state"]
    outreach = payload["outreach_state"]
    portal = payload["portal_state"]
    lines = [
        "# MissionWeave Deadline Closeout - 2026-07-20",
        "",
        f"- Status: `{payload['status']}`",
        f"- Expected deadline: {deadline['expected_local']}",
        f"- Deadline state at build: `{deadline['state']}`",
        f"- Live DSIP recheck required: `{str(deadline['live_dsip_recheck_required']).lower()}`",
        f"- Passed gates: `{summary['passed_gate_count']}/{summary['required_gate_count']}`",
        f"- Open gates: `{summary['open_gate_count']}`",
        f"- Supplemental applicability gaps: `{summary['known_supplemental_review_gap_count']}`",
        f"- Submission ready for human click: `{str(summary['submission_ready_for_human_click']).lower()}`",
        f"- Closeout SHA-256: `{payload['closeout_sha256']}`",
        "",
        "## Operating Targets",
        "",
        "- Finish authenticated evidence retrieval and the complete upload preview by `July 21, 3:00 p.m. Central`.",
        "- Reserve the founder's final review and action-time authorization for no later than `July 22, 9:00 a.m. Central`.",
        "- Recheck the live DSIP countdown before entry and again before final submission.",
        "",
        "## Cost Volume Distinction",
        "",
        f"- Computation and export transport verified: `{str(cost['computation_and_export_transport_verified']).lower()}`",
        f"- Official ceiling reconciled: `{str(cost['official_ceiling_reconciled']).lower()}`",
        f"- Cost-basis support gate open: `{str(cost['cost_basis_support_gate_open']).lower()}`",
        f"- {cost['distinction']}",
        "",
        "## Outreach Lock",
        "",
        f"- State: `{outreach['action_state']}`",
        f"- Proactive follow-ups used: `{outreach['recorded_proactive_send_count']}/{outreach['max_proactive_sends']}`",
        f"- Send now: `{str(outreach['send_now']).lower()}`",
        f"- Duplicate send prohibited: `{str(outreach['duplicate_send_prohibited']).lower()}`",
        f"- Next action: {outreach['next_action']}",
        "",
        "## Live Portal State",
        "",
        f"- DSIP completion observed: `{portal['dsip']['completion_percent']}%`",
        f"- DSIP Volume V observed: `{portal['dsip']['volume_v_percent']}%`",
        f"- DSIP final certification observed: `{portal['dsip']['certify_percent']}%`",
        "- SAM active current registration and current FAR/DFARS Reps and Certs page observed: `true`",
        "- JCP authenticated documentary evidence observed: `false`",
        "- JCP state: `AUTHENTICATION_CODE_REQUIRED`",
        "",
        "## Ordered Closeout Actions",
        "",
        "| Order | Gate | Actor | Capture section |",
        "|---:|---|---|---|",
    ]
    for row in payload["ordered_actions"]:
        lines.append(
            f"| {row['order']} | `{row['gate_id']}` | `{row['actor']}` | "
            f"`{row['capture_section']}` |"
        )
        lines.extend(
            [
                "",
                f"**{row['gate_id']}**",
                "",
                f"- Action: {row['action']}",
                f"- Evidence required: {row['evidence_required']}",
                "- Automatic clear allowed: `false`",
                "",
            ]
        )
    lines.extend(
        [
            "## Supplemental Applicability Review",
            "",
            "These items were identified after the original 50-gate model was frozen. They remain independent NO-GO conditions until qualified review is documented.",
            "",
        ]
    )
    for row in payload["supplemental_applicability_review"]["items"]:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- State: `{row['state']}`",
                f"- Actor: `{row['actor']}`",
                f"- Action: {row['action']}",
                "- Automatic clear allowed: `false`",
                "",
            ]
        )
    lines.extend(
        [
            "## Capture Commands",
            "",
            "Run only the section that matches newly reviewed facts. The approval section is action-time only.",
            "",
        ]
    )
    for name, command in payload["capture_commands"].items():
        lines.extend([f"### {name}", "", "```powershell", command, "```", ""])
    lines.extend(["## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated-utc")
    parser.add_argument("--gate", type=Path, default=GATE_JSON)
    parser.add_argument("--followup-queue", type=Path, default=FOLLOWUP_QUEUE_JSON)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    if not args.check_only and args.generated_utc is not None:
        raise SystemExit("--generated-utc is allowed only with --check-only")
    if not args.check_only and (
        args.gate.resolve() != GATE_JSON.resolve()
        or args.followup_queue.resolve() != FOLLOWUP_QUEUE_JSON.resolve()
    ):
        raise SystemExit("alternate source paths are allowed only with --check-only")

    payload = build_payload(
        generated_utc=args.generated_utc,
        gate_path=args.gate,
        followup_queue_path=args.followup_queue,
    )
    if not args.check_only:
        OUT_JSON.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "deadline_state": payload["deadline"]["state"],
                "open_gate_count": payload["summary"]["open_gate_count"],
                "action_count": payload["summary"]["action_count"],
                "supplemental_review_gap_count": payload["summary"][
                    "known_supplemental_review_gap_count"
                ],
                "duplicate_send_prohibited": payload["outreach_state"][
                    "duplicate_send_prohibited"
                ],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
