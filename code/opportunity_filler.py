"""Opportunity filler bot.

Reads `out/opportunities/ranked.json` and drafts a pre-filled application
package for each high-fit opportunity into:

  out/opportunities/<source>__<id>/
    application.json     -- SF-424 field map populated from data/company_profile.json
    cover_letter.md      -- agency-specific opener
    technical_brief.md   -- 1-page narrative pulled from existing technical_volume
    SUBMIT_HOWTO.md      -- portal-specific steps for the human
    approval_state.json  -- {"state": "draft", "blockers": [...]}

The bot does NOT submit. Federal portals require human login + e-sign.
The bot makes the human's job a 5-minute review-and-paste, not a 5-hour
write-from-scratch.

Run:
  python code/opportunity_filler.py [--min-score 0.4] [--limit 20]
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "out" / "opportunities"
PROFILE = DATA / "company_profile.json"
TECH_VOLUME = ROOT / "out" / "grants" / "nsf_sbir_phase_i" / "20260505T121657Z" / "technical_volume.md"

PORTAL_HINTS = {
    "grants.gov": {
        "portal": "Grants.gov Workspace",
        "url": "https://www.grants.gov/",
        "steps": [
            "Log in at grants.gov with your AOR account",
            "Click Workspaces → Create Workspace",
            "Paste the opportunity number into the search",
            "Add the SF-424 + program-specific forms to the workspace",
            "Copy the field values from application.json below",
            "Attach attachments listed in attachments[]",
            "Validate → Sign → Submit",
        ],
    },
    "sbir.gov": {
        "portal": "Agency-specific (DoD DSIP / NIH ASSIST / etc.)",
        "url": "https://www.sbir.gov/",
        "steps": [
            "Open the solicitation URL listed below",
            "Find 'How to Apply' or 'Submit' link in the topic",
            "Register on the host portal (DoD DSIP, NASA SBIR, NIH ASSIST, etc.)",
            "Use field values from application.json for SF-424 fields",
        ],
    },
    "sam.gov": {
        "portal": "SAM.gov / agency contracting officer",
        "url": "https://sam.gov/",
        "steps": [
            "Read full notice at the URL below",
            "Note the 'Primary Contact' contracting officer email",
            "If 'Sources Sought' or 'RFI' — submit capability statement (use SF-330 outline)",
            "If 'Solicitation' — assemble proposal per Section L instructions",
            "Submit per Section M / portal instructions in notice",
        ],
    },
}


def safe_slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", str(s or "")).strip("_")
    return s[:60] or "unknown"


def build_sf424(profile: dict, opp: dict) -> dict:
    pi = profile.get("pi", {}) or {}
    award = (opp.get("raw") or {}).get("awardCeiling")
    floor = (opp.get("raw") or {}).get("awardFloor")
    return {
        "_form": "SF-424 / Federal Assistance",
        "1_type_of_submission": "Application",
        "2_type_of_application": "New",
        "3_date_received": "<auto-on-portal>",
        "4_applicant_identifier": "<auto-on-portal>",
        "5a_federal_entity_identifier": "",
        "5b_federal_award_identifier": opp.get("number") or opp.get("id"),
        "8a_legal_name": profile.get("legal_name"),
        "8b_employer_id": profile.get("ein"),
        "8c_uei": profile.get("duns_or_uei"),
        "8d_address": {
            "street1": profile.get("address_line1"),
            "city": profile.get("city"),
            "state": profile.get("state"),
            "zip": profile.get("zip"),
            "country": profile.get("country") or "United States",
        },
        "8e_organizational_unit": profile.get("dba"),
        "8f_contact": {
            "name": pi.get("name"),
            "phone": pi.get("phone"),
            "email": pi.get("email"),
        },
        "9_type_of_applicant": "M. Small Business (For-Profit)",
        "10_name_of_federal_agency": opp.get("agency"),
        "11_cfda": (opp.get("raw") or {}).get("cfdaList"),
        "12_funding_opportunity_number": opp.get("number") or opp.get("id"),
        "12_funding_opportunity_title": opp.get("title"),
        "13_competition_identification": "",
        "15_descriptive_title": f"LumenCore: {opp.get('title','')[:120]}",
        "16_congressional_districts": "TN-005",
        "17_proposed_project_dates": {
            "start": "<TBD on award>",
            "end": "<TBD on award>",
        },
        "18_estimated_funding": {
            "a_federal": award or floor or "TBD",
            "g_total": award or floor or "TBD",
        },
        "19_state_review": "Program is not covered by E.O. 12372",
        "20_delinquent_federal_debt": "No",
        "21_authorized_representative": {
            "name": pi.get("name"),
            "title": "Founder / Principal Investigator",
            "phone": pi.get("phone"),
            "email": pi.get("email"),
            "signature_date": "<sign on portal>",
        },
        "_attachments_required": [
            "Project Narrative (technical_brief.md)",
            "Budget (build from program ceiling)",
            "Bio Sketch (PI)",
            "Letters of support (if requested)",
            "USPTO patent reference 19/281,546",
        ],
    }


def cover_letter(profile: dict, opp: dict) -> str:
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    pi = profile.get("pi", {}) or {}
    return f"""# Cover Letter

