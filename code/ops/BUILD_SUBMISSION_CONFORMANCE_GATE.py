from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

REGISTRY_PATH = SPRINT_DIR / "SUBMISSION_CONFORMANCE_REGISTRY_2026-07-25.json"
TRACTION_PATH = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
NEAR_DEADLINE_PATH = OUT_OPS / "near_deadline_submission_command_board_latest.json"
PUBLIC_LEADS_PATH = SPRINT_DIR / "CURRENT_PUBLIC_OPPORTUNITY_LEADS_2026-07-25.json"
FALCON_GAP_MAP_PATH = (
    ROOT
    / "grant_submissions"
    / "DPA26BZ04_DV016_FALCON"
    / "DPA26BZ04_DV016_GO_NO_GO_AND_DP2_GAP_MAP_2026-07-15.md"
)
OUT_JSON = OUT_OPS / "submission_conformance_gate_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "submission_conformance_gate.json"
OUT_MD = SPRINT_DIR / "SUBMISSION_CONFORMANCE_GATE_2026-07-25.md"

REGISTRY_SCHEMA = "lumencore.submission_conformance_registry.v1"
OUTPUT_SCHEMA = "lumencore.submission_conformance_gate.v1"

FEDERAL_AND_IP_CHANNELS = {
    "federal_registration",
    "federal_lab_tech_transfer",
    "federal_baa",
    "federal_contract",
    "federal_rfi",
    "federal_sbir",
    "federal_market_research",
    "federal_sources_sought",
    "ip_readiness",
}

REQUIRED_CRITERIA = (
    "official_source_current",
    "mandatory_format_and_route",
    "program_objective_trace",
    "foundational_leap",
    "named_sota_baseline",
    "program_metric_trace",
    "mission_specific_experiment",
    "evidence_applicability",
    "team_compute_execution",
    "risk_transition_and_falsifier",
)

CRITERION_STATES = {"PASS", "PARTIAL", "FAIL", "UNASSESSED"}
DISPOSITIONS = {
    "ACTIVE_SUBMISSION_CANDIDATE",
    "BLOCKED_TECHNICAL_NO_GO",
    "CLOSED_OFFICIAL_DECISION",
    "EXPIRED_NO_VERIFIED_SUBMISSION",
    "MONITOR_ONLY_ALREADY_SENT",
    "NO_SUBMISSION_ROUTE",
    "PARTNER_OR_TOPIC_GATE",
}

NEAR_DEADLINE_LANE_ALIASES = {
    "75D301-26-RFI-73483": "cdc_ai_acquisition_rfi",
    "DLA26BZ03-NV011": "dla_missionweave_sbir",
    "LAUNCHTN-3686-2026": "launchtn_3686_pitch_2026",
    "W912HZ26SC005": "erdc_sovereign_cloud_cso",
}

PUBLIC_LEAD_LANE_ALIASES = {
    "launchtn-3686-pitch-2026": "launchtn_3686_pitch_2026",
    "microsoft-for-startups-no-referral-2026": (
        "microsoft_for_startups_no_referral_2026"
    ),
    "aws-activate-founders-2026": "aws_activate_founders_2026",
    "nvidia-inception-2026": "nvidia_inception_2026",
}

EXPLICIT_CURRENT_LANES = {
    "darpa_falcon_dpa26bz04_dv016",
}

SENSITIVE_MARKERS = (
    "password",
    "one-time password",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "meeting id",
)
SENSITIVE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", re.IGNORECASE),
)


class ConformanceError(ValueError):
    """Raised when a submission conformance registry is unsafe or ambiguous."""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConformanceError(f"expected an object at {path}")
    return payload


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def resolve_repo_path(path_text: str) -> Path:
    if not isinstance(path_text, str) or not path_text.strip():
        raise ConformanceError("artifact path must be a non-empty repository path")
    path = (ROOT / path_text).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ConformanceError(f"artifact path escapes repository: {path_text}") from exc
    return path


def artifact_receipt(path_text: str | None) -> dict[str, Any] | None:
    if path_text is None:
        return None
    path = resolve_repo_path(path_text)
    return {
        "path": path_text,
        "present": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else 0,
        "sha256": sha256_file(path) if path.is_file() else "",
    }


