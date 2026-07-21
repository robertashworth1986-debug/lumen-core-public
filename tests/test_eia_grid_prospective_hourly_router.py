from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
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


def test_module_import_does_not_load_optional_ml_runtime():
    script = (
        "import importlib.util,json,sys;"
        f"p={str(MODULE_PATH)!r};"
        "s=importlib.util.spec_from_file_location('eia_hourly_import_probe',p);"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        "print(json.dumps({k:(k in sys.modules) for k in "
        "['lightgbm','numpy','xgboost','sklearn']}))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        check=False,
        text=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "lightgbm": False,
        "numpy": False,
        "xgboost": False,
        "sklearn": False,
    }


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


def test_eligible_target_scan_reports_each_authority_without_changing_selection():
    module = load_module()
    panel, protocol = synthetic_panel(module)
    series = module.series_by_authority(panel, protocol)

    selected, skipped, diagnostics = module.eligible_target_scan(
        series, protocol, datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
    )

    assert ("ERCO", "2026-07-15T14") in selected
    assert skipped == {}
    assert list(diagnostics) == protocol["balancing_authorities"]
    assert diagnostics["ERCO"]["eligible_target_count"] == 1
    assert diagnostics["ERCO"]["skipped"] == {}
    assert diagnostics["SWPP"]["eligible_target_count"] == 0
    assert diagnostics["TVA"]["eligible_target_count"] == 0


def test_seal_attributes_feature_failure_to_the_blocked_authority(
    tmp_path, monkeypatch
):
    module = load_module()
    panel, protocol = synthetic_panel(module)
    monkeypatch.setattr(module, "PREDICTIONS_PATH", tmp_path / "predictions.jsonl")

    def reject_incomplete_window(*_args, **_kwargs):
        raise ValueError("weekly residual window is incomplete")

    monkeypatch.setattr(module, "build_feature_row", reject_incomplete_window)
    result = module.seal_from_panel(
        protocol,
        panel,
        {"source": "synthetic"},
        datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc),
        dry_run=True,
    )

    erco = result["authority_diagnostics"]["ERCO"]
    assert result["sealed_record_count"] == 0
    assert result["skipped"] == {"weekly residual window is incomplete": 1}
    assert erco["eligible_target_count"] == 1
    assert erco["pending_target_count"] == 1
    assert erco["feature_ready_count"] == 0
    assert erco["sealed_record_count"] == 0
    assert erco["feature_blockers"] == {"weekly residual window is incomplete": 1}
    assert erco["skipped"] == {"weekly residual window is incomplete": 1}


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


def test_text_file_hash_is_stable_across_line_endings(tmp_path):
    module = load_module()
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    lf.write_bytes(b'{"value":1}\n')
    crlf.write_bytes(b'{"value":1}\r\n')
    assert module.file_sha256(lf) == module.file_sha256(crlf)


def test_status_exposes_missing_authorities_without_promoting_sample_gate():
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    target = "2026-07-15T14"
    active = protocol["balancing_authorities"][:6]
    candidates = [row["id"] for row in protocol["candidates"]]
    predictions = [
        {"respondent": authority, "target_period_end_utc": target}
        for authority in active
    ]
    settlements = [
        {
            "respondent": authority,
            "target_period_end_utc": target,
            "candidate_metrics": {
                candidate: {"scaled_absolute_error": 0.5}
                for candidate in candidates
            },
            "router_scaled_absolute_error": 0.5,
        }
        for authority in active
    ]
    source_readiness = {
        authority: {
            "eligible_target_count": 1,
            "pending_target_count": 1,
            "eligible_target_already_sealed_count": 0,
            "feature_ready_count": 0,
            "sealed_record_count": 0,
            "feature_blockers": {"weekly residual window is incomplete": 1},
            "skipped": {"weekly residual window is incomplete": 1},
        }
        for authority in ("SWPP", "TVA")
    }

    status = module.build_status(
        protocol, predictions, settlements, source_readiness
    )
    coverage = status["authority_coverage"]

    assert status["common_settled_hour_count"] == 0
    assert status["sample_gates"] == {
        "preliminary_ready": False,
        "confirmatory_ready": False,
        "durability_ready": False,
        "note": "Sample readiness does not mean a scientific promotion gate passed.",
    }
    assert coverage["required_authority_count"] == 8
    assert coverage["authorities_without_predictions"] == ["SWPP", "TVA"]
    assert coverage["authorities_without_settlements"] == ["SWPP", "TVA"]
    assert coverage["max_authorities_settled_on_same_period"] == 6
    assert coverage["by_authority"]["CISO"]["settlement_count"] == 1
    assert coverage["by_authority"]["SWPP"]["settlement_count"] == 0
    assert status["latest_seal_source_readiness_by_authority"] == source_readiness
