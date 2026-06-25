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

UNCERTAINTY_JSON = OUT_OPS / "geometry_repeat_uncertainty_report_latest.json"
UNCERTAINTY_SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_REPEAT_UNCERTAINTY_REPORT.py"

OUT_JSON = OUT_OPS / "geometry_field_validation_protocol_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_field_validation_protocol.json"
OUT_MD = DOCS / "GEOMETRY_FIELD_VALIDATION_PROTOCOL_2026-06-25.md"

BOUNDARY = (
    "This protocol converts robust repeat-window candidates into buyer- or agency-authorized validation plans. "
    "It does not itself prove field validation, realized savings, procurement value, or trading edge."
)

LANE_PROTOCOLS: dict[str, dict[str, Any]] = {
    "optimal_curve_transport": {
        "pilot_name": "Constrained Transport / Routing Replay Pilot",
        "buyer_segments": [
            "grid operations analytics",
            "water/hydrology infrastructure analytics",
            "port or maritime routing analytics",
            "datacenter airflow/cooling path optimization",
        ],
        "field_data_required": [
            "timestamped constraint windows with obstacles, limits, or route/path decisions",
            "the incumbent route/path or dispatch decision used at the time",
            "measured outcome such as latency, energy, loss, exposure, or recovery time",
            "cost or risk conversion factors supplied by the buyer",
            "holdout windows selected before model scoring",
        ],
        "named_baseline_controls": [
            "minimum_jerk_curve",
            "straight_line_path",
            "spline_path",
            "rrt_star",
            "min_cost_flow_or_dijkstra_when_graph_data_exists",
        ],
        "primary_kpis": [
            "candidate_score_delta_vs_named_baseline",
            "constraint_violation_rate",
            "measured_outcome_delta",
            "operator_review_burden_delta",
        ],
    },
    "wave_resonance_timing": {
        "pilot_name": "Wave / Resonance Timing Forecast Pilot",
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
        "named_baseline_controls": [
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


def load_uncertainty_payload() -> dict[str, Any]:
    payload = read_json(UNCERTAINTY_JSON)
    if payload.get("analyses"):
        return payload

    spec = importlib.util.spec_from_file_location("geometry_repeat_uncertainty_for_field_protocol", UNCERTAINTY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.build_payload()


def evidence_strength(row: dict[str, Any]) -> float:
    stats = row.get("delta_stats", {})
    lower_margin = float(stats.get("normal_t_lower_95_delta") or 0.0)
    min_delta = float(stats.get("min_delta") or 0.0)
    wilson = float(row.get("wilson_lower_95_win_rate") or 0.0)
    sign_component = max(0.0, 0.05 - float(row.get("one_sided_sign_test_p_value") or 1.0))
    source_component = min(1.0, float(row.get("min_source_count") or 0.0) / 5.0)
    return round(100 * (lower_margin + min_delta + wilson + sign_component + source_component), 3)


def build_protocol(row: dict[str, Any], rank: int) -> dict[str, Any]:
    lane = str(row.get("lane", ""))
    lane_protocol = LANE_PROTOCOLS.get(lane, {})
    stats = row.get("delta_stats", {})
    robust = bool(row.get("robust_repeat_uncertainty_gate_passed"))
    protocol = {
        "rank": rank,
        "family_id": row.get("family_id", ""),
        "lane": lane,
        "named_baseline": row.get("named_baseline", ""),
        "pilot_name": lane_protocol.get("pilot_name", f"{lane} validation pilot"),
        "evidence_stage": "ready_for_buyer_authorized_pilot_scoping"
        if robust
        else "not_ready_for_field_validation_scoping",
        "evidence_summary": {
            "window_count": row.get("window_count", 0),
            "win_count": row.get("win_count", 0),
            "min_source_count": row.get("min_source_count", 0),
            "distinct_win_hash_count": row.get("distinct_win_hash_count", 0),
            "min_delta": stats.get("min_delta"),
            "mean_delta": stats.get("mean_delta"),
            "normal_t_lower_95_delta": stats.get("normal_t_lower_95_delta"),
            "wilson_lower_95_win_rate": row.get("wilson_lower_95_win_rate"),
            "one_sided_sign_test_p_value": row.get("one_sided_sign_test_p_value"),
        },
        "buyer_segments": lane_protocol.get("buyer_segments", []),
        "field_data_required": lane_protocol.get("field_data_required", []),
        "baseline_controls": lane_protocol.get("named_baseline_controls", []),
        "primary_kpis": lane_protocol.get("primary_kpis", []),
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
        "next_action": "Use this as a paid evaluation or pilot-scoping offer; do not present it as realized value.",
        "evidence_strength_score": evidence_strength(row),
        "blockers": row.get("blockers", []),
    }
    protocol["protocol_sha256"] = stable_sha256(protocol)
    return protocol


def build_payload() -> dict[str, Any]:
    uncertainty = load_uncertainty_payload()
    robust_rows = [
        row
        for row in uncertainty.get("analyses", [])
        if isinstance(row, dict) and row.get("robust_repeat_uncertainty_gate_passed")
    ]
    robust_rows.sort(key=evidence_strength, reverse=True)
    protocols = [build_protocol(row, index + 1) for index, row in enumerate(robust_rows)]
    summary = {
        "protocol_count": len(protocols),
        "top_family_id": protocols[0]["family_id"] if protocols else "",
        "top_lane": protocols[0]["lane"] if protocols else "",
        "ready_for_buyer_authorized_pilot_scoping_count": sum(
            1 for row in protocols if row["evidence_stage"] == "ready_for_buyer_authorized_pilot_scoping"
        ),
        "ready_for_field_validation_claim": False,
        "ready_for_real_dollar_claim": False,
        "ready_for_bulk_sales_claim": False,
        "ready_for_live_trading": False,
        "protocol_chain_sha256": stable_sha256(protocols),
    }
    return {
        "schema": "geometry_field_validation_protocol_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "geometry_repeat_uncertainty_report": str(UNCERTAINTY_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "uncertainty_summary": uncertainty.get("summary", {}),
        "summary": summary,
        "protocols": protocols,
        "claim_controls": {
            "allowed": [
                "paid evaluation offer",
                "pilot scoping",
                "buyer-authorized field-data request",
                "pre-registered holdout validation plan",
            ],
            "blocked": [
                "field validation already proven",
                "realized savings",
                "fixed-dollar delta claim",
                "bulk frozen-delta sales claim",
                "live trading or autonomous operational execution",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Field Validation Protocol",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Protocols generated: `{summary['protocol_count']}`",
        f"- Pilot-scoping ready: `{summary['ready_for_buyer_authorized_pilot_scoping_count']}`",
        f"- Top family: `{summary['top_family_id']}`",
        f"- Top lane: `{summary['top_lane']}`",
        f"- Ready for field-validation claim: `{str(summary['ready_for_field_validation_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Ready for bulk sales claim: `{str(summary['ready_for_bulk_sales_claim']).lower()}`",
        f"- Protocol chain SHA-256: `{summary['protocol_chain_sha256']}`",
        "",
        "## Protocols",
        "",
    ]
    for protocol in payload["protocols"]:
        evidence = protocol["evidence_summary"]
        lines.extend(
            [
                f"### {protocol['rank']}. `{protocol['family_id']}`",
                "",
                f"- Lane: `{protocol['lane']}`",
                f"- Pilot: {protocol['pilot_name']}",
                f"- Evidence stage: `{protocol['evidence_stage']}`",
                f"- Evidence: {evidence['win_count']}/{evidence['window_count']} repeat windows, "
                f"min delta `{evidence['min_delta']}`, lower 95 delta `{evidence['normal_t_lower_95_delta']}`, "
                f"minimum sources `{evidence['min_source_count']}`.",
                f"- Evidence strength score: `{protocol['evidence_strength_score']}`",
                "- Buyer data required:",
            ]
        )
        for item in protocol["field_data_required"]:
            lines.append(f"  - {item}")
        lines.append("- Acceptance gate:")
        gate = protocol["acceptance_gate"]
        lines.append(
            f"  - At least `{gate['minimum_holdout_windows']}` pre-registered holdout windows, "
            f"`{gate['minimum_independent_source_or_sensor_count']}` independent sources/sensors, "
            f"candidate win rate >= `{gate['minimum_candidate_win_rate']}`, "
            f"Wilson lower win rate >= `{gate['minimum_wilson_lower_95_win_rate']}`, "
            f"lower 95 delta > `{gate['minimum_lower_95_delta']}`."
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- The current proof supports paid evaluation and pilot scoping.",
            "- Real-dollar claims require buyer-approved economic conversion factors and a completed field-data pilot.",
            "- Bulk frozen-delta sales claims remain blocked.",
            "- Live trading or autonomous operational execution remains blocked.",
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
                "protocol_count": payload["summary"]["protocol_count"],
                "top_family_id": payload["summary"]["top_family_id"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
