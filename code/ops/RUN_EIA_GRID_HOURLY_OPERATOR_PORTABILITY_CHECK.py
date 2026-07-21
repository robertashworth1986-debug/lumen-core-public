#!/usr/bin/env python3
"""Verify one frozen EIA packet across local Python runtimes.

This produces operator-controlled software-portability evidence. It cannot create
an independent reproduction receipt or change any scientific promotion gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import stat
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


VERIFIER_RELATIVE = Path(
    "code/ops/VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py"
)
RECEIPT_RELATIVE = Path("REVIEWER_RECEIPT_TEMPLATE.json")
EVALUATOR_RELATIVE = Path(
    "config/eia_grid_hourly_external_evaluator_protocol_template_v1.json"
)
EXPECTED_ZIP_SHA256_LENGTH = 64
RUNNER_REPOSITORY_PATH = (
    "code/ops/RUN_EIA_GRID_HOURLY_OPERATOR_PORTABILITY_CHECK.py"
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def validate_zip_members(archive: zipfile.ZipFile) -> None:
    for member in archive.infolist():
        normalized = member.filename.replace("\\", "/")
        relative = PurePosixPath(normalized)
        file_type = (member.external_attr >> 16) & 0o170000
        has_drive_prefix = bool(relative.parts and ":" in relative.parts[0])
        if relative.is_absolute() or has_drive_prefix or ".." in relative.parts:
            raise ValueError(f"unsafe ZIP member path: {member.filename}")
        if file_type == stat.S_IFLNK:
            raise ValueError(f"symbolic links are not allowed: {member.filename}")


def safe_extract(packet_zip: Path, destination: Path) -> Path:
    with zipfile.ZipFile(packet_zip) as archive:
        validate_zip_members(archive)
        archive.extractall(destination)

    if (destination / VERIFIER_RELATIVE).is_file():
        return destination
    children = [child for child in destination.iterdir() if child.is_dir()]
    if len(children) == 1 and (children[0] / VERIFIER_RELATIVE).is_file():
        return children[0]
    raise ValueError("extracted packet does not contain the expected verifier")


def subprocess_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONHASHSEED"] = "0"
    environment["TZ"] = "UTC"
    return environment


def run_json_command(command: list[str], cwd: Path) -> tuple[dict[str, Any], str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=subprocess_environment(),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(
            f"command failed with exit code {completed.returncode}: {detail}"
        )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("command did not emit one JSON document") from exc
    return payload, completed.stdout


def runtime_metadata(python_executable: Path) -> dict[str, Any]:
    probe = (
        "import json,platform,sys;"
        "print(json.dumps({'implementation':platform.python_implementation(),"
        "'version':platform.python_version(),'system':platform.system(),"
        "'release':platform.release(),'machine':platform.machine(),"
        "'isolated':bool(sys.flags.isolated)},sort_keys=True))"
    )
    payload, _ = run_json_command(
        [str(python_executable), "-I", "-B", "-c", probe],
        Path.cwd(),
    )
    return payload


def require_exact(payload: dict[str, Any], expected: dict[str, Any], name: str) -> None:
    mismatches = {
        key: {"expected": value, "observed": payload.get(key)}
        for key, value in expected.items()
        if payload.get(key) != value
    }
    if mismatches:
        raise ValueError(f"{name} verifier output mismatch: {mismatches}")


def run_verifier_modes(
    python_executable: Path,
    packet_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    verifier = packet_root / VERIFIER_RELATIVE
    base = [str(python_executable), "-I", "-B", str(verifier), "--packet-dir", "."]
    modes = {
        "packet": base,
        "blank_reviewer_receipt": base
        + ["--receipt", str(RECEIPT_RELATIVE), "--expect-template"],
        "blank_evaluator_protocol": base
        + [
            "--evaluator-protocol",
            str(EVALUATOR_RELATIVE),
            "--expect-evaluator-template",
        ],
    }
    outputs: dict[str, Any] = {}
    hashes: dict[str, str] = {}
    for name, command in modes.items():
        payload, stdout = run_json_command(command, packet_root)
        outputs[name] = payload
        hashes[name] = text_sha256(stdout)

    require_exact(
        outputs["packet"],
        {"packet_integrity_passed": True},
        "packet",
    )
    require_exact(
        outputs["blank_reviewer_receipt"],
        {
            "receipt_integrity_passed": True,
            "independent_reproduction_complete": False,
            "performance_promotion_allowed": False,
            "status": "UNSIGNED_INDEPENDENT_REPRODUCTION_TEMPLATE_VALID",
        },
        "blank reviewer receipt",
    )
    require_exact(
        outputs["blank_evaluator_protocol"],
        {
            "protocol_integrity_passed": True,
            "evaluation_design_frozen": False,
            "performance_promotion_allowed": False,
            "status": "UNSIGNED_EXTERNAL_EVALUATOR_PROTOCOL_TEMPLATE_VALID",
        },
        "blank evaluator protocol",
    )
    return outputs, hashes


def runtime_receipt(packet_zip: Path, python_executable: Path) -> dict[str, Any]:
    metadata = runtime_metadata(python_executable)
    with tempfile.TemporaryDirectory(prefix="eia_packet_portability_") as scratch:
        packet_root = safe_extract(packet_zip, Path(scratch))
        outputs, output_hashes = run_verifier_modes(python_executable, packet_root)

    packet_report = outputs["packet"]
    return {
        "runtime": metadata,
        "fresh_extraction": True,
        "checks": {
            "packet_integrity_passed": True,
            "blank_reviewer_receipt_integrity_passed": True,
            "blank_evaluator_protocol_integrity_passed": True,
            "independent_reproduction_complete": False,
            "performance_promotion_allowed": False,
        },
        "verifier_stdout_sha256": output_hashes,
        "packet_manifest_file_sha256": packet_report[
            "packet_manifest_file_sha256"
        ],
        "packet_manifest_payload_sha256": packet_report[
            "packet_manifest_payload_sha256"
        ],
        "snapshot_identity": {
            "protocol_id": packet_report["snapshot"]["protocol_id"],
            "prediction_count": packet_report["snapshot"]["prediction_count"],
            "settlement_count": packet_report["snapshot"]["settlement_count"],
            "common_settled_hour_count": packet_report["snapshot"][
                "common_settled_hour_count"
            ],
            "prediction_terminal_sha256": packet_report["snapshot"][
                "prediction_terminal_sha256"
            ],
            "settlement_terminal_sha256": packet_report["snapshot"][
                "settlement_terminal_sha256"
            ],
        },
    }


def run_portability_check(
    packet_zip: Path,
    python_executables: list[Path],
    expected_zip_sha256: str | None = None,
) -> dict[str, Any]:
    packet_zip = packet_zip.resolve()
    if not packet_zip.is_file():
        raise FileNotFoundError(packet_zip)
    if not python_executables:
        raise ValueError("at least one Python executable is required")

    zip_sha256 = file_sha256(packet_zip)
    if expected_zip_sha256:
        normalized = expected_zip_sha256.lower()
        if len(normalized) != EXPECTED_ZIP_SHA256_LENGTH or zip_sha256 != normalized:
            raise ValueError("packet ZIP SHA-256 does not match the expected value")

    runtimes = [runtime_receipt(packet_zip, path.resolve()) for path in python_executables]
    manifest_identities = {
        (
            item["packet_manifest_file_sha256"],
            item["packet_manifest_payload_sha256"],
        )
        for item in runtimes
    }
    snapshot_identities = {
        json.dumps(item["snapshot_identity"], sort_keys=True) for item in runtimes
    }
    if len(manifest_identities) != 1 or len(snapshot_identities) != 1:
        raise ValueError("runtime verifier outputs do not bind the same packet identity")

    distinct_versions = sorted({item["runtime"]["version"] for item in runtimes})
    manifest_file_sha256, manifest_payload_sha256 = next(iter(manifest_identities))
    cross_version = len(distinct_versions) >= 2
    return {
        "schema": "eia_grid_hourly_operator_portability_receipt.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": (
            "OPERATOR_CONTROLLED_CROSS_VERSION_CHECK_PASSED"
            if cross_version
            else "OPERATOR_CONTROLLED_SINGLE_RUNTIME_CHECK_PASSED"
        ),
        "operator_controlled": True,
        "reviewer_controlled": False,
        "independent_reproduction_complete": False,
        "external_validation_complete": False,
        "performance_promotion_allowed": False,
        "all_checks_passed": True,
        "cross_version_check_passed": cross_version,
        "fresh_extraction_per_runtime": True,
        "runner": {
            "path": RUNNER_REPOSITORY_PATH,
            "sha256": file_sha256(Path(__file__).resolve()),
            "isolated_python_mode": True,
            "network_required": False,
        },
        "packet": {
            "zip_file_name": packet_zip.name,
            "zip_bytes": packet_zip.stat().st_size,
            "zip_sha256": zip_sha256,
            "packet_manifest_file_sha256": manifest_file_sha256,
            "packet_manifest_payload_sha256": manifest_payload_sha256,
        },
        "runtime_version_count": len(distinct_versions),
        "runtime_versions": distinct_versions,
        "runs": runtimes,
        "claim_boundary": (
            "These same-host operator-controlled runs show that the frozen packet's "
            "standard-library verifier, blank receipt, and blank evaluator protocol "
            "execute consistently across the recorded Python versions. They are not "
            "independent reproduction, external validation, model refitting, field "
            "evidence, performance promotion, agency acceptance, or economic proof."
        ),
        "next_valid_state": (
            "A reviewer-controlled machine must rehash the packet, execute the verifier, "
            "and return independently retained receipt, independence, and signature "
            "artifacts."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-zip", required=True, type=Path)
    parser.add_argument(
        "--python-executable",
        action="append",
        required=True,
        type=Path,
        help="Repeat for each local Python runtime.",
    )
    parser.add_argument("--expected-zip-sha256")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = run_portability_check(
        args.packet_zip,
        args.python_executable,
        args.expected_zip_sha256,
    )
    write_json(args.output.resolve(), receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
