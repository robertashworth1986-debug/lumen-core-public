from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LUMENCORE_TWIN_JSON_INVITATION.py"


def load_module():
    spec = importlib.util.spec_from_file_location("lumencore_twin_json_invitation", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_twin_json_invitation_matches_measured_evidence_and_boundaries():
    module = load_module()
    payload = module.build_payload()
    score = payload["machine_twin"]["measured_scorecard"]

    assert payload["schema"] == "lumencore_twin_json_invitation_v1"
    assert payload["machine_twin"]["highest_supported_maturity_level"] == 3
    assert payload["machine_twin"]["level_5_attained"] is False
    assert score["proof_vault_verified_artifacts"] == score["proof_vault_selected_artifacts"]
    assert score["locked_candidate_wins"] + score["locked_candidate_non_wins"] == score[
        "locked_baseline_comparisons"
    ]
    assert score["locked_win_rate_pct"] == round(
        100.0 * score["locked_candidate_wins"] / score["locked_baseline_comparisons"], 2
    )
    spoken = payload["spoken_twin"]["read_aloud_text"]
    assert f"{score['locked_candidate_wins']:,} wins" in spoken
    assert f"{score['locked_candidate_non_wins']:,} non-wins" in spoken
    assert f"{score['locked_estimated_rows_replayed']:,} estimated replay rows" in spoken
    assert score["prospective_prediction_count"] == 0
    assert score["prospective_settlement_count"] == 0
    assert len(payload["source_chain_sha256"]) == 64
    assert len(payload["invitation_sha256"]) == 64


def test_hard_problem_answers_preserve_negative_results_and_stage():
    module = load_module()
    payload = module.build_payload()
    cards = {row["problem_id"]: row for row in payload["hard_problem_cards"]}

    sync = cards["nonlinear_synchronization"]["measured_answer"]
    assert sync["answer"].startswith("No promotion")
    assert sync["kuramoto_mean_seasonal_mase_7"] > sync["best_baseline_mean_seasonal_mase_7"]

    opf = cards["nonconvex_ac_optimal_power_flow"]["measured_answer"]
    assert opf["networks_converged"] == opf["networks_tested"] == 4
    assert opf["candidate_execution_started"] is False

    routing = cards["guarded_hybrid_model_routing"]["measured_answer"]
    assert routing["xgboost_residual_mean_seasonal_mase_7"] < routing[
        "direct_lightgbm_mean_seasonal_mase_7"
    ]
    assert routing["protocol_grade_internal_champion"] is False
    assert routing["prospective_predictions"] == 0


def test_read_aloud_twin_is_calm_and_does_not_claim_unsolved_math():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    dumped = json.dumps(payload).lower()

    assert "My invitation is simple" in rendered
    assert "Level 3" in rendered
    assert "Level 5 attained: `false`" in rendered
    assert "solved open mathematical problem" in dumped
    assert "guaranteed funding" in dumped
    assert "unbeatable" not in payload["spoken_twin"]["read_aloud_text"].lower()
