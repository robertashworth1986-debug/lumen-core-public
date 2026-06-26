from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

ASSET_BOARD_JSON = OUT_OPS / "geometry_asset_wiring_board_latest.json"
CHAMPION_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
PROOF_TO_PILOT_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"
TRUTH_SWEEP_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"

OUT_JSON = OUT_OPS / "geometry_execution_action_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_execution_action_board.json"
OUT_MD = DOCS / "GEOMETRY_EXECUTION_ACTION_BOARD_2026-06-25.md"

BOUNDARY = (
    "Execution action board only. It converts the current frozen proof/champion state into local benchmark, "
    "grant, dashboard, and pilot-scoping actions. It does not authorize live trading, mass email, field-validation "
    "claims, fixed-dollar frozen-delta sales claims, realized savings claims, or grant-award certainty."
)

RUNNER_BY_LANE: dict[str, dict[str, str]] = {
    "optimal_curve_transport": {
        "script": "code/geometry_optimal_curve_transport_benchmark.py",
        "command": (
            "python code\\geometry_optimal_curve_transport_benchmark.py "
            "--out-root out\\action_replays\\optimal_curve_transport "
            "--run-tag NEXT_HOLDOUT --development-scenarios 8 --validation-scenarios 20"
        ),
        "side_effects": "Writes local synthetic/controlled replay artifacts under out/action_replays.",
    },
    "wave_resonance_timing": {
        "script": "code/geometry_wave_resonance_timing_benchmark.py",
        "command": (
            "python code\\geometry_wave_resonance_timing_benchmark.py "
            "--out-root out\\action_replays\\wave_resonance_timing "
            "--run-tag NEXT_HOLDOUT --development-scenarios 8 --validation-scenarios 20"
        ),
        "side_effects": "Writes local synthetic/controlled replay artifacts under out/action_replays.",
    },
    "thermal_ventilation": {
        "script": "code/geometry_thermal_ventilation_benchmark.py",
        "command": (
            "python code\\geometry_thermal_ventilation_benchmark.py "
            "--out-root out\\action_replays\\thermal_ventilation "
            "--run-tag NEXT_HOLDOUT --development-scenarios 8 --validation-scenarios 20"
        ),
        "side_effects": "Writes local synthetic/controlled replay artifacts under out/action_replays.",
    },
    "branching_transport": {
        "script": "code/geometry_branching_transport_benchmark.py",
        "command": (
            "python code\\geometry_branching_transport_benchmark.py "
            "--out-root out\\action_replays\\branching_transport "
            "--run-tag NEXT_HOLDOUT --development-scenarios 8 --validation-scenarios 20"
        ),
        "side_effects": "Writes local synthetic/controlled replay artifacts under out/action_replays.",
    },
    "energy_price_pressure_proxy": {
        "script": "code/ops/BUILD_ENERGY_PRICE_PRESSURE_FORECAST.py",
        "command": "python code\\ops\\BUILD_ENERGY_PRICE_PRESSURE_FORECAST.py",
        "side_effects": "Refreshes local energy price pressure proof and dashboard feeds only.",
    },
}

STANDARD_BLOCKERS = [
    "No field validation claim until buyer/agency-authorized operational data is replayed against accepted incumbents.",
    "No realized-savings or real-dollar claim until buyer-approved economics and traceable results exist.",
    "No fixed-dollar frozen-delta sale claim.",
    "No live trading/order execution claim.",
    "No bulk email or automated outreach.",
]


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


