from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from execution.alpaca_paper_executor import (
    ADAPTIVE_UNIVERSE_FILE,
    AlpacaPaperClient,
    load_api_keys,
    load_json,
    resolve_symbols_for_scan,
)
CONFIG = ROOT / "config"
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
PAPER_RUNTIME_FILE = CONFIG / "paper_trader_runtime.json"

AGENTS_DIR = EXEC_OUT / "alpaca_symbol_agents"
RANKED_FILE = EXEC_OUT / "alpaca_symbol_ranked.json"
SUMMARY_FILE = EXEC_OUT / "alpaca_symbol_agents_summary.json"
CURSOR_FILE = EXEC_OUT / "alpaca_symbol_agents_cursor.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_symbol(symbol: str) -> str:
    return str(symbol or "").upper().strip()


def _looks_like_equity_symbol(symbol: str) -> bool:
    # Alpaca US equity symbols are usually 1-5 uppercase letters.
    # Keep occasional longer symbols but remove obvious noise tokens.
    s = _normalize_symbol(symbol)
    if not s:
        return False
    if len(s) > 8:
        return False
    return s.replace(".", "").replace("-", "").isalnum()


def _compute_agent(snapshot: dict[str, Any], symbol: str) -> dict[str, Any]:
    minute = snapshot.get("minuteBar") or {}
    daily = snapshot.get("dailyBar") or {}
    prev = snapshot.get("prevDailyBar") or {}
    quote = snapshot.get("latestQuote") or {}
    trade = snapshot.get("latestTrade") or {}

    price = safe_float(trade.get("p") or minute.get("c") or daily.get("c"), 0.0)
    prev_close = safe_float(prev.get("c"), price)
    daily_close = safe_float(daily.get("c"), price)
    minute_open = safe_float(minute.get("o"), daily_close)
    minute_close = safe_float(minute.get("c"), daily_close)
    daily_high = safe_float(daily.get("h"), daily_close)
    daily_low = safe_float(daily.get("l"), daily_close)
    minute_vol = safe_float(minute.get("v"), 0.0)
    daily_vol = safe_float(daily.get("v"), 0.0)

    bid = safe_float(quote.get("bp"), 0.0)
    ask = safe_float(quote.get("ap"), 0.0)
    spread = max(0.0, ask - bid) if bid > 0 and ask > 0 else 0.0
    spread_pct = (spread / max(price, 1e-9)) if spread > 0 else 0.0

    day_ret = (daily_close / max(prev_close, 1e-9)) - 1.0 if prev_close > 0 else 0.0
    minute_ret = (minute_close / max(minute_open, 1e-9)) - 1.0 if minute_open > 0 else 0.0

    range_abs = max(daily_high - daily_low, 1e-9)
    range_pct = range_abs / max(prev_close, 1e-9) if prev_close > 0 else 0.0
    volume_impulse = minute_vol / max(daily_vol / 390.0, 1.0)

    peak_signal = max(0.0, day_ret, minute_ret)
    drop_signal = min(0.0, day_ret, minute_ret)

    anomaly_magnitude = (abs(day_ret) * 100.0) + (abs(minute_ret) * 180.0) + min(range_pct * 50.0, 25.0)
    anomaly_strength = min(100.0, anomaly_magnitude + min(math.log1p(max(volume_impulse, 0.0)) * 18.0, 20.0))

    confidence = 0.45
    if price > 1.0:
        confidence += 0.12
    if daily_high > 0 and daily_low > 0 and daily_close > 0:
        confidence += 0.12
    if spread_pct <= 0.004:
        confidence += 0.12
    if spread_pct <= 0.0015 and spread_pct > 0:
        confidence += 0.07
    if volume_impulse >= 0.4:
        confidence += 0.08
    if volume_impulse >= 1.0:
        confidence += 0.08
    confidence = max(0.0, min(0.99, confidence))

    trend_score = max(-100.0, min(100.0, (day_ret * 800.0) + (minute_ret * 900.0)))

    # A conservative, execution-safe score for ranking symbol agents.
    execution_score = (
        (anomaly_strength * 0.38)
        + (max(0.0, trend_score) * 0.32)
        + (confidence * 100.0 * 0.30)
    )

    anomaly_type = "none"
    if peak_signal >= 0.015 or minute_ret >= 0.005:
        anomaly_type = "upside_peak"
    elif drop_signal <= -0.015 or minute_ret <= -0.005:
        anomaly_type = "downside_drop"

    execution_ready = (
        confidence >= 0.68
        and anomaly_strength >= 22.0
        and price >= 1.0
        and spread_pct <= 0.008
    )

    return {
        "symbol": symbol,
        "generated_utc": now_utc(),
        "price": round(price, 6),
        "day_return": round(day_ret, 6),
        "minute_return": round(minute_ret, 6),
        "range_pct": round(range_pct, 6),
        "volume_impulse": round(volume_impulse, 4),
        "spread_pct": round(spread_pct, 6),
        "peak_signal": round(peak_signal, 6),
        "drop_signal": round(drop_signal, 6),
        "anomaly_type": anomaly_type,
        "anomaly_strength": round(anomaly_strength, 4),
        "trend_score": round(trend_score, 4),
        "reality_confidence": round(confidence, 4),
        "execution_score": round(execution_score, 4),
        "execution_ready": bool(execution_ready),
    }


def _fetch_tradable_assets(client: AlpacaPaperClient) -> list[str]:
    assets = client._get(
        f"{client.trading_base}/v2/assets",
        params={"status": "active", "asset_class": "us_equity"},
    )
    tradable = []
    if isinstance(assets, list):
        for row in assets:
            if not isinstance(row, dict):
                continue
            if not bool(row.get("tradable", False)):
                continue
            sym = _normalize_symbol(row.get("symbol", ""))
            if sym and _looks_like_equity_symbol(sym):
                tradable.append(sym)
    # Stable ordering for deterministic scoring cycles.
    return sorted(set(tradable))


