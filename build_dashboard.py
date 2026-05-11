import glob
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
DASH = Path(r"C:\LumaTrader\dashboard")
TRADE_LOG_PATH = OUT / "execution" / "trade_log.json"
STARTING_CAPITAL_USD = 100000.0


def load_json(path: str | Path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def _coerce_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def find_latest(pattern: str):
    files = glob.glob(os.path.join(str(OUT), pattern))
    return max(files, key=os.path.getmtime) if files else None


def _pick_numeric_column(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for col in candidates:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").dropna().reset_index(drop=True)
            if not values.empty:
                return values
    return pd.Series(dtype=float)


def load_closed_trades() -> pd.DataFrame:
    if not TRADE_LOG_PATH.exists():
        return pd.DataFrame()

    payload = load_json(TRADE_LOG_PATH)
    if not isinstance(payload, list):
        return pd.DataFrame()

    df = pd.DataFrame(payload)
    if df.empty:
        return df

    if "status" in df.columns:
        closed = df[df["status"].astype(str).str.upper() == "CLOSED"].copy()
        return closed.reset_index(drop=True)

    return df.reset_index(drop=True)


def compute_live_metrics(df_closed: pd.DataFrame) -> dict:
    if df_closed.empty:
        return {
            "equity": pd.Series([STARTING_CAPITAL_USD], dtype=float),
            "sharpe": 0.0,
            "max_drawdown_pct": 0.0,
            "closed_trades": 0,
            "total_pnl_usd": 0.0,
            "data_status": "no_live_trade_data",
        }

    pnl = _pick_numeric_column(df_closed, ["net_pnl", "pnl_usd", "realized_pnl_usd"])
    if pnl.empty:
        return {
            "equity": pd.Series([STARTING_CAPITAL_USD], dtype=float),
            "sharpe": 0.0,
            "max_drawdown_pct": 0.0,
            "closed_trades": int(len(df_closed)),
            "total_pnl_usd": 0.0,
            "data_status": "closed_trades_without_numeric_pnl",
        }

    equity = STARTING_CAPITAL_USD + pnl.cumsum()
    returns = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna()

    sharpe = 0.0
    if len(returns) >= 2:
        stdev = float(returns.std(ddof=1))
        if stdev > 0:
            sharpe = float((returns.mean() / stdev) * np.sqrt(252))

    drawdown_pct = float((((equity / equity.cummax()) - 1.0).min()) * 100.0)

    return {
        "equity": equity,
        "sharpe": sharpe,
        "max_drawdown_pct": drawdown_pct,
        "closed_trades": int(len(df_closed)),
        "total_pnl_usd": float(pnl.sum()),
        "data_status": "live_trade_log",
    }


# --- LOAD DATA ---
champ_path = find_latest("*champion*.json")
champ = load_json(champ_path) if champ_path else {}

trade_df = load_closed_trades()
metrics = compute_live_metrics(trade_df)
equity = metrics["equity"].tolist()

champ_sharpe = _coerce_float(champ.get("sharpe", champ.get("test_sharpe")), metrics["sharpe"])
champ_vs_baseline = _coerce_float(champ.get("vs_baseline", champ.get("test_vs_baseline")), 0.0)

# --- BUILD HTML ---
html = f"""
<html>
<head>
<title>LumenCore Validation Dashboard</title>
<style>
body {{ background:#0b0f14; color:white; font-family:Arial; }}
.card {{ background:#121a24; padding:20px; margin:10px; border-radius:10px; }}
h1 {{ color:#00ffd5; }}
.metric {{ font-size:22px; }}
.green {{ color:#00ff88; }}
.red {{ color:#ff4d4d; }}
.muted {{ color:#9fb4c4; }}
</style>
</head>
<body>

<h1>LumenCore Live Validation</h1>

<div class='card'>
<h2>Strategy Output</h2>
<p>Flow: {champ.get("flow", "N/A")}</p>
<p>Strategy: {champ.get("strategy", "N/A")}</p>
<p>Selected Sharpe: {round(champ_sharpe, 4)}</p>
<p>Vs Baseline: {round(champ_vs_baseline, 2)}%</p>
</div>

<div class='card'>
<h2>Performance Metrics</h2>
<p class='metric'>Sharpe: <span class='green'>{round(metrics['sharpe'], 4)}</span></p>
<p class='metric'>Max Drawdown: <span class='red'>{round(metrics['max_drawdown_pct'], 2)}%</span></p>
<p class='metric'>Closed Trades: {metrics['closed_trades']}</p>
<p class='metric'>Total PnL: <span class='{"green" if metrics['total_pnl_usd'] >= 0 else "red"}'>${round(metrics['total_pnl_usd'], 2)}</span></p>
<p class='muted'>Data source: {metrics['data_status']}</p>
</div>

<div class='card'>
<h2>Equity Curve</h2>
<canvas id='chart'></canvas>
</div>

<div class='card'>
<h2>Execution Logic</h2>
<ul>
<li>Asset: Multi-sector (crypto / macro / infra)</li>
<li>Position sizing: volatility scaled</li>
<li>Entry: signal alignment threshold</li>
<li>Exit: regime shift / decay</li>
</ul>
</div>

<div class='card'>
<h2>Validation Integrity</h2>
<ul>
<li>Live trade log derived metrics only (no synthetic fallback)</li>
<li>No retroactive metric synthesis</li>
<li>Reproducible pipeline</li>
</ul>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
const ctx = document.getElementById('chart');

new Chart(ctx, {{
    type: 'line',
    data: {{
        labels: {list(range(len(equity)))},
        datasets: [{{
            label: 'Equity USD',
            data: {equity},
            borderColor: '#00ffd5',
            tension: 0.1
        }}]
    }}
}});
</script>

</body>
</html>
"""

DASH.mkdir(parents=True, exist_ok=True)
path = DASH / "validation_front_end.html"
with open(path, "w", encoding="utf-8") as handle:
    handle.write(html)

print(str(path))