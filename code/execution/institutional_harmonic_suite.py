import os
import json
import math
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_DIR = ROOT / "out" / "execution"
DATA_DIR = ROOT / "data"
LEGACY_DATA_DIR = Path(r"C:\LumaTrader\data")

ANNUALIZATION = 252.0
MIN_SERIES_LEN = 120
MIN_RET_LEN = 40
TRAIN_RATIO = 0.70


def _to_series(x, index=None) -> pd.Series:
    if isinstance(x, pd.Series):
        s = x.copy()
    else:
        s = pd.Series(x)
    s = pd.to_numeric(s, errors="coerce")
    if index is not None:
        s = pd.Series(s.values, index=index)
    return s.fillna(0.0)


def sharpe(returns):
    r = _to_series(returns).dropna()
    if len(r) < 2:
        return 0.0
    s = float(r.std(ddof=0))
    if s <= 1e-12:
        return 0.0
    return float((r.mean() / s) * np.sqrt(ANNUALIZATION))


def max_drawdown(equity):
    eq = _to_series(equity).dropna()
    if len(eq) == 0:
        return 0.0
    peak = eq.cummax()
    dd = (eq / peak) - 1.0
    return float(dd.min())


def cagr(equity):
    eq = _to_series(equity).dropna()
    if len(eq) < 2:
        return 0.0
    start = float(eq.iloc[0])
    end = float(eq.iloc[-1])
    if start <= 0 or end <= 0:
        return 0.0
    years = len(eq) / ANNUALIZATION
    if years <= 0:
        return 0.0
    return float((end / start) ** (1.0 / years) - 1.0)


def calmar(equity):
    dd = abs(max_drawdown(equity))
    if dd <= 1e-12:
        return 0.0
    return float(cagr(equity) / dd)


def win_rate(returns):
    r = _to_series(returns).dropna()
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())


def expectancy(returns):
    r = _to_series(returns).dropna()
    if len(r) == 0:
        return 0.0
    wins = r[r > 0]
    losses = r[r < 0]
    pw = float((r > 0).mean())
    pl = float((r < 0).mean())
    aw = float(wins.mean()) if len(wins) else 0.0
    al = float(losses.mean()) if len(losses) else 0.0
    return float((pw * aw) + (pl * al))


def annual_vol(returns):
    r = _to_series(returns).dropna()
    if len(r) < 2:
        return 0.0
    return float(r.std(ddof=0) * np.sqrt(ANNUALIZATION))


def stability_score(equity):
    eq = _to_series(equity).dropna()
    if len(eq) < 10:
        return 0.0
    x = np.arange(len(eq), dtype=float)
    y = np.log(eq.clip(lower=1e-9).values)
    if len(np.unique(y)) < 2:
        return 0.0
    corr = np.corrcoef(x, y)[0, 1]
    if np.isnan(corr):
        return 0.0
    return float(max(corr, 0.0))


def _px_from_ret(ret) -> pd.Series:
    r = _to_series(ret)
    return (1.0 + r).cumprod()


