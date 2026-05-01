import numpy as np
import pandas as pd

# --- Strategies ---
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

# --- Algorithms ---
def _series(x):
    s = pd.Series(x).astype(float).replace([np.inf, -np.inf], np.nan)
    return s.ffill().bfill().fillna(0.0)

def _normalize(x):
    s = _series(x)
    m = float(np.nanmean(np.abs(s.values)))
    if not np.isfinite(m) or m <= 1e-12:
        return pd.Series(np.zeros(len(s)), index=s.index, dtype=float)
    return s / m

def algo_phase_coherence(r):
    s = _series(r)
    fast = s.rolling(5).mean()
    mid  = s.rolling(13).mean()
    slow = s.rolling(34).mean()
    a = np.sign(fast - mid)
    b = np.sign(mid - slow)
    c = np.sign(fast - slow)
    out = (a + b + c) / 3.0
    return _normalize(out).clip(-1, 1)

def algo_resonance_cluster(r):
    s = _series(r)
    mom = s.rolling(8).mean()
    mr  = -(s - s.rolling(21).mean())
    vol = -s.rolling(8).std()
    z1 = _normalize(mom)
    z2 = _normalize(mr)
    z3 = _normalize(vol)
    out = (z1 + z2 + z3) / 3.0
    return _normalize(out).clip(-3, 3)

def algo_multi_timescale_interference(r):
    s = _series(r)
    a = _normalize(s.rolling(5).mean())
    b = _normalize(s.rolling(20).mean())
    c = _normalize(s.rolling(60).mean())
    out = (a * b) + (b * c) + (a * c)
    return _normalize(out).clip(-3, 3)

def algo_harmonic_envelope(r):
    s = _series(r)
    mu = s.rolling(20).mean()
    sd = s.rolling(20).std().replace(0, np.nan)
    z  = ((s - mu) / sd).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    env = np.exp(-0.5 * z**2)
    tilt = np.sign(s.rolling(5).mean())
    out = env * tilt
    return _normalize(out).clip(-3, 3)

def algo_frequency_drift(r):
    s = _series(r)
    f1 = s.rolling(5).mean()
    f2 = s.rolling(13).mean()
    f3 = s.rolling(34).mean()
    drift = (f1 - f2).diff() + (f2 - f3).diff()
    return _normalize(drift).clip(-3, 3)

def algo_curvature_pressure(r):
    s = _series(r)
    first = s.diff()
    second = first.diff()
    curvature = second.abs() / (1.0 + first.abs())
    signed = np.sign(first.fillna(0.0)) * curvature.fillna(0.0)
    return _normalize(signed).clip(-3, 3)

def algo_nodal_compression(r):
    s = _series(r)
    bands = pd.concat([
        s.rolling(5).std(),
        s.rolling(13).std(),
        s.rolling(34).std()
    ], axis=1)
    comp = -bands.mean(axis=1)
    return _normalize(comp).clip(-3, 3)

def algo_harmonic_divergence(r):
    s = _series(r)
    price_like = s.cumsum()
    mom = price_like.diff(5)
    coh = (s.rolling(8).mean() - s.rolling(21).mean())
    div = _normalize(mom) - _normalize(coh)
    return _normalize(div).clip(-3, 3)

def algo_harmonic_entropy(r):
    s = _series(r)
    vol = s.rolling(20).std().fillna(0.0)
    amp = s.abs().rolling(20).mean().fillna(0.0)
    ent = vol / (amp + 1e-9)
    out = -_normalize(ent)
    return out.clip(-3, 3)

def algo_geometry_consensus(r):
    s = _series(r)
    a = _normalize(s.rolling(5).mean())
    b = _normalize(np.sin(s.rolling(8).mean().fillna(0.0)))
    c = _normalize(np.cos(s.rolling(13).mean().fillna(0.0)))
    d = _normalize(np.tanh(s.rolling(21).mean().fillna(0.0)))
    out = (np.sign(a) + np.sign(b) + np.sign(c) + np.sign(d)) / 4.0
    return _normalize(out).clip(-1, 1)

ALGO_WRAPPERS = {
    "phase_coherence": algo_phase_coherence,
    "resonance_cluster": algo_resonance_cluster,
    "multi_timescale_interference": algo_multi_timescale_interference,
    "harmonic_envelope": algo_harmonic_envelope,
    "frequency_drift": algo_frequency_drift,
    "curvature_pressure": algo_curvature_pressure,
    "nodal_compression": algo_nodal_compression,
    "harmonic_divergence": algo_harmonic_divergence,
    "harmonic_entropy": algo_harmonic_entropy,
    "geometry_consensus": algo_geometry_consensus,
}
