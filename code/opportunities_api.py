"""FastAPI router for opportunity harvest, filling, outreach, and tracking.

Core endpoints:
    GET  /api/opportunities/ranked             -> latest ranked.json
    GET  /api/opportunities/queue              -> queue.jsonl as array
    POST /api/opportunities/harvest            -> trigger harvester
    POST /api/opportunities/fill               -> trigger filler bot
    POST /api/opportunities/autopilot          -> harvest + fill + funding + outreach
    POST /api/opportunities/autopilot-v2       -> unified grants + linkedin + jobs autopilot
    POST /api/opportunities/crowdfunding/call  -> run crowdfunding-specific funding call
    GET  /api/opportunities/crowdfunding/queue -> latest crowdfunding queue slice
    GET  /api/opportunities/evidence/shipping/latest -> latest Node-RED + Unity evidence shipping status
    POST /api/opportunities/linkedin/optimize  -> build LumaLinkedIn assets + revised resume
    GET  /api/opportunities/linkedin/latest    -> latest LinkedIn optimization payload
    POST /api/opportunities/email/finder/run   -> run email opportunity finder cycle
    GET  /api/opportunities/email/finder/latest-> latest email finder summary payload
    GET  /api/opportunities/email/finder/queue -> queued email opportunities
    POST /api/opportunities/email/dispatch/run -> send resume packages to scored opportunities
    GET  /api/opportunities/email/dispatch/latest -> latest email dispatch summary payload
    POST /api/opportunities/email/response/run -> run inbox reply watcher cycle
    GET  /api/opportunities/email/response/latest -> latest reply watcher summary payload
    POST /api/opportunities/context/refresh    -> rebuild unified application context
    GET  /api/opportunities/context/latest     -> latest application context payload
    GET  /api/opportunities/investor/mission-pack/latest -> latest investor mission-control pack
    GET  /api/opportunities/investor/heartbeat/latest -> latest mission/control/alpha refresh heartbeat statuses
    GET  /api/opportunities/blueprints/latest  -> latest government-grade blueprint vault payload
    GET  /api/opportunities/site-reach/latest  -> latest site reach and domain mission push payload
    GET  /api/opportunities/grants/live-fill/latest -> latest autonomous grant live-fill payload
    GET  /api/opportunities/alpha-edge/latest -> latest alpha/edge lock engine artifact
    GET  /api/opportunities/investor/pitch/latest -> latest 3-minute Nobel-tier investor pitch
    POST /api/opportunities/jobs/factory       -> build resume-backed job packages
    GET  /api/opportunities/jobs/queue         -> latest jobs queue index
    GET  /api/opportunities/tracker            -> cross-channel state rollup
    GET  /api/opportunities/awards             -> granted/awarded items
    GET  /api/opportunities/outreach/templates -> loaded outreach templates
    POST /api/opportunities/outreach/generate  -> generate pilot outreach pack
    GET  /api/opportunities/package/{slug}     -> read a drafted package
    POST /api/opportunities/{slug}/state       -> update draft/submitted/granted state
    POST /api/opportunities/{slug}/approve     -> compatibility alias to /state
"""
from __future__ import annotations

import csv
import hmac
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "opportunities"
OUTREACH_OUT = OUT / "outreach"
LINKEDIN_OUT = OUT / "linkedin"
SOCIAL_OUT = OUT / "social"
OPS_OUT = ROOT / "out" / "ops"
GRANTS_QUEUE = ROOT / "out" / "grants" / "_queue" / "index.json"
FUNDING_QUEUE = ROOT / "out" / "funding" / "funding_approval_queue.json"
CROWDFUNDING_CAMPAIGN_QUEUE = ROOT / "out" / "crowdfunding_approval_queue.json"
JOBS_ROOT = ROOT / "out" / "jobs"
JOBS_QUEUE = JOBS_ROOT / "_queue" / "index.json"
EMAIL_OUT = OUT / "email"
EMAIL_LATEST = EMAIL_OUT / "email_opportunities_latest.json"
EMAIL_QUEUE = EMAIL_OUT / "email_opportunity_queue_latest.json"
EMAIL_MANIFEST_LATEST = ROOT / "out" / "ops" / "email_opportunity_finder" / "email_opportunity_manifest_latest.json"
EMAIL_DISPATCH_LATEST = EMAIL_OUT / "outbound_resume_dispatch_latest.json"
EMAIL_DISPATCH_QUEUE = EMAIL_OUT / "outbound_resume_dispatch_queue_latest.json"
EMAIL_DISPATCH_MANIFEST_LATEST = ROOT / "out" / "ops" / "email_resume_dispatcher" / "email_resume_dispatch_manifest_latest.json"
EMAIL_RESPONSE_LATEST = EMAIL_OUT / "email_response_watcher_latest.json"
EMAIL_RESPONSE_QUEUE = EMAIL_OUT / "email_response_queue_latest.json"
EMAIL_RESPONSE_MANIFEST_LATEST = ROOT / "out" / "ops" / "email_response_watcher" / "email_response_manifest_latest.json"
RESUME_LATEST = ROOT / "out" / "resume" / "resume_lumalinkedin_v1_latest.json"
LINKEDIN_LATEST = LINKEDIN_OUT / "lumalinkedin_v1_latest.json"
LINKEDIN_BUILD_LATEST = ROOT / "out" / "ops" / "lumalinkedin_v1_build_latest.json"
SOCIAL_LATEST = SOCIAL_OUT / "social_platform_profile_latest.json"
SOCIAL_BUILD_LATEST = ROOT / "out" / "ops" / "social_platform_profile_build_latest.json"
MASTER_VAL_LATEST = ROOT / "out" / "ops" / "master_valuation" / "master_valuation_latest.json"
IP_GRANT_WIN_MANIFEST_LATEST = ROOT / "out" / "ip_layer" / "autonomous_grant_win_manifest_latest.json"
LUMA_EXPLAINER_QUANT_LATEST = ROOT / "out" / "ops" / "luma_explainer" / "luma_explainer_quantified_latest.json"
BOOTH_DESIGN_MANIFEST_LATEST = ROOT / "out" / "ops" / "booth_design" / "booth_design_manifest_latest.json"
BOOTH_PRINT_SPEC_LATEST = ROOT / "out" / "ops" / "booth_design" / "booth_print_spec.md"
BOOTH_SETUP_CHECKLIST_LATEST = ROOT / "out" / "ops" / "booth_design" / "booth_setup_checklist.md"
BOOTH_HOST_STYLE_GUIDE_LATEST = ROOT / "out" / "ops" / "booth_design" / "booth_host_style_guide.md"
PUBLIC_TRUTH_LATEST = ROOT / "out" / "ops" / "public_truth" / "public_truth_latest.json"
PUBLIC_TRUTH_MANIFEST_LATEST = ROOT / "out" / "ops" / "public_truth" / "public_truth_manifest_latest.json"
APP_CONTEXT_LATEST = ROOT / "out" / "ops" / "application_context" / "application_context_latest.json"
APP_CONTEXT_MANIFEST_LATEST = ROOT / "out" / "ops" / "application_context" / "application_context_manifest_latest.json"
GRANT_SUBMIT_FIT_PACK_LATEST = ROOT / "out" / "ops" / "grant_submit_fit_pack" / "grant_submit_fit_pack_latest.json"
INVESTOR_MISSION_CONTROL_PACK_LATEST = ROOT / "out" / "ops" / "investor_mission_control" / "investor_mission_control_pack_latest.json"
INVESTOR_3MIN_PITCH_LATEST = ROOT / "out" / "ops" / "investor_mission_control" / "investor_3min_nobel_pitch_latest.md"
ALPHA_EDGE_LOCK_ENGINE_LATEST = ROOT / "out" / "ops" / "alpha_edge_lock" / "alpha_edge_lock_engine_latest.json"
ALPHA_EDGE_LOCK_ENGINE_HEARTBEAT_LATEST = ROOT / "out" / "ops" / "alpha_edge_lock" / "alpha_edge_lock_engine_heartbeat_latest.json"
INVESTOR_MISSION_CONTROL_HEARTBEAT_LATEST = ROOT / "out" / "ops" / "investor_mission_control" / "investor_mission_control_pack_heartbeat_latest.json"
INVESTOR_PACKET_REFRESH_LATEST = ROOT / "out" / "ops" / "investor_packet_refresh_latest.json"
INVESTOR_PACKET_REFRESH_HEARTBEAT_LATEST = ROOT / "out" / "ops" / "investor_packet_refresh" / "investor_packet_refresh_heartbeat_latest.json"
GOV_BLUEPRINT_VAULT_LATEST = ROOT / "out" / "ops" / "gov_blueprint_vault" / "gov_blueprint_vault_latest.json"
GOV_BLUEPRINT_VAULT_HEARTBEAT_LATEST = ROOT / "out" / "ops" / "gov_blueprint_vault" / "gov_blueprint_vault_heartbeat_latest.json"
SITE_REACH_MISSION_LATEST = ROOT / "out" / "ops" / "site_reach_mission" / "site_reach_mission_latest.json"
SITE_REACH_MISSION_HEARTBEAT_LATEST = ROOT / "out" / "ops" / "site_reach_mission" / "site_reach_mission_heartbeat_latest.json"
SECTOR_EVIDENCE_PIPELINE_LATEST = ROOT / "out" / "ops" / "sector_energy_evidence_pipeline_latest.json"
WHITEHOLE_ROOT = Path(os.getenv("WHITEHOLE_ROOT", r"C:\WhiteHole"))

PY = sys.executable
OUT.mkdir(parents=True, exist_ok=True)
OUTREACH_OUT.mkdir(parents=True, exist_ok=True)
LINKEDIN_OUT.mkdir(parents=True, exist_ok=True)
SOCIAL_OUT.mkdir(parents=True, exist_ok=True)
JOBS_ROOT.mkdir(parents=True, exist_ok=True)
OPS_OUT.mkdir(parents=True, exist_ok=True)

