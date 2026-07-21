from __future__ import annotations

import copy
import importlib.util
import json
import re
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_MISSIONWEAVE_DEADLINE_CLOSEOUT.py"
OUT_JSON = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_DEADLINE_CLOSEOUT_2026-07-20.json"
)
LIVE_STATUS_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_DSIP_LIVE_STATUS_RECEIPT_2026-07-20.json"
)
SAM_REPS_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_SAM_CURRENT_REPS_CERTS_RECEIPT_2026-07-20.json"
)


EXPECTED_OPEN_GATES = {
    "ACTION_TIME_APPROVAL_TIMESTAMP",
    "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
    "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION",
    "COMPLETE_PORTAL_PREVIEW_REVIEW",
    "CONFLICTS_AND_JOINT_VENTURE_STATUS",
    "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
    "CURRENT_CMMC_REQUIREMENTS_REVIEW",
    "DD2345_OR_JCP_APPLICATION_EVIDENCE",
    "DSIP_FIRM_PIN_AVAILABILITY",
    "ITAR_SCOPE_CONFIRMED",
    "NO_DUPLICATE_COST_OR_DELIVERABLE",
    "PORTAL_PREVIEW_RECEIPT_HASH",
    "TECHNICAL_DATA_RIGHTS_ASSERTION",
    "TECHNOLOGY_CONTROL_PLAN_DECISION",
    "VOLUME3_COST_BASIS",
    "VOLUME5_UPLOAD_SET",
}

EXPECTED_SUPPLEMENTAL_GAPS = {
    "ANIMAL_USE_APPLICABILITY",
    "FASCSA_REASONABLE_INQUIRY",
    "HUMAN_SUBJECTS_APPLICABILITY",
    "RECOMBINANT_DNA_APPLICABILITY",
    "SUPPLY_CHAIN_CLAUSE_APPLICABILITY",
}


def load_module():
    spec = importlib.util.spec_from_file_location(
        "missionweave_deadline_closeout", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_closeout_covers_every_open_gate_once_and_preserves_stops():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-21T02:00:00Z")
    actions = payload["ordered_actions"]

    assert payload["schema"] == module.SCHEMA
    assert payload["status"] == "FOUNDER_AND_PORTAL_CLOSEOUT_REQUIRED"
    assert payload["deadline"]["expected_utc"] == "2026-07-22T16:00:00Z"
    assert payload["deadline"]["state"] == "UNDER_48_HOURS"
    assert payload["summary"]["required_gate_count"] == 50
    assert payload["summary"]["passed_gate_count"] == 34
    assert payload["summary"]["open_gate_count"] == 16
    assert payload["summary"]["action_count"] == 16
    assert payload["summary"]["known_supplemental_review_gap_count"] == 5
    assert {row["gate_id"] for row in actions} == EXPECTED_OPEN_GATES
    assert len({row["gate_id"] for row in actions}) == len(actions)
    assert all(row["automatic_clear_allowed"] is False for row in actions)
    assert payload["summary"]["submission_ready_for_human_click"] is False
    assert payload["controls"]["builder_clicked_final_submit"] is False
    assert payload["controls"]["action_time_human_unlock_required"] is True
    supplemental = payload["supplemental_applicability_review"]
    assert supplemental["status"] == "QUALIFIED_REVIEW_REQUIRED_BEFORE_SUBMISSION"
    assert supplemental["automatic_clear_allowed"] is False
    assert {row["id"] for row in supplemental["items"]} == EXPECTED_SUPPLEMENTAL_GAPS
    assert all(row["state"] == "UNRESOLVED" for row in supplemental["items"])


def test_portal_receipts_reject_stale_observations_and_schema_expansion():
    module = load_module()
    dsip = json.loads(LIVE_STATUS_RECEIPT.read_text(encoding="utf-8"))
    sam = json.loads(SAM_REPS_RECEIPT.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="not current"):
        module.validate_portal_receipts(
            dsip,
            sam,
            reference_utc=module.parse_utc("2026-07-21T08:00:00Z"),
        )

    expanded = copy.deepcopy(dsip)
    expanded["unexpected_private_field"] = "synthetic-canary"
    with pytest.raises(ValueError, match="schema drifted"):
        module.validate_portal_receipts(
            expanded,
            sam,
            reference_utc=module.parse_utc("2026-07-21T02:00:00Z"),
        )


def test_closeout_rejects_a_self_rehashed_unverified_all_gates_pass_transition():
    module = load_module()
    gate = copy.deepcopy(json.loads(module.GATE_JSON.read_text(encoding="utf-8")))
    summary = gate["gate_summary"]
    summary["unresolved_gates"] = []
    summary["open_gate_count"] = 0
    summary["passed_private_gate_count"] = summary["required_private_gate_count"]
    gate["submission_ready_for_human_click"] = True
    gate.pop("gate_sha256", None)
    gate["gate_sha256"] = module.stable_hash(gate)
    with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir:
        gate_path = Path(temp_dir) / "gate.json"
        gate_path.write_text(json.dumps(gate), encoding="utf-8")
        with pytest.raises(ValueError, match="open groups"):
            module.build_payload(
                generated_utc="2026-07-21T02:00:00Z", gate_path=gate_path
            )


def test_volume3_integrity_is_not_mislabeled_as_supported_cost_basis():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-21T02:00:00Z")
    state = payload["volume3_review_state"]

    assert state["computation_and_export_transport_verified"] is True
    assert state["official_ceiling_reconciled"] is True
    assert state["cost_basis_support_gate_open"] is True
    assert all(state["verified_checks"].values())
    assert "do not by themselves support" in next(
        row["evidence_required"]
        for row in payload["ordered_actions"]
        if row["gate_id"] == "VOLUME3_COST_BASIS"
    )


def test_missionweave_followup_limit_prevents_duplicate_email():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-21T02:00:00Z")
    outreach = payload["outreach_state"]

    assert outreach["action_state"] == "FOLLOWUP_LIMIT_REACHED_NO_SEND"
    assert outreach["recorded_proactive_send_count"] == 1
    assert outreach["max_proactive_sends"] == 1
    assert outreach["send_now"] is False
    assert outreach["duplicate_send_prohibited"] is True
    assert payload["summary"]["external_email_due"] is False


def test_written_closeout_is_public_safe_source_bound_and_self_hashed():
    module = load_module()
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, sort_keys=True).lower()

    assert payload["schema"] == module.SCHEMA
    assert "c:\\users" not in serialized
    assert "e:\\" not in serialized
    assert "@gmail.com" not in serialized
    assert '"firm_pin"' not in serialized
    assert payload["controls"]["private_paths_or_hashes_exposed"] is False
    assert all(
        (ROOT / row["path"]).is_file()
        and (ROOT / row["path"]).stat().st_size == row["bytes"]
        and module.sha256_file(ROOT / row["path"]) == row["sha256"]
        for row in payload["source_evidence"].values()
    )

    unhashed = dict(payload)
    recorded = unhashed.pop("closeout_sha256")
    assert recorded == module.stable_hash(unhashed)


