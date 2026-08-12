#!/usr/bin/env python3
"""Classify the bounded read-only VPS diagnostic into a reviewer-safe verdict.

The raw diagnostic proves that observation completed; it does not by itself say
that the runtime passed its institutional gate.  This parser keeps those two
facts separate and emits only allowlisted, non-secret findings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "lumencore.vps_runtime_assessment.v1"
EXPECTED_ENDPOINT_CODES = {
    "public_root": 200,
    "public_nginx_health": 200,
    "public_gateway_health": 200,
    "public_gateway_snapshot": 503,
    "loopback_nginx_health": 200,
    "loopback_gateway_via_nginx": 200,
    "loopback_gateway_direct": 200,
}


def _section(text: str, start: str, end: str) -> str:
    if start not in text:
        return ""
    body = text.split(start, 1)[1]
    return body.split(end, 1)[0] if end in body else body


def _unit_fields(text: str, unit: str) -> dict[str, str]:
    services = _section(
        text,
        "=== canonical and related service states ===",
        "=== systemd failed units",
    )
    marker = f"--- {unit} ---"
    if marker not in services:
        return {}
    block = services.split(marker, 1)[1]
    block = block.split("\n--- ", 1)[0]
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def _endpoint_observations(text: str) -> dict[str, dict[str, Any]]:
    observations: dict[str, dict[str, Any]] = {}
    pattern = re.compile(
        r"^(?P<name>[a-z0-9_]+) rc=(?P<rc>\d+) code=(?P<code>\d{3})(?:\s|$)",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        name = match.group("name")
        if name in EXPECTED_ENDPOINT_CODES:
            observations[name] = {
                "rc": int(match.group("rc")),
                "http_code": int(match.group("code")),
            }
    return observations


def _integer(text: str, key: str) -> int | None:
    match = re.search(rf"^{re.escape(key)}=(\d+)$", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def _value(text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}=(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _check(
    check_id: str,
    status: str,
    requirement: str,
    observed: Any,
    *,
    repair_control: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": check_id,
        "status": status,
        "requirement": requirement,
        "observed": observed,
    }
    if repair_control:
        result["repair_control"] = repair_control
    return result


def assess(
    text: str,
    *,
    run_id: str,
    source_commit: str,
    source_url: str,
    diagnostic_sha256: str | None = None,
) -> dict[str, Any]:
    endpoints = _endpoint_observations(text)
    missing_endpoints = sorted(set(EXPECTED_ENDPOINT_CODES) - set(endpoints))
    bad_endpoints = {
        name: observation
        for name, observation in endpoints.items()
        if observation["rc"] != 0
        or observation["http_code"] != EXPECTED_ENDPOINT_CODES[name]
    }
    endpoint_status = (
        "UNKNOWN" if missing_endpoints else "FAIL" if bad_endpoints else "PASS"
    )

    gateway = _unit_fields(text, "luma-gateway")
    gateway_observed = {
        key: gateway.get(key)
        for key in ("active", "ActiveState", "SubState", "User", "Group", "NRestarts")
    }
    gateway_known = bool(gateway)
    gateway_pass = gateway_known and all(
        (
            gateway.get("active") == "active",
            gateway.get("ActiveState") == "active",
            gateway.get("SubState") == "running",
            gateway.get("User") == "lumencore",
            gateway.get("Group") == "lumencore",
        )
    )
    gateway_status = "UNKNOWN" if not gateway_known else "PASS" if gateway_pass else "FAIL"

    lock = _section(
        text,
        "=== gateway singleton-lock identity ===",
        "=== gateway executable and source preflight ===",
    )
    lock_metadata = re.search(
        r"^lock_mode=(?P<mode>\d+) lock_owner=(?P<owner>[^ ]+)",
        lock,
        re.MULTILINE,
    )
    lock_observed = {
        "exists": _value(lock, "lock_exists"),
        "mode": lock_metadata.group("mode") if lock_metadata else None,
        "owner": lock_metadata.group("owner") if lock_metadata else None,
        "pid_matches_systemd_main": _value(lock, "lock_pid_matches_systemd_main"),
    }
    lock_known = lock_observed["exists"] is not None
    lock_pass = lock_known and lock_observed == {
        "exists": "true",
        "mode": "640",
        "owner": "lumencore:lumencore",
        "pid_matches_systemd_main": "true",
    }
    lock_status = "UNKNOWN" if not lock_known else "PASS" if lock_pass else "FAIL"

    closure = _section(
        text,
        "=== approved gateway closure comparison ===",
        "=== end approved gateway closure comparison ===",
    )
    closure_counts = {
        "expected": _integer(closure, "expected_file_count"),
        "match": _integer(closure, "closure_match_count"),
        "mismatch": _integer(closure, "closure_mismatch_count"),
        "missing": _integer(closure, "closure_missing_count"),
        "symbolic": _integer(closure, "closure_symbolic_count"),
        "unreadable": _integer(closure, "closure_unreadable_count"),
    }
    observed_source_commit = _value(closure, "source_commit")
    closure_known = all(value is not None for value in closure_counts.values())
    closure_pass = (
        closure_known
        and observed_source_commit == source_commit
        and closure_counts
        == {
            "expected": 20,
            "match": 20,
            "mismatch": 0,
            "missing": 0,
            "symbolic": 0,
            "unreadable": 0,
        }
    )
    closure_status = (
        "UNKNOWN" if not closure_known else "PASS" if closure_pass else "FAIL"
    )

    ticker = _unit_fields(text, "luma-paper-ticker")
    ticker_observed = {
        key: ticker.get(key)
        for key in ("active", "ActiveState", "SubState", "User", "Group", "NRestarts")
    }
    ticker_known = bool(ticker)
    ticker_pass = ticker_known and all(
        (
            ticker.get("active") == "active",
            ticker.get("ActiveState") == "active",
            ticker.get("SubState") == "running",
            ticker.get("User") == "lumencore",
            ticker.get("Group") == "lumencore",
        )
    )
    ticker_status = "UNKNOWN" if not ticker_known else "PASS" if ticker_pass else "FAIL"

    ledger = _section(
        text,
        "--- paper_ticker_ledger ---",
        "=== runtime allowlisted failure signatures (redacted) ===",
    )
    metadata_match = re.search(
        r"^exists=(?P<exists>true|false).*?mode=(?P<mode>\d+) "
        r"owner=(?P<owner>[^ ]+) group=(?P<group>[^ ]+)",
        ledger,
        re.MULTILINE,
    )
    ledger_observed = {
        "symlink": _value(ledger, "symlink"),
        "exists": metadata_match.group("exists") if metadata_match else None,
        "mode": metadata_match.group("mode") if metadata_match else None,
        "owner": metadata_match.group("owner") if metadata_match else None,
        "group": metadata_match.group("group") if metadata_match else None,
        "lumencore_writable": _value(ledger, "lumencore_test_w"),
    }
    ledger_known = metadata_match is not None
    ledger_pass = ledger_known and ledger_observed == {
        "symlink": "false",
        "exists": "true",
        "mode": "640",
        "owner": "lumencore",
        "group": "lumencore",
        "lumencore_writable": "true",
    }
    ledger_status = "UNKNOWN" if not ledger_known else "PASS" if ledger_pass else "FAIL"

    ticker_failures = _section(
        text,
        "--- luma-paper-ticker failures since 5 minutes ago ---",
        "--- luma-symbol-awareness failures since 5 minutes ago ---",
    )
    failure_window_known = bool(ticker_failures)
    permission_failure_count = ticker_failures.count("PermissionError:")
    failures_status = (
        "UNKNOWN"
        if not failure_window_known
        else "FAIL"
        if permission_failure_count
        else "PASS"
    )

    checks = [
        _check(
            "public_endpoint_contracts",
            endpoint_status,
            "All seven bounded public and loopback probes return their declared codes; the unauthenticated protected snapshot remains fail-closed at 503.",
            {
                "endpoints": endpoints,
                "missing": missing_endpoints,
                "unexpected": bad_endpoints,
            },
        ),
        _check(
            "gateway_service_identity",
            gateway_status,
            "The gateway is active/running under explicit lumencore:lumencore service identity.",
            gateway_observed,
            repair_control="DEPLOY_REVIEWED_NON_ROOT_GATEWAY_SERVICE_IDENTITY",
        ),
        _check(
            "gateway_lock_identity",
            lock_status,
            "The live gateway lock is the systemd main PID and is owned lumencore:lumencore with mode 640.",
            lock_observed,
            repair_control="DEPLOY_REVIEWED_NON_ROOT_GATEWAY_SERVICE_IDENTITY",
        ),
        _check(
            "gateway_source_closure",
            closure_status,
            "All 20 approved current-main gateway files are regular, readable, present, and exact SHA-256 matches.",
            {
                "declared_source_commit": source_commit,
                "observed_source_commit": observed_source_commit,
                **closure_counts,
            },
            repair_control="REPAIR_PUBLIC_GATEWAY_DEPENDENCY_CLOSURE",
        ),
        _check(
            "paper_ticker_service",
            ticker_status,
            "The paper ticker is active/running under lumencore:lumencore.",
            ticker_observed,
            repair_control="REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP",
        ),
        _check(
            "paper_ticker_ledger",
            ledger_status,
            "The exact paper ledger is a nonsymlink regular file owned lumencore:lumencore, mode 640, and writable by lumencore.",
            ledger_observed,
            repair_control="REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP",
        ),
        _check(
            "paper_ticker_recent_failures",
            failures_status,
            "The bounded five-minute paper-ticker journal window contains no ledger PermissionError.",
            {
                "window_present": failure_window_known,
                "permission_error_count": permission_failure_count,
            },
            repair_control="REPAIR_PAPER_TICKER_LEDGER_OWNERSHIP",
        ),
    ]

    failed = [item for item in checks if item["status"] == "FAIL"]
    unknown = [item for item in checks if item["status"] == "UNKNOWN"]
    verdict = "ACTION_REQUIRED" if failed else "INDETERMINATE" if unknown else "PASS"
    repair_controls = sorted(
        {
            item["repair_control"]
            for item in failed
            if item.get("repair_control")
        }
    )
    timestamp_match = re.search(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", text, re.MULTILINE
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
        "source": {
            "run_id": run_id,
            "source_commit": source_commit,
            "source_url": source_url,
            "observed_at_utc": timestamp_match.group(0) if timestamp_match else None,
            "diagnostic_sha256": diagnostic_sha256
            or hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "summary": {
            "pass_count": sum(item["status"] == "PASS" for item in checks),
            "fail_count": len(failed),
            "unknown_count": len(unknown),
            "failed_check_ids": [item["id"] for item in failed],
            "unknown_check_ids": [item["id"] for item in unknown],
            "required_repair_controls": repair_controls,
        },
        "checks": checks,
        "claim_boundary": {
            "proves": "A first-party, point-in-time, bounded runtime assessment of the declared checks.",
            "does_not_prove": [
                "sustained availability",
                "whole-VPS parity or security",
                "external validation or certification",
                "profitable trading",
                "customer acceptance, revenue, or savings",
            ],
        },
    }


def _render_summary(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "## LumenCore VPS runtime assessment",
        "",
        f"**Verdict:** `{payload['verdict']}`",
        "",
        f"- Passed: {summary['pass_count']}",
        f"- Failed: {summary['fail_count']}",
        f"- Unknown: {summary['unknown_count']}",
    ]
    if summary["failed_check_ids"]:
        lines.extend(
            ["", "### Action-required checks", ""]
            + [f"- `{item}`" for item in summary["failed_check_ids"]]
        )
    if summary["required_repair_controls"]:
        lines.extend(
            ["", "### Existing gated repair controls", ""]
            + [f"- `{item}`" for item in summary["required_repair_controls"]]
        )
    lines.extend(
        [
            "",
            "This is first-party point-in-time evidence. It is not external validation, certification, sustained-uptime proof, trading-profit proof, customer acceptance, revenue, or savings.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args()

    if not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        parser.error("--source-commit must be a full lowercase Git SHA")
    raw = args.input.read_bytes()
    text = raw.decode("utf-8")
    payload = assess(
        text,
        run_id=args.run_id,
        source_commit=args.source_commit,
        source_url=args.source_url,
        diagnostic_sha256=hashlib.sha256(raw).hexdigest(),
    )
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.summary_output:
        args.summary_output.write_text(_render_summary(payload), encoding="utf-8")
    print(payload["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
