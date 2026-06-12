from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


STACK_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = STACK_ROOT.parent
DEFAULT_DATA_ROOT = (
    WORKSPACE_ROOT
    / "premium_packages_mirror"
    / "whiteholelab_universe_out"
    / "work_20251220_225712"
)
DEFAULT_EXTRA_FILE = WORKSPACE_ROOT / "kraken_truth_check" / "kraken_btcusd_1h_raw.csv"
DEFAULT_CLUSTER_FILE = STACK_ROOT / "out" / "ops" / "kraken_6m_move_clusters_latest.json"
DEFAULT_OUT_ROOT = STACK_ROOT / "out" / "ops"

STABLE_OR_FIAT = {
    "USD", "USDT", "USDC", "DAI", "FDUSD", "TUSD",
    "EUR", "GBP", "AUD", "JPY", "CAD", "CHF",
}
SYMBOL_ALIAS = {
    "XBT": "BTC",
    "XXBT": "BTC",
    "XDG": "DOGE",
    "XXDG": "DOGE",
    "XETH": "ETH",
    "XXRP": "XRP",
    "XLTC": "LTC",
}
WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


@dataclass(frozen=True)
class Candle:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class ForwardSample:
    index: int
    ts: datetime
    hour: int
    weekday: int
    daily_low_event: bool
    daily_high_event: bool
    net_mfe_pct: float
    mae_pct: float
    close_return_pct: float
    peak_hour: int
    hours_to_peak: int


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * max(0.0, min(100.0, pct)) / 100.0
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)


def mean(values: Iterable[float]) -> float:
    rows = list(values)
    return sum(rows) / len(rows) if rows else 0.0


def median(values: Iterable[float]) -> float:
    rows = list(values)
    return float(statistics.median(rows)) if rows else 0.0


def wilson_interval(successes: int, total: int, z: float = 1.959964) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 1.0
    p = successes / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    half = (
        z
        * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
        / denom
    )
    return max(0.0, center - half), min(1.0, center + half)


def parse_timestamp(raw: Any) -> datetime:
    text = str(raw or "").strip().replace("Z", "+00:00")
    if not text:
        raise ValueError("missing timestamp")
    try:
        numeric = float(text)
        if numeric > 10_000_000:
            return datetime.fromtimestamp(numeric, tz=timezone.utc)
    except ValueError:
        pass
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_symbol_from_file(path: Path) -> tuple[str, str]:
    name = path.stem.upper()
    if name.startswith("OHLC_"):
        name = name[5:]
    if "KRAKEN_BTCUSD" in name:
        return "BTC", "USD"
    parts = name.split("_")
    if len(parts) >= 2:
        base = SYMBOL_ALIAS.get(parts[0], parts[0])
        return base, parts[1]
    for quote in ("USDT", "USDC", "USD", "EUR", "GBP"):
        if name.endswith(quote) and len(name) > len(quote):
            base = SYMBOL_ALIAS.get(name[: -len(quote)], name[: -len(quote)])
            return base, quote
    return "", ""


def load_candles(path: Path) -> list[Candle]:
    candles: list[Candle] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {
            str(field).strip().lower(): field
            for field in (reader.fieldnames or [])
        }
        ts_col = fields.get("time") or fields.get("ts") or fields.get("timestamp")
        open_col = fields.get("open")
        high_col = fields.get("high")
        low_col = fields.get("low")
        close_col = fields.get("close")
        volume_col = fields.get("volume")
        if not all((ts_col, open_col, high_col, low_col, close_col)):
            return candles
        for row in reader:
            try:
                candle = Candle(
                    ts=parse_timestamp(row.get(ts_col)),
                    open=safe_float(row.get(open_col)),
                    high=safe_float(row.get(high_col)),
                    low=safe_float(row.get(low_col)),
                    close=safe_float(row.get(close_col)),
                    volume=safe_float(row.get(volume_col)) if volume_col else 0.0,
                )
            except Exception:
                continue
            if min(candle.open, candle.high, candle.low, candle.close) <= 0.0:
                continue
            candles.append(candle)
    by_ts = {row.ts: row for row in candles}
    return [by_ts[key] for key in sorted(by_ts)]


def interval_hours(candles: list[Candle]) -> float:
    if len(candles) < 3:
        return 0.0
    diffs = [
        (candles[i].ts - candles[i - 1].ts).total_seconds() / 3600.0
        for i in range(1, len(candles))
        if candles[i].ts > candles[i - 1].ts
    ]
    return median(diffs)


