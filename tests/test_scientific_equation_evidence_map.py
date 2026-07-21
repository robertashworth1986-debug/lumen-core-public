from __future__ import annotations

import copy
import importlib.util
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = ROOT / "code" / "ops" / "BUILD_SCIENTIFIC_EQUATION_EVIDENCE_MAP.py"
REGISTRY_PATH = ROOT / "config" / "scientific_equation_registry_v1.json"


def load_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_frequency_equations_match_registered_semantics() -> None:
    module = load_path(ROOT / "code" / "frequency_cluster_truth_gauntlet.py", "frequency_equations")
    days = np.asarray([0.0, 1.0])
    design = module.harmonic_design(days, [4.0])
    assert np.allclose(design[0], [1.0, 0.0, 1.0])
    assert np.allclose(design[1], [1.0, 1.0, 0.0], atol=1e-12)

    train_days = np.arange(12, dtype=float)
    target = 5.0 + np.sin(2.0 * np.pi * train_days / 4.0)
    predicted = module.fit_harmonic_predict(train_days, target, train_days, [4.0])
    assert np.allclose(predicted, target, atol=1e-10)
    assert module.partial_r2(train_days, target, 4.0) > 0.999999

    ewma = module.ewma_predictions(np.asarray([0.0, 10.0]), np.asarray([20.0, 30.0]), 1.0)
    assert np.allclose(ewma, [10.0, 15.0])
    blocks = list(module.moving_block_indices(9, 3, 2, np.random.default_rng(7)))
    assert len(blocks) == 2 and all(len(row) == 9 for row in blocks)
    assert all(np.all((row >= 0) & (row < 9)) for row in blocks)
    assert module.holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])


def test_daily_eia_equations_match_registered_semantics() -> None:
    module = load_path(ROOT / "code" / "eia_grid_residual_moe_benchmark.py", "daily_eia_equations")
    center, scale = module.stable_scale(np.asarray([1.0, 2.0, 3.0]))
    assert center == 2.0
    assert scale == pytest.approx(1.4826)
    assert module.seasonal_mase_scale(list(range(1, 15)), season=7) == pytest.approx(7.0)
    forecast = module.forecast_autoregressive_ridge([float(i) for i in range(60)], lag=7, ridge=1.0)
    assert math.isfinite(forecast)
    metric = module.metric_row(
        {
            "split": "holdout",
            "respondent": "TEST",
            "respondent_name": "Test",
            "target_date": "2026-01-01",
            "calendar_month": "2026-01",
            "actual_mwh": 110.0,
            "last_mwh": 100.0,
            "seasonal_scale_mwh": 5.0,
        },
        "candidate",
        "residual_candidate",
        105.0,
        False,
    )
    assert metric["seasonal_mase_7"] == 1.0
    assert metric["directional_accuracy"] == 1.0
    assert module.exact_two_sided_sign_test([1.0, 2.0, -1.0]) == 1.0


def test_hourly_eia_equations_and_chain_match_registered_semantics(tmp_path: Path) -> None:
    module = load_path(ROOT / "code" / "eia_grid_prospective_hourly_router.py", "hourly_eia_equations")
    target = 500
    actual = {target - 24: 10.0, target - 24 - 168: 4.0}
    assert module.target_scale(actual, target) == 6.0

    existing_test = load_path(ROOT / "tests" / "test_eia_grid_prospective_hourly_router.py", "hourly_test_helpers")
    panel, protocol = existing_test.synthetic_panel(module)
    series = module.series_by_authority(panel, protocol)
    row = module.build_feature_row(series, protocol, "ERCO", "2026-07-15T14", require_actual=False)
    assert "actual_mwh" not in row and len(row["features"]) == 27

    chain = tmp_path / "chain.jsonl"
    first = module.append_chain_record(chain, {"value": 1}, module.ZERO_HASH)
    module.append_chain_record(chain, {"value": 2}, first["record_sha256"])
    records, terminal = module.load_chain(chain)
    assert [record["value"] for record in records] == [1, 2]
    assert terminal == records[-1]["record_sha256"]