def validate_registry(registry: dict[str, Any]) -> None:
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise ConformanceError(f"schema must be {REGISTRY_SCHEMA}")
    if set(registry.get("required_criteria", [])) != set(REQUIRED_CRITERIA):
        raise ConformanceError("required_criteria must contain the complete v1 criterion set")
    controls = registry.get("controls")
    if not isinstance(controls, dict):
        raise ConformanceError("controls must be an object")
    required_controls = {
        "artifact_presence_is_not_argument_readiness": True,
        "criterion_phrase_presence_is_not_evidence": True,
        "independent_red_team_receipt_required": True,
        "missing_criterion_fails_closed": True,
        "proxy_evidence_requires_applicability_boundary": True,
        "separate_human_action_time_approval_required": True,
    }
    for key, expected in required_controls.items():
        if controls.get(key) is not expected:
            raise ConformanceError(f"unsafe control value for {key}")

    lanes = registry.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise ConformanceError("lanes must be a non-empty array")
    lane_ids: list[str] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ConformanceError("every lane must be an object")
        lane_id = lane.get("lane_id")
        if not isinstance(lane_id, str) or not lane_id.strip():
            raise ConformanceError("every lane requires lane_id")
        lane_ids.append(lane_id)
        if lane.get("disposition") not in DISPOSITIONS:
            raise ConformanceError(f"invalid disposition for {lane_id}")
        if not isinstance(lane.get("technical_argument_required"), bool):
            raise ConformanceError(f"{lane_id} requires technical_argument_required")
        if not isinstance(lane.get("submission_candidate_active"), bool):
            raise ConformanceError(f"{lane_id} requires submission_candidate_active")
        if lane["submission_candidate_active"] and not lane["technical_argument_required"]:
            raise ConformanceError(f"{lane_id} cannot be active without an argument gate")
        for field in ("current_state", "next_action", "claim_boundary"):
            if not str(lane.get(field, "")).strip():
                raise ConformanceError(f"{lane_id} requires {field}")

        candidate = lane.get("candidate_artifact")
        if candidate is not None:
            resolve_repo_path(candidate)
        official_source = lane.get("official_source")
        if official_source is not None:
            resolve_repo_path(official_source)
        postmortem = lane.get("postmortem")
        if postmortem is not None:
            resolve_repo_path(postmortem)

        criteria = lane.get("criteria", [])
        if not isinstance(criteria, list):
            raise ConformanceError(f"{lane_id} criteria must be an array")
        criterion_ids: list[str] = []
        for criterion in criteria:
            if not isinstance(criterion, dict):
                raise ConformanceError(f"{lane_id} has a non-object criterion")
            criterion_id = criterion.get("criterion_id")
            if criterion_id not in REQUIRED_CRITERIA:
                raise ConformanceError(f"{lane_id} has unknown criterion {criterion_id}")
            criterion_ids.append(criterion_id)
            if criterion.get("state") not in CRITERION_STATES:
                raise ConformanceError(f"{lane_id}/{criterion_id} has invalid state")
            if not str(criterion.get("finding", "")).strip():
                raise ConformanceError(f"{lane_id}/{criterion_id} requires a finding")
            missing = criterion.get("missing_evidence")
            if not isinstance(missing, list):
                raise ConformanceError(f"{lane_id}/{criterion_id} missing_evidence must be an array")
            if criterion["state"] != "PASS" and not missing:
                raise ConformanceError(
                    f"{lane_id}/{criterion_id} must name missing evidence when not PASS"
                )
            refs = criterion.get("source_refs")
            if not isinstance(refs, list):
                raise ConformanceError(f"{lane_id}/{criterion_id} source_refs must be an array")
            if criterion["state"] == "PASS" and not refs:
                raise ConformanceError(
                    f"{lane_id}/{criterion_id} cannot PASS without source references"
                )
            for source_ref in refs:
                if not isinstance(source_ref, dict):
                    raise ConformanceError(f"{lane_id}/{criterion_id} has invalid source reference")
                resolve_repo_path(str(source_ref.get("path", "")))
                if not str(source_ref.get("anchor", "")).strip():
                    raise ConformanceError(
                        f"{lane_id}/{criterion_id} source reference requires an anchor"
                    )
        if len(criterion_ids) != len(set(criterion_ids)):
            raise ConformanceError(f"{lane_id} contains duplicate criteria")

        red_team = lane.get("independent_red_team_receipt")
        if red_team is not None:
            if not isinstance(red_team, dict):
                raise ConformanceError(f"{lane_id} red-team receipt must be an object")
            resolve_repo_path(str(red_team.get("path", "")))
            if red_team.get("reviewer_relation") in {
                "",
                None,
                "PRIMARY_DRAFTER_SELF_ATTESTED",
            }:
                raise ConformanceError(
                    f"{lane_id} red-team receipt must identify a separate reviewer relation"
                )
    if len(lane_ids) != len(set(lane_ids)):
        raise ConformanceError("lane ids must be unique")


