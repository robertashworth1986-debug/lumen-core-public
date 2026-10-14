"""Offline v2 review guards; these fixtures do not refit or promote v1."""

from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "forecast_evaluation_v2.py"
PROTOCOL = ROOT / "config" / "forecast_evaluation_protocol_v2_synthetic.json"
FIXTURES = ROOT / "tests" / "fixtures" / "forecast_evaluation_v2"
REVIEW_NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def module():
    spec = importlib.util.spec_from_file_location("forecast_evaluation_v2", SCRIPT)
    assert spec is not None and spec.loader is not None
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


@pytest.fixture
def inputs(tmp_path):
    paths = {}
    for key, source in (
        ("protocol", PROTOCOL),
        ("predictions", FIXTURES / "predictions.csv"),
        ("history", FIXTURES / "history.csv"),
    ):
        target = tmp_path / source.name
        target.write_bytes(source.read_bytes())
        paths[key] = target
    return paths


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(module, inputs, protocol_sha256=None):
    return module.evaluate_files(
        inputs["protocol"],
        inputs["predictions"],
        inputs["history"],
        digest(inputs["protocol"]) if protocol_sha256 is None else protocol_sha256,
        now=REVIEW_NOW,
    )


def read_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def write_rows(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def change_protocol(inputs, key, value):
    protocol = json.loads(inputs["protocol"].read_text(encoding="utf-8"))
    protocol[key] = value
    inputs["protocol"].write_text(json.dumps(protocol), encoding="utf-8")


def test_fixture_evaluates_deterministically_without_promoting(module, inputs):
    report = evaluate(module, inputs)
    assert evaluate(module, inputs) == report
    assert report["schema"] == "forecast_evaluation_review.v2"
    assert report["status"] == "HUMAN_REVIEW_HOLD"
    assert report["evidence_type"] == "synthetic"
    assert report["promotion_gate_passed"] is False
    assert report["production_authorized"] is False
    assert report["external_validation_complete"] is False
    assert report["identities"]["paired_target_count"] == 6
    assert report["identities"]["entity_count"] == 2
    assert report["identities"]["all_strategy_identity_sets_exact"] is True
    assert report["inputs"] == {
        key: digest(path) for key, path in inputs.items()
    }
    unsigned = {key: value for key, value in report.items() if key != "receipt_sha256"}
    expected_digest = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    assert report["receipt_sha256"] == expected_digest


def test_fixture_preserves_manual_metrics_and_entity_regression(module, inputs):
    report = evaluate(module, inputs)
    summary = report["strategy_summary"]
    # Six dates share a seven-calendar-day scale of 70 MWh. The candidate has
    # three 5-MWh errors and three 20-MWh errors; incumbent errors are all 10.
    expected_errors = {"candidate_v2": 12.5, "incumbent_fixture": 10.0, "algorithmic_fixture": 15.0}
    assert set(summary) == set(expected_errors)
    for strategy, error in expected_errors.items():
        assert summary[strategy]["row_count"] == 6
        assert summary[strategy]["mae_mwh"] == pytest.approx(error)
        assert summary[strategy]["mean_seasonal_mase_7"] == pytest.approx(error / 70)
    comparisons = {item["baseline"]: item for item in report["baseline_comparisons"]}
    assert set(comparisons) == {"incumbent_fixture", "algorithmic_fixture"}
    incumbent = comparisons["incumbent_fixture"]
    assert incumbent["mean_skill_delta"] == pytest.approx(-2.5 / 70)
    assert incumbent["entity_mean_skill"] == pytest.approx({"FIXTURE_A": 5 / 70, "FIXTURE_B": -10 / 70})
    for item in comparisons.values():
        assert item["paired_target_count"] == 6
        assert item["p_value"] is None
        assert item["confidence_interval"] is None
        assert "dependence" in item["interpretation"].lower()
    assert all(item["seasonal_scale_mwh"] == pytest.approx(70) for item in report["history_diagnostics"])


@pytest.mark.parametrize("candidate_error", [0, 100])
def test_candidate_perfect_or_worse_still_requires_human_review(module, inputs, candidate_error):
    fields, rows = read_rows(inputs["predictions"])
    for row in rows:
        if row["strategy"] == "candidate_v2":
            row["predicted_mwh"] = str(float(row["actual_mwh"]) + candidate_error)
    write_rows(inputs["predictions"], fields, rows)
    report = evaluate(module, inputs)
    assert report["strategy_summary"]["candidate_v2"]["mae_mwh"] == pytest.approx(candidate_error)
    assert report["status"] == "HUMAN_REVIEW_HOLD"
    assert report["promotion_gate_passed"] is False
    assert report["production_authorized"] is False
    assert all(item["p_value"] is None and item["confidence_interval"] is None for item in report["baseline_comparisons"])


@pytest.mark.parametrize("claimed_digest", ["", "0" * 64, "bad", None])
def test_protocol_identity_is_required_and_exact(module, inputs, claimed_digest):
    # None must be supplied explicitly so it cannot select our test helper default.
    with pytest.raises((ValueError, TypeError)):
        module.evaluate_files(
            inputs["protocol"], inputs["predictions"], inputs["history"],
            claimed_digest, now=REVIEW_NOW,
        )


def test_byte_change_cannot_reuse_previous_protocol_digest(module, inputs):
    original_digest = digest(inputs["protocol"])
    with inputs["protocol"].open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError):
        evaluate(module, inputs, original_digest)
    # JSON whitespace does not change policy, but does change its required identity.
    evaluate(module, inputs)


