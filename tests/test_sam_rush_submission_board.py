from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_SAM_RUSH_SUBMISSION_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sam_rush_submission_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_current_payload(module):
    return module.build_payload(
        scan_date=date(2026, 7, 29),
        generated_utc="2026-07-29T09:00:00Z",
    )


def test_sam_rush_board_ranks_submit_ready_lanes_and_blocks_final_submit():
    module = load_module()
    payload = build_current_payload(module)

    assert payload["schema"] == "sam_rush_submission_board_v1"
    assert payload["status"] == (
        "SAM_RUSH_BOARD_HISTORICAL_SOURCE_REVERIFY_REQUIRED"
    )
    assert payload["summary"]["opportunity_count"] == 10
    assert payload["summary"]["submit_ready_human_gate_count"] == 0
    assert payload["summary"]["source_reverify_required_count"] == 3
    assert payload["summary"]["deadline_open_count"] == 3
    assert payload["summary"]["expired_closed_count"] == 7
    assert payload["summary"]["source_fresh"] is False
    assert payload["summary"]["partner_or_watch_count"] == 0
    assert payload["summary"]["no_bid_count"] == 0
    assert payload["summary"]["human_action_required"] is True
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert payload["summary"]["pricing_allowed_without_human"] is False
    assert payload["summary"]["legal_certification_allowed_without_human"] is False

    assert payload["submit_ready_human_gate"] == []
    reverify_ids = {
        row["solicitation_number"]
        for row in payload["source_reverify_required"]
    }
    assert reverify_ids == {
        "693JJ326R000012",
        "W912HZ26SC005",
        "W900KK-26-R-0001",
    }
    expired_ids = {
        row["solicitation_number"] for row in payload["expired_closed"]
    }
    assert "80TECH26RFI0020" in expired_ids
    assert "15BCMS26Q70000005" in expired_ids


def test_sam_rush_board_has_source_urls_hashes_and_safe_rendering():
    module = load_module()
    payload = build_current_payload(module)
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
        assert row["actionable"] is False
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
        assert "HISTORICAL_DRAFT_REVERIFY_BEFORE_USE" in rendered
        assert "Final submission without human: `false`" in rendered
        assert "Pricing/certification without human: `false`" in rendered
        assert filename in rendered


def test_deadline_boundary_never_leaves_notice_actionable_at_or_after_close():
    module = load_module()
    before = module.build_payload(
        scan_date=date(2026, 7, 17),
        generated_utc="2026-07-17T20:59:59Z",
    )
    at_close = module.build_payload(
        scan_date=date(2026, 7, 17),
        generated_utc="2026-07-17T21:00:00Z",
    )
    after = module.build_payload(
        scan_date=date(2026, 7, 18),
        generated_utc="2026-07-18T00:00:00Z",
    )

    def nasa(payload):
        return next(
            row
            for row in payload["opportunities"]
            if row["solicitation_number"] == "80TECH26RFI0020"
        )

    assert nasa(before)["deadline_state"] == "OPEN"
    assert nasa(before)["action_bucket"] == "source_reverify_required"
    assert nasa(before)["actionable"] is False
    assert nasa(at_close)["deadline_state"] == "EXPIRED"
    assert nasa(at_close)["action_bucket"] == "expired_closed"
    assert nasa(at_close)["actionable"] is False
    assert nasa(after)["deadline_state"] == "EXPIRED"
    assert nasa(after)["actionable"] is False
