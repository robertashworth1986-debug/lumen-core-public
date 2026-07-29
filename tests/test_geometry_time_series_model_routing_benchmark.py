from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "geometry_time_series_model_routing_benchmark.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_time_series_model_routing_benchmark", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_extract_series_groups_and_sorts_rows_chronologically():
    module = load_module()
    snapshot = {
        "rows": [
            {"date": "2026-03-01", "series_id": "A", "value": "3.0"},
            {"date": "2026-01-01", "series_id": "A", "value": "1.0"},
            {"date": "2026-02-01", "series_id": "A", "value": "2.0"},
            {"date": "2026-02-01", "series_id": "B", "value": "20.0"},
            {"date": "2026-01-01", "series_id": "B", "value": "10.0"},
        ]
    }

    series = module.extract_series(snapshot, "TEST")

    assert [row["series_id"] for row in series] == ["A", "B"]
    assert series[0]["values"] == [1.0, 2.0, 3.0]
    assert series[1]["values"] == [10.0, 20.0]
    assert series[0]["value_field"] == "value"
    assert series[0]["first_time_key"] == "2026-01-01"
    assert series[0]["last_time_key"] == "2026-03-01"
    assert series[0]["duplicate_time_count"] == 0
    assert series[0]["prospective_confirmation_eligible"] is True


def test_extract_series_flags_duplicates_and_missing_value_compression():
    module = load_module()
    snapshot = {
        "rows": [
            {"date": "2026-01-01", "series_id": "A", "value": "1.0"},
            {"date": "2026-01-01", "series_id": "A", "value": "1.1"},
            {"date": "2026-01-02", "series_id": "A", "value": "."},
            {"date": "2026-01-03", "series_id": "A", "value": "3.0"},
        ]
    }

    series = module.extract_series(snapshot, "TEST")

    assert len(series) == 1
    assert series[0]["raw_row_count"] == 4
    assert series[0]["row_count"] == 3
    assert series[0]["duplicate_time_count"] == 1
    assert series[0]["missing_value_count"] == 1
    assert series[0]["calendar_compression_present"] is True
    assert series[0]["chronology_quality_pass"] is False
    assert series[0]["prospective_confirmation_eligible"] is False


def test_walk_forward_predictions_do_not_change_when_only_future_tail_changes():
    module = load_module()
    base_values = [100.0 + index + 0.1 * (index % 4) for index in range(64)]
    changed_values = list(base_values)
    changed_values[48:] = [value + 10_000.0 for value in changed_values[48:]]
    base = {
        "source": "TEST",
        "series_id": "S1",
        "value_field": "value",
        "values": base_values,
    }
    changed = {**base, "values": changed_values}

    before = module.evaluate_series(base)
    after = module.evaluate_series(changed)
    before_predictions = {
        (row["evaluation_unit"], row["strategy"]): row["predicted"]
        for row in before
        if row["origin"] <= 48
    }
    after_predictions = {
        (row["evaluation_unit"], row["strategy"]): row["predicted"]
        for row in after
        if row["origin"] <= 48
    }

    assert before_predictions
    assert before_predictions == after_predictions


def test_source_specific_baseline_parameters_separate_fred_cadences():
    module = load_module()

    monthly = module.source_baseline_parameters(
        {"source": "FRED", "series_id": "CPIAUCSL"}
    )
    daily = module.source_baseline_parameters(
        {"source": "FRED", "series_id": "DGS10"}
    )

    assert monthly == {
        "cadence": "monthly",
        "seasonal_period": 12,
        "autoregressive_lag": 12,
    }
    assert daily == {
        "cadence": "mixed",
        "seasonal_period": 5,
        "autoregressive_lag": 5,
    }


