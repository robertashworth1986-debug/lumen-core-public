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
OUT_JSON = OUT / "reviewer_red_team_gate_latest.json"
OUT_MD = GRANTS / "REVIEWER_RED_TEAM_GATE_2026-06-20.md"

DICE_MATRIX = GRANTS / "DICE_HR001126S0010" / "DICE_HEILMEIER_REVIEWER_MATRIX_2026-06-20.md"
HARBOR_MATRIX = GRANTS / "NV063_HarborSentinel" / "NV063_NAVY_REVIEWER_PROOF_MATRIX_2026-06-20.md"
DICE_REFERENCE = GRANTS / "DICE_HR001126S0010" / "DICE_REFERENCE_RELEVANCE_MATRIX_2026-06-20.md"
HARBOR_INJECTION = GRANTS / "NV063_HarborSentinel" / "NV063_AIS_INJECTION_BENCHMARK_2026-06-20.md"


BOUNDARY = (
    "This red-team gate is a local reviewer readiness control. It does not "
    "authorize upload, certification, signature, submission, legal claims, cost "
    "certification, CMMC/SPRS representation, partner claims, trading claims, or "
    "award likelihood claims."
)

SENSITIVE_PATTERNS = [
    re.compile(r"\bUEI\s+[A-Z0-9]{8,16}\b", re.IGNORECASE),
    re.compile(r"\bCAGE/NCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
    re.compile(r"\bCAGE\s+[A-Z0-9]{3,10}\b", re.IGNORECASE),
]

PACKAGE_CONFIG = {
    "DICE": {
        "matrix": DICE_MATRIX,
        "required_matrix_phrases": [
            "DICE performance has been proven",
            "Foundation-model scale has been demonstrated",
            "BAAT authority is complete",
            "trading, live-breadth, or frozen-delta results prove grant merit",
            "Phase I measurement program",
            "frozen live-breadth replay",
            "provenance-gated live-breadth annex",
            "context-only estimates",
            "false-rejection cost",
        ],
        "highest_value_question": "Can a DARPA reviewer see a measurable Phase I experiment instead of a vague autonomy claim?",
        "must_fix_before_upload": [
            "BAAT organization, role, DICE opportunity visibility, accepted file types, and preview behavior.",
            "Human signoff on Heilmeier answers and reference relevance.",
            "ROM cost wording preserved or replaced by a reviewed cost basis.",
            "Fresh action-time approval before upload, certification, consent, or submit.",
        ],
    },
    "HarborSentinel": {
        "matrix": HARBOR_MATRIX,
        "required_matrix_phrases": [
            "Controlled injections can be too easy",
            "Natural candidate rates are review queues, not false-positive rates",
            "Public AIS validates Navy radar",
            "CMMC/SPRS, clearance, export, FOCI",
            "bounded public AIS controlled-injection benchmark",
            "unlabeled public AIS review-burden profile",
            "natural candidate rates are review queues, not false-positive rates",
            "LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md",
            "measurement discipline and chain-of-custody",
        ],
        "highest_value_question": "Can a Navy reviewer see strong public AIS evidence without mistaking it for field validation?",
        "must_fix_before_upload": [
            "DSIP organization linkage, submitter role, topic visibility, required forms, and preview behavior.",
            "DoD representations, FOCI, export, cybersecurity, CMMC/SPRS, and U.S. ownership/operation facts.",
            "Domain/team signoff on evidence boundaries and representative-data assumptions.",
            "Cost basis reviewed or explicitly preserved as ROM planning language.",
            "Fresh action-time approval before upload, certification, consent, or submit.",
        ],
    },
}


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


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def sanitize(text: str) -> str:
    clean = text
    for pattern in SENSITIVE_PATTERNS:
        clean = pattern.sub("SAM entity identifier recorded", clean)
    clean = clean.replace(
        "SAM entity identifier recorded, SAM entity identifier recorded",
        "SAM entity identifiers recorded",
    )
    return clean


def package_by_name(readiness: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packages = readiness.get("packages", [])
    if not isinstance(packages, list):
        return {}
    return {
        str(row.get("name")): row
        for row in packages
        if isinstance(row, dict) and row.get("name")
    }


def artifact_summary(pkg: dict[str, Any]) -> dict[str, Any]:
    artifacts = pkg.get("required_artifacts", [])
    manifests = pkg.get("evidence_manifests", [])
    if not isinstance(artifacts, list):
        artifacts = []
    if not isinstance(manifests, list):
        manifests = []
    present = sum(1 for row in artifacts if isinstance(row, dict) and row.get("exists"))
    expected = len(artifacts)
    matched = sum(int(row.get("matched", 0) or 0) for row in manifests if isinstance(row, dict))
    manifest_expected = sum(int(row.get("expected", 0) or 0) for row in manifests if isinstance(row, dict))
    return {
        "required_artifacts_present": present,
        "required_artifacts_total": expected,
        "all_required_artifacts_present": expected > 0 and present == expected,
        "evidence_manifest_matched": matched,
        "evidence_manifest_expected": manifest_expected,
        "all_evidence_manifests_matched": manifest_expected > 0 and matched == manifest_expected,
        "render_ok": bool((pkg.get("render") or {}).get("ok", False)) if isinstance(pkg.get("render"), dict) else None,
    }


def phrase_checks(text: str, phrases: list[str]) -> list[dict[str, Any]]:
    lower = text.lower()
    return [
        {
            "phrase": phrase,
            "present": phrase.lower() in lower,
        }
        for phrase in phrases
    ]


def score_package(pkg: dict[str, Any], matrix_text: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    artifacts = artifact_summary(pkg)
    portal_blockers = [str(item) for item in pkg.get("portal_user_blockers", []) or []]
    local_blockers = [str(item) for item in pkg.get("local_blockers", []) or []]
    present_phrase_count = sum(1 for item in checks if item["present"])
    total_phrase_count = len(checks)

    evidence_score = 0
    if artifacts["all_required_artifacts_present"]:
        evidence_score += 2
    if artifacts["all_evidence_manifests_matched"]:
        evidence_score += 2
    if artifacts["render_ok"] is True:
        evidence_score += 1
    if present_phrase_count == total_phrase_count:
        evidence_score += 2
    elif present_phrase_count >= max(1, total_phrase_count - 1):
        evidence_score += 1
    if not local_blockers:
        evidence_score += 1

    claim_boundary_score = 0
    boundary_markers = [
        "does not authorize",
        "do not say or imply",
        "claims to avoid",
        "does not prove",
        "not field",
        "not a reviewed cost",
    ]
    matrix_lower = matrix_text.lower()
    claim_boundary_score = sum(1 for marker in boundary_markers if marker in matrix_lower)

    return {
        "evidence_score": evidence_score,
        "evidence_score_max": 8,
        "claim_boundary_markers": claim_boundary_score,
        "claim_boundary_markers_max": len(boundary_markers),
        "local_blocker_count": len(local_blockers),
        "portal_user_blocker_count": len(portal_blockers),
        "portal_blocked": bool(portal_blockers),
        "reviewer_gate_posture": (
            "LOCAL_REVIEWER_READY_PORTAL_BLOCKED"
            if evidence_score >= 7 and claim_boundary_score >= 3 and portal_blockers
            else "LOCAL_REVIEWER_NEEDS_REPAIR"
            if local_blockers or evidence_score < 6
            else "LOCAL_REVIEWER_READY_PENDING_HUMAN_SIGNOFF"
        ),
    }


def build_package_gate(name: str, pkg: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    matrix = Path(config["matrix"])
    matrix_text = read_text(matrix)
    checks = phrase_checks(matrix_text, list(config["required_matrix_phrases"]))
    scores = score_package(pkg, matrix_text, checks)
    strengths = [sanitize(str(item)) for item in pkg.get("verified_portal_facts", []) or []]
    blockers = [sanitize(str(item)) for item in pkg.get("portal_user_blockers", []) or []]
    local_blockers = [sanitize(str(item)) for item in pkg.get("local_blockers", []) or []]
    failed_phrase_checks = [item["phrase"] for item in checks if not item["present"]]
    reviewer_objections = []
    if name == "DICE":
        reviewer_objections = [
            "The system may sound speculative unless every claim is tied to a Phase I metric.",
            "Synthetic and preliminary benchmarks do not prove foundation-model scale or DICE performance.",
            "The ROM budget and BAAT authority are not solved by local file readiness.",
            "Team depth and collaborator credibility remain reviewer risk points.",
        ]
    elif name == "HarborSentinel":
        reviewer_objections = [
            "Public AIS is not Navy sensor data and cannot validate ADS-B, radar, SSDS, or field performance.",
            "Controlled injections are useful first tests but can be too easy without labels or adjudication.",
            "Natural candidate rates are not false-positive rates.",
            "CMMC/SPRS, export/FOCI, cost, and DSIP authority remain factual gates.",
        ]
    return {
        "package": name,
        "portal": str(pkg.get("portal", "")),
        "readiness": str(pkg.get("readiness", "UNKNOWN")),
        "matrix": rel(matrix),
        "highest_value_question": str(config["highest_value_question"]),
        "artifact_summary": artifact_summary(pkg),
        "phrase_checks": checks,
        "failed_phrase_checks": failed_phrase_checks,
        "scores": scores,
        "verified_strengths": strengths,
        "local_blockers": local_blockers,
        "portal_user_blockers": blockers,
        "reviewer_objections": reviewer_objections,
        "must_fix_before_upload": list(config["must_fix_before_upload"]),
        "ready_for_upload": False,
        "upload_boundary": "Fresh user action-time approval and portal/compliance/cost gates remain required.",
    }


def build_gate(readiness: dict[str, Any] | None = None) -> dict[str, Any]:
    readiness = readiness or read_json(READINESS_JSON)
    packages = package_by_name(readiness)
    gates = [
        build_package_gate(name, packages[name], config)
        for name, config in PACKAGE_CONFIG.items()
        if name in packages
    ]
    total_portal = sum(item["scores"]["portal_user_blocker_count"] for item in gates)
    return {
        "generated_utc": now_utc(),
        "schema": "reviewer_red_team_gate_v1",
        "boundary": BOUNDARY,
        "source_readiness": rel(READINESS_JSON),
        "source_posture": readiness.get("posture", "UNKNOWN"),
        "summary": {
            "packages_reviewed": len(gates),
            "portal_user_blockers": total_portal,
            "ready_for_upload_count": 0,
            "local_reviewer_ready_portal_blocked": sum(
                1
                for gate in gates
                if gate["scores"]["reviewer_gate_posture"] == "LOCAL_REVIEWER_READY_PORTAL_BLOCKED"
            ),
        },
        "global_reviewer_verdict": (
            "Strong local reviewer posture; do not upload until portal, compliance, cost, signoff, and action-time gates clear."
            if gates and all(gate["scores"]["evidence_score"] >= 7 for gate in gates)
            else "Reviewer posture still needs local repair before upload preview."
        ),
        "reviewer_gates": gates,
        "no_claims": [
            "Do not claim guaranteed funding, guaranteed awards, agency endorsement, partner commitment, CMMC/SPRS status, field validation, trading profit, or institutional-grade execution.",
            "Do not cite SAM identifiers, private portal screenshots, passwords, MFA codes, API keys, banking data, or tax identifiers in reviewer packets.",
        ],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Reviewer Red-Team Gate",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## Boundary",
        "",
        payload["boundary"],
        "",
        "## Verdict",
        "",
        payload["global_reviewer_verdict"],
        "",
        "## Summary",
        "",
        f"- Packages reviewed: {payload['summary']['packages_reviewed']}",
        f"- Portal/user blockers: {payload['summary']['portal_user_blockers']}",
        f"- Ready for upload count: {payload['summary']['ready_for_upload_count']}",
        f"- Local reviewer-ready but portal-blocked: {payload['summary']['local_reviewer_ready_portal_blocked']}",
        "",
    ]
    for gate in payload["reviewer_gates"]:
        scores = gate["scores"]
        artifacts = gate["artifact_summary"]
        lines.extend(
            [
                f"## {gate['package']} ({gate['portal']})",
                "",
                f"- Readiness: `{gate['readiness']}`",
                f"- Red-team posture: `{scores['reviewer_gate_posture']}`",
                f"- Evidence score: {scores['evidence_score']}/{scores['evidence_score_max']}",
                f"- Claim-boundary markers: {scores['claim_boundary_markers']}/{scores['claim_boundary_markers_max']}",
                f"- Required artifacts: {artifacts['required_artifacts_present']}/{artifacts['required_artifacts_total']}",
                f"- Evidence manifests: {artifacts['evidence_manifest_matched']}/{artifacts['evidence_manifest_expected']}",
                f"- Render OK: {artifacts['render_ok']}",
                f"- Highest-value reviewer question: {gate['highest_value_question']}",
                "",
                "### Strongest Defensible Evidence",
                "",
            ]
        )
        if gate["verified_strengths"]:
            lines.extend(f"- {item}" for item in gate["verified_strengths"])
        else:
            lines.append("- No portal facts are cited as strengths.")
        lines.extend(["", "### Reviewer Objections To Answer", ""])
        lines.extend(f"- {item}" for item in gate["reviewer_objections"])
        lines.extend(["", "### Must Fix Before Upload", ""])
        lines.extend(f"- {item}" for item in gate["must_fix_before_upload"])
        if gate["failed_phrase_checks"]:
            lines.extend(["", "### Missing Matrix Phrases", ""])
            lines.extend(f"- {item}" for item in gate["failed_phrase_checks"])
        lines.extend(["", "### Portal/User Blockers", ""])
        if gate["portal_user_blockers"]:
            lines.extend(f"- {item}" for item in gate["portal_user_blockers"])
        else:
            lines.append("- none")
        lines.append("")

    lines.extend(["## No-Claims", ""])
    lines.extend(f"- {item}" for item in payload["no_claims"])
    return "\n".join(lines).rstrip() + "\n"


def write_gate(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or build_gate()
    OUT.mkdir(parents=True, exist_ok=True)
    GRANTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    return payload


def main() -> int:
    payload = write_gate()
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "packages_reviewed": payload["summary"]["packages_reviewed"],
                "portal_user_blockers": payload["summary"]["portal_user_blockers"],
                "markdown": rel(OUT_MD),
                "json": rel(OUT_JSON),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
