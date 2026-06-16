from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPORT_SCHEMA_VERSION = "1.0.0"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_root() -> Path:
    env_root = os.environ.get("LUMA_STACK_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def sha256_file(path: Path) -> str | None:
    try:
        if not path.exists() or not path.is_file():
            return None
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "live"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def compact_config_view(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"valid_object": False}

    allowlist = [
        "mode",
        "runtime_mode",
        "allow_live_orders",
        "live_enabled",
        "paper_enabled",
        "kill_switch",
        "require_controller",
        "require_validate_pass",
        "max_position_usd",
        "max_notional_per_trade_usd",
        "max_daily_loss_usd",
        "daily_loss_limit",
        "max_open_positions",
        "max_portfolio_heat",
        "portfolio_heat_limit",
        "deadman_timeout_seconds",
        "default_pair",
        "default_order_type",
    ]

    return {k: payload.get(k) for k in allowlist if k in payload}


def env_name_audit() -> dict[str, bool]:
    names = [
        "OPENAI_API_KEY",
        "KRAKEN_API_KEY",
        "KRAKEN_API_SECRET",
        "ALPACA_API_KEY",
        "ALPACA_API_SECRET",
        "ALPACA_SECRET_KEY",
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "COINBASE_API_KEY",
        "COINBASE_API_SECRET",
        "FRED_API_KEY",
        "ALPHAVANTAGE_API_KEY",
        "EIA_API_KEY",
    ]
    return {name: bool(os.environ.get(name)) for name in names}


def find_kill_files(root: Path) -> list[str]:
    candidates = [
        root / "KILL_SWITCH_STOP",
        root / "config" / "KILL_SWITCH_STOP",
        root / "out" / "execution" / "KILL_SWITCH_STOP",
        root / "out" / "KILL_SWITCH_STOP",
    ]
    return [str(p) for p in candidates if p.exists()]


def evaluate(stage: str, root: Path) -> dict[str, Any]:
    root = root.resolve()

    runtime_candidates = [
        root / "config" / "runtime_control.json",
        root / "code" / "execution" / "runtime_control.json",
        root / "runtime_control.json",
    ]

    runtime_file = next((p for p in runtime_candidates if p.exists()), runtime_candidates[0])
    control_flags_file = root / "control_flags.json"

    runtime = load_json(runtime_file, {})
    flags = load_json(control_flags_file, {})

    runtime_view = compact_config_view(runtime)
    flags_view = compact_config_view(flags)

    runtime_mode = str(runtime_view.get("mode") or runtime_view.get("runtime_mode") or "").lower()
    flags_mode = str(flags_view.get("runtime_mode") or "").lower()

    runtime_allows_live = boolish(runtime_view.get("allow_live_orders"))
    flags_live_enabled = boolish(flags_view.get("live_enabled"))
    kill_switch = boolish(runtime_view.get("kill_switch")) or boolish(flags_view.get("kill_switch"))

    live_order_config_detected = (
        runtime_mode == "live"
        or flags_mode == "live"
        or runtime_allows_live
        or flags_live_enabled
    )

    kill_files = find_kill_files(root)

    blockers: list[str] = []
    warnings: list[str] = []

    if kill_switch:
        blockers.append("kill_switch_true_in_config")

    if kill_files:
        blockers.append("kill_switch_file_present")

    if live_order_config_detected:
        warnings.append("live_order_config_detected_but_stage_blocks_orders")

    if stage in {"live-data-no-orders", "live_data_no_orders"}:
        stage_status = "PASS_READ_ONLY"
        order_permission = False
        order_permission_reason = "blocked_by_live_data_no_orders_stage"
    elif stage == "paper":
        order_permission = False
        if runtime_mode != "paper":
            blockers.append("runtime_mode_not_paper")
        if runtime_allows_live:
            blockers.append("allow_live_orders_true")
        stage_status = "PASS" if not blockers else "FAIL"
        order_permission_reason = "paper_stage_never_allows_live_orders"
    elif stage in {"tiny-live-manual-arm", "tiny_live_manual_arm"}:
        arm_file = root / "LIVE_TINY_MANUAL_ARM.confirm"
        cap = runtime_view.get("max_position_usd", flags_view.get("max_notional_per_trade_usd", 0))
        try:
            cap_float = float(cap or 0)
        except Exception:
            cap_float = 0.0

        if not arm_file.exists():
            blockers.append("missing_LIVE_TINY_MANUAL_ARM.confirm")
        if not runtime_allows_live:
            blockers.append("allow_live_orders_false")
        if not flags_live_enabled:
            blockers.append("live_enabled_false")
        if cap_float <= 0 or cap_float > 5:
            blockers.append("tiny_live_cap_must_be_between_0_and_5_usd")

        order_permission = not blockers
        stage_status = "PASS_MANUAL_ARM_REQUIRED" if order_permission else "FAIL"
        order_permission_reason = "tiny_live_manual_gate"
    else:
        blockers.append(f"unknown_stage:{stage}")
        stage_status = "FAIL"
        order_permission = False
        order_permission_reason = "unknown_stage"

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_utc": now_utc(),
        "root": str(root),
        "stage": stage,
        "stage_status": stage_status,
        "order_permission": order_permission,
        "order_permission_reason": order_permission_reason,
        "blockers": blockers,
        "warnings": warnings,
        "runtime_file": str(runtime_file),
        "runtime_file_sha256": sha256_file(runtime_file),
        "control_flags_file": str(control_flags_file),
        "control_flags_file_sha256": sha256_file(control_flags_file),
        "runtime_view_no_secrets": runtime_view,
        "control_flags_view_no_secrets": flags_view,
        "env_names_present_no_values": env_name_audit(),
        "kill_files_present": kill_files,
        "meaning": [
            "This gate is intentionally read-only unless tiny-live manual arm passes.",
            "Live-data no-orders mode may read market/account data later, but must not submit orders.",
            "No secret values are printed.",
            "This patch creates the missing middle stage between paper and real live execution.",
        ],
    }
    return report


