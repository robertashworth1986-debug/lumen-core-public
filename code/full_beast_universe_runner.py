import os
import re
import sys
import json
import math
import inspect
import hashlib
import importlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
OUT  = ROOT / "out"
DATA_ROOTS = [
    Path(r"C:\LumaTrader\data"),
    ROOT / "data",
]

ANNUALIZATION = 252.0
MIN_SERIES_LEN = 120
MIN_RET_LEN = 40
TRAIN_RATIO = 0.70
SEED = 42

rng = np.random.default_rng(SEED)

# =========================================
# UTILS
# =========================================
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def safe_read_csv(path: Path) -> pd.DataFrame:
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1"]
    seps = [",", ";", "\t", "|"]
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep)
                if df is not None and len(df.columns) >= 1:
                    return df
            except Exception:
                pass
    return pd.DataFrame()

def clean_numeric_series(s: pd.Series) -> pd.Series:
    if s is None or len(s) == 0:
        return pd.Series(dtype=float)
    x = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    return x.astype(float)

def normalize_series(s: pd.Series) -> pd.Series:
    s = pd.Series(s).astype(float).replace([np.inf, -np.inf], np.nan)
    s = s.ffill().bfill()
    if len(s) == 0:
        return s
    m = float(np.nanmean(np.abs(s.values)))
    if not np.isfinite(m) or m <= 1e-12:
        return pd.Series(np.ones(len(s)), index=s.index, dtype=float)
    return s / m

def pick_time_and_value_cols(df: pd.DataFrame):
    cols = list(df.columns)
    lowered = {c: str(c).strip().lower() for c in cols}

    time_candidates = [
        "timestamp", "time", "date", "datetime", "open_time", "close_time",
        "period", "month", "year", "day", "week", "ds"
    ]
    value_candidates = [
        "close", "price", "value", "open", "last", "adj close", "adj_close",
        "settle", "mid", "nav", "index", "level", "rate", "yield", "spread",
        "volume", "load", "demand", "forecast", "generation", "usage",
        "prior_hour_demand_mwh", "demand_forecast_mwh", "mwh", "mw",
        "unrate", "cpi", "dgs10", "capacity", "outage", "signal", "score"
    ]

    time_col = None
    for c in cols:
        lc = lowered[c]
        if lc in time_candidates or any(tok in lc for tok in time_candidates):
            time_col = c
            break

    value_col = None
    scored = []
    for c in cols:
        lc = lowered[c]
        sc = 0
        if lc in value_candidates:
            sc += 100
        for tok in value_candidates:
            if tok in lc:
                sc += 10
        numeric_ratio = pd.to_numeric(df[c], errors="coerce").notna().mean()
        sc += numeric_ratio * 20
        scored.append((sc, c))
    scored.sort(reverse=True)
    if scored:
        value_col = scored[0][1]

    if value_col is None:
        return time_col, None

    return time_col, value_col

def to_returns(series: pd.Series) -> pd.Series:
    s = clean_numeric_series(series)
    if len(s) < MIN_SERIES_LEN:
        return pd.Series(dtype=float)
    if (s > 0).mean() > 0.80:
        r = s.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    else:
        r = s.diff().replace([np.inf, -np.inf], np.nan).dropna()
        scale = float(r.abs().mean()) if len(r) else 0.0
        if scale > 1e-12:
            r = r / scale
    r = r.clip(lower=r.quantile(0.01), upper=r.quantile(0.99))
    return r.dropna()

def split_train_test(r: pd.Series):
    if len(r) < MIN_RET_LEN:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    n = max(int(len(r) * TRAIN_RATIO), 20)
    n = min(n, len(r) - 10)
    return r.iloc[:n].copy(), r.iloc[n:].copy()

# =========================================
# METRICS
# =========================================
def sharpe(returns):
    r = pd.Series(returns).dropna()
    if len(r) < 2:
        return 0.0
    s = float(r.std(ddof=0))
    if s <= 1e-12:
        return 0.0
    return float((r.mean() / s) * np.sqrt(ANNUALIZATION))

