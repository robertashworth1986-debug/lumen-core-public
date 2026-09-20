from __future__ import annotations

import argparse
import hashlib
import json
import math
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
PROPERTY_SOURCE = SOURCE_DIR / "nic_dpu_packet_pipeline_property_test.c"
PROPERTY_PROTOCOL = ROOT / "config" / "nic_dpu_packet_pipeline_property_protocol_v1.json"
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
    PROPERTY_SOURCE,
    PROPERTY_PROTOCOL,
]
TEST_PATTERN = re.compile(r"^TESTS passed=(\d+) failed=(\d+)$", re.MULTILINE)
BENCH_PATTERN = re.compile(
    r"^BENCH packets=(\d+) elapsed_seconds=([0-9.]+) "
    r"packets_per_second=([0-9.]+) queued=(\d+)$", re.MULTILINE
)
PROPERTY_PATTERN = re.compile(
    r"^PROPERTY cases=(\d+) seed=(\d+) ok=(\d+) non_ipv4=(\d+) truncated=(\d+) malformed=(\d+) failed=(\d+)$",
    re.MULTILINE,
)
PINNED_ZIG_VERSION = "0.15.2"
SANITIZER_DIAGNOSTIC = re.compile(r"runtime error:|(?:ERROR|SUMMARY):[^\n]*(?:Address|UndefinedBehavior)Sanitizer", re.I)
SANITIZER_FLAGS = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O1", "-g",
                   "-fsanitize=address", "-fsanitize=undefined", "-fno-sanitize-recover=all"]
