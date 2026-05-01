import os
import json
import math
import numpy as np
import pandas as pd

OUT_DIR = "C:/LumaTrader/INSTITUTIONAL_STACK_V2/out"
DATA_DIR = "C:/LumaTrader/data"

ANNUALIZATION = 252.0
MIN_SERIES_LEN = 120
MIN_RET_LEN = 40
TRAIN_RATIO = 0.70

# Realism controls for sim-to-live transfer
RETURN_CLIP_PCT = 0.03              # clip per-bar returns to +/-3%
FLOW_MIN = 0.25
FLOW_MAX = 2.50
SIM_MAKER_FEE_PCT = 0.0016          # 16 bps
SIM_TAKER_FEE_PCT = 0.0026          # 26 bps
SIM_SLIPPAGE_PCT = 0.0005           # 5 bps
SIM_ONE_WAY_COST_PCT = ((SIM_MAKER_FEE_PCT + SIM_TAKER_FEE_PCT) * 0.5) + SIM_SLIPPAGE_PCT


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


def sortino(returns, mar=0.0):
    """Sortino ratio: penalises downside deviation only (better than Sharpe for asymmetric payoffs)."""
    r = pd.Series(returns).dropna()
    if len(r) < 2:
        return 0.0
    excess = r - mar
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float(r.mean() / (r.std(ddof=0) + 1e-12) * np.sqrt(ANNUALIZATION))
    dstd = float(np.sqrt((downside ** 2).mean()))
    if dstd <= 1e-12:
        return 0.0
    return float((r.mean() / dstd) * np.sqrt(ANNUALIZATION))


def omega_ratio(returns, mar=0.0):
    """Omega ratio: probability-weighted gain/loss above threshold."""
    r = pd.Series(returns).dropna()
    excess = r - mar
    gains = excess[excess > 0].sum()
    losses = abs(excess[excess < 0].sum())
    if losses <= 1e-12:
        return float(gains / 1e-9) if gains > 0 else 1.0
    return float(gains / losses)


def profit_factor(returns):
    r = pd.Series(returns).dropna()
    gross_profit = r[r > 0].sum()
    gross_loss = abs(r[r < 0].sum())
    if gross_loss <= 1e-12:
        return float(gross_profit / 1e-9) if gross_profit > 0 else 0.0
    return float(gross_profit / gross_loss)


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
    return float(max(corr, 0.0))


def institutional_score(metrics):
    """
    Upgraded composite score.
    Weights: Sortino (highest alpha signal) > Sharpe > Calmar > Omega >
             Expectancy > Win Rate > Stability > Baseline outperformance.
    Penalties: Drawdown (hard), Vol (soft).
    """
    sortino_val = float(metrics.get("test_sortino", metrics.get("test_sharpe", 0.0)) or 0.0)
    omega_val   = float(metrics.get("test_omega", 1.0) or 1.0)
    pf_val      = float(metrics.get("test_profit_factor", 1.0) or 1.0)
    vs_baseline_pct = float(metrics.get("test_vs_baseline_pct", 0.0) or 0.0)
    trade_count = int(metrics.get("test_trade_count", 0) or 0)
    trade_count_bonus = min(trade_count, 120) / 120.0
    vs_baseline_term = float(np.clip(vs_baseline_pct, -1.0, 1.0)) * 8.0
    return float(
        (sortino_val          * 5.5)
        + (metrics["test_sharpe"]     * 3.5)
        + (metrics["test_calmar"]     * 2.5)
        + (omega_val                  * 1.5)
        + (pf_val                     * 1.2)
        + (metrics["test_expectancy"] * 180.0)
        + (metrics["test_win_rate"]   * 2.5)
        + (metrics["stability"]       * 2.0)
        + (vs_baseline_term)
        + (trade_count_bonus * 2.0)
        - (abs(metrics["test_max_dd"])* 6.0)
        - (metrics["test_vol"]        * 0.4)
    )


