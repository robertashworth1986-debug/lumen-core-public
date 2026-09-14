"""Offline view of the existing reported-trade diagnostic, without invented equity."""
from __future__ import annotations
import argparse
import html
import importlib.util
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('lumencore_reported_trade_diagnostics', ROOT / 'code/execution/investor_performance_report.py')
_reporter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reporter)


def load_trade_log(path: str) -> pd.DataFrame:
    rows, receipt = _reporter.read_trade_snapshot(Path(path))
    frame = pd.DataFrame(rows)
    frame.attrs['source_snapshot'] = receipt
    return frame


def _report(df):
    return _reporter.analyze_rows(df.to_dict(orient='records'))


def compute_metrics(df: pd.DataFrame) -> dict:
    report = _report(df)
    return {'total_records': report['record_count'], 'closed_records': report['closed_records'],
            'win_rate': report['win_rate_pct'], 'sharpe': None, 'max_drawdown': None,
            'max_drawdown_pct': None, 'total_pnl': report['reported_net_pnl_sum_usd']}


def plot_equity_curve(df: pd.DataFrame) -> None:
    # A trade log cannot establish initial equity and external account flows.
    return None


def render_report(df: pd.DataFrame) -> str:
    report = _report(df)
    sections = ['<h1>Reported Trade Diagnostics</h1>', '<p class="status">UNVERIFIED_RECORDS</p>',
                '<p>' + html.escape(report['boundary']) + '</p>', '<h2>Record summary</h2><dl>']
    for key in ('record_count', 'closed_records', 'declared_mode', 'declared_currency',
                'reported_net_pnl_sum_usd', 'win_rate_pct', 'sharpe', 'max_drawdown'):
        sections.append(f'<dt>{html.escape(key.replace("_", " "))}</dt><dd>{html.escape(_reporter.display(report[key]))}</dd>')
    sections.append('</dl><h2>Field coverage</h2><div class="scroll">')
    sections.append(pd.DataFrame(report['field_coverage']).T.to_html(escape=True, border=0) + '</div>')
    values = report['reported_pnl_by_closed_record']
    if values:
        # Only numeric values enter the embedded script; source strings remain escaped HTML.
        import plotly.graph_objects as go
        import plotly.io as pio
        figure = go.Figure(go.Bar(x=list(range(1, len(values) + 1)), y=values))
        figure.update_layout(title='Reported net PnL by closed record (unverified)',
                             xaxis_title='Closed record in supplied order', yaxis_title='Reported USD')
        sections.append(pio.to_html(figure, full_html=False, include_plotlyjs=True, config={'responsive': True}))
    sections.append('<h2>Limits</h2><ul>' + ''.join('<li>' + html.escape(reason) + '</li>' for reason in report['limitations']) + '</ul>')
    receipt = df.attrs.get('source_snapshot')
    if receipt:
        sections.append('<p>Source SHA-256: <code>' + html.escape(receipt['sha256']) + '</code></p>')
    if not df.empty:
        columns = [name for name in ('symbol', 'side', 'entry_time', 'exit_time', 'net_pnl', 'net_pnl_pct', 'status', 'mode', 'currency') if name in df]
        sections.append('<h2>Recent supplied records</h2><div class="scroll">' + df[columns].tail(30).to_html(index=False, escape=True, border=0) + '</div>')
    css = ('body{max-width:1100px;margin:auto;padding:24px;font:16px/1.5 system-ui;color:#142534;background:#f5f7fa}'
           'h1,h2{color:#123c59}dt{font-weight:700}dd{margin:0 0 12px}td,th{padding:8px;text-align:left}'
           'table{border-collapse:collapse}tr{border-bottom:1px solid #c9d3de}.scroll{overflow:auto}'
           '.status{background:#fff0cd;padding:12px}code{overflow-wrap:anywhere}')
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reported Trade Diagnostics</title><style>' + css + '</style></head><body>' + ''.join(sections) + '</body></html>'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trade-log', type=Path, default=ROOT / 'out/execution/trade_log.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'dashboard/dashboard_analytics.html')
    args = parser.parse_args()
    try:
        frame = load_trade_log(str(args.trade_log))
        markup = render_report(frame)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Trade diagnostics held: {exc}\n')
    if args.output.resolve() == args.trade_log.resolve():
        parser.exit(2, 'Trade diagnostics held: output must differ from input\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(markup, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
