"""Truthful job-application package assembly for Luma Opportunity Engine.

The factory prepares reviewable employment packets. It never submits an
application, and approving a package never unlocks the final-submit gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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

FINAL_SUBMIT_GATE_TEXT = (
    "Exact, action-time human approval for this role and destination is required "
    "before final external submission."
)
FINGERPRINT_VERSION = "job-application-v1"

_ROLE_FIELD_ALIASES = {
    "employer": ("employer", "company", "organization"),
    "role_url": ("role_url", "application_url", "job_url", "url"),
    "deadline": (
        "deadline",
        "deadline_utc",
        "application_deadline",
        "response_deadline",
        "closing_date",
    ),
    "timezone": ("timezone", "deadline_timezone", "deadline_time_zone"),
    "hard_requirements": (
        "hard_requirements",
        "required_qualifications",
        "minimum_qualifications",
        "must_have",
        "must_haves",
    ),
    "interest_text": ("role_specific_interest_text", "interest_text", "why_interested"),
}

_SENSITIVE_IDENTIFIER_LINE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?"
    r"(?:UEI|EIN|CAGE(?:[ \t]+code)?|"
    r"patent(?:[ \t]+(?:number|numbers|no\.?|identifier|identifiers)))"
    r"[ \t]*[:#=|-].*(?:\r?\n|$)"
)
_UNSUPPORTED_CLAIM_REPLACEMENTS = (
    (re.compile(r"\binstitutional[ -]grade\b", re.IGNORECASE), "evidence-oriented"),
    (re.compile(r"\binvestor[ -]ready\b", re.IGNORECASE), "review-focused"),
    (re.compile(r"\blive[ -]deploy(?:ment|ments|ed)\b", re.IGNORECASE), "deployment"),
    (re.compile(r"\bexternal(?:ly)?[ -]validat(?:ed|ion)\b", re.IGNORECASE), "validation"),
)
_SENSITIVE_IDENTIFIER_KEYS = {
    "uei",
    "ein",
    "tax_id",
    "federal_tax_id",
    "cage",
    "cage_code",
    "patent",
    "patents",
    "patent_no",
    "patent_number",
    "patent_numbers",
    "patent_identifiers",
}
_TIMEZONE_ALIASES = {
    "UTC": "UTC",
    "GMT": "UTC",
    "ET": "America/New_York",
    "EASTERN": "America/New_York",
    "CT": "America/Chicago",
    "CENTRAL": "America/Chicago",
    "MT": "America/Denver",
    "MOUNTAIN": "America/Denver",
    "PT": "America/Los_Angeles",
    "PACIFIC": "America/Los_Angeles",
}

_GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "icloud.com",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "yahoo.com",
}
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


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
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
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


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _first_present(mapping: dict[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name not in mapping:
            continue
        value = mapping.get(name)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _normalized_domain(value: Any) -> str:
    """Return a hostname without credentials, ports, or a leading www label."""
    raw = str(value or "").strip().casefold()
    if not raw:
        return ""
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    host = (parsed.hostname or "").strip(".")
    return host.removeprefix("www.")


def _contact_identity_gate(profile: dict[str, Any]) -> tuple[bool, str]:
    """Block package assembly when a company profile points to a mismatched inbox."""
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    company = company if isinstance(company, dict) else {}
    email = str(company.get("email", "")).strip().casefold()
    email_domain = email.rsplit("@", 1)[-1] if "@" in email else ""
    website_domain = _normalized_domain(company.get("website"))

    if not _EMAIL_RE.fullmatch(email):
        return False, "candidate contact email is missing or invalid"
    if not website_domain:
        return True, "no company website domain is configured"
    if email_domain in _GENERIC_EMAIL_DOMAINS:
        return False, "a generic inbox cannot be used while a company domain is configured"
    if email_domain != website_domain:
        return False, "candidate email domain does not match the configured company domain"
    return True, "candidate contact identity matches the configured company domain"


def _profile_identifier_values(profile: dict[str, Any]) -> list[str]:
    identifiers = profile.get("identifiers", {}) if isinstance(profile, dict) else {}
    values: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif value is not None and not isinstance(value, bool):
            text = str(value).strip()
            if len(text) >= 4:
                values.add(text)

    if isinstance(identifiers, dict):
        for key, value in identifiers.items():
            normalized_key = re.sub(r"[^a-z0-9]+", "_", str(key).casefold()).strip("_")
            if normalized_key in _SENSITIVE_IDENTIFIER_KEYS:
                visit(value)
    return sorted(values, key=len, reverse=True)


def _sanitize_employment_text(text: Any, profile: dict[str, Any]) -> str:
    """Remove employment-inapplicable identifiers and unsupported claim wording."""
    clean = str(text or "")
    clean = _SENSITIVE_IDENTIFIER_LINE.sub("", clean)
    for value in _profile_identifier_values(profile):
        clean = re.sub(re.escape(value), "[removed]", clean, flags=re.IGNORECASE)
    for pattern, replacement in _UNSUPPORTED_CLAIM_REPLACEMENTS:
        clean = pattern.sub(replacement, clean)
    clean = re.sub(r"[ \t]+\n", "\n", clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def _sanitize_structure(value: Any, profile: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return _sanitize_employment_text(value, profile)
    if isinstance(value, list):
        return [_sanitize_structure(item, profile) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_structure(item, profile) for key, item in value.items()}
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return _sanitize_employment_text(value, profile)


def _load_roles() -> list[dict[str, Any]]:
    catalog = _read_json(CATALOG_PATH)
    roles = catalog.get("roles", []) if isinstance(catalog, dict) else []
    if not isinstance(roles, list):
        return []
    return [row for row in roles if isinstance(row, dict) and row.get("id") and row.get("title")]


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


def _role_metadata(role: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for canonical in ("employer", "role_url", "deadline", "timezone", "hard_requirements"):
        value = _first_present(role, _ROLE_FIELD_ALIASES[canonical])
        if value is not None:
            metadata[canonical] = _sanitize_structure(value, profile)
    return metadata


def _timezone_from_name(value: str) -> timezone | ZoneInfo:
    cleaned = str(value or "").strip()
    alias = _TIMEZONE_ALIASES.get(cleaned.upper(), cleaned)
    offset_match = re.fullmatch(r"(?:UTC|GMT)?([+-])(\d{1,2})(?::?(\d{2}))?", alias, re.IGNORECASE)
    if offset_match:
        hours = int(offset_match.group(2))
        minutes = int(offset_match.group(3) or 0)
        if hours > 23 or minutes > 59:
            raise ValueError(f"invalid timezone offset: {value}")
        delta = timedelta(hours=hours, minutes=minutes)
        if offset_match.group(1) == "-":
            delta = -delta
        return timezone(delta)
    try:
        return ZoneInfo(alias)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {value}") from exc


def _parse_datetime_value(value: Any, timezone_name: Any = None) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("missing datetime")

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        parsed = datetime.combine(datetime.fromisoformat(raw).date(), time(23, 59, 59))
    else:
        normalized = re.sub(r"Z$", "+00:00", raw, flags=re.IGNORECASE)
        parsed = datetime.fromisoformat(normalized)

    if parsed.tzinfo is None:
        if timezone_name is None or not str(timezone_name).strip():
            raise ValueError("timezone required for a deadline without an offset")
        parsed = parsed.replace(tzinfo=_timezone_from_name(str(timezone_name)))
    return parsed.astimezone(timezone.utc)


def _deadline_evaluation(role: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    raw_deadline = _first_present(role, _ROLE_FIELD_ALIASES["deadline"])
    raw_timezone = _first_present(role, _ROLE_FIELD_ALIASES["timezone"])
    if raw_deadline is None:
        return {"status": "missing", "eligible": False, "reason": "missing_deadline"}

    try:
        deadline_utc = _parse_datetime_value(raw_deadline, raw_timezone)
    except (TypeError, ValueError) as exc:
        return {"status": "invalid", "eligible": False, "reason": str(exc)}

    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    reference = reference.astimezone(timezone.utc)
    if deadline_utc <= reference:
        return {
            "status": "expired",
            "eligible": False,
            "reason": "deadline_not_after_reference_time",
            "deadline_utc": deadline_utc.isoformat(),
        }
    return {
        "status": "active",
        "eligible": True,
        "reason": "deadline_after_reference_time",
        "deadline_utc": deadline_utc.isoformat(),
    }


def _candidate_payload(profile: dict[str, Any]) -> dict[str, Any]:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    pi = profile.get("pi", {}) if isinstance(profile, dict) else {}
    candidate = {
        "name": pi.get("name") or company.get("founder_pi"),
        "email": company.get("email"),
        "phone": company.get("phone"),
        "website": company.get("website"),
        "linkedin": pi.get("linkedin") or company.get("linkedin"),
        "address_line1": company.get("address_line1"),
        "city": company.get("city"),
        "state": company.get("state"),
        "zip": company.get("zip"),
        "country": company.get("country"),
    }
    return {key: _sanitize_employment_text(value, profile) for key, value in candidate.items() if value}


def _normalized_identity(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _application_fingerprint(role: dict[str, Any], candidate: dict[str, Any]) -> str:
    metadata = {
        key: _first_present(role, _ROLE_FIELD_ALIASES[key])
        for key in ("employer", "role_url")
    }
    identity = {
        "fingerprint_version": FINGERPRINT_VERSION,
        "candidate_email": _normalized_identity(candidate.get("email")),
        "job_id": _normalized_identity(role.get("id")),
        "title": _normalized_identity(role.get("title")),
        "employer": _normalized_identity(metadata.get("employer")),
        "role_url": _normalized_identity(metadata.get("role_url")).rstrip("/"),
    }
    return _hash_payload(identity)


def _role_specific_interest(
    role: dict[str, Any], profile: dict[str, Any], matched: list[str]
) -> str:
    supplied = _first_present(role, _ROLE_FIELD_ALIASES["interest_text"])
    if supplied is not None:
        return _sanitize_employment_text(supplied, profile)

    title = _sanitize_employment_text(role.get("title") or "this role", profile)
    employer = _first_present(role, _ROLE_FIELD_ALIASES["employer"])
    at_employer = f" at {_sanitize_employment_text(employer, profile)}" if employer else ""
    safe_matches = [_sanitize_employment_text(item, profile) for item in matched if str(item).strip()]
    if safe_matches:
        evidence = ", ".join(safe_matches[:4])
        return (
            f"I am interested in the {title} role{at_employer}. My resume contains direct "
            f"references to {evidence}, and I would welcome the opportunity to discuss how "
            "that documented experience maps to the role's stated requirements."
        )
    return (
        f"I am interested in the {title} role{at_employer}. I would welcome the opportunity "
        "to discuss how the experience documented in my resume maps to the role's stated requirements."
    )


def _cover_letter(
    role: dict[str, Any], profile: dict[str, Any], interest_text: str
) -> str:
    candidate = _candidate_payload(profile)
    signature = "\n".join(
        str(value) for value in (candidate.get("name"), candidate.get("email"), candidate.get("phone")) if value
    )
    return _sanitize_employment_text(
        f"""# Cover Letter

