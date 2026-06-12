"""
grant_application_factory.py
================================
Innovation #15 — End-to-end grant application factory.

Pipeline:
    1. Load grant catalog (data/grant_catalog.json)
    2. Load company profile (data/company_profile.json)
    3. Build the live evidence summary from the latest frozen run:
         master_universe_v2 / meta_router / hybrid_stacker /
         stacking_blender / ci_calibration / anomaly_scanner /
         regime_shift_scanner
    4. Score eligibility & topical fit per program
    5. Render section-by-section narrative (markdown + JSON) for each
       eligible program
    6. Write a draft package to:
         out/grants/<grant_id>/<utc>/{
             application.md
             application.json
             evidence_manifest.json
             eligibility_report.json
             cover_letter.md
             technical_volume.md
             commercialization_plan.md
             budget.json
             approval_state.json   ("draft" until UI flips it to "approved")
             manifest.sha256.json
         }
    7. Update queue index at out/grants/_queue/index.json so the API/UI
       can list all draft / approved / submitted apps.

CLI:
    python code/grant_application_factory.py
        -> generates drafts for every eligible program in the catalog

    python code/grant_application_factory.py --grant doe_sbir_phase_i_25_2
        -> only that program

    python code/grant_application_factory.py --approve doe_sbir_phase_i_25_2
        -> flips approval_state to "approved" and copies bundle to
           out/grants/_approved/<grant_id>/<utc>/

    python code/grant_application_factory.py --list
        -> prints queue summary
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from functools import lru_cache
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from application_context_resolver import load_application_profile

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"
GRANTS = OUT / "grants"
QUEUE_DIR = GRANTS / "_queue"
APPROVED_DIR = GRANTS / "_approved"
LIVE_SOURCE_REGISTRY = ROOT / "config" / "live_source_registry.json"
DATASET_CATALOG_PATH = OUT / "dataset_catalog.json"
DATA_BREADTH_PROBE_PATH = OUT / "ops" / "data_breadth_runtime_probe_latest.json"
HUNTER_PROFILE_PATH = ROOT / "code" / "grants_profile_lumencore.json"
OPPORTUNITY_SCAN_PATH = QUEUE_DIR / "opportunity_scan.json"

GRANTS_GOV_SEARCH_API = "https://api.grants.gov/v1/api/search2"
GRANTS_GOV_FETCH_API = "https://api.grants.gov/v1/api/fetchOpportunity"
GRANTS_APPLICANT_SOAP_ENDPOINT = "https://ws07.grants.gov:443/grantsws-applicant/services/v2/ApplicantWebServicesSoapPort"
GRANTS_APPLICANT_SOAP_WSDL = "https://ws07.grants.gov:443/grantsws-applicant/services/v2/ApplicantWebServicesSoapPort?wsdl"
GRANTS_APPLICANT_SOAP_SERVICE_NAME = "ApplicantWebServices-V2.0"
GRANTS_APPLICANT_SOAP_PORT_NAME = "ApplicantWebServicesSoapPort"
SAM_GOV_OPPORTUNITIES_API = "https://api.sam.gov/opportunities/v2/search"

LAYER_ARTIFACTS = {
    "benchmark": lambda utc: OUT / "master_universe_v2" / utc / "summary.json",
    "meta_router": lambda utc: OUT / "meta_router" / utc / "eval.json",
    "hybrid_stacker": lambda utc: OUT / "hybrid_stacker" / utc / "eval.json",
    "stacking_blender": lambda utc: OUT / "stacking_blender" / utc / "eval.json",
    "ci_calibration": lambda utc: OUT / "ci_calibration" / utc / "summary.json",
    "anomaly_scanner": lambda utc: OUT / "anomaly_scanner" / utc / "summary.json",
    "regime_shift": lambda utc: OUT / "regime_shift_scanner" / utc / "summary.json",
}

DOMAIN_KEYWORD_HINTS = {
    "energy": {"eia", "eia930"},
    "grid": {"eia", "eia930"},
    "buildings": {"eia", "eia930"},
    "climate": {"noaa", "nasa", "usgs", "openaq"},
    "weather": {"noaa", "nasa", "openaq"},
    "earth": {"nasa", "noaa", "usgs", "openaq"},
    "ocean": {"noaa", "usgs"},
    "commodities": {"yf", "fred", "coingecko"},
    "financial": {"yf", "fred", "coingecko"},
    "macro": {"fred", "bls"},
    "labor": {"bls"},
    "employment": {"bls"},
    "autonomous": {"nasa", "noaa", "usgs"},
}

SECTOR_QUERY_HINTS = {
    "energy": ["energy sbir", "grid analytics grant", "doe energy data contract"],
    "energy_lab": ["nrel energy innovation", "doe eere funding", "clean energy sbir"],
    "weather": ["noaa sbir", "weather analytics grant", "climate resilience contract"],
    "space": ["nasa sbir", "earth science ai grant", "autonomous systems nasa"],
    "water": ["usgs water analytics", "water resilience grant", "flood forecasting contract"],
    "labor": ["bls data analytics", "workforce forecasting grant", "labor market ai"],
    "macro": ["economic forecasting grant", "federal macro data analytics"],
    "demographic": ["census data innovation grant", "population analytics contract"],
    "market_data": ["financial forecasting sbir", "risk analytics contract", "market intelligence grant"],
    "rates": ["interest rate forecasting", "macroeconomic decision support"],
    "air_quality": ["epa air quality analytics", "environmental anomaly detection"],
    "crypto_exec": ["digital asset compliance analytics", "fintech risk modeling"],
    "broker": ["trading infrastructure analytics", "financial resilience"],
    "federal_contracts": [
        "sam.gov contract opportunity",
        "federal acquisition contract",
        "broad agency announcement contract",
        "idiq research services",
    ],
    "federal_small_business": [
        "sba set-aside opportunity",
        "small business innovation research",
        "hubzone contract",
        "8(a) program opportunity",
    ],
}

SOURCE_QUERY_HINTS = {
    "EIA": ["eia energy forecasting", "grid demand forecasting"],
    "NOAA_NCEI": ["noaa climate analytics", "weather resilience ai"],
    "NASA": ["nasa earth science analytics", "nasa sbir ai"],
    "USGS_WATER": ["usgs hydrology analytics", "water infrastructure forecasting"],
    "BLS": ["labor forecasting", "workforce analytics"],
    "BEA": ["regional economic forecasting", "economic resilience analytics"],
    "CENSUS": ["demographic forecasting", "population trend analytics"],
    "EPA_AQS": ["air quality anomaly detection", "environmental public health forecasting"],
    "SAM_GOV": [
        "sam.gov contract opportunity",
        "federal contract research",
        "small business set aside contract",
    ],
    "SBA_GOV": [
        "sba set-aside opportunity",
        "8(a) contract opportunity",
        "hubzone federal contract",
        "sba open data api",
    ],
}

DISCOVERY_QUERY_SEEDS = [
    "sbir",
    "sttr",
    "small business innovation research",
    "broad agency announcement",
    "baa",
    "contract",
    "small business set aside",
    "8(a)",
    "hubzone",
    "cooperative agreement",
    "research grant",
    "critical infrastructure",
    "predictive analytics",
]

FEDERAL_POLICY_REFERENCES = [
    {
        "title": "SBA Digital Strategy Report",
        "last_updated": "2026-02-24",
        "url": "https://www.sba.gov/document/report-digital-strategy-report",
        "note": "Open data, content, and web API policy alignment across agency developer surfaces.",
    },
    {
        "title": "SBA Audit Report ROM 09-1",
        "last_updated": "2019-08-08",
        "url": "https://www.sba.gov/document/report-09-1-audit-report-rom-09-1-key-unresolved-oig-audit-recommendations-program-areas-funded-american",
        "note": "Audit posture context for safeguards and operational controls.",
    },
]


# ----------------------------------------------------------------------------
# Loaders
# ----------------------------------------------------------------------------
def _load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _read_or_none(p: Path) -> dict | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_csv_rows(p: Path) -> list[dict[str, str]]:
    if not p.exists():
        return []
    try:
        with p.open("r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    txt = str(value or "").strip().lower()
    return txt in {"1", "true", "t", "yes", "y"}


def _dataset_domain(dataset_name: str) -> str:
    up = (dataset_name or "").upper()
    if up.startswith("EIA930_"):
        return "eia930"
    if up.startswith("EIA_"):
        return "eia"
    if up.startswith("NOAA_"):
        return "noaa"
    if up.startswith("NASA_"):
        return "nasa"
    if up.startswith("USGS_"):
        return "usgs"
    if up.startswith("BLS_"):
        return "bls"
    if up.startswith("FRED_"):
        return "fred"
    if up.startswith("YF_"):
        return "yf"
    if up.startswith("COINGECKO_"):
        return "coingecko"
    if up.startswith("OPENAQ_"):
        return "openaq"
    return "other"


def _norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", _norm_text(value))
    return slug.strip("_") or "opportunity"


def _parse_date(value: str) -> datetime | None:
    txt = str(value or "").strip()
    if not txt:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y/%m/%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(txt, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(txt.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _days_to_close(close_date: str) -> int:
    dt = _parse_date(close_date)
    if not dt:
        return 9999
    return (dt.date() - datetime.now(timezone.utc).date()).days


def _program_window_assessment(program: dict[str, Any]) -> dict[str, Any]:
    deadline_raw = str(program.get("deadline_typical") or "").strip()
    state_raw = str(program.get("current_state") or "").strip()
    state = _norm_text(state_raw)
    deadline = _parse_date(deadline_raw)
    source_meta = program.get("source_metadata")
    if not isinstance(source_meta, dict):
        source_meta = {}
    source_name = str(source_meta.get("source") or "catalog").strip().lower()
    verified_at = _parse_date(
        source_meta.get("discovered_utc")
        or program.get("source_verified_utc")
    )
    verification_age_days = (
        (datetime.now(timezone.utc) - verified_at).total_seconds() / 86400.0
        if verified_at is not None
        else None
    )
    days_remaining = (
        (deadline.date() - datetime.now(timezone.utc).date()).days
        if deadline is not None
        else None
    )

    closed_markers = (
        "closed",
        "cancelled",
        "canceled",
        "archived",
        "between cycle",
        "between_cycles",
        "not yet released",
        "future",
        "tba",
    )
    if any(marker in state for marker in closed_markers):
        return {
            "status": "unavailable",
            "actionable": False,
            "reason": f"current_state={state_raw or 'unknown'}",
            "deadline": deadline.date().isoformat() if deadline else deadline_raw or None,
            "days_remaining": days_remaining,
        }
    if deadline is not None and days_remaining is not None and days_remaining < 0:
        return {
            "status": "expired",
            "actionable": False,
            "reason": "deadline_passed",
            "deadline": deadline.date().isoformat(),
            "days_remaining": days_remaining,
        }
    max_source_age_days = 7.0 if source_name == "grants_gov_live_scan" else 30.0
    if verification_age_days is None or verification_age_days > max_source_age_days:
        return {
            "status": "verification_required",
            "actionable": False,
            "reason": (
                "source_never_verified"
                if verification_age_days is None
                else f"source_verification_stale_{verification_age_days:.1f}_days"
            ),
            "deadline": deadline.date().isoformat() if deadline else deadline_raw or None,
            "days_remaining": days_remaining,
            "source": source_name,
            "source_verified_utc": verified_at.isoformat() if verified_at else None,
        }
    if deadline is not None:
        return {
            "status": "open",
            "actionable": True,
            "reason": "dated_window_open",
            "deadline": deadline.date().isoformat(),
            "days_remaining": days_remaining,
        }
    if "open" in state or "posted" in state:
        return {
            "status": "open",
            "actionable": True,
            "reason": f"current_state={state_raw}",
            "deadline": deadline_raw or None,
            "days_remaining": None,
        }
    if "rolling" in _norm_text(deadline_raw):
        return {
            "status": "verification_required",
            "actionable": False,
            "reason": "rolling_window_requires_current_source_verification",
            "deadline": deadline_raw,
            "days_remaining": None,
        }
    return {
        "status": "verification_required",
        "actionable": False,
        "reason": "no_verified_open_window",
        "deadline": deadline_raw or None,
        "days_remaining": None,
    }


def _read_live_source_registry() -> dict[str, Any]:
    payload = _read_or_none(LIVE_SOURCE_REGISTRY) or {}
    rows = payload.get("rows", []) if isinstance(payload.get("rows"), list) else []
    active_rows: list[dict[str, Any]] = []
    active_sources: list[str] = []
    active_sectors: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        enabled = bool(row.get("enabled"))
        status = str(row.get("status") or "").upper()
        active_status = (
            "LIVE_KEY_PRESENT" in status
            or "PUBLIC_OPEN_DATA" in status
            or "OPEN_DATA" in status
        )
        if not enabled or not active_status:
            continue
        active_rows.append(row)
        src = str(row.get("source") or "").strip().upper()
        sec = str(row.get("sector") or "").strip().lower()
        if src:
            active_sources.append(src)
        if sec:
            active_sectors.append(sec)
    return {
        "generated_utc": payload.get("generated_utc"),
        "paper_live_linked": payload.get("paper_live_linked"),
        "active_sources": sorted(set(active_sources)),
        "active_sectors": sorted(set(active_sectors)),
        "active_source_count": len(set(active_sources)),
        "active_sector_count": len(set(active_sectors)),
        "measured_source_count": len({
            str(row.get("source") or "").strip().upper()
            for row in active_rows
            if str(row.get("evidence_basis") or "").upper() == "MEASURED_FILE_MATCH"
        }),
        "credential_only_source_count": len({
            str(row.get("source") or "").strip().upper()
            for row in active_rows
            if str(row.get("evidence_basis") or "").upper() == "KEY_ONLY"
        }),
        "active_rows": active_rows,
    }


def _registry_layer_summary() -> dict[str, Any]:
    reg = _read_live_source_registry()
    return {
        "generated_utc": reg.get("generated_utc"),
        "paper_live_linked": reg.get("paper_live_linked"),
        "active_source_count": reg.get("active_source_count"),
        "active_sector_count": reg.get("active_sector_count"),
        "measured_source_count": reg.get("measured_source_count"),
        "credential_only_source_count": reg.get("credential_only_source_count"),
        "active_sources": reg.get("active_sources", []),
        "active_sectors": reg.get("active_sectors", []),
    }


def _file_provenance(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return {
        "path": str(path.resolve()),
        "exists": True,
        "size_bytes": path.stat().st_size,
        "modified_utc": datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc
        ).isoformat(),
        "sha256": h.hexdigest(),
    }


def _measured_breadth_summary() -> dict[str, Any]:
    probe = _read_or_none(DATA_BREADTH_PROBE_PATH) or {}
    catalog = _read_or_none(DATASET_CATALOG_PATH) or {}
    ds = probe.get("dataset_summary") if isinstance(probe.get("dataset_summary"), dict) else {}
    scan = catalog.get("scan") if isinstance(catalog.get("scan"), dict) else {}
    scan_limit = _safe_int(scan.get("scan_limit"), 0) or 0
    files_considered = _safe_int(scan.get("files_considered"), 0) or 0
    return {
        "scope": "measured_artifact_catalog_not_live_series_count",
        "generated_utc": probe.get("generated_utc") or catalog.get("generated_utc"),
        "artifacts_measured": _safe_int(ds.get("datasets_measured"), 0) or 0,
        "parse_ok_count": _safe_int(ds.get("parse_ok_count"), 0) or 0,
        "parse_ok_pct": _safe_float(ds.get("parse_ok_pct"), 0.0) or 0.0,
        "rows_total": _safe_int(ds.get("rows_total"), 0) or 0,
        "bytes_total": _safe_int(ds.get("bytes_total"), 0) or 0,
        "zip_members_measured": _safe_int(ds.get("zipped_member_count"), 0) or 0,
        "scan_limit": scan_limit,
        "files_considered": files_considered,
        "catalog_capped": bool(scan_limit and files_considered >= scan_limit),
        "provenance": {
            "runtime_probe": _file_provenance(DATA_BREADTH_PROBE_PATH),
            "dataset_catalog": _file_provenance(DATASET_CATALOG_PATH),
        },
    }


def _build_hunter_profile(profile: dict, catalog_programs: list[dict]) -> dict:
    hunter = _read_or_none(HUNTER_PROFILE_PATH) or {}
    qp = hunter.get("qualification_profile") or {}
    if qp:
        hunter["qualification_profile"] = qp
        return hunter

    catalog_keywords: set[str] = set()
    for p in catalog_programs:
        for kw in (p.get("fit_keywords") or []):
            if isinstance(kw, str) and kw.strip():
                catalog_keywords.add(kw.strip().lower())

    hunter["qualification_profile"] = {
        "eligibility_terms": ["small business", "for-profit", "sbir", "sttr", "phase i"],
        "keyword_targets": sorted(catalog_keywords)[:48],
        "exclude_terms": [
            "nonprofit only",
            "state government only",
            "local government only",
            "tribal only",
            "individual applicants only",
        ],
        "agency_allowlist": [
            "department of energy",
            "energy",
            "darpa",
            "dod",
            "nasa",
            "nsf",
            "noaa",
            "nist",
            "afwerx",
        ],
        "min_award_usd": 50000,
        "max_award_usd": 5000000,
    }
    return hunter


def _grantsgov_post(payload: dict[str, Any]) -> dict[str, Any] | None:
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        GRANTS_GOV_SEARCH_API,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _grantsgov_search(keyword: str, rows: int = 250) -> list[dict[str, Any]]:
    payload = {
        "rows": rows,
        "keyword": keyword,
        "oppNum": "",
        "aln": "",
        "oppStatuses": "forecasted|posted",
        "sortBy": "closeDate|asc",
        "eligibilities": "",
        "agencies": "",
        "fundingCategories": "",
        "fundingInstruments": "",
        "searchOnly": False,
        "resultType": "json",
    }
    resp = _grantsgov_post(payload)
    if not resp:
        return []
    data = resp.get("data", resp) if isinstance(resp, dict) else {}
    for key in ("oppHits", "rows", "hits", "opportunities"):
        hits = data.get(key) if isinstance(data, dict) else None
        if isinstance(hits, list):
            return [h for h in hits if isinstance(h, dict)]
    return []


def _grantsgov_fetch_opportunity(opportunity_id: int) -> dict[str, Any] | None:
    payload = {"opportunityId": opportunity_id}
    body = json.dumps(payload).encode("utf-8")
    req = Request(
        GRANTS_GOV_FETCH_API,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=25) as resp:
            parsed = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    data = parsed.get("data")
    return data if isinstance(data, dict) else None


def _as_int_id(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(str(value).strip())
    except Exception:
        return None


def _detail_applicant_types(detail: dict[str, Any]) -> list[str]:
    syn = detail.get("synopsis") if isinstance(detail.get("synopsis"), dict) else {}
    out: list[str] = []
    for row in syn.get("applicantTypes", []):
        if isinstance(row, dict):
            desc = str(row.get("description") or "").strip()
            if desc:
                out.append(desc)
    return out


def _detail_funding_instruments(detail: dict[str, Any]) -> list[str]:
    syn = detail.get("synopsis") if isinstance(detail.get("synopsis"), dict) else {}
    out: list[str] = []
    for row in syn.get("fundingInstruments", []):
        if isinstance(row, dict):
            desc = str(row.get("description") or "").strip()
            if desc:
                out.append(desc)
    return out


def _detail_categories(detail: dict[str, Any]) -> list[str]:
    syn = detail.get("synopsis") if isinstance(detail.get("synopsis"), dict) else {}
    out: list[str] = []
    for row in syn.get("fundingActivityCategories", []):
        if isinstance(row, dict):
            desc = str(row.get("description") or "").strip()
            if desc:
                out.append(desc)
    return out


def _detail_alns(detail: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for row in detail.get("alns", []):
        if isinstance(row, dict):
            aln = str(row.get("alnNumber") or "").strip()
            if aln:
                out.append(aln)
    return out


def _applicant_types_qualify(applicant_types: list[str]) -> bool:
    if not applicant_types:
        return True
    normalized = [_norm_text(x) for x in applicant_types if str(x).strip()]
    if not normalized:
        return True

    positive_markers = [
        "small business",
        "small businesses",
        "for-profit",
        "for profit",
        "businesses",
        "business organization",
    ]
    neutral_markers = ["others", "all", "unrestricted", "eligible applicants"]
    restrictive_markers = [
        "state government",
        "county government",
        "city or township government",
        "tribal",
        "nonprofit",
        "individual",
        "public housing",
        "special district",
        "independent school",
        "private institution of higher education",
        "public and state institution of higher education",
    ]

    if any(any(marker in t for marker in positive_markers) for t in normalized):
        return True
    if any(any(marker in t for marker in neutral_markers) for t in normalized):
        return True

    has_restrictive = any(any(marker in t for marker in restrictive_markers) for t in normalized)
    return not has_restrictive


@lru_cache(maxsize=1)
def _grant_hunter_score_fn():
    try:
        code_dir = str(ROOT / "code")
        if code_dir not in sys.path:
            sys.path.insert(0, code_dir)
        from grant_hunter_v2 import score_opportunity as _score_opportunity  # type: ignore

        return _score_opportunity
    except Exception:
        return None


def _score_live_hit(hit: dict[str, Any], hunter_profile: dict) -> dict[str, Any]:
    detail = hit.get("_detail") if isinstance(hit.get("_detail"), dict) else {}
    syn = detail.get("synopsis") if isinstance(detail.get("synopsis"), dict) else {}
    detail_award_ceiling = _safe_float(syn.get("awardCeiling"), None)
    detail_award_floor = _safe_float(syn.get("awardFloor"), None)
    detail_contact_name = str(syn.get("agencyContactName") or "").strip()
    detail_contact_email = str(syn.get("agencyContactEmail") or "").strip()
    detail_contact_phone = str(syn.get("agencyContactPhone") or "").strip()
    applicant_types = _detail_applicant_types(detail)
    funding_instruments = _detail_funding_instruments(detail)
    funding_categories = _detail_categories(detail)
    alns = _detail_alns(detail)
    opp_type = _classify_opportunity_type(
        str(hit.get("title") or hit.get("oppTitle") or ""),
        funding_instruments=funding_instruments,
        doc_type=str(hit.get("docType") or ""),
    )

    scorer = _grant_hunter_score_fn()
    if scorer is not None:
        try:
            scored = scorer(hit, hunter_profile)
            return {
                "opp_num": scored.opp_num,
                "title": scored.title,
                "agency": scored.agency,
                "status": scored.status,
                "doc_type": scored.doc_type,
                "open_date": scored.open_date,
                "close_date": scored.close_date,
                "days_to_close": scored.days_to_close,
                "expected_awards": scored.expected_awards,
                "total_funding_usd": scored.total_funding_usd,
                "award_ceiling_usd": detail_award_ceiling or scored.award_ceiling_usd,
                "award_floor_usd": detail_award_floor or scored.award_floor_usd,
                "score": float(scored.final_score),
                "reasons": list(scored.reasons),
                "opportunity_type": opp_type,
                "agency_contact": {
                    "name": detail_contact_name,
                    "email": detail_contact_email,
                    "phone": detail_contact_phone,
                },
                "applicant_types": applicant_types,
                "funding_instruments": funding_instruments,
                "funding_categories": funding_categories,
                "alns": alns,
                "detail": detail,
                "raw": hit,
            }
        except Exception:
            pass

    qp = hunter_profile.get("qualification_profile", {})
    kw_targets = [_norm_text(k) for k in qp.get("keyword_targets", []) if str(k).strip()]
    elig_terms = [_norm_text(k) for k in qp.get("eligibility_terms", []) if str(k).strip()]
    agency_allow = [_norm_text(k) for k in qp.get("agency_allowlist", []) if str(k).strip()]

    blob = _norm_text(" ".join(
        str(hit.get(k) or "")
        for k in ("title", "oppTitle", "agencyName", "description", "synopsis", "eligibilities")
    ))
    close_date = str(hit.get("closeDate") or "")
    days = _days_to_close(close_date)
    agency = _norm_text(hit.get("agencyName"))

    score = 0.0
    reasons: list[str] = []
    for kw in kw_targets:
        if kw and kw in blob:
            score += 4.0
            reasons.append(f"kw:{kw}")
    for term in elig_terms:
        if term and term in blob:
            score += 7.0
            reasons.append(f"elig:{term}")
    if agency_allow and any(a in agency for a in agency_allow):
        score += 8.0
        reasons.append("agency_allowlist_match")

    type_bonus = {
        "sbir": 10.0,
        "sttr": 9.0,
        "contract": 7.0,
        "baa": 6.0,
        "cooperative_agreement": 5.0,
        "grant": 3.0,
        "other": 0.0,
    }.get(opp_type, 0.0)
    if type_bonus:
        score += type_bonus
        reasons.append(f"type_bonus:{opp_type}+{type_bonus:.1f}")

    if 0 < days <= 7:
        score += 20.0
    elif 0 < days <= 30:
        score += 10.0
    elif days == 9999:
        score -= 3.0

    return {
        "opp_num": str(hit.get("oppNum") or hit.get("number") or ""),
        "title": str(hit.get("title") or hit.get("oppTitle") or ""),
        "agency": str(hit.get("agencyName") or ""),
        "status": _norm_text(hit.get("oppStatus") or hit.get("status") or ""),
        "doc_type": _norm_text(hit.get("docType") or ""),
        "open_date": str(hit.get("openDate") or ""),
        "close_date": close_date,
        "days_to_close": days,
        "expected_awards": _safe_int(hit.get("expectedNumberOfAwards") or hit.get("numExpectedAwards")),
        "total_funding_usd": _safe_float(hit.get("estimatedTotalProgramFunding") or hit.get("totalFunding")),
        "award_ceiling_usd": detail_award_ceiling or _safe_float(hit.get("awardCeiling") or hit.get("maxAwardAmt")),
        "award_floor_usd": detail_award_floor or _safe_float(hit.get("awardFloor") or hit.get("minAwardAmt")),
        "score": score,
        "reasons": reasons,
        "opportunity_type": opp_type,
        "agency_contact": {
            "name": detail_contact_name,
            "email": detail_contact_email,
            "phone": detail_contact_phone,
        },
        "applicant_types": applicant_types,
        "funding_instruments": funding_instruments,
        "funding_categories": funding_categories,
        "alns": alns,
        "detail": detail,
        "raw": hit,
    }


def _fit_keywords_from_queries(queries: list[str], title: str) -> list[str]:
    stop = {
        "grant",
        "grants",
        "contract",
        "contracts",
        "research",
        "program",
        "funding",
        "opportunity",
        "small",
        "business",
    }
    tokens: set[str] = set()
    for text in [*queries, title]:
        for tok in re.findall(r"[a-z0-9]{3,}", _norm_text(text)):
            if tok not in stop:
                tokens.add(tok)
    return sorted(tokens)


def _classify_opportunity_type(
    title: str,
    funding_instruments: list[str] | None = None,
    doc_type: str | None = None,
) -> str:
    blob = _norm_text(" ".join([title or "", *(funding_instruments or []), doc_type or ""]))
    if "sbir" in blob:
        return "sbir"
    if "sttr" in blob:
        return "sttr"
    if "broad agency announcement" in blob or re.search(r"\bbaa\b", blob):
        return "baa"
    if "contract" in blob:
        return "contract"
    if "cooperative" in blob:
        return "cooperative_agreement"
    if "grant" in blob or "synopsis" in blob:
        return "grant"
    return "other"


def _build_live_program(scored: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    title = str(scored.get("title") or "Untitled Opportunity")
    opp_num = str(scored.get("opp_num") or "")
    key = opp_num or hashlib.sha256(title.encode("utf-8", errors="replace")).hexdigest()[:10]
    prog_id = f"live_{_slug(key)}"
    cap = _safe_float(scored.get("award_ceiling_usd"), None)
    total = _safe_float(scored.get("total_funding_usd"), None)
    ceiling = int(max(50000, min(5000000, cap or total or 250000)))
    title_lower = _norm_text(title)
    phase_ii_required = "phase ii" in title_lower and "phase i" not in title_lower
    queries = scored.get("matched_queries", []) if isinstance(scored.get("matched_queries"), list) else []
    close_date = str(scored.get("close_date") or "")
    contact = scored.get("agency_contact") if isinstance(scored.get("agency_contact"), dict) else {}
    applicant_types = [str(x) for x in (scored.get("applicant_types") or []) if str(x).strip()]
    funding_instruments = [str(x) for x in (scored.get("funding_instruments") or []) if str(x).strip()]
    funding_categories = [str(x) for x in (scored.get("funding_categories") or []) if str(x).strip()]
    alns = [str(x) for x in (scored.get("alns") or []) if str(x).strip()]
    detail = scored.get("detail") if isinstance(scored.get("detail"), dict) else {}
    syn = detail.get("synopsis") if isinstance(detail.get("synopsis"), dict) else {}
    synopsis_desc = str(syn.get("synopsisDesc") or "").strip()
    opp_type = str(scored.get("opportunity_type") or "other")

    detail_url = (
        f"https://www.grants.gov/search-results-detail/{opp_num}"
        if opp_num else "https://www.grants.gov/search-grants"
    )

    small_business_marker = any(
        ("small business" in _norm_text(a)) or ("for-profit" in _norm_text(a)) or ("for profit" in _norm_text(a))
        for a in applicant_types
    )
    if applicant_types and not small_business_marker:
        # Keep strict when detail exists and explicitly lacks small-business markers.
        eligibility_small_business = False
    else:
        eligibility_small_business = True

    return {
        "id": prog_id,
        "agency": scored.get("agency") or "Federal Opportunity (Live Scan)",
        "program": title,
        "topic_area": " / ".join(_fit_keywords_from_queries(queries, title)[:6]) or "Live-discovered opportunity",
        "ceiling_usd": ceiling,
        "duration_months": 6,
        "deadline_typical": close_date or "rolling / verify in announcement",
        "current_state": scored.get("status") or "posted",
        "url": detail_url,
        "eligibility": {
            "small_business": eligibility_small_business,
            "us_owned_majority": True,
            "employees_lt": 500,
            "pi_employed_min_pct": 51,
            "phase_i_completed_required": phase_ii_required,
        },
        "fit_keywords": _fit_keywords_from_queries(queries, title),
        "required_sections": [
            "Project Summary",
            "Technical Approach",
            "Anticipated Results",
            "Commercialization Plan",
            "Budget",
            "Key Personnel",
        ],
        "page_limits": {},
        "source_metadata": {
            "source": "grants_gov_live_scan",
            "opp_num": opp_num,
            "opportunity_id": _as_int_id(scored.get("raw", {}).get("id")) if isinstance(scored.get("raw"), dict) else None,
            "opportunity_score": round(float(scored.get("score") or 0.0), 2),
            "opportunity_type": opp_type,
            "days_to_close": scored.get("days_to_close"),
            "expected_awards": scored.get("expected_awards"),
            "award_ceiling_usd": scored.get("award_ceiling_usd"),
            "total_funding_usd": scored.get("total_funding_usd"),
            "matched_queries": queries,
            "funding_instruments": funding_instruments,
            "funding_categories": funding_categories,
            "applicant_types": applicant_types,
            "alns": alns,
            "agency_contact": {
                "name": contact.get("name"),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
            },
            "synopsis_excerpt": synopsis_desc[:2000] if synopsis_desc else "",
            "registry_active_sectors": registry.get("active_sectors", []),
            "registry_active_sources": registry.get("active_sources", []),
            "discovered_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        },
    }


def discover_live_programs(
    profile: dict,
    catalog_programs: list[dict],
    *,
    query_rows: int = 250,
    max_programs: int = 80,
) -> tuple[list[dict], dict[str, Any]]:
    registry = _read_live_source_registry()
    hunter_profile = _build_hunter_profile(profile, catalog_programs)
    qp = hunter_profile.get("qualification_profile", {})
    keyword_targets = [str(k).strip() for k in qp.get("keyword_targets", []) if str(k).strip()]
    exclude_terms = [_norm_text(x) for x in qp.get("exclude_terms", []) if str(x).strip()]

    queries: set[str] = set(DISCOVERY_QUERY_SEEDS)
    queries.update(keyword_targets)
    for sec in registry.get("active_sectors", []):
        queries.update(SECTOR_QUERY_HINTS.get(sec, []))
    for src in registry.get("active_sources", []):
        queries.update(SOURCE_QUERY_HINTS.get(src, []))

    query_list = sorted(q for q in queries if q)[:36]
    hits_by_key: dict[str, dict[str, Any]] = {}
    matched_queries: dict[str, set[str]] = {}
    per_query_counts: dict[str, int] = {}

    for query in query_list:
        hits = _grantsgov_search(query, rows=query_rows)
        per_query_counts[query] = len(hits)
        for hit in hits:
            raw_key = str(hit.get("oppNum") or hit.get("number") or hit.get("id") or "").strip()
            if not raw_key:
                raw_blob = json.dumps(hit, sort_keys=True)
                raw_key = hashlib.sha256(raw_blob.encode("utf-8", errors="replace")).hexdigest()[:12]
            hits_by_key.setdefault(raw_key, hit)
            matched_queries.setdefault(raw_key, set()).add(query)

    # Enrich opportunities using fetchOpportunity details where ID is available.
    detail_ok = 0
    detail_fail = 0
    for hit in hits_by_key.values():
        opp_id = _as_int_id(hit.get("id"))
        if opp_id is None:
            continue
        detail = _grantsgov_fetch_opportunity(opp_id)
        if isinstance(detail, dict):
            hit["_detail"] = detail
            detail_ok += 1
        else:
            detail_fail += 1

    scored_rows: list[dict[str, Any]] = []
    for key, hit in hits_by_key.items():
        blob = _norm_text(" ".join(
            str(hit.get(k) or "")
            for k in ("title", "oppTitle", "agencyName", "description", "synopsis", "eligibilities")
        ))
        if any(term and term in blob for term in exclude_terms):
            continue
        scored = _score_live_hit(hit, hunter_profile)
        scored["matched_queries"] = sorted(matched_queries.get(key, set()))
        applicant_types = scored.get("applicant_types") if isinstance(scored.get("applicant_types"), list) else []
        if applicant_types and not _applicant_types_qualify([str(x) for x in applicant_types]):
            continue
        days = int(scored.get("days_to_close") or 9999)
        score = float(scored.get("score") or 0.0)
        if days <= 0:
            continue
        if days == 9999 and score < 26:
            continue
        if score < 18:
            continue
        scored_rows.append(scored)

    scored_rows.sort(
        key=lambda r: (
            float(r.get("score") or 0.0),
            -int(r.get("days_to_close") or 9999),
        ),
        reverse=True,
    )

    live_programs = [_build_live_program(row, registry) for row in scored_rows[:max_programs]]
    scan_summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "status": "ok" if hits_by_key else "degraded_no_hits",
        "query_count": len(query_list),
        "queries": query_list,
        "rows_per_query": query_rows,
        "hits_total_unique": len(hits_by_key),
        "fetch_opportunity": {
            "detail_fetched": detail_ok,
            "detail_failed": detail_fail,
        },
        "qualified_count": len(scored_rows),
        "selected_count": len(live_programs),
        "submission_channels": {
            "rest": {
                "search2": GRANTS_GOV_SEARCH_API,
                "fetchOpportunity": GRANTS_GOV_FETCH_API,
            },
            "soap": {
                "service_name": GRANTS_APPLICANT_SOAP_SERVICE_NAME,
                "port_name": GRANTS_APPLICANT_SOAP_PORT_NAME,
                "endpoint": GRANTS_APPLICANT_SOAP_ENDPOINT,
                "wsdl": GRANTS_APPLICANT_SOAP_WSDL,
            },
        },
        "registry": registry,
        "federal_policy_references": FEDERAL_POLICY_REFERENCES,
        "top": [
            {
                "id": p.get("id"),
                "agency": p.get("agency"),
                "program": p.get("program"),
                "deadline_typical": p.get("deadline_typical"),
                "source_metadata": p.get("source_metadata"),
            }
            for p in live_programs[:25]
        ],
        "per_query_counts": per_query_counts,
    }
    OPPORTUNITY_SCAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPPORTUNITY_SCAN_PATH.write_text(json.dumps(scan_summary, indent=2), encoding="utf-8")
    return live_programs, scan_summary


def _layer_coverage_for_run(utc: str) -> dict[str, Any]:
    available = {k: fn(utc).exists() for k, fn in LAYER_ARTIFACTS.items()}
    score = sum(1 for ok in available.values() if ok)
    return {
        "utc": utc,
        "coverage_score": score,
        "available_layers": [k for k, ok in available.items() if ok],
        "missing_layers": [k for k, ok in available.items() if not ok],
    }


def _resolve_v2_utc() -> str:
    root = OUT / "master_universe_v2"
    runs = sorted(
        [p.name for p in root.iterdir() if p.is_dir() and (p / "summary.json").exists()]
    )
    if not runs:
        raise SystemExit("no completed v2 run available")

    candidates = [_layer_coverage_for_run(r) for r in runs]
    # Prefer the run with the strongest cross-layer coverage. Break ties by newest UTC.
    best = sorted(candidates, key=lambda c: (c["coverage_score"], c["utc"]))[-1]

    latest_txt = root / "latest.txt"
    if latest_txt.exists():
        pinned = latest_txt.read_text(encoding="utf-8").strip()
        if pinned in runs:
            pinned_cov = _layer_coverage_for_run(pinned)
            # Keep the pinned run only if it is at least as coherent as the best candidate.
            if pinned_cov["coverage_score"] >= best["coverage_score"]:
                return pinned
    return best["utc"]


def build_evidence_summary(utc: str) -> dict:
    """Aggregate every evidence layer into a flat dict the renderer can use."""
    base = OUT
    v2 = _read_or_none(base / "master_universe_v2" / utc / "summary.json") or {}
    router = _read_or_none(base / "meta_router" / utc / "eval.json") or {}
    stacker = _read_or_none(base / "hybrid_stacker" / utc / "eval.json") or {}
    blender = _read_or_none(base / "stacking_blender" / utc / "eval.json") or {}
    calib = _read_or_none(base / "ci_calibration" / utc / "summary.json") or {}
    anom = _read_or_none(base / "anomaly_scanner" / utc / "summary.json") or {}
    regime = _read_or_none(base / "regime_shift_scanner" / utc / "summary.json") or {}

    n_total = v2.get("n_datasets_succeeded") or v2.get("n_datasets_in_universe")
    fwc = v2.get("family_win_counts") or {}
    rs = router.get("summary", {}) if isinstance(router.get("summary"), dict) else {}
    ss = stacker.get("summary", {}) if isinstance(stacker.get("summary"), dict) else {}
    bs = blender.get("summary", {}) if isinstance(blender.get("summary"), dict) else {}
    cov = (calib.get("overall") or {})

    layers = {
        "benchmark": {
            "n_datasets": n_total,
            "claim_scope": "frozen_benchmark_evaluated_series",
            "n_models": 9,
            "n_families": 5,
            "family_win_counts": fwc,
            "harmonic_win_rate": v2.get("harmonic_win_rate"),
            "harmonic_median_margin_pct": v2.get("harmonic_median_margin_pct"),
            "harmonic_avg_margin_pct": v2.get("harmonic_avg_margin_pct"),
        },
        "meta_router": {
            "wins": rs.get("win_counts", {}).get("router"),
            "n": rs.get("n_datasets"),
            "win_rate": rs.get("win_rates", {}).get("router"),
            "median_rel_rmse_vs_oracle":
                rs.get("median_rel_rmse_vs_oracle", {}).get("router"),
        },
        "hybrid_stacker": {
            "router_wins": ss.get("win_counts", {}).get("router"),
            "n": ss.get("n_datasets"),
            "j_beats_v2_oracle":
                ss.get("beats_v2_oracle", {}).get("j_sarima_plus_harmonic"),
            "k_beats_v2_oracle":
                ss.get("beats_v2_oracle", {}).get("k_linear_plus_harmonic"),
        },
        "ci_calibration": {
            "mean_cov80": cov.get("mean_cov80"),
            "mean_cov95": cov.get("mean_cov95"),
            "method": "residual_sigma_sqrt_h",
        },
        "stacking_blender": {
            "wins": bs.get("win_counts_in_blend_plus_fams", {}).get("blend"),
            "n": bs.get("n_datasets"),
            "median_blend_rel_vs_v2_oracle": bs.get("median_blend_rel_vs_v2_oracle"),
            "beats_v2_oracle": bs.get("blender_beats_v2_oracle"),
            "avg_blend_weights": bs.get("avg_blend_weights"),
        },
        "anomaly_scanner": {
            "n_datasets": anom.get("n_datasets"),
            "n_with_2sigma": anom.get("n_with_2sigma_anomaly"),
            "n_with_3sigma": anom.get("n_with_3sigma_anomaly"),
        },
        "regime_shift": {
            "n_datasets": regime.get("n_datasets"),
            "n_with_break": regime.get("n_with_any_mean_break"),
            "n_recent": regime.get("n_with_recent_break_within_12"),
            "n_variance_break": regime.get("n_with_variance_regime_break"),
            "params": regime.get("params"),
        },
        "measured_breadth": _measured_breadth_summary(),
        "active_registry": _registry_layer_summary(),
    }
    return {"run_utc": utc, "layers": layers}


def _program_target_domains(program: dict) -> set[str]:
    text_parts = [
        str(program.get("agency") or ""),
        str(program.get("program") or ""),
        str(program.get("topic_area") or ""),
    ]
    text_parts.extend(str(k) for k in (program.get("fit_keywords") or []))
    source_meta = program.get("source_metadata") if isinstance(program.get("source_metadata"), dict) else {}
    text_parts.extend(str(q) for q in source_meta.get("matched_queries", []))
    blob = _norm_text(" ".join(text_parts))
    domains: set[str] = set()
    for hint, mapped in DOMAIN_KEYWORD_HINTS.items():
        if hint in blob:
            domains.update(mapped)
    return domains


@lru_cache(maxsize=4)
def _dataset_artifact_maps(utc: str) -> dict[str, Any]:
    v2 = _read_or_none(OUT / "master_universe_v2" / utc / "summary.json") or {}
    dataset_meta: dict[str, dict[str, Any]] = {}
    for name, meta in (v2.get("datasets") or {}).items():
        if not isinstance(name, str) or not isinstance(meta, dict):
            continue
        if meta.get("error"):
            continue
        dataset_meta[name] = meta

    anomaly_rows = _read_csv_rows(OUT / "anomaly_scanner" / utc / "ranked.csv")
    regime_rows = _read_csv_rows(OUT / "regime_shift_scanner" / utc / "regimes.csv")
    stack_rows = _read_csv_rows(OUT / "hybrid_stacker" / utc / "results.csv")
    blend_rows = _read_csv_rows(OUT / "stacking_blender" / utc / "results.csv")

    anomaly_map = {r.get("dataset", ""): r for r in anomaly_rows if r.get("dataset")}
    regime_map = {r.get("dataset", ""): r for r in regime_rows if r.get("dataset")}
    stack_map = {r.get("dataset", ""): r for r in stack_rows if r.get("dataset")}
    blend_map = {r.get("dataset", ""): r for r in blend_rows if r.get("dataset")}

    return {
        "dataset_meta": dataset_meta,
        "anomaly_map": anomaly_map,
        "regime_map": regime_map,
        "stack_map": stack_map,
        "blend_map": blend_map,
    }


def build_program_spotlights(program: dict, utc: str, max_items: int = 6) -> list[dict[str, Any]]:
    maps = _dataset_artifact_maps(utc)
    dataset_meta = maps["dataset_meta"]
    anomaly_map = maps["anomaly_map"]
    regime_map = maps["regime_map"]
    stack_map = maps["stack_map"]
    blend_map = maps["blend_map"]

    target_domains = _program_target_domains(program)
    rows: list[tuple[float, dict[str, Any]]] = []
    for dataset, meta in dataset_meta.items():
        domain = _dataset_domain(dataset)
        if target_domains and domain not in target_domains:
            continue

        anom = anomaly_map.get(dataset, {})
        reg = regime_map.get(dataset, {})
        stack = stack_map.get(dataset, {})
        blend = blend_map.get(dataset, {})

        n_obs = _safe_int(meta.get("n_obs"), 0) or 0
        max_abs_z = _safe_float(anom.get("max_abs_z"), 0.0) or 0.0
        n_2sigma = _safe_int(anom.get("n_anomalies_2sigma"), 0) or 0
        n_3sigma = _safe_int(anom.get("n_anomalies_3sigma"), 0) or 0
        n_breaks = _safe_int(reg.get("n_breaks_total"), 0) or 0
        recent_break = _to_bool(reg.get("recent_break"))
        var_break = _to_bool(reg.get("var_regime_break"))

        router_rmse = _safe_float(stack.get("rmse_l_router"), None)
        oracle_rmse = _safe_float(stack.get("v2_best_rmse"), None)
        router_rel = None
        if router_rmse is not None and oracle_rmse and oracle_rmse > 0:
            router_rel = router_rmse / oracle_rmse

        blend_rel = _safe_float(blend.get("rel_blend_vs_oracle"), None)
        blend_beats = _to_bool(blend.get("beats_v2_oracle"))

        score = 0.0
        if domain in target_domains:
            score += 8.0
        score += min(15.0, max_abs_z)
        score += min(10.0, n_3sigma * 0.9 + n_2sigma * 0.2)
        score += min(10.0, n_breaks * 0.12)
        if recent_break:
            score += 3.5
        if var_break:
            score += 2.5
        if router_rel is not None:
            if router_rel <= 1.0:
                score += 2.5
            else:
                score += max(0.0, 1.5 - (router_rel - 1.0))
        if blend_beats:
            score += 2.0
        score += min(5.0, n_obs / 300.0)

        rows.append((
            score,
            {
                "dataset": dataset,
                "domain": domain,
                "coverage": {
                    "n_obs": n_obs,
                    "n_test": _safe_int(meta.get("n_test"), None),
                    "first": meta.get("first"),
                    "last": meta.get("last"),
                },
                "anomaly": {
                    "max_abs_z": round(max_abs_z, 4) if max_abs_z else None,
                    "n_anomalies_2sigma": n_2sigma,
                    "n_anomalies_3sigma": n_3sigma,
                },
                "regime": {
                    "n_breaks_total": n_breaks,
                    "recent_break": recent_break,
                    "var_regime_break": var_break,
                    "last_break_dir": reg.get("last_break_dir"),
                },
                "model_performance": {
                    "router_rmse": router_rmse,
                    "oracle_rmse": oracle_rmse,
                    "router_rel_vs_oracle": round(router_rel, 4) if router_rel is not None else None,
                    "blend_rel_vs_oracle": round(blend_rel, 4) if blend_rel is not None else None,
                    "blend_beats_oracle": blend_beats,
                },
                "selection_score": round(score, 4),
            },
        ))

    if not rows and not target_domains:
        # Fallback when no domain hints are present: pick globally strongest evidence rows.
        for dataset, meta in dataset_meta.items():
            domain = _dataset_domain(dataset)
            anom = anomaly_map.get(dataset, {})
            reg = regime_map.get(dataset, {})
            max_abs_z = _safe_float(anom.get("max_abs_z"), 0.0) or 0.0
            n_breaks = _safe_int(reg.get("n_breaks_total"), 0) or 0
            score = min(15.0, max_abs_z) + min(10.0, n_breaks * 0.1)
            rows.append((score, {
                "dataset": dataset,
                "domain": domain,
                "coverage": {
                    "n_obs": _safe_int(meta.get("n_obs"), 0) or 0,
                    "n_test": _safe_int(meta.get("n_test"), None),
                    "first": meta.get("first"),
                    "last": meta.get("last"),
                },
                "anomaly": {
                    "max_abs_z": round(max_abs_z, 4) if max_abs_z else None,
                    "n_anomalies_2sigma": _safe_int(anom.get("n_anomalies_2sigma"), 0) or 0,
                    "n_anomalies_3sigma": _safe_int(anom.get("n_anomalies_3sigma"), 0) or 0,
                },
                "regime": {
                    "n_breaks_total": n_breaks,
                    "recent_break": _to_bool(reg.get("recent_break")),
                    "var_regime_break": _to_bool(reg.get("var_regime_break")),
                    "last_break_dir": reg.get("last_break_dir"),
                },
                "model_performance": {
                    "router_rmse": None,
                    "oracle_rmse": None,
                    "router_rel_vs_oracle": None,
                    "blend_rel_vs_oracle": None,
                    "blend_beats_oracle": False,
                },
                "selection_score": round(score, 4),
            }))

    rows.sort(key=lambda item: item[0], reverse=True)
    selected: list[dict[str, Any]] = []
    domain_counts: Counter[str] = Counter()
    deferred: list[dict[str, Any]] = []
    for _, row in rows:
        domain = row.get("domain") or "other"
        if domain_counts[domain] >= 2:
            deferred.append(row)
            continue
        selected.append(row)
        domain_counts[domain] += 1
        if len(selected) >= max_items:
            break
    if len(selected) < max_items:
        for row in deferred:
            selected.append(row)
            if len(selected) >= max_items:
                break
    return selected[:max_items]


def format_spotlight_lines(spotlights: list[dict[str, Any]], limit: int = 4) -> list[str]:
    lines: list[str] = []
    for item in spotlights[:limit]:
        dataset = item.get("dataset")
        domain = item.get("domain")
        anomaly = item.get("anomaly") or {}
        regime = item.get("regime") or {}
        model = item.get("model_performance") or {}
        pieces: list[str] = []
        max_abs_z = anomaly.get("max_abs_z")
        if isinstance(max_abs_z, (int, float)):
            pieces.append(f"max |z| {max_abs_z:.2f}")
        n_3sigma = anomaly.get("n_anomalies_3sigma")
        if isinstance(n_3sigma, int) and n_3sigma > 0:
            pieces.append(f"{n_3sigma} x >=3sigma anomalies")
        n_breaks = regime.get("n_breaks_total")
        if isinstance(n_breaks, int) and n_breaks > 0:
            pieces.append(f"{n_breaks} regime breaks")
        if regime.get("recent_break"):
            pieces.append("recent break in current window")
        rel = model.get("router_rel_vs_oracle")
        if isinstance(rel, (int, float)):
            pieces.append(f"router/oracle RMSE {rel:.2f}")
        detail = "; ".join(pieces) if pieces else "strong cross-layer evidence signal"
        lines.append(f"- {dataset} ({domain}): {detail}.")
    return lines


# ----------------------------------------------------------------------------
# Eligibility
# ----------------------------------------------------------------------------
def score_eligibility(program: dict, profile: dict, evidence: dict) -> dict:
    """Return {eligible, score 0-1, reasons[], gaps[]}."""
    e = program.get("eligibility", {})
    reasons: list[str] = []
    gaps: list[str] = []

    eligible = True
    if e.get("small_business") and not profile["company"].get("small_business"):
        eligible = False
        gaps.append("Not registered as small business")
    else:
        if e.get("small_business"):
            reasons.append("Small business ✓")
    if e.get("us_owned_majority") and not profile["company"].get("us_owned_majority"):
        eligible = False
        gaps.append("US-owned majority required")
    elif e.get("us_owned_majority"):
        reasons.append("US-owned majority ✓")
    if e.get("employees_lt"):
        n = profile["company"].get("employees", 0)
        if n >= e["employees_lt"]:
            eligible = False
            gaps.append(f"Headcount {n} >= {e['employees_lt']}")
        else:
            reasons.append(f"Headcount {n} < {e['employees_lt']} ✓")
    if e.get("pi_employed_min_pct"):
        pct = profile["pi"].get("employed_pct", 0)
        if pct < e["pi_employed_min_pct"]:
            gaps.append(f"PI employment {pct}% < required {e['pi_employed_min_pct']}%")
            eligible = False
        else:
            reasons.append(f"PI employed {pct}% ✓")
    if e.get("phase_i_completed_required"):
        gaps.append("Phase I completion needed (status: TO_BE_FILLED)")
        eligible = False

    window = _program_window_assessment(program)
    if not window.get("actionable"):
        eligible = False
        gaps.append(
            "Opportunity is not currently actionable: "
            f"{window.get('status')} ({window.get('reason')})"
        )
    else:
        reasons.append(
            "Opportunity window verified open"
            + (
                f" ({window.get('days_remaining')} days remaining)"
                if window.get("days_remaining") is not None
                else ""
            )
        )

    # Topical fit — fraction of fit_keywords mentioned in capabilities
    caps_text = " ".join(profile.get("company_capabilities", []) +
                         profile.get("broader_impacts", []) +
                         profile.get("differentiators", [])).lower()
    kws = program.get("fit_keywords", [])
    hit = sum(1 for k in kws if k.lower() in caps_text)
    fit = (hit / max(1, len(kws))) if kws else 0.5
    reasons.append(f"Topical fit {hit}/{len(kws)} keywords matched ({fit*100:.0f}%)")

    # Evidence-strength bonus (cap +0.2)
    ev_score = 0.0
    ben = evidence["layers"]["benchmark"]
    if (ben.get("n_datasets") or 0) >= 100:
        ev_score += 0.10
    if (ben.get("n_datasets") or 0) >= 500:
        ev_score += 0.05
    cov = evidence["layers"]["ci_calibration"]
    if cov.get("mean_cov80") and cov["mean_cov80"] >= 0.80:
        ev_score += 0.05

    source_meta = program.get("source_metadata") if isinstance(program.get("source_metadata"), dict) else {}
    opp_score_raw = _safe_float(source_meta.get("opportunity_score"), None) if source_meta else None
    opp_bonus = 0.0
    if opp_score_raw is not None:
        normalized = max(0.0, min(1.0, opp_score_raw / 100.0))
        opp_bonus = normalized * 0.2
        reasons.append(f"Live opportunity score {opp_score_raw:.1f}/100 (+{opp_bonus:.2f})")
    if source_meta.get("source") == "grants_gov_live_scan":
        opp_num = source_meta.get("opp_num")
        if opp_num:
            reasons.append(f"Discovered from Grants.gov live scan ({opp_num})")
        days = source_meta.get("days_to_close")
        if isinstance(days, int):
            reasons.append(f"Opportunity closes in {days} days")

    score = round(min(1.0, fit * 0.7 + ev_score + 0.1 + opp_bonus), 4)
    fit_floor = 0.02 if source_meta else 0.05
    live_override = opp_score_raw is not None and opp_score_raw >= 18.0
    return {
        "eligible": eligible and (fit > fit_floor or live_override),
        "score": score,
        "topical_fit": round(fit, 3),
        "evidence_bonus": round(ev_score, 3),
        "opportunity_bonus": round(opp_bonus, 3),
        "opportunity_window": window,
        "reasons": reasons,
        "gaps": gaps,
    }


# ----------------------------------------------------------------------------
# Renderers — produce real, paste-ready text per section
# ----------------------------------------------------------------------------
def render_project_summary(
    program: dict,
    profile: dict,
    ev: dict,
    spotlights: list[dict[str, Any]] | None = None,
) -> str:
    L = ev["layers"]
    ben = L["benchmark"]
    rt = L["meta_router"]
    cal = L["ci_calibration"]
    breadth = L.get("measured_breadth", {})
    n = ben.get("n_datasets") or "—"
    rt_rate = rt.get("win_rate")
    rt_pct = f"{rt_rate*100:.1f}%" if isinstance(rt_rate, (int, float)) else "—"
    c80 = cal.get("mean_cov80")
    c95 = cal.get("mean_cov95")
    c80s = f"{c80*100:.1f}%" if isinstance(c80, (int, float)) else "—"
    c95s = f"{c95*100:.1f}%" if isinstance(c95, (int, float)) else "—"
    registry = L.get("active_registry", {}) if isinstance(L.get("active_registry"), dict) else {}
    source_meta = program.get("source_metadata") if isinstance(program.get("source_metadata"), dict) else {}
    spotlight_lines = format_spotlight_lines(spotlights or [], limit=4)
    opp_context_lines: list[str] = []
    if source_meta:
        opp_num = source_meta.get("opp_num")
        if opp_num:
            opp_context_lines.append(f"- Live-discovered opportunity number: **{opp_num}**")
        days = source_meta.get("days_to_close")
        if isinstance(days, int):
            opp_context_lines.append(f"- Time-to-close: **{days} days**")
        applicant_types = source_meta.get("applicant_types")
        if isinstance(applicant_types, list) and applicant_types:
            opp_context_lines.append(f"- Applicant types listed by agency: {', '.join(map(str, applicant_types[:6]))}")
        instruments = source_meta.get("funding_instruments")
        if isinstance(instruments, list) and instruments:
            opp_context_lines.append(f"- Funding instruments: {', '.join(map(str, instruments[:4]))}")
        alns = source_meta.get("alns")
        if isinstance(alns, list) and alns:
            opp_context_lines.append(f"- ALN references: {', '.join(map(str, alns[:6]))}")

    sector_line = ""
    active_sectors = registry.get("active_sectors") if isinstance(registry.get("active_sectors"), list) else []
    active_sources = registry.get("active_sources") if isinstance(registry.get("active_sources"), list) else []
    if active_sectors or active_sources:
        sector_line = (
            f"- **Enabled source registry:** {len(active_sectors)} sectors / {len(active_sources)} "
            f"credentialed or public-data sources; "
            f"{registry.get('measured_source_count', 0)} have measured local artifacts and "
            f"{registry.get('credential_only_source_count', 0)} are credential-only. "
            f"sector list = {', '.join(map(str, active_sectors[:8]))}.\n"
        )

    spotlight_block = ""
    if spotlight_lines:
        spotlight_block = (
            "## Program-specific evidence spotlights\n"
            "The following datasets are selected from the frozen benchmark based on this program's domain and live opportunity context:\n"
            + "\n".join(spotlight_lines)
            + "\n\n"
        )

    opp_block = ""
    if opp_context_lines:
        opp_block = "## Opportunity extraction context\n" + "\n".join(opp_context_lines) + "\n\n"

    return (
        f"# Project Summary\n\n"
        f"**Program:** {program['agency']} — {program['program']}  \n"
        f"**Topic:** {program['topic_area']}  \n"
        f"**Applicant:** {profile['company']['legal_name']} "
        f"(d/b/a {profile['company']['dba']})  \n"
        f"**PI:** {profile['pi']['name']}, {profile['pi']['title']}\n\n"
        f"## Innovation\n"
        f"LumenCore™ ships a production, evidence-chained time-series forecasting "
        f"stack that solves the hardest problem in operational forecasting: "
        f"**no single model family wins everywhere**. We fix this with a "
        f"per-dataset family meta-router that selects the right model for each "
        f"series, plus six independent evidence layers — all SHA-256 verifiable, "
        f"all reproducible from one frozen benchmark.\n\n"
        f"## Headline results (frozen run `{ev['run_utc']}`)\n"
        f"- **{n} frozen benchmark series** evaluated head-to-head across 9 "
        f"models in 5 families.\n"
        f"- **Measured data breadth:** {breadth.get('artifacts_measured', 0):,} physical/archive "
        f"artifacts measured, {breadth.get('parse_ok_count', 0):,} parsed successfully, "
        f"covering {breadth.get('rows_total', 0):,} rows. This catalog is broader than, "
        f"and is not represented as identical to, the frozen benchmark or live feeds.\n"
        f"- **Meta-router evaluation:** {rt.get('wins')}/{rt.get('n')} "
        f"series-level wins ({rt_pct}); median rel-RMSE vs oracle = "
        f"{rt.get('median_rel_rmse_vs_oracle')}.\n"
        f"- **Calibrated uncertainty:** 80% bands cover {c80s} empirically; 95% "
        f"bands cover {c95s} (target 80% / 95%).\n"
        f"- **Anomaly scanner:** {L['anomaly_scanner'].get('n_with_2sigma')}/"
        f"{L['anomaly_scanner'].get('n_datasets')} datasets flagged ≥2σ in the "
        f"holdout window — early-warning candidates.\n"
        f"- **Regime-shift detector:** {L['regime_shift'].get('n_with_break')}/"
        f"{L['regime_shift'].get('n_datasets')} datasets carry mean-shift breaks "
        f"(CUSUM δ=0.5, h=5); {L['regime_shift'].get('n_recent')} broke in the "
        f"most recent 12 steps.\n\n"
        + sector_line
        + "\n"
        + opp_block
        + spotlight_block
        +
        f"## Public benefit\n"
        f"Open evidence surface at https://lumen-core.ai/evidence/. Every claim in "
        f"this proposal chains to a SHA-256 manifest in the published bundle. "
        f"Independent reviewers can re-run and reproduce within hours.\n"
    )


def render_technical_volume(
    program: dict,
    profile: dict,
    ev: dict,
    spotlights: list[dict[str, Any]] | None = None,
) -> str:
    L = ev["layers"]
    rg = L["regime_shift"]
    bl = L["stacking_blender"]
    weights = bl.get("avg_blend_weights") or {}
    weights_lines = "\n".join(
        f"  - {k}: avg weight {v:.3f}" for k, v in
        sorted((weights or {}).items(), key=lambda kv: -float(kv[1] or 0))
    )
    spotlight_lines = format_spotlight_lines(spotlights or [], limit=6)
    spotlight_section = ""
    if spotlight_lines:
        spotlight_section = (
            "## 2B. Program-targeted dataset findings\n"
            "These dataset-level findings were selected to align with the current opportunity's sector and agency framing:\n"
            + "\n".join(spotlight_lines)
            + "\n\n"
        )

    return (
        f"# Technical Volume\n\n"
        f"## 1. Problem statement\n"
        f"Operational forecasting in critical infrastructure (electricity, "
        f"financial, supply chain) suffers three coupled failures:\n"
        f"1. **Model brittleness** — every estimator has datasets where it loses "
        f"badly; users pick one and live with the worst case.\n"
        f"2. **Uncertainty theatre** — point forecasts ship with bands that are "
        f"either wildly miscalibrated or never reported at all.\n"
        f"3. **Silent regime shifts** — when the data-generating process changes, "
        f"models keep predicting yesterday's world.\n\n"
        f"## 2. Approach (seven verifiable layers)\n\n"
        f"**Layer 1 — Master benchmark.** {L['benchmark'].get('n_datasets')} "
        f"frozen benchmark series × 9 models × 5 families: baseline, harmonic, neural, "
        f"tree, classical. Walk-forward 80/20 split per dataset. RMSE per "
        f"(dataset, model). Frozen output: SHA-256 chain in "
        f"`out/master_universe_v2/<UTC>/manifest.sha256.json`.\n\n"
        f"**Layer 2 — Meta-router.** A 16-feature random-forest classifier "
        f"learns which family wins on each series. Features include trend "
        f"slope, harmonic-12 strength, seasonality FFT energy, autocorr at "
        f"k=1..12, hurst exponent, std-of-diffs. Result: "
        f"{L['meta_router'].get('wins')}/{L['meta_router'].get('n')} wins, "
        f"median rel-RMSE vs oracle = {L['meta_router'].get('median_rel_rmse_vs_oracle')}.\n\n"
        f"**Layer 3 — Hybrid stacker.** Eight strategies head-to-head, "
        f"including two novel hybrids: SARIMA + harmonic-residual ("
        f"beats v2-oracle on {L['hybrid_stacker'].get('j_beats_v2_oracle')} "
        f"datasets) and Linear+harmonic-residual (beats on "
        f"{L['hybrid_stacker'].get('k_beats_v2_oracle')}).\n\n"
        f"**Layer 4 — CI calibration.** σ·√h residual-bootstrap bands. "
        f"Empirical coverage: 80% target → "
        f"{L['ci_calibration'].get('mean_cov80')*100:.1f}% actual; "
        f"95% target → {L['ci_calibration'].get('mean_cov95')*100:.1f}% actual.\n\n"
        f"**Layer 5 — NNLS stacking blender.** Convex non-negative least-squares "
        f"weights over five family champions, fit on a holdout slice of training. "
        f"Average blend weights:\n{weights_lines}\n\n"
        f"**Layer 6 — Anomaly scanner.** Router-picked champion forecasts every "
        f"series; |z| against σ·√h bands flags points >2σ as anomalies. "
        f"{L['anomaly_scanner'].get('n_with_2sigma')}/"
        f"{L['anomaly_scanner'].get('n_datasets')} datasets flagged.\n\n"
        f"**Layer 7 — Regime-shift detector.** Two-sided CUSUM "
        f"(δ={(rg.get('params') or {}).get('cusum_delta')}, "
        f"h={(rg.get('params') or {}).get('cusum_h')}) on rolling-standardized "
        f"series, plus variance-ratio test. Found "
        f"{rg.get('n_with_break')}/{rg.get('n_datasets')} datasets with "
        f"mean-shift breaks; {rg.get('n_recent')} in the last 12 steps.\n\n"
        + spotlight_section
        +
        f"## 3. Why this is novel\n"
        + "\n".join(f"- {d}" for d in profile.get("differentiators", [])) + "\n\n"
        f"## 4. Phase {('II' if 'phase_ii' in program['id'] else 'I')} milestones\n"
        f"- M1 (month 1): Deduplicate the measured artifact catalog and promote "
        f"at least 1,500 distinct, quality-controlled series into the benchmark.\n"
        f"- M2 (month 2): Retrain router on expanded universe; target "
        f"≥55% per-dataset wins.\n"
        f"- M3 (month 3): Ship live REST + WebSocket API for forecast "
        f"streaming; SLA <200ms p95 cold latency.\n"
        f"- M4 (month 4): Pilot integration with one DOE partner laboratory "
        f"and one private-sector pilot (energy or critical-infrastructure SCADA).\n"
        f"- M5 (month 5): Reproducibility audit by an independent reviewer "
        f"using only the SHA-256 evidence chain.\n"
        f"- M6 (month 6): Phase I final report + Phase II proposal package.\n\n"
        f"## 5. Anticipated results\n"
        f"- ≥55% per-dataset family-selection wins on a 1,500-set universe.\n"
        f"- Empirical 80% / 95% band coverage within ±2pp of nominal.\n"
        f"- ≥30% reduction in surprise-event misses (anomaly + regime breaks "
        f"detected before manual operator detection in pilot SCADA logs).\n"
        f"- All deliverables published with SHA-256 manifests at "
        f"https://lumen-core.ai/evidence/.\n"
    )


def render_commercialization(program: dict, profile: dict, ev: dict) -> str:
    verified_letters = [
        str(letter).strip()
        for letter in profile.get("team_letters_of_support", [])
        if str(letter).strip()
        and not str(letter).strip().upper().startswith("TO_BE_FILLED")
    ]
    letters_text = (
        "\n".join(f"- {letter}" for letter in verified_letters)
        if verified_letters
        else "- No third-party letter is claimed in this draft; add only executed letters permitted by the solicitation."
    )
    return (
        f"# Commercialization Plan\n\n"
        f"## Market\n"
        f"Three primary verticals, all underserved by current "
        f"forecast-as-a-service offerings:\n"
        f"1. **Energy operations** (utilities, ISO/RTOs, distributed energy "
        f"resource aggregators): forecast load, generation, frequency, "
        f"and detect regime breaks before they propagate.\n"
        f"2. **Financial / commodities desks**: meta-routed forecasts on macro "
        f"and rates series with calibrated bands suitable for risk attribution.\n"
        f"3. **Federal / public-good infrastructure**: federal data partners "
        f"(FRED, EIA, BLS, NOAA) consume pre-validated forecasts with audit "
        f"trail.\n\n"
        f"## Business model\n"
        f"- **Tier 1 — Public evidence (free):** lumen-core.ai/evidence/ — "
        f"acquisition channel and reproducibility proof.\n"
        f"- **Tier 2 — API ($999–$9,999/mo):** rate-limited REST + streaming "
        f"forecasts with SLA, on the deployed FastAPI gateway.\n"
        f"- **Tier 3 — Enterprise pilots ($50–250k/yr):** managed deployment "
        f"with sector-specific model fine-tuning and on-prem option.\n"
        f"- **Tier 4 — Government deliverables:** Phase I → Phase II → "
        f"production contracts.\n\n"
        f"## Competitive positioning\n"
        + "\n".join(f"- {d}" for d in profile.get("differentiators", [])) + "\n\n"
        f"## Letters of support (commitments)\n"
        + letters_text + "\n\n"
        f"## Path to follow-on funding\n"
        f"Phase I → Phase II ({program.get('ceiling_usd')}) → enterprise pilots "
        f"→ Series Seed (LumenCore as standalone product company). "
        f"IP status: {profile.get('ip_status')}\n"
    )


def render_budget(program: dict, profile: dict) -> dict:
    """Generate a default budget that fits the program ceiling."""
    ceiling = int(program.get("ceiling_usd") or 200_000)
    months = int(program.get("duration_months") or 6)
    pi_loaded_rate_per_month = 18_500
    pi_total = min(
        pi_loaded_rate_per_month * months,
        int(ceiling * 0.42),
    )
    fringe = int(pi_total * 0.27)
    travel = min(7_500, int(ceiling * 0.03))
    cloud = min(15_000, int(ceiling * 0.08))
    materials = min(5_000, int(ceiling * 0.02))
    consultants = int(ceiling * 0.12)
    committed = pi_total + fringe + travel + cloud + materials + consultants
    indirect = max(0, ceiling - committed)
    total = committed + indirect
    if total != ceiling:
        raise RuntimeError(
            f"budget allocator invariant failed: total={total} ceiling={ceiling}"
        )
    return {
        "ceiling_usd": ceiling,
        "duration_months": months,
        "categories": {
            "pi_salary": pi_total,
            "fringe_benefits_27pct": fringe,
            "indirect_costs_provisional": indirect,
            "travel_conferences": travel,
            "cloud_compute": cloud,
            "materials_supplies": materials,
            "consultants_subawards": consultants,
        },
        "total": total,
        "notes": [
            "PI rate is a planning assumption; final salary and effort must match payroll and solicitation rules.",
            "Cloud compute covers GPU training + on-demand FastAPI hosting.",
            "Indirect costs are a balancing planning reserve, not a claimed negotiated rate; validate the allowed base and rate before submission.",
            "Consultants/subawards require quotes, scopes, and solicitation-specific allowability review.",
        ],
    }


def render_cover_letter(program: dict, profile: dict, ev: dict) -> str:
    today = datetime.now().date().isoformat()
    return (
        f"{today}\n\n"
        f"To: {program['agency']} — {program['program']} Selection Committee\n"
        f"Re: SBIR / Topic — {program.get('topic_area')}\n\n"
        f"Dear Selection Committee,\n\n"
        f"{profile['company']['legal_name']} respectfully submits this proposal "
        f"under {program['program']}. Our LumenCore™ stack is a production, "
        f"evidence-chained forecasting platform with seven independent, "
        f"SHA-256-verifiable measurement layers — built on "
        f"{ev['layers']['benchmark'].get('n_datasets')} frozen benchmark series and "
        f"validated end-to-end before this submission was assembled.\n\n"
        f"Every quantitative claim in the attached package resolves to a "
        f"public manifest entry at https://lumen-core.ai/evidence/runs/"
        f"{ev['run_utc']}/. Reviewers can independently rebuild any number, "
        f"chart, or model output from the published artifacts.\n\n"
        f"PI: {profile['pi']['name']}, {profile['pi']['title']} "
        f"({profile['pi'].get('employed_pct')}% time commitment).\n\n"
        f"Sincerely,\n\n"
        f"{profile['pi']['name']}\n"
        f"{profile['pi']['title']}, {profile['company']['legal_name']}\n"
        f"{profile['company'].get('email')} · {profile['company'].get('phone')}\n"
    )


def render_application_md(program: dict, profile: dict, ev: dict, budget: dict) -> str:
    spotlights = build_program_spotlights(program, ev["run_utc"], max_items=6)
    parts = [
        f"# {program['agency']} — {program['program']}",
        f"## Topic: {program['topic_area']}",
        f"_Frozen evidence run: `{ev['run_utc']}`_\n",
        "---\n",
        render_project_summary(program, profile, ev, spotlights=spotlights),
        "\n---\n",
        render_technical_volume(program, profile, ev, spotlights=spotlights),
        "\n---\n",
        render_commercialization(program, profile, ev),
        "\n---\n",
        "# Budget Summary\n",
        f"- **Ceiling:** ${budget['ceiling_usd']:,}",
        f"- **Duration:** {budget['duration_months']} months",
        f"- **Total requested:** ${budget['total']:,}\n",
        "| Category | Amount (USD) |",
        "|---|---:|",
    ]
    for cat, amt in budget["categories"].items():
        parts.append(f"| {cat.replace('_', ' ').title()} | ${amt:,} |")
    parts.append("\n## Budget notes\n" + "\n".join(f"- {n}" for n in budget["notes"]))
    parts.append("\n---\n")
    parts.append("# Key Personnel\n")
    parts.append(f"**{profile['pi']['name']}** — {profile['pi']['title']}\n")
    parts.append(profile['pi']['bio_short'])
    parts.append("\n---\n# Facilities & Compute\n")
    parts.append(
        "Local development: Windows 11 with Python 3.14 venv; reproducible "
        "joblib-parallel pipelines on commodity hardware. Production: "
        "Caddy-fronted FastAPI gateway on Oracle Cloud VPS at "
        "https://lumen-core.ai. All evidence served read-only from a "
        "static SHA-256-manifested tree."
    )
    parts.append("\n---\n# Evidence chain (SHA-256 verifiable)\n")
    parts.append(
        f"Public bundle: https://lumen-core.ai/evidence/runs/{ev['run_utc']}/  \n"
        f"Layer manifests:"
    )
    for layer in ["router", "stacker", "blender", "calibration",
                  "anomalies", "regime"]:
        parts.append(f"- {layer}/manifest.sha256.json")
    return "\n".join(parts) + "\n"


def _is_nsf_sbir(program: dict[str, Any]) -> bool:
    source_meta = program.get("source_metadata")
    if not isinstance(source_meta, dict):
        source_meta = {}
    blob = _norm_text(
        " ".join(
            [
                str(program.get("id") or ""),
                str(program.get("agency") or ""),
                str(program.get("program") or ""),
                str(source_meta.get("synopsis_excerpt") or ""),
                str((source_meta.get("agency_contact") or {}).get("name") or ""),
            ]
        )
    )
    return "nsf" in blob and (
        "sbir" in blob or "small business innovation research" in blob
    )


def render_nsf_project_pitch(program: dict, profile: dict, ev: dict) -> str:
    benchmark = ev["layers"]["benchmark"]
    breadth = ev["layers"].get("measured_breadth", {})
    return (
        f"# NSF Project Pitch - {profile['company']['dba']}\n\n"
        f"## 1. Technology innovation\n"
        f"LumenCore is an evidence-chained forecasting and decision platform that "
        f"tests multiple model families per time series, routes each series to the "
        f"best-performing family, calibrates uncertainty empirically, and detects "
        f"anomalies and regime changes. The technical risk is whether model-family "
        f"selection and uncertainty calibration can remain reliable across sectors "
        f"without hiding weak cases behind a single aggregate score.\n\n"
        f"## 2. Technical objectives and challenges\n"
        f"Phase I will: (1) deduplicate and quality-rank the measured data catalog; "
        f"(2) expand the current frozen benchmark of "
        f"{benchmark.get('n_datasets')} evaluated series; (3) run leakage-resistant "
        f"walk-forward validation and calibration; (4) quantify failure modes by "
        f"sector and regime; and (5) expose signed evidence artifacts through a "
        f"reviewable API. The local catalog currently measures "
        f"{breadth.get('artifacts_measured', 0):,} artifacts and "
        f"{breadth.get('rows_total', 0):,} rows, but those counts are not claimed "
        f"as distinct live feeds or benchmarked series.\n\n"
        f"## 3. Market opportunity\n"
        f"Initial customers are operators that need auditable forecasts rather than "
        f"opaque point predictions: energy and infrastructure teams, regulated data "
        f"operations, and enterprise risk groups. The commercialization test is a "
        f"paid pilot in which LumenCore is measured against the customer's incumbent "
        f"forecast and alert workflow on accuracy, calibration, latency, and operator "
        f"time saved.\n\n"
        f"## 4. Company and team\n"
        f"{profile['company']['legal_name']} is a U.S.-owned small business led by "
        f"{profile['pi']['name']}, {profile['pi']['title']}. The current system includes "
        f"data ingestion, multi-family forecasting, uncertainty calibration, anomaly "
        f"detection, signed evidence manifests, and deployed API surfaces. Phase I "
        f"funding would convert the research stack into a repeatable, independently "
        f"validated product with documented security and deployment controls.\n\n"
        f"## Submission status\n"
        f"This file is a draft for the NSF Project Pitch gate. It does not claim an "
        f"NSF invitation or authorization to submit a full proposal.\n"
    )


# ----------------------------------------------------------------------------
# Bundle writer
# ----------------------------------------------------------------------------
def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_bundle(program: dict, profile: dict, ev: dict,
                 elig: dict, utc: str) -> Path:
    out_dir = GRANTS / program["id"] / utc
    out_dir.mkdir(parents=True, exist_ok=True)

    budget = render_budget(program, profile)
    spotlights = build_program_spotlights(program, ev["run_utc"], max_items=6)
    app_md = render_application_md(program, profile, ev, budget)
    tech_md = render_technical_volume(program, profile, ev, spotlights=spotlights)
    comm_md = render_commercialization(program, profile, ev)
    cover = render_cover_letter(program, profile, ev)
    project_pitch = (
        render_nsf_project_pitch(program, profile, ev)
        if _is_nsf_sbir(program)
        else None
    )

    (out_dir / "application.md").write_text(app_md, encoding="utf-8")
    (out_dir / "technical_volume.md").write_text(tech_md, encoding="utf-8")
    (out_dir / "commercialization_plan.md").write_text(comm_md, encoding="utf-8")
    (out_dir / "cover_letter.md").write_text(cover, encoding="utf-8")
    if project_pitch is not None:
        (out_dir / "PROJECT_PITCH.md").write_text(project_pitch, encoding="utf-8")
    (out_dir / "budget.json").write_text(
        json.dumps(budget, indent=2), encoding="utf-8")

    application_json = {
        "schema_version": "1.0",
        "program_id": program["id"],
        "agency": program["agency"],
        "program": program["program"],
        "topic_area": program["topic_area"],
        "evidence_run_utc": ev["run_utc"],
        "applicant": profile["company"],
        "pi": profile["pi"],
        "eligibility": elig,
        "budget": budget,
        "evidence_summary": ev["layers"],
        "deadline_typical": program.get("deadline_typical"),
        "ceiling_usd": program.get("ceiling_usd"),
        "duration_months": program.get("duration_months"),
        "url": program.get("url"),
        "required_sections_provided": program.get("required_sections", []),
        "page_limits": program.get("page_limits"),
        "source_metadata": program.get("source_metadata", {}),
        "evidence_spotlights": spotlights,
        "current_state": program.get("current_state"),
        "source_verified_utc": program.get("source_verified_utc"),
        "source_verification_url": program.get("source_verification_url"),
        "opportunity_window": _program_window_assessment(program),
        "submission_readiness": profile.get("submission_readiness", {}),
    }
    (out_dir / "application.json").write_text(
        json.dumps(application_json, indent=2), encoding="utf-8")

    (out_dir / "eligibility_report.json").write_text(
        json.dumps(elig, indent=2), encoding="utf-8")

    # Approval state
    (out_dir / "approval_state.json").write_text(
        json.dumps({
            "state": "draft",
            "draft_generated_utc": datetime.now(timezone.utc).strftime(
                "%Y%m%dT%H%M%SZ"),
            "approved_utc": None,
            "submitted_utc": None,
            "submitted_by": None,
            "external_tracking_id": None,
        }, indent=2), encoding="utf-8")

    # Evidence manifest — point to live bundle
    (out_dir / "evidence_manifest.json").write_text(
        json.dumps({
            "run_utc": ev["run_utc"],
            "public_url": f"https://lumen-core.ai/evidence/runs/{ev['run_utc']}/",
            "local_path": str((ROOT / "dashboard" / "evidence" / "runs" /
                               ev["run_utc"]).resolve()),
            "layers": list(ev["layers"].keys()),
            "artifact_provenance": {
                "data_breadth_runtime_probe": _file_provenance(DATA_BREADTH_PROBE_PATH),
                "dataset_catalog": _file_provenance(DATASET_CATALOG_PATH),
                "live_source_registry": _file_provenance(LIVE_SOURCE_REGISTRY),
            },
        }, indent=2), encoding="utf-8")

    # SHA-256 manifest of this bundle
    files = [p for p in out_dir.iterdir() if p.is_file()
             and p.name != "manifest.sha256.json"]
    manifest = {
        "program_id": program["id"],
        "generated_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "evidence_run_utc": ev["run_utc"],
        "files": {p.name: {"size_bytes": p.stat().st_size,
                           "sha256": _sha256(p)} for p in files},
    }
    (out_dir / "manifest.sha256.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    return out_dir


# ----------------------------------------------------------------------------
# Queue
# ----------------------------------------------------------------------------
def update_queue() -> dict:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    catalog_payload = _read_or_none(DATA / "grant_catalog.json") or {}
    catalog_by_id = {
        str(row.get("id")): row
        for row in catalog_payload.get("programs", [])
        if isinstance(row, dict) and row.get("id")
    }
    if GRANTS.exists():
        for prog_dir in sorted(GRANTS.iterdir()):
            if not prog_dir.is_dir() or prog_dir.name.startswith("_"):
                continue
            runs = sorted([p for p in prog_dir.iterdir() if p.is_dir()])
            if not runs:
                continue
            latest = runs[-1]
            elig = _read_or_none(latest / "eligibility_report.json") or {}
            state = _read_or_none(latest / "approval_state.json") or {}
            app = _read_or_none(latest / "application.json") or {}
            source_meta = app.get("source_metadata") if isinstance(app.get("source_metadata"), dict) else {}
            catalog_program = catalog_by_id.get(prog_dir.name, {})
            window_input = dict(app)
            for key in (
                "deadline_typical",
                "current_state",
                "url",
                "source_verified_utc",
                "source_verification_url",
            ):
                if catalog_program.get(key) is not None:
                    window_input[key] = catalog_program.get(key)
            window = _program_window_assessment(window_input)
            effective_state = state.get("state", "draft")
            if effective_state == "approved" and not window.get("actionable"):
                effective_state = "stale_approved"
            items.append({
                "program_id": prog_dir.name,
                "latest_utc": latest.name,
                "state": state.get("state", "draft"),
                "effective_state": effective_state,
                "approved_utc": state.get("approved_utc"),
                "score": elig.get("score"),
                "eligible": elig.get("eligible"),
                "agency": app.get("agency"),
                "program": app.get("program"),
                "ceiling_usd": app.get("ceiling_usd"),
                "deadline_typical": window_input.get("deadline_typical"),
                "url": window_input.get("url"),
                "opportunity_window": window,
                "actionable": bool(window.get("actionable")) and bool(elig.get("eligible")),
                "source": source_meta.get("source", "catalog"),
                "opportunity_id": source_meta.get("opportunity_id"),
                "opp_num": source_meta.get("opp_num"),
                "opportunity_type": source_meta.get("opportunity_type"),
            })
    items.sort(key=lambda r: (r.get("score") or 0), reverse=True)
    scan = _read_or_none(OPPORTUNITY_SCAN_PATH) or {}
    registry = scan.get("registry") if isinstance(scan.get("registry"), dict) else {}
    scan_summary = {
        "generated_utc": scan.get("generated_utc"),
        "status": scan.get("status"),
        "query_count": scan.get("query_count"),
        "hits_total_unique": scan.get("hits_total_unique"),
        "qualified_count": scan.get("qualified_count"),
        "selected_count": scan.get("selected_count"),
        "active_sector_count": registry.get("active_sector_count"),
        "active_source_count": registry.get("active_source_count"),
    }
    index = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "n_total": len(items),
        "n_draft": sum(1 for i in items if i["state"] == "draft"),
        "n_approved": sum(1 for i in items if i["state"] == "approved"),
        "n_submitted": sum(1 for i in items if i["state"] == "submitted"),
        "n_actionable": sum(1 for i in items if i.get("actionable")),
        "n_stale_approved": sum(
            1 for i in items if i.get("effective_state") == "stale_approved"
        ),
        "opportunity_scan": scan_summary,
        "items": items,
    }
    (QUEUE_DIR / "index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8")
    return index


def approve(program_id: str) -> dict:
    prog_dir = GRANTS / program_id
    if not prog_dir.exists():
        raise SystemExit(f"no draft for {program_id}")
    runs = sorted([p for p in prog_dir.iterdir() if p.is_dir()])
    if not runs:
        raise SystemExit(f"no runs in {prog_dir}")
    latest = runs[-1]
    app = _read_or_none(latest / "application.json") or {}
    catalog_payload = _read_or_none(DATA / "grant_catalog.json") or {}
    catalog_program = next(
        (
            row
            for row in catalog_payload.get("programs", [])
            if isinstance(row, dict) and row.get("id") == program_id
        ),
        {},
    )
    window_input = dict(app)
    for key in (
        "deadline_typical",
        "current_state",
        "url",
        "source_verified_utc",
        "source_verification_url",
    ):
        if catalog_program.get(key) is not None:
            window_input[key] = catalog_program.get(key)
    window = _program_window_assessment(window_input)
    if not window.get("actionable"):
        raise SystemExit(
            f"refusing approval for non-actionable opportunity {program_id}: "
            f"{window.get('status')} ({window.get('reason')})"
        )
    state_p = latest / "approval_state.json"
    state = json.loads(state_p.read_text(encoding="utf-8"))
    state["state"] = "approved"
    state["approved_utc"] = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    state_p.write_text(json.dumps(state, indent=2), encoding="utf-8")

    APPROVED_DIR.mkdir(parents=True, exist_ok=True)
    dest = APPROVED_DIR / program_id / latest.name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(latest, dest)
    update_queue()
    print(f"[approve] {program_id} -> {dest}")
    return state


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grant", help="generate only this grant_id")
    ap.add_argument("--approve", help="flip a draft to approved")
    ap.add_argument("--list", action="store_true",
                    help="print queue summary")
    ap.add_argument("--force", action="store_true",
                    help="rebuild bundles even if state==approved (preserves "
                         "the approved state and approved_utc; refuses to "
                         "touch already-submitted grants)")
    args = ap.parse_args(argv)

    if args.approve:
        approve(args.approve)
        return 0

    if args.list:
        idx = update_queue()
        print(f"queue: {idx['n_total']} total · {idx['n_draft']} draft · "
              f"{idx['n_approved']} approved · {idx['n_submitted']} submitted")
        for it in idx["items"]:
            print(f"  [{it['state']:>9}] {it['program_id']:<32} "
                  f"score={it['score']} ${it['ceiling_usd']:,} "
                  f"deadline={it['deadline_typical']}")
        return 0

    catalog = _load_json(DATA / "grant_catalog.json")
    profile = load_application_profile()
    utc = _resolve_v2_utc()
    print(f"[factory] evidence run: {utc}")
    ev = build_evidence_summary(utc)

    catalog_programs = list(catalog["programs"])
    live_programs, scan_summary = discover_live_programs(profile, catalog_programs)
    print(
        "[factory] opportunity scan: "
        f"queries={scan_summary.get('query_count', 0)} "
        f"hits={scan_summary.get('hits_total_unique', 0)} "
        f"qualified={scan_summary.get('qualified_count', 0)} "
        f"selected={scan_summary.get('selected_count', 0)}"
    )
    programs = [*catalog_programs, *live_programs]
    if args.grant:
        programs = [p for p in programs if p["id"] == args.grant]
        if not programs:
            print(f"unknown grant id: {args.grant}")
            return 2

    n_done = 0
    n_locked = 0
    for p in programs:
        # Innovation #17: skip programs already approved/submitted so a nightly
        # rerank cannot overwrite a locked submission. Approved bundles are
        # preserved verbatim under out/grants/_approved/<id>/<utc>/.
        prog_dir = GRANTS / p["id"]
        preserved_state: dict | None = None
        if prog_dir.exists():
            runs = sorted([r for r in prog_dir.iterdir() if r.is_dir()])
            if runs:
                latest_state = _read_or_none(runs[-1] / "approval_state.json") or {}
                cur = latest_state.get("state")
                if cur == "submitted":
                    # Never overwrite a submitted package — hard lock.
                    print(f"[lock] {p['id']:<32} state=submitted — hard-locked")
                    n_locked += 1
                    continue
                if cur == "approved" and not args.force:
                    print(f"[lock] {p['id']:<32} state=approved — skipping rerank (use --force to rebuild)")
                    n_locked += 1
                    continue
                if cur == "approved" and args.force:
                    preserved_state = latest_state
                    print(f"[force] {p['id']:<32} state=approved — rebuilding with new profile")
        elig = score_eligibility(p, profile, ev)
        if not elig["eligible"]:
            print(f"[skip] {p['id']} — gaps: {elig['gaps']}")
            continue
        out_dir = write_bundle(p, profile, ev, elig, utc)
        # If this was an approved grant rebuilt with --force, restore the
        # approval state so the submission queue stays consistent.
        if preserved_state is not None:
            (out_dir / "approval_state.json").write_text(
                json.dumps(preserved_state, indent=2), encoding="utf-8")
        print(f"[draft] {p['id']:<32} score={elig['score']} -> {out_dir}")
        n_done += 1

    idx = update_queue()
    print(f"[factory] {n_done} drafts written, {n_locked} locked")
    print(f"[factory] queue: {idx['n_draft']} draft · "
          f"{idx['n_approved']} approved · {idx['n_submitted']} submitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
