"""
MEGA backtest — runs everything in 6 phases. Each phase writes its own CSV.
Re-uses ohlc_cache.pkl for hourly hot path.

Phases:
  1. Hourly + REALISTIC FEES (25bps round-trip)
  2. Walk-forward (14d train / 7d test rolling)
  3. 15-minute timeframe retest
  4. Microcap basket retest
  5. Two-strategy ensemble combinations (signal averaging)
  6. Flowform position-sizing layer on top combos
"""
from __future__ import annotations
import sys, os, time, math, json, pickle, traceback, itertools
from pathlib import Path
import urllib.request
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from hybrid_harmonic_strategies import STRATEGIES as HYBRID_STRATS
from institutional_harmonic_suite import (
    STRATEGIES as INST_STRATS, ALGOS, FLOWFORMS,
)

OUT = ROOT / "out" / "backtest"
OUT.mkdir(parents=True, exist_ok=True)
CACHE_HOURLY = OUT / "ohlc_cache.pkl"
CACHE_15M    = OUT / "ohlc_cache_15m.pkl"
CACHE_MICRO  = OUT / "ohlc_cache_microcap.pkl"

ALL_STRATS = {**HYBRID_STRATS, **INST_STRATS}
ANNUAL_HOURLY = math.sqrt(24 * 365)
ANNUAL_15M    = math.sqrt(24 * 365 * 4)

PAIRS = [
    "XXBTZUSD","XETHZUSD","SOLUSD","ADAUSD","XXRPZUSD","AVAXUSD","DOTUSD","LINKUSD",
    "ATOMUSD","XLTCZUSD","UNIUSD","AAVEUSD","ALGOUSD","FILUSD","ICPUSD","ARBUSD",
    "OPUSD","INJUSD","SUIUSD","TIAUSD","NEARUSD","APTUSD","HBARUSD","EGLDUSD",
    "FETUSD","GRTUSD","RUNEUSD","CRVUSD","COMPUSD","LDOUSD","STXUSD","TRXUSD",
    "BCHUSD","XETCZUSD","MANAUSD",
]
# Microcap-ish pairs (small/newer listings, same family as live positions)
MICROCAP = [
    "API3USD","BABYUSD","FHEUSD","PYTHUSD","JTOUSD","WUSD","BONKUSD","MEMEUSD",
    "WIFUSD","TAOUSD","BLZUSD","CTSIUSD","GHSTUSD","MASKUSD","ENAUSD","JUPUSD",
    "PEPEUSD","FLOKIUSD","SHIBUSD","NOTUSD","DOGSUSD","WLDUSD","ZKUSD","STRKUSD",
    "POLUSD","RNDRUSD","ORDIUSD","PENDLEUSD","WBTCUSD","TURBOUSD","PORTALUSD",
]

KRAKEN_OHLC = "https://api.kraken.com/0/public/OHLC"

