"""Job application factory for Luma Opportunity Engine.

Pipeline:
  1. Load job target catalog (data/job_target_catalog.json)
  2. Load latest revised resume and evidence snapshot
  3. Score role fit using keyword overlap and priority boost
  4. Generate per-role application packages under out/jobs/<job_id>/<utc>/
  5. Refresh queue index at out/jobs/_queue/index.json

Important:
  - This engine prepares submission-grade packages.
  - Final submit stays human-in-the-loop for compliance and account safety.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from application_context_resolver import load_application_profile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
JOBS_ROOT = ROOT / "out" / "jobs"
QUEUE_ROOT = JOBS_ROOT / "_queue"
APPROVED_ROOT = JOBS_ROOT / "_approved"

CATALOG_PATH = DATA / "job_target_catalog.json"
PROFILE_PATH = DATA / "company_profile.json"
RESUME_MD_PATH = ROOT / "RESUME_LUMENCORE.md"
RESUME_JSON_PATH = ROOT / "out" / "resume" / "resume_lumalinkedin_v1_latest.json"
RESUME_PDF_PATH = ROOT / "out" / "resume" / "RESUME_LUMENCORE_ELITE.pdf"

VALID_STATES = {
    "draft",
    "approved",
    "submitted",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(value or "")).strip("_")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")
    tmp.replace(path)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_roles() -> list[dict[str, Any]]:
    catalog = _read_json(CATALOG_PATH)
    roles = catalog.get("roles", []) if isinstance(catalog, dict) else []
    if not isinstance(roles, list):
        return []
    clean: list[dict[str, Any]] = []
    for row in roles:
        if isinstance(row, dict) and row.get("id") and row.get("title"):
            clean.append(row)
    return clean


def _load_resume_text() -> str:
    if RESUME_MD_PATH.exists():
        return RESUME_MD_PATH.read_text(encoding="utf-8", errors="ignore")
    return ""


def _role_score(role: dict[str, Any], resume_blob: str) -> tuple[float, list[str]]:
    keywords = role.get("fit_keywords", [])
    if not isinstance(keywords, list):
        keywords = []

    blob = resume_blob.lower()
    matched: list[str] = []
    for kw in keywords:
        kw_txt = str(kw).strip().lower()
        if kw_txt and kw_txt in blob:
            matched.append(str(kw))

    ratio = (len(matched) / len(keywords)) if keywords else 0.0
    priority = str(role.get("priority") or "P2").upper()
    boost = {"P0": 0.18, "P1": 0.1, "P2": 0.04}.get(priority, 0.0)
    clearance = bool(role.get("clearance_friendly"))
    clearance_boost = 0.08 if clearance and "government" in blob else 0.0
    score = min(1.0, ratio + boost + clearance_boost)
    return round(score, 4), matched


def _cover_letter(role: dict[str, Any], profile: dict[str, Any], score: float, matched: list[str]) -> str:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    pi = profile.get("pi", {}) if isinstance(profile, dict) else {}
    name = str(pi.get("name") or company.get("founder_pi") or "Robert BabyRay Ashworth")
    email = str(company.get("email") or "robertashworth4444@gmail.com")
    phone = str(company.get("phone") or "615-438-2502")

    return f"""# Cover Letter

Hiring Team,

I am applying for the {role.get('title')} role. I build and operate institutional-grade AI and quant infrastructure with explicit runtime controls, risk guardrails, and machine-readable evidence artifacts.

Fit score for this role in my Luma opportunity engine is {score:.2f}, with direct keyword overlap on: {', '.join(matched) if matched else 'core systems engineering competencies'}.

I have hands-on ownership across architecture, implementation, operations, and validation for live data and execution stacks, including government-style evidence packaging and investor-ready reporting.

Respectfully,

{name}
{email}
{phone}
"""


def _linkedin_intro(role: dict[str, Any], profile: dict[str, Any]) -> str:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    pi = profile.get("pi", {}) if isinstance(profile, dict) else {}
    name = str(pi.get("name") or company.get("founder_pi") or "Robert BabyRay Ashworth")
    return (
        f"Hi, I am {name}. I am reaching out regarding the {role.get('title')} opportunity. "
        "I build institutional-grade AI and quant systems with production controls, proof-grade artifacts, "
        "and strong execution discipline. I can share a role-specific package immediately."
    )


def _submit_howto(role: dict[str, Any]) -> str:
    hints = role.get("submission_portal_hints", [])
    if not isinstance(hints, list):
        hints = []
    hint_text = ", ".join(str(x) for x in hints) if hints else "linkedin_jobs, company_careers"

    return f"""# SUBMIT HOWTO

Role: {role.get('title')}
Channel: {role.get('channel')}
Portal hints: {hint_text}

1. Confirm the active role URL and capture requisition ID.
2. Upload resume.md (and resume.pdf if required) from this package.
3. Paste the cover letter with role-specific edits.
4. Use linkedin_intro_message.md for recruiter outreach.
5. Submit manually under your account.
6. Record confirmation ID in approval_state.json and move state to submitted.