Hiring Team,

{interest_text}

The attached resume is the source of record for my experience, projects, tools, and results. I am available to answer questions or provide supporting work samples that can be shared appropriately.

Respectfully,

{signature}
""",
        profile,
    )


def _linkedin_intro(role: dict[str, Any], profile: dict[str, Any]) -> str:
    candidate = _candidate_payload(profile)
    name = str(candidate.get("name") or "the applicant")
    title = _sanitize_employment_text(role.get("title") or "role", profile)
    employer = _first_present(role, _ROLE_FIELD_ALIASES["employer"])
    destination = f" at {_sanitize_employment_text(employer, profile)}" if employer else ""
    return _sanitize_employment_text(
        f"Hi, I am {name}. I am reaching out regarding the {title} opportunity{destination}. "
        "My resume is available for review, and I would welcome a conversation about the role's stated requirements.",
        profile,
    )


def _format_hard_requirements(value: Any) -> str:
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in value) if value else "Not supplied"
    if isinstance(value, dict):
        return "\n".join(f"- {key}: {item}" for key, item in sorted(value.items())) or "Not supplied"
    return str(value) if value not in (None, "") else "Not supplied"


def _submit_howto(role: dict[str, Any], profile: dict[str, Any], metadata: dict[str, Any]) -> str:
    hints = role.get("submission_portal_hints", [])
    if not isinstance(hints, list):
        hints = []
    hint_text = ", ".join(_sanitize_employment_text(x, profile) for x in hints) if hints else "Not supplied"

    return _sanitize_employment_text(
        f"""# SUBMIT HOWTO

