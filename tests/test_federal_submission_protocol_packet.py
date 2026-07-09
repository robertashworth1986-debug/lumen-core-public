from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FEDERAL_SUBMISSION_PROTOCOL_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("federal_submission_protocol_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_federal_submission_protocol_packet_is_human_gated_and_ready():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "federal_submission_protocol_packet_v1"
    assert payload["status"] == "FEDERAL_SUBMISSION_PROTOCOL_READY_HUMAN_PORTAL_REQUIRED"
    assert summary["official_source_count"] >= 10
    assert summary["protocol_gate_count"] == 7
    assert summary["reviewer_gate_clear"] is True
    assert summary["unsafe_secret_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert summary["all_final_actions_blocked_without_human"] is True
    assert summary["human_protocol_required"] is True
    assert summary["external_send_allowed_without_human"] is False
    assert summary["final_submission_allowed_without_human"] is False
    assert summary["certification_allowed_without_human"] is False
    assert summary["portal_submit_allowed_without_human"] is False
    assert summary["cui_processing_claimed"] is False
    assert summary["cmmc_status_claimed"] is False
    assert summary["award_eligibility_claimed"] is False
    assert len(payload["federal_submission_protocol_packet_sha256"]) == 64


def test_official_sources_cover_federal_submission_lanes():
    module = load_module()
    payload = module.build_payload()
    urls = " ".join(source["url"] for source in payload["official_sources"])

    assert "https://sam.gov/entity-registration" in urls
    assert "https://www.grants.gov/applicants/applicant-registration" in urls
    assert "https://www.sbir.gov/tutorials/program-basics/tutorial-2" in urls
    assert "https://www.defensesbirsttr.mil/SBIR-STTR/Opportunities/" in urls
    assert "https://www.darpa.mil/work-with-us/communities/small-business/sbir-sttr-participate" in urls
    assert "https://dodcio.defense.gov/CMMC/" in urls

    official_hosts = (
        "sam.gov",
        "grants.gov",
        "sbir.gov",
        "defensesbirsttr.mil",
        "darpa.mil",
        "dodcio.defense.gov",
    )
    for source in payload["official_sources"]:
        assert any(host in source["url"] for host in official_hosts)
        assert source["protocol_fact"]
        assert source["lumen_gate"]


def test_submission_readiness_uses_safe_company_profile_summary():
    module = load_module()
    payload = module.build_payload()
    readiness = payload["submission_readiness"]

    assert readiness["sam_gov_status"] == "verification_required"
    assert readiness["uei_present_locally"] is True
    assert readiness["cage_present_locally"] is True
    assert readiness["blocked_readiness_count"] >= 5
    assert "grants_gov_account_verified" in readiness["blocked_readiness_flags"]
    assert "aor_authority_verified" in readiness["blocked_readiness_flags"]
    assert "dsip_account_verified" in readiness["blocked_readiness_flags"]
    assert readiness["profile_source"] == "data/company_profile.json"


def test_protocol_evidence_sources_are_present_and_hash_backed():
    module = load_module()
    payload = module.build_payload()
    by_path = {row["path"]: row for row in payload["evidence_status"]}

    expected_fragments = [
        "AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
        "AGENCY_ACCOUNT_ACTIVATION_DOCKET_2026-07-09.md",
        "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        "HUMAN_ACTION_DOCKET_2026-07-09.md",
        "IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
        "AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
        "DATA_ROOM_MANIFEST_2026-07-09.md",
        "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        "data/company_profile.json",
    ]

    for fragment in expected_fragments:
        path = next(path for path in by_path if path.endswith(fragment))
        row = by_path[path]
        assert row["present"] is True
        assert row["bytes"] > 0
        assert len(row["sha256"]) == 64


def test_rendered_protocol_packet_is_public_safe_and_human_gated():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Federal Submission Protocol Packet" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "Portal submit without human: `false`" in rendered
    assert "Cybersecurity representation without human: `false`" in rendered
    assert "Award eligibility claimed: `false`" in rendered
    assert "Local SAM.gov status: `verification_required`" in rendered

    risky_claims = [
        "field validated",
        "realized savings",
        "guaranteed award",
        "guaranteed returns",
        "certified assurance",
        "cmmc certified",
        "nuclear licensing authority",
        "medical efficacy",
        "airworthiness",
        "operational government deployment",
        "live profit",
        "risk-free",
        "autonomous trading system ready",
        "freedom to operate",
        "patented",
    ]
    sensitive_markers = [
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
    for phrase in risky_claims + sensitive_markers:
        assert phrase not in lowered
