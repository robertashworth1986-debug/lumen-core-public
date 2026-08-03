from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

REGISTRY_JSON = CONFIG / "geometry_championship_v1_registry.json"
READY_REPLAY_JSON = OUT_OPS / "geometry_ready_source_replay_latest.json"
SOURCE_MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"
REPEAT_VALIDATION_JSON = OUT_OPS / "geometry_repeat_proof_validation_latest.json"
UNCERTAINTY_JSON = OUT_OPS / "geometry_repeat_uncertainty_report_latest.json"
KURAMOTO_HOLDOUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
KURAMOTO_CROSS_SECTOR_JSON = OUT_OPS / "kuramoto_cross_sector_benchmark_latest.json"
VALUATION_JSON = OUT_OPS / "valuation_proposal_target_packet_latest.json"
CLAIM_MAP_JSON = OUT_OPS / "claim_strength_value_unlock_map_latest.json"
FIELD_MONEY_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"

OUT_JSON = OUT_OPS / "current_luma_proof_state_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "current_luma_proof_state.json"
OUT_MD = DOCS / "CURRENT_LUMA_PROOF_STATE_2026-06-26.md"

BOUNDARY = (
    "Current proof-state checkpoint generated from authoritative local artifacts. It ranks the strongest geometry "
    "candidates and proposal targets, but it does not grant field-validation, realized-savings, fixed-dollar "
    "frozen-delta, clinical, live-trading, or award-certainty claims."
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


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def pct(value: Any) -> str:
    return f"{safe_float(value) * 100:.1f}%"


def money(value: Any) -> str:
    return f"${safe_float(value):,.0f}"


def registry_summary(registry: dict[str, Any]) -> dict[str, Any]:
    families = [row for row in as_list(registry.get("families")) if isinstance(row, dict)]
    lanes = registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}
    benchmark_specified = [
        row
        for row in families
        if row.get("benchmark_hypothesis") and row.get("promotion_metric") and row.get("failure_mode")
    ]
    natural_paths = [row for row in families if str(row.get("natural_logic", "")).strip()]
    return {
        "family_count": len(families),
        "lane_count": len(lanes),
        "benchmark_specified_family_count": len(benchmark_specified),
        "natural_path_family_count": len(natural_paths),
        "natural_path_target_met": len(natural_paths) >= 50,
        "core_rule": registry.get("core_rule", ""),
        "evidence_boundary": registry.get("evidence_boundary", ""),
    }


def family_index(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("id", "")): row
        for row in as_list(registry.get("families"))
        if isinstance(row, dict) and row.get("id")
    }


def uncertainty_index(uncertainty: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("family_id", "")): row
        for row in as_list(uncertainty.get("analyses"))
        if isinstance(row, dict) and row.get("family_id")
    }


