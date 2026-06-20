from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_EXEC = ROOT / "out" / "execution"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"

RUNTIME_FILE = CONFIG / "runtime_control.json"
EXEC_HEARTBEAT = OUT_EXEC / "live_executor_heartbeat.json"
AUTOFIRE_HEARTBEAT = OUT_EXEC / "approval_autofire_heartbeat.json"
GROWTH_STATUS = OUT_EXEC / "vps_growth_controller_status.json"
QUEUE_FILE = OUT_EXEC / "live_operator_approval_queue.json"

JSON_OUT = OUT_OPS / "trading_stack_safety_audit_latest.json"
MD_OUT = DOCS / "TRADING_STACK_SAFETY_AUDIT_2026-06-19.md"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_load_error": str(exc), "_path": str(path)}
    return default


def parse_dt(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def age_minutes(value: Any) -> float | None:
    dt = parse_dt(value)
    if dt is None:
        return None
    return round(max((now_utc() - dt).total_seconds() / 60.0, 0.0), 3)


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "live", "enabled"}
    return False


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def add_blocker(blockers: list[str], condition: bool, message: str) -> None:
    if condition and message not in blockers:
        blockers.append(message)


def build_audit() -> dict[str, Any]:
    runtime = load_json(RUNTIME_FILE, {})
    executor = load_json(EXEC_HEARTBEAT, {})
    autofire = load_json(AUTOFIRE_HEARTBEAT, {})
    growth = load_json(GROWTH_STATUS, {})
    queue = load_json(QUEUE_FILE, {})

    runtime_mode = str(runtime.get("mode") or runtime.get("runtime_mode") or "").strip().lower()
    allow_live_orders = truthy(runtime.get("allow_live_orders"))
    paper_enabled = truthy(runtime.get("paper_enabled"))
    kill_switch = truthy(runtime.get("kill_switch"))
    executor_age_min = age_minutes(executor.get("timestamp_utc") or executor.get("timestamp") or executor.get("generated_utc"))
    autofire_age_min = age_minutes(autofire.get("generated_utc") or autofire.get("timestamp_utc"))
    growth_guard = growth.get("guard") if isinstance(growth.get("guard"), dict) else {}
    growth_summary = growth.get("summary") if isinstance(growth.get("summary"), dict) else {}

    queue_tickets = queue.get("tickets") if isinstance(queue.get("tickets"), list) else []
    pending_operator_tickets = [
        row for row in queue_tickets
        if str(row.get("decision_state") or row.get("approval_state") or "").upper().startswith("PENDING")
    ]

    blockers: list[str] = []
    warnings: list[str] = []

    add_blocker(blockers, runtime_mode != "paper", f"runtime mode is not paper: {runtime_mode or 'missing'}")
    add_blocker(blockers, allow_live_orders, "allow_live_orders is true")
    add_blocker(blockers, not paper_enabled, "paper_enabled is false")
    add_blocker(blockers, executor_age_min is None or executor_age_min > 20.0, f"executor heartbeat stale or missing: {executor_age_min}")
    add_blocker(blockers, autofire_age_min is None or autofire_age_min > 20.0, f"autofire heartbeat stale or missing: {autofire_age_min}")
    add_blocker(blockers, not bool(growth_guard.get("heartbeat_ok", False)), "growth controller heartbeat check is not ok")
    add_blocker(blockers, str(growth.get("mode") or "").upper() != "SAFE_DRY_RUN", "growth controller is not in SAFE_DRY_RUN")
    add_blocker(blockers, int(growth_summary.get("actionable_candidates") or 0) <= 0, "no actionable candidates in latest growth controller run")
    add_blocker(blockers, int(growth_summary.get("auto_fired_count") or 0) != 0, "auto-fired orders were detected")

    if not kill_switch:
        warnings.append("kill_switch is false; acceptable only while allow_live_orders=false and runtime mode=paper")
    if truthy(runtime.get("gate_override_enabled")):
        warnings.append("gate_override_enabled is true")
    if truthy(runtime.get("auto_convert_collateral")):
        warnings.append("auto_convert_collateral is true; keep disabled for unattended paper governance")
    if pending_operator_tickets:
        warnings.append(f"operator queue has {len(pending_operator_tickets)} pending review tickets")

    posture = "BLOCK_LIVE"
    if not blockers and runtime_mode == "paper" and not allow_live_orders and paper_enabled:
        posture = "PAPER_OK"

    return {
        "generated_utc": now_utc().isoformat(),
        "schema": "trading_stack_safety_audit_v1",
        "posture": posture,
        "runtime": {
            "mode": runtime_mode,
            "allow_live_orders": allow_live_orders,
            "paper_enabled": paper_enabled,
            "kill_switch": kill_switch,
            "max_notional_per_trade_usd": safe_float(runtime.get("max_notional_per_trade_usd"), 0.0),
            "max_daily_loss_usd": safe_float(runtime.get("max_daily_loss_usd"), 0.0),
            "max_open_positions": int(safe_float(runtime.get("max_open_positions"), 0.0)),
        },
        "evidence": {
            "executor_heartbeat_age_min": executor_age_min,
            "executor_status": executor.get("status"),
            "executor_reason": executor.get("reason"),
            "symbol_intel_stale": bool(executor.get("symbol_intel_stale", False)),
            "autofire_heartbeat_age_min": autofire_age_min,
            "autofire_status": autofire.get("status"),
            "autofire_eligible_count": int(safe_float(autofire.get("eligible_count"), 0.0)),
            "autofire_approved_buy_count": int(safe_float(autofire.get("approved_buy_count"), 0.0)),
            "growth_mode": growth.get("mode"),
            "growth_guard_reasons": growth_guard.get("reasons", []),
            "growth_actionable_candidates": int(safe_float(growth_summary.get("actionable_candidates"), 0.0)),
            "growth_emitted_count": int(safe_float(growth_summary.get("emitted_count"), 0.0)),
            "growth_auto_fired_count": int(safe_float(growth_summary.get("auto_fired_count"), 0.0)),
            "portfolio_est_usd": safe_float(growth_guard.get("portfolio_est_usd"), 0.0),
            "operator_pending_tickets": len(pending_operator_tickets),
        },
        "blockers": blockers,
        "warnings": warnings,
        "promotion_rule": "Live execution remains blocked until blockers are empty, paper/live heartbeats are fresh, actionable candidates exist, auto-fire count is zero unless explicitly approved, and a human operator signs a separate action-time approval.",
    }