def daily_extremes(candles: list[Candle]) -> dict[str, tuple[float, float]]:
    grouped: dict[str, list[Candle]] = defaultdict(list)
    for candle in candles:
        grouped[candle.ts.date().isoformat()].append(candle)
    return {
        day: (
            min(row.low for row in rows),
            max(row.high for row in rows),
        )
        for day, rows in grouped.items()
    }


def build_forward_samples(
    candles: list[Candle],
    horizon_hours: int,
    roundtrip_cost_bps: float,
    daily_extreme_tolerance_bps: float,
) -> list[ForwardSample]:
    extremes = daily_extremes(candles)
    cost_pct = roundtrip_cost_bps / 100.0
    tolerance = daily_extreme_tolerance_bps / 10_000.0
    samples: list[ForwardSample] = []
    for i in range(0, len(candles) - horizon_hours):
        current = candles[i]
        future = candles[i + 1 : i + horizon_hours + 1]
        if not future or current.close <= 0.0:
            continue
        day_low, day_high = extremes[current.ts.date().isoformat()]
        peak_offset, peak = max(
            enumerate(future, start=1),
            key=lambda item: item[1].high,
        )
        trough = min(row.low for row in future)
        mfe_pct = (peak.high / current.close - 1.0) * 100.0
        mae_pct = (trough / current.close - 1.0) * 100.0
        close_return_pct = (future[-1].close / current.close - 1.0) * 100.0
        samples.append(
            ForwardSample(
                index=i,
                ts=current.ts,
                hour=current.ts.hour,
                weekday=current.ts.weekday(),
                daily_low_event=current.close <= day_low * (1.0 + tolerance),
                daily_high_event=current.close >= day_high * (1.0 - tolerance),
                net_mfe_pct=mfe_pct - cost_pct,
                mae_pct=mae_pct,
                close_return_pct=close_return_pct - cost_pct,
                peak_hour=peak.ts.hour,
                hours_to_peak=peak_offset,
            )
        )
    return samples


def summarize_bucket(
    samples: list[ForwardSample],
    global_low_rate: float,
    prior_strength: float,
) -> dict[str, Any]:
    n = len(samples)
    low_count = sum(1 for row in samples if row.daily_low_event)
    high_count = sum(1 for row in samples if row.daily_high_event)
    posterior_low = (
        (low_count + global_low_rate * prior_strength) / (n + prior_strength)
        if n + prior_strength > 0
        else 0.0
    )
    low_lo, low_hi = wilson_interval(low_count, n)
    net_mfe = [row.net_mfe_pct for row in samples]
    mae = [row.mae_pct for row in samples]
    close_returns = [row.close_return_pct for row in samples]
    peak_hours = Counter(row.peak_hour for row in samples)
    best_peak_hour, best_peak_count = (
        peak_hours.most_common(1)[0] if peak_hours else (-1, 0)
    )
    shrinkage = n / (n + 20.0)
    raw_score = (
        posterior_low * max(0.0, median(net_mfe))
        + max(0.0, median(close_returns)) * 0.35
        - abs(min(0.0, median(mae))) * 0.35
    )
    return {
        "samples": n,
        "daily_low_events": low_count,
        "daily_low_rate_pct": round(100.0 * low_count / n, 6) if n else 0.0,
        "daily_low_posterior_pct": round(100.0 * posterior_low, 6),
        "daily_low_wilson95_pct": [
            round(100.0 * low_lo, 6),
            round(100.0 * low_hi, 6),
        ],
        "daily_high_events": high_count,
        "median_net_mfe_pct": round(median(net_mfe), 6),
        "p75_net_mfe_pct": round(percentile(net_mfe, 75.0), 6),
        "median_mae_pct": round(median(mae), 6),
        "median_close_return_pct": round(median(close_returns), 6),
        "positive_close_rate_pct": round(
            100.0 * sum(1 for value in close_returns if value > 0.0) / n,
            6,
        ) if n else 0.0,
        "median_hours_to_peak": round(
            median(row.hours_to_peak for row in samples),
            6,
        ),
        "most_common_peak_hour_utc": best_peak_hour,
        "peak_hour_share_pct": round(100.0 * best_peak_count / n, 6) if n else 0.0,
        "shrinkage_factor": round(shrinkage, 6),
        "timing_score": round(raw_score * shrinkage, 8),
    }


