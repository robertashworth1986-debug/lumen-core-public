from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GRANTS = ROOT / "grant_submissions"
OUT = ROOT / "out" / "ops"

READINESS_JSON = OUT / "grant_submission_readiness_audit_latest.json"
OUT_JSON = OUT / "action_time_submission_board_latest.json"
OUT_MD = GRANTS / "ACTION_TIME_SUBMISSION_BOARD_2026-06-20.md"
FREEZE_JSON = OUT / "top_submission_package_freeze_latest.json"
FREEZE_MD = GRANTS / "TOP_SUBMISSION_PACKAGE_FREEZE_2026-06-20.md"
PORTAL_RUNBOOK_JSON = OUT / "portal_preview_runbook_latest.json"
PORTAL_RUNBOOK_MD = GRANTS / "PORTAL_PREVIEW_RUNBOOK_2026-06-20.md"
SUPPORT_PACK_JSON = OUT / "grant_support_outreach_pack_latest.json"
SUPPORT_PACK_MD = GRANTS / "GRANT_SUPPORT_OUTREACH_PACK_2026-06-20.md"
RED_TEAM_GATE_JSON = OUT / "reviewer_red_team_gate_latest.json"
RED_TEAM_GATE_MD = GRANTS / "REVIEWER_RED_TEAM_GATE_2026-06-20.md"


PACKAGE_PRIORITY = {
    "DICE": {
        "rank": 1,
        "deadline_hint": "DICE abstract path; verify current deadline and upload rules in DARPA BAAT before action.",
        "why_now": "Cleanest near-term federal research package: local lock, render QA, references, Heilmeier matrix, and ROM boundary exist.",
        "primary_unlock": "BAAT account, organization association, submitter authority, DICE opportunity visibility, and upload preview.",
    },
    "HarborSentinel": {
        "rank": 2,
        "deadline_hint": "Navy Release 3 path; verify DSIP topic window, forms, and attachment rules inside DSIP.",
        "why_now": "Strongest topic-specific DoD evidence lane: public AIS hashes, held-out split, full-hash preflight, controlled-injection benchmark, and Volume 2 render QA exist.",
        "primary_unlock": "DSIP organization linkage, submitter authority, required forms, compliance representations, and upload preview.",
    },
    "NSF Project Pitch": {
        "rank": 3,
        "deadline_hint": "Rolling portal path; verify duplicate-pitch/open-invitation status in NSF Project Pitch portal.",
        "why_now": "Fastest low-friction non-DoD funding path if legal name, PI/title, duplicate status, and paste counts are confirmed.",
        "primary_unlock": "Portal paste-count check plus legal business name and PI/founder title confirmation.",
    },
    "MissionWeave": {
        "rank": 4,
        "deadline_hint": "DSIP path; verify topic visibility and budget/forms inside DSIP.",
        "why_now": "Good software fit, but needs domain/process confirmation before it should outrank DICE or Harbor.",
        "primary_unlock": "Confirm the bounded process, representative-data path, DSIP forms, and cost assumptions.",
    },
    "NV065": {
        "rank": 5,
        "deadline_hint": "DSIP path; verify topic visibility and budget/forms inside DSIP.",
        "why_now": "Topic-specific benchmark exists, but sensor-resource assumptions need domain review.",
        "primary_unlock": "Sensor-domain review, DSIP authority, cost review, and compliance path.",
    },
}

SAFETY_RULES = [
    "Do not upload, certify, consent, sign, submit, or lock a workspace without fresh action-time approval.",
    "Do not enter or affirm CMMC/SPRS/cybersecurity status without user and qualified reviewer approval.",
    "Do not record passwords, MFA codes, API keys, tax IDs, banking details, or private account tokens.",
    "Do not represent a collaborator, partner, customer, reviewer, facility, clearance, or demo site as committed without written proof.",
    "Do not convert controlled-injection, synthetic, or public-data benchmarks into field-performance claims.",
]

