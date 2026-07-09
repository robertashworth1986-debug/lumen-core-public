from __future__ import annotations

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
MANIFEST_JSON = OUT_OPS / "data_room_manifest_latest.json"

GLOBAL_RUNTIME_JSON = ROOT / "config" / "runtime_control.json"
EXECUTION_STATUS_JSON = ROOT / "out" / "execution_status.json"
AGENT_MANIFEST = ROOT / "code" / "autonomous_agent_manifest.py"

ACCOUNT_RUNTIME_JSONS = [
    ROOT / "config" / "accounts" / "KRAKEN_PRIMARY" / "runtime_control.json",
    ROOT / "config" / "accounts" / "ALPACA_PRIMARY" / "runtime_control.json",
]

RUNTIME_MARKERS = [
    ROOT / "control" / "LIVE.flag",
    ROOT / "config" / "live_arm.confirm",
    ROOT / "config" / "multi_live_arm.confirm",
]

OUT_JSON = OUT_OPS / "autonomous_quant_governance_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "autonomous_quant_governance_packet.json"
OUT_MD = SPRINT_DIR / "AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md"

ALLOWED_MODES = [
    {
        "mode": "replay_lab",
        "allowed": "Approved public, synthetic, or local datasets may be used for baseline-vs-candidate comparison.",
        "gate": "No external system action, no order placement, and no capital movement.",
    },
    {
        "mode": "paper_evaluation",
        "allowed": "Paper simulation may produce research receipts, negative-result records, and benchmark dashboards.",
        "gate": "Paper output cannot be represented as external validation or deployable capital performance.",
    },
    {
        "mode": "opportunity_monitor",
        "allowed": "Official opportunities may be watched, ranked, and drafted into human-review packets.",
        "gate": "Human approval remains required before send, upload, filing, certification, pricing, or term action.",
    },
    {
        "mode": "proof_factory",
        "allowed": "Artifacts may be hashed, mirrored, classified, and scanned into the reviewer data room.",
        "gate": "Public claims remain bounded by reviewer gate and authority matrix.",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_status(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def marker_status(path: Path) -> dict[str, Any]:
    text = ""
    if path.exists() and path.is_file():
        text = path.read_text(encoding="utf-8", errors="ignore").strip()[:160]
    return {
        "path": rel(path),
        "present": path.exists(),
        "value": text,
        "requires_reconciliation": bool(text and text.upper() != "OFF"),
        "sha256": sha256_file(path) if path.exists() else "",
    }


def load_agent_registry() -> dict[str, dict[str, Any]]:
    if not AGENT_MANIFEST.exists():
        return {}
    tree = ast.parse(AGENT_MANIFEST.read_text(encoding="utf-8", errors="ignore"))
    for node in tree.body:
        if not isinstance(node, ast.AnnAssign) and not isinstance(node, ast.Assign):
            continue
        target = node.target if isinstance(node, ast.AnnAssign) else node.targets[0]
        if isinstance(target, ast.Name) and target.id == "AGENT_REGISTRY":
            try:
                value = ast.literal_eval(node.value)
            except Exception:
                return {}
            return value if isinstance(value, dict) else {}
    return {}


def summarize_agents(registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for key, row in sorted(registry.items()):
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "id": str(row.get("id") or key),
                "name": str(row.get("name") or key),
                "channel": str(row.get("channel") or ""),
                "auto_fire": bool(row.get("auto_fire")),
                "requires_approval": bool(row.get("requires_approval")),
                "queue_source": str(row.get("queue_source") or ""),
                "approval_endpoint": str(row.get("approval_endpoint") or ""),
            }
        )
    return rows


def runtime_snapshot() -> dict[str, Any]:
    global_runtime = read_json(GLOBAL_RUNTIME_JSON)
    execution_status = read_json(EXECUTION_STATUS_JSON)
    account_runtimes = [read_json(path) | {"path": rel(path)} for path in ACCOUNT_RUNTIME_JSONS]
    markers = [marker_status(path) for path in RUNTIME_MARKERS]
    registry = load_agent_registry()
    agent_rows = summarize_agents(registry)

    return {
        "global_runtime": {
            "path": rel(GLOBAL_RUNTIME_JSON),
            "mode": str(global_runtime.get("mode") or ""),
            "allow_live_orders": bool(global_runtime.get("allow_live_orders")),
            "paper_enabled": bool(global_runtime.get("paper_enabled")),
            "kill_switch": bool(global_runtime.get("kill_switch")),
            "force_live_mode": bool(global_runtime.get("force_live_mode")),
            "strict_live_only": bool(global_runtime.get("strict_live_only")),
            "live_operator_queue_enabled": bool(global_runtime.get("live_operator_queue_enabled")),
            "x1000_auto_enabled": bool(global_runtime.get("x1000_auto_enabled")),
            "x1000_auto_apply": bool(global_runtime.get("x1000_auto_apply")),
        },
        "execution_status": {
            "path": rel(EXECUTION_STATUS_JSON),
            "execution_mode": str(execution_status.get("execution_mode") or ""),
            "live_arm": str(execution_status.get("live_arm") or ""),
            "note": str(execution_status.get("note") or ""),
            "kill_switch": bool(execution_status.get("kill_switch")),
        },
        "account_runtimes": account_runtimes,
        "runtime_markers": markers,
        "agent_registry": agent_rows,
    }


def build_payload() -> dict[str, Any]:
    gate = read_json(REVIEWER_GATE_JSON)
    authority = read_json(AUTHORITY_JSON)
    manifest = read_json(MANIFEST_JSON)
    snapshot = runtime_snapshot()

    global_runtime = snapshot["global_runtime"]
    execution_status = snapshot["execution_status"]
    account_runtimes = snapshot["account_runtimes"]
    agent_rows = snapshot["agent_registry"]
    markers = snapshot["runtime_markers"]

    gate_clear = (
        bool(gate.get("reviewer_gate_clear"))
        and int((gate.get("summary") or {}).get("unsafe_secret_count") or 0) == 0
        and int((gate.get("summary") or {}).get("unsafe_claim_count") or 0) == 0
    )
    authority_summary = authority.get("summary", {}) if isinstance(authority.get("summary"), dict) else {}
    all_final_actions_blocked = bool(authority_summary.get("all_final_actions_blocked_without_human"))

    global_runtime_paper = global_runtime["mode"] == "paper" and global_runtime["paper_enabled"]
    global_live_orders_disabled = global_runtime["allow_live_orders"] is False
    execution_status_paper = execution_status["execution_mode"] == "paper" and execution_status["live_arm"].upper() == "OFF"
    account_live_orders_disabled = all(not bool(row.get("allow_live_orders")) for row in account_runtimes)
    all_agents_require_approval = all(row["requires_approval"] and not row["auto_fire"] for row in agent_rows)
    marker_reconciliation_count = sum(1 for row in markers if row["requires_reconciliation"])
    evidence_paths = [
        SPRINT_DIR / "AUTONOMOUS_QUANT_INNOVATION_SAFETY_PROTOCOL_2026-07-09.md",
        SPRINT_DIR / "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        SPRINT_DIR / "HUMAN_ACTION_DOCKET_2026-07-09.md",
        SPRINT_DIR / "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        GLOBAL_RUNTIME_JSON,
        EXECUTION_STATUS_JSON,
        AGENT_MANIFEST,
        *ACCOUNT_RUNTIME_JSONS,
        *RUNTIME_MARKERS,
    ]
    evidence_status = [artifact_status(path) for path in evidence_paths]
    evidence_present = all(row["present"] for row in evidence_status)

    ready = (
        gate_clear
        and all_final_actions_blocked
        and global_runtime_paper
        and global_live_orders_disabled
        and execution_status_paper
        and account_live_orders_disabled
        and all_agents_require_approval
        and evidence_present
    )

    payload = {
        "generated_utc": now_utc(),
        "schema": "autonomous_quant_governance_packet_v1",
        "status": "AUTONOMOUS_QUANT_GOVERNANCE_READY_HUMAN_RUNTIME_REQUIRED"
        if ready
        else "AUTONOMOUS_QUANT_GOVERNANCE_BLOCKED",
        "summary": {
            "reviewer_gate_clear": gate_clear,
            "unsafe_sensitive_count": int((gate.get("summary") or {}).get("unsafe_secret_count") or 0),
            "unsafe_claim_count": int((gate.get("summary") or {}).get("unsafe_claim_count") or 0),
            "all_final_actions_blocked_without_human": all_final_actions_blocked,
            "global_runtime_paper": global_runtime_paper,
            "global_live_orders_disabled": global_live_orders_disabled,
            "execution_status_paper": execution_status_paper,
            "account_runtime_count": len(account_runtimes),
            "account_live_orders_disabled": account_live_orders_disabled,
            "agent_count": len(agent_rows),
            "all_agents_require_approval": all_agents_require_approval,
            "auto_fire_enabled_count": sum(1 for row in agent_rows if row["auto_fire"]),
            "runtime_marker_count": len(markers),
            "runtime_marker_reconciliation_count": marker_reconciliation_count,
            "allowed_mode_count": len(ALLOWED_MODES),
            "evidence_artifact_count": len(evidence_status),
            "missing_evidence_count": sum(1 for row in evidence_status if not row["present"]),
            "data_room_markdown_count": int((manifest.get("summary") or {}).get("manifested_markdown_count") or 0),
            "capital_movement_allowed": False,
            "order_placement_allowed": False,
            "external_system_action_allowed_without_human": False,
            "agency_action_allowed_without_human": False,
        },
        "runtime_snapshot": snapshot,
        "allowed_modes": ALLOWED_MODES,
        "human_gate": {
            "capital_movement_allowed_without_human": False,
            "order_placement_allowed_without_human": False,
            "runtime_escalation_allowed_without_human": False,
            "agency_action_allowed_without_human": False,
            "public_performance_claim_allowed_without_human": False,
            "rule": "Autonomous quant work may build replay and paper-evaluation evidence only; human approval is required before runtime escalation, external action, or any capital-impacting step.",
        },
        "evidence_status": evidence_status,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["autonomous_quant_governance_packet_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    runtime = payload["runtime_snapshot"]
    lines: list[str] = [
        "# Autonomous Quant Governance Packet - 2026-07-09",
        "",
        "Purpose: prove that LumenCore autonomy is currently governed as replay, paper-evaluation, opportunity-monitoring, and proof-factory work.",
        "",
        "This packet does not authorize order placement, capital movement, runtime escalation, agency action, certification, public performance expansion, or external commitments.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_sensitive_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- Global runtime paper: `{str(summary['global_runtime_paper']).lower()}`",
        f"- Global live orders disabled: `{str(summary['global_live_orders_disabled']).lower()}`",
        f"- Execution status paper: `{str(summary['execution_status_paper']).lower()}`",
        f"- Account runtimes: `{summary['account_runtime_count']}`",
        f"- Account live orders disabled: `{str(summary['account_live_orders_disabled']).lower()}`",
        f"- Registered agents: `{summary['agent_count']}`",
        f"- All agents require approval: `{str(summary['all_agents_require_approval']).lower()}`",
        f"- Auto-fire enabled count: `{summary['auto_fire_enabled_count']}`",
        f"- Runtime marker reconciliation count: `{summary['runtime_marker_reconciliation_count']}`",
        f"- Capital movement allowed: `{str(summary['capital_movement_allowed']).lower()}`",
        f"- Order placement allowed: `{str(summary['order_placement_allowed']).lower()}`",
        f"- External system action without human: `{str(summary['external_system_action_allowed_without_human']).lower()}`",
        f"- Agency action without human: `{str(summary['agency_action_allowed_without_human']).lower()}`",
        f"- Packet SHA-256: `{payload['autonomous_quant_governance_packet_sha256']}`",
        "",
        "## Runtime Snapshot",
        "",
        f"- Global runtime path: `{runtime['global_runtime']['path']}`",
        f"- Global runtime mode: `{runtime['global_runtime']['mode']}`",
        f"- Global paper enabled: `{str(runtime['global_runtime']['paper_enabled']).lower()}`",
        f"- Global allow live orders: `{str(runtime['global_runtime']['allow_live_orders']).lower()}`",
        f"- Execution status path: `{runtime['execution_status']['path']}`",
        f"- Execution mode: `{runtime['execution_status']['execution_mode']}`",
        f"- Live arm: `{runtime['execution_status']['live_arm']}`",
        "",
        "## Account Runtime Controls",
        "",
    ]
    for account in runtime["account_runtimes"]:
        lines.append(
            f"- `{account.get('path')}` | account=`{account.get('account_id', '')}` | mode=`{account.get('mode', '')}` | allow_live_orders=`{str(bool(account.get('allow_live_orders'))).lower()}` | paper_enabled=`{str(bool(account.get('paper_enabled'))).lower()}` | x1000_auto_enabled=`{str(bool(account.get('x1000_auto_enabled'))).lower()}` | x1000_auto_apply=`{str(bool(account.get('x1000_auto_apply'))).lower()}`"
        )
    lines.extend(["", "## Runtime Markers", ""])
    for marker in runtime["runtime_markers"]:
        lines.append(
            f"- `{marker['path']}` | present=`{str(marker['present']).lower()}` | value=`{marker['value']}` | requires_reconciliation=`{str(marker['requires_reconciliation']).lower()}`"
        )
    lines.extend(["", "## Agent Approval Registry", ""])
    for agent in runtime["agent_registry"]:
        lines.append(
            f"- `{agent['id']}` | channel=`{agent['channel']}` | auto_fire=`{str(agent['auto_fire']).lower()}` | requires_approval=`{str(agent['requires_approval']).lower()}` | queue=`{agent['queue_source']}`"
        )
    lines.extend(["", "## Allowed Autonomous Modes", ""])
    for mode in payload["allowed_modes"]:
        lines.extend(
            [
                f"### {mode['mode']}",
                "",
                f"- Allowed: {mode['allowed']}",
                f"- Gate: {mode['gate']}",
                "",
            ]
        )
    lines.extend(["## Human Gate", ""])
    for key, value in payload["human_gate"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Evidence Sources", ""])
    for row in payload["evidence_status"]:
        lines.append(
            f"- `{row['path']}` | present=`{str(row['present']).lower()}` | bytes=`{row['bytes']}` | sha256=`{row['sha256']}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(json.dumps({"status": payload["status"], "outputs": payload["outputs"]}, indent=2))
    return 0 if payload["status"].endswith("HUMAN_RUNTIME_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
