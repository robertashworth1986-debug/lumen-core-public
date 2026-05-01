from __future__ import annotations

import importlib

import pandas as pd


MODULE_EXPORTS = {
    "modular_signal_engine": [
        "SignalModule",
        "StrategyEngine",
        "moving_average_signal",
        "equal_weight_allocator",
    ],
    "modular_feature_engine": [
        "FeatureModule",
        "FeatureEngine",
        "returns_feature",
        "volatility_feature",
    ],
    "modular_timescale_engine": ["TimescaleModule", "TimescaleEngine"],
    "modular_execution_engine": [
        "ExecutionModule",
        "ExecutionEngine",
        "market_order",
        "twap_order",
    ],
    "modular_analytics_engine": [
        "AnalyticsModule",
        "AnalyticsEngine",
        "sharpe_ratio",
        "max_drawdown",
    ],
    "modular_risk_engine": ["RiskModule", "RiskEngine", "volatility_target", "stop_loss"],
    "modular_portfolio_engine": [
        "PortfolioModule",
        "PortfolioEngine",
        "equal_weight_portfolio",
        "volatility_weighted_portfolio",
    ],
    "modular_alpha_composer": ["AlphaComposer"],
    "modular_reporting_engine": ["ReportModule", "ReportingEngine", "json_report", "markdown_report"],
    "modular_monitoring_engine": ["MonitorModule", "MonitoringEngine", "drawdown_alert", "latency_monitor"],
    "modular_compliance_engin                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       e": [
        "ComplianceModule",
        "ComplianceEngine",
        "position_limit_check",
        "wash_sale_check",
    ],
    "modular_hypercompounder_filter": ["HyperCompounderFilter", "momentum_breakout_score"],
}


def _assert_exports() -> None:
    for module_name, expected_symbols in MODULE_EXPORTS.items():
        mod = importlib.import_module(module_name)
        for symbol in expected_symbols:
            if not hasattr(mod, symbol):
                raise AssertionError(f"{module_name} missing symbol {symbol}")


def _runtime_sanity() -> None:
    from modular_signal_engine import SignalModule, StrategyEngine, equal_weight_allocator, moving_average_signal

    df = pd.DataFrame({"close": [100.0, 101.0, 102.0, 99.0, 100.0, 103.0]})
    engine = StrategyEngine()
    engine.add_signal(SignalModule("ma3", moving_average_signal, {"window": 3}))
    engine.set_capital_allocator(equal_weight_allocator)
    out = engine.run(df)
    if "ma3" not in out.columns or "capital" not in out.columns:
        raise AssertionError("Strategy runtime sanity check failed")


def main() -> int:
    _assert_exports()
    _runtime_sanity()
    print("[MODULAR-WRAPPER-SMOKE] PASS")
    print(f"  modules_checked: {len(MODULE_EXPORTS)}")
    print("  runtime_path: signal -> allocator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())