**Date:** {today}

**Re:** {opp.get('title')}
**Funding Opportunity:** {opp.get('number') or opp.get('id')}
**Agency:** {opp.get('agency')}

To the Program Officer,

I am submitting an application from **{profile.get('legal_name')}**
(DBA {profile.get('dba')}, UEI {profile.get('duns_or_uei')}, CAGE
{profile.get('cage_code')}) in response to the above opportunity.

LumenCore is a per-dataset adaptive forecasting engine with a frozen 673-dataset
benchmark, empirically calibrated uncertainty bands (94.2% coverage at 80%
target), live regime-shift detection (CUSUM + variance-ratio), and a SHA-256
evidence chain. Live execution is verified on a public exchange. Patent
USPTO 19/281,546 covers the harmonic phase-locked detection method.

This proposal directly addresses the opportunity's emphasis on the keyword
matches detected by our automated fit-scoring: {", ".join(opp.get('_keyword_matches', []))}.

We are a sole-proprietor small business (1 employee, US-owned, SAM.gov
active, eligibility verified) and meet the program's eligibility criteria.

Respectfully,
{pi.get('name')}
{pi.get('email')} · {pi.get('phone')}
"""


def technical_brief(opp: dict, tech_master: str | None) -> str:
    matches = ", ".join(opp.get("_keyword_matches", []))
    intro = f"""# Technical Brief — {opp.get('title')}

**Opportunity:** {opp.get('number') or opp.get('id')} ({opp.get('source')})
**Agency:** {opp.get('agency')}
**Close date:** {opp.get('close_date')}
**Fit score:** {opp.get('_fit_score')} (matched: {matches})

---

## Why this fit

Our engine directly addresses the opportunity language detected during
keyword scoring: **{matches}**. Below is a one-page distillation of the
full technical volume.

---
"""
    body = (tech_master or "")[:6000]  # trim to ~1 page if long
    return intro + body + "\n\n---\n\n*Full technical volume on request.*\n"


def submit_howto(opp: dict, sf424: dict) -> str:
    hint = PORTAL_HINTS.get(opp.get("source", ""), PORTAL_HINTS["grants.gov"])
    steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(hint["steps"]))
    field_lines = []
    for k, v in sf424.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict):
            for kk, vv in v.items():
                field_lines.append(f"- **{k}.{kk}:** `{vv}`")
        elif isinstance(v, list):
            field_lines.append(f"- **{k}:** {v}")
        else:
            field_lines.append(f"- **{k}:** `{v}`")
    fields_md = "\n".join(field_lines)
    return f"""# How to Submit — {opp.get('title')}

