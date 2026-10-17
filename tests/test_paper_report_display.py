"""Synthetic display fixtures; no workers, providers or runtime exports."""
from __future__ import annotations

import ast
import importlib.util
import math
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
BRIEF_PATH = ROOT / "code/execution/build_institutional_crypto_executive_brief.py"
DASHBOARD_PATH = ROOT / "code/execution/build_institutional_crypto_paper_dashboard.py"
MISSING = object()
UNKNOWN_VALUES = [MISSING, None, float("nan"), float("inf"), -float("inf"), "invalid", True]


def report_with(value):
    portfolio = {"cash_usd": 500, "equity_usd": 1000, "realized_pnl_usd": -25}
    if value is not MISSING:
        portfolio.update(return_pct=value, unrealized_pnl_usd=value)
    return {"mode": "synthetic_paper_fixture", "portfolio": portfolio}


@pytest.fixture
def brief():
    spec = importlib.util.spec_from_file_location("isolated_paper_brief_display", BRIEF_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def dashboard():
    # Panel/Plotly are optional. Execute the real data adapter and HTML helper
    # without importing their server/extension graph or reading runtime files.
    names = {"_f", "_fmt_pct", "_dashboard_data", "_position_concentration", "_set_metric_value"}
    tree = ast.parse(DASHBOARD_PATH.read_text(encoding="utf-8"))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in functions} == names
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, *functions], type_ignores=[]))
    scope = {
        "math": math, "pd": pd, "Path": Path,
        "load_json": lambda *args, **kwargs: {},
        "load_jsonl": lambda *args, **kwargs: [],
        "now_utc": lambda: "2026-10-14T00:00:00Z",
        "REGIME_HISTORY_FILE": "synthetic-regime.jsonl",
        "LIVE_ENGINE_HEARTBEAT_FILE": "synthetic-heartbeat.json",
    }
    exec(compile(module, str(DASHBOARD_PATH), "exec"), scope)
    return scope


@pytest.mark.parametrize("value", UNKNOWN_VALUES)
def test_dashboard_return_unknown_survives_data_adapter_and_html_formatting(dashboard, value):
    data = dashboard["_dashboard_data"](report_with(value), {}, {}, [], False)
    formatted = dashboard["_fmt_pct"](data["ret"])
    assert formatted == "Unknown"
    pane = types.SimpleNamespace(object="")
    dashboard["_set_metric_value"](pane, formatted)
    assert ">Unknown</div>" in pane.object
    assert ">0.00%</div>" not in pane.object


@pytest.mark.parametrize("value", UNKNOWN_VALUES)
def test_markdown_does_not_turn_unknown_return_or_unrealized_into_zero(brief, value):
    rendered = brief.build_markdown(report_with(value), {}, {})
    assert "- Return Since Seed: Unknown" in rendered
    assert "- Unrealized PnL: Unknown" in rendered
    assert "- Return Since Seed: 0.00%" not in rendered
    assert "- Unrealized PnL: $0" not in rendered
    assert "external cash flows are unreconciled" in rendered
    assert "not captured in the account snapshot" in rendered


def test_known_zero_and_losses_remain_numeric(dashboard, brief):
    for value, expected in [(0.0, "0.00%"), (-.05, "-5.00%")]:
        data = dashboard["_dashboard_data"](report_with(value), {}, {}, [], False)
        assert dashboard["_fmt_pct"](data["ret"]) == expected
        assert brief._fmt_pct(value) == expected
    rendered = brief.build_markdown({
        "portfolio": {"return_pct": -.05, "unrealized_pnl_usd": -125}
    }, {}, {})
    assert "- Return Since Seed: -5.00%" in rendered
    assert "- Unrealized PnL: $-125" in rendered
    assert brief._fmt_usd(0) == "$0"
    assert brief._fmt_pct(1e308) == dashboard["_fmt_pct"](1e308) == "Unknown"


@pytest.mark.parametrize("value,pnl,pct,unrealized", [
    (MISSING, MISSING, "Unknown", "Unknown"),
    (None, None, "Unknown", "Unknown"),
    (-.05, -125, "-5.00%", "$-125"),
    (float("nan"), float("nan"), "Unknown", "Unknown"),
])
def test_pdf_renderer_preserves_unknowns_with_optional_backend_mocked(
    brief, monkeypatch, tmp_path, value, pnl, pct, unrealized
):
    drawn = []

    class Canvas:
        def __init__(self, *args, **kwargs):
            pass

        def drawString(self, x, y, text):
            drawn.append(text)

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    modules = {name: types.ModuleType(name) for name in (
        "reportlab", "reportlab.lib", "reportlab.lib.colors",
        "reportlab.lib.pagesizes", "reportlab.pdfgen", "reportlab.pdfgen.canvas",
    )}
    modules["reportlab.lib.colors"].HexColor = lambda value: value
    modules["reportlab.lib.pagesizes"].letter = (612, 792)
    modules["reportlab.pdfgen.canvas"].Canvas = Canvas
    modules["reportlab.lib"].colors = modules["reportlab.lib.colors"]
    modules["reportlab.pdfgen"].canvas = modules["reportlab.pdfgen.canvas"]
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    output = tmp_path / "synthetic-brief.pdf"
    monkeypatch.setattr(brief, "PDF_FILE", output)
    report = report_with(value)
    if pnl is not MISSING:
        report["portfolio"]["unrealized_pnl_usd"] = pnl
    result = brief.build_pdf(report, {}, {})
    assert f"Return Since Seed: {pct}" in drawn
    assert f"Unrealized PnL: {unrealized}" in drawn
    assert any("external cash flows are unreconciled" in line for line in drawn)
    assert result == str(output)
    assert not output.exists()
