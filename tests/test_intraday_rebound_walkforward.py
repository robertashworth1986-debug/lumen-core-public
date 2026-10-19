"""Adversarial offline checks of executable rebound research, using synthetic bars.

The fixture deliberately separates signal-close prices from later executable
opens. Its predictable pattern is a test oracle, not evidence of market alpha.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "intraday_rebound_research_under_test",
    ROOT / "code/ops/ANALYZE_INTRADAY_SPIKE_WINDOWS.py",
)
STUDY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STUDY
SPEC.loader.exec_module(STUDY)


def bars(count=840, *, flat_opens=False):
    """Daily close dip; only the delayed 14:00-to-16:00 opens rebound."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    result = []
    for index in range(count):
        timestamp = start + timedelta(hours=index)
        hour = timestamp.hour
        close = 90.0 if hour == 12 else (95.0 if hour in (13, 14) else 100.0)
        open_price = 95.0 if hour == 14 and not flat_opens else 100.0
        result.append(STUDY.Candle(
            ts=timestamp,
            open=open_price,
            high=max(open_price, close) + 1,
            low=min(open_price, close) - 1,
            close=close,
        ))
    return result


def evaluate(candles=None, **changes):
    candles = bars() if candles is None else candles
    options = {
        "fee_per_side_bps": 20.0,
        "spread_bps": 10.0,
        "slippage_per_side_bps": 3.0,
        "train_bars": 336,
        "test_bars": 168,
        "lookback_bars": 24,
        "hold_bars": 2,
        "entry_delay_bars": 1,
        "dip_threshold_pct": 1.0,
        "min_training_trades": 8,
        "seasonality": "hour",
        "asof": candles[-1].ts + timedelta(hours=1),
    }
    options.update(changes)
    return STUDY.evaluate_rebound_walkforward(candles, **options)


def write_fixture_csv(path, *, naive_timestamps=False):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("timestamp", "open", "high", "low", "close"))
        for candle in bars():
            timestamp = candle.ts.replace(tzinfo=None) if naive_timestamps else candle.ts
            writer.writerow((timestamp.isoformat(), candle.open, candle.high, candle.low, candle.close))
    return path


def run_cli(directory, *, supply_costs):
    source = directory / "input"
    source.mkdir()
    for symbol in ("TEST", "OTHER"):
        write_fixture_csv(source / f"ohlc_{symbol}_USD.csv")
    command = [
        sys.executable, str(ROOT / "code/ops/ANALYZE_INTRADAY_SPIKE_WINDOWS.py"),
        "--data-root", str(source), "--extra-file", str(directory / "no_extra.csv"),
        "--out-root", str(directory / "output"), "--top-n", "1", "--hold-bars", "2",
    ]
    if supply_costs:
        command += ["--fee-per-side-bps", "20", "--spread-bps", "10",
                    "--slippage-per-side-bps", "3"]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    if completed.returncode:
        raise AssertionError(f"offline CLI failed: {completed.stderr}")
    manifests = list((directory / "output").glob("symbol_spike_study_*/summary.json"))
    if len(manifests) != 1:
        raise AssertionError("CLI must produce one inspectable study output")
    return json.loads(manifests[0].read_text(encoding="utf-8")), manifests[0].parent, source


