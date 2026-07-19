from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / "dashboard" / "data" / "control_plane_state.json"
SCHEMA = "lumencore.control_plane_state.v1"
HASH_SCOPE = (
    "EMBEDDED_SHA256_SELF_CONSISTENCY_ONLY_GIT_COMMIT_IS_CUSTODY_ANCHOR"
)
OWNER_ROLE = "CONTROL_PLANE_STEWARD"
DEFAULT_MAX_FUTURE_SKEW_MINUTES = 5.0
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
    "eia_prospective",
}
NO_ACTION_CONTROL_KEYS = {
    "external_email_sent_by_this_state",
    "portal_submission_performed",
    "signature_or_certification_performed",
    "final_confirmation_performed",
    "merge_performed",
    "deployment_performed",
    "payment_or_legal_acceptance_performed",
    "public_video_publication_performed",
    "devpost_submission_performed",
    "claim_expansion_performed",
}
PUBLIC_SAFETY_PATTERNS = {
    "email address": (
        re.compile(
            r"(?i)(?<![a-z0-9._%+-])[a-z0-9._%+-]+@"
            r"[a-z0-9.-]+\.[a-z]{2,}(?![a-z0-9.-])"
        ),
    ),
    "phone number": (
        re.compile(
            r"(?<![a-zA-Z0-9])(?:\+?1[\s.-]?)?"
            r"(?:\([2-9]\d{2}\)|[2-9]\d{2})[\s.-]"
            r"[2-9]\d{2}[\s.-]\d{4}(?![a-zA-Z0-9])"
        ),
        re.compile(
            r"(?<![a-zA-Z0-9])(?:\(?\d{2,4}\)?[\s.-]){2,4}"
            r"\d{3,4}(?![a-zA-Z0-9])"
        ),
        re.compile(
            r"(?<![a-zA-Z0-9])\+\d{1,3}(?:[\s.-]?\d){7,14}"
            r"(?![a-zA-Z0-9])"
        ),
        re.compile(r"(?<![a-zA-Z0-9])\d{10,15}(?![a-zA-Z0-9])"),
    ),
    "local filesystem path": (
        re.compile(r"(?i)(?:^|[\s\"'(=])[a-z]:[\\/]"),
        re.compile(r"(?:^|[\s\"'(=])\\\\[^\\/\s]+[\\/][^\s\"']+"),
        re.compile(
            r"(?i)(?:^|[\s\"'(=])/(?:home|users|private|tmp|var/tmp|mnt|volumes)/"
        ),
        re.compile(r"(?i)\bfile://(?:localhost/)?[^\s\"']+"),
        re.compile(r"(?:^|[\s\"'(=])\.\.?[\\/][^\s\"']+"),
    ),
    "credential or token": (
        re.compile(
            r"(?i)\b(?:sk-(?:proj-)?|gh[pousr]_|github_pat_|xox[baprs]-)"
            r"[a-z0-9_-]{8,}"
        ),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
        re.compile(
            r"(?i)\b(?:api[_-]?(?:key|token)|access[_-]?token|auth[_-]?token|bearer|secret)"
            r"\s*[:=]\s*[\"']?[a-z0-9._~+/=-]{12,}"
        ),
    ),
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


def iter_text(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from iter_text(item)
    elif isinstance(value, list):
        for item in value:
            yield from iter_text(item)
    elif isinstance(value, str):
        yield value


def finite_limit(
    value: Any,
    *,
    field: str,
    errors: list[str],
    allow_zero: bool,
) -> float | None:
    if isinstance(value, bool):
        errors.append(f"{field} must be a finite number")
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        errors.append(f"{field} must be a finite number")
        return None
    if not math.isfinite(parsed) or parsed < 0 or (parsed == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        errors.append(f"{field} must be a finite {qualifier} number")
        return None
    return parsed


def verify_state(
    state: Any,
    *,
    now: datetime | None = None,
    max_age_hours: float | None = None,
    max_future_skew_minutes: float = DEFAULT_MAX_FUTURE_SKEW_MINUTES,
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
    if safe_state.get("hash_scope") != HASH_SCOPE:
        errors.append(
            "hash_scope must limit the embedded SHA-256 to self-consistency and "
            "identify the Git commit as the custody anchor"
        )
    if safe_state.get("owner_role") != OWNER_ROLE:
        errors.append(f"owner_role must be {OWNER_ROLE}")
    if "owner" in safe_state:
        errors.append("owner must not publish a named person; use owner_role")

    generated = parse_utc(safe_state.get("generated_utc"), "generated_utc", errors)
    observed_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    validated_max_age = None
    if max_age_hours is not None:
        validated_max_age = finite_limit(
            max_age_hours,
            field="max_age_hours",
            errors=errors,
            allow_zero=False,
        )
    validated_future_skew = finite_limit(
        max_future_skew_minutes,
        field="max_future_skew_minutes",
        errors=errors,
        allow_zero=True,
    )
    age_hours = None
    future_skew_minutes = None
    if generated is not None:
        signed_age_hours = (observed_now - generated).total_seconds() / 3600.0
        age_hours = max(signed_age_hours, 0.0)
        future_skew_minutes = max(-signed_age_hours * 60.0, 0.0)
        if validated_max_age is not None and age_hours > validated_max_age:
            errors.append(
                f"control-plane state is stale: "
                f"{age_hours:.2f}h > {validated_max_age:.2f}h"
            )
        if (
            validated_future_skew is not None
            and future_skew_minutes > validated_future_skew
        ):
            errors.append(
                f"control-plane state is too far in the future: "
                f"{future_skew_minutes:.2f}m > {validated_future_skew:.2f}m"
            )

    expected_hash = str(safe_state.get("state_sha256") or "").lower()
    computed_hash = stable_hash(state_payload(safe_state))
    if expected_hash != computed_hash:
        errors.append("state_sha256 does not match the canonical control-plane payload")

    controls = safe_state.get("controls")
    if not isinstance(controls, dict):
        errors.append("controls must be an object")
        controls = {}
    control_keys = set(controls)
    missing_controls = sorted(NO_ACTION_CONTROL_KEYS - control_keys)
    unknown_controls = sorted(control_keys - NO_ACTION_CONTROL_KEYS)
    if missing_controls:
        errors.append(f"controls missing required keys: {', '.join(missing_controls)}")
    if unknown_controls:
        errors.append(f"controls contain unknown keys: {', '.join(unknown_controls)}")
    for key in sorted(NO_ACTION_CONTROL_KEYS):
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

    public_text = tuple(iter_text(safe_state))
    for label, patterns in PUBLIC_SAFETY_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns for text in public_text):
            errors.append(f"public state contains prohibited {label} pattern")

    return {
        "schema": "lumencore.control_plane_verification_report.v1",
        "verified_utc": observed_now.isoformat(),
        "integrity_valid": not errors,
        "state_id": str(safe_state.get("state_id") or ""),
        "lane_count": len(lanes),
        "required_lane_count": len(REQUIRED_LANES),
        "generated_age_hours": round(age_hours, 3) if age_hours is not None else None,
        "generated_future_skew_minutes": (
            round(future_skew_minutes, 3)
            if future_skew_minutes is not None
            else None
        ),
        "state_hash": {
            "expected": expected_hash,
            "computed": computed_hash,
            "matches": expected_hash == computed_hash,
            "scope": "EMBEDDED_SELF_CONSISTENCY_ONLY",
            "custody_anchor": "GIT_COMMIT",
        },
        "errors": errors,
        "warnings": warnings,
        "claim_boundary": (
            "This verifier checks structure, embedded-hash self-consistency, deadline "
            "locks, and fail-closed action boundaries of one public-safe coordination "
            "snapshot. The Git commit, not the recomputable embedded hash, is the "
            "custody and history anchor. "
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
    parser.add_argument(
        "--max-future-skew-minutes",
        type=float,
        default=DEFAULT_MAX_FUTURE_SKEW_MINUTES,
    )
    args = parser.parse_args()

    state = json.loads(args.state.read_text(encoding="utf-8"))
    report = verify_state(
        state,
        max_age_hours=args.max_age_hours,
        max_future_skew_minutes=args.max_future_skew_minutes,
    )
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["integrity_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
