from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_DEADLINE_ACTION_SENTINEL.py"
CONFIG = ROOT / "config" / "deadline_action_sentinel_v1.json"
JSON_OUTPUT = (
    ROOT / "evidence" / "opportunity" / "deadline_action_sentinel_latest.json"
)
MARKDOWN_OUTPUT = ROOT / "docs" / "DEADLINE_ACTION_SENTINEL.md"
WORKFLOW = ROOT / ".github" / "workflows" / "deadline-action-sentinel.yml"

SPEC = importlib.util.spec_from_file_location("deadline_action_sentinel", SCRIPT)
assert SPEC and SPEC.loader
SENTINEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SENTINEL)


def as_of(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def lane(payload: dict, lane_id: str) -> dict:
    return next(item for item in payload["lanes"] if item["id"] == lane_id)


def write_config(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_argos_exact_deadline_is_bound_to_gate_and_fail_closed():
    payload = SENTINEL.build_sentinel(CONFIG, as_of("2026-07-27T02:45:00Z"))
    argos = lane(payload, "ONC_ARGOS_20260730")

    assert argos["state"] == "BLOCKED_HUMAN_ACTION_DUE"
    assert argos["urgency"] == "WITHIN_ALERT_WINDOW"
    assert argos["deadline"]["iso_utc"] == "2026-07-30T21:00:00Z"
    assert argos["deadline"]["hours_until_deadline"] == 90.25
    assert argos["deadline"]["deadline_passed"] is False
    assert argos["source_receipt"]["observed_status"] == "BLOCK_SEND"
    assert len(argos["source_receipt"]["sha256"]) == 64
    assert argos["external_action_authorized"] is False
    assert argos["send_now"] is False
    assert argos["external_action_executed"] is False


def test_exact_deadline_turns_past_without_authorizing_late_action():
    payload = SENTINEL.build_sentinel(CONFIG, as_of("2026-07-30T21:00:01Z"))
    argos = lane(payload, "ONC_ARGOS_20260730")

    assert argos["state"] == "PAST_DEADLINE_NO_EXTERNAL_ACTION_AUTHORIZED"
    assert argos["urgency"] == "PAST"
    assert argos["deadline"]["deadline_passed"] is True
    assert argos["deadline"]["seconds_until_deadline"] == -1
    assert argos["external_action_authorized"] is False


def test_monday_deadline_lanes_are_reconciled_without_new_action():
    payload = SENTINEL.build_sentinel(CONFIG, as_of("2026-07-27T20:12:08Z"))
    csdr = lane(payload, "DAF_CSDR_20260727")
    nsf = lane(payload, "NSF_26_510_20260727")

    assert csdr["state"] == "PAST_DEADLINE_NO_EXTERNAL_ACTION_AUTHORIZED"
    assert csdr["deadline"]["deadline_passed"] is True
    assert (
        csdr["source_receipt"]["observed_status"]
        == "PAST_DEADLINE_NO_LATE_OR_DUPLICATE_ACTION"
    )
    assert csdr["send_now"] is False
    assert csdr["external_action_authorized"] is False

    assert nsf["state"] == "HUMAN_DATE_ONLY_ACTION_DUE_DATE_UNKNOWN_CUTOFF"
    assert nsf["urgency"] == "UNKNOWN_EXACT_CUTOFF_FAIL_CLOSED"
    assert nsf["deadline"]["deadline_passed"] is None
    assert "iso_utc" not in nsf["deadline"]
    assert (
        nsf["source_receipt"]["observed_status"]
        == "BLOCKED_NO_OFFICIAL_PROJECT_PITCH_INVITATION"
    )
    assert nsf["send_now"] is False
    assert nsf["external_action_authorized"] is False


@pytest.mark.parametrize(
    ("evaluated", "expected_state", "expected_relation"),
    [
        (
            "2026-07-30T23:59:59Z",
            "HUMAN_DATE_ONLY_ACTION_OPEN",
            "FUTURE_BY_UTC_CALENDAR_DATE",
        ),
        (
            "2026-07-31T12:00:00Z",
            "HUMAN_DATE_ONLY_ACTION_DUE_DATE_UNKNOWN_CUTOFF",
            "SAME_UTC_CALENDAR_DATE",
        ),
        (
            "2026-08-01T12:00:00Z",
            "HUMAN_DATE_ONLY_RECONCILIATION_REQUIRED",
            "AFTER_DATE_BY_UTC_CALENDAR_ONLY",
        ),
    ],
)
def test_date_only_deadline_never_invents_countdown_or_overdue_status(
    evaluated: str, expected_state: str, expected_relation: str
):
    payload = SENTINEL.build_sentinel(CONFIG, as_of(evaluated))
    onboarding = lane(payload, "NASHVILLE_ONBOARDING_20260731")
    deadline = onboarding["deadline"]

    assert onboarding["state"] == expected_state
    assert onboarding["urgency"] == "UNKNOWN_EXACT_CUTOFF_FAIL_CLOSED"
    assert deadline["calendar_relation"] == expected_relation
    assert deadline["cutoff_time_known"] is False
    assert deadline["timezone_known"] is False
    assert deadline["exact_countdown_available"] is False
    assert deadline["deadline_passed"] is None
    assert "seconds_until_deadline" not in deadline
    assert "hours_until_deadline" not in deadline
    assert "iso_utc" not in deadline
    assert onboarding["external_action_authorized"] is False


def test_autonomous_control_tampering_is_rejected(tmp_path: Path):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["controls"]["autonomous_email_send_allowed"] = True
    tampered = tmp_path / "tampered.json"
    write_config(tampered, config)

    with pytest.raises(ValueError, match="control must remain false"):
        SENTINEL.build_sentinel(tampered, as_of("2026-07-27T02:45:00Z"))


def test_source_deadline_mismatch_is_rejected(tmp_path: Path):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    changed = deepcopy(config)
    argos = next(
        item for item in changed["lanes"] if item["id"] == "ONC_ARGOS_20260730"
    )
    argos["deadline"]["iso_utc"] = "2026-07-30T22:00:00Z"
    tampered = tmp_path / "deadline-mismatch.json"
    write_config(tampered, changed)

    with pytest.raises(ValueError, match="does not match the repository gate"):
        SENTINEL.build_sentinel(tampered, as_of("2026-07-27T02:45:00Z"))


def test_source_date_mismatch_is_rejected(tmp_path: Path):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    changed = deepcopy(config)
    nsf = next(
        item for item in changed["lanes"] if item["id"] == "NSF_26_510_20260727"
    )
    nsf["deadline"]["date"] = "2026-07-28"
    tampered = tmp_path / "date-mismatch.json"
    write_config(tampered, changed)

    with pytest.raises(ValueError, match="does not match the repository gate"):
        SENTINEL.build_sentinel(tampered, as_of("2026-07-27T20:12:08Z"))


def test_snapshot_is_current_private_safe_and_action_free():
    snapshot = json.loads(JSON_OUTPUT.read_text(encoding="utf-8"))
    evaluated = as_of(snapshot["evaluated_utc"])
    rebuilt = SENTINEL.build_sentinel(CONFIG, evaluated)
    markdown = SENTINEL.render_markdown(rebuilt)
    serialized = json.dumps(rebuilt)

    assert snapshot == rebuilt
    assert MARKDOWN_OUTPUT.read_text(encoding="utf-8") == markdown
    assert (
        "`NSF_26_510_20260727`: "
        "`evidence/opportunity/nsf_26_510_deadline_gate_2026-07-27.json`"
        in markdown
    )
    assert (
        "`NSF_26_510_20260727`: private official-event metadata only"
        not in markdown
    )
    assert snapshot["summary"]["autonomous_external_action_count"] == 0
    assert snapshot["summary"]["external_actions_executed_count"] == 0
    assert all(item["send_now"] is False for item in snapshot["lanes"])
    assert all(
        item["external_action_authorized"] is False for item in snapshot["lanes"]
    )
    for forbidden in (
        "@",
        "discount_code",
        "source_message_id",
        "thread_id",
        "account_number",
        "access_code",
    ):
        assert forbidden not in serialized


def test_cli_check_rebuilds_the_snapshot_without_mutation():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "CURRENT"
    assert receipt["external_actions_executed_count"] == 0


def test_ci_enforces_snapshot_and_fail_closed_tests():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "BUILD_DEADLINE_ACTION_SENTINEL.py --check" in workflow
    assert "python-docx==1.2.0" in workflow
    assert "build_argos_private_action_copy.py" in workflow
    assert "tests/test_deadline_action_sentinel.py" in workflow
    assert "tests/test_current_opportunity_and_argos_packet.py" in workflow
    assert "grant_submissions/ONC_ARGOS_20260730/ARGOS_SUBMISSION_GATE_2026-07-26.json" in workflow
    assert "evidence/opportunity/csdr_deadline_gate_2026-07-27.json" in workflow
    assert "evidence/opportunity/nsf_26_510_deadline_gate_2026-07-27.json" in workflow
    assert "evidence/opportunity/official_status_events_2026-07-27.json" in workflow
    assert "permissions:\n  contents: read" in workflow
