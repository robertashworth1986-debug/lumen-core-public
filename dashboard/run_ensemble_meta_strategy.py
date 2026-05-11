import numpy as np
import pandas as pd
from pathlib import Path
import sys
from importlib import import_module

STACK_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = STACK_ROOT.parent

# Import strategy modules from the canonical code tree.
for candidate in (STACK_ROOT / 'code', STACK_ROOT / 'data' / 'code'):
    if candidate.exists():
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)

# Import core strategies and algos from the discovered path set.
hhs = import_module('hybrid_harmonic_strategies')
hha = import_module('hybrid_harmonic_algorithms')
ihc = import_module('institutional_harmonic_core')
nhl = import_module('novel_harmonic_layers')


def load_data(path):
    df = pd.read_csv(path)

    close_candidates = ('close', 'exit_price', 'entry_price')
    for column in close_candidates:
        if column in df.columns:
            close = pd.to_numeric(df[column], errors='coerce')
            if close.notna().any():
                df['close'] = close.ffill().bfill()
                break

    if 'close' not in df.columns:
        for column in df.columns:
            candidate = pd.to_numeric(df[column], errors='coerce')
            if candidate.notna().any():
                df['close'] = candidate.ffill().bfill()
                break

    if 'close' not in df.columns:
        raise ValueError('No usable close/price column found in dataset.')

    return df


def _coerce_signal(raw_signal, index):
    if isinstance(raw_signal, pd.Series):
        values = pd.to_numeric(raw_signal, errors='coerce').to_numpy()
    else:
        values = np.asarray(raw_signal, dtype=float).reshape(-1)

    target_len = len(index)
    if values.size == 0:
        values = np.zeros(target_len, dtype=float)
    elif values.size == 1:
        values = np.repeat(values[0], target_len)
    elif values.size > target_len:
        values = values[-target_len:]
    elif values.size < target_len:
        pad = np.full(target_len - values.size, np.nan)
        values = np.concatenate([pad, values])

    return pd.Series(values, index=index, dtype=float).ffill().fillna(0.0)

# Ensemble/meta-strategy: weighted voting of all signals
def ensemble_signals(df):
    close = pd.to_numeric(df['close'], errors='coerce').ffill().bfill()
    signals = []
    signal_builders = [
        hhs.strat_phase_follow,
        hhs.strat_resonance_revert,
        hhs.strat_interference_breakout,
        hhs.strat_nodal_compression_release,
        hhs.strat_frequency_drift_guard,
        hhs.strat_curvature_reversal,
        hhs.strat_harmonic_consensus,
        hha.algo_phase_coherence,
        hha.algo_resonance_cluster,
        hha.algo_multi_timescale_interference,
        hha.algo_harmonic_envelope,
        nhl.algo_echo_stack,
        nhl.algo_resonant_pressure,
        nhl.algo_phase_lattice,
        nhl.algo_vortex_memory,
    ]

    for builder in signal_builders:
        try:
            raw = builder(close)
        except Exception as exc:
            print(f'[WARN] {builder.__name__} failed: {exc}')
            raw = np.zeros(len(df), dtype=float)
        signals.append(_coerce_signal(raw, df.index).to_numpy())

    ens = np.nanmean(np.column_stack(signals), axis=1)
    ens = np.nan_to_num(ens, nan=0.0, posinf=0.0, neginf=0.0)
    return pd.Series(ens, index=df.index, name='ensemble_signal')

# Auto-tuning stub (expand with Optuna or grid search)
def auto_tune(df, signal_func):
    # Placeholder: run once so downstream flow can evolve into real tuning later.
    _ = signal_func(df)
    return signal_func

# Walk-forward validation
def walk_forward(df, signal_func, window=250, step=50):
    if len(df) <= window:
        return pd.DataFrame(columns=['start', 'end', 'result', 'bars'])

    results = []
    for start in range(0, len(df) - window, step):
        train_end = start + window
        test_end = min(train_end + step, len(df))

        train = df.iloc[start:train_end]
        test = df.iloc[train_end:test_end]
        if len(test) == 0:
            break

        # Build signal with historical context, then evaluate only on test bars.
        combined = df.iloc[start:test_end]
        combined_signal = _coerce_signal(signal_func(combined), combined.index)
        test_signal = combined_signal.iloc[-len(test):].shift(1).fillna(0.0)
        test_returns = pd.to_numeric(test['close'], errors='coerce').pct_change().fillna(0.0)

        test_result = float((test_returns * test_signal).sum())
        results.append({
            'start': train.index[0],
            'end': test.index[-1],
            'result': test_result,
            'bars': int(len(test)),
        })

    return pd.DataFrame(results)

# Main pipeline
def main():
    candidates = [
        WORKSPACE_ROOT / 'clean_data' / 'twelvedata_googl.csv',
        STACK_ROOT / 'clean_data' / 'twelvedata_googl.csv',
        Path('clean_data/twelvedata_googl.csv'),
    ]
    data_path = next((p for p in candidates if p.exists()), None)
    if data_path is None:
        print('No data found.')
        return

    try:
        df = load_data(data_path)
    except Exception as exc:
        print(f'Unable to load data: {exc}')
        return

    tuned_signal_func = auto_tune(df, ensemble_signals)
    results = walk_forward(df, tuned_signal_func, window=50, step=10)

    output_path = Path(__file__).resolve().parent / 'ensemble_walkforward_results.csv'
    results.to_csv(output_path, index=False)
    print(f'Ensemble walk-forward results saved to {output_path}.')
    print(f'Rows: {len(results)}')

if __name__ == '__main__':
    main()