def test_evaluate_series_runs_only_registered_source_baselines_plus_candidate():
    module = load_module()
    series = {
        "source": "BLS",
        "series_id": "LABOR",
        "value_field": "value",
        "values": [100.0 + index + (index % 12) for index in range(48)],
        "source_specific_baseline_parameters": {
            "cadence": "monthly",
            "seasonal_period": 12,
            "autoregressive_lag": 12,
        },
    }

    rows = module.evaluate_series(
        series,
        {
            "naive_last",
            "seasonal_naive_source_period",
            "autoregressive_ridge_source_lag",
        },
    )

    assert {row["strategy"] for row in rows} == {
        "naive_last",
        "seasonal_naive_source_period",
        "autoregressive_ridge_source_lag",
        "fractal_brownian_surface",
    }
    seasonal = next(
        row for row in rows if row["strategy"] == "seasonal_naive_source_period"
    )
    assert seasonal["source_baseline_parameters"]["seasonal_period"] == 12
    candidate = next(
        row for row in rows if row["family_id"] == "fractal_brownian_surface"
    )
    assert candidate["estimator_id"] == (
        "hurst_conditioned_multiscale_increment_heuristic_v1"
    )


def test_eia_grid_extraction_uses_actual_demand_and_composite_series_key():
    module = load_module()
    snapshot = {
        "rows": [
            {
                "period": "2026-01-02",
                "respondent": "CISO",
                "timezone": "Pacific",
                "type": "DF",
                "value": 999.0,
            },
            {
                "period": "2026-01-02",
                "respondent": "CISO",
                "timezone": "Pacific",
                "type": "D",
                "value": 102.0,
            },
            {
                "period": "2026-01-01",
                "respondent": "CISO",
                "timezone": "Pacific",
                "type": "D",
                "value": 101.0,
            },
        ]
    }

    series = module.extract_series(snapshot, "EIA_GRID_VALIDATION")

    assert len(series) == 1
    assert series[0]["series_id"] == "CISO|D|Pacific"
    assert series[0]["values"] == [101.0, 102.0]
    assert "actual demand only" in series[0]["source_extraction_scope"]


def test_live_source_evaluation_reports_accepted_and_skipped_series(tmp_path):
    module = load_module()
    accepted_path = tmp_path / "accepted.json"
    skipped_path = tmp_path / "skipped.json"
    accepted_path.write_text(
        json.dumps(
            {
                "rows": [
                    {"date": f"2026-01-{index + 1:02d}", "symbol": "A", "close": 50.0 + index}
                    for index in range(30)
                ]
            }
        ),
        encoding="utf-8",
    )
    skipped_path.write_text(
        json.dumps({"rows": [{"date": "2026-01-01", "value": 1.0}]}),
        encoding="utf-8",
    )
    refs = [
        {"source": "ACCEPTED", "snapshot_json": accepted_path.name},
        {"source": "SKIPPED", "snapshot_json": skipped_path.name},
    ]

    rows, summary = module.evaluate_live_sources(refs, tmp_path)
    leaderboard = module.ranked_aggregate(module.aggregate(rows))
    gate = module.score_against_baseline(leaderboard)

    assert rows
    assert summary["accepted_source_count"] == 1
    assert summary["accepted_series_count"] == 1
    assert summary["skipped_source_count"] == 1
    assert summary["snapshot_hash_control"].startswith("registered snapshot")
    assert summary["leakage_control"].startswith("expanding history")
    assert {row["family_id"] for row in leaderboard} >= {
        "naive_last",
        "linear_trend",
        "fractal_brownian_surface",
    }
    assert gate["best_baseline"]["kind"] == "baseline"
    assert gate["best_geometry"]["family_id"] == "fractal_brownian_surface"


def test_live_source_evaluation_rejects_context_only_source_before_reading(tmp_path):
    module = load_module()
    path = tmp_path / "context.json"
    path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "date": f"2026-01-{index + 1:02d}",
                        "symbol": "A",
                        "close": 50.0 + index,
                    }
                    for index in range(30)
                ]
            }
        ),
        encoding="utf-8",
    )

    rows, summary = module.evaluate_live_sources(
        [
            {
                "source": "CONTEXT",
                "snapshot_json": path.name,
                "compatibility_mode": "context_only",
                "direct_performance_input_allowed": False,
            }
        ],
        tmp_path,
    )

    assert rows == []
    assert summary["accepted_source_count"] == 0
    assert summary["skipped_sources"][0]["reason"] == (
        "source_not_authorized_for_direct_measured_replay"
    )