def max_drawdown(equity):
    eq = pd.Series(equity).dropna()
    if len(eq) == 0:
        return 0.0
    peak = eq.cummax()
    dd = (eq / peak) - 1.0
    return float(dd.min())

def cagr(equity):
    eq = pd.Series(equity).dropna()
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
    r = pd.Series(returns).dropna()
    if len(r) == 0:
        return 0.0
    return float((r > 0).mean())

def expectancy(returns):
    r = pd.Series(returns).dropna()
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
    r = pd.Series(returns).dropna()
    if len(r) < 2:
        return 0.0
    return float(r.std(ddof=0) * np.sqrt(ANNUALIZATION))

def stability_score(equity):
    eq = pd.Series(equity).dropna()
    if len(eq) < 10:
        return 0.0
    x = np.arange(len(eq), dtype=float)
    y = np.log(eq.clip(lower=1e-9).values)
    if len(np.unique(y)) < 2:
        return 0.0
    corr = np.corrcoef(x, y)[0, 1]
    if np.isnan(corr):
        return 0.0
    return float(corr)

def make_equity(strategy_returns):
    r = pd.Series(strategy_returns).fillna(0.0).astype(float)
    return (1.0 + r).cumprod()

# =========================================
# DEFAULT METRIC PROFILES
# =========================================
METRIC_PROFILES = {
    "institutional": {
        "test_sharpe": 4.0,
        "test_calmar": 2.0,
        "test_expectancy": 150.0,
        "test_win_rate": 2.0,
        "stability": 1.5,
        "test_vs_baseline": 3.0,
        "test_max_dd_penalty": 5.0,
        "test_vol_penalty": 0.5,
    },
    "defensive": {
        "test_sharpe": 3.0,
        "test_calmar": 3.0,
        "test_expectancy": 100.0,
        "test_win_rate": 1.0,
        "stability": 2.0,
        "test_vs_baseline": 2.0,
        "test_max_dd_penalty": 8.0,
        "test_vol_penalty": 1.0,
    },
    "offensive": {
        "test_sharpe": 5.0,
        "test_calmar": 1.0,
        "test_expectancy": 200.0,
        "test_win_rate": 1.0,
        "stability": 1.0,
        "test_vs_baseline": 4.0,
        "test_max_dd_penalty": 3.0,
        "test_vol_penalty": 0.25,
    },
    "stability_first": {
        "test_sharpe": 2.0,
        "test_calmar": 2.5,
        "test_expectancy": 80.0,
        "test_win_rate": 1.0,
        "stability": 3.0,
        "test_vs_baseline": 2.0,
        "test_max_dd_penalty": 6.0,
        "test_vol_penalty": 0.75,
    },
}

# =========================================
# FALLBACK ALGOS
# =========================================
def algo_identity(r):
    return pd.Series(r, index=r.index)

def algo_zscore(r):
    r = pd.Series(r, index=r.index).astype(float)
    mu = r.rolling(20).mean()
    sd = r.rolling(20).std().replace(0, np.nan)
    z = ((r - mu) / sd).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return z.clip(-3, 3)