def test_dice_equations_match_registered_semantics() -> None:
    module = load_path(ROOT / "code" / "dice_constraint_contract_benchmark.py", "dice_equations")
    assert module._strategy_entropy({1: 5}) == 0.0
    assert module._strategy_entropy({index: 1 for index in range(8)}) == pytest.approx(1.0)
    result = SimpleNamespace(
        safe_completion_rate=0.8,
        constraint_violation_rate=0.1,
        false_rejection_rate=0.05,
        strategy_entropy=0.5,
        messages_per_safe_completion=20.0,
    )
    assert module._objective(result) == pytest.approx(0.70)


def test_nv065_expected_contribution_is_bounded_operational_heuristic() -> None:
    module = load_path(ROOT / "code" / "nv065_sensor_tasking_benchmark.py", "nv065_equation")
    sensor = module.Sensor("TEST", 2, 0.25, 1.0, {"air": 0.8})
    spec = module.TrackSpec("T1", 0, "air", 1, 0.3, 0.2, 1.4)
    state = module.TrackState(spec, hostility=1, covariance=1.4)
    condition = module.Condition("test", 1, 0.0, 0.0)
    params = module.PolicyParams("test", 0.03, 1.0, 0.5, 0.6, 1.0)
    score = module.expected_contribution(
        sensor=sensor,
        state=state,
        condition=condition,
        policy="adaptive_sensor_manager",
        params=params,
        timestamp=0,
    )
    assert math.isfinite(score) and score >= 0.0


def test_missionweave_equations_match_registered_semantics() -> None:
    module = load_path(ROOT / "code" / "missionweave_benchmark.py", "missionweave_equations")
    worker = module.Worker("W", "intake", {"intake": 1.0})
    case = module.CaseSpec("C", 0, "a", 3, 20, (2.0, 2.0, 2.0))
    state = module.CaseState(case)
    weights = module.PolicyWeights("test", 2.0, 3.0, 1.0, 1.0, 1.0)
    priority = module._priority(
        policy="missionweave",
        worker=worker,
        state=state,
        timestamp=10,
        weights=weights,
        stage_counts={"intake": 2, "analysis_a": 0, "analysis_b": 0, "review": 0},
    )
    assert len(priority) == 5 and all(math.isfinite(value) for value in priority)
    assert module._gini([1.0, 1.0]) == pytest.approx(0.0)
    assert module._gini([0.0, 1.0]) == pytest.approx(0.5)


def test_geometry_analogue_and_graph_implementations_are_bounded() -> None:
    wave = load_path(ROOT / "code" / "geometry_wave_resonance_timing_benchmark.py", "wave_analogue")
    wave_plan = wave.strategy_kuramoto_phase_coupling(
        wave.generate_scenario(7, wave.CONDITIONS[0], split="validation")
    )
    assert 0.0 <= wave_plan.noise_rejection <= 1.0
    assert 0.0 <= wave_plan.stability_margin <= 1.0

    curve = load_path(ROOT / "code" / "geometry_optimal_curve_transport_benchmark.py", "curve_analogue")
    curve_plan = curve.strategy_brachistochrone_descent(
        curve.generate_scenario(7, curve.CONDITIONS[0], split="validation")
    )
    assert curve_plan.travel_time > 0.0
    assert 0.0 <= curve_plan.constraint_violation_rate <= 1.0

    thermal = load_path(ROOT / "code" / "geometry_thermal_ventilation_benchmark.py", "thermal_analogue")
    thermal_plan = thermal.strategy_thermal_plume_convection(
        thermal.generate_scenario(7, thermal.CONDITIONS[0], split="validation")
    )
    assert thermal_plan.cooling and all(value >= 0.0 for value in thermal_plan.cooling.values())

    branching = load_path(ROOT / "code" / "geometry_branching_transport_benchmark.py", "branching_algorithm")
    scenario = branching.generate_scenario(7, branching.CONDITIONS[0], split="validation")
    goal = next(iter(scenario.sinks))
    path = branching.dijkstra_path(scenario, scenario.source, goal)
    assert path and path[0] == scenario.source and path[-1] == goal


