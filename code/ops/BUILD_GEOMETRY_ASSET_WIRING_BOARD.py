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
PROOF_TO_PILOT_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"
TRUTH_SWEEP_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"
CLAIM_MAP_JSON = OUT_OPS / "claim_strength_value_unlock_map_latest.json"

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


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def rows_from(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return [row for row in as_list(payload.get(key)) if isinstance(row, dict)]


def index_by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row.get(key, "")).strip(): row for row in rows if str(row.get(key, "")).strip()}


def current_truth_gates(truth: dict[str, Any]) -> dict[str, Any]:
    gates = as_dict(truth.get("gates"))
    return {
        "bounded_estimated_value_claim_allowed": as_bool(gates.get("bounded_estimated_value_claim_allowed")),
        "paid_pilot_scoping_allowed": as_bool(gates.get("paid_pilot_scoping_allowed")),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "vps_domain_live_dashboard_routed": as_bool(gates.get("vps_domain_live_dashboard_routed")),
        "glyph_or_external_vault_routed": as_bool(gates.get("glyph_or_external_vault_routed")),
    }


def champion_by_family(champion: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = rows_from(champion, "family_asset_rankings")
    return {str(row.get("family", "")).strip(): row for row in rows if str(row.get("family", "")).strip()}


def pilot_by_family(proof_to_pilot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return index_by(rows_from(proof_to_pilot, "top_cards"), "family_id")


def overlay_tier(card: dict[str, Any], champion_row: dict[str, Any], pilot_card: dict[str, Any]) -> str:
    rolling = str(champion_row.get("rolling_gate_status") or card.get("rolling_gate_status", ""))
    robust = as_bool(champion_row.get("robust_repeat_uncertainty_gate_passed"))
    paid_pilot = bool(pilot_card) or as_bool(champion_row.get("paid_pilot_ready"))
    if rolling == "rolling_champion" and robust and paid_pilot:
        return "rolling_champion_robust_repeat_pilot_ready"
    if rolling == "rolling_champion":
        return "rolling_champion_needs_field_authorized_holdouts"
    if rolling == "triple_source_candidate":
        return "triple_source_candidate_needs_repeat"
    if rolling == "single_run_candidate":
        return "single_run_candidate_needs_more_sources_or_repeat"
    return str(card.get("readiness_tier", "research_candidate_needs_replay"))


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


def outreach_position(card: dict[str, Any], outreach: dict[str, Any], tier_override: str = "") -> dict[str, Any]:
    tier = tier_override or str(card.get("readiness_tier", ""))
    subject = "Hash-backed frozen evidence packets for live-context infrastructure review"
    body_key = "technical_buyer_short"
    if "robust_repeat_pilot_ready" in tier:
        angle = "Lead with a paid buyer-authorized pilot scoping ask; this is repeat-window evidence, not field validation."
    elif "rolling_champion" in tier:
        angle = "Lead with repeat live-context champion evidence; require buyer-authorized holdouts before stronger claims."
    elif "triple_source" in tier:
        angle = "Lead with a repeat-validation ask for a triple-source candidate; require another run before stronger claims."
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


def blockers(
    card: dict[str, Any],
    reviewer_gate: dict[str, Any],
    dollar_gate: dict[str, Any],
    champion_row: dict[str, Any] | None = None,
    pilot_card: dict[str, Any] | None = None,
    tier_override: str = "",
) -> list[str]:
    champion_row = champion_row or {}
    pilot_card = pilot_card or {}
    tier = tier_override or str(card.get("readiness_tier", ""))
    out = [
        "No field validation claim yet.",
        "No realized savings or real-dollar claim yet.",
        "No live trading/order execution claim.",
        "Per-recipient outreach review required before any send.",
    ]
    if "robust_repeat_pilot_ready" in tier:
        out.extend(
            [
                "Needs buyer or agency authorized field data.",
                "Needs pre-registered holdout windows and accepted incumbent baselines.",
                "Needs buyer-approved economic conversion factors before dollar savings language.",
            ]
        )
    elif "rolling_champion" in tier:
        out.extend(
            [
                "Needs more holdout windows or stronger uncertainty gate before field-validation language.",
                "Needs buyer or agency authorized operational data.",
            ]
        )
        source_count = int(champion_row.get("rolling_source_count") or as_dict(card.get("live_evidence")).get("source_count") or 0)
        if source_count < 3:
            out.append("Needs at least three measured source types or a buyer-authorized field source before hardware-energy claims.")
    elif "triple_source" in tier:
        out.append("Needs repeat frozen run on another distinct run hash.")
    if "single_run" in tier:
        out.append("Needs either three measured sources or repeat replay.")
    if "did_not_beat" in tier:
        out.append("Candidate did not beat the named baseline; use as negative evidence only.")
    if pilot_card and not as_bool(as_dict(pilot_card.get("claim_gate")).get("field_validation_claim_allowed")):
        out.append("Pilot card allows scoping only; field-validation claim remains closed.")
    if as_bool(champion_row.get("paid_pilot_ready")) and not pilot_card:
        out.append("Champion row references pilot readiness but no pilot card was attached.")
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
    champion_row: dict[str, Any] | None = None,
    pilot_card: dict[str, Any] | None = None,
) -> dict[str, Any]:
    champion_row = champion_row or {}
    pilot_card = pilot_card or {}
    tier = overlay_tier(card, champion_row, pilot_card)
    live_evidence = as_dict(card.get("live_evidence"))
    repeat_evidence = as_dict(pilot_card.get("repeat_window_evidence"))
    if "robust_repeat_pilot_ready" in tier:
        next_high_value_step = "Ask for buyer-authorized field data and pre-register holdout windows for a paid pilot."
    elif "rolling_champion" in tier:
        next_high_value_step = "Run additional holdout windows and close the uncertainty/field-data gap."
    else:
        next_steps = validation_run(card)["next_steps"]
        next_high_value_step = next_steps[0] if next_steps else "Schedule the next bounded replay or adapter build."
    row = {
        "family_id": card.get("family_id", ""),
        "label": card.get("label", card.get("family_id", "")),
        "lane": card.get("lane", ""),
        "registry_family": bool(card.get("registry_family", False)),
        "proof_asset": card.get("proof_asset", ""),
        "readiness_tier": tier,
        "asset_score": champion_row.get("asset_score"),
        "evidence_status": champion_row.get("evidence_status", ""),
        "claim_stage": champion_row.get("claim_stage", ""),
        "rolling_gate_status": champion_row.get("rolling_gate_status", card.get("rolling_gate_status", "")),
        "rolling_gate_repeat_live_win_count": champion_row.get(
            "rolling_gate_repeat_live_win_count", card.get("rolling_gate_repeat_live_win_count", 0)
        ),
        "rolling_gate_distinct_run_hash_count": champion_row.get(
            "rolling_gate_distinct_run_hash_count", card.get("rolling_gate_distinct_run_hash_count", 0)
        ),
        "robust_repeat_uncertainty_gate_passed": as_bool(champion_row.get("robust_repeat_uncertainty_gate_passed")),
        "repeat_window_evidence": repeat_evidence,
        "paid_pilot_ready": bool(pilot_card) or as_bool(champion_row.get("paid_pilot_ready")),
        "pilot_name": pilot_card.get("pilot_name", champion_row.get("pilot_name", "")),
        "pilot_next_actions": pilot_card.get("next_actions", []),
        "unlock_conditions": champion_row.get("unlock_conditions", pilot_card.get("unlock_conditions", [])),
        "live_source_count": champion_row.get("rolling_source_count", live_evidence.get("source_count", 0)),
        "live_sources": champion_row.get("rolling_sources", []),
        "dashboard_targets": dashboard_targets(card),
        "grant_targets": grant_targets(card),
        "buyer_segments": buyer_segments(card, outreach),
        "buyer_outreach_position": outreach_position(card, outreach, tier),
        "validation_run": validation_run(card),
        "next_high_value_step": next_high_value_step,
        "blockers": blockers(card, reviewer_gate, dollar_gate, champion_row, pilot_card, tier),
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
            "Route the robust repeat-window proof card into grant appendices, VPS/domain dashboard data, and buyer-authorized pilot scoping.",
            "It is the current strongest robust repeat candidate; the next unlock is field-authorized holdouts, not stronger wording.",
        )
    if "kuramoto_phase_coupling" in by_id:
        add(
            2,
            "kuramoto_phase_coupling",
            "Run additional pre-registered holdout windows until the uncertainty gate clearly passes or fails.",
            "It is a rolling champion but still needs stronger uncertainty evidence before field-validation language.",
        )
    if "phase_locked_residual_corrector" in by_id:
        add(
            3,
            "phase_locked_residual_corrector",
            "Promote the energy-price-pressure proxy into a formal registry/replay adapter and keep economics gated.",
            "It has the largest current money-proxy delta but cannot support real-dollar savings until accepted field economics exist.",
        )
    if "thermal_plume_convection" in by_id:
        add(
            4,
            "thermal_plume_convection",
            "Increase source depth and connect to real thermal/datacenter or grid-cooling baselines.",
            "It is a rolling champion but source depth is still thin for hardware-energy buyer claims.",
        )
    if "leaf_veins" in by_id and "crack_propagation_paths" in by_id:
        add(
            5,
            "crack_propagation_paths",
            "Build the next branching/infrastructure replay around crack paths and keep leaf-vein evidence as bounded candidate evidence.",
            "Branching transport is valuable, but the current evidence is not yet strong enough for a performance or dollar claim.",
        )
    return sorted(actions, key=lambda item: item["priority"])


def high_value_wiring_queue(champion: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for row in rows_from(champion, "family_asset_rankings")[:limit]:
        family_id = str(row.get("family", ""))
        rolling = str(row.get("rolling_gate_status", ""))
        robust = as_bool(row.get("robust_repeat_uncertainty_gate_passed"))
        paid = as_bool(row.get("paid_pilot_ready"))
        if rolling == "rolling_champion" and robust and paid:
            next_wire = "grant_appendix + proof_to_pilot + vps_domain_hash + buyer_authorized_holdouts"
        elif rolling == "rolling_champion":
            next_wire = "additional_holdouts + uncertainty_gate + bounded_grant_appendix"
        elif rolling == "triple_source_candidate":
            next_wire = "repeat_frozen_replay + named_baseline_lock"
        elif str(row.get("evidence_status", "")).startswith("proof_value"):
            next_wire = "build_first_live_adapter_or_reroute_to_current_winner"
        else:
            next_wire = "preserve_as_ranked_candidate_and_schedule_benchmark_gap"
        queue.append(
            {
                "rank": row.get("rank"),
                "family_id": family_id,
                "label": row.get("label", family_id),
                "lane": row.get("lane", ""),
                "asset_score": row.get("asset_score"),
                "evidence_status": row.get("evidence_status", ""),
                "claim_stage": row.get("claim_stage", ""),
                "rolling_gate_status": rolling,
                "robust_repeat_uncertainty_gate_passed": robust,
                "paid_pilot_ready": paid,
                "ready_for_field_validation_claim": False,
                "ready_for_real_dollar_claim": False,
                "next_wire": next_wire,
            }
        )
    return queue


def build_payload() -> dict[str, Any]:
    proof_pack = read_json(PROOF_CARD_PACK_JSON)
    replay = read_json(TOP_REPLAY_JSON)
    champion = read_json(CHAMPION_JSON)
    reviewer_gate = read_json(REVIEWER_GATE_JSON)
    dollar_gate = read_json(DOLLAR_GATE_JSON)
    outreach = read_json(BUYER_OUTREACH_JSON)
    proof_to_pilot = read_json(PROOF_TO_PILOT_JSON)
    truth = read_json(TRUTH_SWEEP_JSON)
    claim_map = read_json(CLAIM_MAP_JSON)

    cards = [item for item in proof_pack.get("proof_cards", []) if isinstance(item, dict)]
    champion_map = champion_by_family(champion)
    pilot_map = pilot_by_family(proof_to_pilot)
    rows = [
        build_wiring_row(
            card,
            outreach,
            reviewer_gate,
            dollar_gate,
            champion_map.get(str(card.get("family_id", "")), {}),
            pilot_map.get(str(card.get("family_id", "")), {}),
        )
        for card in cards
    ]

    all_dashboard_targets = sorted({target for row in rows for target in row["dashboard_targets"]})
    all_grant_targets = sorted({target for row in rows for target in row["grant_targets"]})
    all_segments = sorted({segment for row in rows for segment in row["buyer_segments"]})
    rolling_count = sum(1 for row in rows if row.get("rolling_gate_status") == "rolling_champion")
    robust_count = sum(1 for row in rows if row.get("robust_repeat_uncertainty_gate_passed"))
    triple_source_count = sum(1 for row in rows if row.get("rolling_gate_status") == "triple_source_candidate")
    single_run_count = sum(1 for row in rows if row.get("rolling_gate_status") == "single_run_candidate")
    truth_summary = as_dict(truth.get("summary"))
    champion_summary = as_dict(champion.get("summary"))
    truth_gates = current_truth_gates(truth)

    gates = {
        "ready_for_live_geometry_claim": False,
        "ready_for_real_dollar_claim": False,
        "field_validation": False,
        "kraken_live_execution_allowed": False,
        "mass_email_allowed": False,
        "send_without_user_review": False,
        "bounded_estimated_value_claim_allowed": truth_gates["bounded_estimated_value_claim_allowed"],
        "paid_pilot_scoping_allowed": truth_gates["paid_pilot_scoping_allowed"],
        "vps_domain_live_dashboard_routed": truth_gates["vps_domain_live_dashboard_routed"],
        "glyph_or_external_vault_routed": truth_gates["glyph_or_external_vault_routed"],
    }
    summary = {
        "proof_card_count": len(rows),
        "ranked_family_count": champion_summary.get("ranked_family_count", 0),
        "registered_family_count": champion_summary.get("family_count", 0),
        "rolling_champion_count": rolling_count,
        "robust_repeat_candidate_count": robust_count,
        "triple_source_candidate_count": triple_source_count,
        "single_run_candidate_count": single_run_count,
        "live_measured_sources": truth_summary.get("measured_sources", champion_summary.get("live_measured_sources", 0)),
        "live_measured_rows": truth_summary.get("total_measured_rows", champion_summary.get("live_total_measured_rows", 0)),
        "safe_estimated_hourly_value_usd": truth_summary.get("safe_estimated_hourly_value_usd", 0),
        "safe_estimated_annual_value_usd": truth_summary.get("safe_estimated_annual_value_usd", 0),
        "blocked_context_annual_value_usd": truth_summary.get("blocked_context_annual_value_usd", 0),
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
            "proof_to_pilot_control_room": str(PROOF_TO_PILOT_JSON.relative_to(ROOT)),
            "field_money_truth_sweep": str(TRUTH_SWEEP_JSON.relative_to(ROOT)),
            "claim_strength_value_unlock_map": str(CLAIM_MAP_JSON.relative_to(ROOT)),
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
            "proof_to_pilot_summary": proof_to_pilot.get("summary", {}),
            "field_money_truth_summary": truth.get("summary", {}),
            "claim_strength_summary": {
                "claim_ladder_count": len(rows_from(claim_map, "claim_ladder")),
                "current_repeat_candidate_count": len(rows_from(claim_map, "current_repeat_candidates")),
            },
            "buyer_outreach_current_truth": outreach.get("current_truth", {}),
        },
        "summary": summary,
        "current_truth_gates": truth_gates,
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
        "high_value_wiring_queue": high_value_wiring_queue(champion, limit=20),
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
        f"- Ranked families available from champion board: `{summary['ranked_family_count']}` / `{summary['registered_family_count']}`",
        f"- Live measured sources: `{summary['live_measured_sources']}`",
        f"- Live measured rows: `{summary['live_measured_rows']}`",
        f"- Rolling champions in wired proof cards: `{summary['rolling_champion_count']}`",
        f"- Robust repeat candidates in wired proof cards: `{summary['robust_repeat_candidate_count']}`",
        f"- Triple-source candidates: `{summary['triple_source_candidate_count']}`",
        f"- Single-run candidates: `{summary['single_run_candidate_count']}`",
        f"- Candidate wins against named baseline: `{summary['candidate_win_count']}`",
        f"- Bounded estimated value claim allowed: `{str(summary['bounded_estimated_value_claim_allowed']).lower()}`",
        f"- Paid pilot scoping allowed: `{str(summary['paid_pilot_scoping_allowed']).lower()}`",
        f"- Safe estimated value signal: `${summary['safe_estimated_hourly_value_usd']:,.0f}/hour`, `${summary['safe_estimated_annual_value_usd']:,.0f}/year` under assumptions",
        f"- Blocked context-only value surface: `${summary['blocked_context_annual_value_usd']:,.0f}/year`",
        f"- VPS/domain live dashboard routed: `{str(summary['vps_domain_live_dashboard_routed']).lower()}`",
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
            "## High-Value Wiring Queue",
            "",
            "| Rank | Family | Lane | Evidence | Next Wire |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload["high_value_wiring_queue"][:20]:
        lines.append(
            f"| {row['rank']} | `{row['family_id']}` | `{row['lane']}` | "
            f"{row['rolling_gate_status']} / {row['evidence_status']} | {row['next_wire']} |"
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
        next_step = row.get("next_high_value_step") or (
            row["validation_run"]["next_steps"][0] if row["validation_run"]["next_steps"] else "No next step set."
        )
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
