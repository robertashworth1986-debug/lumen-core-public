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

PROOF_CARD_PACK_JSON = OUT_OPS / "geometry_proof_card_pack_latest.json"
TOP_REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
CHAMPION_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "reviewer_evidence_gate_latest.json"
DOLLAR_GATE_JSON = OUT_OPS / "dollar_claim_gate_latest.json"
BUYER_OUTREACH_JSON = OUT_OPS / "frozen_delta_buyer_outreach_latest.json"

OUT_JSON = OUT_OPS / "geometry_asset_wiring_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_asset_wiring_board.json"
OUT_MD = DOCS / "GEOMETRY_ASSET_WIRING_BOARD_2026-06-25.md"

BOUNDARY = (
    "Asset wiring only. These rows identify where frozen live-context proof cards can be used for dashboards, "
    "grant evidence, buyer outreach, and next validation. They do not establish field validation, realized savings, "
    "award certainty, live trading permission, or a real-dollar claim."
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


def as_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else str(value).strip().lower() == "true"


def dashboard_targets(card: dict[str, Any]) -> list[str]:
    family_id = str(card.get("family_id", ""))
    lane = str(card.get("lane", ""))
    targets = [
        "dashboard/data/geometry_proof_card_pack.json",
        "dashboard/data/geometry_asset_wiring_board.json",
        "mission_control",
        "grants",
    ]
    if lane in {"wave_resonance_timing", "optimal_curve_transport"}:
        targets.extend(["quant_lab", "forecast", "anomalies"])
    if lane in {"thermal_ventilation", "branching_transport", "bio_network"}:
        targets.extend(["mission_control", "advanced_fleet_validation"])
    if "phase" in family_id or "kuramoto" in family_id:
        targets.extend(["forecast", "anomalies"])
    if "crack" in family_id or "leaf" in family_id:
        targets.extend(["harbor", "vps_proof"])
    return sorted(set(targets))


def grant_targets(card: dict[str, Any]) -> list[str]:
    family_id = str(card.get("family_id", ""))
    lane = str(card.get("lane", ""))
    targets: list[str] = []
    if lane in {"wave_resonance_timing", "optimal_curve_transport"} or "phase" in family_id:
        targets.extend(
            [
                "DARPA/I2O or DICE-style reviewer evidence annex",
                "DoD cyber-physical control and timing resilience concept note",
            ]
        )
    if lane in {"thermal_ventilation"}:
        targets.extend(["DOE grid/data-center cooling resilience proof annex", "ARPA-E/DOE optimization pilot appendix"])
    if lane in {"branching_transport", "bio_network"} or "crack" in family_id or "leaf" in family_id:
        targets.extend(["Navy/DLA HarborSentinel or MissionWeave evidence annex", "Infrastructure inspection validation pilot"])
    if "kraken" in family_id or lane in {"market_data", "quant"}:
        targets.append("Paper-only quant validation appendix; no live execution or trading claim")
    if not targets:
        targets.append("General LumenCore research evidence appendix")
    return sorted(set(targets))


def buyer_segments(card: dict[str, Any], outreach: dict[str, Any]) -> list[str]:
    family_id = str(card.get("family_id", ""))
    lane = str(card.get("lane", ""))
    configured = outreach.get("best_initial_buyer_segments", [])
    segments = [item for item in configured if isinstance(item, str)][:2]
    if lane in {"wave_resonance_timing", "optimal_curve_transport"} or "phase" in family_id:
        segments.append("Defense primes or labs reviewing timing/control evidence packets")
    if lane in {"thermal_ventilation"}:
        segments.append("Grid, data-center, and energy resilience teams")
    if lane in {"branching_transport", "bio_network"} or "crack" in family_id:
        segments.append("Infrastructure, maritime, and inspection analytics teams")
    if not segments:
        segments.append("Validation partners that can independently test frozen evidence packets")
    return sorted(set(segments))


def outreach_position(card: dict[str, Any], outreach: dict[str, Any]) -> dict[str, Any]:
    tier = str(card.get("readiness_tier", ""))
    subject = "Hash-backed frozen evidence packets for live-context infrastructure review"
    body_key = "technical_buyer_short"
    if "triple_source" in tier:
        angle = "Lead with a paid review/pilot of a triple-source candidate; require repeat replay before stronger claims."
    elif "single_run" in tier:
        angle = "Use as a source-expansion/repeat-validation ask, not as a buyer-ready performance win."
    elif "did_not_beat" in tier:
        angle = "Use as negative evidence: the packet shows discipline and redirects toward the actual winner."
        subject = "Reproducible benchmark packet with explicit negative-result boundary"
    elif "proof_value" in tier:
        angle = "Use as a high-value validation target, not as a current live winner."
    else:
        angle = "Use only as a research candidate in a broader validation pilot."

    templates = outreach.get("email_templates", {})
    if isinstance(templates, dict):
        template = templates.get(body_key, {})
        if isinstance(template, dict):
            subject = str(template.get("subject", subject))

    return {
        "safe_angle": angle,
        "suggested_subject": subject,
        "offer": outreach.get("paid_pilot_offer", {}).get("name", "Frozen Delta Evidence Review Pilot"),
        "suggested_ask_usd": outreach.get("paid_pilot_offer", {}).get(
            "suggested_ask_usd", "5,000-15,000 scoped pilot after buyer requirements review"
        ),
        "send_gate": {
            "mass_email_allowed": False,
            "send_without_user_review": False,
            "requires_per_recipient_review": True,
        },
    }


def blockers(card: dict[str, Any], reviewer_gate: dict[str, Any], dollar_gate: dict[str, Any]) -> list[str]:
    tier = str(card.get("readiness_tier", ""))
    out = [
        "No field validation claim yet.",
        "No realized savings or real-dollar claim yet.",
        "No live trading/order execution claim.",
        "Per-recipient outreach review required before any send.",
    ]
    if "triple_source" in tier:
        out.append("Needs repeat frozen run on a second distinct run hash.")
    if "single_run" in tier:
        out.append("Needs either three measured sources or repeat replay.")
    if "did_not_beat" in tier:
        out.append("Candidate did not beat the named baseline; use as negative evidence only.")
    if not as_bool(reviewer_gate.get("ready_for_submission", False)):
        out.append("Reviewer evidence gate is not globally open.")
    if not as_bool(dollar_gate.get("ready_for_real_dollar_claim", False)):
        out.append("Dollar claim gate is closed.")
    return sorted(set(out))


def validation_run(card: dict[str, Any]) -> dict[str, Any]:
    replay = card.get("replay_result", {}) if isinstance(card.get("replay_result"), dict) else {}
    return {
        "top_next_run_rank": card.get("top_next_run_rank"),
        "adapter_status": replay.get("adapter_status", "not_replayed"),
        "candidate_beats_named_baseline": replay.get("candidate_beats_named_baseline"),
        "candidate_score_delta_vs_named_baseline": replay.get("candidate_score_delta_vs_named_baseline"),
        "live_context_rows_evaluated": replay.get("live_context_rows_evaluated", 0),
        "next_steps": card.get("next_validation_steps", [])[:6],
    }


def build_wiring_row(
    card: dict[str, Any],
    outreach: dict[str, Any],
    reviewer_gate: dict[str, Any],
    dollar_gate: dict[str, Any],
) -> dict[str, Any]:
    row = {
        "family_id": card.get("family_id", ""),
        "label": card.get("label", card.get("family_id", "")),
        "lane": card.get("lane", ""),
        "registry_family": bool(card.get("registry_family", False)),
        "proof_asset": card.get("proof_asset", ""),
        "readiness_tier": card.get("readiness_tier", ""),
        "rolling_gate_status": card.get("rolling_gate_status", ""),
        "rolling_gate_repeat_live_win_count": card.get("rolling_gate_repeat_live_win_count", 0),
        "rolling_gate_distinct_run_hash_count": card.get("rolling_gate_distinct_run_hash_count", 0),
        "live_source_count": card.get("live_evidence", {}).get("source_count", 0),
        "dashboard_targets": dashboard_targets(card),
        "grant_targets": grant_targets(card),
        "buyer_segments": buyer_segments(card, outreach),
        "buyer_outreach_position": outreach_position(card, outreach),
        "validation_run": validation_run(card),
        "blockers": blockers(card, reviewer_gate, dollar_gate),
        "allowed_language": card.get("allowed_language", ""),
        "claim_gate": {
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
            "field_validation": False,
            "kraken_live_execution_allowed": False,
        },
    }
    row["row_sha256"] = stable_sha256(row)
    return row


def top_next_actions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(row.get("family_id", "")): row for row in rows}
    actions: list[dict[str, Any]] = []

    def add(priority: int, family_id: str, action: str, reason: str) -> None:
        row = by_id.get(family_id, {})
        actions.append(
            {
                "priority": priority,
                "family_id": family_id,
                "action": action,
                "reason": reason,
                "target_dashboards": row.get("dashboard_targets", []),
            }
        )

    if "brachistochrone_descent" in by_id:
        add(
            1,
            "brachistochrone_descent",
            "Repeat against a second frozen live-source run hash with the same named baselines.",
            "It currently has a triple-source candidate win and is the strongest next proof run.",
        )
    if "kuramoto_phase_coupling" in by_id:
        add(
            2,
            "kuramoto_phase_coupling",
            "Repeat against a second frozen live-source run hash and report phase/RMSE deltas.",
            "It directly supports timing, phase-lock, and oscillatory control narratives.",
        )
    if "thermal_plume_convection" in by_id:
        add(
            3,
            "thermal_plume_convection",
            "Expand to three measured sources or repeat on a second frozen run before any buyer claim.",
            "It is currently single-run evidence, useful for energy/cooling pilots only after repeat/source expansion.",
        )
    if "phase_locked_residual_corrector" in by_id:
        add(
            4,
            "phase_locked_residual_corrector",
            "Promote from annex into the formal geometry registry or build its replay adapter.",
            "It has rolling-gate candidate evidence but is outside the registry card family.",
        )
    if "leaf_veins" in by_id and "crack_propagation_paths" in by_id:
        add(
            5,
            "crack_propagation_paths",
            "Reroute branching/infrastructure validation away from leaf-vein claims and toward crack propagation paths.",
            "Leaf veins did not beat the named baseline; crack paths are the higher proof-value target.",
        )
    return sorted(actions, key=lambda item: item["priority"])


