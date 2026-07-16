from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
EXECUTION = CODE / "execution"
for path in (CODE, EXECUTION):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from execution.order_safety_gate import ADD_ORDER_PATH  # noqa: E402


class StandaloneNoOrdersFacadeTests(unittest.TestCase):
    def _load_with_stub(
        self,
        *,
        wrapper_path: Path,
        wrapper_name: str,
        legacy_name: str,
        legacy_module: types.ModuleType,
    ) -> types.ModuleType:
        previous = sys.modules.get(legacy_name)
        sys.modules[legacy_name] = legacy_module
        try:
            spec = importlib.util.spec_from_file_location(wrapper_name, wrapper_path)
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        finally:
            if previous is None:
                sys.modules.pop(legacy_name, None)
            else:
                sys.modules[legacy_name] = previous

    def test_swing_hunter_blocks_orders_and_runs_snapshot_only(self) -> None:
        transport_calls: list[tuple[str, dict[str, Any]]] = []
        run_calls: list[str] = []
        scan_calls: list[str] = []
        legacy = types.ModuleType("kraken_swing_hunter_legacy")

        def original_post(endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
            transport_calls.append((endpoint, dict(data or {})))
            return {"ok": True}

        legacy._post = original_post
        legacy.get_balances = lambda: {"ZUSD": 10.0}
        legacy.portfolio_usd = lambda balances: 10.0

        def scan_top_movers() -> list[tuple[Any, ...]]:
            scan_calls.append("scan")
            return [("XBTUSD", 9.0, 100.0, 1_000_000.0, 2.0, 1.0)]

        legacy.scan_top_movers = scan_top_movers
        legacy.run = lambda: run_calls.append("run")

        facade = self._load_with_stub(
            wrapper_path=CODE / "kraken_swing_hunter.py",
            wrapper_name="swing_snapshot_facade_test",
            legacy_name="kraken_swing_hunter_legacy",
            legacy_module=legacy,
        )

        blocked = facade._post(ADD_ORDER_PATH, {"pair": "XBTUSD"})
        self.assertIn("_error", blocked)
        self.assertEqual(blocked["order_safety"]["mode"], "blocked_live_order")
        self.assertEqual(transport_calls, [])

        self.assertEqual(facade._post("/0/private/Balance"), {"ok": True})
        self.assertEqual(len(transport_calls), 1)

        self.assertEqual(facade.main(), 0)
        self.assertEqual(scan_calls, ["scan"])
        self.assertEqual(run_calls, [])

    def test_micro_bot_blocks_both_order_transports_and_skips_loops(self) -> None:
        post_calls: list[tuple[str, dict[str, Any]]] = []
        request_calls: list[tuple[str, dict[str, Any]]] = []
        legacy_main_calls: list[str] = []
        legacy = types.ModuleType("micro_position_kraken_bot_legacy")

        def original_post(endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
            post_calls.append((endpoint, dict(data or {})))
            return {"ok": True}

        def original_request(endpoint: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
            request_calls.append((endpoint, dict(data or {})))
            return {"ok": True}

        legacy._post = original_post
        legacy._kraken_request = original_request
        legacy.value_portfolio = lambda: {"_total_usd": 12.5}
        legacy.get_balance = lambda: {"ZUSD": 12.5}
        legacy.main = lambda: legacy_main_calls.append("main")

        facade = self._load_with_stub(
            wrapper_path=CODE / "micro_position_kraken_bot.py",
            wrapper_name="micro_snapshot_facade_test",
            legacy_name="micro_position_kraken_bot_legacy",
            legacy_module=legacy,
        )

        blocked_post = facade._post(ADD_ORDER_PATH, {"pair": "PEPEUSD"})
        self.assertIn("_error", blocked_post)
        self.assertEqual(post_calls, [])

        blocked_request = facade._kraken_request(
            ADD_ORDER_PATH,
            {"pair": "PEPE/USD"},
        )
        self.assertIn("error", blocked_request)
        self.assertEqual(request_calls, [])

        self.assertEqual(facade._post("/0/private/Balance"), {"ok": True})
        self.assertEqual(facade._kraken_request("/0/private/Balance"), {"ok": True})
        self.assertEqual(len(post_calls), 1)
        self.assertEqual(len(request_calls), 1)

        self.assertEqual(facade.main(), 0)
        self.assertEqual(legacy_main_calls, [])


if __name__ == "__main__":
    unittest.main()
