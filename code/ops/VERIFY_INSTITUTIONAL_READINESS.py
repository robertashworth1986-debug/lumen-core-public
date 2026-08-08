#!/usr/bin/env python3
"""Fail-closed verifier for the bounded LumenCore readiness register."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTER = ROOT / "config" / "institutional_readiness_register_v1.json"
DEFAULT_DOSSIER = ROOT / "docs" / "INSTITUTIONAL_READINESS_DOSSIER.md"

TOP_LEVEL_FIELDS = {
    "schema_version",
    "generated_utc",
    "repository",
    "register_scope",
    "current_decision",
    "production_decision",
    "live_exact_snapshot_status",
    "status_counts",
    "assurance_domains",
    "claim_boundaries",
}
DOMAIN_FIELDS = {
    "id",
    "title",
    "status",
    "owner",
    "evidence_paths",
    "proves",
    "does_not_prove",
    "next_gate",
}
ALLOWED_STATUSES = {
    "implemented_first_party",
    "documented_control",
    "prepared_not_executed",
    "buyer_specific_gate",
    "open_gap",
    "not_applicable_to_bounded_sprint",
}
EXPECTED_DOMAIN_STATUS = {
    "source_and_reproducibility": "implemented_first_party",
    "evidence_custody_and_claim_governance": "implemented_first_party",
    "security_reporting": "documented_control",
    "repository_supply_chain": "documented_control",
    "public_deployment": "prepared_not_executed",
    "data_rights_and_handling": "buyer_specific_gate",
    "identity_access_and_runtime": "prepared_not_executed",
    "incident_response_and_continuity": "open_gap",
    "legal_certification_and_insurance": "open_gap",
    "commercial_delivery": "prepared_not_executed",
    "external_validation": "prepared_not_executed",
    "privacy_and_regulated_data": "buyer_specific_gate",
}
REQUIRED_DOMAIN_NEGATIVES = {
    "source_and_reproducibility": "independent execution",
    "evidence_custody_and_claim_governance": "substantively true",
    "security_reporting": "security certification",
    "repository_supply_chain": "complete product sbom",
    "public_deployment": "currently matches the checked-out commit",
    "data_rights_and_handling": "executed data-processing agreement",
    "identity_access_and_runtime": "production secrets",
    "incident_response_and_continuity": "tested incident-response plan",
    "legal_certification_and_insurance": "soc 2",
    "commercial_delivery": "signed paid scope",
    "external_validation": "completed non-author execution",
    "privacy_and_regulated_data": "hipaa",
}
REQUIRED_CLAIM_BOUNDARIES = {
    "no_independent_validation",
    "no_field_validation",
    "no_customer_or_signed_paid_scope",
    "no_cleared_payment_or_revenue",
    "no_soc2_iso27001_fedramp_certification",
    "no_penetration_test",
    "no_enterprise_sla",
    "no_executed_dpa_or_legal_review",
    "no_complete_product_sbom",
    "no_exact_live_snapshot_established_for_checked_out_commit",
}
REQUIRED_DOSSIER_TEXT = (
    "Production decision: `HOLD`.",
    "Review-ready is not production-certified.",
    "a complete product and deployment SBOM",
    "a customer, signed paid scope, cleared payment, revenue, or market-tested price",
    "does not currently establish",
    "unverified convenience projection",
    "A green verifier or hash establishes only the named property",
    "isolated replay environment",
    "SOC 2, ISO 27001, FedRAMP",
)
FORBIDDEN_PROMOTION_TEXT = (
    "soc 2 certified",
    "iso 27001 certified",
    "fedramp authorized",
    "independently validated platform",
    "field-validated platform",
    "production-ready platform",
    "enterprise-ready platform",
    "paying customer secured",
    "revenue generated",
)


class ReadinessError(ValueError):
    """Raised when readiness evidence fails closed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReadinessError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise ReadinessError(f"non-finite JSON number: {value}")


