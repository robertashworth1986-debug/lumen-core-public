import numpy as np
import pandas as pd
from pathlib import Path
import importlib
import sys

# Dynamically import all strategy modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'data' / 'code'))

# Import core strategies and algos
import hybrid_harmonic_strategies as hhs
import hybrid_harmonic_algorithms as hha
import institutional_harmonic_core as ihc
import novel_harmonic_layers as nhl

# Load price or odds data (stub: replace with real loader)
def load_data(path):
    df = pd.read_csv(path)
    if 'close' not in df.columns:
        if 'exit_price' in df.columns:
            df['close'] = df['exit_price']
        elif 'entry_price' in df.columns:
            df['close'] = df['entry_price']
    return df

# Ensemble/meta-strategy: weighted voting of all signals
def ensemble_signals(df):
    signals = []
    # Core strategies
    signals.append(hhs.strat_phase_follow(df['close']))
    signals.append(hhs.strat_resonance_revert(df['close']))
    signals.append(hhs.strat_interference_breakout(df['close']))
    signals.append(hhs.strat_nodal_compression_release(df['close']))
    signals.append(hhs.strat_frequency_drift_guard(df['close']))
    signals.append(hhs.strat_curvature_reversal(df['close']))
    signals.append(hhs.strat_harmonic_consensus(df['close']))
    # Core algos
    signals.append(hha.algo_phase_coherence(df['close']))
    signals.append(hha.algo_resonance_cluster(df['close']))
    signals.append(hha.algo_multi_timescale_interference(df['close']))
    signals.append(hha.algo_harmonic_envelope(df['close']))
    # Novel algos
    signals.append(nhl.algo_echo_stack(df['close']))
    signals.append(nhl.algo_resonant_pressure(df['close']))
    signals.append(nhl.algo_phase_lattice(df['close']))
    signals.append(nhl.algo_vortex_memory(df['close']))
    # Weighted ensemble (equal weights for now)
    ens = np.nanmean(np.column_stack(signals), axis=1)
    return pd.Series(ens, index=df.index)

# Auto-tuning stub (expand with Optuna or grid search)
def auto_tune(df, signal_func):
    # Placeholder: just run the signal for now
    return signal_func(df)

# Walk-forward validation
def walk_forward(df, signal_func, window=250, step=50):
    results = []
    for start in range(0, len(df) - window, step):
        train = df.iloc[start:start+window]
        test = df.iloc[start+window:start+window+step]
        if len(test) == 0:
            break
        signal = signal_func(train)
        test_result = (test['close'].pct_change().fillna(0.0) * signal[-len(test):]).sum()
        results.append({'start': train.index[0], 'end': test.index[-1], 'result': test_result})
    return pd.DataFrame(results)

# Main pipeline
def main():
    # Use twelvedata_googl.csv as the data source
    data_path = Path('clean_data/twelvedata_googl.csv')
    if not data_path.exists():
        print('No data found.')
        return
    df = pd.read_csv(data_path)
    # Always treat the first column as 'close' if 'close' is not present
    if 'close' not in df.columns:
        df['close'] = df.iloc[:, 0]
    if 'close' not in df.columns:
        print('No close price in data.')
        return
    # Ensemble/meta-strategy
    signal = ensemble_signals(df)
    # Auto-tune (stub)
    tuned_signal = auto_tune(df, lambda d: ensemble_signals(d))
    # Walk-forward validation
    results = walk_forward(df, lambda d: tuned_signal, window=50, step=10)
    # Save results
    results.to_csv('dashboard/ensemble_walkforward_results.csv', index=False)
    print('Ensemble walk-forward results saved.')

if __name__ == '__main__':
    main()
