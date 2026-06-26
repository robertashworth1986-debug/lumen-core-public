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

CHAMPION_BOARD_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
CHAMPION_BOARD_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_CHAMPION_OF_CHAMPIONS.py"
KURAMOTO_REQUEST_JSON = OUT_OPS / "kuramoto_field_replay_request_latest.json"
KURAMOTO_REQUEST_SCRIPT = ROOT / "code" / "ops" / "BUILD_KURAMOTO_FIELD_REPLAY_REQUEST.py"
BUYER_PACKET_JSON = OUT_OPS / "field_validation_buyer_pilot_packet_latest.json"
BUYER_PACKET_SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_VALIDATION_BUYER_PILOT_PACKET.py"

OUT_JSON = OUT_OPS / "field_validation_control_room_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "field_validation_control_room.json"
OUT_MD = DOCS / "FIELD_VALIDATION_CONTROL_ROOM_2026-06-26.md"


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


def load_or_build_json(path: Path, script: Path, schema: str, module_name: str) -> dict[str, Any]:
    payload = read_json(path)
    if payload.get("schema") == schema:
        return payload
    return load_builder_payload(script, module_name)


def selected_family(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": row.get("family", ""),
        "label": row.get("label", ""),
        "lane": row.get("lane", ""),
        "rank": row.get("rank", 0),
        "asset_score": row.get("asset_score", 0),
        "evidence_status": row.get("evidence_status", ""),
        "claim_stage": row.get("claim_stage", ""),
        "rolling_gate_status": row.get("rolling_gate_status", ""),
        "rolling_gate_repeat_live_win_count": row.get("rolling_gate_repeat_live_win_count", 0),
        "rolling_gate_distinct_run_hash_count": row.get("rolling_gate_distinct_run_hash_count", 0),
        "natural_logic": row.get("natural_logic", ""),
        "benchmark_hypothesis": row.get("benchmark_hypothesis", ""),
        "promotion_metric": row.get("promotion_metric", ""),
        "failure_mode": row.get("failure_mode", ""),
        "paid_pilot_ready": bool(row.get("paid_pilot_ready", False)),
        "manual_outreach_allowed": bool(row.get("manual_outreach_allowed", False)),
        "ready_for_field_validation_claim": bool(row.get("ready_for_field_validation_claim", False)),
        "ready_for_real_dollar_claim": bool(row.get("ready_for_real_dollar_claim", False)),
        "kraken_live_execution_allowed": bool(row.get("kraken_live_execution_allowed", False)),
    }


