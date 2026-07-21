#!/usr/bin/env python3
"""Verify the reviewer runtime named by the bounded CODECHECK capsule."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_CONFIG = ROOT / "config" / "codecheck_reviewer_runtime_v1.json"
DEFAULT_OS_RELEASE = Path("/etc/os-release")


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def portable_text_sha256(path: Path) -> str:
    """Hash a UTF-8 text artifact with LF line endings on every platform."""
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _decode_os_release_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1]
    return (
        value.replace(r"\$", "$")
        .replace(r'\"', '"')
        .replace(r"\'", "'")
        .replace(r"\\", "\\")
    )


def read_os_release(path: Path = DEFAULT_OS_RELEASE) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key and key.replace("_", "").isalnum():
            values[key] = _decode_os_release_value(value)
    return values


def normalize_machine(value: str) -> str:
    normalized = value.strip().casefold()
    return "x86_64" if normalized in {"amd64", "x86_64"} else normalized


def normalize_libc_name(value: str) -> str:
    normalized = value.strip().casefold()
    return "glibc" if normalized in {"glibc", "libc"} else normalized


def safe_git(*args: str) -> dict[str, Any]:
    result = subprocess.run(
        [
            "git",
            "-c",
            f"safe.directory={ROOT.as_posix()}",
            "-C",
            str(ROOT),
            *args,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "available": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": result.stdout.strip() if result.returncode == 0 else "",
    }


def source_identity(
    config: dict[str, Any], *, declared_commit: str | None = None
) -> dict[str, Any]:
    rows = []
    relative_paths = [config["source"]["script_path"], config["source"]["config_path"]]
    for relative_path in relative_paths:
        path = ROOT / relative_path
        rows.append(
            {
                "path": relative_path,
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    status = safe_git("status", "--porcelain", "--", *relative_paths)
    commit = safe_git("rev-parse", "HEAD")
    porcelain = status["stdout"]
    return {
        "git_metadata_available": status["available"] and commit["available"],
        "repository_commit_observed": commit["stdout"] or None,
        "repository_commit_declared_by_operator": declared_commit,
        "relevant_source_clean_observed": (
            not bool(porcelain) if status["available"] else None
        ),
        "relevant_change_line_count": (
            len(porcelain.splitlines()) if status["available"] else None
        ),
        "files": rows,
        "source_chain_sha256": canonical_sha256(rows),
    }


def build_receipt(
    *,
    config_path: Path = DEFAULT_CONFIG,
    os_release_path: Path = DEFAULT_OS_RELEASE,
    generated_utc: str | None = None,
    declared_commit: str | None = None,
) -> dict[str, Any]:
    config = read_json(config_path)
    expected = config["expected"]
    os_release = read_os_release(os_release_path)
    libc_name, libc_version = platform.libc_ver()
    observed_environment = {
        key: os.environ.get(key, "") for key in expected["environment"]
    }
    observed = {
        "system": platform.system(),
        "machine": normalize_machine(platform.machine()),
        "python": platform.python_version(),
        "os_release": {
            "id": os_release.get("ID", ""),
            "version_id": os_release.get("VERSION_ID", ""),
        },
        "libc": {
            "name": normalize_libc_name(libc_name),
            "version": libc_version,
        },
        "environment": observed_environment,
    }
    lock_path = ROOT / expected["requirements_lock"]["path"]
    lock_hash = portable_text_sha256(lock_path) if lock_path.is_file() else ""
    checks = {
        "system": observed["system"].casefold() == expected["system"].casefold(),
        "machine": observed["machine"] == normalize_machine(expected["machine"]),
        "python": observed["python"] == expected["python"],
        "os_release_id": observed["os_release"]["id"].casefold()
        == expected["os_release"]["id"].casefold(),
        "os_release_version_id": observed["os_release"]["version_id"]
        == expected["os_release"]["version_id"],
        "libc_name": observed["libc"]["name"]
        == normalize_libc_name(expected["libc"]["name"]),
        "libc_version": observed["libc"]["version"]
        == expected["libc"]["version"],
        "deterministic_environment": observed_environment
        == expected["environment"],
        "requirements_lock_present": lock_path.is_file(),
        "requirements_lock_sha256": lock_hash
        == expected["requirements_lock"]["sha256"],
    }
    sources = source_identity(config, declared_commit=declared_commit)
    passed = all(checks.values())
    payload: dict[str, Any] = {
        "schema": "codecheck_reviewer_runtime_receipt.v1",
        "protocol_id": config["protocol_id"],
        "generated_utc": generated_utc
        or datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        "status": "AUTHORITATIVE_RUNTIME_PASS" if passed else "RUNTIME_MISMATCH",
        "passed": passed,
        "expected": expected,
        "observed": observed,
        "checks": checks,
        "requirements_lock_observed_sha256": lock_hash,
        "source": sources,
        "operator_controlled": True,
        "independent_execution_complete": False,
        "external_validation_complete": False,
        "claim_boundary": config["claim_boundary"],
    }
    payload["receipt_payload_sha256"] = canonical_sha256(payload)
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--os-release", type=Path, default=DEFAULT_OS_RELEASE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    receipt = build_receipt(
        config_path=args.config.resolve(),
        os_release_path=args.os_release.resolve(),
        declared_commit=args.source_commit,
    )
    if args.output and not args.check_only:
        write_json(args.output.resolve(), receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
