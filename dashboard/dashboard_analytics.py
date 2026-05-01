import pandas as pd
import numpy as np
import plotly.graph_objs as go
import plotly.io as pio
import json
from pathlib import Path

def load_trade_log(path):
    if not Path(path).exists():
        return pd.DataFrame()
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return pd.DataFrame(data)

def compute_metrics(df):
    if df.empty:
        return {}
    df_closed = df[df['status'].str.upper() == 'CLOSED']
    pnl = df_closed['net_pnl'].astype(float)
    returns = df_closed['net_pnl_pct'].astype(float) / 100.0
    win_rate = (pnl > 0).mean() * 100
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
    drawdown = (df_closed['net_pnl'].cumsum().cummax() - df_closed['net_pnl'].cumsum()).max()
    return {
        'total_trades': len(df),
        'closed_trades': len(df_closed),
        'win_rate': win_rate,
        'sharpe': sharpe,
        'max_drawdown': drawdown,
        'total_pnl': pnl.sum(),
    }

def plot_equity_curve(df):
    if df.empty:
        return None
    df_closed = df[df['status'].str.upper() == 'CLOSED']
    equity = df_closed['net_pnl'].cumsum()
    fig = go.Figure()
    # Use 'exit_time' if present, else fallback to 'timestamp'
    x_col = 'exit_time' if 'exit_time' in df_closed.columns else 'timestamp'
    fig.add_trace(go.Scatter(x=df_closed[x_col], y=equity, mode='lines', name='Equity Curve'))
    fig.update_layout(title='Equity Curve', xaxis_title='Time', yaxis_title='Cumulative PnL (USD)', template='plotly_dark')
    return pio.to_html(fig, full_html=False)

def main():
    trade_log_path = str(Path(__file__).parent.parent / 'out' / 'execution' / 'trade_log.json')
    df = load_trade_log(trade_log_path)
    metrics = compute_metrics(df)

    # Advanced analytics
    html_sections = []
    html_sections.append('<h1 style="text-align:center;">Institutional Trading Advanced Analytics Dashboard</h1>')
    html_sections.append('<h3>Key Metrics</h3><ul>')
    for k, v in metrics.items():
        html_sections.append(f'<li><b>{k.replace("_", " ").title()}:</b> {v:.4f}</li>')
    html_sections.append('</ul>')

    # Equity curve
    equity_html = plot_equity_curve(df)
    if equity_html:
        html_sections.append('<h3>Equity Curve</h3>')
        html_sections.append(equity_html)

    # Sector/asset breakdowns
    if not df.empty and 'symbol' in df.columns:
        sector_counts = df['symbol'].value_counts()
        sector_fig = go.Figure([go.Bar(x=sector_counts.index, y=sector_counts.values)])
        sector_fig.update_layout(title='Trade Count by Asset/Sector', xaxis_title='Symbol', yaxis_title='Trades', template='plotly_dark')
        html_sections.append('<h3>Trade Count by Asset/Sector</h3>')
        html_sections.append(pio.to_html(sector_fig, full_html=False))

    # PnL distribution
    if not df.empty and 'net_pnl' in df.columns:
        pnl_fig = go.Figure([go.Histogram(x=df['net_pnl'].astype(float), nbinsx=30)])
        pnl_fig.update_layout(title='PnL Distribution', xaxis_title='Net PnL', yaxis_title='Frequency', template='plotly_dark')
        html_sections.append('<h3>PnL Distribution</h3>')
        html_sections.append(pio.to_html(pnl_fig, full_html=False))

    # Trade duration histogram
    if not df.empty and 'entry_time' in df.columns and 'exit_time' in df.columns:
        try:
            entry = pd.to_datetime(df['entry_time'])
            exit = pd.to_datetime(df['exit_time'])
            duration = (exit - entry).dt.total_seconds() / 60
            duration_fig = go.Figure([go.Histogram(x=duration, nbinsx=30)])
            duration_fig.update_layout(title='Trade Duration (minutes)', xaxis_title='Duration (min)', yaxis_title='Frequency', template='plotly_dark')
            html_sections.append('<h3>Trade Duration Distribution</h3>')
            html_sections.append(pio.to_html(duration_fig, full_html=False))
        except Exception:
            pass

    # Regime/rotation detection (simple rolling Sharpe as proxy)
    if not df.empty and 'net_pnl_pct' in df.columns and 'exit_time' in df.columns:
        df_closed = df[df['status'].str.upper() == 'CLOSED'].copy()
        df_closed['returns'] = df_closed['net_pnl_pct'].astype(float) / 100.0
        df_closed['exit_time'] = pd.to_datetime(df_closed['exit_time'])
        df_closed = df_closed.sort_values('exit_time')
        df_closed['rolling_sharpe'] = df_closed['returns'].rolling(window=10, min_periods=3).mean() / (df_closed['returns'].rolling(window=10, min_periods=3).std() + 1e-9) * np.sqrt(252)
        regime_fig = go.Figure([go.Scatter(x=df_closed['exit_time'], y=df_closed['rolling_sharpe'], mode='lines', name='Rolling Sharpe')])
        regime_fig.update_layout(title='Rolling Sharpe Ratio (Regime Proxy)', xaxis_title='Time', yaxis_title='Sharpe', template='plotly_dark')
        html_sections.append('<h3>Regime/Rotation Detection</h3>')
        html_sections.append(pio.to_html(regime_fig, full_html=False))

    # Recent trades table (interactive)
    if not df.empty:
        html_sections.append('<h3>Recent Trades</h3>')
        table_cols = ['symbol', 'side', 'entry_time', 'exit_time', 'net_pnl', 'net_pnl_pct', 'status']
        table_cols = [c for c in table_cols if c in df.columns]
        table_df = df[table_cols].tail(30).copy()
        table_html = table_df.to_html(index=False, classes='table table-striped', border=0)
        html_sections.append('<div style="overflow-x:auto;">' + table_html + '</div>')

    # Modern CSS for better visuals
    css = '''<style>
    body { background: #181818; color: #f0f0f0; font-family: 'Segoe UI', Arial, sans-serif; }
    h1, h2, h3 { color: #00bfff; }
    ul { font-size: 1.1em; }
    .table { background: #222; color: #f0f0f0; border-radius: 8px; }
    .table th { background: #333; color: #00bfff; }
    .table-striped tr:nth-child(even) { background: #232323; }
    </style>'''

    output_path = Path(__file__).parent / 'dashboard_analytics.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<html><head><title>Advanced Trading Dashboard</title>' + css + '</head><body>')
        for section in html_sections:
            f.write(section)
        f.write('</body></html>')

if __name__ == '__main__':
    main()
