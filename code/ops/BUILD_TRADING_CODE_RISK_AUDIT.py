from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"

JSON_OUT = OUT_OPS / "trading_code_risk_audit_latest.json"
MD_OUT = DOCS / "TRADING_CODE_RISK_AUDIT_2026-06-19.md"

SCAN_GLOBS = (
    "code/*.py",
    "code/*.ps1",
    "code/execution/*.py",
    "code/execution/*.ps1",
    "code/ops/*.py",
    "code/ops/*.ps1",
    "config/runtime_control.json",
    "config/multi_account_policy.json",
    "config/accounts/*/runtime_control.json",
    "out/control_flags.json",
)

EXCLUDED_NAMES = {
    "BUILD_TRADING_CODE_RISK_AUDIT.py",
}

MUTATION_OPERATOR = r"(?:\s*:\s*|(?<![=!<>])\s*=\s*(?!=))"

RISK_PATTERNS: dict[str, tuple[int, re.Pattern[str]]] = {
    "kraken_add_order": (3, re.compile(r"/0/private/AddOrder|ADD_ORDER_PATH|AddOrder", re.IGNORECASE)),
    "validate_false": (4, re.compile(r"validate\s*[:=]\s*(?:False|false)|validate=false", re.IGNORECASE)),
    "withdrawal_path": (5, re.compile(r"/0/private/Withdraw|\.withdraw\(|withdraw_btc|auto_withdraw", re.IGNORECASE)),
    "liquidation_path": (5, re.compile(r"LIQUIDATE_ALL|liquidate_all", re.IGNORECASE)),
    "cancel_all_orders": (3, re.compile(r"/0/private/CancelAll(?!OrdersAfter)|\bCancelAll\b", re.IGNORECASE)),
    "live_arm_write": (4, re.compile(rf"allow_live_orders[^\n]{{0,24}}{MUTATION_OPERATOR}\$?true", re.IGNORECASE)),
    "live_mode_write": (4, re.compile(rf"(?:default_)?mode[^\n]{{0,24}}{MUTATION_OPERATOR}[\"']live[\"']", re.IGNORECASE)),
    "kill_switch_off_write": (2, re.compile(rf"kill_switch[^\n]{{0,24}}{MUTATION_OPERATOR}\$?false", re.IGNORECASE)),
    "automatic_approval": (5, re.compile(r"/api/master/approval/decide|build_decide_payload\(|event[\"']?\s*[:=]\s*[\"']approve_attempt", re.IGNORECASE)),
    "startup_persistence": (3, re.compile(r"Register-ScheduledTask|Startup\\|shell:startup", re.IGNORECASE)),
    "direct_key_loader": (2, re.compile(r"luma_live_keys\.env|live_keys\.env|keys\.env|DISCOVER_AND_ROUTE_ALL_LIVE_KEYS|ROUTE_AND_BIND_ALL_LIVE_KEYS", re.IGNORECASE)),
}

PROTECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "dry_run": re.compile(r"dry[-_ ]?run|DRY RUN|status_only|no_orders", re.IGNORECASE),
    "execute_confirm": re.compile(r"--execute|CONFIRM_PHRASE|confirm\s*[!=]=|confirmation", re.IGNORECASE),
    "validate_only": re.compile(r"validate_only|submit_order_validate_only|validate\s*[:=]\s*(?:True|true)", re.IGNORECASE),
    "human_approval": re.compile(r"PENDING_HUMAN_APPROVAL|approval_queue|approved_by|operator approval|human[_ -]action[_ -]time[_ -](?:approval|authority)|HUMAN_APPROVAL_ENV|LUMA_HUMAN_UNLOCK_TOKEN", re.IGNORECASE),
    "runtime_gate": re.compile(r"LiveRuntimeGuard|can_place_live_order|assert_runtime_safety|autofire_authority_state|validate_live_action_authority|_live_action_time_authority|SAFE_DRY_RUN|ExpectedRuntimeSha256|trading_stack_safety_audit", re.IGNORECASE),
}

