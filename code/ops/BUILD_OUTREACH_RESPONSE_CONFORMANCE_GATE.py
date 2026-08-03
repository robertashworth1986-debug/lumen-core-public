"""Build a fail-closed conformance gate for outbound response templates.

The gate cross-checks the canonical outreach queue, reconciliation, template
registry, Monday decision packet, reviewer objection gate, and submission
conformance gate. It cannot read Gmail, render private drafts, or send email.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "outreach_response_conformance_v1.json"
OUTPUT_JSON = ROOT / "out" / "ops" / "outreach_response_conformance_gate_latest.json"
OUTPUT_MD = ROOT / "docs" / "OUTREACH_RESPONSE_CONFORMANCE_GATE_2026-07-26.md"

CONFIG_SCHEMA = "lumencore.outreach_response_conformance_config.v1"
OUTPUT_SCHEMA = "lumencore.outreach_response_conformance_gate.v1"
EXPECTED_CONTROLS = {
    "action_time_human_approval_required": True,
    "autonomous_email_send_allowed": False,
    "current_source_hashes_required": True,
    "duplicate_suppression_required": True,
    "exact_deadline_timezone_required": True,
    "federal_reviewer_gate_required": True,
    "full_thread_recheck_before_followup_draft": True,
    "private_identifiers_omitted": True,
    "submission_conformance_required": True,
    "template_quality_pass_required": True,
}
EXPECTED_MATERIALS = {
    "email_reconciliation",
    "followup_policy",
    "followup_queue",
    "monday_packet",
    "response_template_registry",
    "reviewer_objection_gate",
    "submission_conformance_gate",
}
QUEUE_REQUIRED_CONTROLS = {
    "action_time_human_review_required": True,
    "builder_can_send_email": False,
    "conflicting_gmail_drafts_fail_closed": True,
    "exact_dispatch_binding_required_before_send": True,
    "final_send_performed": False,
    "inbox_recheck_required_before_draft": True,
    "mailbox_recheck_receipt_required": True,
    "past_hold_authorizes_send": False,
    "private_human_unlock_bearer_token_required": True,
    "single_use_action_time_approval_required": True,
}
REGISTRY_REQUIRED_CONTROLS = {
    "action_time_human_review_required": True,
    "builder_can_send_email": False,
    "duplicate_send_fail_closed": True,
    "known_deadline_requires_aware_iso_control": True,
    "missing_fact_fail_closed": True,
    "past_deadline_fail_closed": True,
    "rendered_deadline_matches_evaluated_deadline": True,
}
PRIVATE_KEYS = {
    "access_token",
    "account_number",
    "api_key",
    "body",
    "card_number",
    "client_secret",
    "meeting_credentials",
    "message_id",
    "otp",
    "password",
    "private_key",
    "recipient_email",
    "refresh_token",
    "subject",
    "thread_id",
}


class ConformanceError(ValueError):
    """Raised when the conformance configuration is unsafe or malformed."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConformanceError(f"Unreadable JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ConformanceError(f"Expected an object: {path}")
    return payload


