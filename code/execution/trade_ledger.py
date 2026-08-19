from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from .append_lock import exclusive_append_lock
except ImportError:  # Direct execution imports this module from code/execution.
    from append_lock import exclusive_append_lock


LEDGER_SCHEMA_VERSION = "2.0.0"
LEGACY_LEDGER_SCHEMA_VERSIONS = {None, "", "1.1.0"}
GENESIS_HASH = "GENESIS"

_CSV_PRIORITY_FIELDS = (
    "timestamp",
    "logged_utc",
    "ledger_schema_version",
    "prev_record_hash",
    "record_hash",
    "symbol",
    "side",
    "status",
    "execution_mode",
)


class LedgerIntegrityError(RuntimeError):
    """Raised when the authoritative JSONL ledger cannot be verified."""


class LedgerReconciliationError(RuntimeError):
    """Raised when the derived CSV mirror cannot be reconciled."""


class LedgerLockError(RuntimeError):
    """Raised when another writer owns the append lock."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _legacy_record_hash(record_without_hash: dict[str, Any]) -> str:
    serialized = json.dumps(record_without_hash, sort_keys=True)
    return _sha256_text(serialized)


def _v2_record_hash(record_without_hash: dict[str, Any]) -> str:
    return _sha256_text(_canonical_json(record_without_hash))


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return _canonical_json(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _bounded_error(errors: list[dict[str, Any]], line: int, reason: str) -> None:
    if len(errors) < 20:
        errors.append({"line": line, "reason": reason})


class TradeLedger:
    """Authoritative JSONL trade ledger with a deterministic CSV mirror.

    Existing 1.1.0 rows remain verifiable with their original hash algorithm.
    New rows form a 2.0.0 chain anchored to the terminal legacy or v2 hash.
    """

    def __init__(self, csv_path: str, jsonl_path: str):
        self.csv_path = Path(csv_path)
        self.jsonl_path = Path(jsonl_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        verification, records = self._read_and_verify_jsonl(self.jsonl_path)
        if verification["status"] != "pass":
            raise LedgerIntegrityError(
                "authoritative trade ledger failed verification: "
                + _canonical_json(verification["errors"])
            )
        self._records = records
        self._last_hash = verification["terminal_record_hash"]

    @staticmethod
    def _read_and_verify_jsonl(
        path: Path,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        errors: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        schema_counts: Counter[str] = Counter()
        expected_previous = GENESIS_HASH
        saw_v2 = False

        if not path.exists():
            return (
                {
                    "status": "pass",
                    "record_count": 0,
                    "legacy_unlinked_count": 0,
                    "chained_record_count": 0,
                    "schema_counts": {},
                    "first_record_hash": None,
                    "terminal_record_hash": GENESIS_HASH,
                    "errors": [],
                },
                [],
            )

        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    _bounded_error(errors, line_number, "blank JSONL record")
                    continue
                try:
                    record = json.loads(raw_line)
                except (TypeError, json.JSONDecodeError):
                    _bounded_error(errors, line_number, "invalid JSON object")
                    continue
                if not isinstance(record, dict):
                    _bounded_error(errors, line_number, "record is not an object")
                    continue

                records.append(record)
                version = record.get("ledger_schema_version")
                version_label = str(version) if version not in (None, "") else "legacy-unversioned"
                schema_counts[version_label] += 1

                observed_hash = record.get("record_hash")
                if not _is_sha256(observed_hash):
                    _bounded_error(errors, line_number, "record_hash is not lowercase SHA-256")
                    continue

                body = dict(record)
                body.pop("record_hash", None)
                if version == LEDGER_SCHEMA_VERSION:
                    saw_v2 = True
                    if body.get("prev_record_hash") != expected_previous:
                        _bounded_error(errors, line_number, "prev_record_hash chain mismatch")
                    computed_hash = _v2_record_hash(body)
                elif version in LEGACY_LEDGER_SCHEMA_VERSIONS:
                    if saw_v2:
                        _bounded_error(errors, line_number, "legacy record appears after v2 chain")
                    if "prev_record_hash" in body:
                        _bounded_error(errors, line_number, "legacy record contains unexpected chain field")
                    computed_hash = _legacy_record_hash(body)
                else:
                    _bounded_error(errors, line_number, "unsupported ledger schema version")
                    computed_hash = ""

                if computed_hash != observed_hash:
                    _bounded_error(errors, line_number, "record hash mismatch")
                expected_previous = str(observed_hash)

        first_hash = records[0].get("record_hash") if records else None
        chained_count = schema_counts.get(LEDGER_SCHEMA_VERSION, 0)
        result = {
            "status": "pass" if not errors else "fail",
            "record_count": len(records),
            "legacy_unlinked_count": len(records) - chained_count,
            "chained_record_count": chained_count,
            "schema_counts": dict(sorted(schema_counts.items())),
            "first_record_hash": first_hash,
            "terminal_record_hash": expected_previous if records else GENESIS_HASH,
            "errors": errors,
        }
        return result, records

    @classmethod
    def verify_jsonl(cls, jsonl_path: str | Path) -> dict[str, Any]:
        result, _ = cls._read_and_verify_jsonl(Path(jsonl_path))
        return result

    @staticmethod
    def _fieldnames(records: Iterable[dict[str, Any]]) -> list[str]:
        observed = {key for record in records for key in record}
        ordered = [field for field in _CSV_PRIORITY_FIELDS if field in observed]
        ordered.extend(sorted(observed.difference(ordered)))
        return ordered

    @classmethod
    def _write_csv_atomic(
        cls,
        csv_path: Path,
        records: list[dict[str, Any]],
    ) -> None:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = cls._fieldnames(records)
        file_descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{csv_path.name}.",
            suffix=".tmp",
            dir=str(csv_path.parent),
            text=True,
        )
        try:
            with os.fdopen(file_descriptor, "w", newline="", encoding="utf-8") as handle:
                if fieldnames:
                    writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
                    writer.writeheader()
                    for record in records:
                        writer.writerow({key: _csv_value(record.get(key)) for key in fieldnames})
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, csv_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    @classmethod
    def verify_csv_mirror(
        cls,
        csv_path: str | Path,
        jsonl_path: str | Path,
    ) -> dict[str, Any]:
        json_result, records = cls._read_and_verify_jsonl(Path(jsonl_path))
        errors: list[dict[str, Any]] = []
        path = Path(csv_path)

        if json_result["status"] != "pass":
            return {
                "status": "fail",
                "row_count": 0,
                "column_count": 0,
                "expected_column_count": len(cls._fieldnames(records)),
                "errors": [{"line": 0, "reason": "authoritative JSONL verification failed"}],
            }

        expected_fields = cls._fieldnames(records)
        if not records and not path.exists():
            return {
                "status": "pass",
                "row_count": 0,
                "column_count": 0,
                "expected_column_count": 0,
                "errors": [],
            }
        if not path.exists():
            return {
                "status": "fail",
                "row_count": 0,
                "column_count": 0,
                "expected_column_count": len(expected_fields),
                "errors": [{"line": 0, "reason": "CSV mirror is missing"}],
            }

        with path.open("r", newline="", encoding="utf-8") as handle:
            rows = list(csv.reader(handle))
        header = rows[0] if rows else []
        data_rows = rows[1:] if rows else []
        if header != expected_fields:
            _bounded_error(errors, 1, "CSV header does not match deterministic union schema")
        if len(header) != len(set(header)):
            _bounded_error(errors, 1, "CSV header contains duplicate columns")
        if len(data_rows) != len(records):
            _bounded_error(errors, 0, "CSV and JSONL row counts differ")

        for index, (row, record) in enumerate(zip(data_rows, records), start=2):
            if len(row) != len(header):
                _bounded_error(errors, index, "CSV row width differs from header")
                continue
            observed = dict(zip(header, row))
            expected = {key: _csv_value(record.get(key)) for key in expected_fields}
            if observed != expected:
                _bounded_error(errors, index, "CSV row differs from authoritative JSONL record")

        return {
            "status": "pass" if not errors else "fail",
            "row_count": len(data_rows),
            "column_count": len(header),
            "expected_column_count": len(expected_fields),
            "errors": errors,
        }

    @classmethod
    def reconciliation_receipt(
        cls,
        csv_path: str | Path,
        jsonl_path: str | Path,
    ) -> dict[str, Any]:
        json_result = cls.verify_jsonl(jsonl_path)
        csv_result = cls.verify_csv_mirror(csv_path, jsonl_path)
        return {
            "schema_version": "1.0",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "status": "pass"
            if json_result["status"] == "pass" and csv_result["status"] == "pass"
            else "fail",
            "authoritative_jsonl": json_result,
            "derived_csv_mirror": csv_result,
        }

    def repair_csv_mirror(self) -> dict[str, Any]:
        verification, records = self._read_and_verify_jsonl(self.jsonl_path)
        if verification["status"] != "pass":
            raise LedgerIntegrityError("cannot repair CSV from an invalid JSONL ledger")
        self._write_csv_atomic(self.csv_path, records)
        result = self.verify_csv_mirror(self.csv_path, self.jsonl_path)
        if result["status"] != "pass":
            raise LedgerReconciliationError("CSV repair did not reconcile")
        self._records = records
        self._last_hash = verification["terminal_record_hash"]
        return result

    def append(self, row: dict[str, Any]) -> str:
        lock_path = self.jsonl_path.with_name(self.jsonl_path.name + ".append.lock")
        with exclusive_append_lock(
            lock_path,
            error_type=LedgerLockError,
            error_message=lambda path: (
                f"timed out waiting for ledger append lock: {path.name}"
            ),
        ):
            verification, records = self._read_and_verify_jsonl(self.jsonl_path)
            if verification["status"] != "pass":
                raise LedgerIntegrityError("refusing to append to an invalid JSONL ledger")

            new_record = dict(row)
            for reserved in (
                "ledger_schema_version",
                "logged_utc",
                "prev_record_hash",
                "record_hash",
            ):
                new_record.pop(reserved, None)
            new_record["ledger_schema_version"] = LEDGER_SCHEMA_VERSION
            new_record["logged_utc"] = datetime.now(timezone.utc).isoformat()
            new_record["prev_record_hash"] = verification["terminal_record_hash"]
            digest = _v2_record_hash(new_record)
            new_record["record_hash"] = digest

            with self.jsonl_path.open("a", encoding="utf-8") as handle:
                handle.write(_canonical_json(new_record) + "\n")
                handle.flush()
                os.fsync(handle.fileno())

            records.append(new_record)
            try:
                self._write_csv_atomic(self.csv_path, records)
            except Exception as exc:
                raise LedgerReconciliationError(
                    "JSONL append succeeded but CSV mirror rebuild failed"
                ) from exc

            mirror = self.verify_csv_mirror(self.csv_path, self.jsonl_path)
            if mirror["status"] != "pass":
                raise LedgerReconciliationError("CSV mirror failed post-append verification")

            self._records = records
            self._last_hash = digest
            return digest