def current_federal_and_ip_lanes(traction: dict[str, Any]) -> set[str]:
    lanes = traction.get("lanes", [])
    if not isinstance(lanes, list):
        return set()
    return {
        str(lane.get("lane_id"))
        for lane in lanes
        if isinstance(lane, dict)
        and lane.get("lane_id")
        and str(lane.get("channel", "")) in FEDERAL_AND_IP_CHANNELS
    }


def current_near_deadline_lanes(near_deadline: dict[str, Any]) -> set[str]:
    lanes = near_deadline.get("lanes", [])
    if not isinstance(lanes, list):
        return set()
    output: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        opportunity_number = str(lane.get("opportunity_number") or "").strip()
        canonical = NEAR_DEADLINE_LANE_ALIASES.get(opportunity_number)
        if canonical:
            output.add(canonical)
    return output


def current_public_lead_lanes(public_leads: dict[str, Any]) -> set[str]:
    records = public_leads.get("records", [])
    if not isinstance(records, list):
        return set()
    output: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        record_id = str(record.get("record_id") or "").strip()
        if not record_id:
            continue
        output.add(
            PUBLIC_LEAD_LANE_ALIASES.get(
                record_id,
                re.sub(r"[^a-z0-9]+", "_", record_id.lower()).strip("_"),
            )
        )
    return output


def current_lane_universe(
    traction: dict[str, Any],
    near_deadline: dict[str, Any],
    public_leads: dict[str, Any],
) -> tuple[set[str], dict[str, list[str]]]:
    source_ids = {
        "traction_federal_and_ip": sorted(current_federal_and_ip_lanes(traction)),
        "near_deadline_selected": sorted(current_near_deadline_lanes(near_deadline)),
        "current_public_leads": sorted(current_public_lead_lanes(public_leads)),
        "explicit_current_lanes": sorted(EXPLICIT_CURRENT_LANES),
    }
    current_ids: set[str] = set()
    for lane_ids in source_ids.values():
        current_ids.update(lane_ids)
    return current_ids, source_ids


