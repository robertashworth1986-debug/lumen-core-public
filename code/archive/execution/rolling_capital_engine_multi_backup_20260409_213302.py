# rolling_capital_engine_multi.py
"""
Multi-asset rolling capital engine: scans all major assets, runs multi-family strategies, outputs best edge and heatmap for orchestrator.
"""
import numpy as np
import pandas as pd
import ccxt
from pathlib import Path
import json
import time

OUT = Path(r"C:/LumaTrader/rolling_capital")
OUT.mkdir(parents=True, exist_ok=True)

SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "XRP/USD", "DOGE/USD"]
TIMEFRAME = "1h"
LIMIT = 2500

# --- Live data pull (no fallback) ---
def fetch_live_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT):
    ex = ccxt.kraken({"enableRateLimit": True})
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df["ret"] = df["close"].pct_change().fillna(0.0)
    return df

# --- Strategy families (same as before) ---
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
    strat = strat.clip(-0.20, 0.20)
    return strat, pos, turnover

# --- Main loop: scan all assets, output best edge and heatmap ---
def rolling_capital_engine_multi():
    while True:
        all_rows = []
        heatmap = []
        for symbol in SYMBOLS:
            try:
                df = fetch_live_ohlcv(symbol)
                families = build_families(df)
                ret = df["ret"]
                for family, signal in families.items():
                    strat, pos, turnover = build_strategy_returns(signal, ret)
                    m = stats(strat)
                    m["family"] = family
                    m["symbol"] = symbol
                    m["avg_monthly_turnover"] = float(turnover.mean() * 24 * 30)
                    all_rows.append(m)
                    heatmap.append({"symbol": symbol, "family": family, "sharpe": m["sharpe"], "win_rate": m["win_rate"], "cagr": m["cagr"]})
            except Exception as e:
                print(f"[ERROR] {symbol}: {e}")
        leaderboard = pd.DataFrame(all_rows).sort_values(["sharpe", "calmar", "cagr"], ascending=[False, False, False]).reset_index(drop=True)
        best = leaderboard.iloc[0]
        best_metrics = best.to_dict()
        best_family = best["family"]
        best_symbol = best["symbol"]
        # Output best edge and full heatmap
        (OUT / "rolling_capital_best_multi.json").write_text(json.dumps({"symbol": best_symbol, "family": best_family, "metrics": best_metrics}, indent=2), encoding="utf-8")
        (OUT / "rolling_capital_heatmap.json").write_text(json.dumps(heatmap, indent=2), encoding="utf-8")
        print(f"[ROLLING CAPITAL MULTI] Best: {best_symbol} {best_family} Sharpe: {best_metrics['sharpe']:.3f} Win: {best_metrics['win_rate']:.2%}")
        time.sleep(60)

if __name__ == "__main__":
    rolling_capital_engine_multi()
