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

FIELD_PROTOCOL_JSON = OUT_OPS / "geometry_field_validation_protocol_latest.json"
FIELD_PROTOCOL_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_FIELD_VALIDATION_PROTOCOL.py"
KURAMOTO_HOLDOUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
KURAMOTO_HOLDOUT_SCRIPT = ROOT / "code" / "ops" / "BUILD_KURAMOTO_HOLDOUT_EXPANSION.py"

OUT_JSON = OUT_OPS / "field_validation_buyer_pilot_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_validation_buyer_pilot_packet.json"
OUT_MD = DOCS / "FIELD_VALIDATION_BUYER_PILOT_PACKET_2026-06-25.md"

BOUNDARY = (
    "This packet is for targeted manual buyer outreach and paid pilot scoping. It does not authorize bulk email, "
    "fixed-dollar frozen-delta claims, realized-savings claims, field-validation claims, live trading, or autonomous "
    "operational execution."
)

LANE_BUYER_PERSONAS: dict[str, dict[str, Any]] = {
    "optimal_curve_transport": {
        "priority_titles": [
            "Director of Grid Analytics",
            "Infrastructure Optimization Lead",
            "Port Operations Analytics Lead",
            "Datacenter Cooling Optimization Lead",
            "R&D Program Manager for Critical Infrastructure",
        ],
        "buyer_pain": "constraint-heavy routing, dispatch, airflow, or recovery decisions where small path-quality changes can reduce time, exposure, energy, or operator burden",
        "pilot_question": "Can the brachistochrone-style candidate beat incumbent route/path baselines on pre-registered buyer holdout windows without violating constraints?",
        "technical_hook": "6/6 positive frozen replay windows, minimum 5 sources per replay window, positive lower 95% margin.",
    },
    "wave_resonance_timing": {
        "priority_titles": [
            "Energy Forecasting Lead",
            "Grid Reliability Analytics Lead",
            "Sensor Fusion Program Manager",
            "Industrial Process Stability Lead",
            "R&D Program Manager for Cyber-Physical Systems",
        ],
        "buyer_pain": "oscillatory or cyclic systems where earlier timing, lower phase error, or better drift detection can reduce missed events and manual review",
        "pilot_question": "Can the Kuramoto-style candidate beat incumbent timing/forecast baselines on pre-registered buyer holdout windows?",
        "technical_hook": "24/24 internal source-conditioned holdout wins vs kalman_filter; ready to request buyer-authorized field replay.",
    },
}


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


