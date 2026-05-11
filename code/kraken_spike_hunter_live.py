#!/usr/bin/env python3
"""
LUMA SPIKE HUNTER — LIVE KRAKEN SCANNER
Scans ALL Kraken USD/USDT pairs, pulls 7-day hourly OHLCV,
scores every pair for momentum, dip-from-high, volume surge, and RSI.
Returns a ranked leaderboard of highest-conviction trade setups.
"""

import json, time, sys, math
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import requests

ROOT    = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_DIR = ROOT / "out" / "spike_hunter"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE  = "https://api.kraken.com/0/public"
SESS  = requests.Session()
SESS.headers.update({"User-Agent": "LumaSpikeHunter/3.0"})


# ─────────────────────────────────────────────
# 1. UNIVERSE: all USD/USDT pairs
# ─────────────────────────────────────────────
def fetch_pairs() -> list[dict]:
    """Return all active Kraken spot pairs vs USD or USDT."""
    r = SESS.get(f"{BASE}/AssetPairs", timeout=15)
    raw = r.json().get("result", {})
    pairs = []
    for alt_name, meta in raw.items():
        if meta.get("status") != "online":
            continue
        quote = meta.get("quote", "")
        if quote not in ("ZUSD", "USDT"):
            continue
        wsname = meta.get("wsname", alt_name)
        pairs.append({
            "pair_id":   alt_name,
            "wsname":    wsname,
            "base":      meta.get("base", ""),
            "quote":     quote,
            "altname":   meta.get("altname", alt_name),
            "cost_decimals": meta.get("cost_decimals", 2),
        })
    return pairs


# ─────────────────────────────────────────────
# 2. OHLCV  — 1h candles × 168 (7 days)
# ─────────────────────────────────────────────
def fetch_ohlcv(pair_id: str) -> list[list]:
    """
    Returns list of candles: [time, open, high, low, close, vwap, volume, count]
    Up to 720 candles (30 days) at 1-hour interval.
    """
    since = int(time.time()) - 7 * 24 * 3600
    try:
        r = SESS.get(f"{BASE}/OHLC",
                     params={"pair": pair_id, "interval": 60, "since": since},
                     timeout=12)
        result = r.json().get("result", {})
        for key, val in result.items():
            if key != "last" and isinstance(val, list):
                return val
    except Exception as e:
        pass
    return []


# ─────────────────────────────────────────────
# 3. TICKER SNAPSHOT  — live bid/ask/24h
# ─────────────────────────────────────────────
def fetch_ticker_batch(pair_ids: list[str]) -> dict:
    """Batch ticker fetch — Kraken accepts comma-separated pairs."""
    chunk_size = 20
    result = {}
    for i in range(0, len(pair_ids), chunk_size):
        chunk = pair_ids[i:i+chunk_size]
        try:
            r = SESS.get(f"{BASE}/Ticker",
                         params={"pair": ",".join(chunk)},
                         timeout=12)
            result.update(r.json().get("result", {}))
        except Exception:
            pass
        time.sleep(0.3)
    return result