def test_live_source_evaluation_rejects_snapshot_hash_mismatch(tmp_path):
    module = load_module()
    path = tmp_path / "measured.json"
    unsigned_snapshot = {
        "rows": [
            {
                "date": f"2026-01-{index + 1:02d}",
                "symbol": "A",
                "close": 50.0 + index,
            }
            for index in range(30)
        ]
    }
    observed = hashlib.sha256(
        json.dumps(
            unsigned_snapshot,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    assert observed != "0" * 64
    path.write_text(
        json.dumps({**unsigned_snapshot, "sha256": observed}),
        encoding="utf-8",
    )

    rows, summary = module.evaluate_live_sources(
        [
            {
                "source": "MEASURED",
                "snapshot_json": path.name,
                "snapshot_sha256": "0" * 64,
                "compatibility_mode": "direct_measured_replay",
                "direct_performance_input_allowed": True,
            }
        ],
        tmp_path,
    )

    assert rows == []
    assert summary["accepted_source_count"] == 0
    assert summary["skipped_sources"] == [
        {
            "source": "MEASURED",
            "reason": "snapshot_hash_mismatch",
            "snapshot_json": path.name,
            "hash_mode": "canonical_unsigned_payload",
            "expected_snapshot_sha256": "0" * 64,
            "embedded_snapshot_sha256": observed,
            "observed_snapshot_sha256": observed,
        }
    ]


def test_live_source_evaluation_accepts_canonical_snapshot_hash(tmp_path):
    module = load_module()
    path = tmp_path / "measured.json"
    unsigned_snapshot = {
        "rows": [
            {
                "date": f"2026-01-{index + 1:02d}",
                "symbol": "A",
                "close": 50.0 + index,
            }
            for index in range(30)
        ]
    }
    digest = hashlib.sha256(
        json.dumps(
            unsigned_snapshot,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    path.write_text(
        json.dumps({**unsigned_snapshot, "sha256": digest}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    rows, summary = module.evaluate_live_sources(
        [
            {
                "source": "MEASURED",
                "snapshot_json": path.name,
                "snapshot_sha256": digest,
                "compatibility_mode": "direct_measured_replay",
                "direct_performance_input_allowed": True,
            }
        ],
        tmp_path,
    )

    assert rows
    assert summary["accepted_source_count"] == 1
    assert summary["skipped_sources"] == []
    assert summary["verified_snapshot_hash_modes"] == ["canonical_unsigned_payload"]


def test_live_source_evaluation_accepts_registered_file_hash_without_embedded_digest(tmp_path):
    module = load_module()
    path = tmp_path / "measured.json"
    path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "date": f"2026-01-{index + 1:02d}",
                        "symbol": "A",
                        "close": 50.0 + index,
                    }
                    for index in range(30)
                ]
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    rows, summary = module.evaluate_live_sources(
        [
            {
                "source": "MEASURED",
                "snapshot_json": path.name,
                "snapshot_sha256": digest,
                "compatibility_mode": "direct_measured_replay",
                "direct_performance_input_allowed": True,
            }
        ],
        tmp_path,
    )

    assert rows
    assert summary["accepted_source_count"] == 1
    assert summary["skipped_sources"] == []
    assert summary["verified_snapshot_hash_modes"] == ["file_bytes"]


def test_live_source_evaluation_fails_closed_for_unimplemented_registered_baseline(tmp_path):
    module = load_module()
    path = tmp_path / "measured.json"
    path.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "date": f"2026-01-{index + 1:02d}",
                        "symbol": "A",
                        "close": 50.0 + index,
                    }
                    for index in range(30)
                ]
            }
        ),
        encoding="utf-8",
    )

    rows, summary = module.evaluate_live_sources(
        [
            {
                "source": "MEASURED",
                "snapshot_json": path.name,
                "source_specific_baselines": ["not_implemented"],
                "compatibility_mode": "direct_measured_replay",
                "direct_performance_input_allowed": True,
            }
        ],
        tmp_path,
    )

    assert rows == []
    assert summary["accepted_source_count"] == 0
    assert summary["skipped_sources"][0]["reason"] == (
        "registered_baseline_implementation_missing"
    )
    assert summary["skipped_sources"][0]["missing_baselines"] == [
        "not_implemented"
    ]
