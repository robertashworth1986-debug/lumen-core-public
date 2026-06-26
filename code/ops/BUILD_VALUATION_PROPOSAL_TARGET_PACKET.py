from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

READY_REPLAY_JSON = OUT_OPS / "geometry_ready_source_replay_latest.json"
SOURCE_MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"
CUMBERLAND_NOTE = Path(r"C:\Users\Novac\iCloudDrive\Cumberland Science Museum pilot work\text 7.txt")

OUT_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "valuation_proposal_target_packet.json"
OUT_MD = DOCS / "VALUATION_PROPOSAL_TARGET_PACKET_2026-06-26.md"

BOUNDARY = (
    "Valuation and proposal target packet. This translates current frozen/source-conditioned replay evidence into "
    "bounded business language, a first paid-pilot target, and reviewer-safe proposal numbers. It does not authorize "
    "field-validation, realized-savings, fixed-dollar frozen-delta, medical, live-trading, grant-award, or guaranteed ROI claims."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
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


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def wilson_interval(wins: int, n: int, z: float = 1.96) -> dict[str, float]:
    if n <= 0:
        return {"point": 0.0, "lower_95": 0.0, "upper_95": 0.0}
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return {
        "point": round(p, 6),
        "lower_95": round(max(0.0, center - margin), 6),
        "upper_95": round(min(1.0, center + margin), 6),
    }


def lane_stats(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lanes: dict[str, dict[str, Any]] = {}
    for row in results:
        lane = str(row.get("lane", ""))
        item = lanes.setdefault(
            lane,
            {
                "lane": lane,
                "candidate_family": row.get("candidate_family", ""),
                "baseline_family": row.get("baseline_family", ""),
                "routes": 0,
                "wins": 0,
                "estimated_rows": 0,
                "numeric_samples": 0,
                "deltas": [],
                "sources": [],
            },
        )
        item["routes"] += 1
        item["wins"] += 1 if row.get("candidate_beats_named_baseline") else 0
        item["estimated_rows"] += int(row.get("estimated_rows") or 0)
        item["numeric_samples"] += int(row.get("profile", {}).get("numeric_count") or 0)
        if row.get("candidate_delta_vs_named_baseline") is not None:
            item["deltas"].append(float(row["candidate_delta_vs_named_baseline"]))
        if len(item["sources"]) < 5:
            item["sources"].append(row.get("source_path", ""))

    stats: list[dict[str, Any]] = []
    for item in lanes.values():
        interval = wilson_interval(int(item["wins"]), int(item["routes"]))
        deltas = item.pop("deltas")
        stats.append(
            {
                **item,
                "win_rate": interval["point"],
                "win_rate_lower_95": interval["lower_95"],
                "win_rate_upper_95": interval["upper_95"],
                "mean_delta_vs_named_baseline": round(mean(deltas), 6) if deltas else None,
                "best_delta_vs_named_baseline": round(max(deltas), 6) if deltas else None,
                "evidence_status": "source_conditioned_replay_not_field_validation",
            }
        )
    stats.sort(
        key=lambda item: (
            -float(item["win_rate"]),
            -float(item["mean_delta_vs_named_baseline"] or -999),
            -int(item["estimated_rows"]),
        )
    )
    return stats


def overall_stats(results: list[dict[str, Any]]) -> dict[str, Any]:
    wins = sum(1 for row in results if row.get("candidate_beats_named_baseline"))
    n = len(results)
    interval = wilson_interval(wins, n)
    deltas = [float(row["candidate_delta_vs_named_baseline"]) for row in results if row.get("candidate_delta_vs_named_baseline") is not None]
    return {
        "routes": n,
        "wins": wins,
        "losses_or_ties": n - wins,
        "honest_route_win_rate": interval["point"],
        "honest_route_win_rate_lower_95": interval["lower_95"],
        "honest_route_win_rate_upper_95": interval["upper_95"],
        "mean_delta_vs_named_baseline": round(mean(deltas), 6) if deltas else None,
        "best_delta_vs_named_baseline": round(max(deltas), 6) if deltas else None,
        "estimated_rows": sum(int(row.get("estimated_rows") or 0) for row in results),
        "numeric_samples": sum(int(row.get("profile", {}).get("numeric_count") or 0) for row in results),
    }


def cumberland_note_status() -> dict[str, Any]:
    exists = CUMBERLAND_NOTE.exists()
    text = CUMBERLAND_NOTE.read_text(encoding="utf-8", errors="ignore") if exists else ""
    aggressive_phrases = [
        "15-35% efficiency",
        "$40M",
        "$100M",
        "$500M",
        "$3B",
        "$10B",
        "If our numbers are even half right",
    ]
    found = [phrase for phrase in aggressive_phrases if phrase.lower() in text.lower()]
    return {
        "path": str(CUMBERLAND_NOTE),
        "exists": exists,
        "found_ahead_of_gate_phrases": found,
        "recommendation": (
            "Use the note as vision/business framing only. Replace operational percentage, valuation, and exit claims "
            "with current replay win rates until buyer-authorized field validation exists."
        ),
    }


def proposal_target(best_lane: dict[str, Any]) -> dict[str, Any]:
    lane = best_lane.get("lane", "")
    if lane == "wave_resonance_timing":
        return {
            "target_name": "Energy Forecasting / Grid Reliability Paid Technical Evaluation",
            "target_segment": "utility_grid_analytics_or_energy_forecasting",
            "buyer_role": "Energy Forecasting Lead, Grid Reliability Analytics Lead, or National Lab validation lead",
            "why_this_first": (
                "It is the strongest current multi-source lane: 4/4 source-conditioned replay wins for "
                "kuramoto_phase_coupling versus kalman_filter, using EIA/net-generation and related measured sources."
            ),
            "proposal_ask": "20-minute technical fit call, then a paid evidence review or buyer-authorized field replay.",
            "paid_review_scope_usd": {"low": 5000, "high": 15000, "status": "scoping_range_not_value_claim"},
            "follow_on_pilot_scope_usd": "Quote only after data rights, baselines, holdout windows, and acceptance metrics are defined.",
            "acceptance_metric": "forecast residual, phase/timing error, drift-detection lead time, false positives, and missed-event rate versus incumbent baseline.",
            "required_buyer_inputs": [
                "incumbent baseline method",
                "20+ holdout windows",
                "allowed source fields",
                "economic conversion factors",
                "reviewer/owner of acceptance metric",
            ],
        }
    return {
        "target_name": "Constrained Infrastructure Optimization Paid Technical Evaluation",
        "target_segment": "critical_infrastructure_optimization",
        "buyer_role": "Infrastructure Optimization Lead or R&D Program Manager",
        "why_this_first": f"Current best lane is {lane} with candidate {best_lane.get('candidate_family', '')}.",
        "proposal_ask": "20-minute technical fit call, then a paid evidence review or buyer-authorized replay.",
        "paid_review_scope_usd": {"low": 5000, "high": 15000, "status": "scoping_range_not_value_claim"},
        "follow_on_pilot_scope_usd": "Quote only after data rights, baselines, holdout windows, and acceptance metrics are defined.",
        "acceptance_metric": "score delta under equal constraints versus incumbent baseline.",
        "required_buyer_inputs": ["incumbent baseline", "holdout windows", "data rights", "acceptance metric"],
    }


def valuation_state(overall: dict[str, Any], best_lane: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    manifest_summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
    return {
        "current_evidence_stage": "source_conditioned_replay",
        "honest_current_win_rate": overall["honest_route_win_rate"],
        "honest_current_win_rate_95_interval": [
            overall["honest_route_win_rate_lower_95"],
            overall["honest_route_win_rate_upper_95"],
        ],
        "strongest_lane": best_lane.get("lane", ""),
        "strongest_candidate": best_lane.get("candidate_family", ""),
        "strongest_lane_win_rate": best_lane.get("win_rate"),
        "strongest_lane_mean_delta": best_lane.get("mean_delta_vs_named_baseline"),
        "unique_source_count": manifest_summary.get("unique_source_count", 0),
        "unique_source_estimated_rows": manifest_summary.get("unique_source_estimated_rows", 0),
        "ready_for_benchmark_routes": manifest_summary.get("ready_for_benchmark_row_count", 0),
        "defensible_money_status": "sell paid technical evaluation / buyer-authorized replay; do not sell fixed-value frozen deltas yet",
        "current_priceable_offer": {
            "technical_fit_call": "free_or_no_quote_until_fit",
            "paid_evidence_review_usd": {"low": 5000, "high": 15000},
            "buyer_authorized_replay": "custom quote after scope",
        },
        "not_defensible_yet": [
            "15-35% system efficiency claim",
            "realized customer savings",
            "field validation",
            "$10k fixed frozen-delta value",
            "grant award certainty",
            "live trading edge",
        ],
    }


def proposal_blurb(target: dict[str, Any], best_lane: dict[str, Any], overall: dict[str, Any]) -> str:
    return (
        f"LumenCore requests a technical fit call for a paid evidence review of a source-conditioned replay result in "
        f"{target['target_segment']}. Current frozen replay evidence shows {best_lane['wins']}/{best_lane['routes']} "
        f"wins for `{best_lane['candidate_family']}` against `{best_lane['baseline_family']}` on the `{best_lane['lane']}` "
        f"lane, with mean benchmark delta `{best_lane['mean_delta_vs_named_baseline']}`. Across the current ready-source "
        f"batch, candidates won {overall['wins']}/{overall['routes']} routes. These are benchmark-priority results, not "
        f"field validation or realized savings. The proposed next step is buyer-authorized replay on pre-registered "
        f"holdout windows against the buyer's incumbent baseline."
    )


def build_payload() -> dict[str, Any]:
    ready = read_json(READY_REPLAY_JSON)
    manifest = read_json(SOURCE_MANIFEST_JSON)
    results = [row for row in ready.get("ready_source_replay_results", []) if isinstance(row, dict)]
    lanes = lane_stats(results)
    overall = overall_stats(results)
    best_lane = lanes[0] if lanes else {}
    target = proposal_target(best_lane)
    payload = {
        "schema": "valuation_proposal_target_packet_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "ready_source_replay": str(READY_REPLAY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "source_manifest": str(SOURCE_MANIFEST_JSON.relative_to(ROOT)).replace("\\", "/"),
            "cumberland_note": str(CUMBERLAND_NOTE),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
        "overall_replay_stats": overall,
        "lane_stats": lanes,
        "valuation_state": valuation_state(overall, best_lane, manifest),
        "recommended_first_proposal_target": target,
        "proposal_blurb": proposal_blurb(target, best_lane, overall) if best_lane else "",
        "cumberland_note_status": cumberland_note_status(),
        "claim_gates": {
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
            "grant_award_certainty_allowed": False,
            "paid_technical_evaluation_scoping_allowed": True,
        },
    }
    payload["packet_sha256"] = stable_sha256(
        {
            "overall_replay_stats": payload["overall_replay_stats"],
            "lane_stats": payload["lane_stats"],
            "valuation_state": payload["valuation_state"],
            "recommended_first_proposal_target": payload["recommended_first_proposal_target"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    overall = payload["overall_replay_stats"]
    valuation = payload["valuation_state"]
    target = payload["recommended_first_proposal_target"]
    note = payload["cumberland_note_status"]
    lines = [
        "# Valuation Proposal Target Packet",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Real Numbers Now",
        "",
        f"- Current replay routes: `{overall['routes']}`",
        f"- Candidate wins: `{overall['wins']}`",
        f"- Candidate losses/ties: `{overall['losses_or_ties']}`",
        f"- Honest current route win rate: `{percent(overall['honest_route_win_rate'])}`",
        f"- 95% Wilson interval: `{percent(overall['honest_route_win_rate_lower_95'])}` to `{percent(overall['honest_route_win_rate_upper_95'])}`",
        f"- Mean benchmark delta vs named baselines: `{overall['mean_delta_vs_named_baseline']}`",
        f"- Best benchmark delta vs named baseline: `{overall['best_delta_vs_named_baseline']}`",
        f"- Estimated rows in current replay batch: `{overall['estimated_rows']}`",
        f"- Numeric samples read in current replay batch: `{overall['numeric_samples']}`",
        "",
        "## Lane Results",
        "",
        "| Lane | Candidate | Baseline | Wins/Routes | 95% Win Interval | Mean Delta | Rows | Status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["lane_stats"]:
        lines.append(
            f"| `{row['lane']}` | `{row['candidate_family']}` | `{row['baseline_family']}` | "
            f"`{row['wins']}/{row['routes']}` | `{percent(row['win_rate_lower_95'])}`-`{percent(row['win_rate_upper_95'])}` | "
            f"`{row['mean_delta_vs_named_baseline']}` | `{row['estimated_rows']}` | `{row['evidence_status']}` |"
        )

    lines.extend(
        [
            "",
            "## Honest Valuation State",
            "",
            f"- Evidence stage: `{valuation['current_evidence_stage']}`",
            f"- Strongest lane: `{valuation['strongest_lane']}`",
            f"- Strongest candidate: `{valuation['strongest_candidate']}`",
            f"- Ready-for-benchmark routes in manifest: `{valuation['ready_for_benchmark_routes']}`",
            f"- Unique source files in manifest: `{valuation['unique_source_count']}`",
            f"- Unique estimated rows in manifest: `{valuation['unique_source_estimated_rows']}`",
            f"- Defensible money status: {valuation['defensible_money_status']}",
            f"- Current priceable offer: paid evidence review `{valuation['current_priceable_offer']['paid_evidence_review_usd']['low']}`-`{valuation['current_priceable_offer']['paid_evidence_review_usd']['high']}` USD, scoped only after fit.",
            "",
            "## First Proposal Target",
            "",
            f"- Target: {target['target_name']}",
            f"- Buyer role: {target['buyer_role']}",
            f"- Why this first: {target['why_this_first']}",
            f"- Ask: {target['proposal_ask']}",
            f"- Acceptance metric: {target['acceptance_metric']}",
            "",
            "## Reviewer-Safe Proposal Blurb",
            "",
            payload["proposal_blurb"],
            "",
            "## Cumberland Pitch Cleanup",
            "",
            f"- Source exists: `{str(note['exists']).lower()}`",
            f"- Phrases ahead of current gates: `{note['found_ahead_of_gate_phrases']}`",
            f"- Recommendation: {note['recommendation']}",
            "",
            "## Boundaries",
            "",
            "- Do not state 15-35% system efficiency, realized savings, field validation, or fixed frozen-delta dollar value yet.",
            "- The strongest current claim is source-conditioned benchmark replay plus paid technical evaluation scoping.",
            "- The highest-value next proof is buyer-authorized holdout replay with accepted incumbent baselines.",
            f"- Packet SHA-256: `{payload['packet_sha256']}`",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
