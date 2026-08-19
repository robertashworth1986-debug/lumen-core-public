from __future__ import annotations

import json
import os
import socket
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from execution.append_lock import AppendLockError, exclusive_append_lock


def test_live_owner_lock_fails_closed(tmp_path):
    lock = tmp_path / "collector.lock"
    lock.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
                "created_unix_ns": time.time_ns() - 120_000_000_000,
                "owner_token": "live-owner",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(AppendLockError):
        with exclusive_append_lock(lock, timeout_seconds=0.05, stale_after_seconds=0.01):
            raise AssertionError("lock should not be acquired")

    assert json.loads(lock.read_text(encoding="utf-8"))["owner_token"] == "live-owner"


def test_lock_cleanup_requires_ownership_token(tmp_path):
    lock = tmp_path / "collector.lock"
    with exclusive_append_lock(lock) as owner:
        successor = {**owner, "owner_token": "successor"}
        lock.write_text(json.dumps(successor), encoding="utf-8")

    assert lock.exists()
    assert json.loads(lock.read_text(encoding="utf-8"))["owner_token"] == "successor"
