"""Compatibility wrapper for signal primitives in modular_core_engine."""

from modular_core_engine import SignalModule, StrategyEngine, equal_weight_allocator, moving_average_signal

__all__ = [
    "SignalModule",
    "StrategyEngine",
    "moving_average_signal",
    "equal_weight_allocator",
]