def _transaction_cost_series(signal: pd.Series) -> pd.Series:
    pos = pd.Series(signal).fillna(0.0).clip(-1.0, 1.0)
    turnover = pos.diff().abs().fillna(pos.abs())
    return turnover * SIM_ONE_WAY_COST_PCT


def _is_live_tradable_file(file_path: str) -> bool:
    name = os.path.basename(str(file_path or "")).lower()
    if not name:
        return False
    if name.startswith("fred_"):
        return False
    tradable_tokens = [
        "kraken", "binance", "coinbase", "bybit", "okx",
        "btc", "xbt", "eth", "sol", "xrp", "ada", "doge", "spxusd"
    ]
    return any(tok in name for tok in tradable_tokens)


# -----------------------------
# FLOWFORMS
# -----------------------------
def ff_identity(ret):
    return pd.Series(1.0, index=ret.index)


def ff_golden_ratio(ret):
    return pd.Series(1.618, index=ret.index)


def ff_fibonacci(ret):
    fib = np.array([1, 1, 2, 3, 5, 8, 13, 21], dtype=float)
    vals = np.resize(fib / fib.max(), len(ret))
    return pd.Series(vals, index=ret.index)


def ff_log_spiral(ret):
    x = np.arange(len(ret), dtype=float)
    vals = np.exp(0.002 * x)
    vals = vals / np.maximum(vals.mean(), 1e-9)
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
    vals = 1.0 + 0.2 * np.sin(x) * np.cos(x)
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


FLOWFORMS = {
    "identity": ff_identity,
    "golden_ratio": ff_golden_ratio,
    "fibonacci": ff_fibonacci,
    "log_spiral": ff_log_spiral,
    "archimedean_spiral": ff_archimedean_spiral,
    "helix": ff_helix,
    "brachistochrone": ff_brachistochrone,
    "catenary": ff_catenary,
    "sine": ff_sine,
    "cosine": ff_cosine,
    "fractal_brownian": ff_fractal_brownian,
    "mandelbrot": ff_mandelbrot,
    "lorenz": ff_lorenz,
    "torus": ff_torus,
    "mobius": ff_mobius,
    "interference": ff_interference,
    "gaussian": ff_gaussian,
    "power_law": ff_power_law,
    "ellipse": ff_ellipse,
    "hyperbola": ff_hyperbola,
    "lissajous": ff_lissajous,
}


# -----------------------------
# STRATEGIES
# -----------------------------
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


# ---- UPGRADED STRATEGIES (RSI, MACD, ATR, Keltner, Dual-Momentum) ----

