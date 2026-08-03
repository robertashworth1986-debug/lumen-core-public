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

CHAMPION_BOARD_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
BUYER_PACKET_JSON = OUT_OPS / "field_validation_buyer_pilot_packet_latest.json"
GAUNTLET_JSON = DASHBOARD_DATA / "champion_metric_gauntlet.json"
VALUATION_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"

OUT_JSON = OUT_OPS / "field_validation_control_room_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_validation_control_room.json"
OUT_MD = DOCS / "FIELD_VALIDATION_CONTROL_ROOM_2026-06-26.md"


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


def bounded_asset(row: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "family",
        "label",
        "lane",
        "rank",
        "asset_score",
        "evidence_status",
        "claim_stage",
        "rolling_gate_status",
        "natural_logic",
        "benchmark_hypothesis",
        "promotion_metric",
        "failure_mode",
        "paid_pilot_ready",
        "manual_outreach_allowed",
        "ready_for_field_validation_claim",
        "ready_for_real_dollar_claim",
        "kraken_live_execution_allowed",
    ]
    return {key: row.get(key) for key in keys}


def hardware_tracks() -> dict[str, Any]:
    return {
        "claim_boundary": (
            "Grid, RF, and PLL protocols may be designed now. They become field "
            "evidence only after an authorized owner supplies instrumented data, "
            "freezes the accepted baseline and metrics, and accepts the result."
        ),
        "grid_validation": {
            "required_inputs": [
                "authorized PMU, load, forecast, dispatch, or outage windows",
                "accepted incumbent forecast or control baseline",
                "operator-approved untouched holdout",
            ],
            "acceptance_metrics": [
                "forecast error",
                "event lead time",
                "false positive and false negative rate",
                "latency under operational cadence",
            ],
        },
        "rf_validation": {
            "required_inputs": [
                "authorized RF spectrum or IQ captures",
                "calibrated instrument settings",
                "accepted receiver or classifier baseline",
            ],
            "acceptance_metrics": [
                "SNR or SINR",
                "EVM and BER",
                "reacquisition time",
                "runtime budget",
            ],
        },
        "pll_validation": {
            "required_inputs": [
                "reference oscillator and PLL configuration",
                "jitter or drift injection profile",
                "calibrated phase-noise or timestamp logs",
            ],
            "acceptance_metrics": [
                "lock time",
                "cycle slips",
                "phase error",
                "jitter transfer",
            ],
        },
        "fixed_dollar_claim_blockers": [
            "no buyer-authorized accepted replay",
            "no approved counterfactual baseline",
            "no accepted economic conversion factor",
            "no signed or traceable result acceptance",
            "no contract pricing a validated technical output",
        ],
    }


