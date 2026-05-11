"""
Backtest your spike-hunter scoring algorithm against Kraken historical OHLC.

For each historical hourly bar (lookback >= 24h), we compute the EXACT same
features your live scanner uses (RSI, dip-from-7d-high, vol surge, momentum)
score the setup, then measure forward returns at +4h and +24h.

Output:
  - out/backtest/score_buckets.csv      (per-bucket stats)
  - out/backtest/all_signals.csv        (every scored bar with forward returns)
  - prints summary + recommended threshold

Run:
  .venv\\Scripts\\python.exe code\\backtest_spike_hunter.py
"""
from __future__ import annotations
import csv
import json
import math
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "out" / "backtest"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Reuse exact scoring algorithm from live scanner
sys.path.insert(0, str(ROOT / "code"))
import kraken_spike_hunter_live as sh  # type: ignore

KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"
KRAKEN_PAIRS = "https://api.kraken.com/0/public/AssetPairs"

# Use 60-min bars; 720 bars = 30 days. Kraken returns up to 720 bars per call.
INTERVAL_MIN = 60
LOOKBACK_BARS = 720

# Forward return horizons (in hourly bars)
FWD_HORIZONS = [4, 24]


def _http_get(url: str, params: dict | None = None, timeout: int = 30) -> dict:
    if params:
        from urllib.parse import urlencode
        url = url + "?" + urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "luma-backtest/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def select_pairs(target_count: int = 40) -> list[str]:
    """Pick a representative basket: top-volume USD pairs."""
    data = _http_get(KRAKEN_PAIRS).get("result", {})
    usd_pairs = [
        (k, v) for k, v in data.items()
        if isinstance(v, dict) and v.get("quote") in ("ZUSD", "USD")
        and v.get("status") == "online"
    ]
    # No volume metadata in AssetPairs — use a hand-curated representative set
    # plus current top pairs from any cached spike-hunter scan.
    base_basket = [
        "XBTUSD", "ETHUSD", "SOLUSD", "ADAUSD", "DOGEUSD", "XRPUSD",
        "AVAXUSD", "DOTUSD", "MATICUSD", "LINKUSD", "ATOMUSD", "LTCUSD",
        "UNIUSD", "AAVEUSD", "ALGOUSD", "FILUSD", "ICPUSD", "ARBUSD",
        "OPUSD", "INJUSD", "SUIUSD", "TIAUSD", "RNDRUSD", "NEARUSD",
        "APTUSD", "HBARUSD", "FTMUSD", "EGLDUSD", "FETUSD", "GRTUSD",
        "RUNEUSD", "CRVUSD", "MKRUSD", "COMPUSD", "LDOUSD", "STXUSD",
        "TRXUSD", "BCHUSD", "ETCUSD", "MANAUSD",
    ]
    valid_keys = {k for k, _ in usd_pairs}
    # Map common short forms (e.g., XBTUSD might be XXBTZUSD on Kraken)
    aliases = {p["altname"]: k for k, p in data.items() if isinstance(p, dict) and "altname" in p}
    chosen = []
    for sym in base_basket:
        if sym in valid_keys:
            chosen.append(sym)
        elif sym in aliases:
            chosen.append(aliases[sym])
        if len(chosen) >= target_count:
            break
    return chosen


def fetch_ohlc(pair: str, interval: int = INTERVAL_MIN) -> list[list]:
    """Returns list of [time, open, high, low, close, vwap, volume, count]."""
    try:
        resp = _http_get(KRAKEN_OHLC, {"pair": pair, "interval": interval})
        result = resp.get("result", {})
        # Kraken returns key as the canonical pair name, not necessarily what we asked.
        for k, v in result.items():
            if k == "last":
                continue
            if isinstance(v, list):
                return v
    except Exception as e:
        print(f"  [FETCH FAIL] {pair}: {e}", flush=True)
    return []


def score_at_index(candles: list[list], idx: int) -> dict | None:
    """Replay live scoring at historical index `idx` using only data available then."""
    if idx < 168:  # need at least 7 days (168h) lookback for dip/vol baselines
        return None
    window = candles[idx - 168 : idx + 1]
    if len(window) < 169:
        return None

    closes = [float(c[4]) for c in window]
    highs  = [float(c[2]) for c in window]

    rsi   = sh._rsi(closes)
    vol   = sh._vol_surge(window)
    mom   = sh._momentum_scores(closes)
    dip   = sh._dip_from_high(closes[:-1], highs[:-1])  # 7d high excluding current bar
    bkout = sh._breakout_proximity(closes, highs)
    atr   = sh._atr(window)
    price = closes[-1]
    atr_rel = (atr / price * 100) if price else 0.0

    pair_features = {
        "pair": "BACKTEST",
        "price": price,
        "rsi": rsi,
        "dip_from_high_pct": dip,
        "vol_surge": vol,
        "m1h": mom["m1h"],
        "m4h": mom["m4h"],
        "m24h": mom["m24h"],
        "breakout_pct": bkout,
        "atr_rel_pct": atr_rel,
        "vol_24h_usd": 0,  # not used by score_pair
    }
    return sh.score_pair(pair_features)


def fwd_return(candles: list[list], idx: int, horizon: int) -> float | None:
    if idx + horizon >= len(candles):
        return None
    entry = float(candles[idx][4])
    exit_ = float(candles[idx + horizon][4])
    if entry <= 0:
        return None
    return (exit_ - entry) / entry * 100  # percent


