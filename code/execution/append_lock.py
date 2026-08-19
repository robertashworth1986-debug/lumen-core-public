from __future__ import annotations

import json
import os
import socket
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator


LOCK_SCHEMA_VERSION = "1.0"
DEFAULT_STALE_AFTER_SECONDS = 30.0


class AppendLockError(RuntimeError):
    """Raised when an append lock cannot be acquired safely."""


def _process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        # os.kill(pid, 0) can signal a process on Windows. Query a read-only
        # process handle so stale-lock recovery can never terminate an owner.
        import ctypes
        from ctypes import wintypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            # ERROR_INVALID_PARAMETER means the PID does not exist. Access
            # denial and other errors fail closed as "alive".
            return ctypes.get_last_error() != 87
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_lock(lock_path: Path) -> tuple[dict[str, Any] | None, bytes | None]:
    try:
        raw = lock_path.read_bytes()
    except FileNotFoundError:
        return None, None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, raw
    return (payload if isinstance(payload, dict) else None), raw


def _lock_age_seconds(lock_path: Path, payload: dict[str, Any] | None) -> float:
    created_unix_ns = payload.get("created_unix_ns") if payload else None
    if isinstance(created_unix_ns, int) and created_unix_ns > 0:
        return max(0.0, (time.time_ns() - created_unix_ns) / 1_000_000_000)
    try:
        return max(0.0, time.time() - lock_path.stat().st_mtime)
    except FileNotFoundError:
        return 0.0


def _is_stale_lock(
    lock_path: Path,
    payload: dict[str, Any] | None,
    stale_after_seconds: float,
) -> bool:
    if _lock_age_seconds(lock_path, payload) < stale_after_seconds or not payload:
        return False
    if payload.get("hostname") != socket.gethostname():
        return False
    owner_pid = payload.get("pid")
    if not isinstance(owner_pid, int):
        return True
    return not _process_is_alive(owner_pid)


def _reclaim_if_unchanged(lock_path: Path, expected_bytes: bytes | None) -> bool:
    if expected_bytes is None:
        return False
    try:
        if lock_path.read_bytes() != expected_bytes:
            return False
        lock_path.unlink()
    except FileNotFoundError:
        return True
    return True


@contextmanager
def exclusive_append_lock(
    lock_path: str | Path,
    *,
    timeout_seconds: float = 5.0,
    stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    error_type: type[Exception] = AppendLockError,
    error_message: str | Callable[[Path], str] | None = None,
) -> Iterator[dict[str, Any]]:
    """Acquire an ownership-token lock; reclaim only provably stale residue."""

    path = Path(lock_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + max(0.0, timeout_seconds)
    owner = {
        "schema_version": LOCK_SCHEMA_VERSION,
        "pid": os.getpid(),
        "hostname": socket.gethostname(),
        "created_unix_ns": time.time_ns(),
        "owner_token": uuid.uuid4().hex,
    }
    descriptor: int | None = None

    while descriptor is None:
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            observed, observed_bytes = _read_lock(path)
            if _is_stale_lock(path, observed, stale_after_seconds):
                if _reclaim_if_unchanged(path, observed_bytes):
                    continue
            if time.monotonic() >= deadline:
                message = error_message(path) if callable(error_message) else error_message
                raise error_type(message or f"timed out waiting for append lock: {path.name}")
            time.sleep(0.05)

    raw = (json.dumps(owner, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    try:
        os.write(descriptor, raw)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        yield owner
    finally:
        if descriptor is not None:
            os.close(descriptor)
        current, _ = _read_lock(path)
        if current and current.get("owner_token") == owner["owner_token"]:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
