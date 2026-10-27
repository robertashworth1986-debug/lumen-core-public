"""Offline rolling-research boundaries for the active paper ticker and facade."""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
FRESH = datetime.now(timezone.utc).isoformat()


def screen(**changes):
    return {
        "status": "RESEARCH_ONLY",
        "symbol": "BTC/USD",
        "family": "momentum_lowvol",
        "metrics": {"sharpe": 1000.0, "win_rate": 1.0},
        "generated_utc": FRESH,
        "received_asof_utc": FRESH,
        "latest_closed_bar_utc": FRESH,
        **changes,
    }


SCREENS = [
    screen(),
    screen(generated_utc="2000-01-01T00:00:00Z"),
    screen(status="HOLD"),
    {key: value for key, value in screen().items() if key != "status"},
    screen(status="APPROVED", independently_validated=True),
    screen(status="LIVE", allow_execution=True),
]


def isolated_functions(path, names, **namespace):
    """Load actual function bodies without importing credential/worker graphs."""
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert {node.name for node in functions} == set(names)
    scope = {"Any": Any, "Dict": Dict, "Optional": Optional, "json": json, **namespace}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), scope)
    return scope


def ticker_intel(payload, kpi=None):
    def load_json(path, default):
        return copy.deepcopy(payload if path == "rolling" else (kpi or {}))

    functions = isolated_functions(
        "code/multi_exchange_paper_ticker.py", {"_f", "_load_external_intel"},
        load_json=load_json, ROLLING_BEST_FILE="rolling", DUCKDB_KPI_FILE="kpi",
    )
    return functions["_load_external_intel"]()


@pytest.mark.parametrize("payload", SCREENS)
def test_ticker_keeps_raw_research_diagnostics_without_execution_preferences(payload):
    result = ticker_intel(payload)
    assert result["preferred_symbol"] == ""
    assert result["preferred_family"] == ""
    assert result["preferred_regime"] == ""
    assert result["risk_multiplier"] == result["scan_multiplier"] == 1.0
    assert result["rolling_best"] == payload
    assert result["rolling_preference_rejection_reason"] == "rolling_research_preferences_disabled"


@pytest.mark.parametrize("kpi,risk,scan", [
    ({}, 1.0, 1.0),
    ({"sample_quality_tier": "institutional", "sharpe_proxy": 1.2}, 1.05, 1.05),
    ({"sample_quality_tier": "insufficient", "sharpe_proxy": -1,
      "avg_fee_drag_pct_per_trade": .3, "max_drawdown": -.3}, .70, .95),
])
def test_rolling_screen_cannot_add_to_existing_kpi_multipliers(kpi, risk, scan):
    without_rolling = ticker_intel({}, kpi)
    with_rolling = ticker_intel(screen(), kpi)
    assert with_rolling["risk_multiplier"] == pytest.approx(risk)
    assert with_rolling["scan_multiplier"] == pytest.approx(scan)
    assert with_rolling["risk_multiplier"] == without_rolling["risk_multiplier"]
    assert with_rolling["scan_multiplier"] == without_rolling["scan_multiplier"]
    assert with_rolling["kpi"] == kpi


@pytest.mark.parametrize("payload", [None, [], "research", 1, True])
def test_malformed_rolling_diagnostic_has_no_preference(payload):
    result = ticker_intel(payload)
    assert result["preferred_symbol"] == result["preferred_family"] == result["preferred_regime"] == ""
    assert result["scan_multiplier"] == result["risk_multiplier"] == 1.0
    assert result["rolling_best"] == {}


@pytest.mark.parametrize("payload", SCREENS)
def test_active_executor_facade_disables_rolling_preference_without_importing_legacy(payload, monkeypatch):
    legacy = types.ModuleType("live_executor_legacy")
    calls = []

    class KrakenClient:
        def _private(self, endpoint, data):
            raise AssertionError("no private transport is permitted in this fixture")

    def old_preference():
        calls.append(True)
        return payload["symbol"].split("/")[0]

    legacy.KrakenClient = KrakenClient
    legacy.RobustLiveExecutor = object
    legacy._preferred_live_symbol = old_preference
    gate = types.ModuleType("order_safety_gate")
    gate.ADD_ORDER_PATH = "/0/private/AddOrder"
    gate.ORDER_POLICY = "synthetic-test-policy"
    gate.evaluate_order_request = lambda *args: types.SimpleNamespace(allowed=False, as_dict=lambda: {})
    monkeypatch.setitem(sys.modules, "live_executor_legacy", legacy)
    monkeypatch.setitem(sys.modules, "order_safety_gate", gate)
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location(
        "isolated_live_executor_display_review", ROOT / "code/execution/live_executor.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert legacy._preferred_live_symbol() is None
    assert calls == []
