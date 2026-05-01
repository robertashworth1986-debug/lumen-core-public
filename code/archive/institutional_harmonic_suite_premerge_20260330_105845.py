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
    return float(max(corr, 0.0))


def institutional_score(metrics):
    return float(
        (metrics["test_sharpe"] * 4.0)
        + (metrics["test_calmar"] * 2.0)
        + (metrics["test_expectancy"] * 150.0)
        + (metrics["test_win_rate"] * 2.0)
        + (metrics["stability"] * 1.5)
        + (metrics["test_vs_baseline"] * 3.0)
        - (abs(metrics["test_max_dd"]) * 5.0)
        - (metrics["test_vol"] * 0.5)
    )


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


STRATEGIES = {
    "trend": strat_trend,
    "mean_revert": strat_mean_revert,
    "breakout": strat_breakout,
    "regime_switch": strat_regime_switch,
    "harmonic_blend": strat_harmonic_blend,
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


def evaluate_combo(series, flow_name, flow_fn, strat_name, strat_fn):
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

    tr_flow = flow_fn(tr_ret).reindex(tr_ret.index).fillna(1.0)
    te_flow = flow_fn(te_ret).reindex(te_ret.index).fillna(1.0)

    tr_signal = strat_fn(tr_ret).reindex(tr_ret.index).fillna(0.0)
    te_signal = strat_fn(te_ret).reindex(te_ret.index).fillna(0.0)

    tr_strat_ret = tr_signal * tr_ret * tr_flow
    te_strat_ret = te_signal * te_ret * te_flow

    tr_eq = (1.0 + tr_strat_ret).cumprod()
    te_eq = (1.0 + te_strat_ret).cumprod()
    te_base_eq = (1.0 + te_ret).cumprod()

    metrics = {
        "flow": flow_name,
        "strategy": strat_name,
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
        "test_vs_baseline": (
            float(te_eq.iloc[-1]) - float(te_base_eq.iloc[-1])
            if len(te_eq) and len(te_base_eq) else 0.0
        ),
        "stability": stability_score(te_eq),
    }

    metrics["institutional_score"] = institutional_score(metrics)

    return metrics

FLOWFORMS = {
    "raw": lambda x: x,

    "log_returns": lambda x: np.log1p(x),

    "sqrt_flow": lambda x: np.sign(x) * np.sqrt(np.abs(x)),

    "square_flow": lambda x: x**2 * np.sign(x),

    "cube_flow": lambda x: x**3,

    "tanh_flow": lambda x: np.tanh(x),

    "sigmoid_flow": lambda x: 1 / (1 + np.exp(-x)),

    "zscore_flow": lambda x: (x - np.mean(x)) / (np.std(x) + 1e-9),

    "ema_flow": lambda x: pd.Series(x).ewm(span=10).mean().values,

    "double_ema": lambda x: pd.Series(x).ewm(span=5).mean().ewm(span=5).mean().values,

    "volatility_scaled": lambda x: x / (np.std(x) + 1e-9),

    "cumulative_flow": lambda x: np.cumsum(x),

    "diff_flow": lambda x: np.diff(np.insert(x, 0, 0)),

    "sin_wave": lambda x: np.sin(x),

    "cos_wave": lambda x: np.cos(x),

    "spiral_decay": lambda x: x * np.exp(-np.linspace(0,1,len(x))),

    "fibonacci_weighted": lambda x: x * (np.arange(len(x)) / len(x)),

    "golden_ratio": lambda x: x * 1.618,

    "inverse_flow": lambda x: -x,

    "threshold_clip": lambda x: np.clip(x, -0.02, 0.02),
}
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
                    row = evaluate_combo(series, flow_name, flow_fn, strat_name, strat_fn)
                    if row is None:
                        continue
                    row["file"] = f
                    results.append(row)

        except Exception as e:
            print(f"Error with {f}: {e}")

    os.makedirs(OUT_DIR, exist_ok=True)

    if len(results) == 0:
        print("NO VALID INSTITUTIONAL STRATEGIES")
        empty_cols = [
            "file", "flow", "strategy", "train_sharpe", "test_sharpe",
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
        ["institutional_score", "test_sharpe", "test_vs_baseline"],
        ascending=False
    )

    leaderboard_path = os.path.join(OUT_DIR, "institutional_leaderboard.csv")
    out_df.to_csv(leaderboard_path, index=False)

    champs = (
        out_df.groupby(["flow", "strategy"], as_index=False)
        .first()
        .sort_values(["institutional_score", "test_sharpe"], ascending=False)
    )
    champs_path = os.path.join(OUT_DIR, "institutional_flow_strategy_champions.csv")
    champs.to_csv(champs_path, index=False)

    top10_path = os.path.join(OUT_DIR, "institutional_top10.csv")
    out_df.head(10).to_csv(top10_path, index=False)

    summary = {
        "files_scanned": int(len(files)),
        "total_candidates": int(len(out_df)),
        "top_file": str(out_df.iloc[0]["file"]),
        "top_flow": str(out_df.iloc[0]["flow"]),
        "top_strategy": str(out_df.iloc[0]["strategy"]),
        "top_test_sharpe": float(out_df.iloc[0]["test_sharpe"]),
        "top_test_vs_baseline": float(out_df.iloc[0]["test_vs_baseline"]),
        "top_institutional_score": float(out_df.iloc[0]["institutional_score"]),
    }
    with open(os.path.join(OUT_DIR, "institutional_summary.json"), "w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    print("\n=== TOP 10 RESULTS ===")
    print(out_df.head(10).to_string(index=False))
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