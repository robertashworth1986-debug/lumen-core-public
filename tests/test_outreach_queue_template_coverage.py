from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "code" / "ops" / "AUDIT_OUTREACH_QUEUE_TEMPLATE_COVERAGE.py"
)
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
QUEUE = SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
REGISTRY = (
    SPRINT_DIR / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "outreach_queue_template_coverage_test",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def inputs() -> tuple[dict[str, object], dict[str, object]]:
    return (
        json.loads(QUEUE.read_text(encoding="utf-8")),
        json.loads(REGISTRY.read_text(encoding="utf-8")),
    )


def refresh_summary(queue: dict[str, object]) -> None:
    actions = queue["actions"]
    counts: dict[str, int] = {}
    for action in actions:
        state = action["action_state"]
        counts[state] = counts.get(state, 0) + 1
    queue["summary"]["lane_count"] = len(actions)
    queue["summary"]["action_state_counts"] = dict(sorted(counts.items()))
    if "send_now_count" in queue["summary"]:
        queue["summary"]["send_now_count"] = sum(
            action["send_now"] is True for action in actions
        )


def test_current_committed_queue_has_complete_template_coverage():
    module = load_module()
    queue, registry = inputs()

    audit = module.audit_coverage(queue, registry)

    assert audit["status"] == "PASS"
    assert audit["lane_count"] == 17
    assert audit["template_count"] == 11
    assert audit["failed_lane_count"] == 0
    assert audit["blockers"] == []
    assert all(row["status"] == "PASS" for row in audit["rows"])
    assert audit["builder_can_send_email"] is False
    assert audit["external_action_performed"] is False


def test_due_email_lane_requires_exact_current_template_and_recheck():
    module = load_module()
    queue, registry = inputs()
    due = queue["actions"][0]
    due.update(
        {
            "action_state": "RECHECK_MAILBOX_BEFORE_DRAFT",
            "eligible_template_id": "VALIDATION_PILOT_REQUEST",
            "current_response_template_id": None,
            "inbox_recheck_required": False,
            "send_now": False,
        }
    )
    refresh_summary(queue)

    audit = module.audit_coverage(queue, registry)

    row = audit["rows"][0]
    assert audit["status"] == "FAIL"
    assert "LANE_COVERAGE_FAILURE" in audit["blockers"]
    assert row["blockers"] == [
        "DUE_LANE_CURRENT_TEMPLATE_MISSING",
        "DUE_LANE_INBOX_RECHECK_NOT_REQUIRED",
        "DUE_LANE_TEMPLATE_MISMATCH",
    ]


def test_unknown_template_and_action_state_fail_closed():
    module = load_module()
    queue, registry = inputs()
    queue["actions"][0]["eligible_template_id"] = "UNKNOWN_TEMPLATE"
    queue["actions"][0]["action_state"] = "NEW_UNREVIEWED_STATE"
    refresh_summary(queue)

    audit = module.audit_coverage(queue, registry)

    row = audit["rows"][0]
    assert audit["status"] == "FAIL"
    assert "ACTION_STATE_UNKNOWN" in row["blockers"]
    assert "ELIGIBLE_TEMPLATE_UNKNOWN" in row["blockers"]


def test_autonomous_send_and_summary_drift_are_rejected():
    module = load_module()
    queue, registry = inputs()
    queue["actions"][0]["send_now"] = True
    queue["summary"]["lane_count"] = 999

    audit = module.audit_coverage(queue, registry)

    assert audit["status"] == "FAIL"
    assert "QUEUE_AUTONOMOUS_SEND_PRESENT" in audit["blockers"]
    assert "QUEUE_LANE_COUNT_MISMATCH" in audit["blockers"]
    assert "AUTONOMOUS_SEND_STATE_FORBIDDEN" in audit["rows"][0][
        "blockers"
    ]


def test_duplicate_lane_and_missing_next_action_are_rejected():
    module = load_module()
    queue, registry = inputs()
    duplicate = copy.deepcopy(queue["actions"][0])
    duplicate["next_action"] = ""
    queue["actions"].append(duplicate)
    refresh_summary(queue)

    audit = module.audit_coverage(queue, registry)

    assert audit["status"] == "FAIL"
    assert "QUEUE_LANE_ID_DUPLICATE" in audit["blockers"]
    assert "NEXT_ACTION_MISSING" in audit["rows"][-1]["blockers"]


def test_no_send_template_is_required():
    module = load_module()
    queue, registry = inputs()
    registry["templates"] = [
        template
        for template in registry["templates"]
        if template["template_id"] != "NO_DUPLICATE_MONITOR"
    ]

    audit = module.audit_coverage(queue, registry)

    assert audit["status"] == "FAIL"
    assert "NO_SEND_TEMPLATE_UNAVAILABLE" in audit["blockers"]
    assert "CURRENT_TEMPLATE_UNKNOWN" in audit["rows"][0]["blockers"]


def test_cli_check_mode_writes_nothing(tmp_path):
    json_output = tmp_path / "coverage.json"
    markdown_output = tmp_path / "coverage.md"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--queue",
            str(QUEUE),
            "--registry",
            str(REGISTRY),
            "--json-output",
            str(json_output),
            "--markdown-output",
            str(markdown_output),
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "PASS"
    assert summary["outputs_written"] is False
    assert json_output.exists() is False
    assert markdown_output.exists() is False


def test_cli_rejects_duplicate_json_keys(tmp_path):
    queue_path = tmp_path / "duplicate.json"
    queue_path.write_text(
        '{"schema":"first","schema":"second"}',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--queue",
            str(queue_path),
            "--registry",
            str(REGISTRY),
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "DUPLICATE_JSON_KEY:schema" in result.stderr
