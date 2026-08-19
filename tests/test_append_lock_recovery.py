from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from execution.append_lock import (  # noqa: E402
    AppendLockError,
    LOCK_SCHEMA_VERSION,
    exclusive_append_lock,
)
from execution.audit_chain import AuditChain  # noqa: E402
from execution.trade_ledger import TradeLedger  # noqa: E402


def write_lock(path: Path, *, pid: int, age_seconds: float, token: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": LOCK_SCHEMA_VERSION,
                "pid": pid,
                "hostname": socket.gethostname(),
                "created_unix_ns": time.time_ns() - int(age_seconds * 1_000_000_000),
                "owner_token": token,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


class AppendLockRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_trade_ledger_reclaims_old_dead_process_lock(self) -> None:
        csv_path = self.root / "ledger.csv"
        jsonl_path = self.root / "ledger.jsonl"
        lock_path = Path(str(jsonl_path) + ".append.lock")
        write_lock(lock_path, pid=999_999, age_seconds=60, token="dead-ledger")

        with mock.patch("execution.append_lock._process_is_alive", return_value=False):
            digest = TradeLedger(str(csv_path), str(jsonl_path)).append(
                {"symbol": "AAA", "side": "buy"}
            )

        self.assertEqual(len(digest), 64)
        self.assertEqual(TradeLedger.verify_jsonl(jsonl_path)["status"], "pass")
        self.assertFalse(lock_path.exists())

    def test_audit_chain_reclaims_old_dead_process_lock(self) -> None:
        audit_path = self.root / "audit.jsonl"
        lock_path = Path(str(audit_path) + ".append.lock")
        write_lock(lock_path, pid=999_999, age_seconds=60, token="dead-audit")

        chain = AuditChain(audit_path)
        with mock.patch("execution.append_lock._process_is_alive", return_value=False):
            event = chain.append("paper_buy", {"ledger_hash": "a" * 64})

        self.assertEqual(len(event["event_hash"]), 64)
        self.assertEqual(AuditChain.verify_file(audit_path)["status"], "pass")
        self.assertFalse(lock_path.exists())

    def test_live_owner_is_never_reclaimed(self) -> None:
        lock_path = self.root / "live.append.lock"
        write_lock(lock_path, pid=os.getpid(), age_seconds=60, token="live-owner")

        with self.assertRaises(AppendLockError):
            with exclusive_append_lock(
                lock_path,
                timeout_seconds=0.05,
                stale_after_seconds=0.01,
            ):
                self.fail("a live owner's lock must not be acquired")

        self.assertEqual(json.loads(lock_path.read_text())["owner_token"], "live-owner")

    def test_fresh_malformed_lock_is_not_reclaimed(self) -> None:
        lock_path = self.root / "malformed.append.lock"
        lock_path.write_bytes(b"not-json")

        with self.assertRaises(AppendLockError):
            with exclusive_append_lock(
                lock_path,
                timeout_seconds=0.05,
                stale_after_seconds=30,
            ):
                self.fail("fresh malformed residue must fail closed")

        self.assertEqual(lock_path.read_bytes(), b"not-json")

    def test_old_malformed_lock_is_not_reclaimed_without_owner_evidence(self) -> None:
        lock_path = self.root / "old-malformed.append.lock"
        lock_path.write_bytes(b"not-json")
        old = time.time() - 120
        os.utime(lock_path, (old, old))

        with self.assertRaises(AppendLockError):
            with exclusive_append_lock(
                lock_path,
                timeout_seconds=0.05,
                stale_after_seconds=0.01,
            ):
                self.fail("malformed residue must require operator review")

        self.assertEqual(lock_path.read_bytes(), b"not-json")

    def test_foreign_host_lock_is_not_reclaimed(self) -> None:
        lock_path = self.root / "foreign-host.append.lock"
        lock_path.write_text(
            json.dumps(
                {
                    "schema_version": LOCK_SCHEMA_VERSION,
                    "pid": 999_999,
                    "hostname": "another-host",
                    "created_unix_ns": time.time_ns() - 120_000_000_000,
                    "owner_token": "foreign-owner",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        with self.assertRaises(AppendLockError):
            with exclusive_append_lock(
                lock_path,
                timeout_seconds=0.05,
                stale_after_seconds=0.01,
            ):
                self.fail("a foreign-host owner cannot be proved dead locally")

        self.assertEqual(
            json.loads(lock_path.read_text(encoding="utf-8"))["owner_token"],
            "foreign-owner",
        )

    def test_cleanup_does_not_remove_successor_lock(self) -> None:
        lock_path = self.root / "ownership.append.lock"
        with exclusive_append_lock(lock_path) as owner:
            successor = {
                "schema_version": LOCK_SCHEMA_VERSION,
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
                "created_unix_ns": time.time_ns(),
                "owner_token": "successor-token",
            }
            lock_path.write_text(json.dumps(successor) + "\n", encoding="utf-8")
            self.assertNotEqual(owner["owner_token"], successor["owner_token"])

        self.assertTrue(lock_path.exists())
        self.assertEqual(
            json.loads(lock_path.read_text(encoding="utf-8"))["owner_token"],
            "successor-token",
        )


if __name__ == "__main__":
    unittest.main()