Policy: human review and manual final submit are required.
"""


def _write_manifest(run_dir: Path) -> dict[str, str]:
    files = sorted([p for p in run_dir.iterdir() if p.is_file() and p.name != "manifest.sha256.json"])
    payload = {p.name: _sha256(p) for p in files}
    _write_json(run_dir / "manifest.sha256.json", payload)
    return payload


def _latest_run_dir(job_id: str) -> Path | None:
    root = JOBS_ROOT / job_id
    if not root.exists() or not root.is_dir():
        return None
    runs = [p for p in root.iterdir() if p.is_dir()]
    if not runs:
        return None
    return sorted(runs, key=lambda p: p.name)[-1]


def _refresh_queue_index() -> dict[str, Any]:
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)
    QUEUE_ROOT.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, Any]] = []
    for job_root in sorted(JOBS_ROOT.iterdir()) if JOBS_ROOT.exists() else []:
        if not job_root.is_dir() or job_root.name.startswith("_"):
            continue
        latest = _latest_run_dir(job_root.name)
        if not latest:
            continue
        app = _read_json(latest / "application.json")
        state_obj = _read_json(latest / "approval_state.json")
        state = str(state_obj.get("state") or "draft").lower()
        if state not in VALID_STATES:
            state = "draft"
        items.append(
            {
                "job_id": str(app.get("job_id") or job_root.name),
                "slug": f"{job_root.name}/{latest.name}",
                "title": app.get("title") or job_root.name,
                "channel": app.get("channel"),
                "priority": app.get("priority"),
                "state": state,
                "fit_score": app.get("fit_score"),
                "matched_keywords": app.get("matched_keywords"),
                "updated_utc": state_obj.get("updated_utc") or state_obj.get("generated_utc"),
                "run_dir": str(latest),
            }
        )

    counts: dict[str, int] = {}
    for item in items:
        st = str(item.get("state") or "draft")
        counts[st] = counts.get(st, 0) + 1

    payload = {
        "generated_utc": _now_iso(),
        "n_total": len(items),
        "n_draft": counts.get("draft", 0),
        "n_approved": counts.get("approved", 0),
        "n_submitted": counts.get("submitted", 0),
        "n_interview": counts.get("interview", 0),
        "n_offer": counts.get("offer", 0),
        "n_rejected": counts.get("rejected", 0),
        "items": items,
    }
    _write_json(QUEUE_ROOT / "index.json", payload)

    queue_jsonl = QUEUE_ROOT / "queue.jsonl"
    queue_jsonl.parent.mkdir(parents=True, exist_ok=True)
    queue_jsonl.write_text("\n".join(json.dumps(x) for x in items) + ("\n" if items else ""), encoding="utf-8")
    return payload


def _approve(job_id: str) -> dict[str, Any]:
    latest = _latest_run_dir(job_id)
    if latest is None:
        return {"ok": False, "error": f"job {job_id} not found"}

    state_path = latest / "approval_state.json"
    state = _read_json(state_path)
    state["state"] = "approved"
    state["approved_utc"] = _now_iso()
    state["updated_utc"] = _now_iso()
    _write_json(state_path, state)

    target = APPROVED_ROOT / job_id / latest.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(latest, target, dirs_exist_ok=True)
    queue = _refresh_queue_index()
    return {"ok": True, "job_id": job_id, "run_dir": str(latest), "approved_copy": str(target), "queue": queue}


def _build_resume_blob(resume_text: str, resume_payload: dict[str, Any]) -> str:
    metrics = resume_payload.get("metrics", {}) if isinstance(resume_payload, dict) else {}
    packages = resume_payload.get("proven_packages", []) if isinstance(resume_payload, dict) else []
    package_names = []
    if isinstance(packages, list):
        for row in packages:
            if isinstance(row, dict) and row.get("package"):
                package_names.append(str(row.get("package")))
    metric_text = " ".join(f"{k}:{v}" for k, v in metrics.items()) if isinstance(metrics, dict) else ""
    return f"{resume_text}\n{metric_text}\n{' '.join(package_names)}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build resume-backed job application packages.")
    parser.add_argument("--job", default="", help="Only build a specific job id")
    parser.add_argument("--min-score", type=float, default=0.38)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--approve", default="", help="Approve latest run for a given job id")
    parser.add_argument("--list", action="store_true", help="Print queue summary")
    args = parser.parse_args()

    if args.approve:
        result = _approve(_safe_slug(args.approve))
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 2

    if args.list:
        queue = _refresh_queue_index()
        print(json.dumps(queue, indent=2))
        return 0

    roles = _load_roles()
    if not roles:
        print(f"[error] no roles found in {CATALOG_PATH}")
        return 2

    profile = load_application_profile()
    resume_text = _load_resume_text()
    if not resume_text.strip():
        print(f"[error] missing resume markdown at {RESUME_MD_PATH}")
        print("[hint] run code/lumalinkedin_resume_engine_v1.py first")
        return 2
    resume_payload = _read_json(RESUME_JSON_PATH)
    resume_blob = _build_resume_blob(resume_text, resume_payload)

    selected_roles: list[dict[str, Any]] = []
    for role in roles:
        if args.job and _safe_slug(role.get("id", "")) != _safe_slug(args.job):
            continue
        score, matched = _role_score(role, resume_blob)
        if score < args.min_score:
            continue
        row = dict(role)
        row["_fit_score"] = score
        row["_matched_keywords"] = matched
        selected_roles.append(row)

    selected_roles.sort(key=lambda r: float(r.get("_fit_score", 0.0)), reverse=True)
    selected_roles = selected_roles[: max(1, args.limit)]

    if not selected_roles:
        print("[info] no roles met the min-score threshold")
        queue = _refresh_queue_index()
        print(f"QUEUE={QUEUE_ROOT / 'index.json'}")
        print(f"TOTAL={queue.get('n_total', 0)}")
        return 0

    run_stamp = _stamp()
    built_items: list[dict[str, Any]] = []

    for role in selected_roles:
        job_id = _safe_slug(str(role.get("id") or role.get("title") or "job"))
        run_dir = JOBS_ROOT / job_id / run_stamp
        run_dir.mkdir(parents=True, exist_ok=True)

        matched = role.get("_matched_keywords") if isinstance(role.get("_matched_keywords"), list) else []
        app_payload = {
            "schema_version": "1.0",
            "generated_utc": _now_iso(),
            "job_id": job_id,
            "title": role.get("title"),
            "channel": role.get("channel"),
            "priority": role.get("priority"),
            "location_mode": role.get("location_mode"),
            "target_organizations": role.get("target_organizations", []),
            "fit_score": role.get("_fit_score"),
            "matched_keywords": matched,
            "submission_portal_hints": role.get("submission_portal_hints", []),
            "clearance_friendly": bool(role.get("clearance_friendly")),
            "candidate": {
                "name": (profile.get("pi") or {}).get("name"),
                "email": (profile.get("company") or {}).get("email"),
                "phone": (profile.get("company") or {}).get("phone"),
                "website": (profile.get("company") or {}).get("website"),
                "address_line1": (profile.get("company") or {}).get("address_line1"),
                "city": (profile.get("company") or {}).get("city"),
                "state": (profile.get("company") or {}).get("state"),
                "zip": (profile.get("company") or {}).get("zip"),
                "country": (profile.get("company") or {}).get("country"),
                "uei": (profile.get("identifiers") or {}).get("uei"),
                "ein": (profile.get("identifiers") or {}).get("ein"),
                "cage_code": (profile.get("identifiers") or {}).get("cage_code"),
                "sam_gov_status": (profile.get("identifiers") or {}).get("sam_gov_status"),
                "patent_numbers": (profile.get("identifiers") or {}).get("patent_numbers", []),
            },
            "federal_readiness": profile.get("federal_readiness", {}),
            "evidence_snapshot": resume_payload.get("metrics", {}),
            "submission_policy": {
                "human_review_required": True,
                "manual_submit_required": True,
                "notes": "Do not auto-submit to external job portals without operator confirmation.",
            },
        }
        _write_json(run_dir / "application.json", app_payload)

        _write_text(run_dir / "cover_letter.md", _cover_letter(role, profile, float(role.get("_fit_score", 0.0)), matched))
        _write_text(run_dir / "linkedin_intro_message.md", _linkedin_intro(role, profile))
        _write_text(run_dir / "SUBMIT_HOWTO.md", _submit_howto(role))
        _write_text(run_dir / "resume.md", resume_text)

        if RESUME_PDF_PATH.exists():
            shutil.copy2(RESUME_PDF_PATH, run_dir / "resume.pdf")

        state_payload = {
            "state": "draft",
            "generated_utc": _now_iso(),
            "updated_utc": _now_iso(),
            "fit_score": role.get("_fit_score"),
            "notes": "Awaiting human review before submission.",
            "submission_locked": True,
        }
        _write_json(run_dir / "approval_state.json", state_payload)

        manifest = _write_manifest(run_dir)
        built_items.append(
            {
                "job_id": job_id,
                "title": role.get("title"),
                "fit_score": role.get("_fit_score"),
                "run_dir": str(run_dir),
                "manifest_entries": len(manifest),
            }
        )

    queue = _refresh_queue_index()
    summary = {
        "generated_utc": _now_iso(),
        "run_stamp": run_stamp,
        "min_score": args.min_score,
        "limit": args.limit,
        "built_count": len(built_items),
        "built": built_items,
        "queue": {
            "path": str(QUEUE_ROOT / "index.json"),
            "n_total": queue.get("n_total", 0),
            "n_draft": queue.get("n_draft", 0),
            "n_approved": queue.get("n_approved", 0),
            "n_submitted": queue.get("n_submitted", 0),
        },
    }
    summary_path = QUEUE_ROOT / f"factory_run_{run_stamp}.json"
    _write_json(summary_path, summary)

    print(f"SUMMARY={summary_path}")
    print(f"QUEUE={QUEUE_ROOT / 'index.json'}")
    print(f"BUILT={len(built_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
