from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LUMAJET_FLIGHT_ASSURANCE_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("lumajet_flight_assurance_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_packet_retains_v1_adverse_result_and_bounds_v2_tiny_pass():
    module = load_module()
    payload = module.build_packet()
    summary = payload["summary"]

    assert summary["v1_adverse_result_retained"] is True
    assert summary["v2_internal_generated_gate_pass"] is True
    assert summary["practical_effect_classification"] == "TINY_EFFECT_INTERNAL_GUARD_PASS"
    assert summary["v2_validation_scenario_count"] == 1400
    assert summary["v2_candidate_collision_rate"] == 0
    assert summary["v2_candidate_endpoint_failure_rate"] == 0
    assert summary["v2_candidate_reserve_breach_rate"] == 0
    assert summary["external_reproduction_complete"] is False
    assert summary["airworthiness_claim_allowed"] is False
    assert all(payload["lineage_verification"].values())
    unhashed = {key: value for key, value in payload.items() if key != "packet_sha256"}
    assert module.sha256_payload(unhashed) == payload["packet_sha256"]


def test_four_level_gate_stops_before_self_issuing_external_validation():
    module = load_module()
    payload = module.build_packet()
    levels = {row["level"]: row for row in payload["four_level_gate"]}

    assert levels[1]["status"] == "PASS"
    assert levels[2]["status"] == "PASS"
    assert levels[3]["status"] == "PASS_TINY_EFFECT"
    assert levels[4]["status"] == "KIT_READY_EXTERNAL_EXECUTION_REQUIRED"
    assert levels[4]["external"] is True


def test_summary_receipt_verifier_detects_tampering():
    module = load_module()
    run = module.verify_run(module.DEFAULT_V2_RUN)
    tampered = copy.deepcopy(run["summary"])
    tampered["promotion_gate"]["promoted"] = False

    assert module.verify_summary_receipt(run["summary"])["valid"] is True
    assert module.verify_summary_receipt(tampered)["valid"] is False


def test_blind_kit_omits_expected_leaderboard_and_verifies_inputs():
    module = load_module()
    payload = module.build_packet()
    outputs = module.write_blind_reproduction_kit(payload, module.DEFAULT_V2_RUN)
    manifest = module.load_json(outputs["kit_manifest"])

    assert manifest["expected_leaderboard_included"] is False
    assert "summary.json" not in manifest["files"]
    assert "leaderboard.csv" not in manifest["files"]
    assert outputs["kit_zip"].exists()
    for name, metadata in manifest["files"].items():
        assert module.sha256_file(outputs["kit_dir"] / name) == metadata["sha256"]
