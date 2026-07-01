from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_EXECUTION_ACTION_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_execution_action_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_execution_action_board_builds_context_and_keeps_claim_gates_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "geometry_execution_action_board_v1"
    assert summary["action_count"] >= 20
    assert summary["runnable_local_action_count"] >= 4
    assert summary["adapter_gap_action_count"] >= 1
    assert summary["rolling_champion_action_count"] >= 3
    assert summary["robust_repeat_action_count"] >= 1
    assert summary["registered_family_count"] >= 140
    assert summary["benchmark_specified_family_count"] >= 137
    assert summary["measured_sources"] >= 18
    assert summary["measured_rows"] >= 418
    assert len(summary["board_chain_sha256"]) == 64

    assert summary["bounded_estimated_value_claim_allowed"] is True
    assert summary["paid_pilot_scoping_allowed"] is True
    assert summary["field_validation_claim_allowed"] is False
    assert summary["real_dollar_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_sale_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert summary["mass_email_allowed"] is False
    assert summary["send_without_user_review"] is False
    assert payload["context_checkpoint"]["current_strongest_candidate"] == "brachistochrone_descent"
    assert payload["context_checkpoint"]["current_money_proxy"] == "energy_price_pressure_forecast"
    assert payload["context_checkpoint"]["current_money_proxy_artifact"] == "dashboard/data/energy_price_pressure_forecast.json"


def test_top_families_have_correct_actions_runners_and_blockers():
    module = load_module()
    payload = module.build_payload()
    actions = {row["family_id"]: row for row in payload["all_actions"]}

    brach = actions["brachistochrone_descent"]
    assert brach["next_action_type"] == "buyer_authorized_pilot_and_publication"
    assert brach["robust_repeat_uncertainty_gate_passed"] is True
    assert brach["paid_pilot_ready"] is True
    assert brach["runner"]["script"] == "code/geometry_optimal_curve_transport_benchmark.py"
    assert "geometry_optimal_curve_transport_benchmark.py" in brach["runner"]["safe_local_command"]
    assert brach["runner"]["safe_to_run_without_human_review"] is False
    assert "Buyer/agency accepts" in brach["success_metric"]
    assert any("field validation" in item.lower() for item in brach["blocked_until"])

    kuramoto = actions["kuramoto_phase_coupling"]
    assert kuramoto["next_action_type"] == "buyer_authorized_pilot_and_publication"
    assert kuramoto["runner"]["script"] == "code/geometry_wave_resonance_timing_benchmark.py"
    assert "Buyer/agency accepts" in kuramoto["success_metric"]
    assert kuramoto["runner"]["safe_to_run_without_human_review"] is False

    thermal = actions["thermal_plume_convection"]
    assert thermal["next_action_type"] == "additional_holdout_replay"
    assert thermal["runner"]["script"] == "code/geometry_thermal_ventilation_benchmark.py"
    assert thermal["live_source_count"] == 2
    assert any("field" in item.lower() for item in thermal["blocked_until"])

    leaf = actions["leaf_veins"]
    assert leaf["next_action_type"] == "additional_holdout_replay"
    assert leaf["runner"]["script"] == "code/geometry_branching_transport_benchmark.py"

    assert "phase_locked_residual_corrector" not in actions


def test_commands_are_safe_and_markdown_preserves_boundaries():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    serialized = json.dumps(payload)

    forbidden = [
        "LIQUIDATE_ALL_TO_USD",
        "cancel_open_orders",
        "kraken_execution.py",
        "Send-MailMessage",
        "Remove-Item",
        "live_order_placement",
        "guaranteed profit",
        "guaranteed award",
    ]
    for term in forbidden:
        assert term not in serialized
        assert term.lower() not in rendered.lower()

    assert "Geometry Execution Action Board" in rendered
    assert "No field validation claim." in rendered
    assert "No fixed-dollar frozen-delta sale claim." in rendered
    assert "Live trading/autonomous execution allowed: `false`" in rendered
    assert "Read these first before changing direction" in rendered
    assert "docs/CURRENT_LUMA_PROOF_STATE_2026-06-25.md" in rendered
