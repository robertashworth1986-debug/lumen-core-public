from __future__ import annotations

import hashlib
import importlib.util
import json
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
FIELD_PROTOCOL_JSON = OUT_OPS / "geometry_field_validation_protocol_latest.json"
BUYER_PACKET_JSON = OUT_OPS / "field_validation_buyer_pilot_packet_latest.json"
BUYER_PACKET_SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_VALIDATION_BUYER_PILOT_PACKET.py"

OUT_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "proof_to_pilot_control_room.json"
OUT_MD = DOCS / "PROOF_TO_PILOT_CONTROL_ROOM_2026-06-25.md"

CHAIN_DOCS = [
    DOCS / "GEOMETRY_CHAMPION_ASSET_MAP_2026-06-25.md",
    DOCS / "GEOMETRY_REPEAT_PROOF_VALIDATION_2026-06-25.md",
    DOCS / "GEOMETRY_REPEAT_UNCERTAINTY_REPORT_2026-06-25.md",
    DOCS / "GEOMETRY_FIELD_VALIDATION_PROTOCOL_2026-06-25.md",
    DOCS / "FIELD_VALIDATION_BUYER_PILOT_PACKET_2026-06-25.md",
    DOCS / "FROZEN_DELTA_BUYER_OUTREACH_PACKET_2026-06-25.md",
]

BOUNDARY = (
    "This control room aggregates proof-to-pilot readiness. It can support manual reviewed outreach and paid "
    "evaluation scoping. It does not prove field validation, realized savings, fixed-dollar frozen-delta value, "
    "award certainty, bulk email permission, live trading, or autonomous operational execution."
)