def test_live_dsip_status_receipt_is_bounded_and_public_safe():
    payload = json.loads(LIVE_STATUS_RECEIPT.read_text(encoding="utf-8"))

    assert payload["status"] == (
        "AUTHENTICATED_PORTAL_STATUS_OBSERVED_ACTIONS_REMAIN_OPEN"
    )
    assert payload["proposal_state"]["completion_percent"] == 88
    assert payload["proposal_state"]["volume_percent"]["V"] == 0
    assert payload["proposal_state"]["certify_percent"] == 0
    assert payload["live_deadline_observation"]["deadline_utc"] == (
        "2026-07-22T16:00:00Z"
    )
    assert "proposal_number" not in payload
    assert "private_evidence" not in payload
    assert payload["private_evidence_binding"] == {
        "private_receipt_recorded": True,
        "artifact_count": 2,
        "public_paths_or_hashes_disclosed": False,
    }
    assert not any(payload["redactions"].values())
    serialized = json.dumps(payload, sort_keys=True).lower()
    assert re.search(r"\bl\d{2}[a-z]{2}-[a-z0-9]+-\d+\b", serialized) is None
    assert re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", serialized) is None
    assert re.search(r"\b[a-f0-9]{16,}_[a-f0-9]{4,}\b", serialized) is None
    assert re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", serialized) is None
    assert (
        re.search(
            r"\b(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]\d{3}[-.\s]\d{4}\b",
            serialized,
        )
        is None
    )
    for forbidden in (
        "firm_pin_value",
        "password",
        "refresh_token",
    ):
        assert forbidden not in serialized


def test_sam_current_reps_receipt_is_bounded_and_public_safe():
    payload = json.loads(SAM_REPS_RECEIPT.read_text(encoding="utf-8"))

    assert payload["status"] == "AUTHENTICATED_CURRENT_RECORD_REPS_CERTS_OBSERVED"
    assert payload["observation"]["entity_registration_status"] == "Active"
    assert payload["observation"]["registration_record"] == "Current"
    assert payload["observation"][
        "current_representations_and_certifications_page_accessible"
    ] is True
    assert "private_evidence" not in payload
    assert payload["private_evidence_binding"] == {
        "private_receipt_recorded": True,
        "artifact_count": 1,
        "public_paths_or_hashes_disclosed": False,
    }
    assert not any(payload["redactions"].values())
    serialized = json.dumps(payload, sort_keys=True).lower()
    assert re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", serialized) is None
    assert re.search(r"(?<![\d-])\d{8,}(?![\d-])", serialized) is None
    assert (
        re.search(
            r"\b(?=[a-z0-9]{12}\b)(?=[a-z0-9]*[a-z])(?=[a-z0-9]*\d)[a-z0-9]{12}\b",
            serialized,
        )
        is None
    )
    for forbidden in (
        "routing number",
        "taxpayer",
    ):
        assert forbidden not in serialized
