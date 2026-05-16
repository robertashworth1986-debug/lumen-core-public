from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_EXEC = ROOT / "out" / "execution"
RUNTIME_CONTROL_FILE = ROOT / "config" / "runtime_control.json"
LEDGER_JSONL_FILE = OUT_EXEC / "live_trade_ledger.jsonl"
HEARTBEAT_FILE = OUT_EXEC / "live_executor_heartbeat.json"

OUTPUT_JSON = OUT_EXEC / "symbol_flip_analysis_3d.json"
OUTPUT_MD = OUT_EXEC / "symbol_flip_analysis_3d.md"
OUTPUT_INTEL_JSON = OUT_EXEC / "symbol_flip_intel_top5.json"
OUTPUT_LEARNING_JSON = OUT_EXEC / "symbol_flip_learning_profile.json"

KRAKEN_BASE = "https://api.kraken.com"

STABLE_SYMBOLS = {
    "USD",
    "USDT",
    "USDC",
    "DAI",
    "USDE",
    "USD1",
    "USAT",
    "RLUSD",
    "PYUSD",
    "FDUSD",
    "TUSD",
    "USDS",
}


@dataclass
class OHLCBar:
    ts: int
    open: float
    high: float
    low: float
    close: float


@dataclass
class WindowMetrics:
    bars: int
    first_price: float
    last_price: float
    net_change_pct: float
    low_price: float
    low_ts: int
    high_price: float
    high_ts: int
    range_pct: float
    best_long_flip_pct: float
    best_long_buy_ts: int
    best_long_sell_ts: int
    best_short_flip_pct: float
    best_short_sell_ts: int
    best_short_buy_ts: int
    mean_abs_bar_move_pct: float
    cumulative_abs_move_pct: float
    best_long_hold_minutes: float
    best_short_hold_minutes: float
    avg_bar_spread_pct: float
    max_bar_spread_pct: float
    up_state_minutes: float
    down_state_minutes: float
    flat_state_minutes: float
    up_state_max_streak_minutes: float
    down_state_max_streak_minutes: float
    flat_state_max_streak_minutes: float
    state_transition_count: int
    dominant_state: str
    est_peak_long_profit_usd_per_100: float
    est_peak_short_profit_usd_per_100: float


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def normalize_symbol(raw: Any) -> str:
    token = str(raw or "").upper().strip()
    if not token:
        return ""
    if "/" in token:
        token = token.split("/", 1)[0].strip()
    token = token.replace("-", "").replace("_", "")
    if token.endswith("USD") and len(token) > 3:
        token = token[:-3]
    if token.endswith("USDT") and len(token) > 4:
        token = token[:-4]
    alias = {
        "XBT": "BTC",
        "XXBT": "BTC",
        "XXRP": "XRP",
        "XXDG": "DOGE",
        "XDG": "DOGE",
        "XETH": "ETH",
        "ZUSD": "USD",
    }
    return alias.get(token, token)


def _parse_ledger_symbols(max_rows: int) -> list[str]:
    if not LEDGER_JSONL_FILE.exists():
        return []
    try:
        lines = LEDGER_JSONL_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []

    freq: Counter[str] = Counter()
    for raw in lines[-max_rows:]:
        text = raw.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except Exception:
            continue
        symbol = normalize_symbol(row.get("symbol", ""))
        if not symbol or symbol == "USD":
            continue
        freq[symbol] += 1

    ranked = [symbol for symbol, _ in freq.most_common(80)]
    return ranked


def _runtime_extra_symbols() -> list[str]:
    runtime = load_json(RUNTIME_CONTROL_FILE, {})
    if not isinstance(runtime, dict):
        return []

    out: list[str] = []
    for key in ("symbol_universe_extra", "symbols", "symbol_whitelist"):
        raw = runtime.get(key, [])
        if isinstance(raw, str):
            raw = [s.strip() for s in raw.split(",") if str(s).strip()]
        if isinstance(raw, list):
            for item in raw:
                symbol = normalize_symbol(item)
                if symbol and symbol != "USD":
                    out.append(symbol)
    return out


def _heartbeat_symbol() -> str:
    hb = load_json(HEARTBEAT_FILE, {})
    if not isinstance(hb, dict):
        return ""
    return normalize_symbol(hb.get("selected_symbol") or hb.get("symbol") or "")


def _fetch_asset_pairs_map() -> dict[str, str]:
    try:
        r = requests.get(KRAKEN_BASE + "/0/public/AssetPairs", timeout=15)
        r.raise_for_status()
        payload = r.json()
        if payload.get("error"):
            return {}
        rows = payload.get("result", {})
        if not isinstance(rows, dict):
            return {}

        out: dict[str, str] = {}
        for _, row in rows.items():
            if not isinstance(row, dict):
                continue
            altname = str(row.get("altname", "") or "").upper().strip()
            wsname = str(row.get("wsname", "") or "").upper().strip()
            if not altname or "/" not in wsname:
                continue
            base, quote = wsname.split("/", 1)
            base = normalize_symbol(base)
            quote = normalize_symbol(quote)
            if quote != "USD":
                continue
            if not base:
                continue
            out[base] = altname
            if base == "BTC":
                out["XBT"] = altname
        return out
    except Exception:
        return {}


