from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
OUT_OPS = OUT / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

LIVE_SOURCE_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"
SOURCE_TRUTH_JSON = OUT / "source_truth_table.json"
REGISTRY_JSON = ROOT / "config" / "live_source_registry.json"
GEOMETRY_MATRIX_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"

OUT_JSON = OUT_OPS / "reviewer_evidence_gate_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "reviewer_evidence_gate.json"
OUT_MD = DOCS / "REVIEWER_EVIDENCE_GATE_2026-06-22.md"

LEGACY_SOURCES = [
    {
        "name": "DOE SBIR Phase I master draft",
        "path": r"C:\Users\Novac\DOE_SBIR_LumenCore_PhaseI\08_Submission_Ready\LumenCore_DOE_SBIR_MASTER_DRAFT.txt",
        "classification": "LEGACY_BENCHMARK_REVIEW_REQUIRED",
        "reason": "Contains useful DOE positioning and historic benchmark language, but must be reconciled with the current live-source proof chain before reviewer use.",
    },
    {
        "name": "EchoLock early signal proof note",
        "path": r"C:\Users\Novac\iCloudDrive\ECHOLOCK_EARLY_SIGNAL_PROOF_PWC.md\HTML text.html",
        "classification": "CONCEPT_POSITIONING_SAFE",
        "reason": "Useful read-only resilience framing; proof snapshot language needs an artifact link before numeric or operational claims.",
    },
    {
        "name": "DoD agency alignment memo",
        "path": r"C:\Users\Novac\iCloudDrive\DoD\DOD 2.txt",
        "classification": "AGENCY_POSITIONING_SAFE",
        "reason": "Useful agency alignment language; not a performance proof by itself.",
    },
    {
        "name": "Master master dossier",
        "path": r"C:\Users\Novac\iCloudDrive\The master master dossier",
        "classification": "ARCHIVE_REVIEW_REQUIRED",
        "reason": "Contains historic PDFs, KPI CSVs, reports, and visuals that should be cited only after each claim is mapped to a current hashable artifact.",
    },
]

