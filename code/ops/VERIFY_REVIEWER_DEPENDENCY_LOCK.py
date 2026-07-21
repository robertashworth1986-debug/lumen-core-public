from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = ROOT / "config" / "reviewer_reproducibility_protocol_v1.json"
LOCK_ENTRY = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s\\]+)\s+\\$")
HASH_ENTRY = re.compile(r"^--hash=sha256:([0-9a-f]{64})(?:\s+\\)?$")
LOCK_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.!+_-]*$")
UNSAFE_TOKENS = (
    "--extra-index-url",
    "--find-links",
    "--index-url",
    "--trusted-host",
    "--no-binary",
    "git+",
    "http://",
    "https://",
    " @ ",
)


def canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def normalized_bytes(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def normalized_sha256(path: Path) -> str:
    return hashlib.sha256(normalized_bytes(path)).hexdigest()


def parse_direct_requirements(path: Path) -> tuple[dict[str, str], list[str]]:
    pins: dict[str, str] = {}
    errors: list[str] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "==" not in line or any(token in line for token in (";", "[", "]", " ")):
            errors.append(f"invalid direct requirement at line {line_number}")
            continue
        name, version = line.split("==", 1)
        normalized = canonical_name(name)
        if not name or not version or normalized in pins:
            errors.append(f"invalid or duplicate direct requirement at line {line_number}")
            continue
        pins[normalized] = version
    return pins, errors


def parse_lock(path: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    text = path.read_text(encoding="utf-8")
    entries: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    current: dict[str, Any] | None = None
    for line_number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = LOCK_ENTRY.fullmatch(stripped)
        if match:
            name, version = match.groups()
            normalized = canonical_name(name)
            if not LOCK_VERSION.fullmatch(version):
                errors.append(f"unsupported locked version at line {line_number}")
            if normalized in entries:
                errors.append(f"duplicate locked package at line {line_number}: {normalized}")
            current = {
                "name": normalized,
                "version": version,
                "hashes": [],
                "line": line_number,
            }
            entries[normalized] = current
            continue
        hash_match = HASH_ENTRY.fullmatch(stripped)
        if hash_match and current is not None:
            current["hashes"].append(hash_match.group(1))
            continue
        errors.append(f"unsupported lock syntax at line {line_number}")

    for name, entry in entries.items():
        hashes = entry["hashes"]
        if not hashes:
            errors.append(f"locked package has no SHA-256 hashes: {name}")
        if len(hashes) != len(set(hashes)):
            errors.append(f"locked package has duplicate SHA-256 hashes: {name}")
    return entries, errors


def verify_lock(
    *,
    root: Path = ROOT,
    protocol_path: Path = DEFAULT_PROTOCOL,
    lock_path: Path | None = None,
) -> dict[str, Any]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    environment = protocol["environment"]
    requirements_path = root / environment["requirements_path"]
    resolved_lock_path = lock_path or root / environment["requirements_lock_path"]
    direct, direct_errors = parse_direct_requirements(requirements_path)
    entries, lock_errors = parse_lock(resolved_lock_path)
    lock_text = resolved_lock_path.read_text(encoding="utf-8")
    unsafe_hits = sorted(
        token for token in UNSAFE_TOKENS if token.casefold() in lock_text.casefold()
    )
    workflow_path = root / ".github" / "workflows" / "reviewer-reproducibility.yml"
    workflow_text = (
        workflow_path.read_text(encoding="utf-8") if workflow_path.is_file() else ""
    )
    verifier_position = workflow_text.find(
        "python code/ops/VERIFY_REVIEWER_DEPENDENCY_LOCK.py"
    )
    hash_install_position = workflow_text.find("--require-hashes")
    resolver = environment["requirements_lock_resolver"]
    expected_header_tokens = (
        f"uv=={resolver['version']} pip compile",
        f"--python-version {resolver['python']}",
        f"--python-platform {resolver['target_platform']}",
        "--generate-hashes",
        "--no-build",
    )
    direct_matches = {
        name: entries.get(name, {}).get("version") == version
        for name, version in direct.items()
    }
    required_transitive = environment.get("target_required_transitive", {})
    transitive_matches = {
        canonical_name(name): entries.get(canonical_name(name), {}).get("version")
        == version
        for name, version in required_transitive.items()
    }
    actual_lock_sha256 = normalized_sha256(resolved_lock_path)
    checks = {
        "protocol_schema_matched": protocol.get("schema")
        == "reviewer_reproducibility_protocol.v1",
        "direct_requirements_valid": not direct_errors,
        "lock_syntax_valid": not lock_errors,
        "lock_contains_only_safe_directives": not unsafe_hits,
        "resolver_header_matches_protocol": all(
            token in lock_text for token in expected_header_tokens
        ),
        "lock_sha256_matched": actual_lock_sha256
        == environment["requirements_lock_sha256"],
        "lock_package_count_matched": len(entries)
        == int(environment["requirements_lock_package_count"]),
        "all_direct_pins_matched": bool(direct_matches) and all(direct_matches.values()),
        "required_linux_transitives_matched": bool(transitive_matches)
        and all(transitive_matches.values()),
        "every_locked_package_hashed": bool(entries)
        and all(entry["hashes"] for entry in entries.values()),
        "source_builds_prohibited": resolver["source_builds_allowed"] is False,
        "workflow_requires_hashes": "--require-hashes" in workflow_text,
        "workflow_requires_binary_artifacts": "--only-binary=:all:" in workflow_text,
        "workflow_installs_declared_lock": (
            f"--requirement {environment['requirements_lock_path']}" in workflow_text
        ),
        "workflow_runs_dependency_consistency_check": "python -m pip check"
        in workflow_text,
        "workflow_uses_authoritative_runner": (
            f"runs-on: {environment['authoritative_runner']['github_image']}"
            in workflow_text
        ),
        "workflow_verifies_lock_before_install": 0
        <= verifier_position
        < hash_install_position,
        "authoritative_target_declared": resolver["target_platform"]
        == "x86_64-unknown-linux-gnu",
        "cross_platform_scope_not_overclaimed": environment[
            "cross_platform_artifact_hash_lock_complete"
        ]
        is False,
    }
    passed = all(checks.values()) and environment["artifact_hash_lock_complete"] is True
    receipt: dict[str, Any] = {
        "schema": "reviewer_dependency_lock_verification.v1",
        "status": "AUTHORITATIVE_RUNNER_LOCK_VALID" if passed else "DEPENDENCY_LOCK_FAIL_CLOSED",
        "passed": passed,
        "target": environment["requirements_lock_resolver"],
        "requirements_path": environment["requirements_path"],
        "requirements_lock_path": environment["requirements_lock_path"],
        "requirements_lock_sha256": actual_lock_sha256,
        "direct_requirement_count": len(direct),
        "locked_package_count": len(entries),
        "locked_hash_count": sum(len(entry["hashes"]) for entry in entries.values()),
        "direct_matches": direct_matches,
        "required_transitive_matches": transitive_matches,
        "locked_packages": {
            name: entry["version"] for name, entry in sorted(entries.items())
        },
        "checks": checks,
        "errors": [*direct_errors, *lock_errors],
        "unsafe_token_hits": unsafe_hits,
        "scope_boundary": environment["artifact_hash_lock_scope"],
        "known_gap": environment["artifact_hash_lock_gap"],
    }
    receipt["receipt_sha256"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    args = parser.parse_args()
    receipt = verify_lock(protocol_path=args.protocol.resolve())
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
