"""Causal walk-forward diagnostics for modular, unit-position strategies.

Results are descriptive offline checks, not reconciled brokerage profit. Signals
use only rows available before each scored close move; every fold starts flat
and closes its final position. Fees and slippage are explicit fixed-bps estimates.
"""

import math
import numpy as np
import pandas as pd
from typing import Dict, Any, List


class BacktestResult:
    def __init__(self, pnl: pd.Series, trades: pd.DataFrame, metrics: Dict[str, Any]):
        self.pnl = pnl
        self.trades = trades
        self.metrics = metrics


class BacktestEngine:
    def __init__(self, strategy_engine: Any, fee_bps: float = 0.0, slippage_bps: float = 0.0):
        for value in (fee_bps, slippage_bps):
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("fees and slippage must be finite and nonnegative")
        self.strategy_engine = strategy_engine
        self.fee_bps = float(fee_bps)
        self.slippage_bps = float(slippage_bps)

    def _last_signal(self, history: pd.DataFrame) -> float:
        output = self.strategy_engine.run(history.copy(deep=True))
        if isinstance(output, pd.DataFrame):
            if not len(output.columns):
                raise ValueError("strategy returned no signal column")
            output = output.iloc[:, 0]
        if not isinstance(output, pd.Series) or not output.index.equals(history.index):
            raise ValueError("strategy signals must match the provided historical index")
        value = output.iloc[-1]
        # An explicit warmup NaN means no position, never unknown market PnL.
        if pd.isna(value):
            return 0.0
        if isinstance(value, (bool, np.bool_)) or not math.isfinite(value) or not -1 <= value <= 1:
            raise ValueError("strategy signal must be finite and within [-1, 1]")
        return float(value)

    def run_backtest(self, df: pd.DataFrame, walk_length: int = 50, test_length: int = 20) -> List[BacktestResult]:
        if any(type(value) is not int or value <= 0 for value in (walk_length, test_length)):
            raise ValueError("walk_length and test_length must be positive integers")
        if not df.index.is_unique or not df.index.is_monotonic_increasing:
            raise ValueError("backtest index must be unique and increasing")
        close = pd.to_numeric(df['close'], errors='raise').astype(float)
        if not np.isfinite(close.to_numpy()).all() or (close <= 0).any():
            raise ValueError("backtest requires finite positive close prices")
        results = []
        n = len(df)
        for start in range(0, n - walk_length - test_length + 1, test_length):
            train_end = start + walk_length
            test_end = train_end + test_length
            train = df.iloc[start:train_end].copy(deep=True)
            # Training is separate from scoring. A stateful fitter is never given
            # the test block, and run() only receives a causal prefix thereafter.
            fit = getattr(self.strategy_engine, 'fit', None)
            if callable(fit):
                fit(train)
            positions, gross, fees, slip, turnover, asof = [], [], [], [], [], []
            previous_position = 0.0
            for i in range(train_end, test_end):
                history = df.iloc[start:i]
                position = self._last_signal(history)
                previous_close = float(close.iloc[i - 1])
                current_close = float(close.iloc[i])
                traded_units = abs(position - previous_position)
                traded_notional = traded_units * previous_close
                # All scored windows include the last close and estimated cost
                # of liquidation, rather than omitting the closing side's costs.
                if i == test_end - 1:
                    traded_notional += abs(position) * current_close
                    traded_units += abs(position)
                positions.append(position)
                gross.append((current_close - previous_close) * position)
                fees.append(traded_notional * self.fee_bps / 10000.0)
                slip.append(traded_notional * self.slippage_bps / 10000.0)
                turnover.append(traded_units)
                asof.append(df.index[i - 1])
                previous_position = position
            index = df.index[train_end:test_end]
            trades = pd.DataFrame({'signal': positions, 'signal_asof': asof, 'gross_pnl': gross,
                                   'fee_cost': fees, 'slippage_cost': slip, 'turnover': turnover}, index=index)
            trades['pnl'] = trades['gross_pnl'] - trades['fee_cost'] - trades['slippage_cost']
            pnl = trades['pnl']
            if not np.isfinite(pnl.to_numpy()).all():
                raise ValueError("backtest PnL exceeds finite numeric range")
            std = float(pnl.std()) if len(pnl) > 1 else 0.0
            sharpe = float(pnl.mean() / std) if std > 1e-12 else 0.0
            metrics = {
                'sharpe': sharpe, 'sharpe_per_bar': sharpe,
                'total_return': float(pnl.sum()),  # Legacy name; unit is stated below.
                'total_pnl': float(pnl.sum()), 'pnl_unit': 'price_units_per_unit_position',
                'fee_bps': self.fee_bps, 'slippage_bps': self.slippage_bps,
                'cost_model': 'fixed_bps_on_entry_flip_and_terminal_exit_notional',
                'causal_signal_lag_bars': 1, 'terminal_position_closed': True,
                'evidence_type': 'offline_descriptive_backtest',
                'walk_start': start, 'walk_end': train_end,
                'test_start': train_end, 'test_end': test_end,
            }
            results.append(BacktestResult(pnl, trades, metrics))
        return results


if __name__ == '__main__':
    from modular_signal_engine import StrategyEngine, SignalModule, moving_average_signal, equal_weight_allocator
    data = pd.DataFrame({'close': np.random.default_rng(0).normal(size=200).cumsum() + 100})
    engine = StrategyEngine()
    engine.add_signal(SignalModule('ma20', moving_average_signal, {'window': 20}))
    engine.set_capital_allocator(equal_weight_allocator)
    for result in BacktestEngine(engine).run_backtest(data)[-3:]:
        print(result.metrics)
        print(result.trades.tail())