def write_report(report: dict[str, Any], root: Path) -> Path:
    out_dir = root / "out" / "safety_reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"live_data_no_orders_gate_{stamp}.json"
    latest_json = out_dir / "LATEST_live_data_no_orders_gate.json"
    md_path = out_dir / "LATEST_live_data_no_orders_gate.md"

    payload = json.dumps(report, indent=2, sort_keys=True)
    json_path.write_text(payload, encoding="utf-8")
    latest_json.write_text(payload, encoding="utf-8")

    lines = []
    lines.append("# LumenCore Live-Data No-Orders Gate")
    lines.append("")
    lines.append(f"- Generated UTC: `{report['generated_utc']}`")
    lines.append(f"- Stage: `{report['stage']}`")
    lines.append(f"- Stage status: `{report['stage_status']}`")
    lines.append(f"- Order permission: `{report['order_permission']}`")
    lines.append(f"- Reason: `{report['order_permission_reason']}`")
    lines.append(f"- Runtime file: `{report['runtime_file']}`")
    lines.append(f"- Runtime SHA-256: `{report['runtime_file_sha256']}`")
    lines.append(f"- Control flags SHA-256: `{report['control_flags_file_sha256']}`")
    lines.append("")
    lines.append("## Blockers")
    lines.append("")
    if report["blockers"]:
        for item in report["blockers"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("- None for this stage.")
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    if report["warnings"]:
        for item in report["warnings"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("## Runtime View, No Secrets")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report["runtime_view_no_secrets"], indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")
    lines.append("## Control Flags View, No Secrets")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report["control_flags_view_no_secrets"], indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")
    lines.append("## Env Names Present, No Values")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report["env_names_present_no_values"], indent=2, sort_keys=True))
    lines.append("```")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        default="live-data-no-orders",
        choices=["paper", "live-data-no-orders", "live_data_no_orders", "tiny-live-manual-arm", "tiny_live_manual_arm"],
    )
    parser.add_argument("--root", type=Path, default=resolve_root())
    args = parser.parse_args()

    root = args.root.expanduser().resolve()
    report = evaluate(args.stage, root)
    md_path = write_report(report, root)

    print(f"LIVE_DATA_NO_ORDERS_GATE={report['stage_status']}")
    print(f"ORDER_PERMISSION={report['order_permission']}")
    print(f"REASON={report['order_permission_reason']}")
    print(f"REPORT={md_path}")

    # live-data-no-orders is allowed to pass even when live config exists,
    # because this stage explicitly blocks orders and only reports risk.
    if args.stage in {"live-data-no-orders", "live_data_no_orders"}:
        return 0

    return 0 if not report["blockers"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
