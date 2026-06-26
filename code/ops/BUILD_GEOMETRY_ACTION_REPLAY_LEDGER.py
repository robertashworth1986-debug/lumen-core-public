from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ACTION_REPLAYS = ROOT / "out" / "action_replays"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

ACTION_BOARD_JSON = OUT_OPS / "geometry_execution_action_board_latest.json"
OUT_JSON = OUT_OPS / "geometry_action_replay_ledger_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_action_replay_ledger.json"
OUT_MD = DOCS / "GEOMETRY_ACTION_REPLAY_LEDGER_2026-06-25.md"

BOUNDARY = (
    "Action replay ledger only. These are local generated benchmark replays tied to frozen action-board commands. "
    "They are proof-building evidence, not field validation, medical validation, safety certification, trading signal, "
    "fixed-dollar frozen-delta value, or realized-savings evidence."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def action_by_lane(action_board: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for action in as_list(action_board.get("all_actions")):
        if not isinstance(action, dict):
            continue
        lane = str(action.get("lane", "")).strip()
        if lane:
            out.setdefault(lane, []).append(action)
    return out


def manifest_hash(run_dir: Path) -> str:
    manifest = run_dir / "manifest.sha256.json"
    if manifest.exists():
        return stable_sha256(read_json(manifest))
    return ""


def result_row(latest_path: Path, actions_by_lane: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    payload = read_json(latest_path)
    gate = as_dict(payload.get("promotion_gate"))
    best_geometry = as_dict(gate.get("best_geometry"))
    best_baseline = as_dict(gate.get("best_baseline"))
    lane = str(payload.get("lane", latest_path.parent.name))
    generated_utc = str(payload.get("generated_utc", ""))
    scenario_count = as_dict(payload.get("validation")).get("scenario_count", 0)
    out_dir = Path(str(payload.get("out_dir", latest_path.parent))).resolve()
    if not out_dir.exists() and not str(payload.get("out_dir", "")).startswith(str(ROOT)):
        out_dir = ROOT / str(payload.get("out_dir", latest_path.parent))

    row = {
        "lane": lane,
        "latest_json": rel(latest_path),
        "run_dir": rel(out_dir),
        "generated_utc": generated_utc,
        "scenario_count": scenario_count,
        "best_geometry": best_geometry.get("family_id", ""),
        "best_baseline": best_baseline.get("family_id", ""),
        "gate": gate.get("gate", ""),
        "score_delta_vs_best_baseline": gate.get("score_delta_vs_best_baseline"),
        "claim_language": gate.get("claim_language", ""),
        "evidence_boundary": payload.get("evidence_boundary", ""),
        "leaderboard_top3": as_list(as_dict(payload.get("validation")).get("leaderboard"))[:3],
        "linked_action_family_ids": [
            str(action.get("family_id", ""))
            for action in actions_by_lane.get(lane, [])
            if str(action.get("family_id", "")).strip()
        ],
        "claim_gates": {
            "generated_benchmark_result": True,
            "field_validation_claim_allowed": False,
            "medical_validation_claim_allowed": False,
            "safety_certification_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
        },
        "manifest_hash": manifest_hash(out_dir),
    }
    row["row_sha256"] = stable_sha256(row)
    return row


def build_payload() -> dict[str, Any]:
    action_board = read_json(ACTION_BOARD_JSON)
    actions_by_lane = action_by_lane(action_board)
    rows = []
    for latest in sorted(ACTION_REPLAYS.glob("*/latest.json")):
        row = result_row(latest, actions_by_lane)
        if row["best_geometry"]:
            rows.append(row)

    rows = sorted(rows, key=lambda item: float(item.get("score_delta_vs_best_baseline") or 0), reverse=True)
    positive = [row for row in rows if str(row.get("gate")) == "candidate_geometry_beats_best_baseline"]
    total_scenarios = sum(int(row.get("scenario_count") or 0) for row in rows)
    best = rows[0] if rows else {}

    summary = {
        "lane_count": len(rows),
        "positive_gate_count": len(positive),
        "total_validation_scenarios": total_scenarios,
        "best_current_family": best.get("best_geometry", ""),
        "best_current_lane": best.get("lane", ""),
        "best_current_score_delta": best.get("score_delta_vs_best_baseline"),
        "field_validation_claim_allowed": False,
        "medical_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "ledger_chain_sha256": stable_sha256(rows),
    }
    return {
        "schema": "geometry_action_replay_ledger_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "action_board": rel(ACTION_BOARD_JSON),
            "action_replay_root": rel(ACTION_REPLAYS),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
        "summary": summary,
        "replay_rows": rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Action Replay Ledger",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Replay lanes: `{summary['lane_count']}`",
        f"- Positive gates: `{summary['positive_gate_count']}`",
        f"- Total validation scenarios: `{summary['total_validation_scenarios']}`",
        f"- Best current family: `{summary['best_current_family']}`",
        f"- Best current lane: `{summary['best_current_lane']}`",
        f"- Best current score delta: `{summary['best_current_score_delta']}`",
        f"- Field validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Medical validation claim allowed: `{str(summary['medical_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
        f"- Live trading/autonomous execution allowed: `{str(summary['live_trading_or_autonomous_execution_allowed']).lower()}`",
        f"- Ledger chain SHA-256: `{summary['ledger_chain_sha256']}`",
        "",
        "## Replay Rows",
        "",
        "| Lane | Best Geometry | Best Baseline | Gate | Score Delta | Scenarios |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["replay_rows"]:
        lines.append(
            f"| `{row['lane']}` | `{row['best_geometry']}` | `{row['best_baseline']}` | "
            f"`{row['gate']}` | `{row['score_delta_vs_best_baseline']}` | `{row['scenario_count']}` |"
        )

    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- These results are useful for grant appendices and pilot-scoping evidence.",
            "- They are not medical, addiction-treatment, field, safety, trading, or real-dollar proof.",
            "- Any haptic or neuro-adjacent concept must be handled as a clinician-reviewed wellness or research device, not as a promise to create drug-like effects.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
