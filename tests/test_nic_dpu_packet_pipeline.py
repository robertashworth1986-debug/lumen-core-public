from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

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


@pytest.mark.parametrize(
    ("version", "returncode"),
    [("0.15.1", 0), ("0.16.0", 0), ("0.15.2-dev.1", 0), ("", 0), ("0.15.2", 1)],
)
def test_toolchain_detector_rejects_unverified_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, version: str, returncode: int
) -> None:
    module = load_module()
    python = tmp_path / "python"
    python.touch()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.sys, "executable", str(python))
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, returncode, version, ""),
    )
    with pytest.raises(RuntimeError, match="exact Zig 0.15.2 is required"):
        module.detect_zig_python()


def test_toolchain_detector_selects_exact_version_after_wrong_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_module()
    workspace_python = tmp_path / ".venv" / "Scripts" / "python.exe"
    workspace_python.parent.mkdir(parents=True)
    workspace_python.touch()
    current_python = tmp_path / "python"
    current_python.touch()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.sys, "executable", str(current_python))
    calls = []

    def probe(command, **kwargs):
        calls.append(command)
        version = "0.16.0" if command[0] == str(workspace_python) else "0.15.2\n"
        return subprocess.CompletedProcess(command, 0, version, "")

    monkeypatch.setattr(module.subprocess, "run", probe)
    assert module.detect_zig_python() == current_python
    assert calls == [
        [str(workspace_python), "-m", "ziglang", "version"],
        [str(current_python), "-m", "ziglang", "version"],
    ]


def test_toolchain_detector_rejects_absent_interpreters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.sys, "executable", str(tmp_path / "absent"))

    def unexpected_probe(*args, **kwargs):
        pytest.fail("nonexistent interpreters must not be executed")

    monkeypatch.setattr(module.subprocess, "run", unexpected_probe)
    with pytest.raises(RuntimeError, match="exact Zig 0.15.2 is required"):
        module.detect_zig_python()


def test_c_fast_path_is_allocation_free_and_bounded() -> None:
    text = SOURCE.read_text(encoding="utf-8")
    assert "malloc(" not in text
    assert "calloc(" not in text
    assert "realloc(" not in text
    assert "LC_PARSE_TRUNCATED" in text
    assert "view->fragmented" in text


def test_builder_compiles_tests_and_hash_seals_receipt(tmp_path: Path) -> None:
    module = load_module()
    try:
        module.detect_zig_python()
        module.detect_sanitizer_compiler()
    except RuntimeError as exc:
        pytest.skip(f"optional native C toolchain unavailable: {exc}")
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
    assert receipt["toolchain"]["zig_version"] == "0.15.2"
    sanitizer = receipt["verification"]["sanitizers"]
    assert sanitizer["recover_on_error"] is False
    assert sanitizer["diagnostic_scan_passed"] is True
    compiler = Path(sanitizer["toolchain"]["compiler_path"])
    assert hashlib.sha256(compiler.read_bytes()).hexdigest() == sanitizer["toolchain"]["compiler_file_sha256"]
    assert sanitizer["toolchain"]["flags"] == module.SANITIZER_FLAGS
    options = sanitizer["toolchain"]["runtime_options"]
    assert options["ASAN_OPTIONS"] == "halt_on_error=1:abort_on_error=0"
    assert options["UBSAN_OPTIONS"] == "halt_on_error=1"
    assert "LSAN_OPTIONS" in options
    for control in sanitizer["toolchain"]["positive_controls"].values():
        assert control["detected"] is True
        assert control["test_exit_code"] != 0
        assert control["expected_diagnostic"] in control["test_stderr"]
        assert hashlib.sha256(control["source"].encode()).hexdigest() == control["source_sha256"]
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