def _split_tokens(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [token.strip() for token in raw.split(",") if token.strip()]


def _expected_api_tokens() -> list[str]:
    names = (
        "LUMA_OPPORTUNITY_API_TOKEN",
        "LUMA_OPP_API_TOKEN",
        "LUMA_API_TOKEN",
    )
    values: list[str] = []
    for name in names:
        values.extend(_split_tokens(os.getenv(name)))
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            deduped.append(value)
            seen.add(value)
    return deduped


def _extract_bearer(authorization: str | None) -> str:
    raw = (authorization or "").strip()
    if not raw:
        return ""
    parts = raw.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return ""


def _require_api_token(
    x_luma_token: str | None = Header(default=None, alias="X-Luma-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    expected = _expected_api_tokens()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="api authentication is not configured",
        )

    provided = (x_luma_token or "").strip() or _extract_bearer(authorization)
    if not provided:
        raise HTTPException(status_code=401, detail="missing api token")

    if not any(hmac.compare_digest(provided, token) for token in expected):
        raise HTTPException(status_code=403, detail="invalid api token")


router = APIRouter(
    prefix="/api/opportunities",
    tags=["opportunities"],
    dependencies=[Depends(_require_api_token)],
)


def _read_json(p: Path) -> Any:
    if not p.exists():
        return None
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(p.read_text(encoding=enc))
        except Exception:
            continue
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None


def _read_jsonl(p: Path) -> list[dict[str, Any]]:
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _write_json(p: Path, payload: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(p)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _not_ready(
    *,
    error: str,
    hint: str = "",
    artifact: str | None = None,
    code: str = "not_ready",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": str(code),
        "error": str(error),
        "generated_utc": _now_utc_iso(),
    }
    if hint:
        payload["hint"] = str(hint)
    if artifact:
        payload["artifact"] = str(artifact)
    return payload


def _clamp_limit(limit: int, low: int = 1, high: int = 1000) -> int:
    try:
        value = int(limit)
    except Exception:
        value = low
    return max(low, min(high, value))


def _file_age_sec(path: Path) -> float | None:
    if not path.exists():
        return None
    return max(0.0, time.time() - path.stat().st_mtime)


def _heartbeat_snapshot(path: Path, stale_after_sec: float) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict):
        payload = {}
    age_sec = _file_age_sec(path)
    is_fresh = bool(age_sec is not None and age_sec <= float(stale_after_sec))
    return {
        "path": str(path),
        "exists": path.exists(),
        "status": str(payload.get("status") or "unknown"),
        "reason": str(payload.get("reason") or ""),
        "generated_utc": payload.get("generated_utc") or payload.get("timestamp_utc"),
        "age_sec": round(float(age_sec), 2) if age_sec is not None else None,
        "is_fresh": is_fresh,
        "stale_after_sec": float(stale_after_sec),
    }


def _latest_investor_proof_summary() -> dict[str, Any] | None:
    roots = [
        ROOT / "out" / "ops",
        ROOT.parent / "out" / "ops",
    ]
    candidates: list[Path] = []
    for base in roots:
        if not base.exists():
            continue
        candidates.extend(base.glob("investor_proof_sweep_*/proof_summary.json"))
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    payload = _read_json(latest)
    if not isinstance(payload, dict):
        return None
    payload["_path"] = str(latest)
    return payload


def _safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(value or "")).strip("_")


def _package_dir_from_slug(slug: str) -> Path:
    if ".." in slug or "/" in slug or "\\" in slug:
        raise HTTPException(404, f"package {slug} not found")
    p = OUT / slug
    if not p.is_dir():
        raise HTTPException(404, f"package {slug} not found")
    return p


def _latest_path(pattern: str) -> Path | None:
    if not WHITEHOLE_ROOT.exists():
        return None
    items = sorted(WHITEHOLE_ROOT.glob(pattern), key=lambda x: x.stat().st_mtime)
    return items[-1] if items else None


def _latest_linkedin_payload() -> dict[str, Any]:
    payload = _read_json(LINKEDIN_LATEST)
    return payload if isinstance(payload, dict) else {}


def _latest_social_payload() -> dict[str, Any]:
    payload = _read_json(SOCIAL_LATEST)
    return payload if isinstance(payload, dict) else {}


def _load_outreach_templates() -> dict[str, Any]:
    federal_dir = WHITEHOLE_ROOT / "federal_outreach"
    city_pack = _latest_path("CITY_PILOT_PACK_*")

    city_email = city_pack / "01_CITY_EMAIL_TEMPLATE.txt" if city_pack else None
    city_brief = city_pack / "00_CITY_PILOT_BRIEF.txt" if city_pack else None
    federal_email = federal_dir / "EMAIL_TEMPLATE.txt"
    subjects = federal_dir / "SUBJECT_LINES.txt"
    targets = _latest_path("federal_outreach/FIRST_25_TARGETS_*.csv")

    def _txt(p: Path | None) -> str:
        if not p or not p.exists():
            return ""
        return p.read_text(encoding="utf-8", errors="ignore")

    return {
        "city_email_template": _txt(city_email),
        "city_pilot_brief": _txt(city_brief),
        "federal_email_template": _txt(federal_email),
        "subject_lines": _txt(subjects),
        "targets_csv_path": str(targets) if targets and targets.exists() else None,
        "paths": {
            "city_email": str(city_email) if city_email and city_email.exists() else None,
            "city_brief": str(city_brief) if city_brief and city_brief.exists() else None,
            "federal_email": str(federal_email) if federal_email.exists() else None,
            "subject_lines": str(subjects) if subjects.exists() else None,
        },
    }


def _load_targets_csv(path: Path | None) -> list[dict[str, str]]:
    if not path or not path.exists():
        return []
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({k: str(v or "") for k, v in row.items()})
    return rows


def _render_template(template: str, replacements: dict[str, str]) -> str:
    text = template or ""
    for key, val in replacements.items():
        text = text.replace(key, val)
    return text


def _pilot_records(limit: int) -> list[dict[str, Any]]:
    ranked = _read_json(OUT / "ranked.json") or {}
    records = ranked.get("records", []) if isinstance(ranked, dict) else []
    if not isinstance(records, list):
        return []
    pilot_terms = (
        "pilot", "read-only", "resilience", "infrastructure", "facility",
        "operations", "monitor", "power", "cooling", "compute", "grid",
    )
    picked: list[dict[str, Any]] = []
    for rec in records:
        blob = " ".join([
            str(rec.get("title") or ""),
            str(rec.get("agency") or ""),
            str(rec.get("url") or ""),
            " ".join(rec.get("_keyword_matches") or []),
        ]).lower()
        if any(term in blob for term in pilot_terms):
            picked.append(rec)
    if not picked:
        picked = records
    return picked[:limit]


def _generate_outreach_pack(limit: int = 25) -> dict[str, Any]:
    templates = _load_outreach_templates()
    federal_template = templates.get("federal_email_template") or (
        "Hello <NAME>,\n\n"
        "I am proposing a 30-60 day read-only EchoLock pilot."
    )
    city_template = templates.get("city_email_template") or federal_template
    subject_blob = templates.get("subject_lines") or ""
    subjects = [
        line.strip().split(")", 1)[-1].strip()
        for line in subject_blob.splitlines()
        if line.strip() and not line.lower().startswith("subject")
    ]
    if not subjects:
        subjects = ["Read-only pilot proposal (EchoLock)"]

    targets_path = Path(templates["targets_csv_path"]) if templates.get("targets_csv_path") else None
    targets = _load_targets_csv(targets_path)
    pilots = _pilot_records(limit)
    top_pilot = pilots[0] if pilots else {}

    stamp = _utc_stamp()
    csv_path = OUTREACH_OUT / f"outreach_pack_{stamp}.csv"
    md_path = OUTREACH_OUT / f"outreach_pack_{stamp}.md"
    json_path = OUTREACH_OUT / f"outreach_pack_{stamp}.json"

    rows: list[dict[str, str]] = []
    for i, target in enumerate(targets[:limit] if targets else []):
        org = target.get("Org") or target.get("Organization") or "Target Organization"
        role = target.get("Team/Office") or target.get("Title") or "Facilities/Ops"
        contact = target.get("Contact Name") or target.get("Name") or "<Name>"
        email = target.get("Email") or target.get("email") or ""
        source = city_template if "city" in org.lower() else federal_template
        body = _render_template(source, {
            "<NAME>": contact,
            "<Name>": contact,
            "<name>": contact,
        })
        if top_pilot:
            body += (
                "\n\n"
                f"Pilot fit candidate: {top_pilot.get('title', 'N/A')}"
                f" ({top_pilot.get('source', 'opportunity')} · {top_pilot.get('agency', 'unknown')})."
            )
        subject = subjects[i % len(subjects)]
        rows.append({
            "priority": str(target.get("Priority") or i + 1),
            "organization": org,
            "team_or_office": role,
            "contact_name": contact,
            "email": email,
            "subject": subject,
            "email_draft": body,
            "pilot_opportunity": str(top_pilot.get("title") or ""),
            "pilot_source": str(top_pilot.get("source") or ""),
        })

    if not rows and pilots:
        for i, rec in enumerate(pilots[:limit]):
            subject = subjects[i % len(subjects)]
            body = _render_template(federal_template, {"<NAME>": "<Name>", "<Name>": "<Name>"})
            body += (
                "\n\n"
                f"Target opportunity: {rec.get('title', 'N/A')}\n"
                f"Agency: {rec.get('agency', 'N/A')}\n"
                f"Link: {rec.get('url', 'N/A')}"
            )
            rows.append({
                "priority": str(i + 1),
                "organization": str(rec.get("agency") or "Unknown"),
                "team_or_office": "Pilot Ops",
                "contact_name": "<Name>",
                "email": "",
                "subject": subject,
                "email_draft": body,
                "pilot_opportunity": str(rec.get("title") or ""),
                "pilot_source": str(rec.get("source") or ""),
            })

    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    md_lines = [
        f"# Outreach Pack {stamp}",
        "",
        f"Generated UTC: {_now_utc_iso()}",
        f"Rows: {len(rows)}",
        "",
        "## Pilot Opportunities",
    ]
    for rec in pilots[: min(20, len(pilots))]:
        md_lines.append(
            f"- {rec.get('source','unknown')} | {rec.get('agency','unknown')} | "
            f"{rec.get('title','untitled')} | score={rec.get('_fit_score', 'n/a')}"
        )
    md_lines.append("")
    md_lines.append("## Email Draft Targets")
    for row in rows[: min(30, len(rows))]:
        md_lines.append(
            f"- {row['organization']} | {row['team_or_office']} | {row['contact_name']} | {row['subject']}"
        )
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    payload = {
        "generated_utc": _now_utc_iso(),
        "count": len(rows),
        "targets_path": str(targets_path) if targets_path else None,
        "pilot_records_count": len(pilots),
        "templates": templates.get("paths", {}),
        "artifacts": {
            "csv": str(csv_path),
            "markdown": str(md_path),
        },
        "rows": rows,
    }
    _write_json(json_path, payload)
    payload["artifacts"]["json"] = str(json_path)
    return payload


def _build_tracker() -> dict[str, Any]:
    state_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    package_rows: list[dict[str, Any]] = []

    for p in sorted(OUT.iterdir()) if OUT.exists() else []:
        if not p.is_dir() or p.name == "outreach":
            continue
        state_obj = _read_json(p / "approval_state.json")
        if not isinstance(state_obj, dict):
            continue
        app = _read_json(p / "application.json") or {}
        state = str(state_obj.get("state") or "draft").lower()
        state_counts[state] = state_counts.get(state, 0) + 1
        source = p.name.split("__", 1)[0]
        source_counts[source] = source_counts.get(source, 0) + 1
        package_rows.append({
            "slug": p.name,
            "source": source,
            "state": state,
            "fit_score": state_obj.get("fit_score"),
            "title": app.get("12_funding_opportunity_title") or app.get("15_descriptive_title") or p.name,
            "tracking_id": state_obj.get("external_tracking_id"),
            "award_id": state_obj.get("award_id"),
            "awarded_amount_usd": state_obj.get("awarded_amount_usd"),
            "submitted_utc": state_obj.get("submitted_utc"),
            "granted_utc": state_obj.get("granted_utc"),
        })

    awards = [
        row for row in package_rows
        if row.get("state") in {"granted", "awarded"}
    ]

    grants_q = _read_json(GRANTS_QUEUE) or {}
    funding_q = _read_json(FUNDING_QUEUE) or []
    jobs_q = _read_json(JOBS_QUEUE) or {}
    email_latest = _read_json(EMAIL_LATEST) or {}
    email_queue = _read_json(EMAIL_QUEUE) or []
    email_manifest = _read_json(EMAIL_MANIFEST_LATEST) or {}
    email_dispatch_latest = _read_json(EMAIL_DISPATCH_LATEST) or {}
    email_dispatch_queue = _read_json(EMAIL_DISPATCH_QUEUE) or {}
    email_dispatch_manifest = _read_json(EMAIL_DISPATCH_MANIFEST_LATEST) or {}
    email_response_latest = _read_json(EMAIL_RESPONSE_LATEST) or {}
    email_response_queue = _read_json(EMAIL_RESPONSE_QUEUE) or []
    email_response_manifest = _read_json(EMAIL_RESPONSE_MANIFEST_LATEST) or {}
    linkedin_latest = _latest_linkedin_payload()
    linkedin_build_latest = _read_json(LINKEDIN_BUILD_LATEST) or {}
    social_latest = _latest_social_payload()
    social_build_latest = _read_json(SOCIAL_BUILD_LATEST) or {}
    resume_latest = _read_json(RESUME_LATEST) or {}
    crowdfunding_campaign_queue = _read_json(CROWDFUNDING_CAMPAIGN_QUEUE) or []
    valuation_latest = _read_json(MASTER_VAL_LATEST) or {}
    ip_manifest_latest = _read_json(IP_GRANT_WIN_MANIFEST_LATEST) or {}
    explainer_quant_latest = _read_json(LUMA_EXPLAINER_QUANT_LATEST) or {}
    public_truth_latest = _read_json(PUBLIC_TRUTH_LATEST) or {}
    public_truth_manifest = _read_json(PUBLIC_TRUTH_MANIFEST_LATEST) or {}
    app_context_latest = _read_json(APP_CONTEXT_LATEST) or {}
    app_context_manifest = _read_json(APP_CONTEXT_MANIFEST_LATEST) or {}
    grant_submit_fit_latest = _read_json(GRANT_SUBMIT_FIT_PACK_LATEST) or {}
    alpha_edge_lock_latest = _read_json(ALPHA_EDGE_LOCK_ENGINE_LATEST) or {}
    investor_mission_pack_latest = _read_json(INVESTOR_MISSION_CONTROL_PACK_LATEST) or {}
    investor_packet_refresh_latest = _read_json(INVESTOR_PACKET_REFRESH_LATEST) or {}
    gov_blueprint_vault_latest = _read_json(GOV_BLUEPRINT_VAULT_LATEST) or {}
    site_reach_mission_latest = _read_json(SITE_REACH_MISSION_LATEST) or {}

    alpha_edge_hb = _heartbeat_snapshot(ALPHA_EDGE_LOCK_ENGINE_HEARTBEAT_LATEST, stale_after_sec=3600.0)
    investor_mission_hb = _heartbeat_snapshot(INVESTOR_MISSION_CONTROL_HEARTBEAT_LATEST, stale_after_sec=3600.0)
    investor_refresh_hb = _heartbeat_snapshot(INVESTOR_PACKET_REFRESH_HEARTBEAT_LATEST, stale_after_sec=3600.0)
    blueprint_hb = _heartbeat_snapshot(GOV_BLUEPRINT_VAULT_HEARTBEAT_LATEST, stale_after_sec=7200.0)
    site_reach_hb = _heartbeat_snapshot(SITE_REACH_MISSION_HEARTBEAT_LATEST, stale_after_sec=7200.0)

    live_fill = (
        investor_mission_pack_latest.get("autonomous_grant_live_fill", {})
        if isinstance(investor_mission_pack_latest, dict)
        else {}
    )
    selected_live_fill = (
        live_fill.get("selected_opportunity", {})
        if isinstance(live_fill, dict)
        else {}
    )
    pitch_data = (
        investor_mission_pack_latest.get("three_min_nobel_pitch", {})
        if isinstance(investor_mission_pack_latest, dict)
        else {}
    )
    parity_data = (
        investor_mission_pack_latest.get("powerpoint_mirror_parity", {})
        if isinstance(investor_mission_pack_latest, dict)
        else {}
    )
    funding_counts: dict[str, int] = {}
    funding_channel_counts: dict[str, int] = {}
    if isinstance(funding_q, list):
        for item in funding_q:
            key = str(item.get("approval_state") or "UNKNOWN").upper()
            funding_counts[key] = funding_counts.get(key, 0) + 1
            channel = str(item.get("channel") or "unknown").lower()
            funding_channel_counts[channel] = funding_channel_counts.get(channel, 0) + 1

    crowdfunding_funding_rows = [
        item
        for item in (funding_q if isinstance(funding_q, list) else [])
        if isinstance(item, dict) and str(item.get("channel") or "").lower() == "crowdfund"
    ]
    crowdfunding_funding_rows.sort(key=lambda row: float(row.get("priority_score") or 0.0), reverse=True)

    crowdfunding_campaign_rows = [
        row for row in (crowdfunding_campaign_queue if isinstance(crowdfunding_campaign_queue, list) else []) if isinstance(row, dict)
    ]
    crowdfunding_campaign_rows.sort(
        key=lambda row: float(((row.get("platform") or {}).get("fit_score") or 0.0)),
        reverse=True,
    )

    sector_pipeline_latest = _read_json(SECTOR_EVIDENCE_PIPELINE_LATEST) or {}
    investor_proof_latest = _latest_investor_proof_summary() or {}
    node_red_unity = investor_proof_latest.get("node_red_unity") if isinstance(investor_proof_latest, dict) else {}

    payload = {
        "generated_utc": _now_utc_iso(),
        "opportunities": {
            "n_total": len(package_rows),
            "state_counts": state_counts,
            "source_counts": source_counts,
        },
        "awards": {
            "count": len(awards),
            "items": awards,
        },
        "grants_queue": {
            "n_total": grants_q.get("n_total", 0) if isinstance(grants_q, dict) else 0,
            "n_draft": grants_q.get("n_draft", 0) if isinstance(grants_q, dict) else 0,
            "n_approved": grants_q.get("n_approved", 0) if isinstance(grants_q, dict) else 0,
            "n_submitted": grants_q.get("n_submitted", 0) if isinstance(grants_q, dict) else 0,
        },
        "grant_live_fill": {
            "fit_pack_generated_utc": (
                grant_submit_fit_latest.get("generated_utc")
                if isinstance(grant_submit_fit_latest, dict)
                else None
            ),
            "fit_likely": (
                (grant_submit_fit_latest.get("summary", {}) or {}).get("fit_likely")
                if isinstance(grant_submit_fit_latest, dict)
                else None
            ),
            "status": live_fill.get("status") if isinstance(live_fill, dict) else None,
            "selected_opp_num": (
                selected_live_fill.get("opp_num")
                if isinstance(selected_live_fill, dict)
                else None
            ),
            "selected_submit_url": (
                selected_live_fill.get("submit_url")
                if isinstance(selected_live_fill, dict)
                else None
            ),
            "autofill_packet_ready": (
                live_fill.get("autofill_packet_ready")
                if isinstance(live_fill, dict)
                else None
            ),
        },
        "investor_mission_pack": {
            "latest_generated_utc": (
                investor_mission_pack_latest.get("generated_utc")
                if isinstance(investor_mission_pack_latest, dict)
                else None
            ),
            "pitch_total_seconds": (
                pitch_data.get("total_seconds")
                if isinstance(pitch_data, dict)
                else None
            ),
            "pitch_segments": (
                len(pitch_data.get("segments") or [])
                if isinstance(pitch_data, dict)
                else 0
            ),
            "powerpoint_parity_ok": (
                parity_data.get("parity_ok")
                if isinstance(parity_data, dict)
                else None
            ),
            "powerpoint_parity_drift_count": (
                parity_data.get("drift_count")
                if isinstance(parity_data, dict)
                else None
            ),
            "heartbeat": investor_mission_hb,
        },
        "alpha_edge_lock_engine": {
            "latest_generated_utc": (
                alpha_edge_lock_latest.get("generated_utc")
                if isinstance(alpha_edge_lock_latest, dict)
                else None
            ),
            "problem_count": (
                (alpha_edge_lock_latest.get("summary", {}) or {}).get("problem_count")
                if isinstance(alpha_edge_lock_latest, dict)
                else None
            ),
            "grade_a_locks": (
                (alpha_edge_lock_latest.get("summary", {}) or {}).get("grade_a_locks")
                if isinstance(alpha_edge_lock_latest, dict)
                else None
            ),
            "top_problem": (
                (alpha_edge_lock_latest.get("summary", {}) or {}).get("top_problem")
                if isinstance(alpha_edge_lock_latest, dict)
                else None
            ),
            "top_sector": (
                (alpha_edge_lock_latest.get("summary", {}) or {}).get("top_sector")
                if isinstance(alpha_edge_lock_latest, dict)
                else None
            ),
            "heartbeat": alpha_edge_hb,
        },
        "investor_packet_refresh": {
            "latest_generated_utc": (
                investor_packet_refresh_latest.get("generated_utc")
                if isinstance(investor_packet_refresh_latest, dict)
                else None
            ),
            "latest_artifact": (
                investor_packet_refresh_latest.get("latest_artifact")
                if isinstance(investor_packet_refresh_latest, dict)
                else None
            ),
            "heartbeat": investor_refresh_hb,
        },
        "gov_blueprints": {
            "latest_generated_utc": (
                gov_blueprint_vault_latest.get("generated_utc")
                if isinstance(gov_blueprint_vault_latest, dict)
                else None
            ),
            "asset_count": (
                (gov_blueprint_vault_latest.get("summary", {}) or {}).get("asset_count")
                if isinstance(gov_blueprint_vault_latest, dict)
                else None
            ),
            "focus_term_count": (
                (gov_blueprint_vault_latest.get("summary", {}) or {}).get("focus_term_count")
                if isinstance(gov_blueprint_vault_latest, dict)
                else None
            ),
            "highest_trl_target": (
                (gov_blueprint_vault_latest.get("summary", {}) or {}).get("highest_trl_target")
                if isinstance(gov_blueprint_vault_latest, dict)
                else None
            ),
            "heartbeat": blueprint_hb,
        },
        "site_reach_mission": {
            "latest_generated_utc": (
                site_reach_mission_latest.get("generated_utc")
                if isinstance(site_reach_mission_latest, dict)
                else None
            ),
            "canonical_visitors_30d": (
                (site_reach_mission_latest.get("summary", {}) or {}).get("canonical_visitors_30d")
                if isinstance(site_reach_mission_latest, dict)
                else None
            ),
            "canonical_visitors_source": (
                (site_reach_mission_latest.get("summary", {}) or {}).get("canonical_visitors_source")
                if isinstance(site_reach_mission_latest, dict)
                else None
            ),
            "promotion_channels_ready": (
                (site_reach_mission_latest.get("summary", {}) or {}).get("promotion_channels_ready")
                if isinstance(site_reach_mission_latest, dict)
                else None
            ),
            "heartbeat": site_reach_hb,
        },
        "funding_queue": {
            "n_total": len(funding_q) if isinstance(funding_q, list) else 0,
            "approval_state_counts": funding_counts,
            "channel_counts": funding_channel_counts,
            "crowdfunding_pending_human_approval": (
                sum(
                    1
                    for item in funding_q
                    if isinstance(item, dict)
                    and str(item.get("channel") or "").lower() == "crowdfund"
                    and str(item.get("approval_state") or "").upper() == "PENDING_HUMAN_APPROVAL"
                )
                if isinstance(funding_q, list)
                else 0
            ),
        },
        "crowdfunding": {
            "funding_queue_count": len(crowdfunding_funding_rows),
            "campaign_queue_count": len(crowdfunding_campaign_rows),
            "top_funding": crowdfunding_funding_rows[:5],
            "top_campaigns": crowdfunding_campaign_rows[:5],
        },
        "evidence_shipping": {
            "sector_pipeline_status": (
                sector_pipeline_latest.get("status")
                if isinstance(sector_pipeline_latest, dict)
                else None
            ),
            "sector_pipeline_generated_utc": (
                sector_pipeline_latest.get("generated_utc")
                if isinstance(sector_pipeline_latest, dict)
                else None
            ),
            "node_red_push_attempted": (
                node_red_unity.get("attempted")
                if isinstance(node_red_unity, dict)
                else None
            ),
            "node_red_ingest_status": (
                node_red_unity.get("ingest")
                if isinstance(node_red_unity, dict)
                else None
            ),
            "unity_scene_status": (
                node_red_unity.get("scene")
                if isinstance(node_red_unity, dict)
                else None
            ),
            "investor_proof_summary_path": (
                investor_proof_latest.get("_path")
                if isinstance(investor_proof_latest, dict)
                else None
            ),
        },
        "jobs_queue": {
            "n_total": jobs_q.get("n_total", 0) if isinstance(jobs_q, dict) else 0,
            "n_draft": jobs_q.get("n_draft", 0) if isinstance(jobs_q, dict) else 0,
            "n_approved": jobs_q.get("n_approved", 0) if isinstance(jobs_q, dict) else 0,
            "n_submitted": jobs_q.get("n_submitted", 0) if isinstance(jobs_q, dict) else 0,
            "n_interview": jobs_q.get("n_interview", 0) if isinstance(jobs_q, dict) else 0,
            "n_offer": jobs_q.get("n_offer", 0) if isinstance(jobs_q, dict) else 0,
        },
        "email_opportunities": {
            "latest_generated_utc": email_latest.get("generated_utc") if isinstance(email_latest, dict) else None,
            "sources_configured": email_latest.get("sources_configured") if isinstance(email_latest, dict) else 0,
            "new_opportunities": email_latest.get("new_opportunities") if isinstance(email_latest, dict) else 0,
            "queue_count": len(email_queue) if isinstance(email_queue, list) else 0,
            "manifest_status": email_manifest.get("status") if isinstance(email_manifest, dict) else None,
        },
        "email_dispatch": {
            "latest_generated_utc": email_dispatch_latest.get("generated_utc") if isinstance(email_dispatch_latest, dict) else None,
            "status": email_dispatch_latest.get("status") if isinstance(email_dispatch_latest, dict) else None,
            "dispatch_mode": email_dispatch_latest.get("dispatch_mode") if isinstance(email_dispatch_latest, dict) else None,
            "sent_count": email_dispatch_latest.get("sent_count") if isinstance(email_dispatch_latest, dict) else 0,
            "sent_total": email_dispatch_latest.get("sent_total") if isinstance(email_dispatch_latest, dict) else 0,
            "queue_count": (
                email_dispatch_queue.get("count")
                if isinstance(email_dispatch_queue, dict)
                else len(email_dispatch_queue)
                if isinstance(email_dispatch_queue, list)
                else 0
            ),
            "manifest_status": email_dispatch_manifest.get("status") if isinstance(email_dispatch_manifest, dict) else None,
        },
        "email_response_watcher": {
            "latest_generated_utc": email_response_latest.get("generated_utc") if isinstance(email_response_latest, dict) else None,
            "status": email_response_latest.get("status") if isinstance(email_response_latest, dict) else None,
            "new_responses": email_response_latest.get("new_responses") if isinstance(email_response_latest, dict) else 0,
            "matched_outbound_count": email_response_latest.get("matched_outbound_count") if isinstance(email_response_latest, dict) else 0,
            "queue_count": len(email_response_queue) if isinstance(email_response_queue, list) else 0,
            "manifest_status": email_response_manifest.get("status") if isinstance(email_response_manifest, dict) else None,
        },
        "linkedin": {
            "connected_payload_present": bool(linkedin_latest),
            "latest_generated_utc": linkedin_latest.get("generated_utc") if isinstance(linkedin_latest, dict) else None,
            "headline_primary": (
                linkedin_latest.get("headline_variants", [None])[0]
                if isinstance(linkedin_latest, dict)
                else None
            ),
            "resume_latest_generated_utc": resume_latest.get("generated_utc") if isinstance(resume_latest, dict) else None,
            "build_latest_generated_utc": (
                linkedin_build_latest.get("generated_utc")
                if isinstance(linkedin_build_latest, dict)
                else None
            ),
        },
        "social_media": {
            "profile_payload_present": bool(social_latest),
            "latest_generated_utc": social_latest.get("generated_utc") if isinstance(social_latest, dict) else None,
            "platforms_scanned": (
                ((social_latest.get("summary", {}) or {}).get("platforms_scanned"))
                if isinstance(social_latest, dict)
                else None
            ),
            "platforms_connected": (
                ((social_latest.get("summary", {}) or {}).get("platforms_connected"))
                if isinstance(social_latest, dict)
                else None
            ),
            "build_latest_generated_utc": (
                social_build_latest.get("generated_utc")
                if isinstance(social_build_latest, dict)
                else None
            ),
        },
        "valuation": {
            "latest_generated_utc": valuation_latest.get("generated_utc") if isinstance(valuation_latest, dict) else None,
            "scope": valuation_latest.get("scope") if isinstance(valuation_latest, dict) else None,
            "master_valuation_proxy_usd": (
                (valuation_latest.get("valuation", {}) or {}).get("master_valuation_proxy_usd")
                if isinstance(valuation_latest, dict)
                else None
            ),
            "valuation_increment_usd": (
                (valuation_latest.get("valuation", {}) or {}).get("valuation_increment_usd")
                if isinstance(valuation_latest, dict)
                else None
            ),
            "grant_and_opportunity_pipeline_value_usd": (
                (valuation_latest.get("valuation", {}) or {}).get("grant_and_opportunity_pipeline_value_usd")
                if isinstance(valuation_latest, dict)
                else None
            ),
            "grant_finding_and_ranking_system_license_value_usd": (
                (valuation_latest.get("valuation", {}) or {}).get("grant_finding_and_ranking_system_license_value_usd")
                if isinstance(valuation_latest, dict)
                else None
            ),
            "digital_scout_value_usd": (
                (valuation_latest.get("valuation", {}) or {}).get("digital_scout_value_usd")
                if isinstance(valuation_latest, dict)
                else None
            ),
            "institutional_trading_system_value_usd": (
                (valuation_latest.get("valuation", {}) or {}).get("institutional_trading_system_value_usd")
                if isinstance(valuation_latest, dict)
                else None
            ),
            "validated_engine_autonomy_value_usd": (
                (valuation_latest.get("valuation", {}) or {}).get("validated_engine_autonomy_value_usd")
                if isinstance(valuation_latest, dict)
                else None
            ),
        },
        "ip_grant_win": {
            "manifest_present": bool(ip_manifest_latest),
            "event_id": ip_manifest_latest.get("event_id") if isinstance(ip_manifest_latest, dict) else None,
            "entry_sha256": ip_manifest_latest.get("entry_sha256") if isinstance(ip_manifest_latest, dict) else None,
            "explainer_generated_utc": (
                explainer_quant_latest.get("generated_utc")
                if isinstance(explainer_quant_latest, dict)
                else None
            ),
        },
        "public_truth": {
            "status": public_truth_latest.get("status") if isinstance(public_truth_latest, dict) else None,
            "latest_generated_utc": public_truth_latest.get("generated_utc") if isinstance(public_truth_latest, dict) else None,
            "chain_entry_sha256": (
                (public_truth_latest.get("chain", {}) or {}).get("entry_sha256")
                if isinstance(public_truth_latest, dict)
                else None
            ),
            "manifest_generated_utc": public_truth_manifest.get("generated_utc") if isinstance(public_truth_manifest, dict) else None,
        },
        "application_context": {
            "status": app_context_latest.get("status") if isinstance(app_context_latest, dict) else None,
            "latest_generated_utc": app_context_latest.get("generated_utc") if isinstance(app_context_latest, dict) else None,
            "completeness_score_pct": (
                (app_context_latest.get("completeness", {}) or {}).get("score_pct")
                if isinstance(app_context_latest, dict)
                else None
            ),
            "missing_required_count": (
                len((app_context_latest.get("completeness", {}) or {}).get("missing_required_fields") or [])
                if isinstance(app_context_latest, dict)
                else None
            ),
            "manifest_status": app_context_manifest.get("status") if isinstance(app_context_manifest, dict) else None,
        },
    }
    _write_json(OUT / "tracker.json", payload)
    return payload


@router.get("/ranked")
def get_ranked(limit: int = 50) -> dict:
    payload = _read_json(OUT / "ranked.json")
    if not payload:
        return _not_ready(
            error="no harvest payload yet",
            hint="POST /api/opportunities/harvest",
            code="harvest_not_ready",
        )
    max_rows = _clamp_limit(limit, low=1, high=1000)
    recs = payload.get("records", [])[:max_rows]
    return {
        "generated_utc": payload.get("generated_utc"),
        "total_actionable": payload.get("total_actionable"),
        "records": recs,
    }


@router.get("/queue")
def get_queue() -> dict:
    p = OUT / "queue.jsonl"
    if not p.exists():
        return {"count": 0, "queue": []}
    items: list[dict[str, Any]] = []
    malformed = 0
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except Exception:
            malformed += 1
            continue
        if isinstance(row, dict):
            items.append(row)
        else:
            malformed += 1

    payload: dict[str, Any] = {"count": len(items), "queue": items}
    if malformed:
        payload["dropped_malformed_lines"] = malformed
    return payload


class HarvestArgs(BaseModel):
    min_score: float = 0.30


class FillArgs(BaseModel):
    min_score: float = 0.40
    limit: int = 25


class CrowdfundingCallArgs(BaseModel):
    top: int = 8
    no_network: bool = False


class AutopilotArgs(BaseModel):
    harvest_min_score: float = 0.30
    fill_min_score: float = 0.40
    fill_limit: int = 25
    context_strict: bool = True
    build_funding_queue: bool = True
    include_contract_loan_pack: bool = True
    funding_top: int = 12
    funding_channels: str = "grant,key-source,contract,loan,crowdfund"
    include_crowdfunding_call: bool = True
    crowdfunding_top: int = 8
    include_sector_evidence_push: bool = False
    sector_push_nodered: bool = True
    sector_nodered_base: str = "http://127.0.0.1:8787"
    include_outreach: bool = True
    outreach_limit: int = 25
    no_network: bool = False


class OutreachArgs(BaseModel):
    limit: int = 25


class LinkedInOptimizeArgs(BaseModel):
    build_pdf: bool = True
    publish_summary_post: bool = False
    dry_run_post: bool = True
    max_packages: int = 28


class SocialOptimizeArgs(BaseModel):
    max_platforms: int = 8
    publish_mode: str = "dry_run"


class JobsFactoryArgs(BaseModel):
    min_score: float = 0.38
    limit: int = 20
    job: str = ""


class EmailFinderArgs(BaseModel):
    min_score: float = 0.90
    max_per_cycle: int = 80
    once: bool = True


class EmailDispatchArgs(BaseModel):
    min_fit_score: float = 0.42
    limit: int = 20
    once: bool = True
    dry_run: bool = True


class EmailResponseWatcherArgs(BaseModel):
    max_per_cycle: int = 120
    once: bool = True


class AutopilotV2Args(BaseModel):
    harvest_min_score: float = 0.30
    fill_min_score: float = 0.40
    fill_limit: int = 25
    context_strict: bool = True
    include_nobel_assets: bool = True
    include_skip_pack: bool = True
    include_grant_hunter: bool = True
    grant_hunter_rows: int = 180
    grant_hunter_top: int = 8
    include_alpha_edge_lock_engine: bool = True
    alpha_edge_sim_runs: int = 5000
    include_blueprint_vault: bool = True
    include_grant_submit_fit_pack: bool = True
    grant_submit_fit_limit: int = 120
    include_investor_mission_pack: bool = True
    mission_pack_top_sectors: int = 10
    include_site_reach_mission: bool = True
    site_reach_days: int = 30
    site_reach_allow_live_push: bool = False
    build_funding_queue: bool = True
    include_contract_loan_pack: bool = True
    funding_top: int = 12
    funding_channels: str = "grant,key-source,contract,loan,crowdfund"
    include_crowdfunding_call: bool = True
    crowdfunding_top: int = 8
    include_sector_evidence_push: bool = True
    sector_push_nodered: bool = True
    sector_nodered_base: str = "http://127.0.0.1:8787"
    include_outreach: bool = True
    outreach_limit: int = 25
    include_linkedin: bool = True
    linkedin_build_pdf: bool = True
    linkedin_publish_summary_post: bool = False
    linkedin_dry_run_post: bool = True
    include_social_profiles: bool = True
    social_max_platforms: int = 8
    social_publish_mode: str = "dry_run"
    include_email_finder: bool = True
    email_min_score: float = 0.90
    email_max_per_cycle: int = 80
    include_email_dispatch: bool = True
    email_dispatch_min_fit_score: float = 0.42
    email_dispatch_limit: int = 20
    email_dispatch_dry_run: bool = True
    include_email_response_watcher: bool = True
    email_response_max_per_cycle: int = 120
    include_jobs: bool = True
    jobs_min_score: float = 0.38
    jobs_limit: int = 20
    include_ip_lock: bool = True
    include_booth_design: bool = True
    include_booth_explainer: bool = True
    include_truth_snapshot: bool = True
    truth_strict: bool = False
    no_network: bool = False


class ApprovalPatch(BaseModel):
    state: str = Field(description="draft|approved|submitted|granted|withdrawn")
    notes: str = ""
    external_tracking_id: str | None = None
    submitted_by: str | None = None
    award_id: str | None = None
    awarded_amount_usd: float | None = None


def _run(script: str, args: list[str], timeout: int = 900) -> dict:
    try:
        proc = subprocess.run(
            [PY, str(ROOT / "code" / script), *args],
            capture_output=True, text=True, timeout=timeout,
        )
        return {
            "rc": proc.returncode,
            "stdout_tail": (proc.stdout or "").splitlines()[-15:],
            "stderr_tail": (proc.stderr or "").splitlines()[-5:],
        }
    except subprocess.TimeoutExpired:
        return {"rc": -1, "error": "timeout"}


def _run_linkedin_optimize(args: LinkedInOptimizeArgs) -> dict:
    run_args = ["--max-packages", str(args.max_packages)]
    if not args.build_pdf:
        run_args.append("--no-pdf")
    if args.publish_summary_post:
        run_args.append("--publish-linkedin-summary")
        if args.dry_run_post:
            run_args.append("--dry-run-post")
    return _run("lumalinkedin_resume_engine_v1.py", run_args, timeout=1200)


def _run_social_optimize(args: SocialOptimizeArgs) -> dict:
    run_args = ["--max-platforms", str(max(1, int(args.max_platforms)))]
    publish_mode = str(args.publish_mode or "dry_run").strip().lower()
    if publish_mode not in {"none", "dry_run"}:
        publish_mode = "dry_run"
    run_args.extend(["--publish-mode", publish_mode])
    return _run("social_platform_profile_engine_v1.py", run_args, timeout=1200)


def _run_jobs_factory(args: JobsFactoryArgs) -> dict:
    run_args = ["--min-score", str(args.min_score), "--limit", str(args.limit)]
    if args.job:
        run_args.extend(["--job", args.job])
    return _run("job_application_factory.py", run_args, timeout=1200)


def _run_email_finder(args: EmailFinderArgs) -> dict:
    run_args = ["--min-score", str(args.min_score), "--max-per-cycle", str(args.max_per_cycle)]
    if args.once:
        run_args.append("--once")
    return _run("email_opportunity_finder.py", run_args, timeout=1200)


def _run_email_dispatch(args: EmailDispatchArgs) -> dict:
    run_args = ["--min-fit-score", str(args.min_fit_score), "--limit", str(args.limit)]
    if args.once:
        run_args.append("--once")
    if args.dry_run:
        run_args.append("--dry-run")
    return _run("email_resume_dispatcher.py", run_args, timeout=1200)


def _run_email_response_watcher(args: EmailResponseWatcherArgs) -> dict:
    run_args = ["--max-per-cycle", str(args.max_per_cycle)]
    if args.once:
        run_args.append("--once")
    return _run("email_response_watcher.py", run_args, timeout=1200)


def _run_context_resolver(strict: bool = False) -> dict:
    run_args: list[str] = []
    if strict:
        run_args.append("--strict")
    return _run("application_context_resolver.py", run_args, timeout=900)


@router.post("/harvest")
def trigger_harvest(args: HarvestArgs) -> dict:
    return _run("opportunity_harvester.py", ["--min-score", str(args.min_score)])


@router.post("/fill")
def trigger_fill(args: FillArgs) -> dict:
    return _run("opportunity_filler.py",
                ["--min-score", str(args.min_score), "--limit", str(args.limit)])


@router.post("/autopilot")
def run_autopilot(args: AutopilotArgs) -> dict:
    context_refresh = _run_context_resolver(strict=args.context_strict)
    harvest = _run("opportunity_harvester.py", ["--min-score", str(args.harvest_min_score)])
    fill = _run(
        "opportunity_filler.py",
        ["--min-score", str(args.fill_min_score), "--limit", str(args.fill_limit)],
    )

    funding = None
    if args.build_funding_queue:
        funding_args = [
            "build",
            "--top",
            str(args.funding_top),
            "--channels",
            args.funding_channels,
        ]
        if args.no_network:
            funding_args.append("--no-network")
        funding = _run("funding_autopilot.py", funding_args)

    crowdfunding_call = None
    if args.include_crowdfunding_call:
        crowdfunding_args = [
            "build",
            "--top",
            str(args.crowdfunding_top),
            "--channels",
            "crowdfund",
        ]
        if args.no_network:
            crowdfunding_args.append("--no-network")
        crowdfunding_call = _run("funding_autopilot.py", crowdfunding_args)

    sector_evidence_push = None
    if args.include_sector_evidence_push:
        sector_args: list[str] = ["--run-investor-sweep"]
        if args.sector_push_nodered:
            sector_args.extend(["--push-nodered", "--nodered-base", args.sector_nodered_base])
        sector_evidence_push = _run("ops/run_sector_energy_evidence_pipeline.py", sector_args, timeout=5400)

    contract_loan_pack = None
    if args.include_contract_loan_pack:
        contract_loan_pack = _run("ops/GENERATE_CONTRACT_LOAN_AND_INVESTOR_PACK.py", [])

    outreach = None
    if args.include_outreach:
        outreach = _generate_outreach_pack(limit=args.outreach_limit)

    tracker = _build_tracker()
    ranked = _read_json(OUT / "ranked.json") or {}
    ranked_count = int(ranked.get("total_actionable", 0)) if isinstance(ranked, dict) else 0

    payload = {
        "generated_utc": _now_utc_iso(),
        "application_context": context_refresh,
        "harvest": harvest,
        "fill": fill,
        "funding": funding,
        "crowdfunding_call": crowdfunding_call,
        "sector_evidence_push": sector_evidence_push,
        "contract_loan_pack": contract_loan_pack,
        "outreach": outreach,
        "ranked_actionable": ranked_count,
        "tracker": tracker,
    }

    summary_path = OPS_OUT / f"opportunity_autopilot_{_utc_stamp()}.json"
    _write_json(summary_path, payload)
    payload["artifact"] = str(summary_path)
    return payload


@router.post("/autopilot-v2")
def run_autopilot_v2(args: AutopilotV2Args) -> dict:
    context_refresh = _run_context_resolver(strict=args.context_strict)

    nobel_assets = None
    if args.include_nobel_assets:
        nobel_assets = _run("execution/build_nobel_tier_assets.py", [], timeout=1800)

    skip_pack = None
    if args.include_skip_pack:
        skip_pack = _run("ops/build_skips_grant_autofill_pack.py", [])

    harvest = _run("opportunity_harvester.py", ["--min-score", str(args.harvest_min_score)])
    fill = _run(
        "opportunity_filler.py",
        ["--min-score", str(args.fill_min_score), "--limit", str(args.fill_limit)],
    )

    grant_hunter = None
    if args.include_grant_hunter:
        grant_hunter = _run(
            "grant_hunter_v2.py",
            ["run-all", "--rows", str(args.grant_hunter_rows), "--top", str(args.grant_hunter_top)],
            timeout=1800,
        )

    alpha_edge_lock_build = None
    if args.include_alpha_edge_lock_engine:
        alpha_edge_lock_build = _run(
            "ops/BUILD_ALPHA_EDGE_LOCK_ENGINE.py",
            ["--sim-runs", str(args.alpha_edge_sim_runs), "--top-n", "12"],
            timeout=1800,
        )

    blueprint_vault = None
    if args.include_blueprint_vault:
        blueprint_vault = _run(
            "ops/BUILD_GOV_BLUEPRINT_VAULT.py",
            ["--exposure-level", "highest_level"],
            timeout=1800,
        )

    grant_submit_fit_pack = None
    if args.include_grant_submit_fit_pack:
        grant_submit_fit_pack = _run(
            "ops/BUILD_GRANT_SUBMIT_FIT_PACK.py",
            ["--state", "APPROVED", "--limit", str(args.grant_submit_fit_limit)],
            timeout=1800,
        )

    investor_mission_pack = None
    if args.include_investor_mission_pack:
        investor_mission_pack = _run(
            "ops/BUILD_INVESTOR_MISSION_CONTROL_PACK.py",
            ["--top-sectors", str(args.mission_pack_top_sectors)],
            timeout=1800,
        )

    site_reach_mission = None
    if args.include_site_reach_mission:
        site_reach_args = [
            "--days",
            str(max(1, int(args.site_reach_days))),
        ]
        if args.site_reach_allow_live_push:
            site_reach_args.append("--allow-live-push")
        site_reach_mission = _run(
            "ops/BUILD_SITE_REACH_AND_DOMAIN_MISSION_PUSH.py",
            site_reach_args,
            timeout=1800,
        )

    funding = None
    if args.build_funding_queue:
        funding_args = [
            "build",
            "--top",
            str(args.funding_top),
            "--channels",
            args.funding_channels,
        ]
        if args.no_network:
            funding_args.append("--no-network")
        funding = _run("funding_autopilot.py", funding_args)

    crowdfunding_call = None
    if args.include_crowdfunding_call:
        crowdfunding_args = [
            "build",
            "--top",
            str(args.crowdfunding_top),
            "--channels",
            "crowdfund",
        ]
        if args.no_network:
            crowdfunding_args.append("--no-network")
        crowdfunding_call = _run("funding_autopilot.py", crowdfunding_args)

    sector_evidence_push = None
    if args.include_sector_evidence_push:
        sector_args: list[str] = ["--run-investor-sweep"]
        if args.sector_push_nodered:
            sector_args.extend(["--push-nodered", "--nodered-base", args.sector_nodered_base])
        sector_evidence_push = _run("ops/run_sector_energy_evidence_pipeline.py", sector_args, timeout=5400)

    contract_loan_pack = None
    if args.include_contract_loan_pack:
        contract_loan_pack = _run("ops/GENERATE_CONTRACT_LOAN_AND_INVESTOR_PACK.py", [])

    outreach = None
    if args.include_outreach:
        outreach = _generate_outreach_pack(limit=args.outreach_limit)

    linkedin = None
    if args.include_linkedin:
        linkedin = _run_linkedin_optimize(
            LinkedInOptimizeArgs(
                build_pdf=args.linkedin_build_pdf,
                publish_summary_post=args.linkedin_publish_summary_post,
                dry_run_post=args.linkedin_dry_run_post,
            )
        )

    social_profiles = None
    if args.include_social_profiles:
        social_profiles = _run_social_optimize(
            SocialOptimizeArgs(
                max_platforms=args.social_max_platforms,
                publish_mode=args.social_publish_mode,
            )
        )

    email_finder = None
    if args.include_email_finder:
        email_finder = _run_email_finder(
            EmailFinderArgs(
                min_score=args.email_min_score,
                max_per_cycle=args.email_max_per_cycle,
                once=True,
            )
        )

    email_dispatch = None
    if args.include_email_dispatch:
        email_dispatch = _run_email_dispatch(
            EmailDispatchArgs(
                min_fit_score=args.email_dispatch_min_fit_score,
                limit=args.email_dispatch_limit,
                once=True,
                dry_run=args.email_dispatch_dry_run,
            )
        )

    email_response_watcher = None
    if args.include_email_response_watcher:
        email_response_watcher = _run_email_response_watcher(
            EmailResponseWatcherArgs(
                max_per_cycle=args.email_response_max_per_cycle,
                once=True,
            )
        )

    jobs = None
    if args.include_jobs:
        jobs = _run_jobs_factory(
            JobsFactoryArgs(
                min_score=args.jobs_min_score,
                limit=args.jobs_limit,
            )
        )

    ip_lock = None
    if args.include_ip_lock:
        ip_lock = _run("ops/LOCK_AUTONOMOUS_GRANT_WIN.py", [])

    booth_design = None
    if args.include_booth_design:
        booth_design = _run("ops/build_booth_design_pack.py", [])

    booth_explainer = None
    if args.include_booth_explainer:
        booth_explainer = _run("build_booth_explainer_brief.py", [])

    truth_snapshot = None
    if args.include_truth_snapshot:
        truth_args: list[str] = []
        if args.truth_strict:
            truth_args.append("--strict")
        truth_snapshot = _run("ops/ENFORCE_PRODUCTION_TRUTH_RULE.py", truth_args)

    tracker_payload = _build_tracker()
    ranked = _read_json(OUT / "ranked.json") or {}
    ranked_count = int(ranked.get("total_actionable", 0)) if isinstance(ranked, dict) else 0

    payload = {
        "generated_utc": _now_utc_iso(),
        "application_context": context_refresh,
        "nobel_assets": nobel_assets,
        "skip_pack": skip_pack,
        "harvest": harvest,
        "fill": fill,
        "grant_hunter": grant_hunter,
        "alpha_edge_lock_build": alpha_edge_lock_build,
        "blueprint_vault": blueprint_vault,
        "grant_submit_fit_pack": grant_submit_fit_pack,
        "investor_mission_pack": investor_mission_pack,
        "site_reach_mission": site_reach_mission,
        "funding": funding,
        "crowdfunding_call": crowdfunding_call,
        "sector_evidence_push": sector_evidence_push,
        "contract_loan_pack": contract_loan_pack,
        "outreach": outreach,
        "linkedin": linkedin,
        "social_profiles": social_profiles,
        "email_finder": email_finder,
        "email_dispatch": email_dispatch,
        "email_response_watcher": email_response_watcher,
        "jobs": jobs,
        "ip_lock": ip_lock,
        "booth_design": booth_design,
        "booth_explainer": booth_explainer,
        "truth_snapshot": truth_snapshot,
        "ranked_actionable": ranked_count,
        "tracker": tracker_payload,
    }

    summary_path = OPS_OUT / f"opportunity_autopilot_v2_{_utc_stamp()}.json"
    _write_json(summary_path, payload)
    payload["artifact"] = str(summary_path)
    return payload


@router.post("/linkedin/optimize")
def optimize_linkedin(args: LinkedInOptimizeArgs) -> dict:
    run = _run_linkedin_optimize(args)
    latest = _latest_linkedin_payload()
    resume = _read_json(RESUME_LATEST) or {}
    return {
        "generated_utc": _now_utc_iso(),
        "run": run,
        "linkedin_latest": latest,
        "resume_latest": {
            "generated_utc": resume.get("generated_utc") if isinstance(resume, dict) else None,
            "artifacts": resume.get("artifacts") if isinstance(resume, dict) else None,
        },
    }


@router.get("/linkedin/latest")
def linkedin_latest() -> dict:
    payload = _latest_linkedin_payload()
    if not payload:
        return _not_ready(
            error="no linkedin optimization payload yet",
            hint="POST /api/opportunities/linkedin/optimize",
            code="linkedin_not_ready",
        )
    return payload


@router.post("/social/optimize")
def optimize_social(args: SocialOptimizeArgs) -> dict:
    run = _run_social_optimize(args)
    latest = _latest_social_payload()
    build = _read_json(SOCIAL_BUILD_LATEST) or {}
    return {
        "generated_utc": _now_utc_iso(),
        "run": run,
        "social_latest": latest,
        "build_latest": build,
    }


@router.get("/social/latest")
def social_latest() -> dict:
    payload = _latest_social_payload()
    if not payload:
        return _not_ready(
            error="no social optimization payload yet",
            hint="POST /api/opportunities/social/optimize",
            code="social_not_ready",
        )
    return payload


@router.post("/jobs/factory")
def run_jobs_factory(args: JobsFactoryArgs) -> dict:
    run = _run_jobs_factory(args)
    queue = _read_json(JOBS_QUEUE) or {}
    return {
        "generated_utc": _now_utc_iso(),
        "run": run,
        "jobs_queue": queue,
    }


@router.get("/jobs/queue")
def jobs_queue() -> dict:
    payload = _read_json(JOBS_QUEUE)
    if not payload:
        return _not_ready(
            error="no jobs queue yet",
            hint="POST /api/opportunities/jobs/factory",
            code="jobs_not_ready",
        )
    return payload


@router.post("/email/finder/run")
def run_email_finder(args: EmailFinderArgs) -> dict:
    run = _run_email_finder(args)
    latest = _read_json(EMAIL_LATEST) or {}
    queue = _read_json(EMAIL_QUEUE) or []
    return {
        "generated_utc": _now_utc_iso(),
        "run": run,
        "email_latest": latest,
        "email_queue_count": len(queue) if isinstance(queue, list) else 0,
    }


@router.post("/crowdfunding/call")
def crowdfunding_call(args: CrowdfundingCallArgs) -> dict:
    run_args = ["build", "--top", str(args.top), "--channels", "crowdfund"]
    if args.no_network:
        run_args.append("--no-network")
    run = _run("funding_autopilot.py", run_args, timeout=1800)
    queue = _read_json(FUNDING_QUEUE)
    rows = [
        row
        for row in (queue if isinstance(queue, list) else [])
        if isinstance(row, dict) and str(row.get("channel") or "").lower() == "crowdfund"
    ]
    state_counts: dict[str, int] = {}
    for row in rows:
        state = str(row.get("approval_state") or "UNKNOWN").upper()
        state_counts[state] = state_counts.get(state, 0) + 1
    return {
        "generated_utc": _now_utc_iso(),
        "run": run,
        "queue_count": len(rows),
        "approval_state_counts": state_counts,
        "queue": rows[:100],
    }


@router.get("/crowdfunding/queue")
def crowdfunding_queue(limit: int = 100) -> dict:
    payload = _read_json(FUNDING_QUEUE)
    rows = [
        row
        for row in (payload if isinstance(payload, list) else [])
        if isinstance(row, dict) and str(row.get("channel") or "").lower() == "crowdfund"
    ]
    max_rows = _clamp_limit(limit, low=1, high=500)
    return {
        "generated_utc": _now_utc_iso(),
        "count": len(rows),
        "queue": rows[:max_rows],
    }


@router.get("/crowdfunding/highlights")
def crowdfunding_highlights(limit: int = 8) -> dict:
    max_rows = _clamp_limit(limit, low=1, high=50)
    funding_payload = _read_json(FUNDING_QUEUE)
    campaign_payload = _read_json(CROWDFUNDING_CAMPAIGN_QUEUE)

    funding_rows = [
        row
        for row in (funding_payload if isinstance(funding_payload, list) else [])
        if isinstance(row, dict) and str(row.get("channel") or "").lower() == "crowdfund"
    ]
    funding_rows.sort(key=lambda row: float(row.get("priority_score") or 0.0), reverse=True)

    campaign_rows = [row for row in (campaign_payload if isinstance(campaign_payload, list) else []) if isinstance(row, dict)]
    campaign_rows.sort(
        key=lambda row: float(((row.get("platform") or {}).get("fit_score") or 0.0)),
        reverse=True,
    )

    return {
        "generated_utc": _now_utc_iso(),
        "funding_queue_count": len(funding_rows),
        "campaign_queue_count": len(campaign_rows),
        "pending_human_approval_count": sum(
            1
            for row in funding_rows
            if str(row.get("approval_state") or "").upper() == "PENDING_HUMAN_APPROVAL"
        ),
        "top_funding_opportunities": funding_rows[:max_rows],
        "top_campaign_blueprints": campaign_rows[:max_rows],
    }


@router.get("/email/finder/latest")
def email_finder_latest() -> dict:
    payload = _read_json(EMAIL_LATEST)
    if not payload:
        return _not_ready(
            error="no email opportunity payload yet",
            hint="POST /api/opportunities/email/finder/run",
            code="email_finder_not_ready",
        )
    return payload


@router.get("/email/finder/queue")
def email_finder_queue(limit: int = 250) -> dict:
    payload = _read_json(EMAIL_QUEUE)
    if not payload:
        return {"queue": [], "count": 0}
    max_rows = _clamp_limit(limit, low=1, high=1000)
    rows = payload if isinstance(payload, list) else []
    return {"count": len(rows), "queue": rows[:max_rows]}


@router.get("/email/finder/manifest/latest")
def email_finder_manifest_latest() -> dict:
    payload = _read_json(EMAIL_MANIFEST_LATEST)
    if not payload:
        return _not_ready(
            error="no email opportunity manifest yet",
            hint="POST /api/opportunities/email/finder/run",
            code="email_finder_manifest_not_ready",
        )
    return payload


@router.post("/email/dispatch/run")
def run_email_dispatch(args: EmailDispatchArgs) -> dict:
    run = _run_email_dispatch(args)
    latest = _read_json(EMAIL_DISPATCH_LATEST) or {}
    queue = _read_json(EMAIL_DISPATCH_QUEUE) or {}
    return {
        "generated_utc": _now_utc_iso(),
        "run": run,
        "dispatch_latest": latest,
        "dispatch_queue_count": (
            queue.get("count")
            if isinstance(queue, dict)
            else len(queue)
            if isinstance(queue, list)
            else 0
        ),
    }


@router.get("/email/dispatch/latest")
def email_dispatch_latest() -> dict:
    payload = _read_json(EMAIL_DISPATCH_LATEST)
    if not payload:
        return _not_ready(
            error="no email dispatch payload yet",
            hint="POST /api/opportunities/email/dispatch/run",
            code="email_dispatch_not_ready",
        )
    return payload


@router.get("/email/dispatch/queue")
def email_dispatch_queue(limit: int = 250) -> dict:
    payload = _read_json(EMAIL_DISPATCH_QUEUE)
    if not payload:
        return {"queue": [], "count": 0}
    max_rows = _clamp_limit(limit, low=1, high=1000)
    if isinstance(payload, dict):
        rows = payload.get("items", []) if isinstance(payload.get("items"), list) else []
        return {"count": len(rows), "queue": rows[:max_rows]}
    rows = payload if isinstance(payload, list) else []
    return {"count": len(rows), "queue": rows[:max_rows]}


@router.get("/email/dispatch/manifest/latest")
def email_dispatch_manifest_latest() -> dict:
    payload = _read_json(EMAIL_DISPATCH_MANIFEST_LATEST)
    if not payload:
        return _not_ready(
            error="no email dispatch manifest yet",
            hint="POST /api/opportunities/email/dispatch/run",
            code="email_dispatch_manifest_not_ready",
        )
    return payload


@router.post("/email/response/run")
def run_email_response_watcher(args: EmailResponseWatcherArgs) -> dict:
    run = _run_email_response_watcher(args)
    latest = _read_json(EMAIL_RESPONSE_LATEST) or {}
    queue = _read_json(EMAIL_RESPONSE_QUEUE) or []
    return {
        "generated_utc": _now_utc_iso(),
        "run": run,
        "response_latest": latest,
        "response_queue_count": len(queue) if isinstance(queue, list) else 0,
    }


@router.get("/email/response/latest")
def email_response_latest() -> dict:
    payload = _read_json(EMAIL_RESPONSE_LATEST)
    if not payload:
        return _not_ready(
            error="no response watcher payload yet",
            hint="POST /api/opportunities/email/response/run",
            code="email_response_not_ready",
        )
    return payload


@router.get("/email/response/queue")
def email_response_queue(limit: int = 250) -> dict:
    payload = _read_json(EMAIL_RESPONSE_QUEUE)
    if not payload:
        return {"queue": [], "count": 0}
    max_rows = _clamp_limit(limit, low=1, high=1000)
    rows = payload if isinstance(payload, list) else []
    return {"count": len(rows), "queue": rows[:max_rows]}


@router.get("/email/response/manifest/latest")
def email_response_manifest_latest() -> dict:
    payload = _read_json(EMAIL_RESPONSE_MANIFEST_LATEST)
    if not payload:
        return _not_ready(
            error="no response watcher manifest yet",
            hint="POST /api/opportunities/email/response/run",
            code="email_response_manifest_not_ready",
        )
    return payload


@router.post("/context/refresh")
def refresh_application_context(strict: bool = True) -> dict:
    run = _run_context_resolver(strict=strict)
    latest = _read_json(APP_CONTEXT_LATEST) or {}
    manifest = _read_json(APP_CONTEXT_MANIFEST_LATEST) or {}
    return {
        "generated_utc": _now_utc_iso(),
        "run": run,
        "application_context_latest": latest,
        "application_context_manifest": manifest,
    }


@router.get("/context/latest")
def application_context_latest() -> dict:
    payload = _read_json(APP_CONTEXT_LATEST)
    if not payload:
        return _not_ready(
            error="no application context payload yet",
            hint="POST /api/opportunities/context/refresh",
            code="application_context_not_ready",
        )
    return payload


@router.get("/investor/mission-pack/latest")
def investor_mission_pack_latest() -> dict:
    payload = _read_json(INVESTOR_MISSION_CONTROL_PACK_LATEST)
    if not payload:
        return _not_ready(
            error="no investor mission-control pack yet",
            hint="Run RUN_INVESTOR_PACKET_REFRESH or POST /api/opportunities/autopilot-v2",
            code="investor_mission_pack_not_ready",
        )
    return payload


@router.get("/investor/heartbeat/latest")
def investor_heartbeat_latest() -> dict:
    return {
        "generated_utc": _now_utc_iso(),
        "mission_control_pack": _heartbeat_snapshot(INVESTOR_MISSION_CONTROL_HEARTBEAT_LATEST, stale_after_sec=3600.0),
        "alpha_edge_lock": _heartbeat_snapshot(ALPHA_EDGE_LOCK_ENGINE_HEARTBEAT_LATEST, stale_after_sec=3600.0),
        "investor_packet_refresh": _heartbeat_snapshot(INVESTOR_PACKET_REFRESH_HEARTBEAT_LATEST, stale_after_sec=3600.0),
    }


@router.get("/blueprints/latest")
def blueprints_latest() -> dict:
    payload = _read_json(GOV_BLUEPRINT_VAULT_LATEST)
    if not payload:
        return _not_ready(
            error="no government blueprint vault payload yet",
            hint="Run RUN_INVESTOR_PACKET_REFRESH or POST /api/opportunities/autopilot-v2",
            code="blueprints_not_ready",
        )
    return payload


@router.get("/site-reach/latest")
def site_reach_latest() -> dict:
    payload = _read_json(SITE_REACH_MISSION_LATEST)
    if not payload:
        return _not_ready(
            error="no site reach payload yet",
            hint="Run RUN_INVESTOR_PACKET_REFRESH or POST /api/opportunities/autopilot-v2",
            code="site_reach_not_ready",
        )
    return payload


@router.get("/grants/live-fill/latest")
def grants_live_fill_latest() -> dict:
    payload = _read_json(INVESTOR_MISSION_CONTROL_PACK_LATEST)
    if not isinstance(payload, dict):
        return _not_ready(
            error="no investor mission-control pack yet",
            hint="Run RUN_INVESTOR_PACKET_REFRESH or POST /api/opportunities/autopilot-v2",
            code="investor_mission_pack_not_ready",
        )
    live_fill = payload.get("autonomous_grant_live_fill")
    if not isinstance(live_fill, dict):
        return _not_ready(
            error="mission-control pack missing autonomous_grant_live_fill section",
            hint="Rebuild with RUN_INVESTOR_PACKET_REFRESH",
            code="grant_live_fill_missing",
        )
    return {
        "generated_utc": payload.get("generated_utc"),
        "live_fill": live_fill,
    }


@router.get("/alpha-edge/latest")
def alpha_edge_latest() -> dict:
    payload = _read_json(ALPHA_EDGE_LOCK_ENGINE_LATEST)
    if not payload:
        return _not_ready(
            error="no alpha-edge lock engine artifact yet",
            hint="Run RUN_INVESTOR_PACKET_REFRESH or POST /api/opportunities/autopilot-v2",
            code="alpha_edge_not_ready",
        )
    return payload


@router.get("/investor/pitch/latest")
def investor_pitch_latest() -> dict:
    payload = _read_json(INVESTOR_MISSION_CONTROL_PACK_LATEST)
    if not isinstance(payload, dict):
        return _not_ready(
            error="no investor mission-control pack yet",
            hint="Run RUN_INVESTOR_PACKET_REFRESH or POST /api/opportunities/autopilot-v2",
            code="investor_mission_pack_not_ready",
        )
    pitch = payload.get("three_min_nobel_pitch")
    if not isinstance(pitch, dict):
        return _not_ready(
            error="mission-control pack missing three_min_nobel_pitch section",
            hint="Rebuild with RUN_INVESTOR_PACKET_REFRESH",
            code="investor_pitch_missing",
        )
    markdown = None
    if INVESTOR_3MIN_PITCH_LATEST.exists():
        markdown = INVESTOR_3MIN_PITCH_LATEST.read_text(encoding="utf-8", errors="ignore")
    return {
        "generated_utc": payload.get("generated_utc"),
        "pitch": pitch,
        "pitch_markdown": markdown,
    }


@router.get("/valuation/latest")
def valuation_latest() -> dict:
    payload = _read_json(MASTER_VAL_LATEST)
    if not payload:
        return _not_ready(
            error="no master valuation payload yet",
            code="valuation_not_ready",
        )
    return payload


@router.get("/ip/grant-win/latest")
def ip_grant_win_latest() -> dict:
    payload = _read_json(IP_GRANT_WIN_MANIFEST_LATEST)
    if not payload:
        return _not_ready(
            error="no autonomous grant win manifest yet",
            code="ip_grant_win_not_ready",
        )
    return payload


@router.get("/explainer/quantified/latest")
def explainer_quantified_latest() -> dict:
    payload = _read_json(LUMA_EXPLAINER_QUANT_LATEST)
    if not payload:
        return _not_ready(
            error="no quantified explainer payload yet",
            code="explainer_not_ready",
        )
    return payload


@router.get("/booth/design/latest")
def booth_design_latest() -> dict:
    payload = _read_json(BOOTH_DESIGN_MANIFEST_LATEST)
    if not payload:
        return _not_ready(
            error="no booth design manifest yet",
            code="booth_design_not_ready",
        )
    return payload


@router.get("/booth/setup/latest")
def booth_setup_latest() -> dict:
    payload = _read_json(BOOTH_DESIGN_MANIFEST_LATEST)
    if not payload:
        return _not_ready(
            error="no booth setup pack yet",
            code="booth_setup_not_ready",
        )
    return {
        "generated_utc": _now_utc_iso(),
        "manifest": payload,
        "print_spec_markdown": (
            BOOTH_PRINT_SPEC_LATEST.read_text(encoding="utf-8", errors="ignore")
            if BOOTH_PRINT_SPEC_LATEST.exists()
            else None
        ),
        "setup_checklist_markdown": (
            BOOTH_SETUP_CHECKLIST_LATEST.read_text(encoding="utf-8", errors="ignore")
            if BOOTH_SETUP_CHECKLIST_LATEST.exists()
            else None
        ),
        "host_style_guide_markdown": (
            BOOTH_HOST_STYLE_GUIDE_LATEST.read_text(encoding="utf-8", errors="ignore")
            if BOOTH_HOST_STYLE_GUIDE_LATEST.exists()
            else None
        ),
    }


@router.get("/evidence/shipping/latest")
def evidence_shipping_latest() -> dict:
    payload = _latest_investor_proof_summary()
    if not payload:
        return _not_ready(
            error="no investor proof sweep summary found",
            hint="Run RUN_INVESTOR_PROOF_SWEEP or RUN_SECTOR_ENERGY_EVIDENCE_PIPELINE with investor sweep",
            code="evidence_shipping_not_ready",
        )
    node_red_unity = payload.get("node_red_unity") if isinstance(payload, dict) else {}
    artifacts = payload.get("artifacts") if isinstance(payload, dict) else {}
    return {
        "generated_utc": _now_utc_iso(),
        "summary_generated_utc": payload.get("generated_utc"),
        "summary_path": payload.get("_path"),
        "push_attempted": node_red_unity.get("attempted") if isinstance(node_red_unity, dict) else None,
        "ingest_status": node_red_unity.get("ingest") if isinstance(node_red_unity, dict) else None,
        "scene_status": node_red_unity.get("scene") if isinstance(node_red_unity, dict) else None,
        "ingest_detail": node_red_unity.get("ingest_detail") if isinstance(node_red_unity, dict) else None,
        "scene_detail": node_red_unity.get("scene_detail") if isinstance(node_red_unity, dict) else None,
        "nodered_payload_json": artifacts.get("nodered_payload_json") if isinstance(artifacts, dict) else None,
        "unity_edge_payload_json": artifacts.get("unity_edge_payload_json") if isinstance(artifacts, dict) else None,
    }


@router.get("/truth/latest")
def truth_latest() -> dict:
    payload = _read_json(PUBLIC_TRUTH_LATEST)
    if not payload:
        return _not_ready(
            error="no public truth snapshot yet",
            code="truth_snapshot_not_ready",
        )
    return payload


@router.get("/truth/manifest/latest")
def truth_manifest_latest() -> dict:
    payload = _read_json(PUBLIC_TRUTH_MANIFEST_LATEST)
    if not payload:
        return _not_ready(
            error="no public truth manifest yet",
            code="truth_manifest_not_ready",
        )
    return payload


@router.get("/tracker")
def tracker() -> dict:
    return _build_tracker()


@router.get("/awards")
def awards(limit: int = 100) -> dict:
    payload = _build_tracker()
    rows = payload.get("awards", {}).get("items", [])
    max_rows = _clamp_limit(limit, low=1, high=1000)
    return {
        "generated_utc": payload.get("generated_utc"),
        "count": payload.get("awards", {}).get("count", 0),
        "items": rows[:max_rows],
    }


@router.get("/outreach/templates")
def outreach_templates() -> dict:
    payload = _load_outreach_templates()
    payload["generated_utc"] = _now_utc_iso()
    return payload


@router.post("/outreach/generate")
def generate_outreach(args: OutreachArgs) -> dict:
    return _generate_outreach_pack(limit=args.limit)


@router.get("/package/{slug}")
def get_package(slug: str) -> dict:
    p = _package_dir_from_slug(slug)
    files = {}
    for name in ("application.json", "approval_state.json", "cover_letter.md",
                 "technical_brief.md", "SUBMIT_HOWTO.md"):
        f = p / name
        if f.exists():
            files[name] = f.read_text(encoding="utf-8")
    return {"slug": slug, "files": files}


@router.post("/{slug}/state")
def set_state(slug: str, patch: ApprovalPatch) -> dict:
    state = str(patch.state or "").strip().lower()
    if state not in {"draft", "approved", "submitted", "granted", "withdrawn"}:
        raise HTTPException(400, "state must be draft|approved|submitted|granted|withdrawn")

    p = _package_dir_from_slug(slug) / "approval_state.json"
    if not p.exists():
        raise HTTPException(404, f"package {slug} missing approval_state.json")

    cur = _read_json(p)
    if not isinstance(cur, dict):
        raise HTTPException(500, f"package {slug} has malformed approval_state.json")
    cur["state"] = state
    cur["notes"] = patch.notes or cur.get("notes", "")
    cur["updated_utc"] = _now_utc_iso()

    if patch.external_tracking_id is not None:
        cur["external_tracking_id"] = patch.external_tracking_id
    if patch.submitted_by is not None:
        cur["submitted_by"] = patch.submitted_by
    if patch.award_id is not None:
        cur["award_id"] = patch.award_id
    if patch.awarded_amount_usd is not None:
        cur["awarded_amount_usd"] = float(patch.awarded_amount_usd)

    if state == "submitted" and not cur.get("submitted_utc"):
        cur["submitted_utc"] = _now_utc_iso()
    if state == "granted":
        cur["granted_utc"] = _now_utc_iso()

    _write_json(p, cur)
    tracker_payload = _build_tracker()
    return {
        "ok": True,
        "slug": slug,
        "state": state,
        "approval_state": cur,
        "awards_count": tracker_payload.get("awards", {}).get("count", 0),
    }


@router.post("/{slug}/approve")
def approve(slug: str, patch: ApprovalPatch) -> dict:
    """Compatibility alias. Prefer POST /state."""
    return set_state(slug, patch)
