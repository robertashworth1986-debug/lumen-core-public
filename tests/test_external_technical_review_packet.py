from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EXTERNAL_TECHNICAL_REVIEW_PACKET.py"
CONFIG = ROOT / "config" / "external_technical_review_packet_v1.json"
JSON_OUT = ROOT / "dashboard" / "data" / "external_technical_review_packet.json"
MD_OUT = ROOT / "docs" / "EXTERNAL_TECHNICAL_REVIEW_PACKET_2026-07-28.md"


def load_module():
    spec = importlib.util.spec_from_file_location("external_review_packet", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_packet_is_no_send_and_no_duplicate():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))

    assert payload["status"] == "MEETING_PREP_READY_NO_DUPLICATE_SEND"
    assert payload["meeting"]["invite_state"] == "ACCEPTED"
    assert payload["meeting"]["selected_template_id"] == (
        "NO_DUPLICATE_MEETING_PREP"
    )
    assert payload["controls"]["builder_can_send_email"] is False
    assert payload["controls"]["builder_can_create_calendar_event"] is False
    assert payload["controls"]["duplicate_invite_prohibited"] is True
    assert payload["summary"]["duplicate_invite_blocked"] is True


def test_every_evidence_asset_exists_and_is_hash_bound():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))

    assert payload["summary"]["evidence_asset_count"] == 7
    for row in payload["evidence_assets"]:
        assert len(row["sha256"]) == 64
        assert row["bytes"] > 0
        if row["required_status"]:
            assert row["observed_status"] == row["required_status"]
            assert row["claim_boundary"]


def test_public_snapshot_discloses_the_degraded_dynamic_endpoint():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))
    by_label = {row["label"]: row for row in payload["public_surfaces"]}

    assert payload["summary"]["public_surface_count"] == 5
    assert payload["summary"]["degraded_surface_count"] == 1
    assert by_label["Dynamic health endpoint"]["observed_http_status"] == 502
    assert by_label["Dynamic health endpoint"]["demo"] is False
    assert all(row["url"].startswith("https://") for row in by_label.values())


def test_packet_keeps_draft_and_external_evidence_boundaries_explicit():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))
    markdown = module.render_markdown(payload)

    assert payload["draft_references"][0]["state"] == "DRAFT_PR_NOT_MERGED"
    assert "not independent external validation" in markdown
    assert "not main-branch state" in markdown
    assert "does not establish attendance" in markdown
    assert "Do not send another reply or invitation" in markdown
    assert "meeting link" not in markdown.lower()
    assert "recipient_name" not in markdown


def test_reviewer_questions_force_buyer_baseline_metric_and_negative_result_path():
    module = load_module()
    payload = module.build_payload(module.read_json(CONFIG))
    questions = " ".join(payload["reviewer_questions"]).lower()
    next_steps = " ".join(payload["bounded_next_steps"]).lower()

    assert "buyer" in questions
    assert "baseline" in questions
    assert "acceptance metric" in questions
    assert "independent evaluator" in questions
    assert "no fit" in next_steps


def test_written_outputs_match_the_builder():
    module = load_module()
    expected = module.build_payload(module.read_json(CONFIG))

    assert json.loads(JSON_OUT.read_text(encoding="utf-8")) == expected
    assert MD_OUT.read_text(encoding="utf-8") == module.render_markdown(expected)
