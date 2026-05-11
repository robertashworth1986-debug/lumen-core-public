"""
Unified multi-strategy backtest.
Runs every directional strategy in:
  - code/hybrid_harmonic_strategies.py        (10 strats)
  - code/institutional_harmonic_suite.py      (12 strats + 7 algos)
across the same 35 USD-pair / 30-day / hourly basket and ranks by Sharpe.

Outputs:
  out/backtest/all_strats_rows.csv     per-combo per-pair row
  out/backtest/all_strats_summary.csv  per-combo aggregate ranked by Sharpe
  out/backtest/all_strats_run.log      stdout
"""
from __future__ import annotations
import sys, os, time, math, json, pickle, traceback
from pathlib import Path
import urllib.request, urllib.parse
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from hybrid_harmonic_strategies import STRATEGIES as HYBRID_STRATS
from institutional_harmonic_suite import STRATEGIES as INST_STRATS, ALGOS

OUT = ROOT / "out" / "backtest"
OUT.mkdir(parents=True, exist_ok=True)
CACHE = OUT / "ohlc_cache.pkl"

PAIRS = [
    "XXBTZUSD","XETHZUSD","SOLUSD","ADAUSD","XXRPZUSD","AVAXUSD","DOTUSD","LINKUSD",
    "ATOMUSD","XLTCZUSD","UNIUSD","AAVEUSD","ALGOUSD","FILUSD","ICPUSD","ARBUSD",
    "OPUSD","INJUSD","SUIUSD","TIAUSD","NEARUSD","APTUSD","HBARUSD","EGLDUSD",
    "FETUSD","GRTUSD","RUNEUSD","CRVUSD","COMPUSD","LDOUSD","STXUSD","TRXUSD",
    "BCHUSD","XETCZUSD","MANAUSD",
]

KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"

