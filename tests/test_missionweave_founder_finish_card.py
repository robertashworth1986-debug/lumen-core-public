from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_MISSIONWEAVE_FOUNDER_FINISH_CARD.py"
OUT_JSON = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_FOUNDER_FINISH_CARD_2026-07-21.json"
)
OUT_MD = OUT_JSON.with_suffix(".md")


def load_module():
    spec = importlib.util.spec_from_file_location(
        "missionweave_founder_finish_card", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def stable_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest().upper()


def tracked_as_of_utc() -> str:
    return json.loads(OUT_JSON.read_text(encoding="utf-8"))["generated_utc"]


def test_finish_card_matches_current_fail_closed_missionweave_truth():
    module = load_module()
    payload = module.build_card(as_of_utc=tracked_as_of_utc())

    assert payload["schema"] == "lumencore.missionweave_founder_finish_card.v1"
    assert payload["status"] == "FOUNDER_ACTION_REQUIRED_NOT_SUBMISSION_READY"
    assert payload["topic"] == "DLA26BZ03-NV011"
    assert payload["current_truth"]["passed_gate_count"] == 35
    assert payload["current_truth"]["open_gate_count"] == 15
    assert payload["current_truth"]["required_gate_count"] == 50
    assert payload["current_truth"]["submission_ready_for_human_click"] is False
    assert payload["current_truth"]["portal_submission_observed"] is False
    assert payload["deadline"]["deadline_passed"] is False
    assert payload["deadline"]["seconds_remaining"] > 0
    assert payload["start_here"]["title"].startswith("Submit the JCP")
    assert payload["start_here"]["url"].startswith("https://www.public.dacs.dla.mil/")


def test_finish_card_covers_every_open_gate_once_and_preserves_human_boundaries():
    module = load_module()
    payload = module.build_card(as_of_utc=tracked_as_of_utc())

    flattened = [
        gate_id
        for step in payload["ordered_founder_steps"]
        for gate_id in step["open_gates"]
    ]
    assert len(payload["ordered_founder_steps"]) == 7
    assert len(flattened) == len(set(flattened)) == 15
    assert set(flattened) == set(payload["current_truth"]["unresolved_gates"])
    assert payload["controls"]["builder_can_click_final_submit"] is False
    assert payload["controls"]["builder_can_certify_legal_facts"] is False
    assert payload["controls"]["builder_can_send_duplicate_followup"] is False
    assert payload["controls"]["action_time_approval_required"] is True
    assert payload["controls"]["approval_max_age_seconds"] == 900
    assert payload["controls"]["preview_max_age_seconds"] == 1800
    assert "--confirm-entity-match" in payload["jcp_receipt_capture_command_template"]
    assert "--confirm-corporate-review" in payload["jcp_receipt_capture_command_template"]

    lifecycle_gates = [
        gate_id
        for stage in payload["operator_focus"]["lifecycle_stages"]
        for gate_id in stage["open_gates"]
    ]
    assert len(lifecycle_gates) == len(set(lifecycle_gates)) == 15
    assert set(lifecycle_gates) == set(payload["current_truth"]["unresolved_gates"])
    assert [
        stage["open_gate_count"]
        for stage in payload["operator_focus"]["lifecycle_stages"]
    ] == [8, 2, 5]
    assert [
        stage["title"] for stage in payload["operator_focus"]["lifecycle_stages"]
    ] == ["Do now", "Bound the pre-award position", "Do last"]


def test_finish_card_records_no_duplicate_email_state_and_source_hashes():
    module = load_module()
    payload = module.build_card(as_of_utc=tracked_as_of_utc())

    outreach = payload["outreach_control"]
    assert outreach["no_email_send_due"] is True
    assert outreach["missionweave_action_state"] == "FOLLOWUP_LIMIT_REACHED_NO_SEND"
    assert outreach["recorded_proactive_send_count"] == 1
    assert outreach["routing_integrity_exception_count"] == 1
    assert len(payload["source_integrity"]["gate_canonical_text_sha256"]) == 64
    assert len(payload["source_integrity"]["queue_canonical_text_sha256"]) == 64
    assert payload["source_integrity"]["gate_source_checks_pass"] is True


def test_source_locks_are_portable_across_line_endings(tmp_path):
    module = load_module()
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    lf.write_bytes(b'{\n  "value": 1\n}\n')
    crlf.write_bytes(b'{\r\n  "value": 1\r\n}\r\n')

    assert module.sha256_file(lf) != module.sha256_file(crlf)
    assert module.sha256_canonical_text(lf) == module.sha256_canonical_text(crlf)


def test_finish_card_self_hash_and_rendered_operator_language_are_current():
    module = load_module()
    payload = module.build_card(as_of_utc=tracked_as_of_utc())
    unhashed = dict(payload)
    recorded = unhashed.pop("card_sha256")
    rendered = module.render_markdown(payload)

    assert stable_hash(unhashed) == recorded
    assert "35/50 passed; 15 open" in rendered
    assert "official JCP portal" in rendered
    assert "Do not certify or click final submit" in rendered
    assert "Additional email due now: **false**" in rendered
    assert "one-time code" in rendered
    assert "CAPTURE_MISSIONWEAVE_JCP_EVIDENCE.py" in rendered
    assert "CMMC And TCP Decision Support" in rendered
    assert rendered.index("## What To Do Now") < rendered.index("## Do These In Order")
    assert "**Do now**: 8 open" in rendered
    assert "APPLICABILITY_UNRESOLVED" in rendered
    assert "during contracting negotiation" in rendered
    assert "does not prove JCP approval" in rendered


def test_tracked_finish_card_rebuilds_exactly_from_recorded_timestamp():
    module = load_module()
    tracked = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    rebuilt = module.build_card(as_of_utc=tracked["generated_utc"])

    assert rebuilt == tracked
    assert module.render_markdown(rebuilt) == OUT_MD.read_text(encoding="utf-8")
