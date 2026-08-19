from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_strict_live_locked(runtime_control: Optional[Mapping[str, Any]]) -> bool:
    cfg = runtime_control if isinstance(runtime_control, Mapping) else {}
    return (
        bool(cfg.get("strict_live_only", False))
        and str(cfg.get("mode", "paper")).strip().lower() == "live"
        and bool(cfg.get("allow_live_orders", False))
        and not bool(cfg.get("paper_enabled", True))
        and not bool(cfg.get("kill_switch", False))
    )


def human_action_time_authority_state(
    runtime_control: Optional[Mapping[str, Any]],
    runtime_path: Path,
    receipt_path: Path,
    controller: Optional[str] = None,
    ttl_seconds: int = 300,
) -> Dict[str, Any]:
    requested = is_strict_live_locked(runtime_control)
    if not requested:
        return {
            "strict_live_requested": False,
            "authorized_strict_live_lock": False,
            "authorized": False,
            "reasons": ["strict_live_lock_not_requested"],
            "receipt_present": Path(receipt_path).exists(),
            "receipt_age_sec": None,
        }

    from execution.live_action_authority import validate_live_action_authority

    authority = validate_live_action_authority(
        runtime_path=Path(runtime_path),
        receipt_path=Path(receipt_path),
        controller=controller,
        ttl_seconds=ttl_seconds,
    )
    return {
        **authority,
        "strict_live_requested": True,
        "authorized_strict_live_lock": bool(authority.get("authorized")),
    }


def stamp_runtime_writer(
    runtime_control: Optional[Dict[str, Any]],
    writer: str,
    strict_live_lock: Optional[bool] = None,
    reason: str = "",
) -> Dict[str, Any]:
    cfg = runtime_control if isinstance(runtime_control, dict) else {}
    lock_state = is_strict_live_locked(cfg) if strict_live_lock is None else bool(strict_live_lock)

    cfg["_last_runtime_writer"] = str(writer or "").strip()
    cfg["_last_runtime_write_utc"] = now_utc_iso()
    cfg["_last_runtime_write_reason"] = str(reason or "").strip()
    cfg["_strict_live_locked_at_write"] = bool(lock_state)
    return cfg


def runtime_writer_hint(runtime_control: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    cfg = runtime_control if isinstance(runtime_control, Mapping) else {}
    return {
        "last_runtime_writer": str(cfg.get("_last_runtime_writer", "") or "").strip(),
        "last_runtime_write_utc": str(cfg.get("_last_runtime_write_utc", "") or "").strip(),
        "last_runtime_write_reason": str(cfg.get("_last_runtime_write_reason", "") or "").strip(),
        "strict_live_locked_at_write": bool(cfg.get("_strict_live_locked_at_write", False)),
    }
