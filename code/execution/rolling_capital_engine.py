# rolling_capital_engine.py
"""
Live rolling capital engine: pulls live OHLCV, runs multi-family strategies, outputs best edge for orchestrator.
"""
import pandas as pd
import json
import time
from pathlib import Path
try:
    from .capital_engine_core import build_families, stats, build_strategy_returns, safe_series
except ImportError:  # Script/path-based loading without changing global import paths.
    import importlib.util
    _core_spec = importlib.util.spec_from_file_location(
        "_lumencore_capital_engine_core", Path(__file__).with_name("capital_engine_core.py")
    )
    _core = importlib.util.module_from_spec(_core_spec)
    _core_spec.loader.exec_module(_core)
    build_families = _core.build_families
    stats = _core.stats
    build_strategy_returns = _core.build_strategy_returns
    safe_series = _core.safe_series

OUT = Path(r"C:/LumaTrader/rolling_capital")

SYMBOL = "BTC/USD"
TIMEFRAME = "1h"
LIMIT = 2500

FAMILIES = {}

# --- Live data pull (no fallback) ---
def fetch_live_ohlcv(symbol=SYMBOL, timeframe=TIMEFRAME, limit=LIMIT):
    import ccxt
    ex = ccxt.kraken({"enableRateLimit": True})
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df["ret"] = df["close"].pct_change(fill_method=None).fillna(0.0)
    return df

# --- Main loop: always live, always hunting ---
def rolling_capital_engine():
    OUT.mkdir(parents=True, exist_ok=True)
    while True:
        df = fetch_live_ohlcv()
        families = build_families(df)
        ret = df["ret"]
        rows = []
        for family, signal in families.items():
            strat, pos, turnover = build_strategy_returns(signal, ret)
            m = stats(strat)
            m["family"] = family
            m["avg_monthly_turnover"] = float(turnover.mean() * 24 * 30)
            rows.append(m)
        leaderboard = pd.DataFrame(rows).sort_values(["sharpe", "calmar", "cagr"], ascending=[False, False, False]).reset_index(drop=True)
        best_family = leaderboard.iloc[0]["family"]
        best_metrics = leaderboard.iloc[0].to_dict()
        # Output best edge for orchestrator
        (OUT / "rolling_capital_best.json").write_text(json.dumps({"family": best_family, "metrics": best_metrics}, indent=2), encoding="utf-8")
        print(f"[ROLLING CAPITAL] Best family: {best_family} Sharpe: {best_metrics['sharpe']:.3f} Win: {best_metrics['win_rate']:.2%}")
        time.sleep(60)  # Update every 60s

if __name__ == "__main__":
    rolling_capital_engine()