def fetch_ohlc(pair: str, interval: int) -> pd.DataFrame | None:
    try:
        url = f"{KRAKEN_OHLC}?pair={pair}&interval={interval}"
        req = urllib.request.Request(url, headers={"User-Agent": "luma-mega/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        if data.get("error"): return None
        result = data.get("result", {})
        key = next((k for k in result.keys() if k != "last"), None)
        if not key: return None
        rows = result[key]
        df = pd.DataFrame(rows, columns=["t","o","h","l","c","vwap","v","trades"])
        df["c"] = df["c"].astype(float)
        df["t"] = pd.to_datetime(df["t"].astype(int), unit="s")
        return df.set_index("t").sort_index()
    except Exception:
        return None

def load_or_fetch(pairs: list[str], interval: int, cache: Path) -> dict[str, pd.DataFrame]:
    if cache.exists():
        try:
            with open(cache, "rb") as f: return pickle.load(f)
        except Exception: pass
    out = {}
    for p in pairs:
        df = fetch_ohlc(p, interval)
        if df is not None and len(df) >= 100:
            out[p] = df
        time.sleep(0.2)
    with open(cache, "wb") as f: pickle.dump(out, f)
    return out

def get_signal(strat_name, strat_fn, close, ret):
    if strat_name in HYBRID_STRATS:
        return strat_fn(close)
    return strat_fn(ret)

def run_combo_pair(strat_name, strat_fn, algo_name, algo_fn, df, fee_bps):
    close = df["c"].astype(float)
    ret = close.pct_change().fillna(0.0)
    sig_raw = get_signal(strat_name, strat_fn, close, ret)
    sig = algo_fn(sig_raw, ret).reindex(ret.index).fillna(0.0).clip(-1, 1).shift(1).fillna(0.0)
    strat_ret = sig * ret
    turnover = sig.diff().abs().fillna(0.0)
    cost = turnover * (fee_bps / 10000.0)
    return (strat_ret - cost), sig

def stats_pooled(net_series_list, annual):
    pooled = pd.concat(net_series_list, axis=0)
    if len(pooled) < 50 or pooled.std() == 0:
        return None
    mean, std = float(pooled.mean()), float(pooled.std())
    return {
        "n_bars": len(pooled),
        "mean_bp": round(mean*10000, 4),
        "sharpe": round(mean/std*annual, 3),
        "cum_return": round(float((1+pooled).prod()-1), 4),
        "win_rate": round(float((pooled>0).sum()/max(1,(pooled!=0).sum())), 4),
        "max_dd": round(float(((1+pooled).cumprod() / (1+pooled).cumprod().cummax() - 1).min()), 4),
    }

# ============================================================================
# PHASE 1: Hourly + realistic fees (5/15/25 bps)
# ============================================================================
def phase1(ohlc):
    print("\n" + "="*76)
    print("PHASE 1: HOURLY @ MULTIPLE FEE LEVELS")
    print("="*76)
    rows = []
    for fee in [5, 15, 25, 40]:
        for s_name, s_fn in ALL_STRATS.items():
            for a_name, a_fn in ALGOS.items():
                nets = []
                pos_pairs = 0
                for pair, df in ohlc.items():
                    try:
                        net, _ = run_combo_pair(s_name, s_fn, a_name, a_fn, df, fee)
                        if len(net) >= 50 and net.std() > 0:
                            nets.append(net)
                            if (1+net).prod() > 1: pos_pairs += 1
                    except Exception: continue
                if not nets: continue
                st = stats_pooled(nets, ANNUAL_HOURLY)
                if not st: continue
                rows.append({"fee_bps": fee, "strategy": s_name, "algo": a_name,
                             "pairs_pos": pos_pairs, "n_pairs": len(nets), **st})
    df = pd.DataFrame(rows).sort_values(["fee_bps","sharpe"], ascending=[True,False])
    df.to_csv(OUT/"mega_phase1_fees.csv", index=False)
    for fee in [5, 15, 25, 40]:
        sub = df[df.fee_bps == fee].head(5)
        print(f"\n  Fee = {fee}bps  TOP 5:")
        print(sub[["strategy","algo","sharpe","cum_return","win_rate","pairs_pos","n_pairs","max_dd"]].to_string(index=False))

# ============================================================================
# PHASE 2: Walk-forward 14/7 rolling
# ============================================================================
def phase2(ohlc):
    print("\n" + "="*76)
    print("PHASE 2: WALK-FORWARD (14d train / 7d test rolling, 25bps fee)")
    print("="*76)
    # For each pair, build a single combined ret series and split by index.
    # We rank combos by OOS Sharpe pooled across all OOS windows.
    rows = []
    for s_name, s_fn in ALL_STRATS.items():
        for a_name, a_fn in ALGOS.items():
            oos_nets = []
            for pair, df in ohlc.items():
                try:
                    net, sig = run_combo_pair(s_name, s_fn, a_name, a_fn, df, 25)
                    n = len(net)
                    if n < 21*24: continue
                    train_h = 14*24; test_h = 7*24
                    cursor = train_h
                    while cursor + test_h <= n:
                        oos = net.iloc[cursor:cursor+test_h]
                        oos_nets.append(oos)
                        cursor += test_h
                except Exception: continue
            if not oos_nets: continue
            st = stats_pooled(oos_nets, ANNUAL_HOURLY)
            if not st: continue
            rows.append({"strategy": s_name, "algo": a_name, **st})
    df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    df.to_csv(OUT/"mega_phase2_walkforward.csv", index=False)
    print("\n  WALK-FORWARD TOP 15 (out-of-sample):")
    print(df.head(15).to_string(index=False))
    print("\n  WALK-FORWARD BOTTOM 5 (worst OOS):")
    print(df.tail(5).to_string(index=False))

# ============================================================================
# PHASE 3: 15-min retest (top 30 hourly combos)
# ============================================================================
def phase3():
    print("\n" + "="*76)
    print("PHASE 3: 15-MINUTE TIMEFRAME (top 30 combos from Phase 1 @ 25bps)")
    print("="*76)
    # need 15m data — limit to fewer pairs for speed
    pairs15 = PAIRS[:20]  # first 20 of basket
    print(f"  Fetching 15m bars for {len(pairs15)} pairs...")
    ohlc15 = load_or_fetch(pairs15, 15, CACHE_15M)
    print(f"  Got {len(ohlc15)} pairs.")
    if not ohlc15: return

    # take top combos from phase1 25bps file
    p1 = pd.read_csv(OUT/"mega_phase1_fees.csv")
    top = p1[p1.fee_bps==25].head(30)[["strategy","algo"]].values.tolist()

    rows = []
    for s_name, a_name in top:
        s_fn = ALL_STRATS[s_name]; a_fn = ALGOS[a_name]
        nets = []
        for pair, df in ohlc15.items():
            try:
                net, _ = run_combo_pair(s_name, s_fn, a_name, a_fn, df, 25)
                if len(net) >= 50 and net.std() > 0: nets.append(net)
            except Exception: continue
        if not nets: continue
        st = stats_pooled(nets, ANNUAL_15M)
        if not st: continue
        rows.append({"strategy": s_name, "algo": a_name, "n_pairs": len(nets), **st})
    df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    df.to_csv(OUT/"mega_phase3_15m.csv", index=False)
    print(df.head(15).to_string(index=False))

# ============================================================================
# PHASE 4: Microcap basket
# ============================================================================
def phase4():
    print("\n" + "="*76)
    print("PHASE 4: MICROCAP BASKET (live-position-family)")
    print("="*76)
    print(f"  Fetching hourly for {len(MICROCAP)} microcap pairs...")
    ohlc_mc = load_or_fetch(MICROCAP, 60, CACHE_MICRO)
    print(f"  Got {len(ohlc_mc)} pairs.")
    if not ohlc_mc: return
    print(f"  Microcap pairs available: {sorted(ohlc_mc.keys())}")

    p1 = pd.read_csv(OUT/"mega_phase1_fees.csv")
    top = p1[p1.fee_bps==25].head(30)[["strategy","algo"]].values.tolist()
    rows = []
    for s_name, a_name in top:
        s_fn = ALL_STRATS[s_name]; a_fn = ALGOS[a_name]
        nets = []; pos_pairs=0
        for pair, df in ohlc_mc.items():
            try:
                net, _ = run_combo_pair(s_name, s_fn, a_name, a_fn, df, 25)
                if len(net) >= 50 and net.std() > 0:
                    nets.append(net)
                    if (1+net).prod() > 1: pos_pairs += 1
            except Exception: continue
        if not nets: continue
        st = stats_pooled(nets, ANNUAL_HOURLY)
        if not st: continue
        rows.append({"strategy": s_name, "algo": a_name, "n_pairs": len(nets), "pairs_pos": pos_pairs, **st})
    df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    df.to_csv(OUT/"mega_phase4_microcap.csv", index=False)
    print(df.head(15).to_string(index=False))

# ============================================================================
# PHASE 5: Two-strategy ensemble (signal average)
# ============================================================================
def phase5(ohlc):
    print("\n" + "="*76)
    print("PHASE 5: 2-STRATEGY ENSEMBLES (signal averaging, 25bps, hourly)")
    print("="*76)
    p1 = pd.read_csv(OUT/"mega_phase1_fees.csv")
    top10 = p1[p1.fee_bps==25].head(10)[["strategy","algo"]].values.tolist()
    rows = []
    for (s1,a1),(s2,a2) in itertools.combinations(top10, 2):
        if s1 == s2: continue
        s1f, a1f = ALL_STRATS[s1], ALGOS[a1]
        s2f, a2f = ALL_STRATS[s2], ALGOS[a2]
        nets = []
        for pair, df in ohlc.items():
            try:
                close = df["c"].astype(float); ret = close.pct_change().fillna(0.0)
                g1 = get_signal(s1, s1f, close, ret); g1 = a1f(g1, ret)
                g2 = get_signal(s2, s2f, close, ret); g2 = a2f(g2, ret)
                sig = ((g1+g2)/2.0).reindex(ret.index).fillna(0.0).clip(-1,1).shift(1).fillna(0.0)
                strat_ret = sig*ret
                cost = sig.diff().abs().fillna(0.0)*(25/10000.0)
                net = strat_ret - cost
                if len(net) >= 50 and net.std() > 0: nets.append(net)
            except Exception: continue
        if not nets: continue
        st = stats_pooled(nets, ANNUAL_HOURLY)
        if not st: continue
        rows.append({"s1": s1, "a1": a1, "s2": s2, "a2": a2, **st})
    df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    df.to_csv(OUT/"mega_phase5_ensembles.csv", index=False)
    print(df.head(15).to_string(index=False))

# ============================================================================
# PHASE 6: Flowform position-sizing on champion
# ============================================================================
def phase6(ohlc):
    print("\n" + "="*76)
    print("PHASE 6: FLOWFORMS as POSITION SIZER on champion combos")
    print("="*76)
    p1 = pd.read_csv(OUT/"mega_phase1_fees.csv")
    top5 = p1[p1.fee_bps==25].head(5)[["strategy","algo"]].values.tolist()
    rows = []
    for s_name, a_name in top5:
        s_fn, a_fn = ALL_STRATS[s_name], ALGOS[a_name]
        for ff_name, ff_fn in FLOWFORMS.items():
            nets = []
            for pair, df in ohlc.items():
                try:
                    close = df["c"].astype(float); ret = close.pct_change().fillna(0.0)
                    sig_raw = get_signal(s_name, s_fn, close, ret)
                    sig = a_fn(sig_raw, ret).reindex(ret.index).fillna(0.0).clip(-1,1)
                    # flowform produces a weight series — normalize and clip
                    try:
                        w = ff_fn(ret)
                        if isinstance(w, (int, float)):
                            w_series = pd.Series(float(w), index=ret.index)
                        else:
                            w_series = pd.Series(w, index=ret.index[:len(w)] if len(w) <= len(ret) else ret.index).reindex(ret.index).ffill().bfill().fillna(1.0)
                    except Exception:
                        w_series = pd.Series(1.0, index=ret.index)
                    w_norm = (w_series.abs() / (w_series.abs().rolling(50).mean() + 1e-9)).clip(0.25, 2.5).fillna(1.0)
                    final = (sig * w_norm).clip(-2.5, 2.5).shift(1).fillna(0.0)
                    strat_ret = final*ret
                    cost = final.diff().abs().fillna(0.0)*(25/10000.0)
                    net = strat_ret - cost
                    if len(net) >= 50 and net.std() > 0: nets.append(net)
                except Exception: continue
            if not nets: continue
            st = stats_pooled(nets, ANNUAL_HOURLY)
            if not st: continue
            rows.append({"strategy": s_name, "algo": a_name, "flowform": ff_name, **st})
    df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    df.to_csv(OUT/"mega_phase6_flowforms.csv", index=False)
    print(df.head(20).to_string(index=False))

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("="*76); print("MEGA MULTI-PHASE BACKTEST"); print("="*76)
    ohlc = load_or_fetch(PAIRS, 60, CACHE_HOURLY)
    print(f"Hourly basket: {len(ohlc)} pairs  |  Strats={len(ALL_STRATS)} Algos={len(ALGOS)} Flowforms={len(FLOWFORMS)}")

    t0 = time.time()
    try: phase1(ohlc)
    except Exception as e: traceback.print_exc()
    print(f"\n[Phase 1 done @ {time.time()-t0:.1f}s]")

    try: phase2(ohlc)
    except Exception as e: traceback.print_exc()
    print(f"\n[Phase 2 done @ {time.time()-t0:.1f}s]")

    try: phase3()
    except Exception as e: traceback.print_exc()
    print(f"\n[Phase 3 done @ {time.time()-t0:.1f}s]")

    try: phase4()
    except Exception as e: traceback.print_exc()
    print(f"\n[Phase 4 done @ {time.time()-t0:.1f}s]")

    try: phase5(ohlc)
    except Exception as e: traceback.print_exc()
    print(f"\n[Phase 5 done @ {time.time()-t0:.1f}s]")

    try: phase6(ohlc)
    except Exception as e: traceback.print_exc()
    print(f"\n[Phase 6 done @ {time.time()-t0:.1f}s]")

    print(f"\n[ALL DONE in {time.time()-t0:.1f}s]")

if __name__ == "__main__":
    main()