Role: {role.get('title')}
Employer: {metadata.get('employer') or 'Not supplied'}
Role URL: {metadata.get('role_url') or 'Not supplied'}
Deadline: {metadata.get('deadline') or 'Not supplied'}
Timezone: {metadata.get('timezone') or 'Not supplied'}
Channel: {role.get('channel') or 'Not supplied'}
Portal hints: {hint_text}
Hard requirements:
{_format_hard_requirements(metadata.get('hard_requirements'))}

1. Re-open the official role URL and confirm the role is still active.
2. Re-check every hard requirement and application answer against current facts.
3. Convert the sanitized resume.md to PDF only if the portal requires PDF.
4. Upload only the reviewed artifacts required by the portal.
5. Stop at the final-submit control for exact, action-time human approval.
6. After a human submits, record the external confirmation ID and receipt separately.

Final-submit gate: {FINAL_SUBMIT_GATE_TEXT}
This factory never performs the external submission.
""",
        profile,
    )


def _write_manifest(run_dir: Path) -> dict[str, str]:
    files = sorted(p for p in run_dir.iterdir() if p.is_file() and p.name != "manifest.sha256.json")
    payload = {p.name: _sha256(p) for p in files}
    _write_json(run_dir / "manifest.sha256.json", payload)
    return payload


def _latest_run_dir(job_id: str) -> Path | None:
    root = JOBS_ROOT / job_id
    if not root.exists() or not root.is_dir():
        return None
    runs = [p for p in root.iterdir() if p.is_dir()]
    return sorted(runs, key=lambda p: p.name)[-1] if runs else None


def _find_duplicate(application_fingerprint: str) -> Path | None:
    if not JOBS_ROOT.exists():
        return None
    for app_path in sorted(JOBS_ROOT.glob("*/*/application.json")):
        if any(part.startswith("_") for part in app_path.relative_to(JOBS_ROOT).parts):
            continue
        app = _read_json(app_path)
        if app.get("application_fingerprint") == application_fingerprint:
            return app_path.parent
    return None


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
        receipt = _read_json(latest / "receipt.json")
        state = str(state_obj.get("state") or "draft").lower()
        if state not in VALID_STATES:
            state = "draft"
        items.append(
            {
                "job_id": str(app.get("job_id") or job_root.name),
                "slug": f"{job_root.name}/{latest.name}",
                "title": app.get("title") or job_root.name,
                "employer": app.get("employer"),
                "role_url": app.get("role_url"),
                "deadline": app.get("deadline"),
                "timezone": app.get("timezone"),
                "deadline_utc": app.get("deadline_utc"),
                "channel": app.get("channel"),
                "priority": app.get("priority"),
                "state": state,
                "fit_score": app.get("fit_score"),
                "matched_keywords": app.get("matched_keywords"),
                "application_fingerprint": app.get("application_fingerprint"),
                "receipt_status": receipt.get("status") or "missing",
                "updated_utc": state_obj.get("updated_utc") or state_obj.get("generated_utc"),
                "run_dir": str(latest),
            }
        )

    counts: dict[str, int] = {}
    for item in items:
        state = str(item.get("state") or "draft")
        counts[state] = counts.get(state, 0) + 1

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
    queue_jsonl.write_text("\n".join(json.dumps(x, sort_keys=True) for x in items) + ("\n" if items else ""), encoding="utf-8")
    return payload


def _approve(job_id: str) -> dict[str, Any]:
    latest = _latest_run_dir(job_id)
    if latest is None:
        return {"ok": False, "error": f"job {job_id} not found"}

    changed_utc = _now_iso()
    state_path = latest / "approval_state.json"
    state = _read_json(state_path)
    state.update(
        {
            "state": "approved",
            "approved_utc": changed_utc,
            "updated_utc": changed_utc,
            "submission_locked": True,
            "final_submit_gate": FINAL_SUBMIT_GATE_TEXT,
        }
    )
    _write_json(state_path, state)

    receipt_path = latest / "receipt.json"
    receipt = _read_json(receipt_path)
    if receipt:
        receipt["package_review_status"] = "approved"
        receipt["package_reviewed_utc"] = changed_utc
        receipt["status"] = "approved_not_submitted"
        receipt["external_submission"] = {
            "status": "not_submitted",
            "confirmation_id": None,
            "submitted_utc": None,
            "receipt_source": None,
        }
        receipt["artifact_sha256"] = {
            path.name: _sha256(path)
            for path in sorted(latest.iterdir())
            if path.is_file() and path.name not in {"manifest.sha256.json", "receipt.json"}
        }
        _write_json(receipt_path, receipt)

    _write_manifest(latest)
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
    metric_text = " ".join(f"{key}:{value}" for key, value in metrics.items()) if isinstance(metrics, dict) else ""
    return f"{resume_text}\n{metric_text}\n{' '.join(package_names)}"


def _select_roles(
    roles: list[dict[str, Any]],
    resume_blob: str,
    min_score: float,
    limit: int,
    *,
    deadline_ranked: bool = False,
    now: datetime | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for role in roles:
        deadline = _deadline_evaluation(role, now=now)
        if deadline_ranked and not deadline.get("eligible"):
            excluded.append(
                {
                    "job_id": _safe_slug(str(role.get("id") or role.get("title") or "job")),
                    "deadline_status": deadline.get("status"),
                    "reason": deadline.get("reason"),
                }
            )
            continue
        score, matched = _role_score(role, resume_blob)
        if score < min_score:
            continue
        row = dict(role)
        row["_fit_score"] = score
        row["_matched_keywords"] = matched
        row["_deadline_evaluation"] = deadline
        selected.append(row)

    if deadline_ranked:
        selected.sort(
            key=lambda row: (
                str((row.get("_deadline_evaluation") or {}).get("deadline_utc") or "9999"),
                -float(row.get("_fit_score", 0.0)),
                _safe_slug(str(row.get("id") or "")),
            )
        )
    else:
        selected.sort(
            key=lambda row: (-float(row.get("_fit_score", 0.0)), _safe_slug(str(row.get("id") or "")))
        )
    return selected[: max(1, limit)], excluded


def _build_role_package(
    role: dict[str, Any],
    profile: dict[str, Any],
    resume_text: str,
    run_stamp: str,
    *,
    allow_duplicate: bool = False,
) -> dict[str, Any]:
    job_id = _safe_slug(str(role.get("id") or role.get("title") or "job"))
    matched = role.get("_matched_keywords") if isinstance(role.get("_matched_keywords"), list) else []
    metadata = _role_metadata(role, profile)
    deadline = role.get("_deadline_evaluation")
    if not isinstance(deadline, dict):
        deadline = _deadline_evaluation(role)
    candidate = _candidate_payload(profile)
    application_fingerprint = _application_fingerprint(role, candidate)
    duplicate = _find_duplicate(application_fingerprint)
    if duplicate is not None and not allow_duplicate:
        return {
            "built": False,
            "job_id": job_id,
            "title": role.get("title"),
            "application_fingerprint": application_fingerprint,
            "duplicate_of": str(duplicate),
            "reason": "duplicate_application_fingerprint",
        }

    generated_utc = _now_iso()
    safe_resume = _sanitize_employment_text(resume_text, profile)
    interest_text = _role_specific_interest(role, profile, matched)
    cover_letter = _cover_letter(role, profile, interest_text)
    linkedin_intro = _linkedin_intro(role, profile)
    submit_howto = _submit_howto(role, profile, metadata)

    app_payload: dict[str, Any] = {
        "schema_version": "2.0",
        "generated_utc": generated_utc,
        "job_id": job_id,
        "title": _sanitize_employment_text(role.get("title"), profile),
        "channel": _sanitize_employment_text(role.get("channel"), profile),
        "priority": _sanitize_employment_text(role.get("priority"), profile),
        "location_mode": _sanitize_employment_text(role.get("location_mode"), profile),
        "target_organizations": _sanitize_structure(role.get("target_organizations", []), profile),
        "fit_score": role.get("_fit_score"),
        "matched_keywords": _sanitize_structure(matched, profile),
        "submission_portal_hints": _sanitize_structure(role.get("submission_portal_hints", []), profile),
        "clearance_friendly": bool(role.get("clearance_friendly")),
        "candidate": candidate,
        "interest_text": interest_text,
        "application_fingerprint": application_fingerprint,
        "fingerprint_algorithm": "sha256",
        "fingerprint_version": FINGERPRINT_VERSION,
        "deadline_status": deadline.get("status"),
        "submission_policy": {
            "human_review_required": True,
            "manual_submit_required": True,
            "submission_locked": True,
            "final_submit_gate": FINAL_SUBMIT_GATE_TEXT,
            "factory_can_submit": False,
        },
    }
    app_payload.update(metadata)
    if deadline.get("deadline_utc"):
        app_payload["deadline_utc"] = deadline.get("deadline_utc")

    package_basis = {
        "application": {key: value for key, value in app_payload.items() if key != "generated_utc"},
        "cover_letter": cover_letter,
        "interest_text": interest_text,
        "linkedin_intro": linkedin_intro,
        "resume": safe_resume,
        "submit_howto": submit_howto,
    }
    package_fingerprint = _hash_payload(package_basis)
    app_payload["package_fingerprint"] = package_fingerprint

    run_dir = JOBS_ROOT / job_id / run_stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "application.json", app_payload)
    _write_text(run_dir / "cover_letter.md", cover_letter)
    _write_text(run_dir / "interest_text.md", interest_text)
    _write_text(run_dir / "linkedin_intro_message.md", linkedin_intro)
    _write_text(run_dir / "SUBMIT_HOWTO.md", submit_howto)
    _write_text(run_dir / "resume.md", safe_resume)

    state_payload = {
        "state": "draft",
        "generated_utc": generated_utc,
        "updated_utc": generated_utc,
        "fit_score": role.get("_fit_score"),
        "application_fingerprint": application_fingerprint,
        "notes": "Awaiting human review before submission.",
        "submission_locked": True,
        "final_submit_gate": FINAL_SUBMIT_GATE_TEXT,
    }
    _write_json(run_dir / "approval_state.json", state_payload)

    artifact_hashes = {
        path.name: _sha256(path)
        for path in sorted(run_dir.iterdir())
        if path.is_file()
    }
    receipt_payload = {
        "schema_version": "1.0",
        "receipt_type": "job_application_package",
        "status": "prepared_not_submitted",
        "prepared_utc": generated_utc,
        "job_id": job_id,
        "title": app_payload.get("title"),
        "employer": app_payload.get("employer"),
        "role_url": app_payload.get("role_url"),
        "application_fingerprint": application_fingerprint,
        "package_fingerprint": package_fingerprint,
        "fingerprint_algorithm": "sha256",
        "fingerprint_version": FINGERPRINT_VERSION,
        "duplicate_of": str(duplicate) if duplicate else None,
        "artifact_sha256": artifact_hashes,
        "package_review_status": "pending",
        "external_submission": {
            "status": "not_submitted",
            "confirmation_id": None,
            "submitted_utc": None,
            "receipt_source": None,
        },
        "final_submit_gate": {
            "required": True,
            "locked": True,
            "instruction": FINAL_SUBMIT_GATE_TEXT,
        },
    }
    _write_json(run_dir / "receipt.json", receipt_payload)
    manifest = _write_manifest(run_dir)
    return {
        "built": True,
        "job_id": job_id,
        "title": app_payload.get("title"),
        "fit_score": role.get("_fit_score"),
        "run_dir": str(run_dir),
        "application_fingerprint": application_fingerprint,
        "package_fingerprint": package_fingerprint,
        "manifest_entries": len(manifest),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build truthful resume-backed job application packages.")
    parser.add_argument("--job", default="", help="Only build a specific job id")
    parser.add_argument("--min-score", type=float, default=0.38)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--approve", default="", help="Approve package review for the latest run")
    parser.add_argument("--list", action="store_true", help="Print queue summary")
    parser.add_argument(
        "--deadline-ranked",
        action="store_true",
        help="Rank only roles with parseable, unexpired deadlines; missing or expired deadlines are excluded",
    )
    parser.add_argument("--as-of", default="", help="UTC/offset ISO timestamp for deterministic deadline ranking")
    parser.add_argument(
        "--allow-duplicate",
        action="store_true",
        help="Build another package with the same application fingerprint; never submits it",
    )
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
    contact_identity_ok, contact_identity_reason = _contact_identity_gate(profile)
    if not contact_identity_ok:
        print(f"[error] contact identity gate blocked package assembly: {contact_identity_reason}")
        print("[hint] verify the company mailbox in the application profile before preparing job packets")
        return 2
    resume_text = _load_resume_text()
    if not resume_text.strip():
        print(f"[error] missing resume markdown at {RESUME_MD_PATH}")
        print("[hint] run code/lumalinkedin_resume_engine_v1.py first")
        return 2
    resume_payload = _read_json(RESUME_JSON_PATH)
    resume_blob = _build_resume_blob(resume_text, resume_payload)

    candidate_roles = [
        role
        for role in roles
        if not args.job or _safe_slug(role.get("id", "")) == _safe_slug(args.job)
    ]
    if args.job and not candidate_roles:
        print(f"[error] job {args.job} not found")
        return 2

    as_of = None
    if args.as_of:
        try:
            as_of = _parse_datetime_value(args.as_of, "UTC")
        except ValueError as exc:
            print(f"[error] invalid --as-of value: {exc}")
            return 2

    selected_roles, deadline_exclusions = _select_roles(
        candidate_roles,
        resume_blob,
        args.min_score,
        args.limit,
        deadline_ranked=args.deadline_ranked,
        now=as_of,
    )

    if not selected_roles:
        if args.deadline_ranked:
            print("[error] no roles have a parseable, unexpired deadline and meet the score threshold")
            print(json.dumps({"deadline_exclusions": deadline_exclusions}, indent=2))
            return 2
        print("[info] no roles met the min-score threshold")
        queue = _refresh_queue_index()
        print(f"QUEUE={QUEUE_ROOT / 'index.json'}")
        print(f"TOTAL={queue.get('n_total', 0)}")
        return 0

    run_stamp = _stamp()
    results = [
        _build_role_package(
            role,
            profile,
            resume_text,
            run_stamp,
            allow_duplicate=args.allow_duplicate,
        )
        for role in selected_roles
    ]
    built_items = [item for item in results if item.get("built")]
    duplicate_items = [item for item in results if not item.get("built")]

    queue = _refresh_queue_index()
    summary = {
        "generated_utc": _now_iso(),
        "run_stamp": run_stamp,
        "min_score": args.min_score,
        "limit": args.limit,
        "deadline_ranked": args.deadline_ranked,
        "deadline_exclusions": deadline_exclusions,
        "built_count": len(built_items),
        "duplicate_skipped_count": len(duplicate_items),
        "built": built_items,
        "duplicates_skipped": duplicate_items,
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
    print(f"DUPLICATES_SKIPPED={len(duplicate_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
