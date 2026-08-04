from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "eia_grid_hourly_hybrid_confirmation.py"
PROTOCOL_PATH = ROOT / "config" / "eia_grid_hourly_hybrid_confirmation_protocol_v3.json"


def load_module():
    spec = importlib.util.spec_from_file_location("eia_hourly_hybrid_v3", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_parent_panel(module, target="2026-08-02T12"):
    protocol = module.load_protocol(PROTOCOL_PATH)
    candidates = protocol["candidate"]["input_candidates"]
    authority_predictions = []
    for index, authority in enumerate(protocol["balancing_authorities"], start=1):
        center = 10_000.0 + index * 1_000.0
        values = {
            candidate: center + offset * 25.0
            for offset, candidate in enumerate(candidates, start=-3)
        }
        authority_predictions.append(
            {
                "respondent": authority,
                "respondent_name": authority,
                "candidate_predictions_mwh": values,
                "error_scale_mwh": 500.0 + index,
                "level_scale_mwh": center,
                "selected_candidate": "xgboost_direct",
                "router_prediction_mwh": values["xgboost_direct"],
                "target_actual_present_at_seal": False,
            }
        )
    panel = {
        "schema": "eia_grid_all_authority_direct_hourly_prediction_panel.v2",
        "protocol_sha256": protocol["parent_v2"]["protocol_sha256"],
        "protocol_commit": protocol["parent_v2"]["protocol_commit"],
        "record_sha256": "a" * 64,
        "target_period_end_utc": target,
        "target_interval_start_utc": module.target_interval_start_utc(target).isoformat(),
        "sealed_utc": "2026-08-02T09:20:00+00:00",
        "seal_lead_seconds": 6000.0,
        "authority_count": 8,
        "authorities": list(protocol["balancing_authorities"]),
        "authority_predictions": authority_predictions,
        "source_panel_row_chain_sha256": "b" * 64,
        "source_receipt_sha256": "c" * 64,
        "target_actual_present_at_seal": False,
        "target_official_forecast_used": False,
        "backfilled": False,
    }
    return panel, protocol


def test_protocol_freezes_one_v3_candidate_and_defers_v4_v5():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    assert protocol["candidate"]["id"] == "constrained_historical_inverse_square_blend_v3"
    assert protocol["candidate"]["constraints"]["prospective_weight_updates_allowed"] is False
    assert protocol["candidate"]["constraints"]["dynamic_regime_switching_allowed"] is False
    assert protocol["succession"]["v4_start_allowed_now"] is False
    assert protocol["succession"]["v5_start_allowed_now"] is False
    assert protocol["automatic_promotion_allowed"] is False


def test_frozen_inputs_and_runtime_are_hash_bound():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    observed = module.verify_frozen_inputs(protocol)
    assert observed["parent_v2_protocol_sha256"] == protocol["parent_v2"]["protocol_sha256"]
    assert observed["historical_design_artifact_sha256"] == protocol["historical_design"]["artifact_sha256"]
    assert len(observed["v3_protocol_sha256"]) == 64
    assert len(observed["v3_runtime_sha256"]) == 64


def test_inverse_square_weights_are_nonnegative_and_sum_to_one():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    design = module.load_design_metrics(protocol)
    for authority in protocol["balancing_authorities"]:
        weights = module.inverse_square_weights(authority, protocol, design)
        assert set(weights) == set(protocol["candidate"]["input_candidates"])
        assert all(value >= 0.0 for value in weights.values())
        assert abs(sum(weights.values()) - 1.0) < 1e-12


def test_v3_forecast_is_deterministic_convex_and_ignores_unrelated_actual_field():
    module = load_module()
    panel, protocol = synthetic_parent_panel(module)
    design = module.load_design_metrics(protocol)
    first = module.compute_v3_panel(panel, protocol, design)
    panel["unrelated_future_actual_mwh"] = 999_999_999.0
    second = module.compute_v3_panel(panel, protocol, design)
    assert first == second
    for row in first:
        values = list(row["input_candidate_predictions_mwh"].values())
        assert min(values) <= row["v3_prediction_mwh"] <= max(values)
        assert row["target_actual_present_at_seal"] is False


def test_issuance_window_accepts_only_60_to_120_minute_lead():
    module = load_module()
    panel, protocol = synthetic_parent_panel(module)
    accepted, _ = module.eligible_parent_panels(
        [panel], [], protocol, datetime(2026, 8, 2, 9, 30, tzinfo=timezone.utc)
    )
    assert accepted == [panel]
    too_late, late_skips = module.eligible_parent_panels(
        [panel], [], protocol, datetime(2026, 8, 2, 10, 30, tzinfo=timezone.utc)
    )
    assert too_late == []
    assert late_skips["below_frozen_minimum_lead"] == 1
    too_early, early_skips = module.eligible_parent_panels(
        [panel], [], protocol, datetime(2026, 8, 2, 8, 30, tzinfo=timezone.utc)
    )
    assert too_early == []
    assert early_skips["above_frozen_maximum_lead"] == 1


def test_before_window_and_backfilled_panels_are_rejected():
    module = load_module()
    old, protocol = synthetic_parent_panel(module, target="2026-08-02T11")
    selected, skipped = module.eligible_parent_panels(
        [old], [], protocol, datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc)
    )
    assert selected == []
    assert skipped["before_v3_window"] == 1
    future, _ = synthetic_parent_panel(module)
    future["backfilled"] = True
    try:
        module.eligible_parent_panels(
            [future], [], protocol, datetime(2026, 8, 2, 9, 30, tzinfo=timezone.utc)
        )
    except ValueError as exc:
        assert "backfilled" in str(exc)
    else:
        raise AssertionError("backfilled v2 panel was accepted")


def test_append_only_chain_detects_tampering(tmp_path):
    module = load_module()
    path = tmp_path / "chain.jsonl"
    first = module.append_chain_record(path, {"value": 1}, module.ZERO_HASH)
    module.append_chain_record(path, {"value": 2}, first["record_sha256"])
    records, _ = module.load_chain(path)
    assert [row["value"] for row in records] == [1, 2]
    lines = path.read_text(encoding="utf-8").splitlines()
    altered = json.loads(lines[0])
    altered["value"] = 99
    lines[0] = json.dumps(altered, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        module.load_chain(path)
    except ValueError as exc:
        assert "record hash mismatch" in str(exc)
    else:
        raise AssertionError("tampered v3 chain was accepted")


def test_status_suppresses_scores_and_keeps_future_stages_deferred():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    status = module.build_status(
        protocol,
        parent_prediction_count=200,
        parent_settlement_count=196,
        predictions=[],
        settlements=[],
        prediction_terminal=module.ZERO_HASH,
        settlement_terminal=module.ZERO_HASH,
    )
    assert status["performance"]["scores_suppressed"] is True
    assert status["performance"]["aggregate_metrics"] is None
    assert status["performance"]["promotion_evaluation_complete"] is False
    assert status["succession"]["v2"] == "ACTIVE_PRESERVED_PARENT"
    assert status["succession"]["v4"].startswith("DEFERRED")
    assert status["succession"]["v5"].startswith("DEFERRED")


def test_complete_utc_days_requires_all_24_hour_keys():
    module = load_module()
    incomplete = [
        {"target_period_end_utc": f"2026-08-03T{hour:02d}"} for hour in range(23)
    ]
    complete = [
        {"target_period_end_utc": f"2026-08-04T{hour:02d}"} for hour in range(24)
    ]
    assert module.complete_utc_days(incomplete + complete) == ["2026-08-04"]
