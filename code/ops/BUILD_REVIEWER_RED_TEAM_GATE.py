from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GRANTS = ROOT / "grant_submissions"
OUT = ROOT / "out" / "ops"

READINESS_JSON = OUT / "grant_submission_readiness_audit_latest.json"
CONFORMANCE_JSON = OUT / "submission_conformance_gate_latest.json"
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
        "conformance_lane_id": "darpa_dice_full_submission",
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
        "conformance_lane_id": None,
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


def score_package(
    pkg: dict[str, Any],
    matrix_text: str,
    checks: list[dict[str, Any]],
    conformance: dict[str, Any],
) -> dict[str, Any]:
    artifacts = artifact_summary(pkg)
    portal_blockers = [str(item) for item in pkg.get("portal_user_blockers", []) or []]
    local_blockers = [str(item) for item in pkg.get("local_blockers", []) or []]
    present_phrase_count = sum(1 for item in checks if item["present"])
    total_phrase_count = len(checks)

    artifact_custody_score = 0
    if artifacts["all_required_artifacts_present"]:
        artifact_custody_score += 2
    if artifacts["all_evidence_manifests_matched"]:
        artifact_custody_score += 2
    if artifacts["render_ok"] is True:
        artifact_custody_score += 1
    if not local_blockers:
        artifact_custody_score += 1

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

    conformance_status = str(conformance.get("status", "MISSING_SUBMISSION_CONFORMANCE_RECORD"))
    argument_conformance_pass = bool(conformance.get("argument_conformance_pass", False))
    if conformance_status == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY":
        reviewer_gate_posture = "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    elif not conformance:
        reviewer_gate_posture = "LOCAL_REVIEWER_BLOCKED_ARGUMENT_GATE_UNASSESSED"
    elif bool(conformance.get("technical_argument_required", False)) and not argument_conformance_pass:
        reviewer_gate_posture = "LOCAL_REVIEWER_BLOCKED_ARGUMENT_CONFORMANCE"
    elif local_blockers or artifact_custody_score < 5:
        reviewer_gate_posture = "LOCAL_REVIEWER_NEEDS_ARTIFACT_REPAIR"
    elif portal_blockers:
        reviewer_gate_posture = "ARGUMENT_CONFORMANT_LOCAL_REVIEW_PORTAL_BLOCKED"
    else:
        reviewer_gate_posture = "ARGUMENT_CONFORMANT_PENDING_HUMAN_SIGNOFF"

    return {
        "artifact_custody_score": artifact_custody_score,
        "artifact_custody_score_max": 6,
        "self_authored_phrase_checks_present": present_phrase_count,
        "self_authored_phrase_checks_total": total_phrase_count,
        "self_authored_phrase_checks_informational_only": True,
        "claim_boundary_markers": claim_boundary_score,
        "claim_boundary_markers_max": len(boundary_markers),
        "local_blocker_count": len(local_blockers),
        "portal_user_blocker_count": len(portal_blockers),
        "portal_blocked": bool(portal_blockers),
        "submission_conformance_status": conformance_status,
        "argument_conformance_pass": argument_conformance_pass,
        "reviewer_gate_posture": reviewer_gate_posture,
    }


