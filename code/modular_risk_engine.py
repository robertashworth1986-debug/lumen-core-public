"""Compatibility wrapper for risk primitives in modular_core_engine."""

from modular_core_engine import RiskEngine, RiskModule, stop_loss, volatility_target

__all__ = [
    "RiskModule",
    "RiskEngine",
    "volatility_target",
    "stop_loss",
]
