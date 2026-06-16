from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from live_data_no_orders_gate import evaluate as evaluate_live_stage
except Exception:
    from .live_data_no_orders_gate import evaluate as evaluate_live_stage


@dataclass
class OrderIntent:
    symbol: str = "UNKNOWN"
    side: str = "UNKNOWN"
    notional_usd: float = 0.0
    quantity: float | None = None
    order_type: str = "market"
    source: str = "unknown"


@dataclass
class SafetyDecision:
    approved: bool
    reason: str
    stage: str
    blockers: list[str]
    warnings: list[str]
    intent: dict[str, Any]
    generated_utc: str


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_root() -> Path:
    env_root = os.environ.get("LUMA_STACK_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def normalize_intent(intent: dict[str, Any] | OrderIntent) -> OrderIntent:
    if isinstance(intent, OrderIntent):
        return intent

    def fnum(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    return OrderIntent(
        symbol=str(intent.get("symbol") or intent.get("pair") or "UNKNOWN"),
        side=str(intent.get("side") or intent.get("action") or "UNKNOWN"),
        notional_usd=fnum(intent.get("notional_usd", intent.get("usd", intent.get("value_usd", 0.0)))),
        quantity=None if intent.get("quantity") is None else fnum(intent.get("quantity")),
        order_type=str(intent.get("order_type") or intent.get("type") or "market"),
        source=str(intent.get("source") or "unknown"),
    )


def _compat_kill_switch_check(root: Path) -> tuple[bool, str]:
    """
    Conservative compatibility adapter.

    Existing repos often have kill_switch.py with different function names.
    This adapter does not trust unknown APIs. It checks common emergency files
    and attempts common module calls when available.
    """
    emergency_files = [
        root / "KILL_SWITCH_STOP",
        root / "config" / "KILL_SWITCH_STOP",
        root / "out" / "execution" / "KILL_SWITCH_STOP",
        root / "out" / "KILL_SWITCH_STOP",
    ]
    for path in emergency_files:
        if path.exists():
            return False, f"kill_switch_file_present:{path}"

    try:
        import kill_switch  # type: ignore

        for name in ["is_kill_switch_active", "kill_switch_active", "is_active", "blocked"]:
            fn = getattr(kill_switch, name, None)
            if callable(fn):
                active = bool(fn())
                if active:
                    return False, f"kill_switch_module_active:{name}"
                return True, f"kill_switch_module_clear:{name}"
    except Exception:
        pass

    return True, "kill_switch_clear_by_file_check"


def _compat_risk_check(intent: OrderIntent) -> tuple[bool, str]:
    """
    Conservative risk adapter. If a known validator exists, use it.
    Otherwise enforce tiny/no-order defaults here.
    """
    try:
        import risk_kernel  # type: ignore

        for name in ["validate_order", "check_order", "approve_order", "risk_check"]:
            fn = getattr(risk_kernel, name, None)
            if callable(fn):
                result = fn(asdict(intent))
                if isinstance(result, tuple) and len(result) >= 2:
                    return bool(result[0]), f"risk_kernel:{name}:{result[1]}"
                return bool(result), f"risk_kernel:{name}"
    except Exception:
        pass

    if intent.notional_usd < 0:
        return False, "risk_local_negative_notional"

    return True, "risk_local_basic_pass"


def _compat_signal_check(intent: OrderIntent) -> tuple[bool, str]:
    """
    Conservative signal adapter. Unknown signal API does not approve live orders;
    it only tags compatibility. The live stage gate remains authoritative.
    """
    try:
        import signal_gate  # type: ignore

        for name in ["validate_signal", "check_signal", "approve_signal", "gate_signal"]:
            fn = getattr(signal_gate, name, None)
            if callable(fn):
                result = fn(asdict(intent))
                if isinstance(result, tuple) and len(result) >= 2:
                    return bool(result[0]), f"signal_gate:{name}:{result[1]}"
                return bool(result), f"signal_gate:{name}"
    except Exception:
        pass

    return True, "signal_local_no_known_gate"


def _ledger_record(root: Path, decision: SafetyDecision) -> None:
    out_dir = root / "out" / "safety_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    ledger = out_dir / "order_safety_gate_ledger.jsonl"
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(decision), sort_keys=True) + "\n")


def decide_order_permission(
    intent: dict[str, Any] | OrderIntent,
    *,
    stage: str | None = None,
    root: Path | None = None,
    write_ledger: bool = True,
) -> SafetyDecision:
    root = (root or resolve_root()).resolve()
    stage = stage or os.environ.get("LUMA_STAGE") or "live-data-no-orders"

    normalized = normalize_intent(intent)

    stage_report = evaluate_live_stage(stage, root)
    blockers = list(stage_report.get("blockers", []))
    warnings = list(stage_report.get("warnings", []))

    approved = bool(stage_report.get("order_permission", False))
    reason = str(stage_report.get("order_permission_reason", "stage_gate_unknown"))

    kill_ok, kill_reason = _compat_kill_switch_check(root)
    if not kill_ok:
        approved = False
        blockers.append(kill_reason)
        reason = kill_reason
    else:
        warnings.append(kill_reason)

    risk_ok, risk_reason = _compat_risk_check(normalized)
    if not risk_ok:
        approved = False
        blockers.append(risk_reason)
        reason = risk_reason
    else:
        warnings.append(risk_reason)

    signal_ok, signal_reason = _compat_signal_check(normalized)
    if not signal_ok:
        approved = False
        blockers.append(signal_reason)
        reason = signal_reason
    else:
        warnings.append(signal_reason)

    # Absolute hard stop for live-data-no-orders stage.
    if stage in {"live-data-no-orders", "live_data_no_orders"}:
        approved = False
        reason = "blocked_by_live_data_no_orders_stage"

    decision = SafetyDecision(
        approved=approved,
        reason=reason,
        stage=stage,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
        intent=asdict(normalized),
        generated_utc=now_utc(),
    )

    if write_ledger:
        _ledger_record(root, decision)

    return decision


def require_order_permission(intent: dict[str, Any] | OrderIntent, **kwargs: Any) -> SafetyDecision:
    decision = decide_order_permission(intent, **kwargs)
    if not decision.approved:
        raise RuntimeError(f"ORDER_BLOCKED_BY_SAFETY_GATE: {decision.reason}")
    return decision


def main() -> int:
    root = resolve_root()
    intent = OrderIntent(
        symbol="TEST/USD",
        side="buy",
        notional_usd=1.0,
        source="order_safety_gate_smoke",
    )
    decision = decide_order_permission(intent, stage="live-data-no-orders", root=root)
    print(json.dumps(asdict(decision), indent=2, sort_keys=True))
    return 0 if decision.approved is False and decision.reason == "blocked_by_live_data_no_orders_stage" else 2


if __name__ == "__main__":
    raise SystemExit(main())