def repeat_candidates(
    repeat: dict[str, Any],
    uncertainty: dict[str, dict[str, Any]],
    families: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in as_list(repeat.get("validations")):
        if not isinstance(row, dict):
            continue
        family_id = str(row.get("family_id", ""))
        if not family_id:
            continue
        u = uncertainty.get(family_id, {})
        deltas = [
            safe_float(item.get("candidate_score_delta_vs_named_baseline"))
            for item in as_list(row.get("window_results"))
            if isinstance(item, dict) and item.get("candidate_score_delta_vs_named_baseline") is not None
        ]
        mean_delta = safe_float(u.get("delta_stats", {}).get("mean_delta")) if isinstance(u.get("delta_stats"), dict) else 0.0
        if mean_delta == 0.0 and deltas:
            mean_delta = mean(deltas)
        robust = bool(u.get("robust_repeat_uncertainty_gate_passed"))
        repeat_passed = bool(row.get("repeat_candidate_gate_passed"))
        evidence_mode = str(row.get("evidence_mode", ""))
        evidence_stage = str(row.get("evidence_stage", "not_repeat_promoted"))
        if robust:
            score = 100.0
        elif repeat_passed:
            score = 70.0
        elif evidence_mode == "direct_measured_replay":
            score = 35.0
        elif evidence_mode == "source_conditioned_synthetic_stress":
            score = 20.0
        else:
            score = 8.0
        rows[family_id] = {
            "family_id": family_id,
            "label": families.get(family_id, {}).get("label", family_id),
            "lane": row.get("lane", ""),
            "named_baseline": row.get("named_baseline", ""),
            "evidence_stage": evidence_stage,
            "proof_score": round(score, 3),
            "evidence_mode": evidence_mode,
            "eligible_for_repeat_confirmation": bool(
                row.get("eligible_for_repeat_confirmation")
            ),
            "repeat_candidate_gate_passed": repeat_passed,
            "robust_repeat_uncertainty_gate_passed": robust,
            "repeat_live_win_count": safe_int(row.get("repeat_live_win_count")),
            "window_count": safe_int(row.get("available_window_count")),
            "distinct_win_hash_count": safe_int(row.get("distinct_win_hash_count")),
            "min_source_count": safe_int(row.get("min_source_count")),
            "mean_delta_vs_named_baseline": round(mean_delta, 6),
            "lower_95_delta": (
                round(safe_float(u.get("delta_stats", {}).get("normal_t_lower_95_delta")), 6)
                if isinstance(u.get("delta_stats"), dict)
                else None
            ),
            "sign_test_p_value": u.get("one_sided_sign_test_p_value"),
            "wilson_lower_95_win_rate": u.get("wilson_lower_95_win_rate"),
            "source_names": sorted(
                set(row.get("direct_replay_source_names", []))
                | set(row.get("conditioned_stress_source_names", []))
            ),
            "blockers": row.get("blockers", []),
            "claim_boundary": row.get("claim_boundary", ""),
        }
    return rows


def ready_source_candidates(
    ready: dict[str, Any],
    families: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in as_list(ready.get("lane_scoreboard")):
        if not isinstance(row, dict):
            continue
        family_id = str(row.get("candidate_family", ""))
        if not family_id:
            continue
        replay_count = safe_int(row.get("replay_count"))
        wins = safe_int(row.get("candidate_win_count"))
        mean_delta = safe_float(row.get("mean_delta_vs_named_baseline"))
        evidence_mode = str(row.get("evidence_mode", ""))
        baseline_count = safe_int(row.get("baseline_comparison_count"))
        global_positive = safe_int(row.get("global_holm_positive_count"))
        if (
            evidence_mode == "direct_measured_replay"
            and baseline_count > 0
            and global_positive == baseline_count
        ):
            stage = "direct_measured_all_baseline_internal_champion_not_field_validated"
            base = 82.0
        elif evidence_mode == "direct_measured_replay":
            stage = "direct_measured_source_specific_nonpromotion"
            base = 35.0
        elif evidence_mode == "source_conditioned_synthetic_stress":
            stage = "source_conditioned_synthetic_stress_research_lead"
            base = 25.0 + min(wins * 2.0, 8.0)
        else:
            stage = "no_compatible_direct_measured_replay"
            base = 8.0
        rows[family_id] = {
            "family_id": family_id,
            "label": families.get(family_id, {}).get("label", family_id),
            "lane": row.get("lane", ""),
            "named_baseline": row.get("baseline_family", ""),
            "evidence_stage": stage,
            "proof_score": round(base, 3),
            "evidence_mode": evidence_mode,
            "direct_measured_replays": (
                replay_count if evidence_mode == "direct_measured_replay" else 0
            ),
            "source_conditioned_replays": (
                replay_count
                if evidence_mode == "source_conditioned_synthetic_stress"
                else 0
            ),
            "source_conditioned_wins": (
                wins
                if evidence_mode == "source_conditioned_synthetic_stress"
                else 0
            ),
            "source_conditioned_win_rate": (
                round(wins / baseline_count, 6)
                if evidence_mode == "source_conditioned_synthetic_stress"
                and baseline_count
                else 0.0
            ),
            "baseline_comparison_count": baseline_count,
            "global_holm_positive_count": global_positive,
            "estimated_rows": safe_int(row.get("performance_rows")),
            "numeric_samples": safe_int(row.get("performance_rows")),
            "mean_delta_vs_named_baseline": round(mean_delta, 6),
            "best_delta_vs_named_baseline": row.get("best_delta_vs_named_baseline"),
        }
    return rows


def merge_candidates(
    repeat_rows: dict[str, dict[str, Any]],
    ready_rows: dict[str, dict[str, Any]],
    families: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    merged_ids = set(repeat_rows) | set(ready_rows)
    merged: list[dict[str, Any]] = []
    for family_id in merged_ids:
        repeat = repeat_rows.get(family_id, {})
        ready = ready_rows.get(family_id, {})
        family = families.get(family_id, {})
        proof_score = max(safe_float(repeat.get("proof_score")), safe_float(ready.get("proof_score")))
        stages = [str(item.get("evidence_stage", "")) for item in (repeat, ready) if item]
        if any(stage.startswith("robust_repeat") for stage in stages):
            stage = "robust_repeat_plus_current_replay" if ready else "robust_repeat_champion_not_field_validated"
        elif any("direct_measured_source_specific_nonpromotion" in stage for stage in stages):
            stage = "direct_measured_source_specific_nonpromotion"
        elif any("source_conditioned_synthetic_stress" in stage for stage in stages):
            stage = "source_conditioned_synthetic_stress_research_lead"
        elif any("no_compatible" in stage for stage in stages):
            stage = "no_compatible_direct_measured_replay"
        else:
            stage = stages[0] if stages else "registry_only"
        merged.append(
            {
                "family_id": family_id,
                "label": family.get("label", family_id),
                "lane": repeat.get("lane") or ready.get("lane") or family.get("lane", ""),
                "evidence_stage": stage,
                "proof_score": round(proof_score, 3),
                "repeat_evidence": repeat,
                "source_conditioned_evidence": ready,
                "safe_claim": safe_claim(stage, repeat or ready),
                "next_move": next_move(stage, repeat or ready),
            }
        )
    merged.sort(key=lambda row: (-safe_float(row.get("proof_score")), row.get("family_id", "")))
    for rank, row in enumerate(merged, start=1):
        row["rank"] = rank
    return merged


def apply_kuramoto_holdout_expansion(
    champion_rankings: list[dict[str, Any]],
    holdout: dict[str, Any],
) -> list[dict[str, Any]]:
    summary = holdout.get("summary", {}) if isinstance(holdout.get("summary"), dict) else {}
    if summary.get("candidate") != "kuramoto_phase_coupling":
        return champion_rankings

    wins = safe_int(summary.get("wins_vs_kalman"))
    total = safe_int(summary.get("holdout_count"))
    mean_delta = safe_float(summary.get("mean_delta_vs_kalman"))
    passed = bool(
        holdout.get("schema") == "kuramoto_holdout_expansion_v2"
        and summary.get("protocol_grade_internal_champion")
        and summary.get("candidate_beats_all_registered_baselines_after_holm")
    )
    stage = (
        "direct_measured_all_baseline_internal_champion_not_field_validated"
        if passed
        else "direct_measured_eia_nonpromotion_result"
    )

    matched = False
    for row in champion_rankings:
        if row.get("family_id") != "kuramoto_phase_coupling":
            continue
        matched = True
        row["evidence_stage"] = stage
        row["proof_score"] = round(
            max(safe_float(row.get("proof_score")), 82.0)
            if passed
            else min(max(safe_float(row.get("proof_score")), 20.0), 35.0),
            3,
        )
        row["kuramoto_holdout_evidence"] = {
            "evidence_mode": summary.get("evidence_mode", ""),
            "development_selected_candidate": summary.get(
                "development_selected_candidate", ""
            ),
            "candidate_was_protocol_selected": bool(
                summary.get("candidate_was_protocol_selected")
            ),
            "holdout_count": total,
            "wins_vs_kalman": wins,
            "losses_or_ties_vs_kalman": summary.get("losses_or_ties_vs_kalman", 0),
            "win_rate_vs_kalman": summary.get("win_rate_vs_kalman", 0.0),
            "wilson_95_win_rate_lower": summary.get("wilson_95_win_rate_lower", 0.0),
            "one_sided_sign_test_p_value": summary.get("one_sided_sign_test_p_value", 1.0),
            "mean_delta_vs_kalman": mean_delta,
            "estimated_rows_replayed": summary.get("estimated_rows_replayed", 0),
            "numeric_samples_read": summary.get("numeric_samples_read", 0),
            "holdout_chain_sha256": summary.get("holdout_chain_sha256", ""),
            "passes_internal_20_holdout_gate": passed,
            "registered_baseline_count": summary.get(
                "registered_baseline_count", 0
            ),
            "registered_baseline_mean_win_count": summary.get(
                "registered_baseline_mean_win_count", 0
            ),
            "candidate_beats_all_registered_baselines_after_holm": bool(
                summary.get(
                    "candidate_beats_all_registered_baselines_after_holm"
                )
            ),
        }
        if passed:
            row["safe_claim"] = (
                "Kuramoto cleared the frozen direct measured source-specific "
                "baseline gate internally; independent replay is still required."
            )
        else:
            row["safe_claim"] = (
                "On the frozen measured EIA holdout, Kuramoto was not the "
                "development-selected candidate and did not beat the registered "
                f"baseline gauntlet; mean skill vs Kalman was {mean_delta}."
            )
        row["next_move"] = (
            "Preserve this negative result. Search only on development data, "
            "freeze one new wave candidate, then rerun the untouched EIA holdout."
        )
        break

    if not matched:
        champion_rankings.append(
            {
                "family_id": "kuramoto_phase_coupling",
                "label": "Kuramoto Phase Coupling",
                "lane": "wave_resonance_timing",
                "evidence_stage": stage,
                "proof_score": 20.0 if not passed else 82.0,
                "repeat_evidence": {},
                "source_conditioned_evidence": {},
                "kuramoto_holdout_evidence": {
                    "evidence_mode": summary.get("evidence_mode", ""),
                    "development_selected_candidate": summary.get(
                        "development_selected_candidate", ""
                    ),
                    "candidate_was_protocol_selected": bool(
                        summary.get("candidate_was_protocol_selected")
                    ),
                    "holdout_count": total,
                    "wins_vs_kalman": wins,
                    "losses_or_ties_vs_kalman": summary.get(
                        "losses_or_ties_vs_kalman", 0
                    ),
                    "win_rate_vs_kalman": summary.get(
                        "win_rate_vs_kalman", 0.0
                    ),
                    "mean_delta_vs_kalman": mean_delta,
                    "registered_baseline_count": summary.get(
                        "registered_baseline_count", 0
                    ),
                    "registered_baseline_mean_win_count": summary.get(
                        "registered_baseline_mean_win_count", 0
                    ),
                    "candidate_beats_all_registered_baselines_after_holm": bool(
                        summary.get(
                            "candidate_beats_all_registered_baselines_after_holm"
                        )
                    ),
                    "holdout_chain_sha256": summary.get(
                        "holdout_chain_sha256", ""
                    ),
                    "passes_internal_20_holdout_gate": passed,
                },
                "safe_claim": (
                    "On the frozen measured EIA holdout, Kuramoto was not the "
                    "development-selected candidate and did not beat any "
                    "registered source-specific baseline on mean skill."
                ),
                "next_move": (
                    "Preserve this negative result and search a new wave candidate "
                    "on development data only."
                ),
            }
        )

    champion_rankings.sort(key=lambda item: (-safe_float(item.get("proof_score")), item.get("family_id", "")))
    for rank, row in enumerate(champion_rankings, start=1):
        row["rank"] = rank
    return champion_rankings


def apply_current_cross_sector_evidence(
    champion_rankings: list[dict[str, Any]],
    cross_sector: dict[str, Any],
) -> list[dict[str, Any]]:
    if cross_sector.get("candidate", {}).get("id") != "kuramoto_phase_coupling":
        return champion_rankings

    gates = cross_sector.get("gates", {}) if isinstance(cross_sector.get("gates"), dict) else {}
    proven = safe_int(gates.get("sector_gain_proven_count"))
    sector_count = safe_int(gates.get("sector_count"))
    status = str(cross_sector.get("status") or "")
    for row in champion_rankings:
        if row.get("family_id") != "kuramoto_phase_coupling":
            continue
        row["evidence_stage"] = "negative_current_cross_sector_benchmark"
        row["proof_score"] = min(safe_float(row.get("proof_score")), 20.0)
        row["current_cross_sector_evidence"] = {
            "status": status,
            "sector_gain_proven_count": proven,
            "sector_count": sector_count,
            "evaluation_origin_count": safe_int(gates.get("total_evaluation_origin_count")),
            "cross_sector_efficiency_claim_allowed": bool(
                gates.get("cross_sector_efficiency_claim_allowed")
            ),
            "dollar_projection_from_forecast_error_allowed": bool(
                gates.get("dollar_projection_from_forecast_error_allowed")
            ),
            "evidence_chain_sha256": cross_sector.get("evidence_chain_sha256", ""),
        }
        row["safe_claim"] = (
            f"The current governed cross-sector benchmark found {proven}/{sector_count} proven Kuramoto sector gains. "
            "The direct measured EIA audit also failed the source-specific baseline gauntlet. "
            "Neither result supports performance marketing, cross-sector efficiency, field-validation, or dollar claims."
        )
        row["next_move"] = str(cross_sector.get("safest_next_action") or "")
        break

    champion_rankings.sort(key=lambda item: (-safe_float(item.get("proof_score")), item.get("family_id", "")))
    for rank, row in enumerate(champion_rankings, start=1):
        row["rank"] = rank
    return champion_rankings


def safe_claim(stage: str, evidence: dict[str, Any]) -> str:
    family = evidence.get("family_id", "candidate")
    lane = evidence.get("lane", "lane")
    if stage.startswith("robust_repeat"):
        return (
            f"{family} is a robust repeat-window benchmark candidate on {lane}; this supports paid technical "
            "evaluation scoping, not field validation or realized savings."
        )
    if stage.startswith("direct_measured_source_specific_nonpromotion"):
        return (
            f"{family} is a direct measured nonpromotion result on {lane}; it "
            "failed at least one source-specific baseline gate and is not a winner claim."
        )
    if stage.startswith("source_conditioned_synthetic_stress"):
        return (
            f"{family} is a conditioned-synthetic research lead on {lane}; it "
            "does not establish performance on the measured source."
        )
    if "negative" in stage or "nonpromotion" in stage:
        return f"{family} is current negative or nonpromotion evidence and should not be pitched as a winner."
    return f"{family} remains a research candidate until it wins frozen replays against named baselines."


def next_move(stage: str, evidence: dict[str, Any]) -> str:
    if stage.startswith("robust_repeat"):
        return "Package as a bounded appendix and ask for buyer-authorized holdout replay."
    if stage.startswith("direct_measured_source_specific_nonpromotion"):
        return "Search on development data only, freeze one candidate, then rerun the untouched source-native holdout."
    if stage.startswith("source_conditioned_synthetic_stress"):
        return "Build a direct measured adapter and register source-native baselines."
    if "negative" in stage:
        return "Do not pitch this as a winner; use it as negative evidence and test alternate branching families."
    return "Wire to an adapter or leave as registry-only."


def top_next_actions(payload: dict[str, Any]) -> list[str]:
    best = payload["champion_rankings"][0] if payload["champion_rankings"] else {}
    return [
        f"Lead with {best.get('family_id', 'the top candidate')} only in bounded benchmark language.",
        "Do not market a Kuramoto efficiency gain; preserve the current negative cross-sector result.",
        "Run a future model test only after an external owner locks the unseen window, incumbent baseline, native metric, and economic conversion.",
        "Move leaf-vein branching out of winner language until it beats minimum-spanning-tree on fresh source-conditioned routes.",
        "Attach the current proof-state JSON hash to grant and buyer packets so reviewers can reproduce the evidence boundary.",
    ]


def build_payload() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    ready = read_json(READY_REPLAY_JSON)
    manifest = read_json(SOURCE_MANIFEST_JSON)
    repeat = read_json(REPEAT_VALIDATION_JSON)
    uncertainty = read_json(UNCERTAINTY_JSON)
    kuramoto_holdout = read_json(KURAMOTO_HOLDOUT_JSON)
    kuramoto_cross_sector = read_json(KURAMOTO_CROSS_SECTOR_JSON)
    valuation = read_json(VALUATION_JSON)
    claim_map = read_json(CLAIM_MAP_JSON)
    field_money = read_json(FIELD_MONEY_JSON)

    families = family_index(registry)
    repeat_rows = repeat_candidates(repeat, uncertainty_index(uncertainty), families)
    ready_rows = ready_source_candidates(ready, families)
    champion_rankings = merge_candidates(repeat_rows, ready_rows, families)
    champion_rankings = apply_kuramoto_holdout_expansion(champion_rankings, kuramoto_holdout)
    champion_rankings = apply_current_cross_sector_evidence(champion_rankings, kuramoto_cross_sector)

    ready_summary = ready.get("summary", {}) if isinstance(ready.get("summary"), dict) else {}
    manifest_summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
    kuramoto_summary = kuramoto_holdout.get("summary", {}) if isinstance(kuramoto_holdout.get("summary"), dict) else {}
    cross_sector_gates = (
        kuramoto_cross_sector.get("gates", {})
        if isinstance(kuramoto_cross_sector.get("gates"), dict)
        else {}
    )
    valuation_state = valuation.get("valuation_state", {}) if isinstance(valuation.get("valuation_state"), dict) else {}
    claim_summary = claim_map.get("summary", {}) if isinstance(claim_map.get("summary"), dict) else {}
    field_summary = field_money.get("summary", {}) if isinstance(field_money.get("summary"), dict) else {}

    gates = {
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "paid_technical_evaluation_scoping_allowed": True,
        "all_registered_families_live_benchmarked": False,
        "natural_path_registry_target_met": registry_summary(registry)["natural_path_target_met"],
    }

    payload = {
        "schema": "current_luma_proof_state.v2",
        "generated_utc": now_utc(),
        "boundary": BOUNDARY,
        "registry": registry_summary(registry),
        "ready_source_replay": {
            "routes": ready_summary.get("routes_replayed", 0),
            "candidate_wins": ready_summary.get("candidate_win_count", 0),
            "candidate_losses_or_ties": ready_summary.get("candidate_loss_or_tie_count", 0),
            "direct_measured_replay_count": ready_summary.get(
                "direct_measured_replay_count", 0
            ),
            "source_conditioned_synthetic_stress_count": ready_summary.get(
                "source_conditioned_synthetic_stress_count", 0
            ),
            "source_conditioned_named_baseline_mean_win_count": ready_summary.get(
                "source_conditioned_named_baseline_mean_win_count", 0
            ),
            "direct_all_baseline_global_holm_positive_count": ready_summary.get(
                "direct_all_baseline_global_holm_positive_count", 0
            ),
            "legacy_ready_for_benchmark_rows_excluded": ready_summary.get(
                "legacy_ready_for_benchmark_rows_excluded", 0
            ),
            "numeric_fallback_profile_count": ready_summary.get(
                "numeric_fallback_profile_count", 0
            ),
            "estimated_rows_replayed": ready_summary.get("estimated_rows_replayed", 0),
            "numeric_samples_read": ready_summary.get("numeric_samples_read", 0),
            "replay_chain_sha256": ready_summary.get("replay_chain_sha256", ""),
        },
        "manifest": {
            "ready_for_benchmark_routes": manifest_summary.get("ready_for_benchmark_row_count", 0),
            "unique_source_count": manifest_summary.get("unique_source_count", 0),
            "unique_source_estimated_rows": manifest_summary.get("unique_source_estimated_rows", 0),
            "manifest_sha256": manifest_summary.get("manifest_sha256", ""),
        },
        "repeat_validation": repeat.get("summary", {}),
        "uncertainty": uncertainty.get("summary", {}),
        "kuramoto_holdout_expansion": {
            "holdout_count": kuramoto_summary.get("holdout_count", 0),
            "wins_vs_kalman": kuramoto_summary.get("wins_vs_kalman", 0),
            "losses_or_ties_vs_kalman": kuramoto_summary.get("losses_or_ties_vs_kalman", 0),
            "mean_delta_vs_kalman": kuramoto_summary.get("mean_delta_vs_kalman", 0.0),
            "estimated_rows_replayed": kuramoto_summary.get("estimated_rows_replayed", 0),
            "numeric_samples_read": kuramoto_summary.get("numeric_samples_read", 0),
            "passes_internal_20_holdout_gate": kuramoto_summary.get("passes_internal_20_holdout_gate", False),
            "evidence_mode": kuramoto_summary.get("evidence_mode", ""),
            "development_selected_candidate": kuramoto_summary.get(
                "development_selected_candidate", ""
            ),
            "candidate_was_protocol_selected": bool(
                kuramoto_summary.get("candidate_was_protocol_selected")
            ),
            "registered_baseline_count": kuramoto_summary.get(
                "registered_baseline_count", 0
            ),
            "registered_baseline_mean_win_count": kuramoto_summary.get(
                "registered_baseline_mean_win_count", 0
            ),
            "candidate_beats_all_registered_baselines_after_holm": bool(
                kuramoto_summary.get(
                    "candidate_beats_all_registered_baselines_after_holm"
                )
            ),
            "ready_for_buyer_authorized_field_replay_request": kuramoto_summary.get(
                "ready_for_buyer_authorized_field_replay_request", False
            ),
            "holdout_chain_sha256": kuramoto_summary.get("holdout_chain_sha256", ""),
            "historical_narrow_result_only": False,
            "legacy_source_conditioned_claim_superseded": True,
        },
        "kuramoto_cross_sector_benchmark": {
            "status": kuramoto_cross_sector.get("status"),
            "sector_gain_proven_count": safe_int(cross_sector_gates.get("sector_gain_proven_count")),
            "sector_count": safe_int(cross_sector_gates.get("sector_count")),
            "evaluation_origin_count": safe_int(cross_sector_gates.get("total_evaluation_origin_count")),
            "cross_sector_efficiency_claim_allowed": bool(
                cross_sector_gates.get("cross_sector_efficiency_claim_allowed")
            ),
            "dollar_projection_from_forecast_error_allowed": bool(
                cross_sector_gates.get("dollar_projection_from_forecast_error_allowed")
            ),
            "evidence_chain_sha256": kuramoto_cross_sector.get("evidence_chain_sha256", ""),
            "claim_boundary": kuramoto_cross_sector.get("claim_boundary", ""),
        },
        "valuation": {
            "strongest_current_claim": claim_summary.get("strongest_current_claim", ""),
            "safe_estimated_hourly_value_usd": claim_summary.get(
                "safe_estimated_hourly_value_usd", field_summary.get("safe_estimated_hourly_value_usd", 0)
            ),
            "safe_estimated_annual_value_usd": claim_summary.get(
                "safe_estimated_annual_value_usd", field_summary.get("safe_estimated_annual_value_usd", 0)
            ),
            "blocked_context_annual_value_usd": claim_summary.get(
                "blocked_context_annual_value_usd", field_summary.get("blocked_context_annual_value_usd", 0)
            ),
            "current_priceable_offer": valuation_state.get("current_priceable_offer", {}),
        },
        "proposal_target": valuation.get("recommended_first_proposal_target", {}),
        "champion_rankings": champion_rankings,
        "gates": gates,
        "next_actions": [],
        "inputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)),
            "ready_source_replay": str(READY_REPLAY_JSON.relative_to(ROOT)),
            "source_manifest": str(SOURCE_MANIFEST_JSON.relative_to(ROOT)),
            "repeat_validation": str(REPEAT_VALIDATION_JSON.relative_to(ROOT)),
            "uncertainty": str(UNCERTAINTY_JSON.relative_to(ROOT)),
            "kuramoto_holdout_expansion": str(KURAMOTO_HOLDOUT_JSON.relative_to(ROOT)),
            "kuramoto_cross_sector_benchmark": str(KURAMOTO_CROSS_SECTOR_JSON.relative_to(ROOT)),
            "valuation": str(VALUATION_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
    }
    payload["next_actions"] = top_next_actions(payload)
    payload["proof_state_sha256"] = stable_sha256(
        {
            "registry": payload["registry"],
            "ready_source_replay": payload["ready_source_replay"],
            "manifest": payload["manifest"],
            "repeat_validation": payload["repeat_validation"],
            "uncertainty": payload["uncertainty"],
            "kuramoto_holdout_expansion": payload["kuramoto_holdout_expansion"],
            "kuramoto_cross_sector_benchmark": payload["kuramoto_cross_sector_benchmark"],
            "valuation": payload["valuation"],
            "proposal_target": payload["proposal_target"],
            "champion_rankings": payload["champion_rankings"],
            "gates": payload["gates"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    registry = payload["registry"]
    ready = payload["ready_source_replay"]
    manifest = payload["manifest"]
    kuramoto = payload["kuramoto_holdout_expansion"]
    cross_sector = payload["kuramoto_cross_sector_benchmark"]
    valuation = payload["valuation"]
    gates = payload["gates"]
    lines = [
        "# Current Luma Proof State",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Hard Numbers",
        "",
        f"- Registered geometry families: `{registry['family_count']}`",
        f"- Natural-path families: `{registry['natural_path_family_count']}`",
        f"- Benchmark-specified families: `{registry['benchmark_specified_family_count']}`",
        f"- Ready-for-benchmark manifest routes: `{manifest['ready_for_benchmark_routes']}`",
        f"- Unique source files in manifest: `{manifest['unique_source_count']}`",
        f"- Manifest estimated rows: `{manifest['unique_source_estimated_rows']}`",
        f"- Compatibility-gated adapters run: `{ready['routes']}`",
        f"- Direct measured replays: `{ready['direct_measured_replay_count']}`",
        f"- Source-conditioned synthetic stress cards: `{ready['source_conditioned_synthetic_stress_count']}`",
        f"- Direct all-baseline globally corrected promotions: `{ready['direct_all_baseline_global_holm_positive_count']}`",
        f"- Conditioned-synthetic named-baseline mean wins: `{ready['source_conditioned_named_baseline_mean_win_count']}`",
        f"- Legacy generic ready rows excluded: `{ready['legacy_ready_for_benchmark_rows_excluded']}`",
        f"- Numeric fallback profiles: `{ready['numeric_fallback_profile_count']}`",
        f"- Current replay estimated rows: `{ready['estimated_rows_replayed']}`",
        f"- Numeric samples read: `{ready['numeric_samples_read']}`",
        f"- Kuramoto measured EIA holdout: `{kuramoto['wins_vs_kalman']}` / `{kuramoto['holdout_count']}` paired-day wins vs Kalman",
        f"- Kuramoto holdout mean delta vs Kalman: `{kuramoto['mean_delta_vs_kalman']}`",
        f"- Kuramoto selected by frozen development protocol: `{str(kuramoto['candidate_was_protocol_selected']).lower()}`",
        f"- Kuramoto source-specific all-baseline gate passed: `{str(kuramoto['candidate_beats_all_registered_baselines_after_holm']).lower()}`",
        (
            f"- Current Kuramoto cross-sector result: `{cross_sector['status']}` "
            f"({cross_sector['sector_gain_proven_count']}/{cross_sector['sector_count']} proven sector gains)"
        ),
        "",
        "## Champion Ranking",
        "",
        "| Rank | Family | Lane | Stage | Score | Main Claim |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in payload["champion_rankings"][:8]:
        lines.append(
            f"| {row['rank']} | `{row['family_id']}` | `{row['lane']}` | `{row['evidence_stage']}` | "
            f"{row['proof_score']} | {row['safe_claim']} |"
        )
    lines.extend(
        [
            "",
            "## Money State",
            "",
            f"- Strongest current commercial claim: `{valuation['strongest_current_claim']}`",
            f"- Claimable estimated hourly value signal: `{money(valuation['safe_estimated_hourly_value_usd'])}`",
            f"- Claimable estimated annual value signal: `{money(valuation['safe_estimated_annual_value_usd'])}`",
            "- No current dollar projection clears the buyer-approved gate.",
            "",
            "## First Proposal Target",
            "",
        ]
    )
    target = payload["proposal_target"]
    if target:
        lines.extend(
            [
                f"- Target: {target.get('target_name', '')}",
                f"- Buyer role: {target.get('buyer_role', '')}",
                f"- Ask: {target.get('proposal_ask', '')}",
                f"- Acceptance metric: {target.get('acceptance_metric', '')}",
            ]
        )
    else:
        lines.append("- No proposal target generated yet.")
    lines.extend(["", "## Claim Gates", ""])
    for key, value in gates.items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(["", "## Next Actions", ""])
    for item in payload["next_actions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Inputs",
            "",
        ]
    )
    for label, path in payload["inputs"].items():
        lines.append(f"- {label}: `{path}`")
    lines.append(f"- Proof-state SHA-256: `{payload['proof_state_sha256']}`")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Proof state SHA256: {payload['proof_state_sha256']}")


if __name__ == "__main__":
    main()
