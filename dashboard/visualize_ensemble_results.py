import pandas as pd
import plotly.graph_objs as go
from pathlib import Path

# Load walk-forward results
results_path = Path('dashboard/ensemble_walkforward_results.csv')
if not results_path.exists():
    raise FileNotFoundError('No walk-forward results found.')
df = pd.read_csv(results_path)

# Plot cumulative result
if 'result' in df.columns:
    df['cumulative'] = df['result'].cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['end'], y=df['cumulative'], mode='lines+markers', name='Cumulative PnL'))
    fig.update_layout(title='Ensemble Meta-Strategy Walk-Forward Results', xaxis_title='End Date', yaxis_title='Cumulative PnL', template='plotly_dark')
    html = fig.to_html(full_html=True)
    with open('dashboard/ensemble_walkforward_results.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print('Walk-forward results visualization saved: dashboard/ensemble_walkforward_results.html')
else:
    print('No result column in walk-forward results.')
