from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_VALIDATION_OUTREACH_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("field_validation_outreach_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_field_validation_outreach_board_keeps_live_breadth_distinction():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    snapshot = payload["proof_snapshot"]

    assert payload["schema"] == "field_validation_outreach_board_v1"
    assert summary["champion_replay_source_system_count"] >= 4
    assert summary["broader_measured_provider_count"] > summary["champion_replay_source_system_count"]
    assert summary["manifest_unique_source_count"] >= summary["broader_measured_provider_count"]
    assert summary["manifest_ready_for_benchmark_row_count"] >= 100
    assert snapshot["champion_wins"] == 24
    assert snapshot["champion_holdouts"] == 24
    assert "not automatically part of the champion win" in snapshot["claim_boundary"]
    assert len(payload["outreach_board_sha256"]) == 64


def test_field_validation_outreach_targets_include_nashville_tennessee_and_funders():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    targets = payload["ranked_targets"]
    organizations = " ".join(row["organization"] for row in targets)

    assert summary["target_count"] >= 10
    assert summary["nashville_or_tennessee_targets"] >= 8
    assert summary["field_validation_unlockers"] >= 3
    assert summary["funder_or_connector_targets"] >= 4
    assert "OpenPOWER AI" in organizations
    assert "EPRI" in organizations
    assert "EPB" in organizations
    assert "TVA" in organizations
    assert "LaunchTN" in organizations
    assert "Nashville Entrepreneur Center" in organizations
    assert "Vanderbilt" in organizations
    assert "Tennessee Tech" in organizations


def test_field_validation_outreach_send_gate_blocks_bulk_and_overclaiming():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    gate = payload["send_gate"]

    assert summary["manual_reviewed_outreach_allowed"] is True
    assert summary["send_without_user_review_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["contact_scraping_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_claim_allowed"] is False

    assert gate["requires_exact_recipient"] is True
    assert gate["requires_physical_mailing_address"] is True
    assert gate["requires_opt_out_language"] is True
    assert gate["requires_final_human_approval_at_send_time"] is True

    dumped = json.dumps(payload).lower()
    assert "guaranteed savings" not in dumped
    assert "guaranteed alpha" not in dumped
    assert "field validated" not in dumped
    assert "i am not claiming field validation or realized savings yet" in dumped
    assert "buyer-authorized replay" in dumped or "buyer-authorized field replay" in dumped


def test_field_validation_outreach_markdown_is_ready_for_manual_action():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Field Validation Outreach Board" in rendered
    assert "Live Breadth Correction" in rendered
    assert "Broader measured providers" in rendered
    assert "Dollar Posture" in rendered
    assert "Claimable today" in rendered
    assert "OpenPOWER AI" in rendered
    assert "Send without user review allowed: `false`" in rendered
    assert "Bulk email allowed: `false`" in rendered
    assert "Draft Emails" in rendered
    assert "Request for buyer-authorized field replay" in rendered
    assert "held-out data" in rendered
    assert "economic conversion" in rendered
