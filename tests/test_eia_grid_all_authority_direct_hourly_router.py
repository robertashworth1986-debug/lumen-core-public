from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "eia_grid_all_authority_direct_hourly_router.py"
PROTOCOL_PATH = ROOT / "config" / "eia_grid_all_authority_direct_hourly_protocol_v2.json"
V1_PROTOCOL_PATH = ROOT / "config" / "eia_grid_prospective_hourly_router_protocol_v1.json"
V1_CODE_PATH = ROOT / "code" / "eia_grid_prospective_hourly_router.py"


def load_module():
    spec = importlib.util.spec_from_file_location("eia_all_authority_v2", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_test_protocol(module):
    return module.load_protocol(PROTOCOL_PATH, allow_design_pending=True)


def synthetic_panel(module, target="2026-07-16T07", include_target_actual=False):
    protocol = load_test_protocol(module)
    rows = []
    end = module.period_end_utc(target)
    for authority_index, authority in enumerate(protocol["balancing_authorities"]):
        for offset in range(24 * 45, 0, -1):
            period = module.period_string(end - module.timedelta(hours=offset))
            actual = (
                1000.0
                + 125.0 * authority_index
                + 60.0 * module.math.sin(offset / 24.0)
                + 15.0 * module.math.cos(offset / 168.0)
            )
            rows.append(
                {
                    "period": period,
                    "respondent": authority,
                    "respondent_name": authority,
                    "type": "D",
                    "type_name": "Demand",
                    "value": actual,
                    "value_units": "megawatthours",
                }
            )
        if include_target_actual:
            rows.append(
                {
                    "period": target,
                    "respondent": authority,
                    "respondent_name": authority,
                    "type": "D",
                    "type_name": "Demand",
                    "value": 1200.0 + authority_index,
                    "value_units": "megawatthours",
                }
            )
    rows.sort(key=lambda row: (row["period"], row["respondent"], row["type"]))
    return {
        "schema": "eia_grid_all_authority_source_cache.v2",
        "row_count": len(rows),
        "row_chain_sha256": module.canonical_sha256(rows),
        "rows": rows,
    }, protocol


def test_v1_protocol_and_source_are_unchanged():
    module = load_module()
    assert module.file_sha256(V1_PROTOCOL_PATH) == (
        "5398f17f57e02bdaadb1cef5b6dae20708146eaa0de534ebbe6ce36ab28952e5"
    )
    assert module.file_sha256(V1_CODE_PATH) == (
        "82f48921f5e3553fbb3b169ef1b1dc3e9c6677507735482e7d5cb820e12ccb41"
    )


def test_protocol_excludes_target_official_and_backfill():
    module = load_module()
    protocol = load_test_protocol(module)
    assert protocol["feature_contract"]["target_official_forecast_may_be_used"] is False
    assert protocol["prediction_seal"]["require_target_official_forecast"] is False
    assert protocol["prospective_window"]["backfilled_predictions_allowed"] is False
    assert protocol["prediction_seal"]["require_atomic_all_authority_panel_record"] is True


def test_frozen_route_map_is_complete_and_bound_to_design_result():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    routes = protocol["router"]["route_map"]
    assert set(routes) == set(protocol["balancing_authorities"])
    design_path = ROOT / protocol["historical_design"]["result_path"]
    assert module.file_sha256(design_path) == protocol["historical_design"]["result_sha256"]
    design = json.loads(design_path.read_text(encoding="utf-8"))
    assert design["selected_route_map"] == routes


def test_next_target_leaves_one_full_hour_before_interval():
    module = load_module()
    protocol = load_test_protocol(module)
    protocol["prospective_window"]["first_allowed_period_end_utc"] = None
    sealed_at = datetime(2026, 7, 16, 5, 10, tzinfo=timezone.utc)
    target = module.next_common_target(sealed_at, protocol)
    assert target == "2026-07-16T08"
    assert module.target_interval_start_utc(target) == datetime(
        2026, 7, 16, 7, 0, tzinfo=timezone.utc
    )
    assert module.target_interval_start_utc(target) - sealed_at >= module.timedelta(hours=1)


def test_all_eight_authorities_build_same_target_without_official_forecast():
    module = load_module()
    panel, protocol = synthetic_panel(module)
    series = module.series_by_authority(panel, protocol)
    sealed_at = datetime(2026, 7, 16, 5, 10, tzinfo=timezone.utc)
    rows, failures = module.prepare_common_forecast_rows(
        series, protocol, "2026-07-16T07", sealed_at
    )
    assert failures == {}
    assert len(rows) == 8
    assert {row["respondent"] for row in rows} == set(protocol["balancing_authorities"])
    assert {row["target_period_end_utc"] for row in rows} == {"2026-07-16T07"}
    assert all("actual_mwh" not in row for row in rows)
    assert all("official_mwh" not in row for row in rows)
    assert all(len(row["features"]) == 31 for row in rows)


def test_target_official_forecast_cannot_change_features():
    module = load_module()
    panel, protocol = synthetic_panel(module)
    series = module.series_by_authority(panel, protocol)
    before = module.build_feature_row(
        series, protocol, "SWPP", "2026-07-16T07", require_actual=False
    )
    panel["rows"].append(
        {
            "period": "2026-07-16T07",
            "respondent": "SWPP",
            "respondent_name": "SWPP",
            "type": "DF",
            "type_name": "Demand forecast",
            "value": 999999999.0,
            "value_units": "megawatthours",
        }
    )
    after_series = module.series_by_authority(panel, protocol)
    after = module.build_feature_row(
        after_series, protocol, "SWPP", "2026-07-16T07", require_actual=False
    )
    assert before["features"] == after["features"]
    assert module.canonical_sha256(before["features"]) == module.canonical_sha256(
        after["features"]
    )


def test_missing_one_authority_lag_fails_closed_for_whole_panel():
    module = load_module()
    panel, protocol = synthetic_panel(module)
    missing_period = module.shift_period("2026-07-16T07", -24)
    panel["rows"] = [
        row
        for row in panel["rows"]
        if not (
            row["respondent"] == "TVA"
            and row["period"] == missing_period
            and row["type"] == "D"
        )
    ]
    series = module.series_by_authority(panel, protocol)
    rows, failures = module.prepare_common_forecast_rows(
        series,
        protocol,
        "2026-07-16T07",
        datetime(2026, 7, 16, 5, 10, tzinfo=timezone.utc),
    )
    assert rows == []
    assert failures == {"TVA": "required actual lag is unavailable"}


def test_present_target_actual_fails_closed_for_whole_panel():
    module = load_module()
    panel, protocol = synthetic_panel(module)
    panel["rows"].append(
        {
            "period": "2026-07-16T07",
            "respondent": "CISO",
            "respondent_name": "CISO",
            "type": "D",
            "type_name": "Demand",
            "value": 1200.0,
            "value_units": "megawatthours",
        }
    )
    series = module.series_by_authority(panel, protocol)
    rows, failures = module.prepare_common_forecast_rows(
        series,
        protocol,
        "2026-07-16T07",
        datetime(2026, 7, 16, 5, 10, tzinfo=timezone.utc),
    )
    assert rows == []
    assert failures == {"CISO": "target actual is already present"}


def test_settlement_waits_until_all_eight_actuals_exist(tmp_path):
    module = load_module()
    panel, protocol = synthetic_panel(module)
    module.PREDICTIONS_PATH = tmp_path / "predictions.jsonl"
    module.SETTLEMENTS_PATH = tmp_path / "settlements.jsonl"
    candidate_ids = [row["id"] for row in protocol["candidates"]]
    authority_predictions = [
        {
            "respondent": authority,
            "candidate_predictions_mwh": {
                candidate: 1000.0 + index for candidate in candidate_ids
            },
            "selected_candidate": "seasonal_naive_24",
            "router_prediction_mwh": 1000.0,
            "error_scale_mwh": 10.0,
        }
        for index, authority in enumerate(protocol["balancing_authorities"])
    ]
    prediction = module.append_chain_record(
        module.PREDICTIONS_PATH,
        {
            "schema": "eia_grid_all_authority_direct_hourly_prediction_panel.v2",
            "target_period_end_utc": "2026-07-16T07",
            "authority_count": 8,
            "authorities": protocol["balancing_authorities"],
            "authority_predictions": authority_predictions,
            "protocol_sha256": "a" * 64,
            "protocol_commit": "b" * 40,
        },
        module.ZERO_HASH,
    )
    waiting = module.settle_from_panel(
        protocol, panel, {"source": "synthetic"}, dry_run=False
    )
    assert waiting["settled_panel_count"] == 0
    assert set(waiting["waiting_for_authorities"]["2026-07-16T07"]) == set(
        protocol["balancing_authorities"]
    )
    complete, _ = synthetic_panel(module, include_target_actual=True)
    settled = module.settle_from_panel(
        protocol, complete, {"source": "synthetic"}, dry_run=False
    )
    assert settled["settled_panel_count"] == 1
    record = settled["settlement_panels"][0]
    assert record["authority_count"] == 8
    assert len(record["authority_metrics"]) == 8
    assert record["prediction_panel_record_sha256"] == prediction["record_sha256"]


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
        raise AssertionError("tampered chain was accepted")
