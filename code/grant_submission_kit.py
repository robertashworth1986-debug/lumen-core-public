"""
grant_submission_kit.py
========================
Submission preflight + escort for federal grant packages.

Federal grant submission has a hard human-in-the-loop wall:
- SAM.gov UEI registration (one-time, ~10 business days, free)
- Grants.gov account linked to UEI
- AOR (Authorized Organization Representative) signature
- E-Biz POC MFA each submission

We cannot legally bypass that. What we CAN do:
1. Validate the package is complete and ready
2. Surface every TO_BE_FILLED field so the user knows what's blocking
3. Emit a copy-paste-ready SF-424 field map
4. Generate a per-agency SUBMIT_HOWTO.md with portal URL + steps
5. Compute deadline countdown + risk flag
6. Write a `submission_packet.json` snapshot that locks the run

Usage from grants_api.py:
    from grant_submission_kit import build_preflight, write_submission_kit
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
GRANTS = ROOT / "out" / "grants"
DATA = ROOT / "data"

# Per-agency submission portals + AOR-required steps. Keyed by program_id prefix
# matching the grant_catalog. URLs are public landing pages (safe to open).
PORTAL_REGISTRY: dict[str, dict[str, Any]] = {
    "doe_sbir": {
        "agency": "U.S. Department of Energy",
        "portal_url": "https://science.osti.gov/sbir/Funding-Opportunities",
        "submission_system": "Grants.gov Workspace + DOE PAMS",
        "pams_url": "https://pamspublic.science.energy.gov/",
        "requires": ["UEI", "SAM.gov active", "Grants.gov account",
                     "PAMS account", "AOR signature"],
    },
    "nist_sbir": {
        "agency": "NIST",
        "portal_url": "https://www.nist.gov/sbir",
        "submission_system": "Grants.gov Workspace",
        "requires": ["UEI", "SAM.gov active", "Grants.gov account", "AOR signature"],
    },
    "nsf_sbir": {
        "agency": "National Science Foundation",
        "portal_url": "https://seedfund.nsf.gov/",
        "submission_system": "NSF Project Pitch (online form) → Research.gov full proposal",
        "pitch_url": "https://seedfund.nsf.gov/project-pitch/",
        "requires": ["NSF Project Pitch (3-page) FIRST", "Pitch invite",
                     "UEI", "SAM.gov active", "Research.gov account"],
        "note": "NSF SBIR uses a 2-step gate: short Project Pitch first; only invited pitches submit a full proposal.",
    },
    "afwerx_sbir": {
        "agency": "U.S. Air Force / AFWERX",
        "portal_url": "https://afwerx.com/",
        "submission_system": "DSIP (Defense SBIR/STTR Innovation Portal)",
        "dsip_url": "https://www.dodsbirsttr.mil/submissions/",
        "requires": ["UEI", "SAM.gov active", "DSIP account", "AOR signature"],
    },
    "arpa_e": {
        "agency": "ARPA-E",
        "portal_url": "https://arpa-e-foa.energy.gov/",
        "submission_system": "ARPA-E eXCHANGE",
        "requires": ["UEI", "SAM.gov active", "ARPA-E eXCHANGE account",
                     "Concept Paper FIRST (gating)", "AOR signature"],
    },
    "darpa": {
        "agency": "DARPA",
        "portal_url": "https://www.darpa.mil/work-with-us/opportunities",
        "submission_system": "BAA-specific (Grants.gov, BIDS, or DARPA-IPT)",
        "requires": ["UEI", "SAM.gov active", "BAA-specific account",
                     "Abstract first (most BAAs)", "AOR signature"],
    },
    "nsf_pfi": {
        "agency": "NSF",
        "portal_url": "https://new.nsf.gov/funding/opportunities/partnerships-innovation-pfi",
        "submission_system": "Research.gov",
        "requires": ["UEI", "SAM.gov active", "Research.gov account",
                     "Letter of Intent (recommended)", "AOR signature"],
    },
    "doe_phase_ii": {
        "agency": "U.S. Department of Energy",
        "portal_url": "https://science.osti.gov/sbir",
        "submission_system": "Grants.gov + PAMS (Phase I awardees only)",
        "requires": ["Active Phase I award", "Phase I report",
                     "UEI / SAM still active", "AOR signature"],
    },
}


def _portal_for(program_id: str) -> dict[str, Any]:
    for prefix, info in PORTAL_REGISTRY.items():
        if program_id.startswith(prefix):
            return info
    return {
        "agency": "Unknown",
        "portal_url": "https://www.grants.gov/",
        "submission_system": "Grants.gov Workspace",
        "requires": ["UEI", "SAM.gov active", "Grants.gov account", "AOR signature"],
    }


def _scan_to_be_filled(obj: Any, path: str = "") -> list[str]:
    """Recursively find every leaf with value 'TO_BE_FILLED' or starting with it."""
    missing: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            missing.extend(_scan_to_be_filled(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            missing.extend(_scan_to_be_filled(v, f"{path}[{i}]"))
    elif isinstance(obj, str) and obj.strip().upper().startswith("TO_BE_FILLED"):
        missing.append(path)
    return missing


def _days_to_deadline(deadline_str: str | None) -> dict[str, Any]:
    """Best-effort parse of catalog deadline_typical."""
    if not deadline_str:
        return {"deadline": None, "days_remaining": None, "rolling": False, "parseable": False}
    s = deadline_str.lower()
    if "rolling" in s or "follow-on" in s or "post-phase" in s:
        return {"deadline": deadline_str, "days_remaining": None,
                "rolling": True, "parseable": True}
    # Try common federal listing date formats anywhere in the string.
    import re as _re
    # YYYY-MM-DD
    m_iso = _re.search(r"(20\d{2})-(\d{2})-(\d{2})", deadline_str)
    if m_iso:
        try:
            d = datetime(
                int(m_iso.group(1)),
                int(m_iso.group(2)),
                int(m_iso.group(3)),
                tzinfo=timezone.utc,
            )
            now = datetime.now(timezone.utc)
            delta = (d - now).days
            return {
                "deadline": d.date().isoformat(),
                "days_remaining": delta,
                "rolling": False,
                "parseable": True,
                "risk": "expired" if delta < 0 else
                        "critical" if delta < 14 else
                        "soon" if delta < 45 else "ok",
            }
        except Exception:
            pass

    # MM/DD/YYYY and MM-DD-YYYY
    m_us = _re.search(r"(\d{1,2})[/-](\d{1,2})[/-](20\d{2})", deadline_str)
    if m_us:
        try:
            month = int(m_us.group(1))
            day = int(m_us.group(2))
            year = int(m_us.group(3))
            d = datetime(year, month, day, tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = (d - now).days
            return {
                "deadline": d.date().isoformat(),
                "days_remaining": delta,
                "rolling": False,
                "parseable": True,
                "risk": "expired" if delta < 0 else
                        "critical" if delta < 14 else
                        "soon" if delta < 45 else "ok",
            }
        except Exception:
            pass
    return {"deadline": deadline_str, "days_remaining": None,
            "rolling": False, "parseable": False}


def _sf424_field_map(app: dict[str, Any]) -> dict[str, Any]:
    """Map our application.json fields to SF-424 form field labels.

    The SF-424 (R&R) is the canonical federal grant cover form. This map gives
    the user copy-paste-ready values keyed to the exact form field labels they
    will see in Grants.gov Workspace."""
    appl = app.get("applicant", {})
    pi = app.get("pi", {})
    budget = app.get("budget", {})
    return {
        # Section 1
        "1. Type of Submission": "Application",
        "2. Type of Application": "New",
        # Section 4
        "4.a Federal Identifier": "(leave blank — assigned by agency)",
        # Section 5 — Applicant Info
        "5. Applicant Information / Legal Name": appl.get("legal_name"),
        "5. DBA / Trade Name": appl.get("dba"),
        "5. Department / Division": "Research & Engineering",
        "5. Street1": appl.get("address_line1"),
        "5. City": appl.get("city"),
        "5. State": appl.get("state"),
        "5. ZIP / Postal Code": appl.get("zip"),
        "5. Country": appl.get("country"),
        "5. UEI (formerly DUNS)": appl.get("duns_or_uei"),
        "5. EIN / TIN": appl.get("ein"),
        # Section 7 — Type of Applicant
        "7. Type of Applicant": "R - Small Business",
        "7. Small Business Organization Type": "Women-owned: No · Socially-economically-disadvantaged: No · 8(a): No",
        # Section 8 — Title of Project
        "8. Project Title": f"{app.get('topic_area') or app.get('program')}: LumenCore Harmonic-Resonance Forecasting Stack",
        # Section 9 — Proposed Project
        "9. Proposed Start Date": "(award + 30 days)",
        "9. Proposed End Date": f"(start + {budget.get('duration_months', 6)} months)",
        # Section 10 — Congressional District
        "10. Congressional District of Applicant": appl.get("state") + "-TBD" if appl.get("state") else "TBD",
        # Section 11 — Project Director / PI
        "11. PI Prefix": "Mr.",
        "11. PI First Name": (pi.get("name") or "").split()[0] if pi.get("name") else "",
        "11. PI Last Name": (pi.get("name") or "").split()[-1] if pi.get("name") else "",
        "11. PI Position/Title": pi.get("title"),
        "11. PI Organization": appl.get("legal_name"),
        "11. PI Email": appl.get("email"),
        "11. PI Phone": appl.get("phone"),
        # Section 14 — Estimated Funding
        "14.a Total Federal Funds Requested": budget.get("ceiling_usd"),
        "14.b Total Non-Federal Funds": 0,
        "14.c Total Federal & Non-Federal Funds": budget.get("ceiling_usd"),
        "14.d Estimated Program Income": 0,
        # Section 15 — IRB
        "15. Subject to State Executive Order 12372": "No",
        # Section 17 — AOR Certification
        "17. AOR Signature": "(SIGNED IN WORKSPACE BY AOR — required)",
        "17. AOR Name": appl.get("founder_pi"),
        "17. AOR Title": appl.get("founder_role"),
        "17. AOR Email": appl.get("email"),
        "17. AOR Phone": appl.get("phone"),
    }


def build_preflight(grant_id: str, run_dir: Path,
                    catalog_entry: dict[str, Any] | None) -> dict[str, Any]:
    """Build the full submission preflight report for one grant.

    Returns a dict with: ready (bool), blockers (list), warnings (list),
    missing_fields (list), deadline (dict), portal (dict), sf424_map (dict),
    package_files (list), package_complete (bool).
    """
    app_p = run_dir / "application.json"
    state_p = run_dir / "approval_state.json"
    if not app_p.exists():
        return {"ready": False, "blockers": ["application.json missing"],
                "grant_id": grant_id}
    app = json.loads(app_p.read_text(encoding="utf-8"))
    state = (json.loads(state_p.read_text(encoding="utf-8"))
             if state_p.exists() else {})

    # Required artifacts in a complete package
    required_files = [
        "application.json", "application.md",
        "technical_volume.md", "commercialization_plan.md",
        "cover_letter.md", "budget.json",
        "eligibility_report.json", "evidence_manifest.json",
        "manifest.sha256.json", "approval_state.json",
    ]
    present_files = {p.name for p in run_dir.iterdir() if p.is_file()}
    missing_files = [f for f in required_files if f not in present_files]
    package_complete = len(missing_files) == 0

    missing_fields = _scan_to_be_filled(app)
    portal = _portal_for(grant_id)
    deadline = _days_to_deadline(
        (catalog_entry or {}).get("deadline_typical")
        or app.get("deadline_typical"))

    blockers: list[str] = []
    warnings: list[str] = []

    if state.get("state") not in ("approved", "submitted"):
        blockers.append(f"approval_state is '{state.get('state')}' — must be 'approved' before submission")
    if missing_files:
        blockers.append(f"package missing required files: {missing_files}")
    if missing_fields:
        # SAM.gov UEI is the universal hard blocker
        crit = [f for f in missing_fields if any(
            k in f.lower() for k in ("uei", "duns", "ein", "sam_gov"))]
        if crit:
            blockers.append(f"SAM.gov / UEI / EIN required before submission: {crit}")
        other = [f for f in missing_fields if f not in crit]
        if other:
            warnings.append(f"non-critical TO_BE_FILLED fields: {other}")
    if deadline.get("risk") == "expired":
        blockers.append(f"deadline expired ({deadline.get('deadline')})")
    elif deadline.get("risk") == "critical":
        warnings.append(f"deadline in {deadline.get('days_remaining')} days — submit immediately")

    # Eligibility from the package
    elig = (app.get("eligibility") or {})
    if not elig.get("eligible", False):
        blockers.append(f"eligibility check failed: {elig.get('reasons', [])}")

    sf424 = _sf424_field_map(app)

    return {
        "grant_id": grant_id,
        "agency": app.get("agency"),
        "program": app.get("program"),
        "approval_state": state.get("state"),
        "approved_utc": state.get("approved_utc"),
        "package_complete": package_complete,
        "missing_files": missing_files,
        "missing_fields": missing_fields,
        "deadline": deadline,
        "portal": portal,
        "sf424_map": sf424,
        "blockers": blockers,
        "warnings": warnings,
        "ready": len(blockers) == 0,
        "ceiling_usd": (app.get("budget") or {}).get("ceiling_usd"),
        "submitted_utc": state.get("submitted_utc"),
        "external_tracking_id": state.get("external_tracking_id"),
        "preflight_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    }


def write_submission_kit(grant_id: str, run_dir: Path,
                         preflight: dict[str, Any]) -> dict[str, Path]:
    """Write submission_packet.json + SUBMIT_HOWTO.md to the run dir."""
    packet_p = run_dir / "submission_packet.json"
    howto_p = run_dir / "SUBMIT_HOWTO.md"
    packet_p.write_text(json.dumps(preflight, indent=2), encoding="utf-8")

    p = preflight
    portal = p.get("portal", {})
    deadline = p.get("deadline", {})
    blockers = p.get("blockers", [])
    warnings = p.get("warnings", [])
    sf424 = p.get("sf424_map", {})

    md: list[str] = []
    md.append(f"# Submission Kit — {p.get('grant_id')}")
    md.append("")
    md.append(f"**Agency:** {p.get('agency')}  ")
    md.append(f"**Program:** {p.get('program')}  ")
    md.append(f"**Ceiling:** ${p.get('ceiling_usd'):,}  " if p.get('ceiling_usd') else "")
    md.append(f"**Approval state:** `{p.get('approval_state')}`  ")
    if deadline.get("rolling"):
        md.append(f"**Deadline:** rolling ({deadline.get('deadline')})  ")
    elif deadline.get("days_remaining") is not None:
        md.append(f"**Deadline:** {deadline.get('deadline')} "
                  f"({deadline.get('days_remaining')} days, risk={deadline.get('risk')})  ")
    md.append("")
    md.append(f"**READY TO SUBMIT:** {'✅ YES' if p.get('ready') else '❌ NO'}")
    md.append("")

    if blockers:
        md.append("## ⛔ Blockers (must resolve before submission)")
        for b in blockers:
            md.append(f"- {b}")
        md.append("")
    if warnings:
        md.append("## ⚠️ Warnings")
        for w in warnings:
            md.append(f"- {w}")
        md.append("")

    md.append("## 🎯 Submission Portal")
    md.append(f"- **System:** {portal.get('submission_system')}")
    md.append(f"- **Portal URL:** {portal.get('portal_url')}")
    for k, v in portal.items():
        if k.endswith("_url") and k != "portal_url":
            md.append(f"- **{k.replace('_url','').upper()}:** {v}")
    if portal.get("note"):
        md.append(f"- **Note:** {portal.get('note')}")
    md.append("")
    md.append("### Required to submit")
    for r in portal.get("requires", []):
        md.append(f"- [ ] {r}")
    md.append("")

    md.append("## 📋 Step-by-step")
    md.append("1. **Verify SAM.gov registration** is active (UEI, EIN, banking, NAICS).")
    md.append("   - If not yet registered: https://sam.gov/content/entity-registration")
    md.append("   - Allow ~10 business days for first-time registration.")
    md.append("2. **Confirm Grants.gov account** is linked to the UEI and you are designated AOR.")
    md.append("   - https://www.grants.gov/applicants/registration")
    md.append(f"3. **Open the opportunity** in the portal: {portal.get('portal_url')}")
    md.append("4. **Click 'Apply'** → creates a Workspace package.")
    md.append("5. **Upload the attachments** from this run directory:")
    md.append("   - `application.md` (or rendered PDF) → Project Narrative")
    md.append("   - `technical_volume.md` → Technical Volume")
    md.append("   - `commercialization_plan.md` → Commercialization Plan")
    md.append("   - `budget.json` → fill SF-424A budget form (use values below)")
    md.append("   - `cover_letter.md` → Cover Letter")
    md.append("   - `evidence_manifest.json` + `manifest.sha256.json` → Supplementary")
    md.append("6. **Fill SF-424 cover form** using the field map below (copy-paste).")
    md.append("7. **AOR signs and submits** in Workspace.")
    md.append("8. **Record the Grants.gov Tracking Number** returned (format: GRANT##########).")
    md.append("9. Mark submitted in Luma:")
    md.append(f"   ```")
    md.append(f"   POST /api/grants/{p.get('grant_id')}/submitted")
    md.append(f"   {{\"submitted_by\":\"<AOR name>\",\"external_tracking_id\":\"GRANT##########\"}}")
    md.append("   ```")
    md.append("")

    md.append("## 📑 SF-424 Field Map (copy-paste ready)")
    md.append("")
    md.append("| Form Field | Value |")
    md.append("|---|---|")
    for k, v in sf424.items():
        vv = "" if v is None else str(v).replace("|", "\\|")
        md.append(f"| {k} | {vv} |")
    md.append("")

    if p.get("missing_fields"):
        md.append("## ✏️ Fields needing your input (from `data/company_profile.json`)")
        for f in p.get("missing_fields", []):
            md.append(f"- `{f}`")
        md.append("")
        md.append("Edit `data/company_profile.json` and POST `/api/grants/regenerate` "
                  "to refresh all packages with the new values.")
        md.append("")

    md.append("---")
    md.append(f"_Generated {p.get('preflight_utc')} by `grant_submission_kit.py`._")
    howto_p.write_text("\n".join(md), encoding="utf-8")
    return {"packet": packet_p, "howto": howto_p}
