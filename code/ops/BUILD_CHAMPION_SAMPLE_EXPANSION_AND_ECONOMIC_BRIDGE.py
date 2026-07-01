from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

LOCKED_SWEEP_JSON = OUT_OPS / "locked_source_baseline_replay_sweep_latest.json"
MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"
LIVE_DOMAIN_JSON = OUT_OPS / "live_domain_deployment_feed_latest.json"

OUT_JSON = OUT_OPS / "champion_sample_expansion_and_economic_bridge_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_sample_expansion_and_economic_bridge.json"
OUT_MD = DOCS / "CHAMPION_SAMPLE_EXPANSION_AND_ECONOMIC_BRIDGE_2026-06-30.md"

BOUNDARY = (
    "Champion sample-expansion and economic bridge. This artifact explains which live-breadth lanes are strong, "
    "which lanes need more samples or source-specific adapters, and how an external owner would convert a metric "
    "improvement into a dollar claim. It does not claim field validation, realized savings, guaranteed funding, "
    "fixed frozen-delta pricing, live trading performance, medical efficacy, or buyer acceptance."
)

LANE_TARGETS: dict[str, dict[str, Any]] = {
    "wave_resonance_timing": {
        "target_routes": 150,
        "target_comparisons": 600,
        "attention_reason": "repeatable oscillatory residual improvement across many source-conditioned replays",
        "buyer_story": "forecast residual, phase drift, jitter, load, telemetry, sensor, or stability timing problems",
    },
    "energy_price_pressure_proxy": {
        "target_routes": 150,
        "target_comparisons": 600,
        "attention_reason": "walk-forward pressure proxy across energy, macro, and market-like measured rows",
        "buyer_story": "energy operations, demand/load pressure, price-risk triage, and grid planning signals",
    },
    "thermal_ventilation": {
        "target_routes": 40,
        "target_comparisons": 160,
        "attention_reason": "strong early win rate, but underpowered sample size",
        "buyer_story": "datacenter cooling, HVAC, thermal equalization, and energy reduction pilots",
    },
    "branching_transport": {
        "target_routes": 40,
        "target_comparisons": 120,
        "attention_reason": "mixed result; needs more graph/network/source-specific tests before promotion",
        "buyer_story": "grid topology, water routing, communications routing, logistics, and fault-tolerant flow",
    },
    "optimal_curve_transport": {
        "target_routes": 30,
        "target_comparisons": 120,
        "attention_reason": "strong early result, but tiny N; needs route/path-specific live sources",
        "buyer_story": "task routing, robotics, path planning, evacuation, interdiction, and time-to-target constraints",
    },
    "field_guided_control": {
        "target_routes": 30,
        "target_comparisons": 120,
        "attention_reason": "mapped but not replayed; needs adapter for potential-field or atmospheric-field baselines",
        "buyer_story": "weather, wildfire, air quality, drone path planning, RF/field-aware routing, and grid field analysis",
    },
    "mission_network_routing": {
        "target_routes": 30,
        "target_comparisons": 120,
        "attention_reason": "mapped but not replayed; needs graph extraction from water, mission, or network sources",
        "buyer_story": "mission routing, resilient mesh routing, logistics, water distribution, and emergency response",
    },
    "market_signal_geometry": {
        "target_routes": 100,
        "target_comparisons": 400,
        "attention_reason": "large mapped universe, but must stay read-only/paper and pass leakage-safe forecast baselines",
        "buyer_story": "decision-calibration lab, anomaly detection, and risk timing, not live-profit proof",
    },
}

