from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
GRANTS = ROOT / "grant_submissions"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD = ROOT / "dashboard"
DASHBOARD_DATA = DASHBOARD / "data"

OUT_JSON = OUT_OPS / "luma_context_dashboard_parity_audit_latest.json"
OUT_MD = DOCS / "LUMA_CONTEXT_DASHBOARD_PARITY_AUDIT_2026-06-22.md"
DASHBOARD_JSON = DASHBOARD_DATA / "luma_context_dashboard_parity_audit.json"

LIVE_BASE = "https://lumen-core.ai"

CONTEXT_CHECKPOINTS = [
    ("agent_continuity_rules", ROOT / "AGENTS.md"),
    ("operating_memory", DOCS / "LUMAJARVIS_OPERATING_MEMORY_2026-06-20.md"),
    ("legendary_goal_prompt", DOCS / "LUMAJARVIS_LEGENDARY_GOAL_PROMPT_2026-06-21.md"),
    ("dashboard_architecture", DOCS / "DASHBOARD_ARCHITECTURE.md"),
    ("grant_deadline_triage", GRANTS / "GRANT_DEADLINE_TRIAGE_2026-06-22.md"),
    ("top5_live_proof_board", GRANTS / "TOP5_LIVE_PROOF_SUBMISSION_BOARD_2026-06-22.md"),
    ("geometry_frontier", DOCS / "GEOMETRY_PROOF_FRONTIER_BOARD_2026-06-22.md"),
    ("geometry_live_breadth_queue", DOCS / "GEOMETRY_LIVE_BREADTH_PROOF_QUEUE_2026-06-22.md"),
    ("public_visibility", DOCS / "PUBLIC_VISIBILITY_AND_SOURCE_AUTHORITY_2026-06-20.md"),
    ("local_icloud_intake", GRANTS / "LOCAL_ICLOUD_EVIDENCE_INTAKE_2026-06-21.md"),
    ("patent_legal_rescue", GRANTS / "PATENT_LEGAL_RESCUE_PACKET_2026-06-20.md"),
]

CANONICAL_DASHBOARDS = [
    {
        "key": "mission_control",
        "route": "/mission_control.html",
        "path": DASHBOARD / "mission_control.html",
        "role": "system health, evidence, approvals, operating posture",
        "must_show": ["grant_pipeline", "live_breadth", "live_proof_value_meter", "domain_parity", "claim_boundaries"],
    },
    {
        "key": "quant_lab",
        "route": "/quant_lab.html",
        "path": DASHBOARD / "quant_lab.html",
        "role": "unified research cockpit and operator navigation host",
        "must_show": ["geometry_frontier", "kraken_truth", "grant_pipeline", "live_proof_value_meter", "claim_boundaries"],
    },
    {
        "key": "grants",
        "route": "/grants.html",
        "path": DASHBOARD / "grants.html",
        "role": "opportunity qualification, application readiness, submission workflow",
        "must_show": [
            "top5_live_proof",
            "live_proof_value_meter",
            "portal_gates",
            "discarded_workspaces",
            "action_order",
            "field_validation_targets",
        ],
    },
    {
        "key": "proof_to_pilot",
        "route": "/proof_to_pilot.html",
        "path": DASHBOARD / "proof_to_pilot.html",
        "role": "field-validation gate, buyer-safe outreach, pilot conversion, claim controls",
        "must_show": [
            "proof_to_pilot_control_room",
            "field_validation_control_room",
            "field_validation_outreach_board",
            "buyer_authorized_replay",
            "claim_boundaries",
        ],
    },
]

