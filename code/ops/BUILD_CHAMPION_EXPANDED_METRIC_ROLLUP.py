from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

GAUNTLET_JSON = DASHBOARD_DATA / "champion_metric_gauntlet.json"
BATTERY_JSON = DASHBOARD_DATA / "champion_metric_battery.json"
LOCKED_SWEEP_JSON = DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json"
SOURCE_MAX_JSON = DASHBOARD_DATA / "live_source_measurement_maximizer.json"
DOMAIN_JSON = DASHBOARD_DATA / "live_domain_deployment_feed.json"
DOLLAR_GATE_JSON = DASHBOARD_DATA / "dollar_claim_gate.json"

OUT_JSON = OUT_OPS / "champion_expanded_metric_rollup_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_expanded_metric_rollup.json"
OUT_MD = DOCS / "CHAMPION_EXPANDED_METRIC_ROLLUP_2026-07-01.md"

BOUNDARY = (
    "Champion expanded metric rollup. This summarizes internal replay lanes, live-source breadth, "
    "baseline comparisons, and claim gates. It does not prove external field validation, realized savings, "
    "fixed frozen-delta pricing, medical efficacy, grant award certainty, or live trading performance."
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


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def percent(value: float) -> float:
    return round(value * 100.0, 2)


def first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row.get(key) is not None:
            return row.get(key)
    return None


def lane_status(win_rate: float, comparisons: int, estimated_rows: int) -> str:
    if comparisons <= 0:
        return "NO_COMPARISONS"
    if comparisons < 20 or estimated_rows < 100_000:
        return "PROMISING_SMALL_SAMPLE" if win_rate >= 0.80 else "MIXED_SMALL_SAMPLE"
    if win_rate >= 0.90:
        return "STRONG_INTERNAL_REPLAY_WIN"
    if win_rate >= 0.60:
        return "MEANINGFUL_INTERNAL_EDGE_NEEDS_MORE_HOLDOUTS"
    if win_rate > 0:
        return "MIXED_OR_BASELINE_STILL_COMPETITIVE"
    return "NO_EDGE_DETECTED"


def lane_plain_english(lane: str, win_rate: float, comparisons: int) -> str:
    if lane == "wave_resonance_timing" and win_rate == 1.0:
        return (
            "This is the cleanest current internal result: the wave/resonance timing lane beat all locked "
            "timing baselines in this replay. Treat it as the lead field-replay candidate, not as a realized "
            "savings claim."
        )
    if lane == "thermal_ventilation" and win_rate == 1.0:
        return (
            "This lane is strong but smaller. It is good pilot material for HVAC, cooling, or thermal-flow "
            "partners once real facility data and acceptance metrics are supplied."
        )
    if lane == "optimal_curve_transport" and win_rate == 1.0:
        return (
            "This lane is strong but narrow. It should be pitched as an optimization replay candidate, not a "
            "universal transport claim."
        )
    if lane == "energy_price_pressure_proxy":
        return (
            "This is economically interesting because it touches energy-price pressure, but the win rate is "
            "mixed enough that it needs more holdouts and external baselines before money language gets stronger."
        )
    if lane == "branching_transport":
        return (
            "This lane is not a current champion. It is useful because it records negative evidence and keeps the "
            "platform honest when classic graph baselines still compete."
        )
    return f"This lane has {comparisons} locked comparisons and should be expanded before strong claims."


def route_results(locked_sweep: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in as_list(locked_sweep.get("route_results")) if isinstance(row, dict)]


def unique_sorted(values: list[Any]) -> list[str]:
    return sorted({str(value) for value in values if value not in (None, "")})


def route_scope(locked_sweep: dict[str, Any]) -> dict[str, Any]:
    routes = route_results(locked_sweep)
    systems = unique_sorted([row.get("system") for row in routes])
    sources = unique_sorted([row.get("source_path") for row in routes])
    lanes = unique_sorted([row.get("lane") for row in routes])
    families = unique_sorted([row.get("candidate_family") for row in routes])
    return {
        "route_result_count": len(routes),
        "source_system_count": len(systems),
        "source_systems": systems,
        "source_file_count": len(sources),
        "lane_count": len(lanes),
        "candidate_family_count": len(families),
        "candidate_families": families,
    }


def source_hygiene(locked_sweep: dict[str, Any]) -> dict[str, Any]:
    suspicious_fragments = [
        "site-packages",
        "node_modules",
        ".venv",
        "\\venv\\",
        "/venv/",
        "wordlist",
        "static_dependencies",
        "__pycache__",
    ]
    suspicious_rows: list[dict[str, Any]] = []
    for row in route_results(locked_sweep):
        source_path = str(row.get("source_path") or "")
        lowered = source_path.lower().replace("/", "\\")
        matched = [fragment for fragment in suspicious_fragments if fragment.lower().replace("/", "\\") in lowered]
        if matched:
            suspicious_rows.append(
                {
                    "system": row.get("system"),
                    "lane": row.get("lane"),
                    "source_path": source_path,
                    "matched_fragments": matched,
                }
            )
    return {
        "suspicious_route_result_count": len(suspicious_rows),
        "suspicious_source_examples": suspicious_rows[:12],
        "field_grade_source_hygiene_passed": len(suspicious_rows) == 0,
        "claim_impact": (
            "Some replay rows appear to come from package/runtime paths. Keep them as stress/noise tests, "
            "but exclude them from field-grade live-system proof until the source manifest is cleaned."
            if suspicious_rows
            else "No package/runtime source paths were detected in the route-result sample."
        ),
    }


def lane_route_scope(locked_sweep: dict[str, Any], lane: str) -> dict[str, Any]:
    rows = [row for row in route_results(locked_sweep) if str(row.get("lane")) == lane]
    sources = unique_sorted([row.get("source_path") for row in rows])
    systems = unique_sorted([row.get("system") for row in rows])
    families = unique_sorted([row.get("candidate_family") for row in rows])
    top_sources = sorted(
        rows,
        key=lambda item: (
            as_int(item.get("estimated_rows")),
            as_float(item.get("score_delta")),
            as_int(item.get("candidate_win_count")),
        ),
        reverse=True,
    )[:5]
    return {
        "route_result_count": len(rows),
        "source_system_count": len(systems),
        "source_systems": systems,
        "source_file_count": len(sources),
        "candidate_families": families,
        "top_source_paths": [str(row.get("source_path")) for row in top_sources if row.get("source_path")],
    }


def build_dataset_champion_cards(locked_sweep: dict[str, Any], limit: int = 24) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for row in route_results(locked_sweep):
        comparisons = as_int(first_present(row, "comparison_count", "baseline_comparison_count", "comparisons"))
        wins = as_int(first_present(row, "candidate_win_count", "wins"))
        estimated_rows = as_int(row.get("estimated_rows"))
        win_rate = round(wins / comparisons, 6) if comparisons else 0.0
        profile = as_dict(row.get("profile"))
        cards.append(
            {
                "system": str(row.get("system") or "unknown_system"),
                "lane": str(row.get("lane") or "unknown_lane"),
                "source_path": str(row.get("source_path") or profile.get("source_path") or ""),
                "candidate_family": str(row.get("candidate_family") or ""),
                "candidate_wins": wins,
                "baseline_comparisons": comparisons,
                "win_rate": win_rate,
                "win_rate_pct": percent(win_rate),
                "estimated_rows": estimated_rows,
                "numeric_count": as_int(profile.get("numeric_count")),
                "source_sha256_prefix": profile.get("source_sha256_prefix"),
                "locked_baselines": [str(item) for item in as_list(row.get("locked_baselines"))],
                "metric_names": [str(item) for item in as_list(row.get("metric_names"))],
                "score_delta": row.get("score_delta"),
                "adapter_status": row.get("adapter_status"),
                "status": lane_status(win_rate, comparisons, estimated_rows),
                "claim_gate": "internal source-conditioned replay only; needs external owner holdout before dollar claims",
            }
        )
    return sorted(
        cards,
        key=lambda item: (
            item["win_rate"],
            item["baseline_comparisons"],
            item["estimated_rows"],
            as_float(item.get("score_delta")),
        ),
        reverse=True,
    )[:limit]


def build_lane_cards(locked_sweep: dict[str, Any]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for row in as_list(locked_sweep.get("lane_scoreboard")):
        if not isinstance(row, dict):
            continue
        comparisons = as_int(first_present(row, "baseline_comparison_count", "comparisons"))
        wins = as_int(first_present(row, "candidate_win_count", "wins"))
        estimated_rows = as_int(first_present(row, "estimated_rows_replayed", "estimated_rows"))
        numeric_samples = as_int(row.get("numeric_samples_read"))
        win_rate = round(wins / comparisons, 6) if comparisons else 0.0
        lane = str(row.get("lane") or row.get("name") or "unknown_lane")
        baselines = [str(item) for item in as_list(row.get("locked_baselines"))]
        metrics = [str(item) for item in as_list(row.get("metrics"))]
        lane_scope = lane_route_scope(locked_sweep, lane)
        cards.append(
            {
                "lane": lane,
                "status": lane_status(win_rate, comparisons, estimated_rows),
                "candidate_wins": wins,
                "baseline_comparisons": comparisons,
                "win_rate": win_rate,
                "win_rate_pct": percent(win_rate),
                "mean_score_delta": row.get("mean_score_delta"),
                "best_score_delta": row.get("best_score_delta"),
                "estimated_rows_replayed": estimated_rows,
                "numeric_samples_read": numeric_samples,
                "geometry_routes_replayed": as_int(row.get("geometry_routes_replayed")),
                "route_result_count": lane_scope["route_result_count"],
                "source_system_count": lane_scope["source_system_count"],
                "source_systems": lane_scope["source_systems"],
                "source_file_count": lane_scope["source_file_count"],
                "candidate_families": lane_scope["candidate_families"],
                "top_source_paths": lane_scope["top_source_paths"],
                "locked_baselines": baselines,
                "metrics": metrics,
                "claim_gate": "internal locked replay only; requires buyer-authorized holdout for field validation",
                "plain_english": lane_plain_english(lane, win_rate, comparisons),
            }
        )
    return sorted(cards, key=lambda item: (item["win_rate"], item["baseline_comparisons"]), reverse=True)


def source_health(source_max: dict[str, Any]) -> dict[str, Any]:
    summary = as_dict(source_max.get("summary"))
    measured = as_int(first_present(summary, "measured_sources", "measured_source_count"))
    enabled = as_int(first_present(summary, "enabled_sources", "enabled_source_count"))
    failed = as_int(first_present(summary, "failed_or_thin_sources", "failed_or_thin_source_count"))
    rows = as_int(summary.get("total_measured_rows"))
    return {
        "enabled_sources": enabled,
        "measured_sources": measured,
        "failed_or_thin_sources": failed,
        "coverage_pct": as_float(first_present(summary, "coverage_pct", "coverage_percent")),
        "total_measured_rows_latest_pull": rows,
        "measured_source_names": summary.get("measured_source_names", []),
        "failed_or_thin_source_names": summary.get("failed_or_thin_source_names", []),
        "missing_or_next_sources": [
            "SAM.gov contract opportunity API",
            "EPA AQS with valid email/key pairing",
            "NREL or OpenEI energy lab endpoints",
            "ISO/RTO operations feeds: PJM, MISO, ERCOT, CAISO, SPP, NYISO, ISO-NE, TVA/BPA",
            "utility outage or reliability event windows",
            "NOAA SWPC space weather and NWS alerts",
            "MarineCadastre AIS / NOAA PORTS for HarborSentinel lanes",
        ],
    }


def claim_state(
    gauntlet: dict[str, Any],
    battery: dict[str, Any],
    domain: dict[str, Any],
    dollar_gate: dict[str, Any],
    locked_sweep: dict[str, Any],
) -> dict[str, Any]:
    gauntlet_summary = as_dict(gauntlet.get("summary"))
    battery_summary = as_dict(battery.get("summary"))
    domain_summary = as_dict(domain.get("summary"))
    dollar_summary = as_dict(dollar_gate.get("summary"))
    sweep_summary = as_dict(locked_sweep.get("summary"))
    return {
        "source_conditioned_replay_claim_allowed": bool(
            gauntlet_summary.get("source_conditioned_replay_claim_allowed")
            or battery_summary.get("source_conditioned_replay_claim_allowed")
            or sweep_summary.get("source_conditioned_replay_claim_allowed")
        ),
        "live_domain_reviewer_ready": bool(domain_summary.get("live_domain_reviewer_ready")),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_frozen_delta_price_claim_allowed": False,
        "safe_estimated_hourly_value_usd": first_present(
            dollar_summary,
            "allowed_estimated_hourly_value_usd",
            "safe_estimated_hourly_value_usd",
        )
        or gauntlet_summary.get("safe_estimated_hourly_value_usd"),
        "safe_estimated_annual_value_usd": first_present(
            dollar_summary,
            "allowed_estimated_annual_value_usd",
            "safe_estimated_annual_value_usd",
        )
        or gauntlet_summary.get("safe_estimated_annual_value_usd"),
        "allowed_language": [
            "internal source-conditioned replay",
            "locked baseline comparison",
            "public hash-verified proof feed" if domain_summary.get("live_domain_reviewer_ready") else "local proof feed pending domain verification",
            "paid field-replay scoping candidate",
        ],
        "blocked_language": [
            "field validated",
            "realized customer savings",
            "fixed price per frozen delta",
            "guaranteed award",
            "guaranteed trading profit",
            "hardware PLL/RF/grid validation without instrumented data",
        ],
    }


def build_payload() -> dict[str, Any]:
    gauntlet = read_json(GAUNTLET_JSON)
    battery = read_json(BATTERY_JSON)
    locked_sweep = read_json(LOCKED_SWEEP_JSON)
    source_max = read_json(SOURCE_MAX_JSON)
    domain = read_json(DOMAIN_JSON)
    dollar_gate = read_json(DOLLAR_GATE_JSON)

    gauntlet_summary = as_dict(gauntlet.get("summary"))
    battery_summary = as_dict(battery.get("summary"))
    sweep_summary = as_dict(locked_sweep.get("summary"))
    lane_cards = build_lane_cards(locked_sweep)
    scope = route_scope(locked_sweep)
    hygiene = source_hygiene(locked_sweep)
    dataset_cards = build_dataset_champion_cards(locked_sweep)
    total_comparisons = sum(as_int(row.get("baseline_comparisons")) for row in lane_cards)
    total_wins = sum(as_int(row.get("candidate_wins")) for row in lane_cards)
    overall_win_rate = round(total_wins / total_comparisons, 6) if total_comparisons else 0.0
    strong_lanes = [
        row
        for row in lane_cards
        if row["status"] in {"STRONG_INTERNAL_REPLAY_WIN", "PROMISING_SMALL_SAMPLE"}
    ]
    mixed_lanes = [row for row in lane_cards if row not in strong_lanes]

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_expanded_metric_rollup_v1",
        "purpose": "Make the current live-breadth champion evidence legible lane-by-lane for reviewers and buyers.",
        "boundary": BOUNDARY,
        "summary": {
            "evidence_stage": "internal_locked_replay_not_field_validated",
            "champion_family": gauntlet_summary.get("champion_family") or battery_summary.get("champion_family"),
            "champion_label": gauntlet_summary.get("champion_label") or battery_summary.get("champion_label"),
            "named_baseline": gauntlet_summary.get("named_baseline") or battery_summary.get("named_baseline"),
            "holdout_wins": gauntlet_summary.get("holdout_wins") or battery_summary.get("holdout_wins"),
            "holdout_count": gauntlet_summary.get("holdout_count") or battery_summary.get("holdout_count"),
            "lane_count": len(lane_cards),
            "strong_lane_count": len(strong_lanes),
            "mixed_or_learning_lane_count": len(mixed_lanes),
            "total_baseline_comparisons": total_comparisons,
            "total_candidate_wins": total_wins,
            "overall_locked_lane_win_rate": overall_win_rate,
            "overall_locked_lane_win_rate_pct": percent(overall_win_rate),
            "estimated_rows_replayed": as_int(
                first_present(sweep_summary, "estimated_rows_replayed", "estimated_rows")
            ),
            "numeric_samples_read": as_int(sweep_summary.get("numeric_samples_read")),
            "source_system_count": scope["source_system_count"],
            "source_systems": scope["source_systems"],
            "source_file_count": scope["source_file_count"],
            "manifest_source_count": as_int(sweep_summary.get("source_count")),
            "route_result_count": scope["route_result_count"],
            "candidate_family_count": scope["candidate_family_count"],
            "field_grade_source_hygiene_passed": hygiene["field_grade_source_hygiene_passed"],
            "suspicious_route_result_count": hygiene["suspicious_route_result_count"],
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_frozen_delta_price_claim_allowed": False,
            "plain_english_answer": (
                "The strongest current story is not 'everything wins.' It is that one champion family has a "
                "clear source-conditioned replay win, with the wave/resonance timing lane standing out as the "
                "cleanest high-volume internal lane. Energy price pressure is promising but mixed; branching is "
                "honest negative evidence where classic baselines still compete."
            ),
        },
        "lane_scoreboard": lane_cards,
        "dataset_champion_cards": dataset_cards,
        "source_hygiene": hygiene,
        "source_health": source_health(source_max),
        "claim_state": claim_state(gauntlet, battery, domain, dollar_gate, locked_sweep),
        "next_10_actions": [
            "Promote wave_resonance_timing as the first paid field-replay candidate.",
            "Run leave-one-source-out on the current champion.",
            "Run residual autocorrelation on each lane, not only aggregate scores.",
            "Clean the replay manifest so package/runtime files stay in stress tests and cannot inflate live-system proof.",
            "Expand thermal_ventilation with real HVAC/cooling or facility traces.",
            "Expand energy_price_pressure_proxy with ISO/RTO load, price, outage, and forecast windows.",
            "Keep branching_transport visible as negative evidence until it beats min-cost/Steiner/MST baselines.",
            "Add SAM.gov opportunity feed after a valid key is configured.",
            "Fix EPA AQS and NREL credentials/endpoints or demote them from enabled sources.",
            "Ask EPRI/TVA/utility lab for a held-out dataset, baseline, acceptance metric, and cost conversion.",
        ],
        "source_artifacts": {
            "champion_metric_gauntlet": str(GAUNTLET_JSON.relative_to(ROOT)),
            "champion_metric_battery": str(BATTERY_JSON.relative_to(ROOT)),
            "locked_source_baseline_replay_sweep": str(LOCKED_SWEEP_JSON.relative_to(ROOT)),
            "live_source_measurement_maximizer": str(SOURCE_MAX_JSON.relative_to(ROOT)),
            "live_domain_deployment_feed": str(DOMAIN_JSON.relative_to(ROOT)),
            "dollar_claim_gate": str(DOLLAR_GATE_JSON.relative_to(ROOT)),
        },
    }
    payload["rollup_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "lane_scoreboard": payload["lane_scoreboard"],
            "source_health": payload["source_health"],
            "claim_state": payload["claim_state"],
            "source_hygiene": payload["source_hygiene"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    claim = as_dict(payload.get("claim_state"))
    source = as_dict(payload.get("source_health"))
    lines = [
        "# Champion Expanded Metric Rollup",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        f"Rollup SHA-256: `{payload.get('rollup_sha256')}`",
        "",
        "## Plain English",
        "",
        str(summary.get("plain_english_answer") or ""),
        "",
        "## Evidence Summary",
        "",
        f"- Champion: `{summary.get('champion_family')}`",
        f"- Named baseline: `{summary.get('named_baseline')}`",
        f"- Holdout wins: `{summary.get('holdout_wins')}/{summary.get('holdout_count')}`",
        f"- Lanes: `{summary.get('lane_count')}`",
        f"- Strong lanes: `{summary.get('strong_lane_count')}`",
        f"- Total baseline comparisons: `{summary.get('total_baseline_comparisons')}`",
        f"- Total candidate wins: `{summary.get('total_candidate_wins')}`",
        f"- Overall locked-lane win rate: `{summary.get('overall_locked_lane_win_rate_pct')}%`",
        f"- Estimated rows replayed: `{summary.get('estimated_rows_replayed')}`",
        f"- Numeric samples read: `{summary.get('numeric_samples_read')}`",
        f"- Source systems replayed: `{summary.get('source_system_count')}`",
        f"- Source files replayed: `{summary.get('source_file_count')}`",
        f"- Manifest source entries: `{summary.get('manifest_source_count')}`",
        f"- Field-grade source hygiene passed: `{str(summary.get('field_grade_source_hygiene_passed')).lower()}`",
        f"- Suspicious route results: `{summary.get('suspicious_route_result_count')}`",
        f"- Measured sources: `{source.get('measured_sources')}/{source.get('enabled_sources')}`",
        f"- Latest bounded measured rows: `{source.get('total_measured_rows_latest_pull')}`",
        "",
        "## Lane Scoreboard",
        "",
        "| Lane | Status | Wins | Comparisons | Win Rate | Rows | Claim Gate |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for row in as_list(payload.get("lane_scoreboard")):
        if not isinstance(row, dict):
            continue
        lines.append(
            "| "
            f"`{row.get('lane')}` | "
            f"`{row.get('status')}` | "
            f"`{row.get('candidate_wins')}` | "
            f"`{row.get('baseline_comparisons')}` | "
            f"`{row.get('win_rate_pct')}%` | "
            f"`{row.get('estimated_rows_replayed')}` | "
            f"{row.get('claim_gate')} |"
        )
    lines.extend(
        [
            "",
            "## Top Dataset Champion Cards",
            "",
            "| System | Lane | Candidate | Wins | Comparisons | Win Rate | Rows | Source |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in as_list(payload.get("dataset_champion_cards"))[:12]:
        if not isinstance(row, dict):
            continue
        source_path = str(row.get("source_path") or "")
        source_label = Path(source_path).name if source_path else ""
        lines.append(
            "| "
            f"`{row.get('system')}` | "
            f"`{row.get('lane')}` | "
            f"`{row.get('candidate_family')}` | "
            f"`{row.get('candidate_wins')}` | "
            f"`{row.get('baseline_comparisons')}` | "
            f"`{row.get('win_rate_pct')}%` | "
            f"`{row.get('estimated_rows')}` | "
            f"`{source_label}` |"
        )
    lines.extend(
        [
            "",
            "## Claim State",
            "",
            f"- Live-domain reviewer ready: `{str(claim.get('live_domain_reviewer_ready')).lower()}`",
            f"- Field-validation claim allowed: `{str(claim.get('field_validation_claim_allowed')).lower()}`",
            f"- Real-dollar savings claim allowed: `{str(claim.get('real_dollar_savings_claim_allowed')).lower()}`",
            f"- Fixed frozen-delta price claim allowed: `{str(claim.get('fixed_frozen_delta_price_claim_allowed')).lower()}`",
            "",
            "## Source Hygiene",
            "",
            str(as_dict(payload.get("source_hygiene")).get("claim_impact") or ""),
            "",
            "## Missing / Next Source Families",
            "",
        ]
    )
    for item in as_list(source.get("missing_or_next_sources")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Next 10 Actions",
            "",
        ]
    )
    for action in as_list(payload.get("next_10_actions")):
        lines.append(f"- {action}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            BOUNDARY,
        ]
    )
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
