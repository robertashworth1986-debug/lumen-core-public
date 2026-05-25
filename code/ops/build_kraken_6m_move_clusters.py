from __future__ import annotations

import argparse
import csv
import json
import statistics
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
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


def pair_token(raw: Any) -> str:
    return str(raw or "").strip().upper().replace("/", "").replace("-", "")


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


def kraken_get(
    session: requests.Session,
    path: str,
    params: dict[str, Any] | None,
    timeout_sec: float,
) -> dict[str, Any]:
    response = session.get(f"{BASE_URL}/{path}", params=params, timeout=timeout_sec)
    response.raise_for_status()
    payload = response.json()
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

    rows.sort(key=lambda r: str(r.get("pair_id") or ""))
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
    open_24h = to_float(item.get("o"), 0.0)
    high_24h = to_float((item.get("h") or [0.0, 0.0])[1], 0.0)
    low_24h = to_float((item.get("l") or [0.0, 0.0])[1], 0.0)
    vol_24h = to_float((item.get("v") or [0.0, 0.0])[1], 0.0)

    change_24h_pct = 0.0
    if open_24h > 0.0:
        change_24h_pct = (last - open_24h) / open_24h * 100.0

    range_24h_pct = 0.0
    if low_24h > 0.0 and high_24h >= low_24h:
        range_24h_pct = (high_24h - low_24h) / low_24h * 100.0

    turnover_24h_usd = last * vol_24h if last > 0.0 and vol_24h > 0.0 else 0.0

    return {
        "last": last,
        "change_24h_pct": change_24h_pct,
        "range_24h_pct": range_24h_pct,
        "turnover_24h_usd": turnover_24h_usd,
    }