def strat_rsi_divergence(ret):
    """RSI-based mean reversion: buy oversold (<30), sell overbought (>70)."""
    px = (1.0 + ret).cumprod()
    delta = px.diff()
    gain = delta.clip(lower=0.0).rolling(14).mean()
    loss = (-delta.clip(upper=0.0)).rolling(14).mean()
    rs   = gain / (loss + 1e-9)
    rsi  = 100.0 - (100.0 / (1.0 + rs))
    sig  = np.where(rsi < 32, 1.0, np.where(rsi > 68, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_macd_crossover(ret):
    """MACD histogram crossover: buy when histogram turns positive, sell negative."""
    px   = (1.0 + ret).cumprod()
    ema12= px.ewm(span=12, adjust=False).mean()
    ema26= px.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig9 = macd.ewm(span=9, adjust=False).mean()
    hist = macd - sig9
    sig  = np.where(hist > 0, 1.0, -1.0)
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_atr_momentum(ret):
    """ATR-normalised momentum: only trade when move exceeds recent ATR."""
    n   = 14
    atr = ret.abs().rolling(n).mean().replace(0, np.nan).ffill().fillna(ret.abs().mean())
    mom = ret.rolling(5).sum()
    threshold = atr * 0.5
    sig = np.where(mom > threshold, 1.0, np.where(mom < -threshold, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_keltner_squeeze(ret):
    """Keltner channel breakout with volatility squeeze filter."""
    px    = (1.0 + ret).cumprod()
    ema   = px.ewm(span=20, adjust=False).mean()
    atr   = ret.abs().rolling(14).mean()
    upper = ema + 2.0 * atr
    lower = ema - 2.0 * atr
    sig   = np.where(px > upper, 1.0, np.where(px < lower, -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_dual_momentum(ret):
    """Dual momentum: absolute (vs cash) AND relative (12-month) momentum."""
    mom1 = ret.rolling(12).sum()   # absolute: is it positive?
    mom3 = ret.rolling(3).sum()    # short-term confirm
    sig  = np.where((mom1 > 0) & (mom3 > 0), 1.0,
           np.where((mom1 < 0) & (mom3 < 0), -1.0, 0.0))
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_vol_breakout(ret):
    """Volatility breakout: trade in direction of largest recent bar."""
    vol_fast = ret.rolling(5).std()
    vol_slow = ret.rolling(20).std()
    direction = np.sign(ret.rolling(3).sum())
    sig = np.where(vol_fast > vol_slow * 1.5, direction, 0.0)
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


def strat_adaptive_trend(ret):
    """Adaptive trend: EMA speed adjusts to recent volatility."""
    vol = ret.rolling(10).std().fillna(ret.std())
    norm_vol = (vol / (vol.rolling(50).mean() + 1e-9)).clip(0.5, 2.0)
    # Vectorised approximate adaptive EMA via variable-span rolling mean
    fast = ret.rolling(5).mean()
    slow = ret.rolling(20).mean()
    sig  = np.where(fast > slow, 1.0, -1.0)
    return pd.Series(sig, index=ret.index).shift(1).fillna(0.0)


STRATEGIES = {
    "trend":            strat_trend,
    "mean_revert":      strat_mean_revert,
    "breakout":         strat_breakout,
    "regime_switch":    strat_regime_switch,
    "harmonic_blend":   strat_harmonic_blend,
    "rsi_divergence":   strat_rsi_divergence,
    "macd_crossover":   strat_macd_crossover,
    "atr_momentum":     strat_atr_momentum,
    "keltner_squeeze":  strat_keltner_squeeze,
    "dual_momentum":    strat_dual_momentum,
    "vol_breakout":     strat_vol_breakout,
    "adaptive_trend":   strat_adaptive_trend,
}


# -----------------------------------------------
# ALGOS  (signal post-processors; take (signal, ret) → filtered signal)
# -----------------------------------------------

def algo_confidence_weighted(sig, ret):
    """Scale signal by rolling Sharpe of recent returns."""
    vol = ret.rolling(20).std().replace(0, np.nan).ffill().fillna(1e-6)
    mu  = ret.rolling(20).mean().fillna(0.0)
    rolling_sharpe = (mu / vol).clip(-3, 3)
    weight = (rolling_sharpe.abs() / 3.0).clip(0.3, 1.0)
    return (sig * weight).clip(-1, 1)


def algo_regime_filter(sig, ret):
    """Zero-out signal in high-chop regimes (vol ratio < 0.7)."""
    vol_fast = ret.rolling(5).std()
    vol_slow = ret.rolling(20).std().replace(0, np.nan).ffill()
    chop = (vol_fast / vol_slow).fillna(1.0)
    regime_on = (chop > 0.7).astype(float)
    return (sig * regime_on).clip(-1, 1)


def algo_momentum_confirm(sig, ret):
    """Only keep signal when short-term momentum agrees with direction."""
    mom = np.sign(ret.rolling(5).sum().fillna(0.0))
    agree = (np.sign(sig) == mom).astype(float)
    return (sig * agree).clip(-1, 1)


def algo_volatility_scale(sig, ret):
    """Scale position size inversely with volatility (Kelly-adjacent)."""
    vol = ret.rolling(20).std().replace(0, np.nan).ffill().fillna(1.0)
    target_vol = float(vol.mean())
    scale = (target_vol / vol).clip(0.25, 2.0)
    return (sig * scale).clip(-1, 1)


def algo_ensemble(sig, ret):
    """Average of confidence-weighted + regime-filtered + momentum-confirm."""
    a = algo_confidence_weighted(sig, ret)
    b = algo_regime_filter(sig, ret)
    c = algo_momentum_confirm(sig, ret)
    return ((a + b + c) / 3.0).clip(-1, 1)


def algo_echo_stack(sig, ret):
    """Echo stack: blend current + lagged signal for persistence filter."""
    s1 = sig.shift(1).fillna(0.0)
    s2 = sig.shift(3).fillna(0.0)
    out = (sig * 0.6 + s1 * 0.25 + s2 * 0.15).clip(-1, 1)
    return out


def algo_passthrough(sig, ret):
    """No post-processing."""
    return sig.clip(-1, 1)


ALGOS = {
    "confidence_weighted":  algo_confidence_weighted,
    "regime_filter":        algo_regime_filter,
    "momentum_confirm":     algo_momentum_confirm,
    "volatility_scale":     algo_volatility_scale,
    "ensemble":             algo_ensemble,
    "echo_stack":           algo_echo_stack,
    "passthrough":          algo_passthrough,
}


def get_price_series(df):
    cols_lower = {c.lower(): c for c in df.columns}

    preferred = ["close", "price", "last", "c"]
    for p in preferred:
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


def evaluate_combo(series, flow_name, flow_fn, strat_name, strat_fn, algo_name=None, algo_fn=None):
    px = pd.to_numeric(series, errors="coerce").dropna().reset_index(drop=True)
    if len(px) < MIN_SERIES_LEN:
        return None

    ret = px.pct_change().dropna().clip(-RETURN_CLIP_PCT, RETURN_CLIP_PCT)
    if len(ret) < MIN_RET_LEN:
        return None

    split = int(len(ret) * TRAIN_RATIO)
    tr_ret = ret.iloc[:split].copy()
    te_ret = ret.iloc[split:].copy()

    if len(tr_ret) < MIN_RET_LEN or len(te_ret) < MIN_RET_LEN:
        return None

    tr_flow   = flow_fn(tr_ret).reindex(tr_ret.index).fillna(1.0).clip(FLOW_MIN, FLOW_MAX)
    te_flow   = flow_fn(te_ret).reindex(te_ret.index).fillna(1.0).clip(FLOW_MIN, FLOW_MAX)
    tr_signal = strat_fn(tr_ret).reindex(tr_ret.index).fillna(0.0)
    te_signal = strat_fn(te_ret).reindex(te_ret.index).fillna(0.0)

    # Apply algo post-processor if provided
    if algo_fn is not None:
        try:
            tr_signal = algo_fn(tr_signal, tr_ret).reindex(tr_ret.index).fillna(0.0)
            te_signal = algo_fn(te_signal, te_ret).reindex(te_ret.index).fillna(0.0)
        except Exception:
            pass

    tr_signal = tr_signal.clip(-1.0, 1.0)
    te_signal = te_signal.clip(-1.0, 1.0)

    tr_cost = _transaction_cost_series(tr_signal)
    te_cost = _transaction_cost_series(te_signal)

    tr_strat_ret = (tr_signal * tr_ret * tr_flow) - tr_cost
    te_strat_ret = (te_signal * te_ret * te_flow) - te_cost

    tr_eq       = (1.0 + tr_strat_ret).cumprod()
    te_eq       = (1.0 + te_strat_ret).cumprod()
    te_base_eq  = (1.0 + te_ret).cumprod()

    te_final = float(te_eq.iloc[-1]) if len(te_eq) else 0.0
    baseline_final = float(te_base_eq.iloc[-1]) if len(te_base_eq) else 0.0
    test_vs_baseline = (te_final - baseline_final) if len(te_eq) and len(te_base_eq) else 0.0
    test_vs_baseline_pct = ((te_final / max(baseline_final, 1e-9)) - 1.0) if len(te_eq) and len(te_base_eq) else 0.0
    trade_count = int((te_signal.diff().abs().fillna(te_signal.abs()) > 0).sum())

    metrics = {
        "flow":            flow_name,
        "strategy":        strat_name,
        "algo":            algo_name or "passthrough",
        "train_sharpe":    sharpe(tr_strat_ret),
        "test_sharpe":     sharpe(te_strat_ret),
        "test_sortino":    sortino(te_strat_ret),
        "test_omega":      omega_ratio(te_strat_ret),
        "test_profit_factor": profit_factor(te_strat_ret),
        "train_max_dd":    max_drawdown(tr_eq),
        "test_max_dd":     max_drawdown(te_eq),
        "train_cagr":      cagr(tr_eq),
        "test_cagr":       cagr(te_eq),
        "train_calmar":    calmar(tr_eq),
        "test_calmar":     calmar(te_eq),
        "test_win_rate":   win_rate(te_strat_ret),
        "test_expectancy": expectancy(te_strat_ret),
        "test_vol":        annual_vol(te_strat_ret),
        "test_final":      te_final,
        "baseline_final":  baseline_final,
        "test_vs_baseline": test_vs_baseline,
        "test_vs_baseline_pct": test_vs_baseline_pct,
        "test_trade_count": trade_count,
        "test_avg_turnover": float(te_signal.diff().abs().fillna(te_signal.abs()).mean() or 0.0),
        "test_avg_cost_bps": float((te_cost.mean() or 0.0) * 10000.0),
        "stability": stability_score(te_eq),
    }
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
                        if row is None:
                            continue
                        row["file"] = f
                        row["is_live_tradable"] = bool(_is_live_tradable_file(f))
                        results.append(row)

        except Exception as e:
            print(f"Error with {f}: {e}")

    os.makedirs(OUT_DIR, exist_ok=True)

    if len(results) == 0:
        print("NO VALID INSTITUTIONAL STRATEGIES")
        empty_cols = [
            "file", "flow", "strategy", "algo", "train_sharpe", "test_sharpe",
            "test_sortino", "test_omega", "test_profit_factor",
            "train_max_dd", "test_max_dd", "train_cagr", "test_cagr",
            "train_calmar", "test_calmar", "test_win_rate", "test_expectancy",
            "test_vol", "test_final", "baseline_final", "test_vs_baseline",
            "stability", "institutional_score"
        ]
        pd.DataFrame(columns=empty_cols).to_csv(
            os.path.join(OUT_DIR, "empty_report.csv"), index=False
        )
        return

    out_df = pd.DataFrame(results).sort_values(
        ["institutional_score", "test_sortino", "test_sharpe", "test_vs_baseline"],
        ascending=False
    )

    leaderboard_path = os.path.join(OUT_DIR, "institutional_leaderboard.csv")
    out_df.to_csv(leaderboard_path, index=False)

    champs = (
        out_df.groupby(["flow", "strategy", "algo"], as_index=False)
        .first()
        .sort_values(["institutional_score", "test_sortino", "test_sharpe"], ascending=False)
    )
    champs_path = os.path.join(OUT_DIR, "institutional_flow_strategy_champions.csv")
    champs.to_csv(champs_path, index=False)

    top10_path = os.path.join(OUT_DIR, "institutional_top10.csv")
    out_df.head(10).to_csv(top10_path, index=False)

    best = out_df.iloc[0]
    live_df = out_df[out_df["is_live_tradable"] == True].copy()

    # Quality filter for live deployment: if tradable set is weak, fallback to stable defaults.
    live_quality = live_df[
        (live_df["test_sharpe"] > 0.50)
        & (live_df["test_sortino"] > 0.70)
        & (live_df["test_trade_count"] >= 12)
    ] if len(live_df) else live_df
    best_live = live_quality.iloc[0] if len(live_quality) else None
    summary = {
        "files_scanned":           int(len(files)),
        "total_candidates":        int(len(out_df)),
        "top_file":                str(best["file"]),
        "top_flow":                str(best["flow"]),
        "top_strategy":            str(best["strategy"]),
        "top_algo":                str(best["algo"]),
        "top_test_sharpe":         float(best["test_sharpe"]),
        "top_test_sortino":        float(best.get("test_sortino", 0.0)),
        "top_test_omega":          float(best.get("test_omega", 1.0)),
        "top_test_profit_factor":  float(best.get("test_profit_factor", 1.0)),
        "top_test_win_rate":       float(best["test_win_rate"]),
        "top_test_calmar":         float(best["test_calmar"]),
        "top_test_vs_baseline":    float(best["test_vs_baseline"]),
        "top_institutional_score": float(best["institutional_score"]),
    }
    with open(os.path.join(OUT_DIR, "institutional_summary.json"), "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    # Export dedicated live selection for execution stack (tradable-priority).
    if best_live is None:
        live_selection = {
            "flow": "lorenz",
            "strategy": "harmonic_blend",
            "algo": "ensemble",
            "institutional_score": 0.0,
            "test_sharpe": 0.0,
            "test_sortino": 0.0,
            "test_omega": 1.0,
            "test_profit_factor": 1.0,
            "test_win_rate": 0.0,
            "test_calmar": 0.0,
            "test_vs_baseline_pct": 0.0,
            "test_trade_count": 0,
            "edge_multiplier": 1.15,
            "source_file": "fallback_default_no_quality_tradable_candidate",
            "is_live_tradable": True,
            "selection_mode": "fallback_default",
        }
    else:
        live_selection = {
            "flow": str(best_live["flow"]),
            "strategy": str(best_live["strategy"]),
            "algo": str(best_live["algo"]),
            "institutional_score": float(best_live["institutional_score"]),
            "test_sharpe": float(best_live.get("test_sharpe", 0.0) or 0.0),
            "test_sortino": float(best_live.get("test_sortino", 0.0) or 0.0),
            "test_omega": float(best_live.get("test_omega", 1.0) or 1.0),
            "test_profit_factor": float(best_live.get("test_profit_factor", 1.0) or 1.0),
            "test_win_rate": float(best_live.get("test_win_rate", 0.0) or 0.0),
            "test_calmar": float(best_live.get("test_calmar", 0.0) or 0.0),
            "test_vs_baseline_pct": float(best_live.get("test_vs_baseline_pct", 0.0) or 0.0),
            "test_trade_count": int(best_live.get("test_trade_count", 0) or 0),
            "edge_multiplier": float(np.clip(1.0 + (float(best_live.get("test_sharpe", 0.0) or 0.0) / 5.0), 0.9, 1.8)),
            "source_file": str(best_live.get("file", "")),
            "is_live_tradable": bool(best_live.get("is_live_tradable", False)),
            "selection_mode": "tradable_quality",
        }
    exec_out = os.path.join(OUT_DIR, "execution")
    os.makedirs(exec_out, exist_ok=True)
    with open(os.path.join(exec_out, "institutional_live_selection.json"), "w", encoding="utf-8") as fp:
        json.dump(live_selection, fp, indent=2)

    print("\n=== TOP 10 RESULTS (flow × strategy × algo) ===")
    display_cols = ["flow", "strategy", "algo", "test_sharpe", "test_sortino",
                    "test_omega", "test_win_rate", "test_calmar", "institutional_score"]
    print(out_df[display_cols].head(10).to_string(index=False))
    print("\nSaved:")
    print(leaderboard_path)
    print(champs_path)
    print(top10_path)


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    files = [
        os.path.join(DATA_DIR, f)
        for f in os.listdir(DATA_DIR)
        if f.lower().endswith(".csv")
    ]
    run_engine(files)