CLAIM_BOUNDARY = (
    "Reviewer-facing claims may cite live measured rows, hashes, and conservative readiness status. "
    "Do not present paper trades, synthetic-only benchmarks, generated visuals, estimated value surfaces, "
    "or legacy benchmark numbers as field validation, realized savings, trading profit, or award certainty."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def path_status(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    exists = path.exists()
    return {
        "path": path_text,
        "exists": exists,
        "is_dir": path.is_dir() if exists else False,
        "bytes": path.stat().st_size if exists and path.is_file() else 0,
    }


def measured_rows(live_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = live_payload.get("provider_rows", [])
    if not isinstance(rows, list):
        return []
    measured = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("measured") and int(row.get("rows", 0) or 0) > 0 and row.get("snapshot_sha256"):
            measured.append(
                {
                    "source": row.get("source", ""),
                    "sector": row.get("sector", ""),
                    "rows": int(row.get("rows", 0) or 0),
                    "status": row.get("status", ""),
                    "snapshot_json": row.get("snapshot_json", ""),
                    "snapshot_sha256": row.get("snapshot_sha256", ""),
                    "claim_use": "LIVE_MEASURED_REFERENCE",
                }
            )
    return measured


def blocked_rows(live_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = live_payload.get("provider_rows", [])
    if not isinstance(rows, list):
        return []
    blocked = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("measured") and int(row.get("rows", 0) or 0) > 0:
            continue
        blocked.append(
            {
                "source": row.get("source", ""),
                "sector": row.get("sector", ""),
                "status": row.get("status", ""),
                "http_status": row.get("http_status"),
                "probe_note": row.get("probe_note", ""),
                "claim_use": "EXCLUDED_UNTIL_MEASURED",
            }
        )
    return blocked


def source_truth_from_registry(registry: dict[str, Any]) -> dict[str, Any]:
    rows = registry.get("rows", []) if isinstance(registry.get("rows"), list) else []
    truth_rows = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("source"):
            continue
        translated = row.get("translated_value", {}) if isinstance(row.get("translated_value"), dict) else {}
        truth_rows.append(
            {
                "source": row.get("source", ""),
                "sector": row.get("sector", ""),
                "status": row.get("status", ""),
                "rows": row.get("rows", 0),
                "enabled": bool(row.get("enabled", False)),
                "measured": bool(row.get("measured", False)),
                "estimated_hour_value": translated.get("hour", 0.0),
                "value_basis": "MEASURED" if row.get("measured") else "UNMEASURED",
                "last_probe_utc": row.get("last_probe_utc", ""),
                "probe_note": row.get("probe_note", ""),
                "snapshot_json": row.get("snapshot_json", ""),
                "snapshot_sha256": row.get("snapshot_sha256", ""),
            }
        )
    return {"generated_utc": now_utc(), "rows": truth_rows, "repair_source": "config/live_source_registry.json"}


def geometry_gate(geometry_payload: dict[str, Any]) -> dict[str, Any]:
    summary = geometry_payload.get("summary", {}) if isinstance(geometry_payload.get("summary"), dict) else {}
    queue = geometry_payload.get("priority_queue", [])
    if not isinstance(queue, list):
        queue = []
    lane_rows = []
    for row in queue[:12]:
        if not isinstance(row, dict):
            continue
        lane_rows.append(
            {
                "lane": row.get("lane", ""),
                "proof_build_priority_rank": row.get("proof_build_priority_rank"),
                "live_wiring_score": row.get("live_wiring_score"),
                "ready_for_live_replay_build": bool(row.get("lane_ready_for_live_replay_build")),
                "ready_for_live_geometry_claim": bool(row.get("ready_for_live_geometry_claim")),
                "ready_for_real_dollar_claim": bool(row.get("ready_for_real_dollar_claim")),
                "generated_champion": row.get("generated_champion", {}),
                "proof_value_champion": row.get("proof_value_champion", {}),
                "claim_blockers": row.get("claim_blockers", []),
            }
        )
    return {
        "classification": "LIVE_WIRED_NOT_CLAIM_READY",
        "summary": {
            "lane_count": summary.get("lane_count", 0),
            "family_count": summary.get("family_count", 0),
            "live_source_measured_count": summary.get("live_source_measured_count", 0),
            "total_measured_rows": summary.get("total_measured_rows", 0),
            "ready_for_live_geometry_claim": bool(summary.get("ready_for_live_geometry_claim")),
            "ready_for_real_dollar_claim": bool(summary.get("ready_for_real_dollar_claim")),
        },
        "lanes": lane_rows,
    }


def legacy_gate() -> list[dict[str, Any]]:
    rows = []
    for item in LEGACY_SOURCES:
        row = dict(item)
        row.update(path_status(str(item["path"])))
        rows.append(row)
    return rows


def build_payload() -> dict[str, Any]:
    live = read_json(LIVE_SOURCE_JSON)
    truth = read_json(SOURCE_TRUTH_JSON)
    registry = read_json(REGISTRY_JSON)
    geometry = read_json(GEOMETRY_MATRIX_JSON)
    live_summary = live.get("summary", {}) if isinstance(live.get("summary"), dict) else {}
    truth_rows = truth.get("rows", []) if isinstance(truth.get("rows"), list) else []
    measured = measured_rows(live)
    blocked = blocked_rows(live)
    repaired_source_truth = False

    if len(truth_rows) < len(measured):
        repaired = source_truth_from_registry(registry)
        repaired_rows = repaired.get("rows", []) if isinstance(repaired.get("rows"), list) else []
        if len(repaired_rows) >= len(measured):
            write_json(SOURCE_TRUTH_JSON, repaired)
            truth_rows = repaired_rows
            repaired_source_truth = True

    ready_for_reviewer = bool(measured) and len(truth_rows) >= len(measured)
    return {
        "generated_utc": now_utc(),
        "schema": "reviewer_evidence_gate_v1",
        "ready_for_reviewer_packet": ready_for_reviewer,
        "claim_boundary": CLAIM_BOUNDARY,
        "summary": {
            "live_enabled_sources": live_summary.get("enabled_sources", 0),
            "live_measured_sources": live_summary.get("measured_sources", 0),
            "live_failed_or_thin_sources": live_summary.get("failed_or_thin_sources", 0),
            "live_total_measured_rows": live_summary.get("total_measured_rows", 0),
            "source_truth_rows": len(truth_rows),
            "source_truth_repaired_from_registry": repaired_source_truth,
            "estimated_annual_value_surface_usd": live_summary.get("estimated_annual_value_surface_usd", 0.0),
            "legacy_sources_reviewed": len(LEGACY_SOURCES),
        },
        "promote": {
            "live_measured_sources": measured,
            "safe_claims": [
                "The stack currently maintains a hashable live-source measurement chain.",
                "The latest pass measured multiple public/private data-source surfaces and recorded snapshot hashes.",
                "Geometry families are wired to live-source replay queues but are not yet field-validation claims.",
            ],
        },
        "quarantine": {
            "blocked_or_thin_sources": blocked,
            "paper_or_synthetic_rules": [
                "Paper trades are internal calibration evidence only.",
                "Synthetic benchmarks are lab evidence only until paired with fresh live replay windows.",
                "Generated visuals are communication assets only, not engineering proof.",
                "Dollar surfaces are sizing/context estimates only until a buyer, baseline, and measured lift are validated.",
            ],
            "legacy_sources": legacy_gate(),
        },
        "geometry": geometry_gate(geometry),
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Reviewer Evidence Gate",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Verdict",
        "",
        f"- Ready for reviewer packet: `{payload['ready_for_reviewer_packet']}`",
        f"- Claim boundary: {payload['claim_boundary']}",
        "",
        "## Live Evidence Promoted",
        "",
        f"- Enabled sources: {summary['live_enabled_sources']}",
        f"- Measured sources: {summary['live_measured_sources']}",
        f"- Failed/thin sources: {summary['live_failed_or_thin_sources']}",
        f"- Total measured rows: {summary['live_total_measured_rows']}",
        f"- Source truth rows: {summary['source_truth_rows']}",
        f"- Source truth repaired from registry: `{summary.get('source_truth_repaired_from_registry', False)}`",
        f"- Estimated annual value surface: ${float(summary['estimated_annual_value_surface_usd']):,.2f}",
        "",
        "### Reviewer-Safe Claims",
        "",
    ]
    for claim in payload["promote"]["safe_claims"]:
        lines.append(f"- {claim}")
    lines.extend(["", "### Live Measured Sources", "", "| Source | Sector | Rows | Snapshot | SHA-256 |", "|---|---|---:|---|---|"])
    for row in payload["promote"]["live_measured_sources"]:
        lines.append(
            f"| {row['source']} | {row['sector']} | {row['rows']} | "
            f"`{row['snapshot_json']}` | `{row['snapshot_sha256']}` |"
        )
    lines.extend(["", "## Quarantine", "", "### Blocked Or Thin Sources", "", "| Source | Status | Reason |", "|---|---|---|"])
    for row in payload["quarantine"]["blocked_or_thin_sources"]:
        note = str(row.get("probe_note", "")).replace("\n", " ")[:180]
        lines.append(f"| {row['source']} | {row['status']} | {note} |")
    lines.extend(["", "### Paper/Synthetic Rules", ""])
    for rule in payload["quarantine"]["paper_or_synthetic_rules"]:
        lines.append(f"- {rule}")
    lines.extend(["", "### Legacy Sources", "", "| Source | Classification | Exists | Reason |", "|---|---|---:|---|"])
    for row in payload["quarantine"]["legacy_sources"]:
        lines.append(f"| {row['name']} | {row['classification']} | {row['exists']} | {row['reason']} |")
    geom = payload["geometry"]
    lines.extend(
        [
            "",
            "## Geometry Gate",
            "",
            f"- Classification: `{geom['classification']}`",
            f"- Lanes: {geom['summary']['lane_count']}",
            f"- Families: {geom['summary']['family_count']}",
            f"- Live-source measured count: {geom['summary']['live_source_measured_count']}",
            f"- Ready for live geometry claim: `{geom['summary']['ready_for_live_geometry_claim']}`",
            f"- Ready for real-dollar claim: `{geom['summary']['ready_for_real_dollar_claim']}`",
            "",
            "| Rank | Lane | Live Wiring Score | Claim Ready | Champion Candidate |",
            "|---:|---|---:|---:|---|",
        ]
    )
    for row in geom["lanes"][:8]:
        champion = row.get("proof_value_champion", {}) if isinstance(row.get("proof_value_champion"), dict) else {}
        label = champion.get("label") or champion.get("family") or ""
        lines.append(
            f"| {row.get('proof_build_priority_rank', '')} | {row.get('lane', '')} | "
            f"{row.get('live_wiring_score', 0)} | {row.get('ready_for_live_geometry_claim')} | {label} |"
        )
    lines.extend(
        [
            "",
            "## Submission Rule",
            "",
            "Use this gate as the first page of any grant, contract, LinkedIn, or investor evidence review. "
            "If a claim is not in `promote.live_measured_sources` or explicitly marked as concept/legacy, it should not be presented as proof.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "ready_for_reviewer_packet": payload["ready_for_reviewer_packet"],
                "live_measured_sources": payload["summary"]["live_measured_sources"],
                "source_truth_rows": payload["summary"]["source_truth_rows"],
                "blocked_or_thin_sources": len(payload["quarantine"]["blocked_or_thin_sources"]),
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