# ─────────────────────────────────────────────
# 4. TECHNICAL INDICATORS
# ─────────────────────────────────────────────
def _rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[-period + i] - closes[-period + i - 1]
        (gains if delta > 0 else losses).append(abs(delta))
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss <= 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    k = 2 / (period + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


def _atr(candles: list[list], period: int = 14) -> float:
    """Average True Range from OHLCV candles."""
    trs = []
    for i in range(1, min(len(candles), period + 1)):
        high = float(candles[i][2])
        low  = float(candles[i][3])
        prev_close = float(candles[i-1][4])
        trs.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return sum(trs) / len(trs) if trs else 0.0


def _vol_surge(candles: list[list]) -> float:
    """Latest 3 candles avg volume / 7-day avg volume — >2.0 = surge."""
    vols = [float(c[6]) for c in candles]
    if len(vols) < 10:
        return 1.0
    baseline = sum(vols[:-3]) / max(len(vols) - 3, 1)
    recent   = sum(vols[-3:]) / 3
    return round(recent / baseline if baseline > 0 else 1.0, 3)


def _momentum_scores(closes: list[float]) -> dict:
    """Returns % change over 1h, 4h, 24h windows."""
    def pct(n):
        if len(closes) <= n:
            return 0.0
        old = closes[-n - 1]
        return round((closes[-1] - old) / old * 100, 3) if old else 0.0
    return {"m1h": pct(1), "m4h": pct(4), "m24h": pct(24)}


def _dip_from_high(closes: list[float], highs: list[float]) -> float:
    """How far is current price below 7-day high? Positive = dip."""
    h = max(highs) if highs else 0
    c = closes[-1] if closes else 0
    return round((h - c) / h * 100, 2) if h else 0.0


def _breakout_proximity(closes: list[float], highs: list[float]) -> float:
    """How close is current price to 7-day high? 100 = AT the high."""
    h = max(highs) if highs else 0
    c = closes[-1] if closes else 0
    return round(c / h * 100, 2) if h else 0.0


# ─────────────────────────────────────────────
# 5. OPPORTUNITY SCORER
# ─────────────────────────────────────────────
SIGNAL_WEIGHTS = {
    # Reversal hunters: deep dip + RSI oversold + vol surge
    "DEEP_DIP":          dict(rsi_max=38, dip_min=15, vol_surge_min=1.5, label="DEEP DIP REVERSAL"),
    # Momentum breakouts: at/near high, vol surge, strong m4h
    "BREAKOUT":          dict(breakout_pct_min=95, vol_surge_min=2.0, m4h_min=2.0, label="BREAKOUT SURGE"),
    # Accumulation: moderate dip, RSI neutral, vol building
    "ACCUMULATION":      dict(dip_min=8, dip_max=20, rsi_range=(40,55), label="ACCUMULATION SETUP"),
    # Extreme oversold — RSI < 25, high dip
    "EXTREME_OVERSOLD":  dict(rsi_max=25, dip_min=25, label="EXTREME OVERSOLD"),
}


def score_pair(p: dict) -> dict:
    """Compute a composite score 0–100 for each pair."""
    rsi         = p["rsi"]
    dip         = p["dip_from_high_pct"]
    vol         = p["vol_surge"]
    m4h         = p["m4h"]
    m24h        = p["m24h"]
    breakout    = p["breakout_pct"]
    atr_rel     = p["atr_rel_pct"]   # ATR as % of price

    signals = []

    # RSI oversold component (30=full, 50=zero)
    rsi_score = max(0, (50 - rsi) / 50 * 40) if rsi < 50 else 0

    # Dip component (20% dip = 20 pts max, capped at 25)
    dip_score = min(25, dip * 1.2)

    # Volume surge component (2x = 10 pts, 3x = 20 pts)
    vol_score = min(20, (vol - 1) * 13)

    # Momentum — 4h upward reversal from dip
    mom_score = min(10, max(0, m4h) * 3)

    # Breakout bonus (near 7d high with surge = high conviction)
    breakout_bonus = 5 if (breakout > 95 and vol > 1.8) else 0

    # Extreme oversold bonus
    extreme_bonus = 5 if rsi < 25 else 0

    # Signal classification
    if rsi < 38 and dip > 15 and vol > 1.5:
        signals.append("DEEP_DIP")
    if breakout > 95 and vol > 2.0 and m4h > 2.0:
        signals.append("BREAKOUT")
    if 8 < dip < 20 and 40 <= rsi <= 55:
        signals.append("ACCUMULATION")
    if rsi < 25 and dip > 25:
        signals.append("EXTREME_OVERSOLD")
    if not signals:
        signals.append("WATCH")

    total = max(0, min(100, rsi_score + dip_score + vol_score + mom_score + breakout_bonus + extreme_bonus))

    return {**p,
            "score":     round(total, 1),
            "signals":   signals,
            "rsi_score": round(rsi_score, 1),
            "dip_score": round(dip_score, 1),
            "vol_score": round(vol_score, 1),
            "mom_score": round(mom_score, 1),
            }


# ─────────────────────────────────────────────
# 6. SIZING SUGGESTION (for $150 bankroll)
# ─────────────────────────────────────────────
def suggest_sizing(score: float, bankroll: float = 150.0) -> dict:
    """
    Fractional Kelly-inspired sizing given score and bankroll.
    Never risks more than 20% on single trade. Minimum $5.
    """
    if score < 20:
        pct = 0.0
    elif score < 35:
        pct = 0.04   # 4%
    elif score < 50:
        pct = 0.07   # 7%
    elif score < 65:
        pct = 0.10   # 10%
    elif score < 80:
        pct = 0.15   # 15%
    else:
        pct = 0.20   # 20% max

    suggested = round(bankroll * pct, 2)
    if 0 < suggested < 5.0:
        suggested = 5.0
    return {"pct": round(pct * 100, 0), "usd": suggested}


# ─────────────────────────────────────────────
# 7. MAIN SCANNER
# ─────────────────────────────────────────────
def run_scan(bankroll: float = 150.0, top_n: int = 15) -> dict:
    print("[SPIKE-HUNTER] Fetching universe...", flush=True)
    all_pairs = fetch_pairs()
    print(f"[SPIKE-HUNTER] {len(all_pairs)} active USD/USDT pairs found", flush=True)

    pair_ids = [p["pair_id"] for p in all_pairs]

    print("[SPIKE-HUNTER] Fetching live tickers...", flush=True)
    tickers = fetch_ticker_batch(pair_ids)

    results = []
    for idx, meta in enumerate(all_pairs):
        pid  = meta["pair_id"]
        tick = tickers.get(pid) or tickers.get(meta["altname"]) or {}

        print(f"  [{idx+1}/{len(all_pairs)}] {pid}", end="  ", flush=True)

        try:
            candles = fetch_ohlcv(pid)
            if len(candles) < 20:
                print("skip (insufficient data)")
                continue
            time.sleep(0.15)  # polite rate limiting

            closes = [float(c[4]) for c in candles]
            highs  = [float(c[2]) for c in candles]
            lows   = [float(c[3]) for c in candles]

            cur_price = closes[-1]
            if cur_price <= 0:
                print("skip (zero price)")
                continue

            rsi     = _rsi(closes)
            moms    = _momentum_scores(closes)
            dip     = _dip_from_high(closes, highs)
            brk     = _breakout_proximity(closes, highs)
            vol_s   = _vol_surge(candles)
            atr     = _atr(candles)
            atr_rel = round(atr / cur_price * 100, 3)

            week_high = max(highs)
            week_low  = min(lows)

            t24h_vol = 0.0
            change24h = 0.0
            if tick:
                try:
                    t24h_vol  = float(tick.get("v", [0, 0])[1])
                    open24h   = float(tick.get("o", cur_price))
                    change24h = round((cur_price - open24h) / open24h * 100, 3) if open24h else 0
                except Exception:
                    pass

            row = {
                "pair":           pid,
                "wsname":         meta["wsname"],
                "price":          round(cur_price, 6),
                "week_high":      round(week_high, 6),
                "week_low":       round(week_low, 6),
                "rsi":            rsi,
                "dip_from_high_pct": dip,
                "breakout_pct":   brk,
                "vol_surge":      vol_s,
                "m1h":            moms["m1h"],
                "m4h":            moms["m4h"],
                "m24h":           moms["m24h"],
                "change24h":      change24h,
                "atr_rel_pct":    atr_rel,
                "vol_24h_usd":    round(t24h_vol * cur_price, 0),
            }

            scored = score_pair(row)
            sizing = suggest_sizing(scored["score"], bankroll)
            scored["size_pct"]  = sizing["pct"]
            scored["size_usd"]  = sizing["usd"]
            scored["bankroll"]  = bankroll

            results.append(scored)
            print(f"score={scored['score']} RSI={rsi} dip={dip}% vol×{vol_s} signals={scored['signals']}")
        except Exception as exc:
            print(f"skip (error: {exc})")
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[:top_n]

    out = {
        "schema":       "luma_spike_hunter_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "bankroll":     bankroll,
        "pairs_scanned": len(results),
        "top_n":        top_n,
        "leaderboard":  top,
    }

    # Save to disk
    out_file = OUT_DIR / "spike_hunter_latest.json"
    out_file.write_text(json.dumps(out, indent=2))
    print(f"\n[SPIKE-HUNTER] Saved -> {out_file}")
    print(f"[SPIKE-HUNTER] TOP {top_n} RESULTS:")
    for i, r in enumerate(top, 1):
        sigs = ",".join(r["signals"])
        print(f"  #{i:2d}  {r['pair']:20s}  score={r['score']:5.1f}  "
              f"RSI={r['rsi']:5.1f}  dip={r['dip_from_high_pct']:5.1f}%  "
              f"vol×{r['vol_surge']:.2f}  signals=[{sigs}]  "
              f"-> ${r['size_usd']} ({r['size_pct']}%)")

    return out


if __name__ == "__main__":
    bankroll = float(sys.argv[1]) if len(sys.argv) > 1 else 150.0
    run_scan(bankroll=bankroll)
