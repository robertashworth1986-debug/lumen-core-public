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


class OrderSafetyFacadeTests(unittest.TestCase):
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

    def test_live_executor_blocks_before_private_transport(self) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []
        legacy = types.ModuleType("live_executor_legacy")

        class KrakenClient:
            def __init__(self, api_key: str = "", api_secret: str = "") -> None:
                self.api_key = api_key
                self.api_secret = api_secret

            def _private(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
                calls.append((endpoint, dict(data)))
                return {"transport": "called"}

        class RobustLiveExecutor:
            def __init__(self, api_keys: dict[str, Any]) -> None:
                self.api_keys = api_keys

            def run_institutional_execution_loop(self) -> None:
                return None

        legacy.KrakenClient = KrakenClient
        legacy.RobustLiveExecutor = RobustLiveExecutor
        legacy._is_duplicate_child_executor = lambda: (False, 0)
        legacy._write_live_heartbeat = lambda payload: None
        legacy._acquire_executor_lock = lambda: True
        legacy._release_executor_lock = lambda: None
        legacy.load_api_keys = lambda: {}

        facade = self._load_with_stub(
            wrapper_path=EXECUTION / "live_executor.py",
            wrapper_name="live_executor_facade_test",
            legacy_name="live_executor_legacy",
            legacy_module=legacy,
        )

        client = facade.KrakenClient()
        blocked = client._private(
            ADD_ORDER_PATH,
            {"pair": "XBTUSD", "type": "buy", "volume": "1"},
        )
        self.assertIn("error", blocked)
        self.assertEqual(blocked["order_safety"]["mode"], "blocked_live_order")
        self.assertEqual(calls, [])

        validated = client._private(
            ADD_ORDER_PATH,
            {"pair": "XBTUSD", "validate": "true"},
        )
        self.assertEqual(validated, {"transport": "called"})
        self.assertEqual(len(calls), 1)

        balance = client._private("/0/private/Balance", {})
        self.assertEqual(balance, {"transport": "called"})
        self.assertEqual(len(calls), 2)

    def test_gateway_blocks_before_key_loading_or_transport(self) -> None:
        calls: list[dict[str, Any]] = []
        legacy = types.ModuleType("luma_experience_gateway_legacy")

        class GatewayApp:
            def __init__(self) -> None:
                self.middleware: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

            def add_middleware(self, *args: Any, **kwargs: Any) -> None:
                self.middleware.append((args, kwargs))

        legacy.app = GatewayApp()

        def original_add_order(payload: dict[str, Any]) -> dict[str, Any]:
            calls.append(dict(payload))
            return {"result": {"descr": {"order": "validated"}}}

        legacy._kraken_add_order = original_add_order

        facade = self._load_with_stub(
            wrapper_path=CODE / "luma_experience_gateway.py",
            wrapper_name="gateway_facade_test",
            legacy_name="luma_experience_gateway_legacy",
            legacy_module=legacy,
        )

        blocked = facade._kraken_add_order(
            {"pair": "XBTUSD", "type": "buy", "validate": "false"}
        )
        self.assertIn("error", blocked)
        self.assertEqual(blocked["order_safety"]["mode"], "blocked_live_order")
        self.assertEqual(calls, [])

        validated = facade._kraken_add_order(
            {"pair": "XBTUSD", "type": "buy", "validate": "true"}
        )
        self.assertIn("result", validated)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["validate"], "true")
        self.assertEqual(len(facade.app.middleware), 1)
        self.assertEqual(
            facade.app.middleware[0][0][0].__name__,
            "OperatorApiAccessMiddleware",
        )

    def test_ticket_facade_forces_validate_and_disables_autofire(self) -> None:
        calls: list[dict[str, Any]] = []
        legacy = types.ModuleType("auto_ticket_producer_legacy")
        legacy.SCAN_MAX_AGE_SEC_DEFAULT = 30.0
        legacy._read_runtime_config = lambda default_threshold, default_enabled: {
            "enabled": default_enabled,
            "auto_fire_score": default_threshold,
            "max_auto_fires_per_cycle": 9,
        }

        def original_emit_tickets(**kwargs: Any) -> dict[str, Any]:
            calls.append(dict(kwargs))
            return {
                "validate_mode": kwargs["validate"],
                "auto_fire_score": kwargs["auto_fire_score"],
                "auto_fired": [{"ticket_id": "unsafe"}],
                "auto_fired_count": 1,
                "emitted": [],
            }

        legacy.emit_tickets = original_emit_tickets
        legacy.main = lambda: 0

        facade = self._load_with_stub(
            wrapper_path=CODE / "auto_ticket_producer.py",
            wrapper_name="auto_ticket_facade_test",
            legacy_name="auto_ticket_producer_legacy",
            legacy_module=legacy,
        )

        summary = facade.emit_tickets(
            use_cached=True,
            validate=False,
            controller="Robert",
            bankroll=500.0,
            top_n=10,
            auto_fire_score=99.0,
            runtime_cfg={
                "max_auto_fires_per_cycle": 7,
                "max_auto_fires_per_cycle_moonshot": 3,
            },
        )

        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertTrue(call["validate"])
        self.assertIsNone(call["auto_fire_score"])
        self.assertEqual(call["runtime_cfg"]["max_auto_fires_per_cycle"], 0)
        self.assertEqual(call["runtime_cfg"]["max_auto_fires_per_cycle_moonshot"], 0)
        self.assertEqual(call["runtime_cfg"]["order_promotion_stage"], "live_data_no_orders")
        self.assertTrue(summary["validate_mode"])
        self.assertEqual(summary["auto_fired"], [])
        self.assertEqual(summary["auto_fired_count"], 0)

    def test_ticket_cli_removes_live_and_autofire_switches(self) -> None:
        legacy = types.ModuleType("auto_ticket_producer_legacy")
        legacy.SCAN_MAX_AGE_SEC_DEFAULT = 30.0
        legacy.emit_tickets = lambda **kwargs: {}
        legacy._read_runtime_config = lambda default_threshold, default_enabled: {}
        legacy.main = lambda: 0

        facade = self._load_with_stub(
            wrapper_path=CODE / "auto_ticket_producer.py",
            wrapper_name="auto_ticket_cli_facade_test",
            legacy_name="auto_ticket_producer_legacy",
            legacy_module=legacy,
        )

        filtered = facade._validated_only_argv(
            [
                "--daemon",
                "--live",
                "--auto-fire-score",
                "88",
                "--controller",
                "Robert",
                "--auto-fire-score=91",
            ]
        )
        self.assertEqual(filtered, ["--daemon", "--controller", "Robert"])


if __name__ == "__main__":
    unittest.main()
