#!/usr/bin/env python3
"""Fail-closed verifier for the LumenCore institutional assurance crosswalk."""

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
DEFAULT_CROSSWALK = ROOT / "config" / "institutional_assurance_crosswalk_v1.json"
DEFAULT_GUIDE = ROOT / "docs" / "INSTITUTIONAL_ASSURANCE_CROSSWALK.md"
DEFAULT_WORKFLOW = ROOT / ".github" / "workflows" / "institutional-assurance-crosswalk.yml"

TOP_LEVEL_FIELDS = {
    "schema_version",
    "generated_utc",
    "repository",
    "scope",
    "assessment_type",
    "assurance_statement",
    "status_vocabulary",
    "status_counts",
    "frameworks",
    "controls",
    "claim_boundaries",
}
FRAMEWORK_FIELDS = {
    "id",
    "title",
    "version",
    "publication_date",
    "official_url",
    "reference_use",
    "not_claimed",
}
CONTROL_FIELDS = {
    "id",
    "topic",
    "status",
    "framework_mappings",
    "evidence_paths",
    "evidence_establishes",
    "evidence_does_not_establish",
    "next_gate",
}
MAPPING_FIELDS = {"framework_id", "reference_points"}
ALLOWED_STATUSES = {
    "implemented_first_party",
    "documented_control",
    "partial_or_scoped",
    "prepared_not_executed",
    "buyer_specific_gate",
    "open_gap",
}
EXPECTED_FRAMEWORKS = {
    "nist_ai_rmf_1_0": {
        "version": "AI RMF 1.0 / NIST AI 100-1",
        "publication_date": "2023-01-26",
        "official_url": "https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10",
    },
    "nist_ai_600_1": {
        "version": "NIST AI 600-1",
        "publication_date": "2024-07-26",
        "official_url": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf",
    },
    "nist_csf_2_0": {
        "version": "CSF 2.0 / NIST CSWP 29",
        "publication_date": "2024-02-26",
        "official_url": "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf",
    },
    "nist_ssdf_1_1": {
        "version": "SSDF 1.1 / NIST SP 800-218 final",
        "publication_date": "2022-02-03",
        "official_url": "https://csrc.nist.gov/pubs/sp/800/218/final",
    },
    "owasp_asvs_5_0_0": {
        "version": "ASVS 5.0.0",
        "publication_date": "2025-05-30",
        "official_url": "https://owasp.org/www-project-application-security-verification-standard/",
    },
    "owasp_llmsvs_2_0": {
        "version": "LLMSVS 2.0",
        "publication_date": "2026-06-15",
        "official_url": "https://owasp.org/www-project-llm-verification-standard/LLMSVS-v2.0-en.html",
    },
    "slsa_1_2": {
        "version": "SLSA 1.2 approved specification",
        "publication_date": "2025-11-24",
        "official_url": "https://slsa.dev/spec/v1.2/",
    },
}
EXPECTED_CONTROL_STATUS = {
    "AC-01": "implemented_first_party",
    "AC-02": "implemented_first_party",
    "AC-03": "buyer_specific_gate",
    "AC-04": "partial_or_scoped",
    "AC-05": "partial_or_scoped",
    "AC-06": "partial_or_scoped",
    "AC-07": "partial_or_scoped",
    "AC-08": "documented_control",
    "AC-09": "documented_control",
    "AC-10": "partial_or_scoped",
    "AC-11": "partial_or_scoped",
    "AC-12": "buyer_specific_gate",
    "AC-13": "prepared_not_executed",
    "AC-14": "open_gap",
}
REQUIRED_CONTROL_NEGATIVES = {
    "AC-01": "production authorization",
    "AC-02": "independent scientific validation",
    "AC-03": "data-processing agreement",
    "AC-04": "full ssdf",
    "AC-05": "complete product",
    "AC-06": "slsa build",
    "AC-07": "production secret",
    "AC-08": "penetration test",
    "AC-09": "live recovery exercise",
    "AC-10": "asvs level",
    "AC-11": "llmsvs level",
    "AC-12": "hipaa",
    "AC-13": "completed non-author execution",
    "AC-14": "soc 2",
}
REQUIRED_CLAIM_BOUNDARIES = {
    "not_a_certification_or_attestation",
    "not_full_framework_conformance",
    "not_an_external_audit",
    "not_a_penetration_test",
    "not_a_complete_product_or_deployment_sbom",
    "not_a_slsa_level_or_complete_product_provenance",
    "not_a_live_recovery_exercise",
    "not_an_executed_dpa_or_legal_review",
    "not_regulated_data_authorization",
    "not_independent_or_field_validation",
    "not_customer_acceptance_or_revenue",
    "not_production_authorization",
}
REQUIRED_GUIDE_TEXT = (
    "first-party, informative, evidence-linked",
    "Production decision:** `HOLD`",
    "do **not** establish certification",
    "not claimed certifications or conformance",
    "NIST states AI RMF 1.0 is being revised",
    "SSDF 1.2 remains draft",
    "No ASVS level",
    "No LLMSVS level",
    "No Source or Build level",
    "A green receipt establishes only",
    "We do not claim certification or full conformance",
)
REQUIRED_WORKFLOW_TEXT = (
    "permissions:\n  contents: read",
    "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
    "persist-credentials: false",
    "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
    "python code/ops/VERIFY_INSTITUTIONAL_ASSURANCE_CROSSWALK.py",
    "--json-out out/institutional-assurance-crosswalk/receipt.json",
    "test_institutional_assurance_crosswalk.py",
    "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    "git diff --check",
)
FORBIDDEN_ESTABLISHES_TEXT = (
    "fully conforms",
    "nist certified",
    "owasp certified",
    "slsa build l1 achieved",
    "slsa build l2 achieved",
    "slsa build l3 achieved",
    "soc 2 certified",
    "iso 27001 certified",
    "fedramp authorized",
    "independently validated",
    "field validated",
    "production authorized",
)


