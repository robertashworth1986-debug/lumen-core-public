"""Compatibility wrapper for monitoring primitives in modular_core_engine."""

from modular_core_engine import MonitorModule, MonitoringEngine, drawdown_alert, latency_monitor

__all__ = [
    "MonitorModule",
    "MonitoringEngine",
    "drawdown_alert",
    "latency_monitor",
]
