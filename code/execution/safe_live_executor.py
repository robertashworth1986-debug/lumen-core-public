from __future__ import annotations

"""
LumenCore safe live executor facade.

Purpose:
- Provide one safe entry point before anything reaches live_executor.py.
- In live-data-no-orders mode, block every order before broker code can run.
- Later, tiny-live manual arm can call the underlying executor only after the
  central order_safety_gate approves the intent.

This module intentionally does not contain broker keys and does not print secrets.
"""

import importlib
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from order_safety_gate import OrderIntent, decide_order_permission
except Exception:
    from .order_safety_gate import OrderIntent, decide_order_permission


CANDIDATE_EXECUTOR_FUNCTIONS = [
    "submit_order",
    "place_order",
    "execute_order",
    "create_order",
    "send_order",
    "route_order",
    "buy",
    "sell",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root() -> Path:
    env_root = os.environ.get("LUMA_STACK_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def import_live_executor():
    try:
        return importlib.import_module("live_executor")
    except Exception:
        try:
            return importlib.import_module(".live_executor", package=__package__)
        except Exception as exc:
            return exc


def discover_live_executor_surface() -> dict[str, Any]:
    module_or_error = import_live_executor()

    if isinstance(module_or_error, Exception):
        return {
            "import_ok": False,
            "error": repr(module_or_error),
            "candidate_functions_found": [],
        }

    found = []
    for name in CANDIDATE_EXECUTOR_FUNCTIONS:
        obj = getattr(module_or_error, name, None)
        if callable(obj):
            found.append(name)

    callable_names = []
    for name in dir(module_or_error):
        if name.startswith("_"):
            continue
        try:
            obj = getattr(module_or_error, name)
            if callable(obj) and any(token in name.lower() for token in ["order", "buy", "sell", "execute", "route"]):
                callable_names.append(name)
        except Exception:
            pass

    return {
        "import_ok": True,
        "candidate_functions_found": found,
        "order_related_callables": sorted(set(callable_names))[:80],
    }


def _normalize_order(order: dict[str, Any] | OrderIntent) -> OrderIntent:
    if isinstance(order, OrderIntent):
        return order

    def fnum(value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    return OrderIntent(
        symbol=str(order.get("symbol") or order.get("pair") or "UNKNOWN"),
        side=str(order.get("side") or order.get("action") or "UNKNOWN"),
        notional_usd=fnum(order.get("notional_usd", order.get("usd", order.get("value_usd", 0.0)))),
        quantity=None if order.get("quantity") is None else fnum(order.get("quantity")),
        order_type=str(order.get("order_type") or order.get("type") or "market"),
        source=str(order.get("source") or "safe_live_executor"),
    )


def _find_default_executor() -> Callable[[dict[str, Any]], Any] | None:
    module_or_error = import_live_executor()
    if isinstance(module_or_error, Exception):
        return None

    for name in CANDIDATE_EXECUTOR_FUNCTIONS:
        obj = getattr(module_or_error, name, None)
        if callable(obj):
            return obj

    return None


def guarded_execute_order(
    order: dict[str, Any] | OrderIntent,
    *,
    stage: str | None = None,
    root: Path | None = None,
    executor: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """
    Safety-first live executor facade.

    In live-data-no-orders mode, this returns blocked=True and never calls the
    underlying live executor.
    """
    root = (root or repo_root()).resolve()
    stage = stage or os.environ.get("LUMA_STAGE") or "live-data-no-orders"
    intent = _normalize_order(order)

    decision = decide_order_permission(
        intent,
        stage=stage,
        root=root,
        write_ledger=True,
    )

    result: dict[str, Any] = {
        "generated_utc": now_utc(),
        "stage": stage,
        "blocked": not decision.approved,
        "approved": decision.approved,
        "reason": decision.reason,
        "intent": asdict(intent),
        "decision": asdict(decision),
        "live_executor_surface": discover_live_executor_surface(),
        "executor_called": False,
        "executor_result": None,
    }

    if not decision.approved:
        return result

    selected_executor = executor or _find_default_executor()
    if selected_executor is None:
        result["blocked"] = True
        result["approved"] = False
        result["reason"] = "no_underlying_live_executor_callable_found"
        return result

    result["executor_result"] = selected_executor(asdict(intent))
    result["executor_called"] = True
    result["blocked"] = False
    result["approved"] = True
    result["reason"] = "underlying_executor_called_after_safety_approval"
    return result


def write_smoke_report(payload: dict[str, Any], root: Path) -> Path:
    out_dir = root / "out" / "safety_reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "LATEST_safe_live_executor_smoke.json"
    md_path = out_dir / "LATEST_safe_live_executor_smoke.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    lines = []
    lines.append("# Safe Live Executor Smoke")
    lines.append("")
    lines.append(f"- Generated UTC: `{payload.get('generated_utc')}`")
    lines.append(f"- Stage: `{payload.get('stage')}`")
    lines.append(f"- Approved: `{payload.get('approved')}`")
    lines.append(f"- Blocked: `{payload.get('blocked')}`")
    lines.append(f"- Reason: `{payload.get('reason')}`")
    lines.append(f"- Executor called: `{payload.get('executor_called')}`")
    lines.append("")
    lines.append("## Live Executor Surface")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload.get("live_executor_surface"), indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")
    lines.append("## Safety Decision")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload.get("decision"), indent=2, sort_keys=True))
    lines.append("```")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main() -> int:
    root = repo_root()
    order = {
        "symbol": "TEST/USD",
        "side": "buy",
        "notional_usd": 1.0,
        "source": "safe_live_executor_smoke",
    }

    result = guarded_execute_order(order, stage="live-data-no-orders", root=root)
    report_path = write_smoke_report(result, root)

    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"REPORT={report_path}")

    expected = (
        result.get("blocked") is True
        and result.get("executor_called") is False
        and result.get("reason") == "blocked_by_live_data_no_orders_stage"
    )
    return 0 if expected else 2


if __name__ == "__main__":
    raise SystemExit(main())
