from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


EXPECTED_SCHEMA = "lumencore.submission_conformance_gate.v1"
DEFAULT_MAX_AGE_HOURS = 24.0
FUTURE_CLOCK_SKEW = timedelta(minutes=5)
REQUIRED_SOURCE_EVIDENCE = (
    "registry",
    "traction",
    "near_deadline",
    "public_leads",
    "falcon_gap_map",
    "builder",
)

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

REQUIRED_CONTROLS = {
    "artifact_presence_is_not_argument_readiness": True,
    "criterion_phrase_presence_is_not_evidence": True,
    "independent_red_team_receipt_required": True,
    "missing_criterion_fails_closed": True,
    "proxy_evidence_requires_applicability_boundary": True,
    "separate_human_action_time_approval_required": True,
}

PASS_STATUS = "ARGUMENT_CONFORMANCE_PASS_HUMAN_ACTION_STILL_REQUIRED"
SELF_ATTESTED_RELATIONS = {
    "",
    "PRIMARY_DRAFTER_SELF_ATTESTED",
}


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_identifier(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def parse_utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _within_repo(repo_root: Path, path_text: Any) -> Path | None:
    if not isinstance(path_text, str) or not path_text.strip():
        return None
    root = repo_root.resolve()
    path = (root / path_text).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    return path


def _receipt_blockers(
    receipt: Any,
    *,
    label: str,
    repo_root: Path,
) -> list[str]:
    if not isinstance(receipt, dict):
        return [f"{label} receipt is missing or malformed"]
    if receipt.get("present") is not True:
        return [f"{label} receipt does not record a present artifact"]

    path = _within_repo(repo_root, receipt.get("path"))
    if path is None:
        return [f"{label} receipt path is missing or escapes the repository"]
    if not path.is_file():
        return [f"{label} artifact is no longer present: {receipt.get('path')}"]

    expected_sha = str(receipt.get("sha256") or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        return [f"{label} receipt has no valid SHA-256"]
    if sha256_file(path) != expected_sha:
        return [f"{label} artifact changed after the conformance gate was built"]
    return []


def _self_hash_blocker(payload: dict[str, Any], hash_field: str, label: str) -> str | None:
    expected = str(payload.get(hash_field) or "").strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        return f"{label} has no valid {hash_field}"
    material = dict(payload)
    material.pop(hash_field, None)
    if canonical_sha256(material) != expected:
        return f"{label} self-hash verification failed"
    return None


def _dedupe_nonempty(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def _map_lane(
    lanes: list[dict[str, Any]],
    *,
    identifiers: Iterable[Any],
    explicit_lane_ids: Iterable[Any],
) -> tuple[dict[str, Any] | None, str, list[str]]:
    explicit = _dedupe_nonempty(explicit_lane_ids)
    lane_by_id = {
        str(lane.get("lane_id") or ""): lane
        for lane in lanes
        if str(lane.get("lane_id") or "").strip()
    }
    if len(explicit) > 1:
        return None, "conflicting_explicit_lane_ids", [
            f"conflicting submission conformance lane IDs: {explicit}"
        ]
    if explicit:
        lane = lane_by_id.get(explicit[0])
        if lane is None:
            return None, "explicit_lane_id_unmapped", [
                f"submission conformance lane is unmapped: {explicit[0]}"
            ]
        return lane, "explicit_lane_id", []

    normalized_identifiers = {
        normalize_identifier(value)
        for value in identifiers
        if normalize_identifier(value)
    }
    matches = [
        lane
        for lane in lanes
        if normalize_identifier(lane.get("lane_id")) in normalized_identifiers
    ]
    if len(matches) == 1:
        return matches[0], "exact_normalized_identifier", []
    if len(matches) > 1:
        return None, "ambiguous_identifier_match", [
            "submission identifiers map to more than one conformance lane"
        ]
    return None, "unmapped", [
        "technical submission has no explicit lane-specific conformance mapping"
    ]


def assess_submission_conformance(
    *,
    gate_path: Path,
    repo_root: Path,
    identifiers: Iterable[Any],
    explicit_lane_ids: Iterable[Any],
    now_utc: datetime | None = None,
    max_age_hours: float = DEFAULT_MAX_AGE_HOURS,
) -> dict[str, Any]:
    blockers: list[str] = []
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    base = {
        "required": True,
        "gate_path": gate_path.as_posix(),
        "gate_schema": None,
        "gate_status": None,
        "gate_as_of_utc": None,
        "gate_age_hours": None,
        "registry_as_of_utc": None,
        "registry_age_hours": None,
        "fresh": False,
        "mapping_source": "unavailable",
        "lane_id": None,
        "lane_status": None,
        "submission_candidate_active": False,
        "all_required_criteria_pass": False,
        "independent_red_team_pass": False,
        "argument_conformance_pass": False,
        "content_unlock": False,
        "action_approval_still_required": True,
        "external_action_allowed_without_human": False,
        "blockers": blockers,
        "status": "CONTENT_BLOCKED_CONFORMANCE_UNAVAILABLE",
    }

    if not gate_path.is_file():
        blockers.append(f"submission conformance gate is absent: {gate_path.as_posix()}")
        return base
    try:
        payload = json.loads(gate_path.read_text(encoding="utf-8"))
    except Exception:
        blockers.append("submission conformance gate is unreadable or invalid JSON")
        return base
    if not isinstance(payload, dict):
        blockers.append("submission conformance gate root must be an object")
        return base

    base["gate_schema"] = payload.get("schema")
    base["gate_status"] = payload.get("status")
    base["gate_as_of_utc"] = payload.get("as_of_utc")
    base["registry_as_of_utc"] = payload.get("registry_as_of_utc")

    if payload.get("schema") != EXPECTED_SCHEMA:
        blockers.append(f"submission conformance schema must be {EXPECTED_SCHEMA}")

    gate_hash_error = _self_hash_blocker(payload, "gate_sha256", "submission conformance gate")
    if gate_hash_error:
        blockers.append(gate_hash_error)

    as_of = parse_utc(payload.get("as_of_utc"))
    if as_of is None:
        blockers.append("submission conformance gate has no parseable as_of_utc")
    else:
        age_hours = (now - as_of).total_seconds() / 3600.0
        base["gate_age_hours"] = round(age_hours, 6)
        if as_of > now + FUTURE_CLOCK_SKEW:
            blockers.append("submission conformance gate is dated in the future")
        elif age_hours > max_age_hours:
            blockers.append(
                f"submission conformance gate is stale ({age_hours:.2f}h > {max_age_hours:.2f}h)"
            )
        else:
            base["fresh"] = True

    registry_as_of = parse_utc(payload.get("registry_as_of_utc"))
    if registry_as_of is None:
        blockers.append("submission conformance gate has no parseable registry_as_of_utc")
    else:
        registry_age_hours = (now - registry_as_of).total_seconds() / 3600.0
        base["registry_age_hours"] = round(registry_age_hours, 6)
        if registry_as_of > now + FUTURE_CLOCK_SKEW:
            blockers.append("submission conformance registry is dated in the future")
        elif registry_age_hours > max_age_hours:
            blockers.append(
                "submission conformance registry is stale "
                f"({registry_age_hours:.2f}h > {max_age_hours:.2f}h)"
            )

    required = payload.get("required_criteria")
    if (
        not isinstance(required, list)
        or len(required) != len(REQUIRED_CRITERIA)
        or set(required) != set(REQUIRED_CRITERIA)
    ):
        blockers.append("submission conformance gate does not declare the complete criterion set")

    controls = payload.get("controls")
    if not isinstance(controls, dict):
        blockers.append("submission conformance controls are missing")
    else:
        for key, expected in REQUIRED_CONTROLS.items():
            if controls.get(key) is not expected:
                blockers.append(f"submission conformance control is unsafe: {key}")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        blockers.append("submission conformance summary is missing")
    else:
        if summary.get("final_submission_allowed_without_human") is not False:
            blockers.append(
                "submission conformance gate does not preserve the human action wall"
            )
        if summary.get("all_current_lanes_covered") is not True:
            blockers.append(
                "submission conformance gate does not cover every current lane"
            )

    source_evidence = payload.get("source_evidence")
    if not isinstance(source_evidence, dict):
        blockers.append("submission conformance source evidence is missing")
    else:
        for key in REQUIRED_SOURCE_EVIDENCE:
            blockers.extend(
                _receipt_blockers(
                    source_evidence.get(key),
                    label=f"conformance {key}",
                    repo_root=repo_root,
                )
            )

    raw_lanes = payload.get("lanes")
    if not isinstance(raw_lanes, list):
        blockers.append("submission conformance lanes are missing")
        raw_lanes = []
    lanes = [lane for lane in raw_lanes if isinstance(lane, dict)]
    lane, mapping_source, mapping_blockers = _map_lane(
        lanes,
        identifiers=identifiers,
        explicit_lane_ids=explicit_lane_ids,
    )
    base["mapping_source"] = mapping_source
    blockers.extend(mapping_blockers)
    if lane is None:
        base["status"] = "CONTENT_BLOCKED_CONFORMANCE_UNMAPPED"
        return base

    lane_id = str(lane.get("lane_id") or "")
    base["lane_id"] = lane_id
    base["lane_status"] = lane.get("status")
    base["submission_candidate_active"] = lane.get("submission_candidate_active") is True

    lane_hash_error = _self_hash_blocker(lane, "lane_gate_sha256", f"conformance lane {lane_id}")
    if lane_hash_error:
        blockers.append(lane_hash_error)
    if lane.get("technical_argument_required") is not True:
        blockers.append(f"conformance lane {lane_id} is not marked as a technical argument lane")
    if lane.get("submission_candidate_active") is not True:
        blockers.append(f"conformance lane {lane_id} is not an active submission candidate")
    if lane.get("status") != PASS_STATUS:
        blockers.append(f"conformance lane {lane_id} is blocked: {lane.get('status')}")
    if lane.get("argument_conformance_pass") is not True:
        blockers.append(f"conformance lane {lane_id} has no argument_conformance_pass")

    criteria = lane.get("criteria")
    criteria_by_id = {}
    if isinstance(criteria, list):
        criteria_by_id = {
            str(row.get("criterion_id") or ""): row
            for row in criteria
            if isinstance(row, dict)
        }
    if set(criteria_by_id) != set(REQUIRED_CRITERIA) or len(criteria_by_id) != len(
        REQUIRED_CRITERIA
    ):
        blockers.append(f"conformance lane {lane_id} does not contain exactly all required criteria")
    criteria_pass = True
    for criterion_id in REQUIRED_CRITERIA:
        row = criteria_by_id.get(criterion_id)
        if not isinstance(row, dict):
            criteria_pass = False
            continue
        if (
            row.get("state") != "PASS"
            or row.get("passed") is not True
            or row.get("source_refs_all_present") is not True
        ):
            blockers.append(f"conformance criterion is not a source-bound PASS: {criterion_id}")
            criteria_pass = False
            continue
        refs = row.get("source_refs")
        if not isinstance(refs, list) or not refs:
            blockers.append(f"conformance criterion has no source receipts: {criterion_id}")
            criteria_pass = False
            continue
        for index, receipt in enumerate(refs):
            if not isinstance(receipt, dict) or not str(receipt.get("anchor") or "").strip():
                blockers.append(
                    f"conformance criterion source has no anchor: {criterion_id}[{index}]"
                )
                criteria_pass = False
                continue
            receipt_errors = _receipt_blockers(
                receipt,
                label=f"criterion {criterion_id} source {index}",
                repo_root=repo_root,
            )
            if receipt_errors:
                criteria_pass = False
                blockers.extend(receipt_errors)
    base["all_required_criteria_pass"] = criteria_pass

    red_team = lane.get("independent_red_team_receipt")
    red_team_pass = isinstance(red_team, dict)
    if not isinstance(red_team, dict):
        blockers.append(f"conformance lane {lane_id} has no independent red-team receipt")
    else:
        if red_team.get("passes") is not True or red_team.get("verdict") != "PASS":
            blockers.append(f"conformance lane {lane_id} red-team verdict is not PASS")
            red_team_pass = False
        reviewer_relation = str(red_team.get("reviewer_relation") or "").strip()
        if reviewer_relation in SELF_ATTESTED_RELATIONS:
            blockers.append(f"conformance lane {lane_id} red-team review is not independent")
            red_team_pass = False
        receipt_errors = _receipt_blockers(
            red_team,
            label=f"conformance lane {lane_id} red-team",
            repo_root=repo_root,
        )
        if receipt_errors:
            red_team_pass = False
            blockers.extend(receipt_errors)
    base["independent_red_team_pass"] = red_team_pass

    for field, label in (
        ("candidate_artifact", "candidate artifact"),
        ("official_source", "official source"),
    ):
        blockers.extend(
            _receipt_blockers(
                lane.get(field),
                label=f"conformance lane {lane_id} {label}",
                repo_root=repo_root,
            )
        )

    if lane.get("final_submission_allowed_without_human") is not False:
        blockers.append(f"conformance lane {lane_id} does not preserve final human approval")
    if lane.get("external_send_allowed_without_human") is not False:
        blockers.append(f"conformance lane {lane_id} does not preserve external-send approval")

    content_unlock = not blockers
    base["argument_conformance_pass"] = content_unlock
    base["content_unlock"] = content_unlock
    base["status"] = (
        "CONTENT_UNLOCKED_ACTION_APPROVAL_STILL_REQUIRED"
        if content_unlock
        else "CONTENT_BLOCKED_CONFORMANCE_FAILED"
    )
    return base