def algo_vol_scaled(r):
    r = pd.Series(r, index=r.index).astype(float)
    vol = r.rolling(20).std().replace(0, np.nan)
    out = (r / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return out.clip(-3, 3)

def algo_threshold_clip(r):
    r = pd.Series(r, index=r.index).astype(float)
    clipv = 2.0 * max(float(r.std(ddof=0)), 1e-9)
    return r.clip(-clipv, clipv).fillna(0.0)

DEFAULT_ALGOS = {
    "identity": algo_identity,
    "zscore": algo_zscore,
    "vol_scaled": algo_vol_scaled,
    "threshold_clip": algo_threshold_clip,
}

# =========================================
# FALLBACK FLOWFORMS
# =========================================
def ff_identity(ret):
    return pd.Series(1.0, index=ret.index)

def ff_golden_ratio(ret):
    return pd.Series(1.618, index=ret.index)

def ff_fibonacci(ret):
    fib = np.array([1, 1, 2, 3, 5, 8, 13, 21], dtype=float)
    vals = np.resize(fib / fib.max(), len(ret))
    return pd.Series(vals, index=ret.index)

def ff_log_spiral(ret):
    x = np.linspace(0.0, 3.0, len(ret))
    vals = np.exp(x / max(len(ret), 1))
    vals = vals / max(vals.mean(), 1e-9)
    return pd.Series(vals, index=ret.index)

def ff_archimedean_spiral(ret):
    x = np.arange(len(ret), dtype=float)
    vals = 1.0 + (x / max(len(ret), 1))
    return pd.Series(vals, index=ret.index)

def ff_helix(ret):
    x = np.linspace(0, 8 * np.pi, len(ret))
    vals = 1.0 + 0.25 * np.sin(x)
    return pd.Series(vals, index=ret.index)

def ff_brachistochrone(ret):
    x = np.linspace(0, 1, len(ret))
    vals = np.sqrt(np.clip(x, 1e-6, None))
    vals = vals / np.maximum(vals.mean(), 1e-9)
    return pd.Series(vals, index=ret.index)

def ff_catenary(ret):
    x = np.linspace(-2, 2, len(ret))
    vals = np.cosh(x)
    vals = vals / np.maximum(vals.mean(), 1e-9)
    return pd.Series(vals, index=ret.index)

def ff_sine(ret):
    x = np.linspace(0, 6 * np.pi, len(ret))
    vals = 1.0 + 0.3 * np.sin(x)
    return pd.Series(vals, index=ret.index)

def ff_cosine(ret):
    x = np.linspace(0, 6 * np.pi, len(ret))
    vals = 1.0 + 0.3 * np.cos(x)
    return pd.Series(vals, index=ret.index)

def ff_fractal_brownian(ret):
    vol = ret.rolling(8).std().fillna(0.0)
    vals = 1.0 + (vol / np.maximum(vol.mean(), 1e-9))
    return pd.Series(vals, index=ret.index)

def ff_mandelbrot(ret):
    z = ret.abs().rolling(5).mean().fillna(0.0)
    vals = 1.0 + (z / np.maximum(z.mean(), 1e-9))
    return pd.Series(vals, index=ret.index)

def ff_lorenz(ret):
    x = ret.rolling(3).mean().fillna(0.0)
    y = ret.rolling(8).mean().fillna(0.0)
    vals = 1.0 + np.tanh((x - y) * 50.0)
    return pd.Series(vals, index=ret.index)

def ff_torus(ret):
    x = np.linspace(0, 4 * np.pi, len(ret))
    vals = 1.0 + 0.15 * np.sin(x) * np.cos(2 * x)
    return pd.Series(vals, index=ret.index)

def ff_mobius(ret):
    mom = ret.rolling(5).mean().fillna(0.0)
    vals = np.where(mom >= 0, 1.2, 0.8)
    return pd.Series(vals, index=ret.index)

def ff_interference(ret):
    x = np.linspace(0, 6 * np.pi, len(ret))
    vals = 1.0 + 0.2 * (np.sin(x) + np.sin(1.618 * x))
    return pd.Series(vals, index=ret.index)

def ff_gaussian(ret):
    z = (ret - ret.rolling(20).mean()) / (ret.rolling(20).std() + 1e-9)
    vals = np.exp(-0.5 * z.fillna(0.0) ** 2)
    vals = vals / np.maximum(vals.mean(), 1e-9)
    return pd.Series(vals, index=ret.index)

def ff_power_law(ret):
    x = np.arange(1, len(ret) + 1, dtype=float)
    vals = 1.0 / np.power(x, 0.15)
    vals = vals / np.maximum(vals.mean(), 1e-9)
    return pd.Series(vals, index=ret.index)

def ff_ellipse(ret):
    x = np.linspace(0, 2 * np.pi, len(ret))
    vals = 1.0 + 0.2 * np.sqrt(np.clip(1 - 0.7 * np.sin(x) ** 2, 0, None))
    return pd.Series(vals, index=ret.index)

def ff_hyperbola(ret):
    x = np.linspace(0.2, 2.0, len(ret))
    vals = 1.0 / x
    vals = vals / np.maximum(vals.mean(), 1e-9)
    return pd.Series(vals, index=ret.index)

def ff_lissajous(ret):
    x = np.linspace(0, 4 * np.pi, len(ret))
    vals = 1.0 + 0.2 * np.sin(3 * x + np.pi / 2) * np.sin(2 * x)
    return pd.Series(vals, index=ret.index)

FALLBACK_FLOWFORMS = {k.replace("ff_", ""): v for k, v in globals().items() if callable(v) and k.startswith("ff_")}

# =========================================
# FALLBACK STRATEGIES
# =========================================
def strat_trend(ret):
    fast = ret.rolling(5).mean()
    slow = ret.rolling(20).mean()
    sig = np.where(fast > slow, 1.0, -1.0)
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)