def group_summary(
    samples: list[ForwardSample],
    key_fn,
    prior_strength: float,
) -> dict[Any, dict[str, Any]]:
    grouped: dict[Any, list[ForwardSample]] = defaultdict(list)
    for sample in samples:
        grouped[key_fn(sample)].append(sample)
    global_low_rate = (
        sum(1 for row in samples if row.daily_low_event) / len(samples)
        if samples
        else 0.0
    )
    return {
        key: summarize_bucket(rows, global_low_rate, prior_strength)
        for key, rows in grouped.items()
    }


def evaluate_selected_hours(
    test_samples: list[ForwardSample],
    selected_hours: list[int],
    prior_strength: float,
) -> dict[str, Any]:
    selected = [row for row in test_samples if row.hour in selected_hours]
    all_summary = summarize_bucket(
        test_samples,
        (
            sum(1 for row in test_samples if row.daily_low_event) / len(test_samples)
            if test_samples
            else 0.0
        ),
        prior_strength,
    )
    selected_summary = summarize_bucket(
        selected,
        (
            sum(1 for row in test_samples if row.daily_low_event) / len(test_samples)
            if test_samples
            else 0.0
        ),
        prior_strength,
    )
    return {
        "selected_hours_utc": selected_hours,
        "selected": selected_summary,
        "all_test_hours": all_summary,
        "net_mfe_lift_pct_points": round(
            selected_summary["median_net_mfe_pct"]
            - all_summary["median_net_mfe_pct"],
            6,
        ),
        "close_return_lift_pct_points": round(
            selected_summary["median_close_return_pct"]
            - all_summary["median_close_return_pct"],
            6,
        ),
    }


def moonshot_event_study(
    candles: list[Candle],
    thresholds_pct: list[float],
    horizon_hours: int,
) -> dict[str, Any]:
    anchors: list[tuple[int, Candle]] = [
        (i, candle)
        for i, candle in enumerate(candles)
        if candle.ts.hour == 0 and i + horizon_hours < len(candles)
    ]
    max_returns: list[float] = []
    precursor_rows: list[dict[str, float]] = []
    for i, candle in anchors:
        future = candles[i + 1 : i + horizon_hours + 1]
        max_return = (max(row.high for row in future) / candle.close - 1.0) * 100.0
        max_returns.append(max_return)
        prior = candles[max(0, i - 6) : i]
        prior_return = (
            (candle.close / prior[0].close - 1.0) * 100.0
            if prior and prior[0].close > 0.0
            else 0.0
        )
        prior_range = (
            (max(row.high for row in prior) / min(row.low for row in prior) - 1.0) * 100.0
            if prior
            else 0.0
        )
        precursor_rows.append(
            {
                "max_return_pct": max_return,
                "prior_6h_return_pct": prior_return,
                "prior_6h_range_pct": prior_range,
            }
        )

    rates: list[dict[str, Any]] = []
    for threshold in thresholds_pct:
        hits = [row for row in precursor_rows if row["max_return_pct"] >= threshold]
        lo, hi = wilson_interval(len(hits), len(anchors))
        rates.append(
            {
                "threshold_pct": threshold,
                "events": len(hits),
                "anchors": len(anchors),
                "event_rate_pct": round(
                    100.0 * len(hits) / len(anchors), 6
                ) if anchors else 0.0,
                "wilson95_pct": [round(100.0 * lo, 6), round(100.0 * hi, 6)],
                "median_prior_6h_return_pct": round(
                    median(row["prior_6h_return_pct"] for row in hits), 6
                ),
                "median_prior_6h_range_pct": round(
                    median(row["prior_6h_range_pct"] for row in hits), 6
                ),
            }
        )
    return {
        "horizon_hours": horizon_hours,
        "daily_non_overlapping_anchors": len(anchors),
        "status": "ok" if len(anchors) >= 60 else "insufficient_history",
        "p95_forward_max_return_pct": round(percentile(max_returns, 95.0), 6),
        "p99_forward_max_return_pct": round(percentile(max_returns, 99.0), 6),
        "max_forward_return_pct": round(max(max_returns), 6) if max_returns else 0.0,
        "event_rates": rates,
        "warning": (
            None
            if len(anchors) >= 60
            else "Fewer than 60 non-overlapping daily anchors; do not use for execution authorization."
        ),
    }


