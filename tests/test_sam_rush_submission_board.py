from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_SAM_RUSH_SUBMISSION_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sam_rush_submission_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sam_rush_board_ranks_submit_ready_lanes_and_blocks_final_submit():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "sam_rush_submission_board_v1"
    assert payload["status"] == "SAM_RUSH_BOARD_READY_HUMAN_SUBMIT_REQUIRED"
    assert payload["summary"]["opportunity_count"] == 10
    assert payload["summary"]["submit_ready_human_gate_count"] == 4
    assert payload["summary"]["partner_or_watch_count"] == 4
    assert payload["summary"]["no_bid_count"] == 2
    assert payload["summary"]["human_action_required"] is True
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert payload["summary"]["pricing_allowed_without_human"] is False
    assert payload["summary"]["legal_certification_allowed_without_human"] is False

    ready_ids = {row["solicitation_number"] for row in payload["submit_ready_human_gate"]}
    assert "693JJ326R000012" in ready_ids
    assert "80TECH26RFI0020" in ready_ids
    assert "W912HZ26SC005" in ready_ids
    assert "15BCMS26Q70000005" in ready_ids


def test_sam_rush_board_has_source_urls_hashes_and_safe_rendering():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "SAM Rush Submission Board" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "Legal certification without human: `false`" in rendered
    assert "https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view" in rendered
    assert "https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/" in rendered
    assert len(payload["board_sha256"]) == 64

    for row in payload["opportunities"]:
        assert row["human_gate_required"] is True
        assert row["external_send_allowed_without_human"] is False
        assert row["final_submission_allowed_without_human"] is False
        assert row["pricing_allowed_without_human"] is False
        assert len(row["opportunity_sha256"]) == 64

    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered


def test_submission_stubs_are_human_gated_and_named_for_packages():
    module = load_module()

    assert len(module.STUBS) == 6
    expected_stubs = {
        "FHWA_TSMO_PHASE1_SUBMISSION_STUB_2026-07-10.md",
        "NASA_DATA_CENTER_RFI_RESPONSE_STUB_2026-07-10.md",
        "ERDC_SOVEREIGN_DEFENSE_CLOUD_CSO_CONCEPT_STUB_2026-07-10.md",
        "DOJ_BOP_MEDICAL_CLAIMS_ANALYSIS_QUOTE_STUB_2026-07-10.md",
        "USTDA_INDO_PACIFIC_DIGITAL_INFRA_SCOPING_STUB_2026-07-10.md",
        "ARMY_AIDP_RFI4_PARTNER_NOTE_STUB_2026-07-10.md",
    }
    assert expected_stubs == set(module.STUBS)

    for filename, stub in module.STUBS.items():
        rendered = module.render_stub(filename, stub)
        assert "DRAFT_READY_HUMAN_REVIEW_REQUIRED" in rendered
        assert "Final submission without human: `false`" in rendered
        assert "Pricing/certification without human: `false`" in rendered
        assert filename in rendered