SANITIZER_CONTROLS = {
    "address": (
        "#include <stdlib.h>\nint main(int argc, char **argv) {\n"
        "volatile char *p = malloc(1); (void)argv; if (!p) return 2;\n"
        "p[argc + 3] = 'x'; free((void *)p); return 0; }\n",
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
                cwd=ROOT, capture_output=True, text=True, check=False, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0 and result.stdout.strip() == PINNED_ZIG_VERSION:
            return candidate
    raise RuntimeError(
        "No verified C toolchain found. Install the pinned workspace toolchain with "
        "`.venv\\Scripts\\python.exe -m pip install ziglang==0.15.2`."
    )


def run_checked(command: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
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
    configured = explicit or os.environ.get("LUMA_NIC_SANITIZER_CC") or shutil.which("clang")
    if not configured:
        raise RuntimeError("Sanitizer compiler unavailable; supply --sanitizer-cc or LUMA_NIC_SANITIZER_CC")
    compiler = Path(configured).resolve(strict=True)
    if not compiler.is_file():
        raise RuntimeError("Sanitizer compiler must be an executable file")
    return compiler


def sanitizer_environment(compiler: Path) -> dict[str, str]:
    return dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get("PATH", ""),
                ASAN_OPTIONS="halt_on_error=1:abort_on_error=0", UBSAN_OPTIONS="halt_on_error=1")


def verify_sanitizer_toolchain(compiler: Path, run_dir: Path) -> dict[str, Any]:
    """A success exit from the target cannot prove instrumentation is enabled."""
    environment = sanitizer_environment(compiler)
    version = run_checked([str(compiler), "--version"], ROOT, env=environment)
    identity = sha256_file(compiler)
    controls_dir = run_dir / "sanitizer_controls"
    controls_dir.mkdir()
    controls = {}
    with tempfile.TemporaryDirectory(prefix="lc_sanitizer_controls_") as temp_name:
        for kind, (body, marker) in SANITIZER_CONTROLS.items():
            source = controls_dir / f"{kind}_positive_control.c"
            source.write_text(body, encoding="utf-8")
            executable = Path(temp_name) / f"{kind}_positive_control.exe"
            compiled = run_checked([str(compiler), *SANITIZER_FLAGS, str(source), "-o", str(executable)],
                                   ROOT, env=environment)
            ran = subprocess.run([str(executable)], cwd=ROOT, env=environment,
                                 capture_output=True, text=True, timeout=30, check=False)
            (controls_dir / f"{kind}_compile.log").write_text(compiled.stdout + compiled.stderr, encoding="utf-8")
            (controls_dir / f"{kind}_run.log").write_text(ran.stdout + ran.stderr, encoding="utf-8")
            detected = ran.returncode != 0 and marker in ran.stderr
            controls[kind] = {
                "source_path": source.relative_to(run_dir).as_posix(),
                "source_sha256": sha256_file(source), "executable_sha256": sha256_file(executable),
                "compile_exit_code": compiled.returncode, "test_exit_code": ran.returncode,
                "expected_diagnostic": marker, "detected": detected,
            }
            if not detected:
                raise RuntimeError(f"sanitizer {kind} positive control did not detect its deliberate fault")
    if sha256_file(compiler) != identity:
        raise RuntimeError("sanitizer compiler changed during positive controls")
    return {"compiler_path": compiler.as_posix(), "compiler_file_sha256": identity,
            "compiler_version": version.stdout.strip(), "flags": SANITIZER_FLAGS,
            "positive_controls": controls,
            "identity_scope": "selected compiler executable and reported version; not a complete toolchain dependency attestation"}


def run_generated_properties(compiler: Path, run_dir: Path, frozen: dict[Path, Path], cases: int) -> dict[str, Any]:
    protocol = json.loads(frozen[PROPERTY_PROTOCOL].read_text(encoding="utf-8"))
    if sha256_file(frozen[PROPERTY_SOURCE]) != protocol["generator_source_sha256"]:
        raise RuntimeError("property generator does not match the frozen supplemental protocol")
    seed = int(protocol["seed"])
    environment = sanitizer_environment(compiler)
    with tempfile.TemporaryDirectory(prefix="lc_nic_properties_") as temp_name:
        executable = Path(temp_name) / "nic_dpu_packet_properties.exe"
        compiled = run_checked([str(compiler), *SANITIZER_FLAGS, str(frozen[SOURCES[1]]),
                                str(frozen[PROPERTY_SOURCE]), "-o", str(executable)], ROOT, env=environment)
        result = subprocess.run([str(executable), str(cases), str(seed)], cwd=run_dir, env=environment,
                                capture_output=True, text=True, timeout=120, check=False)
        (run_dir / "property_compile.log").write_text(compiled.stdout + compiled.stderr, encoding="utf-8")
        (run_dir / "property_run.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        binary_hash = sha256_file(executable)
    matches = PROPERTY_PATTERN.findall(result.stdout)
    if result.returncode != 0 or SANITIZER_DIAGNOSTIC.search(result.stdout + "\n" + result.stderr) or len(matches) != 1:
        raise RuntimeError("generated property execution failed; retain the run diagnostics")
    count, reported_seed, ok, non_ipv4, truncated, malformed, failed = map(int, matches[0])
    if count != cases or reported_seed != seed or failed != 0 or ok + non_ipv4 + truncated + malformed != cases:
        raise RuntimeError("generated property summary does not reconcile with the frozen request")
    return {"protocol_schema": protocol["schema"], "protocol_sha256": sha256_file(frozen[PROPERTY_PROTOCOL]),
            "generator_sha256": sha256_file(frozen[PROPERTY_SOURCE]), "executable_sha256": binary_hash,
            "cases": count, "seed": seed, "outcomes": {"ok": ok, "non_ipv4": non_ipv4,
            "truncated": truncated, "malformed": malformed}, "failed": failed, "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr, "coverage_guided_fuzzing": False,
            "interpretation": "generated input iterations under one frozen deterministic method; not independent tests, exhaustive coverage or hardware evidence"}


def freeze_package(run_dir: Path) -> tuple[dict[Path, Path], list[dict[str, Any]]]:
    """Retain the exact worktree bytes used for this run before compiling them."""
    frozen = {}
    entries = []
    for source in dict.fromkeys([*PACKAGE_PATHS, *SOURCES]):
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f"package input must be a regular file: {source.name}")
        relative = source.relative_to(ROOT)
        if source.stat().st_size > 16 * 1024 * 1024:
            raise RuntimeError("package input exceeds the 16 MiB file limit")
        body = source.read_bytes()
        if len(body) > 16 * 1024 * 1024:
            raise RuntimeError("package input exceeds the 16 MiB file limit")
        target = run_dir / "sources" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        frozen[source] = target
        entries.append({"path": relative.as_posix(), "frozen_path": target.relative_to(run_dir).as_posix(),
                        "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    return frozen, entries


def verify_frozen_package(run_dir: Path, entries: list[dict[str, Any]]) -> None:
    for row in entries:
        path = run_dir / row["frozen_path"]
        if path.stat().st_size != row["bytes"] or sha256_file(path) != row["sha256"]:
            raise RuntimeError("frozen compile/package input changed during the run")


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", delete=False) as temporary:
        temporary.write(source.read_bytes())
        staged = Path(temporary.name)
    try:
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)


def parse_test_output(stdout: str) -> tuple[dict[str, int], dict[str, Any]]:
    test_matches = list(TEST_PATTERN.finditer(stdout))
    bench_matches = list(BENCH_PATTERN.finditer(stdout))
    if len(test_matches) != 1 or len(bench_matches) != 1:
        raise RuntimeError(f"unexpected C test output:\n{stdout}")
    test_match, bench_match = test_matches[0], bench_matches[0]
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
    properties = receipt["verification"]["generated_properties"]
    property_text = (f"{properties['cases']} generated input iterations passed with seed {properties['seed']}; "
                     "the method is deterministic and is not coverage-guided fuzzing."
                     if properties else "The optional generated property supplement was not requested.")
    return f"""# NIC/DPU Packet-Pipeline Foundation Receipt

Generated: {receipt['generated_utc']}

## Verified

- The bounded reference implementation compiled as strict C11 with warnings treated as errors.
- {tests['passed']} deterministic parser and policy tests passed; {tests['failed']} failed.
- The same vector suite completed under AddressSanitizer and UndefinedBehaviorSanitizer.
- The implementation is allocation-free and uses a fixed rule table and counters.
- Source and protocol files are SHA-256 identified in the receipt and run manifest.
- Compilation used the retained run snapshot. Source edits made after that snapshot are not substituted into this receipt.
- The pinned Zig version, matching sanitizer test summary and absence of sanitizer diagnostics were checked before publication.
- A separately identified sanitizer compiler detected deliberate heap-overflow and signed-overflow faults before testing the pipeline with identical sanitizer flags.
- {property_text}

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

1. Extend generated property testing with coverage-guided fuzzing and IPv6 before broad parser claims.
2. Port the same policy contract to an isolated XDP/eBPF or DPDK harness.
3. Measure on named NIC hardware with a frozen traffic protocol and loss/latency metrics.
4. Port to a named DPU SDK and preserve host-versus-offload parity receipts.
5. Seek independent review before using expert, production, or hardware-performance language.
"""


def mirror_package(
    out_root: Path,
    run_dir: Path,
    destinations: list[Path],
    frozen: dict[Path, Path],
) -> dict[str, Any]:
    generated_paths = [
        out_root / "nic_dpu_packet_pipeline_latest.json",
        out_root / "nic_dpu_packet_pipeline_latest.md",
        *sorted(path for path in run_dir.rglob("*") if path.is_file()),
    ]
    package_paths = [(frozen[path], path.relative_to(ROOT)) for path in PACKAGE_PATHS]
    for path in generated_paths:
        try:
            package_path = path.relative_to(ROOT)
        except ValueError:
            package_path = Path("generated") / path.relative_to(out_root)
        package_paths.append((path, package_path))
    artifacts = []
    for path, package_path in package_paths:
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
        for (source, _package_path), artifact in zip(package_paths, artifacts, strict=True):
            target = destination / artifact["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_copy(source, target)
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
        atomic_copy(receipt_path, target)
        if sha256_file(target) != sha256_file(receipt_path):
            raise RuntimeError(f"mirror receipt hash mismatch: {target}")
    return receipt


def build_evidence(
    out_root: Path,
    benchmark_packets: int,
    mirror_destinations: list[Path] | None = None,
    sanitizer_cc: Path | None = None,
    property_cases: int = 0,
) -> dict[str, Any]:
    if type(benchmark_packets) is not int or not 1 <= benchmark_packets <= 10_000_000:
        raise ValueError("benchmark_packets must be an integer between 1 and 10000000")
    if type(property_cases) is not int or not 0 <= property_cases <= 10_000_000:
        raise ValueError("property_cases must be an integer between 0 and 10000000")
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
    frozen, package_entries = freeze_package(run_dir)
    protocol = json.loads(frozen[SOURCES[-1]].read_text(encoding="utf-8"))
    sanitizer_toolchain = verify_sanitizer_toolchain(sanitizer_compiler, run_dir)
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
            str(frozen[SOURCES[1]]),
            str(frozen[SOURCES[2]]),
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
            str(frozen[SOURCES[1]]),
            str(frozen[SOURCES[2]]),
            "-o",
            str(sanitized_executable),
        ]
        sanitizer_compile_result = run_checked(sanitizer_command, ROOT, env=sanitizer_env)
        sanitizer_test_result = run_checked([str(sanitized_executable)], ROOT, env=sanitizer_env)
        if SANITIZER_DIAGNOSTIC.search(sanitizer_test_result.stdout + "\n" + sanitizer_test_result.stderr):
            raise RuntimeError("sanitizer diagnostic prevents a successful evidence receipt")

    tests, benchmark = parse_test_output(test_result.stdout)
    if tests["passed"] < int(protocol["acceptance_gates"]["minimum_deterministic_tests"]):
        raise RuntimeError("C test count did not meet the frozen minimum")
    sanitizer_summaries = TEST_PATTERN.findall(sanitizer_test_result.stdout)
    if sanitizer_summaries != [(str(tests["passed"]), str(tests["failed"]))]:
        raise RuntimeError("sanitizer test summary must match the deterministic vector suite")
    if (tests["failed"] != 0 or benchmark["queued"] != benchmark["packets"]
            or benchmark["packets"] != benchmark_packets
            or not math.isfinite(benchmark["elapsed_seconds"]) or benchmark["elapsed_seconds"] < 0
            or not math.isfinite(benchmark["packets_per_second"]) or benchmark["packets_per_second"] < 0):
        raise RuntimeError("C verification output failed a frozen invariant")

    generated_properties = (run_generated_properties(sanitizer_compiler, run_dir, frozen, property_cases)
                            if property_cases else None)
    verify_frozen_package(run_dir, package_entries)
    if sha256_file(sanitizer_compiler) != sanitizer_toolchain["compiler_file_sha256"]:
        raise RuntimeError("sanitizer compiler changed during pipeline verification")
    source_receipts = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "frozen_path": frozen[path].relative_to(run_dir).as_posix(),
            "bytes": frozen[path].stat().st_size,
            "sha256": sha256_file(frozen[path]),
        }
        for path in SOURCES
    ]
    receipt: dict[str, Any] = {
        "schema": "lumencore.nic_dpu_packet_pipeline_evidence.v2",
        "version": "2.0.0",
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
        "frozen_package": package_entries,
        "source_identity_scope": "retained worktree input bytes compiled from the run snapshot; no clean Git or authorship claim",
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
                "test_exit_code": sanitizer_test_result.returncode,
                "test_stdout": sanitizer_test_result.stdout,
                "test_stderr": sanitizer_test_result.stderr,
            },
            "benchmark": benchmark,
            "generated_properties": generated_properties,
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
                "path": path.relative_to(run_dir).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in sorted(path for path in run_dir.rglob("*") if path.is_file())
        ],
    }
    manifest["entry_count"] = len(manifest["entries"])
    (run_dir / "SHA256_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    atomic_copy(report_path, out_root / "nic_dpu_packet_pipeline_latest.md")
    atomic_copy(receipt_path, out_root / "nic_dpu_packet_pipeline_latest.json")
    mirror_receipt = None
    if mirror_destinations:
        mirror_receipt = mirror_package(out_root, run_dir, mirror_destinations, frozen)
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
    parser.add_argument("--sanitizer-cc", type=Path, help="Compiler with ASAN/UBSAN runtimes; deliberate-fault controls must pass.")
    parser.add_argument("--property-cases", type=int, default=0, help="Optional deterministic generated cases, up to 10000000; reference run uses 500000.")
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
        property_cases=args.property_cases,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
