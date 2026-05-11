"""
Parallel deep-dive — runs while mega is going.
Phase 7: Per-pair champion (best strategy per asset)
Phase 8: 3-strategy weighted ensemble (Sharpe-weighted)
Phase 9: Strategy CORRELATION matrix (find diversifiers)
Phase 10: Direction inversion test (does flipping LOW-Sharpe strats produce alpha?)
"""
from __future__ import annotations
import sys, math, json, pickle, itertools, traceback
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
from hybrid_harmonic_strategies import STRATEGIES as HYBRID_STRATS
from institutional_harmonic_suite import STRATEGIES as INST_STRATS, ALGOS

OUT = ROOT / "out" / "backtest"
ALL_STRATS = {**HYBRID_STRATS, **INST_STRATS}
ANNUAL_HOURLY = math.sqrt(24*365)
CACHE = OUT / "ohlc_cache.pkl"

def get_signal(name, fn, close, ret):
    return fn(close) if name in HYBRID_STRATS else fn(ret)

def run_pair(s_name, s_fn, a_name, a_fn, df, fee=25):
    close = df["c"].astype(float); ret = close.pct_change().fillna(0.0)
    sig_raw = get_signal(s_name, s_fn, close, ret)
    sig = a_fn(sig_raw, ret).reindex(ret.index).fillna(0.0).clip(-1,1).shift(1).fillna(0.0)
    cost = sig.diff().abs().fillna(0.0)*(fee/10000.0)
    return sig, sig*ret - cost

