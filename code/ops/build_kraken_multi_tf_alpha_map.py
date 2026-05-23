from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://api.kraken.com/0/public"
DEFAULT_QUOTES = ("ZUSD", "USDT")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def pct_change(closes: list[float], lookback: int) -> float:
    if len(closes) <= lookback:
        return 0.0
    old = to_float(closes[-lookback - 1], 0.0)
    cur = to_float(closes[-1], 0.0)
    if old <= 0.0:
        return 0.0
    return (cur - old) / old * 100.0


def rel_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def parse_quotes(raw: str) -> tuple[str, ...]:
    parts = [p.strip().upper() for p in str(raw or "").split(",") if p.strip()]
    if not parts:
        return DEFAULT_QUOTES
    return tuple(parts)


def kraken_get(session: requests.Session, path: str, params: dict[str, Any] | None, timeout_sec: float) -> dict[str, Any]:
    resp = session.get(f"{BASE_URL}/{path}", params=params, timeout=timeout_sec)
    resp.raise_for_status()
    payload = resp.json()
    errors = payload.get("error") or []
    if errors:
        raise RuntimeError(f"Kraken {path} error: {errors}")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"Kraken {path} returned non-dict result")
    return result


def fetch_pairs(
    session: requests.Session,
    timeout_sec: float,
    quotes: tuple[str, ...],
) -> list[dict[str, Any]]:
    payload = kraken_get(session, "AssetPairs", None, timeout_sec)
    rows: list[dict[str, Any]] = []

    for pair_id, meta in payload.items():
        if not isinstance(meta, dict):
            continue

        status = str(meta.get("status") or "")
        quote = str(meta.get("quote") or "")
        altname = str(meta.get("altname") or pair_id)
        wsname = str(meta.get("wsname") or altname)

        if status != "online":
            continue
        if quote not in quotes:
            continue

        # Ignore dark pool variants for clean spot scanning.
        if ".d" in altname or ".d" in wsname:
            continue

        rows.append(
            {
                "pair_id": pair_id,
                "altname": altname,
                "wsname": wsname,
                "base": str(meta.get("base") or ""),
                "quote": quote,
            }
        )

    rows.sort(key=lambda r: r["pair_id"])
    return rows


