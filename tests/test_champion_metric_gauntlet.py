from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CHAMPION_METRIC_GAUNTLET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("champion_metric_gauntlet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gauntlet_surfaces_current_champion_without_field_claim():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    strongest = payload["strongest_current"]

    assert payload["schema"] == "champion_metric_gauntlet_v1"
    assert strongest["family"] == "kuramoto_phase_coupling"
    assert strongest["named_baseline"] == "kalman_filter"
    assert summary["holdout_count"] >= 20
    assert summary["holdout_wins"] >= 20
    assert summary["holdout_win_rate"] >= 0.8
    assert summary["estimated_rows_replayed"] >= 1_000_000
    assert summary["source_system_count"] >= 3
    assert summary["broader_measured_provider_count"] >= summary["source_system_count"]
    assert summary["manifest_unique_source_count"] >= summary["source_system_count"]
    assert summary["reviewer_safe_internal_claim_allowed"] is True
    assert summary["buyer_authorized_field_replay_request_ready"] is True
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False


def test_gauntlet_has_passes_and_blockers():
    module = load_module()
    payload = module.build_payload()
    gates = {row["name"]: row for row in payload["metric_gauntlet"]}

    assert gates["holdout_depth"]["passed"] is True
    assert gates["baseline_win_count"]["passed"] is True
    assert gates["minimum_delta_positive"]["passed"] is True
    assert gates["sign_test_strength"]["passed"] is True
    assert gates["source_system_diversity"]["passed"] is True
    assert gates["row_replay_depth"]["passed"] is True
    assert gates["field_validation"]["passed"] is False
    assert gates["field_validation"]["blocker"] is True
    assert gates["live_domain_feed_routed"]["passed"] is payload["summary"]["live_domain_reviewer_ready"]
    assert payload["summary"]["blocking_gate_count"] >= 1
    assert payload["summary"]["metric_expansion_family_count"] >= 10
    assert payload["summary"]["metric_expansion_blocked_count"] >= 3


def test_gauntlet_routes_dashboard_feed_and_hashes_itself():
    module = load_module()
    payload = module.build_payload()
    feeds = payload["dashboard_feed_status"]

    assert len(payload["gauntlet_sha256"]) == 64
    assert feeds["local_feed_count"] >= 6
    assert feeds["status"] in {"LIVE_DOMAIN_HASH_VERIFIED", "LOCAL_READY_DOMAIN_NOT_VERIFIED", "LOCAL_FEEDS_INCOMPLETE"}
    assert feeds["live_domain_routed"] is payload["summary"]["live_domain_reviewer_ready"]
    assert any(row["relative_path"] == "dashboard/data/champion_metric_gauntlet.json" for row in feeds["feeds"])


def test_markdown_answers_what_to_ask_and_refuses_overclaiming():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert "Champion Metric Gauntlet" in rendered
    assert "What To Ask Me" in rendered
    assert "Holdout wins" in rendered
    assert "Metric Expansion Suite" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "Real-dollar savings claim allowed: `false`" in rendered
    assert "Buyer-authorized field replay request ready: `true`" in rendered
    assert "guaranteed grant" not in dumped
    assert "guaranteed profit" not in dumped
    assert "money printer" not in dumped


def test_gauntlet_separates_champion_replay_from_broader_live_sources():
    module = load_module()
    payload = module.build_payload()
    source_breadth = payload["source_breadth_universe"]
    replay = source_breadth["champion_replay"]
    fresh = source_breadth["fresh_provider_measurement"]
    manifest = source_breadth["geometry_manifest"]
    boundary = source_breadth["claim_boundary"].lower()

    assert replay["source_system_count"] == payload["summary"]["source_system_count"]
    assert fresh["measured_provider_count"] >= replay["source_system_count"]
    assert fresh["enabled_provider_count"] >= fresh["measured_provider_count"]
    assert manifest["unique_source_count"] >= replay["source_system_count"]
    assert manifest["ready_for_benchmark_row_count"] >= replay["source_system_count"]
    assert "not the same metric" in boundary
    assert "not automatically part of the current champion win" in boundary


def test_gauntlet_documents_hardware_and_fixed_dollar_blockers():
    module = load_module()
    payload = module.build_payload()
    hardware = payload["hardware_validation_unlock"]
    rendered = module.render_markdown(payload)

    assert "Grid/RF/PLL Hardware Validation Gate" in rendered
    assert "What API Keys Are For" in rendered
    assert "Fixed-Dollar Claim Blockers" in rendered
    assert hardware["grid_validation"]["required_inputs"]
    assert hardware["rf_validation"]["acceptance_metrics"]
    assert hardware["pll_validation"]["required_inputs"]
    assert len(hardware["fixed_dollar_claim_blockers"]) >= 5


def test_gauntlet_metric_expansion_suite_covers_money_and_field_gates():
    module = load_module()
    payload = module.build_payload()
    suite = {row["family_id"]: row for row in payload["metric_expansion_suite"]}

    assert "forecast_error_and_residuals" in suite
    assert "phase_lock_and_timing" in suite
    assert "source_generalization" in suite
    assert "economic_conversion" in suite
    assert "external_field_replay" in suite
    assert "all_family_championship" in suite
    assert suite["phase_lock_and_timing"]["metrics"]
    assert "BLOCKED" in suite["economic_conversion"]["status"]
    assert "external owner" in suite["external_field_replay"]["claim_gate"].lower()
    assert "Universal geometry-superiority" in suite["all_family_championship"]["claim_gate"]
