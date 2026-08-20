#!/usr/bin/env python3
"""Create a sealed, non-destructive migration of a legacy paper ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from execution.audit_chain import AuditChain  # noqa: E402
from execution.trade_ledger import TradeLedger  # noqa: E402
from ops.VERIFY_PAPER_LEDGER_RECONCILIATION import (  # noqa: E402
    build_receipt,
    write_json_atomic,
)


ACKNOWLEDGEMENT = "preserve-source-and-seal-legacy-boundary"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_hashes(
    source_csv: Path,
    source_jsonl: Path,
    source_audit_chain: Path,
) -> dict[str, str | None]:
    return {
        "csv": sha256_file(source_csv) if source_csv.is_file() else None,
        "jsonl": sha256_file(source_jsonl),
        "audit_chain": (
            sha256_file(source_audit_chain)
            if source_audit_chain.is_file()
            else None
        ),
    }


def _require_stable_sources(
    expected: dict[str, str | None],
    observed: dict[str, str | None],
    *,
    phase: str,
) -> None:
    changed = sorted(name for name in expected if expected[name] != observed[name])
    if changed:
        raise ValueError(
            f"source files changed during {phase}: {', '.join(changed)}"
        )


def _require_empty_destination(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise ValueError("destination must be absent or empty")
    path.mkdir(parents=True, exist_ok=True)


def migrate(
    source_csv: str | Path,
    source_jsonl: str | Path,
    source_audit_chain: str | Path,
    output_dir: str | Path,
    *,
    acknowledgement: str,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    if acknowledgement != ACKNOWLEDGEMENT:
        raise ValueError(f"acknowledgement must equal {ACKNOWLEDGEMENT!r}")

    source_csv = Path(source_csv)
    source_jsonl = Path(source_jsonl)
    source_audit_chain = Path(source_audit_chain)
    output_dir = Path(output_dir)
    if not source_jsonl.is_file():
        raise FileNotFoundError("authoritative source JSONL ledger is missing")

    source_hashes_before_verification = _source_hashes(
        source_csv, source_jsonl, source_audit_chain
    )
    source_ledger_verification = TradeLedger.verify_jsonl(source_jsonl)
    if source_ledger_verification["status"] != "pass":
        raise ValueError("source JSONL ledger must verify before migration")
    source_audit_verification = AuditChain.verify_file(source_audit_chain)
    source_csv_verification = TradeLedger.verify_csv_mirror(source_csv, source_jsonl)
    source_hashes_after_verification = _source_hashes(
        source_csv, source_jsonl, source_audit_chain
    )
    _require_stable_sources(
        source_hashes_before_verification,
        source_hashes_after_verification,
        phase="source verification",
    )

    _require_empty_destination(output_dir)
    destination_jsonl = output_dir / "multi_exchange_trade_ledger.jsonl"
    destination_csv = output_dir / "multi_exchange_trade_ledger.csv"
    destination_audit = output_dir / "execution_audit_chain.jsonl"
    preserved_source_audit = output_dir / "legacy_source_execution_audit_chain.jsonl"
    receipt_path = output_dir / "paper_ledger_migration_receipt.json"

    shutil.copyfile(source_jsonl, destination_jsonl)
    if source_audit_chain.is_file():
        shutil.copyfile(source_audit_chain, preserved_source_audit)

    source_hashes_after_copy = _source_hashes(
        source_csv, source_jsonl, source_audit_chain
    )
    _require_stable_sources(
        source_hashes_before_verification,
        source_hashes_after_copy,
        phase="destination capture",
    )
    destination_jsonl_sha256 = sha256_file(destination_jsonl)
    if destination_jsonl_sha256 != source_hashes_before_verification["jsonl"]:
        raise ValueError("destination JSONL does not match the verified source bytes")
    destination_source_audit_sha256 = (
        sha256_file(preserved_source_audit)
        if preserved_source_audit.is_file()
        else None
    )
    if (
        destination_source_audit_sha256
        != source_hashes_before_verification["audit_chain"]
    ):
        raise ValueError("preserved audit chain does not match the verified source bytes")

    ledger = TradeLedger(str(destination_csv), str(destination_jsonl))
    ledger.repair_csv_mirror()

    source_ledger_sha256 = source_hashes_before_verification["jsonl"]
    source_audit_sha256 = source_hashes_before_verification["audit_chain"]
    migration_time = generated_utc or datetime.now(timezone.utc).isoformat()
    audit = AuditChain(destination_audit)
    audit.append(
        "legacy_reconciliation_manifest",
        {
            "migration_time_utc": migration_time,
            "source_ledger_sha256": source_ledger_sha256,
            "source_audit_sha256": source_audit_sha256,
            "source_audit_status": source_audit_verification["status"],
            "source_audit_error_counts": source_audit_verification.get("error_counts", {}),
            "source_record_count": source_ledger_verification["record_count"],
            "boundary": (
                "Imported links prove migration custody only; they do not reconstruct or certify "
                "the timing or completeness of legacy execution events."
            ),
        },
        event_time_utc=migration_time,
    )

    with destination_jsonl.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            record = json.loads(raw_line)
            audit.append(
                "legacy_ledger_reconciliation_import",
                {
                    "ledger_hash": record["record_hash"],
                    "source_ledger_sha256": source_ledger_sha256,
                    "source_record_line": line_number,
                    "linkage_type": "retrospective_migration_custody",
                },
                event_time_utc=migration_time,
            )

    destination_receipt = build_receipt(
        destination_csv,
        destination_jsonl,
        destination_audit,
        generated_utc=migration_time,
    )
    migration_receipt = {
        "schema_version": "1.0",
        "generated_utc": migration_time,
        "status": destination_receipt["status"],
        "mutation_scope": "new_destination_only",
        "source_files_modified": False,
        "source_capture": {
            "hashes_before_verification": source_hashes_before_verification,
            "hashes_after_verification": source_hashes_after_verification,
            "hashes_after_copy": source_hashes_after_copy,
            "destination_jsonl_sha256": destination_jsonl_sha256,
            "destination_source_audit_sha256": destination_source_audit_sha256,
            "source_stable": True,
            "destination_copies_match_sources": True,
        },
        "legacy_boundary": {
            "authoritative_jsonl": source_ledger_verification,
            "csv_mirror": source_csv_verification,
            "audit_chain": source_audit_verification,
            "source_ledger_sha256": source_ledger_sha256,
            "source_csv_sha256": source_hashes_before_verification["csv"],
            "source_audit_sha256": source_audit_sha256,
        },
        "destination_reconciliation": destination_receipt,
        "claim_boundary": (
            "A passing migration receipt proves byte-preserved ledger custody, deterministic CSV "
            "reconstruction, and a new migration audit chain. It does not retroactively prove that "
            "the legacy audit chain was complete or un-forked."
        ),
    }
    write_json_atomic(receipt_path, migration_receipt)
    return migration_receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-csv", type=Path, required=True)
    parser.add_argument("--source-jsonl", type=Path, required=True)
    parser.add_argument("--source-audit-chain", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--acknowledgement", required=True)
    parser.add_argument("--generated-utc")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = migrate(
        args.source_csv,
        args.source_jsonl,
        args.source_audit_chain,
        args.output_dir,
        acknowledgement=args.acknowledgement,
        generated_utc=args.generated_utc,
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "source_files_modified": receipt["source_files_modified"],
                "output_dir": str(args.output_dir),
            },
            sort_keys=True,
        )
    )
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
