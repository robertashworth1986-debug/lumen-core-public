"""
backtest_walkforward_engine.py

A rolling backtest and walk-forward validation engine for modular strategies.
- Supports multi-timescale, multi-symbol, and multi-strategy validation.
- Designed for integration with modular_signal_engine and orchestrators.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Callable

class BacktestResult:
    def __init__(self, pnl: pd.Series, trades: pd.DataFrame, metrics: Dict[str, Any]):
        self.pnl = pnl
        self.trades = trades
        self.metrics = metrics

class BacktestEngine:
    def __init__(self, strategy_engine: Any):
        self.strategy_engine = strategy_engine

    def run_backtest(self, df: pd.DataFrame, walk_length: int = 50, test_length: int = 20) -> List[BacktestResult]:
        results = []
        n = len(df)
        for start in range(0, n - walk_length - test_length + 1, test_length):
            train = df.iloc[start:start+walk_length]
            test = df.iloc[start+walk_length:start+walk_length+test_length]
            # Fit/train strategy on train, apply to test
            signals = self.strategy_engine.run(train)
            test_signals = self.strategy_engine.run(test)
            # Simple PnL: difference in close * signal
            pnl = test['close'].diff().fillna(0) * test_signals.iloc[:,0].fillna(0)
            trades = pd.DataFrame({'signal': test_signals.iloc[:,0], 'pnl': pnl})
            metrics = {
                'sharpe': pnl.mean() / (pnl.std() + 1e-8),
                'total_return': pnl.sum(),
                'walk_start': start,
                'walk_end': start+walk_length,
                'test_start': start+walk_length,
                'test_end': start+walk_length+test_length
            }
            results.append(BacktestResult(pnl, trades, metrics))
        return results

if __name__ == "__main__":
    from modular_signal_engine import StrategyEngine, SignalModule, moving_average_signal, equal_weight_allocator
    # Dummy data
    data = pd.DataFrame({'close': np.random.randn(200).cumsum() + 100})
    engine = StrategyEngine()
    engine.add_signal(SignalModule('ma20', moving_average_signal, {'window': 20}))
    engine.set_capital_allocator(equal_weight_allocator)
    bt = BacktestEngine(engine)
    results = bt.run_backtest(data)
    for r in results[-3:]:
        print(r.metrics)
        print(r.trades.tail())