def load_alpha_priority_tokens(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    leaders = payload.get("alpha_leaderboard") or []
    if not isinstance(leaders, list):
        return []

    tokens: list[str] = []
    seen: set[str] = set()
    for row in leaders:
        if not isinstance(row, dict):
            continue
        for key in ("pair", "wsname", "altname"):
            token = pair_token(row.get(key))
            if token and token not in seen:
                seen.add(token)
                tokens.append(token)
    return tokens


def select_pairs(
    pairs: list[dict[str, Any]],
    tickers: dict[str, dict[str, Any]],
    alpha_tokens: list[str],
    pair_limit: int,
    min_turnover_usd: float,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    token_to_meta: dict[str, dict[str, Any]] = {}

    for row in pairs:
        pair_id = str(row.get("pair_id") or "")
        altname = str(row.get("altname") or "")
        wsname = str(row.get("wsname") or "")
        item = tickers.get(pair_id) or tickers.get(altname)
        if not isinstance(item, dict):
            continue

        metrics = ticker_metrics(item)
        if metrics["last"] <= 0.0:
            continue
        if metrics["turnover_24h_usd"] < min_turnover_usd:
            continue

        meta = {**row, **metrics}
        enriched.append(meta)

        for token in (pair_token(pair_id), pair_token(altname), pair_token(wsname)):
            if token and token not in token_to_meta:
                token_to_meta[token] = meta

    chosen: list[dict[str, Any]] = []
    seen_tokens: set[str] = set()

    for token in alpha_tokens:
        meta = token_to_meta.get(token)
        if meta is None:
            continue
        primary = pair_token(meta.get("altname") or meta.get("pair_id"))
        if primary in seen_tokens:
            continue
        chosen.append(meta)
        seen_tokens.add(primary)
        if len(chosen) >= pair_limit:
            return chosen

    remaining = sorted(
        enriched,
        key=lambda r: to_float(r.get("turnover_24h_usd"), 0.0),
        reverse=True,
    )
    for meta in remaining:
        primary = pair_token(meta.get("altname") or meta.get("pair_id"))
        if primary in seen_tokens:
            continue
        chosen.append(meta)
        seen_tokens.add(primary)
        if len(chosen) >= pair_limit:
            break

    return chosen


def fetch_ohlc_page(
    session: requests.Session,
    pair_id: str,
    interval_min: int,
    since_ts: int,
    timeout_sec: float,
) -> tuple[list[list[Any]], int]:
    payload = kraken_get(
        session,
        "OHLC",
        {"pair": pair_id, "interval": int(interval_min), "since": int(since_ts)},
        timeout_sec,
    )

    rows: list[list[Any]] = []
    for key, value in payload.items():
        if key == "last":
            continue
        if isinstance(value, list):
            rows = value
            break

    next_since = to_int(payload.get("last"), 0)
    return rows, next_since


def fetch_ohlc_paginated(
    session: requests.Session,
    pair_id: str,
    interval_min: int,
    since_ts: int,
    end_ts: int,
    timeout_sec: float,
    request_pause_sec: float,
    max_pages_per_pair: int,
) -> tuple[list[list[Any]], int]:
    by_ts: dict[int, list[Any]] = {}
    cursor = int(since_ts)
    pages = 0

    while cursor < end_ts and pages < max_pages_per_pair:
        rows, next_since = fetch_ohlc_page(
            session=session,
            pair_id=pair_id,
            interval_min=interval_min,
            since_ts=cursor,
            timeout_sec=timeout_sec,
        )
        pages += 1

        max_ts = cursor
        for row in rows:
            if not isinstance(row, list) or len(row) < 5:
                continue
            ts = to_int(row[0], 0)
            if ts <= 0:
                continue
            if ts < since_ts or ts > end_ts:
                continue
            by_ts[ts] = row
            if ts > max_ts:
                max_ts = ts

        if request_pause_sec > 0:
            time.sleep(request_pause_sec)

        step = max(60, interval_min * 60)
        proposed = max(next_since, max_ts + step)
        if proposed <= cursor:
            break
        cursor = proposed

    ordered = [row for _ts, row in sorted(by_ts.items(), key=lambda kv: kv[0])]
    return ordered, pages


def mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    try:
        return float(statistics.pstdev(values))
    except Exception:
        return 0.0


def coverage_days(rows: list[list[Any]]) -> float:
    if len(rows) < 2:
        return 0.0
    first_ts = to_int(rows[0][0], 0)
    last_ts = to_int(rows[-1][0], 0)
    if first_ts <= 0 or last_ts <= first_ts:
        return 0.0
    return round((last_ts - first_ts) / 86400.0, 6)


def win_rate(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(1 for x in values if x > 0.0) / len(values) * 100.0)


def burst_rate(values: list[float], spike_threshold_pct: float) -> float:
    if not values:
        return 0.0
    return float(sum(1 for x in values if abs(x) >= spike_threshold_pct) / len(values) * 100.0)


def cluster_bucket_score(values: list[float], spike_threshold_pct: float) -> float:
    if not values:
        return 0.0
    wr = win_rate(values)
    med = float(statistics.median(values)) if values else 0.0
    abs_move = mean([abs(v) for v in values])
    br = burst_rate(values, spike_threshold_pct)
    return (
        max(0.0, wr - 50.0) * 0.22
        + med * 3.8
        + abs_move * 2.4
        + br * 0.42
    )


def weekday_name(idx: int) -> str:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if 0 <= idx < len(names):
        return names[idx]
    return str(idx)


def markdown_report(
    summary: dict[str, Any],
    top_pairs: list[dict[str, Any]],
    top_windows: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# Kraken 6M Movement Clusters")
    lines.append("")
    lines.append(f"Generated UTC: {summary.get('generated_utc')}")
    lines.append(f"Scope: {summary.get('scope')}")
    lines.append("")
    lines.append("## Coverage")
    lines.append(f"- Pairs discovered: {summary.get('pairs_discovered', 0)}")
    lines.append(f"- Pairs selected: {summary.get('pairs_selected', 0)}")
    lines.append(f"- Pairs analyzed: {summary.get('pairs_analyzed', 0)}")
    lines.append(f"- Pair-level errors: {summary.get('pair_errors', 0)}")
    lines.append("")
    lines.append("## Controls")
    controls = summary.get("controls", {})
    lines.append(f"- Lookback days: {controls.get('lookback_days')}")
    lines.append(f"- Interval minutes: {controls.get('interval_min')}")
    lines.append(f"- Pair limit: {controls.get('pair_limit')}")
    lines.append(f"- Spike threshold pct: {controls.get('spike_threshold_pct')}")
    lines.append("")
    lines.append("## Top Pair Clusters")
    lines.append("| Rank | Pair | Cluster Score | Best Hour UTC | Best Weekday | Turnover 24h USD |")
    lines.append("|---:|---|---:|---:|---|---:|")
    for i, row in enumerate(top_pairs, start=1):
        lines.append(
            "| "
            + str(i)
            + " | "
            + str(row.get("pair") or "")
            + " | "
            + str(row.get("cluster_score") or 0)
            + " | "
            + str(row.get("best_hour_utc") or 0)
            + " | "
            + str(row.get("best_weekday_name") or "")
            + " | "
            + str(round(to_float(row.get("turnover_24h_usd"), 0.0), 2))
            + " |"
        )

    lines.append("")
    lines.append("## Top Time Windows (Cross-Pair)")
    lines.append("| Rank | Weekday | Hour UTC | Window Score | Samples | Mean Abs Move % | Win Rate % | Burst Rate % |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|")
    for i, row in enumerate(top_windows, start=1):
        lines.append(
            "| "
            + str(i)
            + " | "
            + str(row.get("weekday_name") or "")
            + " | "
            + str(row.get("hour_utc") or 0)
            + " | "
            + str(row.get("window_score") or 0)
            + " | "
            + str(row.get("samples") or 0)
            + " | "
            + str(row.get("mean_abs_move_pct") or 0)
            + " | "
            + str(row.get("win_rate_pct") or 0)
            + " | "
            + str(row.get("burst_rate_pct") or 0)
            + " |"
        )

    weekday_clusters = summary.get("weekday_clusters") or []
    if isinstance(weekday_clusters, list) and weekday_clusters:
        lines.append("")
        lines.append("## Top Weekday Clusters (Cross-Pair)")
        lines.append("| Rank | Weekday | Weekday Score | Samples | Mean Abs Move % | Win Rate % | Burst Rate % |")
        lines.append("|---:|---|---:|---:|---:|---:|---:|")
        for i, row in enumerate(weekday_clusters[:20], start=1):
            lines.append(
                "| "
                + str(i)
                + " | "
                + str(row.get("weekday_name") or "")
                + " | "
                + str(row.get("weekday_score") or 0)
                + " | "
                + str(row.get("samples") or 0)
                + " | "
                + str(row.get("mean_abs_move_pct") or 0)
                + " | "
                + str(row.get("win_rate_pct") or 0)
                + " | "
                + str(row.get("burst_rate_pct") or 0)
                + " |"
            )

    lines.append("")
    lines.append("## Evidence Paths")
    for key, value in (summary.get("evidence_paths") or {}).items():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines)


def build_clusters(args: argparse.Namespace) -> dict[str, Any]:
    stack_root = Path(args.stack_root).resolve()
    workspace_root = stack_root.parent
    out_root = Path(args.out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    run_stamp = now_tag()
    run_dir = out_root / f"kraken_6m_move_clusters_{run_stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    alpha_map_path = Path(args.alpha_map_json)
    if not alpha_map_path.is_absolute():
        alpha_map_path = (stack_root / alpha_map_path).resolve()

    session = requests.Session()
    session.headers.update({"User-Agent": "LumaKraken6MClusters/1.0"})

    quotes = parse_quotes(args.quotes)
    pairs = fetch_pairs(session=session, timeout_sec=args.timeout_sec, quotes=quotes)
    tickers = fetch_tickers(
        session=session,
        pairs=pairs,
        timeout_sec=args.timeout_sec,
        request_pause_sec=args.request_pause_sec,
    )
    alpha_tokens = load_alpha_priority_tokens(alpha_map_path)

    selected = select_pairs(
        pairs=pairs,
        tickers=tickers,
        alpha_tokens=alpha_tokens,
        pair_limit=max(1, int(args.pair_limit)),
        min_turnover_usd=max(0.0, float(args.min_turnover_usd)),
    )

    end_ts = int(datetime.now(timezone.utc).timestamp())
    since_ts = int((datetime.now(timezone.utc) - timedelta(days=max(7, int(args.lookback_days)))).timestamp())

    pair_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    global_windows: dict[tuple[int, int], list[float]] = defaultdict(list)
    global_weekdays: dict[int, list[float]] = defaultdict(list)
    total_pages_hourly = 0
    total_pages_weekday = 0

    for idx, meta in enumerate(selected, start=1):
        pair_id = str(meta.get("pair_id") or "")
        altname = str(meta.get("altname") or pair_id)
        wsname = str(meta.get("wsname") or altname)

        try:
            hourly_rows, hourly_pages = fetch_ohlc_paginated(
                session=session,
                pair_id=pair_id,
                interval_min=int(args.interval_min),
                since_ts=since_ts,
                end_ts=end_ts,
                timeout_sec=args.timeout_sec,
                request_pause_sec=args.request_pause_sec,
                max_pages_per_pair=max(1, int(args.max_pages_per_pair)),
            )
            weekday_rows_raw, weekday_pages = fetch_ohlc_paginated(
                session=session,
                pair_id=pair_id,
                interval_min=int(args.weekday_interval_min),
                since_ts=since_ts,
                end_ts=end_ts,
                timeout_sec=args.timeout_sec,
                request_pause_sec=args.request_pause_sec,
                max_pages_per_pair=max(1, int(args.max_pages_per_pair)),
            )
            total_pages_hourly += hourly_pages
            total_pages_weekday += weekday_pages

            if len(hourly_rows) < max(24, int(args.min_samples)):
                raise RuntimeError("insufficient_hourly_samples")
            if len(weekday_rows_raw) < max(14, int(args.min_weekday_samples)):
                raise RuntimeError("insufficient_weekday_samples")

            hourly_returns: list[float] = []
            by_hour: dict[int, list[float]] = defaultdict(list)
            by_weekday: dict[int, list[float]] = defaultdict(list)
            weekday_returns: list[float] = []

            for i in range(0, len(hourly_rows) - 1):
                cur = hourly_rows[i]
                nxt = hourly_rows[i + 1]
                if len(cur) < 5 or len(nxt) < 5:
                    continue
                ts = to_int(cur[0], 0)
                c0 = to_float(cur[4], 0.0)
                c1 = to_float(nxt[4], 0.0)
                if ts <= 0 or c0 <= 0.0:
                    continue

                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                ret = (c1 - c0) / c0 * 100.0
                hourly_returns.append(ret)
                by_hour[dt.hour].append(ret)
                global_windows[(dt.weekday(), dt.hour)].append(ret)

            for i in range(0, len(weekday_rows_raw) - 1):
                cur = weekday_rows_raw[i]
                nxt = weekday_rows_raw[i + 1]
                if len(cur) < 5 or len(nxt) < 5:
                    continue
                ts = to_int(cur[0], 0)
                c0 = to_float(cur[4], 0.0)
                c1 = to_float(nxt[4], 0.0)
                if ts <= 0 or c0 <= 0.0:
                    continue

                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                ret = (c1 - c0) / c0 * 100.0
                weekday_returns.append(ret)
                by_weekday[dt.weekday()].append(ret)
                global_weekdays[dt.weekday()].append(ret)

            if len(hourly_returns) < max(24, int(args.min_samples)):
                raise RuntimeError("insufficient_hourly_return_points")
            if len(weekday_returns) < max(14, int(args.min_weekday_samples)):
                raise RuntimeError("insufficient_weekday_return_points")

            hour_rows: list[dict[str, Any]] = []
            for hour, vals in sorted(by_hour.items()):
                if len(vals) < 20:
                    continue
                hour_rows.append(
                    {
                        "hour_utc": int(hour),
                        "samples": len(vals),
                        "win_rate_pct": round(win_rate(vals), 6),
                        "median_ret_pct": round(float(statistics.median(vals)), 6),
                        "mean_abs_move_pct": round(mean([abs(v) for v in vals]), 6),
                        "burst_rate_pct": round(burst_rate(vals, float(args.spike_threshold_pct)), 6),
                        "bucket_score": round(cluster_bucket_score(vals, float(args.spike_threshold_pct)), 6),
                    }
                )
            if not hour_rows:
                raise RuntimeError("missing_hour_rows")

            weekday_rows: list[dict[str, Any]] = []
            for weekday, vals in sorted(by_weekday.items()):
                if len(vals) < 10:
                    continue
                weekday_rows.append(
                    {
                        "weekday_utc": int(weekday),
                        "weekday_name": weekday_name(int(weekday)),
                        "samples": len(vals),
                        "win_rate_pct": round(win_rate(vals), 6),
                        "median_ret_pct": round(float(statistics.median(vals)), 6),
                        "mean_abs_move_pct": round(mean([abs(v) for v in vals]), 6),
                        "burst_rate_pct": round(burst_rate(vals, float(args.spike_threshold_pct)), 6),
                        "bucket_score": round(cluster_bucket_score(vals, float(args.spike_threshold_pct)), 6),
                    }
                )
            if not weekday_rows:
                raise RuntimeError("missing_weekday_rows")

            best_hour = max(hour_rows, key=lambda r: to_float(r.get("bucket_score"), 0.0))
            best_weekday = max(weekday_rows, key=lambda r: to_float(r.get("bucket_score"), 0.0))

            cluster_score = (
                to_float(best_hour.get("bucket_score"), 0.0) * 0.5
                + to_float(best_weekday.get("bucket_score"), 0.0) * 0.4
                + mean([abs(v) for v in hourly_returns]) * 2.8
                + mean([abs(v) for v in weekday_returns]) * 1.8
                + burst_rate(hourly_returns, float(args.spike_threshold_pct)) * 0.12
            )

            pair_rows.append(
                {
                    "pair": altname,
                    "wsname": wsname,
                    "pair_id": pair_id,
                    "quote": meta.get("quote"),
                    "turnover_24h_usd": round(to_float(meta.get("turnover_24h_usd"), 0.0), 6),
                    "change_24h_pct": round(to_float(meta.get("change_24h_pct"), 0.0), 6),
                    "range_24h_pct": round(to_float(meta.get("range_24h_pct"), 0.0), 6),
                    "lookback_days": int(args.lookback_days),
                    "samples": len(hourly_returns),
                    "hour_samples": len(hourly_returns),
                    "weekday_samples": len(weekday_returns),
                    "pages": hourly_pages + weekday_pages,
                    "hour_pages": hourly_pages,
                    "weekday_pages": weekday_pages,
                    "hour_coverage_days": coverage_days(hourly_rows),
                    "weekday_coverage_days": coverage_days(weekday_rows_raw),
                    "win_rate_pct": round(win_rate(hourly_returns), 6),
                    "mean_abs_move_pct": round(mean([abs(v) for v in hourly_returns]), 6),
                    "volatility_pct": round(stdev(hourly_returns), 6),
                    "burst_rate_pct": round(burst_rate(hourly_returns, float(args.spike_threshold_pct)), 6),
                    "weekday_win_rate_pct": round(win_rate(weekday_returns), 6),
                    "weekday_mean_abs_move_pct": round(mean([abs(v) for v in weekday_returns]), 6),
                    "weekday_volatility_pct": round(stdev(weekday_returns), 6),
                    "best_hour_utc": int(best_hour.get("hour_utc")),
                    "best_hour_score": round(to_float(best_hour.get("bucket_score"), 0.0), 6),
                    "best_hour_win_rate_pct": round(to_float(best_hour.get("win_rate_pct"), 0.0), 6),
                    "best_hour_mean_abs_move_pct": round(to_float(best_hour.get("mean_abs_move_pct"), 0.0), 6),
                    "best_weekday_utc": int(best_weekday.get("weekday_utc")),
                    "best_weekday_name": best_weekday.get("weekday_name"),
                    "best_weekday_score": round(to_float(best_weekday.get("bucket_score"), 0.0), 6),
                    "best_weekday_win_rate_pct": round(to_float(best_weekday.get("win_rate_pct"), 0.0), 6),
                    "best_weekday_mean_abs_move_pct": round(to_float(best_weekday.get("mean_abs_move_pct"), 0.0), 6),
                    "cluster_score": round(cluster_score, 6),
                }
            )

            if idx % 10 == 0:
                print(
                    f"CLUSTER_PROGRESS {idx}/{len(selected)} analyzed={len(pair_rows)} errors={len(errors)}",
                    flush=True,
                )

        except Exception as exc:
            errors.append(
                {
                    "pair": altname,
                    "wsname": wsname,
                    "error": str(exc),
                }
            )

    pair_rows.sort(key=lambda r: to_float(r.get("cluster_score"), 0.0), reverse=True)

    window_rows: list[dict[str, Any]] = []
    for (weekday, hour), vals in global_windows.items():
        if len(vals) < 40:
            continue
        ws = cluster_bucket_score(vals, float(args.spike_threshold_pct))
        window_rows.append(
            {
                "weekday_utc": int(weekday),
                "weekday_name": weekday_name(int(weekday)),
                "hour_utc": int(hour),
                "samples": len(vals),
                "win_rate_pct": round(win_rate(vals), 6),
                "mean_ret_pct": round(mean(vals), 6),
                "median_ret_pct": round(float(statistics.median(vals)), 6),
                "mean_abs_move_pct": round(mean([abs(v) for v in vals]), 6),
                "burst_rate_pct": round(burst_rate(vals, float(args.spike_threshold_pct)), 6),
                "window_score": round(ws, 6),
            }
        )

    window_rows.sort(key=lambda r: to_float(r.get("window_score"), 0.0), reverse=True)

    weekday_cluster_rows: list[dict[str, Any]] = []
    for weekday, vals in global_weekdays.items():
        if len(vals) < 120:
            continue
        score = cluster_bucket_score(vals, float(args.spike_threshold_pct))
        weekday_cluster_rows.append(
            {
                "weekday_utc": int(weekday),
                "weekday_name": weekday_name(int(weekday)),
                "samples": len(vals),
                "win_rate_pct": round(win_rate(vals), 6),
                "mean_ret_pct": round(mean(vals), 6),
                "median_ret_pct": round(float(statistics.median(vals)), 6),
                "mean_abs_move_pct": round(mean([abs(v) for v in vals]), 6),
                "burst_rate_pct": round(burst_rate(vals, float(args.spike_threshold_pct)), 6),
                "weekday_score": round(score, 6),
            }
        )

    weekday_cluster_rows.sort(key=lambda r: to_float(r.get("weekday_score"), 0.0), reverse=True)

    top_pairs = pair_rows[: max(1, min(50, int(args.top_report_n)))]
    top_windows = window_rows[: max(1, min(50, int(args.top_report_n)))]
    top_weekdays = weekday_cluster_rows[: max(1, min(50, int(args.top_report_n)))]

    summary = {
        "generated_utc": now_iso(),
        "scope": "kraken_6m_move_clusters",
        "controls": {
            "quotes": list(parse_quotes(args.quotes)),
            "lookback_days": int(args.lookback_days),
            "interval_min": int(args.interval_min),
            "weekday_interval_min": int(args.weekday_interval_min),
            "pair_limit": int(args.pair_limit),
            "min_turnover_usd": float(args.min_turnover_usd),
            "spike_threshold_pct": float(args.spike_threshold_pct),
            "min_samples": int(args.min_samples),
            "min_weekday_samples": int(args.min_weekday_samples),
            "request_pause_sec": float(args.request_pause_sec),
            "timeout_sec": float(args.timeout_sec),
            "max_pages_per_pair": int(args.max_pages_per_pair),
            "alpha_map_json": rel_path(alpha_map_path, workspace_root) if alpha_map_path.exists() else str(alpha_map_path),
        },
        "pairs_discovered": len(pairs),
        "pairs_selected": len(selected),
        "pairs_analyzed": len(pair_rows),
        "pair_errors": len(errors),
        "total_ohlc_pages": int(total_pages_hourly + total_pages_weekday),
        "total_ohlc_pages_hourly": int(total_pages_hourly),
        "total_ohlc_pages_weekday": int(total_pages_weekday),
        "pair_clusters": pair_rows,
        "time_windows": top_windows,
        "weekday_clusters": top_weekdays,
        "error_samples": errors[:100],
    }

    csv_fields = [
        "pair",
        "wsname",
        "pair_id",
        "quote",
        "cluster_score",
        "samples",
        "hour_samples",
        "weekday_samples",
        "lookback_days",
        "hour_coverage_days",
        "weekday_coverage_days",
        "turnover_24h_usd",
        "change_24h_pct",
        "range_24h_pct",
        "win_rate_pct",
        "mean_abs_move_pct",
        "volatility_pct",
        "burst_rate_pct",
        "weekday_win_rate_pct",
        "weekday_mean_abs_move_pct",
        "weekday_volatility_pct",
        "best_hour_utc",
        "best_hour_score",
        "best_hour_win_rate_pct",
        "best_hour_mean_abs_move_pct",
        "best_weekday_utc",
        "best_weekday_name",
        "best_weekday_score",
        "best_weekday_win_rate_pct",
        "best_weekday_mean_abs_move_pct",
        "pages",
        "hour_pages",
        "weekday_pages",
    ]

    windows_csv_fields = [
        "weekday_utc",
        "weekday_name",
        "hour_utc",
        "window_score",
        "samples",
        "win_rate_pct",
        "mean_ret_pct",
        "median_ret_pct",
        "mean_abs_move_pct",
        "burst_rate_pct",
    ]

    run_json = run_dir / "kraken_6m_move_clusters.json"
    run_csv = run_dir / "kraken_6m_move_clusters.csv"
    run_windows_csv = run_dir / "kraken_6m_move_clusters_windows.csv"
    run_md = run_dir / "kraken_6m_move_clusters.md"

    write_json(run_json, summary)
    write_csv(run_csv, pair_rows, csv_fields)
    write_csv(run_windows_csv, window_rows, windows_csv_fields)
    write_text(run_md, markdown_report(summary, top_pairs, top_windows))

    latest_json = out_root / "kraken_6m_move_clusters_latest.json"
    latest_csv = out_root / "kraken_6m_move_clusters_latest.csv"
    latest_windows_csv = out_root / "kraken_6m_move_clusters_windows_latest.csv"
    latest_md = out_root / "kraken_6m_move_clusters_latest.md"

    write_json(latest_json, summary)
    write_csv(latest_csv, pair_rows, csv_fields)
    write_csv(latest_windows_csv, window_rows, windows_csv_fields)
    write_text(latest_md, markdown_report(summary, top_pairs, top_windows))

    summary["evidence_paths"] = {
        "run_json": rel_path(run_json, workspace_root),
        "run_csv": rel_path(run_csv, workspace_root),
        "run_windows_csv": rel_path(run_windows_csv, workspace_root),
        "run_md": rel_path(run_md, workspace_root),
        "latest_json": rel_path(latest_json, workspace_root),
        "latest_csv": rel_path(latest_csv, workspace_root),
        "latest_windows_csv": rel_path(latest_windows_csv, workspace_root),
        "latest_md": rel_path(latest_md, workspace_root),
    }

    write_json(run_json, summary)
    write_json(latest_json, summary)

    print(f"KRAKEN_6M_CLUSTERS_JSON={run_json}", flush=True)
    print(f"KRAKEN_6M_CLUSTERS_CSV={run_csv}", flush=True)
    print(f"KRAKEN_6M_CLUSTERS_WINDOWS_CSV={run_windows_csv}", flush=True)
    print(f"KRAKEN_6M_CLUSTERS_MD={run_md}", flush=True)
    print(
        "KRAKEN_6M_CLUSTERS_COUNTS"
        + f" discovered={summary['pairs_discovered']}"
        + f" selected={summary['pairs_selected']}"
        + f" analyzed={summary['pairs_analyzed']}"
        + f" errors={summary['pair_errors']}",
        flush=True,
    )

    return summary


def parse_args() -> argparse.Namespace:
    script_path = Path(__file__).resolve()
    stack_root = script_path.parents[2]

    parser = argparse.ArgumentParser(
        description="Build 6-month Kraken mover clusters (pair + weekday/hour consistency)."
    )
    parser.add_argument("--stack-root", default=str(stack_root))
    parser.add_argument("--out-root", default=str(stack_root / "out" / "ops"))
    parser.add_argument("--alpha-map-json", default="out/ops/kraken_multi_tf_alpha_map_latest.json")
    parser.add_argument("--quotes", default=",".join(DEFAULT_QUOTES))
    parser.add_argument("--lookback-days", type=int, default=180)
    parser.add_argument("--interval-min", type=int, default=60)
    parser.add_argument("--weekday-interval-min", type=int, default=1440)
    parser.add_argument("--pair-limit", type=int, default=711)
    parser.add_argument("--top-report-n", type=int, default=20)
    parser.add_argument("--min-turnover-usd", type=float, default=0.0)
    parser.add_argument("--spike-threshold-pct", type=float, default=1.2)
    parser.add_argument("--min-samples", type=int, default=240)
    parser.add_argument("--min-weekday-samples", type=int, default=120)
    parser.add_argument("--max-pages-per-pair", type=int, default=12)
    parser.add_argument("--request-pause-sec", type=float, default=0.08)
    parser.add_argument("--timeout-sec", type=float, default=16.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_clusters(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