def fetch_tickers(
    session: requests.Session,
    pairs: list[dict[str, Any]],
    timeout_sec: float,
    request_pause_sec: float,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    pair_ids = [str(p.get("pair_id") or "") for p in pairs if str(p.get("pair_id") or "")]

    chunk_size = 20
    for i in range(0, len(pair_ids), chunk_size):
        chunk = pair_ids[i : i + chunk_size]
        if not chunk:
            continue
        try:
            payload = kraken_get(
                session,
                "Ticker",
                {"pair": ",".join(chunk)},
                timeout_sec,
            )
        except Exception:
            payload = {}

        for key, value in payload.items():
            if isinstance(value, dict):
                out[str(key)] = value

        if request_pause_sec > 0:
            time.sleep(request_pause_sec)

    return out


def ticker_metrics(item: dict[str, Any]) -> dict[str, float]:
    last = to_float((item.get("c") or [0.0])[0], 0.0)
    ask = to_float((item.get("a") or [0.0])[0], 0.0)
    bid = to_float((item.get("b") or [0.0])[0], 0.0)
    open_24h = to_float(item.get("o"), 0.0)
    high_24h = to_float((item.get("h") or [0.0, 0.0])[1], 0.0)
    low_24h = to_float((item.get("l") or [0.0, 0.0])[1], 0.0)
    vol_24h = to_float((item.get("v") or [0.0, 0.0])[1], 0.0)
    trades_24h = to_int((item.get("t") or [0, 0])[1], 0)

    spread_bps = 0.0
    if last > 0.0 and ask > 0.0 and bid > 0.0:
        spread_bps = (ask - bid) / last * 10000.0

    range_24h_pct = 0.0
    if low_24h > 0.0 and high_24h >= low_24h:
        range_24h_pct = (high_24h - low_24h) / low_24h * 100.0

    change_24h_pct = 0.0
    if open_24h > 0.0:
        change_24h_pct = (last - open_24h) / open_24h * 100.0

    turnover_24h_usd = last * vol_24h if last > 0.0 and vol_24h > 0.0 else 0.0

    return {
        "last": last,
        "ask": ask,
        "bid": bid,
        "spread_bps": spread_bps,
        "range_24h_pct": range_24h_pct,
        "change_24h_pct": change_24h_pct,
        "turnover_24h_usd": turnover_24h_usd,
        "trades_24h": float(trades_24h),
    }


def prefilter_pairs(
    pairs: list[dict[str, Any]],
    tickers: dict[str, dict[str, Any]],
    top_liquid: int,
    min_turnover_usd: float,
    max_spread_bps: float,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []

    for row in pairs:
        pair_id = str(row.get("pair_id") or "")
        altname = str(row.get("altname") or "")
        item = tickers.get(pair_id) or tickers.get(altname)
        if not isinstance(item, dict):
            continue

        tm = ticker_metrics(item)
        if tm["last"] <= 0.0:
            continue
        if tm["turnover_24h_usd"] < min_turnover_usd:
            continue

        spread_penalty = max(tm["spread_bps"] - max_spread_bps, 0.0)
        prefilter_score = (
            math.log10(tm["turnover_24h_usd"] + 1.0) * 12.0
            + tm["range_24h_pct"] * 2.0
            + abs(tm["change_24h_pct"]) * 1.2
            + math.log10(max(tm["trades_24h"], 1.0)) * 2.0
            - spread_penalty * 1.5
        )

        enriched.append(
            {
                **row,
                **tm,
                "prefilter_score": round(prefilter_score, 6),
            }
        )

    enriched.sort(key=lambda r: r.get("prefilter_score", 0.0), reverse=True)
    return enriched[: max(1, int(top_liquid))]


def fetch_ohlc(
    session: requests.Session,
    pair_id: str,
    interval: int,
    since_ts: int,
    timeout_sec: float,
) -> list[list[Any]]:
    payload = kraken_get(
        session,
        "OHLC",
        {"pair": pair_id, "interval": int(interval), "since": int(since_ts)},
        timeout_sec,
    )

    for key, value in payload.items():
        if key == "last":
            continue
        if isinstance(value, list):
            return value
    return []


def close_series(rows: list[list[Any]]) -> list[float]:
    out: list[float] = []
    for r in rows:
        if not isinstance(r, list) or len(r) < 5:
            continue
        c = to_float(r[4], 0.0)
        if c > 0.0:
            out.append(c)
    return out


def hourly_forward_returns(rows: list[list[Any]]) -> dict[int, list[float]]:
    by_hour: dict[int, list[float]] = defaultdict(list)
    if len(rows) < 3:
        return by_hour

    closes = close_series(rows)
    if len(closes) < 3:
        return by_hour

    for i in range(0, min(len(rows), len(closes)) - 1):
        raw_ts = to_float(rows[i][0], 0.0)
        if raw_ts <= 0.0:
            continue
        ts = datetime.fromtimestamp(raw_ts, tz=timezone.utc)
        c0 = closes[i]
        c1 = closes[i + 1]
        if c0 <= 0.0:
            continue
        by_hour[ts.hour].append((c1 - c0) / c0 * 100.0)

    return by_hour


def recent_returns(series: list[float], windows: list[int]) -> dict[int, float]:
    return {w: round(pct_change(series, w), 6) for w in windows}


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    try:
        return float(statistics.pstdev(values))
    except Exception:
        return 0.0


def daily_return_series(closes: list[float]) -> list[float]:
    out: list[float] = []
    if len(closes) < 2:
        return out

    for i in range(1, len(closes)):
        prev = to_float(closes[i - 1], 0.0)
        cur = to_float(closes[i], 0.0)
        if prev <= 0.0:
            continue
        out.append((cur - prev) / prev * 100.0)
    return out


def hit_counts(changes: list[float], lookback: int, threshold_pct: float) -> dict[str, float]:
    if not changes:
        return {
            "up_hits": 0.0,
            "down_hits": 0.0,
            "up_freq_pct": 0.0,
            "down_freq_pct": 0.0,
        }

    sample = changes[-lookback:] if len(changes) >= lookback else changes
    n = float(len(sample))
    if n <= 0.0:
        return {
            "up_hits": 0.0,
            "down_hits": 0.0,
            "up_freq_pct": 0.0,
            "down_freq_pct": 0.0,
        }

    up_hits = float(sum(1 for x in sample if x >= threshold_pct))
    down_hits = float(sum(1 for x in sample if x <= -threshold_pct))

    return {
        "up_hits": up_hits,
        "down_hits": down_hits,
        "up_freq_pct": up_hits / n * 100.0,
        "down_freq_pct": down_hits / n * 100.0,
    }


def score_row(row: dict[str, Any], max_spread_bps: float) -> dict[str, Any]:
    r1m = to_float(row.get("r_1m_pct"), 0.0)
    r5m = to_float(row.get("r_5m_pct"), 0.0)
    r30m = to_float(row.get("r_30m_pct"), 0.0)
    r1h = to_float(row.get("r_1h_pct"), 0.0)
    r24h = to_float(row.get("r_24h_pct"), 0.0)
    r7d = to_float(row.get("r_7d_pct"), 0.0)
    r30d = to_float(row.get("r_30d_pct"), 0.0)
    r180d = to_float(row.get("r_180d_pct"), 0.0)

    spread_bps = to_float(row.get("spread_bps"), 0.0)
    turnover_24h_usd = to_float(row.get("turnover_24h_usd"), 0.0)
    hv_24h_pct = to_float(row.get("hv_24h_pct"), 0.0)
    up_freq_30 = to_float(row.get("up_spike_freq_30d_pct"), 0.0)
    down_freq_30 = to_float(row.get("down_spike_freq_30d_pct"), 0.0)

    momentum_score = (
        clamp(r1m, -3.0, 3.0) * 4.0
        + clamp(r5m, -8.0, 8.0) * 2.8
        + clamp(r30m, -18.0, 18.0) * 1.5
        + clamp(r1h, -25.0, 25.0) * 1.2
        + clamp(r24h, -60.0, 60.0) * 0.35
    )

    trend_score = (
        clamp(r7d, -120.0, 120.0) * 0.22
        + clamp(r30d, -260.0, 260.0) * 0.10
        + clamp(r180d, -400.0, 400.0) * 0.04
    )

    reversion_score = (
        max(0.0, -r24h) * 0.70
        + max(0.0, -r7d) * 0.25
        + max(0.0, -r30d) * 0.08
    )

    liquidity_score = clamp(math.log10(turnover_24h_usd + 1.0), 4.0, 9.0) * 3.0
    volatility_score = clamp(hv_24h_pct, 0.0, 6.0) * 1.8 + clamp(up_freq_30 + down_freq_30, 0.0, 30.0) * 0.45

    spread_penalty = max(spread_bps - max_spread_bps, 0.0) * 1.3
    execution_quality_score = clamp(22.0 - spread_bps * 0.35, 0.0, 22.0)

    alpha_edge_score = (
        momentum_score * 0.42
        + trend_score * 0.18
        + reversion_score * 0.16
        + liquidity_score * 0.10
        + volatility_score * 0.09
        + execution_quality_score * 0.05
        - spread_penalty
    )

    strategy_mode = "watch"
    if momentum_score >= 16.0 and spread_bps <= max_spread_bps:
        strategy_mode = "momentum_snipe"
    elif reversion_score >= 14.0 and spread_bps <= max_spread_bps * 1.1:
        strategy_mode = "mean_reversion_snapback"
    elif trend_score >= 12.0 and spread_bps <= max_spread_bps * 1.2:
        strategy_mode = "trend_follow_swing"

    return {
        **row,
        "momentum_score": round(momentum_score, 6),
        "trend_score": round(trend_score, 6),
        "reversion_score": round(reversion_score, 6),
        "liquidity_score": round(liquidity_score, 6),
        "volatility_score": round(volatility_score, 6),
        "execution_quality_score": round(execution_quality_score, 6),
        "spread_penalty": round(spread_penalty, 6),
        "alpha_edge_score": round(alpha_edge_score, 6),
        "strategy_mode": strategy_mode,
    }


def pick_top(rows: list[dict[str, Any]], key: str, n: int, reverse: bool = True) -> list[dict[str, Any]]:
    picked = sorted(rows, key=lambda r: to_float(r.get(key), 0.0), reverse=reverse)[:n]
    return [
        {
            "pair": r.get("pair"),
            "wsname": r.get("wsname"),
            key: r.get(key),
            "alpha_edge_score": r.get("alpha_edge_score"),
            "strategy_mode": r.get("strategy_mode"),
            "turnover_24h_usd": r.get("turnover_24h_usd"),
            "spread_bps": r.get("spread_bps"),
        }
        for r in picked
    ]


def median_hourly_curve(hour_map: dict[int, list[float]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hour in sorted(hour_map.keys()):
        vals = hour_map[hour]
        if len(vals) < 6:
            continue
        rows.append(
            {
                "hour_utc": int(hour),
                "samples": len(vals),
                "median_forward_1h_pct": round(float(statistics.median(vals)), 6),
                "mean_forward_1h_pct": round(float(sum(vals) / len(vals)), 6),
                "win_rate_pct": round(float(sum(1 for v in vals if v > 0.0) / len(vals) * 100.0), 6),
            }
        )
    return rows


def markdown_report(summary: dict[str, Any], leaders: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Kraken Multi-Timeframe Alpha Map")
    lines.append("")
    lines.append(f"Generated UTC: {summary.get('generated_utc')}")
    lines.append(f"Scope: {summary.get('scope')}")
    lines.append("")
    lines.append("## Coverage")
    lines.append(f"- Pairs discovered: {summary.get('pairs_discovered', 0)}")
    lines.append(f"- Pairs after liquidity filter: {summary.get('pairs_after_liquidity_filter', 0)}")
    lines.append(f"- Pairs analyzed: {summary.get('pairs_analyzed', 0)}")
    lines.append(f"- Pair-level errors: {summary.get('pair_errors', 0)}")
    lines.append("")
    lines.append("## Controls")
    lines.append(f"- Min turnover USD: {summary.get('controls', {}).get('min_turnover_usd')}")
    lines.append(f"- Max spread bps (soft): {summary.get('controls', {}).get('max_spread_bps')}")
    lines.append(f"- Spike threshold pct: {summary.get('controls', {}).get('spike_threshold_pct')}")
    lines.append("")
    lines.append("## Top Alpha Edge")
    lines.append("| Rank | Pair | Strategy | Alpha Edge | Spread bps | 24h Turnover USD |")
    lines.append("|---:|---|---|---:|---:|---:|")
    for i, row in enumerate(leaders, 1):
        lines.append(
            "| "
            + str(i)
            + " | "
            + str(row.get("pair") or "")
            + " | "
            + str(row.get("strategy_mode") or "")
            + " | "
            + str(row.get("alpha_edge_score") or 0)
            + " | "
            + str(row.get("spread_bps") or 0)
            + " | "
            + str(round(to_float(row.get("turnover_24h_usd"), 0.0), 2))
            + " |"
        )
    lines.append("")
    lines.append("## Evidence Paths")
    for key, value in (summary.get("evidence_paths") or {}).items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build_alpha_map(args: argparse.Namespace) -> dict[str, Any]:
    stack_root = Path(args.stack_root).resolve()
    workspace_root = stack_root.parent
    out_root = Path(args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    run_stamp = now_tag()
    run_dir = out_root / f"kraken_multi_tf_alpha_map_{run_stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "LumaKrakenMultiTFAlphaMap/1.0"})

    quotes = parse_quotes(args.quotes)
    pairs = fetch_pairs(session, args.timeout_sec, quotes)
    tickers = fetch_tickers(session, pairs, args.timeout_sec, args.request_pause_sec)

    filtered = prefilter_pairs(
        pairs=pairs,
        tickers=tickers,
        top_liquid=args.top_liquid,
        min_turnover_usd=args.min_turnover_usd,
        max_spread_bps=args.max_spread_bps,
    )

    now_ts = int(time.time())
    since_1m = now_ts - 3 * 3600
    since_5m = now_ts - 36 * 3600
    since_30m = now_ts - 21 * 24 * 3600
    since_1h = now_ts - 21 * 24 * 3600
    since_1d = now_ts - 420 * 24 * 3600

    analyzed_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    global_hourly_returns: dict[int, list[float]] = defaultdict(list)

    for idx, row in enumerate(filtered, start=1):
        pair_id = str(row.get("pair_id") or "")
        wsname = str(row.get("wsname") or pair_id)

        try:
            ohlc_1h = fetch_ohlc(session, pair_id, 60, since_1h, args.timeout_sec)
            closes_1h = close_series(ohlc_1h)
            if len(closes_1h) < 48:
                raise RuntimeError("insufficient_1h_bars")

            ohlc_1m = fetch_ohlc(session, pair_id, 1, since_1m, args.timeout_sec)
            closes_1m = close_series(ohlc_1m)

            ohlc_5m = fetch_ohlc(session, pair_id, 5, since_5m, args.timeout_sec)
            closes_5m = close_series(ohlc_5m)

            ohlc_30m = fetch_ohlc(session, pair_id, 30, since_30m, args.timeout_sec)
            closes_30m = close_series(ohlc_30m)

            ohlc_1d = fetch_ohlc(session, pair_id, 1440, since_1d, args.timeout_sec)
            closes_1d = close_series(ohlc_1d)
            if len(closes_1d) < 60:
                raise RuntimeError("insufficient_1d_bars")

            ret_1m = recent_returns(closes_1m, [1]).get(1, 0.0)
            ret_5m = recent_returns(closes_5m, [1]).get(1, 0.0)
            ret_30m = recent_returns(closes_30m, [1]).get(1, 0.0)

            ret_1h_map = recent_returns(closes_1h, [1, 24])
            ret_1d_map = recent_returns(closes_1d, [7, 30, 180, 365])

            hourly_curve = hourly_forward_returns(ohlc_1h)
            for hour, vals in hourly_curve.items():
                global_hourly_returns[hour].extend(vals)

            hourly_returns_pct = []
            for i in range(1, len(closes_1h)):
                prev = closes_1h[i - 1]
                cur = closes_1h[i]
                if prev > 0.0:
                    hourly_returns_pct.append((cur - prev) / prev * 100.0)
            hv_24h_pct = stdev(hourly_returns_pct[-24:]) if hourly_returns_pct else 0.0

            day_changes = daily_return_series(closes_1d)
            spikes_30 = hit_counts(day_changes, 30, args.spike_threshold_pct)
            spikes_180 = hit_counts(day_changes, 180, args.spike_threshold_pct)

            best_buy_hour = -1
            best_buy_hour_median = -999.0
            best_sell_hour = -1
            best_sell_hour_median = 999.0

            for hour, vals in hourly_curve.items():
                if len(vals) < 6:
                    continue
                med = float(statistics.median(vals))
                if med > best_buy_hour_median:
                    best_buy_hour = int(hour)
                    best_buy_hour_median = med
                if med < best_sell_hour_median:
                    best_sell_hour = int(hour)
                    best_sell_hour_median = med

            enriched = {
                "pair": pair_id,
                "wsname": wsname,
                "altname": row.get("altname"),
                "quote": row.get("quote"),
                "price": round(to_float(row.get("last"), 0.0), 8),
                "spread_bps": round(to_float(row.get("spread_bps"), 0.0), 6),
                "range_24h_pct": round(to_float(row.get("range_24h_pct"), 0.0), 6),
                "change_24h_pct": round(to_float(row.get("change_24h_pct"), 0.0), 6),
                "turnover_24h_usd": round(to_float(row.get("turnover_24h_usd"), 0.0), 2),
                "trades_24h": to_int(row.get("trades_24h"), 0),
                "prefilter_score": round(to_float(row.get("prefilter_score"), 0.0), 6),
                "r_1m_pct": round(ret_1m, 6),
                "r_5m_pct": round(ret_5m, 6),
                "r_30m_pct": round(ret_30m, 6),
                "r_1h_pct": round(ret_1h_map.get(1, 0.0), 6),
                "r_24h_pct": round(ret_1h_map.get(24, 0.0), 6),
                "r_7d_pct": round(ret_1d_map.get(7, 0.0), 6),
                "r_30d_pct": round(ret_1d_map.get(30, 0.0), 6),
                "r_180d_pct": round(ret_1d_map.get(180, 0.0), 6),
                "r_365d_pct": round(ret_1d_map.get(365, 0.0), 6),
                "hv_24h_pct": round(hv_24h_pct, 6),
                "up_spike_hits_30d": to_int(spikes_30["up_hits"], 0),
                "down_spike_hits_30d": to_int(spikes_30["down_hits"], 0),
                "up_spike_freq_30d_pct": round(spikes_30["up_freq_pct"], 6),
                "down_spike_freq_30d_pct": round(spikes_30["down_freq_pct"], 6),
                "up_spike_hits_180d": to_int(spikes_180["up_hits"], 0),
                "down_spike_hits_180d": to_int(spikes_180["down_hits"], 0),
                "up_spike_freq_180d_pct": round(spikes_180["up_freq_pct"], 6),
                "down_spike_freq_180d_pct": round(spikes_180["down_freq_pct"], 6),
                "best_buy_hour_utc": best_buy_hour,
                "best_buy_hour_median_fwd_1h_pct": round(best_buy_hour_median if best_buy_hour >= 0 else 0.0, 6),
                "best_sell_hour_utc": best_sell_hour,
                "best_sell_hour_median_fwd_1h_pct": round(best_sell_hour_median if best_sell_hour >= 0 else 0.0, 6),
            }

            analyzed_rows.append(score_row(enriched, args.max_spread_bps))

            if args.request_pause_sec > 0:
                time.sleep(args.request_pause_sec)

            if idx % 5 == 0 or idx == len(filtered):
                print(
                    f"SCAN_PROGRESS {idx}/{len(filtered)} analyzed={len(analyzed_rows)} errors={len(errors)}"
                )

        except Exception as exc:
            errors.append(
                {
                    "pair": pair_id,
                    "wsname": wsname,
                    "error": str(exc),
                }
            )

    analyzed_rows.sort(key=lambda r: to_float(r.get("alpha_edge_score"), 0.0), reverse=True)

    hourly_curve_rows = median_hourly_curve(global_hourly_returns)
    best_hours = sorted(hourly_curve_rows, key=lambda r: to_float(r.get("median_forward_1h_pct"), 0.0), reverse=True)[:8]
    weak_hours = sorted(hourly_curve_rows, key=lambda r: to_float(r.get("median_forward_1h_pct"), 0.0))[:8]

    leaders = analyzed_rows[: max(1, args.limit)]

    top_up_1h = pick_top(analyzed_rows, "r_1h_pct", 10, reverse=True)
    top_down_1h = pick_top(analyzed_rows, "r_1h_pct", 10, reverse=False)
    top_up_24h = pick_top(analyzed_rows, "r_24h_pct", 10, reverse=True)
    top_down_24h = pick_top(analyzed_rows, "r_24h_pct", 10, reverse=False)

    run_json = run_dir / "kraken_multi_tf_alpha_map.json"
    run_csv = run_dir / "kraken_multi_tf_alpha_map.csv"
    run_md = run_dir / "kraken_multi_tf_alpha_map.md"

    latest_json = out_root / "kraken_multi_tf_alpha_map_latest.json"
    latest_csv = out_root / "kraken_multi_tf_alpha_map_latest.csv"
    latest_md = out_root / "kraken_multi_tf_alpha_map_latest.md"

    summary: dict[str, Any] = {
        "generated_utc": now_iso(),
        "scope": "kraken_multi_tf_alpha_map",
        "controls": {
            "quotes": list(quotes),
            "top_liquid": int(args.top_liquid),
            "limit": int(args.limit),
            "min_turnover_usd": float(args.min_turnover_usd),
            "max_spread_bps": float(args.max_spread_bps),
            "spike_threshold_pct": float(args.spike_threshold_pct),
            "request_pause_sec": float(args.request_pause_sec),
            "timeout_sec": float(args.timeout_sec),
        },
        "pairs_discovered": len(pairs),
        "pairs_after_liquidity_filter": len(filtered),
        "pairs_analyzed": len(analyzed_rows),
        "pair_errors": len(errors),
        "alpha_leaderboard": leaders,
        "movers": {
            "top_up_1h": top_up_1h,
            "top_down_1h": top_down_1h,
            "top_up_24h": top_up_24h,
            "top_down_24h": top_down_24h,
        },
        "timing_windows": {
            "best_buy_hours_utc": best_hours,
            "weak_hours_utc": weak_hours,
        },
        "error_samples": errors[:20],
        "evidence_paths": {
            "run_json": rel_path(run_json, workspace_root),
            "run_csv": rel_path(run_csv, workspace_root),
            "run_md": rel_path(run_md, workspace_root),
            "latest_json": rel_path(latest_json, workspace_root),
            "latest_csv": rel_path(latest_csv, workspace_root),
            "latest_md": rel_path(latest_md, workspace_root),
        },
    }

    csv_columns = [
        "pair",
        "wsname",
        "quote",
        "strategy_mode",
        "alpha_edge_score",
        "momentum_score",
        "trend_score",
        "reversion_score",
        "liquidity_score",
        "volatility_score",
        "execution_quality_score",
        "spread_penalty",
        "price",
        "spread_bps",
        "turnover_24h_usd",
        "trades_24h",
        "range_24h_pct",
        "change_24h_pct",
        "r_1m_pct",
        "r_5m_pct",
        "r_30m_pct",
        "r_1h_pct",
        "r_24h_pct",
        "r_7d_pct",
        "r_30d_pct",
        "r_180d_pct",
        "r_365d_pct",
        "hv_24h_pct",
        "up_spike_hits_30d",
        "down_spike_hits_30d",
        "up_spike_freq_30d_pct",
        "down_spike_freq_30d_pct",
        "up_spike_hits_180d",
        "down_spike_hits_180d",
        "up_spike_freq_180d_pct",
        "down_spike_freq_180d_pct",
        "best_buy_hour_utc",
        "best_buy_hour_median_fwd_1h_pct",
        "best_sell_hour_utc",
        "best_sell_hour_median_fwd_1h_pct",
        "prefilter_score",
    ]

    write_json(run_json, summary)
    write_csv(run_csv, analyzed_rows, csv_columns)
    write_text(run_md, markdown_report(summary, leaders))

    write_json(latest_json, summary)
    write_csv(latest_csv, analyzed_rows, csv_columns)
    write_text(latest_md, markdown_report(summary, leaders))

    print(f"KRAKEN_ALPHA_MAP_JSON={run_json}")
    print(f"KRAKEN_ALPHA_MAP_CSV={run_csv}")
    print(f"KRAKEN_ALPHA_MAP_MD={run_md}")
    print(
        "KRAKEN_ALPHA_MAP_COUNTS "
        f"discovered={len(pairs)} "
        f"filtered={len(filtered)} "
        f"analyzed={len(analyzed_rows)} "
        f"errors={len(errors)}"
    )

    return summary


def parse_args() -> argparse.Namespace:
    script_path = Path(__file__).resolve()
    stack_root = script_path.parents[2]

    parser = argparse.ArgumentParser(
        description="Build a Kraken multi-timeframe alpha map with deterministic artifacts."
    )
    parser.add_argument("--stack-root", default=str(stack_root))
    parser.add_argument("--out-root", default=str(stack_root / "out" / "ops"))
    parser.add_argument("--quotes", default=",".join(DEFAULT_QUOTES))
    parser.add_argument("--top-liquid", type=int, default=36)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--min-turnover-usd", type=float, default=300000.0)
    parser.add_argument("--max-spread-bps", type=float, default=45.0)
    parser.add_argument("--spike-threshold-pct", type=float, default=3.0)
    parser.add_argument("--request-pause-sec", type=float, default=0.12)
    parser.add_argument("--timeout-sec", type=float, default=16.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_alpha_map(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
