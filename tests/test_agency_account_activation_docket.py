from __future__ import annotations

import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_AGENCY_ACCOUNT_ACTIVATION_DOCKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("agency_account_activation_docket", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_agency_account_activation_docket_is_ready_and_human_gated():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "agency_account_activation_docket_v1"
    assert payload["status"] == "AGENCY_ACCOUNT_ACTIVATION_READY_HUMAN_PORTAL_REQUIRED"
    assert summary["activation_item_count"] == 8
    assert summary["human_required_item_count"] == 8
    assert summary["ready_item_count"] >= 1
    assert summary["blocked_item_count"] >= 5
    assert summary["blocked_readiness_count"] == 6
    assert summary["reviewer_packaging_gate_clear"] is True
    assert summary["submission_argument_gate_clear"] is False
    assert summary["unsafe_secret_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert summary["portal_action_allowed_without_human"] is False
    assert summary["credential_entry_allowed_without_human"] is False
    assert summary["certification_allowed_without_human"] is False
    assert summary["final_submission_allowed_without_human"] is False
    assert summary["external_send_allowed_without_human"] is False
    assert summary["calendar_or_meeting_invite_allowed_without_human"] is False
    assert summary["live_trading_allowed"] is False
    assert len(payload["activation_docket_sha256"]) == 64


def test_activation_rows_cover_federal_account_stack():
    module = load_module()
    payload = module.build_payload()
    rows = {row["id"]: row for row in payload["activation_rows"]}

    expected = {
        "sam_entity_renewal",
        "grants_gov_profile_aor",
        "research_gov_nsf_pitch",
        "dsip_firm_pin_topic_access",
        "dod_cyber_cmmc_scope",
        "ip_patent_center_counsel",
        "submission_signer_pricing_authority",
        "secure_artifact_custody",
    }
    assert expected == set(rows)

    for row in rows.values():
        assert row["human_required"] is True
        assert row["portal_action_allowed_without_human"] is False
        assert row["credential_entry_allowed_without_human"] is False
        assert row["certification_allowed_without_human"] is False
        assert row["final_submit_allowed_without_human"] is False
        assert row["external_share_allowed_without_human"] is False
        assert len(row["row_sha256"]) == 64
        assert row["next_human_actions"]
        assert row["blocks"]


def test_local_readiness_summarizes_private_fields_safely():
    module = load_module()
    payload = module.build_payload()
    readiness = payload["local_readiness"]

    assert readiness["company_profile_status"] == "verification_required"
    assert readiness["uei_present_locally"] is True
    assert readiness["cage_present_locally"] is True
    assert readiness["sam_portal_capture_present"] is True
    assert readiness["sam_portal_active_registration_observed"] is True
    assert readiness["sam_expiration_date_observed"] == "2026-08-30"
    assert readiness["blocked_readiness_count"] == 6
    assert "grants_gov_account_verified" in readiness["blocked_readiness_flags"]
    assert "research_gov_account_verified" in readiness["blocked_readiness_flags"]
    assert "aor_authority_verified" in readiness["blocked_readiness_flags"]
    assert "dsip_account_verified" in readiness["blocked_readiness_flags"]
    assert "dod_compliance_verified" in readiness["blocked_readiness_flags"]


def test_official_sources_and_evidence_chain_are_present():
    module = load_module()
    payload = module.build_payload()
    urls = " ".join(source["url"] for source in payload["official_sources"])

    assert "https://sam.gov/entity-registration" in urls
    assert "https://www.grants.gov/applicants/applicant-registration" in urls
    assert "https://seedfund.nsf.gov/project-pitch/" in urls
    assert "https://www.defensesbirsttr.mil/SBIR-STTR/Opportunities/" in urls
    assert "https://dodcio.defense.gov/CMMC/" in urls
    assert "https://patentcenter.uspto.gov/" in urls

    for source in payload["official_sources"]:
        assert source["label"]
        assert source["activation_use"]

    for row in payload["evidence_status"]:
        assert row["present"] is True
        assert row["bytes"] > 0
        assert len(row["sha256"]) == 64


def test_rendered_activation_docket_is_public_safe_and_human_gated():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Agency Account Activation Docket" in rendered
    assert "Certification without human: `false`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "Credential entry without human: `false`" in rendered
    assert "Portal action without human: `false`" in rendered
    assert "UEI present locally: `true`" in rendered
    assert "CAGE present locally: `true`" in rendered

    private_or_sensitive_markers = [
        "SQY2XW71ZM51",
        "14TM8",
        "2613 Paddle Wheel",
        "zoom.us",
        "meeting id",
        "password",
        "one tap mobile",
        "private key",
        "refresh_token",
        "client_secret",
        "api_key",
        "sk-",
        "xox",
    ]
    for marker in private_or_sensitive_markers:
        assert marker.lower() not in lowered
    assert re.search(r"\b\d{2}-\d{7}\b", rendered) is None
    assert re.search(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b", rendered) is None
    assert re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", rendered, re.I) is None
