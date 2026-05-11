"""
MULTI-SOURCE universe backtest.
Loads Kraken USD pairs + Alpaca SIP stocks + Alpaca crypto.
Walk-forward (60d train / 30d test rolling) on the 2-year sample.
Multi-process across ~20 CPU cores.
"""
from __future__ import annotations
import sys, os, time, math, pickle
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
sys.path.insert(0, str(CODE))
OUT = ROOT / "out" / "backtest"

CACHES = [
    (OUT/"ohlc_universe.pkl",        "kraken_crypto"),  # 30d hourly Kraken
    (OUT/"ohlc_alpaca_stocks.pkl",   "alpaca_stock"),   # 2y hourly SIP stocks
    (OUT/"ohlc_alpaca_crypto.pkl",   "alpaca_crypto"),  # 2y hourly Alpaca crypto
]

ANNUAL_HOURLY = math.sqrt(24*365)
FEE_BPS_BY_CLASS = {
    "kraken_crypto": 25.0,
    "alpaca_crypto": 15.0,   # alpaca crypto fees ~10-15 bps
    "alpaca_stock":  2.0,    # equities essentially zero commission, just spread+slippage
}

# Walk-forward windows (in HOURS).  60d/30d rolling for 2y sample, fallback for 30d sample.
def walk_windows(n_hours: int):
    if n_hours >= 60*24 + 30*24*2:  # 2y sample
        return 60*24, 30*24
    return 14*24, 7*24             # 30d sample

