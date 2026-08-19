from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NIC_DPU_PACKET_PIPELINE_EVIDENCE.py"
SOURCE = ROOT / "code" / "hardware" / "nic_dpu_packet_pipeline.c"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_nic_dpu_packet_pipeline_evidence", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_c_fast_path_is_allocation_free_and_bounded() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    assert "malloc(" not in text
    assert "calloc(" not in text
    assert "realloc(" not in text
    assert "LC_PARSE_TRUNCATED" in text
    assert "view->fragmented" in text


def test_builder_compiles_tests_and_hash_seals_receipt(tmp_path: Path) -> None:
    module = load_module()
    mirrors = [tmp_path / "mirror_a", tmp_path / "mirror_b"]
    result = module.build_evidence(
        tmp_path / "out",
        benchmark_packets=20_000,
        mirror_destinations=mirrors,
    )
    run_dir = Path(result["run_dir"])
    receipt = json.loads((run_dir / "RECEIPT.json").read_text(encoding="utf-8"))
    gates = receipt["claim_gates"]
    assert receipt["verification"]["tests"] == {"passed": 7, "failed": 0}
    assert receipt["verification"]["benchmark"]["queued"] == 20_000
    assert receipt["verification"]["sanitizers"]["address_sanitizer"] is True
    assert receipt["verification"]["sanitizers"]["undefined_behavior_sanitizer"] is True
    assert receipt["verification"]["sanitizers"]["test_exit_code"] == 0
    assert gates["bounded_c11_packet_pipeline_implemented_and_tested"] is True
    assert gates["deep_c_expertise"] is False
    assert gates["nic_expertise"] is False
    assert gates["dpu_expertise"] is False
    assert gates["nic_or_dpu_hardware_offload"] is False
    manifest = json.loads(
        (run_dir / "SHA256_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert manifest["entry_count"] == 2
    for entry in manifest["entries"]:
        actual = hashlib.sha256((run_dir / entry["path"]).read_bytes()).hexdigest()
        assert actual == entry["sha256"]
    report = (run_dir / "REPORT.md").read_text(encoding="utf-8")
    assert "Not Verified" in report
    assert "NVIDIA BlueField hardware" in report
    mirror_receipt = result["mirror_receipt"]
    assert mirror_receipt["artifact_count"] >= 10
    assert all(row["all_hashes_verified"] for row in mirror_receipt["destinations"])
    for destination in mirrors:
        copied_receipt = json.loads(
            (destination / "MIRROR_RECEIPT.json").read_text(encoding="utf-8")
        )
        assert copied_receipt["artifact_count"] == mirror_receipt["artifact_count"]