SENSITIVE_FACT_PATTERNS = [
    (re.compile(r"UEI\s+[A-Z0-9]+", re.IGNORECASE), "SAM entity identifier recorded"),
    (re.compile(r"CAGE/NCAGE\s+[A-Z0-9]+", re.IGNORECASE), "SAM entity identifier recorded"),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def package_by_name(readiness: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packages = readiness.get("packages", [])
    if not isinstance(packages, list):
        return {}
    return {
        str(pkg.get("name")): pkg
        for pkg in packages
        if isinstance(pkg, dict) and pkg.get("name")
    }


def artifact_counts(pkg: dict[str, Any]) -> dict[str, Any]:
    required = pkg.get("required_artifacts", [])
    manifests = pkg.get("evidence_manifests", [])
    required_present = sum(1 for row in required if isinstance(row, dict) and row.get("exists"))
    required_total = len(required) if isinstance(required, list) else 0
    manifest_matched = sum(int(row.get("matched", 0) or 0) for row in manifests if isinstance(row, dict))
    manifest_expected = sum(int(row.get("expected", 0) or 0) for row in manifests if isinstance(row, dict))
    render = pkg.get("render") if isinstance(pkg.get("render"), dict) else {}
    return {
        "required_artifacts_present": required_present,
        "required_artifacts_total": required_total,
        "evidence_manifest_matched": manifest_matched,
        "evidence_manifest_expected": manifest_expected,
        "render_ok": bool(render.get("ok", False)) if render else None,
        "render_pdf_count": render.get("pdf_count") if render else None,
        "render_png_count": render.get("png_count") if render else None,
    }


def gate_task(blocker: str) -> dict[str, str]:
    lower = blocker.lower()
    if re.search(r"\b(approval|upload|submit|certify|certification)\b", lower):
        return {
            "gate": "Action-time approval",
            "capture": "Explicit user approval at the moment of upload/certification/submit.",
            "proof": "Approval occurs during the live portal action, not earlier in the planning packet.",
        }
    if "baat" in lower:
        return {
            "gate": "BAAT authority",
            "capture": "Organization visible, user associated, submitter role, DICE opportunity visible, accepted file types, preview behavior.",
            "proof": "Non-secret portal status facts recorded in the worksheet.",
        }
    if "dsip" in lower or "organization linkage" in lower:
        return {
            "gate": "DSIP authority",
            "capture": "Organization linked, user role, topic visible, volume requirements, budget/forms, preview behavior.",
            "proof": "Non-secret DSIP status facts recorded in the worksheet.",
        }
    if "cmmc" in lower or "sprs" in lower or "cyber" in lower:
        return {
            "gate": "CMMC/SPRS/cybersecurity representation",
            "capture": "PIEE/SPRS access, Cyber Vendor User role, CAGE hierarchy, Affirming Official path, current score/status if any.",
            "proof": "Reviewed factual status or explicitly unknown status; no unsupported certification claim.",
        }
    if "foci" in lower or "export" in lower or "ownership" in lower:
        return {
            "gate": "DoD reps / FOCI / export / ownership",
            "capture": "User-reviewed factual company status for required DoD representations.",
            "proof": "Representation answers reviewed before any portal affirmation.",
        }
    if "cost" in lower or "rom" in lower:
        return {
            "gate": "Cost basis",
            "capture": "Whether rates, fringe, indirects, consultants, cloud/HPC, travel, materials, and fee are reviewed.",
            "proof": "ROM language preserved or reviewed budget basis replaces it.",
        }
    if "signoff" in lower or "review" in lower or "matrix" in lower or "reference" in lower:
        return {
            "gate": "Human/domain signoff",
            "capture": "Who reviewed the matrix/claims, what they accepted, and which boundaries remain.",
            "proof": "Written reviewer note or user approval, without implying endorsement.",
        }
    if "duplicate" in lower or "paste" in lower or "legal business" in lower or "pi/founder" in lower:
        return {
            "gate": "NSF portal identity and paste check",
            "capture": "Legal company name, PI/founder title, duplicate-pitch status, and pasted field counts.",
            "proof": "Portal-safe facts recorded before final save/submit.",
        }
    return {
        "gate": "Package-specific blocker",
        "capture": "Record the exact non-secret fact that resolves this blocker.",
        "proof": "Evidence is documented in the capture worksheet or package notes.",
    }


def safe_fact(fact: str) -> str:
    sanitized = fact
    for pattern, replacement in SENSITIVE_FACT_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    sanitized = sanitized.replace(
        "SAM entity identifier recorded, SAM entity identifier recorded",
        "SAM entity identifiers recorded",
    )
    return sanitized


def package_card(name: str, pkg: dict[str, Any]) -> dict[str, Any]:
    meta = PACKAGE_PRIORITY.get(name, {"rank": 99, "deadline_hint": "Verify in portal.", "why_now": "", "primary_unlock": ""})
    blockers = [str(item) for item in pkg.get("portal_user_blockers", []) or []]
    tasks = []
    seen = set()
    for blocker in blockers:
        task = gate_task(blocker)
        key = (task["gate"], task["capture"])
        if key in seen:
            continue
        seen.add(key)
        tasks.append({**task, "source_blocker": blocker})
    local_blockers = [str(item) for item in pkg.get("local_blockers", []) or []]
    verified_facts = [safe_fact(str(item)) for item in pkg.get("verified_portal_facts", []) or []]
    return {
        "rank": meta["rank"],
        "package": name,
        "portal": pkg.get("portal", ""),
        "readiness": pkg.get("readiness", "UNKNOWN"),
        "local_ready": len(local_blockers) == 0,
        "ready_to_submit": len(local_blockers) == 0 and len(blockers) == 0,
        "deadline_hint": meta["deadline_hint"],
        "why_now": meta["why_now"],
        "primary_unlock": meta["primary_unlock"],
        "artifact_counts": artifact_counts(pkg),
        "verified_strengths": verified_facts,
        "local_blockers": local_blockers,
        "portal_user_blockers": blockers,
        "next_capture_tasks": tasks,
    }


def build_board(readiness: dict[str, Any] | None = None) -> dict[str, Any]:
    readiness = readiness or read_json(READINESS_JSON)
    freeze = read_json(FREEZE_JSON)
    support_pack = read_json(SUPPORT_PACK_JSON)
    red_team_gate = read_json(RED_TEAM_GATE_JSON)
    packages = package_by_name(readiness)
    cards = [
        package_card(name, packages[name])
        for name in PACKAGE_PRIORITY
        if name in packages
    ]
    cards.sort(key=lambda row: row["rank"])
    return {
        "generated_utc": now_utc(),
        "schema": "action_time_submission_board_v1",
        "readiness_source": str(READINESS_JSON.relative_to(ROOT)).replace("\\", "/"),
        "source_posture": readiness.get("posture", "UNKNOWN"),
        "summary": readiness.get("summary", {}),
        "decision": (
            "DICE remains the first live-portal unlock. HarborSentinel is second and should be previewed "
            "as soon as DSIP topic/forms access is available. NSF Project Pitch remains the fastest low-friction "
            "cash-path candidate if the portal state allows a clean pitch."
        ),
        "safety_rules": SAFETY_RULES,
        "package_freeze": {
            "available": FREEZE_MD.exists(),
            "markdown": str(FREEZE_MD.relative_to(ROOT)).replace("\\", "/") if FREEZE_MD.exists() else "",
            "json": str(FREEZE_JSON.relative_to(ROOT)).replace("\\", "/") if FREEZE_JSON.exists() else "",
            "signature_sha256": str(freeze.get("freeze_signature_sha256", "")) if freeze else "",
            "boundary": (
                "The freeze hashes local package artifacts only; it does not clear portal, compliance, cost, "
                "team, preview, or action-time approval gates."
            ),
        },
        "portal_preview_runbook": {
            "available": PORTAL_RUNBOOK_MD.exists(),
            "markdown": str(PORTAL_RUNBOOK_MD.relative_to(ROOT)).replace("\\", "/") if PORTAL_RUNBOOK_MD.exists() else "",
            "json": str(PORTAL_RUNBOOK_JSON.relative_to(ROOT)).replace("\\", "/") if PORTAL_RUNBOOK_JSON.exists() else "",
            "boundary": (
                "Use this only to navigate, preview, and record non-secret facts. "
                "It does not authorize upload finalization, certification, consent, signature, lock, or submit."
            ),
        },
        "support_outreach_pack": {
            "available": SUPPORT_PACK_MD.exists(),
            "markdown": str(SUPPORT_PACK_MD.relative_to(ROOT)).replace("\\", "/") if SUPPORT_PACK_MD.exists() else "",
            "json": str(SUPPORT_PACK_JSON.relative_to(ROOT)).replace("\\", "/") if SUPPORT_PACK_JSON.exists() else "",
            "official_support_lanes": len(support_pack.get("official_support_lanes", []) or []),
            "sign_in_targets": [
                str(item.get("site", ""))
                for item in support_pack.get("sign_in_queue", []) or []
                if isinstance(item, dict) and item.get("site")
            ],
            "boundary": (
                "Use this to contact support organizations and capture non-secret readiness facts. "
                "It does not authorize upload, certification, signature, submission, legal representation, "
                "trading, or investment claims."
            ),
        },
        "reviewer_red_team_gate": {
            "available": RED_TEAM_GATE_MD.exists(),
            "markdown": str(RED_TEAM_GATE_MD.relative_to(ROOT)).replace("\\", "/") if RED_TEAM_GATE_MD.exists() else "",
            "json": str(RED_TEAM_GATE_JSON.relative_to(ROOT)).replace("\\", "/") if RED_TEAM_GATE_JSON.exists() else "",
            "packages_reviewed": int((red_team_gate.get("summary", {}) or {}).get("packages_reviewed", 0) or 0),
            "portal_user_blockers": int((red_team_gate.get("summary", {}) or {}).get("portal_user_blockers", 0) or 0),
            "ready_for_upload_count": int((red_team_gate.get("summary", {}) or {}).get("ready_for_upload_count", 0) or 0),
            "verdict": str(red_team_gate.get("global_reviewer_verdict", "")),
            "boundary": (
                "Use this to pressure-test reviewer objections and claim boundaries. "
                "It does not authorize upload, certification, signature, submission, cost certification, "
                "CMMC/SPRS representation, or award-likelihood claims."
            ),
        },
        "cards": cards,
    }


def render_markdown(board: dict[str, Any]) -> str:
    summary = board.get("summary", {})
    lines = [
        "# Action-Time Submission Board",
        "",
        f"Generated UTC: {board['generated_utc']}",
        "",
        f"Source posture: `{board.get('source_posture', 'UNKNOWN')}`",
        "",
        "## Decision",
        "",
        board["decision"],
        "",
        "## Current Counts",
        "",
        f"- Packages tracked: {summary.get('packages', 0)}",
        f"- Local blockers: {summary.get('local_blockers', 0)}",
        f"- Portal/user blockers: {summary.get('portal_user_blockers', 0)}",
        "",
        "## Package Freeze",
        "",
    ]
    freeze = board.get("package_freeze", {})
    if freeze.get("available"):
        lines.extend(
            [
                f"- Freeze packet: `{freeze.get('markdown')}`",
                f"- Freeze signature SHA-256: `{freeze.get('signature_sha256') or 'not recorded'}`",
                f"- Boundary: {freeze.get('boundary')}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "- Freeze packet: not generated yet",
                "- Boundary: generate the freeze before portal upload preview.",
                "",
            ]
        )
    runbook = board.get("portal_preview_runbook", {})
    if runbook.get("available"):
        lines.extend(
            [
                f"- Portal preview runbook: `{runbook.get('markdown')}`",
                f"- Runbook boundary: {runbook.get('boundary')}",
                "",
            ]
        )
    support = board.get("support_outreach_pack", {})
    lines.extend(["## Support Outreach", ""])
    if support.get("available"):
        lines.extend(
            [
                f"- Outreach pack: `{support.get('markdown')}`",
                f"- Official support lanes: {support.get('official_support_lanes', 0)}",
                f"- Boundary: {support.get('boundary')}",
                "- Sign-in targets:",
            ]
        )
        lines.extend(f"  - {target}" for target in support.get("sign_in_targets", []))
        lines.append("")
    else:
        lines.extend(
            [
                "- Outreach pack: not generated yet",
                "- Boundary: generate support outreach before contacting external reviewers or support organizations.",
                "",
            ]
        )
    red_team = board.get("reviewer_red_team_gate", {})
    lines.extend(["## Reviewer Red-Team Gate", ""])
    if red_team.get("available"):
        lines.extend(
            [
                f"- Red-team gate: `{red_team.get('markdown')}`",
                f"- Packages reviewed: {red_team.get('packages_reviewed', 0)}",
                f"- Portal/user blockers: {red_team.get('portal_user_blockers', 0)}",
                f"- Ready for upload count: {red_team.get('ready_for_upload_count', 0)}",
                f"- Verdict: {red_team.get('verdict')}",
                f"- Boundary: {red_team.get('boundary')}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "- Red-team gate: not generated yet",
                "- Boundary: run reviewer red-team gate before treating DICE or Harbor as reviewer-ready.",
                "",
            ]
        )
    lines.extend(
        [
        "## Universal Safety Rules",
        "",
        ]
    )
    lines.extend(f"- {rule}" for rule in board["safety_rules"])
    lines.extend(["", "## Action Order", ""])
    for card in board["cards"]:
        counts = card["artifact_counts"]
        lines.extend(
            [
                f"### {card['rank']}. {card['package']} ({card['portal']})",
                "",
                f"- Readiness: `{card['readiness']}`",
                f"- Ready to submit: `{card['ready_to_submit']}`",
                f"- Deadline/window hint: {card['deadline_hint']}",
                f"- Why now: {card['why_now']}",
                f"- Primary unlock: {card['primary_unlock']}",
                f"- Required artifacts present: {counts['required_artifacts_present']}/{counts['required_artifacts_total']}",
                f"- Evidence manifest matches: {counts['evidence_manifest_matched']}/{counts['evidence_manifest_expected']}",
            ]
        )
        if counts.get("render_ok") is not None:
            lines.append(
                f"- Render QA: ok={counts['render_ok']}, pdfs={counts['render_pdf_count']}, pngs={counts['render_png_count']}"
            )
        if card["verified_strengths"]:
            lines.append("- Verified strengths:")
            lines.extend(f"  - {fact}" for fact in card["verified_strengths"])
        if card["local_blockers"]:
            lines.append("- Local blockers:")
            lines.extend(f"  - {item}" for item in card["local_blockers"])
        else:
            lines.append("- Local blockers: none")
        lines.append("- Portal/user blockers:")
        if card["portal_user_blockers"]:
            lines.extend(f"  - {item}" for item in card["portal_user_blockers"])
        else:
            lines.append("  - none")
        lines.append("- Next capture tasks:")
        for task in card["next_capture_tasks"]:
            lines.extend(
                [
                    f"  - Gate: {task['gate']}",
                    f"    Capture: {task['capture']}",
                    f"    Proof required: {task['proof']}",
                ]
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    board = build_board()
    write_json(OUT_JSON, board)
    write_text(OUT_MD, render_markdown(board))
    print(
        json.dumps(
            {
                "posture": board["source_posture"],
                "packages": len(board["cards"]),
                "portal_user_blockers": board.get("summary", {}).get("portal_user_blockers", 0),
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