def _fetch_ohlc_bars(pair: str, since_ts: int, interval: int) -> list[OHLCBar]:
    try:
        r = requests.get(
            KRAKEN_BASE + "/0/public/OHLC",
            params={"pair": pair, "interval": int(interval), "since": int(since_ts)},
            timeout=15,
        )
        r.raise_for_status()
        payload = r.json()
        if payload.get("error"):
            return []
        result = payload.get("result", {})
        if not isinstance(result, dict):
            return []

        key = ""
        for maybe_key in result.keys():
            if str(maybe_key).lower() == "last":
                continue
            key = str(maybe_key)
            break
        if not key:
            return []

        rows = result.get(key, [])
        if not isinstance(rows, list):
            return []

        out: list[OHLCBar] = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 5:
                continue
            try:
                ts = int(float(row[0]))
                open_px = float(row[1])
                high_px = float(row[2])
                low_px = float(row[3])
                close_px = float(row[4])
            except Exception:
                continue
            if (
                ts <= 0
                or min(open_px, high_px, low_px, close_px) <= 0
                or (not math.isfinite(open_px))
                or (not math.isfinite(high_px))
                or (not math.isfinite(low_px))
                or (not math.isfinite(close_px))
            ):
                continue
            high_px = max(high_px, low_px)
            out.append(
                OHLCBar(
                    ts=int(ts),
                    open=float(open_px),
                    high=float(high_px),
                    low=float(low_px),
                    close=float(close_px),
                )
            )

        out.sort(key=lambda item: item.ts)
        return out
    except Exception:
        return []


def _state_from_move_pct(move_pct: float, threshold_pct: float) -> str:
    if float(move_pct) > float(threshold_pct):
        return "up"
    if float(move_pct) < -float(threshold_pct):
        return "down"
    return "flat"


def _window_metrics(
    bars: list[OHLCBar],
    now_ts: int,
    window_sec: int,
    state_move_threshold_pct: float,
    assumed_entry_usd: float,
) -> WindowMetrics | None:
    cutoff = int(now_ts - window_sec)
    rows = [row for row in bars if int(row.ts) >= cutoff and float(row.close) > 0.0]
    if len(rows) < 4:
        return None

    first_bar = rows[0]
    last_bar = rows[-1]
    first_px = float(first_bar.close)
    last_px = float(last_bar.close)

    low_bar = min(rows, key=lambda item: float(item.low))
    high_bar = max(rows, key=lambda item: float(item.high))
    low_ts = int(low_bar.ts)
    low_px = float(low_bar.low)
    high_ts = int(high_bar.ts)
    high_px = float(high_bar.high)

    net_change_pct = ((last_px / max(first_px, 1e-9)) - 1.0) * 100.0
    range_pct = ((high_px / max(low_px, 1e-9)) - 1.0) * 100.0

    min_px_so_far = float("inf")
    min_ts_so_far = 0
    best_long_flip_pct = 0.0
    best_long_buy_ts = 0
    best_long_sell_ts = 0

    max_px_so_far = 0.0
    max_ts_so_far = 0
    best_short_flip_pct = 0.0
    best_short_sell_ts = 0
    best_short_buy_ts = 0

    for row in rows:
        ts = int(row.ts)
        px = float(row.close)
        if px < min_px_so_far:
            min_px_so_far = px
            min_ts_so_far = ts
        long_flip_pct = ((px / max(min_px_so_far, 1e-9)) - 1.0) * 100.0
        if long_flip_pct > best_long_flip_pct and ts > min_ts_so_far:
            best_long_flip_pct = long_flip_pct
            best_long_buy_ts = min_ts_so_far
            best_long_sell_ts = ts

        if px > max_px_so_far:
            max_px_so_far = px
            max_ts_so_far = ts
        short_flip_pct = ((max_px_so_far / max(px, 1e-9)) - 1.0) * 100.0
        if short_flip_pct > best_short_flip_pct and ts > max_ts_so_far:
            best_short_flip_pct = short_flip_pct
            best_short_sell_ts = max_ts_so_far
            best_short_buy_ts = ts

    abs_moves: list[float] = []
    prev_px = float(rows[0].close)
    for row in rows[1:]:
        px = float(row.close)
        abs_moves.append(abs((px / max(prev_px, 1e-9)) - 1.0) * 100.0)
        prev_px = px

    mean_abs_bar_move_pct = sum(abs_moves) / max(len(abs_moves), 1)
    cumulative_abs_move_pct = sum(abs_moves)

    bar_spreads_pct: list[float] = []
    for row in rows:
        spread_pct = ((float(row.high) - float(row.low)) / max(float(row.close), 1e-9)) * 100.0
        if math.isfinite(spread_pct) and spread_pct >= 0.0:
            bar_spreads_pct.append(float(spread_pct))

    avg_bar_spread_pct = (sum(bar_spreads_pct) / float(len(bar_spreads_pct))) if bar_spreads_pct else 0.0
    max_bar_spread_pct = max(bar_spreads_pct) if bar_spreads_pct else 0.0

    best_long_hold_minutes = 0.0
    if best_long_buy_ts > 0 and best_long_sell_ts > best_long_buy_ts:
        best_long_hold_minutes = max((best_long_sell_ts - best_long_buy_ts) / 60.0, 0.0)

    best_short_hold_minutes = 0.0
    if best_short_sell_ts > 0 and best_short_buy_ts > best_short_sell_ts:
        best_short_hold_minutes = max((best_short_buy_ts - best_short_sell_ts) / 60.0, 0.0)

    state_totals_sec = {"up": 0.0, "down": 0.0, "flat": 0.0}
    state_max_streak_sec = {"up": 0.0, "down": 0.0, "flat": 0.0}
    state_transition_count = 0

    prev_close = float(rows[0].close)
    prev_ts = int(rows[0].ts)
    prev_state = ""
    current_streak_sec = 0.0
    threshold = max(float(state_move_threshold_pct), 0.0)

    for row in rows[1:]:
        current_close = float(row.close)
        current_ts = int(row.ts)
        dt_sec = max(float(current_ts - prev_ts), 60.0)
        move_pct = ((current_close / max(prev_close, 1e-9)) - 1.0) * 100.0
        state = _state_from_move_pct(float(move_pct), threshold)

        state_totals_sec[state] = float(state_totals_sec[state]) + float(dt_sec)

        if not prev_state:
            prev_state = state
            current_streak_sec = float(dt_sec)
        elif state == prev_state:
            current_streak_sec += float(dt_sec)
        else:
            state_max_streak_sec[prev_state] = max(float(state_max_streak_sec[prev_state]), float(current_streak_sec))
            prev_state = state
            current_streak_sec = float(dt_sec)
            state_transition_count += 1

        prev_close = current_close
        prev_ts = current_ts

    if prev_state:
        state_max_streak_sec[prev_state] = max(float(state_max_streak_sec[prev_state]), float(current_streak_sec))

    dominant_state = max(state_totals_sec.items(), key=lambda item: float(item[1]))[0]

    up_state_minutes = float(state_totals_sec["up"]) / 60.0
    down_state_minutes = float(state_totals_sec["down"]) / 60.0
    flat_state_minutes = float(state_totals_sec["flat"]) / 60.0
    up_state_max_streak_minutes = float(state_max_streak_sec["up"]) / 60.0
    down_state_max_streak_minutes = float(state_max_streak_sec["down"]) / 60.0
    flat_state_max_streak_minutes = float(state_max_streak_sec["flat"]) / 60.0

    entry_usd = max(float(assumed_entry_usd), 0.0)
    est_peak_long_profit_usd_per_100 = entry_usd * (float(best_long_flip_pct) / 100.0)
    est_peak_short_profit_usd_per_100 = entry_usd * (float(best_short_flip_pct) / 100.0)

    return WindowMetrics(
        bars=len(rows),
        first_price=float(first_px),
        last_price=float(last_px),
        net_change_pct=float(net_change_pct),
        low_price=float(low_px),
        low_ts=int(low_ts),
        high_price=float(high_px),
        high_ts=int(high_ts),
        range_pct=float(range_pct),
        best_long_flip_pct=float(best_long_flip_pct),
        best_long_buy_ts=int(best_long_buy_ts),
        best_long_sell_ts=int(best_long_sell_ts),
        best_short_flip_pct=float(best_short_flip_pct),
        best_short_sell_ts=int(best_short_sell_ts),
        best_short_buy_ts=int(best_short_buy_ts),
        mean_abs_bar_move_pct=float(mean_abs_bar_move_pct),
        cumulative_abs_move_pct=float(cumulative_abs_move_pct),
        best_long_hold_minutes=float(best_long_hold_minutes),
        best_short_hold_minutes=float(best_short_hold_minutes),
        avg_bar_spread_pct=float(avg_bar_spread_pct),
        max_bar_spread_pct=float(max_bar_spread_pct),
        up_state_minutes=float(up_state_minutes),
        down_state_minutes=float(down_state_minutes),
        flat_state_minutes=float(flat_state_minutes),
        up_state_max_streak_minutes=float(up_state_max_streak_minutes),
        down_state_max_streak_minutes=float(down_state_max_streak_minutes),
        flat_state_max_streak_minutes=float(flat_state_max_streak_minutes),
        state_transition_count=int(state_transition_count),
        dominant_state=str(dominant_state),
        est_peak_long_profit_usd_per_100=float(est_peak_long_profit_usd_per_100),
        est_peak_short_profit_usd_per_100=float(est_peak_short_profit_usd_per_100),
    )


