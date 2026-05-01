"""Compatibility wrapper for portfolio primitives in modular_core_engine."""

from modular_core_engine import (
    PortfolioEngine,
    PortfolioModule,
    equal_weight_portfolio,
    volatility_weighted_portfolio,
)

__all__ = [
    "PortfolioModule",
    "PortfolioEngine",
    "equal_weight_portfolio",
    "volatility_weighted_portfolio",
]