def robust_zscore(x, win: int = 20) -> pd.Series:
    s = _to_series(x)
    minp = max(5, win // 2)
    med = s.rolling(win, min_periods=minp).median()
    mad = (s - med).abs().rolling(win, min_periods=minp).median()
    z = (s - med) / (1.4826 * mad + 1e-9)
    return z.replace([np.inf, -np.inf], 0.0).fillna(0.0).clip(-5.0, 5.0)


def bounded_weight(x, lo: float = 0.25, hi: float = 1.75) -> pd.Series:
    s = _to_series(x).replace([np.inf, -np.inf], 1.0).fillna(1.0)
    return s.clip(lo, hi)


def smooth_signal(x, span: int = 5) -> pd.Series:
    return _to_series(x).ewm(span=span, adjust=False).mean().fillna(0.0).clip(-1.0, 1.0)


def safe_flow(x, index=None):
    s = _to_series(x, index=index).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    return s.clip(0.25, 1.75)


def test_vs_baseline(te_eq, te_base_eq):
    if len(te_eq) == 0 or len(te_base_eq) == 0:
        return 0.0
    base = max(float(te_base_eq.iloc[-1]), 1e-9)
    return float((float(te_eq.iloc[-1]) / base) - 1.0)


def walk_forward_metrics(ret, flow_fn, strat_fn, algo_fn, folds: int = 5):
    r = _to_series(ret).dropna().reset_index(drop=True)
    if len(r) < max(120, folds * 30):
        return {
            "wf_sharpe_mean": 0.0,
            "wf_sharpe_std": 0.0,
            "wf_win_rate_mean": 0.0,
            "wf_calmar_mean": 0.0,
            "wf_stability": 0.0,
        }

    step = len(r) // (folds + 1)
    wf_sharpes = []
    wf_win_rates = []
    wf_calmars = []

    for i in range(1, folds + 1):
        train_end = i * step
        test_end = min((i + 1) * step, len(r))
        tr = r.iloc[:train_end]
        te = r.iloc[train_end:test_end]
        if len(tr) < MIN_RET_LEN or len(te) < MIN_RET_LEN:
            continue

        te_flow = safe_flow(flow_fn(te), index=te.index)
        te_signal_raw = _to_series(strat_fn(te), index=te.index).fillna(0.0).clip(-1.0, 1.0)
        te_signal = _to_series(algo_fn(te_signal_raw, te), index=te.index).fillna(0.0).clip(-1.0, 1.0)
        te_ret = (te_signal * te * te_flow).clip(-0.10, 0.10)
        te_eq = (1.0 + te_ret).cumprod()

        wf_sharpes.append(sharpe(te_ret))
        wf_win_rates.append(win_rate(te_ret))
        wf_calmars.append(calmar(te_eq))

    if len(wf_sharpes) == 0:
        return {
            "wf_sharpe_mean": 0.0,
            "wf_sharpe_std": 0.0,
            "wf_win_rate_mean": 0.0,
            "wf_calmar_mean": 0.0,
            "wf_stability": 0.0,
        }

    wf_sharpes_s = pd.Series(wf_sharpes)
    wf_stability = 1.0 / (1.0 + float(wf_sharpes_s.std(ddof=0)))
    return {
        "wf_sharpe_mean": float(wf_sharpes_s.mean()),
        "wf_sharpe_std": float(wf_sharpes_s.std(ddof=0)),
        "wf_win_rate_mean": float(pd.Series(wf_win_rates).mean()),
        "wf_calmar_mean": float(pd.Series(wf_calmars).mean()),
        "wf_stability": float(np.clip(wf_stability, 0.0, 1.0)),
    }


def quality_score(metrics):
    return float(
        (float(np.clip(metrics["test_sharpe"], -4.0, 4.0)) * 4.0)
        + (float(np.clip(metrics.get("wf_sharpe_mean", 0.0), -4.0, 4.0)) * 1.6)
        + (float(np.clip(metrics["test_calmar"], -4.0, 4.0)) * 2.0)
        + (float(np.clip(metrics.get("wf_calmar_mean", 0.0), -4.0, 4.0)) * 1.0)
        + (float(np.clip(metrics["test_expectancy"], -0.03, 0.03)) * 200.0)
        + (float(np.clip(metrics["test_win_rate"], 0.0, 1.0)) * 2.0)
        + (float(np.clip(metrics.get("wf_win_rate_mean", 0.0), 0.0, 1.0)) * 1.0)
    )


def resilience_score(metrics):
    return float(
        (float(np.clip(metrics["stability"], 0.0, 1.0)) * 2.0)
        + (float(np.clip(metrics.get("wf_stability", 0.0), 0.0, 1.0)) * 2.0)
        - (abs(float(np.clip(metrics["test_max_dd"], -1.0, 0.0))) * 6.0)
        - (float(np.clip(metrics["test_vol"], 0.0, 5.0)) * 0.6)
        - (float(np.clip(metrics["train_test_gap"], 0.0, 6.0)) * 0.8)
        - (float(np.clip(metrics.get("wf_sharpe_std", 0.0), 0.0, 5.0)) * 0.8)
    )


def deployment_score(metrics):
    return float(
        (float(np.clip(metrics["test_vs_baseline"], -3.0, 3.0)) * 3.0)
        + (float(np.clip(metrics["train_sharpe"], -4.0, 4.0)) * 0.5)
        + (float(np.clip(metrics["test_final"], 0.0, 5.0)) * 0.5)
        + (float(np.clip(metrics.get("wf_sharpe_mean", 0.0), -4.0, 4.0)) * 0.5)
    )


def institutional_score(metrics):
    return float(
        quality_score(metrics)
        + resilience_score(metrics)
        + deployment_score(metrics)
    )


# -----------------------------
# FLOWFORMS (Geometry)
# -----------------------------
def ff_identity(ret):
    ret = _to_series(ret)
    return pd.Series(1.0, index=ret.index)


def ff_golden_ratio(ret):
    ret = _to_series(ret)
    return pd.Series(1.25, index=ret.index)


def ff_fibonacci(ret):
    ret = _to_series(ret)
    fib = np.array([1, 1, 2, 3, 5, 8, 13, 21], dtype=float)
    vals = np.resize(fib / fib.mean(), len(ret))
    return bounded_weight(pd.Series(vals, index=ret.index), 0.60, 1.40)


def ff_log_spiral(ret):
    ret = _to_series(ret)
    x = np.arange(len(ret), dtype=float)
    vals = np.exp(0.001 * x)
    vals = vals / np.maximum(np.mean(vals), 1e-9)
    return bounded_weight(pd.Series(vals, index=ret.index), 0.85, 1.15)


def ff_archimedean_spiral(ret):
    ret = _to_series(ret)
    x = np.arange(len(ret), dtype=float)
    vals = 0.90 + 0.10 * (x / max(len(ret), 1))
    return bounded_weight(pd.Series(vals, index=ret.index), 0.85, 1.10)


def ff_helix(ret):
    ret = _to_series(ret)
    x = np.linspace(0, 8 * np.pi, len(ret))
    vals = 1.0 + 0.15 * np.sin(x)
    return bounded_weight(pd.Series(vals, index=ret.index), 0.80, 1.20)


def ff_gaussian(ret):
    ret = _to_series(ret)
    z = robust_zscore(ret, 20)
    vals = np.exp(-0.5 * (z ** 2))
    vals = vals / np.maximum(vals.mean(), 1e-9)
    return bounded_weight(pd.Series(vals, index=ret.index), 0.60, 1.40)


def ff_vol_target(ret):
    ret = _to_series(ret)
    rv = ret.rolling(20, min_periods=10).std()
    target = rv.rolling(60, min_periods=20).median()
    vals = target / (rv + 1e-9)
    return bounded_weight(vals.fillna(1.0), 0.60, 1.40)


def ff_regime_strength(ret):
    ret = _to_series(ret)
    px = _px_from_ret(ret)
    trend = (px.ewm(span=10, adjust=False).mean() - px.ewm(span=30, adjust=False).mean()).abs() / (px + 1e-9)
    vol = ret.rolling(20, min_periods=10).std()
    vals = 1.0 + (trend / (vol + 1e-9))
    return bounded_weight(vals.fillna(1.0), 0.70, 1.50)


def ff_drawdown_guard(ret):
    ret = _to_series(ret)
    eq = _px_from_ret(ret)
    dd = (eq / eq.cummax()) - 1.0
    vals = 1.0 + dd
    return bounded_weight(vals.fillna(1.0), 0.30, 1.00)


def ff_range_compression(ret):
    ret = _to_series(ret)
    px = _px_from_ret(ret)
    width = (px.rolling(20, min_periods=10).max() - px.rolling(20, min_periods=10).min()) / (px + 1e-9)
    med = width.rolling(60, min_periods=20).median()
    vals = med / (width + 1e-9)
    return bounded_weight(vals.fillna(1.0), 0.70, 1.30)


def ff_autocorr_weight(ret):
    ret = _to_series(ret)
    ac = ret.rolling(20, min_periods=10).corr(ret.shift(1)).fillna(0.0)
    vals = 1.0 + 0.25 * ac
    return bounded_weight(vals, 0.75, 1.25)


GEOMETRY_FLOWFORMS = {
    "geom_identity": ff_identity,
    "geom_golden_ratio": ff_golden_ratio,
    "geom_fibonacci": ff_fibonacci,
    "geom_log_spiral": ff_log_spiral,
    "geom_archimedean_spiral": ff_archimedean_spiral,
    "geom_helix": ff_helix,
    "geom_gaussian": ff_gaussian,
}

SIGNAL_FLOWFORMS = {
    "sig_vol_target": ff_vol_target,
    "sig_regime_strength": ff_regime_strength,
    "sig_drawdown_guard": ff_drawdown_guard,
    "sig_range_compression": ff_range_compression,
    "sig_autocorr_weight": ff_autocorr_weight,
    "sig_gaussian_filter": ff_gaussian,
}

UNSAFE_FLOWFORMS: frozenset = frozenset()

FLOWFORMS = {**GEOMETRY_FLOWFORMS, **SIGNAL_FLOWFORMS}
FLOWFORMS = {k: v for k, v in FLOWFORMS.items() if k not in UNSAFE_FLOWFORMS}


# -----------------------------
# STRATEGIES
# -----------------------------
def strat_trend(ret):
    ret = _to_series(ret)
    fast = ret.rolling(5).mean()
    slow = ret.rolling(20).mean()
    sig = np.where(fast > slow, 1.0, -1.0)
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_mean_revert(ret):
    ret = _to_series(ret)
    z = (ret - ret.rolling(20).mean()) / (ret.rolling(20).std() + 1e-9)
    sig = np.where(z < -1.0, 1.0, np.where(z > 1.0, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_breakout(ret):
    ret = _to_series(ret)
    hi = ret.rolling(20).max()
    lo = ret.rolling(20).min()
    sig = np.where(ret >= hi, 1.0, np.where(ret <= lo, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_regime_switch(ret):
    ret = _to_series(ret)
    fast_vol = ret.rolling(5).std()
    slow_vol = ret.rolling(20).std()
    trend = strat_trend(ret)
    mr = strat_mean_revert(ret)
    sig = np.where(fast_vol > slow_vol, trend, mr)
    return pd.Series(sig, index=ret.index).fillna(0.0)


def strat_harmonic_blend(ret):
    ret = _to_series(ret)
    a = strat_trend(ret)
    b = strat_mean_revert(ret)
    c = strat_breakout(ret)
    return pd.Series(np.sign(a + b + c), index=ret.index).fillna(0.0)


# -----------------------------
# STRATEGIES (Robust, deployable)
# -----------------------------
def strat_trend_ema(ret):
    ret = _to_series(ret)
    px = _px_from_ret(ret)
    fast = px.ewm(span=10, adjust=False).mean()
    slow = px.ewm(span=30, adjust=False).mean()
    sig = np.sign(fast - slow)
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0).clip(-1.0, 1.0)


def strat_mean_revert_robust(ret):
    ret = _to_series(ret)
    z = robust_zscore(ret, 20)
    sig = np.where(z < -1.25, 1.0, np.where(z > 1.25, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_breakout_donchian(ret):
    ret = _to_series(ret)
    px = _px_from_ret(ret)
    hi = px.rolling(20, min_periods=10).max()
    lo = px.rolling(20, min_periods=10).min()
    sig = np.where(px >= hi, 1.0, np.where(px <= lo, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_pullback_trend(ret):
    ret = _to_series(ret)
    px = _px_from_ret(ret)
    fast = px.ewm(span=10, adjust=False).mean()
    slow = px.ewm(span=30, adjust=False).mean()
    z = robust_zscore(ret, 15)
    long_sig = (fast > slow) & (z < -0.75)
    short_sig = (fast < slow) & (z > 0.75)
    sig = np.where(long_sig, 1.0, np.where(short_sig, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_vol_expansion_breakout(ret):
    ret = _to_series(ret)
    px = _px_from_ret(ret)
    breakout = strat_breakout_donchian(ret)
    fast_vol = ret.rolling(5, min_periods=3).std()
    slow_vol = ret.rolling(20, min_periods=10).std()
    gate = np.where(fast_vol > slow_vol, 1.0, 0.0)
    sig = _to_series(breakout, index=ret.index) * _to_series(gate, index=ret.index)
    return sig.shift(1).fillna(0.0).clip(-1.0, 1.0)


def strat_regime_switch(ret):
    ret = _to_series(ret)
    px = _px_from_ret(ret)
    trend_strength = ((px.ewm(span=10, adjust=False).mean() - px.ewm(span=30, adjust=False).mean()).abs() / (px + 1e-9)).fillna(0.0)
    vol = ret.rolling(20, min_periods=10).std().fillna(0.0)
    use_trend = trend_strength > vol
    trend_sig = strat_trend_ema(ret)
    mr_sig = strat_mean_revert_robust(ret)
    sig = np.where(use_trend, trend_sig, mr_sig)
    return pd.Series(sig, index=ret.index).fillna(0.0).clip(-1.0, 1.0)


def strat_harmonic_blend(ret):
    ret = _to_series(ret)
    a = strat_trend_ema(ret)
    b = strat_mean_revert_robust(ret)
    c = strat_breakout_donchian(ret)
    d = strat_pullback_trend(ret)
    sig = np.sign((a * 0.35) + (b * 0.20) + (c * 0.30) + (d * 0.15))
    return pd.Series(sig, index=ret.index).fillna(0.0)


STRATEGIES = {
    "trend_ema": strat_trend_ema,
    "mean_revert_robust": strat_mean_revert_robust,
    "breakout_donchian": strat_breakout_donchian,
    "pullback_trend": strat_pullback_trend,
    "vol_expansion_breakout": strat_vol_expansion_breakout,
    "regime_switch": strat_regime_switch,
    "harmonic_blend": strat_harmonic_blend,
}

# -----------------------------
# ALGORITHMS (Signal execution logic)
# -----------------------------
def algo_direct(signal, ret):
    return smooth_signal(signal, span=3)


def algo_confidence_weighted(signal, ret):
    s = smooth_signal(signal, span=3)
    conf = 1.0 - (robust_zscore(ret, 20).abs() / 5.0)
    return (s * conf.clip(0.25, 1.0)).clip(-1.0, 1.0)


def algo_persistence_filter(signal, ret):
    s = smooth_signal(signal, span=4)
    conf = s.abs().rolling(3, min_periods=1).mean()
    out = np.where(conf >= 0.35, np.sign(s), 0.0)
    return pd.Series(out, index=_to_series(signal).index).clip(-1.0, 1.0)


def algo_consensus_filter(signal, ret):
    s = smooth_signal(signal, span=5)
    px = _px_from_ret(ret)
    trend = np.sign(px.ewm(span=10, adjust=False).mean() - px.ewm(span=30, adjust=False).mean())
    out = np.where(np.sign(s) == np.sign(trend), s, 0.0)
    return pd.Series(out, index=_to_series(signal).index).fillna(0.0).clip(-1.0, 1.0)


ALGOS = {
    "direct": algo_direct,
    "confidence_weighted": algo_confidence_weighted,
    "persistence_filter": algo_persistence_filter,
    "consensus_filter": algo_consensus_filter,
}

def get_price_series(df):
    cols_lower = {c.lower(): c for c in df.columns}
    for p in ["close", "price", "last", "c"]:
        if p in cols_lower:
            s = pd.to_numeric(df[cols_lower[p]], errors="coerce").dropna()
            if len(s) > 0:
                return s.reset_index(drop=True)

    numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
    if len(numeric_cols) == 0:
        return None
    s = pd.to_numeric(df[numeric_cols[-1]], errors="coerce").dropna()
    if len(s) == 0:
        return None
    return s.reset_index(drop=True)


def evaluate_combo(series, flow_name, flow_fn, strat_name, strat_fn, algo_name, algo_fn):
    px = pd.to_numeric(series, errors="coerce").dropna().reset_index(drop=True)
    if len(px) < MIN_SERIES_LEN:
        return None

    ret = px.pct_change().dropna()
    if len(ret) < MIN_RET_LEN:
        return None

    split = int(len(ret) * TRAIN_RATIO)
    tr_ret = ret.iloc[:split].copy()
    te_ret = ret.iloc[split:].copy()
    if len(tr_ret) < MIN_RET_LEN or len(te_ret) < MIN_RET_LEN:
        return None

    tr_flow = safe_flow(flow_fn(tr_ret), index=tr_ret.index)
    te_flow = safe_flow(flow_fn(te_ret), index=te_ret.index)

    tr_signal_raw = _to_series(strat_fn(tr_ret), index=tr_ret.index).fillna(0.0).clip(-1.0, 1.0)
    te_signal_raw = _to_series(strat_fn(te_ret), index=te_ret.index).fillna(0.0).clip(-1.0, 1.0)

    tr_signal = _to_series(algo_fn(tr_signal_raw, tr_ret), index=tr_ret.index).fillna(0.0).clip(-1.0, 1.0)
    te_signal = _to_series(algo_fn(te_signal_raw, te_ret), index=te_ret.index).fillna(0.0).clip(-1.0, 1.0)

    tr_strat_ret = (tr_signal * tr_ret * tr_flow).clip(-0.10, 0.10)
    te_strat_ret = (te_signal * te_ret * te_flow).clip(-0.10, 0.10)

    tr_eq = (1.0 + tr_strat_ret).cumprod()
    te_eq = (1.0 + te_strat_ret).cumprod()
    te_base_eq = (1.0 + te_ret).cumprod()

    metrics = {
        "flow": flow_name,
        "strategy": strat_name,
        "algo": algo_name,
        "train_sharpe": sharpe(tr_strat_ret),
        "test_sharpe": sharpe(te_strat_ret),
        "train_max_dd": max_drawdown(tr_eq),
        "test_max_dd": max_drawdown(te_eq),
        "train_cagr": cagr(tr_eq),
        "test_cagr": cagr(te_eq),
        "train_calmar": calmar(tr_eq),
        "test_calmar": calmar(te_eq),
        "test_win_rate": win_rate(te_strat_ret),
        "test_expectancy": expectancy(te_strat_ret),
        "test_vol": annual_vol(te_strat_ret),
        "test_final": float(te_eq.iloc[-1]) if len(te_eq) else 0.0,
        "baseline_final": float(te_base_eq.iloc[-1]) if len(te_base_eq) else 0.0,
        "test_vs_baseline": test_vs_baseline(te_eq, te_base_eq),
        "stability": stability_score(te_eq),
    }
    metrics.update(walk_forward_metrics(ret, flow_fn, strat_fn, algo_fn, folds=5))
    metrics["train_test_gap"] = abs(float(metrics["train_sharpe"]) - float(metrics["test_sharpe"]))
    metrics["quality_score"] = quality_score(metrics)
    metrics["resilience_score"] = resilience_score(metrics)
    metrics["deployment_score"] = deployment_score(metrics)
    metrics["institutional_score"] = institutional_score(metrics)
    return metrics


def run_engine(files):
    results = []

    for f in files:
        try:
            df = pd.read_csv(f)
            series = get_price_series(df)
            if series is None:
                continue

            for flow_name, flow_fn in FLOWFORMS.items():
                for strat_name, strat_fn in STRATEGIES.items():
                    for algo_name, algo_fn in ALGOS.items():
                        row = evaluate_combo(series, flow_name, flow_fn, strat_name, strat_fn, algo_name, algo_fn)
                        if row is not None:
                            row["file"] = str(f)
                            results.append(row)
        except Exception as e:
            print(f"Error with {f}: {e}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not results:
        print("NO VALID INSTITUTIONAL STRATEGIES")
        return

    out_df = pd.DataFrame(results).sort_values(
        ["institutional_score", "test_sharpe", "test_vs_baseline"],
        ascending=False
    )

    leaderboard_path = OUT_DIR / "institutional_leaderboard.csv"
    champs_path = OUT_DIR / "institutional_flow_strategy_champions.csv"
    family_path = OUT_DIR / "institutional_champion_families.csv"
    lineage_path = OUT_DIR / "institutional_champion_lineages.json"
    top10_path = OUT_DIR / "institutional_top10.csv"
    summary_path = OUT_DIR / "institutional_summary.json"
    selection_path = OUT_DIR / "institutional_live_selection.json"

    out_df.to_csv(leaderboard_path, index=False)
    (
        out_df.groupby(["flow", "strategy", "algo"], as_index=False)
        .first()
        .sort_values(["institutional_score", "test_sharpe"], ascending=False)
        .to_csv(champs_path, index=False)
    )
    family_df = (
        out_df.groupby(["flow", "strategy"], as_index=False)
        .agg(
            family_candidates=("institutional_score", "count"),
            family_mean_score=("institutional_score", "mean"),
            family_max_score=("institutional_score", "max"),
            family_mean_wf_sharpe=("wf_sharpe_mean", "mean"),
            family_mean_wf_stability=("wf_stability", "mean"),
        )
        .sort_values(["family_max_score", "family_mean_score"], ascending=False)
    )
    family_df.to_csv(family_path, index=False)

    champions_df = out_df.groupby(["flow", "strategy", "algo"], as_index=False).first()
    lineage = {
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "top_lineages": champions_df.head(50).to_dict(orient="records"),
        "family_summary_top20": family_df.head(20).to_dict(orient="records"),
    }
    with open(lineage_path, "w", encoding="utf-8") as fp:
        json.dump(lineage, fp, indent=2)

    out_df.head(10).to_csv(top10_path, index=False)

    top = out_df.iloc[0]
    summary = {
        "files_scanned": int(len(files)),
        "total_candidates": int(len(out_df)),
        "top_file": str(top["file"]),
        "top_flow": str(top["flow"]),
        "top_strategy": str(top["strategy"]),
        "top_algo": str(top["algo"]),
        "top_test_sharpe": float(top["test_sharpe"]),
        "top_test_vs_baseline": float(top["test_vs_baseline"]),
        "top_institutional_score": float(top["institutional_score"]),
        "top_wf_sharpe_mean": float(top.get("wf_sharpe_mean", 0.0)),
        "top_wf_stability": float(top.get("wf_stability", 0.0)),
    }
    with open(summary_path, "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    edge_multiplier = float(np.clip(1.0 + (float(top["institutional_score"]) / 100.0), 0.70, 1.30))
    selection = {
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "flow": str(top["flow"]),
        "strategy": str(top["strategy"]),
        "algo": str(top["algo"]),
        "institutional_score": float(top["institutional_score"]),
        "test_sharpe": float(top["test_sharpe"]),
        "test_vs_baseline": float(top["test_vs_baseline"]),
        "wf_sharpe_mean": float(top.get("wf_sharpe_mean", 0.0)),
        "wf_stability": float(top.get("wf_stability", 0.0)),
        "edge_multiplier": edge_multiplier,
    }
    with open(selection_path, "w", encoding="utf-8") as fp:
        json.dump(selection, fp, indent=2)

    print(top10_path)
    print("\n=== TOP 10 RESULTS ===")
    print(out_df.head(10).to_string(index=False))
    print("\nSaved:")
    print(leaderboard_path)
    print(champs_path)
    print(family_path)
    print(lineage_path)
    print(top10_path)
    print(summary_path)


if __name__ == "__main__":
    data_root = DATA_DIR if DATA_DIR.exists() else LEGACY_DATA_DIR
    data_root.mkdir(parents=True, exist_ok=True)

    files = [p for p in data_root.iterdir() if p.suffix.lower() == ".csv"]
    run_engine(files)