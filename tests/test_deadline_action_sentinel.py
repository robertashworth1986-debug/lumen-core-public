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
ARGOS_STATUS = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "ARGOS_PARTNER_OUTREACH_STATUS_2026-07-28.json"
)
ARGOS_GOVERNMENT_STATUS = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "ARGOS_GOVERNMENT_RESPONSE_STATUS_2026-07-29.json"
)
ARGOS_OFFICIAL_SOURCE_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "source_attachments"
    / "PROJECT_ARGOS_SOW_OFFICIAL_SOURCE_RECEIPT_2026-07-28.json"
)

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
    payload = SENTINEL.build_sentinel(CONFIG, as_of("2026-07-29T02:00:00Z"))
    argos = lane(payload, "ONC_ARGOS_20260730")

    assert (
        argos["state"]
        == "GOVERNMENT_RESPONSE_SENT_ONCE_WAITING_FOR_SUBSTANTIVE_REPLY"
    )
    assert argos["urgency"] == "WITHIN_72_HOURS"
    assert argos["deadline"]["iso_utc"] == "2026-07-30T21:00:00Z"
    assert argos["deadline"]["hours_until_deadline"] == 43.0
    assert argos["deadline"]["deadline_passed"] is False
    assert (
        argos["source_receipt"]["observed_status"]
        == "BLOCK_SEND"
    )
    assert len(argos["source_receipt"]["sha256"]) == 64
    assert argos["external_action_authorized"] is False
    assert argos["send_now"] is False
    assert argos["external_action_executed"] is False
    outreach = argos["outreach_status"]
    assert (
        outreach["current_state_as_of_evaluation"]
        == "PARTNER_TARGET_PASSED_WAITING_FOR_REPLY"
    )
    assert outreach["seconds_until_partner_target"] == -32400
    assert outreach["mailbox_state_as_of_record"] == {
        "current_draft_count": 0,
        "sent_count": 1,
        "inbound_count": 0,
        "attachment_count": 0,
        "cc_count": 0,
        "bcc_count": 0,
    }
    assert outreach["selected_template_id"] == "INITIAL_PARTNER_TEAMING_INQUIRY"
    assert outreach["prior_binding_expired"] is True
    assert outreach["prior_approval_reusable"] is False
    assert outreach["binding_match_status"] == (
        "MISMATCH_RETAINED_AS_UNRECONCILED_PUBLIC_AUDIT_GAP"
    )
    assert outreach["public_authorization_chain_reconciled"] is False
    assert outreach["sent_content_source_bound_by_post_send_hashes"] is True
    assert outreach["fresh_recheck_required"] is False
    assert outreach["new_exact_approval_required"] is False
    assert outreach["duplicate_send_prohibited"] is True
    assert outreach["government_response_action_time_gates_required"] is False
    government = argos["government_response_status"]
    assert government["observed_state"] == (
        "SENT_ONCE_AUTOMATIC_MAILBOX_ACK_WAITING_FOR_SUBSTANTIVE_REPLY"
    )
    assert government["sent_utc"] == "2026-07-29T01:52:18Z"
    assert government["automatic_acknowledgment_utc"] == "2026-07-29T01:54:02Z"
    assert government["official_source_receipt_path"] == (
        "grant_submissions/funding_sprint_20260709/source_attachments/"
        "PROJECT_ARGOS_SOW_OFFICIAL_SOURCE_RECEIPT_2026-07-28.json"
    )
    assert government["official_source_receipt_sha256"] == (
        "5479D7DB1DC3777D9E6C177F92800BD198392105D46A2CF78C56554C86B8820D"
    )
    assert government["official_source_receipt_sha256"] == SENTINEL.sha256(
        ARGOS_OFFICIAL_SOURCE_RECEIPT
    ).upper()
    assert government["mailbox_state_as_of_record"] == {
        "sent_count": 1,
        "automatic_acknowledgment_count": 1,
        "formal_receipt_count": 0,
        "substantive_inbound_count": 0,
        "attachment_count": 1,
        "cc_count": 0,
        "bcc_count": 0,
    }
    assert government["attachment_filename"] == "ARGOS_PRIVATE_ACTION_COPY.docx"
    assert government["attachment_size_bytes"] == 730579
    assert government["attachment_sha256"] == (
        "459C92DB998CC6B7CB9C81064186CBB65DD897261CD3C7F1F1D69A3D38368CC1"
    )
    assert government["duplicate_send_prohibited"] is True
    assert government["automatic_acknowledgment_is_formal_receipt"] is False
    assert government["automatic_acknowledgment_is_substantive_review"] is False
    assert government["automatic_acknowledgment_authorizes_follow_up"] is False
    assert government["action_time_provenance_reconciled"] is False
    assert (
        government["sent_event_cryptographically_anchored_at_action_time"]
        is False
    )


