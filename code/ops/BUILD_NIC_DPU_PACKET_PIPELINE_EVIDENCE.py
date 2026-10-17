from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "code" / "hardware"
SOURCES = [
    SOURCE_DIR / "nic_dpu_packet_pipeline.h",
    SOURCE_DIR / "nic_dpu_packet_pipeline.c",
    SOURCE_DIR / "nic_dpu_packet_pipeline_test.c",
    ROOT / "config" / "nic_dpu_packet_pipeline_protocol_v1.json",
]
DEFAULT_OUT = ROOT / "out" / "hardware" / "nic_dpu_packet_pipeline"
DEFAULT_MIRROR_DESTINATIONS = (
    Path("E:/LumaProofVault/CAPABILITIES/NIC_DPU_PACKET_PIPELINE_V1"),
    Path("E:/LumenCoreSync/capabilities/nic_dpu_packet_pipeline_v1"),
    Path("E:/INSTITUTIONAL_STACK_V2/evidence/capabilities/nic_dpu_packet_pipeline_v1"),
)
PACKAGE_PATHS = [
    ROOT / "README.md",
    ROOT / "code" / "ops" / "BUILD_NIC_DPU_PACKET_PIPELINE_EVIDENCE.py",
    ROOT / "tests" / "test_nic_dpu_packet_pipeline.py",
    ROOT / "docs" / "NIC_DPU_PACKET_PIPELINE_FOUNDATION_2026-08-17.md",
    *SOURCES,
]
TEST_PATTERN = re.compile(r"TESTS passed=(\d+) failed=(\d+)")
BENCH_PATTERN = re.compile(
    r"BENCH packets=(\d+) elapsed_seconds=([0-9.]+) "
    r"packets_per_second=([0-9.]+) queued=(\d+)"
)
PINNED_ZIG_VERSION = "0.15.2"
SANITIZER_FLAGS = [
    "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O1", "-g",
    "-fsanitize=address", "-fsanitize=undefined", "-fno-sanitize-recover=all",
]
SANITIZER_DIAGNOSTIC = re.compile(
    r"runtime error:|AddressSanitizer:|UndefinedBehaviorSanitizer:", re.IGNORECASE
)
SANITIZER_CONTROLS = {
    "address": (
        "#include <stdlib.h>\n#include <stdint.h>\n"
        "int main(int argc, char **argv) {\n"
        "char *p = malloc(1); (void)argv; if (!p) return 2;\n"
        # Prevent UBSan object-size inference from preempting the ASan check.
        "volatile uintptr_t address = (uintptr_t)p; volatile char *access = (char *)address;\n"
        "access[argc + 3] = 'x'; free(p); return 0; }\n",
        "AddressSanitizer: heap-buffer-overflow",
    ),
    "undefined": (
        "#include <limits.h>\nint main(int argc, char **argv) {\n"
        "volatile int value = INT_MAX; (void)argv; return value + argc; }\n",
        "runtime error: signed integer overflow",
    ),
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_zig_python() -> Path:
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            result = subprocess.run(
                [str(candidate), "-m", "ziglang", "version"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0 and result.stdout.strip() == PINNED_ZIG_VERSION:
            return candidate
    raise RuntimeError(
        f"No verified C toolchain found; exact Zig {PINNED_ZIG_VERSION} is required. "
        "Install the pinned workspace toolchain with "
        "`.venv\\Scripts\\python.exe -m pip install ziglang==0.15.2`."
    )


def run_checked(
    command: list[str], cwd: Path, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "command failed\n"
            f"command: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def detect_sanitizer_compiler(explicit: Path | None = None) -> Path:
    configured = (
        explicit or os.environ.get("LUMA_NIC_SANITIZER_CC")
        or shutil.which("clang") or shutil.which("gcc")
    )
    if not configured:
        raise RuntimeError("Sanitizer compiler unavailable; supply --sanitizer-cc")
    try:
        compiler = Path(shutil.which(str(configured)) or configured).resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("Sanitizer compiler must be an executable file") from exc
    if not compiler.is_file() or not os.access(compiler, os.X_OK):
        raise RuntimeError("Sanitizer compiler must be an executable file")
    return compiler


def sanitizer_environment(compiler: Path) -> dict[str, str]:
    return dict(
        os.environ,
        PATH=str(compiler.parent) + os.pathsep + os.environ.get("PATH", ""),
        ASAN_OPTIONS="halt_on_error=1:abort_on_error=0",
        UBSAN_OPTIONS="halt_on_error=1",
    )


def verify_sanitizer_toolchain(compiler: Path) -> dict[str, Any]:
    """Require each sanitizer to diagnose its deliberate fault, not just a crash."""
    environment = sanitizer_environment(compiler)
    identity = sha256_file(compiler)
    version = run_checked([str(compiler), "--version"], ROOT, env=environment)
    controls = {}
    with tempfile.TemporaryDirectory(prefix="lc_sanitizer_controls_") as temp_name:
        for kind, (body, marker) in SANITIZER_CONTROLS.items():
            source = Path(temp_name) / f"{kind}_control.c"
            executable = Path(temp_name) / f"{kind}_control.exe"
            source.write_text(body, encoding="utf-8", newline="\n")
            compiled = run_checked(
                [str(compiler), *SANITIZER_FLAGS, str(source), "-o", str(executable)],
                ROOT, env=environment,
            )
            ran = subprocess.run(
                [str(executable)], cwd=ROOT, env=environment,
                capture_output=True, text=True, check=False, timeout=30,
            )
            detected = ran.returncode != 0 and marker in ran.stderr
            controls[kind] = {
                "source": body,
                "source_sha256": sha256_file(source),
                "executable_sha256": sha256_file(executable),
                "compile_exit_code": compiled.returncode,
                "compile_stdout": compiled.stdout,
                "compile_stderr": compiled.stderr,
                "test_exit_code": ran.returncode,
                "test_stdout": ran.stdout,
                "test_stderr": ran.stderr,
                "expected_diagnostic": marker,
                "detected": detected,
            }
            if not detected:
                raise RuntimeError(
                    f"sanitizer {kind} positive control did not detect its deliberate fault; "
                    f"exit={ran.returncode}\n{ran.stderr}"
                )
    if sha256_file(compiler) != identity:
        raise RuntimeError("sanitizer compiler changed during positive controls")
    return {
        "compiler_path": compiler.as_posix(),
        "compiler_file_sha256": identity,
        "compiler_version": version.stdout.strip(),
        "flags": SANITIZER_FLAGS,
        "runtime_options": {
            name: environment.get(name, "")
            for name in ("ASAN_OPTIONS", "UBSAN_OPTIONS", "LSAN_OPTIONS")
        },
        "positive_controls": controls,
        "scope": "this separately identified compiler and observed sanitizer controls only",
    }


def parse_test_output(stdout: str) -> tuple[dict[str, int], dict[str, Any]]:
    test_match = TEST_PATTERN.search(stdout)
    bench_match = BENCH_PATTERN.search(stdout)
    if test_match is None or bench_match is None:
        raise RuntimeError(f"unexpected C test output:\n{stdout}")
    tests = {
        "passed": int(test_match.group(1)),
        "failed": int(test_match.group(2)),
    }
    benchmark = {
        "packets": int(bench_match.group(1)),
        "elapsed_seconds": float(bench_match.group(2)),
        "packets_per_second": float(bench_match.group(3)),
        "queued": int(bench_match.group(4)),
        "interpretation": "informative host-user-space measurement only",
        "promotion_gate": False,
    }
    return tests, benchmark


def build_report(receipt: dict[str, Any]) -> str:
    tests = receipt["verification"]["tests"]
    benchmark = receipt["verification"]["benchmark"]
    return f"""# NIC/DPU Packet-Pipeline Foundation Receipt

Generated: {receipt['generated_utc']}

## Verified

- The bounded reference implementation compiled as strict C11 with warnings treated as errors.
- {tests['passed']} deterministic parser and policy tests passed; {tests['failed']} failed.
- The same vector suite completed under AddressSanitizer and UndefinedBehaviorSanitizer.
- Both sanitizers detected their deliberate-fault controls under the same flags before the vector run; the separately identified sanitizer compiler is recorded in the receipt.
- The implementation is allocation-free and uses a fixed rule table and counters.
- Source and protocol files are SHA-256 identified in the receipt and run manifest.

## Informative Host Measurement

- Packets processed: {benchmark['packets']}
- Measured packets per second: {benchmark['packets_per_second']:.3f}
- Interpretation: {benchmark['interpretation']}.

The timing is not a NIC, DPU, line-rate, production-latency, or cross-machine claim.

## Not Verified

- DPDK, XDP/eBPF, RDMA/RoCE, GPUDirect, NIC firmware, or DPU offload.
- NVIDIA BlueField hardware or DOCA SDK behavior.
- Production security, line-rate capacity, operational reliability, or expert certification.

## Next Evidence Gates

1. Add property/fuzz testing and IPv6 before broad parser claims.
2. Port the same policy contract to an isolated XDP/eBPF or DPDK harness.
3. Measure on named NIC hardware with a frozen traffic protocol and loss/latency metrics.
4. Port to a named DPU SDK and preserve host-versus-offload parity receipts.
5. Seek independent review before using expert, production, or hardware-performance language.
"""


def mirror_package(
    out_root: Path,
    run_dir: Path,
    destinations: list[Path],
) -> dict[str, Any]:
    generated_paths = [
        out_root / "nic_dpu_packet_pipeline_latest.json",
        out_root / "nic_dpu_packet_pipeline_latest.md",
        run_dir / "SHA256_MANIFEST.json",
    ]
    package_paths = [*PACKAGE_PATHS, *generated_paths]
    artifacts = []
    for path in package_paths:
        try:
            package_path = path.relative_to(ROOT)
        except ValueError:
            package_path = Path("generated") / path.relative_to(out_root)
        artifacts.append(
            {
                "path": package_path.as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    destination_rows: list[dict[str, Any]] = []
    for destination in destinations:
        destination.mkdir(parents=True, exist_ok=True)
        copied = 0
        for source, artifact in zip(package_paths, artifacts, strict=True):
            target = destination / artifact["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if sha256_file(target) != artifact["sha256"]:
                raise RuntimeError(f"mirror hash mismatch: {target}")
            copied += 1
        destination_rows.append(
            {
                "root": destination.as_posix(),
                "copied_artifact_count": copied,
                "all_hashes_verified": True,
            }
        )
    receipt = {
        "schema": "lumencore.nic_dpu_packet_pipeline_mirror_receipt.v1",
        "generated_utc": now_utc(),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "destinations": destination_rows,
        "claim_boundary": (
            "Mirror integrity is custody evidence only; it is not publication, "
            "hardware validation, production readiness, or expert certification."
        ),
    }
    receipt_path = out_root / "nic_dpu_packet_pipeline_mirror_latest.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for destination in destinations:
        target = destination / "MIRROR_RECEIPT.json"
        shutil.copy2(receipt_path, target)
        if sha256_file(target) != sha256_file(receipt_path):
            raise RuntimeError(f"mirror receipt hash mismatch: {target}")
    return receipt


def build_evidence(
    out_root: Path,
    benchmark_packets: int,
    mirror_destinations: list[Path] | None = None,
    sanitizer_cc: Path | None = None,
) -> dict[str, Any]:
    protocol = json.loads(SOURCES[-1].read_text(encoding="utf-8"))
    python_executable = detect_zig_python()
    sanitizer_compiler = detect_sanitizer_compiler(sanitizer_cc)
    version_result = run_checked(
        [str(python_executable), "-m", "ziglang", "version"], ROOT
    )
    if version_result.stdout.strip() != PINNED_ZIG_VERSION:
        raise RuntimeError("C toolchain version changed after detection")
    compiler_result = run_checked(
        [str(python_executable), "-m", "ziglang", "cc", "--version"], ROOT
    )
    generated = datetime.now(timezone.utc)
    run_id = generated.strftime("run_%Y%m%dT%H%M%SZ")
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    sanitizer_toolchain = verify_sanitizer_toolchain(sanitizer_compiler)
    sanitizer_env = sanitizer_environment(sanitizer_compiler)

    with tempfile.TemporaryDirectory(prefix="lc_nic_dpu_") as temp_name:
        executable = Path(temp_name) / "nic_dpu_packet_pipeline_test.exe"
        sanitized_executable = Path(temp_name) / "nic_dpu_packet_pipeline_sanitized.exe"
        compile_command = [
            str(python_executable),
            "-m",
            "ziglang",
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-O2",
            str(SOURCES[1]),
            str(SOURCES[2]),
            "-o",
            str(executable),
        ]
        compile_result = run_checked(compile_command, ROOT)
        test_result = run_checked(
            [str(executable), "--benchmark", str(benchmark_packets)], ROOT
        )
        sanitizer_command = [
            str(sanitizer_compiler),
            *SANITIZER_FLAGS,
            str(SOURCES[1]),
            str(SOURCES[2]),
            "-o",
            str(sanitized_executable),
        ]
        sanitizer_compile_result = run_checked(sanitizer_command, ROOT, env=sanitizer_env)
        sanitizer_test_result = run_checked([str(sanitized_executable)], ROOT, env=sanitizer_env)
        if SANITIZER_DIAGNOSTIC.search(
            sanitizer_test_result.stdout + "\n" + sanitizer_test_result.stderr
        ):
            raise RuntimeError("sanitizer diagnostic prevents a successful evidence receipt")

    tests, benchmark = parse_test_output(test_result.stdout)
    if tests["passed"] < int(protocol["acceptance_gates"]["minimum_deterministic_tests"]):
        raise RuntimeError("C test count did not meet the frozen minimum")
    if tests["failed"] != 0 or benchmark["queued"] != benchmark["packets"]:
        raise RuntimeError("C verification output failed a frozen invariant")
    sanitizer_summaries = re.findall(
        r"^TESTS passed=(\d+) failed=(\d+)$", sanitizer_test_result.stdout, re.MULTILINE
    )
    if sanitizer_summaries != [(str(tests["passed"]), str(tests["failed"]))]:
        raise RuntimeError("sanitizer test summary must match the deterministic vector suite")
    if sha256_file(sanitizer_compiler) != sanitizer_toolchain["compiler_file_sha256"]:
        raise RuntimeError("sanitizer compiler changed during pipeline verification")

    source_receipts = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in SOURCES
    ]
    receipt: dict[str, Any] = {
        "schema": "lumencore.nic_dpu_packet_pipeline_evidence.v1",
        "version": "1.0.0",
        "run_id": run_id,
        "generated_utc": generated.isoformat(),
        "protocol": {
            "schema": protocol["schema"],
            "version": protocol["version"],
            "sha256": source_receipts[-1]["sha256"],
        },
        "toolchain": {
            "provider": "ziglang Python wheel",
            "zig_version": version_result.stdout.strip(),
            "compiler_version": compiler_result.stdout.splitlines()[0].strip(),
            "compile_flags": [
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                "-O2",
            ],
        },
        "sources": source_receipts,
        "verification": {
            "compile_exit_code": compile_result.returncode,
            "compile_stdout": compile_result.stdout,
            "compile_stderr": compile_result.stderr,
            "tests": tests,
            "test_stdout": test_result.stdout,
            "sanitizers": {
                "address_sanitizer": sanitizer_toolchain["positive_controls"]["address"]["detected"],
                "undefined_behavior_sanitizer": sanitizer_toolchain["positive_controls"]["undefined"]["detected"],
                "toolchain": sanitizer_toolchain,
                "recover_on_error": False,
                "diagnostic_scan_passed": True,
                "compile_exit_code": sanitizer_compile_result.returncode,
                "compile_stdout": sanitizer_compile_result.stdout,
                "compile_stderr": sanitizer_compile_result.stderr,
                "test_exit_code": sanitizer_test_result.returncode,
                "test_stdout": sanitizer_test_result.stdout,
                "test_stderr": sanitizer_test_result.stderr,
            },
            "benchmark": benchmark,
        },
        "claim_gates": {
            "bounded_c11_packet_pipeline_implemented_and_tested": True,
            "host_user_space_reference_only": True,
            "deep_c_expertise": False,
            "nic_expertise": False,
            "dpu_expertise": False,
            "dpdk_or_xdp_validation": False,
            "rdma_or_roce_validation": False,
            "nic_or_dpu_hardware_offload": False,
            "production_readiness": False,
        },
    }
    receipt_path = run_dir / "RECEIPT.json"
    report_path = run_dir / "REPORT.md"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(build_report(receipt), encoding="utf-8")

    manifest = {
        "schema": "lumencore.sha256_manifest.v1",
        "generated_utc": now_utc(),
        "entries": [
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in (receipt_path, report_path)
        ],
    }
    manifest["entry_count"] = len(manifest["entries"])
    (run_dir / "SHA256_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    shutil.copy2(receipt_path, out_root / "nic_dpu_packet_pipeline_latest.json")
    shutil.copy2(report_path, out_root / "nic_dpu_packet_pipeline_latest.md")
    mirror_receipt = None
    if mirror_destinations:
        mirror_receipt = mirror_package(out_root, run_dir, mirror_destinations)
    return {
        "run_dir": str(run_dir),
        "receipt": receipt,
        "mirror_receipt": mirror_receipt,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile, test, and seal the bounded C NIC/DPU reference pipeline."
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--benchmark-packets", type=int, default=250_000)
    parser.add_argument("--sanitizer-cc", type=Path, help="Compiler whose ASan/UBSan positive controls must pass")
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="Copy the bounded package to the three established E-drive mirrors.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.benchmark_packets < 1:
        raise ValueError("--benchmark-packets must be positive")
    mirror_destinations = list(DEFAULT_MIRROR_DESTINATIONS) if args.mirror else None
    result = build_evidence(
        args.out.resolve(),
        args.benchmark_packets,
        mirror_destinations=mirror_destinations,
        sanitizer_cc=args.sanitizer_cc,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