def render_markdown(audit: dict[str, Any]) -> str:
    runtime = audit["runtime"]
    evidence = audit["evidence"]
    blockers = audit.get("blockers", [])
    warnings = audit.get("warnings", [])
    lines = [
        "# Trading Stack Safety Audit",
        "",
        f"Generated UTC: {audit['generated_utc']}",
        "",
        f"Posture: {audit['posture']}",
        "",
        "## Runtime Gates",
        "",
        f"- mode: {runtime['mode']}",
        f"- allow_live_orders: {runtime['allow_live_orders']}",
        f"- paper_enabled: {runtime['paper_enabled']}",
        f"- kill_switch: {runtime['kill_switch']}",
        f"- max_notional_per_trade_usd: {runtime['max_notional_per_trade_usd']}",
        f"- max_daily_loss_usd: {runtime['max_daily_loss_usd']}",
        f"- max_open_positions: {runtime['max_open_positions']}",
        "",
        "## Evidence Readout",
        "",
        f"- executor heartbeat age min: {evidence['executor_heartbeat_age_min']}",
        f"- executor status/reason: {evidence['executor_status']} / {evidence['executor_reason']}",
        f"- symbol intel stale: {evidence['symbol_intel_stale']}",
        f"- autofire heartbeat age min: {evidence['autofire_heartbeat_age_min']}",
        f"- autofire eligible/approved buy: {evidence['autofire_eligible_count']} / {evidence['autofire_approved_buy_count']}",
        f"- growth mode: {evidence['growth_mode']}",
        f"- growth guard reasons: {evidence['growth_guard_reasons']}",
        f"- actionable/emitted/auto-fired: {evidence['growth_actionable_candidates']} / {evidence['growth_emitted_count']} / {evidence['growth_auto_fired_count']}",
        f"- portfolio estimate USD: {evidence['portfolio_est_usd']}",
        f"- operator pending tickets: {evidence['operator_pending_tickets']}",
        "",
        "## Live Promotion Blockers",
        "",
    ]
    if blockers:
        lines.extend(f"- {item}" for item in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {item}" for item in warnings)
    else:
        lines.append("- none")
    lines.extend(["", "## Promotion Rule", "", audit["promotion_rule"], ""])
    return "\n".join(lines)


def main() -> int:
    OUT_OPS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    audit = build_audit()
    JSON_OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    MD_OUT.write_text(render_markdown(audit), encoding="utf-8")
    print(json.dumps({"posture": audit["posture"], "blockers": len(audit["blockers"]), "json": str(JSON_OUT), "md": str(MD_OUT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())