**Portal:** {hint['portal']}
**URL:** {hint['url']}
**Notice URL:** {opp.get('url')}
**Close date:** {opp.get('close_date')}

## Steps

{steps_md}

## SF-424 field values (copy / paste)

{fields_md}

## Attachments to upload

{chr(10).join('- ' + a for a in sf424.get('_attachments_required', []))}

---

*This file is auto-generated by `code/opportunity_filler.py`. Re-run after
profile or scoring updates.*
"""


def fill_one(opp: dict, profile: dict, tech_master: str | None) -> Path:
    src = opp.get("source") or "unknown"
    oid = safe_slug(opp.get("id"))
    out_dir = OUT / f"{safe_slug(src)}__{oid}"
    out_dir.mkdir(parents=True, exist_ok=True)

    sf424 = build_sf424(profile, opp)
    (out_dir / "application.json").write_text(
        json.dumps(sf424, indent=2, default=str), encoding="utf-8")
    (out_dir / "cover_letter.md").write_text(
        cover_letter(profile, opp), encoding="utf-8")
    (out_dir / "technical_brief.md").write_text(
        technical_brief(opp, tech_master), encoding="utf-8")
    (out_dir / "SUBMIT_HOWTO.md").write_text(
        submit_howto(opp, sf424), encoding="utf-8")

    state = {
        "state": "draft",
        "fit_score": opp.get("_fit_score"),
        "matched_keywords": opp.get("_keyword_matches"),
        "drafted_utc": datetime.now(timezone.utc).isoformat(),
        "blockers": _check_blockers(profile, opp),
        "ready_for_human_review": True,
    }
    (out_dir / "approval_state.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8")
    return out_dir


def _check_blockers(profile: dict, opp: dict) -> list[str]:
    blockers: list[str] = []
    must = ["legal_name", "duns_or_uei", "ein", "address_line1",
            "city", "state", "zip"]
    for f in must:
        if not profile.get(f):
            blockers.append(f"profile missing: {f}")
    if (profile.get("sam_gov_status") or "").lower() != "active":
        blockers.append("SAM.gov status not active")
    cd = opp.get("close_date") or ""
    if not cd:
        blockers.append("close_date unknown — verify on portal")
    return blockers


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=float, default=0.40)
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    ranked_path = OUT / "ranked.json"
    if not ranked_path.exists():
        print("[fill] no ranked.json -- run opportunity_harvester.py first")
        return 1

    profile_full = json.loads(PROFILE.read_text(encoding="utf-8"))
    # Profile schema nests fields under "company"; flatten for SF-424 mapping.
    profile = dict(profile_full.get("company") or {})
    profile["pi"] = profile_full.get("pi") or {}
    tech_master = TECH_VOLUME.read_text(encoding="utf-8") if TECH_VOLUME.exists() else None
    payload = json.loads(ranked_path.read_text(encoding="utf-8"))
    records = [r for r in payload.get("records", []) if r.get("_fit_score", 0) >= args.min_score]
    records = records[: args.limit]

    print(f"[fill] drafting {len(records)} packages (min_score={args.min_score})")
    drafted: list[dict] = []
    for rec in records:
        d = fill_one(rec, profile, tech_master)
        drafted.append({
            "id": rec.get("id"),
            "source": rec.get("source"),
            "title": rec.get("title"),
            "fit_score": rec.get("_fit_score"),
            "out_dir": str(d.relative_to(ROOT)),
        })
        print(f"  [draft] {rec.get('source'):12} {str(rec.get('id')):>10}  "
              f"score={rec.get('_fit_score')}  -> {d.name}")

    summary = OUT / "filler_summary.json"
    tmp = summary.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "min_score": args.min_score,
        "drafted_count": len(drafted),
        "drafted": drafted,
    }, indent=2), encoding="utf-8")
    tmp.replace(summary)
    print(f"[fill] summary -> {summary.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
