from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_REVIEWER_DILIGENCE_QA_MATRIX.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reviewer_diligence_qa_matrix", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_diligence_qa_matrix_builds_evidence_backed_answers():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "reviewer_diligence_qa_matrix_v1"
    assert payload["status"] == "REVIEWER_DILIGENCE_QA_READY"
    assert payload["summary"]["qa_count"] >= 12
    assert payload["summary"]["missing_evidence_count"] == 0
    assert payload["summary"]["decision_lane_count"] == 15
    assert payload["summary"]["authority_lane_count"] == 15
    assert payload["summary"]["docket_lane_count"] == 15
    assert payload["summary"]["reviewer_gate_clear"] is True
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert payload["summary"]["all_final_actions_blocked_without_human"] is True
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert payload["summary"]["live_trading_allowed"] is False
    assert len(payload["qa_matrix_sha256"]) == 64


def test_diligence_rows_have_boundaries_hashes_and_present_evidence():
    module = load_module()
    payload = module.build_payload()
    questions = {row["question"]: row for row in payload["qa_rows"]}

    assert "What traction is strongest right now?" in questions
    assert "How is IP and patent-risk handled?" in questions
    assert "How is autonomous quant or AI-risk controlled?" in questions
    assert "What remains unproven or still needs external validation?" in questions

    for row in payload["qa_rows"]:
        assert row["answer"]
        assert row["decision_use"]
        assert row["claim_boundary"]
        assert row["human_gate"]
        assert row["missing_evidence_count"] == 0
        assert len(row["qa_row_sha256"]) == 64
        for evidence in row["evidence_status"]:
            assert evidence["present"] is True
            assert evidence["bytes"] > 0
            assert len(evidence["sha256"]) == 64


def test_rendered_diligence_qa_is_public_safe_and_blocks_final_action():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Reviewer Diligence Q&A Matrix" in rendered
    assert "All final actions blocked without human: `true`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "Live trading allowed: `false`" in rendered
    assert "risk-free" in lowered
    assert module.scan_sensitive_text("risk-free") == []
    assert module.scan_sensitive_text("sk-" + "a" * 16)
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
