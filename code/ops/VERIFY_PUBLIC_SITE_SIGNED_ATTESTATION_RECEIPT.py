#!/usr/bin/env python3
"""Fail-closed verifier for the retained public-site signed-attestation receipt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_COMMIT = "5fff567c11bee65b5b1de5415d8b8935cd2dfab0"
DEFAULT_RECEIPT = (
    ROOT
    / "evidence"
    / "public-site-supply-chain"
    / SOURCE_COMMIT
    / "attestation-receipt.json"
)
PACKAGER_PATH = ROOT / "code" / "deploy" / "package_public_site_release.py"
SHA256_LENGTH = 64
TOP_LEVEL_FIELDS = {
    "attestations",
    "claim_boundaries",
    "generated_utc",
    "live_domain_audit",
    "private_custody",
    "production_decision",
    "public_verification",
    "receipt_sha256",
    "repository",
    "schema",
    "signer_identity",
    "source_commit",
    "subject",
    "workflow_run",
}
ATTESTATION_FIELDS = {
    "independent_verification_sha256",
    "name",
    "predicate_type",
    "sigstore_bundle_sha256",
    "verification_state",
    "verified_timestamp_count",
    "workflow_verification_sha256",
}
EXPECTED_ATTESTATIONS = {
    "build_provenance": {
        "predicate_type": "https://slsa.dev/provenance/v1",
        "sigstore_bundle_sha256": "9ed7cffc70e2878920647f51d280676516aa742d2c9eb5cc07c58e2d844a3f69",
        "workflow_verification_sha256": "80bdeb6caff833c4074fad016b515320688a4b82a9147daa5996ae5235e299fd",
        "independent_verification_sha256": "e2ec2d55ff683ec6b00e97d556bc7566dfd577d54eb58287fcb196d3280a23fe",
    },
    "cyclonedx_sbom": {
        "predicate_type": "https://cyclonedx.org/bom",
        "sigstore_bundle_sha256": "461de8b8ecaf4fbd5b94ca79e84fdcaf43329e5345b2600b4f2828c8f6faed8f",
        "workflow_verification_sha256": "6d1e8cded80ad579cf101a45d63f9300a0956a62c494016d0177cd94d8f5698d",
        "independent_verification_sha256": "647250b6b94382b813a542987571b09af3145ef3a247b63b059d89c02b412aa8",
    },
}


class SignedAttestationReceiptError(ValueError):
    """Raised when retained signed-attestation evidence fails closed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SignedAttestationReceiptError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> None:
    raise SignedAttestationReceiptError(f"non-finite JSON number: {value}")