def build_package_gate(
    name: str,
    pkg: dict[str, Any],
    config: dict[str, Any],
    conformance: dict[str, Any],
) -> dict[str, Any]:
    matrix = Path(config["matrix"])
    matrix_text = read_text(matrix)
    checks = phrase_checks(matrix_text, list(config["required_matrix_phrases"]))
    scores = score_package(pkg, matrix_text, checks, conformance)
    artifact_or_portal_facts = [sanitize(str(item)) for item in pkg.get("verified_portal_facts", []) or []]
    blockers = [sanitize(str(item)) for item in pkg.get("portal_user_blockers", []) or []]
    local_blockers = [sanitize(str(item)) for item in pkg.get("local_blockers", []) or []]
    failed_phrase_checks = [item["phrase"] for item in checks if not item["present"]]
    reviewer_objections = []
    if name == "DICE":
        reviewer_objections = [
            "The abstract did not provide a submission-blocking crosswalk from every program objective to a claim, metric, experiment, and acceptance threshold.",
            "A generic centralized assignment comparison did not establish improvement over a named current state-of-the-art multi-agent orchestration baseline.",
            "Synthetic task executors did not exercise inference-time control of heterogeneous foundation-model agents.",
            "The one-person team, uncommitted collaborators, and insufficient local compute left execution credibility unresolved.",
        ]
    elif name == "HarborSentinel":
        reviewer_objections = [
            "Public AIS is not Navy sensor data and cannot validate ADS-B, radar, SSDS, or field performance.",
            "Controlled injections are useful first tests but can be too easy without labels or adjudication.",
            "Natural candidate rates are not false-positive rates.",
            "CMMC/SPRS, export/FOCI, cost, and DSIP authority remain factual gates.",
        ]
    must_fix = list(config["must_fix_before_upload"])
    if scores["reviewer_gate_posture"] == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY":
        must_fix = [
            "Closed route: preserve the source-bound postmortem and do not treat artifact custody as technical merit.",
            str(
                conformance.get(
                    "next_action",
                    "Preserve the official decision and postmortem; do not upload or recycle this packet as an active route.",
                )
            )
        ]
    elif not scores["argument_conformance_pass"]:
        must_fix.insert(
            0,
            str(
                conformance.get(
                    "next_action",
                    "Complete a source-bound submission conformance review before calling this package reviewer-ready.",
                )
            ),
        )

    return {
        "package": name,
        "conformance_lane_id": config.get("conformance_lane_id"),
        "portal": str(pkg.get("portal", "")),
        "readiness": str(pkg.get("readiness", "UNKNOWN")),
        "matrix": rel(matrix),
        "highest_value_question": str(config["highest_value_question"]),
        "artifact_summary": artifact_summary(pkg),
        "phrase_checks": checks,
        "phrase_checks_informational_only": True,
        "failed_phrase_checks": failed_phrase_checks,
        "scores": scores,
        "artifact_or_portal_facts": artifact_or_portal_facts,
        "local_blockers": local_blockers,
        "portal_user_blockers": blockers,
        "reviewer_objections": reviewer_objections,
        "must_fix_before_upload": must_fix,
        "ready_for_upload": False,
        "upload_boundary": "Fresh user action-time approval and portal/compliance/cost gates remain required.",
    }


def build_conformance_only_gate(conformance: dict[str, Any]) -> dict[str, Any]:
    lane_id = str(conformance.get("lane_id", ""))
    status = str(conformance.get("status", "MISSING_SUBMISSION_CONFORMANCE_RECORD"))
    active = conformance.get("submission_candidate_active") is True
    argument_pass = conformance.get("argument_conformance_pass") is True
    candidate = conformance.get("candidate_artifact")
    official_source = conformance.get("official_source")
    candidate_present = bool(
        isinstance(candidate, dict) and candidate.get("present") is True
    )
    official_source_present = bool(
        isinstance(official_source, dict) and official_source.get("present") is True
    )

    if status == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY":
        posture = "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    elif status == "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED":
        posture = "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED"
    elif status == "TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY":
        posture = "TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY"
    elif status == "MONITOR_ONLY_NO_DUPLICATE_SUBMISSION":
        posture = "MONITOR_ONLY_NO_DUPLICATE_SUBMISSION"
    elif active and not argument_pass:
        posture = "LOCAL_REVIEWER_BLOCKED_ARGUMENT_CONFORMANCE"
    elif not active:
        posture = "LOCAL_REVIEWER_BLOCKED_BEFORE_ACTIVE_CANDIDATE"
    else:
        posture = "ARGUMENT_CONFORMANT_PENDING_HUMAN_SIGNOFF"

    criteria = [
        row
        for row in conformance.get("criteria", [])
        if isinstance(row, dict)
    ]
    reviewer_objections = []
    for criterion in criteria:
        if criterion.get("passed") is True:
            continue
        criterion_id = str(criterion.get("criterion_id", "unknown_criterion"))
        finding = str(criterion.get("finding", "No source-bound finding is registered."))
        missing = [
            str(item)
            for item in criterion.get("missing_evidence", [])
            if str(item).strip()
        ]
        objection = f"{criterion_id}: {finding}"
        if missing:
            objection += " Missing: " + "; ".join(missing)
        reviewer_objections.append(objection)
    if not reviewer_objections and not argument_pass:
        reviewer_objections.append(
            "The source-bound technical argument has not passed every required criterion."
        )

    artifact_facts = []
    if candidate_present:
        artifact_facts.append(
            f"Candidate artifact is present: {candidate.get('path', '')}"
        )
    if official_source_present:
        artifact_facts.append(
            f"Official-source artifact is present: {official_source.get('path', '')}"
        )
    if not artifact_facts:
        artifact_facts.append(
            "No candidate or official-source artifact is cited as reviewer-ready evidence."
        )

    must_fix = [str(conformance.get("next_action", "")).strip()]
    must_fix.extend(
        f"Close source-bound criterion: {criterion.get('criterion_id', 'unknown')}"
        for criterion in criteria
        if criterion.get("passed") is not True
    )
    must_fix = [item for item in must_fix if item]

    artifact_summary_row = {
        "required_artifacts_present": 1 if candidate_present else 0,
        "required_artifacts_total": 1,
        "all_required_artifacts_present": candidate_present,
        "evidence_manifest_matched": 0,
        "evidence_manifest_expected": 0,
        "all_evidence_manifests_matched": False,
        "render_ok": None,
    }
    return {
        "package": str(conformance.get("name", lane_id)),
        "conformance_lane_id": lane_id,
        "portal": "submission_conformance_registry",
        "readiness": status,
        "matrix": "",
        "highest_value_question": (
            "Can a reviewer trace every required program objective, leap, baseline, "
            "metric, experiment, evidence boundary, execution commitment, risk, and "
            "falsifier to current sources?"
        ),
        "artifact_summary": artifact_summary_row,
        "phrase_checks": [],
        "phrase_checks_informational_only": True,
        "failed_phrase_checks": [],
        "scores": {
            "artifact_custody_score": (
                (1 if candidate_present else 0)
                + (1 if official_source_present else 0)
            ),
            "artifact_custody_score_max": 6,
            "self_authored_phrase_checks_present": 0,
            "self_authored_phrase_checks_total": 0,
            "self_authored_phrase_checks_informational_only": True,
            "claim_boundary_markers": 1
            if str(conformance.get("claim_boundary", "")).strip()
            else 0,
            "claim_boundary_markers_max": 1,
            "local_blocker_count": len(reviewer_objections),
            "portal_user_blocker_count": 0,
            "portal_blocked": False,
            "submission_conformance_status": status,
            "argument_conformance_pass": argument_pass,
            "reviewer_gate_posture": posture,
        },
        "artifact_or_portal_facts": artifact_facts,
        "local_blockers": reviewer_objections,
        "portal_user_blockers": [],
        "reviewer_objections": reviewer_objections,
        "must_fix_before_upload": must_fix,
        "ready_for_upload": False,
        "upload_boundary": (
            "Fresh human action-time approval and every source, argument, portal, "
            "eligibility, compliance, cost, and certification gate remain required."
        ),
    }


