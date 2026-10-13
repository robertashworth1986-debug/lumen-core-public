"""Append-only paper/research records with a canonical JSONL source.

New CSV files use a stable projection plus record_json for arbitrary fields.
Existing CSV headers and historical bytes are retained: new rows follow the
existing column order and full records remain in JSONL. This does not repair or
restate previously malformed CSV rows, or reconcile records to a brokerage.
"""

import csv
import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

LEDGER_SCHEMA_VERSION = "1.2.0"
CSV_FIELDS = (
    "timestamp", "symbol", "side", "status", "execution_mode", "entry_price",
    "exit_price", "qty", "size_usd", "pnl", "pnl_pct", "net_pnl", "net_pnl_pct",
    "round_trip_fee_usd", "gate_score", "tp_net_bps", "sl_net_bps", "close_reason",
    "ledger_schema_version", "logged_utc", "event_payload_sha256", "record_hash", "record_json",
)
_METADATA = {"ledger_schema_version", "logged_utc", "event_payload_sha256", "record_hash"}


def _canonical(row):
    _validate_text_keys(row)
    return json.dumps(row, sort_keys=True, allow_nan=False)


def _validate_text_keys(value):
    """JSON coerces numeric object keys, which would invalidate later hashes."""
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("trade ledger JSON object keys must be text at every depth")
        for item in value.values():
            _validate_text_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _validate_text_keys(item)


def _needs_line_terminator(path):
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return False
    with path.open("rb") as stream:
        stream.seek(-1, os.SEEK_END)
        return stream.read(1) != b"\n"


def _payload_hash(row):
    body = {key: value for key, value in row.items() if key not in _METADATA}
    return hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


class TradeLedger:
    def __init__(self, csv_path: str, jsonl_path: str):
        if Path(csv_path).resolve() == Path(jsonl_path).resolve():
            raise ValueError("CSV and JSONL must be separate files")
        self.csv_path = os.fspath(csv_path)
        self.jsonl_path = os.fspath(jsonl_path)

    @contextmanager
    def _lock(self):
        path = Path(self.jsonl_path + ".lock")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as lock:
            if os.name == "nt":
                import msvcrt
                lock.seek(0, os.SEEK_END)
                if lock.tell() == 0:
                    lock.write(b"\0")
                    lock.flush()
                lock.seek(0)
                try:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise RuntimeError("trade ledger is busy; retry the same event") from exc
                try:
                    yield
                finally:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                try:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise RuntimeError("trade ledger is busy; retry the same event") from exc
                try:
                    yield
                finally:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def read_records(self):
        """Read authoritative records, rejecting broken JSON/hash custody."""
        path = Path(self.jsonl_path)
        if not path.exists():
            return []
        records = []
        with path.open("r", encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict) or not isinstance(row.get("record_hash"), str):
                        raise ValueError("missing record hash")
                    body = {key: value for key, value in row.items() if key != "record_hash"}
                    expected = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
                    if expected != row["record_hash"]:
                        raise ValueError("record hash mismatch")
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"invalid trade ledger record at line {number}") from exc
                records.append(row)
        return records

    def _csv_projection(self, records):
        path = Path(self.csv_path)
        if not path.exists() or path.stat().st_size == 0:
            return list(CSV_FIELDS), set(), True
        with path.open("r", newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream, strict=True)
            header = reader.fieldnames
            if not header or len(set(header)) != len(header) or "record_hash" not in header:
                raise ValueError("existing CSV requires a unique header with record_hash")
            known_records = {record["record_hash"]: record for record in records}
            hashes = set()
            try:
                for row in reader:
                    record_hash = row.get("record_hash")
                    expected = known_records.get(record_hash)
                    if expected is None or None in row:
                        continue
                    # A hash cell can precede the interrupted part of a CSV
                    # write. Accept only an entire canonical projection.
                    matches = True
                    for key in header:
                        if key == "record_json":
                            try:
                                matches = _canonical(json.loads(row.get(key) or "")) == _canonical(expected)
                            except (ValueError, TypeError):
                                matches = False
                        else:
                            value = expected.get(key, "")
                            matches = row.get(key) == ("" if value is None else str(value))
                        if not matches:
                            break
                    if matches:
                        hashes.add(record_hash)
            except csv.Error as exc:
                raise ValueError("existing CSV has malformed quoted fields; preserve it and reconstruct a separate projection from JSONL") from exc
        return header, hashes, False

    def _append_csv(self, record, header, write_header):
        # CSV is a readable projection. JSONL owns every field and its hash.
        projected = {key: record.get(key, "") for key in header}
        if "record_json" in header:
            projected["record_json"] = _canonical(record)
        Path(self.csv_path).parent.mkdir(parents=True, exist_ok=True)
        needs_terminator = _needs_line_terminator(self.csv_path)
        with open(self.csv_path, "a", newline="", encoding="utf-8") as stream:
            if needs_terminator:
                stream.write("\n")
            writer = csv.DictWriter(stream, fieldnames=header)
            if write_header:
                writer.writeheader()
            writer.writerow(projected)
            stream.flush()
            os.fsync(stream.fileno())

    def append(self, row: dict) -> str:
        if not isinstance(row, dict) or any(not isinstance(key, str) for key in row):
            raise ValueError("trade ledger row must have text keys")
        payload = {key: value for key, value in row.items() if key not in _METADATA}
        if "event_id" in payload and (not isinstance(payload["event_id"], str) or not payload["event_id"].strip()):
            raise ValueError("event_id must be nonempty text when supplied")
        payload_digest = _payload_hash(payload)  # Reject NaN/Infinity before any write.
        with self._lock():
            records = self.read_records()
            header, projected_hashes, write_header = self._csv_projection(records)
            event_id = payload.get("event_id")
            existing = None
            for record in records:
                digest = record.get("event_payload_sha256") or _payload_hash(record)
                if event_id is not None and record.get("event_id") == event_id and digest != payload_digest:
                    raise ValueError("event_id was already recorded with a different payload")
                if digest == payload_digest:
                    existing = record
                    break
            if existing is not None:
                # A JSONL write can succeed before CSV fails. Retrying repairs
                # only the missing projection and never repeats the source event.
                if existing["record_hash"] not in projected_hashes:
                    self._append_csv(existing, header, write_header)
                return existing["record_hash"]
            record = {
                **payload, "ledger_schema_version": LEDGER_SCHEMA_VERSION,
                "logged_utc": datetime.now(timezone.utc).isoformat(),
                "event_payload_sha256": payload_digest,
            }
            digest = hashlib.sha256(_canonical(record).encode("utf-8")).hexdigest()
            record["record_hash"] = digest
            Path(self.jsonl_path).parent.mkdir(parents=True, exist_ok=True)
            needs_terminator = _needs_line_terminator(self.jsonl_path)
            with open(self.jsonl_path, "a", encoding="utf-8") as stream:
                # read_records() already verified every existing source object.
                # Adding its missing terminator preserves the original prefix.
                if needs_terminator:
                    stream.write("\n")
                stream.write(_canonical(record) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            self._append_csv(record, header, write_header)
            return digest