LOCAL_FEEDS = [
    ("grant_readiness_status", DASHBOARD_DATA / "grant_readiness_status.json"),
    ("top5_live_proof_submission_board", DASHBOARD_DATA / "top5_live_proof_submission_board.json"),
    ("live_proof_value_meter", DASHBOARD_DATA / "live_proof_value_meter.json"),
    ("geometry_asset_wiring_board", DASHBOARD_DATA / "geometry_asset_wiring_board.json"),
    ("geometry_proof_frontier_board", DASHBOARD_DATA / "geometry_proof_frontier_board.json"),
    ("geometry_live_breadth_proof_queue", DASHBOARD_DATA / "geometry_live_breadth_proof_queue.json"),
    ("champion_metric_gauntlet", DASHBOARD_DATA / "champion_metric_gauntlet.json"),
    ("kuramoto_holdout_expansion", DASHBOARD_DATA / "kuramoto_holdout_expansion.json"),
    ("geometry_champion_of_champions", DASHBOARD_DATA / "geometry_champion_of_champions.json"),
    ("field_validation_control_room", DASHBOARD_DATA / "field_validation_control_room.json"),
    ("field_validation_outreach_board", DASHBOARD_DATA / "field_validation_outreach_board.json"),
    ("proof_to_pilot_control_room", DASHBOARD_DATA / "proof_to_pilot_control_room.json"),
    ("paid_pilot_outreach_queue", DASHBOARD_DATA / "paid_pilot_outreach_queue.json"),
    ("proof_to_revenue_engine", DASHBOARD_DATA / "proof_to_revenue_engine.json"),
    ("live_domain_deployment_feed", DASHBOARD_DATA / "live_domain_deployment_feed.json"),
    ("public_visibility_packet", DASHBOARD_DATA / "public_visibility_packet.json"),
    ("lumencore_high_impact_goal", DASHBOARD_DATA / "lumencore_high_impact_goal.json"),
]

LIVE_FEED_PATHS = [
    "/data/grant_readiness_status.json",
    "/data/top5_live_proof_submission_board.json",
    "/data/live_proof_value_meter.json",
    "/data/geometry_asset_wiring_board.json",
    "/data/geometry_proof_frontier_board.json",
    "/data/geometry_live_breadth_proof_queue.json",
    "/data/champion_metric_gauntlet.json",
    "/data/field_validation_control_room.json",
    "/data/field_validation_outreach_board.json",
    "/data/proof_to_pilot_control_room.json",
    "/data/proof_to_revenue_engine.json",
    "/data/public_visibility_packet.json",
    "/dashboard/data/grant_readiness_status.json",
    "/dashboard/data/top5_live_proof_submission_board.json",
    "/dashboard/data/live_proof_value_meter.json",
    "/dashboard/data/geometry_asset_wiring_board.json",
    "/dashboard/data/geometry_proof_frontier_board.json",
    "/dashboard/data/geometry_live_breadth_proof_queue.json",
    "/dashboard/data/champion_metric_gauntlet.json",
    "/dashboard/data/field_validation_control_room.json",
    "/dashboard/data/field_validation_outreach_board.json",
    "/dashboard/data/proof_to_pilot_control_room.json",
    "/dashboard/data/proof_to_revenue_engine.json",
    "/dashboard/data/public_visibility_packet.json",
    "/out/ops/grant_dashboard_status_feed_latest.json",
    "/out/ops/geometry_asset_wiring_board_latest.json",
]


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


def sha256_prefix(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def file_card(key: str, path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "key": key,
        "path": str(path.relative_to(ROOT)) if path.is_absolute() and path.exists() else str(path),
        "exists": exists,
        "bytes": path.stat().st_size if exists and path.is_file() else 0,
        "modified_utc": datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
        if exists and path.is_file()
        else None,
        "sha256_prefix": sha256_prefix(path) if exists and path.is_file() else "",
    }


def git_dirty_summary() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "total_dirty_entries": 0,
            "counts_by_code": {},
            "sample": [],
            "policy": "Do not clean or reset without user approval.",
        }
    lines = [line.rstrip("\n") for line in proc.stdout.splitlines() if line.strip()]
    counts = Counter(line[:2] for line in lines)
    untracked = [line[3:] for line in lines if line.startswith("?? ")]
    modified = [line[3:] for line in lines if "M" in line[:2] and not line.startswith("?? ")]
    added = [line[3:] for line in lines if "A" in line[:2] and not line.startswith("?? ")]
    return {
        "available": proc.returncode == 0,
        "total_dirty_entries": len(lines),
        "counts_by_code": dict(sorted(counts.items())),
        "untracked_count": len(untracked),
        "modified_count": len(modified),
        "added_count": len(added),
        "sample": lines[:40],
        "policy": (
            "Treat the dirty repo as active worktrail. Classify before committing. "
            "Do not reset, checkout, delete, or clean generated artifacts unless Robert explicitly approves."
        ),
    }


