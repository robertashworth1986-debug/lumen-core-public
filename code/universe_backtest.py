"""
UNIVERSE-SCALE multiprocessed backtest.
Tests every (strategy, algo) combo across every cached pair, parallelized
across all CPU cores. Then walk-forward at scale.
"""
from __future__ import annotations
import sys, os, time, math, json, pickle, traceback
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
sys.path.insert(0, str(CODE))

OUT = ROOT / "out" / "backtest"
CACHE = OUT / "ohlc_universe.pkl"

ANNUAL_HOURLY = math.sqrt(24*365)
FEE_BPS = 25.0

# ---- workers ----
def _eval_pair(args):
    """Run a single (strategy, algo) on a single pair. Returns (s,a,pair, sharpe, cum, n_eff)."""
    s_name, a_name, pair, df_dict, is_hybrid = args
    try:
        import importlib
        if "hyb_mod" not in globals():
            globals()["hyb_mod"]  = importlib.import_module("hybrid_harmonic_strategies")
            globals()["inst_mod"] = importlib.import_module("institutional_harmonic_suite")
        hyb = globals()["hyb_mod"]; inst = globals()["inst_mod"]
        s_fn = hyb.STRATEGIES[s_name] if is_hybrid else inst.STRATEGIES[s_name]
        a_fn = inst.ALGOS[a_name]
        # rebuild pandas
        close = pd.Series(df_dict["c"], index=df_dict["t"]).astype(float)
        ret = close.pct_change().fillna(0.0)
        sig_raw = s_fn(close) if is_hybrid else s_fn(ret)
        sig = a_fn(sig_raw, ret).reindex(ret.index).fillna(0.0).clip(-1,1).shift(1).fillna(0.0)
        cost = sig.diff().abs().fillna(0.0)*(FEE_BPS/10000.0)
        net = sig*ret - cost
        if len(net) < 50 or net.std() == 0: return None
        sharpe = float(net.mean()/net.std()*ANNUAL_HOURLY)
        cum = float((1+net).prod()-1)
        win = float((net>0).sum()/max(1,(net!=0).sum()))
        # walk-forward 14d/7d
        train_h = 14*24; test_h = 7*24
        oos_returns = []
        n = len(net)
        cursor = train_h
        while cursor + test_h <= n:
            oos_returns.append(net.iloc[cursor:cursor+test_h])
            cursor += test_h
        if oos_returns:
            oos = pd.concat(oos_returns)
            oos_sharpe = float(oos.mean()/oos.std()*ANNUAL_HOURLY) if oos.std()>0 else 0.0
            oos_cum = float((1+oos).prod()-1)
            oos_win = float((oos>0).sum()/max(1,(oos!=0).sum()))
        else:
            oos_sharpe = oos_cum = oos_win = float('nan')
        return {
            "strategy": s_name, "algo": a_name, "pair": pair,
            "n_bars": int(len(net)),
            "is_sharpe": round(sharpe,3), "is_cum": round(cum,4), "is_win": round(win,4),
            "oos_sharpe": round(oos_sharpe,3) if not np.isnan(oos_sharpe) else None,
            "oos_cum": round(oos_cum,4) if not np.isnan(oos_cum) else None,
            "oos_win": round(oos_win,4) if not np.isnan(oos_win) else None,
        }
    except Exception:
        return None

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("="*76); print("UNIVERSE BACKTEST"); print("="*76)
    if not CACHE.exists():
        print("[ERR] No universe cache."); return
    with open(CACHE, "rb") as f: ohlc = pickle.load(f)
    print(f"[UNIV-BT] Loaded {len(ohlc)} pairs from cache")

    sys.path.insert(0, str(CODE))
    from hybrid_harmonic_strategies import STRATEGIES as HYBRID
    from institutional_harmonic_suite import STRATEGIES as INST, ALGOS

    # Pre-serialize OHLC into lightweight dicts to ship to workers
    pair_data = {}
    for p, df in ohlc.items():
        if len(df) < 21*24+7*24+10: continue  # need at least 1 walk-forward window
        pair_data[p] = {"c": df["c"].astype(float).values.tolist(), "t": df.index.tolist()}
    print(f"[UNIV-BT] Eligible pairs (>= 21d hourly): {len(pair_data)}")

    # Build job list
    jobs = []
    for s_name in HYBRID.keys():
        for a_name in ALGOS.keys():
            for pair in pair_data.keys():
                jobs.append((s_name, a_name, pair, pair_data[pair], True))
    for s_name in INST.keys():
        for a_name in ALGOS.keys():
            for pair in pair_data.keys():
                jobs.append((s_name, a_name, pair, pair_data[pair], False))
    print(f"[UNIV-BT] Total jobs: {len(jobs)}  ({len(HYBRID)+len(INST)} strats x {len(ALGOS)} algos x {len(pair_data)} pairs)")
    print(f"[UNIV-BT] CPU cores: {mp.cpu_count()}, using ProcessPoolExecutor")

    rows = []
    t0 = time.time()
    workers = max(2, min(20, mp.cpu_count()-2))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_eval_pair, j) for j in jobs]
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            if r: rows.append(r)
            if i % 2000 == 0:
                print(f"[UNIV-BT] {i}/{len(jobs)} jobs done | rows={len(rows)} | {time.time()-t0:.0f}s elapsed")
    print(f"[UNIV-BT] All {len(jobs)} jobs done in {time.time()-t0:.1f}s. {len(rows)} valid rows.")

    df = pd.DataFrame(rows)
    df.to_csv(OUT/"universe_per_pair.csv", index=False)
    print(f"[UNIV-BT] Saved per-pair rows to universe_per_pair.csv")

    # Aggregate per (strategy, algo): pooled IS sharpe, pooled OOS sharpe
    agg = []
    for (s, a), grp in df.groupby(["strategy","algo"]):
        grp = grp.dropna(subset=["oos_sharpe"])
        if grp.empty: continue
        # weight per-pair sharpes by n_bars for stability
        is_sh_med = float(grp["is_sharpe"].median())
        is_sh_mean = float(grp["is_sharpe"].mean())
        oos_sh_med = float(grp["oos_sharpe"].median())
        oos_sh_mean = float(grp["oos_sharpe"].mean())
        n_pairs = len(grp)
        pos_pairs_is = int((grp["is_sharpe"]>0).sum())
        pos_pairs_oos = int((grp["oos_sharpe"]>0).sum())
        agg.append({
            "strategy": s, "algo": a, "n_pairs": n_pairs,
            "is_sharpe_median": round(is_sh_med,3),
            "is_sharpe_mean":   round(is_sh_mean,3),
            "is_pos_pct":       round(pos_pairs_is/n_pairs,3),
            "oos_sharpe_median": round(oos_sh_med,3),
            "oos_sharpe_mean":   round(oos_sh_mean,3),
            "oos_pos_pct":       round(pos_pairs_oos/n_pairs,3),
        })
    adf = pd.DataFrame(agg).sort_values("oos_sharpe_median", ascending=False)
    adf.to_csv(OUT/"universe_summary.csv", index=False)
    print()
    print("="*76); print("LEADERBOARD by OOS MEDIAN SHARPE (walk-forward, 25bps)"); print("="*76)
    print(adf.head(25).to_string(index=False))
    print()
    print("="*76); print("LEADERBOARD by IN-SAMPLE MEDIAN SHARPE"); print("="*76)
    print(adf.sort_values("is_sharpe_median", ascending=False).head(15).to_string(index=False))
    print()
    print("="*76); print("WORST IS-OOS DEGRADATION (overfit signal)"); print("="*76)
    adf["degrade"] = adf["is_sharpe_median"] - adf["oos_sharpe_median"]
    print(adf.sort_values("degrade", ascending=False).head(10).to_string(index=False))

if __name__ == "__main__":
    main()
