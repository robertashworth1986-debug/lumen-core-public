"""
grants_api.py
================================
FastAPI router for the grant application factory.

Endpoints (all under /api/grants):
    GET  /api/grants/                       queue summary
    GET  /api/grants/catalog                full grant catalog
    GET  /api/grants/profile                company + PI profile
    GET  /api/grants/{grant_id}             latest draft package
    GET  /api/grants/{grant_id}/markdown    application.md as text
    GET  /api/grants/{grant_id}/submission  latest submission packet + howto
    POST /api/grants/regenerate             re-run factory (all or one)
    POST /api/grants/draft                  regenerate + prepare submission kit
    POST /api/grants/{grant_id}/approve     flip draft -> approved
    POST /api/grants/{grant_id}/submitted   record external submission

Mount in luma_experience_gateway.py:
    from grants_api import router as _grants_router
    app.include_router(_grants_router)
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GRANTS = ROOT / "out" / "grants"
QUEUE = GRANTS / "_queue" / "index.json"
CATALOG = DATA / "grant_catalog.json"
PROFILE = DATA / "company_profile.json"

router = APIRouter(prefix="/api/grants", tags=["grants"])

# ----------------------------------------------------------------------------
# Real-time event hook — gateway wires this to its WebSocket manager so
# Node-RED, Unity, and the Mission Control dashboard get push events when
# a grant is approved or marked submitted. Default is a no-op.
# ----------------------------------------------------------------------------
_event_sink = None  # type: ignore


def set_event_sink(sink) -> None:
    """Gateway calls this after mounting the router:
        from grants_api import set_event_sink
        set_event_sink(lambda p: asyncio.create_task(manager.broadcast(p)))
    """
    global _event_sink
    _event_sink = sink


def _emit(event_type: str, **payload) -> None:
    if _event_sink is None:
        return
    try:
        _event_sink({
            "type": f"grants_{event_type}",
            "ts": datetime.now(timezone.utc).isoformat(),
            **payload,
        })
    except Exception:
        pass


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _latest_run(prog_dir: Path) -> Path | None:
    if not prog_dir.exists():
        return None
    runs = sorted([p for p in prog_dir.iterdir() if p.is_dir()])
    return runs[-1] if runs else None


def _run_factory(args: list[str]) -> dict:
    """Invoke the factory CLI in-process by calling its main()."""
    sys.path.insert(0, str(ROOT / "code"))
    try:
        from grant_application_factory import main as factory_main
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"factory import failed: {e}")
    rc = factory_main(args)
    if rc != 0:
        raise HTTPException(status_code=500,
                            detail=f"factory returned non-zero: {rc}")
    return _load(QUEUE) if QUEUE.exists() else {}


# ----------------------------------------------------------------------------
# GET endpoints
# ----------------------------------------------------------------------------
@router.get("")
def queue_summary() -> JSONResponse:
    if not QUEUE.exists():
        # auto-bootstrap empty queue
        try:
            _run_factory(["--list"])
        except HTTPException as exc:
            return JSONResponse({
                "items": [],
                "status": "factory_unavailable",
                "detail": str(exc.detail),
                "generated_utc": datetime.now(timezone.utc).isoformat(),
            })
    return JSONResponse(_load(QUEUE) if QUEUE.exists() else {"items": []})


@router.get("/catalog")
def catalog() -> JSONResponse:
    if not CATALOG.exists():
        raise HTTPException(status_code=404, detail="catalog missing")
    return JSONResponse(_load(CATALOG))


@router.get("/profile")
def profile() -> JSONResponse:
    if not PROFILE.exists():
        raise HTTPException(status_code=404, detail="profile missing")
    return JSONResponse(_load(PROFILE))


class ProfilePatch(BaseModel):
    """Partial update for data/company_profile.json. Any field omitted is left
    untouched. Pass either flat keys (uei, ein, address_line1, city, state, zip,
    phone, email) or nested dicts (company={...}, pi={...})."""
    company: dict | None = None
    pi: dict | None = None
    uei: str | None = None
    ein: str | None = None
    sam_gov_status: str | None = None
    address_line1: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    phone: str | None = None
    email: str | None = None
    regenerate: bool = True


@router.post("/profile")
def patch_profile(patch: ProfilePatch) -> JSONResponse:
    """Patch the company / PI profile and (optionally) regenerate all grant
    packages so TO_BE_FILLED blockers clear in one shot.

    This is the operator's one-stop fix when SAM.gov UEI clears: drop in
    `{"uei":"...","ein":"...","address_line1":"...","city":"...","state":"...",
    "zip":"...","phone":"...","email":"..."}` and the entire grant queue is
    regenerated with the new values.
    """
    if not PROFILE.exists():
        raise HTTPException(status_code=404, detail="profile missing")
    prof = _load(PROFILE)
    company = prof.setdefault("company", {})
    pi = prof.setdefault("pi", {})

    # Merge nested dicts if provided
    if patch.company:
        company.update({k: v for k, v in patch.company.items() if v is not None})
    if patch.pi:
        pi.update({k: v for k, v in patch.pi.items() if v is not None})

    # Convenience flat-key shortcuts (overwrite company-level fields)
    if patch.uei is not None:
        company["duns_or_uei"] = patch.uei
    if patch.ein is not None:
        company["ein"] = patch.ein
    if patch.sam_gov_status is not None:
        company["sam_gov_status"] = patch.sam_gov_status
    for k in ("address_line1", "city", "state", "zip", "phone", "email"):
        v = getattr(patch, k, None)
        if v is not None:
            company[k] = v

    # Atomic write
    tmp = PROFILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(prof, indent=2), encoding="utf-8")
    tmp.replace(PROFILE)
    _emit("profile_patched", patched_keys=[k for k in (
        "company", "pi", "uei", "ein", "sam_gov_status",
        "address_line1", "city", "state", "zip", "phone", "email")
        if getattr(patch, k, None) is not None])

    result: dict = {"ok": True, "profile": prof}
    if patch.regenerate:
        try:
            # --force so approved (but not yet submitted) grants get rebuilt
            # with the new profile; their approved state is preserved.
            queue = _run_factory(["--force"])
            result["regenerated"] = True
            result["queue"] = queue
        except HTTPException as e:
            result["regenerated"] = False
            result["regenerate_error"] = e.detail
    return JSONResponse(result)


@router.get("/{grant_id}")
def grant_detail(grant_id: str) -> JSONResponse:
    run = _latest_run(GRANTS / grant_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"no draft for {grant_id}")
    out: dict = {"grant_id": grant_id, "run_utc": run.name}
    for f in ["application.json", "eligibility_report.json", "budget.json",
              "approval_state.json", "evidence_manifest.json",
              "manifest.sha256.json"]:
        p = run / f
        if p.exists():
            out[f.replace(".json", "")] = json.loads(p.read_text(encoding="utf-8"))
    return JSONResponse(out)


@router.get("/{grant_id}/markdown")
def grant_markdown(grant_id: str,
                   section: str = Query(default="application")) -> PlainTextResponse:
    run = _latest_run(GRANTS / grant_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"no draft for {grant_id}")
    fname = {
        "application": "application.md",
        "technical": "technical_volume.md",
        "commercialization": "commercialization_plan.md",
        "cover": "cover_letter.md",
    }.get(section)
    if not fname:
        raise HTTPException(status_code=400, detail=f"unknown section {section}")
    p = run / fname
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"no {fname}")
    return PlainTextResponse(p.read_text(encoding="utf-8"),
                             media_type="text/markdown; charset=utf-8")


# ----------------------------------------------------------------------------
# Print-ready HTML (browser "Save as PDF" -> grants.gov-grade PDF)
# ----------------------------------------------------------------------------
_PRINT_CSS = """
@page { size: Letter; margin: 0.9in 0.85in; }
* { box-sizing: border-box; }
body { font: 11pt/1.55 "Times New Roman", Georgia, serif; color: #111;
       max-width: 7in; margin: 0 auto; padding: 0; }
