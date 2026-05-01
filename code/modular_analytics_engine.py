"""Compatibility wrapper for analytics primitives in modular_core_engine."""

from modular_core_engine import AnalyticsEngine, AnalyticsModule, max_drawdown, sharpe_ratio

__all__ = [
    "AnalyticsModule",
    "AnalyticsEngine",
    "sharpe_ratio",
    "max_drawdown",
]