def load_auxiliary_clusters(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in payload.get("pair_clusters", []):
        if not isinstance(row, dict):
            continue
        for key in ("pair", "wsname", "pair_id"):
            token = str(row.get(key) or "").upper().replace("/", "").replace("-", "")
            if token:
                out[token] = row
    return out


def analyze_symbol(
    symbol: str,
    quote: str,
    source_file: Path,
    candles: list[Candle],
    args: argparse.Namespace,
    auxiliary_clusters: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    samples = build_forward_samples(
        candles,
        horizon_hours=args.horizon_hours,
        roundtrip_cost_bps=args.roundtrip_cost_bps,
        daily_extreme_tolerance_bps=args.daily_extreme_tolerance_bps,
    )
    split_index = max(1, min(len(samples) - 1, int(len(samples) * args.train_fraction)))
    train = samples[:split_index]
    test = samples[split_index:]

    hour_train = group_summary(train, lambda row: row.hour, args.prior_strength)
    hour_test = group_summary(test, lambda row: row.hour, args.prior_strength)
    weekday_train = group_summary(train, lambda row: row.weekday, args.prior_strength)
    weekday_hour_train = group_summary(
        train,
        lambda row: (row.weekday, row.hour),
        args.prior_strength,
    )

    ranked_hours_all = sorted(
        (
            {"hour_utc": int(hour), **summary}
            for hour, summary in hour_train.items()
            if summary["samples"] >= args.min_bucket_samples
        ),
        key=lambda row: (
            row["timing_score"],
            row["daily_low_posterior_pct"],
            row["median_net_mfe_pct"],
        ),
        reverse=True,
    )
    ranked_hours = [
        row
        for row in ranked_hours_all
        if row["timing_score"] > 0.0
        and row["median_net_mfe_pct"] > 0.0
        and row["daily_low_events"] >= 2
    ]
    selected_hours = [row["hour_utc"] for row in ranked_hours[: args.top_windows]]
    walk_forward = evaluate_selected_hours(
        test,
        selected_hours,
        args.prior_strength,
    )

    exploratory_weekday_hours = sorted(
        (
            {
                "weekday_utc": int(key[0]),
                "weekday_name": WEEKDAY_NAMES[int(key[0])],
                "hour_utc": int(key[1]),
                **summary,
            }
            for key, summary in weekday_hour_train.items()
            if summary["samples"] >= args.min_weekday_hour_samples
        ),
        key=lambda row: (
            row["timing_score"],
            row["daily_low_posterior_pct"],
        ),
        reverse=True,
    )[: args.top_windows]

    pair_tokens = {
        f"{symbol}{quote}".upper(),
        ("XBT" + quote).upper() if symbol == "BTC" else "",
    }
    auxiliary = next(
        (
            auxiliary_clusters[token]
            for token in pair_tokens
            if token and token in auxiliary_clusters
        ),
        None,
    )
    coverage_hours = (
        (candles[-1].ts - candles[0].ts).total_seconds() / 3600.0
        if len(candles) >= 2
        else 0.0
    )
    effective_weeks = coverage_hours / (24.0 * 7.0)
    selected_test = walk_forward.get("selected") or {}
    holdout_pass = bool(
        selected_hours
        and selected_test.get("samples", 0) >= 30
        and walk_forward.get("net_mfe_lift_pct_points", 0.0) > 0.0
        and walk_forward.get("close_return_lift_pct_points", 0.0) > 0.0
        and selected_test.get("median_close_return_pct", 0.0) > 0.0
    )
    validation_status = (
        "insufficient_history"
        if effective_weeks < 26 or len(test) < 500
        else "no_positive_train_candidate"
        if not selected_hours
        else "walk_forward_pass"
        if holdout_pass
        else "walk_forward_fail"
    )
    holdout_diagnostic = (
        "no_train_candidate"
        if not selected_hours
        else "pass"
        if holdout_pass
        else "fail"
    )
    return {
        "symbol": symbol,
        "quote": quote,
        "pair": f"{symbol}/{quote}",
        "source_file": str(source_file.resolve()),
        "bars": len(candles),
        "interval_hours": round(interval_hours(candles), 6),
        "first_utc": candles[0].ts.isoformat(),
        "last_utc": candles[-1].ts.isoformat(),
        "coverage_days": round(coverage_hours / 24.0, 6),
        "effective_weeks": round(effective_weeks, 6),
        "horizon_hours": args.horizon_hours,
        "train_samples": len(train),
        "test_samples": len(test),
        "history_status": (
            "production_candidate"
            if effective_weeks >= 26 and len(test) >= 500
            else "research_only"
        ),
        "validation_status": validation_status,
        "holdout_diagnostic": holdout_diagnostic,
        "hour_models_train": [
            {"hour_utc": int(hour), **summary}
            for hour, summary in sorted(hour_train.items())
        ],
        "hour_models_test": [
            {"hour_utc": int(hour), **summary}
            for hour, summary in sorted(hour_test.items())
        ],
        "weekday_models_train": [
            {
                "weekday_utc": int(weekday),
                "weekday_name": WEEKDAY_NAMES[int(weekday)],
                **summary,
            }
            for weekday, summary in sorted(weekday_train.items())
        ],
        "best_buy_windows_train": ranked_hours[: args.top_windows],
        "rejected_hour_models_train": ranked_hours_all[: args.top_windows],
        "exploratory_weekday_hour_windows_train": exploratory_weekday_hours,
        "walk_forward_test": walk_forward,
        "moonshot_event_study": moonshot_event_study(
            candles,
            thresholds_pct=args.moonshot_thresholds_pct,
            horizon_hours=args.moonshot_horizon_hours,
        ),
        "auxiliary_daily_cluster": (
            {
                "generated_utc": auxiliary.get("generated_utc"),
                "best_weekday_utc": auxiliary.get("best_weekday_utc"),
                "best_weekday_name": auxiliary.get("best_weekday_name"),
                "best_weekday_score": auxiliary.get("best_weekday_score"),
                "weekday_samples": auxiliary.get("weekday_samples"),
                "weekday_coverage_days": auxiliary.get("weekday_coverage_days"),
                "note": "Auxiliary in-sample daily-resolution context; not part of walk-forward score.",
            }
            if auxiliary
            else None
        ),
        "execution_authorized": False,
        "limitations": [
            "Daily-low labels use completed-day extremes for research labeling only.",
            "Weekday-hour cells are exploratory when history provides only a few weekly repeats.",
            "Walk-forward results are necessary but not sufficient for live execution.",
            "Moonshot event rates require at least 60 non-overlapping daily anchors.",
        ],
    }


def markdown_report(payload: dict[str, Any]) -> str:
    coverages = [
        safe_float(row.get("coverage_days"))
        for row in payload.get("symbols", [])
        if safe_float(row.get("coverage_days")) > 0.0
    ]
    median_coverage = median(coverages)
    max_coverage = max(coverages) if coverages else 0.0
    lines = [
        "# Symbol Timing Edge Model",
        "",
        f"Generated UTC: {payload.get('generated_utc')}",
        f"Symbols analyzed: {payload.get('symbols_analyzed')}",
        f"Execution authorized: {payload.get('execution_authorized')}",
        "",
        "## Evidence Contract",
        "",
        "- Hour and weekday effects are estimated separately with Bayesian shrinkage.",
        "- Candidate buy hours are selected on the training segment and measured on the later test segment.",
        "- Exact weekday-hour windows remain exploratory until enough weekly repeats exist.",
        "- Rare-event rates use non-overlapping daily anchors and are disabled when history is insufficient.",
        "",
        "## Top Walk-Forward Results",
        "",
        "| Pair | Coverage days | Test samples | Buy hours UTC | Net MFE lift pp | Close-return lift pp | Status |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    ranked = sorted(
        [
            row
            for row in payload.get("symbols", [])
            if (row.get("walk_forward_test") or {}).get("selected_hours_utc")
        ],
        key=lambda row: safe_float(
            (row.get("walk_forward_test") or {}).get("net_mfe_lift_pct_points")
        ),
        reverse=True,
    )
    for row in ranked[:25]:
        wf = row.get("walk_forward_test") or {}
        hours = ",".join(str(hour) for hour in wf.get("selected_hours_utc", []))
        lines.append(
            f"| {row.get('pair')} | {row.get('coverage_days')} | "
            f"{row.get('test_samples')} | {hours} | "
            f"{wf.get('net_mfe_lift_pct_points')} | "
            f"{wf.get('close_return_lift_pct_points')} | "
            f"{row.get('history_status')}/holdout_{row.get('holdout_diagnostic')} |"
        )
    if not ranked:
        lines.append("| none | - | - | - | - | - | no positive training candidate |")
    lines.extend(
        [
            "",
            "## Important Limitation",
            "",
            f"The current local universe has median coverage of {median_coverage:.1f} days "
            f"and maximum coverage of {max_coverage:.1f} days. These outputs are research evidence, "
            "not live-order authorization. The model becomes a production candidate only "
            "after at least 26 weeks of hourly history and a materially sized holdout.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any], out_root: Path) -> dict[str, str]:
    stamp = now_tag()
    run_dir = out_root / f"symbol_timing_edge_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_json = run_dir / "symbol_timing_edge.json"
    run_csv = run_dir / "symbol_timing_edge.csv"
    run_md = run_dir / "symbol_timing_edge.md"
    latest_json = out_root / "symbol_timing_edge_latest.json"
    latest_csv = out_root / "symbol_timing_edge_latest.csv"
    latest_md = out_root / "symbol_timing_edge_latest.md"

    compact_rows: list[dict[str, Any]] = []
    for row in payload.get("symbols", []):
        wf = row.get("walk_forward_test") or {}
        selected = wf.get("selected") or {}
        moonshot = row.get("moonshot_event_study") or {}
        compact_rows.append(
            {
                "pair": row.get("pair"),
                "bars": row.get("bars"),
                "coverage_days": row.get("coverage_days"),
                "history_status": row.get("history_status"),
                "validation_status": row.get("validation_status"),
                "holdout_diagnostic": row.get("holdout_diagnostic"),
                "selected_hours_utc": ",".join(
                    str(hour) for hour in wf.get("selected_hours_utc", [])
                ),
                "test_samples": row.get("test_samples"),
                "test_median_net_mfe_pct": selected.get("median_net_mfe_pct"),
                "test_median_close_return_pct": selected.get("median_close_return_pct"),
                "test_daily_low_posterior_pct": selected.get("daily_low_posterior_pct"),
                "net_mfe_lift_pct_points": wf.get("net_mfe_lift_pct_points"),
                "close_return_lift_pct_points": wf.get("close_return_lift_pct_points"),
                "moonshot_status": moonshot.get("status"),
                "moonshot_p99_forward_max_return_pct": moonshot.get(
                    "p99_forward_max_return_pct"
                ),
                "execution_authorized": False,
            }
        )

    report = markdown_report(payload)
    for path in (run_json, latest_json):
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for path in (run_md, latest_md):
        path.write_text(report + "\n", encoding="utf-8")
    fieldnames = list(compact_rows[0].keys()) if compact_rows else ["pair"]
    for path in (run_csv, latest_csv):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(compact_rows)
    return {
        "run_json": str(run_json),
        "run_csv": str(run_csv),
        "run_md": str(run_md),
        "latest_json": str(latest_json),
        "latest_csv": str(latest_csv),
        "latest_md": str(latest_md),
    }


def parse_thresholds(raw: str) -> list[float]:
    values = [
        safe_float(token)
        for token in str(raw or "").split(",")
        if str(token).strip()
    ]
    return sorted({value for value in values if value > 0.0}) or [10.0, 20.0, 50.0]


def build_model(args: argparse.Namespace) -> dict[str, Any]:
    roots = [Path(value).resolve() for value in args.data_root]
    candidates: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.glob("ohlc_*.csv"):
            candidates[str(path.resolve())] = path
    extra_file = Path(args.extra_file).resolve()
    if extra_file.exists():
        candidates[str(extra_file)] = extra_file

    auxiliary_clusters = load_auxiliary_clusters(Path(args.cluster_file).resolve())
    best_by_pair: dict[tuple[str, str], tuple[Path, list[Candle]]] = {}
    skipped: list[dict[str, Any]] = []
    for path in sorted(candidates.values(), key=lambda item: str(item).lower()):
        symbol, quote = parse_symbol_from_file(path)
        if not symbol or not quote:
            skipped.append({"path": str(path), "reason": "symbol_parse_failed"})
            continue
        if symbol in STABLE_OR_FIAT:
            skipped.append({"path": str(path), "reason": "stable_or_fiat_filtered"})
            continue
        candles = load_candles(path)
        cadence = interval_hours(candles)
        if not (0.75 <= cadence <= 1.25):
            skipped.append({
                "path": str(path),
                "reason": f"not_hourly_interval_{cadence:.3f}",
            })
            continue
        if len(candles) < args.min_bars:
            skipped.append({
                "path": str(path),
                "reason": f"insufficient_bars_{len(candles)}",
            })
            continue
        key = (symbol, quote)
        previous = best_by_pair.get(key)
        if previous is None or len(candles) > len(previous[1]):
            best_by_pair[key] = (path, candles)

    rows = [
        analyze_symbol(
            symbol=symbol,
            quote=quote,
            source_file=source_file,
            candles=candles,
            args=args,
            auxiliary_clusters=auxiliary_clusters,
        )
        for (symbol, quote), (source_file, candles) in sorted(best_by_pair.items())
    ]
    payload = {
        "generated_utc": now_iso(),
        "scope": "symbol_timing_edge_model",
        "model_version": "1.0",
        "execution_authorized": False,
        "controls": {
            "data_roots": [str(path) for path in roots],
            "extra_file": str(extra_file),
            "cluster_file": str(Path(args.cluster_file).resolve()),
            "min_bars": args.min_bars,
            "horizon_hours": args.horizon_hours,
            "roundtrip_cost_bps": args.roundtrip_cost_bps,
            "daily_extreme_tolerance_bps": args.daily_extreme_tolerance_bps,
            "train_fraction": args.train_fraction,
            "prior_strength": args.prior_strength,
            "min_bucket_samples": args.min_bucket_samples,
            "min_weekday_hour_samples": args.min_weekday_hour_samples,
            "moonshot_thresholds_pct": args.moonshot_thresholds_pct,
            "moonshot_horizon_hours": args.moonshot_horizon_hours,
        },
        "symbols_analyzed": len(rows),
        "files_skipped": len(skipped),
        "symbols": rows,
        "skipped_samples": skipped[:200],
        "production_gate": {
            "status": "blocked",
            "reasons": [
                "No symbol currently has the required 26 weeks of hourly history plus a large holdout.",
                "The artifact is shadow research and cannot authorize orders.",
            ],
        },
    }
    payload["evidence_paths"] = write_outputs(payload, Path(args.out_root).resolve())
    for path_key in ("run_json", "latest_json"):
        Path(payload["evidence_paths"][path_key]).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a leakage-aware, walk-forward symbol timing and rare-event model "
            "from local hourly OHLC evidence."
        )
    )
    parser.add_argument(
        "--data-root",
        action="append",
        default=[],
        help="Directory containing ohlc_<BASE>_<QUOTE>.csv files. Repeatable.",
    )
    parser.add_argument("--extra-file", default=str(DEFAULT_EXTRA_FILE))
    parser.add_argument("--cluster-file", default=str(DEFAULT_CLUSTER_FILE))
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--min-bars", type=int, default=168)
    parser.add_argument("--horizon-hours", type=int, default=24)
    parser.add_argument("--roundtrip-cost-bps", type=float, default=52.0)
    parser.add_argument("--daily-extreme-tolerance-bps", type=float, default=10.0)
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--prior-strength", type=float, default=20.0)
    parser.add_argument("--min-bucket-samples", type=int, default=5)
    parser.add_argument("--min-weekday-hour-samples", type=int, default=2)
    parser.add_argument("--top-windows", type=int, default=3)
    parser.add_argument("--moonshot-thresholds-pct", default="10,20,50,100")
    parser.add_argument("--moonshot-horizon-hours", type=int, default=48)
    args = parser.parse_args()
    if not args.data_root:
        args.data_root = [str(DEFAULT_DATA_ROOT)]
    args.train_fraction = max(0.5, min(0.9, float(args.train_fraction)))
    args.moonshot_thresholds_pct = parse_thresholds(args.moonshot_thresholds_pct)
    return args


def main() -> int:
    payload = build_model(parse_args())
    print(f"SYMBOL_TIMING_EDGE_JSON={payload['evidence_paths']['run_json']}")
    print(
        "SYMBOL_TIMING_EDGE_COUNTS "
        f"analyzed={payload['symbols_analyzed']} skipped={payload['files_skipped']}"
    )
    print("SYMBOL_TIMING_EDGE_EXECUTION_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
