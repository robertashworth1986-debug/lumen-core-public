"""Compatibility wrapper for execution primitives in modular_core_engine."""

from modular_core_engine import ExecutionEngine, ExecutionModule, market_order, twap_order

__all__ = [
    "ExecutionModule",
    "ExecutionEngine",
    "market_order",
    "twap_order",
]
