from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))


def load_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CapitalTransferSafetyTests(unittest.TestCase):
    def test_retired_kraken_withdrawal_utility_is_inert(self) -> None:
        path = ROOT / "code" / "kraken_auto_withdraw_btc.py"
        source = path.read_text(encoding="utf-8")
        module = load_path("kraken_auto_withdraw_btc_test", path)

        status = module.build_inert_status()
        self.assertEqual(status["status"], "blocked")
        self.assertEqual(status["policy"], "CAPITAL_TRANSFER_BLOCKED")
        self.assertEqual(status["promotion_stage"], "live_data_no_orders")
        self.assertFalse(status["credentials_loaded"])
        self.assertFalse(status["network_access"])
        self.assertFalse(status["destination_address_loaded"])
        self.assertFalse(status["withdrawal_authorized"])

        self.assertNotIn("ccxt", source)
        self.assertNotIn("KRAKEN_API_KEY", source)
        self.assertNotIn("KRAKEN_API_SECRET", source)
        self.assertNotIn("luma_live_keys.env", source)
        self.assertNotRegex(source, r"\.withdraw\s*\(")
        self.assertNotRegex(source, r"/0/private/Withdraw\b")
        self.assertNotRegex(source, r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b")

    def test_command_line_facade_fails_closed(self) -> None:
        module = load_path(
            "kraken_auto_withdraw_btc_cli_test",
            ROOT / "code" / "kraken_auto_withdraw_btc.py",
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = module.main()
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["withdrawal_authorized"])

    def test_retired_cancel_utility_is_inert_and_import_safe(self) -> None:
        path = ROOT / "code" / "ops" / "cancel_open_orders.py"
        source = path.read_text(encoding="utf-8")
        module = load_path("cancel_open_orders_inert_test", path)

        status = module.build_inert_status()
        self.assertEqual(status["policy"], "VENUE_MUTATION_BLOCKED")
        self.assertFalse(status["credentials_loaded"])
        self.assertFalse(status["network_access"])
        self.assertFalse(status["open_orders_loaded"])
        self.assertFalse(status["mutation_authorized"])
        self.assertNotIn("requests", source)
        self.assertNotIn("ccxt", source)
        self.assertNotIn("KRAKEN_API_KEY", source)
        self.assertNotIn("KRAKEN_API_SECRET", source)
        self.assertNotIn("luma_live_keys.env", source)
        self.assertNotRegex(source, r"/0/private/(?:CancelOrder|CancelAll)\b")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = module.main()
        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "blocked")

    def test_retired_payout_bridge_is_inert_and_import_safe(self) -> None:
        path = ROOT / "code" / "execution" / "payout_bridge.py"
        source = path.read_text(encoding="utf-8")
        module = load_path("payout_bridge_inert_test", path)

        status = module.build_inert_status()
        self.assertEqual(status["policy"], "CAPITAL_DISPATCH_BLOCKED")
        self.assertFalse(status["credentials_loaded"])
        self.assertFalse(status["network_access"])
        self.assertFalse(status["destination_loaded"])
        self.assertFalse(status["payout_intents_loaded"])
        self.assertFalse(status["transfer_authorized"])
        self.assertNotIn("requests", source)
        self.assertNotIn("httpx", source)
        self.assertNotIn("urlopen", source)
        self.assertNotIn("luma_live_keys.env", source)
        self.assertNotIn("webhook_url", source)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = module.main()
        self.assertEqual(exit_code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "blocked")

    def _load_multi_exchange_ticker_with_stubs(self):
        names = {
            "execution.crypto_allocator": {
                "optimize_candidate_weights": lambda *args, **kwargs: {},
            },
            "execution.adaptive_regime_router": {
                "route_crypto_signal": lambda *args, **kwargs: {},
                "route_equity_signal": lambda *args, **kwargs: {},
            },
            "execution.crypto_regime_controller": {
                "infer_market_regime": lambda *args, **kwargs: {},
            },
            "execution.order_router": {
                "OrderRouter": type("OrderRouter", (), {}),
                "RouteIntent": type("RouteIntent", (), {}),
            },
            "execution.shadow_runner": {
                "ShadowRunner": type("ShadowRunner", (), {}),
                "ShadowFill": type("ShadowFill", (), {}),
            },
            "execution.trade_ledger": {
                "TradeLedger": type("TradeLedger", (), {}),
            },
            "execution.audit_chain": {
                "AuditChain": type("AuditChain", (), {}),
            },
        }
        cleanup_names = (
            *names.keys(),
            "execution.alpaca_paper_executor",
            "execution.alpaca_paper_executor_legacy",
        )
        previous = {name: sys.modules.get(name) for name in cleanup_names}
        try:
            for name, attributes in names.items():
                stub = types.ModuleType(name)
                for attribute, value in attributes.items():
                    setattr(stub, attribute, value)
                sys.modules[name] = stub
            return load_path(
                "multi_exchange_paper_ticker_origin_test",
                ROOT / "code" / "multi_exchange_paper_ticker.py",
            )
        finally:
            for name, prior in previous.items():
                if prior is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = prior

    def test_multi_exchange_ticker_rejects_non_paper_origin_before_network(self) -> None:
        module = self._load_multi_exchange_ticker_with_stubs()
        calls = []

        def fake_request(**kwargs):
            calls.append(kwargs)
            raise AssertionError("network should not be reached")

        with patch.object(module.requests, "request", fake_request):
            result = module._alpaca_request(
                "POST",
                "https://api.alpaca.markets",
                "/v2/orders",
                "key",
                "secret",
                payload={"symbol": "AAPL"},
            )
        self.assertFalse(result["ok"])
        self.assertEqual(calls, [])

        with patch.dict(
            os.environ,
            {"ALPACA_BASE_URL": "https://api.alpaca.markets"},
            clear=True,
        ):
            with self.assertRaises(module.PaperEndpointError):
                module._resolve_alpaca_paper_base()

    def test_multi_exchange_ticker_blocks_redirects_on_exact_paper_origin(self) -> None:
        module = self._load_multi_exchange_ticker_with_stubs()
        calls = []

        class RedirectResponse:
            status_code = 302
            text = ""

        def fake_request(**kwargs):
            calls.append(kwargs)
            return RedirectResponse()

        with patch.object(module.requests, "request", fake_request):
            result = module._alpaca_request(
                "POST",
                module.PAPER_TRADING_ORIGIN,
                "/v2/orders",
                "key",
                "secret",
                payload={"symbol": "AAPL"},
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "paper_redirect_blocked")
        self.assertEqual(len(calls), 1)
        self.assertFalse(calls[0]["allow_redirects"])

    def test_auditor_rejects_unclassified_capital_transfer(self) -> None:
        auditor = load_path(
            "capital_transfer_auditor_test",
            ROOT / "code" / "ops" / "AUDIT_ORDER_SUBMISSION_PATHS.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "code").mkdir()
            (root / "code" / "unsafe_transfer.py").write_text(
                'exchange.withdraw("BTC", amount, address)\n',
                encoding="utf-8",
            )
            policy = {
                "version": "test",
                "promotion_stage": "live_data_no_orders",
                "patterns": {
                    "ccxt_withdraw_call": r"\.withdraw\s*\(",
                },
                "rules": [],
            }
            report = auditor.audit_repository(root, policy)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["active_unclassified_count"], 1)
        self.assertEqual(report["errors"][0]["code"], "unclassified_order_submission_path")

    def test_auditor_rejects_cancel_transfer_and_capital_endpoint_fixtures(self) -> None:
        auditor = load_path(
            "expanded_mutation_auditor_test",
            ROOT / "code" / "ops" / "AUDIT_ORDER_SUBMISSION_PATHS.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "code").mkdir()
            (root / "code" / "unsafe_mutations.py").write_text(
                'cancel = "/0/private/CancelAll"\n'
                'exchange.transfer("USDT", 1, "spot", "funding")\n'
                'capital = "/sapi/v1/capital/withdraw/apply"\n',
                encoding="utf-8",
            )
            policy = {
                "version": "test",
                "promotion_stage": "live_data_no_orders",
                "patterns": {
                    "kraken_cancel_all": r"/0/private/CancelAll\b",
                    "ccxt_transfer_call": r"\.transfer\s*\(",
                    "binance_capital_withdraw": (
                        r"/sapi/v[0-9]+/capital/withdraw/apply\b"
                    ),
                },
                "rules": [],
            }
            report = auditor.audit_repository(root, policy)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["active_unclassified_count"], 1)
        self.assertEqual(
            set(report["matches"][0]["patterns"]),
            {
                "kraken_cancel_all",
                "ccxt_transfer_call",
                "binance_capital_withdraw",
            },
        )

    def test_repository_capital_transfer_paths_are_classified(self) -> None:
        auditor = load_path(
            "repository_capital_transfer_auditor_test",
            ROOT / "code" / "ops" / "AUDIT_ORDER_SUBMISSION_PATHS.py",
        )
        policy = auditor.load_policy(ROOT / "config" / "order_submission_path_policy.json")
        report = auditor.audit_repository(ROOT, policy)
        self.assertEqual(report["status"], "pass", report["errors"])
        self.assertTrue(
            any(
                rule.get("path") == "code/kraken_auto_withdraw_btc.py"
                and rule.get("classification") == "capital_transfer_blocked_facade"
                and rule.get("required") is True
                for rule in policy["rules"]
            )
        )
        expected_rules = {
            "code/ops/cancel_open_orders.py": "venue_mutation_blocked_facade",
            "code/execution/payout_bridge.py": "capital_dispatch_blocked_facade",
            "code/multi_exchange_paper_ticker.py": "paper_supervisor_exact_host",
        }
        actual_rules = {
            str(rule.get("path")): str(rule.get("classification"))
            for rule in policy["rules"]
            if str(rule.get("path")) in expected_rules
        }
        self.assertEqual(actual_rules, expected_rules)


if __name__ == "__main__":
    unittest.main()