def _iso_from_ts(ts: int) -> str:
    if int(ts or 0) <= 0:
        return ""
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()


def _window_to_dict(metrics: WindowMetrics) -> dict[str, Any]:
    return {
        "bars": int(metrics.bars),
        "first_price": round(float(metrics.first_price), 8),
        "last_price": round(float(metrics.last_price), 8),
        "net_change_pct": round(float(metrics.net_change_pct), 6),
        "low_price": round(float(metrics.low_price), 8),
        "low_ts": int(metrics.low_ts),
        "low_utc": _iso_from_ts(int(metrics.low_ts)),
        "high_price": round(float(metrics.high_price), 8),
        "high_ts": int(metrics.high_ts),
        "high_utc": _iso_from_ts(int(metrics.high_ts)),
        "range_pct": round(float(metrics.range_pct), 6),
        "best_long_flip_pct": round(float(metrics.best_long_flip_pct), 6),
        "best_long_buy_ts": int(metrics.best_long_buy_ts),
        "best_long_buy_utc": _iso_from_ts(int(metrics.best_long_buy_ts)),
        "best_long_sell_ts": int(metrics.best_long_sell_ts),
        "best_long_sell_utc": _iso_from_ts(int(metrics.best_long_sell_ts)),
        "best_short_flip_pct": round(float(metrics.best_short_flip_pct), 6),
        "best_short_sell_ts": int(metrics.best_short_sell_ts),
        "best_short_sell_utc": _iso_from_ts(int(metrics.best_short_sell_ts)),
        "best_short_buy_ts": int(metrics.best_short_buy_ts),
        "best_short_buy_utc": _iso_from_ts(int(metrics.best_short_buy_ts)),
        "mean_abs_bar_move_pct": round(float(metrics.mean_abs_bar_move_pct), 6),
        "cumulative_abs_move_pct": round(float(metrics.cumulative_abs_move_pct), 6),
        "best_long_hold_minutes": round(float(metrics.best_long_hold_minutes), 6),
        "best_short_hold_minutes": round(float(metrics.best_short_hold_minutes), 6),
        "avg_bar_spread_pct": round(float(metrics.avg_bar_spread_pct), 6),
        "max_bar_spread_pct": round(float(metrics.max_bar_spread_pct), 6),
        "up_state_minutes": round(float(metrics.up_state_minutes), 6),
        "down_state_minutes": round(float(metrics.down_state_minutes), 6),
        "flat_state_minutes": round(float(metrics.flat_state_minutes), 6),
        "up_state_max_streak_minutes": round(float(metrics.up_state_max_streak_minutes), 6),
        "down_state_max_streak_minutes": round(float(metrics.down_state_max_streak_minutes), 6),
        "flat_state_max_streak_minutes": round(float(metrics.flat_state_max_streak_minutes), 6),
        "state_transition_count": int(metrics.state_transition_count),
        "dominant_state": str(metrics.dominant_state),
        "est_peak_long_profit_usd_per_100": round(float(metrics.est_peak_long_profit_usd_per_100), 6),
        "est_peak_short_profit_usd_per_100": round(float(metrics.est_peak_short_profit_usd_per_100), 6),
    }


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _is_stable_symbol(symbol: str) -> bool:
    return str(symbol or "").upper().strip() in STABLE_SYMBOLS


