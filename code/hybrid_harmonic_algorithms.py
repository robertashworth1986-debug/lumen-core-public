import numpy as np
import pandas as pd

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
