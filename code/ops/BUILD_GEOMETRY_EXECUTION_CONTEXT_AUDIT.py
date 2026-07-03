from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DATA = ROOT / "dashboard" / "data"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"

OUT_JSON = OUT_OPS / "geometry_execution_context_audit_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_execution_context_audit.json"
OUT_MD = DOCS / "GEOMETRY_EXECUTION_CONTEXT_AUDIT_2026-07-03.md"

BOUNDARY = (
    "Continuity and control audit only. It summarizes internal benchmark state, geometry coverage, real-noise "
    "readiness, and trading guardrails. It does not prove field validation, realized savings, fixed frozen-delta "
    "pricing, medical efficacy, safety certification, grant award certainty, or autonomous live trading permission."
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


def compact_trading_blockers(stack: dict[str, Any], code: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime_posture": stack.get("posture", "unknown"),
        "runtime_mode": stack.get("runtime", {}).get("mode"),
        "allow_live_orders": stack.get("runtime", {}).get("allow_live_orders"),
        "paper_enabled": stack.get("runtime", {}).get("paper_enabled"),
        "runtime_blockers": stack.get("blockers", [])[:8],
        "runtime_warnings": stack.get("warnings", [])[:8],
        "code_posture": code.get("posture", "unknown"),
        "code_blockers": code.get("blockers", [])[:8],
        "safe_spine": code.get("safe_spine", [])[:12],
        "operator_read": (
            "Trading research and paper execution can inform noisy-signal replay. Live execution remains blocked "
            "until fresh heartbeats, clean blockers, action-time approval, and guarded order paths are present."
        ),
    }


def build_payload() -> dict[str, Any]:
    geometry = read_json(DASHBOARD_DATA / "geometry_champion_of_champions.json")
    proof_queue = read_json(DASHBOARD_DATA / "geometry_live_breadth_proof_queue.json")
    proof_state = read_json(DASHBOARD_DATA / "current_luma_proof_state.json")
    stress = read_json(DASHBOARD_DATA / "champion_stress_test_matrix.json")
    live_sources = read_json(OUT_OPS / "live_source_measurement_maximizer_latest.json")
    real_noise = read_json(DASHBOARD_DATA / "real_noise_promotion_sweep.json")
    trading_stack = read_json(OUT_OPS / "trading_stack_safety_audit_latest.json")
    trading_code = read_json(OUT_OPS / "trading_code_risk_audit_latest.json")
    alpha_map = read_json(OUT_OPS / "kraken_multi_tf_alpha_map_latest.json")

    geo_summary = geometry.get("summary", {})
    champion = geometry.get("champion_of_champions", {}).get("strongest_current", {})
    gates = proof_state.get("gates", {})
    live_summary = live_sources.get("summary", {})
    real_noise_summary = real_noise.get("summary", {})
    stress_summary = stress.get("summary", {})

    rolling = proof_queue.get("rolling_champions", [])
    triple = proof_queue.get("triple_source_rolling_champions", [])

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "geometry_execution_context_audit_v1",
        "boundary": BOUNDARY,
        "geometry_state": {
            "registered_family_count": geo_summary.get("family_count"),
            "lane_count": geo_summary.get("lane_count"),
            "benchmark_specified_family_count": geo_summary.get("benchmark_specified_family_count"),
            "benchmark_specified_family_gap_count": geo_summary.get("benchmark_specified_family_gap_count"),
            "all_registered_families_live_benchmarked": geo_summary.get("all_registered_families_live_benchmarked", False),
            "rolling_champion_count": len(rolling),
            "triple_source_rolling_champion_count": len(triple),
            "current_strongest_family": champion.get("family"),
            "current_strongest_lane": champion.get("lane"),
            "current_strongest_status": champion.get("status"),
            "current_strongest_evidence_status": champion.get("evidence_status"),
            "latest_delta_vs_named_baseline": champion.get("latest_delta_vs_named_baseline"),
            "rolling_gate_repeat_live_win_count": champion.get("rolling_gate_repeat_live_win_count"),
            "distinct_run_hash_count": champion.get("distinct_run_hash_count"),
            "vesica_piscis_status": {
                "is_geometry_candidate": True,
                "registered_in_current_geometry_registry": False,
                "description": (
                    "Lens/overlap geometry from two equal circles whose centers lie on each other's circumference. "
                    "Best treated as an intersection, overlap-gating, resonance-coupling, or phase-window candidate."
                ),
                "claim_status": "candidate_not_benchmarked_not_a_winner",
                "next_test_lane": "lens_overlap_phase_gating",
            },
        },
        "kuramoto_and_stress_state": {
            "kuramoto_holdout_count": geo_summary.get("kuramoto_holdout_count"),
            "kuramoto_holdout_wins_vs_kalman": geo_summary.get("kuramoto_holdout_wins_vs_kalman"),
            "kuramoto_holdout_mean_delta_vs_kalman": geo_summary.get("kuramoto_holdout_mean_delta_vs_kalman"),
            "kuramoto_holdout_estimated_rows_replayed": geo_summary.get("kuramoto_holdout_estimated_rows_replayed"),
            "kuramoto_holdout_source_system_count": geo_summary.get("kuramoto_holdout_source_system_count"),
            "stress_matrix_holdout_count": stress_summary.get("holdout_compact"),
            "stress_metric_count": stress_summary.get("metric_stress_tests"),
            "stress_source_system_count": stress_summary.get("source_system_matrix"),
            "safe_read": (
                "Strong internal holdout evidence, especially for Kuramoto phase coupling, but still not external "
                "field validation because an outside owner has not approved held-out data, baseline, acceptance "
                "metric, and economic conversion."
            ),
        },
        "live_breadth_state": {
            "registry_enabled_sources": live_summary.get("enabled_sources"),
            "measured_sources": live_summary.get("measured_sources"),
            "failed_or_thin_sources": live_summary.get("failed_or_thin_sources"),
            "total_measured_rows": live_summary.get("total_measured_rows"),
            "measured_source_names": live_summary.get("measured_source_names", []),
            "failed_or_thin_source_names": live_summary.get("failed_or_thin_source_names", []),
            "real_noise_csv_snapshots_scanned": real_noise_summary.get("csv_snapshots_scanned"),
            "real_noise_rows_read": real_noise_summary.get("rows_read"),
            "real_noise_numeric_samples": real_noise_summary.get("numeric_samples"),
            "real_noise_ready_for_locked_replay": real_noise_summary.get("ready_for_locked_replay"),
            "real_noise_strong_candidates": real_noise_summary.get("strong_real_noise_candidates"),
            "real_noise_lanes_with_ready_data": real_noise_summary.get("lanes_with_ready_data"),
        },
        "claim_gates": gates,
        "trading_execution_state": compact_trading_blockers(trading_stack, trading_code),
        "alpha_research_state": {
            "alpha_map_present": bool(alpha_map),
            "alpha_map_keys": list(alpha_map.keys())[:20],
            "claim_status": "research_or_paper_only_until_trading_guardrails_clear",
        },
        "next_actions": [
            "Run locked replay on the 206 real-noise-ready datasets and write pass/fail deltas back into champion feeds.",
            "Register Vesica Piscis as a lens-overlap candidate and benchmark it against named baselines before using it in claims.",
            "Fix or quarantine legacy direct-order trading scripts before any live execution discussion.",
            "Keep outreach language centered on buyer-authorized field replay, not realized savings or guaranteed ROI.",
        ],
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    geo = payload["geometry_state"]
    live = payload["live_breadth_state"]
    trade = payload["trading_execution_state"]
    stress = payload["kuramoto_and_stress_state"]
    gates = payload["claim_gates"]

    lines = [
        "# Geometry Execution Context Audit",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Boundary",
        "",
        payload["boundary"],
        "",
        "## Geometry Coverage",
        "",
        f"- Registered geometry families: `{geo.get('registered_family_count')}`",
        f"- Geometry lanes: `{geo.get('lane_count')}`",
        f"- Families with benchmark specs: `{geo.get('benchmark_specified_family_count')}`",
        f"- Missing benchmark specs: `{geo.get('benchmark_specified_family_gap_count')}`",
        f"- All families live-benchmarked: `{geo.get('all_registered_families_live_benchmarked')}`",
        f"- Rolling champions: `{geo.get('rolling_champion_count')}`",
        f"- Triple-source rolling champions: `{geo.get('triple_source_rolling_champion_count')}`",
        "",
        "## Current Strongest Geometry",
        "",
        f"- Family: `{geo.get('current_strongest_family')}`",
        f"- Lane: `{geo.get('current_strongest_lane')}`",
        f"- Status: `{geo.get('current_strongest_status')}`",
        f"- Evidence status: `{geo.get('current_strongest_evidence_status')}`",
        f"- Latest delta vs named baseline: `{geo.get('latest_delta_vs_named_baseline')}`",
        f"- Repeat live-win count: `{geo.get('rolling_gate_repeat_live_win_count')}`",
        "",
        "## Kuramoto / Stress",
        "",
        f"- Kuramoto holdouts: `{stress.get('kuramoto_holdout_count')}`",
        f"- Wins vs Kalman: `{stress.get('kuramoto_holdout_wins_vs_kalman')}`",
        f"- Mean delta vs Kalman: `{stress.get('kuramoto_holdout_mean_delta_vs_kalman')}`",
        f"- Estimated rows replayed: `{stress.get('kuramoto_holdout_estimated_rows_replayed')}`",
        f"- Source systems in that holdout: `{stress.get('kuramoto_holdout_source_system_count')}`",
        "",
        stress.get("safe_read", ""),
        "",
        "## Vesica Piscis",
        "",
        f"- Candidate status: `{geo['vesica_piscis_status'].get('claim_status')}`",
        f"- Proposed lane: `{geo['vesica_piscis_status'].get('next_test_lane')}`",
        f"- Description: {geo['vesica_piscis_status'].get('description')}",
        "",
        "## Live Breadth",
        "",
        f"- Registry enabled sources: `{live.get('registry_enabled_sources')}`",
        f"- Measured sources: `{live.get('measured_sources')}`",
        f"- Failed or thin sources: `{live.get('failed_or_thin_sources')}`",
        f"- Total measured rows from maximizer: `{live.get('total_measured_rows')}`",
        f"- Real-noise CSV snapshots scanned: `{live.get('real_noise_csv_snapshots_scanned')}`",
        f"- Real-noise rows read: `{live.get('real_noise_rows_read')}`",
        f"- Real-noise numeric samples: `{live.get('real_noise_numeric_samples')}`",
        f"- Real-noise datasets ready for locked replay: `{live.get('real_noise_ready_for_locked_replay')}`",
        f"- Strong real-noise candidates: `{live.get('real_noise_strong_candidates')}`",
        "",
        "## Claim Gates",
        "",
    ]
    for key, value in gates.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Trading Execution Guardrails",
            "",
            f"- Runtime posture: `{trade.get('runtime_posture')}`",
            f"- Runtime mode: `{trade.get('runtime_mode')}`",
            f"- Live orders allowed: `{trade.get('allow_live_orders')}`",
            f"- Code posture: `{trade.get('code_posture')}`",
            "",
            "Runtime blockers:",
        ]
    )
    for blocker in trade.get("runtime_blockers", []):
        lines.append(f"- {blocker}")
    lines.append("")
    lines.append("Code blockers:")
    for blocker in trade.get("code_blockers", []):
        lines.append(f"- {blocker}")
    lines.extend(["", trade.get("operator_read", ""), "", "## Next Actions", ""])
    for item in payload["next_actions"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(json.dumps({
        "geometry_families": payload["geometry_state"].get("registered_family_count"),
        "all_live_benchmarked": payload["geometry_state"].get("all_registered_families_live_benchmarked"),
        "real_noise_ready": payload["live_breadth_state"].get("real_noise_ready_for_locked_replay"),
        "trading_posture": payload["trading_execution_state"].get("runtime_posture"),
        "out": str(OUT_JSON),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
