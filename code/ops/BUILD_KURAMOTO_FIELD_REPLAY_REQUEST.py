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

BUYER_PACKET_JSON = OUT_OPS / "field_validation_buyer_pilot_packet_latest.json"
CHAMPION_BOARD_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
KURAMOTO_HOLDOUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"

OUT_JSON = OUT_OPS / "kuramoto_field_replay_request_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "kuramoto_field_replay_request.json"
OUT_MD = DOCS / "KURAMOTO_FIELD_REPLAY_REQUEST_2026-06-26.md"


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


def select_packet(payload: dict[str, Any]) -> dict[str, Any]:
    packets = payload.get("packets", [])
    if not isinstance(packets, list):
        return {}
    for packet in packets:
        if (
            isinstance(packet, dict)
            and packet.get("family_id") == "kuramoto_phase_coupling"
        ):
            return packet
    return {}


def require_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    buyer = read_json(BUYER_PACKET_JSON)
    board = read_json(CHAMPION_BOARD_JSON)
    holdout = read_json(KURAMOTO_HOLDOUT_JSON)
    required = {
        "field_validation_buyer_pilot_packet_v2": buyer.get("schema"),
        "geometry_champion_of_champions_v3": board.get("schema"),
        "kuramoto_holdout_expansion_v2": holdout.get("schema"),
    }
    for expected, actual in required.items():
        if actual != expected:
            raise ValueError(f"{expected} is required; found {actual!r}")
    return buyer, board, holdout