def strat_mean_revert(ret):
    z = (ret - ret.rolling(20).mean()) / (ret.rolling(20).std() + 1e-9)
    sig = np.where(z < -1.0, 1.0, np.where(z > 1.0, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)

def strat_breakout(ret):
    hi = ret.rolling(20).max()
    lo = ret.rolling(20).min()
    sig = np.where(ret >= hi, 1.0, np.where(ret <= lo, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)

def strat_regime_switch(ret):
    fast_vol = ret.rolling(5).std()
    slow_vol = ret.rolling(20).std()
    trend = strat_trend(ret)
    mr = strat_mean_revert(ret)
    sig = np.where(fast_vol > slow_vol, trend, mr)
    return pd.Series(sig, index=ret.index).fillna(0.0)

def strat_harmonic_blend(ret):
    a = strat_trend(ret)
    b = strat_mean_revert(ret)
    c = strat_breakout(ret)
    sig = np.sign(a + b + c)
    return pd.Series(sig, index=ret.index).fillna(0.0)

def strat_momentum_lowvol(ret):
    mom = ret.rolling(10).mean()
    vol = ret.rolling(10).std()
    sig = np.where((mom > 0) & (vol < vol.rolling(20).mean()), 1.0, 0.0)
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)

def strat_inverse_vol(ret):
    vol = ret.rolling(10).std().fillna(0.0)
    sig = 1.0 / np.maximum(vol, 1e-6)
    sig = sig / np.maximum(np.nanmean(np.abs(sig)), 1e-9)
    sig = np.sign(sig - np.nanmean(sig))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)

def strat_equal_weight(ret):
    return pd.Series(1.0, index=ret.index).shift(1).fillna(0.0)

FALLBACK_STRATEGIES = {k.replace("strat_", ""): v for k, v in globals().items() if callable(v) and k.startswith("strat_")}

# =========================================
# MODULE DISCOVERY
# =========================================
sys.path.insert(0, str(CODE))

def try_import(name):
    try:
        return importlib.import_module(name)
    except Exception:
        return None

MODULES = [
    try_import("institutional_harmonic_suite"),
    try_import("adaptive_engine"),
    try_import("institutional_harmonic_core"),
    try_import("hybrid_harmonic_algorithms"),
    try_import("hybrid_harmonic_strategies"),
    try_import("novel_harmonic_layers"),
    try_import("meta_harmonic_router"),
]

MODULES = [
    try_import("institutional_harmonic_suite"),
    try_import("adaptive_engine"),
    try_import("institutional_harmonic_core"),
    try_import("hybrid_harmonic_algorithms"),
    try_import("hybrid_harmonic_strategies"),
    try_import("novel_harmonic_layers"),
    try_import("meta_harmonic_router"),
]

def discover_prefixed(modules, prefix):
    found = {}
    for mod in modules:
        for name, obj in inspect.getmembers(mod):
            if callable(obj) and name.startswith(prefix):
                found[name.replace(prefix, "")] = obj
    return found

def discover_named_dict(modules, dict_name):
    out = {}
    for mod in modules:
        d = getattr(mod, dict_name, None)
        if isinstance(d, dict):
            for k, v in d.items():
                out[str(k)] = v
    return out

DISCOVERED_FLOWFORMS = discover_named_dict(MODULES, "FLOWFORMS")
if not DISCOVERED_FLOWFORMS:
    DISCOVERED_FLOWFORMS = discover_prefixed(MODULES, "ff_")
