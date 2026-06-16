from __future__ import annotations

"""
LumenCore order router.

Safety rule:
Every order intent must pass order_safety_gate before any downstream executor
or broker adapter can receive it.

Default stage is live-data-no-orders, so orders are blocked unless a later,
manual, explicit stage transition approves them.
"""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

try:
    from order_safety_gate import OrderIntent, decide_order_permission
except Exception:
    from .order_safety_gate import OrderIntent, decide_order_permission


class OrderBlocked(RuntimeError):
    """Raised when the central safety gate blocks an order intent."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_order_intent(order: dict[str, Any] | OrderIntent) -> OrderIntent:
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
        source=str(order.get("source") or "order_router"),
    )


def preflight_order(
    order: dict[str, Any] | OrderIntent,
    *,
    stage: str = "live-data-no-orders",
    root: Path | None = None,
) -> tuple[bool, dict[str, Any]]:
    """
    Non-throwing check for dashboards, tests, and dry runs.

    Returns:
        (approved, decision_dict)
    """
    intent = normalize_order_intent(order)
    decision = decide_order_permission(
        intent,
        stage=stage,
        root=root or _repo_root(),
        write_ledger=True,
    )
    return decision.approved, asdict(decision)


def route_order(
    order: dict[str, Any] | OrderIntent,
    *,
    executor: Callable[[dict[str, Any]], Any] | None = None,
    stage: str = "live-data-no-orders",
    root: Path | None = None,
) -> dict[str, Any]:
    """
    Safety-first route function.

    In live-data-no-orders mode this must block every order. Later, tiny-live
    can provide an executor only after the safety gate approves the intent.
    """
    intent = normalize_order_intent(order)

    decision = decide_order_permission(
        intent,
        stage=stage,
        root=root or _repo_root(),
        write_ledger=True,
    )

    decision_dict = asdict(decision)

    if not decision.approved:
        return {
            "routed": False,
            "blocked": True,
            "reason": decision.reason,
            "decision": decision_dict,
            "intent": asdict(intent),
        }

    if executor is None:
        return {
            "routed": False,
            "blocked": True,
            "reason": "missing_executor_even_after_safety_approval",
            "decision": decision_dict,
            "intent": asdict(intent),
        }

    result = executor(asdict(intent))
    return {
        "routed": True,
        "blocked": False,
        "reason": "executor_called_after_safety_approval",
        "decision": decision_dict,
        "intent": asdict(intent),
        "executor_result": result,
    }


def require_route_order(
    order: dict[str, Any] | OrderIntent,
    *,
    executor: Callable[[dict[str, Any]], Any] | None = None,
    stage: str = "live-data-no-orders",
    root: Path | None = None,
) -> dict[str, Any]:
    result = route_order(order, executor=executor, stage=stage, root=root)
    if result.get("blocked"):
        raise OrderBlocked(str(result.get("reason")))
    return result


def main() -> int:
    test_order = {
        "symbol": "TEST/USD",
        "side": "buy",
        "notional_usd": 1.0,
        "source": "order_router_smoke",
    }
    result = route_order(test_order, stage="live-data-no-orders")
    import json

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("blocked") and result.get("reason") == "blocked_by_live_data_no_orders_stage" else 2


if __name__ == "__main__":
    raise SystemExit(main())