@pytest.mark.parametrize("kind", ["address", "undefined"])
@pytest.mark.parametrize("outcome", ["silent_success", "silent_crash", "zero_exit_diagnostic", "wrong_diagnostic"])
def test_sanitizer_controls_reject_unproved_instrumentation(tmp_path, monkeypatch, kind, outcome):
    module = load_module()
    compiler = tmp_path / "compiler"
    compiler.write_bytes(b"fixture compiler")

    def compile_command(command, cwd, **kwargs):
        if "-o" in command:
            Path(command[command.index("-o") + 1]).write_bytes(b"fixture executable")
        return subprocess.CompletedProcess(command, 0, "fixture compiler", "")

    def run_control(command, **kwargs):
        current = Path(command[0]).stem.removesuffix("_control")
        marker = module.SANITIZER_CONTROLS[current][1]
        if current != kind:
            return subprocess.CompletedProcess(command, 1, "", marker)
        code, diagnostic = {
            "silent_success": (0, ""),
            "silent_crash": (-11, ""),
            "zero_exit_diagnostic": (0, marker),
            "wrong_diagnostic": (1, "different runtime failure"),
        }[outcome]
        return subprocess.CompletedProcess(command, code, "", diagnostic)

    monkeypatch.setattr(module, "run_checked", compile_command)
    monkeypatch.setattr(module.subprocess, "run", run_control)
    with pytest.raises(RuntimeError, match=f"sanitizer {kind} positive control"):
        module.verify_sanitizer_toolchain(compiler)


def _stub_builder_commands(module, monkeypatch, *, summary="TESTS passed=7 failed=0\n", diagnostic="", stdout_diagnostic=False):
    compiler = Path(sys.executable)
    monkeypatch.setattr(module, "detect_zig_python", lambda: compiler)
    monkeypatch.setattr(module, "detect_sanitizer_compiler", lambda explicit=None: compiler)
    monkeypatch.setattr(module, "verify_sanitizer_toolchain", lambda value: {
        "compiler_file_sha256": module.sha256_file(compiler),
        "positive_controls": {"address": {"detected": True}, "undefined": {"detected": True}},
    })

    def command(args, cwd, **kwargs):
        output = ""
        error = ""
        if args[-1] == "version":
            output = "0.15.2\n"
        elif args[-1] == "--version":
            output = "fixture compiler\n"
        elif "-o" in args:
            pass
        elif "sanitized" in args[0]:
            output = summary + (diagnostic if stdout_diagnostic else "")
            error = "" if stdout_diagnostic else diagnostic
        else:
            output = "TESTS passed=7 failed=0\nBENCH packets=100 elapsed_seconds=0.1 packets_per_second=1000.0 queued=100\n"
        return subprocess.CompletedProcess(args, 0, output, error)

    monkeypatch.setattr(module, "run_checked", command)


@pytest.mark.parametrize("stdout_diagnostic", [False, True])
@pytest.mark.parametrize("diagnostic", ["runtime error: signed integer overflow", "ERROR: AddressSanitizer: heap-buffer-overflow"])
def test_pipeline_cannot_publish_zero_exit_with_sanitizer_diagnostic(tmp_path, monkeypatch, stdout_diagnostic, diagnostic):
    module = load_module()
    _stub_builder_commands(module, monkeypatch, diagnostic=diagnostic, stdout_diagnostic=stdout_diagnostic)
    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="sanitizer diagnostic"):
        module.build_evidence(out, 100)
    assert not list(out.rglob("RECEIPT.json"))
    assert not (out / "nic_dpu_packet_pipeline_latest.json").exists()


@pytest.mark.parametrize("summary", ["", "TESTS passed=6 failed=0\n", "TESTS passed=7 failed=1\n", "TESTS passed=7 failed=0\nTESTS passed=7 failed=0\n"])
def test_pipeline_cannot_publish_missing_mismatched_or_duplicate_sanitizer_summary(tmp_path, monkeypatch, summary):
    module = load_module()
    _stub_builder_commands(module, monkeypatch, summary=summary)
    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="sanitizer test summary"):
        module.build_evidence(out, 100)
    assert not list(out.rglob("RECEIPT.json"))
    assert not (out / "nic_dpu_packet_pipeline_latest.json").exists()


def test_pipeline_cannot_publish_if_sanitizer_controls_fail(tmp_path, monkeypatch):
    module = load_module()
    _stub_builder_commands(module, monkeypatch)

    def reject(compiler):
        raise RuntimeError("positive control did not detect deliberate fault")

    monkeypatch.setattr(module, "verify_sanitizer_toolchain", reject)
    out = tmp_path / "out"
    with pytest.raises(RuntimeError, match="positive control"):
        module.build_evidence(out, 100)
    assert not list(out.rglob("RECEIPT.json"))
    assert not (out / "nic_dpu_packet_pipeline_latest.json").exists()


def test_missing_explicit_sanitizer_compiler_is_not_replaced_by_another(tmp_path):
    module = load_module()
    with pytest.raises(RuntimeError, match="Sanitizer compiler must be an executable file"):
        module.detect_sanitizer_compiler(tmp_path / "missing")