if not DISCOVERED_FLOWFORMS:
    DISCOVERED_FLOWFORMS = FALLBACK_FLOWFORMS

DISCOVERED_STRATEGIES = discover_named_dict(MODULES, "STRATEGIES")
if not DISCOVERED_STRATEGIES:
    DISCOVERED_STRATEGIES = discover_prefixed(MODULES, "strat_")
if not DISCOVERED_STRATEGIES:
    DISCOVERED_STRATEGIES = FALLBACK_STRATEGIES

DISCOVERED_ALGOS = discover_named_dict(MODULES, "ALGO_WRAPPERS")
if not DISCOVERED_ALGOS:
    DISCOVERED_ALGOS = discover_prefixed(MODULES, "algo_")
if not DISCOVERED_ALGOS:
    DISCOVERED_ALGOS = DEFAULT_ALGOS

DISCOVERED_METRIC_PROFILES = discover_named_dict(MODULES, "METRIC_PROFILES")
if not DISCOVERED_METRIC_PROFILES:
    DISCOVERED_METRIC_PROFILES = METRIC_PROFILES

DISCOVERED_METRIC_PROFILES = {
    k: v for k, v in DISCOVERED_METRIC_PROFILES.items()
    if isinstance(v, dict)
}
if not DISCOVERED_METRIC_PROFILES:
    DISCOVERED_METRIC_PROFILES = METRIC_PROFILES

# =========================================
# CANDIDATE EVAL
# =========================================
def apply_flowform(flow_fn, ret: pd.Series) -> pd.Series:
    try:
        out = flow_fn(ret)
        out = pd.Series(out, index=ret.index)
        out = normalize_series(out)
        return out
    except Exception:
        return pd.Series(np.ones(len(ret)), index=ret.index, dtype=float)

def apply_algo(algo_fn, x: pd.Series) -> pd.Series:
    try:
        out = algo_fn(x)
        out = pd.Series(out, index=x.index)
        out = out.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return out
    except Exception:
        return pd.Series(x, index=x.index).fillna(0.0)

def apply_strategy(strat_fn, x: pd.Series) -> pd.Series:
    try:
        sig = strat_fn(x)
        sig = pd.Series(sig, index=x.index).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        sig = np.sign(sig)
        return pd.Series(sig, index=x.index)
    except Exception:
        return pd.Series(np.zeros(len(x)), index=x.index, dtype=float)

def score_candidate(metrics: dict, profile: dict) -> float:
    return float(
        (metrics["test_sharpe"]      * profile.get("test_sharpe", 0.0)) +
        (metrics["test_calmar"]      * profile.get("test_calmar", 0.0)) +
        (metrics["test_expectancy"]  * profile.get("test_expectancy", 0.0)) +
        (metrics["test_win_rate"]    * profile.get("test_win_rate", 0.0)) +
        (metrics["stability"]        * profile.get("stability", 0.0)) +
        (metrics["test_vs_baseline"] * profile.get("test_vs_baseline", 0.0)) -
        (abs(metrics["test_max_dd"]) * profile.get("test_max_dd_penalty", 0.0)) -
        (metrics["test_vol"]         * profile.get("test_vol_penalty", 0.0))
    )

