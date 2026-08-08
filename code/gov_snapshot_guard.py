from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any


DEFAULT_MIN_FREE_BYTES = 2 * 1024**3
DEFAULT_MAX_SNAPSHOT_FILES = 100_000


def _safe_int(value: Any, default: int) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return default


def snapshot_capacity_status(
    snapshot_dir: Path,
    *,
    min_free_bytes: int | None = None,
    max_snapshot_files: int | None = None,
) -> dict[str, Any]:
    """Return a fail-closed capacity decision without deleting evidence."""

    snapshot_dir = Path(snapshot_dir)
    min_free = _safe_int(
        os.getenv("LUMA_GOV_SNAPSHOT_MIN_FREE_BYTES")
        if min_free_bytes is None
        else min_free_bytes,
        DEFAULT_MIN_FREE_BYTES,
    )
    max_files = _safe_int(
        os.getenv("LUMA_GOV_SNAPSHOT_MAX_FILES")
        if max_snapshot_files is None
        else max_snapshot_files,
        DEFAULT_MAX_SNAPSHOT_FILES,
    )
    probe = snapshot_dir if snapshot_dir.exists() else snapshot_dir.parent

    try:
        free_bytes = shutil.disk_usage(probe).free
    except OSError as exc:
        return {
            "allowed": False,
            "reason": "disk_usage_unavailable",
            "error": str(exc),
        }

    status: dict[str, Any] = {
        "allowed": True,
        "reason": "capacity_available",
        "free_bytes": free_bytes,
        "min_free_bytes": min_free,
        "max_snapshot_files": max_files,
    }
    if free_bytes < min_free:
        status.update(allowed=False, reason="minimum_free_space_not_met")
        return status

    file_count = 0
    if snapshot_dir.exists() and max_files:
        try:
            for path in snapshot_dir.iterdir():
                if path.is_file():
                    file_count += 1
                    if file_count >= max_files:
                        status.update(
                            allowed=False,
                            reason="snapshot_file_limit_reached",
                            snapshot_files_at_least=file_count,
                        )
                        return status
        except OSError as exc:
            status.update(
                allowed=False,
                reason="snapshot_inventory_unavailable",
                error=str(exc),
            )
            return status

    status["snapshot_files"] = file_count
    return status


def claim_persistent_lease(
    lease_path: Path,
    *,
    min_interval_sec: float,
    now_epoch: float | None = None,
) -> dict[str, Any]:
    """Atomically persist an attempt timestamp before starting collection."""

    lease_path = Path(lease_path)
    now_value = time.time() if now_epoch is None else float(now_epoch)
    last_attempt = 0.0
    try:
        payload = json.loads(lease_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            last_attempt = float(payload.get("last_attempt_epoch", 0.0) or 0.0)
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        # A malformed lease must not disable the collector forever. Replacing it
        # below is safe only if the atomic write succeeds.
        last_attempt = 0.0

    remaining = max(0.0, float(min_interval_sec) - (now_value - last_attempt))
    if remaining > 0:
        return {
            "claimed": False,
            "reason": "persistent_throttle",
            "retry_after_sec": remaining,
        }

    temp_path = lease_path.with_name(
        f".{lease_path.name}.{os.getpid()}.{int(now_value * 1000)}.tmp"
    )
    try:
        lease_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(
            json.dumps(
                {
                    "schema": "lumencore.gov_collector_lease.v1",
                    "last_attempt_epoch": now_value,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        os.replace(temp_path, lease_path)
    except OSError as exc:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return {
            "claimed": False,
            "reason": "lease_persistence_failed",
            "error": str(exc),
        }

    return {"claimed": True, "reason": "lease_claimed"}