def test_argos_government_status_is_time_consistent_before_post_send_record():
    payload = SENTINEL.build_sentinel(CONFIG, as_of("2026-07-29T01:50:00Z"))
    argos = lane(payload, "ONC_ARGOS_20260730")

    assert argos["state"] == "PARTNER_OUTREACH_SENT_ONCE_GOVERNMENT_RESPONSE_DUE"
    assert "government_response_status" not in argos
    assert "government_response_status" not in argos["source_receipt"]
    assert (
        argos["outreach_status"][
            "government_response_action_time_gates_required"
        ]
        is True
    )


@pytest.mark.parametrize(
    "evaluated",
    ["2026-07-30T21:00:00Z", "2026-07-30T21:00:01Z"],
)
def test_exact_deadline_turns_past_without_authorizing_late_action(
    evaluated: str,
):
    payload = SENTINEL.build_sentinel(CONFIG, as_of(evaluated))
    argos = lane(payload, "ONC_ARGOS_20260730")

    assert argos["state"] == "PAST_DEADLINE_NO_EXTERNAL_ACTION_AUTHORIZED"
    assert argos["urgency"] == "PAST"
    assert argos["deadline"]["deadline_passed"] is True
    assert argos["deadline"]["seconds_until_deadline"] <= 0
    assert argos["external_action_authorized"] is False
    assert argos["send_now"] is False
    assert (
        argos["outreach_status"]["current_state_as_of_evaluation"]
        == "OFFICIAL_DEADLINE_PASSED_NO_SEND"
    )


def test_argos_status_cannot_be_used_before_its_record_time():
    with pytest.raises(ValueError, match="before its record time"):
        SENTINEL.build_sentinel(CONFIG, as_of("2026-07-28T16:45:48Z"))


def test_monday_deadline_lanes_are_reconciled_without_new_action():
    payload = SENTINEL.build_sentinel(CONFIG, as_of("2026-07-28T20:20:00Z"))
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

    assert nsf["state"] == "HUMAN_DATE_ONLY_RECONCILIATION_REQUIRED"
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


def test_ec_onboarding_completion_receipt_closes_only_the_onboarding_lane():
    payload = SENTINEL.build_sentinel(CONFIG, as_of("2026-08-03T14:30:00Z"))
    onboarding = lane(payload, "NASHVILLE_ONBOARDING_20260731")
    deposit = lane(payload, "NASHVILLE_DEPOSIT_20260814")

    assert onboarding["completion_evidence_present"] is True
    assert onboarding["completion_evidence_recorded_utc"] == (
        "2026-08-03T14:19:08Z"
    )
    assert onboarding["state"] == (
        "COMPLETION_EVIDENCE_RECORDED_NO_EXTERNAL_ACTION_REQUIRED"
    )
    assert onboarding["urgency"] == "COMPLETED"
    assert onboarding["requires_human_attention"] is False
    assert onboarding["external_action_authorized"] is False
    assert onboarding["send_now"] is False
    assert onboarding["external_action_executed"] is False
    assert "separate 125 USD deposit" in onboarding["blockers"][0]

    assert deposit["completion_evidence_present"] is False
    assert deposit["requires_human_attention"] is True
    assert deposit["external_action_authorized"] is False


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
        SENTINEL.build_sentinel(tampered, as_of("2026-07-28T16:50:00Z"))


