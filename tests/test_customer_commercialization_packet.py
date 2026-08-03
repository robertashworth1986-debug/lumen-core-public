from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CUSTOMER_COMMERCIALIZATION_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("customer_commercialization_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_customer_commercialization_packet_preserves_current_reviewer_block():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    source_register = json.loads(
        (
            ROOT
            / "out"
            / "ops"
            / "measured_source_evidence_register_latest.json"
        ).read_text(encoding="utf-8")
    )["summary"]

    assert payload["schema"] == "customer_commercialization_packet_v1"
    assert payload["status"] == "CUSTOMER_COMMERCIALIZATION_PACKET_BLOCKED"
    assert summary["customer_segment_count"] == 5
    assert summary["offer_count"] == 5
    assert summary["buyer_proof_check_count"] == 8
    assert summary["traction_lane_count"] >= 15
    assert summary["reviewer_gate_clear"] is False
    assert summary["unsafe_secret_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert summary["registry_enabled_sources"] == (
        source_register["registry_enabled_sources"]
    )
    assert summary["registry_measured_sources"] == (
        source_register["registry_measured_sources"]
    )
    assert summary["current_probe_measured_sources"] == (
        source_register["current_probe_measured_sources"]
    )
    assert summary["human_terms_required"] is True
    assert len(payload["customer_commercialization_sha256"]) == 64


def test_customer_commercialization_packet_names_customers_and_offers():
    module = load_module()
    payload = module.build_payload()
    segment_ids = {row["segment_id"] for row in payload["customer_cards"]}
    offer_ids = {row["offer_id"] for row in payload["offers"]}

    assert segment_ids == {
        "agency_program_reviewer",
        "technical_validation_owner",
        "venture_builder_or_investor",
        "pilot_partner",
        "ip_or_compliance_reviewer",
    }
    assert offer_ids == {
        "reviewer_proof_sprint",
        "paid_replay_scope",
        "agency_submission_factory",
        "proof_portal_subscription",
        "partner_diligence_room",
    }
    assert payload["business_model"]["first_revenue_motion"].startswith("Paid reviewer proof sprint")
    assert "proof-to-pilot infrastructure" in payload["executive_summary"]


def test_customer_commercialization_packet_blocks_unapproved_actions_and_claims():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert summary["external_send_allowed_without_human"] is False
    assert summary["schedule_allowed_without_human"] is False
    assert summary["final_submission_allowed_without_human"] is False
    assert summary["pricing_commitment_allowed_without_human"] is False
    assert summary["private_file_share_allowed_without_human"] is False
    assert summary["partnership_claimed"] is False
    assert summary["investment_claimed"] is False
    assert summary["award_claimed"] is False
    assert summary["paying_customer_claimed"] is False
    assert summary["customer_result_claimed"] is False
    assert summary["production_deployment_claimed"] is False
    assert all(row["present"] for row in payload["evidence_artifacts"])
    assert "Customer Commercialization Packet" in rendered
    assert "External send without human: `false`" in rendered
    assert "api_key" not in lowered
    assert "client_secret" not in lowered
    assert "refresh_token" not in lowered
    assert "password" not in lowered
