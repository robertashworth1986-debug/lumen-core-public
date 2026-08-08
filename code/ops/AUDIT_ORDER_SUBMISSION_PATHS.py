#!/usr/bin/env python3
"""Fail CI when a direct order-submission path is new or unclassified."""

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
    if not isinstance(policy.get("rules"), list):
        raise ValueError("order-submission rules are invalid")
    return policy


def audit_repository(repo_root: Path, policy: dict[str, Any]) -> dict[str, Any]:
    root = repo_root.resolve()
    patterns = {
        name: re.compile(str(expression), re.MULTILINE)
        for name, expression in policy["patterns"].items()
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
        if not hits:
            continue

        rule = _matching_rule(relative, rules)
        classification = str(rule.get("classification")) if rule else "unclassified"
        item = {
            "path": relative,
            "patterns": hits,
            "classification": classification,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha": _git_blob_sha(raw),
        }
        matches.append(item)

        if rule is None:
            errors.append({"path": relative, "code": "unclassified_order_submission_path", "patterns": hits})
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
            required_values = ("LIQUIDATE_ALL_TO_USD", "isatty", "--reason")
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({"path": rule_path, "code": "manual_emergency_gate_incomplete", "missing": missing})

        if classification == "validate_only_ticket_facade":
            required_values = ("validate=True", "auto_fire_score=None", "max_auto_fires_per_cycle")
            missing = [value for value in required_values if value not in text]
            if missing:
                errors.append({"path": rule_path, "code": "ticket_facade_invariant_missing", "missing": missing})

    unclassified = [error for error in errors if error["code"] == "unclassified_order_submission_path"]
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "policy_version": policy.get("version"),
        "promotion_stage": policy.get("promotion_stage"),
        "status": "pass" if not errors else "fail",
        "match_count": len(matches),
        "error_count": len(errors),
        "active_unclassified_count": len(unclassified),
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