@pytest.mark.parametrize(("key", "value"), [
    ("inference", "independent_authority_month_sign_test"),
    ("promotion", "PASS"),
    ("owner_acceptance_reference", " "),
    ("baseline_scope_reference", ""),
    ("scope_match_declared", False),
    ("grain", "observation_index"),
    ("time_zone", "America/New_York"),
    ("unit", "megawatts"),
    ("candidate_strategy", "incumbent_fixture"),
    ("baseline_strategies", []),
    ("baseline_strategies", ["incumbent_fixture", "incumbent_fixture"]),
    ("entities", []),
    ("entities", ["FIXTURE_A", "FIXTURE_A"]),
    ("locked_at_utc", "2026-10-14T04:00:00Z"),
    ("locked_at_utc", "2026-10-15T03:00:00Z"),
])
def test_digest_does_not_accept_invalid_or_unlocked_policy(module, inputs, key, value):
    change_protocol(inputs, key, value)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


def test_duplicate_protocol_json_key_fails_even_with_matching_digest(module, inputs):
    raw = inputs["protocol"].read_text(encoding="utf-8")
    inputs["protocol"].write_text(raw.replace('"schema":', '"schema": "forecast_evaluation_protocol.v2", "schema":', 1), encoding="utf-8")
    with pytest.raises(ValueError):
        evaluate(module, inputs)