def load_field_protocol_payload() -> dict[str, Any]:
    payload = read_json(FIELD_PROTOCOL_JSON)
    if payload.get("protocols"):
        return payload

    spec = importlib.util.spec_from_file_location("geometry_field_validation_protocol_for_buyer_packet", FIELD_PROTOCOL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_payload()


def load_kuramoto_holdout_payload() -> dict[str, Any]:
    payload = read_json(KURAMOTO_HOLDOUT_JSON)
    if payload.get("schema") == "kuramoto_holdout_expansion_v1" and payload.get("summary"):
        return payload

    if not KURAMOTO_HOLDOUT_SCRIPT.exists():
        return {}

    spec = importlib.util.spec_from_file_location("kuramoto_holdout_expansion_for_buyer_packet", KURAMOTO_HOLDOUT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    payload = module.build_payload()
    return payload if isinstance(payload, dict) else {}


def make_kuramoto_holdout_evidence(holdout_payload: dict[str, Any]) -> dict[str, Any]:
    summary = holdout_payload.get("summary", {})
    if not isinstance(summary, dict) or not summary:
        return {}
    return {
        "artifact": str(KURAMOTO_HOLDOUT_JSON.relative_to(ROOT)),
        "candidate": summary.get("candidate", "kuramoto_phase_coupling"),
        "named_baseline": summary.get("named_baseline", "kalman_filter"),
        "holdout_count": summary.get("holdout_count", 0),
        "wins_vs_kalman": summary.get("wins_vs_kalman", 0),
        "losses_or_ties_vs_kalman": summary.get("losses_or_ties_vs_kalman", 0),
        "win_rate_vs_kalman": summary.get("win_rate_vs_kalman", 0),
        "mean_delta_vs_kalman": summary.get("mean_delta_vs_kalman", 0),
        "min_delta_vs_kalman": summary.get("min_delta_vs_kalman", 0),
        "max_delta_vs_kalman": summary.get("max_delta_vs_kalman", 0),
        "wilson_95_win_rate_lower": summary.get("wilson_95_win_rate_lower", 0),
        "wilson_95_win_rate_upper": summary.get("wilson_95_win_rate_upper", 0),
        "one_sided_sign_test_p_value": summary.get("one_sided_sign_test_p_value", 0),
        "estimated_rows_replayed": summary.get("estimated_rows_replayed", 0),
        "numeric_samples_read": summary.get("numeric_samples_read", 0),
        "source_system_count": summary.get("source_system_count", 0),
        "source_systems": summary.get("source_systems", []),
        "passes_internal_20_holdout_gate": summary.get("passes_internal_20_holdout_gate", False),
        "ready_for_buyer_authorized_field_replay_request": summary.get(
            "ready_for_buyer_authorized_field_replay_request", False
        ),
        "holdout_chain_sha256": summary.get("holdout_chain_sha256", ""),
        "claim_boundary": holdout_payload.get("evidence_boundary", ""),
    }


def make_kuramoto_field_replay_protocol(holdout: dict[str, Any], rank: int) -> dict[str, Any]:
    protocol = {
        "rank": rank,
        "family_id": "kuramoto_phase_coupling",
        "lane": "wave_resonance_timing",
        "named_baseline": holdout.get("named_baseline", "kalman_filter"),
        "pilot_name": "Wave / Resonance Timing Forecast Pilot",
        "evidence_stage": "ready_for_buyer_authorized_pilot_scoping"
        if holdout.get("ready_for_buyer_authorized_field_replay_request")
        else "not_ready_for_field_validation_scoping",
        "evidence_summary": {
            "window_count": holdout.get("holdout_count", 0),
            "win_count": holdout.get("wins_vs_kalman", 0),
            "min_source_count": holdout.get("source_system_count", 0),
            "distinct_win_hash_count": holdout.get("holdout_count", 0),
            "min_delta": holdout.get("min_delta_vs_kalman", 0),
            "mean_delta": holdout.get("mean_delta_vs_kalman", 0),
            "normal_t_lower_95_delta": holdout.get("min_delta_vs_kalman", 0),
            "wilson_lower_95_win_rate": holdout.get("wilson_95_win_rate_lower", 0),
            "one_sided_sign_test_p_value": holdout.get("one_sided_sign_test_p_value", 1),
        },
        "buyer_segments": [
            "energy-market forecasting",
            "grid frequency or load forecasting analytics",
            "industrial process stability monitoring",
            "sensor drift and anomaly timing teams",
        ],
        "field_data_required": [
            "timestamped oscillatory or cyclic measurements",
            "incumbent forecast, filter, or timing-control baseline",
            "measured downstream outcome such as error, drift, outage lead time, or intervention cost",
            "known exogenous event markers where available",
            "holdout windows selected before model scoring",
        ],
        "baseline_controls": [
            "kalman_filter",
            "fft_peak_tracker",
            "arima_or_ets_forecast",
            "pll_phase_tracker",
            "seasonal_naive_forecast",
        ],
        "primary_kpis": [
            "candidate_score_delta_vs_named_baseline",
            "forecast_error_delta",
            "phase_error_delta",
            "lead_time_delta",
            "false_alarm_or_missed_event_delta",
        ],
        "acceptance_gate": {
            "minimum_holdout_windows": 20,
            "minimum_independent_source_or_sensor_count": 3,
            "minimum_candidate_win_rate": 0.6,
            "minimum_wilson_lower_95_win_rate": 0.5,
            "minimum_lower_95_delta": 0.0,
            "maximum_constraint_violation_rate": "buyer_defined_before_pilot",
            "required_result": "candidate must beat named baselines on pre-registered holdout windows without guardrail failure",
        },
        "commercial_claim_unlock_requires": [
            "buyer-authorized field data",
            "pre-registered holdout windows",
            "buyer-approved economic conversion factors",
            "baseline and candidate replay under identical constraints",
            "adverse-outcome and operator-burden guardrails",
            "signed or otherwise traceable pilot result artifact",
        ],
        "current_claim_gate": {
            "ready_for_field_validation_claim": False,
            "ready_for_real_dollar_claim": False,
            "ready_for_bulk_sales_claim": False,
            "ready_for_live_trading": False,
        },
        "next_action": "Use this as a buyer-authorized field replay request; do not present it as realized value.",
        "evidence_strength_score": round(
            100
            * (
                float(holdout.get("mean_delta_vs_kalman") or 0.0)
                + float(holdout.get("wilson_95_win_rate_lower") or 0.0)
                + min(1.0, float(holdout.get("source_system_count") or 0.0) / 5.0)
            ),
            3,
        ),
        "blockers": [],
    }
    protocol["protocol_sha256"] = stable_sha256(protocol)
    return protocol


def data_room_artifacts() -> list[str]:
    return [
        "docs/GEOMETRY_CHAMPION_ASSET_MAP_2026-06-25.md",
        "docs/GEOMETRY_REPEAT_PROOF_VALIDATION_2026-06-25.md",
        "docs/GEOMETRY_REPEAT_UNCERTAINTY_REPORT_2026-06-25.md",
        "docs/GEOMETRY_FIELD_VALIDATION_PROTOCOL_2026-06-25.md",
        "docs/KURAMOTO_HOLDOUT_EXPANSION_2026-06-26.md",
        "docs/FROZEN_DELTA_BUYER_OUTREACH_PACKET_2026-06-25.md",
    ]


def make_email(
    protocol: dict[str, Any],
    persona: dict[str, Any],
    latest_holdout_evidence: dict[str, Any] | None = None,
) -> dict[str, str]:
    family = str(protocol.get("family_id", ""))
    lane = str(protocol.get("lane", ""))
    pilot = str(protocol.get("pilot_name", ""))
    evidence = protocol.get("evidence_summary", {})
    latest_holdout_evidence = latest_holdout_evidence or {}
    if latest_holdout_evidence:
        holdout_lines = f"""- Expanded internal holdout: {latest_holdout_evidence.get('wins_vs_kalman')}/{latest_holdout_evidence.get('holdout_count')} wins vs {latest_holdout_evidence.get('named_baseline')}
- Mean delta vs {latest_holdout_evidence.get('named_baseline')}: {latest_holdout_evidence.get('mean_delta_vs_kalman')}
- Estimated rows replayed: {latest_holdout_evidence.get('estimated_rows_replayed')}
- Holdout chain SHA-256: {latest_holdout_evidence.get('holdout_chain_sha256')}"""
        follow_up_evidence = (
            f"{latest_holdout_evidence.get('wins_vs_kalman')}/{latest_holdout_evidence.get('holdout_count')} "
            f"internal holdout wins vs {latest_holdout_evidence.get('named_baseline')}"
        )
    else:
        holdout_lines = ""
        follow_up_evidence = f"repeat-window frozen replay evidence for {family}"
    subject = f"Paid pilot scoping: {pilot}"
    body = f"""Hello [Name],

I am Robert Ashworth, inventor of the LumenCore/NovaCore frozen evidence framework. I am reaching out because your team works near {persona['buyer_pain']}.

The current evidence is not a field-validation or savings claim. It is a narrower pilot-scoping signal:
- Candidate: {family}
- Lane: {lane}
- Repeat-window evidence: {evidence.get('win_count')}/{evidence.get('window_count')} positive frozen replay windows
- Lower 95% score-margin estimate: {evidence.get('normal_t_lower_95_delta')}
{holdout_lines}
- Current technical question: {persona['pilot_question']}

I am looking for one paid technical evaluation or buyer-authorized pilot where we replay the candidate against your incumbent baselines on pre-registered holdout windows. The output would be a claim-bounded evidence report: what improved, what failed, what cannot yet be claimed, and what would be required for a procurement-grade validation.

Would you be open to a 20-minute technical fit call this week?

Best,
Robert Ashworth
[Organization / LumenCore]
[Website or proof portal link]
[Physical mailing address]

To stop further outreach, reply "remove."
"""
    follow_up = f"""Hello [Name],

Following up once on the LumenCore/NovaCore pilot-scoping request.

The short version: we have {follow_up_evidence}, but the next real milestone is buyer-authorized field data. I am not asking you to accept a savings claim; I am asking whether your team would review a bounded pilot plan and decide if the evidence is worth testing on your holdout windows.

If you are not the right technical contact, who owns {pilot.lower()} or related analytics pilots on your team?

Best,
Robert Ashworth
"""
    return {
        "subject": subject,
        "first_email": body,
        "follow_up_email": follow_up,
    }


def make_packet(protocol: dict[str, Any], kuramoto_holdout_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    lane = str(protocol.get("lane", ""))
    persona = LANE_BUYER_PERSONAS.get(
        lane,
        {
            "priority_titles": ["Technical Evaluation Lead", "Innovation Program Manager"],
            "buyer_pain": "complex operational optimization problems",
            "pilot_question": "Can the candidate beat named baselines on pre-registered holdout data?",
            "technical_hook": "repeat-window candidate evidence with blocked commercial claims",
        },
    )
    latest_holdout_evidence = {}
    if protocol.get("family_id") == "kuramoto_phase_coupling":
        latest_holdout_evidence = make_kuramoto_holdout_evidence(kuramoto_holdout_payload or {})
    email = make_email(protocol, persona, latest_holdout_evidence)
    packet = {
        "family_id": protocol.get("family_id", ""),
        "lane": lane,
        "pilot_name": protocol.get("pilot_name", ""),
        "evidence_stage": protocol.get("evidence_stage", ""),
        "evidence_strength_score": protocol.get("evidence_strength_score", 0),
        "priority_buyer_titles": persona["priority_titles"],
        "buyer_pain": persona["buyer_pain"],
        "pilot_question": persona["pilot_question"],
        "technical_hook": persona["technical_hook"],
        "latest_holdout_evidence": latest_holdout_evidence,
        "field_replay_request": {
            "request_type": "buyer-authorized field replay on pre-registered holdout windows",
            "minimum_holdout_windows": 20,
            "required_buyer_inputs": [
                "accepted historical or operational field dataset",
                "incumbent baseline or current decision process",
                "pre-registered metric and pass/fail threshold",
                "forbidden tuning or lookahead rules",
                "guardrail conditions that stop the pilot",
                "buyer-approved economic conversion factors if dollar impact is later evaluated",
            ],
            "unlock_condition": "external owner signoff on data, baseline, metrics, logs, hashes, and result interpretation",
            "current_status": "ready_to_request_field_replay_not_yet_field_validated",
        },
        "paid_offer": {
            "offer_type": "paid technical evaluation or buyer-authorized pilot scoping",
            "pricing_status": "quote_after_fit_call_and_data_scope",
            "safe_positioning": "paid evaluation of a repeat-window candidate, not sale of guaranteed-value frozen deltas",
        },
        "deliverables": [
            "buyer-specific data checklist",
            "pre-registered holdout and baseline plan",
            "candidate replay against incumbent and named baselines",
            "uncertainty and failure-mode report",
            "claim-boundary memo separating proven evidence from unproven commercial claims",
            "pilot result artifact with hashable chain references",
        ],
        "data_room_artifacts": data_room_artifacts(),
        "buyer_data_checklist": protocol.get("field_data_required", []),
        "baseline_controls": protocol.get("baseline_controls", []),
        "primary_kpis": protocol.get("primary_kpis", []),
        "acceptance_gate": protocol.get("acceptance_gate", {}),
        "pre_call_questions": [
            "What operational decision or forecast would you want this to improve?",
            "What incumbent baseline does your team trust today?",
            "Can you provide at least 20 pre-registered holdout windows?",
            "Which measured outcome would make the pilot worth continuing?",
            "Which guardrail failure would stop the pilot immediately?",
            "Who can approve use of field data and economic conversion factors?",
        ],
        "sow_outline": [
            "Scope the buyer decision lane and incumbent baselines.",
            "Define permitted data fields, privacy boundaries, and holdout windows.",
            "Run baseline and candidate replay under identical constraints.",
            "Report win rate, lower-bound margin, failure cases, and guardrail results.",
            "Only discuss economic impact if buyer-provided conversion factors support it.",
        ],
        "email": email,
        "claim_gate": {
            "send_manually_to_reviewed_contacts": True,
            "bulk_email_allowed": False,
            "fixed_dollar_delta_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
        },
        "no_send_phrases": [
            "guaranteed savings",
            "field validated",
            "$10k per frozen delta",
            "guaranteed trading edge",
            "bulk government-ready assets",
        ],
    }
    packet["packet_sha256"] = stable_sha256(packet)
    return packet


def build_payload() -> dict[str, Any]:
    protocol_payload = load_field_protocol_payload()
    kuramoto_holdout_payload = load_kuramoto_holdout_payload()
    kuramoto_holdout_evidence = make_kuramoto_holdout_evidence(kuramoto_holdout_payload)
    protocols = [
        row
        for row in protocol_payload.get("protocols", [])
        if isinstance(row, dict) and row.get("evidence_stage") == "ready_for_buyer_authorized_pilot_scoping"
    ]
    protocol_family_ids = {str(row.get("family_id", "")) for row in protocols}
    if (
        "kuramoto_phase_coupling" not in protocol_family_ids
        and kuramoto_holdout_evidence.get("ready_for_buyer_authorized_field_replay_request")
    ):
        protocols.append(make_kuramoto_field_replay_protocol(kuramoto_holdout_evidence, len(protocols) + 1))
    packets = [make_packet(protocol, kuramoto_holdout_payload) for protocol in protocols]
    summary = {
        "packet_count": len(packets),
        "manual_outreach_ready_count": sum(1 for packet in packets if packet["claim_gate"]["send_manually_to_reviewed_contacts"]),
        "bulk_email_allowed": False,
        "fixed_dollar_delta_claim_allowed": False,
        "field_validation_claim_allowed": False,
        "realized_savings_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "top_packet_family_id": packets[0]["family_id"] if packets else "",
        "kuramoto_holdout_ready_for_field_replay_request": bool(
            kuramoto_holdout_evidence.get("ready_for_buyer_authorized_field_replay_request")
        ),
        "kuramoto_holdout_count": kuramoto_holdout_evidence.get("holdout_count", 0),
        "kuramoto_holdout_wins_vs_kalman": kuramoto_holdout_evidence.get("wins_vs_kalman", 0),
        "kuramoto_holdout_chain_sha256": kuramoto_holdout_evidence.get("holdout_chain_sha256", ""),
        "packet_chain_sha256": stable_sha256(packets),
    }
    return {
        "schema": "field_validation_buyer_pilot_packet_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "geometry_field_validation_protocol": str(FIELD_PROTOCOL_JSON.relative_to(ROOT)),
            "kuramoto_holdout_expansion": str(KURAMOTO_HOLDOUT_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "field_protocol_summary": protocol_payload.get("summary", {}),
        "summary": summary,
        "packets": packets,
        "claim_controls": {
            "allowed": [
                "manual reviewed outreach",
                "paid evaluation offer",
                "buyer-authorized pilot scoping",
                "field-data request",
            ],
            "blocked": [
                "bulk email",
                "fixed-dollar frozen-delta claim",
                "field validation already proven",
                "realized savings",
                "live trading or autonomous operational execution",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Field Validation Buyer Pilot Packet",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Buyer pilot packets: `{summary['packet_count']}`",
        f"- Manual outreach ready: `{summary['manual_outreach_ready_count']}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        f"- Fixed-dollar delta claim allowed: `{str(summary['fixed_dollar_delta_claim_allowed']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Kuramoto holdout ready for field replay request: `{str(summary['kuramoto_holdout_ready_for_field_replay_request']).lower()}`",
        f"- Kuramoto holdout wins vs Kalman: `{summary['kuramoto_holdout_wins_vs_kalman']}/{summary['kuramoto_holdout_count']}`",
        f"- Packet chain SHA-256: `{summary['packet_chain_sha256']}`",
        "",
        "## Packets",
        "",
    ]
    for packet in payload["packets"]:
        lines.extend(
            [
                f"### `{packet['family_id']}`",
                "",
                f"- Pilot: {packet['pilot_name']}",
                f"- Lane: `{packet['lane']}`",
                f"- Evidence stage: `{packet['evidence_stage']}`",
                f"- Evidence strength score: `{packet['evidence_strength_score']}`",
                f"- Buyer pain: {packet['buyer_pain']}",
                f"- Pilot question: {packet['pilot_question']}",
                f"- Field replay request: {packet['field_replay_request']['request_type']}",
                f"- Paid offer: {packet['paid_offer']['offer_type']}",
                f"- Pricing status: `{packet['paid_offer']['pricing_status']}`",
                "- Priority buyer titles:",
            ]
        )
        holdout = packet.get("latest_holdout_evidence", {})
        if holdout:
            lines.extend(
                [
                    "- Expanded internal holdout evidence:",
                    f"  - Wins vs `{holdout['named_baseline']}`: `{holdout['wins_vs_kalman']}/{holdout['holdout_count']}`",
                    f"  - Mean delta vs `{holdout['named_baseline']}`: `{holdout['mean_delta_vs_kalman']}`",
                    f"  - Estimated rows replayed: `{holdout['estimated_rows_replayed']}`",
                    f"  - Source systems: `{holdout['source_system_count']}`",
                    f"  - Internal 20-holdout gate passed: `{str(holdout['passes_internal_20_holdout_gate']).lower()}`",
                    f"  - Holdout chain SHA-256: `{holdout['holdout_chain_sha256']}`",
                    "  - Boundary: internal source-conditioned replay, not field validation or a dollar claim.",
                ]
            )
        for title in packet["priority_buyer_titles"]:
            lines.append(f"  - {title}")
        lines.append("- Deliverables:")
        for item in packet["deliverables"]:
            lines.append(f"  - {item}")
        lines.append("- Pre-call questions:")
        for question in packet["pre_call_questions"]:
            lines.append(f"  - {question}")
        lines.extend(
            [
                "",
                "Email subject:",
                "",
                f"```text\n{packet['email']['subject']}\n```",
                "",
                "First email:",
                "",
                f"```text\n{packet['email']['first_email'].rstrip()}\n```",
                "",
            ]
        )
    lines.extend(
        [
            "## Claim Boundary",
            "",
            "- Send manually only to reviewed contacts.",
            "- Do not run bulk outreach from this packet.",
            "- Do not claim fixed-dollar value per frozen delta.",
            "- Do not claim field validation or realized savings until a buyer-authorized pilot produces that evidence.",
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
                "packet_count": payload["summary"]["packet_count"],
                "manual_outreach_ready_count": payload["summary"]["manual_outreach_ready_count"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