def _score_long_alpha(row: dict[str, Any]) -> float:
    w24 = row.get("w24h", {}) if isinstance(row, dict) else {}
    w72 = row.get("w72h", {}) if isinstance(row, dict) else {}

    long24 = _safe_float((w24 or {}).get("best_long_flip_pct", 0.0), 0.0)
    long72 = _safe_float((w72 or {}).get("best_long_flip_pct", 0.0), 0.0)
    range72 = _safe_float((w72 or {}).get("range_pct", 0.0), 0.0)
    net72 = _safe_float((w72 or {}).get("net_change_pct", 0.0), 0.0)
    mean_abs72 = _safe_float((w72 or {}).get("mean_abs_bar_move_pct", 0.0), 0.0)
    avg_spread72 = _safe_float((w72 or {}).get("avg_bar_spread_pct", 0.0), 0.0)
    up_state_minutes = _safe_float((w72 or {}).get("up_state_minutes", 0.0), 0.0)

    trend_bonus = max(net72, 0.0) * 0.20
    persistence_bonus = min((up_state_minutes / 60.0) * 0.60, 6.0)
    spread_penalty = min(max(avg_spread72, 0.0) * 0.35, 12.0)
    return (
        (0.42 * long24)
        + (0.58 * long72)
        + (0.22 * range72)
        + (0.15 * mean_abs72)
        + trend_bonus
        + persistence_bonus
        - spread_penalty
    )


def _score_short_alpha(row: dict[str, Any]) -> float:
    w24 = row.get("w24h", {}) if isinstance(row, dict) else {}
    w72 = row.get("w72h", {}) if isinstance(row, dict) else {}

    short24 = _safe_float((w24 or {}).get("best_short_flip_pct", 0.0), 0.0)
    short72 = _safe_float((w72 or {}).get("best_short_flip_pct", 0.0), 0.0)
    range72 = _safe_float((w72 or {}).get("range_pct", 0.0), 0.0)
    net72 = _safe_float((w72 or {}).get("net_change_pct", 0.0), 0.0)
    avg_spread72 = _safe_float((w72 or {}).get("avg_bar_spread_pct", 0.0), 0.0)
    down_state_minutes = _safe_float((w72 or {}).get("down_state_minutes", 0.0), 0.0)
    downside_bonus = max(-net72, 0.0) * 0.25
    persistence_bonus = min((down_state_minutes / 60.0) * 0.60, 6.0)
    spread_penalty = min(max(avg_spread72, 0.0) * 0.35, 12.0)

    return (0.45 * short24) + (0.55 * short72) + (0.20 * range72) + downside_bonus + persistence_bonus - spread_penalty


def _score_learning_long(row: dict[str, Any]) -> float:
    w72 = row.get("w72h", {}) if isinstance(row, dict) else {}
    long72 = _safe_float((w72 or {}).get("best_long_flip_pct", 0.0), 0.0)
    long24 = _safe_float((row.get("w24h", {}) or {}).get("best_long_flip_pct", 0.0), 0.0)
    profit_hint = _safe_float((w72 or {}).get("est_peak_long_profit_usd_per_100", 0.0), 0.0)
    avg_spread72 = max(_safe_float((w72 or {}).get("avg_bar_spread_pct", 0.0), 0.0), 0.01)
    up_streak_minutes = _safe_float((w72 or {}).get("up_state_max_streak_minutes", 0.0), 0.0)
    efficiency = max(long72, 0.0) / max(avg_spread72, 0.01)
    return (0.58 * long72) + (0.20 * long24) + (0.16 * efficiency) + (0.08 * (up_streak_minutes / 60.0)) + (0.06 * profit_hint)


def _score_learning_short(row: dict[str, Any]) -> float:
    w72 = row.get("w72h", {}) if isinstance(row, dict) else {}
    short72 = _safe_float((w72 or {}).get("best_short_flip_pct", 0.0), 0.0)
    short24 = _safe_float((row.get("w24h", {}) or {}).get("best_short_flip_pct", 0.0), 0.0)
    profit_hint = _safe_float((w72 or {}).get("est_peak_short_profit_usd_per_100", 0.0), 0.0)
    avg_spread72 = max(_safe_float((w72 or {}).get("avg_bar_spread_pct", 0.0), 0.0), 0.01)
    down_streak_minutes = _safe_float((w72 or {}).get("down_state_max_streak_minutes", 0.0), 0.0)
    efficiency = max(short72, 0.0) / max(avg_spread72, 0.01)
    return (0.58 * short72) + (0.20 * short24) + (0.16 * efficiency) + (0.08 * (down_streak_minutes / 60.0)) + (0.06 * profit_hint)