# ---- workers ----
def _eval(args):
    s_name, a_name, sym, df_dict, is_hybrid, asset_class = args
    try:
        import importlib
        if "hyb_mod" not in globals():
            globals()["hyb_mod"]  = importlib.import_module("hybrid_harmonic_strategies")
            globals()["inst_mod"] = importlib.import_module("institutional_harmonic_suite")
        hyb = globals()["hyb_mod"]; inst = globals()["inst_mod"]
        s_fn = hyb.STRATEGIES[s_name] if is_hybrid else inst.STRATEGIES[s_name]
        a_fn = inst.ALGOS[a_name]
        close = pd.Series(df_dict["c"], index=df_dict["t"]).astype(float)
        if len(close) < 60: return None
        ret = close.pct_change().fillna(0.0)
        sig_raw = s_fn(close) if is_hybrid else s_fn(ret)
        sig = a_fn(sig_raw, ret).reindex(ret.index).fillna(0.0).clip(-1,1).shift(1).fillna(0.0)
        fee = FEE_BPS_BY_CLASS.get(asset_class, 25.0) / 10000.0
        cost = sig.diff().abs().fillna(0.0) * fee
        net = sig*ret - cost
        if len(net) < 50 or net.std() == 0: return None
        is_sharpe = float(net.mean()/net.std()*ANNUAL_HOURLY)
        is_cum = float((1+net).prod()-1)
        active_share = float((sig.abs() > 0.01).mean())

        train_h, test_h = walk_windows(len(net))
        oos_segments = []
        cursor = train_h
        while cursor + test_h <= len(net):
            oos_segments.append(net.iloc[cursor:cursor+test_h])
            cursor += test_h
        if oos_segments:
            oos = pd.concat(oos_segments)
            oos_sharpe = float(oos.mean()/oos.std()*ANNUAL_HOURLY) if oos.std()>0 else 0.0
            oos_cum    = float((1+oos).prod()-1)
            oos_win    = float((oos>0).sum()/max(1,(oos!=0).sum()))
            n_windows  = len(oos_segments)
        else:
            oos_sharpe = oos_cum = oos_win = float('nan'); n_windows = 0

        return {
            "strategy": s_name, "algo": a_name, "symbol": sym, "asset_class": asset_class,
            "n_bars": int(len(net)), "active_share": round(active_share,3),
            "is_sharpe": round(is_sharpe,3), "is_cum": round(is_cum,4),
            "oos_sharpe": round(oos_sharpe,3) if not np.isnan(oos_sharpe) else None,
            "oos_cum":    round(oos_cum,4)    if not np.isnan(oos_cum)    else None,
            "oos_win":    round(oos_win,4)    if not np.isnan(oos_win)    else None,
            "n_oos_windows": n_windows,
        }
    except Exception:
        return None

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("="*76); print("MULTI-SOURCE UNIVERSE BACKTEST"); print("="*76)
    pair_data = {}  # symbol -> dict; key collisions resolved by class suffix
    classes_seen = {}
    for path, klass in CACHES:
        if not path.exists():
            print(f"[SKIP] {path.name} not found"); continue
        try:
            with open(path,"rb") as f: cache = pickle.load(f)
        except Exception as e:
            print(f"[SKIP] {path.name} load fail: {e}"); continue
        n = 0
        for sym, df in cache.items():
            if df is None or len(df) < 30*24: continue
            tag = f"{klass}::{sym}"
            pair_data[tag] = {"c": df["c"].astype(float).values.tolist(), "t": df.index.tolist(), "class": klass}
            n += 1
        classes_seen[klass] = n
        print(f"[LOAD] {path.name}: {n} eligible symbols")
    print(f"[TOTAL] {len(pair_data)} symbols across {len(classes_seen)} asset classes")

    sys.path.insert(0, str(CODE))
    from hybrid_harmonic_strategies import STRATEGIES as HYBRID
    from institutional_harmonic_suite import STRATEGIES as INST, ALGOS

    jobs = []
    for sym, d in pair_data.items():
        klass = d["class"]
        for s_name in HYBRID:
            for a_name in ALGOS:
                jobs.append((s_name, a_name, sym, d, True, klass))
        for s_name in INST:
            for a_name in ALGOS:
                jobs.append((s_name, a_name, sym, d, False, klass))
    n_strats = len(HYBRID) + len(INST)
    print(f"[JOBS] strats={n_strats} algos={len(ALGOS)} symbols={len(pair_data)} -> {len(jobs)} total jobs")

    workers = max(2, min(20, mp.cpu_count()-2))
    print(f"[POOL] workers={workers} (cpu={mp.cpu_count()})")

    rows = []
    t0 = time.time()
    INCR = OUT/"universe_multi_per_pair_incr.csv"
    if INCR.exists(): INCR.unlink()
    header_written = False
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_eval, j) for j in jobs]
        done = 0
        batch = []
        for fut in as_completed(futures):
            try: r = fut.result()
            except: r = None
            if r:
                rows.append(r); batch.append(r)
            done += 1
            if done % 5000 == 0:
                # flush batch to disk
                if batch:
                    bdf = pd.DataFrame(batch)
                    bdf.to_csv(INCR, mode="a", header=not header_written, index=False)
                    header_written = True; batch = []
                pct = 100*done/len(jobs)
                print(f"[BT] {done}/{len(jobs)} ({pct:.1f}%) | rows={len(rows)} | {time.time()-t0:.0f}s", flush=True)
        if batch:
            bdf = pd.DataFrame(batch)
            bdf.to_csv(INCR, mode="a", header=not header_written, index=False)
    print(f"[BT] DONE {len(jobs)} jobs in {time.time()-t0:.1f}s | valid rows={len(rows)}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT/"universe_multi_per_pair.csv", index=False)
    print(f"[BT] Wrote universe_multi_per_pair.csv ({len(df)} rows)")

    # Aggregate per (asset_class, strategy, algo)
    agg = []
    for (klass, s, a), grp in df.groupby(["asset_class","strategy","algo"]):
        g2 = grp.dropna(subset=["oos_sharpe"])
        if len(g2) < 5: continue
        agg.append({
            "asset_class": klass, "strategy": s, "algo": a,
            "n_symbols": len(g2),
            "is_sharpe_med":  round(g2["is_sharpe"].median(),3),
            "is_pos_pct":     round((g2["is_sharpe"]>0).mean(),3),
            "oos_sharpe_med": round(g2["oos_sharpe"].median(),3),
            "oos_sharpe_mean":round(g2["oos_sharpe"].mean(),3),
            "oos_pos_pct":    round((g2["oos_sharpe"]>0).mean(),3),
            "active_share":   round(g2["active_share"].median(),3),
        })
    adf = pd.DataFrame(agg)
    adf["degrade"] = (adf["is_sharpe_med"] - adf["oos_sharpe_med"]).round(3)
    adf = adf.sort_values(["asset_class","oos_sharpe_med"], ascending=[True,False])
    adf.to_csv(OUT/"universe_multi_summary.csv", index=False)

    pd.set_option("display.width", 240)
    pd.set_option("display.max_colwidth", 30)
    for klass in adf["asset_class"].unique():
        sub = adf[adf["asset_class"]==klass]
        print(); print("="*100)
        print(f"TOP 15 by OOS MEDIAN SHARPE  --  {klass}")
        print("="*100)
        print(sub.head(15).to_string(index=False))
        print(f"\nBOTTOM 5 -- {klass}")
        print(sub.tail(5).to_string(index=False))

    print()
    print("="*100); print("WHICH STRATEGIES SURVIVE OOS ACROSS ALL CLASSES (median oos_sharpe > 0.5 in 2+ classes)")
    print("="*100)
    survivors = adf[adf["oos_sharpe_med"]>0.5].groupby(["strategy","algo"]).agg(
        classes=("asset_class","nunique"),
        avg_oos=("oos_sharpe_med","mean"),
    ).reset_index().query("classes>=2").sort_values("avg_oos", ascending=False)
    print(survivors.to_string(index=False) if not survivors.empty else "(no strategy survives OOS in 2+ classes)")

if __name__ == "__main__":
    main()
