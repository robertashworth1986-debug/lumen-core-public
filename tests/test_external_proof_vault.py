from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "STAGE_EXTERNAL_PROOF_VAULT.py"
INTAKE_SCRIPT = ROOT / "code" / "ops" / "BUILD_EXTERNAL_PROOF_DRIVE_INTAKE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("stage_external_proof_vault", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def load_intake_module():
    spec = importlib.util.spec_from_file_location("build_external_proof_drive_intake", INTAKE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_manifest_selects_high_value_proof_artifacts_without_moving_sources(tmp_path):
    module = load_module()
    manifest = module.build_manifest(tmp_path, package_name="TEST_PACKET")

    assert manifest["schema"] == "external_proof_vault_manifest_v2"
    assert manifest["packet_dir"].endswith("TEST_PACKET")
    assert manifest["summary"]["artifact_count"] >= 25
    assert manifest["summary"]["ready_count"] >= 20
    assert manifest["copy_policy"].startswith("Copy selected proof artifacts only")
    assert "does not create revenue" in manifest["claim_boundary"]

    relative_paths = {row["relative_path"] for row in manifest["artifacts"]}
    assert "out/ops/geometry_live_breadth_proof_queue_latest.json" in relative_paths
    assert "out/ops/live_proof_value_meter_latest.json" in relative_paths
    assert "out/ops/dollar_claim_gate_latest.json" in relative_paths
    assert "grant_submissions/TOP5_LIVE_PROOF_SUBMISSION_BOARD_2026-06-22.md" in relative_paths
    assert "out/ops/top_geometry_live_replay_results_latest.json" in relative_paths
    assert "out/ops/sector_validation_priority_board_latest.json" in relative_paths
    assert "out/ops/lumencore_estate_master_index_manifest_latest.json" in relative_paths
    assert "code/geometry_time_series_model_routing_benchmark.py" in relative_paths
    assert manifest["summary"]["frozen_input_count"] >= 5


def test_stage_vault_copies_and_hash_verifies_to_temp_packet(tmp_path):
    module = load_module()
    manifest = module.stage_vault(tmp_path, package_name="TEST_PACKET", copy_files=True)

    packet_dir = Path(manifest["packet_dir"])
    assert (packet_dir / "manifest.json").exists()
    assert (packet_dir / "manifest.sha256.txt").exists()
    assert (packet_dir / "README.md").exists()
    assert manifest["copy_result"]["copied_count"] == manifest["summary"]["ready_count"]
    assert manifest["copy_result"]["all_copied_hashes_verified"] is True

    queue_copy = packet_dir / "artifacts" / "geometry" / "out" / "ops" / "geometry_live_breadth_proof_queue_latest.json"
    assert queue_copy.exists()

def test_external_drive_intake_scores_proof_tokens_without_path_mangling(tmp_path):
    module = load_intake_module()
    proof_file = tmp_path / "whitehole_proofs" / "CHAMPION_FREEZE_20260205T122631Z" / "EVIDENCE"
    proof_file.mkdir(parents=True)
    target = proof_file / "multi_asset_live_delta_ledger.jsonl"
    target.write_text('{"measured_rows": 3}\n', encoding="utf-8")

    normalized = module.normalized_text(target)
    scored = module.score_file(tmp_path, target, target.stat())

    assert "multi_asset_live_delta_ledger.jsonl" in normalized
    assert "/m/u/l/t/i" not in normalized
    assert "proof_chain" in scored["matched_groups"]
    assert "live_measurement" in scored["matched_groups"]
    assert "multi_asset" in scored["matched_groups"]
    assert scored["evidence_class"] == "live_frozen_triple_threat_candidate"
