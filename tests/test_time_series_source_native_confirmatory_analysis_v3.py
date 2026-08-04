from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "time_series_source_native_confirmatory_analysis_v3.py"


def load_module():
    spec = importlib.util.spec_from_file_location("confirmatory_v3", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def utc_text(day: date, hour: int = 12) -> str:
    return datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def add_months(start: date, count: int) -> list[date]:
    result = []
    year = start.year
    month = start.month
    for _ in range(count):
        result.append(date(year, month, 1))
        month += 1
        if month == 13:
            year += 1
            month = 1
    return result


def make_protocol(module, *, fred_horizons: list[int] | None = None) -> dict:
    protocol = {
        "schema": "time_series_source_native_prospective_protocol.v3",
        "protocol_id": "TEST_CONFIRMATORY_V3",
        "freeze": {"freeze_utc": "2000-01-01T00:00:00Z"},
        "candidate": {"registered_family_id": "candidate"},
        "registered_baselines": [f"baseline_{index}" for index in range(8)],
        "ledger_contract": {
            "settlement_schema": "time_series_source_native_settlement.v3"
        },
        "sources": [
            {
                "source": "FRED",
                "series": [
                    {
                        "series_id": "FRED_SERIES",
                        "horizons": fred_horizons or [1],
                    }
                ],
            },
            {
                "source": "TWELVE_DATA",
                "series": [{"series_id": "TD_SERIES", "horizons": [1]}],
            },
        ],
        "analysis_contract": {
            "source_arms": ["FRED", "TWELVE_DATA"],
            "contrast_count": 16,
            "cell_definition": "source-series-horizon",
            "cell_weighting": "equal_mean_log_rmae",
            "familywise_error_rate": 0.05,
            "bootstrap_replications": 20000,
            "bootstrap_seed": 2026072901,
            "quantile_method": "linear",
            "bootstrap_by_source": {
                "FRED": {
                    "cluster_grain": "calendar_month",
                    "block_length": 6,
                    "minimum_clusters": 60,
                },
                "TWELVE_DATA": {
                    "cluster_grain": "exchange_week_monday",
                    "block_length": 8,
                    "minimum_clusters": 104,
                },
            },
        },
        "decision_rule": {
            "effect_floor_max_rmae": 0.95,
            "cell_rmae_max": 1.05,
            "p95_error_ratio_max": 1.10,
            "upper_confidence_level": 0.95,
            "require_all_contrasts_each_arm": True,
            "require_independent_replication_period": True,
        },
        "period_contract": {
            "first_confirmatory_period": {
                "period_id": "V3_CONFIRMATORY_P1",
                "target_period_start_inclusive": "2000-01-02",
                "target_period_end_inclusive": "2005-02-01",
            },
            "independent_replication_period": {
                "period_id": "V3_REPLICATION_P2",
                "target_period_start_inclusive": "2005-02-02",
                "target_period_end_inclusive": "2010-04-01",
            },
            "replication_reuses_first_period_rows": False,
        },
    }
    protocol["protocol_payload_sha256"] = module.protocol_payload_sha256(protocol)
    return protocol


def make_record(
    protocol: dict,
    *,
    period_id: str,
    source: str,
    target: date,
    horizon: int = 1,
    candidate_error: float = 0.5,
    baseline_errors: dict[str, float] | None = None,
) -> dict:
    baseline_errors = baseline_errors or {
        baseline: 1.0 for baseline in protocol["registered_baselines"]
    }
    series_id = "FRED_SERIES" if source == "FRED" else "TD_SERIES"
    actual = 100.0
    predictions = {"candidate": actual - candidate_error}
    predictions.update(
        {baseline: actual - baseline_errors[baseline] for baseline in protocol["registered_baselines"]}
    )
    identity = f"{period_id}|{source}|{series_id}|{horizon}|{target.isoformat()}"
    record_hash = hashlib.sha256(f"settlement|{identity}".encode("ascii")).hexdigest()
    prediction_hash = hashlib.sha256(f"prediction|{identity}".encode("ascii")).hexdigest()
    return {
        "schema": "time_series_source_native_settlement.v3",
        "protocol_id": protocol["protocol_id"],
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "record_sha256": record_hash,
        "prediction_record_sha256": prediction_hash,
        "source": source,
        "series_id": series_id,
        "horizon": horizon,
        "period_id": period_id,
        "target_period": target.isoformat(),
        "actual_observed_at_utc": utc_text(target),
        "actual": actual,
        "release_order_proof": (
            {
                "passed": True,
                "conservative_release_boundary_utc": utc_text(target, hour=0),
            }
            if source == "FRED"
            else {
                "passed": True,
                "exchange_timezone": "America/New_York",
            }
        ),
        "verification": {
            "chain_record_verified": True,
            "prediction_reference_verified": True,
            "protocol_binding_verified": True,
        },
        "strategy_metrics": {
            strategy_id: {
                "prediction": prediction,
                "absolute_error": abs(actual - prediction),
            }
            for strategy_id, prediction in predictions.items()
        },
    }


def make_period_rows(
    protocol: dict,
    *,
    period_id: str,
    fred_start: date,
    twelve_start_monday: date,
    fred_count: int = 60,
    twelve_count: int = 104,
) -> list[dict]:
    rows = [
        make_record(protocol, period_id=period_id, source="FRED", target=target)
        for target in add_months(fred_start, fred_count)
    ]
    rows.extend(
        make_record(
            protocol,
            period_id=period_id,
            source="TWELVE_DATA",
            target=twelve_start_monday + timedelta(weeks=index),
        )
        for index in range(twelve_count)
    )
    return rows


def make_anchor_coverage(
    protocol: dict,
    first_rows: list[dict],
    second_rows: list[dict] | None = None,
    *,
    reuse_receipt: bool = False,
) -> dict:
    first_cutoff = "2005-02-01T00:00:00Z"
    first_receipt = "b" * 64
    periods = [
        {
            "period_id": "V3_CONFIRMATORY_P1",
            "anchors": [
                {
                    "anchor_receipt_sha256": first_receipt,
                    "anchor_subject_sha256": "c" * 64,
                    "verified": True,
                    "independent": True,
                    "anchored_at_utc": "2000-01-01T01:00:00Z",
                    "covered_prediction_record_sha256": [
                        row["prediction_record_sha256"] for row in first_rows
                    ],
                }
            ],
        }
    ]
    coverage = {
        "schema": "time_series_source_native_anchor_coverage.v3",
        "protocol_id": protocol["protocol_id"],
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "verification_complete": True,
        "analysis_as_of_utc": "2005-02-02T12:00:00Z",
        "periods": periods,
    }
    if second_rows is not None:
        periods.append(
            {
                "period_id": "V3_REPLICATION_P2",
                "anchors": [
                    {
                        "anchor_receipt_sha256": first_receipt if reuse_receipt else "d" * 64,
                        "anchor_subject_sha256": "e" * 64,
                        "verified": True,
                        "independent": True,
                        "anchored_at_utc": "2005-02-02T00:00:00Z",
                        "covered_prediction_record_sha256": [
                            row["prediction_record_sha256"] for row in second_rows
                        ],
                    }
                ],
            }
        )
        coverage["analysis_as_of_utc"] = "2010-04-02T12:00:00Z"
    return coverage


def full_fixture(module):
    protocol = make_protocol(module)
    first_rows = make_period_rows(
        protocol,
        period_id="V3_CONFIRMATORY_P1",
        fred_start=date(2000, 2, 1),
        twelve_start_monday=date(2000, 1, 3),
    )
    second_rows = make_period_rows(
        protocol,
        period_id="V3_REPLICATION_P2",
        fred_start=date(2005, 3, 1),
        twelve_start_monday=date(2005, 2, 7),
    )
    coverage = make_anchor_coverage(protocol, first_rows, second_rows)
    return protocol, first_rows, second_rows, coverage


def test_protocol_requires_production_bootstrap_contract() -> None:
    module = load_module()
    protocol = make_protocol(module)
    assert module.validate_protocol(protocol) == []
    protocol["analysis_contract"]["bootstrap_replications"] = 499
    protocol["protocol_payload_sha256"] = module.protocol_payload_sha256(protocol)
    assert "bootstrap_replications_must_equal_20000" in module.validate_protocol(protocol)


def test_holm_adjustment_is_stable_and_order_preserving() -> None:
    module = load_module()
    adjusted = module.holm_adjust([0.01, 0.04, 0.03])
    assert adjusted == pytest.approx([0.03, 0.06, 0.06])


def test_complete_two_period_evidence_promotes_with_synchronized_dependence_plan() -> None:
    module = load_module()
    protocol, first_rows, second_rows, coverage = full_fixture(module)
    report = module.analyze_confirmatory(
        [*first_rows, *second_rows],
        coverage,
        protocol,
        _test_bootstrap_replications=499,
    )

    assert report["decision"] == "PROMOTION_SUPPORTED"
    assert report["promotion_supported"] is True
    assert report["bounded_forecasting_claim_supported"] is True
    assert report["test_only_replication_override_used"] is True
    assert len(report["periods"]) == 2
    for period in report["periods"]:
        assert len(period["contrast_order"]) == 16
        assert period["period_criteria_satisfied"] is True
        for arm in period["arms"]:
            hashes = {item["bootstrap_plan_sha256"] for item in arm["contrasts"]}
            assert hashes == {arm["bootstrap_plan_sha256"]}
            assert len(arm["contrasts"]) == 8
            assert all(item["all_decision_gates_passed"] for item in arm["contrasts"])
    rendered = json.dumps(report).lower()
    assert "trading" not in rendered
    assert '"alpha"' not in rendered


def test_missing_registered_cell_fails_closed() -> None:
    module = load_module()
    protocol = make_protocol(module, fred_horizons=[1, 3])
    first_rows = make_period_rows(
        protocol,
        period_id="V3_CONFIRMATORY_P1",
        fred_start=date(2000, 2, 1),
        twelve_start_monday=date(2000, 1, 3),
    )
    coverage = make_anchor_coverage(protocol, first_rows)
    report = module.analyze_confirmatory(
        first_rows,
        coverage,
        protocol,
        _test_bootstrap_replications=99,
    )

    assert report["promotion_supported"] is False
    assert report["decision"] == "INCONCLUSIVE"
    fred = report["periods"][0]["arms"][0]
    assert fred["missing_cells"] == [{"series_id": "FRED_SERIES", "horizon": 3}]


def test_zero_mae_denominator_is_invalid() -> None:
    module = load_module()
    protocol = make_protocol(module)
    first_rows = make_period_rows(
        protocol,
        period_id="V3_CONFIRMATORY_P1",
        fred_start=date(2000, 2, 1),
        twelve_start_monday=date(2000, 1, 3),
    )
    for row in first_rows:
        metric = row["strategy_metrics"]["baseline_0"]
        metric["prediction"] = row["actual"]
        metric["absolute_error"] = 0.0
    coverage = make_anchor_coverage(protocol, first_rows)
    report = module.analyze_confirmatory(
        first_rows,
        coverage,
        protocol,
        _test_bootstrap_replications=99,
    )

    assert report["decision"] == "INVALID"
    assert report["promotion_supported"] is False
    first_contrast = report["periods"][0]["arms"][0]["contrasts"][0]
    assert any("baseline_mae_denominator_invalid" in item for item in first_contrast["errors"])


def test_insufficient_source_clusters_never_promote() -> None:
    module = load_module()
    protocol = make_protocol(module)
    first_rows = make_period_rows(
        protocol,
        period_id="V3_CONFIRMATORY_P1",
        fred_start=date(2000, 2, 1),
        twelve_start_monday=date(2000, 1, 3),
        fred_count=59,
        twelve_count=103,
    )
    coverage = make_anchor_coverage(protocol, first_rows)
    report = module.analyze_confirmatory(
        first_rows,
        coverage,
        protocol,
        _test_bootstrap_replications=99,
    )

    assert report["decision"] == "INCONCLUSIVE"
    assert report["promotion_supported"] is False
    assert all(not arm["sample_gate_passed"] for arm in report["periods"][0]["arms"])


def test_complete_but_tail_error_gate_failure_is_not_supported() -> None:
    module = load_module()
    protocol = make_protocol(module)
    first_rows = make_period_rows(
        protocol,
        period_id="V3_CONFIRMATORY_P1",
        fred_start=date(2000, 2, 1),
        twelve_start_monday=date(2000, 1, 3),
    )
    for source in ("FRED", "TWELVE_DATA"):
        source_rows = [row for row in first_rows if row["source"] == source]
        tail_count = max(1, int(len(source_rows) * 0.06) + 1)
        for row in source_rows[-tail_count:]:
            metric = row["strategy_metrics"]["candidate"]
            metric["prediction"] = row["actual"] - 2.0
            metric["absolute_error"] = 2.0
    coverage = make_anchor_coverage(protocol, first_rows)
    report = module.analyze_confirmatory(
        first_rows,
        coverage,
        protocol,
        _test_bootstrap_replications=99,
    )

    assert report["decision"] == "PERIOD_CRITERIA_NOT_SATISFIED"
    assert report["promotion_supported"] is False
    assert all(
        not arm["contrasts"][0]["p95_limit_passed"]
        for arm in report["periods"][0]["arms"]
    )


def test_replication_requires_a_separate_verified_anchor_receipt() -> None:
    module = load_module()
    protocol, first_rows, second_rows, _ = full_fixture(module)
    coverage = make_anchor_coverage(
        protocol,
        first_rows,
        second_rows,
        reuse_receipt=True,
    )
    report = module.analyze_confirmatory(
        [*first_rows, *second_rows],
        coverage,
        protocol,
        _test_bootstrap_replications=99,
    )

    assert report["decision"] == "INVALID"
    assert report["promotion_supported"] is False
    assert "replication_must_use_separate_anchor_receipts" in report["errors"]


def test_settlement_period_id_must_match_frozen_target_window() -> None:
    module = load_module()
    protocol = make_protocol(module)
    first_rows = make_period_rows(
        protocol,
        period_id="V3_CONFIRMATORY_P1",
        fred_start=date(2000, 2, 1),
        twelve_start_monday=date(2000, 1, 3),
    )
    coverage = make_anchor_coverage(protocol, first_rows)
    first_rows[0]["period_id"] = "V3_REPLICATION_P2"
    report = module.analyze_confirmatory(
        first_rows,
        coverage,
        protocol,
        _test_bootstrap_replications=99,
    )

    assert report["decision"] == "INVALID"
    assert report["promotion_supported"] is False
    assert "settlement_period_id_mismatch" in report["errors"]


def test_replication_helper_rejects_shared_targets_even_if_metadata_is_tampered() -> None:
    module = load_module()
    protocol, first_rows, second_rows, coverage = full_fixture(module)
    tampered = copy.deepcopy(second_rows[0])
    tampered["record_sha256"] = "f" * 64
    tampered["target_period"] = first_rows[0]["target_period"]
    tampered["actual_observed_at_utc"] = "2005-03-01T12:00:00Z"
    coverage["periods"][1]["anchors"][0]["covered_prediction_record_sha256"].append(
        tampered["prediction_record_sha256"]
    )
    with pytest.raises(module.ConfirmatoryInputError):
        module.split_nonoverlapping_replication_periods(
            [*first_rows, *second_rows, tampered], coverage, protocol
        )


def test_first_period_alone_can_only_request_replication() -> None:
    module = load_module()
    protocol = make_protocol(module)
    first_rows = make_period_rows(
        protocol,
        period_id="V3_CONFIRMATORY_P1",
        fred_start=date(2000, 2, 1),
        twelve_start_monday=date(2000, 1, 3),
    )
    coverage = make_anchor_coverage(protocol, first_rows)
    report = module.analyze_confirmatory(
        first_rows,
        coverage,
        protocol,
        _test_bootstrap_replications=499,
    )

    assert report["decision"] == "INCONCLUSIVE_REPLICATION_REQUIRED"
    assert report["promotion_supported"] is False
    assert report["periods"][0]["period_criteria_satisfied"] is True
