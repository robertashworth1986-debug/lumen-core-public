"""
benchmark_beater.py — LumaTrader Phase-Locked Flowform vs. Benchmark Engine
============================================================================
The highest-level question answered in one file:

    "Are our phase-locked flowform champions BEATING the benchmark RIGHT NOW?
     Prove it, live, with a clock, on every refresh."

What this does every 60 seconds:
  1. Fetches live OHLC price data for benchmark instruments (SPY, QQQ, BTC-USD, ETH-USD)
     via yfinance (free, no key required).
  2. Runs the Fibonacci Bubble Lattice Harmonic (FBLH) engine on each series.
  3. Simulates our champion signal vs. buy-and-hold benchmark over
     7d / 30d / 90d / 365d windows.
  4. Computes: benchmark_return, strategy_return, alpha_edge, beat_pct, win/loss.
  5. Writes a JSON snapshot to out/execution/benchmark_beater.json — live clock included.
  6. Loops forever (--loop) for live dashboard feed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
OUT_FILE = ROOT / "out" / "execution" / "benchmark_beater.json"

# Auto-load env keys
_ENV_FILE = ROOT / "config" / "luma_live_keys.env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ─── Optional yfinance ────────────────────────────────────────────────────────
try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

# ─── Inlined FBLH engine (no circular import) ─────────────────────────────────

FIB_RATIOS = [0.0, 0.236, 0.382, 0.500, 0.618, 0.786, 1.000, 1.272, 1.618, 2.618]
HARMONIC_PERIODS = [8, 13, 21, 34, 55, 89]


def _mean(v: List[float]) -> float:
    return sum(v) / len(v) if v else 0.0


def _std(v: List[float]) -> float:
    if len(v) < 2:
        return 0.0
    m = _mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def _sma(prices: List[float], w: int) -> List[float]:
    out = [float("nan")] * len(prices)
    for i in range(w - 1, len(prices)):
        out[i] = _mean(prices[i - w + 1 : i + 1])
    return out


def _rsi(prices: List[float], w: int = 14) -> float:
    if len(prices) < w + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = _mean(gains[-w:])
    al = _mean(losses[-w:])
    if al == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + ag / al)


def _fib_prox(prices: List[float], lb: int = 55) -> float:
    if len(prices) < lb:
        return 0.5
    w = prices[-lb:]
    hi, lo = max(w), min(w)
    rng = hi - lo
    if rng == 0:
        return 0.0
    p = prices[-1]
    return min(abs(p - lo + r * rng - p) for r in FIB_RATIOS) / rng  # type: ignore[return-value]


def _bubble_z(prices: List[float], w: int = 50) -> float:
    if len(prices) < w:
        return 0.0
    window = prices[-w:]
    m, s = _mean(window), _std(window)
    return (prices[-1] - m) / s if s > 0 else 0.0


def _harmonic(prices: List[float]) -> Tuple[float, float]:
    i = len(prices) - 1
    vals = [math.sin((2 * math.pi * i) / p) for p in HARMONIC_PERIODS]
    phase = _mean(vals)
    coh = 1.0 - _std(vals) / (max(abs(v) for v in vals) + 1e-8)
    return phase, max(0.0, min(1.0, coh))


def fblh_alpha(prices: List[float]) -> Dict[str, float]:
    """Compute FBLH composite alpha from price series. Returns dict of signal components."""
    if len(prices) < 90:
        return {"composite": 0.0, "confidence": 0.0, "regime": "INSUFFICIENT_DATA"}

    sma20 = _sma(prices, 20)[-1]
    sma50 = _sma(prices, 50)[-1]
    sma20 = prices[-1] if math.isnan(sma20) else sma20
    sma50 = prices[-1] if math.isnan(sma50) else sma50

    rsi = _rsi(prices, 14)
    fib = _fib_prox(prices, 55)
    bz = _bubble_z(prices, 50)
    h_phase, h_coh = _harmonic(prices)
    lattice = abs((sma20 - sma50) / (sma50 + 1e-8))

    c_fib = 1.0 - min(fib * 2, 1.0)
    c_rsi = (50.0 - rsi) / 50.0
    c_harmonic = h_phase
    c_bubble = -bz / 3.0
    c_trend = (sma20 - sma50) / (sma50 + 1e-8) * 10.0

    composite = max(-1.0, min(1.0,
        0.20 * c_fib + 0.20 * c_rsi + 0.25 * c_harmonic + 0.15 * c_bubble + 0.20 * c_trend
    ))

    fib_score = 1.0 - min(fib, 1.0)
    rsi_extreme = abs(rsi - 50) / 50.0
    confidence = max(0.0, min(1.0, h_coh * fib_score * (0.5 + 0.5 * rsi_extreme)))

    if abs(bz) > 2.5:
        regime = "BUBBLE"
    elif lattice > 0.03 and sma20 > sma50:
        regime = "TREND_UP"
    elif lattice > 0.03 and sma20 < sma50:
        regime = "TREND_DOWN"
    elif abs(bz) < 0.5 and lattice < 0.01:
        regime = "COMPRESSION"
    else:
        regime = "MEAN_REVERT"

    if composite > 0.35 and confidence > 0.4:
        entry = "LONG"
    elif composite < -0.35 and confidence > 0.4:
        entry = "SHORT"
    elif abs(composite) > 0.15:
        entry = "WATCH"
    else:
        entry = "FLAT"

    return {
        "composite": round(composite, 4),
        "confidence": round(confidence, 4),
        "regime": regime,
        "entry": entry,
        "fib_proximity": round(fib, 4),
        "bubble_z": round(bz, 4),
        "harmonic_phase": round(h_phase, 4),
        "harmonic_coherence": round(h_coh, 4),
        "rsi": round(rsi, 2),
        "sma20": round(sma20, 4),
        "sma50": round(sma50, 4),
    }


# ─── Strategy simulation ──────────────────────────────────────────────────────

def simulate_vs_benchmark(prices: List[float], lookback_days: int) -> Dict[str, Any]:
    """
    Given a price series (daily closes), simulate:
    - Benchmark: buy-and-hold from lookback_days ago to now
    - FBLH strategy: signal-driven long/flat/short
    Returns performance metrics and % edge.
    """
    n = min(lookback_days + 1, len(prices))
    window = prices[-n:]
    if len(window) < 5:
        return {"ok": False, "reason": "insufficient_data"}

    # --- Benchmark (buy and hold) ---
    bh_return = (window[-1] - window[0]) / (window[0] + 1e-8)

    # --- FBLH strategy simulation ---
    strat_returns = []
    position = 0.0  # +1 long, -1 short, 0 flat
    trade_count = 0
    wins = 0

    for i in range(90, len(window)):
        sig = fblh_alpha(window[:i])
        new_pos = {"LONG": 1.0, "SHORT": -1.0, "WATCH": 0.5, "FLAT": 0.0}.get(sig["entry"], 0.0)
        bar_ret = (window[i] - window[i - 1]) / (window[i - 1] + 1e-8)
        pnl = position * bar_ret
        strat_returns.append(pnl)
        if new_pos != position and position != 0.0:
            trade_count += 1
            if pnl > 0:
                wins += 1
        position = new_pos

    if not strat_returns:
        return {"ok": False, "reason": "no_bars_simulated"}

    # Compound strategy return
    strat_equity = 1.0
    for r in strat_returns:
        strat_equity *= (1 + r)
    strat_return = strat_equity - 1.0

    alpha_edge = strat_return - bh_return
    beat_pct = alpha_edge * 100.0
    sharpe = (_mean(strat_returns) / _std(strat_returns) * math.sqrt(252)) if _std(strat_returns) > 0 else 0.0

    peak = 1.0
    max_dd = 0.0
    eq = 1.0
    for r in strat_returns:
        eq *= (1 + r)
        peak = max(peak, eq)
        dd = (peak - eq) / peak
        max_dd = max(max_dd, dd)

    win_rate = wins / trade_count if trade_count > 0 else 0.0

    return {
        "ok": True,
        "lookback_days": lookback_days,
        "benchmark_return_pct": round(bh_return * 100, 3),
        "strategy_return_pct": round(strat_return * 100, 3),
        "alpha_edge_pct": round(beat_pct, 3),
        "beating_benchmark": bool(strat_return > bh_return),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 3),
        "trade_count": int(trade_count),
        "win_rate_pct": round(win_rate * 100, 1),
        "bars_simulated": len(strat_returns),
    }


# ─── Data fetching ────────────────────────────────────────────────────────────

BENCHMARKS = [
    {"symbol": "SPY",     "name": "S&P 500 ETF",        "class": "equity"},
    {"symbol": "QQQ",     "name": "Nasdaq 100 ETF",      "class": "equity"},
    {"symbol": "BTC-USD", "name": "Bitcoin",             "class": "crypto"},
    {"symbol": "ETH-USD", "name": "Ethereum",            "class": "crypto"},
    {"symbol": "GLD",     "name": "Gold ETF",            "class": "commodities"},
    {"symbol": "TLT",     "name": "20yr Treasury ETF",   "class": "fixed_income"},
]

WINDOWS = [7, 30, 90, 365]

_PRICE_CACHE: Dict[str, Any] = {}
_PRICE_CACHE_TS: Dict[str, float] = {}
_CACHE_TTL = 300  # 5 minutes


def fetch_prices(symbol: str, days: int = 400) -> List[float]:
    """Fetch daily close prices via yfinance. Caches for 5 minutes."""
    if not HAS_YF:
        return []
    now_ts = time.time()
    cache_key = f"{symbol}_{days}"
    if cache_key in _PRICE_CACHE and now_ts - _PRICE_CACHE_TS.get(cache_key, 0) < _CACHE_TTL:
        return _PRICE_CACHE[cache_key]

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=f"{days}d", interval="1d", auto_adjust=True)
        if hist.empty:
            return []
        prices = [float(v) for v in hist["Close"].dropna().tolist()]
        _PRICE_CACHE[cache_key] = prices
        _PRICE_CACHE_TS[cache_key] = now_ts
        return prices
    except Exception:
        return []


def fallback_synthetic_prices(symbol: str, days: int = 400) -> List[float]:
    """
    Fallback synthetic price series when yfinance is unavailable.
    Uses deterministic seeded random walk so results are reproducible but still
    exercises the FBLH engine.
    """
    import random as _r
    seed = sum(ord(c) for c in symbol) + days
    rng = _r.Random(seed)
    price = 100.0
    prices = [price]
    for _ in range(days - 1):
        drift = 0.0003
        vol = 0.015
        price *= (1 + drift + vol * (rng.gauss(0, 1)))
        prices.append(max(0.01, price))
    return prices


# ─── Main snapshot builder ─────────────────────────────────────────────────────

def build_snapshot() -> Dict[str, Any]:
    generated = datetime.now(timezone.utc)
    results = []
    summary_beats = 0
    summary_total = 0

    for bench in BENCHMARKS:
        symbol = bench["symbol"]
        prices = fetch_prices(symbol, days=400)
        source = "yfinance_live"
        if len(prices) < 100:
            prices = fallback_synthetic_prices(symbol, days=400)
            source = "synthetic_fallback"

        # Current FBLH signal on full series
        current_sig = fblh_alpha(prices)
        latest_price = prices[-1] if prices else 0.0

        windows_out = {}
        for w in WINDOWS:
            perf = simulate_vs_benchmark(prices, lookback_days=w)
            windows_out[f"{w}d"] = perf
            if perf.get("ok") and perf.get("beating_benchmark"):
                summary_beats += 1
            if perf.get("ok"):
                summary_total += 1

        results.append({
            "symbol": symbol,
            "name": bench["name"],
            "asset_class": bench["class"],
            "data_source": source,
            "latest_price": round(latest_price, 4),
            "bars_available": len(prices),
            "current_signal": current_sig,
            "performance_vs_benchmark": windows_out,
        })

    beat_rate_pct = round(summary_beats / summary_total * 100, 1) if summary_total > 0 else 0.0
    overall_verdict = "BEATING" if beat_rate_pct >= 50 else "TRAILING"

    return {
        "generated_utc": generated.isoformat(),
        "schema": "benchmark_beater_v1",
        "clock": {
            "unix_ts": int(generated.timestamp()),
            "human": generated.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "day_of_year": generated.timetuple().tm_yday,
        },
        "headline": {
            "overall_verdict": overall_verdict,
            "beat_rate_pct": beat_rate_pct,
            "windows_beating": int(summary_beats),
            "windows_total": int(summary_total),
            "yfinance_available": HAS_YF,
        },
        "benchmarks": results,
    }


def atomic_write(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def run_once() -> Dict[str, Any]:
    snap = build_snapshot()
    atomic_write(OUT_FILE, snap)
    return snap


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Phase-locked flowform vs benchmark engine")
    p.add_argument("--loop", action="store_true", help="Run continuously")
    p.add_argument("--interval", type=int, default=60, help="Refresh interval seconds")
    p.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = p.parse_args(argv)

    def _run():
        snap = run_once()
        h = snap["headline"]
        if not args.quiet:
            verdict = h["overall_verdict"]
            beat = h["beat_rate_pct"]
            ts = snap["clock"]["human"]
            print(json.dumps({
                "ts": ts,
                "verdict": verdict,
                "beat_rate_pct": beat,
                "windows_beating": h["windows_beating"],
                "windows_total": h["windows_total"],
                "yf_live": h["yfinance_available"],
            }, indent=2))
        return snap

    if args.loop:
        while True:
            try:
                _run()
            except Exception as exc:
                print(f"[benchmark_beater] error: {exc}", file=sys.stderr)
            time.sleep(args.interval)
    else:
        _run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