h1 { font-size: 18pt; margin: 0 0 6pt; border-bottom: 2pt solid #111; padding-bottom: 4pt; }
h2 { font-size: 13pt; margin: 18pt 0 6pt; color: #1f2a4f; page-break-after: avoid; }
h3 { font-size: 11.5pt; margin: 12pt 0 4pt; color: #444; page-break-after: avoid; }
hr { border: 0; border-top: 1pt solid #aaa; margin: 14pt 0; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0; page-break-inside: avoid; }
th, td { padding: 4pt 8pt; border-bottom: 0.5pt solid #999; text-align: left; vertical-align: top; }
th { background: #f0f2fa; }
ul { margin: 4pt 0 8pt; padding-left: 22pt; }
li { margin: 2pt 0; }
code { font-family: "Consolas", "Courier New", monospace; font-size: 9.5pt;
       background: #f4f4f4; padding: 1pt 4pt; border-radius: 2pt; }
.cover { text-align: center; padding-top: 1.5in; page-break-after: always; }
.cover h1 { border: 0; font-size: 26pt; margin-bottom: 12pt; }
.cover .sub { font-size: 14pt; color: #555; margin-bottom: 36pt; }
.cover .meta { font-size: 11pt; color: #333; line-height: 1.9; }
.section-break { page-break-before: always; }
.toolbar { background: #1f2a4f; color: white; padding: 8pt 14pt; margin-bottom: 12pt;
           border-radius: 4pt; font-family: -apple-system, sans-serif; font-size: 10pt; }
.toolbar a { color: #93c5fd; margin-right: 14pt; text-decoration: none; }
.toolbar button { background: #22d3ee; color: #0b1020; border: 0; padding: 4pt 12pt;
                  font-weight: 600; border-radius: 3pt; cursor: pointer; font-size: 10pt; }
@media print { .toolbar { display: none; } body { max-width: none; } }
"""


def _md_to_html(md: str) -> str:
    """Lightweight markdown -> HTML for print rendering."""
    lines = md.split("\n")
    out: list[str] = []
    in_list = False
    in_table = False

    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def inline(s: str) -> str:
        s = esc(s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        return s

    def flush() -> None:
        nonlocal in_list, in_table
        if in_list:
            out.append("</ul>"); in_list = False
        if in_table:
            out.append("</tbody></table>"); in_table = False

    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("### "):
            flush(); out.append(f"<h3>{inline(l[4:])}</h3>")
        elif l.startswith("## "):
            flush(); out.append(f"<h2>{inline(l[3:])}</h2>")
        elif l.startswith("# "):
            flush(); out.append(f"<h1>{inline(l[2:])}</h1>")
        elif l.startswith("---"):
            flush(); out.append("<hr/>")
        elif l.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-:\s|]+\|$", lines[i+1]):
            flush()
            cells = [c.strip() for c in l.strip("|").split("|")]
            out.append("<table><thead><tr>" +
                       "".join(f"<th>{inline(c)}</th>" for c in cells) +
                       "</tr></thead><tbody>")
            in_table = True
            i += 1  # skip separator
        elif l.startswith("|") and in_table:
            cells = [c.strip() for c in l.strip("|").split("|")]
            out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in cells) + "</tr>")
        elif l.startswith("- "):
            if not in_list:
                flush(); out.append("<ul>"); in_list = True
            out.append(f"<li>{inline(l[2:])}</li>")
        elif l.strip():
            flush(); out.append(f"<p>{inline(l)}</p>")
        else:
            flush()
        i += 1
    flush()
    return "\n".join(out)


@router.get("/{grant_id}/print", response_class=HTMLResponse)
def print_html(grant_id: str) -> HTMLResponse:
    """Single-document print view: cover + application + technical + commercialization + budget."""
    run = _latest_run(GRANTS / grant_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"no draft for {grant_id}")

    app_json = json.loads((run / "application.json").read_text(encoding="utf-8"))
    budget = json.loads((run / "budget.json").read_text(encoding="utf-8"))

    def _read(name: str) -> str:
        p = run / name
        return p.read_text(encoding="utf-8") if p.exists() else ""

    cover = _read("cover_letter.md")
    application = _read("application.md")
    technical = _read("technical_volume.md")
    commercialization = _read("commercialization_plan.md")

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    title_block = f"""
    <div class="cover">
      <h1>{app_json.get('agency','')}</h1>
      <div class="sub">{app_json.get('program','')} — {app_json.get('topic_area','')}</div>
      <div class="meta">
        <b>Applicant:</b> LumenCore Research, LLC<br/>
        <b>Principal Investigator:</b> Robert (BabyRay) Ashworth<br/>
        <b>Requested:</b> ${app_json.get('ceiling_usd', 0):,} over {app_json.get('duration_months','—')} months<br/>
        <b>Frozen evidence run:</b> {app_json.get('run_utc','')}<br/>
        <b>Prepared:</b> {today}
      </div>
    </div>
    """

    body_parts = [title_block]
    for label, md in [
        ("Cover Letter", cover),
        ("Application", application),
        ("Technical Volume", technical),
        ("Commercialization Plan", commercialization),
    ]:
        if md.strip():
            body_parts.append(f'<div class="section-break"></div>')
            body_parts.append(_md_to_html(md))

    # Budget table
    rows = "".join(
        f"<tr><td>{k.replace('_',' ').title()}</td>"
        f"<td style='text-align:right'>${v:,.0f}</td></tr>"
        for k, v in (budget.get("categories") or {}).items()
    )
    notes = "".join(f"<li>{n}</li>" for n in (budget.get("notes") or []))
    body_parts.append('<div class="section-break"></div>')
    body_parts.append(
        f"<h1>Budget Detail</h1>"
        f"<p><b>Total:</b> ${budget.get('total',0):,} over "
        f"{budget.get('duration_months','—')} months</p>"
        f"<table><thead><tr><th>Category</th><th style='text-align:right'>USD</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f"<h3>Notes</h3><ul>{notes}</ul>"
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<title>{app_json.get('agency','')} — {grant_id}</title>
<style>{_PRINT_CSS}</style>
</head><body>
<div class="toolbar">
  <a href="/grants.html">&larr; back to console</a>
  <button onclick="window.print()">Save as PDF</button>
  <span style="float:right; opacity:0.7">{grant_id} · {run.name}</span>
</div>
{''.join(body_parts)}
</body></html>"""
    return HTMLResponse(html)


@router.get("/{grant_id}/bundle.zip")
def bundle_zip(grant_id: str) -> Response:
    """Download a ZIP of the entire approved (or draft) submission package."""
    run = _latest_run(GRANTS / grant_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"no draft for {grant_id}")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in run.iterdir():
            if p.is_file():
                z.write(p, arcname=p.name)
    buf.seek(0)
    fname = f"{grant_id}_{run.name}.zip"
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ----------------------------------------------------------------------------
# Innovation #18: run-over-run diff (current draft vs approved snapshot)
# ----------------------------------------------------------------------------
@router.get("/{grant_id}/diff")
def grant_diff(grant_id: str) -> JSONResponse:
    """Compare the current draft vs the approved snapshot (if any).

    Returns per-file SHA-256 deltas plus a structured diff of headline numbers
    in application.json (eligibility score, budget total, evidence run UTC,
    layer counts) so the user can decide whether to re-approve.
    """
    current = _latest_run(GRANTS / grant_id)
    if not current:
        raise HTTPException(status_code=404, detail=f"no draft for {grant_id}")
    approved_root = GRANTS / "_approved" / grant_id
    approved = _latest_run(approved_root) if approved_root.exists() else None

    out: dict = {
        "grant_id": grant_id,
        "current_run_utc": current.name,
        "approved_run_utc": approved.name if approved else None,
        "has_approved": approved is not None,
        "files": [],
        "headline": {},
    }

    if not approved:
        out["files"] = [{"name": p.name, "status": "new"}
                        for p in current.iterdir() if p.is_file()]
        return JSONResponse(out)

    cur_man = _load(current / "manifest.sha256.json").get("files", {})
    app_man = _load(approved / "manifest.sha256.json").get("files", {})
    names = sorted(set(cur_man) | set(app_man))
    for n in names:
        cur_h = cur_man.get(n, {}).get("sha256")
        app_h = app_man.get(n, {}).get("sha256")
        if cur_h and app_h and cur_h == app_h:
            status = "unchanged"
        elif cur_h and not app_h:
            status = "added"
        elif app_h and not cur_h:
            status = "removed"
        else:
            status = "modified"
        out["files"].append({
            "name": n, "status": status,
            "current_sha256": cur_h, "approved_sha256": app_h,
            "current_bytes": cur_man.get(n, {}).get("size_bytes"),
            "approved_bytes": app_man.get(n, {}).get("size_bytes"),
        })

    # Headline diff from application.json
    cur_app = _load(current / "application.json")
    app_app = _load(approved / "application.json")
    headline: dict = {}

    def cmp(label: str, cur, prev):
        headline[label] = {
            "current": cur, "approved": prev,
            "changed": cur != prev,
        }

    cmp("evidence_run_utc",
        cur_app.get("run_utc") or cur_app.get("evidence_summary", {}).get("run_utc"),
        app_app.get("run_utc") or app_app.get("evidence_summary", {}).get("run_utc"))
    cmp("eligibility_score",
        cur_app.get("eligibility", {}).get("score"),
        app_app.get("eligibility", {}).get("score"))
    cmp("budget_total",
        cur_app.get("budget", {}).get("total"),
        app_app.get("budget", {}).get("total"))

    # Per-layer evidence deltas
    cur_layers = cur_app.get("evidence_summary", {}) or {}
    app_layers = app_app.get("evidence_summary", {}) or {}
    layers_diff: dict = {}
    for k in sorted(set(cur_layers) | set(app_layers)):
        layers_diff[k] = {
            "current": cur_layers.get(k),
            "approved": app_layers.get(k),
            "changed": cur_layers.get(k) != app_layers.get(k),
        }
    headline["layers"] = layers_diff
    out["headline"] = headline
    return JSONResponse(out)


# ----------------------------------------------------------------------------
# Innovation #19: submission preflight + escort
# ----------------------------------------------------------------------------
def _catalog_entry_for(grant_id: str) -> dict | None:
    """Look up the catalog row for a grant_id; tolerate missing catalog."""
    try:
        if not QUEUE.exists():
            return None
        idx = _load(QUEUE)
        for it in idx.get("items", []):
            if it.get("program_id") == grant_id:
                return it
    except Exception:
        pass
    return None


def _load_submission_tooling():
    sys.path.insert(0, str(ROOT / "code"))
    try:
        from grant_submission_kit import build_preflight, write_submission_kit  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"submission kit import failed: {e}")
    return build_preflight, write_submission_kit


def _prepare_submission_for_run(grant_id: str, run: Path, catalog_entry: dict | None) -> dict:
    build_preflight, write_submission_kit = _load_submission_tooling()
    pf = build_preflight(grant_id, run, catalog_entry)
    files = write_submission_kit(grant_id, run, pf)
    pf["written"] = {k: str(v) for k, v in files.items()}
    return pf


@router.get("/submission/dashboard")
def submission_dashboard() -> JSONResponse:
    """One-shot preflight across every grant in the queue.

    Returns ready-to-submit count, total ceiling at risk, blockers histogram,
    and per-grant status. The dashboard surface for the cockpit."""
    build_preflight, _ = _load_submission_tooling()
    if not QUEUE.exists():
        return JSONResponse({"items": [], "totals": {}})
    idx = _load(QUEUE)
    items: list[dict] = []
    blockers_hist: dict[str, int] = {}
    ready_count = 0
    approved_count = 0
    submitted_count = 0
    total_ceiling = 0.0
    ready_ceiling = 0.0
    for row in idx.get("items", []):
        gid = row.get("program_id")
        if not gid:
            continue
        run = _latest_run(GRANTS / gid)
        if not run:
            continue
        try:
            pf = build_preflight(gid, run, row)
        except Exception as e:
            pf = {"grant_id": gid, "ready": False,
                  "blockers": [f"preflight error: {e}"]}
        items.append(pf)
        ceiling = float(pf.get("ceiling_usd") or 0.0)
        total_ceiling += ceiling
        if pf.get("approval_state") == "approved":
            approved_count += 1
        if pf.get("approval_state") == "submitted":
            submitted_count += 1
        if pf.get("ready"):
            ready_count += 1
            ready_ceiling += ceiling
        for b in pf.get("blockers", []):
            # Bucketize first 4 words for histogram
            key = " ".join(str(b).split()[:4])
            blockers_hist[key] = blockers_hist.get(key, 0) + 1
    totals = {
        "n_total": len(items),
        "n_approved": approved_count,
        "n_submitted": submitted_count,
        "n_ready_to_submit": ready_count,
        "ceiling_total_usd": round(total_ceiling, 2),
        "ceiling_ready_to_submit_usd": round(ready_ceiling, 2),
        "blockers_histogram": blockers_hist,
        "preflight_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    }
    return JSONResponse({"items": items, "totals": totals})


@router.get("/{grant_id}/submission")
def submission_status(grant_id: str) -> JSONResponse:
    """Read the latest submission packet + howto for a grant if generated."""
    run = _latest_run(GRANTS / grant_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"no draft for {grant_id}")

    packet_p = run / "submission_packet.json"
    howto_p = run / "SUBMIT_HOWTO.md"
    if not packet_p.exists():
        raise HTTPException(status_code=404,
                            detail="submission packet missing - run prepare_submission")

    payload = {
        "grant_id": grant_id,
        "run_utc": run.name,
        "submission_packet": _load(packet_p),
        "has_howto": howto_p.exists(),
        "howto_markdown": howto_p.read_text(encoding="utf-8") if howto_p.exists() else None,
    }
    return JSONResponse(payload)


@router.post("/{grant_id}/prepare_submission")
def prepare_submission(grant_id: str) -> JSONResponse:
    """Run preflight for one grant and write submission_packet.json + SUBMIT_HOWTO.md
    into the latest run directory. Returns the preflight dict."""
    run = _latest_run(GRANTS / grant_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"no draft for {grant_id}")
    catalog_entry = _catalog_entry_for(grant_id)
    pf = _prepare_submission_for_run(grant_id, run, catalog_entry)
    _emit("preflight", grant_id=grant_id,
          ready=pf.get("ready"),
          blockers=pf.get("blockers", []),
          ceiling_usd=pf.get("ceiling_usd"))
    return JSONResponse(pf)


# ----------------------------------------------------------------------------
# POST endpoints
# ----------------------------------------------------------------------------
class RegenerateRequest(BaseModel):
    grant_id: str | None = None


class DraftRequest(BaseModel):
    grant_id: str | None = None
    force: bool = True
    prepare_submission: bool = True


@router.post("/draft")
def draft(req: DraftRequest) -> JSONResponse:
    """One-click drafting pipeline: regenerate + submission kit preflight.

    This endpoint powers the portal's "Draft to submit-ready" action so
    operators can refresh narrative artifacts and immediately see blockers
    before manual AOR submission.
    """
    args: list[str] = []
    if req.grant_id:
        args.extend(["--grant", req.grant_id])
    if req.force:
        args.append("--force")

    idx = _run_factory(args)
    items = idx.get("items", []) if isinstance(idx, dict) else []
    target_ids: list[str] = []
    if req.grant_id:
        target_ids = [req.grant_id]
    else:
        target_ids = [str(it.get("program_id")) for it in items if it.get("program_id")]

    draft_items: list[dict] = []
    if req.prepare_submission:
        for grant_id in target_ids:
            run = _latest_run(GRANTS / grant_id)
            if not run:
                draft_items.append({
                    "grant_id": grant_id,
                    "ready": False,
                    "error": "no draft run found",
                })
                continue
            try:
                pf = _prepare_submission_for_run(grant_id, run, _catalog_entry_for(grant_id))
                draft_items.append({
                    "grant_id": grant_id,
                    "run_utc": run.name,
                    "ready": bool(pf.get("ready")),
                    "package_complete": bool(pf.get("package_complete")),
                    "approval_state": pf.get("approval_state"),
                    "blockers": pf.get("blockers", []),
                    "warnings": pf.get("warnings", []),
                    "written": pf.get("written", {}),
                    "portal_url": (pf.get("portal") or {}).get("portal_url"),
                })
            except HTTPException as e:
                draft_items.append({
                    "grant_id": grant_id,
                    "ready": False,
                    "error": str(e.detail),
                })

    n_ready = sum(1 for it in draft_items if it.get("ready") is True)
    n_blocked = sum(1 for it in draft_items if it.get("ready") is False)
    response = {
        "ok": True,
        "queue": idx,
        "draft": {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "n_total": len(draft_items),
            "n_ready": n_ready,
            "n_blocked": n_blocked,
            "items": draft_items,
        },
    }

    _emit(
        "drafted",
        grant_id=req.grant_id,
        force=req.force,
        prepare_submission=req.prepare_submission,
        n_ready=n_ready,
        n_blocked=n_blocked,
    )
    return JSONResponse(response)


@router.post("/regenerate")
def regenerate(req: RegenerateRequest) -> JSONResponse:
    args = []
    if req.grant_id:
        args = ["--grant", req.grant_id]
    idx = _run_factory(args)
    return JSONResponse({"ok": True, "queue": idx})


class SubmittedRequest(BaseModel):
    submitted_by: str | None = None
    external_tracking_id: str | None = None
    notes: str | None = None


@router.post("/{grant_id}/approve")
def approve(grant_id: str) -> JSONResponse:
    sys.path.insert(0, str(ROOT / "code"))
    try:
        from grant_application_factory import approve as _approve, update_queue
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"factory import failed: {e}")
    state = _approve(grant_id)
    queue = update_queue()
    _emit("approved", grant_id=grant_id, state=state, queue_summary={
        "n_total": queue.get("n_total"),
        "n_draft": queue.get("n_draft"),
        "n_approved": queue.get("n_approved"),
        "n_submitted": queue.get("n_submitted"),
    })
    return JSONResponse({"ok": True, "state": state, "queue": queue})


@router.post("/{grant_id}/submitted")
def mark_submitted(grant_id: str, req: SubmittedRequest) -> JSONResponse:
    run = _latest_run(GRANTS / grant_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"no draft for {grant_id}")
    state_p = run / "approval_state.json"
    if not state_p.exists():
        raise HTTPException(status_code=500, detail="approval_state missing")
    state = json.loads(state_p.read_text(encoding="utf-8"))
    if state.get("state") not in ("approved", "submitted"):
        raise HTTPException(
            status_code=400,
            detail=f"grant must be approved before marking submitted (state={state.get('state')})")
    state["state"] = "submitted"
    state["submitted_utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    state["submitted_by"] = req.submitted_by
    state["external_tracking_id"] = req.external_tracking_id
    if req.notes:
        state["notes"] = req.notes
    state_p.write_text(json.dumps(state, indent=2), encoding="utf-8")

    sys.path.insert(0, str(ROOT / "code"))
    from grant_application_factory import update_queue
    queue = update_queue()
    _emit("submitted", grant_id=grant_id, state=state, queue_summary={
        "n_total": queue.get("n_total"),
        "n_draft": queue.get("n_draft"),
        "n_approved": queue.get("n_approved"),
        "n_submitted": queue.get("n_submitted"),
    })
    return JSONResponse({"ok": True, "state": state, "queue": queue})
