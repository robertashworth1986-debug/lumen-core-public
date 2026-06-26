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

BUYER_PACKET_JSON = OUT_OPS / "field_validation_buyer_pilot_packet_latest.json"
BUYER_PACKET_SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_VALIDATION_BUYER_PILOT_PACKET.py"
CHAMPION_BOARD_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
CHAMPION_BOARD_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_CHAMPION_OF_CHAMPIONS.py"
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


def load_builder_payload(script: Path, module_name: str) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(module_name, script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    payload = module.build_payload()
    return payload if isinstance(payload, dict) else {}


def load_buyer_packet_payload() -> dict[str, Any]:
    payload = read_json(BUYER_PACKET_JSON)
    if payload.get("schema") == "field_validation_buyer_pilot_packet_v1" and payload.get("packets"):
        return payload
    return load_builder_payload(BUYER_PACKET_SCRIPT, "field_validation_buyer_packet_for_kuramoto_request")


def load_champion_board_payload() -> dict[str, Any]:
    payload = read_json(CHAMPION_BOARD_JSON)
    if payload.get("schema") == "geometry_champion_of_champions_v1":
        return payload
    if CHAMPION_BOARD_SCRIPT.exists():
        return load_builder_payload(CHAMPION_BOARD_SCRIPT, "champion_board_for_kuramoto_request")
    return {}


def select_kuramoto_packet(payload: dict[str, Any]) -> dict[str, Any]:
    packets = payload.get("packets", [])
    if not isinstance(packets, list):
        return {}
    for packet in packets:
        if isinstance(packet, dict) and packet.get("family_id") == "kuramoto_phase_coupling":
            return packet
    return {}


def select_kuramoto_champion(payload: dict[str, Any]) -> dict[str, Any]:
    champion = payload.get("champion_of_champions", {})
    if isinstance(champion, dict):
        strongest = champion.get("strongest_current", {})
        if isinstance(strongest, dict) and strongest.get("family") == "kuramoto_phase_coupling":
            return strongest

    for key in ("families", "ranked_families", "family_rankings"):
        rows = payload.get(key, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("family") == "kuramoto_phase_coupling":
                return row
    return {}


def make_summary(packet: dict[str, Any], champion: dict[str, Any]) -> dict[str, Any]:
    holdout = packet.get("latest_holdout_evidence", {})
    if not isinstance(holdout, dict):
        holdout = {}
    return {
        "candidate": "kuramoto_phase_coupling",
        "lane": packet.get("lane", "wave_resonance_timing"),
        "pilot_name": packet.get("pilot_name", "Wave / Resonance Timing Forecast Pilot"),
        "current_status": "ready_to_request_field_replay_not_yet_field_validated",
        "manual_outreach_allowed": True,
        "bulk_email_allowed": False,
        "minimum_holdout_windows_requested": 20,
        "holdout_count": int(holdout.get("holdout_count") or 0),
        "wins_vs_kalman": int(holdout.get("wins_vs_kalman") or 0),
        "losses_or_ties_vs_kalman": int(holdout.get("losses_or_ties_vs_kalman") or 0),
        "win_rate_vs_kalman": float(holdout.get("win_rate_vs_kalman") or 0.0),
        "mean_delta_vs_kalman": float(holdout.get("mean_delta_vs_kalman") or 0.0),
        "min_delta_vs_kalman": float(holdout.get("min_delta_vs_kalman") or 0.0),
        "estimated_rows_replayed": int(holdout.get("estimated_rows_replayed") or 0),
        "source_system_count": int(holdout.get("source_system_count") or 0),
        "source_systems": holdout.get("source_systems", []),
        "wilson_95_win_rate_lower": float(holdout.get("wilson_95_win_rate_lower") or 0.0),
        "one_sided_sign_test_p_value": float(holdout.get("one_sided_sign_test_p_value") or 1.0),
        "holdout_chain_sha256": str(holdout.get("holdout_chain_sha256", "")),
        "champion_asset_score": champion.get("asset_score", 0),
        "champion_rank": champion.get("rank", 0),
        "champion_claim_stage": champion.get("claim_stage", ""),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
    }


def build_payload() -> dict[str, Any]:
    buyer_payload = load_buyer_packet_payload()
    champion_payload = load_champion_board_payload()
    packet = select_kuramoto_packet(buyer_payload)
    champion = select_kuramoto_champion(champion_payload)
    summary = make_summary(packet, champion)
    holdout = packet.get("latest_holdout_evidence", {}) if isinstance(packet, dict) else {}
    if not isinstance(holdout, dict):
        holdout = {}

    request_packet = {
        "one_sentence_ask": (
            "Authorize a field replay on pre-registered holdout windows so "
            "kuramoto_phase_coupling can be compared against the buyer's accepted incumbent baseline."
        ),
        "technical_question": packet.get(
            "pilot_question",
            "Can the Kuramoto-style candidate beat incumbent timing or forecast baselines on pre-registered buyer holdout windows?",
        ),
        "buyer_roles": packet.get("priority_buyer_titles", []),
        "data_required": packet.get("buyer_data_checklist", []),
        "baseline_controls": packet.get("baseline_controls", []),
        "primary_kpis": packet.get("primary_kpis", []),
        "acceptance_gate": packet.get("acceptance_gate", {}),
        "deliverables": packet.get("deliverables", []),
        "pre_call_questions": packet.get("pre_call_questions", []),
        "field_replay_request": packet.get("field_replay_request", {}),
    }

    payload = {
        "schema": "kuramoto_field_replay_request_v1",
        "generated_utc": now_utc(),
        "purpose": (
            "Convert the strongest current internal replay result into a buyer-authorized field replay request. "
            "This is a validation ask, not a completed field-validation claim."
        ),
        "summary": summary,
        "request_packet": request_packet,
        "evidence": {
            "latest_holdout_evidence": holdout,
            "champion_board_status": {
                "family": champion.get("family", "kuramoto_phase_coupling"),
                "asset_score": champion.get("asset_score", 0),
                "evidence_status": champion.get("evidence_status", ""),
                "claim_stage": champion.get("claim_stage", ""),
                "rank": champion.get("rank", 0),
                "ready_for_buyer_authorized_field_replay_request": champion.get(
                    "ready_for_buyer_authorized_field_replay_request", False
                ),
            },
            "source_artifacts": {
                "buyer_packet_json": str(BUYER_PACKET_JSON.relative_to(ROOT)),
                "champion_board_json": str(CHAMPION_BOARD_JSON.relative_to(ROOT)),
                "kuramoto_holdout_json": str(KURAMOTO_HOLDOUT_JSON.relative_to(ROOT)),
                "markdown": str(OUT_MD.relative_to(ROOT)),
            },
        },
        "email": packet.get("email", {}),
        "claim_boundary": {
            "not_field_validation": True,
            "not_realized_savings": True,
            "not_fixed_dollar_delta_value": True,
            "not_live_trading": True,
            "not_medical_or_addiction_treatment_evidence": True,
            "safe_statement": (
                "The current result supports a manual request for buyer-authorized replay. "
                "It does not prove external operational performance until the buyer controls the data, baseline, "
                "holdout windows, logs, and result interpretation."
            ),
        },
        "next_actions": [
            "Pick one external system owner with authority over a real operational or accepted historical holdout dataset.",
            "Pre-register at least 20 windows, the incumbent baseline, metrics, and pass/fail thresholds.",
            "Run the incumbent baseline and Kuramoto candidate under identical constraints with no tuning after seeing results.",
            "Hash the inputs, replay logs, outputs, and reviewer interpretation.",
            "Convert improvements to dollars only after the buyer approves the economic conversion factors.",
        ],
        "no_go_claims": [
            "field validated",
            "guaranteed savings",
            "$10k per frozen delta",
            "guaranteed trading edge",
            "proven institutional profit",
            "medical treatment claim",
        ],
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
    }
    payload["packet_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    request = payload["request_packet"]
    evidence = payload["evidence"]["latest_holdout_evidence"]
    email = payload.get("email", {})
    claim_boundary = payload["claim_boundary"]
    lines = [
        "# Kuramoto Field Replay Request",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["purpose"],
        "",
        "## Summary",
        "",
        f"- Candidate: `{summary['candidate']}`",
        f"- Lane: `{summary['lane']}`",
        f"- Status: `{summary['current_status']}`",
        f"- Internal holdout wins vs Kalman: `{summary['wins_vs_kalman']}/{summary['holdout_count']}`",
        f"- Mean delta vs Kalman: `{summary['mean_delta_vs_kalman']}`",
        f"- Estimated rows replayed: `{summary['estimated_rows_replayed']}`",
        f"- Source systems: `{summary['source_system_count']}`",
        f"- Wilson lower 95% win-rate bound: `{summary['wilson_95_win_rate_lower']}`",
        f"- Holdout chain SHA-256: `{summary['holdout_chain_sha256']}`",
        f"- Manual outreach allowed: `{str(summary['manual_outreach_allowed']).lower()}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        "",
        "## Why It Matters",
        "",
        "The evidence says this candidate is worth taking to a real owner-controlled replay. "
        "It does not say the candidate is already field validated. The next value step is to let a buyer or agency "
        "control the holdout data, accepted baseline, metrics, and result interpretation.",
        "",
        "## What We Can Ask For Now",
        "",
        request["one_sentence_ask"],
        "",
        f"Technical question: {request['technical_question']}",
        "",
        "Buyer roles:",
    ]
    lines.extend([f"- {role}" for role in request.get("buyer_roles", [])])
    lines.extend(["", "Data required:"])
    lines.extend([f"- {item}" for item in request.get("data_required", [])])
    lines.extend(["", "Baseline controls:"])
    lines.extend([f"- `{item}`" for item in request.get("baseline_controls", [])])
    lines.extend(["", "Primary KPIs:"])
    lines.extend([f"- `{item}`" for item in request.get("primary_kpis", [])])
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- Holdout count: `{evidence.get('holdout_count', 0)}`",
            f"- Wins vs `{evidence.get('named_baseline', 'kalman_filter')}`: `{evidence.get('wins_vs_kalman', 0)}`",
            f"- Losses or ties vs `{evidence.get('named_baseline', 'kalman_filter')}`: `{evidence.get('losses_or_ties_vs_kalman', 0)}`",
            f"- Estimated rows replayed: `{evidence.get('estimated_rows_replayed', 0)}`",
            f"- Numeric samples read: `{evidence.get('numeric_samples_read', 0)}`",
            f"- Source systems: `{', '.join(evidence.get('source_systems', []))}`",
            f"- Chain SHA-256: `{evidence.get('holdout_chain_sha256', '')}`",
            "",
            "## Buyer Replay Protocol",
            "",
            "Acceptance gate:",
            "",
            "```json",
            json.dumps(request.get("acceptance_gate", {}), indent=2, sort_keys=True, default=str),
            "```",
            "",
            "Pre-call questions:",
        ]
    )
    lines.extend([f"- {item}" for item in request.get("pre_call_questions", [])])
    lines.extend(
        [
            "",
            "## Manual Email Copy",
            "",
            f"Subject: {email.get('subject', '')}",
            "",
            "```text",
            email.get("first_email", "").strip(),
            "```",
            "",
            "## Claim Boundary",
            "",
            claim_boundary["safe_statement"],
            "",
            f"- Field-validation claim allowed: `{str(not claim_boundary['not_field_validation']).lower()}`",
            f"- Realized savings claim allowed: `{str(not claim_boundary['not_realized_savings']).lower()}`",
            f"- Fixed-dollar delta value claim allowed: `{str(not claim_boundary['not_fixed_dollar_delta_value']).lower()}`",
            f"- Live trading claim allowed: `{str(not claim_boundary['not_live_trading']).lower()}`",
            "",
            "No-go claims:",
        ]
    )
    lines.extend([f"- `{claim}`" for claim in payload["no_go_claims"]])
    lines.extend(["", f"Packet SHA-256: `{payload['packet_sha256']}`"])
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    summary = payload["summary"]
    print(
        "Kuramoto field replay request built: "
        f"{summary['wins_vs_kalman']}/{summary['holdout_count']} wins vs Kalman; "
        f"status={summary['current_status']}"
    )


if __name__ == "__main__":
    main()
