from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from execution.order_safety_gate import (  # noqa: E402
    ADD_ORDER_PATH,
    CANCEL_ALL_AFTER_PATH,
    MANUAL_LIQUIDATION_SCOPE,
    OrderSafetyError,
    build_manual_emergency_authorization,
    evaluate_order_request,
    require_order_request_allowed,
)


class OrderSafetyGateTests(unittest.TestCase):
    @staticmethod
    def _manual_liquidation_record() -> tuple[dict[str, Any], datetime]:
        now = datetime.now(timezone.utc)
        material = {
            "authorized_utc": now.isoformat(),
            "scope": MANUAL_LIQUIDATION_SCOPE,
            "reason": "manual emergency exit",
            "interactive_terminal": True,
            "command_line_confirmation": True,
            "interactive_confirmation": True,
        }
        digest = hashlib.sha256(
            json.dumps(
                material,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
        return {
            **material,
            "authorized": True,
            "execute": True,
            "authorization_sha256": digest,
        }, now

    def test_only_explicit_read_only_private_calls_are_allowed(self) -> None:
        for endpoint in (
            "/0/private/Balance",
            "/0/private/OpenOrders",
            "/0/private/QueryOrders",
            "/0/private/TradesHistory",
            "/0/private/TradeBalance",
        ):
            with self.subTest(endpoint=endpoint):
                decision = require_order_request_allowed(endpoint, {"nonce": "1"})
                self.assertTrue(decision.allowed)
                self.assertEqual(decision.mode, "read_only_private_call")

    def test_mutations_and_unknown_private_endpoints_fail_closed(self) -> None:
        for endpoint in (
            "/0/private/CancelOrder",
            "/0/private/CancelAll",
            CANCEL_ALL_AFTER_PATH,
            "/0/private/Withdraw",
            "/0/private/WalletTransfer",
            "/0/private/FutureMutation",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(OrderSafetyError):
                    require_order_request_allowed(endpoint, {"txid": "example"})

    def test_manual_emergency_receipt_is_scoped_to_market_sells_and_deadman(self) -> None:
        record, now = self._manual_liquidation_record()
        authorization = build_manual_emergency_authorization(record, now=now)

        sell = require_order_request_allowed(
            ADD_ORDER_PATH,
            {"type": "sell", "ordertype": "market", "volume": "0.1"},
            emergency_authorization=authorization,
        )
        self.assertTrue(sell.allowed)
        self.assertEqual(sell.mode, "manual_emergency_liquidation")

        deadman = require_order_request_allowed(
            CANCEL_ALL_AFTER_PATH,
            {"timeout": 60},
            emergency_authorization=authorization,
        )
        self.assertTrue(deadman.allowed)

        blocked_cases = (
            (ADD_ORDER_PATH, {"type": "buy", "ordertype": "market"}),
            (ADD_ORDER_PATH, {"type": "sell", "ordertype": "limit"}),
            ("/0/private/CancelAll", {}),
            ("/0/private/Withdraw", {"asset": "XBT"}),
            (CANCEL_ALL_AFTER_PATH, {"timeout": 0}),
            (CANCEL_ALL_AFTER_PATH, {"timeout": 301}),
        )
        for endpoint, payload in blocked_cases:
            with self.subTest(endpoint=endpoint, payload=payload):
                with self.assertRaises(OrderSafetyError):
                    require_order_request_allowed(
                        endpoint,
                        payload,
                        emergency_authorization=authorization,
                    )

    def test_manual_emergency_receipt_digest_and_freshness_are_verified(self) -> None:
        record, now = self._manual_liquidation_record()
        bad_digest = {**record, "authorization_sha256": "0" * 64}
        with self.assertRaises(OrderSafetyError):
            build_manual_emergency_authorization(bad_digest, now=now)

        stale_now = now + timedelta(minutes=6)
        with self.assertRaises(OrderSafetyError):
            build_manual_emergency_authorization(record, now=stale_now)

    def test_validate_true_is_the_only_allowed_add_order_mode(self) -> None:
        for value in (True, "true", " TRUE "):
            with self.subTest(value=value):
                decision = require_order_request_allowed(
                    ADD_ORDER_PATH,
                    {"pair": "XBTUSD", "validate": value},
                )
                self.assertTrue(decision.allowed)
                self.assertEqual(decision.mode, "validate_only")

        for value in (False, None, "false", "1", 1, ""):
            with self.subTest(value=value):
                with self.assertRaises(OrderSafetyError):
                    require_order_request_allowed(
                        ADD_ORDER_PATH,
                        {"pair": "XBTUSD", "validate": value},
                    )

    def test_payload_hash_is_deterministic(self) -> None:
        left = evaluate_order_request(
            ADD_ORDER_PATH,
            {"pair": "XBTUSD", "validate": "false", "volume": "1"},
        )
        right = evaluate_order_request(
            ADD_ORDER_PATH,
            {"volume": "1", "validate": "false", "pair": "XBTUSD"},
        )
        self.assertEqual(left.payload_sha256, right.payload_sha256)
        self.assertFalse(left.allowed)

    def _load_facade_with_stub(self) -> tuple[types.ModuleType, list[dict[str, Any]]]:
        calls: list[dict[str, Any]] = []
        stub = types.ModuleType("kraken_execution_legacy")

        class KrakenExecutionError(Exception):
            pass

        stub.KrakenExecutionError = KrakenExecutionError
        stub.ADD_ORDER_PATH = ADD_ORDER_PATH
        stub.INTENTS_FILE = "intents"
        stub.EVENTS_FILE = "events"
        stub.LAST_RESULT_FILE = "last_result"
        stub.assert_controller = lambda controller: None
        stub._ensure_flags = lambda: {
            "default_pair": "XBTUSD",
            "default_volume_base": 0.0004,
        }
        stub.get_last_price = lambda pair: 100.0
        stub.enforce_risk = lambda **kwargs: None
        stub._now_iso = lambda: "2026-07-16T00:00:00Z"
        stub._append_jsonl = lambda *args, **kwargs: None
        stub._write_json = lambda *args, **kwargs: None
        stub._runtime_snapshot = lambda **kwargs: None
        stub.queue_approval_ticket = lambda **kwargs: {
            "approval_state": "PENDING_HUMAN_APPROVAL",
            "payload": kwargs["payload"],
        }

        def build_order_payload(**kwargs: Any) -> dict[str, Any]:
            return {
                "pair": kwargs["pair"],
                "type": kwargs["side"],
                "ordertype": kwargs["ordertype"],
                "volume": f"{float(kwargs['volume_base']):.8f}",
                "validate": "true" if kwargs["validate"] else "false",
                "userref": kwargs["userref"],
            }

        stub._build_order_payload = build_order_payload

        def original_private_post(
            url_path: str,
            payload: dict[str, Any],
            timeout: int = 20,
            retry_attempt: int = 0,
        ) -> dict[str, Any]:
            calls.append(
                {
                    "url_path": url_path,
                    "payload": dict(payload),
                    "timeout": timeout,
                    "retry_attempt": retry_attempt,
                }
            )
            return {"validated": True}

        stub._private_post = original_private_post
        stub.submit_order_validate_only = lambda **kwargs: {"legacy": True}

        previous = sys.modules.get("kraken_execution_legacy")
        sys.modules["kraken_execution_legacy"] = stub
        try:
            spec = importlib.util.spec_from_file_location(
                "kraken_execution_facade_test",
                ROOT / "code" / "kraken_execution.py",
            )
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            if previous is None:
                sys.modules.pop("kraken_execution_legacy", None)
            else:
                sys.modules["kraken_execution_legacy"] = previous
        return module, calls

    def test_facade_blocks_live_add_order_before_transport(self) -> None:
        facade, calls = self._load_facade_with_stub()
        with self.assertRaises(facade.KrakenExecutionError):
            facade._private_post(
                ADD_ORDER_PATH,
                {"pair": "XBTUSD", "validate": "false"},
            )
        self.assertEqual(calls, [])

    def test_facade_blocks_non_order_mutations_before_transport(self) -> None:
        facade, calls = self._load_facade_with_stub()
        for endpoint in (
            "/0/private/CancelOrder",
            "/0/private/CancelAll",
            "/0/private/Withdraw",
            "/0/private/FutureMutation",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(facade.KrakenExecutionError):
                    facade._private_post(endpoint, {})
        self.assertEqual(calls, [])

    def test_facade_accepts_only_scoped_reviewed_emergency_mutation(self) -> None:
        record, now = self._manual_liquidation_record()
        authorization = build_manual_emergency_authorization(record, now=now)
        facade, calls = self._load_facade_with_stub()

        result = facade._private_post(
            ADD_ORDER_PATH,
            {"type": "sell", "ordertype": "market", "volume": "0.1"},
            emergency_authorization=authorization,
        )
        self.assertEqual(result, {"validated": True})
        self.assertEqual(len(calls), 1)

        with self.assertRaises(facade.KrakenExecutionError):
            facade._private_post(
                "/0/private/CancelAll",
                {},
                emergency_authorization=authorization,
            )
        self.assertEqual(len(calls), 1)

    def test_facade_validate_only_helper_emits_validate_true(self) -> None:
        facade, calls = self._load_facade_with_stub()
        result = facade.submit_order_validate_only(
            controller="Robert",
            pair="XBTUSD",
            side="buy",
            notional_usd=25.0,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["url_path"], ADD_ORDER_PATH)
        self.assertEqual(calls[0]["payload"]["validate"], "true")
        self.assertEqual(result["mode"], "VALIDATE_ONLY")
        self.assertTrue(result["deadman_result"]["skipped"])
        self.assertEqual(
            result["approval_ticket"]["approval_state"],
            "PENDING_HUMAN_APPROVAL",
        )


if __name__ == "__main__":
    unittest.main()
