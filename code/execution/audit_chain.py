from __future__ import annotations

import hashlib
import json
import os
import time
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


GENESIS_HASH = "GENESIS"


class AuditChainIntegrityError(RuntimeError):
    """Raised when an append-only audit chain fails verification."""


class AuditChainLockError(RuntimeError):
    """Raised when another process owns the audit append lock."""


@contextmanager
def _exclusive_lock(lock_path: Path, timeout_seconds: float = 5.0):
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise AuditChainLockError(
                    f"timed out waiting for audit append lock: {lock_path.name}"
                )
            time.sleep(0.05)
    try:
        os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
        os.close(descriptor)
        descriptor = None
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _record_error(
    errors: list[dict[str, Any]],
    counts: Counter[str],
    line: int,
    reason: str,
) -> None:
    counts[reason] += 1
    if len(errors) < 20:
        errors.append({"line": line, "reason": reason})


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


class AuditChain:
    """Append-only hash chain for tamper-evident execution/audit events."""

    def __init__(self, chain_file: Path):
        self.chain_file = Path(chain_file)
        self.chain_file.parent.mkdir(parents=True, exist_ok=True)
        verification = self.verify_file(self.chain_file)
        if verification["status"] != "pass":
            raise AuditChainIntegrityError(
                "audit chain failed verification: "
                + self._canonical(verification["errors"])
            )
        self._last_hash = verification["terminal_event_hash"]
        self._expected_stat = self._stat_signature()

    def _stat_signature(self) -> tuple[int, int] | None:
        try:
            stat = self.chain_file.stat()
        except FileNotFoundError:
            return None
        return stat.st_size, stat.st_mtime_ns

    @staticmethod
    def _canonical(obj: Any) -> str:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def verify_file(cls, chain_file: str | Path) -> dict[str, Any]:
        path = Path(chain_file)
        errors: list[dict[str, Any]] = []
        error_counts: Counter[str] = Counter()
        expected_previous = GENESIS_HASH
        first_hash: str | None = None
        event_count = 0

        if not path.exists():
            return {
                "status": "pass",
                "event_count": 0,
                "first_event_hash": None,
                "terminal_event_hash": GENESIS_HASH,
                "error_counts": {},
                "errors": [],
            }

        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    _record_error(errors, error_counts, line_number, "blank JSONL event")
                    continue
                try:
                    event = json.loads(raw_line)
                except (TypeError, json.JSONDecodeError):
                    _record_error(errors, error_counts, line_number, "invalid JSON event")
                    continue
                if not isinstance(event, dict):
                    _record_error(errors, error_counts, line_number, "event is not an object")
                    continue

                event_count += 1
                observed_hash = event.get("event_hash")
                if not _is_sha256(observed_hash):
                    _record_error(
                        errors,
                        error_counts,
                        line_number,
                        "event_hash is not lowercase SHA-256",
                    )
                    continue
                if first_hash is None:
                    first_hash = observed_hash

                body = dict(event)
                body.pop("event_hash", None)
                if set(body) != {"event_type", "event_time_utc", "payload", "prev_hash"}:
                    _record_error(errors, error_counts, line_number, "event fields mismatch")
                if body.get("prev_hash") != expected_previous:
                    _record_error(errors, error_counts, line_number, "prev_hash chain mismatch")
                computed_hash = hashlib.sha256(
                    cls._canonical(body).encode("utf-8")
                ).hexdigest()
                if computed_hash != observed_hash:
                    _record_error(errors, error_counts, line_number, "event hash mismatch")
                expected_previous = observed_hash

        return {
            "status": "pass" if not errors else "fail",
            "event_count": event_count,
            "first_event_hash": first_hash,
            "terminal_event_hash": expected_previous if event_count else GENESIS_HASH,
            "error_counts": dict(sorted(error_counts.items())),
            "errors": errors,
        }

    @classmethod
    def iter_verified_events(cls, chain_file: str | Path) -> Iterator[dict[str, Any]]:
        verification = cls.verify_file(chain_file)
        if verification["status"] != "pass":
            raise AuditChainIntegrityError("cannot iterate an invalid audit chain")
        path = Path(chain_file)
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                if raw_line.strip():
                    yield json.loads(raw_line)

    def append(
        self,
        event_type: str,
        payload: Dict[str, Any],
        event_time_utc: Optional[str] = None,
    ) -> Dict[str, Any]:
        lock_path = self.chain_file.with_name(self.chain_file.name + ".append.lock")
        with _exclusive_lock(lock_path):
            if self._stat_signature() != self._expected_stat:
                raise AuditChainIntegrityError(
                    "audit chain changed after initialization; re-open and verify before appending"
                )
            ts = event_time_utc or datetime.now(timezone.utc).isoformat()
            body = {
                "event_type": event_type,
                "event_time_utc": ts,
                "payload": payload,
                "prev_hash": self._last_hash,
            }
            digest = hashlib.sha256(self._canonical(body).encode("utf-8")).hexdigest()
            row = {
                **body,
                "event_hash": digest,
            }
            with self.chain_file.open("a", encoding="utf-8") as handle:
                handle.write(self._canonical(row) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._last_hash = digest
            self._expected_stat = self._stat_signature()
            return row


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
