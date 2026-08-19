from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_EXEC = ROOT / "out" / "execution"
PAPER_LEDGER = ROOT / "out" / "paper_trade_ledger.jsonl"
REAL_API_LEDGER = ROOT / "out" / "paper_trade_real_api_ledger.jsonl"
PAPER_CANONICAL = OUT_EXEC / "paper_trade_ledger_canonical.jsonl"
REAL_API_CANONICAL = OUT_EXEC / "paper_trade_real_api_ledger_canonical.jsonl"
RECEIPT_FILE = OUT_EXEC / "paper_ledger_reconciliation.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            Path(tmp_name).unlink()
        except FileNotFoundError:
            pass


def _fill_identity(row: dict[str, Any]) -> str:
    event_type = str(row.get("event_type") or "").strip().lower()
    if row.get("fill_id") is None and not event_type.endswith("fill"):
        return ""
    return str(row.get("fill_id") or "").strip()


def reconcile_ledger(source: Path, canonical: Path) -> dict[str, Any]:
    if not source.exists():
        return {
            "status": "FAIL",
            "reason": "source_missing",
            "source_path": rel(source),
            "canonical_path": rel(canonical),
        }

    before = source.stat()
    source_sha256 = sha256_file(source)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(prefix=f".{canonical.name}.", suffix=".tmp", dir=canonical.parent)
    seen_fill_ids: set[str] = set()
    total_rows = valid_rows = invalid_rows = fill_rows = duplicate_fill_rows = 0
    missing_fill_id_rows = snapshot_rows = canonical_rows = 0
    max_snapshot_trade_count = 0
    first_timestamp = ""
    latest_timestamp = ""

    try:
        with source.open("r", encoding="utf-8", errors="replace") as src, os.fdopen(
            descriptor, "w", encoding="utf-8", newline="\n"
        ) as dst:
            for raw_line in src:
                line = raw_line.strip()
                if not line:
                    continue
                total_rows += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    invalid_rows += 1
                    continue
                if not isinstance(row, dict):
                    invalid_rows += 1
                    continue
                valid_rows += 1
                timestamp = str(row.get("timestamp") or row.get("timestamp_utc") or "").strip()
                if timestamp:
                    first_timestamp = min(first_timestamp, timestamp) if first_timestamp else timestamp
                    latest_timestamp = max(latest_timestamp, timestamp)
                event_type = str(row.get("event_type") or "").strip().lower()
                if event_type == "account_snapshot":
                    snapshot_rows += 1
                    try:
                        max_snapshot_trade_count = max(
                            max_snapshot_trade_count, int(float(row.get("trade_count") or 0))
                        )
                    except (TypeError, ValueError):
                        pass
                fill_id = _fill_identity(row)
                is_fill = row.get("fill_id") is not None or event_type.endswith("fill")
                if is_fill:
                    fill_rows += 1
                    if not fill_id:
                        missing_fill_id_rows += 1
                    elif fill_id in seen_fill_ids:
                        duplicate_fill_rows += 1
                        continue
                    else:
                        seen_fill_ids.add(fill_id)
                dst.write(json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n")
                canonical_rows += 1
            dst.flush()
            os.fsync(dst.fileno())

        after = source.stat()
        source_changed = before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns
        if source_changed or sha256_file(source) != source_sha256:
            return {
                "status": "FAIL",
                "reason": "source_changed_during_reconciliation",
                "source_path": rel(source),
                "canonical_path": rel(canonical),
            }
        os.replace(tmp_name, canonical)
    finally:
        try:
            Path(tmp_name).unlink()
        except FileNotFoundError:
            pass

    status = "PASS" if invalid_rows == 0 and missing_fill_id_rows == 0 else "FAIL"
    target_basename = ""
    if source.is_symlink():
        try:
            target_basename = source.readlink().name
        except OSError:
            pass
    return {
        "status": status,
        "reason": "canonical_unique_fill_view_built" if status == "PASS" else "source_integrity_failure",
        "source_path": rel(source),
        "source_is_symlink": source.is_symlink(),
        "source_target_basename": target_basename,
        "source_sha256": source_sha256,
        "source_bytes": before.st_size,
        "source_total_rows": total_rows,
        "source_valid_rows": valid_rows,
        "source_invalid_rows": invalid_rows,
        "source_fill_rows": fill_rows,
        "source_unique_fill_ids": len(seen_fill_ids),
        "source_duplicate_fill_rows": duplicate_fill_rows,
        "source_missing_fill_id_rows": missing_fill_id_rows,
        "snapshot_rows": snapshot_rows,
        "max_snapshot_trade_count": max_snapshot_trade_count,
        "first_timestamp": first_timestamp,
        "latest_timestamp": latest_timestamp,
        "canonical_path": rel(canonical),
        "canonical_sha256": sha256_file(canonical),
        "canonical_bytes": canonical.stat().st_size,
        "canonical_total_rows": canonical_rows,
        "canonical_fill_rows": len(seen_fill_ids),
        "canonical_unique_fill_ids": len(seen_fill_ids),
        "canonical_duplicate_fill_rows": 0,
    }


def build_reconciliation() -> dict[str, Any]:
    ledgers = {
        "paper_ledger": reconcile_ledger(PAPER_LEDGER, PAPER_CANONICAL),
        "real_api_ledger": reconcile_ledger(REAL_API_LEDGER, REAL_API_CANONICAL),
    }
    status = "PASS" if all(row.get("status") == "PASS" for row in ledgers.values()) else "FAIL"
    receipt = {
        "schema": "paper_ledger_reconciliation_v1",
        "generated_utc": now_utc(),
        "status": status,
        "raw_evidence_preserved": True,
        "canonical_policy": "Preserve every valid non-fill event and the first occurrence of each nonempty fill_id; never rewrite the raw ledgers.",
        "claim_boundary": "Reconciliation proves local row identity and custody consistency only. It does not prove alpha, profitability, independent validation, or live readiness.",
        "ledgers": ledgers,
    }
    _atomic_write_json(RECEIPT_FILE, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Build non-destructive canonical paper-ledger views")
    parser.parse_args()
    receipt = build_reconciliation()
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "receipt": str(RECEIPT_FILE),
                "ledgers": {
                    key: {
                        "raw_rows": row.get("source_total_rows", 0),
                        "unique_fills": row.get("source_unique_fill_ids", 0),
                        "duplicates_excluded": row.get("source_duplicate_fill_rows", 0),
                        "canonical_sha256": row.get("canonical_sha256", ""),
                    }
                    for key, row in receipt["ledgers"].items()
                },
            },
            indent=2,
        )
    )
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
