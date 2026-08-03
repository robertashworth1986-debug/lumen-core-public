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

KURAMOTO_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
CHAMPION_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
TRUTH_SWEEP_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"
VALUE_METER_JSON = OUT_OPS / "live_proof_value_meter_latest.json"
DOLLAR_LADDER_JSON = OUT_OPS / "field_validated_dollar_claim_ladder_latest.json"
LIVE_DOMAIN_DEPLOYMENT_JSON = OUT_OPS / "live_domain_deployment_feed_latest.json"
LIVE_SOURCE_MAX_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"
GEOMETRY_SOURCE_MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"
GEOMETRY_FRONTIER_JSON = OUT_OPS / "geometry_live_systems_frontier_latest.json"

OUT_JSON = OUT_OPS / "champion_metric_gauntlet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_metric_gauntlet.json"
OUT_MD = DOCS / "CHAMPION_METRIC_GAUNTLET_2026-06-27.md"

BOUNDARY = (
    "Measured candidate metric gauntlet only. This artifact records the current direct measured result, the tests it "
    "passed, the tests it failed, and the safest claim language. No current family is an internal performance champion. It does not create field validation, "
    "realized savings, trading profit, medical efficacy, award certainty, or a fixed dollar price for frozen deltas."
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
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def money(value: Any) -> str:
    return f"${as_float(value):,.2f}"


def metric_gate(
    name: str,
    actual: Any,
    threshold: Any,
    passed: bool,
    why_it_matters: str,
    claim_effect: str,
    blocker: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "actual": actual,
        "threshold": threshold,
        "passed": bool(passed),
        "status": "PASS" if passed else ("BLOCKED" if blocker else "NEEDS_WORK"),
        "blocker": bool(blocker and not passed),
        "why_it_matters": why_it_matters,
        "claim_effect": claim_effect,
    }


def live_domain_verified() -> bool:
    deployment = read_json(LIVE_DOMAIN_DEPLOYMENT_JSON)
    summary = as_dict(deployment.get("summary"))
    return (
        summary.get("domain_deployment_state") == "LIVE_DOMAIN_HASH_VERIFIED"
        and bool(summary.get("live_domain_reviewer_ready"))
        and as_int(summary.get("required_remote_hash_match_count")) >= as_int(summary.get("required_feed_count"), 1)
    )


def live_domain_deployment_status() -> dict[str, Any]:
    deployment = read_json(LIVE_DOMAIN_DEPLOYMENT_JSON)
    summary = as_dict(deployment.get("summary"))
    stale_rows = [row for row in as_list(deployment.get("required_remote_missing_or_stale")) if isinstance(row, dict)]
    stale_keys = [str(row.get("key")) for row in stale_rows if row.get("key")]
    required = as_int(summary.get("required_feed_count"))
    matched = as_int(summary.get("required_remote_hash_match_count"))
    stale_or_missing = as_int(summary.get("required_remote_stale_or_missing_count"), len(stale_rows))
    reachable_but_stale = as_int(summary.get("required_remote_reachable_but_stale_count"))
    state = str(summary.get("domain_deployment_state") or "NOT_CHECKED")
    reviewer_ready = (
        state == "LIVE_DOMAIN_HASH_VERIFIED"
        and bool(summary.get("live_domain_reviewer_ready"))
        and required > 0
        and matched >= required
    )
    return {
        "live_domain_reviewer_ready": reviewer_ready,
        "domain_deployment_state": state,
        "required_feed_count": required,
        "required_remote_hash_match_count": matched,
        "required_remote_stale_or_missing_count": stale_or_missing,
        "required_remote_reachable_but_stale_count": reachable_but_stale,
        "required_remote_missing_or_stale_keys": stale_keys,
        "first_required_remote_issue": stale_rows[0] if stale_rows else {},
        "safe_deploy_command": str(summary.get("safe_deploy_command") or ""),
        "next_domain_action": str(summary.get("next_domain_action") or ""),
        "plain_english_answer": str(summary.get("plain_english_answer") or ""),
    }


def strongest_current(champion: dict[str, Any], kuramoto: dict[str, Any]) -> dict[str, Any]:
    summary = as_dict(kuramoto.get("summary"))
    evidence = summary
    family = str(evidence.get("candidate") or "kuramoto_phase_coupling")
    label = "Kuramoto phase coupling"
    baseline = str(
        evidence.get("named_baseline") or "kalman_local_linear_trend"
    )
    mean_delta = as_float(evidence.get("mean_delta_vs_kalman"))
    stability_ratio = 0.0
    min_delta = as_float(evidence.get("min_delta_vs_kalman"))
    if mean_delta > 0 and min_delta > 0:
        stability_ratio = min_delta / mean_delta

    return {
        "family": family,
        "label": label,
        "lane": "wave_resonance_timing",
        "evidence_mode": evidence.get("evidence_mode", ""),
        "evidence_status": "direct_measured_eia_nonpromotion_result",
        "claim_stage": "direct_measured_source_specific_baseline_gate_failed",
        "named_baseline": baseline,
        "holdout_count": as_int(evidence.get("holdout_count")),
        "wins_vs_named_baseline": as_int(evidence.get("wins_vs_kalman") or evidence.get("wins_vs_best_baseline")),
        "wins_vs_best_baseline": as_int(evidence.get("wins_vs_best_baseline")),
        "losses_or_ties_vs_named_baseline": as_int(evidence.get("losses_or_ties_vs_kalman")),
        "win_rate_vs_named_baseline": round(as_float(evidence.get("win_rate_vs_kalman")), 6),
        "mean_delta_vs_named_baseline": round(mean_delta, 6),
        "min_delta_vs_named_baseline": round(min_delta, 6),
        "max_delta_vs_named_baseline": round(as_float(evidence.get("max_delta_vs_kalman")), 6),
        "effect_stability_ratio_min_over_mean": round(stability_ratio, 6),
        "one_sided_sign_test_p_value": as_float(evidence.get("one_sided_sign_test_p_value"), 1.0),
        "wilson_95_win_rate_lower": round(as_float(evidence.get("wilson_95_win_rate_lower")), 6),
        "wilson_95_win_rate_upper": round(as_float(evidence.get("wilson_95_win_rate_upper")), 6),
        "estimated_rows_replayed": as_int(evidence.get("estimated_rows_replayed")),
        "numeric_samples_read": as_int(evidence.get("numeric_samples_read")),
        "source_system_count": as_int(evidence.get("source_system_count")),
        "source_systems": as_list(evidence.get("source_systems")),
        "authority_count": as_int(evidence.get("authority_count")),
        "holdout_chain_sha256": str(evidence.get("holdout_chain_sha256", "")),
        "development_selected_candidate": str(
            evidence.get("development_selected_candidate", "")
        ),
        "candidate_was_protocol_selected": bool(
            evidence.get("candidate_was_protocol_selected")
        ),
        "registered_baseline_count": as_int(
            evidence.get("registered_baseline_count")
        ),
        "registered_baseline_mean_win_count": as_int(
            evidence.get("registered_baseline_mean_win_count")
        ),
        "candidate_beats_all_registered_baselines_after_holm": bool(
            evidence.get(
                "candidate_beats_all_registered_baselines_after_holm"
            )
        ),
        "protocol_grade_internal_champion": bool(
            evidence.get("protocol_grade_internal_champion")
        ),
        "ready_for_buyer_authorized_field_replay_request": bool(
            evidence.get("ready_for_buyer_authorized_field_replay_request")
        ),
        "passes_internal_20_holdout_gate": bool(evidence.get("passes_internal_20_holdout_gate")),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
    }


def build_metric_gauntlet(
    strongest: dict[str, Any],
    champion_summary: dict[str, Any],
    truth_summary: dict[str, Any],
    truth_gates: dict[str, Any],
    live_domain_status: dict[str, Any],
) -> list[dict[str, Any]]:
    holdout_count = as_int(strongest.get("holdout_count"))
    win_rate = as_float(strongest.get("win_rate_vs_named_baseline"))
    mean_delta = as_float(strongest.get("mean_delta_vs_named_baseline"))
    authorities = as_int(strongest.get("authority_count"))
    rows = as_int(strongest.get("estimated_rows_replayed"))
    chain = str(strongest.get("holdout_chain_sha256", ""))
    live_domain_ready = bool(live_domain_status.get("live_domain_reviewer_ready"))
    required = as_int(live_domain_status.get("required_feed_count"))
    matched = as_int(live_domain_status.get("required_remote_hash_match_count"))
    stale_or_missing = as_int(live_domain_status.get("required_remote_stale_or_missing_count"))

    return [
        metric_gate(
            "holdout_depth",
            holdout_count,
            ">= 1,000 paired measured holdout days",
            holdout_count >= 1_000,
            "Confirms the direct measured result has adequate chronological depth.",
            "Supports reporting the measured nonpromotion result, not champion language.",
        ),
        metric_gate(
            "development_selection_frozen",
            bool(strongest.get("candidate_was_protocol_selected")),
            "true",
            bool(strongest.get("candidate_was_protocol_selected")),
            "Prevents substituting a candidate after inspecting the holdout.",
            "Kuramoto remains a post-selection audit, not the protocol candidate.",
            blocker=True,
        ),
        metric_gate(
            "baseline_win_rate",
            round(win_rate, 6),
            "> 0.50 with positive mean skill",
            win_rate > 0.50 and mean_delta > 0,
            "A paired win count must agree with the direction of the mean source-native metric.",
            "Current named-baseline promotion remains blocked.",
        ),
        metric_gate(
            "mean_skill_positive",
            round(mean_delta, 6),
            "> 0",
            mean_delta > 0,
            "Positive skill means lower seasonal-MASE-7 than the named EIA baseline.",
            "The current negative mean is a nonpromotion result.",
        ),
        metric_gate(
            "all_source_specific_baselines_global_holm",
            bool(
                strongest.get(
                    "candidate_beats_all_registered_baselines_after_holm"
                )
            ),
            "true",
            bool(
                strongest.get(
                    "candidate_beats_all_registered_baselines_after_holm"
                )
            ),
            "Promotion requires beating every registered EIA baseline after global multiplicity correction.",
            "No internal performance champion is allowed.",
            blocker=True,
        ),
        metric_gate(
            "authority_coverage",
            authorities,
            ">= 8 EIA balancing authorities",
            authorities >= 8,
            "Checks that the measured result spans the complete frozen authority panel.",
            "Supports bounded panel-coverage language only.",
        ),
        metric_gate(
            "row_replay_depth",
            rows,
            ">= 10,000 evaluated strategy rows",
            rows >= 10_000,
            "Shows the benchmark evaluated the complete frozen strategy panel.",
            "Supports measured benchmark-depth language.",
        ),
        metric_gate(
            "hash_chain_present",
            chain[:12] + "..." if len(chain) == 64 else chain,
            "64 hex characters",
            len(chain) == 64,
            "Makes the proof packet traceable.",
            "Supports frozen evidence language.",
        ),
        metric_gate(
            "vault_hashes_verified",
            bool(champion_summary.get("vault_hashes_verified") or truth_summary.get("vault_hashes_verified")),
            "true",
            bool(champion_summary.get("vault_hashes_verified") or truth_summary.get("vault_hashes_verified")),
            "Protects provenance when copying to external storage.",
            "Supports reproducibility infrastructure language.",
        ),
        metric_gate(
            "all_families_live_benchmarked",
            bool(truth_gates.get("all_registered_families_live_benchmarked")),
            "true before broad all-family claims",
            bool(truth_gates.get("all_registered_families_live_benchmarked")),
            "Blocks universal geometry-superiority claims.",
            "Broad all-family language remains blocked.",
            blocker=True,
        ),
        metric_gate(
            "live_domain_feed_routed",
            f"{matched}/{required} required hosted hashes match; {stale_or_missing} stale/missing",
            "all required hosted hashes match before hosted reviewer proof claim",
            bool(truth_gates.get("vps_domain_live_dashboard_routed") or live_domain_ready),
            "A reviewer-facing domain needs fresh hosted hashes, not just local files.",
            "Hosted reviewer proof language is allowed once all required feed hashes match.",
            blocker=True,
        ),
        metric_gate(
            "field_validation",
            bool(truth_gates.get("field_validation_claim_allowed")),
            "true before field validated language",
            bool(truth_gates.get("field_validation_claim_allowed")),
            "Requires buyer-authorized operational data and a locked acceptance test.",
            "Field-validation and realized-savings language remains blocked.",
            blocker=True,
        ),
    ]


def dashboard_feed_status() -> dict[str, Any]:
    deployment_status = live_domain_deployment_status()
    feeds = [
        DASHBOARD_DATA / "champion_metric_gauntlet.json",
        DASHBOARD_DATA / "kuramoto_holdout_expansion.json",
        DASHBOARD_DATA / "geometry_champion_of_champions.json",
        DASHBOARD_DATA / "field_money_truth_sweep.json",
        DASHBOARD_DATA / "live_proof_value_meter.json",
        DASHBOARD_DATA / "field_validated_dollar_claim_ladder.json",
        DASHBOARD_DATA / "dollar_claim_gate.json",
    ]
    rows = []
    for path in feeds:
        rows.append(
            {
                "relative_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "",
            }
        )
    ready = [row for row in rows if row["exists"]]
    domain_ready = bool(deployment_status["live_domain_reviewer_ready"])
    return {
        "local_feed_count": len(rows),
        "local_feed_ready_count": len(ready),
        "local_feeds_ready": len(ready) == len(rows),
        "live_domain_routed": domain_ready,
        "domain_deployment_state": deployment_status["domain_deployment_state"],
        "required_feed_count": deployment_status["required_feed_count"],
        "required_remote_hash_match_count": deployment_status["required_remote_hash_match_count"],
        "required_remote_stale_or_missing_count": deployment_status["required_remote_stale_or_missing_count"],
        "required_remote_reachable_but_stale_count": deployment_status[
            "required_remote_reachable_but_stale_count"
        ],
        "required_remote_missing_or_stale_keys": deployment_status["required_remote_missing_or_stale_keys"],
        "first_required_remote_issue": deployment_status["first_required_remote_issue"],
        "safe_deploy_command": deployment_status["safe_deploy_command"],
        "next_domain_action": deployment_status["next_domain_action"],
        "status": (
            "LIVE_DOMAIN_HASH_VERIFIED"
            if len(ready) == len(rows) and domain_ready
            else ("LOCAL_READY_DOMAIN_NOT_VERIFIED" if len(ready) == len(rows) else "LOCAL_FEEDS_INCOMPLETE")
        ),
        "feeds": rows,
    }


def source_breadth_universe(strongest: dict[str, Any]) -> dict[str, Any]:
    """Separate the measured candidate scope from the broader source estate."""
    live_source = read_json(LIVE_SOURCE_MAX_JSON)
    live_summary = as_dict(live_source.get("summary"))
    manifest = read_json(GEOMETRY_SOURCE_MANIFEST_JSON)
    manifest_summary = as_dict(manifest.get("summary"))
    frontier = read_json(GEOMETRY_FRONTIER_JSON)
    frontier_summary = as_dict(frontier.get("summary"))

    measured_names = [str(name) for name in as_list(live_summary.get("measured_source_names"))]
    failed_names = [str(name) for name in as_list(live_summary.get("failed_or_thin_source_names"))]
    champion_sources = [str(name) for name in as_list(strongest.get("source_systems"))]

    return {
        "claim_boundary": (
            "The direct measured candidate source count and the broader live-source universe are intentionally not the "
            "same metric. The candidate count covers the frozen EIA holdout only. The broader universe counts "
            "providers, local/live files, and legacy manifest rows available for future compatibility work; those "
            "counts are not performance evidence and do not imply a champion."
        ),
        "champion_replay": {
            "source_system_count": as_int(strongest.get("source_system_count")),
            "source_systems": champion_sources,
            "estimated_rows_replayed": as_int(strongest.get("estimated_rows_replayed")),
            "numeric_samples_read": as_int(strongest.get("numeric_samples_read")),
        },
        "fresh_provider_measurement": {
            "enabled_provider_count": as_int(live_summary.get("enabled_sources")),
            "measured_provider_count": as_int(live_summary.get("measured_sources")),
            "failed_or_thin_provider_count": as_int(live_summary.get("failed_or_thin_sources")),
            "fresh_measured_rows": as_int(live_summary.get("total_measured_rows")),
            "coverage_pct": as_float(live_summary.get("coverage_pct")),
            "measured_provider_names": measured_names,
            "failed_or_thin_provider_names": failed_names,
            "estimated_annual_value_surface_usd": round(
                as_float(live_summary.get("estimated_annual_value_surface_usd")), 2
            ),
        },
        "geometry_manifest": {
            "unique_source_count": as_int(manifest_summary.get("unique_source_count")),
            "ready_for_benchmark_row_count": as_int(manifest_summary.get("ready_for_benchmark_row_count")),
            "manifest_row_count": as_int(manifest_summary.get("manifest_row_count")),
            "estimated_rows_mapped": as_int(manifest_summary.get("estimated_rows_mapped")),
            "unique_source_estimated_rows": as_int(manifest_summary.get("unique_source_estimated_rows")),
            "lane_count": as_int(manifest_summary.get("lane_count")),
        },
        "frontier": {
            "ranked_family_count": as_int(frontier_summary.get("ranked_family_count")),
            "registered_family_count": as_int(frontier_summary.get("registered_family_count")),
            "canonical_measured_sources": as_int(frontier_summary.get("canonical_measured_sources")),
            "canonical_measured_rows": as_int(frontier_summary.get("canonical_measured_rows")),
            "local_file_inventory_count": as_int(frontier_summary.get("local_file_inventory_count")),
            "local_estimated_rows": as_int(frontier_summary.get("local_estimated_rows")),
            "provider_snapshot_file_count": as_int(frontier_summary.get("provider_snapshot_file_count")),
        },
        "next_fix": (
            "Promote more measured providers into candidate-specific holdout expansions only after each provider "
            "has a named baseline, a normalized schema, and an acceptance metric. That raises source breadth "
            "without weakening the proof chain."
        ),
    }


def hardware_validation_unlock() -> dict[str, Any]:
    return {
        "claim_boundary": (
            "Grid, RF, and PLL hardware validation can be designed now, but it becomes field validation only after "
            "an external lab, buyer, utility, or authorized operator runs or accepts a locked protocol on their "
            "instrumented data or test bench."
        ),
        "grid_validation": {
            "required_inputs": [
                "PMU or frequency/load telemetry",
                "ISO/RTO or utility event windows",
                "forecast and incumbent baseline outputs",
                "accepted cost factors such as imbalance, outage, congestion, or analyst review cost",
                "operator-approved holdout period",
            ],
            "acceptance_metrics": [
                "forecast error reduction",
                "phase/frequency drift early-warning lead time",
                "false positive and false negative rate",
                "latency under operational cadence",
                "dollar conversion agreed before replay",
            ],
        },
        "rf_validation": {
            "required_inputs": [
                "SDR or spectrum analyzer captures",
                "signal generator or channel emulator settings",
                "noise, jammer, fading, or interference profiles",
                "baseline receiver or classifier outputs",
                "timestamped lab notebook and calibration records",
            ],
            "acceptance_metrics": [
                "SNR or SINR improvement",
                "EVM and BER reduction",
                "lock or reacquisition time",
                "classification/detection lift",
                "latency and compute budget",
            ],
        },
        "pll_validation": {
            "required_inputs": [
                "reference oscillator and PLL configuration",
                "signal generator jitter/drift injection profile",
                "oscilloscope, phase-noise analyzer, or timestamp counter logs",
                "temperature/load perturbation profile",
                "baseline loop filter or Kalman/PLL controller result",
            ],
            "acceptance_metrics": [
                "lock time",
                "cycle-slip count",
                "phase error distribution",
                "jitter transfer and peaking",
                "phase noise or Allan deviation",
                "recovery time after perturbation",
            ],
        },
        "fixed_dollar_claim_blockers": [
            "No buyer-authorized before/after deployment or accepted field replay yet.",
            "No pre-agreed economic conversion factor for each sector and use case.",
            "No signed acceptance criteria from the system owner or external lab.",
            "No proof that the measured lift survived external holdouts controlled by the buyer.",
            "No contract term that prices a frozen delta as a deliverable or paid diagnostic artifact.",
        ],
        "what_api_keys_do": [
            "Pull fresh measured rows from many live systems.",
            "Create timestamped, hashable source snapshots.",
            "Populate benchmarks and dashboards with current evidence.",
            "Support buyer discovery by showing where a repeatable anomaly or lift exists.",
            "They do not by themselves create realized savings; the acceptance protocol does that.",
        ],
    }


def next_tests() -> list[dict[str, str]]:
    return [
        {
            "test": "amplitude_error_check",
            "reason": "Phase-locking can win timing while hiding amplitude mistakes.",
            "output": "MAE/RMSE/MAPE by holdout and by source system.",
        },
        {
            "test": "phase_error_distribution",
            "reason": "The strongest claim is phase behavior; measure it directly.",
            "output": "Circular error, phase slip count, and phase-lock duration.",
        },
        {
            "test": "directional_accuracy",
            "reason": "Buyers care whether the system moves action in the right direction.",
            "output": "Up/down or risk/no-risk confusion matrix.",
        },
        {
            "test": "residual_autocorrelation",
            "reason": "A model that leaves structured residuals has not captured the system.",
            "output": "Ljung-Box style residual health by holdout.",
        },
        {
            "test": "ablation_against_neighbor_geometries",
            "reason": "Proves Kuramoto is not just inheriting a general wave-family boost.",
            "output": "Kuramoto vs PLL, Lissajous, harmonic potential, and Kalman variants.",
        },
        {
            "test": "drift_and_outlier_stress",
            "reason": "Field systems break under drift, missingness, and spikes.",
            "output": "Performance under dropouts, jumps, and delayed samples.",
        },
        {
            "test": "latency_and_cost_budget",
            "reason": "Operational buyers need to know if it runs fast enough.",
            "output": "Runtime, memory, and update cadence per source.",
        },
        {
            "test": "buyer_economic_conversion_dry_run",
            "reason": "Dollar claims need accepted conversion factors.",
            "output": "Scenario table only, with field-validation gates still closed.",
        },
        {
            "test": "hosted_hash_verification",
            "reason": "The live domain should serve the same proof hashes as the local packet.",
            "output": "VPS/domain feed manifest with matching SHA-256 values.",
        },
        {
            "test": "authorized_field_replay_protocol",
            "reason": "This is the bridge from internal proof to a field validation claim.",
            "output": "Signed or logged buyer replay packet with locked baseline and acceptance criteria.",
        },
    ]


def metric_expansion_suite(
    strongest: dict[str, Any],
    source_breadth: dict[str, Any],
    feed_status: dict[str, Any],
) -> list[dict[str, Any]]:
    """Define the next serious metric families without pretending they are all passed."""

    champion_replay = as_dict(source_breadth.get("champion_replay"))
    fresh = as_dict(source_breadth.get("fresh_provider_measurement"))
    manifest = as_dict(source_breadth.get("geometry_manifest"))
    rows = as_int(champion_replay.get("estimated_rows_replayed"))
    holdouts = as_int(strongest.get("holdout_count"))
    wins = as_int(strongest.get("wins_vs_named_baseline"))
    min_delta = as_float(strongest.get("min_delta_vs_named_baseline"))
    p_value = as_float(strongest.get("one_sided_sign_test_p_value"), 1.0)

    def row(
        family_id: str,
        status: str,
        target_question: str,
        metrics: list[str],
        current_evidence: str,
        next_action: str,
        claim_gate: str,
    ) -> dict[str, Any]:
        return {
            "family_id": family_id,
            "status": status,
            "target_question": target_question,
            "metrics": metrics,
            "current_evidence": current_evidence,
            "next_action": next_action,
            "claim_gate": claim_gate,
        }

    return [
        row(
            "forecast_error_and_residuals",
            "EVIDENCED_CORE_READY_TO_EXPAND",
            "Does the champion reduce error against a named incumbent baseline?",
            ["MAE", "RMSE", "MAPE_or_SMAPE", "WAPE", "residual_bias", "residual_autocorrelation"],
            (
                f"{wins}/{holdouts} holdout wins vs {strongest.get('named_baseline')} with "
                f"minimum delta {round(min_delta, 6)} and {rows:,} estimated rows replayed."
            ),
            "Add per-source residual health tables before promoting more live-breadth providers into the champion replay.",
            "Internal champion claim allowed; field-performance language remains blocked.",
        ),
        row(
            "phase_lock_and_timing",
            "EVIDENCED_CORE_NEEDS_DIRECT_PHASE_DIAGNOSTICS",
            "Is the win specifically a phase/timing advantage rather than generic smoothing?",
            ["circular_phase_error", "phase_slip_count", "lock_duration", "recovery_time", "coherence", "spectral_concentration"],
            (
                f"Champion lane is {strongest.get('lane')} with sign-test p-value {p_value}; direct phase diagnostics "
                "are still the next strongest proof upgrade."
            ),
            "Run a dedicated phase-error distribution report for grid/EIA, market, macro, and sports-market source slices.",
            "Phase-lock language is allowed as a hypothesis-backed internal finding, not as hardware or field validation.",
        ),
        row(
            "robustness_and_stress",
            "READY_FOR_NEXT_RUN",
            "Does the champion survive missingness, spikes, drift, and delayed samples?",
            ["dropout_sensitivity", "outlier_sensitivity", "regime_split_delta", "rolling_window_stability", "bootstrap_ci"],
            "Current gauntlet passes minimum-positive-delta and Wilson lower-bound gates; explicit perturbation stress is the next layer.",
            "Replay the champion under frozen perturbation seeds and publish pass/fail by source system.",
            "Robustness language waits for perturbation artifacts and frozen seeds.",
        ),
        row(
            "source_generalization",
            "READY_FOR_LIVE_BREADTH_PROMOTION",
            "Does the champion generalize beyond the current four promoted replay systems?",
            ["leave_one_source_out", "source_group_holdout", "provider_promotion_rate", "schema_normalization_success"],
            (
                f"Current champion replay uses {champion_replay.get('source_system_count')} promoted source systems; "
                f"broader live breadth has {fresh.get('measured_provider_count')}/{fresh.get('enabled_provider_count')} measured providers "
                f"and {manifest.get('ready_for_benchmark_row_count')} ready-for-benchmark manifest rows."
            ),
            "Promote one provider at a time only after a named baseline, schema adapter, and acceptance metric exist.",
            "Broad live-breadth claims remain blocked until promoted sources pass locked benchmarks.",
        ),
        row(
            "decision_detection_quality",
            "READY_FOR_DOMAIN_SPECIFIC_RUN",
            "Would the champion improve a buyer decision, not just a numerical score?",
            ["precision", "recall", "F1", "false_alarm_rate", "miss_rate", "lead_time", "precision_recall_auc"],
            "Harbor/DICE/MissionWeave style artifacts provide separate decision lanes; the Kuramoto champion needs domain-specific decision mapping.",
            "Map one grid or maritime event dataset to a binary or ranked decision task with a locked baseline.",
            "Decision-lift language waits for task-specific labels or accepted event windows.",
        ),
        row(
            "operational_runtime_budget",
            "READY_FOR_NEXT_RUN",
            "Can the champion run fast enough for a real operator cadence?",
            ["runtime_p50", "runtime_p95", "memory_mb", "throughput_rows_per_second", "update_latency", "fail_closed_rate"],
            "Current proof establishes replay strength, not operational latency or deployment budget.",
            "Add timed benchmark wrappers around the champion replay and publish runtime budgets by source size.",
            "Operational-readiness language waits for latency and fail-closed evidence.",
        ),
        row(
            "economic_conversion",
            "BLOCKED_REQUIRES_EXTERNAL_OWNER",
            "How does a metric improvement convert into dollars for a named system?",
            ["avoided_outage_minutes", "energy_waste_reduction", "review_burden_reduction", "imbalance_or_congestion_cost", "false_alarm_cost"],
            "Current system has bounded opportunity surfaces, not accepted realized savings.",
            "Ask OpenPOWER AI/EPRI/utility/lab owner to approve baseline, metric, and cost conversion before replay.",
            "Real-dollar savings and fixed-dollar frozen-delta claims remain blocked.",
        ),
        row(
            "provenance_and_reproducibility",
            "EVIDENCED_CORE_READY_TO_EXPAND",
            "Can a reviewer reproduce the evidence chain?",
            ["input_hash", "config_hash", "output_hash", "code_commit", "manifest_sha256", "domain_hash_match"],
            (
                "Champion hash chain exists and dashboard feeds are local-ready; live-domain feed status is "
                f"{feed_status.get('status')}."
            ),
            "Keep regenerating feed manifests after each run and verify live-domain hashes before public claims.",
            "Hash-verified proof language is allowed only for feeds whose local and hosted hashes match.",
        ),
        row(
            "external_field_replay",
            "BLOCKED_REQUIRES_BUYER_OR_LAB",
            "Will an external owner reproduce the win on their held-out data and baseline?",
            ["locked_holdout_window", "incumbent_baseline", "acceptance_metric", "forbidden_tuning_rules", "signed_result"],
            "Current evidence is a direct measured nonpromotion result and is not ready for a performance replay request.",
            "Use the next research cycle to freeze a development-selected candidate before any external performance ask.",
            "Field-validation language remains blocked until an internally promoted candidate and an external owner accept the protocol.",
        ),
        row(
            "all_family_championship",
            "BLOCKED_REQUIRES_FULL_REGISTRY_RUN",
            "Can any development-selected wave family clear every source-specific baseline under the same metric budget?",
            ["family_count_tested", "baseline_count", "matched_budget", "winner_by_lane", "negative_results_logged"],
            "No current wave family cleared the measured EIA promotion gate; all-family live championship remains explicitly blocked.",
            "Search families on development data, freeze one candidate per lane, then publish the untouched holdout result and losers.",
            "Universal geometry-superiority language remains blocked.",
        ),
    ]


def build_payload() -> dict[str, Any]:
    generated = now_utc()
    kuramoto = read_json(KURAMOTO_JSON)
    champion = read_json(CHAMPION_JSON)
    truth = read_json(TRUTH_SWEEP_JSON)
    value_meter = read_json(VALUE_METER_JSON)
    dollar_ladder = read_json(DOLLAR_LADDER_JSON)

    champion_summary = as_dict(champion.get("summary"))
    truth_summary = as_dict(truth.get("summary"))
    truth_gates = as_dict(truth.get("gates"))
    strongest = strongest_current(champion, kuramoto)
    source_breadth = source_breadth_universe(strongest)
    hardware_unlock = hardware_validation_unlock()
    domain_status = live_domain_deployment_status()
    gauntlet = build_metric_gauntlet(strongest, champion_summary, truth_summary, truth_gates, domain_status)
    blockers = [row for row in gauntlet if row.get("blocker")]
    passed = [row for row in gauntlet if row.get("passed")]
    safe_annual = as_float(
        champion_summary.get("safe_estimated_annual_value_usd"),
        as_float(truth_summary.get("safe_estimated_annual_value_usd")),
    )
    safe_hourly = as_float(
        champion_summary.get("safe_estimated_hourly_value_usd"),
        as_float(truth_summary.get("safe_estimated_hourly_value_usd")),
    )
    feed_status = dashboard_feed_status()
    expansion_suite = metric_expansion_suite(strongest, source_breadth, feed_status)

    payload: dict[str, Any] = {
        "generated_utc": generated,
        "schema": "champion_metric_gauntlet_v2",
        "purpose": "Reviewer-safe metric gauntlet for the current direct measured geometry candidate result.",
        "boundary": BOUNDARY,
        "strongest_current": strongest,
        "summary": {
            "internal_champion": False,
            "protocol_grade_internal_champion": bool(
                strongest["protocol_grade_internal_champion"]
            ),
            "champion_family": strongest["family"],
            "champion_label": strongest["label"],
            "named_baseline": strongest["named_baseline"],
            "holdout_wins": strongest["wins_vs_named_baseline"],
            "holdout_count": strongest["holdout_count"],
            "holdout_win_rate": strongest["win_rate_vs_named_baseline"],
            "mean_delta_vs_named_baseline": strongest["mean_delta_vs_named_baseline"],
            "min_delta_vs_named_baseline": strongest["min_delta_vs_named_baseline"],
            "source_system_count": strongest["source_system_count"],
            "broader_measured_provider_count": source_breadth["fresh_provider_measurement"]["measured_provider_count"],
            "broader_enabled_provider_count": source_breadth["fresh_provider_measurement"]["enabled_provider_count"],
            "manifest_unique_source_count": source_breadth["geometry_manifest"]["unique_source_count"],
            "manifest_ready_for_benchmark_row_count": source_breadth["geometry_manifest"][
                "ready_for_benchmark_row_count"
            ],
            "estimated_rows_replayed": strongest["estimated_rows_replayed"],
            "numeric_samples_read": strongest["numeric_samples_read"],
            "one_sided_sign_test_p_value": strongest["one_sided_sign_test_p_value"],
            "wilson_95_win_rate_lower": strongest["wilson_95_win_rate_lower"],
            "gauntlet_pass_count": len(passed),
            "gauntlet_total_count": len(gauntlet),
            "blocking_gate_count": len(blockers),
            "metric_expansion_family_count": len(expansion_suite),
            "metric_expansion_ready_count": sum(
                1 for row in expansion_suite if "READY" in str(row.get("status", ""))
            ),
            "metric_expansion_blocked_count": sum(
                1 for row in expansion_suite if "BLOCKED" in str(row.get("status", ""))
            ),
            "reviewer_safe_internal_claim_allowed": False,
            "reviewer_safe_measured_nonpromotion_claim_allowed": True,
            "buyer_authorized_field_replay_request_ready": bool(
                strongest["ready_for_buyer_authorized_field_replay_request"]
            ),
            "bounded_estimated_value_claim_allowed": False,
            "paid_pilot_scoping_allowed": bool(
                truth_gates.get("paid_pilot_scoping_allowed") or champion_summary.get("paid_pilot_scoping_allowed")
            ),
            "paid_protocol_review_scoping_allowed": True,
            "safe_estimated_hourly_value_usd": 0.0,
            "safe_estimated_annual_value_usd": 0.0,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "live_domain_reviewer_ready": bool(feed_status["live_domain_routed"]),
            "plain_english_answer": (
                f"No current geometry family is an internal performance champion. "
                f"{strongest['label']} was audited on {strongest['holdout_count']} paired measured EIA holdout days; "
                f"it won {strongest['wins_vs_named_baseline']} pairs against {strongest['named_baseline']} but had "
                f"a negative mean skill delta of {strongest['mean_delta_vs_named_baseline']} and did not clear any "
                "complete source-specific all-baseline promotion gate. The broader source inventory is research "
                "capacity only, not performance evidence. The safe commercial ask is a paid protocol or evidence "
                "review, not a performance or savings claim."
            ),
        },
        "source_breadth_universe": source_breadth,
        "hardware_validation_unlock": hardware_unlock,
        "metric_gauntlet": gauntlet,
        "metric_expansion_suite": expansion_suite,
        "blockers": blockers,
        "next_10_tests": next_tests(),
        "dashboard_feed_status": feed_status,
        "source_artifacts": {
            "kuramoto_holdout_expansion": str(KURAMOTO_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_champion_of_champions": str(CHAMPION_JSON.relative_to(ROOT)).replace("\\", "/"),
            "field_money_truth_sweep": str(TRUTH_SWEEP_JSON.relative_to(ROOT)).replace("\\", "/"),
            "live_proof_value_meter": str(VALUE_METER_JSON.relative_to(ROOT)).replace("\\", "/"),
            "field_validated_dollar_claim_ladder": str(DOLLAR_LADDER_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
        "source_status": {
            "kuramoto_loaded": bool(kuramoto),
            "champion_loaded": bool(champion),
            "truth_sweep_loaded": bool(truth),
            "value_meter_loaded": bool(value_meter),
            "dollar_ladder_loaded": bool(dollar_ladder),
        },
        "claim_language": {
            "allowed": [
                "direct measured nonpromotion result",
                "source-specific baseline gauntlet",
                "negative result preserved with hashes",
                "paid protocol or evidence review scoping",
            ],
            "not_allowed": [
                "current internal performance champion",
                "source-conditioned holdout winner",
                "buyer-authorized performance replay request ready",
                "bounded estimated opportunity surface from the failed result",
                "field validated",
                "realized dollar savings",
                "grant award certainty",
                "fixed dollar value per frozen delta",
                "live trading edge or autonomous execution",
                "universal geometry superiority",
            ],
        },
    }
    payload["gauntlet_sha256"] = stable_sha256(
        {
            "strongest_current": payload["strongest_current"],
            "summary": payload["summary"],
            "metric_gauntlet": payload["metric_gauntlet"],
            "blockers": payload["blockers"],
            "next_10_tests": payload["next_10_tests"],
            "metric_expansion_suite": payload["metric_expansion_suite"],
            "source_breadth_universe": payload["source_breadth_universe"],
            "hardware_validation_unlock": payload["hardware_validation_unlock"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    strongest = as_dict(payload.get("strongest_current"))
    source_breadth = as_dict(payload.get("source_breadth_universe"))
    replay_scope = as_dict(source_breadth.get("champion_replay"))
    fresh_sources = as_dict(source_breadth.get("fresh_provider_measurement"))
    manifest = as_dict(source_breadth.get("geometry_manifest"))
    hardware = as_dict(payload.get("hardware_validation_unlock"))
    lines = [
        "# Champion Metric Gauntlet",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        "",
        "## What To Ask Me",
        "",
        "Ask questions that force evidence, gates, and next actions:",
        "",
        "1. What is proven right now, and what is only promising?",
        "2. Which geometry family is the current champion, and what named baseline did it beat?",
        "3. How many holdouts, rows, source systems, and hashes back the claim?",
        "4. Which claim is safe for a grant reviewer today?",
        "5. What exactly blocks field validation and real dollar savings?",
        "6. What is the next test that would increase valuation the most?",
        "7. What should be shown on the live domain before a reviewer sees it?",
        "8. What should never be said because it overclaims the evidence?",
        "",
        "## Current Answer",
        "",
        summary.get("plain_english_answer", ""),
        "",
        "## Strongest Current Candidate",
        "",
        f"- Family: `{strongest.get('family')}`",
        f"- Label: `{strongest.get('label')}`",
        f"- Lane: `{strongest.get('lane')}`",
        f"- Named baseline: `{strongest.get('named_baseline')}`",
        f"- Holdout wins: `{summary.get('holdout_wins')}/{summary.get('holdout_count')}`",
        f"- Mean delta vs baseline: `{summary.get('mean_delta_vs_named_baseline')}`",
        f"- Min delta vs baseline: `{summary.get('min_delta_vs_named_baseline')}`",
        f"- Source systems: `{summary.get('source_system_count')}`",
        f"- Broader measured providers: `{summary.get('broader_measured_provider_count')}/{summary.get('broader_enabled_provider_count')}`",
        f"- Manifest unique sources: `{summary.get('manifest_unique_source_count')}`",
        f"- Manifest ready benchmark rows: `{summary.get('manifest_ready_for_benchmark_row_count')}`",
        f"- Estimated rows replayed: `{summary.get('estimated_rows_replayed')}`",
        f"- Sign-test p-value: `{summary.get('one_sided_sign_test_p_value')}`",
        f"- Wilson lower 95% win-rate bound: `{summary.get('wilson_95_win_rate_lower')}`",
        f"- Holdout chain SHA-256: `{strongest.get('holdout_chain_sha256')}`",
        "",
        "## Safe Claim State",
        "",
        f"- Reviewer-safe internal claim allowed: `{str(summary.get('reviewer_safe_internal_claim_allowed')).lower()}`",
        f"- Buyer-authorized field replay request ready: `{str(summary.get('buyer_authorized_field_replay_request_ready')).lower()}`",
        f"- Bounded estimated value claim allowed: `{str(summary.get('bounded_estimated_value_claim_allowed')).lower()}`",
        f"- Paid pilot scoping allowed: `{str(summary.get('paid_pilot_scoping_allowed')).lower()}`",
        f"- Field-validation claim allowed: `{str(summary.get('field_validation_claim_allowed')).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary.get('real_dollar_savings_claim_allowed')).lower()}`",
        f"- Live trading or autonomous execution allowed: `{str(summary.get('live_trading_or_autonomous_execution_allowed')).lower()}`",
        f"- Safe estimated hourly value surface: `{money(summary.get('safe_estimated_hourly_value_usd'))}`",
        f"- Safe estimated annual value surface: `{money(summary.get('safe_estimated_annual_value_usd'))}`",
        "",
        "## Source Breadth Correction",
        "",
        source_breadth.get("claim_boundary", ""),
        "",
        f"- Champion replay source systems: `{replay_scope.get('source_system_count')}`",
        f"- Champion replay source names: `{', '.join(as_list(replay_scope.get('source_systems')) or [])}`",
        f"- Fresh measured providers: `{fresh_sources.get('measured_provider_count')}` of `{fresh_sources.get('enabled_provider_count')}`",
        f"- Fresh measured rows in latest bounded pull: `{fresh_sources.get('fresh_measured_rows')}`",
        f"- Measured provider names: `{', '.join(as_list(fresh_sources.get('measured_provider_names')) or [])}`",
        f"- Failed or thin provider names: `{', '.join(as_list(fresh_sources.get('failed_or_thin_provider_names')) or [])}`",
        f"- Manifest unique source count: `{manifest.get('unique_source_count')}`",
        f"- Manifest ready-for-benchmark row count: `{manifest.get('ready_for_benchmark_row_count')}`",
        f"- Manifest estimated rows mapped: `{manifest.get('estimated_rows_mapped')}`",
        "",
        "## Grid/RF/PLL Hardware Validation Gate",
        "",
        hardware.get("claim_boundary", ""),
        "",
        "A fixed dollar or realized-savings claim stays blocked until a buyer, lab, utility, or authorized operator accepts the test protocol, baseline, holdout window, and dollar conversion before the replay.",
        "",
        "### What API Keys Are For",
        "",
    ]
    for item in as_list(hardware.get("what_api_keys_do")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "### Fixed-Dollar Claim Blockers",
            "",
        ]
    )
    for item in as_list(hardware.get("fixed_dollar_claim_blockers")):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Metric Gates",
            "",
        ]
    )
    for gate in as_list(payload.get("metric_gauntlet")):
        if not isinstance(gate, dict):
            continue
        lines.append(
            f"- `{gate['name']}`: `{gate['status']}` | actual `{gate['actual']}` | threshold `{gate['threshold']}`"
        )
    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    blockers = [row for row in as_list(payload.get("blockers")) if isinstance(row, dict)]
    if blockers:
        for row in blockers:
            lines.append(f"- `{row['name']}`: {row['claim_effect']}")
    else:
        lines.append("- No blocking gates detected.")
    lines.extend(
        [
            "",
            "## Metric Expansion Suite",
            "",
            "This is the next flex layer: every promoted champion should be pressure-tested across error, phase, robustness, source-generalization, decision quality, runtime, economics, provenance, field replay, and all-family competition. Status labels preserve the difference between proven, ready-to-run, and externally blocked.",
            "",
        ]
    )
    for row in as_list(payload.get("metric_expansion_suite")):
        if isinstance(row, dict):
            lines.append(f"### `{row['family_id']}`")
            lines.append("")
            lines.append(f"- Status: `{row['status']}`")
            lines.append(f"- Question: {row['target_question']}")
            lines.append(f"- Metrics: `{', '.join(as_list(row.get('metrics')) or [])}`")
            lines.append(f"- Current evidence: {row['current_evidence']}")
            lines.append(f"- Next action: {row['next_action']}")
            lines.append(f"- Claim gate: {row['claim_gate']}")
            lines.append("")
    lines.extend(
        [
            "",
            "## Next 10 Tests",
            "",
        ]
    )
    for row in as_list(payload.get("next_10_tests")):
        if isinstance(row, dict):
            lines.append(f"- `{row['test']}`: {row['reason']} Output: {row['output']}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            payload.get("boundary", BOUNDARY),
            "",
            f"Gauntlet SHA-256: `{payload.get('gauntlet_sha256')}`",
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
    print(payload["summary"]["plain_english_answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