def read_json(path: Path, *, max_bytes: int = 1_000_000) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise SignedAttestationReceiptError("receipt must be a regular non-symlink file")
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise SignedAttestationReceiptError(f"receipt exceeds {max_bytes} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except UnicodeDecodeError as exc:
        raise SignedAttestationReceiptError("receipt is not valid UTF-8") from exc
    if not isinstance(value, dict):
        raise SignedAttestationReceiptError("receipt must be a JSON object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def exact_render(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SignedAttestationReceiptError(f"{label} must be a lowercase SHA-256")
    return value


def parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SignedAttestationReceiptError(f"{label} must be a trimmed timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SignedAttestationReceiptError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise SignedAttestationReceiptError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _load_packager(root: Path):
    path = root / "code" / "deploy" / "package_public_site_release.py"
    spec = importlib.util.spec_from_file_location("signed_receipt_release_packager", path)
    if spec is None or spec.loader is None:
        raise SignedAttestationReceiptError("cannot load public-site release packager")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require_exact_fields(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise SignedAttestationReceiptError(f"{label} fields mismatch")
    return value


def verify_receipt(*, root: Path = ROOT, receipt_path: Path = DEFAULT_RECEIPT) -> dict[str, Any]:
    root = root.resolve(strict=True)
    receipt = read_json(receipt_path)
    _require_exact_fields(receipt, TOP_LEVEL_FIELDS, "top-level receipt")
    if receipt_path.read_bytes() != exact_render(receipt):
        raise SignedAttestationReceiptError("receipt serialization drift")
    if receipt["schema"] != "lumencore.public_site_signed_attestation_receipt.v1":
        raise SignedAttestationReceiptError("receipt schema mismatch")
    if receipt["repository"] != "robertashworth1986-debug/lumen-core-public":
        raise SignedAttestationReceiptError("repository identity mismatch")
    if receipt["source_commit"] != SOURCE_COMMIT:
        raise SignedAttestationReceiptError("source commit mismatch")
    claimed_self_hash = require_sha256(receipt["receipt_sha256"], "receipt_sha256")
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if claimed_self_hash != sha256_bytes(canonical_bytes(unhashed)):
        raise SignedAttestationReceiptError("receipt self-hash mismatch")

    generated = parse_utc(receipt["generated_utc"], "generated_utc")
    boundaries = receipt["claim_boundaries"]
    if not isinstance(boundaries, list) or len(boundaries) != 3 or len(set(boundaries)) != 3:
        raise SignedAttestationReceiptError("claim boundaries mismatch")
    normalized_boundaries = " ".join(str(item).lower() for item in boundaries)
    for phrase in (
        "not itself a signature or independent technical validation",
        "do not establish a slsa level",
        "signed archive has not been proven deployed",
        "live domain remains on hold",
    ):
        if phrase not in normalized_boundaries:
            raise SignedAttestationReceiptError(f"claim boundary missing: {phrase}")

    subject = _require_exact_fields(
        receipt["subject"],
        {
            "bytes",
            "cyclonedx_component_count",
            "cyclonedx_spec_version",
            "name",
            "release_file_count",
            "sha256",
        },
        "subject",
    )
    if subject["name"] != "public-site-release.tar":
        raise SignedAttestationReceiptError("archive subject name mismatch")
    if subject["cyclonedx_spec_version"] != "1.6":
        raise SignedAttestationReceiptError("CycloneDX version mismatch")
    if subject["release_file_count"] != 30 or subject["cyclonedx_component_count"] != 30:
        raise SignedAttestationReceiptError("exact release inventory coverage mismatch")
    subject_hash = require_sha256(subject["sha256"], "subject.sha256")

    packager = _load_packager(root)
    try:
        with tempfile.TemporaryDirectory(prefix="lumencore-signed-receipt-") as temporary:
            temporary_root = Path(temporary)
            archive = temporary_root / "public-site-release.tar"
            manifest_path = temporary_root / "public-site-release-manifest.json"
            manifest = packager.build_release_package(
                repo_root=root,
                source_commit=SOURCE_COMMIT,
                archive_path=archive,
                manifest_path=manifest_path,
            )
            if archive.stat().st_size != subject["bytes"]:
                raise SignedAttestationReceiptError("archive subject byte count mismatch")
            if sha256_bytes(archive.read_bytes()) != subject_hash:
                raise SignedAttestationReceiptError("archive subject hash mismatch")
            if manifest["archive_sha256"] != subject_hash:
                raise SignedAttestationReceiptError("manifest archive hash mismatch")
            if manifest["file_count"] != subject["release_file_count"]:
                raise SignedAttestationReceiptError("manifest file count mismatch")
    except (OSError, packager.ReleasePackageError) as exc:
        raise SignedAttestationReceiptError(str(exc)) from exc

    attestations = receipt["attestations"]
    if not isinstance(attestations, list) or len(attestations) != 2:
        raise SignedAttestationReceiptError("attestation set mismatch")
    seen_attestations: set[str] = set()
    for index, raw_attestation in enumerate(attestations):
        attestation = _require_exact_fields(
            raw_attestation, ATTESTATION_FIELDS, f"attestations[{index}]"
        )
        name = attestation["name"]
        if name in seen_attestations or name not in EXPECTED_ATTESTATIONS:
            raise SignedAttestationReceiptError("attestation identity mismatch")
        seen_attestations.add(name)
        expected = EXPECTED_ATTESTATIONS[name]
        for field, expected_value in expected.items():
            if field.endswith("sha256"):
                require_sha256(attestation[field], f"{name}.{field}")
            if attestation[field] != expected_value:
                raise SignedAttestationReceiptError(f"{name}.{field} mismatch")
        if attestation["verification_state"] != "VERIFIED":
            raise SignedAttestationReceiptError(f"{name} is not verified")
        timestamp_count = attestation["verified_timestamp_count"]
        if not isinstance(timestamp_count, int) or isinstance(timestamp_count, bool) or timestamp_count < 1:
            raise SignedAttestationReceiptError(f"{name} lacks a verified timestamp")
    if seen_attestations != set(EXPECTED_ATTESTATIONS):
        raise SignedAttestationReceiptError("required attestation missing")

    public = _require_exact_fields(
        receipt["public_verification"],
        {
            "cli",
            "oidc_issuer_bound",
            "online_lookup_verified",
            "repository_bound",
            "self_hosted_runners_denied",
            "signer_workflow_bound",
            "source_commit_bound",
            "source_ref_bound",
        },
        "public_verification",
    )
    if public["cli"] != "gh attestation verify":
        raise SignedAttestationReceiptError("public verification CLI mismatch")
    for field, value in public.items():
        if field != "cli" and value is not True:
            raise SignedAttestationReceiptError(f"public verification binding false: {field}")

    signer = _require_exact_fields(
        receipt["signer_identity"],
        {
            "certificate_issuer",
            "issuer",
            "runner_environment",
            "source_repository_ref",
            "subject_alternative_name",
            "workflow_trigger",
        },
        "signer_identity",
    )
    expected_signer = {
        "certificate_issuer": "CN=sigstore-intermediate,O=sigstore.dev",
        "issuer": "https://token.actions.githubusercontent.com",
        "runner_environment": "github-hosted",
        "source_repository_ref": "refs/heads/main",
        "subject_alternative_name": "https://github.com/robertashworth1986-debug/lumen-core-public/.github/workflows/public-site-supply-chain.yml@refs/heads/main",
        "workflow_trigger": "push",
    }
    if signer != expected_signer:
        raise SignedAttestationReceiptError("signer identity mismatch")

    workflow = _require_exact_fields(
        receipt["workflow_run"],
        {
            "attempt",
            "completed_utc",
            "conclusion",
            "created_utc",
            "event",
            "id",
            "url",
            "workflow_name",
            "workflow_path",
        },
        "workflow_run",
    )
    expected_workflow = {
        "attempt": 1,
        "conclusion": "success",
        "event": "push",
        "id": 31259179162,
        "url": "https://github.com/robertashworth1986-debug/lumen-core-public/actions/runs/31259179162",
        "workflow_name": "Public site supply-chain assurance",
        "workflow_path": ".github/workflows/public-site-supply-chain.yml",
    }
    for field, expected_value in expected_workflow.items():
        if workflow[field] != expected_value:
            raise SignedAttestationReceiptError(f"workflow_run.{field} mismatch")
    created = parse_utc(workflow["created_utc"], "workflow_run.created_utc")
    completed = parse_utc(workflow["completed_utc"], "workflow_run.completed_utc")
    if not created < completed <= generated:
        raise SignedAttestationReceiptError("workflow timestamps are not monotonic")

    custody = _require_exact_fields(
        receipt["private_custody"],
        {
            "bundle_storage",
            "preserved_sha256_manifest_sha256",
            "repository_contains_private_bundle_bytes",
        },
        "private_custody",
    )
    if custody["bundle_storage"] != "FOUNDER_CONTROLLED_E_DRIVE_VAULT":
        raise SignedAttestationReceiptError("private custody location mismatch")
    require_sha256(
        custody["preserved_sha256_manifest_sha256"],
        "private_custody.preserved_sha256_manifest_sha256",
    )
    if custody["repository_contains_private_bundle_bytes"] is not False:
        raise SignedAttestationReceiptError("public repository cannot claim private bundle bytes")

    live = _require_exact_fields(
        receipt["live_domain_audit"],
        {
            "checked_utc",
            "error_count",
            "expected_file_count",
            "incident_receipt_sha256",
            "incident_state",
            "matched_file_count",
            "mismatch_count",
            "production_decision",
            "release_verified",
            "severity",
        },
        "live_domain_audit",
    )
    if parse_utc(live["checked_utc"], "live_domain_audit.checked_utc") != generated:
        raise SignedAttestationReceiptError("live audit timestamp mismatch")
    if (
        live["expected_file_count"] != 30
        or live["matched_file_count"] != 16
        or live["mismatch_count"] != 12
        or live["error_count"] != 2
        or live["matched_file_count"] + live["mismatch_count"] + live["error_count"]
        != live["expected_file_count"]
    ):
        raise SignedAttestationReceiptError("live audit count mismatch")
    if (
        live["incident_state"] != "ACTIVE_PUBLIC_RELEASE_INTEGRITY_INCIDENT"
        or live["production_decision"] != "HOLD_PUBLIC_RELEASE_PROMOTION"
        or live["release_verified"] is not False
        or live["severity"] != "SEV-2"
    ):
        raise SignedAttestationReceiptError("live domain was falsely promoted")
    require_sha256(live["incident_receipt_sha256"], "live_domain_audit.incident_receipt_sha256")
    if receipt["production_decision"] != (
        "HOLD_UNTIL_EXPLICIT_DEPLOYMENT_AND_EXACT_LIVE_VERIFICATION"
    ):
        raise SignedAttestationReceiptError("production decision was falsely promoted")

    verification: dict[str, Any] = {
        "schema": "lumencore.public_site_signed_attestation_receipt_verification.v1",
        "valid": True,
        "repository": receipt["repository"],
        "source_commit": SOURCE_COMMIT,
        "receipt_sha256": claimed_self_hash,
        "subject_sha256": subject_hash,
        "release_file_count": subject["release_file_count"],
        "attestation_count": len(attestations),
        "verified_predicate_types": sorted(
            item["predicate_type"] for item in attestations
        ),
        "production_decision": receipt["production_decision"],
        "live_release_verified": False,
        "claim_boundary": (
            "This local verifier checks the retained first-party receipt and reconstructs its "
            "exact Git-bound archive. It does not reverify the remote signatures, establish a "
            "SLSA level, certify security, or prove production deployment; use the constrained "
            "gh attestation verify commands in the reviewer guide for remote verification."
        ),
    }
    verification["verification_sha256"] = sha256_bytes(canonical_bytes(verification))
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        verification = verify_receipt(root=args.root, receipt_path=args.receipt)
    except (OSError, SignedAttestationReceiptError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    rendered = json.dumps(verification, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
