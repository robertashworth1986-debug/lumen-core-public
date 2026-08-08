#!/usr/bin/env python3
"""Run the canonical public LumenCore assurance checks and emit one receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

SCHEMA = "lumencore.public_assurance_suite.v1"
VERSION = "1.0.0"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_CAPTURE_BYTES = 1_048_576
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")

DEFAULT_CHECKS: tuple[dict[str, Any], ...] = (
    {
        "check_id": "proof_capsule_v3",
        "command": (
            "{python}",
            "code/proof_capsule_verifier.py",
            "examples/proof_capsule/dice_eia_public_capsule.json",
            "--root",
            ".",
        ),
        "sources": (
            "code/proof_capsule_verifier.py",
            "examples/proof_capsule/dice_eia_public_capsule.json",
            "examples/proof_capsule/dice_eia_public_summary.txt",
        ),
        "expected": {
            "valid": True,
            "receipt_schema": "proof-capsule-receipt-v3",
            "verifier_version": "3.0",
            "verification_scope": "capsule-schema-and-custody",
            "capsule_schema_version": "3.0",
            "capsule_file_custody_complete": True,
            "declared_evidence_type": "replay",
            "run_type": "replay",
            "declared_external_validation_status": "not_established",
            "external_report_manifest_bound": False,
            "external_validator_identity_evaluated": False,
            "external_validator_independence_evaluated": False,
            "external_validation_conclusion_evaluated": False,
            "pilot_decision": "external_review",
            "release_authorization_evaluated": False,
            "human_unlock_required": True,
        },
    },
    {
        "check_id": "external_replication_docket_v1",
        "command": (
            "{python}",
            "code/ops/validate_external_replication_docket.py",
            "config/external_replication_docket_v1.json",
        ),
        "sources": (
            "code/ops/validate_external_replication_docket.py",
            "config/external_replication_docket_v1.json",
        ),
        "expected": {
            "valid": True,
            "schema": "lumencore.external_replication_docket.v1",
            "status": "template_unassigned",
            "decision": "hold",
            "safe_for_external_validation_claim": False,
        },
    },
)


class AssuranceError(ValueError):
    """Raised when the public assurance suite fails closed."""


def _canonical_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw:
        raise AssuranceError("source path must be a non-empty string")
    if "\\" in raw or WINDOWS_DRIVE_RE.match(raw) or raw.startswith("//"):
        raise AssuranceError(f"source path must be repository-relative POSIX: {raw}")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or not pure.parts or any(
        part in {"", ".", ".."} for part in pure.parts
    ):
        raise AssuranceError(f"source path is not canonical: {raw}")
    normalized = pure.as_posix()
    if normalized != raw:
        raise AssuranceError(f"source path is not canonical: {raw}")
    return normalized


def _resolve_under_root(root: Path, raw: str) -> Path:
    canonical = _canonical_path(raw)
    root_resolved = root.resolve()
    path = (root_resolved / Path(*PurePosixPath(canonical).parts)).resolve()
    if path != root_resolved and root_resolved not in path.parents:
        raise AssuranceError(f"source path escapes root: {raw}")
    return path


def _sha256_file(path: Path) -> tuple[str, int]:
    if not path.is_file():
        raise AssuranceError(f"required source file is missing: {path}")
    digest = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            total += len(block)
            digest.update(block)
    return digest.hexdigest(), total


def _strict_json(text: str, *, context: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise AssuranceError(
                    f"{context} contains duplicate JSON key: {key}"
                )
            output[key] = value
        return output

    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda token: (_ for _ in ()).throw(
                AssuranceError(
                    f"{context} contains non-finite value: {token}"
                )
            ),
        )
    except json.JSONDecodeError as exc:
        raise AssuranceError(f"{context} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AssuranceError(f"{context} root must be an object")
    return value


def _bounded_text(value: str, *, context: str) -> str:
    encoded = value.encode("utf-8", errors="replace")
    if len(encoded) > MAX_CAPTURE_BYTES:
        raise AssuranceError(f"{context} exceeds {MAX_CAPTURE_BYTES} bytes")
    return value


def _public_environment() -> dict[str, str]:
    allowed = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"}
    }
    allowed.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "TZ": "UTC",
        }
    )
    return allowed


def _normalize_command(command: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for item in command:
        if not isinstance(item, str) or not item:
            raise AssuranceError(
                "check command entries must be non-empty strings"
            )
        normalized.append(sys.executable if item == "{python}" else item)
    return normalized


def _check_id(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"[a-z][a-z0-9_]{2,63}", value
    ):
        raise AssuranceError(f"invalid check_id: {value!r}")
    return value


def run_check(
    root: Path,
    spec: Mapping[str, Any],
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    check_id = _check_id(spec.get("check_id"))
    raw_command = spec.get("command")
    raw_sources = spec.get("sources")
    expected = spec.get("expected")
    if not isinstance(raw_command, (tuple, list)) or not raw_command:
        raise AssuranceError(f"{check_id}.command must be a non-empty array")
    if not isinstance(raw_sources, (tuple, list)) or not raw_sources:
        raise AssuranceError(f"{check_id}.sources must be a non-empty array")
    if not isinstance(expected, dict) or not expected:
        raise AssuranceError(f"{check_id}.expected must be a non-empty object")

    source_receipts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in raw_sources:
        canonical = _canonical_path(raw)
        if canonical.casefold() in seen:
            raise AssuranceError(
                f"{check_id} contains duplicate source path: {canonical}"
            )
        seen.add(canonical.casefold())
        digest, byte_count = _sha256_file(
            _resolve_under_root(root, canonical)
        )
        source_receipts.append(
            {"path": canonical, "sha256": digest, "bytes": byte_count}
        )

    command = _normalize_command(raw_command)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=_public_environment(),
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssuranceError(
            f"{check_id} exceeded timeout of {timeout_seconds} seconds"
        ) from exc
    duration_ms = round((time.monotonic() - started) * 1000)
    stdout = _bounded_text(
        completed.stdout, context=f"{check_id}.stdout"
    )
    stderr = _bounded_text(
        completed.stderr, context=f"{check_id}.stderr"
    )
    if completed.returncode != 0:
        safe_error = stderr.strip() or stdout.strip() or "no diagnostic output"
        raise AssuranceError(
            f"{check_id} exited {completed.returncode}: {safe_error[:1000]}"
        )
    result = _strict_json(stdout, context=f"{check_id}.stdout")
    mismatches = {
        key: {"expected": expected_value, "observed": result.get(key)}
        for key, expected_value in expected.items()
        if result.get(key) != expected_value
    }
    if mismatches:
        raise AssuranceError(
            f"{check_id} result contract mismatch: "
            + json.dumps(mismatches, sort_keys=True)
        )
    result_digest = hashlib.sha256(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "check_id": check_id,
        "valid": True,
        "duration_ms": duration_ms,
        "result_sha256": result_digest,
        "expected_contract": expected,
        "public_result": result,
        "source_files": source_receipts,
    }


def run_suite(
    root: Path,
    *,
    commit: str = "unknown",
    checks: Sequence[Mapping[str, Any]] = DEFAULT_CHECKS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if timeout_seconds < 1:
        raise AssuranceError("timeout_seconds must be positive")
    if commit != "unknown" and not GIT_SHA_RE.fullmatch(commit):
        raise AssuranceError(
            "commit must be a 40-character lowercase Git SHA or unknown"
        )
    if not checks:
        raise AssuranceError("at least one assurance check is required")
    check_ids = [_check_id(spec.get("check_id")) for spec in checks]
    if len(check_ids) != len(set(check_ids)):
        raise AssuranceError("duplicate assurance check_id")

    results = [
        run_check(root, spec, timeout_seconds=timeout_seconds)
        for spec in checks
    ]
    source_index: dict[str, dict[str, Any]] = {}
    for result in results:
        for source in result["source_files"]:
            prior = source_index.get(source["path"])
            if prior and prior != source:
                raise AssuranceError(
                    f"source file changed between checks: {source['path']}"
                )
            source_index[source["path"]] = source

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_utc": datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "commit": commit,
        "valid": True,
        "check_count": len(results),
        "checks": results,
        "source_files": [source_index[path] for path in sorted(source_index)],
        "claim_boundary": {
            "proves": [
                "The listed public validators executed successfully against the listed source bytes.",
                "The aggregate receipt preserves each validator result and source SHA-256.",
            ],
            "does_not_prove": [
                "Independent reproduction of a private experiment",
                "External validation, field performance, certification, endorsement, deployment, revenue, or customer adoption",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--commit", default="unknown")
    parser.add_argument(
        "--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    try:
        receipt = run_suite(
            args.root.resolve(),
            commit=args.commit,
            timeout_seconds=args.timeout_seconds,
        )
    except (AssuranceError, OSError, ValueError) as exc:
        print(
            json.dumps({"valid": False, "error": str(exc)}, indent=2),
            file=sys.stderr,
        )
        return 1

    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
