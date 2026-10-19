"""Historical price-range study and causal, cost-scenario rebound diagnostics.

The legacy low-to-next-high rankings are hindsight range descriptions. They are
not executable trades, fitted probabilities, or instructions to allocate money.
The separate walk-forward diagnostic uses closed-bar signals, delayed modeled
open-price fills, train-only time-bucket selection and explicit two-sided costs.
Neither calculation establishes order-book fills or eligibility for live orders.
"""

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any


ROOT = Path(r"C:\LumaTrader")
DEFAULT_DATA_ROOT = ROOT / "premium_packages_mirror" / "whiteholelab_universe_out" / "work_20251220_225712"
DEFAULT_EXTRA_FILE = ROOT / "kraken_truth_check" / "kraken_btcusd_1h_raw.csv"
DEFAULT_OUT_ROOT = ROOT / "INSTITUTIONAL_STACK_V2" / "out" / "ops"
DEFAULT_QUOTE_WHITELIST = {"USD", "USDT"}

STABLE_OR_FIAT = {
    "USD",
    "USDT",
    "USDC",
    "DAI",
    "FDUSD",
    "TUSD",
    "EUR",
    "GBP",
    "AUD",
}

SYMBOL_ALIAS = {
    "XBT": "BTC",
    "XDG": "DOGE",
    "XXBT": "BTC",
    "XETH": "ETH",
    "XXRP": "XRP",
    "XLTC": "LTC",
    "XXDG": "DOGE",
    "XXMR": "XMR",
    "XMR": "XMR",
}

PAIR_SUFFIXES = [
    ("USDT", "USDT"),
    ("USDC", "USDC"),
    ("ZUSD", "USD"),
    ("ZEUR", "EUR"),
    ("ZGBP", "GBP"),
    ("ZAUD", "AUD"),
    ("ZJPY", "JPY"),
    ("USD", "USD"),
    ("EUR", "EUR"),
    ("GBP", "GBP"),
    ("AUD", "AUD"),
    ("JPY", "JPY"),
    ("ETH", "ETH"),
    ("XBT", "BTC"),
]


@dataclass
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    timestamp_explicit: bool = True