def read_json(path: Path, *, max_bytes: int = 1_000_000) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise ReadinessError(f"register exceeds {max_bytes} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except UnicodeDecodeError as exc:
        raise ReadinessError("register is not valid UTF-8") from exc
    if not isinstance(value, dict):
        raise ReadinessError("register must be a JSON object")
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ReadinessError(f"{label} must be a trimmed non-empty string")
    return value


def parse_utc(value: str, label: str) -> str:
    require_text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReadinessError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ReadinessError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_evidence_path(root: Path, raw_value: Any, label: str) -> tuple[str, Path]:
    value = require_text(raw_value, label)
    if "\\" in value:
        raise ReadinessError(f"{label} must use canonical POSIX separators")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or value.startswith("./"):
        raise ReadinessError(f"{label} must be a canonical repository-relative path")
    if pure.as_posix() != value:
        raise ReadinessError(f"{label} is not canonical")
    root_resolved = root.resolve(strict=True)
    candidate = (root_resolved / Path(*pure.parts)).resolve(strict=True)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ReadinessError(f"{label} escapes the repository") from exc
    if not candidate.is_file():
        raise ReadinessError(f"{label} is not a regular file: {value}")
    return value, candidate


def _git_commit(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip().lower()
    if result.returncode == 0 and len(value) == 40 and all(c in "0123456789abcdef" for c in value):
        return value
    return None


def verify_register(
    *,
    root: Path = ROOT,
    register_path: Path = DEFAULT_REGISTER,
    dossier_path: Path = DEFAULT_DOSSIER,
    verified_utc: str | None = None,
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    register = read_json(register_path)

    if set(register) != TOP_LEVEL_FIELDS:
        raise ReadinessError("top-level register fields mismatch")
    if register["schema_version"] != "1.0":
        raise ReadinessError("schema_version must be 1.0")
    parse_utc(register["generated_utc"], "generated_utc")
    if register["repository"] != "robertashworth1986-debug/lumen-core-public":
        raise ReadinessError("canonical repository mismatch")
    if register["register_scope"] != "public_repository_and_bounded_validation_sprint":
        raise ReadinessError("register scope mismatch")
    if register["current_decision"] != "ready_for_non_confidential_fit_review_and_buyer_specific_scoping":
        raise ReadinessError("current decision exceeds the bounded review state")
    if register["production_decision"] != "HOLD":
        raise ReadinessError("production decision must remain HOLD")
    if register["live_exact_snapshot_status"] != "not_established_for_checked_out_commit":
        raise ReadinessError("live exact-snapshot status is falsely promoted")

    domains = register["assurance_domains"]
    if not isinstance(domains, list) or len(domains) != len(EXPECTED_DOMAIN_STATUS):
        raise ReadinessError("assurance domain set mismatch")

    evidence: dict[str, dict[str, Any]] = {}
    actual_statuses: Counter[str] = Counter()
    seen_ids: set[str] = set()
    for index, domain in enumerate(domains):
        label = f"assurance_domains[{index}]"
        if not isinstance(domain, dict) or set(domain) != DOMAIN_FIELDS:
            raise ReadinessError(f"{label} fields mismatch")
        domain_id = require_text(domain["id"], f"{label}.id")
        if domain_id in seen_ids:
            raise ReadinessError(f"duplicate assurance domain id: {domain_id}")
        seen_ids.add(domain_id)
        expected_status = EXPECTED_DOMAIN_STATUS.get(domain_id)
        if expected_status is None:
            raise ReadinessError(f"unknown assurance domain id: {domain_id}")
        status = domain["status"]
        if status not in ALLOWED_STATUSES:
            raise ReadinessError(f"invalid assurance status: {status}")
        if status != expected_status:
            raise ReadinessError(f"status promotion or drift for {domain_id}")
        actual_statuses[status] += 1
        if domain["owner"] != "founder_operator":
            raise ReadinessError(f"unsupported owner claim for {domain_id}")
        require_text(domain["title"], f"{label}.title")
        require_text(domain["proves"], f"{label}.proves")
        negative = require_text(domain["does_not_prove"], f"{label}.does_not_prove")
        require_text(domain["next_gate"], f"{label}.next_gate")
        required_negative = REQUIRED_DOMAIN_NEGATIVES[domain_id]
        if required_negative not in negative.lower():
            raise ReadinessError(
                f"required negative boundary missing for {domain_id}: {required_negative}"
            )
        combined_text = " ".join(
            str(domain[field]).lower()
            for field in ("proves", "does_not_prove", "next_gate")
        )
        for forbidden in FORBIDDEN_PROMOTION_TEXT:
            if forbidden in combined_text:
                raise ReadinessError(
                    f"unsupported promotion in {domain_id}: {forbidden}"
                )
        paths = domain["evidence_paths"]
        if not isinstance(paths, list) or not paths:
            raise ReadinessError(f"{label}.evidence_paths must be a non-empty list")
        if len(paths) != len(set(paths)):
            raise ReadinessError(f"{label}.evidence_paths contains a duplicate")
        for path_index, raw_path in enumerate(paths):
            relative, resolved = resolve_evidence_path(
                root, raw_path, f"{label}.evidence_paths[{path_index}]"
            )
            evidence.setdefault(
                relative,
                {"path": relative, "bytes": resolved.stat().st_size, "sha256": sha256_file(resolved)},
            )

    if seen_ids != set(EXPECTED_DOMAIN_STATUS):
        raise ReadinessError("required assurance domain missing")
    status_counts = register["status_counts"]
    if not isinstance(status_counts, dict) or set(status_counts) != ALLOWED_STATUSES:
        raise ReadinessError("status_counts fields mismatch")
    expected_counts = {status: actual_statuses.get(status, 0) for status in ALLOWED_STATUSES}
    if status_counts != expected_counts:
        raise ReadinessError("status_counts do not match assurance domains")

    boundaries = register["claim_boundaries"]
    if not isinstance(boundaries, list) or len(boundaries) != len(set(boundaries)):
        raise ReadinessError("claim_boundaries must be a unique list")
    if set(boundaries) != REQUIRED_CLAIM_BOUNDARIES:
        raise ReadinessError("required negative claim boundary missing or promoted")

    dossier_bytes = dossier_path.read_bytes()
    try:
        dossier = dossier_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReadinessError("dossier is not valid UTF-8") from exc
    lowered = dossier.lower()
    for required in REQUIRED_DOSSIER_TEXT:
        if required.lower() not in lowered:
            raise ReadinessError(f"dossier missing required boundary: {required}")
    for forbidden in FORBIDDEN_PROMOTION_TEXT:
        if forbidden in lowered:
            raise ReadinessError(f"dossier contains unsupported promotion: {forbidden}")

    verified = parse_utc(
        verified_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verified_utc",
    )
    evidence_files = [evidence[key] for key in sorted(evidence)]
    receipt = {
        "receipt_schema": "lumencore-institutional-readiness-receipt-v1",
        "valid": True,
        "verified_utc": verified,
        "commit": _git_commit(root),
        "institutional_pilot_decision": register["current_decision"],
        "production_decision": "HOLD",
        "live_exact_snapshot_status": register["live_exact_snapshot_status"],
        "assurance_domain_count": len(domains),
        "status_counts": status_counts,
        "claim_boundary_count": len(boundaries),
        "register_canonical_sha256": sha256_bytes(canonical_bytes(register)),
        "dossier_sha256": sha256_bytes(dossier_bytes),
        "evidence_file_count": len(evidence_files),
        "evidence_files": evidence_files,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER)
    parser.add_argument("--dossier", type=Path, default=DEFAULT_DOSSIER)
    parser.add_argument("--verified-utc")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        receipt = verify_register(
            root=args.root,
            register_path=args.register,
            dossier_path=args.dossier,
            verified_utc=args.verified_utc,
        )
    except (OSError, ReadinessError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
