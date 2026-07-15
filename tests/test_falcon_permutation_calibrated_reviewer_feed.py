from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FALCON_PERMUTATION_CALIBRATED_REVIEWER_FEED.py"
FEED = ROOT / "dashboard" / "data" / "falcon_permutation_calibrated_router.json"
OUT_FEED = ROOT / "out" / "ops" / "falcon_permutation_calibrated_router_latest.json"
PUBLIC_DOC = ROOT / "docs" / "FALCON_PERMUTATION_CALIBRATED_ROUTER_V3_NULL_RESULT_2026-07-15.md"
GRANT_DOC = (
    ROOT
    / "grant_submissions"
    / "DPA26BZ04_DV016_FALCON"
    / "DPA26BZ04_DV016_PERMUTATION_CALIBRATED_ROUTER_V3_NULL_RESULT_2026-07-15.md"
)
MODEL_RECEIPT = (
    ROOT
    / "evidence"
    / "falcon"
    / "qwen2_5_1_5b_instruct_weights_receipt_20260715.json"
)
MANIFEST = (
    ROOT
    / "out"
    / "ops"
    / "falcon_permutation_calibrated_router_review_manifest_latest.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("falcon_reviewer_feed", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_source_packet_recomputes_every_hash_and_trace_link() -> None:
    module = load_module()
    packet = module.verify_source_packet()

    assert packet["manifest"]["manifest_sha256"] == (
        "2b6ad75db13396a26ab2600da73e764b33400f815945e3e9f057cf699bfb5bcb"
    )
    assert packet["trace"]["verified"] is True
    assert packet["trace"]["record_count"] == 30
    assert packet["trace"]["terminal_sha256"] == (
        "a2b51eb22f287f939909028f06218e0f7077e65b414ac9b8af858b21a83015ec"
    )
    assert packet["failed_gate_checks"] == [
        "mean_permutation_agreement",
        "minimum_permutation_agreement",
        "per_context_accuracy",
    ]


def test_published_feed_preserves_null_result_and_closes_claim_gates() -> None:
    payload = json.loads(FEED.read_text(encoding="utf-8"))

    assert payload["schema"] == "falcon_permutation_calibrated_router_reviewer_feed.v1"
    assert payload["status"] == "FROZEN_NULL_RESULT_PRESERVED"
    assert payload["decision"]["qualification_gate_passed"] is False
    assert payload["decision"]["correct_decision_count"] == 27
    assert payload["decision"]["decision_count"] == 30
    assert payload["decision"]["overall_accuracy"] == pytest.approx(0.9)
    assert payload["decision"]["unsupported_output_rate"] == 0.0
    assert payload["decision"]["per_context_accuracy"]["nominal"] == pytest.approx(0.7)
    assert payload["error_pattern"]["error_count"] == 3
    assert all(
        row["expected_context_class"] == "nominal"
        and row["selected_context_class"] == "noise"
        for row in payload["error_pattern"]["rows"]
    )
    assert all(value is False for value in payload["claim_gate"].values())
    assert payload["development_lineage"]["cross_protocol_lift_claim_allowed"] is False
    assert payload["next_allowed_experiment"]["requires_new_protocol_identity"] is True


def test_feed_copies_match_and_canonical_feed_hash_recomputes() -> None:
    module = load_module()
    dashboard_raw = FEED.read_bytes()
    out_raw = OUT_FEED.read_bytes()
    payload = json.loads(dashboard_raw)

    assert dashboard_raw == out_raw
    observed = payload.pop("feed_sha256")
    assert observed == module.canonical_sha256(payload)


def test_model_receipt_records_exact_bytes_without_local_path() -> None:
    module = load_module()
    receipt = json.loads(MODEL_RECEIPT.read_text(encoding="utf-8"))
    observed = receipt.pop("receipt_sha256")

    assert receipt["model_id"] == module.PINNED_MODEL_ID
    assert receipt["resolved_revision"] == module.PINNED_MODEL_REVISION
    assert receipt["bytes"] == 3_087_467_144
    assert receipt["sha256"] == module.PINNED_MODEL_WEIGHTS_SHA256
    assert receipt["byte_identity_verified"] is True
    assert receipt["local_path_published"] is False
    assert observed == module.canonical_sha256(receipt)
    rendered = json.dumps(receipt).casefold().replace("\\", "/")
    assert "c:/users/" not in rendered
    assert "e:/lumaruntime/" not in rendered


def test_generated_manifest_hashes_every_public_artifact() -> None:
    module = load_module()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    without_hash = {key: value for key, value in manifest.items() if key != "manifest_sha256"}

    assert manifest["schema"] == "falcon_permutation_calibrated_router_review_manifest.v1"
    assert manifest["manifest_sha256"] == module.canonical_sha256(without_hash)
    assert manifest["artifact_chain_sha256"] == module.canonical_sha256(
        manifest["artifacts"]
    )
    assert len(manifest["artifacts"]) == 5
    for row in manifest["artifacts"]:
        path = ROOT / row["path"]
        assert path.is_file()
        assert path.stat().st_size == row["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_public_projection_excludes_raw_prompts_outputs_and_private_paths() -> None:
    combined = "\n".join(
        [
            FEED.read_text(encoding="utf-8"),
            PUBLIC_DOC.read_text(encoding="utf-8"),
            GRANT_DOC.read_text(encoding="utf-8"),
        ]
    ).casefold().replace("\\", "/")

    assert "c:/users/" not in combined
    assert "e:/lumaruntime/" not in combined
    assert '"prompt":' not in combined
    assert '"raw_output":' not in combined
    assert "qualification gate passed: `false`" in combined
    assert "does not close the falcon requirement" in combined


def test_trace_tamper_is_rejected(tmp_path: Path) -> None:
    module = load_module()
    copied = tmp_path / "run"
    shutil.copytree(module.RUN_DIR, copied)
    trace_path = copied / "traces.jsonl"
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["validation_error"] = "tampered"
    lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    trace_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact receipt mismatch|trace record hash mismatch"):
        module.verify_source_packet(copied)


def test_model_blob_verifier_rejects_changed_bytes(tmp_path: Path) -> None:
    module = load_module()
    blob = tmp_path / "model.safetensors"
    blob.write_bytes(b"bounded-model-fixture")
    expected = hashlib.sha256(blob.read_bytes()).hexdigest()

    receipt = module.verify_model_blob(
        blob, expected_sha256=expected, expected_bytes=blob.stat().st_size
    )
    assert receipt["byte_identity_verified"] is True

    blob.write_bytes(blob.read_bytes() + b"x")
    with pytest.raises(ValueError, match="byte identity mismatch"):
        module.verify_model_blob(
            blob, expected_sha256=expected, expected_bytes=len(b"bounded-model-fixture")
        )


def test_custody_mirror_is_complete_verified_and_non_destructive(tmp_path: Path) -> None:
    module = load_module()
    packet = module.verify_source_packet()
    result = module.stage_mirror_packet(tmp_path / "vault", packet)
    manifest_path = Path(result["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    without_hash = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }

    assert result["all_file_hashes_verified"] is True
    assert result["file_count"] >= 16
    assert manifest["qualification_gate_passed"] is False
    assert manifest["manifest_sha256"] == module.canonical_sha256(without_hash)
    assert manifest["packet_chain_sha256"] == module.canonical_sha256(manifest["files"])
    for row in manifest["files"]:
        mirrored = manifest_path.parent / row["packet_path"]
        assert mirrored.is_file()
        assert mirrored.stat().st_size == row["bytes"]
        assert hashlib.sha256(mirrored.read_bytes()).hexdigest() == row["sha256"]

    first = manifest["files"][0]
    collision = manifest_path.parent / first["packet_path"]
    collision.write_bytes(collision.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="immutable mirror collision"):
        module.stage_mirror_packet(tmp_path / "vault", packet)
