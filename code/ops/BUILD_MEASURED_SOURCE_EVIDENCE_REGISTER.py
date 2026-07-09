from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

REGISTRY_JSON = ROOT / "config" / "live_source_registry.json"
MAXIMIZER_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"
GEOMETRY_MANIFEST_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"
CLAIM_MAP_JSON = OUT_OPS / "claim_strength_value_unlock_map_latest.json"
EDGE_INDEX_MD = SPRINT_DIR / "PROOF_STACK_EDGE_INDEX_2026-07-09.md"

OUT_JSON = OUT_OPS / "measured_source_evidence_register_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "measured_source_evidence_register.json"
OUT_MD = SPRINT_DIR / "MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md"

SENSITIVE_MARKERS = [
    "api_key",
    "client_secret",
    "refresh_token",
    "private key",
    "password",
    "sk-",
    "xox",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_status(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def rows_from(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key, [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def count_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    enabled = [row for row in rows if bool(row.get("enabled"))]
    measured = [row for row in enabled if bool(row.get("measured"))]
    failed = [row for row in enabled if not bool(row.get("measured"))]
    hash_backed = [
        row
        for row in measured
        if isinstance(row.get("snapshot_sha256"), str) and len(str(row.get("snapshot_sha256"))) == 64
    ]
    return {
        "total_sources": len(rows),
        "enabled_sources": len(enabled),
        "measured_sources": len(measured),
        "failed_or_thin_sources": len(failed),
        "hash_backed_measured_sources": len(hash_backed),
        "total_measured_rows": sum(int(row.get("rows") or 0) for row in measured),
        "measured_source_names": sorted(str(row.get("source")) for row in measured),
        "failed_or_thin_source_names": sorted(str(row.get("source")) for row in failed),
    }


def sector_counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        sector = str(row.get("sector") or "unknown")
        item = out.setdefault(sector, {"enabled": 0, "measured": 0, "rows": 0})
        if row.get("enabled"):
            item["enabled"] += 1
        if row.get("measured"):
            item["measured"] += 1
            item["rows"] += int(row.get("rows") or 0)
    return dict(sorted(out.items()))


def by_source(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("source") or "").upper(): row for row in rows if row.get("source")}


def source_register_rows(registry_rows: list[dict[str, Any]], provider_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    registry_by_source = by_source(registry_rows)
    provider_by_source = by_source(provider_rows)
    names = sorted(set(registry_by_source) | set(provider_by_source))
    rows: list[dict[str, Any]] = []
    for name in names:
        registry = registry_by_source.get(name, {})
        provider = provider_by_source.get(name, {})
        chosen = provider or registry
        snapshot_sha = str(chosen.get("snapshot_sha256") or registry.get("snapshot_sha256") or "")
        snapshot_json = str(chosen.get("snapshot_json") or registry.get("snapshot_json") or "")
        registry_measured = bool(registry.get("measured"))
        provider_measured = bool(provider.get("measured"))
        row = {
            "source": name,
            "sector": str(chosen.get("sector") or registry.get("sector") or "unknown"),
            "registry_enabled": bool(registry.get("enabled")),
            "registry_measured": registry_measured,
            "registry_rows": int(registry.get("rows") or 0),
            "current_probe_seen": bool(provider),
            "current_probe_enabled": bool(provider.get("enabled")) if provider else False,
            "current_probe_measured": provider_measured if provider else False,
            "current_probe_rows": int(provider.get("rows") or 0) if provider else 0,
            "status": str(chosen.get("status") or registry.get("status") or ""),
            "snapshot_json": snapshot_json,
            "snapshot_sha256": snapshot_sha,
            "hash_backed": len(snapshot_sha) == 64,
            "evidence_tier": evidence_tier(registry_measured, provider_measured, bool(provider), len(snapshot_sha) == 64),
            "reviewer_use": reviewer_use(chosen),
            "source_authority_claimed": False,
            "live_execution_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "claim_boundary": (
                "Source inventory and measured-row evidence only; it is not field validation, realized savings, "
                "award eligibility, source authority, or live execution approval."
            ),
        }
        row["row_sha256"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()
        rows.append(row)
    rows.sort(
        key=lambda item: (
            item["evidence_tier"] != "CURRENT_HASHED_MEASURED_SOURCE",
            item["evidence_tier"] != "REGISTRY_MEASURED_NEEDS_HASH_REFRESH",
            item["source"],
        )
    )
    return rows


def evidence_tier(
    registry_measured: bool,
    provider_measured: bool,
    provider_seen: bool,
    hash_backed: bool,
) -> str:
    if provider_seen and provider_measured and hash_backed:
        return "CURRENT_HASHED_MEASURED_SOURCE"
    if registry_measured and hash_backed:
        return "REGISTRY_HASHED_MEASURED_SOURCE"
    if registry_measured:
        return "REGISTRY_MEASURED_NEEDS_HASH_REFRESH"
    if provider_seen:
        return "CURRENT_PROBE_UNMEASURED_OR_THIN"
    return "REGISTRY_UNMEASURED_OR_DISABLED"


def reviewer_use(row: dict[str, Any]) -> str:
    sector = str(row.get("sector") or "unknown")
    if sector in {"federal_opportunity"}:
        return "Agency/opportunity discovery context, not submission acceptance."
    if sector in {"energy", "weather", "air_quality", "water", "space"}:
        return "Domain-source coverage for benchmark routing and agency proof appendices."
    if sector in {"market_data", "rates", "macro", "labor", "demographic", "crypto_market", "crypto_exec"}:
        return "Fresh external signal coverage for replay calibration and bounded value-surface context."
    if sector == "broker":
        return "Account connectivity presence only; no trading authority or capital movement."
    return "Source inventory context for reviewer diligence."


def build_payload() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    maximizer = read_json(MAXIMIZER_JSON)
    geometry = read_json(GEOMETRY_MANIFEST_JSON)
    claim_map = read_json(CLAIM_MAP_JSON)

    registry_rows = rows_from(registry, "rows")
    provider_rows = rows_from(maximizer, "provider_rows")
    registry_counts = count_rows(registry_rows)
    provider_counts = count_rows(provider_rows)
    register_rows = source_register_rows(registry_rows, provider_rows)

    registry_names = {str(row.get("source") or "").upper() for row in registry_rows if row.get("source")}
    provider_names = {str(row.get("source") or "").upper() for row in provider_rows if row.get("source")}
    measured_no_hash = [
        row["source"]
        for row in register_rows
        if row["registry_measured"] and not row["hash_backed"]
    ]
    current_hash_backed = [
        row["source"]
        for row in register_rows
        if row["evidence_tier"] == "CURRENT_HASHED_MEASURED_SOURCE"
    ]
    reconciliation_required = registry_counts["measured_sources"] != provider_counts["measured_sources"] or bool(
        measured_no_hash
    )

    geometry_summary = geometry.get("summary", {}) if isinstance(geometry.get("summary"), dict) else {}
    claim_summary = claim_map.get("summary", {}) if isinstance(claim_map.get("summary"), dict) else {}

    payload = {
        "generated_utc": now_utc(),
        "schema": "measured_source_evidence_register_v1",
        "status": "MEASURED_SOURCE_REGISTER_READY_RECONCILIATION_REQUIRED"
        if reconciliation_required
        else "MEASURED_SOURCE_REGISTER_READY",
        "summary": {
            "registry_total_sources": registry_counts["total_sources"],
            "registry_enabled_sources": registry_counts["enabled_sources"],
            "registry_measured_sources": registry_counts["measured_sources"],
            "registry_failed_or_thin_sources": registry_counts["failed_or_thin_sources"],
            "registry_hash_backed_measured_sources": registry_counts["hash_backed_measured_sources"],
            "registry_total_measured_rows": registry_counts["total_measured_rows"],
            "current_probe_total_sources": provider_counts["total_sources"],
            "current_probe_enabled_sources": provider_counts["enabled_sources"],
            "current_probe_measured_sources": provider_counts["measured_sources"],
            "current_probe_failed_or_thin_sources": provider_counts["failed_or_thin_sources"],
            "current_probe_hash_backed_measured_sources": provider_counts["hash_backed_measured_sources"],
            "current_probe_total_measured_rows": provider_counts["total_measured_rows"],
            "source_register_rows": len(register_rows),
            "registry_only_sources": sorted(registry_names - provider_names),
            "current_probe_only_sources": sorted(provider_names - registry_names),
            "registry_measured_without_snapshot_hash": measured_no_hash,
            "current_hash_backed_measured_sources": current_hash_backed,
            "reconciliation_required": reconciliation_required,
            "geometry_manifest_unique_source_count": int(geometry_summary.get("unique_source_count") or 0),
            "geometry_manifest_row_count": int(geometry_summary.get("manifest_row_count") or 0),
            "claim_map_safe_estimated_annual_value_usd": float(claim_summary.get("safe_estimated_annual_value_usd") or 0.0),
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
            "award_value_claim_allowed": False,
            "source_authority_claimed": False,
            "live_trading_allowed": False,
            "autonomous_external_action_allowed": False,
        },
        "sector_counts": {
            "registry": sector_counts(registry_rows),
            "current_probe": sector_counts(provider_rows),
        },
        "source_rows": register_rows,
        "claim_policy": {
            "allowed": [
                "registry-backed 29-source inventory",
                "current-probe measured source rows when snapshot hashes are present",
                "bounded estimated-value context under stated assumptions",
                "source coverage for reviewer diligence and benchmark routing",
            ],
            "blocked": [
                "field validation",
                "realized savings",
                "guaranteed award",
                "source authority",
                "trading profit",
                "autonomous execution approval",
            ],
            "reconciliation_note": (
                "The registry is a merged continuity layer. The current probe array is the latest measurement run. "
                "Sources measured in the registry but absent from the current probe, or lacking snapshot hashes, remain useful context "
                "but require refresh before being called current hash-backed evidence."
            ),
        },
        "evidence_status": [
            artifact_status(REGISTRY_JSON),
            artifact_status(MAXIMIZER_JSON),
            artifact_status(GEOMETRY_MANIFEST_JSON),
            artifact_status(CLAIM_MAP_JSON),
            artifact_status(EDGE_INDEX_MD),
        ],
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["measured_source_register_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Measured Source Evidence Register - 2026-07-09",
        "",
        "Purpose: make the live-source proof layer inspectable for reviewers without inflating it into a result, award, or operating claim.",
        "",
        "This register is an evidence inventory. It does not authorize source-rights claims, field validation language, realized savings language, final submissions, live trading, or autonomous external actions.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Register SHA-256: `{payload['measured_source_register_sha256']}`",
        f"- Registry-backed sources: `{summary['registry_total_sources']}`",
        f"- Registry-backed enabled sources: `{summary['registry_enabled_sources']}`",
        f"- Registry-backed measured sources: `{summary['registry_measured_sources']}`",
        f"- Registry-backed hash-backed measured sources: `{summary['registry_hash_backed_measured_sources']}`",
        f"- Registry-backed measured rows: `{summary['registry_total_measured_rows']}`",
        f"- Current probe sources: `{summary['current_probe_total_sources']}`",
        f"- Current probe enabled sources: `{summary['current_probe_enabled_sources']}`",
        f"- Current probe measured sources: `{summary['current_probe_measured_sources']}`",
        f"- Current probe hash-backed measured sources: `{summary['current_probe_hash_backed_measured_sources']}`",
        f"- Current probe measured rows: `{summary['current_probe_total_measured_rows']}`",
        f"- Registry-only sources: `{', '.join(summary['registry_only_sources'])}`",
        f"- Registry measured without snapshot hash: `{', '.join(summary['registry_measured_without_snapshot_hash'])}`",
        f"- Reconciliation required: `{str(summary['reconciliation_required']).lower()}`",
        f"- Geometry manifest unique sources: `{summary['geometry_manifest_unique_source_count']}`",
        f"- Geometry manifest rows: `{summary['geometry_manifest_row_count']}`",
        f"- Field validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Customer outcome value claim allowed: `{str(summary['realized_savings_claim_allowed']).lower()}`",
        f"- Award value claim allowed: `{str(summary['award_value_claim_allowed']).lower()}`",
        f"- Source authority claimed: `{str(summary['source_authority_claimed']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Autonomous external action allowed: `{str(summary['autonomous_external_action_allowed']).lower()}`",
        "",
        "## Reconciliation Note",
        "",
        payload["claim_policy"]["reconciliation_note"],
        "",
        "## Allowed Language",
        "",
    ]
    for item in payload["claim_policy"]["allowed"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Blocked Language", ""])
    for item in payload["claim_policy"]["blocked"]:
        lines.append(f"- Do not claim {item}.")

    lines.extend(
        [
            "",
            "## Source Rows",
            "",
            "| Source | Sector | Evidence tier | Registry measured | Current measured | Rows | Hash-backed | Snapshot SHA-256 |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in payload["source_rows"]:
        rows = row["current_probe_rows"] if row["current_probe_seen"] else row["registry_rows"]
        lines.append(
            "| "
            f"{row['source']} | {row['sector']} | {row['evidence_tier']} | "
            f"{str(row['registry_measured']).lower()} | {str(row['current_probe_measured']).lower()} | "
            f"{rows} | {str(row['hash_backed']).lower()} | `{row['snapshot_sha256']}` |"
        )

    lines.extend(["", "## Evidence Sources", ""])
    for row in payload["evidence_status"]:
        lines.append(
            f"- `{row['path']}` | present=`{str(row['present']).lower()}` | bytes=`{row['bytes']}` | sha256=`{row['sha256']}`"
        )
    lines.append("")
    return "\n".join(lines)


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public register markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "registry_measured_sources": payload["summary"]["registry_measured_sources"],
                "current_probe_measured_sources": payload["summary"]["current_probe_measured_sources"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
