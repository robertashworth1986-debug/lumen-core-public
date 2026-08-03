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

ASSET_MAP_JSON = OUT_OPS / "geometry_champion_asset_map_latest.json"
REPEAT_JSON = OUT_OPS / "geometry_repeat_proof_validation_latest.json"
UNCERTAINTY_JSON = OUT_OPS / "geometry_repeat_uncertainty_report_latest.json"
BUYER_PACKET_JSON = OUT_OPS / "field_validation_buyer_pilot_packet_latest.json"
CONTROL_ROOM_JSON = OUT_OPS / "field_validation_control_room_latest.json"
VALUATION_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"

OUT_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "proof_to_pilot_control_room.json"
OUT_MD = DOCS / "PROOF_TO_PILOT_CONTROL_ROOM_2026-06-25.md"

CHAIN_DOCS = [
    DOCS / "GEOMETRY_REPEAT_PROOF_VALIDATION_2026-06-25.md",
    DOCS / "GEOMETRY_REPEAT_UNCERTAINTY_REPORT_2026-06-25.md",
    DOCS / "FIELD_VALIDATION_BUYER_PILOT_PACKET_2026-06-25.md",
    DOCS / "FIELD_VALIDATION_CONTROL_ROOM_2026-06-26.md",
    DOCS / "VALUATION_PROPOSAL_TARGET_PACKET_2026-06-26.md",
    DOCS / "KURAMOTO_FIELD_REPLAY_REQUEST_2026-06-26.md",
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


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def artifact_row(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "exists": exists,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if exists else "",
    }


def require_inputs() -> dict[str, dict[str, Any]]:
    inputs = {
        "asset_map": read_json(ASSET_MAP_JSON),
        "repeat": read_json(REPEAT_JSON),
        "uncertainty": read_json(UNCERTAINTY_JSON),
        "buyer": read_json(BUYER_PACKET_JSON),
        "control": read_json(CONTROL_ROOM_JSON),
        "valuation": read_json(VALUATION_JSON),
    }
    expected = {
        "asset_map": "geometry_champion_asset_map_v1",
        "repeat": "geometry_repeat_proof_validation_v2",
        "uncertainty": "geometry_repeat_uncertainty_report_v2",
        "buyer": "field_validation_buyer_pilot_packet_v2",
        "control": "field_validation_control_room_v2",
        "valuation": "valuation_proposal_target_packet_v3",
    }
    for name, schema in expected.items():
        actual = inputs[name].get("schema")
        if actual != schema:
            raise ValueError(f"{name} must use {schema}; found {actual!r}")
    return inputs


def build_protocol_review_card(packet: dict[str, Any]) -> dict[str, Any]:
    field_gate = as_dict(packet.get("field_replay_request"))
    claim_gate = as_dict(packet.get("claim_gate"))
    holdout = as_dict(packet.get("latest_holdout_evidence"))
    offer = as_dict(packet.get("paid_offer"))
    card = {
        "family_id": packet.get("family_id"),
        "lane": packet.get("lane"),
        "title": packet.get("pilot_name"),
        "packet_role": packet.get("packet_role"),
        "commercial_stage": "paid_protocol_review_scoping_draft_only",
        "evidence_stage": packet.get("evidence_stage"),
        "field_replay_status": field_gate.get("current_status"),
        "field_replay_unlock_condition": field_gate.get("unlock_condition"),
        "protocol_question": packet.get("protocol_question"),
        "reviewer_roles": packet.get("priority_buyer_titles") or [],
        "source_and_baseline_controls": {
            "data_checklist": packet.get("buyer_data_checklist") or [],
            "baseline_controls": packet.get("baseline_controls") or [],
            "primary_kpis": packet.get("primary_kpis") or [],
        },
        "measured_reference": {
            "candidate": holdout.get("candidate"),
            "development_selected_candidate": holdout.get(
                "development_selected_candidate"
            ),
            "candidate_was_protocol_selected": holdout.get(
                "candidate_was_protocol_selected"
            ),
            "holdout_count": holdout.get("holdout_count"),
            "wins_vs_named_baseline": holdout.get("wins_vs_kalman"),
            "mean_delta_vs_named_baseline": holdout.get("mean_delta_vs_kalman"),
            "all_baseline_gate_passed": holdout.get(
                "candidate_beats_all_registered_baselines_after_holm"
            ),
            "holdout_chain_sha256": holdout.get("holdout_chain_sha256"),
        },
        "paid_offer": offer,
        "deliverables": packet.get("deliverables") or [],
        "data_room_artifacts": packet.get("data_room_artifacts") or [],
        "next_actions": packet.get("sow_outline") or [],
        "claim_gate": {
            "paid_protocol_review_scoping_allowed": True,
            "pilot_ready": False,
            "field_replay_request_allowed": False,
            "manual_outreach_allowed": False,
            "send_allowed": False,
            "exact_action_time_approval_required": True,
            "field_validation_claim_allowed": bool(
                claim_gate.get("field_validation_claim_allowed")
            ),
            "realized_savings_claim_allowed": bool(
                claim_gate.get("realized_savings_claim_allowed")
            ),
            "fixed_dollar_delta_claim_allowed": bool(
                claim_gate.get("fixed_dollar_delta_claim_allowed")
            ),
            "bulk_email_allowed": bool(claim_gate.get("bulk_email_allowed")),
            "live_trading_or_autonomous_execution_allowed": bool(
                claim_gate.get("live_trading_or_autonomous_execution_allowed")
            ),
        },
    }
    card["card_sha256"] = stable_sha256(card)
    return card


def build_payload() -> dict[str, Any]:
    inputs = require_inputs()
    asset_summary = as_dict(inputs["asset_map"].get("summary"))
    repeat_summary = as_dict(inputs["repeat"].get("summary"))
    uncertainty_summary = as_dict(inputs["uncertainty"].get("summary"))
    buyer_summary = as_dict(inputs["buyer"].get("summary"))
    control_summary = as_dict(inputs["control"].get("summary"))
    valuation_state = as_dict(inputs["valuation"].get("valuation_state"))
    cards = [
        build_protocol_review_card(as_dict(packet))
        for packet in as_list(inputs["buyer"].get("packets"))
        if as_dict(packet)
    ]
    artifact_health = [artifact_row(path) for path in CHAIN_DOCS]
    all_docs_present = all(row["exists"] for row in artifact_health)
    top_family_ids = [str(card["family_id"]) for card in cards]

    summary = {
        "family_count": asset_summary.get("family_count", 0),
        "natural_path_family_count": asset_summary.get(
            "natural_path_family_count", 0
        ),
        "natural_path_target_met": bool(
            asset_summary.get("natural_path_target_met")
        ),
        "repeat_confirmation_eligible_count": repeat_summary.get(
            "repeat_confirmation_eligible_count", 0
        ),
        "robust_candidate_count": uncertainty_summary.get(
            "robust_repeat_uncertainty_gate_passed_count", 0
        ),
        "protocol_review_packet_count": buyer_summary.get(
            "protocol_review_packet_count", len(cards)
        ),
        "field_replay_candidate_count": buyer_summary.get(
            "field_replay_candidate_count", 0
        ),
        "pilot_ready_count": 0,
        "manual_outreach_ready_count": buyer_summary.get(
            "manual_outreach_ready_count", 0
        ),
        "top_family_ids": top_family_ids,
        "current_commercial_stage": (
            "paid_protocol_review_scoping_ready_draft_only_no_recipient"
        ),
        "all_chain_docs_present": all_docs_present,
        "internal_performance_champion_present": False,
        "paid_protocol_review_scoping_allowed": bool(
            control_summary.get("paid_protocol_review_scoping_ready")
        ),
        "manual_reviewed_outreach_allowed": False,
        "paid_evaluation_offer_allowed": True,
        "buyer_authorized_pilot_scoping_ready": False,
        "field_validation_claim_allowed": False,
        "realized_savings_claim_allowed": False,
        "fixed_dollar_delta_claim_allowed": False,
        "bulk_email_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "enterprise_valuation_asserted": bool(
            valuation_state.get("enterprise_valuation_asserted")
        ),
    }
    summary["control_room_chain_sha256"] = stable_sha256(
        {
            "summary": summary,
            "repeat": repeat_summary,
            "uncertainty": uncertainty_summary,
            "buyer": buyer_summary,
            "cards": cards,
            "artifact_health": artifact_health,
        }
    )

    return {
        "schema": "proof_to_pilot_control_room_v2",
        "generated_utc": now_utc(),
        "legacy_filename_notice": (
            "The filename is retained for downstream compatibility. No current "
            "candidate is pilot-ready; the live commercial stage is bounded "
            "protocol-review scoping."
        ),
        "evidence_boundary": (
            "This control room separates registry breadth, direct measured replay, "
            "conditioned-synthetic stress, repeat eligibility, field replay, and "
            "commercial service scoping. It does not authorize outreach or establish "
            "candidate superiority, field validation, realized savings, enterprise "
            "value, award certainty, or live execution."
        ),
        "inputs": {
            "geometry_champion_asset_map": str(
                ASSET_MAP_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "geometry_repeat_proof_validation": str(
                REPEAT_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "geometry_repeat_uncertainty_report": str(
                UNCERTAINTY_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "field_validation_buyer_pilot_packet": str(
                BUYER_PACKET_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "field_validation_control_room": str(
                CONTROL_ROOM_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "valuation_packet": str(VALUATION_JSON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
        "summary": summary,
        "protocol_review_cards": cards,
        "top_cards": cards,
        "artifact_health": artifact_health,
        "claim_controls": {
            "allowed": [
                "measured nonpromotion evidence",
                "paid protocol-review service scoping",
                "benchmark implementation scoping",
                "grant or reviewer evidence appendix",
            ],
            "blocked": [
                "current performance champion",
                "pilot-ready candidate",
                "field-replay request for current candidates",
                "manual or bulk outreach without exact action-time approval",
                "field validation already proven",
                "realized savings",
                "fixed-dollar frozen-delta value",
                "enterprise valuation from current evidence",
                "award certainty",
                "live trading or autonomous operational execution",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Proof To Protocol Review Control Room",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["legacy_filename_notice"],
        "",
        payload["evidence_boundary"],
        "",
        "## Current State",
        "",
        f"- Geometry families registered: `{summary['family_count']}`",
        f"- Natural-path families: `{summary['natural_path_family_count']}`",
        f"- Repeat-eligible candidates: `{summary['repeat_confirmation_eligible_count']}`",
        f"- Robust candidates: `{summary['robust_candidate_count']}`",
        f"- Protocol-review packets: `{summary['protocol_review_packet_count']}`",
        f"- Field-replay candidates: `{summary['field_replay_candidate_count']}`",
        f"- Pilot-ready candidates: `{summary['pilot_ready_count']}`",
        f"- Manual outreach ready: `{summary['manual_outreach_ready_count']}`",
        f"- Commercial stage: `{summary['current_commercial_stage']}`",
        f"- All chain docs present: `{str(summary['all_chain_docs_present']).lower()}`",
        f"- Control-room chain SHA-256: `{summary['control_room_chain_sha256']}`",
        "",
        "## Gates",
        "",
        f"- Internal performance champion present: `{str(summary['internal_performance_champion_present']).lower()}`",
        f"- Paid protocol-review scoping allowed: `{str(summary['paid_protocol_review_scoping_allowed']).lower()}`",
        f"- Manual reviewed outreach allowed: `{str(summary['manual_reviewed_outreach_allowed']).lower()}`",
        f"- Buyer-authorized pilot scoping ready: `{str(summary['buyer_authorized_pilot_scoping_ready']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Realized-savings claim allowed: `{str(summary['realized_savings_claim_allowed']).lower()}`",
        f"- Fixed-dollar delta claim allowed: `{str(summary['fixed_dollar_delta_claim_allowed']).lower()}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        f"- Enterprise valuation asserted: `{str(summary['enterprise_valuation_asserted']).lower()}`",
        "",
        "## Protocol Review Cards",
        "",
    ]
    for card in payload["protocol_review_cards"]:
        evidence = card["measured_reference"]
        lines.extend(
            [
                f"### `{card['family_id']}`",
                "",
                f"- Lane: `{card['lane']}`",
                f"- Title: {card['title']}",
                f"- Commercial stage: `{card['commercial_stage']}`",
                f"- Evidence stage: `{card['evidence_stage']}`",
                f"- Field-replay status: `{card['field_replay_status']}`",
                f"- Candidate: `{evidence['candidate'] or 'none'}`",
                f"- Holdout wins: `{evidence['wins_vs_named_baseline']}`",
                f"- Holdout count: `{evidence['holdout_count']}`",
                f"- Mean delta: `{evidence['mean_delta_vs_named_baseline']}`",
                f"- Pilot ready: `{str(card['claim_gate']['pilot_ready']).lower()}`",
                f"- Send allowed: `{str(card['claim_gate']['send_allowed']).lower()}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "- The strongest current commercial action is a bounded paid protocol review.",
            "- No current candidate is eligible for a buyer field-replay request.",
            "- Any external send requires a current route, duplicate reconciliation, a real recipient, and exact action-time approval.",
            "- Performance, field, savings, enterprise-value, and live-execution claims remain blocked.",
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
                "top_family_ids": payload["summary"]["top_family_ids"],
                "commercial_stage": payload["summary"][
                    "current_commercial_stage"
                ],
                "pilot_ready_count": payload["summary"]["pilot_ready_count"],
                "manual_outreach_ready_count": payload["summary"][
                    "manual_outreach_ready_count"
                ],
                "json": payload["outputs"]["json"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