def run_backtest():
    print(f"[BACKTEST] Selecting pairs...", flush=True)
    pairs = select_pairs(40)
    print(f"[BACKTEST] {len(pairs)} pairs: {pairs}", flush=True)

    all_signals = []  # rows for CSV
    pair_count = 0
    bar_count = 0

    for pair in pairs:
        print(f"[BACKTEST] Fetching {pair}...", flush=True)
        candles = fetch_ohlc(pair)
        if len(candles) < 200:
            print(f"  [SKIP] {pair} only {len(candles)} bars", flush=True)
            continue
        pair_count += 1

        # Score every bar from 168 to (len - max horizon)
        last_scoreable = len(candles) - max(FWD_HORIZONS) - 1
        for idx in range(168, last_scoreable):
            scored = score_at_index(candles, idx)
            if scored is None:
                continue
            score = scored["score"]
            signals = ",".join(scored["signals"])
            row = {
                "pair": pair,
                "bar_idx": idx,
                "ts": int(candles[idx][0]),
                "price": scored["price"],
                "rsi": scored["rsi"],
                "dip": scored["dip_from_high_pct"],
                "vol_surge": scored["vol_surge"],
                "score": score,
                "signals": signals,
            }
            for h in FWD_HORIZONS:
                r = fwd_return(candles, idx, h)
                row[f"fwd_{h}h_pct"] = r
            all_signals.append(row)
            bar_count += 1
        time.sleep(0.5)  # be polite to Kraken public API

    if not all_signals:
        print("[BACKTEST] No signals generated. Aborting.", flush=True)
        return

    # Write raw rows
    raw_path = OUT_DIR / "all_signals.csv"
    fieldnames = list(all_signals[0].keys())
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_signals)
    print(f"[BACKTEST] Wrote {len(all_signals)} rows -> {raw_path}", flush=True)

    # Bucket analysis
    buckets = [(0, 20), (20, 35), (35, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 101)]
    print()
    print(f"  Pairs scored: {pair_count}   Total bars: {bar_count}")
    print()

    bucket_rows = []
    for h in FWD_HORIZONS:
        print(f"=== Forward return horizon: +{h}h ===")
        print(f"{'Score Range':<14}{'N':>7}{'Mean %':>10}{'Median %':>10}{'StDev':>9}{'WinRate':>9}{'Sharpe':>9}{'EdgeFreq':>10}")
        for lo, hi in buckets:
            rs = [r[f"fwd_{h}h_pct"] for r in all_signals
                  if r["score"] >= lo and r["score"] < hi and r[f"fwd_{h}h_pct"] is not None]
            n = len(rs)
            if n < 5:
                continue
            mean = statistics.mean(rs)
            median = statistics.median(rs)
            sd = statistics.stdev(rs) if n > 1 else 0.0
            wins = sum(1 for x in rs if x > 0)
            wr = wins / n * 100
            sharpe = (mean / sd) if sd > 0 else 0.0
            edge_freq = mean * n  # crude proxy: mean edge × frequency
            print(f"  [{lo:>3}-{hi:>3})   {n:>7}{mean:>10.3f}{median:>10.3f}{sd:>9.3f}{wr:>8.1f}%{sharpe:>9.3f}{edge_freq:>10.1f}")
            bucket_rows.append({
                "horizon_h": h,
                "score_lo": lo, "score_hi": hi,
                "n": n, "mean_pct": round(mean, 4), "median_pct": round(median, 4),
                "stdev_pct": round(sd, 4), "win_rate_pct": round(wr, 2),
                "sharpe": round(sharpe, 4), "edge_x_freq": round(edge_freq, 2),
            })
        print()

    # Write bucket analysis
    if bucket_rows:
        bucket_path = OUT_DIR / "score_buckets.csv"
        with bucket_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(bucket_rows[0].keys()))
            w.writeheader()
            w.writerows(bucket_rows)
        print(f"[BACKTEST] Wrote bucket analysis -> {bucket_path}", flush=True)

    # Threshold sweep — find score threshold that maximizes Sharpe (need >=20 trades)
    print()
    print("=== Threshold sweep — find optimal cutoff ===")
    for h in FWD_HORIZONS:
        print(f"  Horizon +{h}h:")
        best = None
        for thresh in range(20, 95, 5):
            rs = [r[f"fwd_{h}h_pct"] for r in all_signals
                  if r["score"] >= thresh and r[f"fwd_{h}h_pct"] is not None]
            if len(rs) < 20:
                continue
            mean = statistics.mean(rs)
            sd = statistics.stdev(rs) if len(rs) > 1 else 0.0
            sharpe = (mean / sd) if sd > 0 else 0.0
            wins = sum(1 for x in rs if x > 0)
            wr = wins / len(rs) * 100
            print(f"    score>={thresh:>3}  N={len(rs):>5}  mean={mean:+.3f}%  win={wr:5.1f}%  sharpe={sharpe:+.3f}")
            if best is None or sharpe > best[3]:
                best = (thresh, mean, len(rs), sharpe, wr)
        if best:
            print(f"  >>> Best Sharpe at score>={best[0]}: mean={best[1]:+.3f}% N={best[2]} sharpe={best[3]:+.3f} wins={best[4]:.1f}%")
        print()


if __name__ == "__main__":
    run_backtest()
