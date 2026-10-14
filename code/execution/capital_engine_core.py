import numpy as np
import pandas as pd


def _numeric_series(values, *, name, allow_nan=False):
    series = pd.Series(values, copy=True)
    if not series.index.is_unique or not series.index.is_monotonic_increasing:
        raise ValueError(f"{name} index must be unique and increasing")
    try:
        series = pd.to_numeric(series, errors="raise").astype(float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if np.isinf(series.to_numpy()).any() or (not allow_nan and series.isna().any()):
        raise ValueError(f"{name} contains nonfinite observations")
    return series

def build_families(df):
    close = _numeric_series(df["close"], name="close")
    ret = _numeric_series(df["ret"], name="returns")
    if not close.index.equals(ret.index) or (close <= 0).any():
        raise ValueError("close and returns require matching indexes and positive prices")
    mom_12 = close.pct_change(12, fill_method=None)
    mom_48 = close.pct_change(48, fill_method=None)
    ma_fast = close.rolling(24).mean()
    ma_slow = close.rolling(96).mean()
    trend_strength = (ma_fast / ma_slow) - 1.0
    vol_24 = ret.rolling(24).std()
    vol_72 = ret.rolling(72).std()
    z_24 = (close - close.rolling(24).mean()) / close.rolling(24).std()
    breakout_72 = close / close.rolling(72).max()
    drawup_24 = close / close.rolling(24).min() - 1.0
    families = {}
    families["momentum_lowvol"] = np.where((mom_12 > 0) & (vol_24 < vol_24.expanding(min_periods=1).median()), 1,
        np.where((mom_12 < 0) & (vol_24 < vol_24.expanding(min_periods=1).median()), -1, 0))
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
        np.sign(drawup_24.fillna(0)) * np.where(vol_24 < vol_24.expanding(min_periods=1).quantile(0.7), 1.0, 0.0)
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

def stats(r, periods_per_year=24 * 365):
    """Descriptive bar-return metrics; no out-of-sample or profit claim is implied."""
    r = _numeric_series(r, name="strategy returns")
    if isinstance(periods_per_year, bool) or not np.isfinite(periods_per_year) or periods_per_year <= 0:
        raise ValueError("periods_per_year must be finite and positive")
    if (r < -1).any():
        raise ValueError("simple returns below -100% cannot form a nonnegative NAV")
    if len(r) == 0:
        return {"samples": 0, "sharpe": 0.0, "win_rate": 0.0, "max_drawdown": 0.0, "cagr": 0.0, "final_nav": 1.0, "calmar": 0.0, "vol": 0.0, "annualization_ready": False}
    with np.errstate(over="ignore", invalid="ignore"):
        eq = (1.0 + r).cumprod()
    if not np.isfinite(eq.to_numpy()).all():
        raise ValueError("compounded NAV exceeds finite numeric range")
    # Include initial capital so a loss on the very first bar is not hidden.
    peak = eq.cummax().clip(lower=1.0)
    max_dd = float(((eq / peak) - 1.0).min())
    final_nav = float(eq.iloc[-1])
    with np.errstate(over="ignore", invalid="ignore"):
        mean = float(r.mean())
        std = float(r.std()) if len(r) > 1 else 0.0
    if not np.isfinite(mean) or not np.isfinite(std):
        raise ValueError("return moments exceed finite numeric range")
    annualization_ready = len(r) >= 50
    sharpe = mean / std * np.sqrt(periods_per_year) if annualization_ready and std > 1e-12 else 0.0
    years = len(r) / float(periods_per_year)
    with np.errstate(over="ignore", invalid="ignore"):
        cagr = float(np.expm1(np.log(final_nav) / years)) if annualization_ready and final_nav > 0 else (-1.0 if final_nav == 0 else 0.0)
    if not np.isfinite(cagr):
        raise ValueError("annualized growth exceeds finite numeric range")
    calmar = cagr / abs(max_dd) if annualization_ready and max_dd < 0 else 0.0
    vol = float(std * np.sqrt(periods_per_year)) if annualization_ready else 0.0
    if not all(np.isfinite(value) for value in (sharpe, calmar, vol)):
        raise ValueError("annualized metrics exceed finite numeric range")
    return {"samples": len(r), "sharpe": float(sharpe), "win_rate": float((r > 0).mean()), "max_drawdown": max_dd, "cagr": cagr, "final_nav": final_nav, "calmar": float(calmar), "vol": vol, "annualization_ready": annualization_ready}


def build_strategy_returns(signal, ret, cost_bps=2.0):
    """Close-bar signals execute one bar later, with cost on absolute turnover.

    A flip from +1 to -1 trades two units. Returns are retained unchanged rather
    than clipped; missing realized returns are rejected rather than fabricated.
    """
    returns = _numeric_series(ret, name="market returns")
    # These are simple spot-price returns. A value below -100% is an invalid
    # market observation, even when short or flat exposure would mask the loss.
    if (returns < -1).any():
        raise ValueError("market simple returns below -100% are invalid")
    if isinstance(signal, pd.Series):
        if not signal.index.equals(returns.index):
            raise ValueError("signals and returns must have exactly matching indexes")
        signals = _numeric_series(signal, name="signals", allow_nan=True)
    else:
        if len(signal) != len(returns):
            raise ValueError("signals and returns must have the same length")
        signals = _numeric_series(pd.Series(signal, index=returns.index), name="signals", allow_nan=True)
    if isinstance(cost_bps, bool) or not np.isfinite(cost_bps) or cost_bps < 0:
        raise ValueError("cost_bps must be finite and nonnegative")
    pos = signals.clip(-1, 1).shift(1).fillna(0.0)
    turnover = pos.diff().abs()
    if len(turnover):
        turnover.iloc[0] = abs(pos.iloc[0])
    costs = turnover * (float(cost_bps) / 10000.0)
    strat = pos * returns - costs
    if not np.isfinite(strat.to_numpy()).all():
        raise ValueError("strategy returns exceed finite numeric range")
    return strat, pos, turnover
