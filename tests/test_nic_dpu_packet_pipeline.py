from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


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


def test_retained_reference_manifests_have_every_exact_dependency() -> None:
    root = ROOT / "evidence/hardware/nic_dpu_packet_pipeline_20260914"
    manifests = list(root.rglob("SHA256_MANIFEST.json"))
    assert len(manifests) == 2
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["entry_count"] == len(manifest["entries"])
        for entry in manifest["entries"]:
            path = (manifest_path.parent / entry["path"]).resolve()
            assert path.is_relative_to(root.resolve())
            body = path.read_bytes()
            assert len(body) == entry["bytes"]
            assert hashlib.sha256(body).hexdigest() == entry["sha256"]


def test_builder_compiles_tests_and_hash_seals_receipt(tmp_path: Path) -> None:
    module = load_module()
    try:
        module.detect_zig_python()
        module.detect_sanitizer_compiler()
    except RuntimeError as exc:
        pytest.skip(f"optional pinned Zig C toolchain unavailable: {exc}")
    mirrors = [tmp_path / "mirror_a", tmp_path / "mirror_b"]
    result = module.build_evidence(
        tmp_path / "out",
        benchmark_packets=20_000,
        mirror_destinations=mirrors,
        property_cases=5000,
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
    assert manifest["entry_count"] == 10 + len(module.PACKAGE_PATHS)
    properties = receipt["verification"]["generated_properties"]
    assert properties["cases"] == sum(properties["outcomes"].values()) == 5000
    assert properties["seed"] == 20260914
    assert properties["failed"] == 0
    assert properties["coverage_guided_fuzzing"] is False
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
        manifests = list(destination.rglob("SHA256_MANIFEST.json"))
        assert len(manifests) == 1
        mirrored_manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
        for entry in mirrored_manifest["entries"]:
            retained = manifests[0].parent / entry["path"]
            assert retained.is_file()
            assert hashlib.sha256(retained.read_bytes()).hexdigest() == entry["sha256"]


def test_toolchain_detector_rejects_an_unpinned_version(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs:
        SimpleNamespace(returncode=0, stdout="0.14.1\n", stderr=""))
    with pytest.raises(RuntimeError, match="toolchain"):
        module.detect_zig_python()


def stub_native_commands(module, monkeypatch, *, sanitizer_error=False, change_original=False):
    original_c_hash = hashlib.sha256(module.SOURCES[1].read_bytes()).hexdigest()
    mutated = False
    def result(command, cwd, **kwargs):
        nonlocal mutated
        output = ""
        error = ""
        if command[-1] == "version":
            output = "0.15.2\n"
        elif command[-1] == "--version":
            output = "fixture C compiler\n"
        elif "-o" in command:
            if change_original and not mutated:
                module.SOURCES[1].write_bytes(module.SOURCES[1].read_bytes() + b"\n/* changed during compile */\n")
                mutated = True
        elif "sanitized" in command[0]:
            output = "TESTS passed=7 failed=0\n"
            error = "runtime error: signed integer overflow\n" if sanitizer_error else ""
        else:
            output = ("TESTS passed=7 failed=0\n"
                      "BENCH packets=100 elapsed_seconds=0.1 packets_per_second=1000.0 queued=100\n")
        return SimpleNamespace(returncode=0, stdout=output, stderr=error)
    monkeypatch.setattr(module, "detect_zig_python", lambda: Path(sys.executable))
    monkeypatch.setattr(module, "detect_sanitizer_compiler", lambda explicit=None: Path(sys.executable))
    monkeypatch.setattr(module, "verify_sanitizer_toolchain", lambda *args: {
        "compiler_file_sha256": module.sha256_file(Path(sys.executable)),
        "positive_controls": {"address": {"detected": True}, "undefined": {"detected": True}}})
    monkeypatch.setattr(module, "run_checked", result)
    return original_c_hash


def test_zero_exit_with_a_sanitizer_diagnostic_cannot_claim_success(tmp_path, monkeypatch) -> None:
    module = load_module()
    stub_native_commands(module, monkeypatch, sanitizer_error=True)
    with pytest.raises(RuntimeError, match="sanitizer"):
        module.build_evidence(tmp_path / "out", benchmark_packets=100)


def test_receipt_binds_the_frozen_compile_input_not_later_source_bytes(tmp_path, monkeypatch) -> None:
    module = load_module()
    original_root = module.ROOT
    fixture_root = tmp_path / "fixture-root"
    copied = []
    for source in module.SOURCES:
        destination = fixture_root / source.relative_to(original_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
        copied.append(destination)
    module.ROOT = fixture_root
    module.SOURCES = copied
    module.PACKAGE_PATHS = copied
    original_c_hash = stub_native_commands(module, monkeypatch, change_original=True)
    result = module.build_evidence(tmp_path / "out", benchmark_packets=100)
    source_row = next(row for row in result["receipt"]["sources"]
                      if row["path"] == "code/hardware/nic_dpu_packet_pipeline.c")
    assert source_row["sha256"] == original_c_hash


def test_changed_frozen_compile_input_cannot_publish_a_receipt(tmp_path, monkeypatch) -> None:
    module = load_module()
    stub_native_commands(module, monkeypatch)
    original = module.run_checked
    def changed(command, cwd, **kwargs):
        result = original(command, cwd, **kwargs)
        if "-o" in command:
            source = next(Path(arg) for arg in command if arg.endswith("nic_dpu_packet_pipeline.c"))
            source.write_bytes(source.read_bytes() + b"\n/* frozen input tampered */\n")
        return result
    monkeypatch.setattr(module, "run_checked", changed)
    with pytest.raises(RuntimeError, match="frozen compile/package input changed"):
        module.build_evidence(tmp_path / "out", benchmark_packets=100)
    assert not (tmp_path / "out/nic_dpu_packet_pipeline_latest.json").exists()
    assert not list((tmp_path / "out").rglob("RECEIPT.json"))


def test_conflicting_duplicate_native_summaries_are_rejected() -> None:
    module = load_module()
    output = ("TESTS passed=7 failed=0\nTESTS passed=0 failed=7\n"
              "BENCH packets=100 elapsed_seconds=0.1 packets_per_second=1000.0 queued=100\n")
    with pytest.raises(RuntimeError, match="unexpected C test output"):
        module.parse_test_output(output)


def test_changed_property_generator_is_rejected_before_execution(tmp_path):
    module = load_module()
    source = tmp_path / "changed.c"
    source.write_bytes(module.PROPERTY_SOURCE.read_bytes() + b"\n/* changed */\n")
    frozen = {module.PROPERTY_SOURCE: source, module.PROPERTY_PROTOCOL: module.PROPERTY_PROTOCOL}
    with pytest.raises(RuntimeError, match="frozen supplemental protocol"):
        module.run_generated_properties(Path(sys.executable), tmp_path, frozen, 100)


@pytest.mark.parametrize("cases", [-1, 10_000_001, True, 1.5])
def test_invalid_property_case_bounds_are_rejected_before_toolchain_use(tmp_path, cases):
    module = load_module()
    with pytest.raises(ValueError, match="property_cases"):
        module.build_evidence(tmp_path, 100, property_cases=cases)


def test_native_sanitizer_positive_controls_detect_deliberate_faults(tmp_path) -> None:
    module = load_module()
    try:
        compiler = module.detect_sanitizer_compiler()
    except RuntimeError as exc:
        pytest.skip(f"optional sanitizer compiler unavailable: {exc}")
    result = module.verify_sanitizer_toolchain(compiler, tmp_path)
    assert all(row["detected"] for row in result["positive_controls"].values())


@pytest.mark.parametrize("exit_code,diagnostic", [(0, ""), (1, ""), (0, "AddressSanitizer: heap-buffer-overflow")])
def test_positive_control_rejects_silent_success_crash_or_nonfailing_diagnostic(tmp_path, monkeypatch, exit_code, diagnostic):
    module = load_module()
    def command(args, cwd, **kwargs):
        if "-o" in args:
            Path(args[args.index("-o") + 1]).write_bytes(b"fixture binary")
        return SimpleNamespace(returncode=0, stdout="fixture compiler", stderr="")
    monkeypatch.setattr(module, "run_checked", command)
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs:
        SimpleNamespace(returncode=exit_code, stdout="", stderr=diagnostic))
    with pytest.raises(RuntimeError, match="positive control"):
        module.verify_sanitizer_toolchain(Path(sys.executable), tmp_path)
