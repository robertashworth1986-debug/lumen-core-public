#!/usr/bin/env python3
"""Fail CI when an order or capital-transfer path is new or unclassified."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCAN_SUFFIXES = {".py", ".ps1", ".sh"}
SKIP_PARTS = {".git", ".venv", "venv", "node_modules", "out", "dist", "build", "__pycache__"}
PRODUCTION_ALPACA_ORIGIN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9.-])https://api\.alpaca\.markets(?=[:/\"']|\s|$)"
)


def _git_blob_sha(data: bytes) -> str:
    # Git's text filter stores LF bytes even when a Windows checkout presents
    # CRLF. These policy pins describe repository blobs, not host checkout
    # formatting, so normalize the scannable text before computing the blob ID.
    normalized = data.replace(b"\r\n", b"\n")
    return hashlib.sha1(
        f"blob {len(normalized)}\0".encode("ascii") + normalized
    ).hexdigest()


def _matching_rule(path: str, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    for rule in rules:
        if fnmatch.fnmatch(path, str(rule.get("path", ""))):
            return rule
    return None


def _scannable(path: Path) -> bool:
    if any(part in SKIP_PARTS for part in path.parts):
        return False
    return path.suffix.lower() in SCAN_SUFFIXES or path.name.lower().endswith(".py.bak")


def load_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or not isinstance(policy.get("patterns"), dict):
        raise ValueError("order-submission policy is invalid")
    if not isinstance(policy.get("arming_patterns", {}), dict):
        raise ValueError("live-arming patterns are invalid")
    if not isinstance(policy.get("rules"), list):
        raise ValueError("order-submission rules are invalid")
    if not isinstance(policy.get("runtime_invariants", []), list):
        raise ValueError("runtime invariants are invalid")
    return policy


def audit_repository(repo_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    root = repo_root.resolve()
    patterns = {
        name: re.compile(str(expression), re.MULTILINE)
        for name, expression in policy["patterns"].items()
    }
    arming_patterns = {
        name: re.compile(str(expression), re.MULTILINE | re.IGNORECASE)
        for name, expression in policy.get("arming_patterns", {}).items()
    }
    rules = list(policy["rules"])
    matches: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root).as_posix()
        if not _scannable(Path(relative)):
            continue
        raw = file_path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        hits = sorted(name for name, pattern in patterns.items() if pattern.search(text))
        arming_hits = sorted(
            name for name, pattern in arming_patterns.items() if pattern.search(text)
        )
        if not hits and not arming_hits:
            continue

        rule = _matching_rule(relative, rules)
        classification = str(rule.get("classification")) if rule else "unclassified"
        item = {
            "path": relative,
            "patterns": hits,
            "arming_patterns": arming_hits,
            "classification": classification,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha": _git_blob_sha(raw),
        }
        matches.append(item)

        if hits and rule is None:
            errors.append({"path": relative, "code": "unclassified_order_submission_path", "patterns": hits})

        if arming_hits and classification not in {
            "historical_preserved",
            "historical_backup",
            "test_fixture",
        }:
            errors.append({
                "path": relative,
                "code": "active_live_arming_path",
                "patterns": arming_hits,
            })

        if rule is None:
            continue

        expected = str(rule.get("expected_git_blob_sha", "") or "")
        if expected and item["git_blob_sha"] != expected:
            errors.append({
                "path": relative,
                "code": "preserved_blob_mismatch",
                "expected": expected,
                "actual": item["git_blob_sha"],
            })

        if classification == "paper_sandbox":
            if PRODUCTION_ALPACA_ORIGIN_PATTERN.search(text):
                errors.append({"path": relative, "code": "paper_path_contains_production_alpaca_host"})
            if "https://paper-api.alpaca.markets" not in text:
                errors.append({"path": relative, "code": "paper_path_missing_paper_host"})

    # Exact required paths are checked even when they intentionally contain no
    # submission token, such as the read-only monitor and manual facade.
    for rule in rules:
        rule_path = str(rule.get("path", ""))
        if any(char in rule_path for char in "*?["):
            continue
        path = root / rule_path
        required = bool(rule.get("required", False))
        expected = str(rule.get("expected_git_blob_sha", "") or "")
        classification = str(rule.get("classification", "") or "")

        if not path.exists():
            if required or expected:
                errors.append({"path": rule_path, "code": "required_policy_path_missing"})
            continue

        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        if expected and _git_blob_sha(raw) != expected:
            mismatch = {
                "path": rule_path,
                "code": "preserved_blob_mismatch",
                "expected": expected,
                "actual": _git_blob_sha(raw),
            }
            if mismatch not in errors:
                errors.append(mismatch)

        if classification == "read_only_monitor":
            hits = sorted(name for name, pattern in patterns.items() if pattern.search(text))
            if hits:
                errors.append({"path": rule_path, "code": "read_only_monitor_contains_order_path", "patterns": hits})
            required_values = ("public_market_data_only", "credentials_loaded", "allow_live_orders", "live_data_no_orders")
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({"path": rule_path, "code": "read_only_monitor_invariant_missing", "missing": missing})

        if classification == "paper_only_orchestrator":
            required_values = (
                "PAPER_ONLY_POLICY",
                "live_order_submission_disabled",
                "LIVE_REQUEST_BLOCKED",
            )
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({
                    "path": rule_path,
                    "code": "paper_only_orchestrator_invariant_missing",
                    "missing": missing,
                })
            hits = sorted(name for name, pattern in patterns.items() if pattern.search(text))
            if hits:
                errors.append({
                    "path": rule_path,
                    "code": "paper_only_orchestrator_contains_order_path",
                    "patterns": hits,
                })

        if classification == "manual_emergency_facade":
            required_values = (
                "LIQUIDATE_ALL_TO_USD",
                "isatty",
                "--reason",
                "build_manual_emergency_authorization",
                "authorization_sha256",
            )
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({"path": rule_path, "code": "manual_emergency_gate_incomplete", "missing": missing})

        if classification == "validate_only_ticket_facade":
            required_values = ("validate=True", "auto_fire_score=None", "max_auto_fires_per_cycle")
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({"path": rule_path, "code": "ticket_facade_invariant_missing", "missing": missing})

        if classification == "capital_transfer_blocked_facade":
            required_values = (
                "CAPITAL_TRANSFER_BLOCKED",
                '"credentials_loaded": False',
                '"network_access": False',
                '"destination_address_loaded": False',
                '"withdrawal_authorized": False',
            )
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({
                    "path": rule_path,
                    "code": "capital_transfer_facade_invariant_missing",
                    "missing": missing,
                })
            hits = sorted(name for name, pattern in patterns.items() if pattern.search(text))
            if hits:
                errors.append({
                    "path": rule_path,
                    "code": "capital_transfer_facade_contains_submission_path",
                    "patterns": hits,
                })
            forbidden_values = (
                "KRAKEN_API_KEY",
                "KRAKEN_API_SECRET",
                "luma_live_keys.env",
            )
            present = [value for value in forbidden_values if value in text]
            if present:
                errors.append({
                    "path": rule_path,
                    "code": "capital_transfer_facade_loads_sensitive_runtime_data",
                    "present": present,
                })

        if classification in {
            "venue_mutation_blocked_facade",
            "capital_dispatch_blocked_facade",
        }:
            marker = (
                "VENUE_MUTATION_BLOCKED"
                if classification == "venue_mutation_blocked_facade"
                else "CAPITAL_DISPATCH_BLOCKED"
            )
            required_values = (
                marker,
                '"credentials_loaded": False',
                '"network_access": False',
                (
                    '"mutation_authorized": False'
                    if classification == "venue_mutation_blocked_facade"
                    else '"transfer_authorized": False'
                ),
            )
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({
                    "path": rule_path,
                    "code": "blocked_mutation_facade_invariant_missing",
                    "missing": missing,
                })
            hits = sorted(name for name, pattern in patterns.items() if pattern.search(text))
            if hits:
                errors.append({
                    "path": rule_path,
                    "code": "blocked_mutation_facade_contains_mutation_path",
                    "patterns": hits,
                })
            forbidden_values = (
                "requests",
                "httpx",
                "ccxt",
                "urlopen",
                "luma_live_keys.env",
                "_API_KEY",
                "_API_SECRET",
            )
            present = [value for value in forbidden_values if value in text]
            if present:
                errors.append({
                    "path": rule_path,
                    "code": "blocked_mutation_facade_contains_runtime_transport",
                    "present": present,
                })

        if classification == "paper_supervisor_exact_host":
            required_values = (
                "PAPER_TRADING_ORIGIN",
                "normalize_paper_trading_base",
                "_resolve_alpaca_paper_base",
                "generic_override and not paper_override",
                "allow_redirects=False",
            )
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({
                    "path": rule_path,
                    "code": "paper_supervisor_origin_gate_incomplete",
                    "missing": missing,
                })
            if PRODUCTION_ALPACA_ORIGIN_PATTERN.search(text):
                errors.append({
                    "path": rule_path,
                    "code": "paper_supervisor_contains_production_alpaca_host",
                })

        if classification == "guard_implementation":
            required_values = (
                "READ_ONLY_PRIVATE_PATHS",
                "blocked_private_mutation",
                "build_manual_emergency_authorization",
                "private_endpoint_allowlist_fail_closed",
            )
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({
                    "path": rule_path,
                    "code": "private_endpoint_guard_incomplete",
                    "missing": missing,
                })
            if "request is not an AddOrder submission" in text:
                errors.append({
                    "path": rule_path,
                    "code": "private_endpoint_guard_retains_allow_unknown_logic",
                })

    for invariant in policy.get("runtime_invariants", []):
        invariant_path = str(invariant.get("path", "") or "")
        expected_values = invariant.get("expected", {})
        path = root / invariant_path
        if not invariant_path or not isinstance(expected_values, dict):
            errors.append({"path": invariant_path, "code": "invalid_runtime_invariant"})
            continue
        if not path.exists():
            errors.append({"path": invariant_path, "code": "runtime_control_missing"})
            continue
        try:
            runtime = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append({"path": invariant_path, "code": "runtime_control_invalid_json"})
            continue
        if not isinstance(runtime, dict):
            errors.append({"path": invariant_path, "code": "runtime_control_not_object"})
            continue
        mismatches = {
            key: {"expected": expected, "actual": runtime.get(key)}
            for key, expected in expected_values.items()
            if runtime.get(key) != expected
        }
        if mismatches:
            errors.append({
                "path": invariant_path,
                "code": "runtime_control_invariant_mismatch",
                "mismatches": mismatches,
            })

    unclassified = [error for error in errors if error["code"] == "unclassified_order_submission_path"]
    active_arming = [error for error in errors if error["code"] == "active_live_arming_path"]
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "policy_version": policy.get("version"),
        "promotion_stage": policy.get("promotion_stage"),
        "status": "pass" if not errors else "fail",
        "match_count": len(matches),
        "error_count": len(errors),
        "active_unclassified_count": len(unclassified),
        "active_arming_count": len(active_arming),
        "matches": matches,
        "errors": errors,
    }
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    report["report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--policy", default="config/order_submission_path_policy.json")
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[2]
    policy_path = Path(args.policy)
    if not policy_path.is_absolute():
        policy_path = root / policy_path
    report = audit_repository(root, load_policy(policy_path))

    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
