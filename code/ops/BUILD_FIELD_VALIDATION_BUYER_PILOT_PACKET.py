from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

REPEAT_JSON = OUT_OPS / "geometry_repeat_proof_validation_latest.json"
UNCERTAINTY_JSON = OUT_OPS / "geometry_repeat_uncertainty_report_latest.json"
KURAMOTO_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
READY_REPLAY_JSON = OUT_OPS / "geometry_ready_source_replay_latest.json"
VALUATION_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"

OUT_JSON = OUT_OPS / "field_validation_buyer_pilot_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_validation_buyer_pilot_packet.json"
OUT_MD = DOCS / "FIELD_VALIDATION_BUYER_PILOT_PACKET_2026-06-25.md"

BOUNDARY = (
    "This is a protocol-readiness packet, not an outreach authorization or a "
    "field-validation packet. No current geometry family is a performance "
    "champion or buyer field-replay candidate. The priceable work is a bounded "
    "source-native benchmark and evidence protocol review. Every send still "
    "requires recipient verification, duplicate reconciliation, routing review, "
    "and exact action-time approval."
)

DATA_ROOM_ARTIFACTS = [
    "docs/GEOMETRY_CHAMPION_ASSET_MAP_2026-06-25.md",
    "docs/GEOMETRY_REPEAT_PROOF_VALIDATION_2026-06-25.md",
    "docs/GEOMETRY_REPEAT_UNCERTAINTY_REPORT_2026-06-25.md",
    "docs/GEOMETRY_FIELD_VALIDATION_PROTOCOL_2026-06-25.md",
    "docs/KURAMOTO_HOLDOUT_EXPANSION_2026-06-26.md",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")
    os.replace(temporary, path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def summary(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("summary", {})
    return value if isinstance(value, dict) else {}


def rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def repeat_card(repeat_payload: dict[str, Any], family_id: str) -> dict[str, Any]:
    for row in rows(repeat_payload, "validations"):
        if row.get("family_id") == family_id:
            return row
    return {}


def kuramoto_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    source = summary(payload)
    keys = [
        "candidate",
        "development_selected_candidate",
        "candidate_was_protocol_selected",
        "named_baseline",
        "best_registered_baseline",
        "holdout_count",
        "wins_vs_kalman",
        "wins_vs_best_baseline",
        "losses_or_ties_vs_kalman",
        "win_rate_vs_kalman",
        "mean_delta_vs_kalman",
        "mean_delta_vs_best_baseline",
        "estimated_rows_replayed",
        "numeric_samples_read",
        "source_system_count",
        "source_systems",
        "authority_count",
        "registered_baseline_count",
        "registered_baseline_mean_win_count",
        "registered_baseline_gate_pass_count",
        "candidate_beats_all_registered_baselines_after_holm",
        "protocol_grade_internal_champion",
        "passes_internal_20_holdout_gate",
        "ready_for_buyer_authorized_field_replay_request",
        "holdout_chain_sha256",
        "claim_boundary",
    ]
    evidence = {key: source.get(key) for key in keys}
    evidence["artifact"] = str(KURAMOTO_JSON.relative_to(ROOT)).replace("\\", "/")
    evidence["evidence_mode"] = source.get("evidence_mode", "direct_measured_replay")
    return evidence


def common_packet(
    *,
    family_id: str,
    lane: str,
    name: str,
    titles: list[str],
    question: str,
    status: str,
    blockers: list[str],
    review_low: int,
    review_high: int,
    review_duration_business_days: int,
    review_fee_status: str,
) -> dict[str, Any]:
    packet = {
        "family_id": family_id,
        "lane": lane,
        "pilot_name": name,
        "packet_role": "protocol_review_candidate_not_field_replay_candidate",
        "evidence_stage": status,
        "priority_buyer_titles": titles,
        "protocol_question": question,
        "field_replay_request": {
            "request_type": "not_authorized_current_candidate_failed_or_lacks_promotion_gate",
            "minimum_holdout_windows": 20,
            "current_status": "blocked",
            "blockers": blockers,
            "unlock_condition": (
                "A development-selected candidate must first beat every registered "
                "source-specific baseline after multiplicity correction, then pass "
                "independent frozen repeats before any field-replay request."
            ),
        },
        "paid_offer": {
            "offer_type": "paid source-native benchmark and evidence protocol review",
            "pricing_status": "bounded_service_scoping_not_performance_value",
            "price_range_usd": {"low": review_low, "high": review_high},
            "duration_business_days": review_duration_business_days,
            "fee_status": review_fee_status,
            "founder_approved": False,
            "buyer_accepted": False,
            "safe_positioning": (
                "Sell source-task mapping, baseline registration, frozen chronology, "
                "reproducible execution, and claim-boundary review. Do not sell a "
                "winning candidate, savings estimate, or field result."
            ),
        },
        "deliverables": [
            "source-task compatibility matrix",
            "data-quality and source-normalization report",
            "registered incumbent baseline set",
            "frozen development and holdout protocol",
            "reproducible benchmark with hashes and negative results",
            "claim and non-claim boundary memo",
        ],
        "data_room_artifacts": DATA_ROOM_ARTIFACTS,
        "buyer_data_checklist": [
            "authorized timestamped source data or approved public source",
            "operational question and target variable",
            "accepted incumbent or source-native baselines",
            "development and untouched holdout boundaries",
            "acceptance metrics, guardrails, and failure reporting rules",
        ],
        "baseline_controls": [
            "source-native incumbent",
            "naive or persistence baseline",
            "seasonal baseline where applicable",
            "linear or autoregressive baseline",
            "best accepted domain baseline",
        ],
        "primary_kpis": [
            "source-task compatibility pass",
            "all-baseline score delta",
            "globally corrected positive comparison count",
            "reproducibility and claim-boundary completeness",
        ],
        "pre_call_questions": [
            "What operational decision should the benchmark represent?",
            "Which source is authorized for evaluation?",
            "Which incumbent baseline does the system owner accept?",
            "Which metric and guardrail determine pass or fail?",
            "Which window can remain untouched until the protocol is frozen?",
            "Who owns result interpretation and any later economic conversion?",
        ],
        "sow_outline": [
            "Confirm data rights, task grain, and source schema.",
            "Register accepted baselines and forbidden tuning rules.",
            "Freeze development, holdout, metrics, and failure reporting.",
            "Run candidate and baselines under identical constraints.",
            "Deliver reproducible evidence and explicit non-claims.",
        ],
        "draft_outreach": {
            "status": "not_generated_no_recipient_selected",
            "send_mode": "blocked_pending_routing_duplicate_and_action_time_review",
        },
        "claim_gate": {
            "send_manually_to_reviewed_contacts": False,
            "exact_action_time_approval_required": True,
            "bulk_email_allowed": False,
            "performance_champion_claim_allowed": False,
            "fixed_dollar_delta_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
        },
        "no_send_phrases": [
            "guaranteed savings",
            "field validated",
            "current performance champion",
            "$10k per frozen delta",
            "guaranteed trading edge",
        ],
    }
    return packet


def build_payload() -> dict[str, Any]:
    repeat_payload = read_json(REPEAT_JSON)
    uncertainty_payload = read_json(UNCERTAINTY_JSON)
    kuramoto_payload = read_json(KURAMOTO_JSON)
    ready_payload = read_json(READY_REPLAY_JSON)
    valuation_payload = read_json(VALUATION_JSON)

    required = {
        "geometry_repeat_proof_validation_v2": repeat_payload.get("schema"),
        "geometry_repeat_uncertainty_report_v2": uncertainty_payload.get("schema"),
        "kuramoto_holdout_expansion_v2": kuramoto_payload.get("schema"),
        "geometry_ready_source_replay_v2": ready_payload.get("schema"),
        "valuation_proposal_target_packet_v3": valuation_payload.get("schema"),
    }
    for expected, actual in required.items():
        if actual != expected:
            raise ValueError(f"{expected} is required; found {actual!r}")

    valuation_target = valuation_payload.get("recommended_first_proposal_target", {})
    review_range = valuation_target.get("paid_review_scope_usd", {})
    review_low = int(review_range["low"])
    review_high = int(review_range["high"])
    review_duration_business_days = int(review_range["duration_business_days"])
    review_fee_status = str(review_range["status"])
    if review_low != review_high or review_duration_business_days <= 0:
        raise ValueError("Current protocol-review offer must be fixed-fee and time-bounded")

    brach_repeat = repeat_card(repeat_payload, "brachistochrone_descent")
    kuramoto = kuramoto_evidence(kuramoto_payload)

    brach = common_packet(
        family_id="brachistochrone_descent",
        lane="optimal_curve_transport",
        name="Constrained Transport Benchmark Protocol Review",
        titles=[
            "Infrastructure Analytics Validation Lead",
            "Routing or Operations Research Lead",
            "Research Software Assurance Lead",
        ],
        question=(
            "Can a direct measured transport task and accepted route baselines be "
            "defined before this family is scored?"
        ),
        status="blocked_no_compatible_direct_measured_replay",
        blockers=[
            "no compatible direct measured replay input",
            "no source-native baseline gauntlet result",
            "no qualified independent repeat hashes",
        ],
        review_low=review_low,
        review_high=review_high,
        review_duration_business_days=review_duration_business_days,
        review_fee_status=review_fee_status,
    )
    brach["latest_repeat_evidence"] = brach_repeat

    wave = common_packet(
        family_id="kuramoto_phase_coupling",
        lane="wave_resonance_timing",
        name="Wave Timing Negative-Result and Protocol Review",
        titles=[
            "Energy Forecasting Validation Lead",
            "Grid Analytics Research Lead",
            "Time-Series Benchmark Owner",
        ],
        question=(
            "Which new development-selected wave candidate, if any, can beat all "
            "registered EIA baselines on a future untouched holdout?"
        ),
        status="direct_measured_source_specific_baseline_gate_failed",
        blockers=[
            "Kuramoto was not selected by the frozen development protocol",
            "negative mean skill versus the named Kalman baseline",
            "zero registered baseline mean wins",
            "zero all-baseline globally corrected promotions",
        ],
        review_low=review_low,
        review_high=review_high,
        review_duration_business_days=review_duration_business_days,
        review_fee_status=review_fee_status,
    )
    wave["latest_holdout_evidence"] = kuramoto

    packets = [brach, wave]
    for packet in packets:
        packet["packet_sha256"] = stable_sha256(
            {key: value for key, value in packet.items() if key != "packet_sha256"}
        )

    ready_summary = summary(ready_payload)
    uncertainty_summary = summary(uncertainty_payload)
    payload: dict[str, Any] = {
        "schema": "field_validation_buyer_pilot_packet_v2",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "summary": {
            "packet_count": len(packets),
            "protocol_review_packet_count": len(packets),
            "manual_outreach_ready_count": 0,
            "field_replay_candidate_count": 0,
            "internal_performance_champion_count": 0,
            "repeat_confirmation_eligible_count": int(
                uncertainty_summary.get("repeat_confirmation_eligible_count") or 0
            ),
            "direct_measured_replay_count": int(
                ready_summary.get("direct_measured_replay_count") or 0
            ),
            "conditioned_synthetic_replay_count": int(
                ready_summary.get("source_conditioned_synthetic_stress_count") or 0
            ),
            "direct_all_baseline_global_holm_positive_count": int(
                ready_summary.get(
                    "direct_all_baseline_global_holm_positive_count"
                )
                or 0
            ),
            "legacy_ready_rows_excluded": int(
                ready_summary.get("legacy_ready_for_benchmark_rows_excluded") or 0
            ),
            "numeric_fallback_profile_count": int(
                ready_summary.get("numeric_fallback_profile_count") or 0
            ),
            "kuramoto_holdout_ready_for_field_replay_request": bool(
                kuramoto.get("ready_for_buyer_authorized_field_replay_request")
            ),
            "kuramoto_holdout_count": int(kuramoto.get("holdout_count") or 0),
            "kuramoto_holdout_wins_vs_kalman": int(
                kuramoto.get("wins_vs_kalman") or 0
            ),
            "kuramoto_holdout_mean_delta_vs_kalman": float(
                kuramoto.get("mean_delta_vs_kalman") or 0.0
            ),
            "kuramoto_holdout_chain_sha256": kuramoto.get(
                "holdout_chain_sha256", ""
            ),
            "bulk_email_allowed": False,
            "fixed_dollar_delta_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
        },
        "packets": packets,
        "inputs": {
            "repeat_validation": str(REPEAT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "repeat_uncertainty": str(UNCERTAINTY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "kuramoto_holdout": str(KURAMOTO_JSON.relative_to(ROOT)).replace("\\", "/"),
            "ready_replay": str(READY_REPLAY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "valuation": str(VALUATION_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
        "claim_controls": {
            "allowed": [
                "paid protocol review scoping",
                "source compatibility and baseline registration",
                "reviewer-safe negative-result reporting",
            ],
            "blocked": [
                "outreach without exact action-time approval",
                "field replay request for either current candidate",
                "performance champion language",
                "bulk email",
                "fixed-dollar frozen-delta claim",
                "realized savings",
            ],
        },
    }
    payload["summary"]["packet_chain_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "packets": packets,
            "claim_controls": payload["claim_controls"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    info = payload["summary"]
    lines = [
        "# Field Validation Buyer Pilot Packet",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Current Gate",
        "",
        f"- Protocol-review packets: `{info['protocol_review_packet_count']}`",
        f"- Manual outreach ready: `{info['manual_outreach_ready_count']}`",
        f"- Field-replay candidates: `{info['field_replay_candidate_count']}`",
        f"- Internal performance champions: `{info['internal_performance_champion_count']}`",
        f"- Direct all-baseline global promotions: `{info['direct_all_baseline_global_holm_positive_count']}`",
        f"- Kuramoto holdout: `{info['kuramoto_holdout_wins_vs_kalman']}/{info['kuramoto_holdout_count']}`",
        f"- Kuramoto mean delta vs Kalman: `{info['kuramoto_holdout_mean_delta_vs_kalman']}`",
        f"- Kuramoto field-replay request ready: `{str(info['kuramoto_holdout_ready_for_field_replay_request']).lower()}`",
        f"- Bulk email allowed: `{str(info['bulk_email_allowed']).lower()}`",
        f"- Fixed-dollar delta claim allowed: `{str(info['fixed_dollar_delta_claim_allowed']).lower()}`",
        f"- Field-validation claim allowed: `{str(info['field_validation_claim_allowed']).lower()}`",
        "",
    ]
    for packet in payload["packets"]:
        lines.extend(
            [
                f"## `{packet['family_id']}`",
                "",
                f"- Lane: `{packet['lane']}`",
                f"- Role: `{packet['packet_role']}`",
                f"- Evidence stage: `{packet['evidence_stage']}`",
                f"- Protocol question: {packet['protocol_question']}",
                f"- Field replay status: `{packet['field_replay_request']['current_status']}`",
                f"- Offer: {packet['paid_offer']['offer_type']}",
                f"- Draft outreach: `{packet['draft_outreach']['status']}`",
                f"- Send allowed: `{str(packet['claim_gate']['send_manually_to_reviewed_contacts']).lower()}`",
                f"- Packet SHA-256: `{packet['packet_sha256']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "Do not run bulk outreach, request a field replay for these candidates, or describe either family as a current performance champion.",
            "",
            f"Packet chain SHA-256: `{info['packet_chain_sha256']}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "packets": payload["summary"]["packet_count"],
                "manual_outreach_ready": payload["summary"][
                    "manual_outreach_ready_count"
                ],
                "field_replay_candidates": payload["summary"][
                    "field_replay_candidate_count"
                ],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