class TestIntradayReboundWalkforward(unittest.TestCase):
    def assert_held(self, result):
        self.assertIs(result["allow_live_orders"], False)
        self.assertEqual(result["promotion_status"], "HOLD")

    def test_synthetic_pattern_uses_later_opens_and_remains_research_only(self):
        candles = bars()
        result = evaluate(candles)
        self.assert_held(result)
        self.assertEqual(result["status"], "research_only_hold")
        self.assertTrue(result["trades"], "test fixture must exercise actual scoring")
        self.assertTrue(result["folds"])
        for fold in result["folds"]:
            self.assertEqual(fold["train_end_index"], fold["test_start_index"])
        for trade in result["trades"]:
            signal, entry, exit_index = (
                trade["signal_index"], trade["entry_index"], trade["exit_index"]
            )
            self.assertGreaterEqual(entry, signal + 2)
            self.assertEqual(exit_index - entry, 2)
            # A dip signal at 90 cannot masquerade as an execution at 90.
            self.assertEqual(candles[signal].ts.hour, 12)
            self.assertEqual(candles[entry].open, 95.0)
            self.assertAlmostEqual(trade["gross_return_pct"], 100 * (100 / 95 - 1))
            # $95 open, 8 bps adverse entry, 20 bps entry fee; $100 exit,
            # 8 bps adverse exit and 20 bps exit fee. Independent decimal receipt.
            self.assertAlmostEqual(trade["net_return_pct"], 4.675331066169231)

    def test_extreme_high_low_oracle_cannot_create_executable_profit(self):
        candles = bars(flat_opens=True)
        baseline = evaluate(candles)
        exaggerated = copy.deepcopy(candles)
        for candle in exaggerated:
            candle.low = 0.01
            candle.high = 100000.0
        result = evaluate(exaggerated)
        self.assert_held(result)
        self.assertEqual(result["trades"], [])
        self.assertEqual(result["trades"], baseline["trades"])
        self.assertEqual(
            [fold["selected_bucket"] for fold in result["folds"]],
            [fold["selected_bucket"] for fold in baseline["folds"]],
        )

    def test_flat_executable_prices_cannot_pass_positive_after_cost_selection(self):
        candles = bars(flat_opens=True)
        result = evaluate(candles, dip_threshold_pct=0.0)
        self.assert_held(result)
        self.assertTrue(result["folds"])
        self.assertEqual(result["trades"], [])
        self.assertTrue(all(fold["selected_bucket"] is None for fold in result["folds"]))

    def test_later_outcomes_cannot_rewrite_earlier_selected_bucket_or_trade(self):
        candles = bars()
        baseline = evaluate(candles)
        self.assertTrue(baseline["trades"])
        first_trade = baseline["trades"][0]
        cutoff = first_trade["exit_index"] + 1
        changed = copy.deepcopy(candles)
        for index, candle in enumerate(changed):
            if index >= cutoff:
                factor = 7.0 if index % 2 else 0.2
                candle.open *= factor
                candle.high *= factor
                candle.low *= factor
                candle.close *= factor
        result = evaluate(changed)
        self.assertEqual(result["folds"][0]["selected_bucket"], baseline["folds"][0]["selected_bucket"])
        unchanged = [trade for trade in result["trades"] if trade["exit_index"] < cutoff]
        expected = [trade for trade in baseline["trades"] if trade["exit_index"] < cutoff]
        self.assertEqual(unchanged, expected)

    def test_exit_at_training_cutoff_is_not_an_available_training_outcome(self):
        candles = bars(flat_opens=True)
        # Manufacture one apparently spectacular training signal whose exit is
        # exactly the first test open. It is not mature strictly before cutoff.
        candles[332].close = 90.0
        candles[332].low = 89.0
        candles[336].open = 1000.0
        candles[336].high = 1001.0
        result = evaluate(candles, min_training_trades=1)
        self.assert_held(result)
        self.assertIsNone(result["folds"][0]["selected_bucket"])
        self.assertEqual(result["folds"][0]["selected_training_trade_count"], 0)

    def test_no_test_position_overlaps_or_crosses_fold_boundary(self):
        result = evaluate()
        self.assertTrue(result["trades"])
        previous_exit = -1
        for trade in result["trades"]:
            entry, exit_index = trade["entry_index"], trade["exit_index"]
            self.assertGreater(entry, previous_exit)
            containing = [fold for fold in result["folds"]
                          if fold["test_start_index"] <= entry
                          and exit_index < fold["test_end_index"]]
            self.assertEqual(len(containing), 1)
            previous_exit = exit_index

    def test_each_required_cost_is_fail_closed_when_missing(self):
        for field in ("fee_per_side_bps", "spread_bps", "slippage_per_side_bps"):
            with self.subTest(field=field):
                result = evaluate(**{field: None})
                self.assert_held(result)
                self.assertEqual(result["status"], "blocked_cost_inputs_missing")
                self.assertEqual(result["trades"], [])

    def test_invalid_costs_reject_instead_of_fabricating_an_edge(self):
        for field in ("fee_per_side_bps", "spread_bps", "slippage_per_side_bps"):
            for value in (-1, math.nan, math.inf, True, 10000):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        evaluate(**{field: value})
        with self.assertRaises(ValueError):
            evaluate(spread_bps=9000, slippage_per_side_bps=6000)

    def test_noncausal_or_invalid_parameters_reject(self):
        cases = (
            {"entry_delay_bars": -1}, {"entry_delay_bars": True},
            {"hold_bars": 0}, {"lookback_bars": 0}, {"train_bars": 0},
            {"test_bars": 0}, {"min_training_trades": 0},
            {"dip_threshold_pct": -1}, {"dip_threshold_pct": math.nan},
            {"seasonality": "best_future_hour"},
        )
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                evaluate(**changes)

    def test_duplicate_out_of_order_gap_and_naive_timestamps_reject(self):
        for defect in ("duplicate", "out_of_order", "gap", "naive"):
            candles = bars()
            if defect == "duplicate":
                candles[100].ts = candles[99].ts
            elif defect == "out_of_order":
                candles[100], candles[101] = candles[101], candles[100]
            elif defect == "gap":
                del candles[100]
            else:
                candles[100].ts = candles[100].ts.replace(tzinfo=None)
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                evaluate(candles)

    def test_nonfinite_negative_or_impossible_ohlc_reject(self):
        for field, value in (("open", math.nan), ("close", math.inf),
                             ("low", 0), ("high", 1), ("low", 200)):
            candles = bars()
            setattr(candles[100], field, value)
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                evaluate(candles)

    def test_unclosed_candle_is_excluded_before_scoring(self):
        candles = bars()
        asof = candles[-1].ts + timedelta(minutes=30)
        result = evaluate(candles, asof=asof)
        self.assert_held(result)
        self.assertEqual(result["discarded_unclosed_bars"], 1)
        self.assertEqual(result["closed_bar_count"], len(candles) - 1)
        expected = evaluate(candles[:-1], asof=asof)
        self.assertEqual(result["trades"], expected["trades"])
        self.assertEqual(result["folds"], expected["folds"])

    def test_short_history_abstains_without_promotion(self):
        result = evaluate(bars(100))
        self.assert_held(result)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["trades"], [])

    def test_csv_naive_timezone_cannot_be_laundered_into_explicit_utc(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture_csv(Path(directory) / "ohlc_TEST_USD.csv", naive_timestamps=True)
            candles = STUDY.load_candles(path)
            self.assertTrue(candles)
            self.assertTrue(all(candle.timestamp_explicit is False for candle in candles))
            with self.assertRaisesRegex(ValueError, "explicit timezone"):
                evaluate(candles)

    def test_strict_csv_loading_cannot_silently_drop_a_bad_trailing_row(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture_csv(Path(directory) / "ohlc_TEST_USD.csv")
            with path.open("a", encoding="utf-8") as handle:
                handle.write("not-a-time,100,101,99,100\n")
            with self.assertRaisesRegex(ValueError, "invalid OHLC CSV row"):
                STUDY.load_candles(path, strict=True)

    def test_cli_retains_all_coin_results_and_distinguishes_hindsight_from_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            report, out, source = run_cli(Path(directory), supply_costs=True)
            self.assertEqual(report["status"], "research_only_hold")
            self.assertIs(report["allow_live_orders"], False)
            self.assertEqual(report["scope"]["symbol_count"], 2)
            self.assertEqual(len(report["top_quick_gain_symbols"]), 1)
            self.assertEqual({row["symbol"] for row in report["symbols"]}, {"TEST", "OTHER"})
            for row in report["symbols"]:
                self.assertEqual(row["evidence_type"], "hindsight_low_to_next_high_range_description")
                self.assertIs(row["executable_trade"], False)
                validation = row["walkforward_validation"]
                self.assert_held(validation)
                self.assertEqual(validation["status"], "research_only_hold")
                self.assertTrue(validation["trades"])
                expected_hash = hashlib.sha256((source / f"ohlc_{row['symbol']}_USD.csv").read_bytes()).hexdigest()
                self.assertEqual(row["source_sha256"], expected_hash)
            blueprint = report["logic_blueprint"]
            self.assertEqual(blueprint["status"], "research_only_hold")
            self.assertNotIn("risk_tiers", blueprint)
            self.assertNotIn("mode_selector", blueprint)
            markdown = (out / "summary.md").read_text(encoding="utf-8")
            self.assertIn("Hindsight", markdown)
            self.assertIn("modeled", markdown)
            self.assertIn("HOLD", markdown)
            self.assertNotIn("buy@", markdown)

    def test_cli_missing_costs_keeps_every_coin_validation_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            report, _, _ = run_cli(Path(directory), supply_costs=False)
            self.assertTrue(report["symbols"])
            for row in report["symbols"]:
                validation = row["walkforward_validation"]
                self.assert_held(validation)
                self.assertEqual(validation["status"], "blocked_cost_inputs_missing")
                self.assertEqual(validation["trades"], [])


if __name__ == "__main__":
    unittest.main()
