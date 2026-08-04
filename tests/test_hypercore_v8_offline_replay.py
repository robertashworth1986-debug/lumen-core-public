from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "run_hypercore_v8_offline_replay.py"
PROTOCOL = ROOT / "config" / "hypercore_v8_validation_protocol_v1.json"
FIXED_UTC = "2026-08-02T10:30:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("hypercore_v8_offline_replay", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_synthetic_preflight_is_deterministic_and_never_promotes_claims(tmp_path):
    module = load_module()
    bundle = module.build_synthetic_fixture(tmp_path / "fixture", seed=20260802)
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    first = module.run_replay(
        protocol_path=PROTOCOL,
        bundle_path=bundle,
        output_path=first_path,
        generated_utc=FIXED_UTC,
        seed=20260802,
        null_replicates=None,
    )
    second = module.run_replay(
        protocol_path=PROTOCOL,
        bundle_path=bundle,
        output_path=second_path,
        generated_utc=FIXED_UTC,
        seed=20260802,
        null_replicates=None,
    )

    assert first["status"] == "SYNTHETIC_PREFLIGHT_COMPLETE_NOT_EXTERNAL_VALIDATION"
    assert first["result_classification"] == "DESCRIPTIVE_ONLY"
    assert first["deterministic_result_sha256"] == second["deterministic_result_sha256"]
    assert first["deterministic_result"] == second["deterministic_result"]
    assert first["deterministic_result"]["split_manifest"]["walk_forward_fold_count"] == 5
    assert first["deterministic_result"]["threshold_receipt"]["thresholds_frozen_before_holdout"] is True
    assert len(first["deterministic_result"]["null_results"]) == 3
    assert all(
        row["replicate_count"] == 999
        for row in first["deterministic_result"]["null_results"]
    )
    assert len(first["deterministic_result"]["ablation_results"]) == 6
    assert len(first["deterministic_result"]["stress_results"]) == 9
    gates = first["deterministic_result"]["promotion_gate_results"]
    assert gates["all_registered_baselines_executed"] is True
    assert gates["multiplicity_adjustment_applied"] is True
    assert gates["independent_reproduction_complete"] is False
    assert gates["economic_counterfactual_complete"] is False
    controls = first["execution_controls"]
    assert controls["network_access_performed"] is False
    assert controls["production_connection_performed"] is False
    assert controls["control_write_performed"] is False
    assert controls["credentials_read"] is False
    assert controls["holdout_outcomes_used_for_threshold_selection"] is False
    assert "external validation" in first["claim_boundary"]["blocked"]


def test_source_hash_mismatch_writes_abstention_receipt(tmp_path):
    module = load_module()
    bundle_path = module.build_synthetic_fixture(tmp_path / "fixture", seed=20260802)
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    data_path = bundle_path.parent / bundle["data_path"]
    data_path.write_text(data_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    output = tmp_path / "abstained.json"

    result = module.main(
        [
            "--source-bundle",
            str(bundle_path),
            "--protocol",
            str(PROTOCOL),
            "--output",
            str(output),
            "--generated-utc",
            FIXED_UTC,
        ]
    )

    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert result == 2
    assert receipt["status"] == "ABSTAINED_PRECONDITION"
    assert receipt["result_classification"] == "NO_RESULT"
    assert receipt["precondition_code"] == "SOURCE_HASH_MISMATCH"
    assert "No performance" in receipt["claim_boundary"]


def test_null_replicate_floor_fails_closed_before_scoring(tmp_path):
    module = load_module()
    bundle = module.build_synthetic_fixture(tmp_path / "fixture", seed=20260802)

    try:
        module.run_replay(
            protocol_path=PROTOCOL,
            bundle_path=bundle,
            output_path=tmp_path / "should_not_exist.json",
            generated_utc=FIXED_UTC,
            seed=20260802,
            null_replicates=998,
        )
    except module.ReplayPreconditionError as exc:
        assert exc.code == "NULL_REPLICATES_BELOW_PROTOCOL"
    else:
        raise AssertionError("runner accepted fewer null replicates than the protocol")
