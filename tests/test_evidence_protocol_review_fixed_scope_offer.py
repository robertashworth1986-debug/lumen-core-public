from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_EVIDENCE_PROTOCOL_REVIEW_FIXED_SCOPE_OFFER.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "evidence_protocol_review_fixed_scope_offer", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_offer_is_fixed_scope_and_within_existing_bounded_range():
    module = load_module()
    payload = module.build_payload("2026-07-30T05:30:00Z")
    terms = payload["commercial_terms"]
    limits = payload["scope_limits"]

    assert payload["product_id"] == "prooflock_evidence_protocol_review_sprint_v1"
    assert terms["candidate_fixed_fee_usd"] == 3500
    assert terms["candidate_deposit_usd"] + terms["candidate_balance_usd"] == 3500
    assert (
        terms["existing_supported_service_range_usd"]["low"]
        <= terms["candidate_fixed_fee_usd"]
        <= terms["existing_supported_service_range_usd"]["high"]
    )
    assert terms["duration_business_days"] == 10
    assert limits["buyer_workflows"] == 1
    assert limits["authorized_source_systems"] == 1
    assert limits["production_access"] is False
    assert len(payload["deliverables"]) == 6
    assert len(payload["payload_sha256"]) == 64


def test_offer_does_not_convert_local_protocol_evidence_into_performance_claims():
    module = load_module()
    payload = module.build_payload("2026-07-30T05:30:00Z")
    controls = payload["controls"]
    source = payload["source_evidence"]

    assert source["protocol_review_packet_count"] >= 1
    assert source["internal_performance_champion_count"] == 0
    assert source["pilot_ready_count"] == 0
    assert source["paid_evaluation_offer_allowed"] is True
    assert controls["external_send_allowed"] is False
    assert controls["bulk_outreach_allowed"] is False
    assert controls["performance_claim_allowed"] is False
    assert controls["savings_claim_allowed"] is False
    assert controls["field_validation_claim_allowed"] is False
    assert "not a customer result" in payload["claim_boundary"].lower()


def test_published_offer_matches_stable_rebuild():
    module = load_module()
    module.check_outputs()
    published = json.loads(module.OUT_JSON.read_text(encoding="utf-8"))
    dashboard = json.loads(
        module.OUT_DASHBOARD_JSON.read_text(encoding="utf-8")
    )
    assert published["payload_sha256"] == module.stable_json_sha256(
        {key: value for key, value in published.items() if key != "payload_sha256"}
    )
    assert dashboard == published
    assert module.OUT_DASHBOARD_JSON.as_posix().endswith(
        "dashboard/data/evidence_protocol_review_fixed_scope_offer.json"
    )