def build_gate(readiness: dict[str, Any] | None = None) -> dict[str, Any]:
    readiness = readiness or read_json(READINESS_JSON)
    conformance_payload = read_json(CONFORMANCE_JSON)
    conformance_rows = {
        str(row.get("lane_id", "")): row
        for row in conformance_payload.get("lanes", [])
        if isinstance(row, dict)
    }
    packages = package_by_name(readiness)
    gates = [
        build_package_gate(
            name,
            packages[name],
            config,
            conformance_rows.get(str(config.get("conformance_lane_id") or ""), {}),
        )
        for name, config in PACKAGE_CONFIG.items()
        if name in packages
    ]
    represented_conformance_lane_ids = {
        str(gate.get("conformance_lane_id", ""))
        for gate in gates
        if str(gate.get("conformance_lane_id", "")).strip()
    }
    gates.extend(
        build_conformance_only_gate(row)
        for row in sorted(
            conformance_rows.values(),
            key=lambda item: str(item.get("lane_id", "")),
        )
        if row.get("technical_argument_required") is True
        and str(row.get("lane_id", "")) not in represented_conformance_lane_ids
    )
    total_portal = sum(item["scores"]["portal_user_blocker_count"] for item in gates)
    argument_pass_count = sum(1 for gate in gates if gate["scores"]["argument_conformance_pass"])
    closed_count = sum(
        1
        for gate in gates
        if gate["scores"]["reviewer_gate_posture"] == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    )
    argument_blocked_count = sum(
        1
        for gate in gates
        if gate["scores"]["argument_conformance_pass"] is False
        and gate["scores"]["reviewer_gate_posture"]
        != "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    )
    active_conformance_lane_ids = {
        lane_id
        for lane_id, row in conformance_rows.items()
        if row.get("submission_candidate_active") is True
        and row.get("technical_argument_required") is True
    }
    reviewed_conformance_lane_ids = {
        str(gate.get("conformance_lane_id", ""))
        for gate in gates
        if str(gate.get("conformance_lane_id", "")).strip()
    }
    unrepresented_active_lane_ids = sorted(
        active_conformance_lane_ids - reviewed_conformance_lane_ids
    )
    active_candidate_gates = [
        gate
        for gate in gates
        if str(gate.get("conformance_lane_id", "")) in active_conformance_lane_ids
    ]
    payload = {
        "generated_utc": now_utc(),
        "schema": "reviewer_red_team_gate_v2",
        "boundary": BOUNDARY,
        "source_readiness": rel(READINESS_JSON),
        "source_submission_conformance": rel(CONFORMANCE_JSON),
        "source_posture": readiness.get("posture", "UNKNOWN"),
        "summary": {
            "packages_reviewed": len(gates),
            "portal_user_blockers": total_portal,
            "ready_for_upload_count": 0,
            "argument_conformance_pass_count": argument_pass_count,
            "closed_official_decision_count": closed_count,
            "argument_blocked_count": argument_blocked_count,
            "technical_conformance_lane_count": sum(
                1
                for row in conformance_rows.values()
                if row.get("technical_argument_required") is True
            ),
            "active_submission_candidate_count": len(
                active_conformance_lane_ids
            ),
            "active_candidate_gate_count": len(active_candidate_gates),
            "active_candidate_argument_blocked_count": sum(
                1
                for gate in active_candidate_gates
                if gate["scores"]["argument_conformance_pass"] is False
            ),
            "unrepresented_active_conformance_lane_count": len(
                unrepresented_active_lane_ids
            ),
            "unrepresented_active_conformance_lane_ids": (
                unrepresented_active_lane_ids
            ),
            "argument_conformant_local_review_portal_blocked": sum(
                1
                for gate in gates
                if gate["scores"]["reviewer_gate_posture"] == "ARGUMENT_CONFORMANT_LOCAL_REVIEW_PORTAL_BLOCKED"
            ),
        },
        "global_reviewer_verdict": (
            "No package is upload-ready. Artifact custody and self-authored matrix "
            "phrases do not substitute for source-bound argument conformance; every "
            "active candidate is represented, blocked candidates remain blocked, "
            "expired and no-go routes cannot be revived, and sent routes cannot be "
            "duplicated."
        ),
        "reviewer_gates": gates,
        "no_claims": [
            "Do not claim guaranteed funding, guaranteed awards, agency endorsement, partner commitment, CMMC/SPRS status, field validation, trading profit, or institutional-grade execution.",
            "Do not cite SAM identifiers, private portal screenshots, passwords, MFA codes, API keys, banking data, or tax identifiers in reviewer packets.",
        ],
    }
    payload["reviewer_gate_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


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
        f"- Argument conformance passes: {payload['summary']['argument_conformance_pass_count']}",
        f"- Closed official decisions: {payload['summary']['closed_official_decision_count']}",
        f"- Argument blocked or unassessed: {payload['summary']['argument_blocked_count']}",
        f"- Technical conformance lanes: {payload['summary']['technical_conformance_lane_count']}",
        f"- Active submission candidates: {payload['summary']['active_submission_candidate_count']}",
        f"- Active candidate gates: {payload['summary']['active_candidate_gate_count']}",
        f"- Active candidate argument blocks: {payload['summary']['active_candidate_argument_blocked_count']}",
        f"- Unrepresented active conformance lanes: {payload['summary']['unrepresented_active_conformance_lane_count']}",
        f"- Argument-conformant but portal-blocked: {payload['summary']['argument_conformant_local_review_portal_blocked']}",
        f"- Reviewer gate SHA-256: `{payload['reviewer_gate_sha256']}`",
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
                f"- Submission conformance: `{scores['submission_conformance_status']}`",
                f"- Argument conformance pass: `{str(scores['argument_conformance_pass']).lower()}`",
                f"- Artifact custody score: {scores['artifact_custody_score']}/{scores['artifact_custody_score_max']}",
                f"- Self-authored phrase checks: {scores['self_authored_phrase_checks_present']}/{scores['self_authored_phrase_checks_total']} (informational only)",
                f"- Claim-boundary markers: {scores['claim_boundary_markers']}/{scores['claim_boundary_markers_max']}",
                f"- Required artifacts: {artifacts['required_artifacts_present']}/{artifacts['required_artifacts_total']}",
                f"- Evidence manifests: {artifacts['evidence_manifest_matched']}/{artifacts['evidence_manifest_expected']}",
                f"- Render OK: {artifacts['render_ok']}",
                f"- Highest-value reviewer question: {gate['highest_value_question']}",
                "",
                "### Artifact Or Portal Facts",
                "",
            ]
        )
        if gate["artifact_or_portal_facts"]:
            lines.extend(f"- {item}" for item in gate["artifact_or_portal_facts"])
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