def utc_now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_iso_dt(raw: str) -> datetime:
    txt = str(raw or "").strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(txt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def parse_set_arg(raw: str) -> set[str]:
    txt = str(raw or "").strip()
    if not txt:
        return set()
    if txt.upper() == "ALL":
        return {"ALL"}
    return {
        token.upper().strip()
        for token in txt.split(",")
        if token and token.strip()
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * max(min(pct, 100.0), 0.0) / 100.0
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return sorted_vals[int(k)]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    var = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(max(var, 0.0))


def parse_symbol_from_file(path: Path) -> tuple[str, str]:
    name = path.name
    if name.startswith("ohlc_") and name.endswith(".csv"):
        core = name[len("ohlc_") : -len(".csv")]
        parts = core.split("_")
        if len(parts) >= 2:
            base = parts[0].upper().strip()
            quote = parts[1].upper().strip()
            return SYMBOL_ALIAS.get(base, base), quote

    if name.endswith(".csv") and "_" in name:
        core = name[: -len(".csv")]
        parts = core.split("_")
        if len(parts) == 2:
            base = parts[0].upper().strip()
            quote = parts[1].upper().strip()
            if base and quote:
                return SYMBOL_ALIAS.get(base, base), quote

    if name.endswith(".csv"):
        core = name[: -len(".csv")].upper().strip()
        for raw_suffix, quote in PAIR_SUFFIXES:
            if not core.endswith(raw_suffix):
                continue
            base = core[: -len(raw_suffix)].strip()
            if len(base) < 2:
                continue
            return SYMBOL_ALIAS.get(base, base), quote

    lower = name.lower()
    if "kraken_btcusd" in lower:
        return "BTC", "USD"
    return "", ""


def load_candles(path: Path, *, strict: bool = False) -> list[Candle]:
    rows: list[Candle] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return rows

        fields = {c.lower().strip(): c for c in reader.fieldnames}
        t_col = fields.get("time") or fields.get("ts") or fields.get("timestamp")
        o_col = fields.get("open")
        h_col = fields.get("high")
        l_col = fields.get("low")
        c_col = fields.get("close")
        if not (t_col and o_col and h_col and l_col and c_col):
            if strict:
                raise ValueError("OHLC CSV requires time, open, high, low and close columns")
            return rows

        for line_number, row in enumerate(reader, 2):
            try:
                raw_time = str(row.get(t_col, "") or "").strip().replace("Z", "+00:00")
                parsed_time = datetime.fromisoformat(raw_time)
                timestamp_explicit = parsed_time.tzinfo is not None and parsed_time.utcoffset() is not None
                ts = parse_iso_dt(raw_time)
                o = safe_float(row.get(o_col, 0.0))
                h = safe_float(row.get(h_col, 0.0))
                l = safe_float(row.get(l_col, 0.0))
                c = safe_float(row.get(c_col, 0.0))
                if min(o, h, l, c) <= 0.0 or not all(math.isfinite(v) for v in (o, h, l, c)):
                    raise ValueError("invalid price")
                rows.append(Candle(ts=ts, open=o, high=h, low=l, close=c,
                                   timestamp_explicit=timestamp_explicit))
            except Exception as exc:
                if strict:
                    raise ValueError(f"invalid OHLC CSV row at line {line_number}") from exc
                continue

    rows.sort(key=lambda r: r.ts)
    return rows


def _modeled_roundtrip(
    entry_open: float, exit_open: float, fee_bps: float, spread_bps: float, slip_bps: float,
) -> tuple[float, float]:
    """Gross and net decimal returns, with fees paid in quote currency.

Spread is the FULL assumed bid/ask spread, charged half on each side. Slippage
is additional per-side displacement. Open prices and these displacements are
model assumptions, not observed fills, queue priority, or measured market depth.
"""
    displacement = (spread_bps / 2.0 + slip_bps) / 10_000.0
    entry_fill = entry_open * (1.0 + displacement)
    exit_fill = exit_open * (1.0 - displacement)
    fee = fee_bps / 10_000.0
    gross = exit_open / entry_open - 1.0
    net = (exit_fill / entry_fill) * ((1.0 - fee) / (1.0 + fee)) - 1.0
    if not all(math.isfinite(value) for value in (gross, net)):
        raise ValueError("modeled return exceeds finite numeric range")
    return gross, net


def evaluate_rebound_walkforward(
    candles: list[Candle],
    *,
    fee_per_side_bps: float | None = None,
    spread_bps: float | None = None,
    slippage_per_side_bps: float | None = None,
    train_bars: int = 336,
    test_bars: int = 168,
    lookback_bars: int = 24,
    hold_bars: int = 4,
    entry_delay_bars: int = 1,
    dip_threshold_pct: float = 1.0,
    min_training_trades: int = 8,
    seasonality: str = "hour",
    asof: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate one frozen dip rule with rolling train/test time blocks.

    A completed close below the maximum of PRIOR lookback closes is a signal.
    Entry is modeled at open i+1+delay and exit at open entry+hold. At least one
    full bar elapses after signal availability. Only outcomes strictly matured
    before a fold are used to choose its hour/weekday-hour bucket. Each tested
    strategy holds at most one position per symbol; folds never share positions.

    This is a retrospective diagnostic over assumed fills. Cross-symbol/hyper-
    parameter searches and repeated examinations still require fresh validation.
    Counts, wins and historical returns never promote a strategy to live trading.
    """
    integer_parameters = (train_bars, test_bars, lookback_bars, hold_bars,
                          entry_delay_bars, min_training_trades)
    if any(type(value) is not int or value <= 0 for value in integer_parameters):
        raise ValueError("bar counts, entry delay and minimum trades must be positive integers")
    if (isinstance(dip_threshold_pct, bool)
            or not isinstance(dip_threshold_pct, (int, float))
            or not math.isfinite(dip_threshold_pct) or not 0 <= dip_threshold_pct < 100):
        raise ValueError("dip threshold must be finite and within [0, 100)")
    if seasonality not in {"hour", "weekday_hour"}:
        raise ValueError("seasonality must be hour or weekday_hour")
    for value in (fee_per_side_bps, spread_bps, slippage_per_side_bps):
        if value is not None and (isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value) or not 0 <= value < 10_000):
            raise ValueError("costs must be finite bps within [0, 10000)")
    if (spread_bps is not None and slippage_per_side_bps is not None
            and spread_bps / 2 + slippage_per_side_bps >= 10_000):
        raise ValueError("spread plus slippage must leave a positive modeled exit price")
    asof = datetime.now(timezone.utc) if asof is None else asof
    if not isinstance(asof, datetime) or asof.tzinfo is None or asof.utcoffset() is None:
        raise ValueError("asof must have an explicit timezone")
    for index, candle in enumerate(candles):
        if (not candle.timestamp_explicit or not isinstance(candle.ts, datetime) or candle.ts.tzinfo is None
                or candle.ts.utcoffset() is None):
            raise ValueError("candle timestamps must have an explicit timezone")
        prices = (candle.open, candle.high, candle.low, candle.close)
        if any(isinstance(value, bool) or not isinstance(value, (int, float))
               or not math.isfinite(value) or value <= 0 for value in prices):
            raise ValueError("candles require finite positive OHLC prices")
        if candle.low > min(candle.open, candle.close) or candle.high < max(candle.open, candle.close):
            raise ValueError("candle OHLC range is inconsistent")
        if index and candle.ts <= candles[index - 1].ts:
            raise ValueError("candle timestamps must be unique and increasing")
    result: dict[str, Any] = {
        "status": "insufficient_data", "promotion_status": "HOLD",
        "allow_live_orders": False, "deployment_eligible": False,
        "evidence_type": "retrospective_causal_ohlc_cost_scenario",
        "asof_utc": asof.astimezone(timezone.utc).isoformat(),
        "costs": {"fee_per_side_bps": fee_per_side_bps, "full_spread_bps": spread_bps,
                  "slippage_per_side_bps": slippage_per_side_bps, "account_fee_tier_verified": False},
        "protocol": {"train_bars": train_bars, "test_bars": test_bars,
                     "lookback_bars": lookback_bars, "hold_bars": hold_bars,
                     "entry_delay_bars": entry_delay_bars, "dip_threshold_pct": dip_threshold_pct,
                     "min_training_trades": min_training_trades, "seasonality": seasonality,
                     "timezone": "UTC", "partial_final_test_block": "excluded"},
        "limitations": ["modeled_open_price_fills_not_verified_execution",
                        "fixed_cost_scenarios_not_measured_order_book_depth_or_partial_fills",
                        "cross_symbol_and_repeated_strategy_selection_require_fresh_validation",
                        "no_latency_or_realized_account_profit_claim"],
        "folds": [], "trades": [], "closed_bar_count": 0, "discarded_unclosed_bars": 0,
    }
    if len(candles) < 2:
        result["reason"] = "at_least_two_bars_needed_to_infer_cadence"
        return result
    cadence = candles[1].ts - candles[0].ts
    if any(candles[i].ts - candles[i - 1].ts != cadence for i in range(2, len(candles))):
        raise ValueError("candle cadence must be regular; missing intervals cannot be compressed")
    closed = [candle for candle in candles if candle.ts + cadence <= asof]
    result["closed_bar_count"] = len(closed)
    result["discarded_unclosed_bars"] = len(candles) - len(closed)
    result["bar_interval_seconds"] = cadence.total_seconds()
    if any(value is None for value in (fee_per_side_bps, spread_bps, slippage_per_side_bps)):
        result.update(status="blocked_cost_inputs_missing", reason="supply_all_three_explicit_cost_assumptions")
        return result
    if len(closed) < train_bars + test_bars:
        result["reason"] = "insufficient_closed_bars_for_one_complete_train_test_fold"
        return result

    events: list[dict[str, Any]] = []
    for i in range(lookback_bars, len(closed)):
        prior_high_close = max(c.close for c in closed[i - lookback_bars:i])
        dip_pct = (1.0 - closed[i].close / prior_high_close) * 100.0
        if dip_pct < dip_threshold_pct:
            continue
        entry = i + 1 + entry_delay_bars
        exit_ = entry + hold_bars
        if exit_ >= len(closed):
            continue
        signal_time = (closed[i].ts + cadence).astimezone(timezone.utc)
        bucket = (f"{signal_time.weekday()}:{signal_time.hour:02d}" if seasonality == "weekday_hour"
                  else f"{signal_time.hour:02d}")
        gross, net = _modeled_roundtrip(closed[entry].open, closed[exit_].open,
                                       fee_per_side_bps, spread_bps, slippage_per_side_bps)
        events.append({"signal_index": i, "signal_available_utc": signal_time.isoformat(),
                       "entry_index": entry, "exit_index": exit_, "bucket": bucket,
                       "entry_utc": closed[entry].ts.isoformat(), "exit_utc": closed[exit_].ts.isoformat(),
                       "entry_reference_open": closed[entry].open, "exit_reference_open": closed[exit_].open,
                       "gross_return_pct": gross * 100.0, "net_return_pct": net * 100.0})

    def nonoverlapping(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        accepted: list[dict[str, Any]] = []
        previous_exit = -1
        for event in candidates:
            if event["entry_index"] <= previous_exit:
                continue
            accepted.append(event)
            previous_exit = event["exit_index"]
        return accepted

    def metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
        values = [trade["net_return_pct"] for trade in trades]
        nav, peak, max_dd = 1.0, 1.0, 0.0
        for value in values:
            nav *= 1.0 + value / 100.0
            peak = max(peak, nav)
            max_dd = min(max_dd, nav / peak - 1.0)
        if not math.isfinite(nav):
            raise ValueError("modeled equity exceeds finite numeric range")
        return {"trade_count": len(trades), "mean_net_return_pct": sum(values) / len(values) if values else None,
                "net_win_rate_pct": sum(value > 0 for value in values) / len(values) * 100 if values else None,
                "modeled_compounded_return_pct": (nav - 1.0) * 100,
                "closed_trade_drawdown_pct": max_dd * 100,
                "intratrade_mark_to_market_drawdown": None}

    all_baseline_trades: list[dict[str, Any]] = []
    for train_end in range(train_bars, len(closed) - test_bars + 1, test_bars):
        train_start, test_end = train_end - train_bars, train_end + test_bars
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            if train_start + lookback_bars <= event["signal_index"] and event["exit_index"] < train_end:
                groups[event["bucket"]].append(event)
        eligible = []
        for bucket, bucket_events in sorted(groups.items()):
            accepted = nonoverlapping(bucket_events)
            if len(accepted) >= min_training_trades:
                mean_net = sum(event["net_return_pct"] for event in accepted) / len(accepted)
                if mean_net > 0:
                    eligible.append((mean_net, bucket, len(accepted)))
        eligible.sort(key=lambda value: (-value[0], value[1]))
        selected = eligible[0] if eligible else None
        test_events = [event for event in events if train_end <= event["signal_index"]
                       and event["exit_index"] < test_end]
        baseline = nonoverlapping(test_events)
        tested = nonoverlapping([event for event in test_events if selected and event["bucket"] == selected[1]])
        fold_index = len(result["folds"])
        result["trades"].extend({**event, "fold_index": fold_index} for event in tested)
        all_baseline_trades.extend(baseline)
        result["folds"].append({
            "train_start_index": train_start, "train_end_index": train_end,
            "test_start_index": train_end, "test_end_index": test_end,
            "decision_asof_utc": closed[train_end].ts.isoformat(),
            "selected_bucket": selected[1] if selected else None,
            "training_mean_net_return_pct": selected[0] if selected else None,
            "selected_training_trade_count": selected[2] if selected else 0,
            "observed_training_bucket_count": len(groups), "positive_eligible_bucket_count": len(eligible),
            "test": metrics(tested), "all_dips_baseline": metrics(baseline),
        })
    result.update(status="research_only_hold", reason="modeled_diagnostic_not_execution_or_alpha_validation",
                  test=metrics(result["trades"]), all_dips_baseline=metrics(all_baseline_trades),
                  cash_baseline_return_pct=0.0,
                  equity_definition="per_symbol_full_cash_reinvestment_at_each_nonoverlapping_modeled_trade")
    return result


def summarize_symbol(
    symbol: str,
    quote: str,
    candles: list[Candle],
    fee_roundtrip_pct: float,
) -> dict[str, Any] | None:
    if len(candles) < 48:
        return None

    ranges_pct: list[float] = []
    body_ret_pct: list[float] = []
    close_to_close_ret_pct: list[float] = []

    buy_hour_net: dict[int, list[float]] = defaultdict(list)
    buy_hour_raw: dict[int, list[float]] = defaultdict(list)
    sell_hour_edge: dict[int, list[float]] = defaultdict(list)

    trap_candidates = 0
    trap_hits = 0

    for i in range(len(candles) - 1):
        c0 = candles[i]
        c1 = candles[i + 1]

        rng = ((c0.high - c0.low) / c0.open) * 100.0
        body = ((c0.close - c0.open) / c0.open) * 100.0
        c2c = ((c1.close - c0.close) / c0.close) * 100.0

        ranges_pct.append(rng)
        body_ret_pct.append(body)
        close_to_close_ret_pct.append(c2c)

        dip_to_next_high = ((c1.high - c0.low) / c0.low) * 100.0
        dip_to_next_high_net = dip_to_next_high - fee_roundtrip_pct
        high_to_next_low = ((c0.high - c1.low) / c0.high) * 100.0

        hour = c0.ts.hour
        buy_hour_raw[hour].append(dip_to_next_high)
        buy_hour_net[hour].append(dip_to_next_high_net)
        sell_hour_edge[hour].append(high_to_next_low)

        if rng >= 1.2 and abs(body) >= 0.4:
            trap_candidates += 1
            if body > 0.0 and c2c < -0.25:
                trap_hits += 1
            elif body < 0.0 and c2c > 0.25:
                trap_hits += 1

    if not ranges_pct:
        return None

    def pick_best_hour(values_by_hour: dict[int, list[float]]) -> tuple[int, float, float, int]:
        best_hour = -1
        best_median = -10**9
        best_win = 0.0
        best_n = 0
        for hour, vals in values_by_hour.items():
            if len(vals) < 8:
                continue
            med = median(vals)
            win = (sum(1 for v in vals if v > 0.0) / len(vals)) * 100.0
            if med > best_median:
                best_hour = hour
                best_median = med
                best_win = win
                best_n = len(vals)
        return best_hour, best_median, best_win, best_n

    buy_hour, buy_med_net, buy_win, buy_n = pick_best_hour(buy_hour_net)
    sell_hour, sell_med_edge, sell_win, sell_n = pick_best_hour(sell_hour_edge)

    trap_rate_pct = (trap_hits / trap_candidates * 100.0) if trap_candidates > 0 else 0.0
    p95_range = percentile(ranges_pct, 95.0)
    p99_range = percentile(ranges_pct, 99.0)

    quick_gain_score = max(buy_med_net, 0.0) * (buy_win / 100.0)
    spike_power_score = p95_range * max(1.0 - (trap_rate_pct / 100.0), 0.0)

    style = "BASKET_SCALP"
    if p95_range >= 2.0 and trap_rate_pct <= 35.0 and buy_med_net >= 0.8:
        style = "POWER_SPIKE"
    elif trap_rate_pct >= 45.0:
        style = "TRAP_HEAVY"

    return {
        "symbol": symbol,
        "quote": quote,
        "evidence_type": "hindsight_low_to_next_high_range_description",
        "executable_trade": False,
        "allow_live_orders": False,
        "ranking_warning": "extrema_and_best_hour_selected_in_sample_not_predictive_profit",
        "bars": len(candles),
        "first_ts_utc": candles[0].ts.isoformat(),
        "last_ts_utc": candles[-1].ts.isoformat(),
        "median_range_pct": round(median(ranges_pct), 6),
        "p95_range_pct": round(p95_range, 6),
        "p99_range_pct": round(p99_range, 6),
        "max_range_pct": round(max(ranges_pct), 6),
        "max_up_body_pct": round(max(body_ret_pct), 6),
        "max_down_body_pct": round(min(body_ret_pct), 6),
        "hourly_vol_pct_std": round(stdev(close_to_close_ret_pct), 6),
        "best_buy_hour_utc": buy_hour,
        "best_buy_median_net_pct": round(buy_med_net, 6),
        "best_buy_win_rate_pct": round(buy_win, 6),
        "best_buy_samples": buy_n,
        "best_sell_hour_utc": sell_hour,
        "best_sell_median_edge_pct": round(sell_med_edge, 6),
        "best_sell_win_rate_pct": round(sell_win, 6),
        "best_sell_samples": sell_n,
        "trap_rate_pct": round(trap_rate_pct, 6),
        "trap_samples": trap_candidates,
        "quick_gain_score": round(quick_gain_score, 6),
        "spike_power_score": round(spike_power_score, 6),
        "style": style,
        "buy_hour_net_curve": {
            str(h): round(median(v), 6)
            for h, v in sorted(buy_hour_net.items())
            if len(v) >= 8
        },
        "sell_hour_edge_curve": {
            str(h): round(median(v), 6)
            for h, v in sorted(sell_hour_edge.items())
            if len(v) >= 8
        },
    }


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in columns})


def main() -> int:
    parser = argparse.ArgumentParser(description="Describe historical ranges and run causal cost-scenario rebound diagnostics; no orders.")
    parser.add_argument(
        "--data-root",
        action="append",
        default=[],
        help="Directory containing OHLC csv files. Can be supplied multiple times.",
    )
    parser.add_argument("--extra-file", default=str(DEFAULT_EXTRA_FILE), help="Optional extra OHLC CSV path.")
    parser.add_argument("--manifest-csv", default="", help="Optional CSV manifest containing file paths to OHLC datasets.")
    parser.add_argument("--manifest-path-column", default="file", help="Manifest column name containing file paths.")
    parser.add_argument(
        "--quote-whitelist",
        default="USD,USDT",
        help="Comma-separated quote whitelist (e.g. USD,USDT,EUR) or ALL.",
    )
    parser.add_argument(
        "--include-stable-symbols",
        action="store_true",
        help="Include stable/fiat symbols in analysis (default false).",
    )
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT), help="Output root directory.")
    parser.add_argument("--fee-roundtrip-pct", type=float, default=0.52, help="Roundtrip fee+slippage in percent.")
    parser.add_argument("--min-bars", type=int, default=72, help="Minimum candles required per symbol.")
    parser.add_argument("--top-n", type=int, default=12, help="Top-N symbols to surface in summary tables.")
    parser.add_argument("--fee-per-side-bps", type=float, default=None,
                        help="Explicit modeled fee per side; verify venue/account/pair tier separately.")
    parser.add_argument("--spread-bps", type=float, default=None, help="Explicit FULL modeled bid/ask spread.")
    parser.add_argument("--slippage-per-side-bps", type=float, default=None, help="Additional modeled slippage per side.")
    parser.add_argument("--train-bars", type=int, default=336)
    parser.add_argument("--test-bars", type=int, default=168)
    parser.add_argument("--lookback-bars", type=int, default=24)
    parser.add_argument("--hold-bars", type=int, default=4)
    parser.add_argument("--entry-delay-bars", type=int, default=1)
    parser.add_argument("--dip-threshold-pct", type=float, default=1.0)
    parser.add_argument("--min-training-trades", type=int, default=8)
    parser.add_argument("--seasonality", choices=("hour", "weekday_hour"), default="hour")
    args = parser.parse_args()
    protocol = {name: getattr(args, name) for name in (
        "fee_per_side_bps", "spread_bps", "slippage_per_side_bps", "train_bars", "test_bars",
        "lookback_bars", "hold_bars", "entry_delay_bars", "dip_threshold_pct", "min_training_trades", "seasonality")}
    try:
        evaluate_rebound_walkforward([], **protocol)
    except ValueError as exc:
        parser.error(str(exc))

    data_roots = [Path(p) for p in args.data_root] if args.data_root else [DEFAULT_DATA_ROOT]
    extra_file = Path(args.extra_file)
    manifest_csv = Path(str(args.manifest_csv or "").strip()) if str(args.manifest_csv or "").strip() else None
    quote_whitelist = parse_set_arg(args.quote_whitelist)
    out_root = Path(args.out_root)
    out_dir = out_root / f"symbol_spike_study_{utc_now_stamp()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    input_file_set: dict[str, Path] = {}
    for data_root in data_roots:
        if not data_root.exists():
            continue
        for file_path in sorted(data_root.glob("ohlc_*.csv")):
            input_file_set[str(file_path)] = file_path
        for file_path in sorted(data_root.glob("*_*.csv")):
            input_file_set[str(file_path)] = file_path

    if extra_file.exists():
        input_file_set[str(extra_file)] = extra_file

    manifest_rows = 0
    if manifest_csv and manifest_csv.exists():
        try:
            with manifest_csv.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    manifest_rows += 1
                    candidate = str(row.get(str(args.manifest_path_column), "") or "").strip()
                    if not candidate:
                        continue
                    path = Path(candidate)
                    if path.exists() and path.suffix.lower() == ".csv":
                        input_file_set[str(path)] = path
        except Exception:
            pass

    input_files = sorted(input_file_set.values(), key=lambda p: str(p).lower())

    summaries: list[dict[str, Any]] = []
    skipped_files: list[dict[str, Any]] = []

    for file_path in input_files:
        symbol, quote = parse_symbol_from_file(file_path)
        if not symbol:
            skipped_files.append({"path": str(file_path), "reason": "symbol_parse_failed"})
            continue
        if "ALL" not in quote_whitelist and quote.upper() not in quote_whitelist:
            skipped_files.append({"path": str(file_path), "reason": f"quote_{quote}_not_target"})
            continue
        if (not args.include_stable_symbols) and (symbol in STABLE_OR_FIAT):
            skipped_files.append({"path": str(file_path), "reason": f"symbol_{symbol}_filtered"})
            continue

        try:
            candles = load_candles(file_path, strict=True)
        except ValueError as exc:
            skipped_files.append({"path": str(file_path), "reason": str(exc),
                                  "validation_status": "blocked_invalid_raw_input"})
            continue
        if len(candles) < int(args.min_bars):
            skipped_files.append({"path": str(file_path), "reason": f"insufficient_bars_{len(candles)}"})
            continue

        summary = summarize_symbol(
            symbol=symbol,
            quote=quote,
            candles=candles,
            fee_roundtrip_pct=float(args.fee_roundtrip_pct),
        )
        if not summary:
            skipped_files.append({"path": str(file_path), "reason": "summary_failed"})
            continue
        summary["source_file"] = str(file_path)
        summary["source_sha256"] = hashlib.sha256(file_path.read_bytes()).hexdigest()
        try:
            summary["walkforward_validation"] = evaluate_rebound_walkforward(candles, **protocol)
        except ValueError as exc:
            summary["walkforward_validation"] = {
                "status": "blocked_invalid_data", "promotion_status": "HOLD",
                "allow_live_orders": False, "deployment_eligible": False, "reason": str(exc),
            }
        summaries.append(summary)

    # Keep one best source per symbol/quote pair (prefer longest history).
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in summaries:
        key = (str(row.get("symbol", "")), str(row.get("quote", "")))
        prev = deduped.get(key)
        if prev is None or int(row.get("bars", 0) or 0) > int(prev.get("bars", 0) or 0):
            deduped[key] = row
    summaries = list(deduped.values())

    if not summaries:
        (out_dir / "summary.md").write_text("No analyzable symbol files found.\n", encoding="utf-8")
        (out_dir / "summary.json").write_text(
            json.dumps({"error": "no_analyzable_data", "skipped_files": skipped_files}, indent=2),
            encoding="utf-8",
        )
        print(json.dumps({"status": "empty", "out_dir": str(out_dir)}, indent=2))
        return 0

    summaries.sort(key=lambda r: (r.get("quick_gain_score", 0.0), r.get("spike_power_score", 0.0)), reverse=True)

    top_n = max(int(args.top_n), 1)
    top_quick = sorted(summaries, key=lambda r: r.get("quick_gain_score", 0.0), reverse=True)[:top_n]
    top_spike = sorted(summaries, key=lambda r: r.get("p95_range_pct", 0.0), reverse=True)[:top_n]
    top_balanced = sorted(
        summaries,
        key=lambda r: (r.get("quick_gain_score", 0.0) * max(100.0 - r.get("trap_rate_pct", 0.0), 1.0)),
        reverse=True,
    )[:top_n]

    hour_net_map: dict[int, list[float]] = defaultdict(list)
    hour_win_map: dict[int, list[int]] = defaultdict(list)
    for row in summaries:
        curve = row.get("buy_hour_net_curve", {})
        if not isinstance(curve, dict):
            continue
        for h_str, net_val in curve.items():
            try:
                h = int(h_str)
                v = float(net_val)
            except Exception:
                continue
            hour_net_map[h].append(v)
            hour_win_map[h].append(1 if v > 0.0 else 0)

    hour_rows: list[dict[str, Any]] = []
    for h in range(24):
        vals = hour_net_map.get(h, [])
        if len(vals) == 0:
            continue
        med = median(vals)
        win = (sum(hour_win_map.get(h, [])) / len(hour_win_map.get(h, [1]))) * 100.0
        hour_rows.append(
            {
                "hour_utc": h,
                "evidence_type": "hindsight_range_description_not_executable_profit",
                "allow_live_orders": False,
                "median_net_dip_to_next_high_pct": round(med, 6),
                "positive_symbol_share_pct": round(win, 6),
                "symbol_count": len(vals),
            }
        )

    hour_rows.sort(key=lambda r: r["median_net_dip_to_next_high_pct"], reverse=True)

    metrics_columns = [
        "symbol",
        "quote",
        "evidence_type",
        "executable_trade",
        "allow_live_orders",
        "ranking_warning",
        "bars",
        "median_range_pct",
        "p95_range_pct",
        "p99_range_pct",
        "max_range_pct",
        "max_up_body_pct",
        "max_down_body_pct",
        "hourly_vol_pct_std",
        "best_buy_hour_utc",
        "best_buy_median_net_pct",
        "best_buy_win_rate_pct",
        "best_sell_hour_utc",
        "best_sell_median_edge_pct",
        "best_sell_win_rate_pct",
        "trap_rate_pct",
        "trap_samples",
        "quick_gain_score",
        "spike_power_score",
        "style",
        "source_file",
    ]
    write_csv(out_dir / "symbol_metrics.csv", summaries, metrics_columns)
    write_csv(out_dir / "top_quick_gain_symbols.csv", top_quick, metrics_columns)
    write_csv(out_dir / "top_spike_symbols.csv", top_spike, metrics_columns)
    write_csv(out_dir / "top_balanced_symbols.csv", top_balanced, metrics_columns)
    write_csv(
        out_dir / "best_buy_hours_utc.csv",
        hour_rows,
        [
            "hour_utc",
            "evidence_type",
            "allow_live_orders",
            "median_net_dip_to_next_high_pct",
            "positive_symbol_share_pct",
            "symbol_count",
        ],
    )

    logic_blueprint = {
        "status": "research_only_hold", "allow_live_orders": False,
        "instruction": "No sizing or entry recommendation follows from hindsight extrema rankings.",
        "next_evidence": "review train-only selection and later after-cost modeled outcomes, then collect prospective fills",
    }

    summary_payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "research_only_hold", "allow_live_orders": False,
        "claim_boundary": "Historical ranges and modeled walk-forward results are not execution or trading-alpha validation.",
        "scope": {
            "data_roots": [str(p) for p in data_roots],
            "extra_file": str(extra_file),
            "manifest_csv": str(manifest_csv) if manifest_csv else "",
            "manifest_rows": int(manifest_rows),
            "input_file_count": int(len(input_files)),
            "quote_whitelist": sorted(quote_whitelist),
            "include_stable_symbols": bool(args.include_stable_symbols),
            "fee_roundtrip_pct": float(args.fee_roundtrip_pct),
            "fee_roundtrip_scope": "legacy_hindsight_description_only",
            "walkforward_protocol": protocol,
            "min_bars": int(args.min_bars),
            "symbol_count": len(summaries),
        },
        "top_quick_gain_symbols": top_quick,
        "top_spike_symbols": top_spike,
        "top_balanced_symbols": top_balanced,
        "symbols": summaries,
        "best_buy_hours_utc": hour_rows[:12],
        "logic_blueprint": logic_blueprint,
        "artifacts": {
            "symbol_metrics_csv": str(out_dir / "symbol_metrics.csv"),
            "top_quick_gain_csv": str(out_dir / "top_quick_gain_symbols.csv"),
            "top_spike_csv": str(out_dir / "top_spike_symbols.csv"),
            "top_balanced_csv": str(out_dir / "top_balanced_symbols.csv"),
            "best_buy_hours_csv": str(out_dir / "best_buy_hours_utc.csv"),
        },
        "skipped_files": skipped_files,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    md_lines = []
    md_lines.append("# Intraday Spike Window Study")
    md_lines.append("")
    md_lines.append(f"Generated UTC: {summary_payload['generated_utc']}")
    md_lines.append(f"Symbols analyzed: {len(summaries)}")
    md_lines.append(f"Fee roundtrip assumption: {float(args.fee_roundtrip_pct):.3f}%")
    md_lines.append("HOLD: legacy rankings assume hindsight low-to-next-high prices and select hours in-sample. They are not executable profit or entry instructions.")
    md_lines.append("")
    md_lines.append("## Largest Historical Low-to-Next-High Ranges (Hindsight)")
    for row in top_quick[:10]:
        md_lines.append(
            "- "
            f"{row['symbol']} ({row['quote']}): in-sample hour {row['best_buy_hour_utc']:02d} UTC, "
            f"median hypothetical range less legacy costs {row['best_buy_median_net_pct']:.3f}%, "
            f"positive-range share {row['best_buy_win_rate_pct']:.1f}%, trap statistic {row['trap_rate_pct']:.1f}%"
        )
    md_lines.append("")
    md_lines.append("## Top Raw Spike Symbols")
    for row in top_spike[:10]:
        md_lines.append(
            "- "
            f"{row['symbol']} ({row['quote']}): p95 range {row['p95_range_pct']:.3f}%, "
            f"max range {row['max_range_pct']:.3f}%, trap {row['trap_rate_pct']:.1f}%"
        )
    md_lines.append("")
    md_lines.append("## Historical Range Hours (UTC; Not Buy Instructions)")
    for row in hour_rows[:10]:
        md_lines.append(
            "- "
            f"{int(row['hour_utc']):02d}:00 UTC: median hypothetical range less legacy costs {row['median_net_dip_to_next_high_pct']:.3f}%, "
            f"positive symbols {row['positive_symbol_share_pct']:.1f}% over {row['symbol_count']} symbols"
        )
    md_lines.append("")
    md_lines.append("## Causal Rebound Walk-Forward Diagnostics")
    md_lines.append("Hour/day buckets are selected from matured training trades only. Later trades use delayed modeled opens with explicit two-sided fees, full spread and slippage. All results remain HOLD.")
    for row in summaries:
        validation = row["walkforward_validation"]
        test = validation.get("test", {})
        md_lines.append(f"- {row['symbol']} ({row['quote']}): {validation['status']}; "
                        f"modeled test trades {test.get('trade_count', 0)}; "
                        f"modeled compounded return {test.get('modeled_compounded_return_pct', 'unknown')}%; "
                        f"reason {validation.get('reason', '')}.")
    md_lines.append("No order-book depth, queue priority, partial fills, exchange latency or reconciled account profit is established. Costs remain scenarios until checked against the actual account/pair fee tier and measured liquidity. Per-symbol reinvestment results cannot be summed into a multi-coin bankroll return.")

    (out_dir / "summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "research_only_hold",
                "allow_live_orders": False,
                "out_dir": str(out_dir),
                "symbol_count": len(summaries),
                "top_hindsight_range_symbol": top_quick[0]["symbol"] if top_quick else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