def _build_intel_payload(
    payload: dict[str, Any],
    top_n: int,
    min_long_flip_pct: float,
    min_range_pct: float,
) -> dict[str, Any]:
    rows = payload.get("symbols", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []

    long_pool: list[dict[str, Any]] = []
    short_pool: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue

        symbol = str(row.get("symbol", "") or "").upper().strip()
        if not symbol:
            continue

        w24 = row.get("w24h", {}) if isinstance(row.get("w24h", {}), dict) else {}
        w72 = row.get("w72h", {}) if isinstance(row.get("w72h", {}), dict) else {}

        best_long_24 = _safe_float(w24.get("best_long_flip_pct", 0.0), 0.0)
        best_long_72 = _safe_float(w72.get("best_long_flip_pct", 0.0), 0.0)
        best_short_24 = _safe_float(w24.get("best_short_flip_pct", 0.0), 0.0)
        best_short_72 = _safe_float(w72.get("best_short_flip_pct", 0.0), 0.0)
        range_72 = _safe_float(w72.get("range_pct", 0.0), 0.0)
        net_72 = _safe_float(w72.get("net_change_pct", 0.0), 0.0)

        long_score = _score_long_alpha(row)
        short_score = _score_short_alpha(row)
        learned_long_score = _score_learning_long(row)
        learned_short_score = _score_learning_short(row)

        base = {
            "symbol": symbol,
            "pair": str(row.get("pair", "") or ""),
            "range_72h_pct": round(range_72, 6),
            "net_72h_pct": round(net_72, 6),
            "best_long_flip_24h_pct": round(best_long_24, 6),
            "best_long_flip_72h_pct": round(best_long_72, 6),
            "best_short_flip_24h_pct": round(best_short_24, 6),
            "best_short_flip_72h_pct": round(best_short_72, 6),
            "alpha_long_score": round(long_score, 6),
            "alpha_short_score": round(short_score, 6),
            "learned_long_score": round(float(learned_long_score), 6),
            "learned_short_score": round(float(learned_short_score), 6),
            "avg_bar_spread_72h_pct": round(_safe_float(w72.get("avg_bar_spread_pct", 0.0), 0.0), 6),
            "max_bar_spread_72h_pct": round(_safe_float(w72.get("max_bar_spread_pct", 0.0), 0.0), 6),
            "up_state_minutes_72h": round(_safe_float(w72.get("up_state_minutes", 0.0), 0.0), 6),
            "down_state_minutes_72h": round(_safe_float(w72.get("down_state_minutes", 0.0), 0.0), 6),
            "flat_state_minutes_72h": round(_safe_float(w72.get("flat_state_minutes", 0.0), 0.0), 6),
            "dominant_state_72h": str(w72.get("dominant_state", "flat") or "flat"),
            "peak_long_profit_usd_per_100": round(_safe_float(w72.get("est_peak_long_profit_usd_per_100", 0.0), 0.0), 6),
            "peak_short_profit_usd_per_100": round(_safe_float(w72.get("est_peak_short_profit_usd_per_100", 0.0), 0.0), 6),
        }

        if (best_long_24 >= min_long_flip_pct or best_long_72 >= min_long_flip_pct) and range_72 >= min_range_pct:
            long_pool.append(dict(base))

        if (best_short_24 >= min_long_flip_pct or best_short_72 >= min_long_flip_pct) and range_72 >= min_range_pct:
            short_pool.append(dict(base))

    long_ranked = sorted(
        long_pool,
        key=lambda row: _safe_float(row.get("learned_long_score", row.get("alpha_long_score", 0.0)), 0.0),
        reverse=True,
    )
    short_ranked = sorted(
        short_pool,
        key=lambda row: _safe_float(row.get("learned_short_score", row.get("alpha_short_score", 0.0)), 0.0),
        reverse=True,
    )

    top_long = long_ranked[: max(int(top_n), 1)]
    top_short = short_ranked[: max(int(top_n), 1)]

    focus_symbols: list[str] = []
    for row in top_long + top_short:
        symbol = str(row.get("symbol", "") or "").upper().strip()
        if symbol and symbol not in focus_symbols:
            focus_symbols.append(symbol)

    return {
        "generated_utc": now_utc(),
        "schema": "symbol_flip_intel_top5_v2",
        "source_schema": str(payload.get("schema", "")),
        "source_generated_utc": str(payload.get("generated_utc", "")),
        "top_n": max(int(top_n), 1),
        "min_long_flip_pct": round(float(min_long_flip_pct), 6),
        "min_range_pct": round(float(min_range_pct), 6),
        "long_candidates": top_long,
        "short_candidates": top_short,
        "focus_symbols": focus_symbols,
    }


def _build_learning_payload(payload: dict[str, Any], max_profiles: int) -> dict[str, Any]:
    rows = payload.get("symbols", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []

    profiles: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol", "") or "").upper().strip()
        if not symbol:
            continue
        w72 = row.get("w72h", {}) if isinstance(row.get("w72h", {}), dict) else {}

        learned_long = _safe_float(row.get("learned_long_score", _score_learning_long(row)), 0.0)
        learned_short = _safe_float(row.get("learned_short_score", _score_learning_short(row)), 0.0)
        dominant_bias = "long" if learned_long >= learned_short else "short"
        dominant_score = max(learned_long, learned_short)

        profile = {
            "symbol": symbol,
            "pair": str(row.get("pair", "") or ""),
            "dominant_bias": dominant_bias,
            "dominant_score": round(float(dominant_score), 6),
            "learned_long_score": round(float(learned_long), 6),
            "learned_short_score": round(float(learned_short), 6),
            "alpha_long_score": round(_safe_float(row.get("alpha_long_score", 0.0), 0.0), 6),
            "alpha_short_score": round(_safe_float(row.get("alpha_short_score", 0.0), 0.0), 6),
            "best_long_flip_72h_pct": round(_safe_float(w72.get("best_long_flip_pct", 0.0), 0.0), 6),
            "best_short_flip_72h_pct": round(_safe_float(w72.get("best_short_flip_pct", 0.0), 0.0), 6),
            "range_72h_pct": round(_safe_float(w72.get("range_pct", 0.0), 0.0), 6),
            "avg_bar_spread_72h_pct": round(_safe_float(w72.get("avg_bar_spread_pct", 0.0), 0.0), 6),
            "max_bar_spread_72h_pct": round(_safe_float(w72.get("max_bar_spread_pct", 0.0), 0.0), 6),
            "up_state_minutes_72h": round(_safe_float(w72.get("up_state_minutes", 0.0), 0.0), 6),
            "down_state_minutes_72h": round(_safe_float(w72.get("down_state_minutes", 0.0), 0.0), 6),
            "flat_state_minutes_72h": round(_safe_float(w72.get("flat_state_minutes", 0.0), 0.0), 6),
            "dominant_state_72h": str(w72.get("dominant_state", "flat") or "flat"),
            "state_transition_count_72h": int(_safe_float(w72.get("state_transition_count", 0), 0.0)),
            "peak_long_profit_usd_per_100": round(_safe_float(w72.get("est_peak_long_profit_usd_per_100", 0.0), 0.0), 6),
            "peak_short_profit_usd_per_100": round(_safe_float(w72.get("est_peak_short_profit_usd_per_100", 0.0), 0.0), 6),
            "best_long_hold_minutes_72h": round(_safe_float(w72.get("best_long_hold_minutes", 0.0), 0.0), 6),
            "best_short_hold_minutes_72h": round(_safe_float(w72.get("best_short_hold_minutes", 0.0), 0.0), 6),
        }
        profiles.append(profile)

    profiles.sort(key=lambda row: _safe_float(row.get("dominant_score", 0.0), 0.0), reverse=True)
    limited = profiles[: max(int(max_profiles), 1)]

    top_peak_long = sorted(
        limited,
        key=lambda row: _safe_float(row.get("peak_long_profit_usd_per_100", 0.0), 0.0),
        reverse=True,
    )[:15]
    top_peak_short = sorted(
        limited,
        key=lambda row: _safe_float(row.get("peak_short_profit_usd_per_100", 0.0), 0.0),
        reverse=True,
    )[:15]
    top_spread = sorted(
        limited,
        key=lambda row: _safe_float(row.get("max_bar_spread_72h_pct", 0.0), 0.0),
        reverse=True,
    )[:15]

    return {
        "generated_utc": now_utc(),
        "schema": "symbol_flip_learning_profile_v1",
        "source_schema": str(payload.get("schema", "")),
        "source_generated_utc": str(payload.get("generated_utc", "")),
        "profile_count": int(len(limited)),
        "symbol_profiles": limited,
        "top_peak_long_profit": top_peak_long,
        "top_peak_short_profit": top_peak_short,
        "top_max_spread": top_spread,
    }


def _build_markdown(payload: dict[str, Any]) -> str:
    rows = payload.get("symbols", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []

    top_long_24 = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda r: float(((r.get("w24h", {}) or {}).get("best_long_flip_pct", 0.0) or 0.0)),
        reverse=True,
    )[:15]
    top_long_72 = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda r: float(((r.get("w72h", {}) or {}).get("best_long_flip_pct", 0.0) or 0.0)),
        reverse=True,
    )[:15]
    top_short_24 = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda r: float(((r.get("w24h", {}) or {}).get("best_short_flip_pct", 0.0) or 0.0)),
        reverse=True,
    )[:15]
    top_short_72 = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda r: float(((r.get("w72h", {}) or {}).get("best_short_flip_pct", 0.0) or 0.0)),
        reverse=True,
    )[:15]
    top_range_72 = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda r: float(((r.get("w72h", {}) or {}).get("range_pct", 0.0) or 0.0)),
        reverse=True,
    )[:15]
    top_state_persistence = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda r: max(
            float(((r.get("w72h", {}) or {}).get("up_state_max_streak_minutes", 0.0) or 0.0)),
            float(((r.get("w72h", {}) or {}).get("down_state_max_streak_minutes", 0.0) or 0.0)),
            float(((r.get("w72h", {}) or {}).get("flat_state_max_streak_minutes", 0.0) or 0.0)),
        ),
        reverse=True,
    )[:15]

    lines: list[str] = []
    lines.append("# Kraken Symbol Flip Analysis (24h / 72h)")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Symbols analyzed: {payload.get('symbol_count', 0)}")
    lines.append(f"Stablecoin symbols excluded: {bool(payload.get('exclude_stablecoins', True))}")
    lines.append(f"Action filter min_long_flip_pct: {payload.get('action_min_long_flip_pct', 0)}")
    lines.append(f"Action filter min_range_pct: {payload.get('action_min_range_pct', 0)}")
    lines.append("")

    lines.append("## Top Long Flips (24h)")
    for row in top_long_24:
        w = row.get("w24h", {}) if isinstance(row, dict) else {}
        lines.append(
            f"- {row.get('symbol', '')}: best_long_flip={w.get('best_long_flip_pct', 0):.3f}% range={w.get('range_pct', 0):.3f}% net={w.get('net_change_pct', 0):.3f}%"
        )
    lines.append("")

    lines.append("## Top Long Flips (72h)")
    for row in top_long_72:
        w = row.get("w72h", {}) if isinstance(row, dict) else {}
        lines.append(
            f"- {row.get('symbol', '')}: best_long_flip={w.get('best_long_flip_pct', 0):.3f}% range={w.get('range_pct', 0):.3f}% net={w.get('net_change_pct', 0):.3f}%"
        )
    lines.append("")

    lines.append("## Top Short Flips (24h)")
    for row in top_short_24:
        w = row.get("w24h", {}) if isinstance(row, dict) else {}
        lines.append(
            f"- {row.get('symbol', '')}: best_short_flip={w.get('best_short_flip_pct', 0):.3f}% range={w.get('range_pct', 0):.3f}% net={w.get('net_change_pct', 0):.3f}%"
        )
    lines.append("")

    lines.append("## Top Short Flips (72h)")
    for row in top_short_72:
        w = row.get("w72h", {}) if isinstance(row, dict) else {}
        lines.append(
            f"- {row.get('symbol', '')}: best_short_flip={w.get('best_short_flip_pct', 0):.3f}% range={w.get('range_pct', 0):.3f}% net={w.get('net_change_pct', 0):.3f}%"
        )
    lines.append("")

    lines.append("## Highest Up-Down Range (72h)")
    for row in top_range_72:
        w = row.get("w72h", {}) if isinstance(row, dict) else {}
        lines.append(
            f"- {row.get('symbol', '')}: range={w.get('range_pct', 0):.3f}% long_flip={w.get('best_long_flip_pct', 0):.3f}% short_flip={w.get('best_short_flip_pct', 0):.3f}%"
        )

    lines.append("")
    lines.append("## Longest State Persistence (72h)")
    for row in top_state_persistence:
        w = row.get("w72h", {}) if isinstance(row, dict) else {}
        lines.append(
            f"- {row.get('symbol', '')}: dominant={w.get('dominant_state', 'flat')} up={w.get('up_state_minutes', 0):.1f}m down={w.get('down_state_minutes', 0):.1f}m flat={w.get('flat_state_minutes', 0):.1f}m"
        )

    intel = payload.get("intel", {}) if isinstance(payload.get("intel", {}), dict) else {}
    learning = payload.get("learning", {}) if isinstance(payload.get("learning", {}), dict) else {}
    lines.append("")
    lines.append("## Actionable Long Candidates")
    for row in intel.get("long_candidates", [])[:10] if isinstance(intel.get("long_candidates", []), list) else []:
        lines.append(
            f"- {row.get('symbol', '')}: alpha_long_score={row.get('alpha_long_score', 0):.3f} long24={row.get('best_long_flip_24h_pct', 0):.3f}% long72={row.get('best_long_flip_72h_pct', 0):.3f}% range72={row.get('range_72h_pct', 0):.3f}%"
        )

    lines.append("")
    lines.append("## Actionable Short Candidates")
    for row in intel.get("short_candidates", [])[:10] if isinstance(intel.get("short_candidates", []), list) else []:
        lines.append(
            f"- {row.get('symbol', '')}: alpha_short_score={row.get('alpha_short_score', 0):.3f} short24={row.get('best_short_flip_24h_pct', 0):.3f}% short72={row.get('best_short_flip_72h_pct', 0):.3f}% range72={row.get('range_72h_pct', 0):.3f}%"
        )

    lines.append("")
    lines.append("## Top Peak Profit Candidates (Per $100 Entry)")
    for row in learning.get("top_peak_long_profit", [])[:10] if isinstance(learning.get("top_peak_long_profit", []), list) else []:
        lines.append(
            f"- {row.get('symbol', '')} [long]: peak_profit_usd={row.get('peak_long_profit_usd_per_100', 0):.3f} long72={row.get('best_long_flip_72h_pct', 0):.3f}%"
        )
    for row in learning.get("top_peak_short_profit", [])[:10] if isinstance(learning.get("top_peak_short_profit", []), list) else []:
        lines.append(
            f"- {row.get('symbol', '')} [short]: peak_profit_usd={row.get('peak_short_profit_usd_per_100', 0):.3f} short72={row.get('best_short_flip_72h_pct', 0):.3f}%"
        )

    lines.append("")
    lines.append("## Largest Bar Spread Symbols (72h)")
    for row in learning.get("top_max_spread", [])[:10] if isinstance(learning.get("top_max_spread", []), list) else []:
        lines.append(
            f"- {row.get('symbol', '')}: max_bar_spread_72h_pct={row.get('max_bar_spread_72h_pct', 0):.3f} avg_bar_spread_72h_pct={row.get('avg_bar_spread_72h_pct', 0):.3f}"
        )

    return "\n".join(lines).strip() + "\n"