def top_family_rows(champion_board: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    rows = champion_board.get("family_asset_rankings", [])
    if not isinstance(rows, list):
        return []
    selected: list[dict[str, Any]] = []
    for row in rows[:limit]:
        if isinstance(row, dict):
            selected.append(selected_family(row))
    return selected


def select_packet(buyer_packet: dict[str, Any], family_id: str) -> dict[str, Any]:
    packets = buyer_packet.get("packets", [])
    if not isinstance(packets, list):
        return {}
    for packet in packets:
        if isinstance(packet, dict) and packet.get("family_id") == family_id:
            return packet
    return {}


def build_claim_ladder(kuramoto_request: dict[str, Any], champion_board: dict[str, Any]) -> list[dict[str, Any]]:
    summary = kuramoto_request.get("summary", {})
    if not isinstance(summary, dict):
        summary = {}
    truth_gates = champion_board.get("current_truth_gates", {})
    if not isinstance(truth_gates, dict):
        truth_gates = {}
    return [
        {
            "stage": "internal_live_replay",
            "status": "passed",
            "evidence": (
                f"{summary.get('wins_vs_kalman', 0)}/{summary.get('holdout_count', 0)} wins vs Kalman; "
                f"{summary.get('estimated_rows_replayed', 0)} estimated rows replayed"
            ),
            "claim_allowed": "internal source-conditioned replay winner",
        },
        {
            "stage": "buyer_authorized_field_replay_request",
            "status": "ready",
            "evidence": "request packet built with buyer data checklist, baselines, KPIs, acceptance gates, and manual email copy",
            "claim_allowed": "ready to request buyer-authorized field replay",
        },
        {
            "stage": "field_validation",
            "status": "blocked_until_external_owner_replay",
            "evidence": "missing buyer or agency controlled replay and result interpretation",
            "claim_allowed": bool(truth_gates.get("field_validation_claim_allowed", False)),
        },
        {
            "stage": "real_dollar_claim",
            "status": "blocked_until_buyer_approved_economics",
            "evidence": "missing buyer-approved cost factors and signed conversion from technical improvement to dollars",
            "claim_allowed": bool(truth_gates.get("real_dollar_savings_claim_allowed", False)),
        },
        {
            "stage": "live_execution_or_trading",
            "status": "blocked",
            "evidence": "research and buyer-pilot assets are not live autonomous execution authorization",
            "claim_allowed": bool(truth_gates.get("live_trading_or_autonomous_execution_allowed", False)),
        },
    ]


def build_payload() -> dict[str, Any]:
    champion_board = load_or_build_json(
        CHAMPION_BOARD_JSON,
        CHAMPION_BOARD_SCRIPT,
        "geometry_champion_of_champions_v1",
        "champion_board_for_field_validation_control_room",
    )
    kuramoto_request = load_or_build_json(
        KURAMOTO_REQUEST_JSON,
        KURAMOTO_REQUEST_SCRIPT,
        "kuramoto_field_replay_request_v1",
        "kuramoto_request_for_field_validation_control_room",
    )
    buyer_packet = load_or_build_json(
        BUYER_PACKET_JSON,
        BUYER_PACKET_SCRIPT,
        "field_validation_buyer_pilot_packet_v1",
        "buyer_packet_for_field_validation_control_room",
    )

    champion = champion_board.get("champion_of_champions", {})
    if not isinstance(champion, dict):
        champion = {}
    strongest = selected_family(champion.get("strongest_current", {}) if isinstance(champion.get("strongest_current", {}), dict) else {})
    buyer_card = selected_family(champion.get("best_buyer_pilot_card", {}) if isinstance(champion.get("best_buyer_pilot_card", {}), dict) else {})
    kuramoto_summary = kuramoto_request.get("summary", {})
    if not isinstance(kuramoto_summary, dict):
        kuramoto_summary = {}
    kuramoto_packet = select_packet(buyer_packet, "kuramoto_phase_coupling")
    brach_packet = select_packet(buyer_packet, "brachistochrone_descent")

    control_room = {
        "schema": "field_validation_control_room_v1",
        "generated_utc": now_utc(),
        "purpose": (
            "One reviewer/buyer control surface for the strongest geometry evidence, current claim gates, "
            "field-validation blockers, and next validation actions."
        ),
        "summary": {
            "strongest_current_family": strongest.get("family", ""),
            "strongest_current_lane": strongest.get("lane", ""),
            "strongest_current_asset_score": strongest.get("asset_score", 0),
            "strongest_current_status": kuramoto_summary.get(
                "current_status", "ready_to_request_field_replay_not_yet_field_validated"
            ),
            "kuramoto_holdout_wins_vs_kalman": kuramoto_summary.get("wins_vs_kalman", 0),
            "kuramoto_holdout_count": kuramoto_summary.get("holdout_count", 0),
            "kuramoto_estimated_rows_replayed": kuramoto_summary.get("estimated_rows_replayed", 0),
            "kuramoto_source_system_count": kuramoto_summary.get("source_system_count", 0),
            "best_buyer_pilot_family": buyer_card.get("family", ""),
            "best_buyer_pilot_lane": buyer_card.get("lane", ""),
            "manual_outreach_ready": True,
            "bulk_email_allowed": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
        },
        "top_assets": {
            "strongest_current": strongest,
            "best_buyer_pilot_card": buyer_card,
            "top_family_asset_rankings": top_family_rows(champion_board, 5),
        },
        "proof_bridge": {
            "internal_replay_result": {
                "candidate": kuramoto_summary.get("candidate", "kuramoto_phase_coupling"),
                "named_baseline": "kalman_filter",
                "wins": kuramoto_summary.get("wins_vs_kalman", 0),
                "windows": kuramoto_summary.get("holdout_count", 0),
                "mean_delta": kuramoto_summary.get("mean_delta_vs_kalman", 0),
                "wilson_lower_95": kuramoto_summary.get("wilson_95_win_rate_lower", 0),
                "estimated_rows_replayed": kuramoto_summary.get("estimated_rows_replayed", 0),
                "source_systems": kuramoto_summary.get("source_systems", []),
                "chain_sha256": kuramoto_summary.get("holdout_chain_sha256", ""),
            },
            "field_replay_request": kuramoto_request.get("request_packet", {}),
            "claim_ladder": build_claim_ladder(kuramoto_request, champion_board),
        },
        "buyer_tracks": [
            {
                "family_id": "kuramoto_phase_coupling",
                "pilot_name": kuramoto_packet.get("pilot_name", ""),
                "priority_buyer_titles": kuramoto_packet.get("priority_buyer_titles", []),
                "technical_question": kuramoto_packet.get("pilot_question", ""),
                "manual_email_subject": kuramoto_packet.get("email", {}).get("subject", "")
                if isinstance(kuramoto_packet.get("email", {}), dict)
                else "",
            },
            {
                "family_id": "brachistochrone_descent",
                "pilot_name": brach_packet.get("pilot_name", ""),
                "priority_buyer_titles": brach_packet.get("priority_buyer_titles", []),
                "technical_question": brach_packet.get("pilot_question", ""),
                "manual_email_subject": brach_packet.get("email", {}).get("subject", "")
                if isinstance(brach_packet.get("email", {}), dict)
                else "",
            },
        ],
        "next_10_actions": [
            "Use the Kuramoto field replay request as the primary buyer-facing validation ask.",
            "Select one energy/grid, forecasting, sensor-fusion, or industrial-stability owner with real holdout data.",
            "Ask for 20 pre-registered windows and their accepted incumbent baseline before any replay.",
            "Freeze the buyer baseline, metrics, pass/fail threshold, and forbidden tuning rules.",
            "Run candidate and incumbent under identical constraints.",
            "Hash inputs, logs, outputs, and the interpretation memo.",
            "Record failures as first-class evidence rather than deleting them.",
            "Only convert to dollars after the buyer supplies accepted economic conversion factors.",
            "Keep brachistochrone as the second paid-pilot lane for constrained transport/routing.",
            "Do not use field-validation or fixed-dollar language until the external replay passes.",
        ],
        "dashboard_cards": [
            {
                "title": "Strongest Current Asset",
                "metric": f"{kuramoto_summary.get('wins_vs_kalman', 0)}/{kuramoto_summary.get('holdout_count', 0)}",
                "subtitle": "Kuramoto wins vs Kalman on internal source-conditioned holdouts",
                "status": "request-field-replay",
            },
            {
                "title": "Claim Gate",
                "metric": "not field validated",
                "subtitle": "External owner-controlled replay still required",
                "status": "blocked-until-buyer-replay",
            },
            {
                "title": "Rows Replayed",
                "metric": str(kuramoto_summary.get("estimated_rows_replayed", 0)),
                "subtitle": "Estimated internal replay rows across measured source systems",
                "status": "internal-evidence",
            },
            {
                "title": "Next Commercial Step",
                "metric": "paid pilot",
                "subtitle": "Manual outreach to one qualified owner, not bulk claims",
                "status": "manual-outreach-only",
            },
        ],
        "claim_controls": {
            "allowed": [
                "internal source-conditioned replay evidence",
                "ready to request buyer-authorized field replay",
                "manual paid-pilot scoping outreach",
                "bounded technical evaluation proposal",
            ],
            "blocked": [
                "field validation already proven",
                "realized dollar savings",
                "fixed dollar value per frozen delta",
                "guaranteed trading or institutional profit",
                "medical or addiction treatment claims",
                "bulk outreach",
            ],
        },
        "inputs": {
            "champion_board": str(CHAMPION_BOARD_JSON.relative_to(ROOT)),
            "kuramoto_field_replay_request": str(KURAMOTO_REQUEST_JSON.relative_to(ROOT)),
            "buyer_pilot_packet": str(BUYER_PACKET_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
    }
    control_room["control_room_sha256"] = stable_sha256(control_room)
    return control_room


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    bridge = payload["proof_bridge"]["internal_replay_result"]
    top_assets = payload["top_assets"]
    lines = [
        "# Field Validation Control Room",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["purpose"],
        "",
        "## Current Truth",
        "",
        f"- Strongest current family: `{summary['strongest_current_family']}`",
        f"- Lane: `{summary['strongest_current_lane']}`",
        f"- Asset score: `{summary['strongest_current_asset_score']}`",
        f"- Status: `{summary['strongest_current_status']}`",
        f"- Internal wins vs Kalman: `{summary['kuramoto_holdout_wins_vs_kalman']}/{summary['kuramoto_holdout_count']}`",
        f"- Estimated rows replayed: `{summary['kuramoto_estimated_rows_replayed']}`",
        f"- Source systems: `{summary['kuramoto_source_system_count']}`",
        f"- Best secondary buyer-pilot family: `{summary['best_buyer_pilot_family']}`",
        "",
        "## Claim Gates",
        "",
        f"- Manual outreach ready: `{str(summary['manual_outreach_ready']).lower()}`",
        f"- Bulk email allowed: `{str(summary['bulk_email_allowed']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
        f"- Fixed-dollar delta claim allowed: `{str(summary['fixed_dollar_delta_claim_allowed']).lower()}`",
        f"- Live autonomous execution allowed: `{str(summary['live_trading_or_autonomous_execution_allowed']).lower()}`",
        "",
        "## Strongest Proof Bridge",
        "",
        f"- Candidate: `{bridge['candidate']}`",
        f"- Baseline: `{bridge['named_baseline']}`",
        f"- Holdout result: `{bridge['wins']}/{bridge['windows']}`",
        f"- Mean delta: `{bridge['mean_delta']}`",
        f"- Wilson lower 95%: `{bridge['wilson_lower_95']}`",
        f"- Chain SHA-256: `{bridge['chain_sha256']}`",
        "",
        "This supports a field-replay request. It does not establish field validation or a realized-dollar claim.",
        "",
        "## Top Assets",
        "",
    ]
    for row in top_assets.get("top_family_asset_rankings", []):
        lines.extend(
            [
                f"### `{row['family']}`",
                "",
                f"- Lane: `{row['lane']}`",
                f"- Asset score: `{row['asset_score']}`",
                f"- Evidence status: `{row['evidence_status']}`",
                f"- Claim stage: `{row['claim_stage']}`",
                f"- Benchmark hypothesis: {row['benchmark_hypothesis']}",
                "",
            ]
        )
    lines.extend(["## Claim Ladder", ""])
    for row in payload["proof_bridge"]["claim_ladder"]:
        lines.extend(
            [
                f"- `{row['stage']}`: `{row['status']}`",
                f"  Evidence: {row['evidence']}",
                f"  Claim allowed: `{row['claim_allowed']}`",
            ]
        )
    lines.extend(["", "## Next 10 Actions", ""])
    lines.extend([f"{i}. {item}" for i, item in enumerate(payload["next_10_actions"], start=1)])
    lines.extend(["", "## Dashboard Cards", ""])
    for card in payload["dashboard_cards"]:
        lines.extend(
            [
                f"- {card['title']}: `{card['metric']}`",
                f"  {card['subtitle']} (`{card['status']}`)",
            ]
        )
    lines.extend(["", "## Blocked Claims", ""])
    lines.extend([f"- `{item}`" for item in payload["claim_controls"]["blocked"]])
    lines.extend(["", f"Control room SHA-256: `{payload['control_room_sha256']}`"])
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    summary = payload["summary"]
    print(
        "Field validation control room built: "
        f"{summary['strongest_current_family']} "
        f"{summary['kuramoto_holdout_wins_vs_kalman']}/{summary['kuramoto_holdout_count']} wins; "
        f"field_validation_claim_allowed={summary['field_validation_claim_allowed']}"
    )


if __name__ == "__main__":
    main()
