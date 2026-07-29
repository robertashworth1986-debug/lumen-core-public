from __future__ import annotations

import copy
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FUNDING_SPRINT_REVIEWER_GATE.py"
CONFORMANCE = ROOT / "out" / "ops" / "submission_conformance_gate_latest.json"


def load_module():
    spec = importlib.util.spec_from_file_location("funding_sprint_reviewer_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_conformance() -> dict:
    return json.loads(CONFORMANCE.read_text(encoding="utf-8"))


def refresh_hashes(module, payload: dict, changed_lane_id: str) -> None:
    row = next(row for row in payload["lanes"] if row["lane_id"] == changed_lane_id)
    row["lane_gate_sha256"] = module.canonical_sha256(
        {key: value for key, value in row.items() if key != "lane_gate_sha256"}
    )
    payload["gate_sha256"] = module.canonical_sha256(
        {key: value for key, value in payload.items() if key != "gate_sha256"}
    )


def make_temporally_current(module, payload: dict) -> None:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload["as_of_utc"] = now
    payload["registry_as_of_utc"] = now
    payload["gate_sha256"] = module.canonical_sha256(
        {key: value for key, value in payload.items() if key != "gate_sha256"}
    )


def test_reviewer_gate_blocks_current_candidates_on_source_bound_arguments():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "funding_sprint_reviewer_gate_v2"
    assert payload["reviewer_gate_clear"] is False
    assert payload["status"] == (
        "REVIEWER_GATE_BLOCKED_SOURCE_BOUND_ARGUMENT_CONFORMANCE"
    )
    assert summary["packaging_checks_clear"] is True
    assert summary["conformance_document_valid"] is True
    assert summary["conformance_coverage_clear"] is True
    assert summary["missing_conformance_mapping_count"] == 0
    assert summary["unrepresented_active_conformance_lane_count"] == 0
    assert summary["proof_card_count"] == 9
    assert summary["unsafe_secret_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert summary["boundary_hit_count"] > 0
    assert summary["active_technical_candidate_count"] == 3
    assert summary["active_argument_pass_count"] == 0
    assert summary["active_argument_blocked_count"] == 3
    assert summary["closed_route_count"] == 1
    assert summary["expired_route_count"] == 1
    assert summary["technical_no_go_count"] == 1
    assert summary["autonomous_external_action_allowed"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["final_submission_allowed_without_human"] is False
    assert payload["submission_conformance"]["validation_errors"] == []
    assert len(payload["gate_sha256"]) == 64


def test_packet_artifacts_and_hashes_do_not_make_packets_reviewer_ready():
    module = load_module()
    conformance = copy.deepcopy(load_conformance())
    make_temporally_current(module, conformance)
    payload = module.build_payload(conformance)
    cards = {card["lane"]: card for card in payload["proof_cards"]}

    expected = {
        "DARPA DICE",
        "NASA Data Center Infrastructure RFI",
        "CDC AI for Acquisition Support RFI",
        "DLA MissionWeave DSIP SBIR",
        "FHWA TSMO Data Initiative",
        "NSF SBIR/STTR Project Pitch",
        "ERDC Sovereign Defense Cloud CSO",
        "DARPA FALCON Direct to Phase II",
        "Launch Tennessee 3686 Pitch Competition",
    }
    assert set(cards) == expected

    for card in cards.values():
        assert card["artifact_present"] is True
        assert len(card["artifact_sha256"]) == 64
        assert len(card["card_sha256"]) == 64
        assert card["human_gate"]
        assert card["reviewer_ready"] is False
        assert card["source_bound_argument_conformance_pass"] is False
        assert card["reviewer_posture"] != "ready_for_human_review"

    assert (
        cards["DLA MissionWeave DSIP SBIR"]["reviewer_posture"]
        == "expired_no_verified_submission_reuse_blocked"
    )
    assert (
        cards["NASA Data Center Infrastructure RFI"]["reviewer_posture"]
        == "monitor_only_no_duplicate_submission"
    )
    assert (
        cards["CDC AI for Acquisition Support RFI"]["reviewer_posture"]
        == "monitor_only_no_duplicate_submission"
    )
    assert (
        cards["FHWA TSMO Data Initiative"]["reviewer_posture"]
        == "not_a_current_submission_route"
    )
    assert (
        cards["DARPA DICE"]["reviewer_posture"]
        == "closed_official_decision_postmortem_only"
    )
    assert (
        cards["DARPA FALCON Direct to Phase II"]["reviewer_posture"]
        == "technical_no_go_evidence_sprint_only"
    )
    for lane_name in (
        "NSF SBIR/STTR Project Pitch",
        "ERDC Sovereign Defense Cloud CSO",
        "Launch Tennessee 3686 Pitch Competition",
    ):
        assert cards[lane_name]["reviewer_posture"] == (
            "blocked_source_bound_argument_conformance"
        )


def test_declared_pass_and_complete_counts_cannot_replace_source_bound_evidence():
    module = load_module()
    conformance = copy.deepcopy(load_conformance())
    make_temporally_current(module, conformance)
    lane = next(
        row
        for row in conformance["lanes"]
        if row["lane_id"] == "erdc_sovereign_cloud_cso"
    )
    lane["status"] = module.LANE_CONFORMANCE_PASS_STATUS
    lane["argument_conformance_pass"] = True
    lane["criterion_pass_count"] = len(module.REQUIRED_ARGUMENT_CRITERIA)
    lane["criterion_partial_count"] = 0
    lane["criterion_fail_count"] = 0
    lane["criterion_unassessed_count"] = 0
    for criterion in lane["criteria"]:
        criterion["state"] = "PASS"
        criterion["passed"] = True
        criterion["source_refs_all_present"] = True
    official_source = next(
        criterion
        for criterion in lane["criteria"]
        if criterion["criterion_id"] == "official_source_current"
    )
    official_source["source_refs_all_present"] = False
    conformance["status"] = module.CONFORMANCE_PASS_STATUS
    refresh_hashes(module, conformance, "erdc_sovereign_cloud_cso")

    payload = module.build_payload(conformance)
    card = next(
        card
        for card in payload["proof_cards"]
        if card["conformance_lane_id"] == "erdc_sovereign_cloud_cso"
    )

    assert payload["summary"]["packaging_checks_clear"] is True
    assert card["argument_conformance_declared_pass"] is True
    assert card["reviewer_ready"] is False
    assert card["source_bound_argument_conformance_pass"] is False
    assert "criterion_sources_not_current:official_source_current" in card[
        "readiness_blockers"
    ]
    assert "independent_red_team_not_passed" in card["readiness_blockers"]


def test_closed_conformance_route_stays_closed_even_with_artifact_present():
    module = load_module()
    conformance = copy.deepcopy(load_conformance())
    make_temporally_current(module, conformance)
    lane = next(
        row for row in conformance["lanes"] if row["lane_id"] == "dla_missionweave_sbir"
    )
    lane["disposition"] = "CLOSED_OFFICIAL_DECISION"
    lane["status"] = "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    lane["submission_candidate_active"] = False
    lane["argument_conformance_pass"] = False
    refresh_hashes(module, conformance, "dla_missionweave_sbir")

    payload = module.build_payload(conformance)
    card = next(
        card
        for card in payload["proof_cards"]
        if card["conformance_lane_id"] == "dla_missionweave_sbir"
    )

    assert card["artifact_present"] is True
    assert card["conformance_mapping_found"] is True
    assert card["reviewer_ready"] is False
    assert card["reviewer_posture"] == "closed_official_decision_postmortem_only"
    assert card["readiness_blockers"] == ["official_decision_closed_route"]


def test_missing_conformance_document_fails_closed(monkeypatch, tmp_path):
    module = load_module()
    monkeypatch.setattr(
        module,
        "CONFORMANCE_JSON",
        tmp_path / "missing_submission_conformance_gate.json",
    )

    payload = module.build_payload()

    assert payload["summary"]["packaging_checks_clear"] is True
    assert payload["summary"]["conformance_document_valid"] is False
    assert payload["reviewer_gate_clear"] is False
    assert payload["status"] == "REVIEWER_GATE_BLOCKED_INVALID_SUBMISSION_CONFORMANCE"
    assert payload["submission_conformance"]["validation_errors"] == [
        "submission_conformance_gate_missing"
    ]
    assert all(card["reviewer_ready"] is False for card in payload["proof_cards"])


def test_stale_source_receipt_fails_closed_even_with_rehashed_gate():
    module = load_module()
    conformance = copy.deepcopy(load_conformance())
    conformance["source_evidence"]["public_leads"]["sha256"] = "0" * 64
    conformance["gate_sha256"] = module.canonical_sha256(
        {
            key: value
            for key, value in conformance.items()
            if key != "gate_sha256"
        }
    )

    payload = module.build_payload(conformance)

    assert payload["summary"]["conformance_document_valid"] is False
    assert payload["reviewer_gate_clear"] is False
    assert payload["status"] == (
        "REVIEWER_GATE_BLOCKED_INVALID_SUBMISSION_CONFORMANCE"
    )
    assert (
        "submission_conformance_source_evidence_not_current:public_leads"
        in payload["submission_conformance"]["validation_errors"]
    )


def test_rendered_markdown_preserves_argument_and_human_stop_rules():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Funding Sprint Reviewer Gate" in rendered
    assert "Reviewer gate clear: `false`" in rendered
    assert "Packaging checks clear: `true`" in rendered
    assert "Packaging checks and language scans are supporting controls only" in rendered
    assert "Source-bound argument pass: `false`" in rendered
    assert "Autonomous external action allowed: `false`" in rendered
    assert "Live trading allowed: `false`" in rendered
    assert "Final submission without human allowed: `false`" in rendered
    assert "No portal submission" in rendered


def test_scanner_recognizes_structured_negative_claim_and_secret_metadata(tmp_path):
    module = load_module()
    artifact = tmp_path / "bounded.md"
    artifact.write_text(
        "# Review\n\n"
        "- Secret content indexed: `false`\n"
        "- secret_contents_not_published: `true`\n"
        "- `NOT_ESTABLISHED` - All personnel hold a Secret clearance\n"
        "- Realized savings claim allowed: `false`\n\n"
        "## Blocked Until Human\n\n"
        "- claim of agency validation, realized savings, or award certainty\n",
        encoding="utf-8",
    )

    scan = module.scan_files([artifact])
    assert scan["unsafe_secret_count"] == 0
    assert scan["unsafe_claim_count"] == 0
    assert scan["boundary_hit_count"] >= 5


def test_scanner_does_not_treat_security_clearance_requirement_as_secret(tmp_path):
    module = load_module()
    artifact = tmp_path / "clearance-requirement.md"
    artifact.write_text(
        "- `secret_cleared_personnel` - Performing personnel must hold a "
        "Secret clearance.\n",
        encoding="utf-8",
    )

    scan = module.scan_files([artifact])

    assert scan["unsafe_secret_count"] == 0
    assert scan["unsafe_claim_count"] == 0
    assert scan["boundary_hit_count"] == 1
    assert {
        hit["classification"] for hit in scan["boundary_hits"]
    } == {"noncredential_security_clearance_requirement"}
