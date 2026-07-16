from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "error": [],
            "result": {
                "XXBTZUSD": {
                    "c": ["100.0", "1"],
                    "b": ["99.0", "1"],
                    "a": ["101.0", "1"],
                    "v": ["2.0", "3.0"],
                }
            },
        }


class FakeSession:
    def __init__(self) -> None:
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse()


class TtyInput(io.StringIO):
    def isatty(self) -> bool:
        return True


class NonTtyInput(io.StringIO):
    def isatty(self) -> bool:
        return False


class PromotionLaneSafetyTests(unittest.TestCase):
    def test_read_only_orchestrator_has_no_submission_transport(self) -> None:
        path = ROOT / "code" / "execution" / "execution_orchestrator.py"
        source = path.read_text(encoding="utf-8")
        self.assertNotIn("/0/private/", source)
        self.assertNotIn("AddOrder", source)
        self.assertNotIn("/v2/orders", source)
        self.assertIn("/0/public/Ticker", source)

        module = load_path("read_only_orchestrator_test", path)
        session = FakeSession()
        snapshot = module.build_read_only_snapshot(session, ["XBT/USD"])
        self.assertEqual(snapshot["status"], "live_data_no_orders")
        self.assertTrue(snapshot["public_market_data_only"])
        self.assertFalse(snapshot["credentials_loaded"])
        self.assertFalse(snapshot["allow_live_orders"])
        self.assertTrue(snapshot["kill_switch"])
        self.assertEqual(session.calls[0]["params"], {"pair": "XBTUSD"})

    def test_read_only_snapshot_has_sha256_chain(self) -> None:
        module = load_path(
            "read_only_orchestrator_chain_test",
            ROOT / "code" / "execution" / "execution_orchestrator.py",
        )
        snapshot = module.build_read_only_snapshot(FakeSession(), ["XBTUSD"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = module.persist_snapshot(
                snapshot,
                heartbeat_path=root / "heartbeat.json",
                snapshot_path=root / "snapshot.json",
                ledger_path=root / "audit.jsonl",
            )
            module.persist_snapshot(
                snapshot,
                heartbeat_path=root / "heartbeat.json",
                snapshot_path=root / "snapshot.json",
                ledger_path=root / "audit.jsonl",
            )
            records = [
                json.loads(line)
                for line in (root / "audit.jsonl").read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(len(first["snapshot"]["snapshot_sha256"]), 64)
        self.assertEqual(records[1]["previous_sha256"], records[0]["record_sha256"])

    def test_manual_liquidation_requires_two_confirmations_reason_and_tty(self) -> None:
        module = load_path(
            "manual_liquidation_test",
            ROOT / "code" / "ops" / "LIQUIDATE_ALL_TO_USD.py",
        )
        dry = module.require_manual_emergency_confirmation(
            execute=False,
            confirm="",
            reason="",
            stdin=NonTtyInput(),
        )
        self.assertFalse(dry["authorized"])

        bad_cases = [
            ("WRONG", "manual emergency exit", TtyInput(), module.CONFIRM_PHRASE),
            (module.CONFIRM_PHRASE, "short", TtyInput(), module.CONFIRM_PHRASE),
            (module.CONFIRM_PHRASE, "manual emergency exit", NonTtyInput(), module.CONFIRM_PHRASE),
            (module.CONFIRM_PHRASE, "manual emergency exit", TtyInput(), "WRONG"),
        ]
        for confirm, reason, stdin, typed in bad_cases:
            with self.subTest(confirm=confirm, reason=reason, typed=typed):
                with self.assertRaises(RuntimeError):
                    module.require_manual_emergency_confirmation(
                        execute=True,
                        confirm=confirm,
                        reason=reason,
                        stdin=stdin,
                        prompt=lambda _message, value=typed: value,
                    )

        allowed = module.require_manual_emergency_confirmation(
            execute=True,
            confirm=module.CONFIRM_PHRASE,
            reason="manual emergency exit",
            stdin=TtyInput(),
            prompt=lambda _message: module.CONFIRM_PHRASE,
        )
        self.assertTrue(allowed["authorized"])
        self.assertEqual(len(allowed["authorization_sha256"]), 64)

    def test_auditor_rejects_new_unclassified_path(self) -> None:
        module = load_path(
            "order_path_audit_test",
            ROOT / "code" / "ops" / "AUDIT_ORDER_SUBMISSION_PATHS.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "code").mkdir()
            (root / "code" / "new_live.py").write_text('ENDPOINT = "AddOrder"\n', encoding="utf-8")
            policy = {
                "version": "test",
                "promotion_stage": "live_data_no_orders",
                "patterns": {"kraken_add_order": r"\bAddOrder\b"},
                "rules": [{"path": "tests/**", "classification": "test_fixture"}],
            }
            report = module.audit_repository(root, policy)
        self.assertEqual(report["status"], "fail")
        self.assertEqual(report["active_unclassified_count"], 1)

    def test_auditor_checks_locked_blob_and_read_only_invariants(self) -> None:
        module = load_path(
            "order_path_audit_invariant_test",
            ROOT / "code" / "ops" / "AUDIT_ORDER_SUBMISSION_PATHS.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "code" / "engine_legacy.py"
            monitor = root / "code" / "execution" / "monitor.py"
            legacy.parent.mkdir(parents=True)
            monitor.parent.mkdir(parents=True)
            legacy.write_text('ENDPOINT = "AddOrder"\n', encoding="utf-8")
            monitor.write_text(
                "public_market_data_only=True\ncredentials_loaded=False\n"
                "allow_live_orders=False\nstage='live_data_no_orders'\n",
                encoding="utf-8",
            )
            policy = {
                "version": "test",
                "promotion_stage": "live_data_no_orders",
                "patterns": {"kraken_add_order": r"\bAddOrder\b"},
                "rules": [
                    {
                        "path": "code/engine_legacy.py",
                        "classification": "historical_preserved",
                        "expected_git_blob_sha": "0" * 40,
                    },
                    {
                        "path": "code/execution/monitor.py",
                        "classification": "read_only_monitor",
                        "required": True,
                    },
                ],
            }
            report = module.audit_repository(root, policy)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(any(error["code"] == "preserved_blob_mismatch" for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
