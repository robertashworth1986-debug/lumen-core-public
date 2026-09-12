#!/usr/bin/env python3
"""Build a read-only, fail-closed paper-ledger reconciliation receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from execution.audit_chain import AuditChain  # noqa: E402
from execution.trade_ledger import TradeLedger  # noqa: E402


DEFAULT_EXECUTION_DIR = ROOT / "out" / "execution"
DEFAULT_CSV = DEFAULT_EXECUTION_DIR / "multi_exchange_trade_ledger.csv"
DEFAULT_JSONL = DEFAULT_EXECUTION_DIR / "multi_exchange_trade_ledger.jsonl"
DEFAULT_AUDIT_CHAIN = DEFAULT_EXECUTION_DIR / "execution_audit_chain.jsonl"
DEFAULT_OUTPUT = ROOT / "out" / "ops" / "paper_ledger_reconciliation_latest.json"
LINKED_EVENT_TYPES = {
    "paper_buy",
    "paper_sell",
    "legacy_ledger_reconciliation_import",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protocol_receipts() -> list[dict[str, Any]]:
    paths = (
        ROOT / "code" / "execution" / "trade_ledger.py",
        ROOT / "code" / "execution" / "audit_chain.py",
        Path(__file__).resolve(),
    )
    return [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in paths
    ]


def _ledger_hashes(path: Path) -> list[str]:
    if not path.exists():
        return []
    hashes: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            if raw_line.strip():
                record = json.loads(raw_line)
                hashes.append(str(record["record_hash"]))
    return hashes


def verify_audit_linkage(
    jsonl_path: Path,
    audit_chain_path: Path,
    ledger_status: str,
    audit_status: str,
) -> dict[str, Any]:
    if ledger_status != "pass" or audit_status != "pass":
        return {
            "status": "fail",
            "ledger_hash_count": 0,
            "linked_audit_hash_count": 0,
            "missing_audit_link_count": 0,
            "orphan_audit_link_count": 0,
            "duplicate_audit_link_count": 0,
            "errors": ["linkage not evaluated because an input failed verification"],
        }

    ledger_hashes = _ledger_hashes(jsonl_path)
    ledger_set = set(ledger_hashes)
    audit_links: list[str] = []
    for event in AuditChain.iter_verified_events(audit_chain_path):
        if event.get("event_type") not in LINKED_EVENT_TYPES:
            continue
        payload = event.get("payload")
        if isinstance(payload, dict) and payload.get("ledger_hash"):
            audit_links.append(str(payload["ledger_hash"]))

    audit_counts = Counter(audit_links)
    audit_set = set(audit_links)
    missing = ledger_set.difference(audit_set)
    orphan = audit_set.difference(ledger_set)
    duplicates = {digest for digest, count in audit_counts.items() if count != 1}
    duplicate_ledger_hashes = len(ledger_hashes) - len(ledger_set)
    errors: list[str] = []
    if missing:
        errors.append("ledger records are missing audit-chain links")
    if orphan:
        errors.append("audit-chain links do not resolve to ledger records")
    if duplicates:
        errors.append("ledger hashes are linked more than once in the audit chain")
    if duplicate_ledger_hashes:
        errors.append("ledger contains duplicate record hashes")

    return {
        "status": "pass" if not errors else "fail",
        "ledger_hash_count": len(ledger_hashes),
        "linked_audit_hash_count": len(audit_links),
        "missing_audit_link_count": len(missing),
        "orphan_audit_link_count": len(orphan),
        "duplicate_audit_link_count": len(duplicates),
        "duplicate_ledger_hash_count": duplicate_ledger_hashes,
        "errors": errors,
    }


def build_receipt(
    csv_path: str | Path,
    jsonl_path: str | Path,
    audit_chain_path: str | Path,
    *,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    csv_path = Path(csv_path)
    jsonl_path = Path(jsonl_path)
    audit_chain_path = Path(audit_chain_path)
    ledger = TradeLedger.reconciliation_receipt(csv_path, jsonl_path)
    audit = AuditChain.verify_file(audit_chain_path)
    linkage = verify_audit_linkage(
        jsonl_path,
        audit_chain_path,
        ledger["authoritative_jsonl"]["status"],
        audit["status"],
    )
    status = (
        "pass"
        if ledger["status"] == audit["status"] == linkage["status"] == "pass"
        else "fail"
    )
    return {
        "schema_version": "1.0",
        "generated_utc": generated_utc or datetime.now(timezone.utc).isoformat(),
        "status": status,
        "execution_boundary": "paper_only",
        "claim_boundary": (
            "A passing receipt proves internal file integrity, CSV parity, and audit linkage only; "
            "it does not prove profitability, alpha, external validation, production readiness, "
            "or authority to trade live capital."
        ),
        "ledger": ledger,
        "audit_chain": audit,
        "audit_linkage": linkage,
        "protocol_receipts": protocol_receipts(),
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent), text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    parser.add_argument("--audit-chain", type=Path, default=DEFAULT_AUDIT_CHAIN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--generated-utc")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = build_receipt(
        args.csv,
        args.jsonl,
        args.audit_chain,
        generated_utc=args.generated_utc,
    )
    write_json_atomic(args.output, receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "ledger_records": receipt["ledger"]["authoritative_jsonl"]["record_count"],
                "audit_events": receipt["audit_chain"]["event_count"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
