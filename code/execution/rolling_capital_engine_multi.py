# rolling_capital_engine_multi.py
"""
Multi-asset rolling capital engine: scans all major assets, runs multi-family strategies, outputs best edge and heatmap for orchestrator.
"""
import pandas as pd
from pathlib import Path
import json
import time
try:
    from .capital_engine_core import build_families, stats, build_strategy_returns, safe_series
except ImportError:  # Direct execution from this directory.
    from capital_engine_core import build_families, stats, build_strategy_returns, safe_series

OUT = Path(r"C:/LumaTrader/rolling_capital")

SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "XRP/USD", "DOGE/USD"]
TIMEFRAME = "1h"
LIMIT = 2500

# --- Live data pull (no fallback) ---
def fetch_live_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT):
    try:
        import ccxt
    except ImportError as exc:
        raise ImportError(
            "ccxt is required for Kraken OHLCV fetch. Install it with `pip install ccxt` "
            "or ensure the virtual environment has ccxt available."
        ) from exc
    ex = ccxt.kraken({"enableRateLimit": True})
    ohlcv = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df["ret"] = df["close"].pct_change(fill_method=None).fillna(0.0)
    return df

# --- Main loop: scan all assets, output best edge and heatmap ---
def rolling_capital_engine_multi():
    OUT.mkdir(parents=True, exist_ok=True)
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
        if not all_rows:
            time.sleep(60)
            continue
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
