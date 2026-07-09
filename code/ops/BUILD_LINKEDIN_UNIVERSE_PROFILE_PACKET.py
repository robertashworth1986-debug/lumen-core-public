from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

DECISION_JSON = OUT_OPS / "reviewer_decision_brief_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
DOCKET_JSON = OUT_OPS / "human_action_docket_latest.json"
MANIFEST_JSON = OUT_OPS / "data_room_manifest_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
QA_JSON = OUT_OPS / "reviewer_diligence_qa_matrix_latest.json"
LAUNCHPACK_JSON = OUT_OPS / "linkedin_app_launchpack" / "linkedin_app_launchpack_latest.json"

OUT_JSON = OUT_OPS / "linkedin_universe_profile_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "linkedin_universe_profile_packet.json"
OUT_MD = SPRINT_DIR / "LINKEDIN_UNIVERSE_PROFILE_PACKET_2026-07-09.md"

DEFAULT_PROFILE_URL = "https://www.linkedin.com/in/robert-ashworth-40a9b7376"
DEFAULT_COMPANY_URL = "https://www.linkedin.com/company/1337"

SENSITIVE_MARKERS = [
    "zoom.us",
    "meeting id",
    "password",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "xox",
]

SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}", re.I),
]

PUBLIC_UNSAFE_PHRASES = [
    "field validated",
    "realized savings",
    "guaranteed award",
    "guaranteed returns",
    "certified assurance",
    "cmmc certified",
    "nuclear licensing authority",
    "medical efficacy",
    "airworthiness",
    "operational government deployment",
    "live profit",
    "risk-free",
    "autonomous trading system ready",
    "freedom to operate",
    "patented",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_status(path_text: str) -> dict[str, Any]:
    path = ROOT / path_text
    return {
        "path": path_text,
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def clean_words(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def scan_text(text: str) -> dict[str, Any]:
    lowered = text.lower()
    sensitive_hits = [marker for marker in SENSITIVE_MARKERS if marker in lowered]
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            sensitive_hits.append(pattern.pattern)
    unsafe_public_hits = [phrase for phrase in PUBLIC_UNSAFE_PHRASES if phrase in lowered]
    return {
        "sensitive_hits": sorted(set(sensitive_hits)),
        "unsafe_public_hits": sorted(set(unsafe_public_hits)),
        "sensitive_count": len(set(sensitive_hits)),
        "unsafe_public_count": len(set(unsafe_public_hits)),
    }


def top_decision_cards(decision: dict[str, Any], limit: int = 7) -> list[dict[str, Any]]:
    cards = [row for row in decision.get("decision_cards", []) if isinstance(row, dict)]
    cards.sort(key=lambda row: int(row.get("priority") or 999))
    out = []
    for row in cards[:limit]:
        out.append(
            {
                "priority": int(row.get("priority") or 999),
                "lane_id": str(row.get("lane_id") or ""),
                "name": str(row.get("name") or ""),
                "audience": str(row.get("audience") or ""),
                "readiness_mode": str(row.get("readiness_mode") or ""),
                "human_gate": str(row.get("required_authority") or ""),
                "claim_boundary": str(row.get("claim_boundary") or ""),
                "first_artifact": str(row.get("first_artifact") or ""),
            }
        )
    return out


def urgent_docket_items(docket: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    items = [row for row in docket.get("docket_items", []) if isinstance(row, dict)]
    items.sort(key=lambda row: int(row.get("priority") or 999))
    out = []
    for row in items[:limit]:
        out.append(
            {
                "priority": int(row.get("priority") or 999),
                "name": str(row.get("name") or ""),
                "status": str(row.get("status") or ""),
                "action_due": row.get("action_due"),
                "docket_action": str(row.get("docket_action") or ""),
                "human_gate": str(row.get("human_gate") or ""),
            }
        )
    return out


def launchpack_summary(launchpack: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": str(launchpack.get("status") or "unknown"),
        "status_reason": str(launchpack.get("status_reason") or ""),
        "readiness_score_pct": int(launchpack.get("readiness_score_pct") or 0),
        "profile_url": str(launchpack.get("profile_url") or DEFAULT_PROFILE_URL),
        "company_page_url": str(launchpack.get("company_page_url") or DEFAULT_COMPANY_URL),
        "logo_present": bool((launchpack.get("validation") or {}).get("logo_present")) if isinstance(launchpack.get("validation"), dict) else False,
    }


def build_profile_copy(manifest: dict[str, Any], launchpack: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
    manifested_count = int(summary.get("manifested_markdown_count") or 0)
    control_count = int(summary.get("control_artifact_count") or 0)
    profile_url = str(launchpack.get("profile_url") or DEFAULT_PROFILE_URL)

    headline = (
        "Founder, LumenCore | Proof-to-Pilot AI Infrastructure Validation | "
        "Source Provenance, Replay Evidence & Human-Gated Packets"
    )
    headline_variants = [
        headline,
        "Founder, LumenCore | Infrastructure AI Validation | Replay Evidence & Public-Safe Proof Feeds",
        "Proof-to-Pilot Systems Builder | LumenCore | Agency, Investor & Utility Validation Packets",
        "Founder & Chief Scientist | LumenCore / LumaTrader | Evidence-Gated AI Infrastructure",
    ]
    about_short = (
        "I build LumenCore, a proof-to-pilot platform for source provenance, baseline-vs-candidate replay, "
        "hash-backed proof rooms, and human-gated agency and investor packets."
    )
    about_full = clean_words(
        f"""
        I build LumenCore, a proof-to-pilot platform for turning infrastructure, energy, environmental,
        market, and operational data into source-provenance records, baseline-vs-candidate replay plans,
        and reviewer-ready proof packets.

        The July 2026 proof room is organized around live-source measurement, replay evidence,
        claim-boundary gates, authority matrices, human action dockets, and E-drive custody mirrors.
        Current data-room posture: {manifested_count} public-safe Markdown artifacts and {control_count}
        machine-readable control receipts.

        The active universe includes EVTit/Black Dog meeting prep, LvlUp First Check review watch,
        DARPA DICE full-proposal sprint, FHWA TSMO, NASA data-center RFI, DSIP MissionWeave,
        NSF Project Pitch, and patent-counsel review.

        Boundary: this profile does not claim award, agency approval, production deployment,
        external field validation, trading performance, legal IP conclusions, or external operational
        savings results. The next milestone is buyer or agency authorized replay with held-out data,
        incumbent baseline, acceptance metric, replay window, and approved economic conversion.

        I am looking for utility, lab, agency, investor, and engineering partners who want disciplined
        measurement before they trust AI/control methods in infrastructure settings.
        """
    )
    experience_bullets = [
        "Built a reviewer-ready proof stack with decision briefs, Q&A matrices, authority gates, human dockets, and data-room manifests.",
        "Organized active SBIR, RFI, BAA, investor, and partner lanes into public-safe packages with final-action gates.",
        "Developed source-provenance and baseline-vs-candidate replay workflows for infrastructure, energy, environmental, market, and operational data.",
        "Maintained explicit public-claim boundaries across agency, investor, IP, and autonomous systems materials.",
        "Mirrored reviewer packets and machine-readable receipts into E-drive proof vault targets for custody continuity.",
    ]
    featured_links = [
        {
            "label": "Proof-to-Pilot Control Room",
            "url": "https://lumen-core.ai/proof_to_pilot.html",
            "placement": 1,
            "reason": "Lead with the clearest public proof-to-pilot experience.",
        },
        {
            "label": "Mission Control",
            "url": "https://lumen-core.ai/mission_control.html",
            "placement": 2,
            "reason": "Show the operating surface behind the proof universe.",
        },
        {
            "label": "Evidence Index",
            "url": "https://lumen-core.ai/evidence/",
            "placement": 3,
            "reason": "Give technical reviewers a route into public evidence artifacts.",
        },
    ]
    skills = [
        "Proof-to-pilot validation",
        "Infrastructure AI",
        "Source provenance",
        "Replay evaluation",
        "Baseline benchmarking",
        "Evidence packaging",
        "SBIR/STTR readiness",
        "Federal opportunity triage",
        "Reviewer diligence",
        "Human-gated automation",
        "Python",
        "FastAPI",
        "PowerShell",
        "Data-room operations",
        "Claim-boundary governance",
    ]
    post_templates = [
        {
            "title": "Proof room upgrade",
            "text": clean_words(
                f"""
                LumenCore July proof-room update: the platform now has a reviewer path that starts with a
                decision brief, moves through a diligence Q&A matrix, and lands in a data-room manifest with
                {manifested_count} public-safe artifacts and {control_count} machine-readable control receipts.

                The purpose is simple: make AI/control claims easier to inspect before a pilot, contract,
                or investment decision. This is not an award or deployment claim. It is a proof-to-pilot
                validation layer built for disciplined external review.
                """
            ),
        },
        {
            "title": "Partner ask",
            "text": clean_words(
                """
                I am looking for one serious utility, lab, agency, infrastructure, or engineering partner
                that wants a measured replay path: approved held-out data, incumbent baseline, acceptance
                metric, replay window, and a clear report on what improved, what failed, and what still
                cannot be claimed.
                """
            ),
        },
        {
            "title": "Funding sprint posture",
            "text": clean_words(
                """
                LumenCore is organizing active SBIR, RFI, BAA, investor, and partner lanes around one rule:
                prepare fast, but keep final sends, submissions, filings, terms, and public claims under
                human review. The evidence stack should make decisions faster without making claims bigger
                than the proof.
                """
            ),
        },
    ]
    return {
        "profile_url": profile_url,
        "recommended_headline": headline,
        "headline_variants": headline_variants,
        "about_short": about_short,
        "about_full": about_full,
        "experience": {
            "title": "Founder, Chief Scientist & Principal Systems Engineer",
            "company": "LumenCore / LumaTrader",
            "date_range": "2014 - Present",
            "location": "Nashville, Tennessee, United States",
            "bullets": experience_bullets,
        },
        "featured_links": featured_links,
        "skills": skills,
        "post_templates": post_templates,
        "manual_update_sequence": [
            "Open the LinkedIn profile and review the current headline/About before editing.",
            "Paste the recommended headline or a selected variant.",
            "Paste About (Full), preserving the boundary paragraph.",
            "Add or reorder featured links in the listed order.",
            "Refresh the LumenCore / LumaTrader experience entry from the bullet pack.",
            "Publish at most one post after human review of the exact text.",
        ],
        "public_action_gate": "Human approval is required before any LinkedIn profile edit, post, comment, follow, message, or company-page change.",
    }


def build_payload() -> dict[str, Any]:
    decision = read_json(DECISION_JSON)
    authority = read_json(AUTHORITY_JSON)
    docket = read_json(DOCKET_JSON)
    manifest = read_json(MANIFEST_JSON)
    reviewer_gate = read_json(REVIEWER_GATE_JSON)
    qa = read_json(QA_JSON)
    launchpack_raw = read_json(LAUNCHPACK_JSON)
    launchpack = launchpack_summary(launchpack_raw)

    profile_copy = build_profile_copy(manifest, launchpack)

    evidence_paths = [
        "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
    ]
    evidence_status = [artifact_status(path) for path in evidence_paths]

    rendered_text = "\n".join(
        [
            profile_copy["recommended_headline"],
            profile_copy["about_short"],
            profile_copy["about_full"],
            "\n".join(profile_copy["experience"]["bullets"]),
            "\n".join(row["text"] for row in profile_copy["post_templates"]),
        ]
    )
    public_scan = scan_text(rendered_text)

    gate_clear = (
        bool(reviewer_gate.get("reviewer_gate_clear"))
        and int((reviewer_gate.get("summary") or {}).get("unsafe_secret_count") or 0) == 0
        and int((reviewer_gate.get("summary") or {}).get("unsafe_claim_count") or 0) == 0
    )
    authority_summary = authority.get("summary", {}) if isinstance(authority.get("summary"), dict) else {}
    decision_summary = decision.get("summary", {}) if isinstance(decision.get("summary"), dict) else {}
    all_final_actions_blocked = bool(authority_summary.get("all_final_actions_blocked_without_human")) and bool(
        decision_summary.get("all_final_actions_blocked_without_human")
    )
    evidence_present = all(row["present"] for row in evidence_status)
    public_safe = public_scan["sensitive_count"] == 0 and public_scan["unsafe_public_count"] == 0

    payload = {
        "generated_utc": now_utc(),
        "schema": "linkedin_universe_profile_packet_v1",
        "status": (
            "LINKEDIN_UNIVERSE_PROFILE_READY_HUMAN_POST_REQUIRED"
            if gate_clear and all_final_actions_blocked and evidence_present and public_safe
            else "LINKEDIN_UNIVERSE_PROFILE_BLOCKED"
        ),
        "profile_url": profile_copy["profile_url"],
        "company_page_url": launchpack["company_page_url"],
        "summary": {
            "headline_character_count": len(profile_copy["recommended_headline"]),
            "about_character_count": len(profile_copy["about_full"]),
            "post_template_count": len(profile_copy["post_templates"]),
            "featured_link_count": len(profile_copy["featured_links"]),
            "skill_count": len(profile_copy["skills"]),
            "decision_lane_count": int(decision_summary.get("lane_count") or 0),
            "qa_count": int((qa.get("summary") or {}).get("qa_count") or 0),
            "manifested_markdown_count": int((manifest.get("summary") or {}).get("manifested_markdown_count") or 0),
            "control_artifact_count": int((manifest.get("summary") or {}).get("control_artifact_count") or 0),
            "reviewer_gate_clear": gate_clear,
            "all_final_actions_blocked_without_human": all_final_actions_blocked,
            "public_copy_sensitive_count": public_scan["sensitive_count"],
            "public_copy_unsafe_count": public_scan["unsafe_public_count"],
            "linkedin_public_action_requires_human": True,
        },
        "launchpack": launchpack,
        "profile_copy": profile_copy,
        "proof_stack_alignment": {
            "top_decision_cards": top_decision_cards(decision),
            "urgent_docket_items": urgent_docket_items(docket),
        },
        "evidence_status": evidence_status,
        "public_copy_scan": public_scan,
        "human_gate": {
            "profile_edit_allowed_without_human": False,
            "post_allowed_without_human": False,
            "message_allowed_without_human": False,
            "company_page_change_allowed_without_human": False,
            "rule": "Human approval is required before any public LinkedIn action.",
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["linkedin_universe_profile_packet_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    copy = payload["profile_copy"]
    lines: list[str] = [
        "# LinkedIn Universe Profile Packet - 2026-07-09",
        "",
        "Purpose: upgrade Robert Ashworth's LinkedIn profile into the same LumenCore proof universe as the funding sprint, without performing a public profile edit or post from automation.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Profile URL: {payload['profile_url']}",
        f"- Company page URL: {payload['company_page_url']}",
        f"- Headline characters: `{summary['headline_character_count']}`",
        f"- About characters: `{summary['about_character_count']}`",
        f"- Post templates: `{summary['post_template_count']}`",
        f"- Featured links: `{summary['featured_link_count']}`",
        f"- Skills: `{summary['skill_count']}`",
        f"- Decision lanes: `{summary['decision_lane_count']}`",
        f"- Reviewer Q&A rows: `{summary['qa_count']}`",
        f"- Data-room Markdown artifacts: `{summary['manifested_markdown_count']}`",
        f"- Data-room control artifacts: `{summary['control_artifact_count']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- Public copy sensitive hits: `{summary['public_copy_sensitive_count']}`",
        f"- Public copy unsafe hits: `{summary['public_copy_unsafe_count']}`",
        f"- LinkedIn public action requires human: `{str(summary['linkedin_public_action_requires_human']).lower()}`",
        f"- Packet SHA-256: `{payload['linkedin_universe_profile_packet_sha256']}`",
        "",
        "## Recommended Headline",
        "",
        copy["recommended_headline"],
        "",
        "## Headline Variants",
        "",
    ]
    for idx, headline in enumerate(copy["headline_variants"], start=1):
        lines.append(f"{idx}. {headline}")
    lines.extend(["", "## About Short", "", copy["about_short"], "", "## About Full", "", copy["about_full"], ""])

    exp = copy["experience"]
    lines.extend(
        [
            "## Experience Entry",
            "",
            f"### {exp['title']} | {exp['company']}",
            "",
            f"{exp['date_range']} | {exp['location']}",
            "",
        ]
    )
    for bullet in exp["bullets"]:
        lines.append(f"- {bullet}")
    lines.extend(["", "## Featured Link Order", ""])
    for item in copy["featured_links"]:
        lines.append(f"- {item['placement']}. {item['label']}: {item['url']} | {item['reason']}")
    lines.extend(["", "## Skills", "", ", ".join(copy["skills"]), "", "## Post Templates", ""])
    for item in copy["post_templates"]:
        lines.extend([f"### {item['title']}", "", item["text"], ""])

    lines.extend(["## Proof Stack Alignment", ""])
    for row in payload["proof_stack_alignment"]["top_decision_cards"]:
        lines.append(
            f"- P{row['priority']} {row['name']} | {row['readiness_mode']} | human gate: {row['human_gate']}"
        )
    lines.extend(["", "## Manual Update Sequence", ""])
    for idx, step in enumerate(copy["manual_update_sequence"], start=1):
        lines.append(f"{idx}. {step}")
    lines.extend(["", "## Human Gate", ""])
    for key, value in payload["human_gate"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Evidence Sources", ""])
    for row in payload["evidence_status"]:
        lines.append(
            f"- `{row['path']}` | present=`{str(row['present']).lower()}` | bytes=`{row['bytes']}` | sha256=`{row['sha256']}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(json.dumps({"status": payload["status"], "outputs": payload["outputs"]}, indent=2))
    return 0 if payload["status"].endswith("HUMAN_POST_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
