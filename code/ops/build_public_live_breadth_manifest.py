from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "dashboard" / "data" / "public_live_breadth_manifest.json"
DEFAULT_MARKDOWN = ROOT / "docs" / "PUBLIC_LIVE_BREADTH_MANIFEST_2026-08-08.md"
SOURCE_NAMESPACE = "lumencore-public-live-breadth-v1"

RIGHTS_STATUSES = {"verified_for_review", "internal_only", "restricted", "unknown"}
RELEVANCE_STATUSES = {"verified", "not_relevant", "unknown"}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def source_ref(source: str) -> str:
    digest = sha256_bytes(f"{SOURCE_NAMESPACE}:{source}".encode("utf-8"))
    return f"source-{digest[:16]}"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def load_governance(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"schema": "public_live_breadth_governance_v1", "sources": {}}
    payload = load_json(path)
    sources = payload.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("Governance sidecar must contain a 'sources' object")
    return payload


def governance_sha256(governance: dict[str, Any]) -> str:
    payload = deepcopy(governance)
    integrity = payload.setdefault("integrity", {})
    integrity.pop("governance_sha256", None)
    return sha256_bytes(canonical_bytes(payload))


def seal_governance(governance: dict[str, Any]) -> dict[str, Any]:
    sealed = deepcopy(governance)
    integrity = sealed.setdefault("integrity", {})
    integrity["algorithm"] = "sha256"
    integrity["canonicalization"] = "utf8-json-sort-keys-compact"
    integrity["hash_scope"] = "entire governance sidecar excluding integrity.governance_sha256"
    integrity["governance_sha256"] = governance_sha256(sealed)
    return sealed


def validate_governance(
    governance: dict[str, Any], registry_sha256: str
) -> dict[str, Any]:
    issues: list[str] = []
    sources = governance.get("sources")
    protocol = governance.get("protocol")
    integrity = governance.get("integrity")

    if (
        sources == {}
        and protocol is None
        and integrity is None
        and governance.get("registry_sha256") is None
    ):
        return {
            "valid": False,
            "issues": ["governance_not_supplied"],
            "governance_sha256": None,
        }

    if governance.get("schema") != "public_live_breadth_governance_v1":
        issues.append("unsupported_governance_schema")
    if not isinstance(sources, dict) or not sources:
        issues.append("missing_governance_sources")
    if strict_sha256(governance.get("registry_sha256")) != registry_sha256.lower():
        issues.append("registry_hash_mismatch")
    if not isinstance(protocol, dict):
        issues.append("missing_protocol_review")
    else:
        if protocol.get("approval_status") != "approved":
            issues.append("protocol_not_approved")
        if not str(protocol.get("reviewed_by_role") or "").strip():
            issues.append("missing_reviewer_role")
        if parse_utc(protocol.get("reviewed_utc")) is None:
            issues.append("missing_or_invalid_reviewed_utc")
        if strict_sha256(protocol.get("worklist_sha256")) is None:
            issues.append("missing_or_invalid_worklist_sha256")
    if not isinstance(integrity, dict):
        issues.append("missing_governance_integrity")
    else:
        expected = strict_sha256(integrity.get("governance_sha256"))
        if expected is None or expected != governance_sha256(governance):
            issues.append("governance_hash_mismatch")

    return {
        "valid": not issues,
        "issues": sorted(set(issues)),
        "governance_sha256": (
            integrity.get("governance_sha256") if isinstance(integrity, dict) else None
        ),
    }


def safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def safe_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def strict_sha256(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if len(normalized) != 64:
        return None
    if any(char not in "0123456789abcdef" for char in normalized):
        return None
    return normalized


def age_hours(earlier: datetime | None, later: datetime) -> float | None:
    if earlier is None:
        return None
    return round(max(0.0, (later - earlier).total_seconds() / 3600.0), 4)


def classify_probe(row: dict[str, Any]) -> str:
    if row.get("probe_ok") is True:
        return "passed"
    if row.get("probe_ok") is False:
        return "failed"
    return "unknown"


def normalize_status(value: Any, allowed: set[str]) -> str:
    normalized = str(value or "unknown").strip().lower()
    return normalized if normalized in allowed else "unknown"


def build_source_row(
    row: dict[str, Any],
    governance: dict[str, Any],
    generated_at: datetime,
    governance_valid: bool,
) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    source = str(row.get("source") or "").strip()
    if not source:
        source = "missing-source"
        issues.append("missing_source_identifier")

    observed_rows = safe_int(row.get("rows"))
    if observed_rows is None:
        issues.append("invalid_observed_rows")

    last_probe = parse_utc(row.get("last_probe_utc"))
    if last_probe is None:
        issues.append("missing_or_invalid_last_probe_utc")
    elif last_probe > generated_at:
        issues.append("last_probe_after_manifest")

    minimum_rows = safe_int(governance.get("minimum_rows"))
    if minimum_rows is None or minimum_rows < 1:
        minimum_rows = None
        row_depth_status = "threshold_missing"
    elif observed_rows is None:
        row_depth_status = "unknown"
    elif observed_rows >= minimum_rows:
        row_depth_status = "passed"
    else:
        row_depth_status = "failed"

    max_age_hours = safe_float(governance.get("max_age_hours"))
    observed_age_hours = age_hours(last_probe, generated_at)
    if max_age_hours is None:
        freshness_status = "threshold_missing"
    elif observed_age_hours is None:
        freshness_status = "unknown"
    elif observed_age_hours <= max_age_hours:
        freshness_status = "passed"
    else:
        freshness_status = "stale"

    rights_status = normalize_status(governance.get("rights_status"), RIGHTS_STATUSES)
    relevance_status = normalize_status(
        governance.get("relevance_status"), RELEVANCE_STATUSES
    )
    dataset_snapshot_sha256 = strict_sha256(governance.get("dataset_snapshot_sha256"))
    probe_status = classify_probe(row)
    enabled = row.get("enabled") is True

    review_ready = all(
        (
            enabled,
            probe_status == "passed",
            row_depth_status == "passed",
            freshness_status == "passed",
            rights_status == "verified_for_review",
            relevance_status == "verified",
            dataset_snapshot_sha256 is not None,
            governance_valid,
            not issues,
        )
    )

    public_row: dict[str, Any] = {
        "source_ref": source_ref(source),
        "sector": str(row.get("sector") or "unknown").strip().lower() or "unknown",
        "configured_enabled": enabled,
        "first_party_measured_flag": row.get("measured") is True,
        "probe_status": probe_status,
        "last_probe_utc": last_probe.isoformat() if last_probe else None,
        "probe_age_hours": observed_age_hours,
        "observed_rows": observed_rows,
        "minimum_rows": minimum_rows,
        "row_depth_status": row_depth_status,
        "max_age_hours": max_age_hours,
        "freshness_status": freshness_status,
        "rights_status": rights_status,
        "relevance_status": relevance_status,
        "dataset_snapshot_sha256": dataset_snapshot_sha256,
        "dataset_snapshot_bound": dataset_snapshot_sha256 is not None,
        "review_ready": review_ready,
        "quality_issues": sorted(issues),
    }
    public_row["registry_row_sha256"] = sha256_bytes(canonical_bytes(public_row))
    return public_row, issues


def build_manifest(
    registry: dict[str, Any],
    registry_sha256: str,
    governance: dict[str, Any] | None = None,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    generated_at = parse_utc(generated_utc or now_utc())
    if generated_at is None:
        raise ValueError("generated_utc must be an ISO-8601 timestamp")

    raw_rows = registry.get("rows")
    if not isinstance(raw_rows, list):
        raise ValueError("Registry must contain a 'rows' array")

    governance_sources = (governance or {}).get("sources", {})
    if not isinstance(governance_sources, dict):
        raise ValueError("Governance sidecar must contain a 'sources' object")
    governance_validation = validate_governance(
        governance or {"sources": {}}, registry_sha256
    )

    source_names = [
        str(row.get("source") or "").strip()
        for row in raw_rows
        if isinstance(row, dict)
    ]
    source_counts = Counter(source_names)
    duplicates = sorted(source for source, count in source_counts.items() if source and count > 1)
    invalid_row_indexes = [index for index, row in enumerate(raw_rows) if not isinstance(row, dict)]

    public_rows: list[dict[str, Any]] = []
    issue_count = len(invalid_row_indexes)
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        source = str(row.get("source") or "").strip()
        public_row, issues = build_source_row(
            row,
            governance_sources.get(source, {})
            if isinstance(governance_sources.get(source, {}), dict)
            else {},
            generated_at,
            governance_validation["valid"],
        )
        issue_count += len(issues)
        public_rows.append(public_row)

    public_rows.sort(key=lambda item: item["source_ref"])
    registry_generated_at = parse_utc(registry.get("generated_utc"))
    registry_age_hours = age_hours(registry_generated_at, generated_at)
    registry_max_age_hours = safe_float((governance or {}).get("registry_max_age_hours"))
    if registry_generated_at is None:
        registry_freshness_status = "unknown"
        registry_time_valid = False
    elif registry_generated_at > generated_at:
        registry_freshness_status = "invalid_future_timestamp"
        registry_time_valid = False
    elif registry_max_age_hours is None:
        registry_freshness_status = "threshold_missing"
        registry_time_valid = True
    elif registry_age_hours is not None and registry_age_hours <= registry_max_age_hours:
        registry_freshness_status = "passed"
        registry_time_valid = True
    else:
        registry_freshness_status = "stale"
        registry_time_valid = True

    governance_names = set(str(name) for name in governance_sources)
    registry_names = set(source for source in source_names if source)
    orphan_governance_names = sorted(governance_names - registry_names)
    governance_complete_sources = sum(
        row["minimum_rows"] is not None
        and row["max_age_hours"] is not None
        and row["rights_status"] != "unknown"
        and row["relevance_status"] != "unknown"
        and row["dataset_snapshot_bound"]
        for row in public_rows
    )

    summary = {
        "registry_rows": len(raw_rows),
        "unique_source_identifiers": len(set(source for source in source_names if source)),
        "configured_enabled_sources": sum(row["configured_enabled"] for row in public_rows),
        "first_party_measured_flag_sources": sum(
            row["first_party_measured_flag"] for row in public_rows
        ),
        "probe_success_sources": sum(row["probe_status"] == "passed" for row in public_rows),
        "material_row_depth_sources": sum(
            row["row_depth_status"] == "passed" for row in public_rows
        ),
        "fresh_sources": sum(row["freshness_status"] == "passed" for row in public_rows),
        "rights_verified_sources": sum(
            row["rights_status"] == "verified_for_review" for row in public_rows
        ),
        "relevance_verified_sources": sum(
            row["relevance_status"] == "verified" for row in public_rows
        ),
        "snapshot_bound_sources": sum(row["dataset_snapshot_bound"] for row in public_rows),
        "governance_complete_sources": governance_complete_sources,
        "review_ready_sources": sum(row["review_ready"] for row in public_rows),
    }

    structurally_valid = (
        not duplicates
        and not invalid_row_indexes
        and issue_count == 0
        and registry_time_valid
        and strict_sha256(registry_sha256) is not None
    )
    manifest: dict[str, Any] = {
        "schema": "public_live_breadth_manifest_v1",
        "manifest_generated_utc": generated_at.isoformat(),
        "purpose": (
            "Publish a privacy-bounded, first-party source-observation manifest that "
            "separates configuration, probe success, row depth, freshness, rights, "
            "decision relevance, and dataset snapshot binding."
        ),
        "source_snapshot": {
            "registry_generated_utc": (
                registry_generated_at.isoformat() if registry_generated_at else None
            ),
            "registry_age_hours_at_manifest": registry_age_hours,
            "registry_max_age_hours": registry_max_age_hours,
            "registry_freshness_status": registry_freshness_status,
            "registry_sha256": registry_sha256.lower(),
            "governance_sidecar_included": bool(governance_sources),
            "governance_protocol_valid": governance_validation["valid"],
            "governance_protocol_issues": governance_validation["issues"],
            "governance_sha256": governance_validation["governance_sha256"],
            "source_names_disclosed": False,
            "credential_field_names_disclosed": False,
            "economic_estimates_included": False,
            "underlying_datasets_included": False,
        },
        "metric_definitions": {
            "configured_enabled_sources": "Rows explicitly marked enabled in the source registry.",
            "first_party_measured_flag_sources": (
                "Rows carrying the mutable first-party measured flag; not dataset fitness."
            ),
            "probe_success_sources": "Rows with an explicit boolean probe_ok=true.",
            "material_row_depth_sources": (
                "Rows meeting a source-specific minimum accepted in the governance sidecar."
            ),
            "fresh_sources": (
                "Rows within a source-specific maximum age accepted in the governance sidecar."
            ),
            "review_ready_sources": (
                "Rows passing probe, row-depth, freshness, rights, relevance, snapshot-hash, and validity gates."
            ),
        },
        "summary": summary,
        "sources": public_rows,
        "data_quality": {
            "intended_use": "technical reviewer source-provenance triage",
            "grain": "one row per configured source identifier",
            "completeness_issue_count": issue_count,
            "duplicate_source_refs": [source_ref(source) for source in duplicates],
            "orphan_governance_refs": [
                source_ref(source) for source in orphan_governance_names
            ],
            "invalid_row_indexes": invalid_row_indexes,
            "structurally_valid": structurally_valid,
            "freshness_assessable_sources": sum(
                row["max_age_hours"] is not None and row["last_probe_utc"] is not None
                for row in public_rows
            ),
            "row_depth_assessable_sources": sum(
                row["minimum_rows"] is not None and row["observed_rows"] is not None
                for row in public_rows
            ),
            "governance_gap_sources": len(public_rows) - governance_complete_sources,
            "risk": (
                "Configured, measured, or successful-probe counts can materially overstate "
                "usable breadth when source-specific row depth, freshness, rights, relevance, "
                "and dataset hashes are absent."
            ),
        },
        "claim_gate": {
            "configured_source_count_is_first_party_diagnostic": True,
            "probe_success_is_dataset_fitness": False,
            "review_ready_source_count_claim_allowed": (
                structurally_valid
                and governance_validation["valid"]
                and registry_freshness_status == "passed"
                and summary["review_ready_sources"] > 0
            ),
            "current_runtime_state_proven": False,
            "independent_validation_claim_allowed": False,
            "performance_claim_allowed": False,
            "economic_value_claim_allowed": False,
            "live_capital_recommendation_allowed": False,
        },
        "limitations": [
            "This is a first-party point-in-time manifest, not an independent validation.",
            "A source probe can succeed while the observation is too thin, stale, irrelevant, or restricted.",
            "The registry hash binds the input registry, not any underlying dataset unless a per-source dataset hash is supplied.",
            "No source count in this artifact proves alpha, savings, field performance, or production readiness.",
        ],
        "integrity": {
            "algorithm": "sha256",
            "canonicalization": "utf8-json-sort-keys-compact",
            "hash_scope": "entire manifest excluding integrity.manifest_sha256",
        },
    }
    manifest["integrity"]["manifest_sha256"] = manifest_sha256(manifest)
    return manifest


def manifest_sha256(manifest: dict[str, Any]) -> str:
    payload = deepcopy(manifest)
    integrity = payload.setdefault("integrity", {})
    integrity.pop("manifest_sha256", None)
    return sha256_bytes(canonical_bytes(payload))


def verify_manifest(manifest: dict[str, Any]) -> bool:
    expected = manifest.get("integrity", {}).get("manifest_sha256")
    return isinstance(expected, str) and expected == manifest_sha256(manifest)


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    quality = manifest["data_quality"]
    gate = manifest["claim_gate"]
    rows = [
        "# Public Live-Breadth Manifest",
        "",
        f"Manifest generated UTC: {manifest['manifest_generated_utc']}",
        f"Registry generated UTC: {manifest['source_snapshot']['registry_generated_utc']}",
        f"Registry SHA-256: `{manifest['source_snapshot']['registry_sha256']}`",
        f"Manifest SHA-256: `{manifest['integrity']['manifest_sha256']}`",
        "",
        "## Reviewer Result",
        "",
        (
            "This manifest makes the source-count denominator auditable without "
            "publishing provider names, credential field names, or economic estimates."
        ),
        "",
        "| Gate | Count |",
        "|---|---:|",
        f"| Registry rows | {summary['registry_rows']} |",
        f"| Configured/enabled | {summary['configured_enabled_sources']} |",
        f"| First-party measured flag | {summary['first_party_measured_flag_sources']} |",
        f"| Explicit probe success | {summary['probe_success_sources']} |",
        f"| Material row depth | {summary['material_row_depth_sources']} |",
        f"| Fresh under accepted threshold | {summary['fresh_sources']} |",
        f"| Rights verified for review | {summary['rights_verified_sources']} |",
        f"| Decision relevance verified | {summary['relevance_verified_sources']} |",
        f"| Dataset snapshot bound | {summary['snapshot_bound_sources']} |",
        f"| Governance complete | {summary['governance_complete_sources']} |",
        f"| Review-ready sources | {summary['review_ready_sources']} |",
        "",
        "## Data-Quality Assessment",
        "",
        f"- Intended use: {quality['intended_use']}",
        f"- Grain: {quality['grain']}",
        f"- Structurally valid: `{str(quality['structurally_valid']).lower()}`",
        f"- Completeness issues: {quality['completeness_issue_count']}",
        f"- Registry freshness status: `{manifest['source_snapshot']['registry_freshness_status']}`",
        f"- Freshness-assessable sources: {quality['freshness_assessable_sources']}",
        f"- Row-depth-assessable sources: {quality['row_depth_assessable_sources']}",
        f"- Sources with governance gaps: {quality['governance_gap_sources']}",
        f"- Analytical risk: {quality['risk']}",
        "",
        "## Claim Gate",
        "",
        f"- Review-ready source-count claim allowed: `{str(gate['review_ready_source_count_claim_allowed']).lower()}`",
        f"- Current runtime state proven: `{str(gate['current_runtime_state_proven']).lower()}`",
        f"- Independent validation claim allowed: `{str(gate['independent_validation_claim_allowed']).lower()}`",
        f"- Performance claim allowed: `{str(gate['performance_claim_allowed']).lower()}`",
        f"- Economic value claim allowed: `{str(gate['economic_value_claim_allowed']).lower()}`",
        f"- Live-capital recommendation allowed: `{str(gate['live_capital_recommendation_allowed']).lower()}`",
        "",
        "## Required Promotion Work",
        "",
        "For each source intended to count as review-ready, supply a private governance sidecar with:",
        "",
        "- accepted minimum row depth,",
        "- accepted maximum probe age,",
        "- rights status for reviewer use,",
        "- relevance to the named decision, and",
        "- SHA-256 of the underlying dataset snapshot.",
        "",
        "## Reproduction",
        "",
        "Run the builder against an authorized private registry and governance sidecar:",
        "",
        "```text",
        "python code/ops/build_public_live_breadth_manifest.py --registry <registry.json> --governance <governance.json> --output <manifest.json> --markdown <manifest.md>",
        "```",
        "",
        "Omit `--governance` only for a diagnostic manifest; review-ready counts will fail closed to zero.",
        "",
        "## Limitations",
        "",
    ]
    rows.extend(f"- {limitation}" for limitation in manifest["limitations"])
    return "\n".join(rows) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def build_from_paths(
    registry_path: Path,
    governance_path: Path | None,
    generated_utc: str | None,
) -> dict[str, Any]:
    registry = load_json(registry_path)
    governance = load_governance(governance_path)
    return build_manifest(
        registry,
        registry_sha256=file_sha256(registry_path),
        governance=governance,
        generated_utc=generated_utc,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a public-safe live-breadth source manifest."
    )
    parser.add_argument(
        "--registry",
        type=Path,
        required=True,
        help="Explicit authorized live_source_registry.json snapshot; no implicit runtime path is used.",
    )
    parser.add_argument("--governance", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--generated-at")
    args = parser.parse_args()

    manifest = build_from_paths(args.registry, args.governance, args.generated_at)
    write_json(args.output, manifest)
    write_text(args.markdown, render_markdown(manifest))
    print(
        json.dumps(
            {
                "schema": manifest["schema"],
                "registry_rows": manifest["summary"]["registry_rows"],
                "probe_success_sources": manifest["summary"]["probe_success_sources"],
                "review_ready_sources": manifest["summary"]["review_ready_sources"],
                "manifest_sha256": manifest["integrity"]["manifest_sha256"],
                "output": str(args.output),
                "markdown": str(args.markdown),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
