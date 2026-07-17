from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_IP_COUNSEL_DILIGENCE_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ip_counsel_diligence_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ip_packet_is_ready_and_not_legal_advice():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "ip_counsel_diligence_packet_v1"
    assert payload["status"] == "IP_COUNSEL_DILIGENCE_READY_HUMAN_COUNSEL_REQUIRED"
    assert payload["summary"]["official_source_count"] >= 5
    assert payload["summary"]["invention_family_count"] == 6
    assert payload["summary"]["reviewer_gate_clear"] is True
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert payload["summary"]["legal_advice_claimed"] is False
    assert payload["summary"]["patent_grant_claimed"] is False
    assert payload["summary"]["clearance_to_operate_claimed"] is False
    assert payload["summary"]["licensed_counsel_required"] is True
    assert payload["summary"]["human_patent_center_check_required"] is True
    assert payload["summary"]["patent_deadline_control_status"] == (
        "PAYMENT_ACKNOWLEDGEMENT_ONLY_OFFICIAL_DOCKET_REQUIRED"
    )
    assert payload["summary"]["us_prosecution_deadline_verified"] is False
    assert payload["summary"]["foreign_pct_priority_review_time_sensitive"] is True
    assert payload["patent_deadline_control"]["private_paths_published"] is False
    assert payload["patent_deadline_control"]["application_identifier_published"] is False


def test_ip_packet_cites_official_uspto_routes():
    module = load_module()
    payload = module.build_payload()
    urls = {row["url"] for row in payload["official_sources"]}

    assert any("incomplete-or-missing-information" in url for url in urls)
    assert any("utility-patent" in url for url in urls)
    assert any("checking-application-status" in url for url in urls)
    assert any("patent-pro-bono-program" in url for url in urls)
    assert any(url.startswith("https://www.wipo.int/") for url in urls)
    assert all(
        url.startswith("https://www.uspto.gov/")
        or url.startswith("https://www.wipo.int/")
        for url in urls
    )


def test_ip_packet_evidence_sources_are_present_and_hashed():
    module = load_module()
    payload = module.build_payload()
    evidence_by_name = {Path(row["path"]).name: row for row in payload["evidence_status"]}

    for name in [
        "IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md",
        "PATENT_LEGAL_RESCUE_PACKET_2026-06-20.md",
        "REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
        "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        "HUMAN_ACTION_DOCKET_2026-07-09.md",
        "LINKEDIN_UNIVERSE_PROFILE_PACKET_2026-07-09.md",
        "DATA_ROOM_MANIFEST_2026-07-09.md",
        "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        "PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json",
        "PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.md",
    ]:
        assert evidence_by_name[name]["present"] is True
        assert evidence_by_name[name]["bytes"] > 0
        assert len(evidence_by_name[name]["sha256"]) == 64


def test_ip_packet_keeps_actions_human_and_counsel_gated():
    module = load_module()
    payload = module.build_payload()
    gate = payload["human_gate"]
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert gate["patent_center_access_allowed_without_human"] is False
    assert gate["legal_filing_allowed_without_human"] is False
    assert gate["public_disclosure_expansion_allowed_without_human"] is False
    assert gate["investor_ip_claim_expansion_allowed_without_human"] is False
    assert "licensed patent counsel" in gate["rule"]
    assert "not legal advice" in lowered
    assert "patent grant claimed: `false`" in lowered
    assert "clearance to operate claimed: `false`" in lowered