def canonical_sha256(payload: Any, *, uppercase: bool = True) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    return digest.upper() if uppercase else digest


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def normalize_utc(value: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ConformanceError("as_of_utc must be canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ConformanceError("as_of_utc is invalid") from exc
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_repo_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ConformanceError("material path must be a nonempty string")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ConformanceError(f"material path escapes repository: {relative}") from exc
    return resolved


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != CONFIG_SCHEMA or config.get("version") != 1:
        raise ConformanceError("Unsupported outreach conformance config")
    if config.get("controls") != EXPECTED_CONTROLS:
        raise ConformanceError("Outreach conformance controls are not fail-closed")
    materials = config.get("materials")
    if not isinstance(materials, dict) or set(materials) != EXPECTED_MATERIALS:
        raise ConformanceError("Outreach conformance materials are incomplete")
    for material_id, material in materials.items():
        if not isinstance(material, dict) or set(material) != {"path", "schema"}:
            raise ConformanceError(f"Invalid material declaration: {material_id}")
        if not all(isinstance(material.get(key), str) and material[key] for key in material):
            raise ConformanceError(f"Incomplete material declaration: {material_id}")
    if not isinstance(config.get("claim_boundary"), str) or not config["claim_boundary"]:
        raise ConformanceError("claim_boundary is required")


def _walk_private_keys(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in PRIVATE_KEYS:
                raise ConformanceError(f"Private-data key in output: {path}.{key}")
            _walk_private_keys(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_private_keys(child, path=f"{path}[{index}]")


def _receipt(root: Path, material_id: str, declaration: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    path = resolve_repo_path(root, declaration["path"])
    receipt = {
        "id": material_id,
        "path": declaration["path"],
        "expected_schema": declaration["schema"],
        "present": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else 0,
        "sha256": file_sha256(path) if path.is_file() else "",
        "schema_matches": False,
    }
    if not path.is_file():
        return receipt, None
    payload = read_json(path)
    receipt["schema_matches"] = payload.get("schema") == declaration["schema"]
    return receipt, payload


def _append_blocker(blockers: list[dict[str, str]], code: str, detail: str) -> None:
    blockers.append({"code": code, "detail": detail})


def _verify_self_hashes(
    payloads: dict[str, dict[str, Any]],
    blockers: list[dict[str, str]],
) -> None:
    queue = payloads["followup_queue"]
    expected_queue = canonical_sha256(
        {key: value for key, value in queue.items() if key != "queue_sha256"}
    )
    if queue.get("queue_sha256") != expected_queue:
        _append_blocker(blockers, "QUEUE_SELF_HASH_INVALID", "Follow-up queue seal does not match.")

    monday = payloads["monday_packet"]
    expected_monday = canonical_sha256(
        {key: value for key, value in monday.items() if key != "control_sha256"}
    )
    if monday.get("control_sha256") != expected_monday:
        _append_blocker(blockers, "MONDAY_PACKET_SELF_HASH_INVALID", "Monday packet seal does not match.")

    reviewer = payloads["reviewer_objection_gate"]
    expected_reviewer = canonical_sha256(
        {key: value for key, value in reviewer.items() if key != "gate_sha256"}
    )
    if reviewer.get("gate_sha256") != expected_reviewer:
        _append_blocker(blockers, "REVIEWER_GATE_SELF_HASH_INVALID", "Reviewer gate seal does not match.")

    submission = payloads["submission_conformance_gate"]
    expected_submission = canonical_sha256(
        {key: value for key, value in submission.items() if key != "gate_sha256"},
        uppercase=False,
    )
    if submission.get("gate_sha256") != expected_submission:
        _append_blocker(blockers, "SUBMISSION_GATE_SELF_HASH_INVALID", "Submission gate seal does not match.")


def _verify_source_evidence(
    root: Path,
    source_name: str,
    source_evidence: Any,
    blockers: list[dict[str, str]],
) -> int:
    if not isinstance(source_evidence, dict):
        _append_blocker(blockers, "SOURCE_EVIDENCE_MISSING", f"{source_name} source evidence is missing.")
        return 0
    verified = 0
    for evidence_id, evidence in sorted(source_evidence.items()):
        if not isinstance(evidence, dict):
            _append_blocker(blockers, "SOURCE_EVIDENCE_INVALID", f"{source_name}:{evidence_id} is malformed.")
            continue
        relative = evidence.get("path")
        if not isinstance(relative, str) or not relative:
            _append_blocker(blockers, "SOURCE_EVIDENCE_PATH_MISSING", f"{source_name}:{evidence_id} has no path.")
            continue
        path = resolve_repo_path(root, relative)
        expected_present = evidence.get("present", True)
        if bool(expected_present) != path.is_file():
            _append_blocker(blockers, "SOURCE_EVIDENCE_PRESENCE_DRIFT", f"{source_name}:{evidence_id} presence drifted.")
            continue
        if not path.is_file():
            verified += 1
            continue
        if evidence.get("sha256", "").upper() != file_sha256(path):
            _append_blocker(blockers, "SOURCE_EVIDENCE_HASH_DRIFT", f"{source_name}:{evidence_id} hash drifted.")
            continue
        verified += 1
    return verified


def build_gate(
    config_path: Path = CONFIG_PATH,
    *,
    root: Path = ROOT,
    as_of_utc: str,
) -> dict[str, Any]:
    config = read_json(config_path)
    validate_config(config)
    generated_at = normalize_utc(as_of_utc)

    receipts: list[dict[str, Any]] = []
    payloads: dict[str, dict[str, Any]] = {}
    blockers: list[dict[str, str]] = []
    for material_id, declaration in config["materials"].items():
        receipt, payload = _receipt(root, material_id, declaration)
        receipts.append(receipt)
        if not receipt["present"]:
            _append_blocker(blockers, "MATERIAL_MISSING", f"{material_id} is missing.")
        elif not receipt["schema_matches"]:
            _append_blocker(blockers, "MATERIAL_SCHEMA_MISMATCH", f"{material_id} schema does not match.")
        if payload is not None:
            payloads[material_id] = payload

    if set(payloads) != EXPECTED_MATERIALS:
        status = "BLOCKED_MATERIAL_OR_CONTROL_INTEGRITY"
        gate = {
            "schema": OUTPUT_SCHEMA,
            "generated_at_utc": generated_at,
            "status": status,
            "summary": {
                "material_count": len(receipts),
                "material_blocker_count": len(blockers),
                "template_count": 0,
                "structurally_valid_template_count": 0,
                "externally_releasable_template_count": 0,
                "lane_count": 0,
                "mailbox_recheck_candidate_count": 0,
                "draft_render_ready_count": 0,
                "send_ready_lane_count": 0,
                "external_action_count": 0,
            },
            "material_receipts": receipts,
            "blockers": blockers,
            "template_release_states": [],
            "lane_release_states": [],
            "controls": config["controls"],
            "claim_boundary": config["claim_boundary"],
            "capability_boundary": {
                "gmail_read_performed": False,
                "email_send_performed": False,
                "private_draft_rendered": False,
                "portal_action_performed": False,
                "submission_performed": False,
            },
        }
        _walk_private_keys(gate)
        gate["gate_sha256"] = canonical_sha256(gate)
        return gate

    _verify_self_hashes(payloads, blockers)
    queue = payloads["followup_queue"]
    reconciliation = payloads["email_reconciliation"]
    registry = payloads["response_template_registry"]
    policy = payloads["followup_policy"]
    monday = payloads["monday_packet"]
    reviewer = payloads["reviewer_objection_gate"]
    submission = payloads["submission_conformance_gate"]

    source_evidence_verified = 0
    source_evidence_verified += _verify_source_evidence(
        root, "followup_queue", queue.get("source_evidence"), blockers
    )
    source_evidence_verified += _verify_source_evidence(
        root, "email_reconciliation", reconciliation.get("source_evidence"), blockers
    )

    source_config = registry.get("source_config")
    source_config_sha = registry.get("source_config_sha256", "")
    source_config_hash_basis = registry.get("source_config_hash_basis")
    if not isinstance(source_config, str) or not source_config:
        _append_blocker(blockers, "TEMPLATE_SOURCE_CONFIG_MISSING", "Template source config is not declared.")
    else:
        source_path = resolve_repo_path(root, source_config)
        if not source_path.is_file():
            _append_blocker(blockers, "TEMPLATE_SOURCE_CONFIG_DRIFT", "Template source config hash drifted.")
        else:
            if source_config_hash_basis == "SORTED_COMPACT_JSON_UTF8":
                actual_source_config_sha = canonical_sha256(read_json(source_path))
            elif source_config_hash_basis == "FILE_BYTES_SHA256":
                actual_source_config_sha = file_sha256(source_path)
            else:
                actual_source_config_sha = None
                _append_blocker(
                    blockers,
                    "TEMPLATE_SOURCE_CONFIG_HASH_BASIS_UNSUPPORTED",
                    "Template source config hash basis is unsupported.",
                )
            if (
                actual_source_config_sha is not None
                and actual_source_config_sha != str(source_config_sha).upper()
            ):
                _append_blocker(
                    blockers,
                    "TEMPLATE_SOURCE_CONFIG_DRIFT",
                    "Template source config hash drifted.",
                )
            elif actual_source_config_sha is not None:
                source_evidence_verified += 1

    for key, expected in QUEUE_REQUIRED_CONTROLS.items():
        if queue.get("controls", {}).get(key) is not expected:
            _append_blocker(blockers, "QUEUE_CONTROL_RELAXED", f"Queue control {key} is not fail-closed.")
    for key, expected in REGISTRY_REQUIRED_CONTROLS.items():
        if registry.get("controls", {}).get(key) is not expected:
            _append_blocker(blockers, "REGISTRY_CONTROL_RELAXED", f"Registry control {key} is not fail-closed.")

    quality = registry.get("quality_gate", {})
    if quality.get("status") != "PASS" or quality.get("all_templates_pass") is not True:
        _append_blocker(blockers, "TEMPLATE_QUALITY_GATE_FAILED", "Template registry quality gate is not passing.")

    templates = registry.get("templates", [])
    template_quality = {
        row.get("template_id"): row
        for row in quality.get("template_results", [])
        if isinstance(row, dict)
    }
    template_map = {
        row.get("template_id"): row
        for row in templates
        if isinstance(row, dict) and isinstance(row.get("template_id"), str)
    }
    template_release_states = []
    for template_id, template in sorted(template_map.items()):
        profile = template_quality.get(template_id, {})
        structural_pass = profile.get("status") == "PASS"
        template_release_states.append(
            {
                "template_id": template_id,
                "send_policy": template.get("send_policy"),
                "private_render_only": template.get("private_render_only"),
                "structural_quality_pass": structural_pass,
                "release_state": (
                    "MONITOR_ONLY_CONTENT_FREE"
                    if template.get("send_policy") == "MONITOR_NO_SEND"
                    else "STRUCTURALLY_VALID_EXTERNAL_RELEASE_BLOCKED"
                ),
                "external_release_allowed": False,
            }
        )

    queue_actions = queue.get("actions", [])
    reconciliation_lanes = reconciliation.get("lanes", [])
    policy_lanes = policy.get("lane_policies", [])
    queue_lane_ids = {
        row.get("lane_id") for row in queue_actions if isinstance(row, dict)
    }
    reconciliation_lane_ids = {
        row.get("lane_id") for row in reconciliation_lanes if isinstance(row, dict)
    }
    policy_lane_ids = {
        row.get("lane_id") for row in policy_lanes if isinstance(row, dict)
    }
    if queue_lane_ids != reconciliation_lane_ids or queue_lane_ids != policy_lane_ids:
        _append_blocker(blockers, "LANE_UNIVERSE_DRIFT", "Queue, reconciliation, and policy lane sets differ.")

    lane_release_states = []
    for row in sorted(queue_actions, key=lambda item: item.get("lane_id", "")):
        lane_id = row.get("lane_id", "")
        referenced_templates = {
            value
            for value in (
                row.get("current_response_template_id"),
                row.get("eligible_template_id"),
            )
            if isinstance(value, str) and value
        }
        unknown_templates = sorted(referenced_templates - set(template_map))
        if unknown_templates:
            _append_blocker(blockers, "UNKNOWN_TEMPLATE_REFERENCE", f"{lane_id} references unknown templates.")
        if row.get("send_now") is not False:
            _append_blocker(blockers, "QUEUE_SEND_NOW_NOT_BLOCKED", f"{lane_id} is not fail-closed.")
        if row.get("draft_rendered") is not False:
            _append_blocker(blockers, "QUEUE_DRAFT_RENDERED", f"{lane_id} has an unapproved rendered draft.")
        if row.get("conflicting_gmail_draft_count", 0) > 0 and not row.get("draft_quarantine_status"):
            _append_blocker(blockers, "DRAFT_CONFLICT_NOT_QUARANTINED", f"{lane_id} draft conflict is not quarantined.")
        mailbox_candidate = row.get("action_state") == "RECHECK_MAILBOX_BEFORE_DRAFT"
        draft_ready = (
            mailbox_candidate
            and row.get("inbox_recheck_required") is False
            and not unknown_templates
            and row.get("conflicting_gmail_draft_count", 0) == 0
        )
        lane_release_states.append(
            {
                "lane_id": lane_id,
                "action_state": row.get("action_state"),
                "current_response_template_id": row.get("current_response_template_id"),
                "eligible_template_id": row.get("eligible_template_id"),
                "mailbox_recheck_candidate": mailbox_candidate,
                "draft_render_ready": draft_ready,
                "send_ready": False,
                "external_action_allowed": False,
                "next_action": row.get("next_action"),
            }
        )

    if queue.get("summary", {}).get("send_now_count") != 0:
        _append_blocker(blockers, "QUEUE_SEND_COUNT_NONZERO", "Queue summary reports a send-now lane.")
    if reconciliation.get("summary", {}).get("send_now_count") != 0:
        _append_blocker(blockers, "RECONCILIATION_SEND_COUNT_NONZERO", "Reconciliation reports a send-now lane.")
    if reconciliation.get("summary", {}).get("external_send_allowed_without_human") is not False:
        _append_blocker(blockers, "RECONCILIATION_EXTERNAL_SEND_RELAXED", "Reconciliation permits an external send.")

    monday_summary = monday.get("summary", {})
    if (
        monday_summary.get("prime_submission_ready_count") != 0
        or monday_summary.get("partner_brief_ready_count") != 0
        or monday_summary.get("external_action_count") != 0
    ):
        _append_blocker(blockers, "MONDAY_RESPONSE_NOT_BLOCKED", "Monday opportunity response state is not fail-closed.")
    if any(
        row.get("prime_submission_ready") is not False
        or row.get("partner_brief_ready") is not False
        or row.get("external_action_authorized") is not False
        for row in monday.get("opportunities", [])
        if isinstance(row, dict)
    ):
        _append_blocker(blockers, "MONDAY_LANE_FLAG_NOT_BLOCKED", "A Monday opportunity flag is not fail-closed.")

    reviewer_summary = reviewer.get("summary", {})
    for field in (
        "prime_submission_allowed",
        "external_capability_distribution_allowed",
        "partner_outreach_allowed",
    ):
        if reviewer_summary.get(field) is not False:
            _append_blocker(blockers, "REVIEWER_RELEASE_GATE_RELAXED", f"Reviewer gate field {field} is not blocked.")
    if reviewer_summary.get("external_action_count") != 0:
        _append_blocker(blockers, "REVIEWER_EXTERNAL_ACTION_NONZERO", "Reviewer gate reports an external action.")

    submission_summary = submission.get("summary", {})
    if submission.get("status") != "SUBMISSION_CONFORMANCE_BLOCKED":
        _append_blocker(blockers, "SUBMISSION_GATE_STATUS_UNEXPECTED", "Submission gate is not in its current blocked state.")
    if submission_summary.get("active_argument_pass_count") != 0:
        _append_blocker(blockers, "SUBMISSION_ARGUMENT_PASS_NONZERO", "Submission gate reports an active argument pass.")
    if submission_summary.get("external_send_allowed_without_human") is not False:
        _append_blocker(blockers, "SUBMISSION_EXTERNAL_SEND_RELAXED", "Submission gate permits an external send.")

    status = (
        "BLOCKED_MATERIAL_OR_CONTROL_INTEGRITY"
        if blockers
        else "BLOCKED_NO_OUTBOUND_RESPONSE_READY"
    )
    summary = {
        "material_count": len(receipts),
        "material_blocker_count": len(blockers),
        "source_evidence_verified_count": source_evidence_verified,
        "template_count": len(template_release_states),
        "structurally_valid_template_count": sum(
            row["structural_quality_pass"] for row in template_release_states
        ),
        "externally_releasable_template_count": 0,
        "lane_count": len(lane_release_states),
        "mailbox_recheck_candidate_count": sum(
            row["mailbox_recheck_candidate"] for row in lane_release_states
        ),
        "draft_render_ready_count": sum(
            row["draft_render_ready"] for row in lane_release_states
        ),
        "send_ready_lane_count": 0,
        "external_action_count": 0,
    }
    gate = {
        "schema": OUTPUT_SCHEMA,
        "generated_at_utc": generated_at,
        "status": status,
        "summary": summary,
        "material_receipts": sorted(receipts, key=lambda row: row["id"]),
        "blockers": sorted(blockers, key=lambda row: (row["code"], row["detail"])),
        "template_release_states": template_release_states,
        "lane_release_states": lane_release_states,
        "controls": config["controls"],
        "claim_boundary": config["claim_boundary"],
        "safest_next_action": (
            "Keep all response templates local. Recheck the complete LANL thread; "
            "only after a fresh no-reply receipt may one bounded private draft be "
            "rendered for exact action-time review. Do not send or submit any "
            "Monday opportunity response."
        ),
        "capability_boundary": {
            "gmail_read_performed": False,
            "email_send_performed": False,
            "private_draft_rendered": False,
            "portal_action_performed": False,
            "submission_performed": False,
        },
    }
    _walk_private_keys(gate)
    gate["gate_sha256"] = canonical_sha256(gate)
    return gate


def render_json(gate: dict[str, Any]) -> str:
    return json.dumps(gate, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def render_markdown(gate: dict[str, Any]) -> str:
    summary = gate["summary"]
    lines = [
        "# Outreach Response Conformance Gate",
        "",
        f"- As of UTC: `{gate['generated_at_utc']}`",
        f"- Status: `{gate['status']}`",
        f"- Materials: `{summary['material_count']}`",
        f"- Material/control blockers: `{summary['material_blocker_count']}`",
        f"- Structurally valid templates: `{summary['structurally_valid_template_count']}` / `{summary['template_count']}`",
        f"- Externally releasable templates: `{summary['externally_releasable_template_count']}`",
        f"- Mailbox-recheck candidates: `{summary['mailbox_recheck_candidate_count']}`",
        f"- Draft-render ready: `{summary['draft_render_ready_count']}`",
        f"- Send-ready lanes: `{summary['send_ready_lane_count']}`",
        f"- External actions performed: `{summary['external_action_count']}`",
        f"- Gate SHA-256: `{gate['gate_sha256']}`",
        "",
        "## Decision",
        "",
        "All registered templates pass structural quality checks, but no outbound response is currently release-ready. Template polish cannot override missing qualification, duplicate suppression, mailbox recheck, reviewer, submission-conformance, or action-time authority gates.",
        "",
        "## Lane Release States",
        "",
        "| Lane | Action state | Current template | Eligible template | Mailbox recheck | Draft ready | Send ready |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in gate["lane_release_states"]:
        lines.append(
            f"| `{row['lane_id']}` | `{row['action_state']}` | "
            f"`{row['current_response_template_id'] or 'NONE'}` | "
            f"`{row['eligible_template_id'] or 'NONE'}` | "
            f"`{str(row['mailbox_recheck_candidate']).lower()}` | "
            f"`{str(row['draft_render_ready']).lower()}` | `false` |"
        )
    lines.extend(
        [
            "",
            "## Template Release States",
            "",
            "| Template | Send policy | Structural pass | Release state |",
            "|---|---|---|---|",
        ]
    )
    for row in gate["template_release_states"]:
        lines.append(
            f"| `{row['template_id']}` | `{row['send_policy']}` | "
            f"`{str(row['structural_quality_pass']).lower()}` | "
            f"`{row['release_state']}` |"
        )
    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    if gate["blockers"]:
        for blocker in gate["blockers"]:
            lines.append(f"- `{blocker['code']}`: {blocker['detail']}")
    else:
        lines.append("- No material or control-integrity blocker. Release remains blocked because no lane satisfies all response and action-time gates.")
    lines.extend(
        [
            "",
            "## Safest Next Action",
            "",
            gate["safest_next_action"],
            "",
            "## Claim Boundary",
            "",
            gate["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(gate: dict[str, Any]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(render_json(gate), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(gate), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--as-of-utc", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    gate = build_gate(args.config, root=ROOT, as_of_utc=args.as_of_utc)
    if args.check:
        matches = (
            OUTPUT_JSON.is_file()
            and OUTPUT_MD.is_file()
            and OUTPUT_JSON.read_text(encoding="utf-8") == render_json(gate)
            and OUTPUT_MD.read_text(encoding="utf-8") == render_markdown(gate)
        )
        print(
            json.dumps(
                {
                    "status": gate["status"],
                    "outputs_match": matches,
                    "gate_sha256": gate["gate_sha256"],
                },
                sort_keys=True,
            )
        )
        return 0 if matches else 1
    write_outputs(gate)
    print(
        json.dumps(
            {
                "status": gate["status"],
                **gate["summary"],
                "gate_sha256": gate["gate_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