def html_title(text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def dashboard_card(surface: dict[str, Any]) -> dict[str, Any]:
    path = surface["path"]
    card = file_card(surface["key"], path)
    text = ""
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
    refs = {
        "command_fabric_css": "luma_command_fabric.css" in text,
        "command_fabric_js": "luma_command_fabric.js" in text,
        "path_resolver": "luma_path_resolver.js" in text,
        "cinematic_layer": "cinematic_telemetry_layer.js" in text,
        "grant_readiness_status": "grant_readiness_status" in text,
        "top5_live_proof": "top5_live_proof" in text,
        "live_proof_value_meter": "live_proof_value_meter" in text or "Live Proof Value Meter" in text,
        "geometry_asset_wiring_board": "geometry_asset_wiring_board" in text,
        "champion_metric_gauntlet": "champion_metric_gauntlet" in text,
        "field_validation_control_room": "field_validation_control_room" in text,
        "field_validation_outreach_board": "field_validation_outreach_board" in text,
        "proof_to_pilot_control_room": "proof_to_pilot_control_room" in text,
        "proof_to_revenue_engine": "proof_to_revenue_engine" in text,
        "field_validation_targets": (
            "field-validation" in text.lower()
            or "field_validation_target_queue" in text
            or "buyer-authorized replay" in text.lower()
        ),
        "discarded_workspaces": "discarded_workspaces" in text or "discardedLabel" in text,
        "context_parity_audit": "luma_context_dashboard_parity_audit" in text or "continuity audit" in text.lower(),
        "geometry_frontier": "geometry_proof_frontier" in text or "geometry_frontier" in text,
        "public_visibility": "public_visibility_packet" in text,
        "kraken_truth": "kraken" in text.lower() and ("live" in text.lower() or "paper" in text.lower()),
    }
    missing = []
    for required in surface["must_show"]:
        if required == "top5_live_proof" and not refs["top5_live_proof"]:
            missing.append(required)
        elif required == "live_proof_value_meter" and not refs["live_proof_value_meter"]:
            missing.append(required)
        elif required == "geometry_frontier" and not refs["geometry_frontier"]:
            missing.append(required)
        elif required == "domain_parity" and not refs["context_parity_audit"]:
            missing.append(required)
        elif required == "claim_boundaries" and "boundary" not in text.lower() and "claim" not in text.lower():
            missing.append(required)
        elif required == "discarded_workspaces" and not refs["discarded_workspaces"]:
            missing.append(required)
        elif required == "field_validation_targets" and not refs["field_validation_targets"]:
            missing.append(required)
        elif required == "proof_to_pilot_control_room" and not refs["proof_to_pilot_control_room"]:
            missing.append(required)
        elif required == "field_validation_control_room" and not refs["field_validation_control_room"]:
            missing.append(required)
        elif required == "field_validation_outreach_board" and not refs["field_validation_outreach_board"]:
            missing.append(required)
        elif required == "buyer_authorized_replay" and "buyer-authorized" not in text.lower():
            missing.append(required)
        elif required == "paper_or_live_truth" and "PAPER" not in text and "LIVE" not in text:
            missing.append(required)
        elif required == "no_profit_claim_without_audit" and "profit" not in text.lower():
            missing.append(required)
    card.update(
        {
            "route": surface["route"],
            "role": surface["role"],
            "title": html_title(text),
            "references": refs,
            "parity_state": "NEEDS_TODAY_FEED_WIRING" if missing else "CANONICAL_SURFACE_PRESENT",
            "missing_or_weak_lanes": missing,
        }
    )
    return card


def local_feed_cards() -> list[dict[str, Any]]:
    rows = []
    for key, path in LOCAL_FEEDS:
        card = file_card(key, path)
        payload = read_json(path)
        card["schema"] = payload.get("schema", "")
        card["generated_utc"] = payload.get("generated_utc")
        card["posture"] = payload.get("posture")
        rows.append(card)
    return rows


def probe_url(url: str, timeout: int = 12) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": "LumaContextParityAudit/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read(1024 * 1024)
            return {
                "url": url,
                "ok": 200 <= int(resp.status) < 400,
                "status": int(resp.status),
                "bytes_sampled": len(body),
                "content_type": resp.headers.get("Content-Type", ""),
            }
    except HTTPError as exc:
        return {
            "url": url,
            "ok": False,
            "status": int(exc.code),
            "bytes_sampled": 0,
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
        }
    except URLError as exc:
        return {"url": url, "ok": False, "status": "URL_ERROR", "bytes_sampled": 0, "error": str(exc.reason)}
    except Exception as exc:
        return {"url": url, "ok": False, "status": "ERROR", "bytes_sampled": 0, "error": str(exc)}


def live_domain_parity(check_live_domain: bool) -> dict[str, Any]:
    page_routes = [surface["route"] for surface in CANONICAL_DASHBOARDS]
    if not check_live_domain:
        return {
            "checked": False,
            "base": LIVE_BASE,
            "page_probes": [],
            "feed_probes": [],
            "parity_state": "NOT_CHECKED",
            "boundary": "Live domain parity was not checked in this build.",
        }
    pages = [probe_url(f"{LIVE_BASE}{route}") for route in page_routes]
    feeds = [probe_url(f"{LIVE_BASE}{path}") for path in LIVE_FEED_PATHS]
    page_ok = sum(1 for row in pages if row.get("ok"))
    feed_ok = sum(1 for row in feeds if row.get("ok"))
    return {
        "checked": True,
        "base": LIVE_BASE,
        "page_probes": pages,
        "feed_probes": feeds,
        "page_ok": page_ok,
        "page_total": len(pages),
        "feed_ok": feed_ok,
        "feed_total": len(feeds),
        "parity_state": "HTML_LIVE_DATA_FEEDS_MISSING" if page_ok and feed_ok < len(feeds) else "DOMAIN_PARITY_OK",
        "boundary": (
            "Local dashboard/data freshness does not prove VPS/domain deployment. "
            "A reviewer-facing live claim requires the same fresh JSON feeds to be reachable on the live domain."
        ),
    }


def grant_pipeline_snapshot() -> dict[str, Any]:
    feed = read_json(OUT_OPS / "grant_dashboard_status_feed_latest.json")
    top5 = read_json(OUT_OPS / "top5_live_proof_submission_board_latest.json")
    triage = read_json(OUT_OPS / "grant_deadline_triage_latest.json")
    priority_cards = feed.get("priority_cards", []) if isinstance(feed.get("priority_cards"), list) else []
    live_card = next((row for row in priority_cards if isinstance(row, dict) and row.get("key") == "Live Proof Gate"), {})
    return {
        "dashboard_posture": feed.get("posture", "UNKNOWN"),
        "summary": feed.get("summary", {}),
        "live_proof_gate": {
            "value": live_card.get("value"),
            "sub": live_card.get("sub"),
            "tone": live_card.get("tone"),
        },
        "active_start_package": top5.get("active_start_package", {}),
        "closest_action_gate": top5.get("closest_action_gate", {}),
        "triage_summary": triage.get("summary", {}),
        "rule": (
            "No final grant submit until the exact proposal has proposal-specific live proof "
            "and portal/compliance/action-time gates pass."
        ),
    }


def geometry_snapshot() -> dict[str, Any]:
    frontier = read_json(OUT_OPS / "geometry_proof_frontier_board_latest.json")
    queue = read_json(OUT_OPS / "geometry_live_breadth_proof_queue_latest.json")
    asset_wiring = read_json(OUT_OPS / "geometry_asset_wiring_board_latest.json")
    champions = frontier.get("champion_board", {}) if isinstance(frontier.get("champion_board"), dict) else {}
    gate = frontier.get("promotion_gate", {}) if isinstance(frontier.get("promotion_gate"), dict) else {}
    queue_champions = queue.get("champions", {}) if isinstance(queue.get("champions"), dict) else {}
    queue_gate = queue.get("promotion_gate", {}) if isinstance(queue.get("promotion_gate"), dict) else {}
    queue_value = queue.get("valuation_posture", {}) if isinstance(queue.get("valuation_posture"), dict) else {}
    top_next_runs = queue.get("top_next_runs", []) if isinstance(queue.get("top_next_runs"), list) else []
    asset_summary = asset_wiring.get("summary", {}) if isinstance(asset_wiring.get("summary"), dict) else {}
    field_targets = (
        asset_wiring.get("field_validation_target_queue", [])
        if isinstance(asset_wiring.get("field_validation_target_queue"), list)
        else []
    )
    return {
        "registry_health": frontier.get("registry_health", {}),
        "champions": champions,
        "promotion_gate": gate,
        "next_live_wiring": champions.get("recommended_next_live_wiring", {}),
        "live_breadth_queue": {
            "schema": queue.get("schema", ""),
            "families_ranked": queue_gate.get("families_ranked", 0),
            "champions": queue_champions,
            "promotion_gate": queue_gate,
            "valuation_posture": queue_value,
            "top_next_runs": top_next_runs[:6],
        },
        "field_validation_targets": {
            "summary": asset_summary,
            "top_targets": field_targets[:5],
            "boundary": asset_wiring.get(
                "evidence_boundary",
                "Field-validation targets require outside-owner data, locked baselines, and accepted holdouts.",
            ),
        },
        "rule": "No geometry is sacred until it wins on frozen, reproducible, proposal-relevant data.",
    }


def evidence_intake_snapshot() -> dict[str, Any]:
    intake = read_json(OUT_OPS / "local_icloud_evidence_intake_latest.json")
    summary = intake.get("summary", {}) if isinstance(intake.get("summary"), dict) else {}
    return {
        "available": bool(intake),
        "summary": summary,
        "best_current_use": (
            "provenance, grant context, read-only ops scaffold, patent/legal context, and concept visuals"
        ),
        "boundary": (
            "Local/iCloud evidence intake is metadata/provenance unless each item passes source, hash, "
            "license, privacy, and proposal-specific relevance checks."
        ),
    }


def anti_drift_protocol() -> list[str]:
    return [
        "Read this audit before new grant, dashboard, trading, or proof work.",
        "Read LUMAJARVIS_OPERATING_MEMORY_2026-06-20.md next; treat it as operating law unless superseded by a newer audited file.",
        "Run git status and classify dirty entries before editing or committing.",
        "Do not reset, clean, delete, or overwrite unrelated generated/user work.",
        "Converge public work into four canonical boards: Mission Control, Grants, Quant Lab, and Proof-to-Pilot.",
        "Treat Kraken Execution, LumaScout, investor rooms, and immersive demos as secondary boards unless this audit promotes them.",
        "Use TOP5_LIVE_PROOF_SUBMISSION_BOARD and GRANT_DEADLINE_TRIAGE for grant ordering.",
        "Use GEOMETRY_PROOF_FRONTIER_BOARD and CHAMPION_METRIC_GAUNTLET for geometry claims; do not turn generated wins into live, field, or dollar claims.",
        "Use Proof-to-Pilot for buyer-authorized replay, outreach, and claim-gate work; do not create a new revenue dashboard first.",
        "Use LOCAL_ICLOUD_EVIDENCE_INTAKE as an index, not as automatic proof.",
        "Verify live domain data feeds before saying the VPS/public site reflects today’s local work.",
        "Keep Kraken/trading output separated from grant proof unless an audited track record exists.",
    ]


def build_audit(check_live_domain: bool = True) -> dict[str, Any]:
    dashboards = [dashboard_card(surface) for surface in CANONICAL_DASHBOARDS]
    context = [file_card(key, path) for key, path in CONTEXT_CHECKPOINTS]
    local_feeds = local_feed_cards()
    domain = live_domain_parity(check_live_domain)
    dirty = git_dirty_summary()
    needs = []
    if dirty["total_dirty_entries"] > 0:
        needs.append("classify_dirty_worktrail_before_commit")
    if domain.get("parity_state") == "HTML_LIVE_DATA_FEEDS_MISSING":
        needs.append("deploy_or_route_fresh_dashboard_data_feeds_to_live_domain")
    if any(card["parity_state"] != "CANONICAL_SURFACE_PRESENT" for card in dashboards):
        needs.append("wire_today_proof_boards_into_top_dashboards")
    return {
        "schema": "luma_context_dashboard_parity_audit_v1",
        "generated_utc": now_utc(),
        "repo": str(ROOT),
        "dirty_worktree": dirty,
        "context_checkpoints": context,
        "canonical_dashboards": dashboards,
        "local_dashboard_feeds": local_feeds,
        "live_domain_parity": domain,
        "grant_pipeline": grant_pipeline_snapshot(),
        "geometry_frontier": geometry_snapshot(),
        "local_icloud_evidence_intake": evidence_intake_snapshot(),
        "anti_drift_protocol": anti_drift_protocol(),
        "priority_needs": needs,
        "answer_to_why_dirty": (
            "The repo is dirty because the workspace contains active generated artifacts, tests, dashboards, "
            "grant packets, proof boards, and prior uncommitted work. That is dangerous only if treated as trash; "
            "handled correctly, it is the worktrail that must be classified and promoted deliberately."
        ),
        "answer_to_context_loss": (
            "Codex does not continuously see every local/iCloud file or retain unlimited chat memory. "
            "The durable solution is audited checkpoints like this report plus the operating memory, read first on every serious run."
        ),
    }


def render_markdown(audit: dict[str, Any]) -> str:
    dirty = audit["dirty_worktree"]
    domain = audit["live_domain_parity"]
    grant = audit["grant_pipeline"]
    geometry = audit["geometry_frontier"]
    intake = audit["local_icloud_evidence_intake"]
    lines = [
        "# Luma Context + Dashboard Parity Audit",
        "",
        f"Generated: {audit['generated_utc']}",
        "",
        "## Why The Repo Is Dirty",
        "",
        audit["answer_to_why_dirty"],
        "",
        f"- Dirty entries: `{dirty['total_dirty_entries']}`",
        f"- Untracked: `{dirty.get('untracked_count', 0)}`",
        f"- Modified: `{dirty.get('modified_count', 0)}`",
        f"- Added: `{dirty.get('added_count', 0)}`",
        f"- Policy: {dirty['policy']}",
        "",
        "## Context Checkpoints",
        "",
    ]
    for row in audit["context_checkpoints"]:
        mark = "OK" if row["exists"] else "MISSING"
        lines.append(f"- {mark} `{row['key']}` -> `{row['path']}`")
    lines.extend(["", "## Dashboard Parity", ""])
    for row in audit["canonical_dashboards"]:
        refs = row["references"]
        lines.append(
            f"- `{row['route']}`: `{row['parity_state']}`; fabric js={str(refs['command_fabric_js']).lower()}, "
            f"grant_feed={str(refs['grant_readiness_status']).lower()}, top5={str(refs['top5_live_proof']).lower()}, "
            f"value_meter={str(refs['live_proof_value_meter']).lower()}, "
            f"geometry_frontier={str(refs['geometry_frontier']).lower()}, "
            f"geometry_asset={str(refs.get('geometry_asset_wiring_board', False)).lower()}, "
            f"field_targets={str(refs.get('field_validation_targets', False)).lower()}, "
            f"champion_gauntlet={str(refs.get('champion_metric_gauntlet', False)).lower()}, "
            f"proof_to_pilot={str(refs.get('proof_to_pilot_control_room', False)).lower()}, "
            f"field_control={str(refs.get('field_validation_control_room', False)).lower()}, "
            f"field_outreach={str(refs.get('field_validation_outreach_board', False)).lower()}"
        )
        if row["missing_or_weak_lanes"]:
            lines.append(f"  - Needs: {', '.join(row['missing_or_weak_lanes'])}")
    lines.extend(["", "## Live Domain Parity", ""])
    lines.append(f"- Base: `{domain['base']}`")
    lines.append(f"- Checked: `{str(domain['checked']).lower()}`")
    lines.append(f"- State: `{domain['parity_state']}`")
    if domain.get("checked"):
        lines.append(f"- HTML pages reachable: `{domain.get('page_ok', 0)}/{domain.get('page_total', 0)}`")
        lines.append(f"- Data feeds reachable: `{domain.get('feed_ok', 0)}/{domain.get('feed_total', 0)}`")
    lines.append(f"- Boundary: {domain['boundary']}")
    lines.extend(["", "## Grant Pipeline", ""])
    summary = grant.get("summary", {})
    live_gate = grant.get("live_proof_gate", {})
    active = grant.get("active_start_package", {})
    action = grant.get("closest_action_gate", {})
    lines.append(f"- Posture: `{grant.get('dashboard_posture')}`")
    lines.append(f"- Local blockers: `{summary.get('local_blockers')}`")
    lines.append(f"- Portal/user blockers: `{summary.get('portal_user_blockers')}`")
    lines.append(f"- Live proof gate: `{live_gate.get('value')}` - {live_gate.get('sub')}")
    lines.append(f"- Active start: `{active.get('package')}` via `{active.get('portal')}`")
    lines.append(f"- Closest action gate: `{action.get('portal')}` - {action.get('action')}")
    lines.append(f"- Rule: {grant['rule']}")
    lines.extend(["", "## Geometry Frontier", ""])
    champions = geometry.get("champions", {})
    generated = champions.get("generated_benchmark_champion", {})
    proof = champions.get("proof_value_champion", {})
    gate = geometry.get("promotion_gate", {})
    lines.append(
        f"- Generated champion: `{generated.get('family')}` on `{generated.get('lane')}`; "
        f"status `{generated.get('status')}`"
    )
    lines.append(
        f"- Proof-value champion: `{proof.get('family')}` on `{proof.get('lane')}`; "
        f"score `{proof.get('proof_priority_score')}`"
    )
    lines.append(f"- Ready for live geometry claim: `{str(gate.get('ready_for_live_geometry_claim')).lower()}`")
    lines.append(f"- Ready for real-dollar claim: `{str(gate.get('ready_for_real_dollar_claim')).lower()}`")
    lines.append(f"- Kraken live execution allowed: `{str(gate.get('kraken_live_execution_allowed')).lower()}`")
    queue = geometry.get("live_breadth_queue", {})
    queue_champions = queue.get("champions", {}) if isinstance(queue.get("champions"), dict) else {}
    queue_value = queue.get("valuation_posture", {}) if isinstance(queue.get("valuation_posture"), dict) else {}
    fastest = queue_champions.get("fastest_live_breadth_adapter", {}) if isinstance(queue_champions, dict) else {}
    lines.append(f"- Live-breadth queue families ranked: `{queue.get('families_ranked', 0)}`")
    lines.append(f"- Fastest live-breadth adapter: `{fastest.get('family_id')}` on `{fastest.get('lane')}`")
    lines.append(f"- Safe estimated annual value surface: `{queue_value.get('safe_estimated_annual_value_usd', 0)}`")
    field_targets = geometry.get("field_validation_targets", {})
    field_summary = field_targets.get("summary", {}) if isinstance(field_targets, dict) else {}
    lines.append(
        f"- Field-validation targets mapped: `{field_summary.get('field_validation_target_count', 0)}`; "
        f"buyer-authorized replay asks: `{field_summary.get('buyer_authorized_replay_ready_count', 0)}`; "
        f"field validated: `{str(field_summary.get('field_validation')).lower()}`"
    )
    lines.extend(["", "## Local + iCloud Worktrail", ""])
    intake_summary = intake.get("summary", {})
    lines.append(f"- Indexed records: `{intake_summary.get('records', 0)}`")
    lines.append(f"- Best current use: {intake['best_current_use']}")
    lines.append(f"- Boundary: {intake['boundary']}")
    lines.extend(["", "## Anti-Drift Protocol", ""])
    for step in audit["anti_drift_protocol"]:
        lines.append(f"- {step}")
    lines.extend(["", "## Priority Needs", ""])
    for need in audit["priority_needs"]:
        lines.append(f"- `{need}`")
    if not audit["priority_needs"]:
        lines.append("- None")
    return "\n".join(lines)


def main() -> None:
    audit = build_audit(check_live_domain=True)
    write_json(OUT_JSON, audit)
    write_json(DASHBOARD_JSON, audit)
    write_text(OUT_MD, render_markdown(audit))
    print(json.dumps({"json": str(OUT_JSON), "markdown": str(OUT_MD), "dashboard": str(DASHBOARD_JSON)}, indent=2))


if __name__ == "__main__":
    main()

