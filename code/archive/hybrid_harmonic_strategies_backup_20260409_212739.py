import numpy as np
import pandas as pd

def _s(x):
    s = pd.Series(x).astype(float).replace([np.inf, -np.inf], np.nan)
    return s.ffill().bfill().fillna(0.0)

def _z(x, win=20):
    s = _s(x)
    mu = s.rolling(win).mean()
    sd = s.rolling(win).std().replace(0, np.nan)
    return ((s - mu) / sd).replace([np.inf, -np.inf], np.nan).fillna(0.0)

def strat_phase_follow(x):
    s = _s(x)
    fast = s.rolling(5).mean()
    slow = s.rolling(21).mean()
    sig = np.sign(fast - slow)
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_resonance_revert(x):
    z = _z(x, 21)
    sig = np.where(z < -1.25, 1.0, np.where(z > 1.25, -1.0, 0.0))
    return pd.Series(sig, index=z.index).shift(1).fillna(0.0)

def strat_interference_breakout(x):
    s = _s(x)
    hi = s.rolling(34).max()
    lo = s.rolling(34).min()
    sig = np.where(s >= hi, 1.0, np.where(s <= lo, -1.0, 0.0))
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_nodal_compression_release(x):
    s = _s(x)
    vol = s.rolling(13).std()
    quiet = vol < vol.rolling(55).median()
    thrust = np.sign(s.diff(3).fillna(0.0))
    sig = np.where(quiet & (thrust > 0), 1.0, np.where(quiet & (thrust < 0), -1.0, 0.0))
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_frequency_drift_guard(x):
    s = _s(x)
    drift = s.diff().rolling(8).mean()
    accel = drift.diff().fillna(0.0)
    sig = np.where((drift > 0) & (accel > 0), 1.0, np.where((drift < 0) & (accel < 0), -1.0, 0.0))
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_curvature_reversal(x):
    s = _s(x)
    first = s.diff()
    second = first.diff()
    sig = np.where((first < 0) & (second > 0), 1.0, np.where((first > 0) & (second < 0), -1.0, 0.0))
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_harmonic_consensus(x):
    s = _s(x)
    a = np.sign(s.rolling(5).mean())
    b = np.sign(s.rolling(13).mean())
    c = np.sign(s.rolling(34).mean())
    sig = np.sign(a + b + c)
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_entropy_filter_trend(x):
    s = _s(x)
    vol = s.rolling(21).std()
    amp = s.abs().rolling(21).mean() + 1e-9
    ent = vol / amp
    trend = np.sign(s.rolling(8).mean() - s.rolling(34).mean())
    sig = np.where(ent < ent.rolling(55).median(), trend, 0.0)
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_echo_memory(x):
    s = _s(x)
    echo1 = s.rolling(8).mean()
    echo2 = echo1.rolling(8).mean()
    sig = np.sign(echo1 - echo2)
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

def strat_symmetry_break(x):
    s = _s(x)
    z = _z(s, 34)
    sig = np.where(z > 1.0, 1.0, np.where(z < -1.0, -1.0, 0.0))
    return pd.Series(sig, index=s.index).shift(1).fillna(0.0)

STRATEGIES = {
    "phase_follow": strat_phase_follow,
    "resonance_revert": strat_resonance_revert,
    "interference_breakout": strat_interference_breakout,
    "nodal_compression_release": strat_nodal_compression_release,
    "frequency_drift_guard": strat_frequency_drift_guard,
    "curvature_reversal": strat_curvature_reversal,
    "harmonic_consensus": strat_harmonic_consensus,
    "entropy_filter_trend": strat_entropy_filter_trend,
    "echo_memory": strat_echo_memory,
    "symmetry_break": strat_symmetry_break,
}
