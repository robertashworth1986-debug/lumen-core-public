from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FROZEN_DELTA_BUYER_OUTREACH.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_frozen_delta_buyer_outreach", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frozen_delta_outreach_keeps_claim_and_send_gates_closed():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "frozen_delta_buyer_outreach.v1"
    assert payload["current_truth"]["ready_for_real_dollar_claim"] is False
    assert payload["current_truth"]["field_validation"] is False
    assert payload["current_truth"]["kraken_live_execution_allowed"] is False
    assert payload["send_gate"]["mass_email_allowed"] is False
    assert payload["send_gate"]["send_without_user_review"] is False
    assert "guaranteed savings" in " ".join(payload["blocked_claims"]).lower()
    assert "paid pilot" in payload["buyer_safe_positioning"].lower()


def test_frozen_delta_outreach_templates_are_pilot_not_blast_language():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert "Do not mass email" in rendered
    assert "paid pilot" in rendered.lower()
    assert "field validation: `false`" in rendered.lower()
    assert "ready for real-dollar claim: `false`" in rendered.lower()
    assert "guaranteed value" in rendered