def analyze(
    interval_minutes: int,
    ledger_tail: int,
    exclude_stablecoins: bool,
    action_min_long_flip_pct: float,
    action_min_range_pct: float,
    action_top_n: int,
    scan_all_usd_pairs: bool,
    max_symbols: int,
    state_move_threshold_pct: float,
    assumed_entry_usd: float,
) -> dict[str, Any]:
    now_ts = int(time.time())
    since_ts = int(now_ts - (3 * 24 * 3600) - (2 * 3600))
    pairs = _fetch_asset_pairs_map()

    raw_symbols: list[str] = []
    raw_symbols.extend(_parse_ledger_symbols(max_rows=max(ledger_tail, 50)))
    raw_symbols.extend(_runtime_extra_symbols())

    if bool(scan_all_usd_pairs):
        raw_symbols.extend(list(pairs.keys()))

    hb_symbol = _heartbeat_symbol()
    if hb_symbol:
        raw_symbols.append(hb_symbol)

    symbols = [normalize_symbol(s) for s in raw_symbols]
    symbols = [s for s in symbols if s and s != "USD"]
    symbols = list(dict.fromkeys(symbols))
    if int(max_symbols) > 0:
        symbols = symbols[: int(max_symbols)]

    analyzed_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for symbol in symbols:
        if exclude_stablecoins and _is_stable_symbol(symbol):
            skipped.append({"symbol": symbol, "reason": "stable_symbol_excluded"})
            continue

        pair = str(pairs.get(symbol, "") or "").upper().strip()
        if not pair:
            skipped.append({"symbol": symbol, "reason": "pair_not_found"})
            continue

        bars = _fetch_ohlc_bars(pair=pair, since_ts=since_ts, interval=max(int(interval_minutes), 1))
        if len(bars) < 10:
            skipped.append({"symbol": symbol, "pair": pair, "reason": "insufficient_ohlc"})
            continue

        m24 = _window_metrics(
            bars,
            now_ts=now_ts,
            window_sec=24 * 3600,
            state_move_threshold_pct=float(state_move_threshold_pct),
            assumed_entry_usd=float(assumed_entry_usd),
        )
        m72 = _window_metrics(
            bars,
            now_ts=now_ts,
            window_sec=72 * 3600,
            state_move_threshold_pct=float(state_move_threshold_pct),
            assumed_entry_usd=float(assumed_entry_usd),
        )
        if m24 is None or m72 is None:
            skipped.append({"symbol": symbol, "pair": pair, "reason": "missing_window_metrics"})
            continue

        w24 = _window_to_dict(m24)
        w72 = _window_to_dict(m72)
        scored = {
            "symbol": symbol,
            "pair": pair,
            "w24h": w24,
            "w72h": w72,
        }
        scored["alpha_long_score"] = round(_score_long_alpha(scored), 6)
        scored["alpha_short_score"] = round(_score_short_alpha(scored), 6)
        analyzed_rows.append(scored)

    analyzed_rows.sort(
        key=lambda r: _safe_float(r.get("alpha_long_score", 0.0), 0.0),
        reverse=True,
    )

    intel_payload = _build_intel_payload(
        {
            "schema": "kraken_symbol_flip_analysis_v1",
            "generated_utc": now_utc(),
            "symbols": analyzed_rows,
        },
        top_n=max(int(action_top_n), 1),
        min_long_flip_pct=max(float(action_min_long_flip_pct), 0.0),
        min_range_pct=max(float(action_min_range_pct), 0.0),
    )

    learning_payload = _build_learning_payload(
        {
            "schema": "kraken_symbol_flip_analysis_v1",
            "generated_utc": now_utc(),
            "symbols": analyzed_rows,
        },
        max_profiles=(int(max_symbols) if int(max_symbols) > 0 else max(len(analyzed_rows), 1)),
    )

    payload = {
        "generated_utc": now_utc(),
        "schema": "kraken_symbol_flip_analysis_v2",
        "interval_minutes": int(interval_minutes),
        "lookback_hours": 72,
        "scan_all_usd_pairs": bool(scan_all_usd_pairs),
        "max_symbols": int(max_symbols),
        "state_move_threshold_pct": round(float(state_move_threshold_pct), 6),
        "assumed_entry_usd": round(float(assumed_entry_usd), 6),
        "scan_symbol_count": int(len(symbols)),
        "available_usd_pair_count": int(len(pairs)),
        "exclude_stablecoins": bool(exclude_stablecoins),
        "action_min_long_flip_pct": round(float(action_min_long_flip_pct), 6),
        "action_min_range_pct": round(float(action_min_range_pct), 6),
        "action_top_n": int(max(action_top_n, 1)),
        "symbol_count": len(analyzed_rows),
        "symbols": analyzed_rows,
        "intel": intel_payload,
        "learning": learning_payload,
        "skipped": skipped,
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze 24h/72h Kraken symbol swing opportunities from live-traded symbols.")
    parser.add_argument("--interval-minutes", type=int, default=5, help="Kraken OHLC interval in minutes.")
    parser.add_argument("--ledger-tail", type=int, default=2500, help="How many recent ledger rows to inspect for symbol universe.")
    parser.add_argument("--scan-all-usd-pairs", action="store_true", help="Include all Kraken USD pairs in scan universe.")
    parser.add_argument("--max-symbols", type=int, default=220, help="Maximum symbols to scan after universe assembly (0 = no cap).")
    parser.add_argument("--exclude-stablecoins", action="store_true", default=True, help="Exclude stable/pegged symbols from flip ranking.")
    parser.add_argument("--include-stablecoins", action="store_true", help="Include stable/pegged symbols in output.")
    parser.add_argument("--action-min-long-flip-pct", type=float, default=2.5, help="Minimum long flip threshold for actionable list.")
    parser.add_argument("--action-min-range-pct", type=float, default=3.5, help="Minimum 72h range threshold for actionable list.")
    parser.add_argument("--action-top-n", type=int, default=5, help="How many candidates to keep per side in intel feed.")
    parser.add_argument("--state-move-threshold-pct", type=float, default=0.12, help="Bar move threshold for up/down/flat state classification.")
    parser.add_argument("--assumed-entry-usd", type=float, default=100.0, help="Assumed entry capital for peak profit projection.")
    args = parser.parse_args()

    exclude_stablecoins = bool(args.exclude_stablecoins)
    if args.include_stablecoins:
        exclude_stablecoins = False

    payload = analyze(
        interval_minutes=max(args.interval_minutes, 1),
        ledger_tail=max(args.ledger_tail, 50),
        exclude_stablecoins=exclude_stablecoins,
        action_min_long_flip_pct=max(float(args.action_min_long_flip_pct), 0.0),
        action_min_range_pct=max(float(args.action_min_range_pct), 0.0),
        action_top_n=max(int(args.action_top_n), 1),
        scan_all_usd_pairs=bool(args.scan_all_usd_pairs),
        max_symbols=int(args.max_symbols),
        state_move_threshold_pct=max(float(args.state_move_threshold_pct), 0.0),
        assumed_entry_usd=max(float(args.assumed_entry_usd), 0.0),
    )

    intel_payload = payload.get("intel", {}) if isinstance(payload.get("intel", {}), dict) else {}
    learning_payload = payload.get("learning", {}) if isinstance(payload.get("learning", {}), dict) else {}

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(payload), encoding="utf-8")
    OUTPUT_INTEL_JSON.write_text(json.dumps(intel_payload, indent=2), encoding="utf-8")
    OUTPUT_LEARNING_JSON.write_text(json.dumps(learning_payload, indent=2), encoding="utf-8")

    print(str(OUTPUT_JSON.as_posix()))
    print(str(OUTPUT_MD.as_posix()))
    print(str(OUTPUT_INTEL_JSON.as_posix()))
    print(str(OUTPUT_LEARNING_JSON.as_posix()))


if __name__ == "__main__":
    main()
