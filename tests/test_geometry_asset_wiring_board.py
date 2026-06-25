from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_ASSET_WIRING_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_asset_wiring_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_asset_wiring_board_builds_reviewer_safe_summary():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "geometry_asset_wiring_board_v1"
    assert summary["proof_card_count"] >= 10
    assert summary["triple_source_candidate_count"] >= 3
    assert summary["single_run_candidate_count"] >= 1
    assert summary["dashboard_feed_count"] >= 4
    assert summary["grant_packet_feed_count"] >= 3
    assert summary["outreach_feed_count"] >= 3
    assert summary["validation_run_count"] >= 8
    assert summary["candidate_win_count"] >= 3
    assert len(summary["board_chain_sha256"]) == 64

    assert summary["ready_for_live_geometry_claim"] is False
    assert summary["ready_for_real_dollar_claim"] is False
    assert summary["field_validation"] is False
    assert summary["kraken_live_execution_allowed"] is False
    assert summary["mass_email_allowed"] is False
    assert payload["send_gate"]["send_without_user_review"] is False


def test_key_rows_wire_to_dashboards_grants_outreach_and_blockers():
    module = load_module()
    payload = module.build_payload()
    rows = {row["family_id"]: row for row in payload["wiring_rows"]}

    for family_id in [
        "brachistochrone_descent",
        "kuramoto_phase_coupling",
        "thermal_plume_convection",
        "leaf_veins",
        "crack_propagation_paths",
        "phase_locked_residual_corrector",
    ]:
        assert family_id in rows
        row = rows[family_id]
        assert "mission_control" in row["dashboard_targets"]
        assert "grants" in row["dashboard_targets"]
        assert row["grant_targets"]
        assert row["buyer_segments"]
        assert row["buyer_outreach_position"]["send_gate"]["mass_email_allowed"] is False
        assert row["claim_gate"]["ready_for_real_dollar_claim"] is False
        assert row["claim_gate"]["field_validation"] is False
        assert len(row["row_sha256"]) == 64

    brach = rows["brachistochrone_descent"]
    assert "triple_source" in brach["readiness_tier"]
    assert any("second distinct run hash" in item for item in brach["blockers"])
    assert brach["validation_run"]["candidate_beats_named_baseline"] is True
    assert "DARPA/I2O or DICE-style reviewer evidence annex" in brach["grant_targets"]

    kuramoto = rows["kuramoto_phase_coupling"]
    assert "forecast" in kuramoto["dashboard_targets"]
    assert "phase/RMSE" not in json.dumps(kuramoto).lower()

    thermal = rows["thermal_plume_convection"]
    assert "single_run" in thermal["readiness_tier"]
    assert any("three measured sources" in item for item in thermal["blockers"])
    assert any("DOE" in target for target in thermal["grant_targets"])

    leaf = rows["leaf_veins"]
    assert "did_not_beat" in leaf["readiness_tier"]
    assert leaf["validation_run"]["candidate_beats_named_baseline"] is False
    assert any("negative evidence" in leaf["buyer_outreach_position"]["safe_angle"] for _ in [0])

    crack = rows["crack_propagation_paths"]
    assert "proof_value" in crack["readiness_tier"]
    assert any("Infrastructure" in target for target in crack["grant_targets"])

    phase = rows["phase_locked_residual_corrector"]
    assert phase["registry_family"] is False
    assert any("registry" in action["action"].lower() for action in payload["top_next_actions"])


def test_next_actions_and_markdown_keep_claim_boundaries_visible():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    actions = {item["family_id"]: item for item in payload["top_next_actions"]}

    assert "brachistochrone_descent" in actions
    assert "second frozen live-source run hash" in actions["brachistochrone_descent"]["action"]
    assert "kuramoto_phase_coupling" in actions
    assert "second frozen live-source run hash" in actions["kuramoto_phase_coupling"]["action"]
    assert "thermal_plume_convection" in actions
    assert "phase_locked_residual_corrector" in actions
    assert "crack_propagation_paths" in actions

    assert "Geometry Asset Wiring Board" in rendered
    assert "Ready for real-dollar claim: `false`" in rendered
    assert "Mass email allowed: `false`" in rendered
    assert "Do not say a packet is worth a fixed dollar amount as fact." in rendered
    assert "guaranteed profit" not in rendered.lower()
    assert "live_order_placement" not in json.dumps(payload)