def fetch_ohlc(pair: str, interval: int = 60) -> pd.DataFrame | None:
    try:
        url = f"{KRAKEN_OHLC}?pair={pair}&interval={interval}"
        req = urllib.request.Request(url, headers={"User-Agent": "luma-backtest/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        if data.get("error"):
            return None
        result = data.get("result", {})
        key = next((k for k in result.keys() if k != "last"), None)
        if not key:
            return None
        rows = result[key]
        df = pd.DataFrame(rows, columns=["t","o","h","l","c","vwap","v","trades"])
        df["c"] = df["c"].astype(float)
        df["t"] = pd.to_datetime(df["t"].astype(int), unit="s")
        df = df.set_index("t").sort_index()
        return df
    except Exception:
        return None

def load_or_fetch_ohlc() -> dict[str, pd.DataFrame]:
    if CACHE.exists():
        try:
            with open(CACHE, "rb") as f:
                cached = pickle.load(f)
            print(f"[BACKTEST] Loaded {len(cached)} pairs from cache.")
            return cached
        except Exception:
            pass
    out = {}
    for p in PAIRS:
        print(f"[BACKTEST] Fetching {p}...")
        df = fetch_ohlc(p)
        if df is not None and len(df) >= 200:
            out[p] = df
        time.sleep(0.25)
    with open(CACHE, "wb") as f:
        pickle.dump(out, f)
    print(f"[BACKTEST] Cached {len(out)} pairs.")
    return out

# Hourly periods per year ~ 24*365 = 8760
ANNUAL = math.sqrt(24 * 365)
COST_BPS = 5.0  # 5 bps per turnover (entry+exit ~10bps round-trip estimate, conservative)

def evaluate(strat_name: str, strat_fn, algo_name: str, algo_fn,
             ohlc: dict[str, pd.DataFrame]) -> dict:
    """Run one (strategy, algo) combo across all pairs. Aggregate stats."""
    all_pair_returns = []   # per-pair series of strategy returns (after sig & cost)
    pair_stats = []
    for pair, df in ohlc.items():
        try:
            close = df["c"].astype(float)
            ret = close.pct_change().fillna(0.0)
            # hybrid takes a price-like series; institutional takes ret
            if strat_name in HYBRID_STRATS:
                sig_raw = strat_fn(close)
            else:
                sig_raw = strat_fn(ret)
            # algo takes (sig, ret)
            sig = algo_fn(sig_raw, ret)
            # align
            sig = sig.reindex(ret.index).fillna(0.0).clip(-1, 1)
            # strategy return: sig at t-1 already (strats apply shift(1)); but algo may not — apply shift here too defensively
            sig = sig.shift(1).fillna(0.0)
            strat_ret = sig * ret
            # transaction cost on |delta sig|
            turnover = sig.diff().abs().fillna(0.0)
            cost = turnover * (COST_BPS / 10000.0)
            net = strat_ret - cost
            if len(net) < 50 or net.std() == 0:
                continue
            all_pair_returns.append(net)
            pair_stats.append({
                "pair": pair,
                "n": int((sig != 0).sum()),
                "mean_bp": float(net.mean()*10000),
                "sharpe": float(net.mean()/net.std()*ANNUAL) if net.std() > 0 else 0.0,
                "cum_ret": float((1+net).prod() - 1),
            })
        except Exception:
            continue
    if not all_pair_returns:
        return None
    pooled = pd.concat(all_pair_returns, axis=0)
    mean = float(pooled.mean())
    std  = float(pooled.std())
    sharpe = (mean / std * ANNUAL) if std > 0 else 0.0
    cum = float((1 + pooled).prod() - 1)
    win = float((pooled > 0).sum() / max(1, (pooled != 0).sum()))
    pos_share = float((pooled != 0).sum() / max(1, len(pooled)))
    pair_sharpes = [s["sharpe"] for s in pair_stats]
    pair_pos = sum(1 for s in pair_sharpes if s > 0)
    return {
        "strategy": strat_name,
        "algo": algo_name,
        "n_pairs": len(pair_stats),
        "n_bars": int(len(pooled)),
        "active_share": round(pos_share, 4),
        "mean_bp_per_bar": round(mean*10000, 4),
        "sharpe_annual": round(sharpe, 3),
        "cum_return": round(cum, 4),
        "win_rate": round(win, 4),
        "pairs_positive": pair_pos,
        "pairs_positive_pct": round(pair_pos/len(pair_stats), 3),
        "median_pair_sharpe": round(float(np.median(pair_sharpes)), 3),
    }

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 76)
    print("UNIFIED MULTI-STRATEGY BACKTEST")
    print("=" * 76)
    ohlc = load_or_fetch_ohlc()
    if not ohlc:
        print("[BACKTEST] No OHLC data, abort."); return
    print(f"[BACKTEST] Universe: {len(ohlc)} pairs")
    print(f"[BACKTEST] Hybrid strats: {len(HYBRID_STRATS)}  Institutional strats: {len(INST_STRATS)}  Algos: {len(ALGOS)}")

    all_strats = {**HYBRID_STRATS, **INST_STRATS}
    print(f"[BACKTEST] Total combos: {len(all_strats)} x {len(ALGOS)} = {len(all_strats)*len(ALGOS)}")
    rows = []
    t0 = time.time()
    for s_name, s_fn in all_strats.items():
        for a_name, a_fn in ALGOS.items():
            try:
                r = evaluate(s_name, s_fn, a_name, a_fn, ohlc)
                if r:
                    rows.append(r)
                    print(f"  {s_name:24s} x {a_name:22s}  sharpe={r['sharpe_annual']:7.3f}  cum={r['cum_return']*100:7.2f}%  active={r['active_share']*100:5.1f}%  pairs+={r['pairs_positive']}/{r['n_pairs']}")
            except Exception as e:
                print(f"  ERR {s_name} x {a_name}: {e}")
    df = pd.DataFrame(rows)
    df = df.sort_values("sharpe_annual", ascending=False).reset_index(drop=True)
    df.to_csv(OUT / "all_strats_summary.csv", index=False)
    print()
    print("=" * 76)
    print("TOP 20 BY SHARPE")
    print("=" * 76)
    print(df.head(20).to_string(index=False))
    print()
    print("=" * 76)
    print("BOTTOM 10 BY SHARPE")
    print("=" * 76)
    print(df.tail(10).to_string(index=False))
    print()
    print(f"[BACKTEST] Done in {time.time()-t0:.1f}s. Wrote {OUT/'all_strats_summary.csv'}")

if __name__ == "__main__":
    main()
