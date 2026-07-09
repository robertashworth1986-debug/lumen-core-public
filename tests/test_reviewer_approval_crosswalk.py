from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_REVIEWER_APPROVAL_CROSSWALK.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reviewer_approval_crosswalk", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_crosswalk_is_post_sam_and_maps_core_reviewer_questions():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "reviewer_approval_crosswalk_v1"
    assert payload["status"] == "REVIEWER_APPROVAL_CROSSWALK_READY_POST_SAM"
    assert payload["summary"]["sam_registration_submitted"] is True
    assert payload["summary"]["sam_confirmation_email_received"] is True
    assert payload["summary"]["same_day_federal_email_push_count"] == 2
    assert payload["summary"]["approval_question_count"] >= 7
    assert payload["summary"]["missing_source_control_count"] == 0
    assert payload["summary"]["all_primary_artifacts_present"] is True
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert payload["summary"]["legal_or_ip_action_allowed_without_human"] is False
    assert payload["summary"]["live_trading_allowed"] is False
    assert len(payload["approval_crosswalk_sha256"]) == 64


def test_crosswalk_rows_have_artifacts_hashes_and_boundaries():
    module = load_module()
    payload = module.build_payload()
    rows = {row["decision_id"]: row for row in payload["approval_rows"]}

    expected_ids = {
        "federal_identity_and_sam",
        "fundable_product_shape",
        "technical_validation_spine",
        "ip_and_claim_defense",
        "governance_and_safety",
        "near_term_funding_traction",
        "data_room_and_mirror_custody",
    }
    assert expected_ids.issubset(rows)
    assert "submitted-confirmation" in rows["federal_identity_and_sam"]["answer"]
    assert "not legal advice" in rows["ip_and_claim_defense"]["claim_boundary"].lower()
    assert "not field validation" in rows["technical_validation_spine"]["claim_boundary"].lower()
    assert rows["governance_and_safety"]["metrics"]["live_trading_allowed"] is False

    for row in payload["approval_rows"]:
        assert row["all_primary_artifacts_present"] is True
        assert len(row["approval_row_sha256"]) == 64
        assert row["remaining_gate"]
        assert row["claim_boundary"]
        for artifact in row["artifact_status"]:
            assert artifact["present"] is True
            assert artifact["bytes"] > 0
            assert len(artifact["sha256"]) == 64


def test_rendered_crosswalk_is_public_safe_and_reviewer_fast_path():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Reviewer Approval Crosswalk" in rendered
    assert "SAM submitted: `true`" in rendered
    assert "Same-day federal email pushes: `2`" in rendered
    assert "Older packets that describe SAM as a pending renewal blocker" in rendered
    assert "No portal submit" in rendered
    assert "Open the SAM/opportunity receipt" in rendered
    assert "zoom.us" not in lowered
    assert "password" not in lowered
    assert "meeting id" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