def source_ref_receipts(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    receipts = []
    for source_ref in refs:
        receipt = artifact_receipt(str(source_ref["path"]))
        assert receipt is not None
        receipts.append({**receipt, "anchor": str(source_ref["anchor"])})
    return receipts


def criterion_rows(lane: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {
        str(row["criterion_id"]): row
        for row in lane.get("criteria", [])
        if isinstance(row, dict)
    }
    rows = []
    for criterion_id in REQUIRED_CRITERIA:
        source = by_id.get(criterion_id)
        if source is None:
            rows.append(
                {
                    "criterion_id": criterion_id,
                    "state": "UNASSESSED",
                    "finding": "No source-bound assessment is registered.",
                    "missing_evidence": [
                        f"Source-bound assessment for {criterion_id.replace('_', ' ')}"
                    ],
                    "source_refs": [],
                    "source_refs_all_present": False,
                    "passed": False,
                }
            )
            continue
        refs = source_ref_receipts(source.get("source_refs", []))
        refs_present = bool(refs) and all(ref["present"] for ref in refs)
        passed = source["state"] == "PASS" and refs_present
        rows.append(
            {
                "criterion_id": criterion_id,
                "state": source["state"],
                "finding": source["finding"],
                "missing_evidence": list(source["missing_evidence"]),
                "source_refs": refs,
                "source_refs_all_present": refs_present,
                "passed": passed,
            }
        )
    return rows


def red_team_receipt(lane: dict[str, Any]) -> dict[str, Any]:
    source = lane.get("independent_red_team_receipt")
    if source is None:
        return {
            "present": False,
            "path": None,
            "sha256": "",
            "reviewer_relation": None,
            "verdict": None,
            "passes": False,
        }
    artifact = artifact_receipt(str(source["path"]))
    assert artifact is not None
    verdict = str(source.get("verdict", ""))
    reviewer_relation = str(source.get("reviewer_relation", ""))
    passes = (
        artifact["present"]
        and verdict == "PASS"
        and reviewer_relation != "PRIMARY_DRAFTER_SELF_ATTESTED"
    )
    return {
        **artifact,
        "reviewer_relation": reviewer_relation,
        "verdict": verdict,
        "passes": passes,
    }


def lane_gate(lane: dict[str, Any]) -> dict[str, Any]:
    criteria = criterion_rows(lane)
    red_team = red_team_receipt(lane)
    candidate = artifact_receipt(lane.get("candidate_artifact"))
    official_source = artifact_receipt(lane.get("official_source"))
    postmortem = artifact_receipt(lane.get("postmortem"))

    argument_required = bool(lane["technical_argument_required"])
    active = bool(lane["submission_candidate_active"])
    pass_count = sum(1 for row in criteria if row["passed"])
    fail_count = sum(1 for row in criteria if row["state"] == "FAIL")
    partial_count = sum(1 for row in criteria if row["state"] == "PARTIAL")
    unassessed_count = sum(1 for row in criteria if row["state"] == "UNASSESSED")
    all_criteria_pass = pass_count == len(REQUIRED_CRITERIA)
    argument_ready = (
        argument_required
        and active
        and all_criteria_pass
        and red_team["passes"]
        and candidate is not None
        and candidate["present"]
        and official_source is not None
        and official_source["present"]
    )

    disposition = str(lane["disposition"])
    if disposition == "CLOSED_OFFICIAL_DECISION":
        status = "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    elif disposition == "EXPIRED_NO_VERIFIED_SUBMISSION":
        status = "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED"
    elif disposition == "BLOCKED_TECHNICAL_NO_GO":
        status = "TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY"
    elif disposition == "MONITOR_ONLY_ALREADY_SENT":
        status = "MONITOR_ONLY_NO_DUPLICATE_SUBMISSION"
    elif disposition == "NO_SUBMISSION_ROUTE":
        status = "NO_SUBMISSION_ARGUMENT_GATE_APPLICABLE"
    elif not argument_required:
        status = "NON_SUBMISSION_ROUTE"
    elif not active:
        status = "BLOCKED_BEFORE_SUBMISSION_CANDIDATE"
    elif unassessed_count:
        status = "BLOCKED_UNASSESSED_CRITERIA"
    elif not all_criteria_pass:
        status = "BLOCKED_CRITERION_FAILURE"
    elif not red_team["passes"]:
        status = "BLOCKED_INDEPENDENT_RED_TEAM_RECEIPT"
    elif not argument_ready:
        status = "BLOCKED_SOURCE_OR_CANDIDATE_ARTIFACT"
    else:
        status = "ARGUMENT_CONFORMANCE_PASS_HUMAN_ACTION_STILL_REQUIRED"

    row = {
        "lane_id": lane["lane_id"],
        "name": lane["name"],
        "disposition": disposition,
        "current_state": lane["current_state"],
        "technical_argument_required": argument_required,
        "submission_candidate_active": active,
        "status": status,
        "argument_conformance_pass": argument_ready,
        "candidate_artifact": candidate,
        "official_source": official_source,
        "postmortem": postmortem,
        "criterion_count": len(criteria),
        "criterion_pass_count": pass_count,
        "criterion_partial_count": partial_count,
        "criterion_fail_count": fail_count,
        "criterion_unassessed_count": unassessed_count,
        "criteria": criteria,
        "independent_red_team_receipt": red_team,
        "next_action": lane["next_action"],
        "claim_boundary": lane["claim_boundary"],
        "final_submission_allowed_without_human": False,
        "external_send_allowed_without_human": False,
    }
    row["lane_gate_sha256"] = canonical_sha256(row)
    return row


def build_gate(
    registry: dict[str, Any] | None = None,
    traction: dict[str, Any] | None = None,
    near_deadline: dict[str, Any] | None = None,
    public_leads: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry or read_json(REGISTRY_PATH)
    traction = traction or read_json(TRACTION_PATH)
    near_deadline = near_deadline or read_json(NEAR_DEADLINE_PATH)
    public_leads = public_leads or read_json(PUBLIC_LEADS_PATH)
    validate_registry(registry)

    rows = [lane_gate(lane) for lane in registry["lanes"]]
    registry_ids = {row["lane_id"] for row in rows}
    current_ids, current_lane_sources = current_lane_universe(
        traction,
        near_deadline,
        public_leads,
    )
    missing_lane_ids = sorted(current_ids - registry_ids)
    extra_lane_ids = sorted(registry_ids - current_ids)
    status_counts = Counter(row["status"] for row in rows)
    active_rows = [row for row in rows if row["submission_candidate_active"]]
    active_pass_count = sum(1 for row in active_rows if row["argument_conformance_pass"])
    closed_count = sum(
        1 for row in rows if row["disposition"] == "CLOSED_OFFICIAL_DECISION"
    )
    expired_count = sum(
        1
        for row in rows
        if row["disposition"] == "EXPIRED_NO_VERIFIED_SUBMISSION"
    )
    no_go_count = sum(
        1 for row in rows if row["disposition"] == "BLOCKED_TECHNICAL_NO_GO"
    )
    all_covered = not missing_lane_ids
    no_unreviewed_active = all(
        row["argument_conformance_pass"] for row in active_rows
    )

    payload = {
        "schema": OUTPUT_SCHEMA,
        "as_of_utc": now_utc(),
        "registry_as_of_utc": registry["as_of_utc"],
        "status": (
            "SUBMISSION_CONFORMANCE_PASS_HUMAN_ACTION_REQUIRED"
            if all_covered and active_rows and no_unreviewed_active
            else "SUBMISSION_CONFORMANCE_BLOCKED"
        ),
        "purpose": (
            "Require a source-bound objective, novelty, baseline, metric, experiment, "
            "evidence-applicability, execution, and independent-red-team trace before "
            "any technical submission can be called reviewer-ready."
        ),
        "summary": {
            "registry_lane_count": len(rows),
            "current_lane_universe_count": len(current_ids),
            "current_federal_and_ip_lane_count": len(
                current_lane_sources["traction_federal_and_ip"]
            ),
            "missing_current_lane_count": len(missing_lane_ids),
            "extra_registry_lane_count": len(extra_lane_ids),
            "active_submission_candidate_count": len(active_rows),
            "active_argument_pass_count": active_pass_count,
            "active_argument_blocked_count": len(active_rows) - active_pass_count,
            "closed_official_decision_count": closed_count,
            "expired_without_verified_submission_count": expired_count,
            "technical_no_go_count": no_go_count,
            "status_counts": dict(sorted(status_counts.items())),
            "all_current_lanes_covered": all_covered,
            "final_submission_allowed_without_human": False,
            "external_send_allowed_without_human": False,
        },
        "missing_current_lane_ids": missing_lane_ids,
        "extra_registry_lane_ids": extra_lane_ids,
        "current_lane_sources": current_lane_sources,
        "required_criteria": list(REQUIRED_CRITERIA),
        "controls": registry["controls"],
        "lanes": rows,
        "source_evidence": {
            "registry": artifact_receipt(repo_path(REGISTRY_PATH)),
            "traction": artifact_receipt(repo_path(TRACTION_PATH)),
            "near_deadline": artifact_receipt(repo_path(NEAR_DEADLINE_PATH)),
            "public_leads": artifact_receipt(repo_path(PUBLIC_LEADS_PATH)),
            "falcon_gap_map": artifact_receipt(repo_path(FALCON_GAP_MAP_PATH)),
            "builder": artifact_receipt(repo_path(Path(__file__))),
        },
        "global_stop_rule": (
            "No technical submission is reviewer-ready unless every required criterion "
            "passes against cited source artifacts and a separate red-team receipt also "
            "passes. File presence, hashes, formatting, and self-authored reviewer notes "
            "cannot substitute for this argument gate. Human action-time approval remains "
            "mandatory after a technical pass."
        ),
    }
    payload["gate_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Submission Conformance Gate",
        "",
        f"As of UTC: `{payload['as_of_utc']}`",
        "",
        payload["purpose"],
        "",
        payload["global_stop_rule"],
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Current lane universe: `{summary['current_lane_universe_count']}`",
        f"- Current traction federal/IP lanes: `{summary['current_federal_and_ip_lane_count']}`",
        f"- Registry lanes: `{summary['registry_lane_count']}`",
        f"- Missing current lanes: `{summary['missing_current_lane_count']}`",
        f"- Active submission candidates: `{summary['active_submission_candidate_count']}`",
        f"- Active argument passes: `{summary['active_argument_pass_count']}`",
        f"- Active argument blocks: `{summary['active_argument_blocked_count']}`",
        f"- Closed official decisions: `{summary['closed_official_decision_count']}`",
        f"- Expired without verified submission: `{summary['expired_without_verified_submission_count']}`",
        f"- Technical no-go lanes: `{summary['technical_no_go_count']}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Gate SHA-256: `{payload['gate_sha256']}`",
        "",
    ]
    if payload["missing_current_lane_ids"]:
        lines.extend(["## Missing Current Lanes", ""])
        lines.extend(f"- `{lane_id}`" for lane_id in payload["missing_current_lane_ids"])
        lines.append("")

    lines.extend(["## Lane Gates", ""])
    for lane in payload["lanes"]:
        lines.extend(
            [
                f"### {lane['lane_id']}",
                "",
                f"- Name: {lane['name']}",
                f"- Disposition: `{lane['disposition']}`",
                f"- Status: `{lane['status']}`",
                f"- Active candidate: `{str(lane['submission_candidate_active']).lower()}`",
                f"- Argument required: `{str(lane['technical_argument_required']).lower()}`",
                f"- Argument pass: `{str(lane['argument_conformance_pass']).lower()}`",
                f"- Criteria: pass `{lane['criterion_pass_count']}`, partial `{lane['criterion_partial_count']}`, fail `{lane['criterion_fail_count']}`, unassessed `{lane['criterion_unassessed_count']}`",
                f"- Separate red-team receipt pass: `{str(lane['independent_red_team_receipt']['passes']).lower()}`",
                f"- Next action: {lane['next_action']}",
                f"- Boundary: {lane['claim_boundary']}",
                "",
            ]
        )
        if lane["technical_argument_required"]:
            lines.append("Criteria:")
            for criterion in lane["criteria"]:
                lines.append(
                    f"- `{criterion['criterion_id']}` state=`{criterion['state']}` "
                    f"passed=`{str(criterion['passed']).lower()}` - {criterion['finding']}"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    hits = {marker for marker in SENSITIVE_MARKERS if marker in lowered}
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            hits.add(pattern.pattern)
    return sorted(hits)


def write_outputs(payload: dict[str, Any]) -> None:
    markdown = render_markdown(payload)
    findings = scan_sensitive_text(canonical_json(payload) + "\n" + markdown)
    if findings:
        raise ConformanceError(f"sensitive markers found in output: {findings}")
    for path in (OUT_JSON, DASHBOARD_JSON):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_gate()
    if not args.check:
        write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "active_submission_candidate_count": payload["summary"][
                    "active_submission_candidate_count"
                ],
                "active_argument_pass_count": payload["summary"][
                    "active_argument_pass_count"
                ],
                "missing_current_lane_count": payload["summary"][
                    "missing_current_lane_count"
                ],
                "gate_sha256": payload["gate_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
