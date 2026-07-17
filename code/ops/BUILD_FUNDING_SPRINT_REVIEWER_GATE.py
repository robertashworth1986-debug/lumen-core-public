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

OUT_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "funding_sprint_reviewer_gate.json"
OUT_MD = SPRINT_DIR / "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md"
GENERATED_MARKDOWN_OUTPUTS = {OUT_MD.name}

SECRET_PATTERNS = [
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"secret", re.I),
    re.compile(r"token", re.I),
    re.compile(r"password", re.I),
    re.compile(r"private key", re.I),
    re.compile(r"BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY"),
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"refresh_token", re.I),
    re.compile(r"client_secret", re.I),
]

RISKY_CLAIMS = [
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

BOUNDARY_MARKERS = [
    "do not",
    "not ",
    "not a ",
    "not an ",
    "no ",
    "forbidden",
    "without",
    "unless",
    "boundary",
    "blocked",
    "claim boundary",
    "do-not-submit",
    "not authorized",
    "not claimed",
    "forbidden wording",
    "scan",
]

BOUNDARY_SECTION_MARKERS = [
    "do not use",
    "forbidden wording",
    "blocked language",
    "forbidden now",
    "do not claim",
    "not allowed as",
    "blocked:",
    "blocked language unless",
    "not allowed",
    "blocked until",
    "must_stop_before",
]

ACTIVE_LANES = [
    {
        "lane": "Air Force Advanced Automation Contract RFI",
        "deadline": "2026-07-13",
        "source": "https://sam.gov/opp/3fa15f166ec244539c808be5c0496427/view",
        "file": "AIR_FORCE_AAC_RFI_CAPABILITY_STATEMENT_2026-07-09.md",
        "next_gate": "Verify SAM attachments, response address, page limit, and time zone before sending.",
        "claim_boundary": "RFI response only; not a contract award or operational deployment.",
        "human_gate": "Human approval before email/submission.",
    },
    {
        "lane": "NASA Data Center Infrastructure RFI",
        "deadline": "2026-07-17",
        "source": "https://sam.gov/workspace/contract/opp/b6d14a4b9eac476b997894d0c5a47a27/view",
        "file": "NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md",
        "next_gate": "Verify official SAM response instructions and build final PDF.",
        "claim_boundary": "No NASA operational claim, energy-savings claim, or infrastructure deployment claim.",
        "human_gate": "Human approval before response submission.",
    },
    {
        "lane": "DLA MissionWeave DSIP SBIR",
        "deadline": "2026-07-22",
        "source": "https://www.sbir.gov/topics/12778",
        "file": "DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md",
        "next_gate": "Robert enters Firm PIN directly; then inspect DSIP org authority, certs, cost, and upload preview.",
        "claim_boundary": "No DLA integration, certified readiness, or 10x productivity claim.",
        "human_gate": "Human-only Firm PIN, certifications, cost approval, and final submit.",
    },
    {
        "lane": "FHWA TSMO Data Initiative",
        "deadline": "2026-08-03",
        "source": "https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view",
        "file": "FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
        "next_gate": "Download SAM package, build compliance matrix, decide prime-vs-team posture.",
        "claim_boundary": "No FHWA field validation, safety benefit, or traffic operations deployment claim.",
        "human_gate": "Human approval before pricing, reps/certs, or submission.",
    },
    {
        "lane": "DOE Advanced Nuclear Licensing Cost-Share",
        "deadline": "2026-09-30",
        "source": "https://www.fedconnect.net/FedConnect/default.aspx?ReturnUrl=%2Ffedconnect%2F%3Fdoc%3DDE-FOA-0003339%26agency%3DDOE&agency=DOE&doc=DE-FOA-0003339",
        "file": "NUCLEAR_LICENSING_EVIDENCE_PARTNER_ONE_PAGER_2026-07-09.md",
        "next_gate": "Qualified nuclear/licensing applicant or full NOFO review before any solo-prime action.",
        "claim_boundary": "Partner-first; no NRC licensing authority, reactor safety validation, nuclear QA, or plant performance claim.",
        "human_gate": "Human approval before partner outreach or FedConnect action.",
    },
    {
        "lane": "NSF SBIR/STTR Project Pitch",
        "deadline": "rolling_invitation_gate",
        "source": "https://seedfund.nsf.gov/project-pitch/",
        "file": "NSF_PROJECT_PITCH_DRAFT_2026-07-09.md",
        "next_gate": "Check NSF login and one-pending-pitch rule before submitting.",
        "claim_boundary": "Full proposal remains invitation-gated; no invitation is represented unless issued by NSF.",
        "human_gate": "Human approval before Project Pitch submit.",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def markdown_files() -> list[Path]:
    if not SPRINT_DIR.exists():
        return []
    return sorted(
        path
        for path in SPRINT_DIR.glob("*.md")
        if path.is_file() and path.name not in GENERATED_MARKDOWN_OUTPUTS
    )


def line_is_boundary(line: str) -> bool:
    lowered = line.lower()
    structured_false = re.search(r":\s*`?false`?\s*$", lowered) is not None
    structured_negative_true = re.search(r"_[a-z0-9]*not_[a-z0-9_]+:\s*`?true`?\s*$", lowered) is not None
    return structured_false or structured_negative_true or any(marker in lowered for marker in BOUNDARY_MARKERS)


def line_opens_boundary_section(line: str) -> bool:
    lowered = line.strip().lower()
    if not lowered:
        return False
    return any(marker in lowered for marker in BOUNDARY_SECTION_MARKERS)


def line_opens_nonboundary_section(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("#") and not line_opens_boundary_section(stripped)


def scan_files(files: list[Path]) -> dict[str, Any]:
    secret_hits = []
    risky_hits = []
    boundary_hits = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lines = path.read_text(errors="ignore").splitlines()
        boundary_section = False
        for lineno, line in enumerate(lines, start=1):
            if line_opens_boundary_section(line):
                boundary_section = True
            elif line_opens_nonboundary_section(line):
                boundary_section = False
            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    hit = {"file": rel(path), "line": lineno, "pattern": pattern.pattern, "text": line.strip()}
                    if line_is_boundary(line) or boundary_section:
                        boundary_hits.append(hit | {"classification": "boundary_language"})
                    else:
                        secret_hits.append(hit | {"classification": "unsafe_secret_pattern"})
            lowered = line.lower()
            for phrase in RISKY_CLAIMS:
                if phrase in lowered:
                    hit = {"file": rel(path), "line": lineno, "phrase": phrase, "text": line.strip()}
                    if line_is_boundary(line) or boundary_section:
                        boundary_hits.append(hit | {"classification": "blocked_or_boundary_claim_language"})
                    else:
                        risky_hits.append(hit | {"classification": "unsafe_claim_language"})
    return {
        "unsafe_secret_hits": secret_hits,
        "unsafe_claim_hits": risky_hits,
        "boundary_hits": boundary_hits,
        "unsafe_secret_count": len(secret_hits),
        "unsafe_claim_count": len(risky_hits),
        "boundary_hit_count": len(boundary_hits),
    }


def file_manifest(files: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in files:
        rows.append(
            {
                "path": rel(path),
                "name": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "classification": "public_safe_markdown_review_required",
            }
        )
    return rows


def proof_cards(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {row["name"]: row for row in manifest}
    cards = []
    for lane in ACTIVE_LANES:
        artifact = by_name.get(lane["file"])
        ready = artifact is not None
        card_seed = {
            "lane": lane["lane"],
            "deadline": lane["deadline"],
            "source": lane["source"],
            "artifact": lane["file"],
            "artifact_present": ready,
            "artifact_sha256": artifact["sha256"] if artifact else "",
            "next_gate": lane["next_gate"],
            "claim_boundary": lane["claim_boundary"],
            "human_gate": lane["human_gate"],
            "reviewer_posture": "ready_for_human_review" if ready else "missing_artifact",
        }
        card_seed["card_sha256"] = hashlib.sha256(
            json.dumps(card_seed, sort_keys=True).encode("utf-8")
        ).hexdigest()
        cards.append(card_seed)
    return cards


def build_payload() -> dict[str, Any]:
    files = markdown_files()
    manifest = file_manifest(files)
    scans = scan_files(files)
    cards = proof_cards(manifest)
    all_cards_present = all(card["artifact_present"] for card in cards)
    gate_clear = (
        bool(files)
        and all_cards_present
        and scans["unsafe_secret_count"] == 0
        and scans["unsafe_claim_count"] == 0
    )
    payload = {
        "generated_utc": now_utc(),
        "schema": "funding_sprint_reviewer_gate_v1",
        "sprint_dir": rel(SPRINT_DIR),
        "reviewer_gate_clear": gate_clear,
        "status": "REVIEWER_GATE_CLEAR_HUMAN_SUBMISSION_REQUIRED" if gate_clear else "REVIEWER_GATE_BLOCKED",
        "summary": {
            "markdown_file_count": len(files),
            "proof_card_count": len(cards),
            "all_cards_present": all_cards_present,
            "unsafe_secret_count": scans["unsafe_secret_count"],
            "unsafe_claim_count": scans["unsafe_claim_count"],
            "boundary_hit_count": scans["boundary_hit_count"],
            "autonomous_external_action_allowed": False,
            "live_trading_allowed": False,
            "final_submission_allowed_without_human": False,
        },
        "claim_policy": {
            "allowed": [
                "proof-to-pilot AI infrastructure validation",
                "source provenance",
                "baseline-vs-candidate replay",
                "hash-verified public proof-feed deployment",
                "29-source inventory with 25 measured providers",
                "human-gated agency submission",
            ],
            "blocked": RISKY_CLAIMS,
        },
        "manifest": manifest,
        "proof_cards": cards,
        "scan": scans,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["gate_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Funding Sprint Reviewer Gate - 2026-07-09",
        "",
        "Purpose: machine-check the active funding sprint before agency, investor, or partner use.",
        "",
        "This gate does not authorize final submission. It confirms the packet is organized, hashed, and free of unbounded claim/secret hits under the current scanner.",
        "",
        "## Gate Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Reviewer gate clear: `{str(payload['reviewer_gate_clear']).lower()}`",
        f"- Markdown files scanned: `{summary['markdown_file_count']}`",
        f"- Proof cards: `{summary['proof_card_count']}`",
        f"- Unsafe secret hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- Boundary/blocked-language hits: `{summary['boundary_hit_count']}`",
        f"- Autonomous external action allowed: `{str(summary['autonomous_external_action_allowed']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Final submission without human allowed: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Gate SHA-256: `{payload['gate_sha256']}`",
        "",
        "## Reviewer Proof Cards",
        "",
    ]
    for card in payload["proof_cards"]:
        lines.extend(
            [
                f"### {card['lane']}",
                "",
                f"- Deadline: `{card['deadline']}`",
                f"- Source: {card['source']}",
                f"- Artifact: `{card['artifact']}`",
                f"- Artifact present: `{str(card['artifact_present']).lower()}`",
                f"- Artifact SHA-256: `{card['artifact_sha256']}`",
                f"- Reviewer posture: `{card['reviewer_posture']}`",
                f"- Next gate: {card['next_gate']}",
                f"- Claim boundary: {card['claim_boundary']}",
                f"- Human gate: {card['human_gate']}",
                f"- Card SHA-256: `{card['card_sha256']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Claim Policy",
            "",
            "Allowed language:",
            "",
        ]
    )
    for item in payload["claim_policy"]["allowed"]:
        lines.append(f"- {item}")
    lines.extend(["", "Blocked language unless explicitly negated or bounded:", ""])
    for item in payload["claim_policy"]["blocked"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Scan Notes",
            "",
            "Boundary hits are expected when a file says not to use a risky phrase. They remain listed in JSON for audit, but they do not block the gate.",
            "",
            "Any unsafe secret or claim hit blocks agency use until removed or rewritten as explicit boundary language.",
            "",
            "## Human Submission Rule",
            "",
            "No portal submission, email send, certification, affirmation, pricing, Firm PIN entry, IP filing, live trading, or capital movement is authorized by this gate.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(json.dumps({"status": payload["status"], "json": rel(OUT_JSON), "markdown": rel(OUT_MD)}, indent=2))


if __name__ == "__main__":
    main()
