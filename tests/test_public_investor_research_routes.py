from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"


def load_module():
    if str(CODE) not in sys.path:
        sys.path.insert(0, str(CODE))
    return importlib.import_module("opportunities_api")


def test_public_alpha_edge_route_uses_claim_bounded_source_native_status():
    module = load_module()
    payload = module.alpha_edge_latest()

    assert payload["schema"] == "claim_bounded_research_edge_status.v1"
    assert payload["status"] == "NO_PROMOTED_CHAMPION"
    assert payload["legacy_alpha_edge_artifact_suppressed"] is True
    assert payload["promotion_gate_pass_count"] == 0
    assert payload["performance_claim_allowed"] is False
    assert payload["trading_alpha_claim_allowed"] is False
    assert payload["live_execution_allowed"] is False


def test_public_grant_candidate_route_is_review_only():
    module = load_module()
    payload = module.grants_live_fill_latest()

    assert payload["route_name_deprecated"] is True
    assert payload["action_allowed"] is False
    assert payload["submission_authorized"] is False
    assert payload["live_fill"]["autofill_packet_ready"] is False
    assert payload["live_fill"]["submission_authorized"] is False
    assert payload["live_fill"]["autofill_payload"] == {}


def test_public_investor_pitch_remains_internal_draft():
    module = load_module()
    payload = module.investor_pitch_latest()

    assert payload["external_share_ready"] is False
    assert payload["recipient_selected"] is False
    assert payload["pitch"]["legacy_value_inputs_suppressed"] is True
    assert "$" not in payload["pitch"]["full_script"]
