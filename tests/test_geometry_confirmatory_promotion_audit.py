from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GEOMETRY_CONFIRMATORY_PROMOTION_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("geometry_confirmatory_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fixture_rows(candidate_scores: dict[str, float], baseline_score: float = 0.7):
    rows = []
    for condition, candidate_score in candidate_scores.items():
        for seed in range(20):
            rows.append(
                {
                    "condition": condition,
                    "seed": seed,
                    "strategy": "candidate",
                    "score": candidate_score,
                    "guard": 0.8,
                }
            )
            rows.append(
                {
                    "condition": condition,
                    "seed": seed,
                    "strategy": "baseline",
                    "score": baseline_score,
                    "guard": 0.8,
                }
            )
    return rows


def test_development_preselected_family_can_pass_confirmatory_gate():
    module = load_module()
    result = module.build_family_comparison(
        fixture_rows({"a": 0.8, "b": 0.82}),
        family_id="candidate",
        baseline_id="baseline",
        development_selected_family="candidate",
        metric_rules=(module.MetricRule("guard", "higher"),),
        condition_score_noninferiority_margin=0.01,
    )

    assert result["confirmatory_pass"] is True
    assert result["decision"] == "INTERNAL_CONFIRMATORY_PASS_NOT_FIELD_VALIDATED"
    assert result["paired_score_interval"]["ci95"][0] > 0


def test_condition_regression_vetoes_positive_average():
    module = load_module()
    result = module.build_family_comparison(
        fixture_rows({"good": 1.0, "bad": 0.55}),
        family_id="candidate",
        baseline_id="baseline",
        development_selected_family="candidate",
        metric_rules=(module.MetricRule("guard", "higher"),),
        condition_score_noninferiority_margin=0.01,
    )

    assert result["paired_score_interval"]["observed_mean_delta"] > 0
    assert result["confirmatory_pass"] is False
    assert result["checks"]["all_condition_score_noninferiority"] is False
    assert result["decision"] == "NOT_PROMOTED_CONFIRMATORY_GATE_FAILED"


def test_non_preselected_family_is_descriptive_only():
    module = load_module()
    result = module.build_family_comparison(
        fixture_rows({"a": 0.85, "b": 0.86}),
        family_id="candidate",
        baseline_id="baseline",
        development_selected_family="different_candidate",
        metric_rules=(module.MetricRule("guard", "higher"),),
        condition_score_noninferiority_margin=0.01,
    )

    assert result["confirmatory_pass"] is False
    assert result["decision"] == "DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED"
    assert result["checks"]["development_preselected"] is False


def test_lumengrade_scale_never_claims_external_certification():
    module = load_module()

    assert set(module.LUMENGRADE_SCALE) == {"LG0", "LG1", "LG2", "LG3", "LG4", "LG5"}
    assert "not certification" in module.LUMENGRADE_SCALE["LG5"]
    assert "not faa" in module.EVIDENCE_BOUNDARY.lower()
