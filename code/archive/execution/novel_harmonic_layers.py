import numpy as np
import pandas as pd

def _s(x):
    s = pd.Series(x).astype(float).replace([np.inf, -np.inf], np.nan)
    return s.ffill().bfill().fillna(0.0)

def _norm(x):
    s = _s(x)
    m = float(np.nanmean(np.abs(s.values)))
    if not np.isfinite(m) or m <= 1e-12:
        return pd.Series(np.zeros(len(s)), index=s.index, dtype=float)
    return s / m

# ================================
# 4 NOVEL ALGOS
# ================================
def algo_echo_stack(r):
    s = _s(r)
    out = s.rolling(5).mean() + s.rolling(13).mean() + s.rolling(34).mean()
    return _norm(out).clip(-3, 3)

def algo_resonant_pressure(r):
    s = _s(r)
    mom = s.diff(5)
    vol = s.rolling(13).std() + 1e-9
    out = mom / vol
    return _norm(out).clip(-3, 3)

def algo_phase_lattice(r):
    s = _s(r)
    x = np.linspace(0, 6*np.pi, len(s))
    out = s * np.sin(x) + s.rolling(8).mean().fillna(0.0) * np.cos(1.618*x)
    return _norm(out).clip(-3, 3)

def algo_vortex_memory(r):
    s = _s(r)
    out = s.rolling(8).mean().fillna(0.0) - s.rolling(21).mean().fillna(0.0) + s.rolling(55).mean().fillna(0.0)
    return _norm(out).clip(-3, 3)

ALGO_WRAPPERS = {
    "echo_stack": algo_echo_stack,
    "resonant_pressure": algo_resonant_pressure,
    "phase_lattice": algo_phase_lattice,
    "vortex_memory": algo_vortex_memory,
}

# ================================
# 4 NOVEL METRIC PROFILES
# ================================
METRIC_PROFILES = {
    "convexity_hunter": {
        "test_sharpe": 3.5,
        "test_calmar": 1.5,
        "test_expectancy": 220.0,
        "test_win_rate": 1.0,
        "stability": 1.0,
        "test_vs_baseline": 5.0,
        "test_max_dd_penalty": 3.0,
        "test_vol_penalty": 0.25,
    },
    "entropy_slayer": {
        "test_sharpe": 3.0,
        "test_calmar": 2.5,
        "test_expectancy": 130.0,
        "test_win_rate": 1.5,
        "stability": 2.5,
        "test_vs_baseline": 3.0,
        "test_max_dd_penalty": 4.0,
        "test_vol_penalty": 0.5,
    },
    "coherence_max": {
        "test_sharpe": 2.5,
        "test_calmar": 2.0,
        "test_expectancy": 110.0,
        "test_win_rate": 2.0,
        "stability": 4.0,
        "test_vs_baseline": 2.0,
        "test_max_dd_penalty": 5.0,
        "test_vol_penalty": 0.5,
    },
    "whitehole_offensive": {
        "test_sharpe": 5.0,
        "test_calmar": 1.0,
        "test_expectancy": 260.0,
        "test_win_rate": 1.0,
        "stability": 0.5,
        "test_vs_baseline": 6.0,
        "test_max_dd_penalty": 2.0,
        "test_vol_penalty": 0.1,
    },
}

# ================================
# 2 NOVEL FLOWFORMS
# ================================
def ff_vortex_breath(ret):
    s = _s(ret)
    x = np.linspace(0, 8*np.pi, len(s))
    vals = 1.0 + 0.2*np.sin(x) + 0.1*np.cos(0.5*x)
    return pd.Series(vals, index=s.index)

def ff_whitehole_pulse(ret):
    s = _s(ret)
    x = np.linspace(0, 1, len(s))
    vals = 1.0 + np.exp(-((x - 0.5)**2) / 0.02)
    vals = vals / np.maximum(vals.mean(), 1e-9)
    return pd.Series(vals, index=s.index)

FLOWFORMS = {
    "vortex_breath": ff_vortex_breath,
    "whitehole_pulse": ff_whitehole_pulse,
}
