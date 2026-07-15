from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "eia_grid_prospective_hourly_router.py"
PROTOCOL_PATH = ROOT / "config" / "eia_grid_prospective_hourly_router_protocol_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("eia_hourly_router", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_panel(module, target="2026-07-15T14"):
    protocol = module.load_protocol(PROTOCOL_PATH)
    rows = []
    end = module.period_end_utc(target)
    for index in range(24 * 40, 0, -1):
        period = module.period_string(end - module.timedelta(hours=index))
        actual = 1000.0 + 75.0 * module.math.sin(index / 24.0)
        rows.extend(
            [
                {
                    "period": period,
                    "respondent": "ERCO",
                    "respondent_name": "ERCO",
                    "type": "D",
                    "type_name": "Demand",
                    "value": actual,
                    "value_units": "megawatthours",
                },
                {
                    "period": period,
                    "respondent": "ERCO",
                    "respondent_name": "ERCO",
                    "type": "DF",
                    "type_name": "Demand forecast",
                    "value": actual + 5.0,
                    "value_units": "megawatthours",
                },
            ]
        )
    rows.append(
        {
            "period": target,
            "respondent": "ERCO",
            "respondent_name": "ERCO",
            "type": "DF",
            "type_name": "Demand forecast",
            "value": 1100.0,
            "value_units": "megawatthours",
        }
    )
    return {
        "schema": "eia_grid_hourly_source_cache.v1",
        "row_count": len(rows),
        "row_chain_sha256": module.canonical_sha256(rows),
        "rows": rows,
    }, protocol


def test_protocol_freezes_real_hybrid_routes_and_no_backfill():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    routes = set(protocol["router"]["route_map"].values())
    assert routes == {
        "eia_official",
        "ridge_residual",
        "xgboost_residual",
        "lightgbm_residual",
    }
    assert protocol["prospective_window"]["backfilled_predictions_allowed"] is False
    assert protocol["router"]["dynamic_override_allowed"] is False


def test_interval_deadline_is_one_hour_before_hour_ending():
    module = load_module()
    assert module.target_interval_start_utc("2026-07-15T14") == datetime(
        2026, 7, 15, 13, 0, tzinfo=timezone.utc
    )


def test_eligible_target_requires_future_interval_and_absent_actual():
    module = load_module()
    panel, protocol = synthetic_panel(module)
    series = module.series_by_authority(panel, protocol)
    selected, _ = module.eligible_targets(
        series, protocol, datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    )
    assert ("ERCO", "2026-07-15T14") in selected
    selected_after, skipped = module.eligible_targets(
        series, protocol, datetime(2026, 7, 15, 13, 0, tzinfo=timezone.utc)
    )
    assert ("ERCO", "2026-07-15T14") not in selected_after
    assert skipped["target_interval_already_started"] == 1


def test_forecast_feature_excludes_target_actual():
    module = load_module()
    panel, protocol = synthetic_panel(module)
    series = module.series_by_authority(panel, protocol)
    row = module.build_feature_row(
        series, protocol, "ERCO", "2026-07-15T14", require_actual=False
    )
    assert row["target_period_end_utc"] == "2026-07-15T14"
    assert "actual_mwh" not in row
    assert "target_residual_scaled" not in row
    assert len(row["features"]) == 27


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