def test_every_strategy_missing_same_target_cannot_pass_common_intersection(module, inputs):
    fields, rows = read_rows(inputs["predictions"])
    first = rows[0]
    rows = [row for row in rows if (row["entity_id"], row["target_date"]) != (first["entity_id"], first["target_date"])]
    write_rows(inputs["predictions"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


def test_unknown_strategy_cannot_replace_a_required_baseline(module, inputs):
    fields, rows = read_rows(inputs["predictions"])
    for row in rows:
        if row["strategy"] == "incumbent_fixture":
            row["strategy"] = "unregistered_baseline"
    write_rows(inputs["predictions"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


@pytest.mark.parametrize("damage", ["missing_target", "missing_entity", "duplicate", "extra_entity", "extra_target"])
def test_every_strategy_requires_exact_scheduled_identity_set(module, inputs, damage):
    fields, original = read_rows(inputs["predictions"])
    strategies = sorted({row["strategy"] for row in original})
    for strategy in strategies:
        rows = copy.deepcopy(original)
        index = next(i for i, row in enumerate(rows) if row["strategy"] == strategy)
        selected = rows[index]
        if damage == "missing_target":
            rows.pop(index)
        elif damage == "missing_entity":
            rows = [row for row in rows if not (
                row["strategy"] == strategy and row["entity_id"] == selected["entity_id"]
            )]
        elif damage == "duplicate":
            rows.append(copy.deepcopy(selected))
        else:
            extra = copy.deepcopy(selected)
            extra["entity_id" if damage == "extra_entity" else "target_date"] = (
                "UNSCHEDULED" if damage == "extra_entity" else "2026-10-17"
            )
            rows.append(extra)
        write_rows(inputs["predictions"], fields, rows)
        with pytest.raises(ValueError):
            evaluate(module, inputs)


@pytest.mark.parametrize("identity_column", ["actual_mwh", "actual_available_at_utc"])
def test_all_strategy_pairs_bind_the_same_outcome(module, inputs, identity_column):
    fields, rows = read_rows(inputs["predictions"])
    original = copy.deepcopy(rows)
    for strategy in sorted({row["strategy"] for row in rows}):
        rows = copy.deepcopy(original)
        selected = next(row for row in rows if row["strategy"] == strategy)
        selected[identity_column] = (
            str(float(selected[identity_column]) + 1)
            if identity_column == "actual_mwh" else "2026-10-19T03:00:00Z"
        )
        write_rows(inputs["predictions"], fields, rows)
        with pytest.raises(ValueError):
            evaluate(module, inputs)


def test_prediction_order_cannot_change_report(module, inputs):
    report = evaluate(module, inputs)
    fields, rows = read_rows(inputs["predictions"])
    write_rows(inputs["predictions"], fields, list(reversed(rows)))
    reordered = evaluate(module, inputs)
    # Content digests must change; scoring and acceptance must not depend on CSV order.
    assert report["status"] == reordered["status"] == "HUMAN_REVIEW_HOLD"
    for key in ("strategy_summary", "baseline_comparisons", "history_diagnostics", "identities"):
        assert report[key] == reordered[key]


@pytest.mark.parametrize("column", ["actual_mwh", "predicted_mwh"])
@pytest.mark.parametrize("invalid_value", ["NaN", "Infinity", "-Infinity", "", "not-a-number"])
def test_nonfinite_or_missing_scoring_values_fail_closed(module, inputs, column, invalid_value):
    fields, rows = read_rows(inputs["predictions"])
    rows[0][column] = invalid_value
    write_rows(inputs["predictions"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


@pytest.mark.parametrize("column", ["issued_at_utc", "prediction_available_at_utc", "actual_available_at_utc"])
@pytest.mark.parametrize("invalid_timestamp", ["2026-10-14T04:00:00", "2026-10-14", "bad-timestamp"])
def test_as_of_timestamps_cannot_omit_utc_timezone(module, inputs, column, invalid_timestamp):
    fields, rows = read_rows(inputs["predictions"])
    rows[0][column] = invalid_timestamp
    write_rows(inputs["predictions"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


@pytest.mark.parametrize("late_time", ["04:00:01", "04:00:00.000001"])
def test_forecast_published_after_issue_cannot_enter_score(module, inputs, late_time):
    fields, rows = read_rows(inputs["predictions"])
    rows[0]["prediction_available_at_utc"] = rows[0]["issued_at_utc"].replace("04:00:00", late_time)
    write_rows(inputs["predictions"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


@pytest.mark.parametrize("timestamp_source", ["issued_at_utc", "prediction_available_at_utc", "actual_available_at_utc", "history", "protocol"])
def test_submicrosecond_timestamps_cannot_be_silently_rounded(module, inputs, timestamp_source):
    if timestamp_source == "protocol":
        protocol = json.loads(inputs["protocol"].read_text(encoding="utf-8"))
        change_protocol(inputs, "locked_at_utc", protocol["locked_at_utc"][:-1] + ".0000009Z")
    else:
        input_name = "history" if timestamp_source == "history" else "predictions"
        column = "actual_available_at_utc" if input_name == "history" else timestamp_source
        fields, rows = read_rows(inputs[input_name])
        rows[0][column] = rows[0][column][:-1] + ".0000009Z"
        write_rows(inputs[input_name], fields, rows)
    with pytest.raises(ValueError, match="at most six fractional digits"):
        evaluate(module, inputs)


@pytest.mark.parametrize("timestamp", ["20261014T040000Z", "2026-10-14 04:00:00Z", "2026-W42-3T04:00:00Z"])
def test_timestamp_aliases_cannot_replace_declared_calendar_utc_format(module, timestamp):
    with pytest.raises(ValueError):
        module._utc(timestamp)


@pytest.mark.parametrize(("fraction", "microseconds"), [("", 0), (".1", 100000), (".000001", 1), (".123456", 123456)])
def test_supported_timestamp_precision_is_preserved_exactly(module, fraction, microseconds):
    assert module._utc(f"2026-10-14T04:00:00{fraction}Z") == datetime(2026, 10, 14, 4, microsecond=microseconds, tzinfo=timezone.utc)


def test_forecasts_and_history_available_exactly_at_issue_are_allowed(module, inputs):
    fields, rows = read_rows(inputs["predictions"])
    for row in rows:
        row["prediction_available_at_utc"] = row["issued_at_utc"]
    write_rows(inputs["predictions"], fields, rows)
    history_fields, history = read_rows(inputs["history"])
    for row in history:
        if row["date"] == "2026-10-13":
            row["actual_available_at_utc"] = "2026-10-14T04:00:00Z"
    write_rows(inputs["history"], history_fields, history)
    assert evaluate(module, inputs)["status"] == "HUMAN_REVIEW_HOLD"


def test_buyer_outcomes_cannot_be_claimed_before_observed_evaluation_time(module, inputs):
    change_protocol(inputs, "evidence_type", "buyer_supplied")
    assert evaluate(module, inputs)["status"] == "HUMAN_REVIEW_HOLD"
    with pytest.raises(ValueError):
        module.evaluate_files(
            inputs["protocol"], inputs["predictions"], inputs["history"],
            digest(inputs["protocol"]), now=datetime(2026, 10, 14, 4, tzinfo=timezone.utc),
        )


def test_evaluation_clock_requires_aware_utc(module, inputs):
    with pytest.raises(ValueError):
        module.evaluate_files(
            inputs["protocol"], inputs["predictions"], inputs["history"],
            digest(inputs["protocol"]), now=datetime(2026, 10, 20),
        )


def test_actual_known_at_issue_cannot_enter_future_forecast_score(module, inputs):
    fields, rows = read_rows(inputs["predictions"])
    first = rows[0]
    for row in rows:
        if (row["entity_id"], row["target_date"]) == (first["entity_id"], first["target_date"]):
            row["actual_available_at_utc"] = row["issued_at_utc"]
    write_rows(inputs["predictions"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


def test_issue_schedule_is_locked_for_every_strategy(module, inputs):
    fields, rows = read_rows(inputs["predictions"])
    rows[0]["issued_at_utc"] = rows[0]["issued_at_utc"].replace("04:00:00", "05:00:00")
    write_rows(inputs["predictions"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


def test_duplicate_history_dates_are_rejected_even_if_values_match(module, inputs):
    fields, rows = read_rows(inputs["history"])
    rows.append(copy.deepcopy(rows[0]))
    write_rows(inputs["history"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


def test_history_availability_after_issue_cannot_supply_lag(module, inputs):
    _, predictions = read_rows(inputs["predictions"])
    first = predictions[0]
    fields, rows = read_rows(inputs["history"])
    lag_date = str(date.fromisoformat(first["target_date"]) - timedelta(days=1))
    selected = next(row for row in rows if row["entity_id"] == first["entity_id"] and row["date"] == lag_date)
    selected["actual_available_at_utc"] = "2026-10-14T04:00:01Z"
    write_rows(inputs["history"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


def test_calendar_gap_cannot_silently_become_previous_observation(module, inputs):
    _, predictions = read_rows(inputs["predictions"])
    first = predictions[0]
    fields, rows = read_rows(inputs["history"])
    lag_date = str(date.fromisoformat(first["target_date"]) - timedelta(days=1))
    rows = [row for row in rows if not (
        row["entity_id"] == first["entity_id"] and row["date"] == lag_date
    )]
    write_rows(inputs["history"], fields, rows)
    with pytest.raises(ValueError):
        evaluate(module, inputs)


def irregular_history(module):
    history = {}
    for day in range(1, 17):
        if day == 5:
            continue
        observed = date(2026, 1, day)
        available = datetime(2026, 1, day + 1, 3, tzinfo=timezone.utc)
        history[("A", observed)] = module.Observation(float(day * day), available)
    return history


def test_calendar_lags_use_dates_across_older_missing_observations(module):
    history = irregular_history(module)
    issued = datetime(2026, 1, 17, 4, tzinfo=timezone.utc)
    assert module.calendar_lags(history, "A", date(2026, 1, 17), issued, [1, 7, 14]) == {
        1: 256.0, 7: 100.0, 14: 9.0,
    }


def test_calendar_seasonal_scale_excludes_cross_gap_index_pairs(module):
    history = irregular_history(module)
    issued = datetime(2026, 1, 17, 4, tzinfo=timezone.utc)
    result = module.calendar_seasonal_scale(history, "A", date(2026, 1, 17), issued, 730, 7)
    # Valid pairs are Jan8/1, 9/2, 10/3, 11/4, 13/6, 14/7, 15/8, 16/9.
    # Jan12/5 is absent. A seven-observation shift would include eight-day pairs.
    assert result["pair_count"] == 8
    assert result["scale_mwh"] == pytest.approx(119.0)


def test_calendar_scale_filters_by_availability_before_counting_pairs(module):
    history = irregular_history(module)
    issued = datetime(2026, 1, 17, 4, tzinfo=timezone.utc)
    history[("A", date(2026, 1, 16))] = module.Observation(
        256.0, issued + timedelta(seconds=1)
    )
    result = module.calendar_seasonal_scale(history, "A", date(2026, 1, 17), issued, 730, 7)
    assert result["pair_count"] == 7
    assert result["scale_mwh"] == pytest.approx(777.0 / 7)
    with pytest.raises(ValueError):
        module.calendar_seasonal_scale(history, "A", date(2026, 1, 17), issued, 730, 8)


@pytest.mark.parametrize("lookback_days", [28, 730])
def test_seasonal_scale_read_budget_depends_on_calendar_window_not_archive_size(module, lookback_days):
    class CountedHistory(dict):
        reads = 0

        def get(self, key, default=None):
            self.reads += 1
            return super().get(key, default)

        def items(self):
            for item in super().items():
                self.reads += 1
                yield item

    history = CountedHistory()
    first = date(2020, 1, 1)
    for entity in range(100):
        for offset in range(1000):
            day = first + timedelta(days=offset)
            history[(f"E{entity}", day)] = module.Observation(
                float(offset * offset + entity),
                datetime.combine(day + timedelta(days=1), datetime.min.time(), timezone.utc),
            )
    result = module.calendar_seasonal_scale(
        history, "E0", first + timedelta(days=1000),
        datetime(2023, 1, 1, tzinfo=timezone.utc), lookback_days, 7,
    )
    # For y[n]=n^2, the paired absolute difference is 14*n-49. All
    # eligible pairs run from n=1000-lookback+7 through n=999.
    expected_scale = 14 * ((1000 - lookback_days + 7 + 999) / 2) - 49
    assert result == {"scale_mwh": expected_scale, "pair_count": lookback_days - 7}
    assert history.reads <= lookback_days


def test_constant_history_cannot_create_an_undeclared_mase_scale_floor(module):
    history = irregular_history(module)
    history = {
        key: module.Observation(100.0, observation.available_at)
        for key, observation in history.items()
    }
    with pytest.raises(ValueError):
        module.calendar_seasonal_scale(
            history, "A", date(2026, 1, 17),
            datetime(2026, 1, 17, 4, tzinfo=timezone.utc), 730, 7,
        )


def test_unavailable_calendar_lag_is_not_replaced_by_another_date(module):
    history = irregular_history(module)
    issued = datetime(2026, 1, 17, 4, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        module.calendar_lags(history, "A", date(2026, 1, 17), issued, [12])
    history[("A", date(2026, 1, 16))] = module.Observation(
        256.0, issued + timedelta(seconds=1)
    )
    with pytest.raises(ValueError):
        module.calendar_lags(history, "A", date(2026, 1, 17), issued, [1])


def test_cli_requires_protocol_digest_and_writes_reviewable_json(tmp_path):
    arguments = [
        sys.executable, str(SCRIPT), "--protocol", str(PROTOCOL),
        "--predictions", str(FIXTURES / "predictions.csv"),
        "--history", str(FIXTURES / "history.csv"),
    ]
    missing = subprocess.run(arguments, capture_output=True, text=True, check=False)
    assert missing.returncode != 0
    assert "protocol-sha256" in missing.stderr
    output = tmp_path / "synthetic_review.json"
    result = subprocess.run(
        [*arguments, "--protocol-sha256", digest(PROTOCOL), "--json-out", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "HUMAN_REVIEW_HOLD"


def test_cli_does_not_emit_review_artifact_for_wrong_protocol(tmp_path):
    output = tmp_path / "rejected.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--protocol", str(PROTOCOL),
         "--protocol-sha256", "0" * 64,
         "--predictions", str(FIXTURES / "predictions.csv"),
         "--history", str(FIXTURES / "history.csv"), "--json-out", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert not output.exists()


@pytest.mark.parametrize("input_name", ["history", "predictions"])
@pytest.mark.parametrize("field_location", ["header", "data"])
def test_oversized_csv_fields_return_structured_rejection(module, inputs, tmp_path, input_name, field_location):
    fields, rows = read_rows(inputs[input_name])
    oversized = "A" * (csv.field_size_limit() + 1)
    if field_location == "header":
        previous = fields[0]
        fields[0] = oversized
        for row in rows:
            row[oversized] = row.pop(previous)
    else:
        rows[0][fields[0]] = oversized
    write_rows(inputs[input_name], fields, rows)
    assert inputs[input_name].stat().st_size < module.MAX_FILE_BYTES
    with pytest.raises(ValueError, match="CSV parser rejected"):
        evaluate(module, inputs)
    output = tmp_path / "rejected_review.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--protocol", str(inputs["protocol"]),
         "--protocol-sha256", digest(inputs["protocol"]),
         "--predictions", str(inputs["predictions"]),
         "--history", str(inputs["history"]), "--json-out", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    rejection = json.loads(result.stderr)
    assert rejection["status"] == "HUMAN_REVIEW_HOLD"
    assert rejection["input_rejected"] is True
    assert rejection["promotion_gate_passed"] is False
    assert rejection["production_authorized"] is False
    assert not output.exists()


def test_cli_preserves_existing_review_artifact(tmp_path):
    output = tmp_path / "existing.json"
    original = b'{"existing_review":"keep"}\n'
    output.write_bytes(original)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--protocol", str(PROTOCOL),
         "--protocol-sha256", digest(PROTOCOL),
         "--predictions", str(FIXTURES / "predictions.csv"),
         "--history", str(FIXTURES / "history.csv"), "--json-out", str(output)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert output.read_bytes() == original
