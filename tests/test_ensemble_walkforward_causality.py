"""Behavioral checks for the existing offline ensemble research evaluator."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types
import json
import csv
import io

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def subject(monkeypatch):
    # The old runner imports this unrelated engine but never uses it. Keep its
    # initialization outside this focused regression's source boundary.
    monkeypatch.setitem(sys.modules, "institutional_harmonic_core", types.ModuleType("unused"))
    spec = spec_from_file_location("ensemble_causality_subject", ROOT / "dashboard/run_ensemble_meta_strategy.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prices(values):
    return pd.DataFrame({"close": values})


def always_long(history):
    return pd.Series(1.0, index=history.index)


def test_signal_sees_only_the_prior_rolling_window(subject):
    df = prices(np.arange(100.0, 109.0))
    histories = []

    def capture(history):
        histories.append(history.index.tolist())
        assert len(history) <= 3, "test outcomes entered the signal's information set"
        return always_long(history)

    subject.walk_forward(df, capture, window=3, step=2)
    assert histories == [list(range(i - 3, i)) for i in range(3, len(df))]


def test_first_out_of_sample_return_and_every_fold_boundary_are_scored(subject):
    df = prices(100.0 * 1.1 ** np.arange(8))
    results = subject.walk_forward(df, always_long, window=2, step=2)
    assert results["bars"].sum() == 6
    assert results["result"].to_numpy() == pytest.approx([0.2, 0.2, 0.2])


def test_reporting_step_does_not_change_the_evaluated_strategy(subject):
    df = prices([100, 101, 103, 102, 105, 104, 108, 109, 107])

    def context_mean(history):
        return history["close"] / history["close"].mean() - 1.0

    a = subject.walk_forward(df, context_mean, window=3, step=1)["result"].sum()
    b = subject.walk_forward(df, context_mean, window=3, step=4)["result"].sum()
    assert a == pytest.approx(b)


@pytest.mark.parametrize("csv", ["clo,e\n100,7\n110,8\n", "close\n100\nNaN\n120\n", "close\n100\n0\n120\n"])
def test_unknown_missing_or_nonpositive_prices_fail_closed(subject, tmp_path, csv):
    path = tmp_path / "input.csv"
    path.write_text(csv, encoding="utf-8")
    with pytest.raises(ValueError):
        subject.load_data(path)


def test_misaligned_signal_is_not_padded_or_truncated(subject):
    with pytest.raises(ValueError):
        subject.walk_forward(prices([100, 101, 102, 103, 104]), lambda _: [1.0], window=3, step=2)


def test_placeholder_tuning_cannot_inspect_the_whole_dataset(subject):
    inspected = []
    with pytest.raises(NotImplementedError):
        subject.auto_tune(prices([100, 101, 102]), lambda df: inspected.append(len(df)))
    assert inspected == []


def test_future_perturbation_cannot_change_earlier_decisions_or_scores(subject):
    original = prices(100 + np.arange(90) * 0.2 + np.sin(np.arange(90)))
    changed = original.copy()
    changed.loc[76:, "close"] *= 50
    a = subject.evaluate_rows(original, subject.ensemble_signals, window=65)
    b = subject.evaluate_rows(changed, subject.ensemble_signals, window=65)
    pd.testing.assert_frame_equal(a[a.target_position < 76], b[b.target_position < 76])
    # The decision for changed target 76 also predates that changed price.
    assert a.loc[a.target_position == 76, "weight"].item() == b.loc[b.target_position == 76, "weight"].item()
    assert a.loc[a.target_position == 76, "price_return"].item() != b.loc[b.target_position == 76, "price_return"].item()


def test_turnover_costs_baselines_and_cross_block_positions_reconcile(subject):
    df = prices([100, 100, 110, 99, 99, 108.9])
    weights = iter([1, -1, -1, 0])

    def selected(history):
        return pd.Series(next(weights), index=history.index)

    rows = subject.evaluate_rows(df, selected, window=2, fee_bps=10, slippage_bps=20)
    assert rows.weight.tolist() == [1, -1, -1, 0]
    assert rows.turnover.tolist() == [1, 2, 0, 1]
    assert rows.gross_score.to_numpy() == pytest.approx([0.1, 0.1, 0, 0])
    assert rows.net_score.to_numpy() == pytest.approx([0.097, 0.094, 0, -0.003])
    assert rows.buy_hold_score.to_numpy() == pytest.approx([0.097, -0.1, 0, 0.1])
    assert rows.cash_score.to_numpy() == pytest.approx([0, 0, 0, 0])
    for step in (1, 2, 3, 20):
        blocks = subject.summarize_rows(rows, step=step)
        assert blocks.result.sum() == pytest.approx(0.188)
        assert blocks.estimated_cost.sum() == pytest.approx(0.012)
        assert blocks.bars.sum() == 4


@pytest.mark.parametrize("raw", [1.0, [1, np.nan, 1], [1, np.inf, 1], [[1, 1, 1]], pd.Series([1, 1, 1], index=[2, 1, 0])])
def test_invalid_signals_do_not_become_flat_or_broadcast_positions(subject, raw):
    with pytest.raises(ValueError):
        subject.evaluate_rows(prices([100, 101, 102, 103]), lambda _: raw, window=3)


@pytest.mark.parametrize("csv_text", [
    "close,close\n100,100\n", "close,volume\n100,1,2\n", "close,volume\n100\n",
    "close\n100\n\n110\n", 'close,label\n100,"unterminated\n', "close\n100\x00\n",
    "close\ninf\n", "close\nTrue\n", "close\n-1\n",
])
def test_ambiguous_csv_records_cannot_be_reinterpreted_or_dropped(subject, tmp_path, csv_text):
    path = tmp_path / "ambiguous.csv"
    path.write_text(csv_text, encoding="utf-8")
    with pytest.raises(ValueError):
        subject.load_data(path)


@pytest.mark.parametrize("dates", ["2026-01-02\n2026-01-01", "2026-01-01\n2026-01-01", "2026-01-01\nNaT"])
def test_explicit_timestamps_must_be_unique_ordered_and_present(subject, tmp_path, dates):
    path = tmp_path / "dated.csv"
    a, b = dates.splitlines()
    path.write_text(f"time,price\n{a},100\n{b},101\n", encoding="utf-8")
    with pytest.raises(ValueError):
        subject.load_data(path, price_column="price", timestamp_column="time")


def test_explicit_price_and_time_columns_preserve_all_rows(subject, tmp_path):
    path = tmp_path / "dated.csv"
    path.write_text("time,price,volume\n2026-01-01,100,9\n2026-01-02,101,8\n", encoding="utf-8")
    df = subject.load_data(path, price_column="price", timestamp_column="time")
    assert df.close.tolist() == [100.0, 101.0]
    assert str(df.index.tz) == "UTC"
    assert len(df) == 2


def test_canonical_strategy_bytes_ignore_ordinary_module_and_legacy_path_poison(subject, monkeypatch, tmp_path):
    legacy = tmp_path / "data" / "code"
    legacy.mkdir(parents=True)
    for name in subject.STRATEGY_MODULES:
        (legacy / (name + ".py")).write_text("raise AssertionError('wrong source')", encoding="utf-8")
        monkeypatch.setitem(sys.modules, name, types.ModuleType("poison"))
    monkeypatch.syspath_prepend(str(legacy))
    signal = subject.ensemble_signals(prices(100 + np.arange(70)))
    assert len(signal) == 70
    assert np.isfinite(signal).all()
    assert len(subject._source_identities()) == 4


def test_invalid_component_cannot_be_hidden_by_the_ensemble_mean(subject, monkeypatch):
    hhs = subject._strategy_modules()[0][0]
    monkeypatch.setattr(hhs, "strat_phase_follow", lambda _: [1.0])
    with pytest.raises(ValueError, match="did not produce a valid signal"):
        subject.ensemble_signals(prices(100 + np.arange(70)))


def test_cli_receipt_binds_reproducible_artifacts_and_never_overwrites(subject, tmp_path):
    path = tmp_path / "input.csv"
    prices(100 + np.arange(70) * 0.1 + np.sin(np.arange(70))).to_csv(path, index=False)
    argv = ["--input", str(path), "--window", "65", "--step", "2", "--fee-bps", "10", "--slippage-bps", "5"]
    a, b = tmp_path / "a", tmp_path / "b"
    assert subject.main(argv + ["--output-dir", str(a)]) == 0
    assert subject.main(argv + ["--output-dir", str(b)]) == 0
    receipt_bytes = (a / "ensemble_run_receipt.json").read_bytes()
    assert b"\r" not in receipt_bytes, "the completion receipt must use canonical LF bytes on Windows too"
    assert receipt_bytes == (b / "ensemble_run_receipt.json").read_bytes()
    receipt = json.loads(receipt_bytes)
    recorded_hash = receipt.pop("receipt_sha256")
    assert recorded_hash == subject.digest(subject.canonical_json(receipt).encode())
    for name, identity in receipt["artifacts"].items():
        artifact = (a / name).read_bytes()
        assert artifact == (b / name).read_bytes()
        assert identity == {"bytes": len(artifact), "sha256": subject.digest(artifact)}
    assert receipt["execution_authorized"] is False
    assert receipt["scientific_performance_claim_supported"] is False
    assert receipt["independent_source_timing_verified"] is False
    assert receipt["evaluated_transitions"] == 5
    assert receipt["input"]["sha256"] == subject.digest(path.read_bytes())
    assert receipt["input"]["kind"] == "unverified_source"
    assert subject.main(argv + ["--output-dir", str(a)]) == 2
    assert (a / "ensemble_run_receipt.json").read_bytes() == receipt_bytes


def test_changed_input_during_evaluation_cannot_get_a_completion_receipt(subject, monkeypatch, tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("close\n100\n101\n102\n", encoding="utf-8")

    def change_source(history):
        path.write_text("close\n1\n2\n3\n", encoding="utf-8")
        return always_long(history)

    monkeypatch.setattr(subject, "ensemble_signals", change_source)
    output = tmp_path / "run"
    assert subject.main(["--input", str(path), "--output-dir", str(output), "--window", "2", "--fee-bps", "0", "--slippage-bps", "0"]) == 2
    assert not output.exists()


@pytest.fixture
def viewer():
    spec = spec_from_file_location("ensemble_viewer_subject", ROOT / "dashboard/visualize_ensemble_results.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def saved_run(subject, tmp_path):
    path = tmp_path / "synthetic-input.csv"
    prices(100 + np.arange(70) * 0.1 + np.sin(np.arange(70))).to_csv(path, index=False)
    output = tmp_path / "run"
    assert subject.main(["--input", str(path), "--input-kind", "synthetic", "--output-dir", str(output), "--window", "65", "--step", "2", "--fee-bps", "10", "--slippage-bps", "5"]) == 0
    return output


def rewrite_receipt(subject, run, change):
    path = run / "ensemble_run_receipt.json"
    receipt = json.loads(path.read_bytes())
    change(receipt)
    receipt.pop("receipt_sha256")
    receipt["receipt_sha256"] = subject.digest(subject.canonical_json(receipt).encode())
    path.write_text(subject.canonical_json(receipt), encoding="utf-8")


def test_viewer_accepts_the_complete_run_and_reconciles_both_baselines(viewer, saved_run):
    receipt, rows, blocks = viewer.read_verified_run(saved_run)
    assert len(rows) == 5 and len(blocks) == 3
    assert sum(row["net_score"] for row in rows) == pytest.approx(receipt["net_score_sum"])
    assert all(row["cash_score"] == 0 for row in rows)


@pytest.mark.parametrize("filename", ["ensemble_evaluation_rows.csv", "ensemble_walkforward_results.csv", "ensemble_run_receipt.json"])
def test_tampered_retained_files_are_rejected(viewer, saved_run, filename):
    path = saved_run / filename
    if filename.endswith("json"):
        receipt = json.loads(path.read_bytes())
        receipt["net_score_sum"] += 1
        path.write_text(json.dumps(receipt), encoding="utf-8")
    else:
        path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="hash"):
        viewer.read_verified_run(saved_run)


def test_duplicate_receipt_members_are_rejected(viewer, saved_run):
    path = saved_run / "ensemble_run_receipt.json"
    content = path.read_text(encoding="utf-8")
    path.write_text('{"schema":"duplicate",' + content[1:], encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        viewer.read_verified_run(saved_run)


@pytest.mark.parametrize("field", ["net_score", "weight", "turnover", "buy_hold_score", "cash_score"])
def test_rehashing_wrong_calculations_does_not_make_them_valid(subject, viewer, saved_run, field):
    name = "ensemble_evaluation_rows.csv"
    path = saved_run / name
    reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
    columns = reader.fieldnames
    records = list(reader)
    records[0][field] = str(float(records[0][field]) + 0.1)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    content = output.getvalue().encode()
    path.write_bytes(content)
    rewrite_receipt(subject, saved_run, lambda receipt: receipt["artifacts"].update({name: {"bytes": len(content), "sha256": subject.digest(content)}}))
    with pytest.raises(ValueError, match="arithmetic"):
        viewer.read_verified_run(saved_run)


@pytest.mark.parametrize("field", ["execution_authorized", "scientific_performance_claim_supported", "parameter_selection_verified", "independent_source_timing_verified"])
def test_rehashed_unsupported_claims_are_rejected(subject, viewer, saved_run, field):
    rewrite_receipt(subject, saved_run, lambda receipt: receipt.update({field: True}))
    with pytest.raises(ValueError, match="unsupported authority"):
        viewer.read_verified_run(saved_run)


def test_viewer_cannot_follow_artifact_path_instructions(subject, viewer, saved_run):
    rewrite_receipt(subject, saved_run, lambda receipt: receipt["artifacts"].update({"../../private.csv": {"bytes": 5, "sha256": "0" * 64}}))
    with pytest.raises(ValueError, match="artifact set"):
        viewer.read_verified_run(saved_run)


def test_html_preserves_units_limitations_and_escapes_input_metadata(subject, viewer, saved_run, tmp_path):
    pytest.importorskip("plotly")
    rewrite_receipt(subject, saved_run, lambda receipt: receipt["input"].update({"name": '<script>window.evil=true</script>.csv'}))
    output = tmp_path / "chart.html"
    assert viewer.main(["--run-dir", str(saved_run), "--output", str(output)]) == 0
    content = output.read_text(encoding="utf-8")
    assert "Cumulative additive score (unitless)" in content
    assert "Synthetic software check" in content
    assert "not compounded returns or realized PnL" in content
    assert "does not authenticate the author or input source" in content
    assert "<script>window.evil=true</script>" not in content
    assert "&lt;script&gt;window.evil=true&lt;/script&gt;.csv" in content
    original = output.read_bytes()
    assert viewer.main(["--run-dir", str(saved_run), "--output", str(output)]) == 2
    assert output.read_bytes() == original


def test_missing_completion_receipt_prevents_chart_creation(viewer, saved_run, tmp_path):
    (saved_run / "ensemble_run_receipt.json").unlink()
    output = tmp_path / "chart.html"
    assert viewer.main(["--run-dir", str(saved_run), "--output", str(output)]) == 2
    assert not output.exists()


def test_source_changes_after_loading_are_detected(subject, monkeypatch, tmp_path):
    local = tmp_path / "local"
    (local / "code").mkdir(parents=True)
    for name in subject.STRATEGY_MODULES:
        relative = Path("code") / (name + ".py")
        (local / relative).write_bytes((ROOT / relative).read_bytes())
    monkeypatch.setattr(subject, "STACK_ROOT", local)
    subject._source_identities()
    changed = local / "code" / (subject.STRATEGY_MODULES[0] + ".py")
    changed.write_bytes(changed.read_bytes() + b"\n# changed after loading\n")
    with pytest.raises(ValueError, match="source changed"):
        subject._source_identities()


def test_retained_synthetic_example_replays_with_the_recorded_sources(subject, viewer, tmp_path):
    example = ROOT / "examples/ensemble_research"
    reference = example / "reference_run"
    receipt, rows, _ = viewer.read_verified_run(reference)
    assert receipt["input"]["kind"] == "synthetic"
    assert receipt["code_sha256"] == subject._source_identities()
    output = tmp_path / "replay"
    assert subject.main([
        "--input", str(example / "synthetic_price_fixture.csv"), "--input-kind", "synthetic",
        "--timestamp-column", "timestamp", "--window", "65", "--step", "7",
        "--fee-bps", "10", "--slippage-bps", "5", "--output-dir", str(output),
    ]) == 0
    replay_receipt, replay_rows, _ = viewer.read_verified_run(output)
    assert replay_receipt["input"] == receipt["input"]
    assert len(rows) == 31
    pd.testing.assert_frame_equal(pd.DataFrame(rows), pd.DataFrame(replay_rows), rtol=1e-10, atol=1e-12)
