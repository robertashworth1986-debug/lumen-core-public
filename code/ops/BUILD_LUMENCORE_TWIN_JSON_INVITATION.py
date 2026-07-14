from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
QUANT_JSON = ROOT / "out" / "ops" / "quant_hub_reviewer_context_latest.json"
WAVE_JSON = ROOT / "out" / "eia_grid_wave_champion" / "eia_grid_wave_champion_benchmark_latest.json"
RESIDUAL_JSON = ROOT / "out" / "eia_grid_residual_moe" / "eia_grid_residual_moe_benchmark_latest.json"
PROSPECTIVE_JSON = ROOT / "out" / "eia_grid_prospective_hybrid_router" / "prospective_status_latest.json"
ACOPF_JSON = ROOT / "out" / "ops" / "ieee_acopf_baseline_smoke_latest.json"

OUT_JSON = ROOT / "out" / "ops" / "lumencore_twin_json_invitation_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "lumencore_twin_json_invitation.json"
OUT_MD = ROOT / "docs" / "LUMENCORE_TWIN_JSON_INVITATION_2026-07-13.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required evidence artifact is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def strategy_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["strategy"]): row for row in payload.get("holdout_leaderboard", [])}


def proof_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row["proof_id"]): row for row in payload.get("proof_cards", [])}


