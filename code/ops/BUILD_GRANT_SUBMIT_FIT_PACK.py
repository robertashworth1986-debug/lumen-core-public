from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_DIR = ROOT / "out" / "ops" / "grant_submit_fit_pack"
QUEUE_PATH = ROOT / "out" / "grant_approval_queue.json"
PROFILE_PATH = ROOT / "code" / "grants_profile_lumencore.json"
SKIP_PACK_PATH = ROOT / "out" / "ops" / "skips_grant_autofill" / "skips_grant_autofill_latest.json"
RANKED_PATH = ROOT / "out" / "grants" / "grants_ranked_v2.json"
BLUEPRINT_VAULT_PATH = ROOT / "out" / "ops" / "gov_blueprint_vault" / "gov_blueprint_vault_latest.json"
KEY_ENV_FILE = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"

GRANTS_API = "https://api.grants.gov/v1/api/search2"
GRANTS_SYNC = "https://api.grants.gov/v1/api/sync"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(value or "")).strip("_").upper() or "SKIP"


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _pick_first(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        txt = str(value).strip()
        if txt:
            return txt
    return ""


def _extract_blueprint_terms(payload: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    if not isinstance(payload, dict):
        return terms

    direct = payload.get("grant_focus_terms", [])
    if isinstance(direct, list):
        terms.extend(str(x) for x in direct if str(x).strip())

    assets = payload.get("assets", [])
    if isinstance(assets, list):
        for row in assets:
            if not isinstance(row, dict):
                continue
            tags = row.get("grant_tags", [])
            if isinstance(tags, list):
                terms.extend(str(x) for x in tags if str(x).strip())
            domain = str(row.get("domain") or "").strip()
            if domain:
                terms.extend(token for token in domain.replace("_", " ").split(" ") if token)

    out: list[str] = []
    seen: set[str] = set()
    for raw in terms:
        token = _norm(str(raw).replace("_", " "))
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _blueprint_alignment(text_blob: str, terms: list[str], limit: int = 14) -> tuple[list[str], float]:
    blob = _norm(text_blob)
    if not blob or not terms:
        return [], 0.0

    matches: list[str] = []
    for term in terms:
        token = _norm(term)
        if token and token in blob:
            matches.append(token)

    deduped: list[str] = []
    seen: set[str] = set()
    for token in matches:
        if token in seen:
            continue
        seen.add(token)
        deduped.append(token)

    deduped = deduped[: max(1, int(limit))]
    score = min(100.0, float(len(deduped)) * 6.0)
    return deduped, round(score, 2)


def _load_key_map() -> dict[str, str]:
    file_keys: dict[str, str] = {}
    if KEY_ENV_FILE.exists():
        try:
            for raw in KEY_ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                file_keys[key.strip()] = value.strip()
        except Exception:
            pass

    grants_key = _pick_first(
        os.environ.get("GRANTS_GOV_API_KEY"),
        os.environ.get("GRANTS_API_KEY"),
        os.environ.get("GRANTS_GOV_KEY"),
        file_keys.get("GRANTS_GOV_API_KEY"),
        file_keys.get("GRANTS_API_KEY"),
        file_keys.get("GRANTS_GOV_KEY"),
    )
    sam_key = _pick_first(
        os.environ.get("SAM_GOV_API_KEY"),
        os.environ.get("SAM_API_KEY"),
        os.environ.get("SAM_KEY"),
        file_keys.get("SAM_GOV_API_KEY"),
        file_keys.get("SAM_API_KEY"),
        file_keys.get("SAM_KEY"),
    )
    return {
        "GRANTS_GOV_API_KEY": grants_key,
        "SAM_GOV_API_KEY": sam_key,
    }


def _api_post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    key_map = _load_key_map()
    grants_key = str(key_map.get("GRANTS_GOV_API_KEY") or "").strip()
    if grants_key:
        headers["x-api-key"] = grants_key
    req = Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except HTTPError as e:
        raise RuntimeError(f"Grants.gov HTTP {e.code}: {e.reason}") from e
    except URLError as e:
        raise RuntimeError(f"Grants.gov network error: {e.reason}") from e


def _hard_eligibility_mismatch_reason(blob: str, opp_num: str, title: str) -> str:
    text = _norm(" ".join([blob or "", opp_num or "", title or ""]))

    hard_patterns = [
        "individual applicants only",
        "applicants must be alumni",
        "exchange program alumni",
        "alumni engagement innovation fund",
        "u.s. citizen alumni are not eligible",
        "us citizen alumni are not eligible",
        "not-for-profit, non-governmental organizations are not eligible",
    ]
    for pat in hard_patterns:
        if pat in text:
            return pat.replace(" ", "_")

    has_individuals = "individual" in text
    has_smallbiz = ("small business" in text) or ("for-profit" in text) or ("for profit" in text)
    if has_individuals and not has_smallbiz:
        return "individual_only_without_small_business_eligibility"

    return ""


def load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def _parse_search_hits(resp: dict[str, Any]) -> list[dict[str, Any]]:
    data = resp.get("data", resp) if isinstance(resp, dict) else {}
    if not isinstance(data, dict):
        return []
    for key in ("oppHits", "rows", "hits", "opportunities"):
        rows = data.get(key)
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    return []


def _search_hit_by_opp_num(opp_num: str) -> dict[str, Any]:
    payloads = [
        {
            "rows": 50,
            "keyword": "",
            "oppNum": opp_num,
            "aln": "",
            "oppStatuses": "forecasted|posted|closed",
            "sortBy": "closeDate|asc",
            "eligibilities": "",
            "agencies": "",
            "fundingCategories": "",
            "fundingInstruments": "",
            "searchOnly": False,
            "resultType": "json",
        },
        {
            "rows": 50,
            "keyword": opp_num,
            "oppNum": "",
            "aln": "",
            "oppStatuses": "forecasted|posted|closed",
            "sortBy": "closeDate|asc",
            "eligibilities": "",
            "agencies": "",
            "fundingCategories": "",
            "fundingInstruments": "",
            "searchOnly": False,
            "resultType": "json",
        },
    ]

    for payload in payloads:
        try:
            resp = _api_post(GRANTS_API, payload)
        except Exception:
            continue
        hits = _parse_search_hits(resp)
        exact = [h for h in hits if _norm(h.get("oppNum")) == _norm(opp_num)]
        if exact:
            return exact[0]
        if hits:
            return hits[0]

    return {}


def _fetch_detail(opportunity_id: int | None) -> dict[str, Any]:
    if not opportunity_id:
        return {}
    payload = {"opportunityId": int(opportunity_id)}
    try:
        resp = _api_post(GRANTS_SYNC, payload)
    except Exception:
        return {}
    data = resp.get("data") if isinstance(resp, dict) else {}
    return data if isinstance(data, dict) else {}


def _detail_list(detail: dict[str, Any], parent_key: str, field_key: str = "description") -> list[str]:
    syn = _as_dict(detail.get("synopsis"))
    rows = syn.get(parent_key)
    if not isinstance(rows, list):
        return []
    out: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            value = str(row.get(field_key) or "").strip()
            if value:
                out.append(value)
    return out


def _fit_status(
    opp_num: str,
    title: str,
    agency: str,
    applicant_types: list[str],
    eligibility_text: str,
    description: str,
) -> tuple[str, str]:
    blob = _norm(" ".join([title, agency, eligibility_text, description, " ".join(applicant_types), opp_num]))
    mismatch = _hard_eligibility_mismatch_reason(blob, opp_num, title)
    if mismatch:
        return "HARD_EXCLUDE", f"hard_fit:{mismatch}"

    if applicant_types:
        joined = _norm(" ".join(applicant_types))
        positive = ["small business", "small businesses", "for-profit", "for profit", "business organization"]
        neutral = ["all", "eligible applicants", "others", "unrestricted"]
        has_positive = any(p in joined for p in positive)
        has_neutral = any(n in joined for n in neutral)
        if not has_positive and not has_neutral:
            return "MANUAL_CHECK", "applicant_types_need_manual_confirmation"

    return "FIT_LIKELY", "passes_profile_gates"


def _submit_url(opp_num: str, is_skip: bool, fallback_url: str = "") -> str:
    if is_skip:
        return "https://helloskip.com/"

    source = str(fallback_url or "").strip()
    source_norm = _norm(source)
    if source and source.startswith("http"):
        if (
            "grants.gov/search-results-detail/" in source_norm
            or "simpler.grants.gov/opportunity/" in source_norm
            or "smartsimple" in source_norm
        ):
            return source

    token = str(opp_num or "").strip()
    if token:
        return f"https://www.grants.gov/search-results-detail/{quote(token)}"

    if source and source.startswith("http"):
        return source

    return "https://www.grants.gov/search-grants"


def _find_skip_variant(skip_payload: dict[str, Any], opp_num: str, title: str) -> dict[str, Any]:
    variants = skip_payload.get("opportunity_variants", []) if isinstance(skip_payload, dict) else []
    if not isinstance(variants, list):
        return {}
    for row in variants:
        if not isinstance(row, dict):
            continue
        opportunity_id = str(row.get("opportunity_id") or "")
        if f"SKIP-{_slug(opportunity_id)}" == opp_num:
            return row
    for row in variants:
        if not isinstance(row, dict):
            continue
        if _norm(row.get("title")) == _norm(title):
            return row
    return {}


def _dedupe_queue(queue_items: list[dict[str, Any]], state: str) -> list[dict[str, Any]]:
    filtered = [
        row
        for row in queue_items
        if isinstance(row, dict) and _norm(row.get("approval_state")) == _norm(state)
    ]
    by_opp: dict[str, dict[str, Any]] = {}
    for row in filtered:
        opp = _as_dict(row.get("opportunity"))
        opp_num = str(opp.get("opp_num") or "")
        if not opp_num:
            continue
        score = _safe_float(opp.get("final_score"), -999999.0)
        existing = by_opp.get(opp_num)
        if existing is None:
            by_opp[opp_num] = row
            continue
        existing_opp = _as_dict(existing.get("opportunity"))
        existing_score = _safe_float(existing_opp.get("final_score"), -999999.0)
        if score > existing_score:
            by_opp[opp_num] = row
    out = list(by_opp.values())
    out.sort(
        key=lambda r: (
            _safe_float((r.get("opportunity") or {}).get("days_to_close"), 9999.0),
            -_safe_float((r.get("opportunity") or {}).get("final_score"), 0.0),
        )
    )
    return out


def _ranked_map() -> dict[str, dict[str, Any]]:
    payload = load_json(RANKED_PATH)
    ranked_rows = payload.get("ranked", []) if isinstance(payload, dict) else []
    if not isinstance(ranked_rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in ranked_rows:
        if not isinstance(row, dict):
            continue
        opp_num = str(row.get("opp_num") or "").strip().upper()
        if not opp_num:
            continue
        out[opp_num] = row
    return out


def build_pack(state: str, limit: int) -> dict[str, Any]:
    queue_raw = load_json(QUEUE_PATH)
    queue_items = queue_raw if isinstance(queue_raw, list) else []
    profile = load_json(PROFILE_PATH)
    skip_payload = load_json(SKIP_PACK_PATH)
    blueprint_payload = load_json(BLUEPRINT_VAULT_PATH)
    blueprint_terms = _extract_blueprint_terms(blueprint_payload if isinstance(blueprint_payload, dict) else {})
    ranked_by_opp = _ranked_map()
    key_map = _load_key_map()

    selected = _dedupe_queue(queue_items, state=state)
    if limit > 0:
        selected = selected[:limit]

    org = _as_dict(profile.get("organization")) if isinstance(profile, dict) else {}
    defaults = _as_dict(profile.get("prefill_defaults")) if isinstance(profile, dict) else {}

    entries: list[dict[str, Any]] = []
    fit_counts = {"FIT_LIKELY": 0, "MANUAL_CHECK": 0, "HARD_EXCLUDE": 0}
    blueprint_aligned_count = 0

    for row in selected:
        opp = _as_dict(row.get("opportunity"))
        opp_num = str(opp.get("opp_num") or "")
        opp_url = str(opp.get("url") or "")
        title = str(opp.get("title") or "")
        agency = str(opp.get("agency") or "")
        close_date = str(opp.get("close_date") or "")
        days_to_close = int(_safe_float(opp.get("days_to_close"), 9999.0))
        award_ceiling = _safe_float(opp.get("award_ceiling_usd"), 0.0)
        is_skip = _norm(opp_num).startswith("skip-")

        applicant_types: list[str] = []
        funding_instruments: list[str] = []
        funding_categories: list[str] = []
        eligibility_text = ""
        description = ""
        fit_status = "FIT_LIKELY"
        fit_reason = "passes_profile_gates"
        wants: list[str] = []
        answer_focus: list[str] = []

        if is_skip:
            variant = _find_skip_variant(skip_payload, opp_num, title)
            required_tags = variant.get("eligibility_required_tags", []) if isinstance(variant, dict) else []
            required_tags = [str(x) for x in required_tags if str(x).strip()]
            conditional_tags = [t for t in required_tags if "requirement" in _norm(t)]

            if conditional_tags:
                fit_status = "MANUAL_CHECK"
                fit_reason = "skip_conditional_requirement"
            else:
                fit_status = "FIT_LIKELY"
                fit_reason = "skip_profile_match"

            wants.extend([f"Eligibility tag: {t}" for t in required_tags])
            deadline_note = str(variant.get("deadline_note") or "")
            if deadline_note:
                wants.append(f"Program deadline note: {deadline_note}")
            paste_answer = str(variant.get("paste_ready_answer") or "")
            if paste_answer:
                answer_focus.append(paste_answer)
            angle = str(variant.get("autofill_angle") or "")
            if angle:
                answer_focus.append(f"Primary angle: {angle}")
        else:
            ranked_row = ranked_by_opp.get(opp_num.strip().upper(), {})
            if isinstance(ranked_row, dict) and ranked_row:
                raw = _as_dict(ranked_row.get("raw"))
                agency = str(raw.get("agencyName") or raw.get("agency") or ranked_row.get("agency") or agency)
                title = str(raw.get("title") or ranked_row.get("title") or title)
                close_date = str(raw.get("closeDate") or ranked_row.get("close_date") or close_date)
                description = str(raw.get("description") or raw.get("synopsis") or "")
                eligibility_text = str(raw.get("eligibilities") or "")
                cfda = raw.get("cfdaList") if isinstance(raw.get("cfdaList"), list) else []
                if cfda:
                    wants.append(f"Assistance listing references: {', '.join(str(x) for x in cfda if str(x).strip())}")

            hit = _search_hit_by_opp_num(opp_num)
            found_live_hit = bool(hit)
            if hit:
                agency = str(hit.get("agencyName") or agency)
                title = str(hit.get("title") or hit.get("oppTitle") or title)
                close_date = str(hit.get("closeDate") or close_date)
                description = str(hit.get("description") or hit.get("synopsis") or "")
                eligibility_text = str(hit.get("eligibilities") or "")
                award_ceiling = _safe_float(hit.get("awardCeiling"), award_ceiling)

                opp_id = hit.get("opportunityId")
                try:
                    opp_id_int = int(str(opp_id)) if opp_id is not None and str(opp_id).strip() else None
                except Exception:
                    opp_id_int = None
                detail = _fetch_detail(opp_id_int)
                applicant_types = _detail_list(detail, "applicantTypes")
                funding_instruments = _detail_list(detail, "fundingInstruments")
                funding_categories = _detail_list(detail, "fundingActivityCategories")
                synopsis = _as_dict(detail.get("synopsis"))
                detail_elig = str(synopsis.get("applicantEligibilityDesc") or "")
                detail_synopsis = str(synopsis.get("synopsisDesc") or "")
                eligibility_text = "\n".join(x for x in [eligibility_text, detail_elig] if x.strip())
                if detail_synopsis and len(description) < len(detail_synopsis):
                    description = detail_synopsis

            fit_status, fit_reason = _fit_status(
                opp_num=opp_num,
                title=title,
                agency=agency,
                applicant_types=applicant_types,
                eligibility_text=eligibility_text,
                description=description,
            )

            if not found_live_hit and fit_status == "FIT_LIKELY":
                fit_status = "MANUAL_CHECK"
                fit_reason = "unable_to_fetch_live_requirements"

            ranked_reasons = ranked_row.get("reasons") if isinstance(ranked_row, dict) else []
            if isinstance(ranked_reasons, list) and ranked_reasons:
                reasons_text = ", ".join(str(x) for x in ranked_reasons if str(x).strip())
                if reasons_text:
                    wants.append(f"Ranking relevance signals: {reasons_text}")

            if applicant_types:
                wants.append(f"Eligible applicant types: {', '.join(applicant_types)}")
            if funding_instruments:
                wants.append(f"Funding instruments: {', '.join(funding_instruments)}")
            if funding_categories:
                wants.append(f"Funding categories: {', '.join(funding_categories)}")
            if eligibility_text:
                wants.append(f"Eligibility guidance: {eligibility_text[:420].replace(chr(10), ' ')}")
            if description:
                wants.append(f"Program intent: {description[:520].replace(chr(10), ' ')}")

            answer_focus.extend(
                [
                    f"Lead with this title-specific alignment: {defaults.get('project_title', 'LumenCore infrastructure risk intelligence')}.",
                    "Answer technical approach with measurable pre-failure detection outcomes and validation evidence.",
                    "Use budget narrative lines mapped to personnel, compute, contractual, and compliance overhead.",
                    "Confirm UEI/EIN/SAM details exactly as registered before final submit.",
                ]
            )

        alignment_blob = " ".join(
            [
                title,
                agency,
                eligibility_text,
                description,
                " ".join(applicant_types),
                " ".join(funding_categories),
                " ".join(wants),
                " ".join(answer_focus),
            ]
        )
        blueprint_matches, blueprint_alignment_score = _blueprint_alignment(alignment_blob, blueprint_terms)
        if blueprint_matches:
            blueprint_aligned_count += 1
            wants.append(f"Blueprint alignment terms: {', '.join(blueprint_matches)}")
            answer_focus.append(
                "Bind narrative to Harmonic + Alpha Lock + Harmonic Edge Lock operating family with evidence-first validation milestones."
            )

        fit_counts[fit_status] = fit_counts.get(fit_status, 0) + 1

        entries.append(
            {
                "ticket_id": str(row.get("ticket_id") or ""),
                "opp_num": opp_num,
                "title": title,
                "agency": agency,
                "close_date": close_date,
                "days_to_close": days_to_close,
                "award_ceiling_usd": award_ceiling,
                "source_channel": "skip" if is_skip else "grants_gov",
                "submit_url": _submit_url(opp_num, is_skip=is_skip, fallback_url=opp_url),
                "fit_status": fit_status,
                "fit_reason": fit_reason,
                "blueprint_alignment_score": blueprint_alignment_score,
                "blueprint_term_matches": blueprint_matches,
                "what_opportunity_wants": wants,
                "answer_strategy": answer_focus,
                "must_answer_fields": [
                    "Legal entity name and identifiers (UEI, EIN, SAM)",
                    "Eligibility confirmation statement for this opportunity",
                    "Project abstract and problem statement tied to program intent",
                    "Technical approach, timeline, deliverables, and measurable outcomes",
                    "Budget totals and budget justification by cost category",
                    "Key personnel qualifications and operational evidence references",
                ],
            }
        )

    payload: dict[str, Any] = {
        "generated_utc": now_iso(),
        "scope": "grant_submit_fit_pack",
        "source_queue_path": str(QUEUE_PATH),
        "source_profile_path": str(PROFILE_PATH),
        "state_filter": state,
        "limit": limit,
        "organization": {
            "legal_name": str(org.get("legal_name") or "LumenCore"),
            "uei": str(org.get("uei") or ""),
            "ein": str(org.get("ein") or ""),
            "entity_type": str(org.get("entity_type") or "for_profit_small_business"),
            "sam_registered": bool(org.get("sam_registered", False)),
        },
        "summary": {
            "selected_opportunities": len(entries),
            "fit_likely": fit_counts.get("FIT_LIKELY", 0),
            "manual_check": fit_counts.get("MANUAL_CHECK", 0),
            "hard_exclude": fit_counts.get("HARD_EXCLUDE", 0),
            "blueprint_aligned": blueprint_aligned_count,
        },
        "blueprint_vault": {
            "path": str(BLUEPRINT_VAULT_PATH),
            "present": bool(isinstance(blueprint_payload, dict) and blueprint_payload),
            "generated_utc": (
                blueprint_payload.get("generated_utc")
                if isinstance(blueprint_payload, dict)
                else None
            ),
            "focus_term_count": len(blueprint_terms),
        },
        "key_status": {
            "grants_gov_api_key_present": bool(str(key_map.get("GRANTS_GOV_API_KEY") or "").strip()),
            "sam_gov_api_key_present": bool(str(key_map.get("SAM_GOV_API_KEY") or "").strip()),
        },
        "opportunities": entries,
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    items = payload.get("opportunities", []) if isinstance(payload, dict) else []
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(items, list):
        items = []

    lines: list[str] = []
    lines.append("# Grant Submit Fit Pack")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"State Filter: {payload.get('state_filter', '')}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Selected opportunities: {summary.get('selected_opportunities', 0)}")
    lines.append(f"- Fit likely: {summary.get('fit_likely', 0)}")
    lines.append(f"- Manual check: {summary.get('manual_check', 0)}")
    lines.append(f"- Hard exclude: {summary.get('hard_exclude', 0)}")
    lines.append(f"- Blueprint aligned: {summary.get('blueprint_aligned', 0)}")
    lines.append("")

    for i, row in enumerate(items, start=1):
        if not isinstance(row, dict):
            continue
        lines.append(f"## {i}. {row.get('opp_num', '')} - {row.get('title', '')}")
        lines.append(f"- Agency: {row.get('agency', '')}")
        lines.append(f"- Fit Status: {row.get('fit_status', '')}")
        lines.append(f"- Fit Reason: {row.get('fit_reason', '')}")
        lines.append(f"- Blueprint Alignment Score: {row.get('blueprint_alignment_score', 0)}")
        lines.append(f"- Blueprint Terms: {', '.join(str(x) for x in row.get('blueprint_term_matches', []))}")
        lines.append(f"- Close Date: {row.get('close_date', '')}")
        lines.append(f"- Days To Close: {row.get('days_to_close', '')}")
        lines.append(f"- Award Ceiling USD: {row.get('award_ceiling_usd', '')}")
        lines.append(f"- Submit URL: {row.get('submit_url', '')}")
        lines.append("- What This Opportunity Wants:")
        wants = row.get("what_opportunity_wants", [])
        if isinstance(wants, list):
            for w in wants:
                lines.append(f"  - {w}")
        lines.append("- Answer Strategy:")
        strategy = row.get("answer_strategy", [])
        if isinstance(strategy, list):
            for s in strategy:
                lines.append(f"  - {s}")
        lines.append("- Must Answer Fields:")
        fields = row.get("must_answer_fields", [])
        if isinstance(fields, list):
            for f in fields:
                lines.append(f"  - {f}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build grant submit fit pack from queue and live opportunity details.")
    ap.add_argument("--state", default="APPROVED", help="Queue approval state to include (default: APPROVED)")
    ap.add_argument("--limit", type=int, default=120, help="Max unique opportunities to include")
    args = ap.parse_args()

    payload = build_pack(state=str(args.state), limit=int(args.limit))
    ts = now_tag()

    json_ts = OUT_DIR / f"grant_submit_fit_pack_{ts}.json"
    md_ts = OUT_DIR / f"grant_submit_fit_pack_{ts}.md"
    json_latest = OUT_DIR / "grant_submit_fit_pack_latest.json"
    md_latest = OUT_DIR / "grant_submit_fit_pack_latest.md"

    write_json(json_ts, payload)
    write_json(json_latest, payload)
    md = render_markdown(payload)
    write_text(md_ts, md)
    write_text(md_latest, md)

    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    print("BUILD_GRANT_SUBMIT_FIT_PACK")
    print(f"selected={summary.get('selected_opportunities', 0)}")
    print(f"fit_likely={summary.get('fit_likely', 0)}")
    print(f"manual_check={summary.get('manual_check', 0)}")
    print(f"hard_exclude={summary.get('hard_exclude', 0)}")
    print(f"json={json_latest}")
    print(f"md={md_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
