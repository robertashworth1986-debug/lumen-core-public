import numpy as np
import pandas as pd

def build_families(df):
    close = df["close"]
    ret = df["ret"]
    mom_12 = close.pct_change(12)
    mom_48 = close.pct_change(48)
    ma_fast = close.rolling(24).mean()
    ma_slow = close.rolling(96).mean()
    trend_strength = (ma_fast / ma_slow) - 1.0
    vol_24 = ret.rolling(24).std()
    vol_72 = ret.rolling(72).std()
    z_24 = (close - close.rolling(24).mean()) / close.rolling(24).std()
    breakout_72 = close / close.rolling(72).max()
    drawup_24 = close / close.rolling(24).min() - 1.0
    families = {}
    families["momentum_lowvol"] = np.where((mom_12 > 0) & (vol_24 < vol_24.median()), 1,
        np.where((mom_12 < 0) & (vol_24 < vol_24.median()), -1, 0))
    families["inverse_vol"] = -np.sign(vol_24 - vol_72)
    families["harmonic_hybrid"] = (
        0.45 * np.sign(mom_12.fillna(0)) +
        0.35 * np.sign(trend_strength.fillna(0)) +
        0.20 * np.sign((-z_24).fillna(0))
    )
    families["helix_cycle"] = (
        0.5 * np.sign(mom_12.fillna(0)) +
        0.5 * np.sign((mom_12 - mom_48).fillna(0))
    )
    families["fractal_balance"] = (
        0.4 * np.sign(mom_48.fillna(0)) +
        0.3 * np.sign((-z_24).fillna(0)) +
        0.3 * np.sign((vol_72 - vol_24).fillna(0))
    )
    families["torsion_trend"] = np.where((ma_fast > ma_slow) & (trend_strength > 0), 1,
        np.where((ma_fast < ma_slow) & (trend_strength < 0), -1, 0))
    families["harmonic_energy"] = (
        np.sign(drawup_24.fillna(0)) * np.where(vol_24 < vol_24.quantile(0.7), 1.0, 0.0)
    )
    families["branch_diversifier"] = (
        0.34 * np.sign(mom_12.fillna(0)) +
        0.33 * np.sign(mom_48.fillna(0)) +
        0.33 * np.sign(trend_strength.fillna(0))
    )
    families["dispersion_harvest"] = np.where(z_24 > 1.25, -1,
        np.where(z_24 < -1.25, 1, 0))
    families["breakout_pressure"] = np.where(breakout_72 > 0.995, 1,
        np.where(close / close.rolling(72).min() < 1.005, -1, 0))
    return families

def safe_series(x):
    return pd.Series(x).replace([np.inf, -np.inf], np.nan).fillna(0.0)

def stats(r):
    r = safe_series(r)
    if len(r) < 50:
        return {"samples": int(len(r)), "sharpe": 0.0, "win_rate": 0.0, "max_drawdown": 0.0, "cagr": 0.0, "final_nav": 1.0, "calmar": 0.0, "vol": 0.0}
    mean = r.mean()
    std = r.std()
    sharpe = (mean / std) * np.sqrt(24 * 365) if std > 1e-12 else 0.0
    win = float((r > 0).mean())
    eq = (1.0 + r).cumprod()
    eq = eq.replace([np.inf, -np.inf], np.nan).dropna()
    if len(eq) == 0:
        eq = pd.Series([1.0])
    peak = eq.cummax()
    dd = (eq / peak) - 1.0
    max_dd = float(dd.min()) if len(dd) else 0.0
    years = len(r) / (24.0 * 365.0)
    final_nav = float(eq.iloc[-1]) if len(eq) else 1.0
    cagr = (final_nav ** (1.0 / years) - 1.0) if years > 0 and final_nav > 0 else 0.0
    calmar = (cagr / abs(max_dd)) if max_dd < 0 else 0.0
    vol = float(std * np.sqrt(24 * 365))
    return {"samples": int(len(r)), "sharpe": float(sharpe), "win_rate": float(win), "max_drawdown": float(max_dd), "cagr": float(cagr), "final_nav": float(final_nav), "calmar": float(calmar), "vol": float(vol)}

def build_strategy_returns(signal, ret, cost_bps=2.0):
    pos = pd.Series(signal).clip(-1, 1).shift(1).fillna(0.0)
    turnover = pos.diff().abs().fillna(0.0)
    costs = turnover * (cost_bps / 10000.0)
    strat = (pos * ret) - costs
    strat = safe_series(strat)

    pos = pd.Series(signal).clip(-1, 1).shift(1).fillna(0.0)
    turnover = pos.diff().abs().fillna(0.0)
    costs = turnover * (cost_bps / 10000.0)
    strat = (pos * ret) - costs
    strat = safe_series(strat)
    strat = strat.clip(-0.20, 0.20)
    return strat, pos, turnover
    costs = turnover * (cost_bps / 10000.0)
    strat = (pos * ret) - costs