def build_payload() -> dict[str, Any]:
    proof_pack = read_json(PROOF_CARD_PACK_JSON)
    replay = read_json(TOP_REPLAY_JSON)
    champion = read_json(CHAMPION_JSON)
    reviewer_gate = read_json(REVIEWER_GATE_JSON)
    dollar_gate = read_json(DOLLAR_GATE_JSON)
    outreach = read_json(BUYER_OUTREACH_JSON)

    cards = [item for item in proof_pack.get("proof_cards", []) if isinstance(item, dict)]
    rows = [build_wiring_row(card, outreach, reviewer_gate, dollar_gate) for card in cards]

    all_dashboard_targets = sorted({target for row in rows for target in row["dashboard_targets"]})
    all_grant_targets = sorted({target for row in rows for target in row["grant_targets"]})
    all_segments = sorted({segment for row in rows for segment in row["buyer_segments"]})
    triple_source_count = sum(1 for row in rows if "triple_source" in str(row.get("readiness_tier", "")))
    single_run_count = sum(1 for row in rows if "single_run" in str(row.get("readiness_tier", "")))

    gates = {
        "ready_for_live_geometry_claim": False,
        "ready_for_real_dollar_claim": False,
        "field_validation": False,
        "kraken_live_execution_allowed": False,
        "mass_email_allowed": False,
        "send_without_user_review": False,
    }
    summary = {
        "proof_card_count": len(rows),
        "triple_source_candidate_count": triple_source_count,
        "single_run_candidate_count": single_run_count,
        "dashboard_feed_count": len(all_dashboard_targets),
        "grant_packet_feed_count": len(all_grant_targets),
        "outreach_feed_count": len(all_segments),
        "validation_run_count": sum(1 for row in rows if row["validation_run"]["next_steps"]),
        "candidate_win_count": sum(
            1 for row in rows if row["validation_run"].get("candidate_beats_named_baseline") is True
        ),
        **gates,
        "board_chain_sha256": stable_sha256(rows),
    }

    return {
        "schema": "geometry_asset_wiring_board_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "geometry_proof_card_pack": str(PROOF_CARD_PACK_JSON.relative_to(ROOT)),
            "top_geometry_live_replay_results": str(TOP_REPLAY_JSON.relative_to(ROOT)),
            "geometry_champion_of_champions": str(CHAMPION_JSON.relative_to(ROOT)),
            "reviewer_evidence_gate": str(REVIEWER_GATE_JSON.relative_to(ROOT)),
            "dollar_claim_gate": str(DOLLAR_GATE_JSON.relative_to(ROOT)),
            "frozen_delta_buyer_outreach": str(BUYER_OUTREACH_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "source_summaries": {
            "proof_card_pack_summary": proof_pack.get("summary", {}),
            "top_replay_summary": replay.get("summary", {}),
            "champion_summary": champion.get("summary", {}),
            "buyer_outreach_current_truth": outreach.get("current_truth", {}),
        },
        "summary": summary,
        "dashboard_targets": all_dashboard_targets,
        "grant_targets": all_grant_targets,
        "buyer_segments": all_segments,
        "send_gate": {
            "mass_email_allowed": False,
            "send_without_user_review": False,
            "recommended_daily_limit": "5-10 highly targeted messages after manual recipient review",
            "requires_per_recipient_review": True,
        },
        "top_next_actions": top_next_actions(rows),
        "wiring_rows": rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Asset Wiring Board",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Proof cards wired: `{summary['proof_card_count']}`",
        f"- Triple-source candidates: `{summary['triple_source_candidate_count']}`",
        f"- Single-run candidates: `{summary['single_run_candidate_count']}`",
        f"- Candidate wins against named baseline: `{summary['candidate_win_count']}`",
        f"- Dashboard feeds/targets: `{summary['dashboard_feed_count']}`",
        f"- Grant packet targets: `{summary['grant_packet_feed_count']}`",
        f"- Buyer/outreach segment count: `{summary['outreach_feed_count']}`",
        f"- Validation run rows: `{summary['validation_run_count']}`",
        f"- Ready for live geometry claim: `{str(summary['ready_for_live_geometry_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Field validation: `{str(summary['field_validation']).lower()}`",
        f"- Mass email allowed: `{str(summary['mass_email_allowed']).lower()}`",
        f"- Board chain SHA-256: `{summary['board_chain_sha256']}`",
        "",
        "## Top Next Actions",
        "",
    ]
    for action in payload["top_next_actions"]:
        lines.append(
            f"{action['priority']}. `{action['family_id']}` - {action['action']} Reason: {action['reason']}"
        )

    lines.extend(
        [
            "",
            "## Wiring Rows",
            "",
            "| Family | Lane | Tier | Dashboards | Grant/Buyer Position | Next Validation |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload["wiring_rows"]:
        dashboards = ", ".join(row["dashboard_targets"][:4])
        grants = "; ".join(row["grant_targets"][:2])
        buyer = row["buyer_outreach_position"]["safe_angle"]
        next_step = row["validation_run"]["next_steps"][0] if row["validation_run"]["next_steps"] else "No next step set."
        lines.append(
            f"| `{row['family_id']}` | `{row['lane']}` | `{row['readiness_tier']}` | {dashboards} | {grants}. {buyer} | {next_step} |"
        )

    lines.extend(
        [
            "",
            "## Send Gate",
            "",
            "- Do not mass email.",
            "- Do not send without manual recipient review.",
            "- Do not say a packet is worth a fixed dollar amount as fact.",
            "- Do not claim field validation, realized savings, grant award certainty, or trading profit.",
            "- Use outreach to ask for a paid evidence review or validation pilot.",
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