def build_payload() -> dict[str, Any]:
    quant = read_json(QUANT_JSON)
    wave = read_json(WAVE_JSON)
    residual = read_json(RESIDUAL_JSON)
    prospective = read_json(PROSPECTIVE_JSON)
    acopf = read_json(ACOPF_JSON)

    proofs = proof_map(quant)
    locked = proofs["locked_source_baseline_replay"]["facts"]
    sources = proofs["live_source_measurement"]["facts"]
    vault = proofs["prooflock_prior_vault"]["facts"]
    estate = proofs["estate_inventory"]["facts"]
    wave_by_strategy = strategy_map(wave)
    residual_by_strategy = strategy_map(residual)

    comparisons = int(locked["baseline_comparison_count"])
    wins = int(locked["candidate_win_count"])
    non_wins = int(locked["candidate_loss_or_tie_count"])
    if wins + non_wins != comparisons:
        raise ValueError("Locked replay win/non-win accounting does not equal total comparisons")

    source_paths = [QUANT_JSON, WAVE_JSON, RESIDUAL_JSON, PROSPECTIVE_JSON, ACOPF_JSON]
    source_artifacts = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in source_paths
    ]

    spoken_invitation = (
        "Thank you for taking a serious look at LumenCore. I am Robert Ashworth. I have built an evidence "
        "operating system for testing candidate geometries, forecasting models, and routing policies against named "
        f"baselines. The research estate currently indexes {int(estate['managed_file_count']):,} managed files, and the selected external proof vault "
        f"preserves {int(vault['verified_count']):,} of {int(vault['artifact_count']):,} artifacts by verified hash. "
        f"On the current locked sweep, {int(locked['adapter_backed_routes']):,} adapter-backed routes "
        f"produced {comparisons:,} baseline comparisons: {wins:,} wins and {non_wins:,} non-wins across "
        f"{int(locked['estimated_rows_replayed']):,} estimated replay rows. "
        "I preserve both sides because a negative result is part of the scientific asset.\n\n"
        "The platform is presently Level 3: reproducible, source-conditioned internal evidence. It is not yet Level 5, "
        "field validated, or authorized for live execution. In the EIA lane, Kuramoto lost the official holdout. An "
        "XGBoost residual model led the aggregate table but failed a declared promotion guardrail. The prospective hybrid "
        "router remains frozen at zero predictions until eligible future targets exist.\n\n"
        "My invitation is simple: bring a real dataset, an accepted loss function, and an independent reviewer. We will "
        "freeze the protocol, run the comparison, preserve every win and non-win, and let the evidence decide whether a "
        "pilot is justified."
    )

    payload: dict[str, Any] = {
        "schema": "lumencore_twin_json_invitation_v1",
        "generated_utc": now_utc(),
        "purpose": "Keep a calm spoken invitation and its machine-verifiable evidence twin synchronized.",
        "spoken_twin": {
            "title": "An invitation into the LumenCore evidence estate",
            "read_aloud_text": spoken_invitation,
            "tone": ["calm", "measured", "scientifically candid", "invitation rather than hype"],
        },
        "machine_twin": {
            "assessment": "strong_internal_research_and_custody_external_validation_pending",
            "highest_supported_maturity_level": quant["current_evidence_posture"][
                "highest_repository_wide_supported_level"
            ],
            "level_5_attained": quant["current_evidence_posture"]["level_5_attained"],
            "measured_scorecard": {
                "estate_managed_file_count": estate["managed_file_count"],
                "estate_managed_total_bytes": estate["managed_total_bytes"],
                "proof_vault_verified_artifacts": vault["verified_count"],
                "proof_vault_selected_artifacts": vault["artifact_count"],
                "live_sources_measured": sources["measured_sources"],
                "live_sources_enabled": sources["enabled_sources"],
                "live_source_coverage_pct": sources["coverage_pct"],
                "locked_adapter_backed_routes": locked["adapter_backed_routes"],
                "locked_baseline_comparisons": comparisons,
                "locked_candidate_wins": wins,
                "locked_candidate_non_wins": non_wins,
                "locked_win_rate_pct": round(100.0 * wins / comparisons, 2),
                "locked_estimated_rows_replayed": locked["estimated_rows_replayed"],
                "locked_numeric_samples_read": locked["numeric_samples_read"],
                "prospective_prediction_count": prospective["prediction_count"],
                "prospective_settlement_count": prospective["settlement_count"],
            },
            "readiness_dimensions": {
                "custody_and_hashing": "verified",
                "source_conditioned_internal_replay": "supported_level_3",
                "prospective_validation": "waiting_for_eligible_forecasts",
                "independent_external_validation": "not_attained",
                "field_validated_savings": "not_attained",
                "live_execution_authority": "not_allowed",
            },
        },
        "hard_problem_cards": [
            {
                "problem_id": "nonlinear_synchronization",
                "name": "Kuramoto coupled-oscillator synchronization",
                "equation": "d(theta_i)/dt = omega_i + (K/N) * sum_j sin(theta_j - theta_i)",
                "operational_question": "Does phase-coupling structure generalize to held-out grid-demand forecasting?",
                "measured_answer": {
                    "answer": "No promotion on the official EIA holdout.",
                    "kuramoto_holdout_rank": wave_by_strategy["kuramoto_phase_coupling"]["rank"],
                    "kuramoto_mean_seasonal_mase_7": wave_by_strategy["kuramoto_phase_coupling"][
                        "mean_seasonal_mase_7"
                    ],
                    "best_baseline": "autoregressive_ridge_p14",
                    "best_baseline_mean_seasonal_mase_7": wave_by_strategy["autoregressive_ridge_p14"][
                        "mean_seasonal_mase_7"
                    ],
                },
                "scientific_value": "The negative result blocks an attractive but unsupported generalization.",
            },
            {
                "problem_id": "nonconvex_ac_optimal_power_flow",
                "name": "AC optimal power flow",
                "equation": "min sum_g C_g(P_g), subject to nonlinear AC power balance and voltage, generator, and branch limits",
                "operational_question": "Can the accepted nonlinear baseline execute reproducibly before a routing candidate is tested?",
                "measured_answer": {
                    "answer": "Yes for the four smoke-test fixtures; no candidate superiority claim exists.",
                    "networks_converged": acopf["summary"]["converged_count"],
                    "networks_tested": acopf["summary"]["network_count"],
                    "candidate_execution_started": acopf["summary"]["candidate_execution_started"],
                    "fixtures": [
                        {
                            "network": row["network"],
                            "reported_objective": row.get("reported_objective"),
                            "converged": row["converged"],
                        }
                        for row in acopf["results"]
                    ],
                },
                "scientific_value": "The reference engine is ready for a frozen, objective-equivalent routing experiment.",
            },
            {
                "problem_id": "guarded_hybrid_model_routing",
                "name": "Frozen hybrid model routing under nonstationarity",
                "equation": "m_t = pi(x_t; D_dev); y_hat_t = f_(m_t)(x_t); freeze pi before observing y_t",
                "operational_question": "Can development-selected specialists improve forecast error without violating authority guardrails?",
                "measured_answer": {
                    "answer": "XGBoost residual led the aggregate holdout but failed the full promotion gate; prospective proof has not begun.",
                    "xgboost_residual_mean_seasonal_mase_7": residual_by_strategy["xgboost_residual"][
                        "mean_seasonal_mase_7"
                    ],
                    "direct_lightgbm_mean_seasonal_mase_7": residual_by_strategy["direct_lightgbm_stack"][
                        "mean_seasonal_mase_7"
                    ],
                    "direct_xgboost_mean_seasonal_mase_7": residual_by_strategy["direct_xgboost_stack"][
                        "mean_seasonal_mase_7"
                    ],
                    "protocol_grade_internal_champion": residual["promotion_gate"][
                        "protocol_grade_internal_champion"
                    ],
                    "prospective_predictions": prospective["prediction_count"],
                    "prospective_settlements": prospective["settlement_count"],
                },
                "scientific_value": "The router is frozen before future outcomes, preventing retrospective route selection from becoming a claim.",
            },
        ],
        "elite_conversation_openers": [
            "Which independently held dataset and owner-defined loss function would make this result decision-relevant to you?",
            "What preregistered failure guardrail would make you reject the candidate even if the aggregate score improves?",
            "What external rerun or limited pilot would you accept as the bridge from Level 3 internal evidence to Level 4 or Level 5 evidence?",
        ],
        "twin_alignment": [
            {"spoken_claim": f"{int(estate['managed_file_count']):,} managed files", "json_path": "machine_twin.measured_scorecard.estate_managed_file_count"},
            {"spoken_claim": f"{int(vault['verified_count']):,} of {int(vault['artifact_count']):,} artifacts", "json_path": "machine_twin.measured_scorecard.proof_vault_verified_artifacts"},
            {"spoken_claim": f"{comparisons:,} comparisons", "json_path": "machine_twin.measured_scorecard.locked_baseline_comparisons"},
            {"spoken_claim": f"{wins:,} wins and {non_wins:,} non-wins", "json_path": "machine_twin.measured_scorecard.locked_candidate_wins"},
            {"spoken_claim": "Level 3, not Level 5", "json_path": "machine_twin.highest_supported_maturity_level"},
            {"spoken_claim": "zero prospective predictions", "json_path": "machine_twin.measured_scorecard.prospective_prediction_count"},
        ],
        "claim_boundary": (
            "This invitation describes indexed assets, internal replay, baseline execution, and frozen prospective protocols. "
            "It does not claim a solved open mathematical problem, patent validity, external validation, field savings, "
            "production readiness, live trading edge, government approval, or guaranteed funding."
        ),
        "source_artifacts": source_artifacts,
    }
    payload["source_chain_sha256"] = stable_sha256(source_artifacts)
    payload["invitation_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    score = payload["machine_twin"]["measured_scorecard"]
    lines = [
        "# LumenCore Twin-JSON Invitation",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Read This Aloud",
        "",
        payload["spoken_twin"]["read_aloud_text"],
        "",
        "## Measured State",
        "",
        f"- Supported maturity: `Level {payload['machine_twin']['highest_supported_maturity_level']}`",
        f"- Level 5 attained: `{str(payload['machine_twin']['level_5_attained']).lower()}`",
        f"- Proof-vault custody: `{score['proof_vault_verified_artifacts']}/{score['proof_vault_selected_artifacts']}`",
        f"- Live-source coverage: `{score['live_sources_measured']}/{score['live_sources_enabled']}` (`{score['live_source_coverage_pct']}%`)",
        f"- Locked baseline comparisons: `{score['locked_baseline_comparisons']}`",
        f"- Wins/non-wins: `{score['locked_candidate_wins']}/{score['locked_candidate_non_wins']}` (`{score['locked_win_rate_pct']}%` wins)",
        f"- Prospective predictions/settlements: `{score['prospective_prediction_count']}/{score['prospective_settlement_count']}`",
        "",
        "## Three Hard Problems",
        "",
    ]
    for index, card in enumerate(payload["hard_problem_cards"], start=1):
        lines.extend(
            [
                f"### {index}. {card['name']}",
                "",
                f"Equation: `{card['equation']}`",
                "",
                f"Question: {card['operational_question']}",
                "",
                f"Measured answer: {card['measured_answer']['answer']}",
                "",
                f"Why it matters: {card['scientific_value']}",
                "",
            ]
        )
    lines.extend(["## Conversation Openers", ""])
    for question in payload["elite_conversation_openers"]:
        lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            f"Invitation SHA-256: `{payload['invitation_sha256']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"output": str(OUT_JSON), "sha256": payload["invitation_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
