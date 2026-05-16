"""FastAPI router for opportunity harvest, filling, outreach, and tracking.

Core endpoints:
    GET  /api/opportunities/ranked             -> latest ranked.json
    GET  /api/opportunities/queue              -> queue.jsonl as array
    POST /api/opportunities/harvest            -> trigger harvester
    POST /api/opportunities/fill               -> trigger filler bot
    POST /api/opportunities/autopilot          -> harvest + fill + funding + outreach
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
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "opportunities"
OUTREACH_OUT = OUT / "outreach"
OPS_OUT = ROOT / "out" / "ops"
GRANTS_QUEUE = ROOT / "out" / "grants" / "_queue" / "index.json"
FUNDING_QUEUE = ROOT / "out" / "funding" / "funding_approval_queue.json"
WHITEHOLE_ROOT = Path(os.getenv("WHITEHOLE_ROOT", r"C:\WhiteHole"))

PY = sys.executable
OUT.mkdir(parents=True, exist_ok=True)
OUTREACH_OUT.mkdir(parents=True, exist_ok=True)
OPS_OUT.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


def _read_json(p: Path) -> Any:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


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
    funding_counts: dict[str, int] = {}
    if isinstance(funding_q, list):
        for item in funding_q:
            key = str(item.get("approval_state") or "UNKNOWN").upper()
            funding_counts[key] = funding_counts.get(key, 0) + 1

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
        "funding_queue": {
            "n_total": len(funding_q) if isinstance(funding_q, list) else 0,
            "approval_state_counts": funding_counts,
        },
    }
    _write_json(OUT / "tracker.json", payload)
    return payload


@router.get("/ranked")
def get_ranked(limit: int = 50) -> dict:
    payload = _read_json(OUT / "ranked.json")
    if not payload:
        return {"error": "no harvest yet -- POST /api/opportunities/harvest"}
    recs = payload.get("records", [])[:limit]
    return {
        "generated_utc": payload.get("generated_utc"),
        "total_actionable": payload.get("total_actionable"),
        "records": recs,
    }


@router.get("/queue")
def get_queue() -> dict:
    p = OUT / "queue.jsonl"
    if not p.exists():
        return {"queue": []}
    items = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"count": len(items), "queue": items}


class HarvestArgs(BaseModel):
    min_score: float = 0.30


class FillArgs(BaseModel):
    min_score: float = 0.40
    limit: int = 25


class AutopilotArgs(BaseModel):
    harvest_min_score: float = 0.30
    fill_min_score: float = 0.40
    fill_limit: int = 25
    build_funding_queue: bool = True
    funding_top: int = 12
    funding_channels: str = "grant,key-source,contract,loan"
    include_outreach: bool = True
    outreach_limit: int = 25
    no_network: bool = False


class OutreachArgs(BaseModel):
    limit: int = 25


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


@router.post("/harvest")
def trigger_harvest(args: HarvestArgs) -> dict:
    return _run("opportunity_harvester.py", ["--min-score", str(args.min_score)])


@router.post("/fill")
def trigger_fill(args: FillArgs) -> dict:
    return _run("opportunity_filler.py",
                ["--min-score", str(args.min_score), "--limit", str(args.limit)])


@router.post("/autopilot")
def run_autopilot(args: AutopilotArgs) -> dict:
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

    outreach = None
    if args.include_outreach:
        outreach = _generate_outreach_pack(limit=args.outreach_limit)

    tracker = _build_tracker()
    ranked = _read_json(OUT / "ranked.json") or {}
    ranked_count = int(ranked.get("total_actionable", 0)) if isinstance(ranked, dict) else 0

    payload = {
        "generated_utc": _now_utc_iso(),
        "harvest": harvest,
        "fill": fill,
        "funding": funding,
        "outreach": outreach,
        "ranked_actionable": ranked_count,
        "tracker": tracker,
    }

    summary_path = OPS_OUT / f"opportunity_autopilot_{_utc_stamp()}.json"
    _write_json(summary_path, payload)
    payload["artifact"] = str(summary_path)
    return payload


@router.get("/tracker")
def tracker() -> dict:
    return _build_tracker()


@router.get("/awards")
def awards(limit: int = 100) -> dict:
    payload = _build_tracker()
    rows = payload.get("awards", {}).get("items", [])
    return {
        "generated_utc": payload.get("generated_utc"),
        "count": payload.get("awards", {}).get("count", 0),
        "items": rows[:limit],
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

    cur = json.loads(p.read_text(encoding="utf-8"))
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