def evaluate_path(file_path: Path, returns: pd.Series, flow_name, flow_fn, algo_name, algo_fn, strat_name, strat_fn, metric_name, metric_profile):
    ret = returns.copy()

    ff = apply_flowform(flow_fn, ret)
    transformed = ret * ff
    transformed = apply_algo(algo_fn, transformed)

    signal = apply_strategy(strat_fn, transformed)
    strat_ret = (signal.shift(1).fillna(0.0) * ret).dropna()
    if len(strat_ret) < MIN_RET_LEN:
        return None

    base_ret = ret.loc[strat_ret.index]
    train_r, test_r = split_train_test(strat_ret)
    train_b, test_b = split_train_test(base_ret)

    if len(test_r) < 10:
        return None

    train_eq = make_equity(train_r)
    test_eq  = make_equity(test_r)

    test_sh = sharpe(test_r)
    base_sh = sharpe(test_b) if len(test_b) else 0.0

    metrics = {
        "train_sharpe": sharpe(train_r),
        "test_sharpe": test_sh,
        "train_max_dd": max_drawdown(train_eq),
        "test_max_dd": max_drawdown(test_eq),
        "train_cagr": cagr(train_eq),
        "test_cagr": cagr(test_eq),
        "train_calmar": calmar(train_eq),
        "test_calmar": calmar(test_eq),
        "test_win_rate": win_rate(test_r),
        "test_expectancy": expectancy(test_r),
        "test_vol": annual_vol(test_r),
        "stability": stability_score(test_eq),
        "baseline_test_sharpe": base_sh,
        "test_vs_baseline": test_sh - base_sh,
    }

    institutional_score = score_candidate(metrics, metric_profile)
    institutional_score = float(np.clip(institutional_score, -1e6, 1e6))

    return {
        "file": str(file_path),
        "flow": flow_name,
        "algo": algo_name,
        "strategy": strat_name,
        "metric_profile": metric_name,
        **metrics,
        "institutional_score": institutional_score,
    }

# =========================================
# DATASET DISCOVERY
# =========================================
def discover_csvs():
    seen = set()
    files = []
    for root in DATA_ROOTS:
        if root.exists():
            for p in root.rglob("*.csv"):
                rp = str(p.resolve())
                if rp not in seen:
                    seen.add(rp)
                    files.append(p)
    return sorted(files, key=lambda x: str(x).lower())

def load_candidate_returns(path: Path):
    df = safe_read_csv(path)
    if df.empty:
        return None
    time_col, value_col = pick_time_and_value_cols(df)
    if value_col is None:
        return None
    s = clean_numeric_series(df[value_col])
    if len(s) < MIN_SERIES_LEN:
        return None
    r = to_returns(s)
    if len(r) < MIN_RET_LEN:
        return None
    return {
        "time_col": time_col,
        "value_col": value_col,
        "returns": r
    }

