"""Compatibility wrapper for compliance primitives in modular_core_engine."""

from modular_core_engine import ComplianceEngine, ComplianceModule, position_limit_check, wash_sale_check

__all__ = [
    "ComplianceModule",
    "ComplianceEngine",
    "position_limit_check",
    "wash_sale_check",
]
