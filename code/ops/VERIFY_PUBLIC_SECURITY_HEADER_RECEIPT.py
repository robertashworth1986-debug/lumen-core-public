#!/usr/bin/env python3
"""Fail-closed verifier for the retained public security-header receipt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "04f5397422cc8e651ddde5cc7e7c57a334866c01"
WORKFLOW_PATH = ".github/workflows/repair-public-security-headers.yml"
WORKFLOW_SHA256 = "6ec9451af22799a5a56b1b5bd850ac1ad12e26b96e47ec1729c13341e5633f19"
DEFAULT_RECEIPT = (
    ROOT
    / "evidence"
    / "public-security-headers"
    / SOURCE_COMMIT
    / "deployment-receipt.json"
)
EXPECTED_ROUTES = [
    "/",
    "/proof_to_pilot.html",
    "/external_review.html",
    "/evidence/",
    "/build_week/prooflock_console/",
    "/health",
    "/api/public/status",
]
EXPECTED_ORIGINS = {
    "vps_loopback",
    "vps_public_network",
    "github_hosted_runner",
}
EXPECTED_POLICY = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": (
        "default-src 'self'; base-uri 'self'; object-src 'none'; "
        "frame-ancestors 'none'; form-action 'self'; img-src 'self' data:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "connect-src 'self'; worker-src 'self' blob:; media-src 'self'; "
        "frame-src 'none'; upgrade-insecure-requests"
    ),
    "Strict-Transport-Security": "max-age=31536000",
    "Permissions-Policy": (
        "accelerometer=(), autoplay=(), camera=(), geolocation=(), gyroscope=(), "
        "magnetometer=(), microphone=(), payment=(), usb=()"
    ),
}


class PublicSecurityHeaderReceiptError(ValueError):
    """Raised when retained public security-header evidence fails closed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PublicSecurityHeaderReceiptError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> None:
    raise PublicSecurityHeaderReceiptError(f"non-finite JSON number: {value}")