def test_universal_harmonic_score_is_exploratory_and_bounded() -> None:
    module = load_path(ROOT / "code" / "universal_harmonic_edge_core.py", "universal_harmonic")
    bonus = module.phi_resonance_bonus(module.PHI * 10.0)
    assert bonus == pytest.approx(10.0)
    result = module.score_signal(
        edge_pct=1.0,
        best_price=2.1,
        ref_price=2.0,
        worst_price=1.9,
        n_sources=3,
        is_soft_source=False,
        repeat_count=2,
        domain="crypto",
    )
    assert 0.0 <= result["hybrid_harmonic_score"] <= 100.0


def test_registry_builds_fail_closed_public_map() -> None:
    builder = load_path(BUILDER_PATH, "equation_map_builder")
    payload = builder.build_payload(REGISTRY_PATH)
    summary = payload["summary"]
    assert payload["schema"] == "lumencore_scientific_equation_evidence_map_v1"
    assert summary["entry_count"] >= 20
    assert summary["independently_reproduced_entry_count"] == 0
    assert summary["field_or_acceptance_validated_entry_count"] == 0
    assert summary["patentability_determined"] is False
    assert summary["external_validation_claim_allowed"] is False
    assert payload["file_hash_audit"]["summary"]["all_current"] is True
    assert payload["file_hash_audit"]["summary"]["drift_count"] == 0
    assert len(payload["terminal_chain_sha256"]) == 64


def test_registry_hash_audit_is_deterministic_and_non_mutating() -> None:
    builder = load_path(BUILDER_PATH, "equation_hash_audit_builder")
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    original = copy.deepcopy(registry)

    first = builder.build_file_hash_audit(registry)
    second = builder.build_file_hash_audit(registry)

    assert first == second
    assert registry == original
    assert first["summary"]["all_current"] is True
    assert first["summary"]["current_count"] == len(registry["files"])
    assert first["summary"]["drift_count"] == 0
    assert len(first["audit_sha256"]) == 64


def test_registry_hash_audit_reports_drift_without_mutation() -> None:
    builder = load_path(BUILDER_PATH, "equation_hash_drift_builder")
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    first_path = next(iter(registry["files"]))
    registry["files"][first_path]["sha256"] = "0" * 64
    original = copy.deepcopy(registry)

    audit = builder.build_file_hash_audit(registry)

    assert registry == original
    assert audit["summary"]["all_current"] is False
    assert audit["summary"]["drift_count"] == 1
    drift = [record for record in audit["records"] if record["status"] == "DRIFT"]
    assert [record["path"] for record in drift] == [first_path]
    assert drift[0]["expected_sha256"] == "0" * 64
    assert len(drift[0]["observed_sha256"]) == 64


def test_registry_rejects_hash_drift_claim_inflation_and_analogue_promotion() -> None:
    builder = load_path(BUILDER_PATH, "equation_map_mutation_builder")
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

    hash_drift = copy.deepcopy(registry)
    first_path = next(iter(hash_drift["files"]))
    hash_drift["files"][first_path]["sha256"] = "0" * 64
    with pytest.raises(builder.RegistryValidationError, match="SHA-256 mismatch"):
        builder.validate_registry(hash_drift)

    inflated = copy.deepcopy(registry)
    inflated["entries"][0]["claim_level"] = "C4_FIELD_OR_ACCEPTANCE"
    with pytest.raises(builder.RegistryValidationError, match="claim level exceeds"):
        builder.validate_registry(inflated, verify_hashes=False)

    promoted = copy.deepcopy(registry)
    analogue = next(row for row in promoted["entries"] if row["equation_id"] == "GEO-WAVE-001")
    analogue["implementation_class"] = "EXACT_STANDARD_METHOD"
    with pytest.raises(builder.RegistryValidationError, match="must be classified"):
        builder.validate_registry(promoted, verify_hashes=False)


def test_markdown_states_patent_and_external_validation_boundaries() -> None:
    builder = load_path(BUILDER_PATH, "equation_map_markdown_builder")
    rendered = builder.render_markdown(builder.build_payload(REGISTRY_PATH))
    assert "Scientific Equation Evidence Map" in rendered
    assert "Patentability determined: `false`" in rendered
    assert "No entry in this release reaches E3" in rendered
    assert "not a numerical solution of the governing equation" in rendered
