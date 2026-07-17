from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EVTIT_TECHNICAL_SPRINT_SCOPE_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("evtit_technical_sprint_scope_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_evtit_sprint_scope_is_ready_but_human_terms_gated():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "evtit_technical_sprint_scope_packet_v1"
    assert payload["status"] == "EVTIT_TECHNICAL_SPRINT_SCOPE_INTERNAL_ONLY_MONITOR_NO_SEND"
    assert summary["workstream_count"] == 6
    assert summary["milestone_count"] == 5
    assert summary["reviewer_gate_clear"] is True
    assert summary["unsafe_secret_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert summary["registry_enabled_sources"] == 29
    assert summary["registry_measured_sources"] == 25
    assert summary["current_probe_measured_sources"] == 23
    assert summary["human_terms_required"] is True
    assert summary["monitor_only"] is True
    assert summary["do_not_duplicate_send"] is True
    assert payload["lane"]["status"] == "OUTBOUND_FOLLOWUPS_SENT_NO_INBOUND_REPLY"
    assert len(payload["evtit_sprint_scope_sha256"]) == 64


def test_evtit_sprint_scope_contains_expected_workstreams_and_outputs():
    module = load_module()
    payload = module.build_payload()
    workstreams = {row["id"]: row for row in payload["workstreams"]}

    expected = {
        "proof_portal_front_door",
        "replay_runner_manifest",
        "measured_source_register_ui",
        "pilot_onboarding_path",
        "api_reliability_cost_controls",
        "grant_investor_packet_automation",
    }
    assert set(workstreams) == expected
    assert "source-register" in workstreams["measured_source_register_ui"]["evidence_output"]
    assert "run manifest" in workstreams["replay_runner_manifest"]["evidence_output"]
    assert payload["positioning"]["decision_question"].startswith("What internal sprint scope")
    assert payload["positioning"]["best_next_meeting"].startswith("None scheduled")


def test_evtit_sprint_scope_blocks_terms_sends_and_claims():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert summary["external_send_allowed_without_human"] is False
    assert summary["schedule_allowed_without_human"] is False
    assert summary["share_private_files_allowed_without_human"] is False
    assert summary["equity_or_services_terms_allowed_without_human"] is False
    assert summary["partnership_claimed"] is False
    assert summary["investment_claimed"] is False
    assert summary["services_award_claimed"] is False
    assert summary["customer_outcome_value_claimed"] is False
    assert summary["production_deployment_claimed"] is False
    assert "EVTit Technical Sprint Scope Packet" in rendered
    assert "Production deployment claimed: `false`" in rendered
    assert "Monitor only: `true`" in rendered
    assert "Do not duplicate send: `true`" in rendered
    assert "api_key" not in lowered
    assert "client_secret" not in lowered
    assert "refresh_token" not in lowered
    assert "password" not in lowered