def _fetch_snapshots_batched(client: AlpacaPaperClient, symbols: list[str], batch_size: int = 250) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    size = max(50, int(batch_size))
    for i in range(0, len(symbols), size):
        chunk = symbols[i : i + size]
        payload = client.get_snapshots(chunk)
        if isinstance(payload, dict):
            merged.update(payload)
    return merged


def _select_symbols_with_cursor(all_symbols: list[str], max_symbols: int) -> tuple[list[str], int, int]:
    if not all_symbols:
        return [], 0, 0

    total = len(all_symbols)
    target = max(10, int(max_symbols))
    if target >= total:
        # Full-universe scan; cursor reset keeps state deterministic.
        write_json(
            CURSOR_FILE,
            {
                "generated_utc": now_utc(),
                "cursor": 0,
                "last_window_size": total,
                "universe_total": total,
            },
        )
        return list(all_symbols), 0, 0

    cursor_state = load_json(CURSOR_FILE, {})
    cursor = int(cursor_state.get("cursor", 0) or 0) % total

    selected = []
    for i in range(target):
        idx = (cursor + i) % total
        selected.append(all_symbols[idx])

    next_cursor = (cursor + target) % total
    write_json(
        CURSOR_FILE,
        {
            "generated_utc": now_utc(),
            "cursor": next_cursor,
            "last_window_start": cursor,
            "last_window_size": target,
            "universe_total": total,
        },
    )
    return selected, cursor, next_cursor


def run_agents(max_symbols: int = 400) -> dict[str, Any]:
    keys = load_api_keys()
    client = AlpacaPaperClient(
        keys.get("ALPACA_API_KEY", ""),
        keys.get("ALPACA_API_SECRET", ""),
        trading_base=keys.get("ALPACA_PAPER_BASE_URL", ""),
        data_base=keys.get("ALPACA_DATA_BASE_URL", ""),
    )
    if not client.is_configured():
        raise SystemExit("Missing Alpaca API keys for symbol agents")

    paper_runtime = load_json(PAPER_RUNTIME_FILE, {})
    universe_mode = str(paper_runtime.get("agent_universe_source", "alpaca_assets")).lower().strip()

    tradable_assets = _fetch_tradable_assets(client)
    tradable_set = set(tradable_assets)

    if universe_mode == "paper_runtime":
        symbols_all, symbols_source, universe_total = resolve_symbols_for_scan(client, paper_runtime)
        symbols_all = [_normalize_symbol(s) for s in symbols_all if _looks_like_equity_symbol(s)]
        symbols_all = [s for s in symbols_all if s in tradable_set]
    else:
        symbols_all = list(tradable_assets)
        symbols_source = "alpaca_tradable_assets"
        universe_total = len(symbols_all)

    symbols, window_start, window_next = _select_symbols_with_cursor(symbols_all, max_symbols=max_symbols)

    snapshots = _fetch_snapshots_batched(client, symbols, batch_size=250)

    agents = []
    for symbol in symbols:
        snap = snapshots.get(symbol) or {}
        agent = _compute_agent(snap, symbol)
        agents.append(agent)

    agents.sort(
        key=lambda a: (
            bool(a.get("execution_ready", False)),
            float(a.get("execution_score", 0.0)),
            float(a.get("anomaly_strength", 0.0)),
        ),
        reverse=True,
    )

    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    for agent in agents:
        write_json(AGENTS_DIR / f"{agent['symbol']}.json", agent)

    ranked_payload = {
        "generated_utc": now_utc(),
        "source": symbols_source,
        "universe_total": int(universe_total),
        "scanned_symbols": len(symbols),
        "scan_window_start": int(window_start),
        "scan_window_next": int(window_next),
        "execution_ready_count": sum(1 for a in agents if a.get("execution_ready")),
        "top_agents": agents[:200],
    }
    write_json(RANKED_FILE, ranked_payload)

    summary = {
        "generated_utc": now_utc(),
        "ranked_file": str(RANKED_FILE),
        "agents_dir": str(AGENTS_DIR),
        "source": symbols_source,
        "universe_total": int(universe_total),
        "scanned_symbols": len(symbols),
        "scan_window_start": int(window_start),
        "scan_window_next": int(window_next),
        "cursor_file": str(CURSOR_FILE),
        "execution_ready_count": sum(1 for a in agents if a.get("execution_ready")),
        "top5": agents[:5],
    }
    write_json(SUMMARY_FILE, summary)
    return summary


_LOCK_FILE = ROOT / "run" / "alpaca_symbol_agents.lock"


def _acquire_singleton_lock() -> None:
    """Prevent duplicate instances. Exits 0 immediately if this script is already running."""
    import atexit
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _LOCK_FILE.exists():
        try:
            pid = int(_LOCK_FILE.read_text().strip())
            if pid != os.getpid():
                os.kill(pid, 0)  # raises OSError if process is gone
                print(f"[singleton] alpaca_symbol_agents already running as PID {pid} — exiting.", flush=True)
                raise SystemExit(0)
        except (ValueError, OSError):
            pass  # stale lock
    _LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: _LOCK_FILE.unlink(missing_ok=True))


def main() -> int:
    _acquire_singleton_lock()
    parser = argparse.ArgumentParser(description="Per-symbol anomaly/score agents for Alpaca paper flow")
    parser.add_argument("--max-symbols", type=int, default=400, help="Max symbols to evaluate per cycle")
    args = parser.parse_args()

    summary = run_agents(max_symbols=args.max_symbols)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
