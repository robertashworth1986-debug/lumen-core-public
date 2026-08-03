from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PAID_PILOT_OUTREACH_QUEUE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("paid_pilot_outreach_queue", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_fixture_payload(module):
    legacy_source = {
        "schema": "proof_to_pilot_control_room_v2",
        "top_cards": [
            {
                "family_id": "legacy_geometry_candidate",
                "commercial_stage": "manual_paid_pilot_outreach_ready",
                "recipient_email": "must-not-propagate@example.test",
                "claimed_savings": 99_999_999,
            }
        ],
    }
    return module.build_payload(
        control_room=legacy_source,
        generated_utc="2026-07-29T12:00:00+00:00",
    )


def test_v2_queue_is_local_protocol_review_scoping_only():
    module = load_module()
    payload = build_fixture_payload(module)
    summary = payload["summary"]

    assert payload["schema"] == "paid_pilot_outreach_queue_v2"
    assert payload["inputs"]["source_schema_observed"] == "proof_to_pilot_control_room_v2"
    assert payload["inputs"]["source_used_for_performance_claims"] is False
    assert payload["inputs"]["source_used_for_target_or_recipient_selection"] is False

    assert summary["queue_count"] == 2
    assert summary["local_scope_count"] == 2
    assert summary["performance_champion_count"] == 0
    assert summary["recipient_selected_count"] == 0
    assert summary["send_ready_target_count"] == 0
    assert summary["manual_outreach_ready_count"] == 0
    assert summary["manual_reviewed_outreach_allowed"] is False
    assert summary["bulk_outreach_allowed"] is False
    assert summary["geometry_performance_claim_inherited"] is False
    assert len(summary["queue_chain_sha256"]) == 64


def test_service_ranges_are_exact_and_not_roi_value_or_savings():
    module = load_module()
    payload = build_fixture_payload(module)
    pricing = payload["service_pricing_boundary"]
    rows = {row["service_id"]: row for row in payload["queue"]}

    assert pricing["protocol_review_usd"] == {"min": 2500, "max": 7500}
    assert pricing["optional_benchmark_implementation_usd"] == {
        "min": 7500,
        "max": 25000,
    }
    assert pricing["prices_are_service_fees_only"] is True
    assert pricing["prices_are_roi_or_value"] is False
    assert pricing["prices_are_savings_estimates"] is False

    assert rows["protocol_review"]["price_min"] == 2500
    assert rows["protocol_review"]["price_max"] == 7500
    assert rows["optional_benchmark_implementation"]["price_min"] == 7500
    assert rows["optional_benchmark_implementation"]["price_max"] == 25000

    for row in rows.values():
        assert row["roi_or_value_claim_allowed"] is False
        assert row["savings_claim_allowed"] is False
        assert row["field_validation_claim_allowed"] is False
        assert row["performance_champion"] is False
        assert row["geometry_performance_claim_inherited"] is False
        assert "not ROI, savings, enterprise value" in row["pricing_boundary"]


def test_every_external_action_and_claim_gate_fails_closed():
    module = load_module()
    payload = build_fixture_payload(module)
    gate = payload["external_action_gate"]

    assert gate["state"] == "blocked_local_scoping_only"
    assert gate["outreach_allowed"] is False
    assert gate["manual_outreach_allowed"] is False
    assert gate["bulk_outreach_allowed"] is False
    assert gate["send_without_action_time_approval_allowed"] is False
    assert gate["current_official_source_verification_required"] is True
    assert gate["full_thread_and_sent_mail_duplicate_check_required"] is True
    assert gate["exact_recipient_and_authority_verification_required"] is True
    assert gate["scope_claims_and_pricing_revalidation_required"] is True
    assert gate["data_rights_and_baselines_confirmation_required"] is True
    assert gate["action_time_human_approval_required"] is True

    for row in payload["queue"]:
        assert row["target_selected"] is False
        assert row["target_organization"] == ""
        assert row["recipient_selected"] is False
        assert row["recipient_name"] == ""
        assert row["recipient_email"] == ""
        assert row["send_ready"] is False
        assert row["outreach_allowed"] is False
        assert row["bulk_or_manual_outreach_allowed"] is False
        assert len(row["row_sha256"]) == 64


def test_legacy_card_claims_and_recipient_do_not_propagate():
    module = load_module()
    payload = build_fixture_payload(module)
    serialized = json.dumps(payload, sort_keys=True).lower()

    assert "legacy_geometry_candidate" not in serialized
    assert "must-not-propagate" not in serialized
    assert "99999999" not in serialized
    assert "positive frozen replay windows" not in serialized
    assert "current champion" not in serialized
    assert "send-ready" in serialized
    assert "does not identify a performance champion" in serialized


def test_writes_can_be_fully_redirected_to_temporary_outputs(tmp_path):
    module = load_module()
    payload = build_fixture_payload(module)
    json_path = tmp_path / "queue.json"
    csv_path = tmp_path / "queue.csv"
    markdown_path = tmp_path / "queue.md"
    dashboard_path = tmp_path / "dashboard.json"

    module.write_outputs(
        payload,
        json_path=json_path,
        csv_path=csv_path,
        markdown_path=markdown_path,
        dashboard_json_path=dashboard_path,
    )

    assert json.loads(json_path.read_text(encoding="utf-8")) == payload
    assert json.loads(dashboard_path.read_text(encoding="utf-8")) == payload

    csv_text = csv_path.read_text(encoding="utf-8")
    rendered = markdown_path.read_text(encoding="utf-8")
    assert "local_protocol_review_scope" in csv_text
    assert "local_optional_benchmark_implementation_scope" in csv_text
    assert "Local Protocol-Review Scoping Queue" in rendered
    assert "Performance champions: `0`" in rendered
    assert "Recipients selected: `0`" in rendered
    assert "Send-ready targets: `0`" in rendered
    assert "Manual outreach allowed: `false`" in rendered
    assert "Bulk outreach allowed: `false`" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "Savings claim allowed: `false`" in rendered
    assert "action-time human approval" in rendered.lower()
    assert "complete thread and Sent mail" in rendered

    lowered = (csv_text + rendered).lower()
    assert "must-not-propagate" not in lowered
    assert ("api" + "_key") not in lowered
    assert "client" + "_sec" + "ret" not in lowered
