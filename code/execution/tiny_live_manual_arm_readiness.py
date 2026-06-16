from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def check_readiness(root: Path) -> dict[str, Any]:
    policy_path = root / "config" / "tiny_live_manual_arm_policy.json"
    policy = load_json(policy_path, {})

    confirmation_rel = str(policy.get("confirmation_file", "LIVE_TINY_MANUAL_ARM.confirm"))
    confirmation_path = root / confirmation_rel

    live_gate_report = root / "out" / "safety_reports" / "LATEST_live_data_no_orders_gate.json"
    safe_executor_report = root / "out" / "safety_reports" / "LATEST_safe_live_executor_smoke.json"
    entrypoint_audit_report = root / "out" / "safety_reports" / "LATEST_live_entrypoint_audit.json"
    redirect_report = root / "out" / "safety_reports" / "LATEST_legacy_launcher_redirects.md"
    ledger = root / "out" / "safety_reports" / "order_safety_gate_ledger.jsonl"

    live_gate = load_json(live_gate_report, {})
    safe_exec = load_json(safe_executor_report, {})
    audit = load_json(entrypoint_audit_report, {})

    raw_refs = audit.get("summary", {}).get("files_with_raw_live_references", None)
    safe_refs = audit.get("summary", {}).get("files_with_safe_references", None)

    checks = {
        "policy_exists": policy_path.exists(),
        "policy_enabled_false": policy.get("enabled") is False,
        "policy_activation_not_active": policy.get("activation_status") == "NOT_ACTIVE",
        "confirmation_file_absent": not confirmation_path.exists(),
        "safe_launcher_exists": exists(root, "code/execution/RUN_LIVE_STACK_SAFE_NO_ORDERS.ps1"),
        "order_safety_gate_exists": exists(root, "code/execution/order_safety_gate.py"),
        "safe_live_executor_exists": exists(root, "code/execution/safe_live_executor.py"),
        "live_data_no_orders_gate_exists": exists(root, "code/execution/live_data_no_orders_gate.py"),
        "router_uses_safety_gate_exists": exists(root, "code/execution/order_router.py"),
        "live_gate_report_present": live_gate_report.exists(),
        "safe_executor_report_present": safe_executor_report.exists(),
        "entrypoint_audit_report_present": entrypoint_audit_report.exists(),
        "redirect_report_present": redirect_report.exists(),
        "ledger_present": ledger.exists(),
        "live_gate_blocks_orders": live_gate.get("order_permission") is False,
        "safe_executor_did_not_call_executor": safe_exec.get("executor_called") is False,
        "safe_executor_blocked": safe_exec.get("blocked") is True,
        "raw_entrypoint_count_known": isinstance(raw_refs, int),
        "safe_reference_count_known": isinstance(safe_refs, int),
    }

    blockers = []
    for name, passed in checks.items():
        if not passed:
            blockers.append(name)

    readiness = {
        "generated_utc": now_utc(),
        "mode": "design_only",
        "live_trading_active": False,
        "tiny_live_ready": False,
        "reason": "manual_arm_not_enabled_design_only",
        "repo_root": str(root),
        "policy_file": str(policy_path),
        "confirmation_file": str(confirmation_path),
        "checks": checks,
        "blockers": blockers,
        "audit_counts": {
            "files_with_raw_live_references": raw_refs,
            "files_with_safe_references": safe_refs,
        },
        "required_future_manual_arm_steps": [
            "Review raw live entrypoint audit and redirect remaining high-risk launchers.",
            "Confirm live-data no-orders gate passes.",
            "Confirm safe_live_executor blocks orders before executor call.",
            "Create a separate deliberate manual-arm patch.",
            "Create LIVE_TINY_MANUAL_ARM.confirm only for tiny-live testing.",
            "Set max_order_usd no higher than 5 for first live test.",
            "Verify exchange/broker balance read works without placing orders.",
            "Run one tiny test only after human confirmation."
        ],
        "meaning": [
            "This patch prepares the future tiny-live path but does not activate it.",
            "The confirmation file must be absent in design-only mode.",
            "The current safe state is live-data/no-orders."
        ]
    }

    return readiness


def write_reports(report: dict[str, Any], root: Path) -> tuple[Path, Path]:
    out_dir = root / "out" / "safety_reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "LATEST_tiny_live_manual_arm_readiness.json"
    md_path = out_dir / "LATEST_tiny_live_manual_arm_readiness.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    lines = []
    lines.append("# Tiny-Live Manual Arm Readiness")
    lines.append("")
    lines.append(f"- Generated UTC: `{report['generated_utc']}`")
    lines.append(f"- Mode: `{report['mode']}`")
    lines.append(f"- Live trading active: `{report['live_trading_active']}`")
    lines.append(f"- Tiny-live ready: `{report['tiny_live_ready']}`")
    lines.append(f"- Reason: `{report['reason']}`")
    lines.append("")
    lines.append("## Audit Counts")
    lines.append("")
    for k, v in report["audit_counts"].items():
        lines.append(f"- `{k}`: `{v}`")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    lines.append("| Check | Passed |")
    lines.append("|---|---|")
    for k, v in report["checks"].items():
        lines.append(f"| `{k}` | `{v}` |")
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if report["blockers"]:
        for b in report["blockers"]:
            lines.append(f"- `{b}`")
    else:
        lines.append("- None for design-only mode.")
    lines.append("")
    lines.append("## Future Manual Arm Steps")
    lines.append("")
    for step in report["required_future_manual_arm_steps"]:
        lines.append(f"- {step}")
    lines.append("")
    lines.append("## Meaning")
    lines.append("")
    for item in report["meaning"]:
        lines.append(f"- {item}")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    root = repo_root()
    report = check_readiness(root)
    json_path, md_path = write_reports(report, root)

    print(json.dumps({
        "mode": report["mode"],
        "live_trading_active": report["live_trading_active"],
        "tiny_live_ready": report["tiny_live_ready"],
        "reason": report["reason"],
        "audit_counts": report["audit_counts"],
        "blockers": report["blockers"],
    }, indent=2, sort_keys=True))

    print(f"JSON_REPORT={json_path}")
    print(f"MD_REPORT={md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
