from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

WHITEHOLE_ROOT = Path("C:/WhiteHole")
WHITEHOLE_PROOFS = WHITEHOLE_ROOT / "proofs"
WHITEHOLE_CHAIN = WHITEHOLE_ROOT / "CHAIN_OF_CUSTODY_256.txt"

LIVE_MAXIMIZER_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "reviewer_evidence_gate_latest.json"
CHAMPIONS_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
LIVE_WIRING_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"

OUT_JSON = OUT_OPS / "deadline_evidence_bridge_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "deadline_evidence_bridge.json"
OUT_MD = DOCS / "DEADLINE_EVIDENCE_BRIDGE_2026-06-23.md"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def mb(size: int) -> float:
    return round(size / (1024 * 1024), 3)


def read_text_safe(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    return text[:max_chars]


def parse_manifest_included(text: str) -> list[str]:
    if "INCLUDED:" not in text:
        return []
    _, tail = text.split("INCLUDED:", 1)
    return [line.strip() for line in tail.splitlines() if line.strip()]


def freeze_sidecar(path: Path, suffix: str) -> Path:
    return path.with_name(path.stem + suffix)


def summarize_whitehole(proofs_dir: Path = WHITEHOLE_PROOFS, chain_path: Path = WHITEHOLE_CHAIN) -> dict[str, Any]:
    zips = sorted(proofs_dir.glob("WHITEHOLE_FREEZE_*.zip"), key=lambda item: item.stat().st_mtime, reverse=True) if proofs_dir.exists() else []
    weekly = sorted(proofs_dir.glob("FED_PILOT_PACKET_WEEKLY_*.zip"), key=lambda item: item.stat().st_mtime, reverse=True) if proofs_dir.exists() else []
    recent = []
    for path in zips[:12]:
        manifest = freeze_sidecar(path, ".manifest.txt")
        sha = freeze_sidecar(path, ".sha256.txt")
        manifest_text = read_text_safe(manifest)
        size = path.stat().st_size
        recent.append(
            {
                "name": path.name,
                "path": str(path),
                "size_bytes": size,
                "size_mb": mb(size),
                "last_write_utc_hint": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "manifest": str(manifest) if manifest.exists() else "",
                "sha256_sidecar": str(sha) if sha.exists() else "",
                "sha256_text": read_text_safe(sha, 400).strip(),
                "included_roots": parse_manifest_included(manifest_text),
                "usable_as": "custody_and_reproducibility_evidence" if size > 0 and sha.exists() else "incomplete_or_broken_freeze",
                "claim_limit": "Use as chain-of-custody and continuity evidence only; not field validation or measured performance.",
            }
        )
    chain_text = read_text_safe(chain_path, 200_000)
    chain_lines = [line for line in chain_text.splitlines() if line.strip()]
    usable = [row for row in recent if row["usable_as"] == "custody_and_reproducibility_evidence"]
    return {
        "root": str(proofs_dir.parent),
        "proof_dir": str(proofs_dir),
        "freeze_zip_count": len(zips),
        "weekly_fed_packet_count": len(weekly),
        "zero_byte_freeze_count": sum(1 for path in zips if path.stat().st_size == 0),
        "recent_freezes": recent,
        "latest_observed_freeze": recent[0] if recent else {},
        "latest_freeze": usable[0] if usable else (recent[0] if recent else {}),
        "latest_freeze_selection": (
            "newest_complete_freeze_with_sha256_sidecar"
            if usable
            else "newest_observed_freeze_no_complete_freeze_available"
        ),
        "chain_of_custody": {
            "path": str(chain_path),
            "exists": chain_path.exists(),
            "line_count_sampled": len(chain_lines),
            "recent_lines": chain_lines[-12:],
        },
        "grant_use": "Continuity, reproducibility, custody, and prior-art/body-of-work support.",
        "grant_limit": "Do not cite these archives as independent performance proof; they are not field validation, realized savings, or agency acceptance.",
    }


def summarize_live_sources(live: dict[str, Any]) -> dict[str, Any]:
    summary = live.get("summary", {}) if isinstance(live.get("summary"), dict) else {}
    rows = live.get("provider_rows", []) if isinstance(live.get("provider_rows"), list) else []
    measured = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("status") == "MEASURED"
        and int(row.get("rows", 0) or 0) > 0
        and row.get("snapshot_sha256")
    ]
    blocked = [row for row in rows if isinstance(row, dict) and row not in measured]
    measured_rows = [
        {
            "source": row.get("source", ""),
            "sector": row.get("sector", ""),
            "rows": int(row.get("rows", 0) or 0),
            "snapshot_json": row.get("snapshot_json", ""),
            "snapshot_sha256": row.get("snapshot_sha256", ""),
            "translated_annual_value_usd": float((row.get("translated_value") or {}).get("year", 0.0) or 0.0),
            "claim_use": "live_measured_reference",
        }
        for row in measured
    ]
    return {
        "enabled_sources": int(summary.get("enabled_sources", 0) or 0),
        "measured_sources": int(summary.get("measured_sources", len(measured)) or 0),
        "failed_or_thin_sources": int(summary.get("failed_or_thin_sources", 0) or 0),
        "total_measured_rows": int(summary.get("total_measured_rows", sum(row["rows"] for row in measured_rows)) or 0),
        "coverage_pct": float(summary.get("coverage_pct", 0.0) or 0.0),
        "estimated_annual_value_surface_usd": float(summary.get("estimated_annual_value_surface_usd", 0.0) or 0.0),
        "measured_source_names": [row["source"] for row in measured_rows],
        "blocked_or_thin_source_names": [str(row.get("source", "")) for row in blocked if row.get("source")],
        "measured_rows": measured_rows,
        "claim_boundary": summary.get(
            "claim_boundary",
            "Fresh measured rows and hashes are evidence inputs, not field validation or realized savings.",
        ),
    }