SAFE_SPINE = [
    "code/kraken_execution.py",
    "code/execution/live_runtime_guard.py",
    "code/execution/risk_kernel.py",
    "code/execution/order_router.py",
    "code/ops/_copilot_watch.py",
    "code/ops/cancel_open_orders.py",
    "code/ops/BUILD_TRADING_STACK_SAFETY_AUDIT.py",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def iter_scan_paths() -> list[Path]:
    paths: set[Path] = set()
    for pattern in SCAN_GLOBS:
        paths.update(path for path in ROOT.glob(pattern) if path.is_file())
    return sorted(path for path in paths if path.name not in EXCLUDED_NAMES)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def pattern_hits(text: str) -> dict[str, list[dict[str, Any]]]:
    hits: dict[str, list[dict[str, Any]]] = {}
    for name, (_, pattern) in RISK_PATTERNS.items():
        rows: list[dict[str, Any]] = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                rows.append({"line": line_no, "snippet": line.strip()[:180]})
                if len(rows) >= 5:
                    break
        if rows:
            hits[name] = rows
    return hits


def protections(text: str) -> list[str]:
    return sorted(name for name, pattern in PROTECTION_PATTERNS.items() if pattern.search(text))


def classify_file(hits: dict[str, list[dict[str, Any]]], guards: list[str]) -> tuple[str, str]:
    signals = set(hits)
    has_confirm = "execute_confirm" in guards
    has_validate = "validate_only" in guards
    has_runtime = "runtime_gate" in guards
    has_human = "human_approval" in guards

    if {"withdrawal_path", "liquidation_path"} & signals and not (has_confirm and has_runtime and has_human):
        return "critical_legacy_quarantine", "withdraw/liquidation path lacks exact execute confirmation, runtime gate, or human action-time approval"
    if "validate_false" in signals and "kraken_add_order" in signals and not has_human:
        return "high_review", "validate=false order path lacks a clear human approval gate"
    if "kraken_add_order" in signals and not (has_validate or has_runtime or has_human):
        return "high_review", "direct order path lacks validate/runtime/human gate"
    if "cancel_all_orders" in signals and not has_confirm:
        return "high_review", "cancel-all path lacks explicit execute confirmation"
    if "automatic_approval" in signals:
        if has_runtime and has_human:
            return "guarded_review", "automatic approval is fail-closed behind runtime and human action-time authority, but still requires live-use review"
        return "high_review", "automatic approval path requires a cross-file action-time authorization review"
    if {"live_arm_write", "live_mode_write"} & signals and not (has_runtime and has_human):
        return "high_review", "live-arm write lacks both a runtime gate and human action-time approval"
    if signals:
        return "guarded_review", "risk-bearing path has at least one guard, but still needs review before live use"
    return "no_risk_signal", "no configured live-order risk signal detected"


def build_audit() -> dict[str, Any]:
    files = []
    for path in iter_scan_paths():
        text = read_text(path)
        hits = pattern_hits(text)
        if not hits:
            continue
        guards = protections(text)
        classification, action = classify_file(hits, guards)
        risk_score = sum(RISK_PATTERNS[name][0] * len(rows) for name, rows in hits.items())
        files.append(
            {
                "path": rel(path),
                "classification": classification,
                "risk_score": risk_score,
                "signals": sorted(hits),
                "protections": guards,
                "required_action": action,
                "hits": hits,
            }
        )

    files.sort(key=lambda row: (row["classification"] != "critical_legacy_quarantine", -row["risk_score"], row["path"]))
    blockers = [
        f"{row['path']}: {row['required_action']}"
        for row in files
        if row["classification"] in {"critical_legacy_quarantine", "high_review"}
    ]
    posture = "BLOCK_LEGACY_LIVE" if blockers else "GUARDED_REVIEW"

    return {
        "generated_utc": now_utc(),
        "schema": "trading_code_risk_audit_v1",
        "posture": posture,
        "scanner_scope": list(SCAN_GLOBS),
        "secret_handling": "Scanner intentionally avoids env/key files and reports only source/config risk signals, never credential values.",
        "safe_spine": SAFE_SPINE,
        "file_count_with_risk_signals": len(files),
        "blockers": blockers,
        "files": files,
        "promotion_rule": "Only route live-capable work through the safe spine after paper evidence, fresh heartbeats, empty blockers, and separate human action-time approval. Legacy direct-order, withdrawal, and liquidation scripts stay quarantined until rewritten behind these guards.",
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Trading Code Risk Audit",
        "",
        f"Generated UTC: {audit['generated_utc']}",
        "",
        f"Posture: {audit['posture']}",
        "",
        "## Secret Handling",
        "",
        audit["secret_handling"],
        "",
        "## Best Current Safe Spine",
        "",
    ]
    lines.extend(f"- {item}" for item in audit["safe_spine"])
    lines.extend(["", "## Blockers", ""])
    if audit["blockers"]:
        lines.extend(f"- {item}" for item in audit["blockers"])
    else:
        lines.append("- none")
    lines.extend(["", "## Risk Files", ""])
    for row in audit["files"][:40]:
        lines.extend(
            [
                f"### {row['path']}",
                "",
                f"- classification: {row['classification']}",
                f"- risk_score: {row['risk_score']}",
                f"- signals: {', '.join(row['signals'])}",
                f"- protections: {', '.join(row['protections']) if row['protections'] else 'none'}",
                f"- required action: {row['required_action']}",
                "",
            ]
        )
    lines.extend(["## Promotion Rule", "", audit["promotion_rule"], ""])
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
