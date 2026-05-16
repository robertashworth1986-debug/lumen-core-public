import argparse
import csv
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


def load_candles(path: Path) -> list[Candle]:
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
            return rows

        for row in reader:
            try:
                ts = parse_iso_dt(row.get(t_col, ""))
                o = safe_float(row.get(o_col, 0.0))
                h = safe_float(row.get(h_col, 0.0))
                l = safe_float(row.get(l_col, 0.0))
                c = safe_float(row.get(c_col, 0.0))
                if min(o, h, l, c) <= 0.0:
                    continue
                rows.append(Candle(ts=ts, open=o, high=h, low=l, close=c))
            except Exception:
                continue

    rows.sort(key=lambda r: r.ts)
    return rows


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
    parser = argparse.ArgumentParser(description="Analyze intraday symbol spike windows and trap-adjusted swing opportunities.")
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
    args = parser.parse_args()

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

        candles = load_candles(file_path)
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
                "median_net_dip_to_next_high_pct": round(med, 6),
                "positive_symbol_share_pct": round(win, 6),
                "symbol_count": len(vals),
            }
        )

    hour_rows.sort(key=lambda r: r["median_net_dip_to_next_high_pct"], reverse=True)

    metrics_columns = [
        "symbol",
        "quote",
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
            "median_net_dip_to_next_high_pct",
            "positive_symbol_share_pct",
            "symbol_count",
        ],
    )

    logic_blueprint = {
        "mode_selector": {
            "POWER_SPIKE": {
                "entry_when": "p95_range_pct >= 2.0 AND best_buy_median_net_pct >= 0.8 AND trap_rate_pct <= 35",
                "positioning": "single-symbol focus with strict stop and max loss budget",
            },
            "BASKET_SCALP": {
                "entry_when": "best_buy_win_rate_pct >= 58 AND trap_rate_pct <= 30",
                "positioning": "spread across 3-6 symbols by quick_gain_score",
            },
            "AVOID": {
                "entry_when": "trap_rate_pct >= 45 OR best_buy_median_net_pct <= 0",
                "positioning": "no new entries",
            },
        },
        "risk_tiers": {
            "balance_under_100": {
                "max_risk_per_trade_pct": 1.0,
                "max_concurrent_positions": 2,
                "no_leverage": True,
            },
            "balance_100_to_2000": {
                "max_risk_per_trade_pct": 0.8,
                "max_concurrent_positions": 5,
                "leverage": "low_or_none",
            },
            "balance_over_2000": {
                "max_risk_per_trade_pct": 0.5,
                "max_concurrent_positions": 8,
                "leverage": "conditional_only_after_200_trades_and_positive_expectancy",
            },
        },
    }

    summary_payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "data_roots": [str(p) for p in data_roots],
            "extra_file": str(extra_file),
            "manifest_csv": str(manifest_csv) if manifest_csv else "",
            "manifest_rows": int(manifest_rows),
            "input_file_count": int(len(input_files)),
            "quote_whitelist": sorted(quote_whitelist),
            "include_stable_symbols": bool(args.include_stable_symbols),
            "fee_roundtrip_pct": float(args.fee_roundtrip_pct),
            "min_bars": int(args.min_bars),
            "symbol_count": len(summaries),
        },
        "top_quick_gain_symbols": top_quick,
        "top_spike_symbols": top_spike,
        "top_balanced_symbols": top_balanced,
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
    md_lines.append("")
    md_lines.append("## Top Quick-Gain Symbols")
    for row in top_quick[:10]:
        md_lines.append(
            "- "
            f"{row['symbol']} ({row['quote']}): buy@{row['best_buy_hour_utc']:02d} UTC, "
            f"median net {row['best_buy_median_net_pct']:.3f}%, "
            f"win {row['best_buy_win_rate_pct']:.1f}%, trap {row['trap_rate_pct']:.1f}%"
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
    md_lines.append("## Best Buy Hours (UTC)")
    for row in hour_rows[:10]:
        md_lines.append(
            "- "
            f"{int(row['hour_utc']):02d}:00 UTC: median net {row['median_net_dip_to_next_high_pct']:.3f}%, "
            f"positive symbols {row['positive_symbol_share_pct']:.1f}% over {row['symbol_count']} symbols"
        )
    md_lines.append("")
    md_lines.append("## Practical Logic")
    md_lines.append("- Use POWER_SPIKE mode only on symbols with high p95 range and controlled trap-rate.")
    md_lines.append("- Use BASKET_SCALP mode for consistent compounding when win-rate is high and traps are low.")
    md_lines.append("- Disable entries on trap-heavy symbols even if raw volatility looks attractive.")

    (out_dir / "summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "out_dir": str(out_dir),
                "symbol_count": len(summaries),
                "top_quick_symbol": top_quick[0]["symbol"] if top_quick else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
