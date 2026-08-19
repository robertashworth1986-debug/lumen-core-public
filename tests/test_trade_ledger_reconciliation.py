from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from execution.audit_chain import (  # noqa: E402
    AuditChain,
    AuditChainIntegrityError,
)
from execution.trade_ledger import (  # noqa: E402
    LEDGER_SCHEMA_VERSION,
    LedgerIntegrityError,
    TradeLedger,
)


VERIFY_PATH = ROOT / "code" / "ops" / "VERIFY_PAPER_LEDGER_RECONCILIATION.py"
MIGRATE_PATH = ROOT / "code" / "ops" / "MIGRATE_PAPER_LEDGER_RECONCILIATION.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("paper_ledger_reconciliation", VERIFY_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_migrator():
    spec = importlib.util.spec_from_file_location("paper_ledger_migration", MIGRATE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_legacy_record(path: Path, body: dict) -> str:
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    record = {**body, "record_hash": digest}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    return digest


class TradeLedgerReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.csv_path = self.root / "trade_ledger.csv"
        self.jsonl_path = self.root / "trade_ledger.jsonl"
        self.audit_path = self.root / "audit_chain.jsonl"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_v2_chain_and_variable_rows_reconcile_to_stable_csv(self) -> None:
        ledger = TradeLedger(str(self.csv_path), str(self.jsonl_path))
        first_hash = ledger.append({"symbol": "AAA", "side": "buy", "entry_price": 10})
        second_hash = ledger.append(
            {
                "symbol": "AAA",
                "side": "sell",
                "entry_price": 10,
                "exit_price": 11,
                "net_pnl": 1,
            }
        )

        json_result = TradeLedger.verify_jsonl(self.jsonl_path)
        csv_result = TradeLedger.verify_csv_mirror(self.csv_path, self.jsonl_path)
        records = [json.loads(line) for line in self.jsonl_path.read_text().splitlines()]
        csv_rows = self.csv_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(json_result["status"], "pass")
        self.assertEqual(json_result["chained_record_count"], 2)
        self.assertEqual(csv_result["status"], "pass")
        self.assertEqual(records[0]["ledger_schema_version"], LEDGER_SCHEMA_VERSION)
        self.assertEqual(records[0]["prev_record_hash"], "GENESIS")
        self.assertEqual(records[1]["prev_record_hash"], first_hash)
        self.assertEqual(records[1]["record_hash"], second_hash)
        self.assertEqual(len({len(row.split(",")) for row in csv_rows}), 1)

    def test_legacy_records_anchor_first_v2_record_without_rewriting_history(self) -> None:
        first_hash = write_legacy_record(
            self.jsonl_path,
            {"symbol": "AAA", "side": "buy", "logged_utc": "2026-01-01T00:00:00Z"},
        )
        second_hash = write_legacy_record(
            self.jsonl_path,
            {
                "symbol": "AAA",
                "side": "sell",
                "ledger_schema_version": "1.1.0",
                "logged_utc": "2026-01-01T01:00:00Z",
            },
        )
        before = self.jsonl_path.read_text(encoding="utf-8")

        ledger = TradeLedger(str(self.csv_path), str(self.jsonl_path))
        third_hash = ledger.append({"symbol": "BBB", "side": "buy"})
        records = [json.loads(line) for line in self.jsonl_path.read_text().splitlines()]
        result = TradeLedger.reconciliation_receipt(self.csv_path, self.jsonl_path)

        self.assertTrue(self.jsonl_path.read_text(encoding="utf-8").startswith(before))
        self.assertEqual(records[0]["record_hash"], first_hash)
        self.assertEqual(records[1]["record_hash"], second_hash)
        self.assertEqual(records[2]["prev_record_hash"], second_hash)
        self.assertEqual(records[2]["record_hash"], third_hash)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["authoritative_jsonl"]["legacy_unlinked_count"], 2)
        self.assertEqual(result["authoritative_jsonl"]["chained_record_count"], 1)

    def test_tampered_ledger_fails_closed(self) -> None:
        ledger = TradeLedger(str(self.csv_path), str(self.jsonl_path))
        ledger.append({"symbol": "AAA", "side": "buy"})
        text = self.jsonl_path.read_text(encoding="utf-8").replace('"AAA"', '"BBB"')
        self.jsonl_path.write_text(text, encoding="utf-8")

        result = TradeLedger.verify_jsonl(self.jsonl_path)
        self.assertEqual(result["status"], "fail")
        self.assertIn("record hash mismatch", {error["reason"] for error in result["errors"]})
        with self.assertRaises(LedgerIntegrityError):
            TradeLedger(str(self.csv_path), str(self.jsonl_path))

    def test_csv_drift_is_detected_without_mutating_jsonl(self) -> None:
        ledger = TradeLedger(str(self.csv_path), str(self.jsonl_path))
        ledger.append({"symbol": "AAA", "side": "buy"})
        original_jsonl = self.jsonl_path.read_bytes()
        self.csv_path.write_text("wrong,header\n1,2\n", encoding="utf-8")

        result = TradeLedger.verify_csv_mirror(self.csv_path, self.jsonl_path)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(self.jsonl_path.read_bytes(), original_jsonl)

    def test_independent_ledger_writers_reverify_under_append_lock(self) -> None:
        first_writer = TradeLedger(str(self.csv_path), str(self.jsonl_path))
        second_writer = TradeLedger(str(self.csv_path), str(self.jsonl_path))
        first_hash = first_writer.append({"symbol": "AAA", "side": "buy"})
        second_hash = second_writer.append({"symbol": "BBB", "side": "buy"})

        records = [json.loads(line) for line in self.jsonl_path.read_text().splitlines()]
        self.assertEqual(records[1]["prev_record_hash"], first_hash)
        self.assertEqual(records[1]["record_hash"], second_hash)
        self.assertEqual(TradeLedger.verify_jsonl(self.jsonl_path)["status"], "pass")
        self.assertFalse(Path(str(self.jsonl_path) + ".append.lock").exists())

    def test_audit_chain_verifies_and_rejects_tampering(self) -> None:
        chain = AuditChain(self.audit_path)
        first = chain.append("paper_buy", {"ledger_hash": "a" * 64})
        second = chain.append("paper_sell", {"ledger_hash": "b" * 64})
        result = AuditChain.verify_file(self.audit_path)

        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["event_count"], 2)
        self.assertEqual(result["first_event_hash"], first["event_hash"])
        self.assertEqual(result["terminal_event_hash"], second["event_hash"])

        text = self.audit_path.read_text(encoding="utf-8").replace("paper_buy", "paper_hold", 1)
        self.audit_path.write_text(text, encoding="utf-8")
        self.assertEqual(AuditChain.verify_file(self.audit_path)["status"], "fail")
        with self.assertRaises(AuditChainIntegrityError):
            AuditChain(self.audit_path)

    def test_stale_audit_writer_cannot_fork_chain(self) -> None:
        first_writer = AuditChain(self.audit_path)
        stale_writer = AuditChain(self.audit_path)
        first_writer.append("paper_buy", {"ledger_hash": "a" * 64})

        with self.assertRaises(AuditChainIntegrityError):
            stale_writer.append("paper_buy", {"ledger_hash": "b" * 64})
        self.assertEqual(AuditChain.verify_file(self.audit_path)["status"], "pass")
        self.assertFalse(Path(str(self.audit_path) + ".append.lock").exists())

    def test_complete_receipt_requires_one_audit_link_per_ledger_record(self) -> None:
        verifier = load_verifier()
        ledger = TradeLedger(str(self.csv_path), str(self.jsonl_path))
        record_hash = ledger.append({"symbol": "AAA", "side": "buy"})
        chain = AuditChain(self.audit_path)
        chain.append("paper_buy", {"ledger_hash": record_hash})

        passing = verifier.build_receipt(
            self.csv_path,
            self.jsonl_path,
            self.audit_path,
            generated_utc="2026-08-19T00:00:00+00:00",
        )
        self.assertEqual(passing["status"], "pass")
        self.assertEqual(passing["execution_boundary"], "paper_only")
        self.assertEqual(passing["audit_linkage"]["missing_audit_link_count"], 0)

        other_jsonl = self.root / "missing_link.jsonl"
        other_csv = self.root / "missing_link.csv"
        other_audit = self.root / "missing_link_audit.jsonl"
        TradeLedger(str(other_csv), str(other_jsonl)).append({"symbol": "BBB", "side": "buy"})
        failing = verifier.build_receipt(
            other_csv,
            other_jsonl,
            other_audit,
            generated_utc="2026-08-19T00:00:00+00:00",
        )
        self.assertEqual(failing["status"], "fail")
        self.assertEqual(failing["audit_linkage"]["missing_audit_link_count"], 1)

    def test_migration_preserves_sources_and_seals_legacy_boundary(self) -> None:
        migrator = load_migrator()
        write_legacy_record(
            self.jsonl_path,
            {"symbol": "AAA", "side": "buy", "logged_utc": "2026-01-01T00:00:00Z"},
        )
        write_legacy_record(
            self.jsonl_path,
            {"symbol": "AAA", "side": "sell", "logged_utc": "2026-01-01T01:00:00Z"},
        )
        self.csv_path.write_text("symbol,side\nAAA,buy,extra\n", encoding="utf-8")
        AuditChain(self.audit_path).append("paper_buy", {"ledger_hash": "a" * 64})
        fork_path = self.root / "fork.jsonl"
        AuditChain(fork_path).append("paper_sell", {"ledger_hash": "b" * 64})
        with self.audit_path.open("a", encoding="utf-8") as target:
            target.write(fork_path.read_text(encoding="utf-8"))

        source_hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (self.csv_path, self.jsonl_path, self.audit_path)
        }
        output_dir = self.root / "migrated"
        receipt = migrator.migrate(
            self.csv_path,
            self.jsonl_path,
            self.audit_path,
            output_dir,
            acknowledgement=migrator.ACKNOWLEDGEMENT,
            generated_utc="2026-08-19T00:00:00+00:00",
        )

        self.assertEqual(receipt["status"], "pass")
        self.assertFalse(receipt["source_files_modified"])
        self.assertEqual(receipt["legacy_boundary"]["audit_chain"]["status"], "fail")
        self.assertEqual(receipt["legacy_boundary"]["csv_mirror"]["status"], "fail")
        self.assertEqual(receipt["destination_reconciliation"]["status"], "pass")
        for path, digest in source_hashes.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        self.assertEqual(
            hashlib.sha256((output_dir / "legacy_source_execution_audit_chain.jsonl").read_bytes()).hexdigest(),
            source_hashes[self.audit_path],
        )


if __name__ == "__main__":
    unittest.main()
