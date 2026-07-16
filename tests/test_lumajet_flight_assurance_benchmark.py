from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "lumajet_flight_assurance_benchmark.py"
PROTOCOL = ROOT / "config" / "lumajet_flight_assurance_protocol_v1.json"
PROTOCOL_V2 = ROOT / "config" / "lumajet_flight_assurance_protocol_v2.json"


def load_module():
    spec = importlib.util.spec_from_file_location("lumajet_flight_assurance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_protocol_blocks_operational_claims_and_bounds_spectral_stress():
    module = load_module()
    protocol = load_protocol()
    receipt = module.validate_protocol(protocol)

    assert receipt["valid"] is True
    assert receipt["all_components_below_guard"] is True
    assert protocol["actuator_commands_allowed"] is False
    assert protocol["operational_outputs_allowed"] is False
    assert protocol["splits"]["holdout_used_for_selection"] is False
    assert "not flight control" in protocol["claim_boundary"].lower()
    assert "airworthiness" in protocol["claim_boundary"].lower()


def test_environment_and_routes_are_deterministic_and_constraint_aware():
    module = load_module()
    protocol = load_protocol()
    spec = module.build_scenarios(protocol, "development", 1)[0]
    first = module.generate_environment(spec, protocol)
    second = module.generate_environment(spec, protocol)

    assert module.environment_digest(first) == module.environment_digest(second)
    assert np.array_equal(first.obstacles, second.obstacles)
    assert first.spectral_receipt["all_components_below_guard"] is True

    specialist = protocol["specialists"][0]
    path, expansions = module.plan_specialist(first, specialist)
    metrics = module.path_metrics(first, path, protocol, observed=False)
    assert expansions > 0
    assert metrics["endpoint_reached"] is True
    assert metrics["collision"] is False


def test_hybrid_router_selects_only_a_frozen_named_specialist():
    module = load_module()
    protocol = load_protocol()
    spec = module.build_scenarios(protocol, "development", 1)[1]
    rows = module.evaluate_scenario(spec, protocol)
    specialist_names = {row["name"] for row in protocol["specialists"]}
    candidate_rows = [row for row in rows if row["kind"] == "hybrid_candidate"]

    assert len(candidate_rows) == len(protocol["hybrid_candidates"])
    assert all(row["selected_specialist"] in specialist_names for row in candidate_rows)
    assert all(row["spectral_guard_pass"] for row in rows)


def test_v2_guard_falls_back_to_balanced_specialist_on_predicted_regression():
    module = load_module()
    protocol = json.loads(PROTOCOL_V2.read_text(encoding="utf-8"))
    module.validate_protocol(protocol)
    candidate = protocol["hybrid_candidates"][0]

    def metrics(*, energy, risk, reserve, energy_score, risk_score):
        return {
            "endpoint_reached": True,
            "collision": False,
            "reserve_fraction": reserve,
            "energy_used": energy,
            "risk_exposure": risk,
            "distance_score": 0.9,
            "energy_score": energy_score,
            "risk_score": risk_score,
            "smoothness_score": 0.9,
            "clearance_score": 0.8,
            "reserve_score": 0.8,
        }

    results = {
        "astar_energy": {
            "observed_metrics": metrics(
                energy=10.2, risk=4.0, reserve=0.30, energy_score=0.98, risk_score=0.78
            )
        },
        "astar_balanced": {
            "observed_metrics": metrics(
                energy=10.0, risk=3.9, reserve=0.32, energy_score=0.94, risk_score=0.82
            )
        },
    }

    assert module.select_hybrid_specialist(results, candidate) == "astar_balanced"


def test_collision_is_a_hard_promotion_veto_even_with_positive_scores():
    module = load_module()
    protocol = load_protocol()
    spec = module.build_scenarios(protocol, "development", 1)[0]
    development_rows = module.evaluate_scenario(spec, protocol)
    development_leaderboard = module.aggregate_rows(development_rows)
    selected_candidate = module.first_ranked_kind(
        development_leaderboard, "hybrid_candidate"
    )["strategy"]

    validation_rows = []
    for condition_index, condition in enumerate(protocol["conditions"][:2]):
        for index in range(3):
            validation_spec = module.ScenarioSpec(
                "validation",
                condition_index,
                condition["name"],
                99000 + condition_index * 100 + index,
            )
            scenario_rows = module.evaluate_scenario(validation_spec, protocol)
            for row in scenario_rows:
                if row["strategy"] == selected_candidate:
                    row = copy.deepcopy(row)
                    row["score"] = 1.0
                    row["collision"] = True
                    row["constraint_violation"] = True
                validation_rows.append(row)
    validation_leaderboard = module.aggregate_rows(validation_rows)
    gate = module.build_promotion_gate(
        development_leaderboard,
        validation_rows,
        validation_leaderboard,
        protocol,
        protocol_conformant=True,
    )

    assert gate["promoted"] is False
    assert gate["checks"]["candidate_collision_rate_within_limit"] is False
    assert gate["gate"] == "NOT_PROMOTED_ASSURANCE_GATE_FAILED"


def test_small_suite_writes_a_hash_valid_reproducibility_packet(tmp_path):
    module = load_module()
    protocol = load_protocol()
    protocol["splits"]["development"]["scenarios_per_condition"] = 1
    protocol["splits"]["validation"]["scenarios_per_condition"] = 1
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
    out_dir = tmp_path / "run"

    summary = module.run_suite(protocol_path, out_dir, workers=1, resume=True)
    manifest = json.loads((out_dir / "manifest.sha256.json").read_text(encoding="utf-8"))

    assert summary["protocol"]["conformant_execution"] is True
    assert summary["validation"]["scenario_count"] == len(protocol["conditions"])
    assert summary["claim_gate"]["airworthiness"] is False
    assert manifest["files"]
    for name, metadata in manifest["files"].items():
        assert module.sha256_file(out_dir / name) == metadata["sha256"]