DEFAULT_UNLOCK_CONDITIONS = [
    "buyer-authorized field data",
    "pre-registered holdout windows",
    "buyer-approved economic conversion factors",
    "baseline and candidate replay under identical constraints",
    "adverse-outcome and operator-burden guardrails",
    "signed or otherwise traceable pilot result artifact",
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


def load_buyer_packet_payload() -> dict[str, Any]:
    payload = read_json(BUYER_PACKET_JSON)
    if payload.get("packets"):
        return payload

    spec = importlib.util.spec_from_file_location("field_validation_buyer_packet_for_control_room", BUYER_PACKET_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_payload()


def artifact_row(path: Path) -> dict[str, Any]:
    exists = path.exists()
    digest = ""
    if exists:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "exists": exists,
        "sha256": digest,
    }


def first_by_family(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        family = str(row.get("family_id", ""))
        if family and family not in result:
            result[family] = row
    return result


def build_top_card(
    packet: dict[str, Any],
    protocol_by_family: dict[str, dict[str, Any]],
    uncertainty_by_family: dict[str, dict[str, Any]],
    repeat_by_family: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    family = str(packet.get("family_id", ""))
    protocol = protocol_by_family.get(family, {})
    uncertainty = uncertainty_by_family.get(family, {})
    repeat = repeat_by_family.get(family, {})
    email = packet.get("email", {})
    card = {
        "family_id": family,
        "lane": packet.get("lane", ""),
        "pilot_name": packet.get("pilot_name", ""),
        "commercial_stage": "manual_paid_pilot_outreach_ready",
        "evidence_stage": packet.get("evidence_stage", ""),
        "evidence_strength_score": packet.get("evidence_strength_score", 0),
        "repeat_window_evidence": {
            "wins": uncertainty.get("win_count", repeat.get("repeat_live_win_count", 0)),
            "windows": uncertainty.get("window_count", repeat.get("available_window_count", 0)),
            "min_delta": (uncertainty.get("delta_stats", {}) or {}).get("min_delta"),
            "lower_95_delta": (uncertainty.get("delta_stats", {}) or {}).get("normal_t_lower_95_delta"),
            "sign_test_p": uncertainty.get("one_sided_sign_test_p_value"),
            "min_source_count": protocol.get("evidence_summary", {}).get("min_source_count"),
            "distinct_win_hash_count": protocol.get("evidence_summary", {}).get("distinct_win_hash_count"),
        },
        "buyer_targets": packet.get("priority_buyer_titles", []),
        "pilot_question": packet.get("pilot_question", ""),
        "paid_offer": packet.get("paid_offer", {}),
        "email_subject": email.get("subject", ""),
        "data_room_artifacts": packet.get("data_room_artifacts", []),
        "next_actions": [
            "manually select 5 to 10 reviewed buyer or agency technical contacts",
            "send one targeted pilot-scoping email per contact",
            "ask for buyer-authorized field data or a paid technical evaluation",
            "pre-register at least 20 holdout windows before replay",
            "run incumbent baselines and candidate under identical constraints",
        ],
        "unlock_conditions": protocol.get("commercial_claim_unlock_requires") or DEFAULT_UNLOCK_CONDITIONS,
        "claim_gate": {
            "manual_outreach_allowed": True,
            "paid_evaluation_offer_allowed": True,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "fixed_dollar_delta_claim_allowed": False,
            "bulk_email_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
        },
    }
    card["card_sha256"] = stable_sha256(card)
    return card


def build_payload() -> dict[str, Any]:
    asset_map = read_json(ASSET_MAP_JSON)
    repeat = read_json(REPEAT_JSON)
    uncertainty = read_json(UNCERTAINTY_JSON)
    protocol = read_json(FIELD_PROTOCOL_JSON)
    buyer_packet = load_buyer_packet_payload()

    protocol_by_family = first_by_family(protocol.get("protocols", []))
    uncertainty_by_family = first_by_family(uncertainty.get("analyses", []))
    repeat_by_family = first_by_family(repeat.get("validations", []))
    top_cards = [
        build_top_card(packet, protocol_by_family, uncertainty_by_family, repeat_by_family)
        for packet in buyer_packet.get("packets", [])
        if isinstance(packet, dict)
    ]
    artifact_health = [artifact_row(path) for path in CHAIN_DOCS]
    all_docs_present = all(row["exists"] for row in artifact_health)
    control_gates = {
        "manual_reviewed_outreach_allowed": bool(top_cards),
        "paid_evaluation_offer_allowed": bool(top_cards),
        "buyer_authorized_pilot_scoping_ready": bool(top_cards),
        "field_validation_claim_allowed": False,
        "realized_savings_claim_allowed": False,
        "fixed_dollar_delta_claim_allowed": False,
        "bulk_email_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
    }
    summary = {
        "family_count": asset_map.get("summary", {}).get("family_count", 0),
        "natural_path_family_count": asset_map.get("summary", {}).get("natural_path_family_count", 0),
        "natural_path_target_met": asset_map.get("summary", {}).get("natural_path_target_met", False),
        "robust_candidate_count": uncertainty.get("summary", {}).get("robust_repeat_uncertainty_gate_passed_count", 0),
        "pilot_packet_count": buyer_packet.get("summary", {}).get("packet_count", len(top_cards)),
        "manual_outreach_ready_count": buyer_packet.get("summary", {}).get("manual_outreach_ready_count", len(top_cards)),
        "top_family_ids": [card["family_id"] for card in top_cards],
        "current_commercial_stage": "paid_evaluation_scoping_ready_not_field_validated" if top_cards else "not_ready",
        "all_chain_docs_present": all_docs_present,
        "control_room_chain_sha256": stable_sha256(
            {
                "asset_map": asset_map.get("summary", {}),
                "repeat": repeat.get("summary", {}),
                "uncertainty": uncertainty.get("summary", {}),
                "protocol": protocol.get("summary", {}),
                "buyer_packet": buyer_packet.get("summary", {}),
                "top_cards": top_cards,
                "artifact_health": artifact_health,
            }
        ),
        **control_gates,
    }
    return {
        "schema": "proof_to_pilot_control_room_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "geometry_champion_asset_map": str(ASSET_MAP_JSON.relative_to(ROOT)),
            "geometry_repeat_proof_validation": str(REPEAT_JSON.relative_to(ROOT)),
            "geometry_repeat_uncertainty_report": str(UNCERTAINTY_JSON.relative_to(ROOT)),
            "geometry_field_validation_protocol": str(FIELD_PROTOCOL_JSON.relative_to(ROOT)),
            "field_validation_buyer_pilot_packet": str(BUYER_PACKET_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "summary": summary,
        "top_cards": top_cards,
        "artifact_health": artifact_health,
        "claim_controls": {
            "allowed": [
                "manual reviewed outreach",
                "paid evaluation offer",
                "buyer-authorized pilot scoping",
                "grant or reviewer evidence appendix",
            ],
            "blocked": [
                "field validation already proven",
                "realized savings",
                "fixed-dollar frozen-delta value",
                "bulk email",
                "award certainty",
                "live trading or autonomous operational execution",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Proof To Pilot Control Room",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Current State",
        "",
        f"- Geometry families ranked: `{summary['family_count']}`",
        f"- Natural-path families: `{summary['natural_path_family_count']}`",
        f"- Natural-path target met: `{str(summary['natural_path_target_met']).lower()}`",
        f"- Robust repeat-window candidates: `{summary['robust_candidate_count']}`",
        f"- Buyer pilot packets: `{summary['pilot_packet_count']}`",
        f"- Manual outreach ready: `{summary['manual_outreach_ready_count']}`",
        f"- Commercial stage: `{summary['current_commercial_stage']}`",
        f"- All chain docs present: `{str(summary['all_chain_docs_present']).lower()}`",
        f"- Control-room chain SHA-256: `{summary['control_room_chain_sha256']}`",
        "",
        "## Gates",
        "",
        f"- Manual reviewed outreach allowed: `{str(summary['manual_reviewed_outreach_allowed']).lower()}`",
        f"- Paid evaluation offer allowed: `{str(summary['paid_evaluation_offer_allowed']).lower()}`",
        f"- Buyer-authorized pilot scoping ready: `{str(summary['buyer_authorized_pilot_scoping_ready']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Realized-savings claim allowed: `{str(summary['realized_savings_claim_allowed']).lower()}`",
        f"- Fixed-dollar delta claim allowed: `{str(summary['fixed_dollar_delta_claim_allowed']).lower()}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        "",
        "## Top Cards",
        "",
    ]
    for card in payload["top_cards"]:
        evidence = card["repeat_window_evidence"]
        lines.extend(
            [
                f"### `{card['family_id']}`",
                "",
                f"- Lane: `{card['lane']}`",
                f"- Pilot: {card['pilot_name']}",
                f"- Commercial stage: `{card['commercial_stage']}`",
                f"- Evidence: {evidence['wins']}/{evidence['windows']} positive windows, "
                f"min delta `{evidence['min_delta']}`, lower 95 delta `{evidence['lower_95_delta']}`, "
                f"minimum sources `{evidence['min_source_count']}`.",
                f"- Email subject: `{card['email_subject']}`",
                "- Next actions:",
            ]
        )
        for action in card["next_actions"]:
            lines.append(f"  - {action}")
    lines.extend(
        [
            "",
            "## Artifact Health",
            "",
            "| Artifact | Present | SHA-256 |",
            "| --- | --- | --- |",
        ]
    )
    for row in payload["artifact_health"]:
        digest = row["sha256"][:16] if row["sha256"] else ""
        lines.append(f"| `{row['path']}` | `{str(row['exists']).lower()}` | `{digest}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- The strongest current commercial action is manual paid-pilot outreach.",
            "- The next proof unlock is buyer-authorized field data with pre-registered holdout windows.",
            "- Real-dollar claims remain blocked until that pilot produces measured operational or economic deltas.",
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
                "commercial_stage": payload["summary"]["current_commercial_stage"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
