from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MISSIONWEAVE_DIR = (
    ROOT / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave"
)
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"

GATE_PATH = MISSIONWEAVE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
QUEUE_PATH = SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
OUT_JSON = MISSIONWEAVE_DIR / "MISSIONWEAVE_FOUNDER_FINISH_CARD_2026-07-21.json"
OUT_MD = MISSIONWEAVE_DIR / "MISSIONWEAVE_FOUNDER_FINISH_CARD_2026-07-21.md"

DSIP_URL = "https://www.dodsbirsttr.mil/submissions/"
JCP_URL = "https://www.public.dacs.dla.mil/jcp/ext/"
LIFECYCLE_STAGE_TITLES = {
    "A_PRE_SUBMISSION_CONTENT_AND_EVIDENCE": "Do now",
    "B_PRE_AWARD_OR_CONTRACT_NEGOTIATION_READINESS": (
        "Bound the pre-award position"
    ),
    "C_FINAL_PREVIEW_AND_ACTION_TIME_HUMAN": "Do last",
}
PRIVATE_INPUT = (
    "grant_submissions/DLA26BZ03_NV011_MissionWeave/private/"
    "MISSIONWEAVE_DSIP_ACTION.private.json"
)


class FinishCardError(ValueError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_canonical_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return sha256_bytes(canonical.encode("utf-8"))


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256_bytes(encoded)


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def read_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinishCardError(f"UNREADABLE_SOURCE:{rel(path)}") from exc
    if not isinstance(payload, dict):
        raise FinishCardError(f"SOURCE_NOT_OBJECT:{rel(path)}")
    return payload


def parse_utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise FinishCardError("INVALID_AWARE_TIMESTAMP") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FinishCardError("INVALID_AWARE_TIMESTAMP")
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise FinishCardError(code)


def _missionweave_queue_action(queue: dict[str, Any]) -> dict[str, Any]:
    actions = queue.get("actions")
    _require(isinstance(actions, list), "QUEUE_ACTIONS_INVALID")
    matches = [
        action
        for action in actions
        if isinstance(action, dict)
        and action.get("lane_id") == "missionweave_dsip_proposal"
    ]
    _require(len(matches) == 1, "MISSIONWEAVE_QUEUE_ACTION_NOT_UNIQUE")
    return matches[0]


def _validated_steps(
    gate: dict[str, Any], unresolved: list[str]
) -> list[dict[str, Any]]:
    sequence = gate.get("founder_action_sequence")
    _require(isinstance(sequence, dict), "FOUNDER_SEQUENCE_MISSING")
    _require(sequence.get("all_open_gates_covered_once") is True, "OPEN_GATE_COVERAGE_FALSE")
    ordered = sequence.get("ordered_steps")
    _require(isinstance(ordered, list) and ordered, "FOUNDER_STEPS_INVALID")

    steps: list[dict[str, Any]] = []
    flattened: list[str] = []
    for index, raw_step in enumerate(ordered, start=1):
        _require(isinstance(raw_step, dict), "FOUNDER_STEP_NOT_OBJECT")
        open_gates = raw_step.get("open_gates")
        _require(isinstance(open_gates, list) and open_gates, "FOUNDER_STEP_GATES_INVALID")
        normalized_gates = [str(gate_id) for gate_id in open_gates]
        flattened.extend(normalized_gates)
        steps.append(
            {
                "order": index,
                "step_id": str(raw_step.get("step_id", "")),
                "title": str(raw_step.get("title", "")),
                "instruction": str(raw_step.get("instruction", "")),
                "evidence_required": str(raw_step.get("evidence_required", "")),
                "human_boundary": str(raw_step.get("human_boundary", "")),
                "open_gates": normalized_gates,
            }
        )

    _require(len(flattened) == len(set(flattened)), "FOUNDER_STEP_GATE_DUPLICATE")
    _require(set(flattened) == set(unresolved), "FOUNDER_STEP_GATE_COVERAGE_DRIFT")
    return steps


def _validated_lifecycle(
    gate: dict[str, Any], unresolved: list[str]
) -> list[dict[str, Any]]:
    lifecycle = gate.get("gate_lifecycle")
    _require(isinstance(lifecycle, dict), "GATE_LIFECYCLE_MISSING")
    _require(
        lifecycle.get("all_open_gates_classified_once") is True,
        "GATE_LIFECYCLE_COVERAGE_FALSE",
    )
    _require(
        lifecycle.get("classification_can_clear_gate") is False,
        "GATE_LIFECYCLE_CLEARANCE_UNSAFE",
    )
    stages = lifecycle.get("stages")
    _require(isinstance(stages, dict) and stages, "GATE_LIFECYCLE_STAGES_INVALID")
    _require(
        set(stages) == set(LIFECYCLE_STAGE_TITLES),
        "GATE_LIFECYCLE_STAGE_SET_DRIFT",
    )

    rows: list[dict[str, Any]] = []
    flattened: list[str] = []
    for stage_id, raw_stage in stages.items():
        _require(isinstance(raw_stage, dict), "GATE_LIFECYCLE_STAGE_NOT_OBJECT")
        open_gates = raw_stage.get("open_gates")
        _require(isinstance(open_gates, list), "GATE_LIFECYCLE_GATES_INVALID")
        normalized_gates = [str(gate_id) for gate_id in open_gates]
        _require(
            int(raw_stage.get("open_gate_count", -1)) == len(normalized_gates),
            "GATE_LIFECYCLE_COUNT_DRIFT",
        )
        flattened.extend(normalized_gates)
        rows.append(
            {
                "stage_id": str(stage_id),
                "title": LIFECYCLE_STAGE_TITLES[str(stage_id)],
                "description": str(raw_stage.get("description", "")),
                "submission_effect": str(raw_stage.get("submission_effect", "")),
                "open_gate_count": len(normalized_gates),
                "open_gates": normalized_gates,
            }
        )

    _require(len(flattened) == len(set(flattened)), "GATE_LIFECYCLE_GATE_DUPLICATE")
    _require(set(flattened) == set(unresolved), "GATE_LIFECYCLE_GATE_COVERAGE_DRIFT")
    return rows


def build_card(
    *,
    as_of_utc: str | datetime | None = None,
    gate_path: Path = GATE_PATH,
    queue_path: Path = QUEUE_PATH,
) -> dict[str, Any]:
    evaluated = parse_utc(as_of_utc or datetime.now(timezone.utc))
    gate = read_object(gate_path)
    queue = read_object(queue_path)

    _require(
        gate.get("schema") == "lumencore.missionweave_dsip_action_gate.v1",
        "GATE_SCHEMA_INVALID",
    )
    _require(
        queue.get("schema") == "lumencore.outreach_followup_action_queue.v1",
        "QUEUE_SCHEMA_INVALID",
    )
    _require(gate.get("topic") == "DLA26BZ03-NV011", "TOPIC_INVALID")

    summary = gate.get("gate_summary")
    _require(isinstance(summary, dict), "GATE_SUMMARY_INVALID")
    unresolved_raw = summary.get("unresolved_gates")
    _require(isinstance(unresolved_raw, list), "UNRESOLVED_GATES_INVALID")
    unresolved = [str(gate_id) for gate_id in unresolved_raw]
    open_count = int(summary.get("open_gate_count", -1))
    passed_count = int(summary.get("passed_private_gate_count", -1))
    required_count = int(summary.get("required_private_gate_count", -1))
    _require(open_count == len(unresolved), "OPEN_GATE_COUNT_DRIFT")
    _require(passed_count + open_count == required_count, "TOTAL_GATE_COUNT_DRIFT")

    steps = _validated_steps(gate, unresolved)
    lifecycle_stages = _validated_lifecycle(gate, unresolved)
    non_final_open_gates = [
        gate_id
        for stage in lifecycle_stages
        if stage["stage_id"] != "C_FINAL_PREVIEW_AND_ACTION_TIME_HUMAN"
        for gate_id in stage["open_gates"]
    ]
    final_open_gates = [
        gate_id
        for stage in lifecycle_stages
        if stage["stage_id"] == "C_FINAL_PREVIEW_AND_ACTION_TIME_HUMAN"
        for gate_id in stage["open_gates"]
    ]
    instruction_facts = gate.get("official_instruction_facts")
    _require(isinstance(instruction_facts, dict), "OFFICIAL_INSTRUCTION_FACTS_INVALID")
    _require(
        instruction_facts.get("projected_cmmc_level") == "Level 2 (Self)",
        "PROJECTED_CMMC_LEVEL_DRIFT",
    )
    cmmc_note = str(instruction_facts.get("cmmc_amendment_note", ""))
    tcp_note = str(
        instruction_facts.get("technology_control_plan_lifecycle_note", "")
    )
    _require("Phase I self-assessment requirements remain" in cmmc_note, "CMMC_NOTE_INVALID")
    _require("during contracting negotiation" in tcp_note, "TCP_LIFECYCLE_NOTE_INVALID")
    deadline = gate.get("deadline")
    _require(isinstance(deadline, dict), "DEADLINE_INVALID")
    deadline_utc = parse_utc(str(deadline.get("expected_utc", "")))
    remaining_seconds = max(0, int((deadline_utc - evaluated).total_seconds()))
    deadline_passed = evaluated >= deadline_utc

    queue_as_of = parse_utc(str(queue.get("as_of_utc", "")))
    _require(queue_as_of <= evaluated, "QUEUE_TIMESTAMP_IN_FUTURE")
    queue_summary = queue.get("summary")
    _require(isinstance(queue_summary, dict), "QUEUE_SUMMARY_INVALID")
    queue_controls = queue.get("controls")
    _require(isinstance(queue_controls, dict), "QUEUE_CONTROLS_INVALID")
    mailbox_recheck_max_age_seconds = int(
        queue_controls.get("mailbox_recheck_max_age_seconds", -1)
    )
    _require(
        mailbox_recheck_max_age_seconds > 0,
        "MAILBOX_RECHECK_MAX_AGE_INVALID",
    )
    queue_age_seconds = int((evaluated - queue_as_of).total_seconds())
    queue_fresh_for_action_time = (
        queue_age_seconds <= mailbox_recheck_max_age_seconds
    )
    queue_action = _missionweave_queue_action(queue)
    no_email_send_due = bool(
        queue_fresh_for_action_time
        and queue_summary.get("send_now_count") == 0
        and queue_summary.get("due_for_mailbox_recheck_count") == 0
        and queue_action.get("send_now") is False
        and queue_action.get("inbox_recheck_required") is False
    )
    if not queue_fresh_for_action_time:
        email_action_state = "UNKNOWN_RECHECK_REQUIRED"
    elif no_email_send_due:
        email_action_state = "NO_EMAIL_DUE"
    else:
        email_action_state = "QUEUE_ACTION_REVIEW_REQUIRED"

    declared_ready = gate.get("submission_ready_for_human_click") is True
    ready_for_founder_final_review = bool(
        declared_ready
        and open_count == 0
        and not deadline_passed
        and no_email_send_due
    )
    if deadline_passed:
        status = "DEADLINE_PASSED_DO_NOT_CLAIM_SUBMISSION"
    elif declared_ready and open_count == 0 and not queue_fresh_for_action_time:
        status = "MAILBOX_RECHECK_REQUIRED_NOT_SUBMISSION_READY"
    elif ready_for_founder_final_review:
        status = "READY_FOR_FOUNDER_FINAL_REVIEW_NOT_SUBMITTED"
    else:
        status = "FOUNDER_ACTION_REQUIRED_NOT_SUBMISSION_READY"

    payload: dict[str, Any] = {
        "schema": "lumencore.missionweave_founder_finish_card.v1",
        "generated_utc": iso_z(evaluated),
        "status": status,
        "topic": gate["topic"],
        "deadline": {
            "expected_local": str(deadline.get("expected_local", "")),
            "expected_utc": iso_z(deadline_utc),
            "seconds_remaining": remaining_seconds,
            "hours_remaining_rounded_down": remaining_seconds // 3600,
            "deadline_passed": deadline_passed,
            "live_dsip_recheck_required": deadline.get("live_dsip_recheck_required") is True,
            "source_discrepancy": str(deadline.get("source_discrepancy", "")),
        },
        "current_truth": {
            "passed_gate_count": passed_count,
            "open_gate_count": open_count,
            "required_gate_count": required_count,
            "submission_ready_for_human_click": ready_for_founder_final_review,
            "portal_submission_observed": gate.get("controls", {}).get("portal_submit_performed") is True,
            "unresolved_gates": unresolved,
        },
        "start_here": {
            "title": steps[0]["title"],
            "instruction": steps[0]["instruction"],
            "url": JCP_URL,
            "why_first": "Volume 5 cannot be locked without the required official JCP/DD Form 2345 evidence for the current ITAR-marked scope.",
        },
        "portal_links": [
            {"name": "Official JCP portal", "url": JCP_URL},
            {"name": "Defense SBIR/STTR submission portal", "url": DSIP_URL},
        ],
        "operator_focus": {
            "instruction": (
                "Work the pre-submission evidence stage first. Do not spend action-time "
                "approval or certify final submission until the upload set and fresh portal "
                "preview are complete."
            ),
            "lifecycle_stages": lifecycle_stages,
            "bounded_decision_support": {
                "cmmc": {
                    "projected_level": instruction_facts["projected_cmmc_level"],
                    "official_note": cmmc_note,
                    "current_packet_state": str(
                        gate.get("cmmc_evidence_packet", {}).get(
                            "requirement_evidence_state", ""
                        )
                    ),
                    "supported_position": gate.get("cmmc_evidence_packet", {}).get(
                        "phase_i_position_supported"
                    )
                    is True,
                    "safe_rule": (
                        "Do not mark the Phase I position supported from projected topic text "
                        "alone; use current authoritative evidence or a qualified reviewed "
                        "not-applicable determination."
                    ),
                },
                "technology_control_plan": {
                    "official_note": tcp_note,
                    "safe_rule": (
                        "Document only the present lifecycle position: a TCP may be requested "
                        "during contracting negotiation. Do not claim it was submitted, "
                        "approved, or accepted unless separate evidence proves that event."
                    ),
                },
            },
        },
        "ordered_founder_steps": steps,
        "operator_command_rails": {
            "current_fact_capture": {
                "status": "RUN_NOW_HUMAN_FACT_REVIEW_REQUIRED",
                "open_gate_count": len(non_final_open_gates),
                "open_gate_ids": non_final_open_gates,
                "command": (
                    "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py "
                    "--section pre-submit --open-gates-only "
                    "--use-current-volume2-hash"
                ),
                "behavior": (
                    "Prompts only unresolved non-final facts through hidden Y/N/Keep "
                    "inputs. It never requests a Firm PIN value, password, or one-time code."
                ),
            },
            "deferred_final_capture": {
                "status": "DO_NOT_RUN_UNTIL_UPLOAD_SET_AND_PREVIEW_ARE_FINAL",
                "open_gate_count": len(final_open_gates),
                "open_gate_ids": final_open_gates,
                "preview_command_template": (
                    "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py "
                    "--section proposal --open-gates-only "
                    "--preview-receipt-file <PRIVATE_PREVIEW_RECEIPT>"
                ),
                "final_compliance_command": (
                    "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py "
                    "--section compliance --open-gates-only"
                ),
                "approval_command": (
                    "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py "
                    "--section approval"
                ),
            },
        },
        "outreach_control": {
            "queue_path": rel(queue_path),
            "queue_as_of_utc": iso_z(queue_as_of),
            "queue_age_seconds": queue_age_seconds,
            "mailbox_recheck_max_age_seconds": mailbox_recheck_max_age_seconds,
            "queue_fresh_for_action_time": queue_fresh_for_action_time,
            "mailbox_recheck_required_now": not queue_fresh_for_action_time,
            "email_action_state": email_action_state,
            "queue_status": str(queue.get("status", "")),
            "routing_integrity_exception_count": int(
                queue_summary.get("routing_integrity_exception_count", 0)
            ),
            "missionweave_action_state": str(queue_action.get("action_state", "")),
            "recorded_proactive_send_count": int(
                queue_action.get("recorded_proactive_send_count", 0)
            ),
            "no_email_send_due": no_email_send_due,
            "next_action": str(queue_action.get("next_action", "")),
        },
        "safe_local_commands": [
            (
                "python code/ops/BUILD_MISSIONWEAVE_FOUNDER_FINISH_CARD.py "
                "--check-only"
            ),
            "python code/ops/CAPTURE_MISSIONWEAVE_JCP_EVIDENCE.py --check-target",
            "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --check-target",
            "python code/ops/FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py --check-target",
            (
                "python code/ops/CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py "
                "--section pre-submit --open-gates-only "
                "--use-current-volume2-hash"
            ),
            (
                "python code/ops/BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py "
                f"--private-input {PRIVATE_INPUT}"
            ),
        ],
        "human_only_actions": [
            "Enter passwords, Firm PIN values, and one-time authentication codes.",
            "Confirm entity, cost, conflicts, rights, CMMC, and export-control facts.",
            "Complete any JCP or DSIP certification or legal attestation.",
            "Review the complete rendered Government portal preview.",
            "Authorize and click the final DSIP submit control.",
        ],
        "jcp_receipt_capture_command_template": (
            "python code/ops/CAPTURE_MISSIONWEAVE_JCP_EVIDENCE.py "
            "--evidence-file <PRIVATE_OFFICIAL_PDF> "
            "--evidence-kind JCP_APPLICATION_SUBMISSION_RECEIPT "
            "--source-issued-utc <OFFICIAL_RECEIPT_TIMESTAMP> "
            "--confirm-entity-match --confirm-corporate-review"
        ),
        "never_record_in_public_files": [
            "passwords",
            "Firm PIN value",
            "one-time authentication codes",
            "private identifiers",
            "assigned proposal number",
            "private receipt paths or hashes",
        ],
        "controls": {
            "builder_can_click_final_submit": False,
            "builder_can_certify_legal_facts": False,
            "builder_can_send_duplicate_followup": False,
            "action_time_approval_required": True,
            "approval_max_age_seconds": int(
                gate.get("controls", {}).get("action_time_approval_max_age_seconds", 0)
            ),
            "preview_max_age_seconds": int(
                gate.get("controls", {}).get("preview_receipt_max_age_seconds", 0)
            ),
        },
        "source_integrity": {
            "gate_path": rel(gate_path),
            "gate_canonical_text_sha256": sha256_canonical_text(gate_path),
            "gate_payload_sha256": str(gate.get("gate_sha256", "")),
            "gate_source_checks_pass": gate.get("source_integrity", {}).get("all_checks_pass") is True,
            "queue_canonical_text_sha256": sha256_canonical_text(queue_path),
            "queue_payload_sha256": str(queue.get("queue_sha256", "")),
        },
        "claim_boundary": (
            "This card is a current operator checklist derived from local control artifacts. "
            "It does not prove JCP approval, DD Form 2345 certification, CMMC status, ITAR "
            "compliance, proposal submission, DLA receipt, eligibility, selection, award, "
            "endorsement, deployment, technical validation, funding, or value."
        ),
    }
    payload["card_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    truth = payload["current_truth"]
    deadline = payload["deadline"]
    outreach = payload["outreach_control"]
    focus = payload["operator_focus"]
    command_rails = payload["operator_command_rails"]
    current_capture = command_rails["current_fact_capture"]
    deferred_capture = command_rails["deferred_final_capture"]
    decision_support = focus["bounded_decision_support"]
    if outreach["email_action_state"] == "NO_EMAIL_DUE":
        email_due_text = "false"
    elif outreach["email_action_state"] == "UNKNOWN_RECHECK_REQUIRED":
        email_due_text = "unknown - refresh mailbox evidence"
    else:
        email_due_text = "review required"
    lines = [
        "# MissionWeave Founder Finish Card",
        "",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Deadline: **{deadline['expected_local']}** (`{deadline['expected_utc']}`)",
        f"- Time remaining at generation: `{deadline['hours_remaining_rounded_down']}` full hours",
        f"- Current gate: **{truth['passed_gate_count']}/{truth['required_gate_count']} passed; {truth['open_gate_count']} open**",
        f"- Submission-ready: **{str(truth['submission_ready_for_human_click']).lower()}**",
        f"- Status: `{payload['status']}`",
        "",
        "## Start Here",
        "",
        f"1. Open the [official JCP portal]({payload['start_here']['url']}).",
        f"2. {payload['start_here']['instruction']}",
        "3. Keep the official receipt PDF private. Do not paste a Firm PIN, password, or one-time code into chat or Git.",
        "",
        "Why first: " + payload["start_here"]["why_first"],
        "",
        "## What To Do Now",
        "",
        focus["instruction"],
        "",
    ]
    for stage in focus["lifecycle_stages"]:
        lines.append(
            f"- **{stage['title']}**: {stage['open_gate_count']} open. "
            f"{stage['description']}"
        )
    lines.extend(
        [
            "",
            "### CMMC And TCP Decision Support",
            "",
            f"- CMMC projected level: `{decision_support['cmmc']['projected_level']}`.",
            f"- CMMC evidence state: `{decision_support['cmmc']['current_packet_state']}`; "
            f"supported position: `{str(decision_support['cmmc']['supported_position']).lower()}`.",
            f"- CMMC rule: {decision_support['cmmc']['safe_rule']}",
            f"- TCP rule: {decision_support['technology_control_plan']['safe_rule']}",
            "",
            "## One Bounded Fact Pass",
            "",
            f"This asks only the `{current_capture['open_gate_count']}` currently open "
            "non-final facts and preserves every already-cleared answer:",
            "",
            f"`{current_capture['command']}`",
            "",
            current_capture["behavior"],
            "",
            f"Deferred final-stage gates: `{deferred_capture['open_gate_count']}`. "
            "Do not run preview or approval capture until the upload set is final.",
            "",
            "## Do These In Order",
            "",
        ]
    )
    for step in payload["ordered_founder_steps"]:
        lines.extend(
            [
                f"### {step['order']}. {step['title']}",
                "",
                f"- Do: {step['instruction']}",
                f"- Evidence needed: {step['evidence_required']}",
                f"- Human boundary: {step['human_boundary']}",
                f"- Clears: `{', '.join(step['open_gates'])}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Email State",
            "",
            f"- Queue status: `{outreach['queue_status']}`",
            f"- MissionWeave action: `{outreach['missionweave_action_state']}`",
            f"- Queue fresh for action time: **{str(outreach['queue_fresh_for_action_time']).lower()}** "
            f"(`{outreach['queue_age_seconds']}` / "
            f"`{outreach['mailbox_recheck_max_age_seconds']}` seconds)",
            f"- Mailbox recheck required now: **{str(outreach['mailbox_recheck_required_now']).lower()}**",
            f"- Additional email due now: **{email_due_text}**",
            f"- Next action: {outreach['next_action']}",
            "",
            "## Safe Local Checks",
            "",
        ]
    )
    lines.extend(f"- `{command}`" for command in payload["safe_local_commands"])
    lines.extend(
        [
            "",
            "After you have reviewed the official receipt PDF and its entity/timestamp, use this template locally:",
            "",
            f"`{payload['jcp_receipt_capture_command_template']}`",
            "",
            "## Deferred Final Commands",
            "",
            "Only after the upload set is final, bind the fresh private preview receipt:",
            "",
            f"`{deferred_capture['preview_command_template']}`",
            "",
            "After reviewing the preview, finish any still-open compliance decision:",
            "",
            f"`{deferred_capture['final_compliance_command']}`",
            "",
            "Run approval capture last, immediately before the founder-controlled submit action:",
            "",
            f"`{deferred_capture['approval_command']}`",
        ]
    )
    lines.extend(
        [
            "",
            "## Stop Line",
            "",
            "Do not certify or click final submit until the regenerated action gate reports `READY_FOR_HUMAN_FINAL_SUBMIT_CLICK`, all 50 gates pass, the complete portal preview is fresh, and Robert performs the final review and action-time authorization.",
            "",
            "## Source Lock",
            "",
            f"- Action gate: `{payload['source_integrity']['gate_path']}`",
            f"- Action-gate canonical-text SHA-256: `{payload['source_integrity']['gate_canonical_text_sha256']}`",
            f"- Outreach queue canonical-text SHA-256: `{payload['source_integrity']['queue_canonical_text_sha256']}`",
            f"- Card SHA-256: `{payload['card_sha256']}`",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    payload: dict[str, Any], *, out_json: Path = OUT_JSON, out_md: Path = OUT_MD
) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed MissionWeave founder finish card."
    )
    parser.add_argument(
        "--as-of-utc",
        help="Aware timestamp used for the deadline countdown; defaults to current UTC.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Print a live fail-closed summary without rewriting tracked artifacts.",
    )
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=OUT_MD)
    args = parser.parse_args()

    payload = build_card(as_of_utc=args.as_of_utc)
    if not args.check_only:
        write_outputs(payload, out_json=args.out_json, out_md=args.out_md)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "passed": payload["current_truth"]["passed_gate_count"],
                "open": payload["current_truth"]["open_gate_count"],
                "hours_remaining": payload["deadline"]["hours_remaining_rounded_down"],
                "no_email_send_due": payload["outreach_control"]["no_email_send_due"],
                "mailbox_recheck_required_now": payload["outreach_control"][
                    "mailbox_recheck_required_now"
                ],
                "write_performed": not args.check_only,
                "card_sha256": payload["card_sha256"],
                "json": rel(args.out_json),
                "markdown": rel(args.out_md),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
