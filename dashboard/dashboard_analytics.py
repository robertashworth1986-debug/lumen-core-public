import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objs as go
import plotly.io as pio


STARTING_CAPITAL_USD = 100000.0


def load_trade_log(path: str) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return pd.DataFrame()

    if not isinstance(data, list):
        return pd.DataFrame()
    return pd.DataFrame(data)


def _select_closed(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "status" not in df.columns:
        return df.copy()
    return df[df["status"].astype(str).str.upper() == "CLOSED"].copy()


def _numeric_series(df: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for col in candidates:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").dropna().reset_index(drop=True)
            if not values.empty:
                return values
    return pd.Series(dtype=float)


def _annualized_sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    returns = pd.to_numeric(returns, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if len(returns) < 2:
        return 0.0
    sigma = float(returns.std(ddof=1))
    if not np.isfinite(sigma) or sigma <= 0:
        return 0.0
    mu = float(returns.mean())
    return float((mu / sigma) * np.sqrt(periods_per_year))


def _max_drawdown_pct(equity: pd.Series) -> float:
    equity = pd.to_numeric(equity, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if equity.empty:
        return 0.0
    dd = (equity / equity.cummax()) - 1.0
    return float(dd.min() * 100.0)


def _build_equity_curve(df_closed: pd.DataFrame, pnl: pd.Series) -> pd.Series:
    if "equity_usd" in df_closed.columns:
        eq = pd.to_numeric(df_closed["equity_usd"], errors="coerce").dropna().reset_index(drop=True)
        if not eq.empty:
            return eq
    return STARTING_CAPITAL_USD + pnl.cumsum()


def compute_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    df_closed = _select_closed(df)
    pnl = _numeric_series(df_closed, ["net_pnl", "pnl_usd", "realized_pnl_usd"])
    if pnl.empty:
        return {
            "total_trades": float(len(df)),
            "closed_trades": float(len(df_closed)),
            "win_rate": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "total_pnl": 0.0,
        }

    returns = _numeric_series(df_closed, ["net_pnl_pct"]) / 100.0
    if returns.empty:
        equity_tmp = STARTING_CAPITAL_USD + pnl.cumsum()
        returns = equity_tmp.pct_change().replace([np.inf, -np.inf], np.nan).dropna()

    equity = _build_equity_curve(df_closed, pnl)
    drawdown_usd = float((equity.cummax() - equity).max()) if not equity.empty else 0.0

    return {
        "total_trades": float(len(df)),
        "closed_trades": float(len(df_closed)),
        "win_rate": float((pnl > 0).mean() * 100.0),
        "sharpe": _annualized_sharpe(returns),
        "max_drawdown": drawdown_usd,
        "max_drawdown_pct": _max_drawdown_pct(equity),
        "total_pnl": float(pnl.sum()),
    }


def plot_equity_curve(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    df_closed = _select_closed(df)
    pnl = _numeric_series(df_closed, ["net_pnl", "pnl_usd", "realized_pnl_usd"])
    if pnl.empty:
        return None

    equity = _build_equity_curve(df_closed, pnl)
    fig = go.Figure()
    x_col = "exit_time" if "exit_time" in df_closed.columns else "timestamp"
    x_vals = df_closed[x_col] if x_col in df_closed.columns else list(range(len(equity)))
    fig.add_trace(go.Scatter(x=x_vals, y=equity, mode="lines", name="Equity Curve"))
    fig.update_layout(title="Equity Curve", xaxis_title="Time", yaxis_title="Equity (USD)", template="plotly_dark")
    return pio.to_html(fig, full_html=False)


def main() -> None:
    trade_log_path = str(Path(__file__).parent.parent / "out" / "execution" / "trade_log.json")
    df = load_trade_log(trade_log_path)
    metrics = compute_metrics(df)

    html_sections = []
    html_sections.append('<h1 style="text-align:center;">Institutional Trading Advanced Analytics Dashboard</h1>')
    html_sections.append('<h3>Key Metrics</h3><ul>')
    for key, value in metrics.items():
        html_sections.append(f'<li><b>{key.replace("_", " ").title()}:</b> {value:.4f}</li>')
    html_sections.append('</ul>')

    equity_html = plot_equity_curve(df)
    if equity_html:
        html_sections.append('<h3>Equity Curve</h3>')
        html_sections.append(equity_html)

    if not df.empty and "symbol" in df.columns:
        sector_counts = df["symbol"].value_counts()
        sector_fig = go.Figure([go.Bar(x=sector_counts.index, y=sector_counts.values)])
        sector_fig.update_layout(title="Trade Count by Asset/Sector", xaxis_title="Symbol", yaxis_title="Trades", template="plotly_dark")
        html_sections.append('<h3>Trade Count by Asset/Sector</h3>')
        html_sections.append(pio.to_html(sector_fig, full_html=False))

    if not df.empty:
        df_closed = _select_closed(df)
        pnl = _numeric_series(df_closed, ["net_pnl", "pnl_usd", "realized_pnl_usd"])
        if not pnl.empty:
            pnl_fig = go.Figure([go.Histogram(x=pnl, nbinsx=30)])
            pnl_fig.update_layout(title="PnL Distribution", xaxis_title="Net PnL", yaxis_title="Frequency", template="plotly_dark")
            html_sections.append('<h3>PnL Distribution</h3>')
            html_sections.append(pio.to_html(pnl_fig, full_html=False))

    if not df.empty and "entry_time" in df.columns and "exit_time" in df.columns:
        try:
            entry = pd.to_datetime(df["entry_time"])
            exit_ = pd.to_datetime(df["exit_time"])
            duration = (exit_ - entry).dt.total_seconds() / 60.0
            duration_fig = go.Figure([go.Histogram(x=duration, nbinsx=30)])
            duration_fig.update_layout(title="Trade Duration (minutes)", xaxis_title="Duration (min)", yaxis_title="Frequency", template="plotly_dark")
            html_sections.append('<h3>Trade Duration Distribution</h3>')
            html_sections.append(pio.to_html(duration_fig, full_html=False))
        except Exception:
            pass

    if not df.empty and "exit_time" in df.columns:
        df_closed = _select_closed(df).copy()
        if not df_closed.empty:
            returns = _numeric_series(df_closed, ["net_pnl_pct"]) / 100.0
            if returns.empty:
                pnl = _numeric_series(df_closed, ["net_pnl", "pnl_usd", "realized_pnl_usd"])
                if not pnl.empty:
                    equity = STARTING_CAPITAL_USD + pnl.cumsum()
                    returns = equity.pct_change().replace([np.inf, -np.inf], np.nan).dropna().reset_index(drop=True)

            if len(returns) >= 5:
                df_closed = df_closed.tail(len(returns)).copy()
                df_closed["returns"] = returns.values
                df_closed["exit_time"] = pd.to_datetime(df_closed["exit_time"])
                df_closed = df_closed.sort_values("exit_time")
                roll_mean = df_closed["returns"].rolling(window=10, min_periods=5).mean()
                roll_std = df_closed["returns"].rolling(window=10, min_periods=5).std(ddof=1)
                rolling_sharpe = np.where(roll_std > 0, (roll_mean / roll_std) * np.sqrt(252), np.nan)
                regime_fig = go.Figure([go.Scatter(x=df_closed["exit_time"], y=rolling_sharpe, mode="lines", name="Rolling Sharpe")])
                regime_fig.update_layout(title="Rolling Sharpe Ratio (Regime Proxy)", xaxis_title="Time", yaxis_title="Sharpe", template="plotly_dark")
                html_sections.append('<h3>Regime/Rotation Detection</h3>')
                html_sections.append(pio.to_html(regime_fig, full_html=False))

    if not df.empty:
        html_sections.append('<h3>Recent Trades</h3>')
        table_cols = ["symbol", "side", "entry_time", "exit_time", "net_pnl", "net_pnl_pct", "status"]
        table_cols = [col for col in table_cols if col in df.columns]
        table_df = df[table_cols].tail(30).copy()
        html_sections.append('<div style="overflow-x:auto;">' + table_df.to_html(index=False, classes="table table-striped", border=0) + '</div>')

    css = '''<style>
    body { background: #181818; color: #f0f0f0; font-family: 'Segoe UI', Arial, sans-serif; }
    h1, h2, h3 { color: #00bfff; }
    ul { font-size: 1.1em; }
    .table { background: #222; color: #f0f0f0; border-radius: 8px; }
    .table th { background: #333; color: #00bfff; }
    .table-striped tr:nth-child(even) { background: #232323; }
    </style>'''

    output_path = Path(__file__).parent / "dashboard_analytics.html"
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("<html><head><title>Advanced Trading Dashboard</title>" + css + "</head><body>")
        for section in html_sections:
            handle.write(section)
        handle.write("</body></html>")


if __name__ == "__main__":
    main()