def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not CACHE.exists():
        print("No cache yet, exiting"); return
    with open(CACHE,"rb") as f: ohlc = pickle.load(f)
    print(f"[DEEP] Loaded {len(ohlc)} pairs")

    # ---- Phase 7: Per-pair champion ----
    print("\n=== PHASE 7: PER-PAIR CHAMPION (best strat-algo per asset, 25bps) ===")
    rows = []
    for pair, df in ohlc.items():
        best = None
        for s_name, s_fn in ALL_STRATS.items():
            for a_name, a_fn in ALGOS.items():
                try:
                    _, net = run_pair(s_name, s_fn, a_name, a_fn, df)
                    if len(net) < 50 or net.std() == 0: continue
                    sh = float(net.mean()/net.std()*ANNUAL_HOURLY)
                    cum = float((1+net).prod()-1)
                    if best is None or sh > best[0]:
                        best = (sh, s_name, a_name, cum, float((net>0).sum()/max(1,(net!=0).sum())))
                except Exception: continue
        if best:
            rows.append({"pair":pair,"sharpe":round(best[0],3),"strategy":best[1],"algo":best[2],"cum":round(best[3],4),"win":round(best[4],4)})
    df7 = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
    df7.to_csv(OUT/"mega_phase7_per_pair.csv", index=False)
    print(df7.to_string(index=False))

    # ---- Phase 9: Correlation matrix among top 10 strategies (signal level) ----
    print("\n=== PHASE 9: STRATEGY CORRELATION MATRIX (top combos by phase1) ===")
    try:
        p1 = pd.read_csv(OUT/"mega_phase1_fees.csv")
        top10 = p1[p1.fee_bps==25].head(10)[["strategy","algo"]].values.tolist()
    except Exception:
        top10 = list(itertools.product(list(ALL_STRATS.keys())[:5], list(ALGOS.keys())[:2]))
    series_map = {}
    for s_name, a_name in top10:
        s_fn = ALL_STRATS[s_name]; a_fn = ALGOS[a_name]
        nets = []
        for pair, df in ohlc.items():
            try:
                _, net = run_pair(s_name, s_fn, a_name, a_fn, df)
                if len(net)>=50 and net.std()>0: nets.append(net.values)
            except Exception: pass
        if nets:
            min_len = min(len(x) for x in nets)
            mat = np.vstack([x[-min_len:] for x in nets])
            series_map[f"{s_name}|{a_name}"] = mat.mean(axis=0)  # mean across pairs
    if series_map:
        min_len = min(len(v) for v in series_map.values())
        df_sigs = pd.DataFrame({k: v[-min_len:] for k,v in series_map.items()})
        corr = df_sigs.corr().round(3)
        corr.to_csv(OUT/"mega_phase9_correlation.csv")
        print(corr.to_string())

    # ---- Phase 8: Sharpe-weighted multi-strategy portfolio ----
    print("\n=== PHASE 8: SHARPE-WEIGHTED ENSEMBLE PORTFOLIO ===")
    try:
        p1 = pd.read_csv(OUT/"mega_phase1_fees.csv")
        top = p1[p1.fee_bps==25].head(8)[["strategy","algo","sharpe"]].values.tolist()
    except Exception: top = []
    if top:
        rows = []
        # build per-pair pooled signal weighted by sharpe
        all_nets = []
        weights = np.array([max(0.0, t[2]) for t in top])
        weights = weights / weights.sum()
        for pair, df in ohlc.items():
            close = df["c"].astype(float); ret = close.pct_change().fillna(0.0)
            sig_combined = pd.Series(0.0, index=ret.index)
            for (s_name, a_name, _sh), w in zip(top, weights):
                s_fn = ALL_STRATS[s_name]; a_fn = ALGOS[a_name]
                sig_raw = get_signal(s_name, s_fn, close, ret)
                sig = a_fn(sig_raw, ret).reindex(ret.index).fillna(0.0).clip(-1,1)
                sig_combined = sig_combined + sig * w
            sig_combined = sig_combined.clip(-1,1).shift(1).fillna(0.0)
            net = sig_combined*ret - sig_combined.diff().abs().fillna(0.0)*(25/10000.0)
            all_nets.append(net)
        pooled = pd.concat(all_nets, axis=0)
        sh = float(pooled.mean()/pooled.std()*ANNUAL_HOURLY) if pooled.std()>0 else 0
        cum = float((1+pooled).prod()-1)
        win = float((pooled>0).sum()/max(1,(pooled!=0).sum()))
        print(f"  Sharpe-weighted top-8 portfolio: sharpe={sh:.3f}  cum={cum*100:.2f}%  win={win*100:.1f}%")
        with open(OUT/"mega_phase8_portfolio.json","w") as f:
            json.dump({"members":top,"weights":weights.tolist(),"sharpe":sh,"cum":cum,"win":win}, f, indent=2)

    # ---- Phase 10: Inversion test on bottom strategies ----
    print("\n=== PHASE 10: INVERSION TEST (flip sign on bottom strats) ===")
    try:
        p1 = pd.read_csv(OUT/"mega_phase1_fees.csv")
        bot = p1[p1.fee_bps==25].tail(8)[["strategy","algo"]].values.tolist()
    except Exception: bot = []
    rows = []
    for s_name, a_name in bot:
        s_fn = ALL_STRATS[s_name]; a_fn = ALGOS[a_name]
        nets = []
        for pair, df in ohlc.items():
            try:
                _, net = run_pair(s_name, s_fn, a_name, a_fn, df)
                if len(net)>=50:
                    inv = -net  # but we actually need to flip signal then redo with cost. Approximation.
                    # Proper: rerun with -1*signal
                    close = df["c"].astype(float); ret = close.pct_change().fillna(0.0)
                    sig_raw = get_signal(s_name, s_fn, close, ret)
                    sig = -a_fn(sig_raw, ret).reindex(ret.index).fillna(0.0).clip(-1,1).shift(1).fillna(0.0)
                    cost = sig.diff().abs().fillna(0.0)*(25/10000.0)
                    inv_net = sig*ret - cost
                    if inv_net.std()>0: nets.append(inv_net)
            except Exception: continue
        if not nets: continue
        pooled = pd.concat(nets, axis=0)
        sh = float(pooled.mean()/pooled.std()*ANNUAL_HOURLY)
        cum = float((1+pooled).prod()-1)
        win = float((pooled>0).sum()/max(1,(pooled!=0).sum()))
        rows.append({"strategy_INVERTED":s_name,"algo":a_name,"sharpe_inv":round(sh,3),"cum_inv":round(cum,4),"win_inv":round(win,4)})
    if rows:
        df10 = pd.DataFrame(rows).sort_values("sharpe_inv", ascending=False)
        df10.to_csv(OUT/"mega_phase10_inversion.csv", index=False)
        print(df10.to_string(index=False))

    print("\n[DEEP DONE]")

if __name__ == "__main__":
    main()
