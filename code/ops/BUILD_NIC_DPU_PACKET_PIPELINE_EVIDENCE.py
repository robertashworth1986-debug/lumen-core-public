from __future__ import annotations

import argparse
import hashlib
import json
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
    ROOT / "config" / "hybrid_agent_capability_registry_v1.json",
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
        result = subprocess.run(
            [str(candidate), "-m", "ziglang", "version"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return candidate
    raise RuntimeError(
        "No verified C toolchain found. Install the pinned workspace toolchain with "
        "`.venv\\Scripts\\python.exe -m pip install ziglang==0.15.2`."
    )


def run_checked(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "command failed\n"
            f"command: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


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
) -> dict[str, Any]:
    protocol = json.loads(SOURCES[-1].read_text(encoding="utf-8"))
    python_executable = detect_zig_python()
    version_result = run_checked(
        [str(python_executable), "-m", "ziglang", "version"], ROOT
    )
    compiler_result = run_checked(
        [str(python_executable), "-m", "ziglang", "cc", "--version"], ROOT
    )
    generated = datetime.now(timezone.utc)
    run_id = generated.strftime("run_%Y%m%dT%H%M%SZ")
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

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
            str(python_executable),
            "-m",
            "ziglang",
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic",
            "-O1",
            "-g",
            "-fsanitize=address,undefined",
            str(SOURCES[1]),
            str(SOURCES[2]),
            "-o",
            str(sanitized_executable),
        ]
        sanitizer_compile_result = run_checked(sanitizer_command, ROOT)
        sanitizer_test_result = run_checked([str(sanitized_executable)], ROOT)

    tests, benchmark = parse_test_output(test_result.stdout)
    if tests["passed"] < int(protocol["acceptance_gates"]["minimum_deterministic_tests"]):
        raise RuntimeError("C test count did not meet the frozen minimum")
    if tests["failed"] != 0 or benchmark["queued"] != benchmark["packets"]:
        raise RuntimeError("C verification output failed a frozen invariant")

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
                "address_sanitizer": True,
                "undefined_behavior_sanitizer": True,
                "compile_exit_code": sanitizer_compile_result.returncode,
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
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