# =========================================
# MAIN TOURNAMENT
# =========================================
def main():
    csvs = discover_csvs()
    usable = []
    dataset_scan = []

    for p in csvs:
        loaded = load_candidate_returns(p)
        if loaded is None:
            dataset_scan.append({
                "file": str(p),
                "status": "skipped"
            })
            continue
        usable.append((p, loaded))
        dataset_scan.append({
            "file": str(p),
            "status": "usable",
            "value_col": loaded["value_col"],
            "time_col": loaded["time_col"] or "",
            "ret_len": int(len(loaded["returns"]))
        })

    rows = []

    for path, info in usable:
        ret = info["returns"]

        for flow_name, flow_fn in DISCOVERED_FLOWFORMS.items():
            for algo_name, algo_fn in DISCOVERED_ALGOS.items():
                for strat_name, strat_fn in DISCOVERED_STRATEGIES.items():
                    for metric_name, metric_profile in DISCOVERED_METRIC_PROFILES.items():
                        row = evaluate_path(
                            file_path=path,
                            returns=ret,
                            flow_name=flow_name,
                            flow_fn=flow_fn,
                            algo_name=algo_name,
                            algo_fn=algo_fn,
                            strat_name=strat_name,
                            strat_fn=strat_fn,
                            metric_name=metric_name,
                            metric_profile=metric_profile
                        )
                        if row is not None:
                            rows.append(row)

    results = pd.DataFrame(rows)
    if results.empty:
        empty_path = OUT / "full_beast_empty.csv"
        pd.DataFrame({"status": ["no_results"]}).to_csv(empty_path, index=False)
        print("No usable full-universe results. Wrote:", empty_path)
        return

    results = results.sort_values(
        ["institutional_score", "test_sharpe", "test_vs_baseline"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    leaderboard_path = OUT / "full_beast_leaderboard.csv"
    top10_path = OUT / "full_beast_top10.csv"
    scan_path = OUT / "full_beast_dataset_scan.csv"
    registry_path = OUT / "full_beast_registry.json"
    summary_path = OUT / "full_beast_summary.json"

    results.to_csv(leaderboard_path, index=False)
    results.head(10).to_csv(top10_path, index=False)
    pd.DataFrame(dataset_scan).to_csv(scan_path, index=False)

    registry = {
        "flowforms_count": len(DISCOVERED_FLOWFORMS),
        "flowforms": sorted(DISCOVERED_FLOWFORMS.keys()),
        "algos_count": len(DISCOVERED_ALGOS),
        "algos": sorted(DISCOVERED_ALGOS.keys()),
        "strategies_count": len(DISCOVERED_STRATEGIES),
        "strategies": sorted(DISCOVERED_STRATEGIES.keys()),
        "metric_profiles_count": len(DISCOVERED_METRIC_PROFILES),
        "metric_profiles": sorted(DISCOVERED_METRIC_PROFILES.keys()),
    }
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    top = results.iloc[0].to_dict()
    summary = {
        "files_scanned": len(csvs),
        "usable_files": len(usable),
        "flowforms_count": len(DISCOVERED_FLOWFORMS),
        "algos_count": len(DISCOVERED_ALGOS),
        "strategies_count": len(DISCOVERED_STRATEGIES),
        "metric_profiles_count": len(DISCOVERED_METRIC_PROFILES),
        "expected_full_candidates": int(len(usable) * len(DISCOVERED_FLOWFORMS) * len(DISCOVERED_ALGOS) * len(DISCOVERED_STRATEGIES) * len(DISCOVERED_METRIC_PROFILES)),
        "actual_candidates_scored": int(len(results)),
        "top_file": top.get("file"),
        "top_flow": top.get("flow"),
        "top_algo": top.get("algo"),
        "top_strategy": top.get("strategy"),
        "top_metric_profile": top.get("metric_profile"),
        "top_test_sharpe": float(top.get("test_sharpe", 0.0)),
        "top_test_vs_baseline": float(top.get("test_vs_baseline", 0.0)),
        "top_institutional_score": float(top.get("institutional_score", 0.0)),
        "leaderboard_csv": str(leaderboard_path),
        "top10_csv": str(top10_path),
        "registry_json": str(registry_path),
        "dataset_scan_csv": str(scan_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    proof = {
        "generated_utc": pd.Timestamp.utcnow().isoformat(),
        "leaderboard_sha256": sha256_file(leaderboard_path),
        "top10_sha256": sha256_file(top10_path),
        "registry_sha256": sha256_file(registry_path),
        "dataset_scan_sha256": sha256_file(scan_path),
        "summary_sha256": sha256_file(summary_path),
    }
    proof_path = OUT / "full_beast_proof.json"
    proof_path.write_text(json.dumps(proof, indent=2), encoding="utf-8")

    print("")
    print("=== FULL BEAST MODE COMPLETE ===")
    print("FILES SCANNED:", len(csvs))
    print("USABLE FILES :", len(usable))
    print("FLOWFORMS    :", len(DISCOVERED_FLOWFORMS))
    print("ALGOS        :", len(DISCOVERED_ALGOS))
    print("STRATEGIES   :", len(DISCOVERED_STRATEGIES))
    print("METRIC PROFS :", len(DISCOVERED_METRIC_PROFILES))
    print("EXPECTED CANDS:", summary["expected_full_candidates"])
    print("ACTUAL SCORED :", summary["actual_candidates_scored"])
    print("TOP FLOW      :", summary["top_flow"])
    print("TOP ALGO      :", summary["top_algo"])
    print("TOP STRATEGY  :", summary["top_strategy"])
    print("TOP PROFILE   :", summary["top_metric_profile"])
    print("TOP SHARPE    :", summary["top_test_sharpe"])
    print("VS BASELINE   :", summary["top_test_vs_baseline"])
    print("SCORE         :", summary["top_institutional_score"])
    print("")
    print("LEADERBOARD:", leaderboard_path)
    print("TOP10      :", top10_path)
    print("REGISTRY   :", registry_path)
    print("SCAN       :", scan_path)
    print("SUMMARY    :", summary_path)
    print("PROOF      :", proof_path)

if __name__ == "__main__":
    main()