def build_payload() -> dict[str, Any]:
    board = read_json(CHAMPION_BOARD_JSON)
    buyer = read_json(BUYER_PACKET_JSON)
    gauntlet = read_json(GAUNTLET_JSON)
    valuation = read_json(VALUATION_JSON)

    required = {
        "geometry_champion_of_champions_v3": board.get("schema"),
        "field_validation_buyer_pilot_packet_v2": buyer.get("schema"),
        "champion_metric_gauntlet_v2": gauntlet.get("schema"),
        "valuation_proposal_target_packet_v3": valuation.get("schema"),
    }
    for expected, actual in required.items():
        if actual != expected:
            raise ValueError(f"{expected} is required; found {actual!r}")

    board_summary = summary(board)
    buyer_summary = summary(buyer)
    gauntlet_summary = summary(gauntlet)
    strongest = gauntlet.get("strongest_current", {})
    if not isinstance(strongest, dict):
        strongest = {}
    section = board.get("champion_of_champions", {})
    if not isinstance(section, dict):
        section = {}
    asset_priority = section.get("next_asset_build_priority", {})
    if not isinstance(asset_priority, dict):
        asset_priority = {}
    family_rows = board.get("family_asset_rankings", [])
    top_rows = [
        bounded_asset(row)
        for row in family_rows[:5]
        if isinstance(row, dict)
    ]

    buyer_tracks = []
    for packet in buyer.get("packets", []):
        if not isinstance(packet, dict):
            continue
        buyer_tracks.append(
            {
                "family_id": packet.get("family_id"),
                "protocol_review_name": packet.get("pilot_name"),
                "evidence_stage": packet.get("evidence_stage"),
                "priority_buyer_titles": packet.get("priority_buyer_titles", []),
                "protocol_question": packet.get("protocol_question", ""),
                "field_replay_status": packet.get("field_replay_request", {}).get(
                    "current_status"
                ),
                "send_allowed": packet.get("claim_gate", {}).get(
                    "send_manually_to_reviewed_contacts", False
                ),
            }
        )

    claim_ladder = [
        {
            "stage": "direct_measured_replay",
            "status": "completed_nonpromotion",
            "evidence": (
                f"Kuramoto {gauntlet_summary.get('holdout_wins', 0)}/"
                f"{gauntlet_summary.get('holdout_count', 0)} paired-day wins; "
                f"mean skill {gauntlet_summary.get('mean_delta_vs_named_baseline', 0)}"
            ),
            "claim_allowed": "measured nonpromotion result",
        },
        {
            "stage": "source_specific_candidate_promotion",
            "status": "blocked_all_baseline_gate_failed",
            "evidence": "zero direct all-baseline globally corrected promotions",
            "claim_allowed": False,
        },
        {
            "stage": "buyer_authorized_field_replay_request",
            "status": "blocked_no_promoted_candidate",
            "evidence": "current candidates are not eligible for a field-replay request",
            "claim_allowed": False,
        },
        {
            "stage": "field_validation",
            "status": "blocked_until_external_owner_protocol_and_accepted_result",
            "evidence": "no external owner-controlled accepted replay",
            "claim_allowed": False,
        },
        {
            "stage": "real_dollar_claim",
            "status": "blocked_until_accepted_economics",
            "evidence": "no accepted technical result or buyer-approved conversion",
            "claim_allowed": False,
        },
        {
            "stage": "live_execution_or_trading",
            "status": "blocked",
            "evidence": "benchmark evidence is not execution authorization",
            "claim_allowed": False,
        },
    ]

    required_external_inputs = [
        {
            "input": "held_out_operational_data",
            "owner": "authorized system owner",
            "status": "missing",
        },
        {
            "input": "incumbent_baseline",
            "owner": "system owner or technical reviewer",
            "status": "missing",
        },
        {
            "input": "acceptance_metric",
            "owner": "technical reviewer or operator",
            "status": "missing",
        },
        {
            "input": "economic_conversion_factor",
            "owner": "buyer operations or finance",
            "status": "missing",
        },
        {
            "input": "signed_or_logged_result_acceptance",
            "owner": "external lab, buyer, agency, or operator",
            "status": "missing",
        },
    ]

    payload: dict[str, Any] = {
        "schema": "field_validation_control_room_v2",
        "generated_utc": now_utc(),
        "purpose": (
            "Separate source breadth, benchmark readiness, candidate promotion, "
            "field validation, and commercial action gates."
        ),
        "summary": {
            "internal_performance_champion_present": False,
            "strongest_current_family": "",
            "strongest_current_lane": "",
            "strongest_current_status": "no_current_performance_champion",
            "next_asset_build_priority_family": asset_priority.get("family", ""),
            "next_asset_build_priority_lane": asset_priority.get("lane", ""),
            "kuramoto_holdout_wins_vs_kalman": int(
                gauntlet_summary.get("holdout_wins") or 0
            ),
            "kuramoto_holdout_count": int(
                gauntlet_summary.get("holdout_count") or 0
            ),
            "kuramoto_mean_delta_vs_kalman": float(
                gauntlet_summary.get("mean_delta_vs_named_baseline") or 0.0
            ),
            "kuramoto_estimated_rows_replayed": int(
                gauntlet_summary.get("estimated_rows_replayed") or 0
            ),
            "kuramoto_source_system_count": int(
                gauntlet_summary.get("source_system_count") or 0
            ),
            "direct_all_baseline_global_holm_positive_count": int(
                board_summary.get(
                    "direct_all_baseline_global_holm_positive_count"
                )
                or 0
            ),
            "best_buyer_pilot_family": "",
            "manual_outreach_ready": False,
            "paid_protocol_review_scoping_ready": True,
            "bulk_email_allowed": False,
            "external_validation_unlock_packet_ready": False,
            "external_approval_received": False,
            "grid_rf_pll_protocols_ready": True,
            "broader_measured_provider_count": int(
                board_summary.get("live_measured_sources") or 0
            ),
            "broader_measured_row_count": int(
                board_summary.get("live_total_measured_rows") or 0
            ),
            "manifest_unique_source_count": int(
                gauntlet_summary.get("manifest_unique_source_count") or 0
            ),
            "legacy_pilot_card_excluded_count": int(
                board_summary.get("legacy_pilot_card_excluded_count") or 0
            ),
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
        },
        "top_assets": {
            "strongest_current": {},
            "next_asset_build_priority": bounded_asset(asset_priority),
            "best_buyer_pilot_card": {},
            "top_family_asset_rankings": top_rows,
        },
        "proof_bridge": {
            "measured_nonpromotion_result": {
                "candidate": strongest.get("family"),
                "development_selected_candidate": strongest.get(
                    "development_selected_candidate"
                ),
                "candidate_was_protocol_selected": strongest.get(
                    "candidate_was_protocol_selected"
                ),
                "named_baseline": strongest.get("named_baseline"),
                "wins": strongest.get("wins_vs_named_baseline"),
                "windows": strongest.get("holdout_count"),
                "mean_delta": strongest.get("mean_delta_vs_named_baseline"),
                "all_baseline_gate_passed": strongest.get(
                    "candidate_beats_all_registered_baselines_after_holm"
                ),
                "chain_sha256": strongest.get("holdout_chain_sha256"),
            },
            "claim_ladder": claim_ladder,
        },
        "external_validation_unlock": {
            "status": "blocked_no_promoted_candidate",
            "external_approval_received": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "what_is_ready_now": [
                "source-native protocol review",
                "source compatibility matrix",
                "baseline registration",
                "negative-result evidence packet",
            ],
            "required_external_inputs": required_external_inputs,
            "allowed_language": (
                "We can scope a source-native benchmark and evidence protocol review."
            ),
            "blocked_language": (
                "We have a current champion, are ready to request field replay, "
                "or have established field performance or savings."
            ),
        },
        "hardware_validation_tracks": hardware_tracks(),
        "buyer_tracks": buyer_tracks,
        "next_10_actions": [
            "Keep the current Kuramoto result as measured negative evidence.",
            "Do not request a buyer field replay for Kuramoto or Brachistochrone.",
            "Select future candidates on development data only.",
            "Register every source-native baseline before scoring the holdout.",
            "Reserve an untouched chronological holdout.",
            "Require every baseline gate to pass after multiplicity correction.",
            "Create independent repeat hashes only after direct promotion.",
            "Use source breadth as adapter inventory, not performance evidence.",
            "Offer a bounded paid protocol review without candidate-win language.",
            "Require exact action-time approval before any external outreach.",
        ],
        "dashboard_cards": [
            {
                "title": "Performance Champion",
                "metric": "none",
                "subtitle": "zero direct all-baseline global promotions",
                "status": "blocked",
            },
            {
                "title": "Kuramoto Measured Read",
                "metric": (
                    f"{gauntlet_summary.get('holdout_wins', 0)}/"
                    f"{gauntlet_summary.get('holdout_count', 0)}"
                ),
                "subtitle": (
                    f"mean skill {gauntlet_summary.get('mean_delta_vs_named_baseline', 0)}"
                ),
                "status": "nonpromotion",
            },
            {
                "title": "Commercially Ready",
                "metric": "protocol review",
                "subtitle": "bounded technical service, no performance claim",
                "status": "draft-only",
            },
        ],
        "claim_controls": {
            "allowed": [
                "measured nonpromotion evidence",
                "source-native protocol review scoping",
                "benchmark implementation proposal",
            ],
            "blocked": [
                "current internal champion",
                "buyer field-replay request for current candidates",
                "manual or bulk outreach without action-time approval",
                "field validation already proven",
                "fixed dollar value per frozen delta",
                "guaranteed trading or institutional profit",
            ],
        },
        "inputs": {
            "champion_board": str(CHAMPION_BOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            "buyer_packet": str(BUYER_PACKET_JSON.relative_to(ROOT)).replace("\\", "/"),
            "gauntlet": str(GAUNTLET_JSON.relative_to(ROOT)).replace("\\", "/"),
            "valuation": str(VALUATION_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    payload["control_room_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "proof_bridge": payload["proof_bridge"],
            "external_validation_unlock": payload["external_validation_unlock"],
            "buyer_tracks": payload["buyer_tracks"],
            "claim_controls": payload["claim_controls"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    info = payload["summary"]
    evidence = payload["proof_bridge"]["measured_nonpromotion_result"]
    lines = [
        "# Field Validation Control Room",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Current Read",
        "",
        f"- Internal performance champion present: `{str(info['internal_performance_champion_present']).lower()}`",
        f"- Current performance champion: `{info['strongest_current_family'] or 'none'}`",
        f"- Next asset-build priority: `{info['next_asset_build_priority_family']}`",
        f"- Kuramoto measured wins vs Kalman: `{info['kuramoto_holdout_wins_vs_kalman']}/{info['kuramoto_holdout_count']}`",
        f"- Kuramoto mean skill delta: `{info['kuramoto_mean_delta_vs_kalman']}`",
        f"- Direct all-baseline global promotions: `{info['direct_all_baseline_global_holm_positive_count']}`",
        f"- Manual outreach ready: `{str(info['manual_outreach_ready']).lower()}`",
        f"- Paid protocol-review scoping ready: `{str(info['paid_protocol_review_scoping_ready']).lower()}`",
        f"- Field-validation claim allowed: `{str(info['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(info['real_dollar_savings_claim_allowed']).lower()}`",
        "",
        "## Measured Nonpromotion",
        "",
        f"- Candidate: `{evidence.get('candidate')}`",
        f"- Development-selected candidate: `{evidence.get('development_selected_candidate')}`",
        f"- Candidate was protocol-selected: `{str(evidence.get('candidate_was_protocol_selected')).lower()}`",
        f"- All-baseline gate passed: `{str(evidence.get('all_baseline_gate_passed')).lower()}`",
        "",
        "## External Validation Unlock",
        "",
        f"- Status: `{payload['external_validation_unlock']['status']}`",
    ]
    for row in payload["external_validation_unlock"]["required_external_inputs"]:
        lines.append(
            f"- `{row['input']}`: `{row['status']}` ({row['owner']})"
        )
    lines.extend(
        [
            "",
            "## Grid/RF/PLL Validation Tracks",
            "",
            payload["hardware_validation_tracks"]["claim_boundary"],
            "",
            "## Next 10 Actions",
            "",
        ]
    )
    lines.extend(
        f"{index}. {action}"
        for index, action in enumerate(payload["next_10_actions"], start=1)
    )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            payload["external_validation_unlock"]["blocked_language"],
            "",
            f"Control-room SHA-256: `{payload['control_room_sha256']}`",
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
                "performance_champion": payload["summary"][
                    "internal_performance_champion_present"
                ],
                "manual_outreach_ready": payload["summary"][
                    "manual_outreach_ready"
                ],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
