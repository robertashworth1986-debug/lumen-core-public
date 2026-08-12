from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REQUIREMENTS = ROOT / "requirements-institutional.txt"
DEFAULT_LOCK = ROOT / "requirements-institutional-ubuntu-py311.lock"
EXPECTED_DIRECT_REQUIREMENT_COUNT = 14
EXPECTED_LOCKED_PACKAGE_COUNT = 39
EXPECTED_HEADER_TOKENS = (
    "uv pip compile requirements-institutional.txt",
    "--python-version 3.11.9",
    "--python-platform x86_64-unknown-linux-gnu",
    "--generate-hashes",
    "--no-build",
)


def load_lock_parser() -> Any:
    path = ROOT / "code" / "ops" / "VERIFY_REVIEWER_DEPENDENCY_LOCK.py"
    spec = importlib.util.spec_from_file_location("reviewer_lock_parser", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load dependency lock parser: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    payload = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_lock(
    *,
    requirements_path: Path = DEFAULT_REQUIREMENTS,
    lock_path: Path = DEFAULT_LOCK,
) -> dict[str, Any]:
    parser = load_lock_parser()
    direct, direct_errors = parser.parse_direct_requirements(requirements_path)
    locked, lock_errors = parser.parse_lock(lock_path)
    lock_text = lock_path.read_text(encoding="utf-8")
    unsafe_hits = sorted(
        token
        for token in parser.UNSAFE_TOKENS
        if token.casefold() in lock_text.casefold()
    )
    direct_matches = {
        name: locked.get(name, {}).get("version") == version
        for name, version in sorted(direct.items())
    }
    checks = {
        "direct_requirements_valid": not direct_errors,
        "lock_syntax_valid": not lock_errors,
        "lock_contains_only_safe_directives": not unsafe_hits,
        "resolver_header_matches_target": all(
            token in lock_text for token in EXPECTED_HEADER_TOKENS
        ),
        "direct_requirement_count_matched": len(direct)
        == EXPECTED_DIRECT_REQUIREMENT_COUNT,
        "locked_package_count_matched": len(locked)
        == EXPECTED_LOCKED_PACKAGE_COUNT,
        "all_direct_pins_matched": bool(direct_matches)
        and all(direct_matches.values()),
        "every_locked_package_hashed": bool(locked)
        and all(entry["hashes"] for entry in locked.values()),
    }
    passed = all(checks.values())
    receipt: dict[str, Any] = {
        "schema": "institutional_dependency_lock_verification.v1",
        "status": (
            "INSTITUTIONAL_DEPENDENCY_LOCK_VALID"
            if passed
            else "INSTITUTIONAL_DEPENDENCY_LOCK_FAIL_CLOSED"
        ),
        "passed": passed,
        "target": {
            "python": "3.11.9",
            "platform": "x86_64-unknown-linux-gnu",
            "source_builds_allowed": False,
        },
        "requirements_path": requirements_path.name,
        "requirements_lock_path": lock_path.name,
        "requirements_lock_sha256": normalized_sha256(lock_path),
        "direct_requirement_count": len(direct),
        "locked_package_count": len(locked),
        "locked_hash_count": sum(len(entry["hashes"]) for entry in locked.values()),
        "direct_matches": direct_matches,
        "checks": checks,
        "errors": [*direct_errors, *lock_errors],
        "unsafe_token_hits": unsafe_hits,
        "scope_boundary": (
            "This verifies the declared Python dependency closure for the bounded "
            "first-party repository test gate. It does not establish production, "
            "external validation, certification, vulnerability-free status, revenue, "
            "or trading performance."
        ),
    }
    receipt["receipt_sha256"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    args = parser.parse_args()
    receipt = verify_lock(
        requirements_path=args.requirements.resolve(),
        lock_path=args.lock.resolve(),
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
