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
HASH_SCOPE = "EMBEDDED_SHA256_SELF_CONSISTENCY_ONLY"
CUSTODY_ANCHOR = "GIT_COMMIT_OR_COMMIT_BOUND_RECEIPT"
OWNER_ROLE = "CONTROL_PLANE_STEWARD"
DEFAULT_MAX_AGE_HOURS = 24.0
DEFAULT_MAX_FUTURE_SKEW_MINUTES = 5.0
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
STATE_ID_RE = re.compile(r"^control-plane-\d{8}T\d{6}Z$")
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
    "portal_access_performed",
    "portal_modification_performed",
    "portal_upload_performed",
    "portal_submission_performed",
    "proposal_submission_performed",
    "signature_performed",
    "certification_performed",
    "final_confirmation_performed",
    "merge_performed",
    "deployment_performed",
    "dns_change_performed",
    "payment_performed",
    "legal_acceptance_performed",
    "public_video_publication_performed",
    "devpost_submission_performed",
    "claim_expansion_performed",
}
TOP_LEVEL_KEYS = {
    "authority",
    "claim_boundary",
    "controls",
    "custody_anchor",
    "failure_mode",
    "generated_utc",
    "hash_scope",
    "independent_findings",
    "lanes",
    "operating_principle",
    "owner_role",
    "schema",
    "source_cutoff",
    "stale_or_conflicting_sources",
    "state_id",
    "state_sha256",
}
SOURCE_CUTOFF_KEYS = {
    "gmail_handoff_observed_utc",
    "github_observed_utc",
    "official_deadlines_observed_utc",
}
INDEPENDENT_FINDING_KEYS = {
    "bounded_fix",
    "finding",
    "finding_id",
    "scope",
    "severity",
}
LANE_KEYS = {
    "category",
    "claim_boundary",
    "deadline_utc",
    "evidence",
    "lane_id",
    "next_actions",
    "open_gates",
    "priority",
    "prohibited_actions",
    "state",
    "summary",
}
EVIDENCE_KEYS = {"observed_utc", "reference", "source_type"}
STALE_SOURCE_KEYS = {"finding", "path", "required_control", "state"}
DIRECT_IDENTIFIER_FIELDS = {
    "owner",
    "owner_name",
    "founder_name",
    "contact",
    "contact_name",
    "contact_email",
    "contact_phone",
    "signatory",
    "signatory_name",
    "inventor",
    "inventor_name",
    "email",
    "email_address",
    "phone",
    "phone_number",
    "address",
    "street_address",
    "mailing_address",
    "home_address",
    "ssn",
    "social_security_number",
    "date_of_birth",
    "dob",
    "tax_id",
    "ein",
}
CREDENTIAL_FIELDS = {
    "api_key",
    "api_token",
    "access_key",
    "access_token",
    "auth_token",
    "bearer_token",
    "client_secret",
    "credential",
    "credentials",
    "password",
    "passwd",
    "private_key",
    "secret",
    "secret_key",
}
PATENT_SENSITIVE_FIELDS = {
    "application_number",
    "customer_number",
    "draft_claims",
    "filing_receipt_path",
    "invention_disclosure",
    "patent_application_number",
    "patent_claims",
    "patent_document_path",
    "claims_text",
}
PUBLIC_SAFETY_PATTERNS = {
    "direct identifier": (
        re.compile(
            r"(?i)(?<![a-z0-9._%+-])[a-z0-9._%+-]+@"
            r"[a-z0-9.-]+\.[a-z]{2,}(?![a-z0-9.-])"
        ),
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
        re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
        re.compile(r"(?<!\d)\d{2}-\d{7}(?!\d)"),
        re.compile(
            r"(?i)\b\d{1,6}\s+(?:[a-z0-9.'-]+\s+){1,6}"
            r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|"
            r"lane|ln|court|ct|way|parkway|pkwy|highway|hwy)\b"
        ),
        re.compile(
            r"(?i)\b(?:owner|founder|contact|signatory|inventor)"
            r"(?:\s+name)?\s*[:=]\s*[a-z][a-z'-]+"
            r"(?:\s+[a-z][a-z'-]+){1,3}\b"
        ),
    ),
    "private or patent-sensitive path": (
        re.compile(r"(?i)(?:^|[\s\"'(=])[a-z]:[\\/]"),
        re.compile(r"(?:^|[\s\"'(=])\\\\[^\\/\s]+[\\/][^\s\"']+"),
        re.compile(
            r"(?i)(?:^|[\s\"'(=])/(?:home|users|private|tmp|var/tmp|mnt|volumes)/"
        ),
        re.compile(r"(?i)\bfile://(?:localhost/)?[^\s\"']+"),
        re.compile(r"(?:^|[\s\"'(=])\.\.?[\\/][^\s\"']+"),
        re.compile(
            r"(?i)(?:^|[\\/])(?:private|confidential|proprietary|secrets?|"
            r"credentials?|patents?|provisional|invention_disclosures?)(?:[\\/])"
        ),
        re.compile(
            r"(?i)(?:^|[\\/])[^\\/\s\"']*(?:private|confidential|"
            r"proprietary|secret|credential|token|password|patent|provisional|"
            r"invention|claims?)[^\\/\s\"']*\.[a-z0-9]{1,10}"
            r"(?:$|[\s\"'])"
        ),
        re.compile(
            r"(?i)(?:^|[\\/])(?:\.env(?:\.[a-z0-9_-]+)?|"
            r"[^\\/]+\.(?:pem|key|p12|pfx|jks|kdbx))(?:$|[\s\"'])"
        ),
    ),
    "credential or token": (
        re.compile(
            r"(?i)\b(?:sk-(?:proj-)?|gh[pousr]_|github_pat_|xox[baprs]-)"
            r"[a-z0-9_-]{8,}"
        ),
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
        re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----"),
        re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"),
        re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@"),
        re.compile(
            r"(?i)\b(?:api[_-]?(?:key|token)|access[_-]?(?:key|token)|"
            r"auth[_-]?token|bearer(?:[_-]?token)?|client[_-]?secret|password|"
            r"passwd|private[_-]?key|secret(?:[_-]?key)?)\s*[:=]\s*"
            r"[\"']?[^\s\"',;]{8,}"
        ),
    ),
    "private or patent-sensitive content": (
        re.compile(r"(?<!\d)\d{2}/\d{3},?\d{3}(?!\d)"),
        re.compile(
            r"(?i)\b(?:attorney-client privileged|attorney work product|"
            r"trade secret|confidential and proprietary|not for public(?:ation)?|"
            r"internal only)\b"
        ),
        re.compile(
            r"(?i)\b(?:unpublished|non-public|confidential|draft)\s+"
            r"(?:patent(?: application)?|provisional application|claims?|"
            r"invention disclosure)\b"
        ),
        re.compile(
            r"(?i)\b(?:patent|provisional)\s+application\s+"
            r"(?:no\.?|number|#)\s*\d"
        ),
        re.compile(
            r"(?i)\bclaim\s+\d+\s*[:.)-]\s+"
            r"(?:a|an|the|wherein|comprising)\b"
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


def normalized_field_name(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def public_safety_findings(value: Any) -> set[str]:
    findings: set[str] = set()

    def scan_text(text: str) -> None:
        for label, patterns in PUBLIC_SAFETY_PATTERNS.items():
            if any(pattern.search(text) for pattern in patterns):
                findings.add(label)

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                field = normalized_field_name(key)
                if field in DIRECT_IDENTIFIER_FIELDS:
                    findings.add("direct identifier")
                if field in CREDENTIAL_FIELDS:
                    findings.add("credential or token")
                if field in PATENT_SENSITIVE_FIELDS:
                    findings.add("private or patent-sensitive content")
                scan_text(str(key))
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, str):
            scan_text(item)

    visit(value)
    return findings


def finite_limit(
    value: Any,
    *,
    field: str,
    errors: list[str],
    allow_zero: bool,
) -> float | None:
    qualifier = "non-negative" if allow_zero else "positive"
    if isinstance(value, bool):
        errors.append(f"{field} must be a finite {qualifier} number")
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        errors.append(f"{field} must be a finite {qualifier} number")
        return None
    if not math.isfinite(parsed) or parsed < 0 or (parsed == 0 and not allow_zero):
        errors.append(f"{field} must be a finite {qualifier} number")
        return None
    return parsed


def validate_json_domain(value: Any, *, field: str, errors: list[str]) -> None:
    """Reject values Python's permissive JSON codec accepts outside strict JSON."""
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                errors.append(f"{field} contains a non-string object key")
                continue
            validate_json_domain(child, field=f"{field} value", errors=errors)
        return
    if isinstance(value, list):
        for child in value:
            validate_json_domain(child, field=f"{field} item", errors=errors)
        return
    if isinstance(value, float) and not math.isfinite(value):
        errors.append(f"{field} contains a non-finite number")
        return
    if value is None or isinstance(value, (str, int, float, bool)):
        return
    errors.append(f"{field} contains a value outside the JSON data model")


def validate_exact_keys(
    value: Any,
    *,
    allowed: set[str],
    field: str,
    errors: list[str],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{field} must be an object")
        return {}
    keys = set(value)
    missing = sorted(allowed - keys)
    if missing:
        errors.append(f"{field} missing required keys: {', '.join(missing)}")
    if keys - allowed:
        errors.append(f"{field} contains unknown keys")
    return value


def verify_state(
    state: Any,
    *,
    now: datetime | None = None,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
    max_future_skew_minutes: float = DEFAULT_MAX_FUTURE_SKEW_MINUTES,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    safe_state = state if isinstance(state, dict) else {}
    validate_json_domain(state, field="control-plane state", errors=errors)
    validate_exact_keys(
        state,
        allowed=TOP_LEVEL_KEYS,
        field="control-plane state",
        errors=errors,
    )
    privacy_findings = public_safety_findings(safe_state)
    for label in sorted(privacy_findings):
        errors.append(f"public state contains prohibited {label}")

    state_id = str(safe_state.get("state_id") or "")
    state_id_valid = bool(STATE_ID_RE.fullmatch(state_id))
    if not state_id_valid:
        errors.append("state_id must use the public-safe canonical identifier format")

    if safe_state.get("schema") != SCHEMA:
        errors.append("unsupported or missing control-plane schema")
    if safe_state.get("authority") != "PUBLIC_SAFE_RECONCILIATION_NOT_ACTION_AUTHORITY":
        errors.append("authority must remain non-action-authorizing")
    if safe_state.get("failure_mode") != "FAIL_CLOSED":
        errors.append("failure_mode must be FAIL_CLOSED")
    if safe_state.get("hash_scope") != HASH_SCOPE:
        errors.append(
            "hash_scope must limit the embedded SHA-256 to self-consistency only"
        )
    if safe_state.get("custody_anchor") != CUSTODY_ANCHOR:
        errors.append(
            "custody_anchor must identify the Git commit or a receipt bound to that commit"
        )
    if safe_state.get("owner_role") != OWNER_ROLE:
        errors.append(f"owner_role must be {OWNER_ROLE}")
    if "owner" in safe_state:
        errors.append("owner must not publish a named person; use owner_role")

    source_cutoff = validate_exact_keys(
        safe_state.get("source_cutoff"),
        allowed=SOURCE_CUTOFF_KEYS,
        field="source_cutoff",
        errors=errors,
    )
    for key in sorted(SOURCE_CUTOFF_KEYS):
        parse_utc(source_cutoff.get(key), f"source_cutoff.{key}", errors)

    independent_findings = safe_state.get("independent_findings")
    if not isinstance(independent_findings, list) or not independent_findings:
        errors.append("independent_findings must be a non-empty array")
        independent_findings = []
    for index, finding in enumerate(independent_findings):
        prefix = f"independent_findings[{index}]"
        checked = validate_exact_keys(
            finding,
            allowed=INDEPENDENT_FINDING_KEYS,
            field=prefix,
            errors=errors,
        )
        for key in sorted(INDEPENDENT_FINDING_KEYS):
            if not str(checked.get(key) or "").strip():
                errors.append(f"{prefix}.{key} is required")

    generated = parse_utc(safe_state.get("generated_utc"), "generated_utc", errors)
    observed_now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
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

    raw_expected_hash = str(safe_state.get("state_sha256") or "").lower()
    expected_hash = raw_expected_hash if SHA256_RE.fullmatch(raw_expected_hash) else None
    computed_hash = stable_hash(state_payload(safe_state))
    hash_matches = expected_hash == computed_hash
    if not hash_matches:
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
        errors.append("controls contain unknown keys")
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
        validate_exact_keys(row, allowed=LANE_KEYS, field=prefix, errors=errors)
        lane_id = str(row.get("lane_id") or "").strip()
        if not lane_id:
            errors.append(f"{prefix}.lane_id is required")
        elif lane_id in lane_ids:
            errors.append(f"{prefix}.lane_id duplicates another lane_id")
        lane_ids.append(lane_id)

        priority = row.get("priority")
        if not isinstance(priority, int) or isinstance(priority, bool) or priority <= 0:
            errors.append(f"{prefix}.priority must be a positive integer")
        else:
            priorities.append(priority)

        lane_state = str(row.get("state") or "")
        if lane_state not in ALLOWED_STATES:
            errors.append(f"{prefix}.state is invalid")

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
                validate_exact_keys(
                    item,
                    allowed=EVIDENCE_KEYS,
                    field=eprefix,
                    errors=errors,
                )
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
    for index, item in enumerate(stale_sources):
        validate_exact_keys(
            item,
            allowed=STALE_SOURCE_KEYS,
            field=f"stale_or_conflicting_sources[{index}]",
            errors=errors,
        )
    for required_path in {
        "docs/CANONICAL_OPERATING_STATE.md",
        "dashboard/data/grant_readiness_status.json",
    }:
        if required_path not in stale_paths:
            errors.append(f"stale source register must include {required_path}")

    return {
        "schema": "lumencore.control_plane_verification_report.v1",
        "verified_utc": observed_now.isoformat(),
        "integrity_valid": not errors,
        "state_id": state_id if state_id_valid and not privacy_findings else "REDACTED",
        "lane_count": len(lanes),
        "required_lane_count": len(REQUIRED_LANES),
        "generated_age_hours": round(age_hours, 3) if age_hours is not None else None,
        "generated_future_skew_minutes": (
            round(future_skew_minutes, 3)
            if future_skew_minutes is not None
            else None
        ),
        "freshness_policy": {
            "max_age_hours": validated_max_age,
            "max_future_skew_minutes": validated_future_skew,
        },
        "state_hash": {
            "expected": expected_hash if hash_matches else None,
            "computed": computed_hash,
            "matches": hash_matches,
            "scope": "SELF_CONSISTENCY_ONLY_NOT_CUSTODY",
        },
        "custody": {
            "authoritative_anchor": CUSTODY_ANCHOR,
            "embedded_hash_is_custody_anchor": False,
        },
        "errors": errors,
        "warnings": warnings,
        "claim_boundary": (
            "This verifier checks structure, embedded-hash self-consistency, deadline "
            "locks, and fail-closed action boundaries of one public-safe coordination "
            "snapshot. The recomputable embedded hash is not a custody anchor. The "
            "authoritative custody/history anchor is the Git commit or a verification "
            "receipt that identifies that exact commit. "
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
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=DEFAULT_MAX_AGE_HOURS,
    )
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