def build_payload() -> dict[str, Any]:
    buyer, board, holdout = require_inputs()
    packet = select_packet(buyer)
    if not packet:
        raise ValueError("Kuramoto protocol-review packet is required")

    measured = holdout.get("summary", {})
    if not isinstance(measured, dict):
        measured = {}
    board_summary = board.get("summary", {})
    if not isinstance(board_summary, dict):
        board_summary = {}

    summary = {
        "candidate": "kuramoto_phase_coupling",
        "lane": packet.get("lane", "wave_resonance_timing"),
        "artifact_role": "nonpromotion_and_future_protocol_redesign_brief",
        "current_status": (
            "field_replay_request_blocked_source_specific_baseline_gate_failed"
        ),
        "internal_performance_champion_present": False,
        "candidate_was_protocol_selected": bool(
            measured.get("candidate_was_protocol_selected", False)
        ),
        "development_selected_candidate": measured.get(
            "development_selected_candidate", ""
        ),
        "evidence_mode": measured.get("evidence_mode", ""),
        "holdout_count": int(measured.get("holdout_count") or 0),
        "wins_vs_kalman": int(measured.get("wins_vs_kalman") or 0),
        "losses_or_ties_vs_kalman": int(
            measured.get("losses_or_ties_vs_kalman") or 0
        ),
        "win_rate_vs_kalman": float(measured.get("win_rate_vs_kalman") or 0.0),
        "mean_delta_vs_kalman": float(
            measured.get("mean_delta_vs_kalman") or 0.0
        ),
        "wins_vs_best_baseline": int(
            measured.get("wins_vs_best_baseline") or 0
        ),
        "mean_delta_vs_best_baseline": float(
            measured.get("mean_delta_vs_best_baseline") or 0.0
        ),
        "named_baseline": measured.get("named_baseline", ""),
        "best_registered_baseline": measured.get(
            "best_registered_baseline", ""
        ),
        "registered_baseline_count": int(
            measured.get("registered_baseline_count") or 0
        ),
        "registered_baseline_mean_win_count": int(
            measured.get("registered_baseline_mean_win_count") or 0
        ),
        "registered_baseline_gate_pass_count": int(
            measured.get("registered_baseline_gate_pass_count") or 0
        ),
        "candidate_beats_all_registered_baselines_after_holm": bool(
            measured.get("candidate_beats_all_registered_baselines_after_holm")
        ),
        "estimated_rows_replayed": int(
            measured.get("estimated_rows_replayed") or 0
        ),
        "panel_row_count": int(measured.get("panel_row_count") or 0),
        "authority_count": int(measured.get("authority_count") or 0),
        "source_system_count": int(measured.get("source_system_count") or 0),
        "source_systems": measured.get("source_systems", []),
        "holdout_chain_sha256": str(
            measured.get("holdout_chain_sha256", "")
        ),
        "field_replay_request_allowed": False,
        "manual_outreach_allowed": False,
        "bulk_email_allowed": False,
        "paid_protocol_review_scoping_allowed": True,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
    }

    request_packet = {
        "request_type": "not_a_field_replay_request",
        "current_status": "blocked",
        "one_sentence_non_ask": (
            "Do not ask an external owner to replay Kuramoto as a promoted "
            "candidate; preserve its direct measured nonpromotion result and "
            "redesign the next source-native wave benchmark."
        ),
        "protocol_review_question": packet.get("protocol_question", ""),
        "reviewer_roles": packet.get("priority_buyer_titles", []),
        "data_required_for_future_protocol": packet.get(
            "buyer_data_checklist", []
        ),
        "baseline_controls": packet.get("baseline_controls", []),
        "future_primary_kpis": packet.get("primary_kpis", []),
        "protocol_review_deliverables": packet.get("deliverables", []),
        "pre_review_questions": packet.get("pre_call_questions", []),
        "current_field_replay_gate": packet.get("field_replay_request", {}),
        "unlock_conditions": [
            "select the future candidate using development data only",
            "freeze source-native baselines before opening the holdout",
            "beat every registered baseline on the untouched holdout",
            "pass multiplicity correction and independent frozen repeats",
            "obtain exact action-time approval before any external request",
        ],
    }

    payload: dict[str, Any] = {
        "schema": "kuramoto_field_replay_request_v2",
        "generated_utc": now_utc(),
        "legacy_filename_notice": (
            "The filename is retained for downstream compatibility. This "
            "artifact blocks the request and is not an outreach packet."
        ),
        "purpose": (
            "Record the direct measured Kuramoto nonpromotion result, close the "
            "legacy field-replay narrative, and define the gates for a future "
            "source-specific wave-family benchmark."
        ),
        "summary": summary,
        "request_packet": request_packet,
        "evidence": {
            "holdout_summary": measured,
            "board_status": {
                "internal_performance_champion_present": bool(
                    board_summary.get("internal_performance_champion_present")
                ),
                "direct_all_baseline_global_holm_positive_count": int(
                    board_summary.get(
                        "direct_all_baseline_global_holm_positive_count"
                    )
                    or 0
                ),
                "legacy_pilot_card_excluded_count": int(
                    board_summary.get("legacy_pilot_card_excluded_count") or 0
                ),
            },
            "source_artifacts": {
                "buyer_packet_json": str(
                    BUYER_PACKET_JSON.relative_to(ROOT)
                ).replace("\\", "/"),
                "champion_board_json": str(
                    CHAMPION_BOARD_JSON.relative_to(ROOT)
                ).replace("\\", "/"),
                "kuramoto_holdout_json": str(
                    KURAMOTO_HOLDOUT_JSON.relative_to(ROOT)
                ).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
            },
        },
        "commercial_boundary": {
            "current_offer": packet.get("paid_offer", {}),
            "offer_allowed": "source-native benchmark and evidence protocol review",
            "performance_value_pricing_allowed": False,
            "outreach": {
                "recipient_selected": False,
                "draft_generated": False,
                "send_allowed": False,
                "exact_action_time_approval_required": True,
            },
        },
        "claim_boundary": {
            "not_a_current_champion": True,
            "not_a_field_replay_request": True,
            "not_field_validation": True,
            "not_realized_savings": True,
            "not_fixed_dollar_delta_value": True,
            "not_live_trading": True,
            "safe_statement": (
                "Kuramoto was measured directly on the frozen EIA panel, was "
                "not selected by the development protocol, and lost on mean "
                "skill to the named Kalman baseline and every registered "
                "baseline. This is useful negative evidence, not a promoted "
                "candidate or field-performance result."
            ),
        },
        "next_actions": [
            "Keep the negative result and its chain hash in the reviewer room.",
            "Do not send the legacy field-replay request.",
            "Map each future wave family to the exact source task it can represent.",
            "Select the future candidate on development data only.",
            "Freeze all source-native baselines before opening the holdout.",
            "Require all-baseline success after multiplicity correction.",
            "Require independent frozen repeats before a field-replay request.",
            "Offer only a bounded protocol review while those gates remain closed.",
        ],
        "no_go_claims": packet.get(
            "no_send_phrases",
            [
                "current performance champion",
                "field replay ready",
                "field validated",
                "guaranteed savings",
                "guaranteed trading edge",
            ],
        ),
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    payload["packet_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "request_packet": payload["request_packet"],
            "commercial_boundary": payload["commercial_boundary"],
            "claim_boundary": payload["claim_boundary"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    request = payload["request_packet"]
    boundary = payload["claim_boundary"]
    lines = [
        "# Kuramoto Nonpromotion and Protocol Redesign Brief",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["legacy_filename_notice"],
        "",
        payload["purpose"],
        "",
        "## Measured Result",
        "",
        f"- Candidate: `{summary['candidate']}`",
        f"- Development-selected candidate: `{summary['development_selected_candidate']}`",
        f"- Candidate was protocol-selected: `{str(summary['candidate_was_protocol_selected']).lower()}`",
        f"- Status: `{summary['current_status']}`",
        f"- Direct measured wins vs Kalman: `{summary['wins_vs_kalman']}/{summary['holdout_count']}`",
        f"- Losses or ties vs Kalman: `{summary['losses_or_ties_vs_kalman']}`",
        f"- Mean skill delta vs Kalman: `{summary['mean_delta_vs_kalman']}`",
        f"- Best registered baseline: `{summary['best_registered_baseline']}`",
        f"- Registered baseline mean wins: `{summary['registered_baseline_mean_win_count']}/{summary['registered_baseline_count']}`",
        f"- Registered baseline gate passes: `{summary['registered_baseline_gate_pass_count']}/{summary['registered_baseline_count']}`",
        f"- All-baseline Holm gate passed: `{str(summary['candidate_beats_all_registered_baselines_after_holm']).lower()}`",
        f"- Panel rows: `{summary['panel_row_count']}`",
        f"- Holdout chain SHA-256: `{summary['holdout_chain_sha256']}`",
        "",
        "## Request Gate",
        "",
        f"- Request type: `{request['request_type']}`",
        f"- Current status: `{request['current_status']}`",
        f"- Field-replay request allowed: `{str(summary['field_replay_request_allowed']).lower()}`",
        f"- Manual outreach allowed: `{str(summary['manual_outreach_allowed']).lower()}`",
        f"- Paid protocol-review scoping allowed: `{str(summary['paid_protocol_review_scoping_allowed']).lower()}`",
        "",
        request["one_sentence_non_ask"],
        "",
        "Unlock conditions:",
        "",
    ]
    lines.extend(f"- {item}" for item in request["unlock_conditions"])
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            boundary["safe_statement"],
            "",
            f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
            f"- Realized savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
            f"- Live execution allowed: `{str(summary['live_trading_or_autonomous_execution_allowed']).lower()}`",
            "",
            "## Next Actions",
            "",
        ]
    )
    lines.extend(
        f"{index}. {action}"
        for index, action in enumerate(payload["next_actions"], start=1)
    )
    lines.extend(
        [
            "",
            f"Packet SHA-256: `{payload['packet_sha256']}`",
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
                "status": payload["summary"]["current_status"],
                "field_replay_request_allowed": payload["summary"][
                    "field_replay_request_allowed"
                ],
                "manual_outreach_allowed": payload["summary"][
                    "manual_outreach_allowed"
                ],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