def read_json(path: Path, *, max_bytes: int = 250_000) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise PublicSecurityHeaderReceiptError("receipt must be a regular non-symlink file")
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise PublicSecurityHeaderReceiptError(f"receipt exceeds {max_bytes} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except UnicodeDecodeError as exc:
        raise PublicSecurityHeaderReceiptError("receipt is not valid UTF-8") from exc
    if not isinstance(value, dict):
        raise PublicSecurityHeaderReceiptError("receipt must be a JSON object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PublicSecurityHeaderReceiptError(f"{label} must be a lowercase SHA-256")
    return value


def parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PublicSecurityHeaderReceiptError(f"{label} must be a trimmed timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PublicSecurityHeaderReceiptError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PublicSecurityHeaderReceiptError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def require_fields(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise PublicSecurityHeaderReceiptError(f"{label} fields mismatch")
    return value


def git_object(root: Path, source_commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{source_commit}:{path}"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise PublicSecurityHeaderReceiptError("pinned workflow is unavailable from Git")
    return completed.stdout


def verify_receipt(
    *, root: Path = ROOT, receipt_path: Path = DEFAULT_RECEIPT
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    receipt = read_json(receipt_path)
    require_fields(
        receipt,
        {
            "artifact",
            "claim_boundaries",
            "execution",
            "generated_utc",
            "header_policy",
            "observation_origins",
            "production_decision",
            "receipt_sha256",
            "repository",
            "routes",
            "schema",
            "source_commit",
            "source_workflow",
            "workflow_run",
        },
        "receipt",
    )
    if receipt["schema"] != "lumencore.public_security_header_deployment_receipt.v1":
        raise PublicSecurityHeaderReceiptError("schema mismatch")
    if receipt["repository"] != "robertashworth1986-debug/lumen-core-public":
        raise PublicSecurityHeaderReceiptError("repository mismatch")
    if receipt["source_commit"] != SOURCE_COMMIT:
        raise PublicSecurityHeaderReceiptError("source commit mismatch")

    claimed_hash = require_sha256(receipt["receipt_sha256"], "receipt_sha256")
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if claimed_hash != sha256_bytes(canonical_bytes(unhashed)):
        raise PublicSecurityHeaderReceiptError("receipt self-hash mismatch")

    generated = parse_utc(receipt["generated_utc"], "generated_utc")
    if receipt["routes"] != EXPECTED_ROUTES:
        raise PublicSecurityHeaderReceiptError("route coverage mismatch")
    if receipt["header_policy"] != EXPECTED_POLICY:
        raise PublicSecurityHeaderReceiptError("header policy mismatch")

    source_workflow = require_fields(receipt["source_workflow"], {"path", "sha256"}, "source_workflow")
    if source_workflow["path"] != WORKFLOW_PATH:
        raise PublicSecurityHeaderReceiptError("workflow path mismatch")
    if require_sha256(source_workflow["sha256"], "source_workflow.sha256") != WORKFLOW_SHA256:
        raise PublicSecurityHeaderReceiptError("workflow hash declaration mismatch")
    workflow_bytes = git_object(root, SOURCE_COMMIT, WORKFLOW_PATH)
    if sha256_bytes(workflow_bytes) != WORKFLOW_SHA256:
        raise PublicSecurityHeaderReceiptError("pinned workflow bytes mismatch")
    for required in (
        '[[ "$RELEASE_COMMIT" == "$WORKFLOW_COMMIT" ]]',
        '[[ "$(git rev-parse origin/main)" == "$RELEASE_COMMIT" ]]',
        "tr -d '\\r' < \"$headers\" > \"$normalized\"",
        "/api/public/status",
    ):
        if required.encode("utf-8") not in workflow_bytes:
            raise PublicSecurityHeaderReceiptError(f"workflow control missing: {required}")

    run = require_fields(
        receipt["workflow_run"],
        {
            "attempt",
            "completed_utc",
            "conclusion",
            "created_utc",
            "event",
            "head_branch",
            "id",
            "name",
            "url",
        },
        "workflow_run",
    )
    expected_run = {
        "attempt": 1,
        "conclusion": "success",
        "event": "workflow_dispatch",
        "head_branch": "main",
        "id": 31289595192,
        "name": "Repair public security headers on VPS",
        "url": "https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31289595192",
    }
    for field, expected in expected_run.items():
        if run[field] != expected:
            raise PublicSecurityHeaderReceiptError(f"workflow_run.{field} mismatch")
    created = parse_utc(run["created_utc"], "workflow_run.created_utc")
    completed = parse_utc(run["completed_utc"], "workflow_run.completed_utc")
    if not created <= completed <= generated:
        raise PublicSecurityHeaderReceiptError("workflow timestamp ordering mismatch")

    artifact = require_fields(
        receipt["artifact"],
        {"digest", "expires_utc", "id", "name", "size_bytes"},
        "artifact",
    )
    expected_artifact = {
        "digest": "sha256:8ac130ba2a313c795750105141cbfec4b4656c40cfe04cb3b5c58a377681f12d",
        "id": 9030952290,
        "name": "public-security-headers-31289595192-1",
        "size_bytes": 1205,
    }
    for field, expected in expected_artifact.items():
        if artifact[field] != expected:
            raise PublicSecurityHeaderReceiptError(f"artifact.{field} mismatch")
    expires = parse_utc(artifact["expires_utc"], "artifact.expires_utc")
    if expires <= completed:
        raise PublicSecurityHeaderReceiptError("artifact expiry ordering mismatch")

    execution = require_fields(
        receipt["execution"],
        {"nginx_configuration_test", "nginx_reload", "remote_staging_removed", "rollback_triggered"},
        "execution",
    )
    if execution != {
        "nginx_configuration_test": "PASS",
        "nginx_reload": "PASS",
        "remote_staging_removed": True,
        "rollback_triggered": False,
    }:
        raise PublicSecurityHeaderReceiptError("execution state mismatch")

    origins = receipt["observation_origins"]
    if not isinstance(origins, list) or len(origins) != len(EXPECTED_ORIGINS):
        raise PublicSecurityHeaderReceiptError("observation origin count mismatch")
    seen: set[str] = set()
    for index, raw_origin in enumerate(origins):
        origin = require_fields(
            raw_origin,
            {"maximum_attempt", "name", "passed_route_count", "route_count", "status"},
            f"observation_origins[{index}]",
        )
        name = origin["name"]
        if name in seen or name not in EXPECTED_ORIGINS:
            raise PublicSecurityHeaderReceiptError("observation origin identity mismatch")
        seen.add(name)
        if origin != {
            "maximum_attempt": 1,
            "name": name,
            "passed_route_count": 7,
            "route_count": 7,
            "status": "PASS",
        }:
            raise PublicSecurityHeaderReceiptError(f"observation origin failed: {name}")
    if seen != EXPECTED_ORIGINS:
        raise PublicSecurityHeaderReceiptError("required observation origin missing")

    boundaries = receipt["claim_boundaries"]
    if not isinstance(boundaries, list) or len(boundaries) != 3 or len(set(boundaries)) != 3:
        raise PublicSecurityHeaderReceiptError("claim boundaries mismatch")
    normalized = " ".join(str(item).lower() for item in boundaries)
    for phrase in (
        "not a penetration test",
        "do not establish an uptime sla",
        "does not prove application correctness",
    ):
        if phrase not in normalized:
            raise PublicSecurityHeaderReceiptError(f"claim boundary missing: {phrase}")
    if receipt["production_decision"] != "PUBLIC_HEADER_POLICY_OBSERVED_NO_BROADER_PRODUCTION_PROMOTION":
        raise PublicSecurityHeaderReceiptError("production decision mismatch")

    return {
        "valid": True,
        "source_commit": SOURCE_COMMIT,
        "workflow_run_id": run["id"],
        "artifact_digest": artifact["digest"],
        "route_count": len(EXPECTED_ROUTES),
        "observation_origin_count": len(EXPECTED_ORIGINS),
        "production_decision": receipt["production_decision"],
        "receipt_sha256": claimed_hash,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_receipt(receipt_path=args.receipt)
    except (OSError, PublicSecurityHeaderReceiptError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(rendered, end="")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