class AssuranceCrosswalkError(ValueError):
    """Raised when the assurance crosswalk fails closed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AssuranceCrosswalkError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise AssuranceCrosswalkError(f"non-finite JSON number: {value}")


def read_json(path: Path, *, max_bytes: int = 1_000_000) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise AssuranceCrosswalkError(f"crosswalk exceeds {max_bytes} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except UnicodeDecodeError as exc:
        raise AssuranceCrosswalkError("crosswalk is not valid UTF-8") from exc
    if not isinstance(value, dict):
        raise AssuranceCrosswalkError("crosswalk must be a JSON object")
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
        raise AssuranceCrosswalkError(f"{label} must be a trimmed non-empty string")
    return value


def parse_utc(value: str, label: str) -> str:
    require_text(value, label)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssuranceCrosswalkError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise AssuranceCrosswalkError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_date(value: Any, label: str) -> str:
    text = require_text(value, label)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise AssuranceCrosswalkError(f"{label} must be YYYY-MM-DD") from exc


def resolve_evidence_path(root: Path, raw_value: Any, label: str) -> tuple[str, Path]:
    value = require_text(raw_value, label)
    if "\\" in value:
        raise AssuranceCrosswalkError(f"{label} must use POSIX separators")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or value.startswith("./"):
        raise AssuranceCrosswalkError(f"{label} must be a repository-relative path")
    if pure.as_posix() != value:
        raise AssuranceCrosswalkError(f"{label} is not canonical")
    root_resolved = root.resolve(strict=True)
    candidate = (root_resolved / Path(*pure.parts)).resolve(strict=True)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise AssuranceCrosswalkError(f"{label} escapes the repository") from exc
    if not candidate.is_file():
        raise AssuranceCrosswalkError(f"{label} is not a regular file: {value}")
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


def _read_required_text(path: Path, label: str) -> tuple[bytes, str]:
    raw = path.read_bytes()
    try:
        return raw, raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssuranceCrosswalkError(f"{label} is not valid UTF-8") from exc


def verify_crosswalk(
    *,
    root: Path = ROOT,
    crosswalk_path: Path = DEFAULT_CROSSWALK,
    guide_path: Path = DEFAULT_GUIDE,
    workflow_path: Path = DEFAULT_WORKFLOW,
    verified_utc: str | None = None,
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    crosswalk = read_json(crosswalk_path)

    if set(crosswalk) != TOP_LEVEL_FIELDS:
        raise AssuranceCrosswalkError("top-level crosswalk fields mismatch")
    if crosswalk["schema_version"] != "1.0":
        raise AssuranceCrosswalkError("schema_version must be 1.0")
    parse_utc(crosswalk["generated_utc"], "generated_utc")
    if crosswalk["repository"] != "robertashworth1986-debug/lumen-core-public":
        raise AssuranceCrosswalkError("canonical repository mismatch")
    if crosswalk["scope"] != "public_repository_and_bounded_validation_sprint":
        raise AssuranceCrosswalkError("crosswalk scope mismatch")
    if crosswalk["assessment_type"] != "first_party_informative_crosswalk":
        raise AssuranceCrosswalkError("assessment type must remain first-party and informative")
    assurance_statement = require_text(crosswalk["assurance_statement"], "assurance_statement")
    for required in ("not a certification", "not", "full framework conformance"):
        if required not in assurance_statement.lower():
            raise AssuranceCrosswalkError(f"assurance statement missing boundary: {required}")

    vocabulary = crosswalk["status_vocabulary"]
    if not isinstance(vocabulary, dict) or set(vocabulary) != ALLOWED_STATUSES:
        raise AssuranceCrosswalkError("status_vocabulary fields mismatch")
    for status, definition in vocabulary.items():
        require_text(definition, f"status_vocabulary.{status}")

    frameworks = crosswalk["frameworks"]
    if not isinstance(frameworks, list) or len(frameworks) != len(EXPECTED_FRAMEWORKS):
        raise AssuranceCrosswalkError("framework set mismatch")
    seen_frameworks: set[str] = set()
    for index, framework in enumerate(frameworks):
        label = f"frameworks[{index}]"
        if not isinstance(framework, dict) or set(framework) != FRAMEWORK_FIELDS:
            raise AssuranceCrosswalkError(f"{label} fields mismatch")
        framework_id = require_text(framework["id"], f"{label}.id")
        if framework_id in seen_frameworks:
            raise AssuranceCrosswalkError(f"duplicate framework id: {framework_id}")
        seen_frameworks.add(framework_id)
        expected = EXPECTED_FRAMEWORKS.get(framework_id)
        if expected is None:
            raise AssuranceCrosswalkError(f"unknown framework id: {framework_id}")
        for field in ("version", "publication_date", "official_url"):
            if framework[field] != expected[field]:
                raise AssuranceCrosswalkError(f"official framework {field} drift for {framework_id}")
        parse_date(framework["publication_date"], f"{label}.publication_date")
        require_text(framework["title"], f"{label}.title")
        require_text(framework["reference_use"], f"{label}.reference_use")
        negative = require_text(framework["not_claimed"], f"{label}.not_claimed")
        if not any(term in negative.lower() for term in ("not", "no ")):
            raise AssuranceCrosswalkError(f"{label}.not_claimed must preserve a negative boundary")
    if seen_frameworks != set(EXPECTED_FRAMEWORKS):
        raise AssuranceCrosswalkError("required framework missing")

    controls = crosswalk["controls"]
    if not isinstance(controls, list) or len(controls) != len(EXPECTED_CONTROL_STATUS):
        raise AssuranceCrosswalkError("control set mismatch")
    status_counter: Counter[str] = Counter()
    seen_controls: set[str] = set()
    evidence: dict[str, dict[str, Any]] = {}
    for index, control in enumerate(controls):
        label = f"controls[{index}]"
        if not isinstance(control, dict) or set(control) != CONTROL_FIELDS:
            raise AssuranceCrosswalkError(f"{label} fields mismatch")
        control_id = require_text(control["id"], f"{label}.id")
        if control_id in seen_controls:
            raise AssuranceCrosswalkError(f"duplicate control id: {control_id}")
        seen_controls.add(control_id)
        expected_status = EXPECTED_CONTROL_STATUS.get(control_id)
        if expected_status is None:
            raise AssuranceCrosswalkError(f"unknown control id: {control_id}")
        status = control["status"]
        if status not in ALLOWED_STATUSES:
            raise AssuranceCrosswalkError(f"invalid control status: {status}")
        if status != expected_status:
            raise AssuranceCrosswalkError(f"status promotion or drift for {control_id}")
        status_counter[status] += 1
        require_text(control["topic"], f"{label}.topic")
        establishes = require_text(control["evidence_establishes"], f"{label}.evidence_establishes")
        negative = require_text(
            control["evidence_does_not_establish"],
            f"{label}.evidence_does_not_establish",
        )
        require_text(control["next_gate"], f"{label}.next_gate")
        required_negative = REQUIRED_CONTROL_NEGATIVES[control_id]
        if required_negative not in negative.lower():
            raise AssuranceCrosswalkError(
                f"required negative boundary missing for {control_id}: {required_negative}"
            )
        for forbidden in FORBIDDEN_ESTABLISHES_TEXT:
            if forbidden in establishes.lower():
                raise AssuranceCrosswalkError(
                    f"unsupported assurance promotion in {control_id}: {forbidden}"
                )

        mappings = control["framework_mappings"]
        if not isinstance(mappings, list) or not mappings:
            raise AssuranceCrosswalkError(f"{label}.framework_mappings must be non-empty")
        mapped_frameworks: set[str] = set()
        for mapping_index, mapping in enumerate(mappings):
            mapping_label = f"{label}.framework_mappings[{mapping_index}]"
            if not isinstance(mapping, dict) or set(mapping) != MAPPING_FIELDS:
                raise AssuranceCrosswalkError(f"{mapping_label} fields mismatch")
            framework_id = require_text(mapping["framework_id"], f"{mapping_label}.framework_id")
            if framework_id not in EXPECTED_FRAMEWORKS:
                raise AssuranceCrosswalkError(f"unknown framework reference: {framework_id}")
            if framework_id in mapped_frameworks:
                raise AssuranceCrosswalkError(f"duplicate framework mapping in {control_id}")
            mapped_frameworks.add(framework_id)
            points = mapping["reference_points"]
            if not isinstance(points, list) or not points or len(points) != len(set(points)):
                raise AssuranceCrosswalkError(f"{mapping_label}.reference_points must be unique")
            for point_index, point in enumerate(points):
                require_text(point, f"{mapping_label}.reference_points[{point_index}]")

        paths = control["evidence_paths"]
        if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
            raise AssuranceCrosswalkError(f"{label}.evidence_paths must be unique and non-empty")
        for path_index, raw_path in enumerate(paths):
            relative, resolved = resolve_evidence_path(
                root,
                raw_path,
                f"{label}.evidence_paths[{path_index}]",
            )
            evidence.setdefault(
                relative,
                {
                    "path": relative,
                    "bytes": resolved.stat().st_size,
                    "sha256": sha256_file(resolved),
                },
            )
    if seen_controls != set(EXPECTED_CONTROL_STATUS):
        raise AssuranceCrosswalkError("required control missing")

    status_counts = crosswalk["status_counts"]
    if not isinstance(status_counts, dict) or set(status_counts) != ALLOWED_STATUSES:
        raise AssuranceCrosswalkError("status_counts fields mismatch")
    expected_counts = {status: status_counter.get(status, 0) for status in ALLOWED_STATUSES}
    if status_counts != expected_counts:
        raise AssuranceCrosswalkError("status_counts do not match controls")
    if status_counts["open_gap"] < 1:
        raise AssuranceCrosswalkError("at least one open gap is required")

    boundaries = crosswalk["claim_boundaries"]
    if not isinstance(boundaries, list) or len(boundaries) != len(set(boundaries)):
        raise AssuranceCrosswalkError("claim_boundaries must be a unique list")
    if set(boundaries) != REQUIRED_CLAIM_BOUNDARIES:
        raise AssuranceCrosswalkError("required claim boundary missing or promoted")

    guide_bytes, guide = _read_required_text(guide_path, "guide")
    guide_normalized = guide.replace("\r\n", "\n")
    for required in REQUIRED_GUIDE_TEXT:
        if required.lower() not in guide_normalized.lower():
            raise AssuranceCrosswalkError(f"guide missing required limitation: {required}")
    workflow_bytes, workflow = _read_required_text(workflow_path, "workflow")
    workflow_normalized = workflow.replace("\r\n", "\n")
    for required in REQUIRED_WORKFLOW_TEXT:
        if required not in workflow_normalized:
            raise AssuranceCrosswalkError(f"workflow binding missing: {required}")

    verified = parse_utc(
        verified_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verified_utc",
    )
    evidence_files = [evidence[key] for key in sorted(evidence)]
    receipt = {
        "receipt_schema": "lumencore-institutional-assurance-crosswalk-receipt-v1",
        "valid": True,
        "verified_utc": verified,
        "commit": _git_commit(root),
        "assessment_type": crosswalk["assessment_type"],
        "production_decision": "HOLD",
        "framework_count": len(frameworks),
        "control_count": len(controls),
        "status_counts": status_counts,
        "claim_boundary_count": len(boundaries),
        "crosswalk_canonical_sha256": sha256_bytes(canonical_bytes(crosswalk)),
        "guide_sha256": sha256_bytes(guide_bytes),
        "workflow_sha256": sha256_bytes(workflow_bytes),
        "evidence_file_count": len(evidence_files),
        "evidence_files": evidence_files,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--crosswalk", type=Path, default=DEFAULT_CROSSWALK)
    parser.add_argument("--guide", type=Path, default=DEFAULT_GUIDE)
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--verified-utc")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        receipt = verify_crosswalk(
            root=args.root,
            crosswalk_path=args.crosswalk,
            guide_path=args.guide,
            workflow_path=args.workflow,
            verified_utc=args.verified_utc,
        )
    except (OSError, AssuranceCrosswalkError, json.JSONDecodeError) as exc:
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
