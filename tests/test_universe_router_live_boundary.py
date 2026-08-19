from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "execution" / "universe_router.py"


def load_module():
    spec = importlib.util.spec_from_file_location("universe_router_boundary", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_mode_cannot_reach_an_imported_order_router(monkeypatch):
    class UnexpectedRouter:
        def place_order(self, *args, **kwargs):
            raise AssertionError("research universe router reached live order placement")

    monkeypatch.setitem(
        sys.modules,
        "execution_orchestrator",
        types.SimpleNamespace(router=UnexpectedRouter()),
    )
    module = load_module()

    result = module.execute_trade("BTC", 1.0, "LIVE")

    assert result == {
        "status": "blocked",
        "symbol": "BTC",
        "reason": "canonical_live_execution_path_required",
    }


def test_mode_file_fails_closed_for_live_or_malformed_values(tmp_path, monkeypatch):
    module = load_module()
    mode_file = tmp_path / "mode.json"
    monkeypatch.setattr(module, "MODE_FILE", mode_file)

    mode_file.write_text('{"mode": "LIVE"}', encoding="utf-8")
    assert module.load_mode() == "SHADOW"

    mode_file.write_text("not json", encoding="utf-8")
    assert module.load_mode() == "SHADOW"


def test_paper_and_shadow_modes_remain_non_executing():
    module = load_module()

    assert module.execute_trade("ETH", 0.5, "paper")["status"] == "paper"
    assert module.execute_trade("ETH", 0.5, "shadow")["status"] == "shadow"
