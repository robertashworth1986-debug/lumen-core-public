from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


DEFAULT_AUTHORITY_TTL_SEC = 300
RECEIPT_SCHEMA = "live_action_time_approval_receipt_v1"
AUTHORIZATION_SCOPE = "single_live_stack_start"
CANONICAL_RUNTIME_PATH = "config/runtime_control.json"


def parse_utc(value: Any) -> Optional[datetime]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_live_action_authority(
    runtime_path: Path,
    receipt_path: Path,
    controller: Optional[str] = None,
    ttl_seconds: int = DEFAULT_AUTHORITY_TTL_SEC,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Validate short-lived, hash-bound live authority without exposing receipt contents."""
    runtime_path = Path(runtime_path)
    receipt_path = Path(receipt_path)
    reasons: list[str] = []
    runtime: dict[str, Any] = {}
    receipt: dict[str, Any] = {}
    runtime_sha256 = ""
    receipt_age_sec: Optional[float] = None

    if not runtime_path.exists():
        reasons.append("runtime_missing")
    else:
        try:
            loaded_runtime = json.loads(runtime_path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded_runtime, dict):
                runtime = loaded_runtime
                runtime_sha256 = sha256_file(runtime_path)
            else:
                reasons.append("runtime_not_object")
        except Exception:
            reasons.append("runtime_unreadable")

    mode = str(runtime.get("mode") or runtime.get("runtime_mode") or "").strip().lower()
    allow_live_orders = runtime.get("allow_live_orders") is True
    paper_enabled = runtime.get("paper_enabled") is True
    kill_switch = runtime.get("kill_switch") is True
    if mode != "live":
        reasons.append("runtime_mode_not_live")
    if not allow_live_orders:
        reasons.append("live_orders_not_armed")
    if paper_enabled:
        reasons.append("paper_mode_conflict")
    if kill_switch:
        reasons.append("kill_switch_enabled")

    if not receipt_path.exists():
        reasons.append("action_receipt_missing")
    else:
        try:
            loaded_receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
            if isinstance(loaded_receipt, dict):
                receipt = loaded_receipt
            else:
                reasons.append("action_receipt_not_object")
        except Exception:
            reasons.append("action_receipt_unreadable")

    if receipt:
        receipt_controller = str(receipt.get("controller") or "").strip()
        if receipt.get("schema") != RECEIPT_SCHEMA:
            reasons.append("action_receipt_schema_mismatch")
        if not receipt_controller:
            reasons.append("action_receipt_controller_missing")
        elif controller is not None and receipt_controller != str(controller).strip():
            reasons.append("action_receipt_controller_mismatch")
        if receipt.get("human_unlock_verified") is not True:
            reasons.append("human_unlock_not_verified")
        if receipt.get("exact_action_time_phrase_verified") is not True:
            reasons.append("action_time_phrase_not_verified")
        if receipt.get("authorization_scope") != AUTHORIZATION_SCOPE:
            reasons.append("action_receipt_scope_mismatch")
        if receipt.get("reusable_for_restart") is not False:
            reasons.append("action_receipt_reusable_or_unspecified")
        if receipt.get("runtime_control_path") != CANONICAL_RUNTIME_PATH:
            reasons.append("action_receipt_runtime_path_mismatch")
        if not runtime_sha256 or receipt.get("armed_runtime_sha256") != runtime_sha256:
            reasons.append("action_receipt_runtime_hash_mismatch")

        generated_at = parse_utc(receipt.get("generated_utc"))
        if generated_at is None:
            reasons.append("action_receipt_timestamp_invalid")
        else:
            reference = now or datetime.now(timezone.utc)
            if reference.tzinfo is None:
                reference = reference.replace(tzinfo=timezone.utc)
            receipt_age_sec = (reference.astimezone(timezone.utc) - generated_at).total_seconds()
            if receipt_age_sec < -5.0:
                reasons.append("action_receipt_timestamp_in_future")
            if receipt_age_sec > max(1, int(ttl_seconds)):
                reasons.append("action_receipt_expired")

    return {
        "authorized": not reasons,
        "reasons": reasons,
        "runtime": {
            "mode": mode,
            "allow_live_orders": allow_live_orders,
            "paper_enabled": paper_enabled,
            "kill_switch": kill_switch,
        },
        "runtime_sha256": runtime_sha256,
        "receipt_present": receipt_path.exists(),
        "receipt_age_sec": round(receipt_age_sec, 3) if receipt_age_sec is not None else None,
        "receipt_ttl_sec": max(1, int(ttl_seconds)),
    }