@pytest.mark.parametrize(
    ("path", "value", "error"),
    [
        (
            ("mailbox_observation", "matching_sent_count"),
            0,
            "mailbox count changed",
        ),
        (
            ("mailbox_observation", "subject_sha256"),
            "0" * 64,
            "subject hash no longer matches",
        ),
        (
            ("prior_binding", "prior_approval_reusable"),
            True,
            "prior approval must remain nonreusable",
        ),
        (
            ("prior_binding", "historical_snapshot_binding_sha256"),
            "0" * 64,
            "no longer matches the historical binding snapshot",
        ),
    ],
)
def test_argos_status_tampering_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    path: tuple[str, str],
    value: object,
    error: str,
):
    status = json.loads(ARGOS_STATUS.read_text(encoding="utf-8"))
    status[path[0]][path[1]] = value
    original_read_json = SENTINEL.read_json

    def read_with_tampered_status(path_value: Path) -> dict:
        if path_value.resolve() == ARGOS_STATUS.resolve():
            return status
        return original_read_json(path_value)

    monkeypatch.setattr(SENTINEL, "read_json", read_with_tampered_status)

    with pytest.raises(ValueError, match=error):
        SENTINEL.build_sentinel(
            CONFIG,
            as_of("2026-07-28T16:50:00Z"),
        )


@pytest.mark.parametrize(
    ("path", "value", "error"),
    [
        (
            ("mailbox_observation", "sent_count"),
            0,
            "mailbox count changed",
        ),
        (
            ("controls", "automatic_acknowledgment_is_formal_receipt"),
            True,
            "control must remain false",
        ),
        (
            ("source_and_attachment_binding", "attachment_sha256"),
            "0" * 64,
            "attachment SHA-256 changed",
        ),
        (
            ("source_and_attachment_binding", "official_source_receipt_sha256"),
            "0" * 64,
            "source receipt SHA-256 changed",
        ),
    ],
)
def test_argos_government_status_tampering_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    path: tuple[str, str],
    value: object,
    error: str,
):
    status = json.loads(ARGOS_GOVERNMENT_STATUS.read_text(encoding="utf-8"))
    status[path[0]][path[1]] = value
    original_read_json = SENTINEL.read_json

    def read_with_tampered_status(path_value: Path) -> dict:
        if path_value.resolve() == ARGOS_GOVERNMENT_STATUS.resolve():
            return status
        return original_read_json(path_value)

    monkeypatch.setattr(SENTINEL, "read_json", read_with_tampered_status)

    with pytest.raises(ValueError, match=error):
        SENTINEL.build_sentinel(
            CONFIG,
            as_of("2026-07-29T02:00:00Z"),
        )


def test_argos_status_rejects_private_identifier_fields(
    monkeypatch: pytest.MonkeyPatch,
):
    status = json.loads(ARGOS_STATUS.read_text(encoding="utf-8"))
    status["mailbox_observation"]["message_id"] = "not-public"
    original_read_json = SENTINEL.read_json

    def read_with_private_status(path_value: Path) -> dict:
        if path_value.resolve() == ARGOS_STATUS.resolve():
            return status
        return original_read_json(path_value)

    monkeypatch.setattr(SENTINEL, "read_json", read_with_private_status)

    with pytest.raises(ValueError, match="private field is not permitted"):
        SENTINEL.build_sentinel(
            CONFIG,
            as_of("2026-07-28T16:50:00Z"),
        )


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
    assert "SENT_ONCE_POST_SEND_VERIFIED_WAITING_FOR_REPLY" in markdown
    assert "0 draft, 1 sent, and 0 inbound" in markdown
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
    assert (
        "grant_submissions/funding_sprint_20260709/"
        "ARGOS_PARTNER_OUTREACH_STATUS_2026-07-28.json"
        in workflow
    )
    assert (
        "grant_submissions/funding_sprint_20260709/"
        "ARGOS_GOVERNMENT_RESPONSE_STATUS_2026-07-29.json"
        in workflow
    )
    assert (
        "grant_submissions/funding_sprint_20260709/source_attachments/"
        "PROJECT_ARGOS_SOW_OFFICIAL_SOURCE_RECEIPT_2026-07-28.json"
        in workflow
    )
    assert "evidence/opportunity/csdr_deadline_gate_2026-07-27.json" in workflow
    assert "evidence/opportunity/nsf_26_510_deadline_gate_2026-07-27.json" in workflow
    assert "evidence/opportunity/official_status_events_2026-07-27.json" in workflow
    assert "permissions:\n  contents: read" in workflow
