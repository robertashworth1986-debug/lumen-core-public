"""Federal opportunity harvester.

Pulls grant/contract opportunities from public federal APIs and scores them
against the company profile in `data/company_profile.json`.

Sources (all free / public):
  * Grants.gov Search2 API   - https://api.grants.gov/v1/api/search2  (no key)
  * SBIR.gov solicitations   - https://api.www.sbir.gov/public/api/solicitations  (no key)
  * SAM.gov Opportunities    - https://api.sam.gov/opportunities/v2/search
                                                                (key OPTIONAL via env SAM_API_KEY or SAM_GOV_API_KEY)
  * SBA loan programs        - static catalog (no public opportunity API)

Output:
  out/opportunities/harvest_<UTC>.json   -- raw fetched records
  out/opportunities/ranked.json          -- scored + filtered "perfect-fit" set
  out/opportunities/queue.jsonl          -- approval queue (one record per line)

Run:
  python code/opportunity_harvester.py [--limit 1000] [--min-score 0.45]

Honest constraints:
  * Federal grant/contract submission requires HUMAN login + e-sign.
    This harvester drafts a pre-filled package and queues it; it never
    auto-submits to grants.gov / sam.gov / agency portals.
  * SBA loans are not API-applyable; bank-mediated. We surface program
    details only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from application_context_resolver import load_application_profile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "out" / "opportunities"
OUT.mkdir(parents=True, exist_ok=True)

KNOWN_ENV_FILES = [
    ROOT / "config" / "luma_live_keys.env",
    ROOT / "code" / "execution" / "config" / "luma_live_keys.env",
]

PROFILE_PATH = DATA / "company_profile.json"
CATALOG_PATH = DATA / "grant_catalog.json"
SKIP_AUTOFILL_PATH = ROOT / "out" / "ops" / "skips_grant_autofill" / "skips_grant_autofill_latest.json"
SAM_GOV_OPPORTUNITIES_API = "https://api.sam.gov/opportunities/v2/search"
SBIR_GOV_SOLICITATIONS_API = "https://api.www.sbir.gov/public/api/solicitations"
SOURCE_HEALTH_PATH = OUT / "source_health_latest.json"
SAM_ROTATION_CONTROL_PATH = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json"
)

# Profile keyword pool (built once from profile + catalog) drives fit scoring.
DEFAULT_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "ml", "forecasting",
    "anomaly detection", "regime", "harmonic", "phase-locked", "calibration",
    "uncertainty", "time series", "deep tech", "infrastructure",
    "energy", "grid", "electricity", "weather", "climate", "earth observation",
    "data analytics", "decision support", "real-time", "explainable",
    "small business", "sbir", "sttr", "phase i", "phase ii",
    "operational", "scada", "resilience", "early warning", "novel algorithm",
    "evidence", "reproducibility", "benchmark",
]

# NAICS codes plausibly applicable to LumenCore / sole-prop deep-tech AI.
PROFILE_NAICS = [
    "541511",  # Custom Computer Programming Services
    "541512",  # Computer Systems Design Services
    "541690",  # Other Scientific & Technical Consulting
    "541714",  # Research & Development - Biotech / Physical / Engineering
    "541715",  # R&D - Physical, Engineering, Life Sciences
    "518210",  # Data Processing, Hosting
]


def _profile_keywords(profile: dict[str, Any]) -> list[str]:
    company = profile.get("company", {}) if isinstance(profile, dict) else {}
    capabilities = profile.get("company_capabilities", []) if isinstance(profile, dict) else []
    identifiers = profile.get("identifiers", {}) if isinstance(profile, dict) else {}
    federal = profile.get("federal_readiness", {}) if isinstance(profile, dict) else {}

    seeds: list[str] = []
    for value in [
        company.get("legal_name"),
        company.get("dba"),
        company.get("website"),
        company.get("sam_gov_status"),
        federal.get("status"),
        federal.get("runtime_mode"),
    ]:
        txt = str(value or "").strip()
        if txt:
            seeds.append(txt)

    if isinstance(capabilities, list):
        for row in capabilities:
            txt = str(row or "").strip()
            if txt:
                seeds.append(txt)

    patent_numbers = identifiers.get("patent_numbers") if isinstance(identifiers, dict) else []
    if isinstance(patent_numbers, list):
        for token in patent_numbers:
            txt = str(token or "").strip()
            if txt:
                seeds.append(txt)

    normalized: list[str] = []
    seen: set[str] = set()
    for value in seeds:
        key = _normalize(value)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(value)
    return normalized


# --------------------------- HTTP helpers --------------------------------- #


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        key = k.strip()
        value = v.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def _hydrate_known_env_files() -> None:
    for env_file in KNOWN_ENV_FILES:
        _load_env_file(env_file)


def _first_nonempty_env(*names: str) -> tuple[str | None, str | None]:
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return name, value
    return None, None


def _safe_error_text(error: Exception) -> str:
    text = str(error)
    text = re.sub(
        r"([?&](?:api_key|apikey|token)=)[^&\s]+",
        r"\1[REDACTED]",
        text,
        flags=re.IGNORECASE,
    )
    for name in ("SAM_API_KEY", "SAM_GOV_API_KEY", "DATA_GOV_API_KEY_PRIMARY"):
        secret = (os.environ.get(name) or "").strip()
        if secret:
            text = text.replace(secret, "[REDACTED]")
            text = text.replace(urllib.parse.quote(secret), "[REDACTED]")
    return text


def _stable_sha256(payload: Any) -> str:
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _source_diagnostic(
    source: str,
    endpoint: str,
    *,
    credential_required: bool = False,
    credential_configured: bool = False,
) -> dict[str, Any]:
    return {
        "source": source,
        "endpoint": endpoint,
        "status": "NOT_RUN",
        "records": 0,
        "request_attempts": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "live_response_observed": False,
        "response_shape_valid": False,
        "credential_required": credential_required,
        "credential_configured": credential_configured,
        "http_status": None,
        "response_body_published": False,
        "secret_value_published": False,
    }


def _classify_fetch_error(error: Exception, *, credential_required: bool) -> dict[str, Any]:
    status = int(error.code) if isinstance(error, urllib.error.HTTPError) else None
    body_bytes: int | None = None
    if isinstance(error, urllib.error.HTTPError):
        try:
            body_bytes = len(error.read(2_000_000))
        except Exception:  # noqa: BLE001 - only the byte count is retained
            body_bytes = None

    if status in {401, 403} and credential_required:
        classification = "CREDENTIAL_REJECTED_OR_UNAUTHORIZED"
    elif status == 404 and body_bytes == 0:
        classification = "HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE"
    elif status == 404:
        classification = "HTTP_404_RESPONSE_INCONCLUSIVE"
    elif status == 429:
        classification = "RATE_LIMITED_INCONCLUSIVE"
    elif status is not None and status >= 500:
        classification = "UPSTREAM_HTTP_FAILURE_INCONCLUSIVE"
    elif isinstance(error, json.JSONDecodeError):
        classification = "INVALID_JSON_RESPONSE_INCONCLUSIVE"
    elif isinstance(error, (urllib.error.URLError, TimeoutError)):
        classification = "NETWORK_FAILURE_INCONCLUSIVE"
    else:
        classification = "REQUEST_FAILURE_INCONCLUSIVE"
    return {
        "status": classification,
        "http_status": status,
        "error_type": type(error).__name__,
        "error_body_bytes": body_bytes,
        "response_body_published": False,
        "secret_value_published": False,
    }


def _set_diagnostic(target: dict[str, Any] | None, payload: dict[str, Any]) -> None:
    if target is None:
        return
    target.clear()
    target.update(payload)


def _read_sam_rotation_status(path: Path = SAM_ROTATION_CONTROL_PATH) -> dict[str, Any]:
    if not path.is_file():
        return {
            "status": "ROTATION_CONTROL_NOT_AVAILABLE",
            "generated_utc": None,
            "rotation_verified": False,
            "deadline_state": "UNVERIFIED",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "ROTATION_CONTROL_UNREADABLE",
            "generated_utc": None,
            "rotation_verified": False,
            "deadline_state": "UNVERIFIED",
        }
    if payload.get("schema") != "lumencore.sam_public_credential_rotation_control.v1":
        return {
            "status": "ROTATION_CONTROL_SCHEMA_UNSUPPORTED",
            "generated_utc": payload.get("generated_utc"),
            "rotation_verified": False,
            "deadline_state": "UNVERIFIED",
        }
    return {
        "status": payload.get("status"),
        "generated_utc": payload.get("generated_utc"),
        "rotation_verified": bool(payload.get("rotation_verified")),
        "deadline_state": (payload.get("deadline") or {}).get("state"),
    }


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _atomic_write_json(path: Path, payload: Any) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, default=str) + "\n")


def _http_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict | None = None,
    headers: dict | None = None,
    timeout: float = 20.0,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    h = {"User-Agent": "LumenCore-Opportunity-Harvester/1.0",
         "Accept": "application/json"}
    if payload is not None:
        h["Content-Type"] = "application/json"
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def _extract_deadline_note_date(note: str) -> str:
    text = str(note or "")
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),\s*(20\d{2})", text)
    if m:
        month_name = _normalize(m.group(1))
        month_map = {
            "jan": 1,
            "january": 1,
            "feb": 2,
            "february": 2,
            "mar": 3,
            "march": 3,
            "apr": 4,
            "april": 4,
            "may": 5,
            "jun": 6,
            "june": 6,
            "jul": 7,
            "july": 7,
            "aug": 8,
            "august": 8,
            "sep": 9,
            "sept": 9,
            "september": 9,
            "oct": 10,
            "october": 10,
            "nov": 11,
            "november": 11,
            "dec": 12,
            "december": 12,
        }
        month = month_map.get(month_name)
        if month:
            day = int(m.group(2))
            year = int(m.group(3))
            return f"{month:02d}/{day:02d}/{year:04d}"
    return datetime.now(timezone.utc).strftime("%m/%d/%Y")


def fetch_skip_grants() -> list[dict[str, Any]]:
    if not SKIP_AUTOFILL_PATH.exists():
        return []

    try:
        payload = json.loads(SKIP_AUTOFILL_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

    opportunities = payload.get("opportunity_variants", []) if isinstance(payload, dict) else []
    use_of_funds = payload.get("use_of_funds_templates", {}) if isinstance(payload, dict) else {}
    business_profile = payload.get("business_profile", {}) if isinstance(payload, dict) else {}
    if not isinstance(opportunities, list):
        return []

    out: list[dict[str, Any]] = []
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        oid = str(item.get("opportunity_id") or "skip-opportunity")
        title = str(item.get("title") or oid)
        fit = _normalize(item.get("fit"))
        budget_key = str(item.get("recommended_budget_template") or "")
        budget_map = use_of_funds.get(budget_key, {}) if isinstance(use_of_funds, dict) else {}
        budget_total = 0.0
        if isinstance(budget_map, dict):
            for val in budget_map.values():
                budget_total += float(val) if str(val).replace(".", "", 1).isdigit() else 0.0

        out.append(
            {
                "source": "skip",
                "id": f"SKIP-{_normalize(oid).replace(' ', '_')}",
                "number": f"SKIP-{_normalize(oid).replace(' ', '_')}",
                "title": title,
                "agency": "Hello Skip Funding Network",
                "status": "posted",
                "open_date": datetime.now(timezone.utc).strftime("%m/%d/%Y"),
                "close_date": _extract_deadline_note_date(str(item.get("deadline_note") or "")),
                "doc_type": "SKIP Grant",
                "url": str(business_profile.get("website") or "https://helloskip.com/"),
                "topics": [
                    str(item.get("autofill_angle") or ""),
                    str(item.get("paste_ready_answer") or ""),
                    "autonomous ai grant execution",
                ],
                "raw": {
                    "awardCeiling": budget_total,
                    "eligibility_required_tags": item.get("eligibility_required_tags", []),
                    "fit": fit,
                },
            }
        )
    return out


# --------------------------- Sources -------------------------------------- #


def fetch_grants_gov(
    rows: int = 200,
    keywords: list[str] | None = None,
    *,
    diagnostic: dict[str, Any] | None = None,
) -> list[dict]:
    """Grants.gov Search2 API. No key. Pagination via startRecordNum."""
    keywords = keywords or ["small business", "sbir", "ai", "data", "energy"]
    health = _source_diagnostic(
        "grants.gov",
        "GRANTS_GOV_SEARCH2_API",
    )
    out: list[dict] = []
    seen: set[str] = set()
    for kw in keywords:
        health["request_attempts"] += 1
        try:
            payload = {
                "rows": rows,
                "keyword": kw,
                "oppStatuses": "forecasted|posted",
            }
            resp = _http_json(
                "https://api.grants.gov/v1/api/search2",
                method="POST",
                payload=payload,
            )
            hits = (resp.get("data", {}) or {}).get("oppHits") if isinstance(resp, dict) else None
            if not isinstance(hits, list):
                health["failed_requests"] += 1
                health["status"] = "INVALID_RESPONSE_SHAPE_INCONCLUSIVE"
                continue
            health["successful_requests"] += 1
            health["live_response_observed"] = True
            health["response_shape_valid"] = True
            for h in hits:
                oid = str(h.get("id") or h.get("number") or "")
                if not oid or oid in seen:
                    continue
                seen.add(oid)
                out.append({
                    "source": "grants.gov",
                    "id": oid,
                    "number": h.get("number"),
                    "title": h.get("title"),
                    "agency": h.get("agency") or h.get("agencyCode"),
                    "status": h.get("oppStatus"),
                    "open_date": h.get("openDate"),
                    "close_date": h.get("closeDate"),
                    "doc_type": h.get("docType"),
                    "url": f"https://www.grants.gov/search-results-detail/{oid}",
                    "raw": h,
                })
        except Exception as error:  # noqa: BLE001
            health["failed_requests"] += 1
            health.update(_classify_fetch_error(error, credential_required=False))
            print(f"[grants.gov] keyword={kw!r} error: {_safe_error_text(error)}")
    health["records"] = len(out)
    if health["successful_requests"] and health["failed_requests"]:
        health["status"] = "PARTIAL_LIVE_RESULTS_WITH_REQUEST_FAILURES"
    elif health["successful_requests"]:
        health["status"] = (
            "LIVE_RESPONSES_RECORDS_PRESENT" if out else "LIVE_RESPONSES_ZERO_RECORDS"
        )
    elif health["status"] == "NOT_RUN":
        health["status"] = "ALL_REQUESTS_FAILED_INCONCLUSIVE"
    _set_diagnostic(diagnostic, health)
    return out


def fetch_sbir_gov(
    keywords: list[str] | None = None,
    *,
    diagnostic: dict[str, Any] | None = None,
) -> list[dict]:
    """Fetch one bounded page of open SBIR.gov solicitations.

    A single open-page request avoids turning an upstream failure into a burst of
    keyword retries. The shared scoring stage performs keyword filtering locally.
    """
    del keywords
    health = _source_diagnostic(
        "sbir.gov",
        "SBIR_GOV_PUBLIC_SOLICITATIONS_API",
    )
    out: list[dict] = []
    seen: set[str] = set()
    health["request_attempts"] = 1
    try:
        resp = _http_json(f"{SBIR_GOV_SOLICITATIONS_API}?open=1&rows=50")
        items = resp if isinstance(resp, list) else resp.get("results") if isinstance(resp, dict) else None
        if not isinstance(items, list):
            health["failed_requests"] = 1
            health["status"] = "INVALID_RESPONSE_SHAPE_INCONCLUSIVE"
            _set_diagnostic(diagnostic, health)
            return []
        health["successful_requests"] = 1
        health["live_response_observed"] = True
        health["response_shape_valid"] = True
        for s in items:
            oid = str(
                s.get("solicitation_number")
                or s.get("solicitation_id")
                or s.get("id")
                or ""
            )
            if not oid or oid in seen:
                continue
            seen.add(oid)
            out.append(
                {
                    "source": "sbir.gov",
                    "id": oid,
                    "title": s.get("solicitation_title") or s.get("title"),
                    "agency": s.get("agency"),
                    "status": s.get("current_status") or s.get("status"),
                    "open_date": s.get("open_date"),
                    "close_date": s.get("close_date"),
                    "doc_type": "SBIR/STTR",
                    "url": s.get("solicitation_agency_url")
                    or s.get("solicitation_link")
                    or s.get("url"),
                    "topics": s.get("solicitation_topics")
                    or s.get("topics")
                    or [],
                    "raw": s,
                }
            )
    except Exception as error:  # noqa: BLE001
        health["failed_requests"] = 1
        health.update(_classify_fetch_error(error, credential_required=False))
        print(f"[sbir.gov] open solicitations unavailable: {_safe_error_text(error)}")
    health["records"] = len(out)
    if health["successful_requests"]:
        health["status"] = "LIVE_RESPONSE_RECORDS_PRESENT" if out else "LIVE_RESPONSE_ZERO_RECORDS"
    _set_diagnostic(diagnostic, health)
    return out


def enrich_grants_gov_synopsis(records: list[dict], top_n: int = 100) -> int:
    """Fetch full opportunity detail for top_n grants.gov records to enable
    body-text scoring. Returns number enriched."""
    enriched = 0
    for rec in records[:top_n]:
        if rec.get("source") != "grants.gov":
            continue
        oid = rec.get("id")
        if not oid:
            continue
        try:
            resp = _http_json(
                "https://api.grants.gov/v1/api/fetchOpportunity",
                method="POST",
                payload={"opportunityId": int(oid)},
                timeout=15.0,
            )
            data = resp.get("data", {}) or {}
            syn = data.get("synopsis", {}) or {}
            rec.setdefault("raw", {})["synopsis"] = syn.get("synopsisDesc") or ""
            rec["raw"]["awardCeiling"] = syn.get("awardCeiling")
            rec["raw"]["awardFloor"] = syn.get("awardFloor")
            rec["raw"]["expectedAwards"] = syn.get("numberOfAwards")
            enriched += 1
        except Exception as e:  # noqa: BLE001
            print(f"[grants.gov detail] id={oid} error: {e}")
        time.sleep(0.3)
    return enriched


def fetch_sam_gov(
    api_key: str | None,
    *,
    days: int = 60,
    limit: int = 200,
    diagnostic: dict[str, Any] | None = None,
) -> list[dict]:
    """SAM.gov Opportunities API. Requires api_key (you can request one
    from your active SAM.gov registration). Returns [] if no key."""
    health = _source_diagnostic(
        "sam.gov",
        "SAM_GET_OPPORTUNITIES_PUBLIC_API_V2",
        credential_required=True,
        credential_configured=bool(api_key),
    )
    health["credential_rotation_control"] = _read_sam_rotation_status()
    if not api_key:
        health["status"] = "CREDENTIAL_NOT_CONFIGURED"
        _set_diagnostic(diagnostic, health)
        return []
    end = datetime.now(timezone.utc).strftime("%m/%d/%Y")
    start_dt = datetime.now(timezone.utc).timestamp() - days * 86400
    start = datetime.fromtimestamp(start_dt, timezone.utc).strftime("%m/%d/%Y")
    out: list[dict] = []

    # Fail once when the upstream service is unavailable instead of spending one
    # request per NAICS code on the same infrastructure error.
    health_qs = urllib.parse.urlencode({
        "api_key": api_key,
        "limit": 1,
        "offset": 0,
        "postedFrom": start,
        "postedTo": end,
    })
    health["request_attempts"] = 1
    try:
        response = _http_json(f"{SAM_GOV_OPPORTUNITIES_API}?{health_qs}")
        if not (
            isinstance(response, dict)
            and isinstance(response.get("opportunitiesData"), list)
            and isinstance(response.get("totalRecords"), int)
        ):
            health["failed_requests"] = 1
            health["status"] = "INVALID_RESPONSE_SHAPE_INCONCLUSIVE"
            _set_diagnostic(diagnostic, health)
            return []
        health["successful_requests"] = 1
        health["live_response_observed"] = True
        health["response_shape_valid"] = True
        health["health_query_total_records"] = response.get("totalRecords")
    except Exception as error:  # noqa: BLE001
        health["failed_requests"] = 1
        health.update(_classify_fetch_error(error, credential_required=True))
        print(
            "[sam.gov] public opportunities API unavailable; "
            f"use signed-in SAM.gov search: {_safe_error_text(error)}"
        )
        _set_diagnostic(diagnostic, health)
        return []

    seen: set[str] = set()
    for naics in PROFILE_NAICS:
        health["request_attempts"] += 1
        try:
            qs = urllib.parse.urlencode({
                "api_key": api_key,
                "limit": min(limit, 1000),
                "offset": 0,
                "postedFrom": start,
                "postedTo": end,
                "ncode": naics,
                # Presolicitation, solicitation, combined, and sources sought.
                "ptype": ["p", "o", "k", "r"],
            }, doseq=True)
            url = f"{SAM_GOV_OPPORTUNITIES_API}?{qs}"
            resp = _http_json(url)
            opportunities = resp.get("opportunitiesData") if isinstance(resp, dict) else None
            if not isinstance(opportunities, list) or not isinstance(resp.get("totalRecords"), int):
                health["failed_requests"] += 1
                continue
            health["successful_requests"] += 1
            for o in opportunities:
                notice_id = str(o.get("noticeId") or "").strip()
                if not notice_id or notice_id in seen:
                    continue
                seen.add(notice_id)
                out.append({
                    "source": "sam.gov",
                    "id": notice_id,
                    "title": o.get("title"),
                    "agency": o.get("fullParentPathName"),
                    "status": o.get("type"),
                    "open_date": o.get("postedDate"),
                    "close_date": o.get("responseDeadLine"),
                    "doc_type": o.get("type"),
                    "url": o.get("uiLink"),
                    "naics": naics,
                    "raw": o,
                })
        except Exception as error:  # noqa: BLE001
            health["failed_requests"] += 1
            print(f"[sam.gov] naics={naics} error: {_safe_error_text(error)}")
    health["records"] = len(out)
    if health["failed_requests"]:
        health["status"] = (
            "PARTIAL_LIVE_RESULTS_WITH_QUERY_FAILURES"
            if out
            else "LIVE_HEALTH_QUERY_TARGETED_QUERIES_INCONCLUSIVE"
        )
    else:
        health["status"] = (
            "LIVE_AUTHENTICATED_RECORDS_PRESENT"
            if out
            else "LIVE_AUTHENTICATED_ZERO_MATCHES"
        )
    _set_diagnostic(diagnostic, health)
    return out


# --------------------------- Scoring --------------------------------------- #


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower()).strip()


def score_fit(rec: dict, keywords: list[str]) -> tuple[float, list[str]]:
    blob_parts: list[str] = []
    for k in ("title", "agency", "doc_type", "status"):
        v = rec.get(k)
        if v:
            blob_parts.append(str(v))
    raw = rec.get("raw") or {}
    for k in ("description", "synopsis", "topic_description", "subject"):
        v = raw.get(k)
        if v:
            blob_parts.append(str(v))
    for t in rec.get("topics") or []:
        if isinstance(t, dict):
            blob_parts.append(str(t.get("topic_title") or t.get("title") or ""))
            blob_parts.append(str(t.get("topic_description") or ""))
        else:
            blob_parts.append(str(t))
    blob = _normalize(" ".join(blob_parts))

    matches: list[str] = []
    score = 0.0
    for kw in keywords:
        kwn = _normalize(kw)
        if not kwn:
            continue
        if kwn in blob:
            matches.append(kw)
            # Multi-word keywords weighted higher
            score += 1.5 if " " in kwn else 1.0

    # Eligibility bumps for sole-prop / small-business friendly programs
    if re.search(r"\bsbir|sttr|small\s+business\b", blob):
        score += 3.0
    if "phase i" in blob:
        score += 1.5
    if "rolling" in blob or "open topic" in blob:
        score += 1.0

    # Normalize to 0..1 against rough ceiling
    # (titles alone rarely score above 6; full synopses can hit 12+)
    norm = min(1.0, score / 6.0)
    return norm, matches


def is_actionable(rec: dict) -> bool:
    """Filter out closed / archived / unfundable rows + agency noise."""
    status = _normalize(str(rec.get("status") or ""))
    if status in {"closed", "archived", "cancelled", "canceled"}:
        return False

    # Profile exclusion: State Dept missions, PEPFAR, narrow-foreign,
    # K-12 education — high keyword overlap, zero fit for solo-prop AI.
    agency = _normalize(str(rec.get("agency") or ""))
    title = _normalize(str(rec.get("title") or ""))
    EXCLUDE_AGENCY = (
        "u.s. mission", "u.s.embassy", "embassy ", "consulate",
        "pepfar", "peace corps", "fulbright",
        "office of overseas schools",
    )
    if any(x in agency for x in EXCLUDE_AGENCY):
        return False
    EXCLUDE_TITLE = (
        "alumni engagement", "freedom 250", "youth ambassador",
        "k-12", "fulbright",
    )
    if any(x in title for x in EXCLUDE_TITLE):
        return False

    cd = rec.get("close_date")
    if cd:
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                dt = datetime.strptime(cd[:19] if "T" in cd else cd, fmt)
                return dt.timestamp() >= time.time() - 7 * 86400
            except (ValueError, TypeError):
                continue
    return True


# --------------------------- Pipeline -------------------------------------- #


def harvest(min_score: float = 0.30, limit: int = 5000) -> dict:
    _hydrate_known_env_files()
    profile = load_application_profile()
    keywords = list(DEFAULT_KEYWORDS)
    keywords.extend(_profile_keywords(profile))
    keywords = list(dict.fromkeys(k for k in keywords if str(k or "").strip()))
    sam_env_name, sam_key = _first_nonempty_env(
        "SAM_API_KEY",
        "SAM_GOV_API_KEY",
        "DATA_GOV_API_KEY_PRIMARY",
    )

    grants_health: dict[str, Any] = {}
    sbir_health: dict[str, Any] = {}
    sam_health: dict[str, Any] = {}

    print("[harvest] grants.gov ...")
    g = fetch_grants_gov(rows=200, keywords=keywords[:8], diagnostic=grants_health)
    print(f"  {len(g)} records")

    print("[harvest] sbir.gov ...")
    s = fetch_sbir_gov(keywords[:6], diagnostic=sbir_health)
    print(f"  {len(s)} records")

    sam_status = f"key set via {sam_env_name}" if sam_key else "NO KEY -- skipping"
    print(f"[harvest] sam.gov ({sam_status}) ...")
    sm = fetch_sam_gov(sam_key, days=60, limit=200, diagnostic=sam_health)
    print(f"  {len(sm)} records")

    print("[harvest] skip grants (local autofill feed) ...")
    sk = fetch_skip_grants()
    print(f"  {len(sk)} records")

    raw = (g + s + sm + sk)[:limit]
    print(f"[harvest] total raw: {len(raw)}")

    # First-pass score on titles only, take top 150 for synopsis enrichment
    pre: list[tuple[float, dict]] = []
    for rec in raw:
        if not is_actionable(rec):
            continue
        sc, _ = score_fit(rec, keywords)
        pre.append((sc, rec))
    pre.sort(key=lambda x: x[0], reverse=True)
    enrich_pool = [r for _, r in pre[:150]]

    print(f"[harvest] enriching synopses for top {len(enrich_pool)} ...")
    n_enriched = enrich_grants_gov_synopsis(enrich_pool, top_n=150)
    print(f"  enriched {n_enriched}")

    scored: list[dict] = []
    for rec in raw:
        if not is_actionable(rec):
            continue
        score, matches = score_fit(rec, keywords)
        if score < min_score:
            continue
        rec["_fit_score"] = round(score, 4)
        rec["_keyword_matches"] = matches
        scored.append(rec)

    scored.sort(key=lambda r: r["_fit_score"], reverse=True)

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")

    skip_health = _source_diagnostic("local_skip_feed", "LOCAL_AUTOFILL_ARTIFACT")
    skip_health.update(
        {
            "status": "LOCAL_RECORDS_PRESENT" if sk else "LOCAL_ZERO_RECORDS",
            "records": len(sk),
            "request_attempts": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "live_response_observed": False,
            "response_shape_valid": True,
        }
    )
    source_health_payload: dict[str, Any] = {
        "schema": "lumencore.opportunity_source_health.v1",
        "generated_utc": now.isoformat(),
        "sources": {
            "grants_gov": grants_health,
            "sbir_gov": sbir_health,
            "sam_gov": sam_health,
            "local_skip_feed": skip_health,
        },
        "claim_boundary": (
            "Source status describes only this bounded harvest attempt. Zero records do not prove "
            "that no opportunities exist, and an inconclusive API response does not prove outage, "
            "maintenance, credential validity, or credential rejection."
        ),
    }
    source_health_payload["control_sha256"] = _stable_sha256(source_health_payload)

    raw_path = OUT / f"harvest_{stamp}.json"
    raw_payload: dict[str, Any] = {
        "schema": "lumencore.opportunity_harvest.v2",
        "harvested_utc": now.isoformat(),
        "totals": {"grants_gov": len(g), "sbir_gov": len(s), "sam_gov": len(sm), "skip": len(sk)},
        "source_health": source_health_payload["sources"],
        "records": raw,
    }
    raw_payload["control_sha256"] = _stable_sha256(raw_payload)
    _atomic_write_json(raw_path, raw_payload)
    _atomic_write_json(SOURCE_HEALTH_PATH, source_health_payload)

    ranked_path = OUT / "ranked.json"
    ranked_payload = {
        "schema": "lumencore.opportunity_ranked.v2",
        "generated_utc": now.isoformat(),
        "min_score": min_score,
        "total_actionable": len(scored),
        "source_health": source_health_payload["sources"],
        "source_health_control_sha256": source_health_payload["control_sha256"],
        "harvest_control_sha256": raw_payload["control_sha256"],
        "records": scored,
    }
    ranked_payload["control_sha256"] = _stable_sha256(ranked_payload)
    _atomic_write_json(ranked_path, ranked_payload)

    queue_path = OUT / "queue.jsonl"
    queue_lines = []
    for rec in scored[:200]:
        queue_lines.append(
            json.dumps({
                "id": rec.get("id"),
                "source": rec.get("source"),
                "title": rec.get("title"),
                "agency": rec.get("agency"),
                "close_date": rec.get("close_date"),
                "fit_score": rec["_fit_score"],
                "matches": rec["_keyword_matches"],
                "url": rec.get("url"),
                "approval_state": "draft",
            }, default=str)
        )
    _atomic_write_text(queue_path, "\n".join(queue_lines) + ("\n" if queue_lines else ""))

    print(f"[harvest] {len(scored)} actionable >= score {min_score}")
    print(f"[harvest] raw  -> {raw_path}")
    print(f"[harvest] rank -> {ranked_path}")
    print(f"[harvest] queue-> {queue_path}")
    print(f"[harvest] health-> {SOURCE_HEALTH_PATH}")
    return ranked_payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=float, default=0.30)
    ap.add_argument("--limit", type=int, default=5000)
    args = ap.parse_args()
    harvest(min_score=args.min_score, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