def as_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else str(value).strip().lower() == "true"


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def rows_from(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [row for row in as_list(payload.get(key)) if isinstance(row, dict)]


def by_family(rows: list[dict[str, Any]], key: str = "family_id") -> dict[str, dict[str, Any]]:
    return {str(row.get(key, "")).strip(): row for row in rows if str(row.get(key, "")).strip()}


def current_claim_gates(truth: dict[str, Any]) -> dict[str, bool]:
    gates = as_dict(truth.get("gates"))
    return {
        "bounded_estimated_value_claim_allowed": as_bool(gates.get("bounded_estimated_value_claim_allowed")),
        "paid_pilot_scoping_allowed": as_bool(gates.get("paid_pilot_scoping_allowed")),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "mass_email_allowed": False,
        "send_without_user_review": False,
        "vps_domain_live_dashboard_routed": as_bool(gates.get("vps_domain_live_dashboard_routed")),
        "glyph_or_external_vault_routed": as_bool(gates.get("glyph_or_external_vault_routed")),
    }


def action_type(row: dict[str, Any]) -> str:
    family_id = str(row.get("family_id", ""))
    rolling = str(row.get("rolling_gate_status", ""))
    evidence = str(row.get("evidence_status", ""))
    robust = as_bool(row.get("robust_repeat_uncertainty_gate_passed"))
    paid = as_bool(row.get("paid_pilot_ready"))

    if family_id == "phase_locked_residual_corrector":
        return "register_money_proxy_adapter"
    if rolling == "rolling_champion" and robust and paid:
        return "buyer_authorized_pilot_and_publication"
    if rolling == "rolling_champion":
        return "additional_holdout_replay"
    if rolling == "triple_source_candidate":
        return "repeat_frozen_replay"
    if evidence.startswith("proof_value") or rolling == "not_in_rolling_gate":
        return "build_live_adapter_or_reroute"
    return "benchmark_gap_review"


def success_metric(row: dict[str, Any], action: str) -> str:
    family_id = str(row.get("family_id", ""))
    if action == "buyer_authorized_pilot_and_publication":
        return (
            "Buyer/agency accepts a pre-registered pilot plan, provides or authorizes field data, "
            "and the candidate beats accepted incumbents under identical constraints with signed or traceable artifacts."
        )
    if action == "additional_holdout_replay":
        return (
            "At least 20 pre-registered holdout windows are frozen, replayed, and promoted only if the uncertainty gate "
            "passes under identical baseline/candidate constraints."
        )
    if action == "repeat_frozen_replay":
        return "A second distinct frozen run hash beats the named baseline across the required measured-source set."
    if action == "register_money_proxy_adapter":
        return (
            "The proxy is represented in the formal registry/replay adapter chain and remains bounded until buyer economics "
            "and field outcomes are accepted."
        )
    if family_id:
        return f"`{family_id}` receives a live adapter or is explicitly demoted behind the current winner."
    return "Candidate is reviewed and either assigned a runnable adapter or archived as unsupported."


def blocked_until(row: dict[str, Any], action: str) -> list[str]:
    blockers = list(STANDARD_BLOCKERS)
    row_blockers = [str(item) for item in as_list(row.get("blockers")) if str(item).strip()]
    blockers.extend(row_blockers[:6])
    if action in {"additional_holdout_replay", "repeat_frozen_replay"}:
        blockers.append("Needs more frozen live-context replay before stronger claim language.")
    if action == "build_live_adapter_or_reroute":
        blockers.append("Needs a concrete live adapter or explicit reroute to the current proven champion.")
    if action == "register_money_proxy_adapter":
        blockers.append("Needs formal adapter/registry status before it can sit beside geometry champions.")
    return sorted(set(blockers))


def runner_for(row: dict[str, Any], action: str) -> dict[str, Any]:
    lane = str(row.get("lane", ""))
    runner = RUNNER_BY_LANE.get(lane)
    if not runner:
        return {
            "runner_available": False,
            "safe_local_command": None,
            "script": None,
            "side_effects": "No runner mapped yet; build or select an adapter before replay.",
            "safe_to_run_without_human_review": False,
        }

    safe_without_review = action not in {"buyer_authorized_pilot_and_publication"}
    return {
        "runner_available": True,
        "safe_local_command": runner["command"],
        "script": runner["script"],
        "side_effects": runner["side_effects"],
        "safe_to_run_without_human_review": safe_without_review,
    }


def merge_queue_and_wired(asset_board: dict[str, Any]) -> list[dict[str, Any]]:
    wired = by_family(rows_from(asset_board, "wiring_rows"))
    queue = rows_from(asset_board, "high_value_wiring_queue")
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in queue:
        family_id = str(item.get("family_id", "")).strip()
        if not family_id:
            continue
        base = dict(item)
        base.update(wired.get(family_id, {}))
        base.setdefault("rank", item.get("rank"))
        base.setdefault("family_id", family_id)
        base.setdefault("lane", item.get("lane", ""))
        base.setdefault("label", item.get("label", family_id))
        merged.append(base)
        seen.add(family_id)

    for family_id, row in wired.items():
        if family_id not in seen:
            merged.append(dict(row))

    return merged


def build_action(row: dict[str, Any], claim_gates: dict[str, bool], priority: int) -> dict[str, Any]:
    action = action_type(row)
    runner = runner_for(row, action)
    dashboard_targets = [str(item) for item in as_list(row.get("dashboard_targets"))]
    grant_targets = [str(item) for item in as_list(row.get("grant_targets"))]
    next_wire = str(row.get("next_wire") or row.get("next_high_value_step") or "")
    payload = {
        "priority": priority,
        "family_id": str(row.get("family_id", "")),
        "label": str(row.get("label", row.get("family_id", ""))),
        "lane": str(row.get("lane", "")),
        "rank": row.get("rank"),
        "asset_score": row.get("asset_score"),
        "evidence_status": str(row.get("evidence_status", "")),
        "claim_stage": str(row.get("claim_stage", "")),
        "rolling_gate_status": str(row.get("rolling_gate_status", "")),
        "readiness_tier": str(row.get("readiness_tier", "")),
        "robust_repeat_uncertainty_gate_passed": as_bool(row.get("robust_repeat_uncertainty_gate_passed")),
        "paid_pilot_ready": as_bool(row.get("paid_pilot_ready")),
        "live_source_count": row.get("live_source_count", row.get("rolling_source_count", 0)),
        "next_action_type": action,
        "next_wire": next_wire,
        "success_metric": success_metric(row, action),
        "runner": runner,
        "proof_inputs": {
            "asset_board": str(ASSET_BOARD_JSON.relative_to(ROOT)),
            "champion_board": str(CHAMPION_JSON.relative_to(ROOT)),
            "proof_to_pilot": str(PROOF_TO_PILOT_JSON.relative_to(ROOT)),
            "truth_sweep": str(TRUTH_SWEEP_JSON.relative_to(ROOT)),
        },
        "dashboard_targets": sorted(set(dashboard_targets + ["dashboard/data/geometry_execution_action_board.json"])),
        "grant_targets": grant_targets,
        "manual_only_actions": [
            "review recipient and use case before outreach",
            "ask for buyer-authorized holdout data or a paid technical evaluation",
            "do not send bulk messages",
        ],
        "claim_gates": claim_gates,
        "blocked_until": blocked_until(row, action),
        "publication_gate": {
            "local_dashboard_feed_ready": True,
            "vps_domain_publication_gate_open": False,
            "required_before_public_claim": [
                "copy dashboard/data/geometry_execution_action_board.json to the live domain",
                "record public URL, retrieval timestamp, and SHA-256 hash",
                "verify the live domain renders the same current claim gates",
            ],
        },
    }
    payload["action_sha256"] = stable_sha256(payload)
    return payload


def build_payload() -> dict[str, Any]:
    asset_board = read_json(ASSET_BOARD_JSON)
    champion = read_json(CHAMPION_JSON)
    proof_to_pilot = read_json(PROOF_TO_PILOT_JSON)
    truth = read_json(TRUTH_SWEEP_JSON)
    claim_gates = current_claim_gates(truth)

    rows = merge_queue_and_wired(asset_board)
    actions = [build_action(row, claim_gates, index + 1) for index, row in enumerate(rows)]
    runnable = [item for item in actions if as_dict(item.get("runner")).get("runner_available")]
    adapter_gap = [item for item in actions if not as_dict(item.get("runner")).get("runner_available")]
    robust = [item for item in actions if item.get("robust_repeat_uncertainty_gate_passed")]
    rolling = [item for item in actions if item.get("rolling_gate_status") == "rolling_champion"]

    truth_summary = as_dict(truth.get("summary"))
    champion_summary = as_dict(champion.get("summary"))
    pilot_cards = rows_from(proof_to_pilot, "top_cards")

    summary = {
        "action_count": len(actions),
        "runnable_local_action_count": len(runnable),
        "adapter_gap_action_count": len(adapter_gap),
        "rolling_champion_action_count": len(rolling),
        "robust_repeat_action_count": len(robust),
        "paid_pilot_card_count": len(pilot_cards),
        "registered_family_count": truth_summary.get("registered_family_count", champion_summary.get("family_count", 0)),
        "benchmark_specified_family_count": truth_summary.get(
            "benchmark_specified_family_count", champion_summary.get("benchmark_specified_family_count", 0)
        ),
        "measured_sources": truth_summary.get("measured_sources", champion_summary.get("live_measured_sources", 0)),
        "measured_rows": truth_summary.get("total_measured_rows", champion_summary.get("live_total_measured_rows", 0)),
        "safe_estimated_hourly_value_usd": truth_summary.get("safe_estimated_hourly_value_usd", 0),
        "safe_estimated_annual_value_usd": truth_summary.get("safe_estimated_annual_value_usd", 0),
        "blocked_context_annual_value_usd": truth_summary.get("blocked_context_annual_value_usd", 0),
        **claim_gates,
        "board_chain_sha256": stable_sha256(actions),
    }

    return {
        "schema": "geometry_execution_action_board_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "geometry_asset_wiring_board": str(ASSET_BOARD_JSON.relative_to(ROOT)),
            "geometry_champion_of_champions": str(CHAMPION_JSON.relative_to(ROOT)),
            "proof_to_pilot_control_room": str(PROOF_TO_PILOT_JSON.relative_to(ROOT)),
            "field_money_truth_sweep": str(TRUTH_SWEEP_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "summary": summary,
        "context_checkpoint": {
            "read_first_next_pass": [
                "docs/CURRENT_LUMA_PROOF_STATE_2026-06-25.md",
                "docs/GEOMETRY_EXECUTION_ACTION_BOARD_2026-06-25.md",
                "out/ops/geometry_execution_action_board_latest.json",
            ],
            "current_strongest_candidate": "brachistochrone_descent",
            "current_money_proxy": "phase_locked_residual_corrector",
            "do_not_overclaim": STANDARD_BLOCKERS,
        },
        "top_actions": actions[:20],
        "all_actions": actions,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Execution Action Board",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## State",
        "",
        f"- Actions: `{summary['action_count']}`",
        f"- Runnable local actions: `{summary['runnable_local_action_count']}`",
        f"- Adapter gaps: `{summary['adapter_gap_action_count']}`",
        f"- Rolling champion actions: `{summary['rolling_champion_action_count']}`",
        f"- Robust repeat actions: `{summary['robust_repeat_action_count']}`",
        f"- Registered families: `{summary['registered_family_count']}`",
        f"- Benchmark-specified families: `{summary['benchmark_specified_family_count']}`",
        f"- Measured sources: `{summary['measured_sources']}`",
        f"- Measured rows: `{summary['measured_rows']}`",
        f"- Bounded estimated value claim allowed: `{str(summary['bounded_estimated_value_claim_allowed']).lower()}`",
        f"- Paid pilot scoping allowed: `{str(summary['paid_pilot_scoping_allowed']).lower()}`",
        f"- Field validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
        f"- Fixed-dollar frozen-delta sale claim allowed: `{str(summary['fixed_dollar_delta_sale_claim_allowed']).lower()}`",
        f"- Live trading/autonomous execution allowed: `{str(summary['live_trading_or_autonomous_execution_allowed']).lower()}`",
        f"- VPS/domain live dashboard routed: `{str(summary['vps_domain_live_dashboard_routed']).lower()}`",
        f"- Board chain SHA-256: `{summary['board_chain_sha256']}`",
        "",
        "## Top Actions",
        "",
        "| Priority | Family | Action Type | Runner | Success Metric |",
        "| --- | --- | --- | --- | --- |",
    ]

    for action in payload["top_actions"]:
        runner = as_dict(action.get("runner"))
        command = runner.get("safe_local_command") or "adapter required"
        lines.append(
            f"| {action['priority']} | `{action['family_id']}` | `{action['next_action_type']}` | "
            f"`{command}` | {action['success_metric']} |"
        )

    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- No field validation claim.",
            "- No realized-savings or real-dollar claim.",
            "- No fixed-dollar frozen-delta sale claim.",
            "- No live trading, order placement, or autonomous execution claim.",
            "- No mass email or automated outreach.",
            "- Use the current evidence for bounded grant appendices, dashboard transparency, and manually reviewed pilot scoping.",
            "",
            "## Next-Pass Context",
            "",
            "Read these first before changing direction:",
        ]
    )
    for item in payload["context_checkpoint"]["read_first_next_pass"]:
        lines.append(f"- `{item}`")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