def summarize_champions(champions: dict[str, Any]) -> dict[str, Any]:
    summary = champions.get("summary", {}) if isinstance(champions.get("summary"), dict) else {}
    lane_rows = champions.get("lane_rankings", []) if isinstance(champions.get("lane_rankings"), list) else []
    family_rows = champions.get("family_asset_rankings", []) if isinstance(champions.get("family_asset_rankings"), list) else []
    return {
        "ranked_lane_count": int(summary.get("ranked_lane_count", len(lane_rows)) or 0),
        "ranked_family_count": int(summary.get("ranked_family_count", len(family_rows)) or 0),
        "top_lanes": lane_rows[:5],
        "top_families": family_rows[:10],
        "claim_boundary": summary.get("claim_boundary", ""),
        "ready_for_field_validation_claim": bool(summary.get("ready_for_field_validation_claim")),
        "ready_for_real_dollar_claim": bool(summary.get("ready_for_real_dollar_claim")),
    }


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def docker_daemon_check() -> dict[str, Any]:
    if not command_available("docker"):
        return {"cli_available": False, "daemon_reachable": False, "note": "docker command not found"}
    try:
        proc = subprocess.run(
            ["docker", "ps", "--format", "{{.ID}} {{.Image}} {{.Names}}"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception as exc:
        return {"cli_available": True, "daemon_reachable": False, "note": f"exception:{type(exc).__name__}"}
    return {
        "cli_available": True,
        "daemon_reachable": proc.returncode == 0,
        "container_lines": [line for line in proc.stdout.splitlines() if line.strip()],
        "note": "ok" if proc.returncode == 0 else proc.stderr.strip()[:500],
    }


def summarize_tooling(check_docker: bool = True) -> dict[str, Any]:
    docker = docker_daemon_check() if check_docker else {"cli_available": command_available("docker"), "daemon_reachable": False, "note": "not_checked"}
    return {
        "docker": docker,
        "node_red": {
            "available": command_available("node-red") or command_available("node-red.cmd") or command_available("node-red.ps1"),
            "grant_use": "Fast local demo/orchestration dashboard if wired to frozen snapshots.",
            "deadline_priority": "use only if an existing flow already supports the story; do not build a new dependency today",
        },
        "spark": {
            "available": any(command_available(name) for name in ["spark-submit", "pyspark", "spark-shell"]),
            "what_it_is": "Apache Spark is a distributed data-processing engine for datasets too large for one local process.",
            "deadline_priority": "not needed for the current 418-row live measurement packet; useful later for massive replay backfills.",
        },
        "unity": {
            "deadline_priority": "demo/visualization only; not proof unless it renders measured replay outputs with custody hashes",
        },
    }


def field_validation_gap(live_summary: dict[str, Any], champion_summary: dict[str, Any]) -> list[str]:
    gaps = [
        "No partner/agency/customer has confirmed a real operational baseline yet.",
        "No top champion has completed a frozen live replay with paired uncertainty intervals in this bridge.",
        "No independent reviewer has reproduced the candidate-vs-baseline result.",
        "Dollar surfaces remain sizing context until a buyer, baseline, measured lift, and validation window are known.",
    ]
    blocked = set(live_summary.get("blocked_or_thin_source_names", []))
    if "SAM_GOV" in blocked:
        gaps.append("SAM_GOV remains unavailable in the live measurement bridge; contract-opportunity evidence should rely on Grants.gov until fixed.")
    if "NREL" in blocked:
        gaps.append("NREL remains thin/blocked, which weakens DOE energy-lab language until retried or replaced.")
    return gaps


def linkedin_resume_drafts(live_summary: dict[str, Any], champion_summary: dict[str, Any], whitehole: dict[str, Any]) -> dict[str, Any]:
    top_lane = (champion_summary.get("top_lanes") or [{}])[0]
    top_family = (champion_summary.get("top_families") or [{}])[0]
    return {
        "linkedin_headline": (
            "Founder & Inventor, LumenCore | Live-Source Evidence Systems | "
            "Geometry-Based Optimization | Patent-Pending AI Infrastructure"
        ),
        "linkedin_about": (
            "I build LumenCore, a live-source evidence and optimization workbench for resilience, "
            "signal drift, infrastructure routing, and geometry-based AI experiments. The current "
            f"stack ranks {champion_summary.get('ranked_family_count', 0)} geometry families across "
            f"{champion_summary.get('ranked_lane_count', 0)} validation lanes, connects "
            f"{live_summary.get('measured_sources', 0)} measured live data sources, and maintains "
            "hashable snapshot/custody artifacts so claims can be separated from assumptions. "
            "My focus is grant-grade, reviewer-safe proof: frozen inputs, baseline comparison, "
            "uncertainty, reproducibility, and field-validation readiness."
        ),
        "resume_summary": (
            "Inventor and systems builder developing LumenCore, a patent-pending AI infrastructure "
            "and evidence workbench for live-source measurement, geometry-family benchmarking, "
            "signal drift analysis, and resilience-oriented optimization."
        ),
        "resume_bullets": [
            f"Built a live-source measurement bridge with {live_summary.get('measured_sources', 0)} measured sources, {live_summary.get('total_measured_rows', 0)} measured rows, and hashable data snapshots.",
            f"Created a geometry registry and champion board ranking {champion_summary.get('ranked_family_count', 0)} natural, mathematical, and control-inspired families across {champion_summary.get('ranked_lane_count', 0)} proof lanes.",
            f"Identified `{top_lane.get('lane', 'time_series_model_routing')}` and `{top_family.get('family', 'fractal_brownian_surface')}` as current top proof-building priorities, while preserving field-validation and dollar-claim boundaries.",
            f"Maintained WhiteHole custody archives with {whitehole.get('freeze_zip_count', 0)} freeze bundles and {whitehole.get('weekly_fed_packet_count', 0)} weekly federal pilot packets as reproducibility/context evidence.",
        ],
        "safe_language_rule": "Do not claim field validation, realized savings, government adoption, or trading profit until the external validation gates pass.",
    }


def build_bridge(check_docker: bool = True) -> dict[str, Any]:
    live = read_json(LIVE_MAXIMIZER_JSON)
    reviewer = read_json(REVIEWER_GATE_JSON)
    champions = read_json(CHAMPIONS_JSON)
    wiring = read_json(LIVE_WIRING_JSON)
    whitehole = summarize_whitehole()
    live_summary = summarize_live_sources(live)
    champion_summary = summarize_champions(champions)
    tooling = summarize_tooling(check_docker=check_docker)
    drafts = linkedin_resume_drafts(live_summary, champion_summary, whitehole)

    return {
        "generated_utc": now_utc(),
        "schema": "deadline_evidence_bridge_v1",
        "purpose": "Turn WhiteHole freezes, measured live rows, geometry champions, and local tooling into a one-day grant/submission evidence bridge.",
        "deadline_posture": "Use measured live-source and custody evidence today; treat Docker/Node-RED/Unity/Spark as optional demo infrastructure, not proof.",
        "summary": {
            "ready_for_reviewer_packet": bool(reviewer.get("ready_for_reviewer_packet")),
            "live_measured_sources": live_summary["measured_sources"],
            "live_total_measured_rows": live_summary["total_measured_rows"],
            "geometry_families_ranked": champion_summary["ranked_family_count"],
            "geometry_lanes_ranked": champion_summary["ranked_lane_count"],
            "whitehole_freeze_zip_count": whitehole["freeze_zip_count"],
            "whitehole_latest_freeze": whitehole.get("latest_freeze", {}).get("name", ""),
            "docker_daemon_reachable": bool(tooling["docker"].get("daemon_reachable")),
            "node_red_available": bool(tooling["node_red"].get("available")),
            "spark_available": bool(tooling["spark"].get("available")),
            "field_validation_claim_ready": False,
            "real_dollar_claim_ready": False,
            "claim_boundary": "This bridge supports grant readiness and proof planning. It does not create field validation, realized savings, trading profit, or guaranteed awards.",
        },
        "use_today": [
            "Reviewer evidence gate: measured rows, hashes, and explicit claim boundaries.",
            "Geometry champion-of-champions board: ranked proof priorities across 75 families and 12 lanes.",
            (
                "Latest live measurement maximizer: "
                f"{live_summary['measured_sources']} measured sources and "
                f"{live_summary['total_measured_rows']} rows."
            ),
            "WhiteHole latest freeze and custody ledger: continuity/reproducibility evidence.",
        ],
        "do_not_overclaim": [
            "WhiteHole freezes are custody evidence, not performance evidence.",
            "Node-RED and Unity are presentation/demo tools unless wired to frozen measured outputs.",
            "Docker is not currently reachable and should not be part of a deadline-critical path.",
            "Spark is not installed and is unnecessary for the current measured-row scale.",
            "Market/Kraken evidence remains paper/read-only unless separate live-trading authorization and risk gates exist.",
        ],
        "whitehole": whitehole,
        "live_sources": live_summary,
        "geometry_champions": champion_summary,
        "local_tooling": tooling,
        "field_validation_gap": field_validation_gap(live_summary, champion_summary),
        "one_day_submission_bridge": [
            {
                "section": "Technical Merit",
                "insert": "Cite the live-source measurement bridge, reviewer evidence gate, and geometry champion board as reproducible pre-field validation infrastructure.",
            },
            {
                "section": "Work Plan",
                "insert": "Make Phase I the decisive live replay: frozen real input windows, incumbent baseline, LumenCore/geometry candidate, uncertainty interval, and independent review package.",
            },
            {
                "section": "Commercial/Government Impact",
                "insert": "Use dollar surfaces only as bounded market-sizing context, then state that validated savings require a partner baseline.",
            },
            {
                "section": "Risk",
                "insert": "Acknowledge current blockers: no partner baseline, NREL/SAM/EPA/Odds gaps, and no field validation yet. Reviewers trust controlled humility.",
            },
        ],
        "linkedin_resume_drafts": drafts,
        "inputs": {
            "live_measurement_maximizer": rel(LIVE_MAXIMIZER_JSON),
            "reviewer_evidence_gate": rel(REVIEWER_GATE_JSON),
            "geometry_champion_of_champions": rel(CHAMPIONS_JSON),
            "geometry_live_wiring_matrix": rel(LIVE_WIRING_JSON),
            "wiring_schema": wiring.get("schema", ""),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    drafts = payload["linkedin_resume_drafts"]
    lines = [
        "# Deadline Evidence Bridge",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Summary",
        "",
        f"- Reviewer packet ready: `{str(summary['ready_for_reviewer_packet']).lower()}`",
        f"- Live measured sources: {summary['live_measured_sources']}",
        f"- Live measured rows: {summary['live_total_measured_rows']}",
        f"- Geometry families ranked: {summary['geometry_families_ranked']}",
        f"- Geometry lanes ranked: {summary['geometry_lanes_ranked']}",
        f"- WhiteHole freeze bundles: {summary['whitehole_freeze_zip_count']}",
        f"- Latest WhiteHole freeze: `{summary['whitehole_latest_freeze']}`",
        f"- Docker daemon reachable: `{str(summary['docker_daemon_reachable']).lower()}`",
        f"- Node-RED available: `{str(summary['node_red_available']).lower()}`",
        f"- Spark available: `{str(summary['spark_available']).lower()}`",
        f"- Field-validation claim ready: `{str(summary['field_validation_claim_ready']).lower()}`",
        f"- Real-dollar claim ready: `{str(summary['real_dollar_claim_ready']).lower()}`",
        "",
        "## Use Today",
        "",
    ]
    lines.extend(f"- {item}" for item in payload["use_today"])
    lines.extend(["", "## Do Not Overclaim", ""])
    lines.extend(f"- {item}" for item in payload["do_not_overclaim"])
    lines.extend(["", "## One-Day Submission Bridge", ""])
    for item in payload["one_day_submission_bridge"]:
        lines.append(f"- {item['section']}: {item['insert']}")
    lines.extend(["", "## Field Validation Gap", ""])
    lines.extend(f"- {item}" for item in payload["field_validation_gap"])
    lines.extend(
        [
            "",
            "## LinkedIn/Resume Draft",
            "",
            f"Headline: {drafts['linkedin_headline']}",
            "",
            "About:",
            "",
            drafts["linkedin_about"],
            "",
            "Resume summary:",
            "",
            drafts["resume_summary"],
            "",
            "Resume bullets:",
        ]
    )
    lines.extend(f"- {item}" for item in drafts["resume_bullets"])
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            summary["claim_boundary"],
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    payload = build_bridge(check_docker=True)
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "live_measured_sources": payload["summary"]["live_measured_sources"],
                "live_total_measured_rows": payload["summary"]["live_total_measured_rows"],
                "whitehole_freeze_zip_count": payload["summary"]["whitehole_freeze_zip_count"],
                "docker_daemon_reachable": payload["summary"]["docker_daemon_reachable"],
                "node_red_available": payload["summary"]["node_red_available"],
                "spark_available": payload["summary"]["spark_available"],
                "field_validation_claim_ready": payload["summary"]["field_validation_claim_ready"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