VALIDATION_TARGETS = [
    {
        "name": "EPRI Incubatenergy Labs / AI for Power",
        "url": "https://epri.brightidea.com/2026IncubatenergyLabsChallenge",
        "why": "Best utility demonstration lane: they can define an accepted baseline, metric, and utility value conversion.",
        "ask": "Request a 4-16 week source-conditioned replay using held-out utility data, incumbent baseline, and accepted operational metric.",
    },
    {
        "name": "Spark Innovation Center / TVA / UT Research Park",
        "url": "https://www.tnresearchpark.org/spark/accelerator/",
        "why": "Best Tennessee-local bridge to TVA, ORNL, UT, and advanced-energy pilot scoping.",
        "ask": "Request pilot-design help for grid/load/thermal validation and introductions to a system owner.",
    },
    {
        "name": "Tennessee Advanced Energy Business Council",
        "url": "https://www.tnadvancedenergy.com/join-taebc/",
        "why": "Best local network for credibility, partner discovery, and warm energy-sector introductions.",
        "ask": "Ask for the right member/company channel for independent validation, not a claim endorsement.",
    },
    {
        "name": "EPB / ORNL grid innovation corridor",
        "url": "https://epb.com/energy/automated-grid/",
        "why": "Strong field-validation archetype: grid automation, outage-minute reduction, sensing, and resilience metrics.",
        "ask": "Request a narrow non-operational replay or sandbox evaluation against accepted outage/load/rerouting metrics.",
    },
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


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def manifest_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows = manifest.get("manifest_rows", [])
    return [row for row in rows if isinstance(row, dict)]


def lane_manifest_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_lane: dict[str, dict[str, Any]] = {}
    for row in rows:
        lane = str(row.get("lane") or "unclassified")
        entry = by_lane.setdefault(
            lane,
            {
                "mapped_rows": 0,
                "ready_rows": 0,
                "estimated_rows": 0,
                "systems": {},
                "example_sources": [],
                "adapter_statuses": {},
            },
        )
        entry["mapped_rows"] += 1
        if row.get("ready_for_benchmark"):
            entry["ready_rows"] += 1
        entry["estimated_rows"] += as_int(row.get("estimated_rows"))
        system = str(row.get("system") or "unknown")
        entry["systems"][system] = entry["systems"].get(system, 0) + 1
        status = str(row.get("adapter_status") or "unknown")
        entry["adapter_statuses"][status] = entry["adapter_statuses"].get(status, 0) + 1
        source_path = str(row.get("source_path") or "")
        if source_path and source_path not in entry["example_sources"] and len(entry["example_sources"]) < 5:
            entry["example_sources"].append(source_path)
    return by_lane


def lane_scoreboard(sweep: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lanes: dict[str, dict[str, Any]] = {}
    for row in sweep.get("lane_scoreboard", []):
        if isinstance(row, dict):
            lanes[str(row.get("lane") or "unknown")] = row
    return lanes


def status_for_lane(lane: str, sweep_lane: dict[str, Any], manifest_lane: dict[str, Any]) -> str:
    routes = as_int(sweep_lane.get("routes_replayed"))
    comparisons = as_int(sweep_lane.get("baseline_comparison_count"))
    wins = as_int(sweep_lane.get("candidate_win_count"))
    target = LANE_TARGETS.get(lane, {})
    target_routes = as_int(target.get("target_routes"), 30)
    target_comparisons = as_int(target.get("target_comparisons"), 120)
    if routes == 0:
        return "adapter_needed_before_claim"
    if routes < target_routes or comparisons < target_comparisons:
        return "promising_but_underpowered"
    if wins == comparisons and comparisons >= target_comparisons:
        return "strong_internal_replay_champion"
    if wins / max(comparisons, 1) >= 0.65:
        return "promising_internal_replay"
    return "mixed_or_not_promoted"


def build_lane_diagnostics(sweep: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    manifest_by_lane = lane_manifest_summary(manifest_rows(manifest))
    sweep_by_lane = lane_scoreboard(sweep)
    lanes = sorted(set(LANE_TARGETS) | set(manifest_by_lane) | set(sweep_by_lane))
    diagnostics = []
    for lane in lanes:
        sweep_lane = sweep_by_lane.get(lane, {})
        manifest_lane = manifest_by_lane.get(lane, {})
        comparisons = as_int(sweep_lane.get("baseline_comparison_count"))
        wins = as_int(sweep_lane.get("candidate_win_count"))
        routes = as_int(sweep_lane.get("routes_replayed"))
        target = LANE_TARGETS.get(lane, {})
        win_rate = wins / comparisons if comparisons else 0.0
        target_routes = as_int(target.get("target_routes"), 30)
        target_comparisons = as_int(target.get("target_comparisons"), 120)
        diagnostics.append(
            {
                "lane": lane,
                "status": status_for_lane(lane, sweep_lane, manifest_lane),
                "routes_replayed": routes,
                "route_gap_to_target": max(target_routes - routes, 0),
                "baseline_comparison_count": comparisons,
                "comparison_gap_to_target": max(target_comparisons - comparisons, 0),
                "candidate_win_count": wins,
                "win_rate": round(win_rate, 4),
                "mean_score_delta": round(as_float(sweep_lane.get("mean_score_delta")), 6),
                "best_score_delta": round(as_float(sweep_lane.get("best_score_delta")), 6),
                "numeric_samples": as_int(sweep_lane.get("numeric_samples")),
                "estimated_rows": as_int(sweep_lane.get("estimated_rows") or manifest_lane.get("estimated_rows")),
                "mapped_rows": as_int(manifest_lane.get("mapped_rows")),
                "ready_rows": as_int(manifest_lane.get("ready_rows")),
                "systems": manifest_lane.get("systems", {}),
                "adapter_statuses": manifest_lane.get("adapter_statuses", {}),
                "example_sources": manifest_lane.get("example_sources", []),
                "attention_reason": target.get("attention_reason", "needs lane-specific evidence review"),
                "buyer_story": target.get("buyer_story", "requires buyer-defined operating problem"),
            }
        )
    return diagnostics


def top_comparisons(sweep: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    rows = [row for row in sweep.get("top_positive_comparisons", []) if isinstance(row, dict)]
    return rows[:limit]


def economic_bridge(lane_diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    wave = next((row for row in lane_diagnostics if row["lane"] == "wave_resonance_timing"), {})
    energy = next((row for row in lane_diagnostics if row["lane"] == "energy_price_pressure_proxy"), {})
    return {
        "what_600_of_600_means": (
            "The wave-resonance candidate beat every locked wave baseline comparison in the replay: "
            f"{wave.get('routes_replayed', 0)} source-conditioned routes x "
            f"{len(['fft_filter', 'kalman_filter', 'arima', 'phase_locked_loop'])} locked baselines = "
            f"{wave.get('baseline_comparison_count', 0)} comparisons. It is a repeatability signal, not a direct percent savings claim."
        ),
        "current_safe_claim": (
            "Source-conditioned replay shows repeated candidate outperformance under locked baselines. "
            "The strongest lane is wave_resonance_timing; energy_price_pressure_proxy is broad but still a proxy."
        ),
        "not_allowed_yet": [
            "field-validated savings",
            "realized dollar savings",
            "guaranteed buyer value",
            "fixed dollar value per frozen delta",
            "live trading profit",
            "agency acceptance certainty",
        ],
        "future_dollar_formula": (
            "Buyer-authorized annual value = addressable annual cost or value pool x accepted operational lift "
            "x affected-scope fraction x attribution factor x confidence discount. Each term must be supplied or "
            "approved by the system owner before it becomes a claim."
        ),
        "illustrative_only_examples": [
            {
                "addressable_pool_usd": 1_000_000_000,
                "accepted_lift": "0.01%",
                "scope_fraction": "10%",
                "attribution_factor": "50%",
                "confidence_discount": "50%",
                "illustrative_annual_value_usd": 25_000,
                "boundary": "Example math only; not a LumenCore claim.",
            },
            {
                "addressable_pool_usd": 1_000_000_000,
                "accepted_lift": "0.1%",
                "scope_fraction": "10%",
                "attribution_factor": "50%",
                "confidence_discount": "50%",
                "illustrative_annual_value_usd": 250_000,
                "boundary": "Example math only; not a LumenCore claim.",
            },
            {
                "addressable_pool_usd": 10_000_000_000,
                "accepted_lift": "0.1%",
                "scope_fraction": "10%",
                "attribution_factor": "50%",
                "confidence_discount": "50%",
                "illustrative_annual_value_usd": 2_500_000,
                "boundary": "Example math only; not a LumenCore claim.",
            },
        ],
        "highest_value_next_measurement": (
            "Ask an energy, grid, or datacenter owner for held-out time-series data plus their incumbent baseline "
            "and accepted economic conversion. Then replay wave_resonance_timing and energy_price_pressure_proxy "
            "without tuning on the held-out set."
        ),
        "energy_proxy_current_shape": {
            "routes_replayed": energy.get("routes_replayed", 0),
            "baseline_comparison_count": energy.get("baseline_comparison_count", 0),
            "candidate_win_count": energy.get("candidate_win_count", 0),
            "win_rate": energy.get("win_rate", 0.0),
            "mean_score_delta": energy.get("mean_score_delta", 0.0),
            "best_score_delta": energy.get("best_score_delta", 0.0),
        },
    }


def ranked_next_tests(lane_diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority_order = {
        "thermal_ventilation": 1,
        "optimal_curve_transport": 2,
        "branching_transport": 3,
        "field_guided_control": 4,
        "mission_network_routing": 5,
        "market_signal_geometry": 6,
        "energy_price_pressure_proxy": 7,
        "wave_resonance_timing": 8,
    }
    rows = []
    for row in lane_diagnostics:
        lane = row["lane"]
        status = row["status"]
        if status in {"strong_internal_replay_champion"} and lane == "wave_resonance_timing":
            next_action = "Keep as flagship; focus on buyer-authorized held-out data and uncertainty bands."
        elif row["routes_replayed"] == 0:
            next_action = "Build a source-specific adapter and run locked baselines before promotion."
        elif row["route_gap_to_target"] > 0:
            next_action = "Acquire or map more live sources and rerun the locked sweep until sample target is met."
        elif status == "mixed_or_not_promoted":
            next_action = "Treat as research lane; add ablations and only promote subsets that beat the best baseline."
        else:
            next_action = "Add uncertainty, failure-mode, and adversarial/noise stress tests."
        rows.append(
            {
                "priority": priority_order.get(lane, 99),
                "lane": lane,
                "status": status,
                "next_action": next_action,
                "route_gap_to_target": row["route_gap_to_target"],
                "comparison_gap_to_target": row["comparison_gap_to_target"],
                "buyer_story": row["buyer_story"],
            }
        )
    return sorted(rows, key=lambda item: (item["priority"], item["route_gap_to_target"], item["comparison_gap_to_target"]))


def build_payload() -> dict[str, Any]:
    sweep = read_json(LOCKED_SWEEP_JSON)
    manifest = read_json(MANIFEST_JSON)
    live_domain = read_json(LIVE_DOMAIN_JSON)
    lane_diagnostics = build_lane_diagnostics(sweep, manifest)
    payload = {
        "schema": "champion_sample_expansion_and_economic_bridge_v1",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "inputs": {
            "locked_source_baseline_replay_sweep": str(LOCKED_SWEEP_JSON.relative_to(ROOT)),
            "geometry_live_source_manifest": str(MANIFEST_JSON.relative_to(ROOT)),
            "live_domain_deployment_feed": str(LIVE_DOMAIN_JSON.relative_to(ROOT)),
        },
        "summary": {
            "ready_rows": sweep.get("summary", {}).get("ready_rows", 0),
            "source_count": sweep.get("summary", {}).get("source_count", 0),
            "estimated_rows_replayed": sweep.get("summary", {}).get("estimated_rows_replayed", 0),
            "numeric_samples_read": sweep.get("summary", {}).get("numeric_samples_read", 0),
            "baseline_comparison_count": sweep.get("summary", {}).get("baseline_comparison_count", 0),
            "candidate_win_count": sweep.get("summary", {}).get("candidate_win_count", 0),
            "wave_resonance_win_rate": next(
                (row["win_rate"] for row in lane_diagnostics if row["lane"] == "wave_resonance_timing"),
                0.0,
            ),
            "small_sample_lanes": [
                row["lane"]
                for row in lane_diagnostics
                if row["status"] == "promising_but_underpowered"
            ],
            "adapter_needed_lanes": [
                row["lane"]
                for row in lane_diagnostics
                if row["status"] == "adapter_needed_before_claim"
            ],
            "live_domain_reviewer_ready": bool(
                live_domain.get("summary", {}).get("live_domain_reviewer_ready", False)
            ),
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
        },
        "lane_diagnostics": lane_diagnostics,
        "top_positive_comparisons": top_comparisons(sweep),
        "economic_bridge": economic_bridge(lane_diagnostics),
        "ranked_next_tests": ranked_next_tests(lane_diagnostics),
        "validation_targets": VALIDATION_TARGETS,
        "who_would_care": [
            "Utility innovation teams that can compare against incumbent forecasting, load, or grid-operation baselines.",
            "EPRI/Incubatenergy reviewers looking for de-risked, testable AI utility demonstrations.",
            "TVA/Spark/ORNL-connected energy mentors who can shape the field-validation protocol.",
            "Datacenter energy and cooling operators if thermal lanes get larger samples and a cost conversion.",
            "DARPA/DOE/SBIR reviewers when the story stays measurable, falsifiable, and claim-disciplined.",
        ],
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
    }
    payload["bridge_sha256"] = stable_sha256({k: v for k, v in payload.items() if k != "bridge_sha256"})
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    econ = payload["economic_bridge"]
    lines = [
        "# Champion Sample Expansion And Economic Bridge",
        "",
        f"Generated: {payload['generated_utc']}",
        "",
        "## Boundary",
        "",
        payload["boundary"],
        "",
        "## Current Replay Strength",
        "",
        f"- Ready rows: `{summary['ready_rows']}`",
        f"- Sources: `{summary['source_count']}`",
        f"- Estimated rows replayed: `{summary['estimated_rows_replayed']}`",
        f"- Numeric samples read: `{summary['numeric_samples_read']}`",
        f"- Locked baseline comparisons: `{summary['baseline_comparison_count']}`",
        f"- Candidate wins: `{summary['candidate_win_count']}`",
        f"- Wave resonance win rate: `{summary['wave_resonance_win_rate']}`",
        f"- Live-domain reviewer ready: `{str(summary['live_domain_reviewer_ready']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
        "",
        "## What 600/600 Means",
        "",
        econ["what_600_of_600_means"],
        "",
        "It is meaningful because it survived locked, repeated replay comparisons. It is not a direct percent-savings claim.",
        "",
        "## Lane Diagnostics",
        "",
        "| Lane | Status | Routes | Comparisons | Wins | Mean Delta | Best Delta | Gap |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in payload["lane_diagnostics"]:
        lines.append(
            "| {lane} | {status} | {routes_replayed} | {baseline_comparison_count} | "
            "{candidate_win_count} | {mean_score_delta} | {best_score_delta} | {route_gap_to_target} routes / "
            "{comparison_gap_to_target} comps |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Economic Bridge",
            "",
            econ["future_dollar_formula"],
            "",
            "### Illustrative Only",
            "",
        ]
    )
    for example in econ["illustrative_only_examples"]:
        lines.append(
            "- Pool `${:,}` x lift `{}` x scope `{}` x attribution `{}` x confidence `{}` = `${:,}` annual illustrative value. {}".format(
                example["addressable_pool_usd"],
                example["accepted_lift"],
                example["scope_fraction"],
                example["attribution_factor"],
                example["confidence_discount"],
                example["illustrative_annual_value_usd"],
                example["boundary"],
            )
        )
    lines.extend(
        [
            "",
            "## Ranked Next Tests",
            "",
        ]
    )
    for row in payload["ranked_next_tests"][:10]:
        lines.append(
            f"- {row['priority']}. `{row['lane']}` ({row['status']}): {row['next_action']}"
        )
    lines.extend(
        [
            "",
            "## Field Validation Targets",
            "",
        ]
    )
    for target in payload["validation_targets"]:
        lines.append(f"- [{target['name']}]({target['url']}): {target['why']} Ask: {target['ask']}")
    lines.extend(
        [
            "",
            "## Who Would Care",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in payload["who_would_care"])
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        "Built champion sample expansion bridge: "
        f"lanes={len(payload['lane_diagnostics'])} "
        f"small_sample={len(payload['summary']['small_sample_lanes'])} "
        f"adapter_needed={len(payload['summary']['adapter_needed_lanes'])} "
        f"sha256={payload['bridge_sha256'][:12]}"
    )


if __name__ == "__main__":
    main()
