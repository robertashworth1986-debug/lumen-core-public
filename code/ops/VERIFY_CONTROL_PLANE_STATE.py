from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / "dashboard" / "data" / "control_plane_state.json"
SCHEMA = "lumencore.control_plane_state.v1"
ALLOWED_STATES = {
    "BLOCKED",
    "HOLD",
    "RECONCILIATION_REQUIRED",
    "READY_FOR_REVIEW",
    "PREPARATION",
    "WAITING",
    "READ_ONLY",
    "NO_ACTION_DUE",
    "PRELIMINARY",
}
REQUIRED_LANES = {
    "missionweave",
    "harbor_sentinel",
    "prooflock",
    "public_site",
    "dice",
    "outreach_governance",
    "epri_opai",
    "patent_center",
}
WRITE_CONTROL_KEYS = {
    "external_email_sent_by_this_state",
    "portal_submission_performed",
    "signature_or_certification_performed",
    "merge_performed",
    "deployment_performed",
    "payment_or_legal_acceptance_performed",
}


def parse_utc(value: Any, field: str, errors: list[str]) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        errors.append(f"{field} is required")
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{field} must be ISO-8601")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{field} must include a timezone")
        return None
    return parsed.astimezone(timezone.utc)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def state_payload(state: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(state)
    payload.pop("state_sha256", None)
    return payload


def verify_state(
    state: Any,
    *,
    now: datetime | None = None,
    max_age_hours: float | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    safe_state = state if isinstance(state, dict) else {}

    if safe_state.get("schema") != SCHEMA:
        errors.append("unsupported or missing control-plane schema")
    if safe_state.get("authority") != "PUBLIC_SAFE_RECONCILIATION_NOT_ACTION_AUTHORITY":
        errors.append("authority must remain non-action-authorizing")
    if safe_state.get("failure_mode") != "FAIL_CLOSED":
        errors.append("failure_mode must be FAIL_CLOSED")

    generated = parse_utc(safe_state.get("generated_utc"), "generated_utc", errors)
    observed_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    age_hours = None
    if generated is not None:
        age_hours = max((observed_now - generated).total_seconds() / 3600.0, 0.0)
        if max_age_hours is not None and age_hours > max_age_hours:
            errors.append(
                f"control-plane state is stale: {age_hours:.2f}h > {max_age_hours:.2f}h"
            )

    expected_hash = str(safe_state.get("state_sha256") or "").lower()
    computed_hash = stable_hash(state_payload(safe_state))
    if expected_hash != computed_hash:
        errors.append("state_sha256 does not match the canonical control-plane payload")

    controls = safe_state.get("controls")
    if not isinstance(controls, dict):
        errors.append("controls must be an object")
        controls = {}
    for key in sorted(WRITE_CONTROL_KEYS):
        if controls.get(key) is not False:
            errors.append(f"{key} must be explicitly false")

    lanes = safe_state.get("lanes")
    if not isinstance(lanes, list):
        errors.append("lanes must be an array")
        lanes = []

    lane_ids: list[str] = []
    priorities: list[int] = []
    deadlines: dict[str, str | None] = {}
    for index, row in enumerate(lanes):
        prefix = f"lanes[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        lane_id = str(row.get("lane_id") or "").strip()
        if not lane_id:
            errors.append(f"{prefix}.lane_id is required")
        elif lane_id in lane_ids:
            errors.append(f"duplicate lane_id: {lane_id}")
        lane_ids.append(lane_id)

        priority = row.get("priority")
        if not isinstance(priority, int) or isinstance(priority, bool) or priority <= 0:
            errors.append(f"{prefix}.priority must be a positive integer")
        else:
            priorities.append(priority)

        lane_state = str(row.get("state") or "")
        if lane_state not in ALLOWED_STATES:
            errors.append(f"{prefix}.state is invalid: {lane_state}")

        deadline = row.get("deadline_utc")
        if deadline is not None:
            parse_utc(deadline, f"{prefix}.deadline_utc", errors)
            deadlines[lane_id] = str(deadline)
        else:
            deadlines[lane_id] = None

        for field in ("summary", "claim_boundary"):
            if not str(row.get(field) or "").strip():
                errors.append(f"{prefix}.{field} is required")

        evidence = row.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}.evidence must be a non-empty array")
        else:
            for evidence_index, item in enumerate(evidence):
                eprefix = f"{prefix}.evidence[{evidence_index}]"
                if not isinstance(item, dict):
                    errors.append(f"{eprefix} must be an object")
                    continue
                if not str(item.get("source_type") or "").strip():
                    errors.append(f"{eprefix}.source_type is required")
                if not str(item.get("reference") or "").strip():
                    errors.append(f"{eprefix}.reference is required")
                parse_utc(item.get("observed_utc"), f"{eprefix}.observed_utc", errors)

        open_gates = row.get("open_gates")
        if lane_state in {
            "BLOCKED",
            "HOLD",
            "RECONCILIATION_REQUIRED",
            "PREPARATION",
            "PRELIMINARY",
        }:
            if not isinstance(open_gates, list) or not open_gates:
                errors.append(f"{prefix}.open_gates must explain the non-promoted state")

        next_actions = row.get("next_actions")
        if not isinstance(next_actions, list) or not next_actions:
            errors.append(f"{prefix}.next_actions must be a non-empty array")

        prohibited = row.get("prohibited_actions")
        if not isinstance(prohibited, list) or not prohibited:
            errors.append(f"{prefix}.prohibited_actions must be a non-empty array")

    missing = sorted(REQUIRED_LANES - set(lane_ids))
    if missing:
        errors.append(f"missing required lanes: {', '.join(missing)}")
    if len(priorities) != len(set(priorities)):
        errors.append("lane priorities must be unique")

    expected_deadlines = {
        "prooflock": "2026-07-22T00:00:00Z",
        "missionweave": "2026-07-22T16:00:00Z",
        "harbor_sentinel": "2026-07-22T16:00:00Z",
        "dice": "2026-08-25T18:00:00Z",
    }
    for lane_id, expected in expected_deadlines.items():
        if deadlines.get(lane_id) != expected:
            errors.append(
                f"{lane_id} deadline must remain {expected} until source-reconciled"
            )

    stale_sources = safe_state.get("stale_or_conflicting_sources")
    if not isinstance(stale_sources, list) or not stale_sources:
        errors.append("stale_or_conflicting_sources must be a non-empty array")
        stale_sources = []
    stale_paths = {
        str(item.get("path") or "")
        for item in stale_sources
        if isinstance(item, dict)
    }
    for required_path in {
        "docs/CANONICAL_OPERATING_STATE.md",
        "dashboard/data/grant_readiness_status.json",
    }:
        if required_path not in stale_paths:
            errors.append(f"stale source register must include {required_path}")

    serialized = canonical_json(safe_state).lower()
    for private_marker in ("@gmail.com", "c:\\users\\", "e:\\", "sk-proj-", "ghp_"):
        if private_marker in serialized:
            errors.append(
                f"public state contains prohibited private marker: {private_marker}"
            )

    return {
        "schema": "lumencore.control_plane_verification_report.v1",
        "verified_utc": observed_now.isoformat(),
        "integrity_valid": not errors,
        "state_id": str(safe_state.get("state_id") or ""),
        "lane_count": len(lanes),
        "required_lane_count": len(REQUIRED_LANES),
        "generated_age_hours": round(age_hours, 3) if age_hours is not None else None,
        "state_hash": {
            "expected": expected_hash,
            "computed": computed_hash,
            "matches": expected_hash == computed_hash,
        },
        "errors": errors,
        "warnings": warnings,
        "claim_boundary": (
            "This verifier checks the structure, custody hash, deadline locks, and "
            "fail-closed action boundaries of one public-safe coordination snapshot. "
            "It does not prove portal readiness, proposal compliance, deployment, "
            "external validation, funding, legal status, or authority to send, sign, "
            "merge, deploy, pay, certify, or submit."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the LumenCore public-safe control-plane state."
    )
    parser.add_argument("state", nargs="?", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--max-age-hours", type=float, default=None)
    args = parser.parse_args()

    state = json.loads(args.state.read_text(encoding="utf-8"))
    report = verify_state(state, max_age_hours=args.max_age_hours)
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["integrity_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
