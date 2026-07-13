from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "eia_grid_prospective_hybrid_router.py"
PROTOCOL_PATH = ROOT / "config" / "eia_grid_prospective_hybrid_router_protocol_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("eia_grid_prospective_router", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_panel(module, protocol, target="2026-07-14"):
    rows = []
    start = datetime.fromisoformat("2024-01-01").date()
    end = datetime.fromisoformat(target).date()
    days = (end - start).days
    for respondent in protocol["balancing_authorities"]:
        for index in range(days):
            period = (start.fromordinal(start.toordinal() + index)).isoformat()
            actual = 1000.0 + index + 10.0 * (index % 7)
            rows.extend(
                [
                    {
                        "period": period,
                        "respondent": respondent,
                        "respondent_name": respondent,
                        "timezone": module.EIA_FACET_TIMEZONES[respondent],
                        "type": "D",
                        "type_name": "Demand",
                        "value": actual,
                        "value_units": "megawatthours",
                    },
                    {
                        "period": period,
                        "respondent": respondent,
                        "respondent_name": respondent,
                        "timezone": module.EIA_FACET_TIMEZONES[respondent],
                        "type": "DF",
                        "type_name": "Day-ahead demand forecast",
                        "value": actual + (5.0 if index % 2 else -3.0),
                        "value_units": "megawatthours",
                    },
                ]
            )
        rows.append(
            {
                "period": target,
                "respondent": respondent,
                "respondent_name": respondent,
                "timezone": module.EIA_FACET_TIMEZONES[respondent],
                "type": "DF",
                "type_name": "Day-ahead demand forecast",
                "value": 2000.0,
                "value_units": "megawatthours",
            }
        )
    return {
        "schema": "eia_grid_validation_panel.v1",
        "rows": rows,
        "row_chain_sha256": module.canonical_sha256(rows),
        "quality": {"row_count": len(rows)},
    }


def test_protocol_freezes_hybrid_routes_and_future_boundary():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    assert protocol["historical_design_evidence"]["panel_last_target_date"] == "2026-07-12"
    assert protocol["prospective_window"]["first_allowed_target_date"] == "2026-07-14"
    assert protocol["router"]["route_map"]["NYIS"] == "direct_lightgbm_stack"
    assert protocol["router"]["route_map"]["SWPP"] == "autoregressive_ridge_p14"
    assert protocol["router"]["dynamic_override_allowed"] is False


def test_seal_must_precede_target_local_midnight():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    before = datetime(2026, 7, 14, 3, 59, tzinfo=timezone.utc)
    after = datetime(2026, 7, 14, 4, 1, tzinfo=timezone.utc)
    assert module.seal_eligibility(protocol, "NYIS", "2026-07-14", before) == (
        True,
        "eligible",
    )
    assert module.seal_eligibility(protocol, "NYIS", "2026-07-14", after) == (
        False,
        "after_target_local_midnight",
    )


def test_forecast_feature_uses_no_target_actual():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    panel = synthetic_panel(module, protocol)
    row = module.build_forecast_feature(panel, protocol, "2026-07-14", "CISO")
    assert row["target_date"] == "2026-07-14"
    assert len(row["features"]) == 26
    assert "actual_mwh" not in row


def test_latest_target_rejects_backfill_and_accepts_future_forecast():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    panel = synthetic_panel(module, protocol)
    sealed_at = datetime(2026, 7, 13, 20, 0, tzinfo=timezone.utc)
    selected, skipped = module.latest_eligible_targets(panel, protocol, sealed_at)
    assert selected == {respondent: "2026-07-14" for respondent in protocol["balancing_authorities"]}
    assert skipped == {}


def test_append_only_hash_chain_detects_tampering(tmp_path):
    module = load_module()
    path = tmp_path / "chain.jsonl"
    first = module.append_chain_record(path, {"value": 1}, module.ZERO_HASH)
    second = module.append_chain_record(path, {"value": 2}, first["record_sha256"])
    records, terminal = module.load_chain(path)
    assert [row["value"] for row in records] == [1, 2]
    assert terminal == second["record_sha256"]

    lines = path.read_text(encoding="utf-8").splitlines()
    altered = json.loads(lines[0])
    altered["value"] = 999
    lines[0] = json.dumps(altered, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        module.load_chain(path)
    except ValueError as exc:
        assert "record hash mismatch" in str(exc)
    else:
        raise AssertionError("tampered chain was accepted")
