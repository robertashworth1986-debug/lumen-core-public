from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_INVESTOR_ONE_PAGER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("investor_one_pager", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_investor_brief_is_claim_bounded_and_hash_sealed():
    module = load_module()
    payload = module.build_payload(
        datetime(2026, 7, 29, 12, tzinfo=timezone.utc)
    )

    assert payload["schema"] == "lumen.investor_one_pager/v2"
    assert payload["external_share_ready"] is False
    assert payload["recipient_selected"] is False
    assert payload["economics"]["valuation_stated"] is False
    assert payload["economics"]["savings_stated"] is False
    assert payload["scientific_evidence"]["performance_claim_allowed"] is False
    assert payload["scientific_evidence"][
        "internal_source_native_promotion_gate_pass_count"
    ] == 0
    assert payload["pilot"]["buyer_selected"] is False
    assert payload["pilot"]["pricing_approved"] is False
    assert payload["government_readiness"]["external_action_count"] == 0
    assert payload["all_canonical_sources_present"] is True

    unsealed = dict(payload)
    receipt = unsealed.pop("brief_payload_sha256")
    assert module.stable_hash(unsealed) == receipt


def test_investor_brief_does_not_render_legacy_value_or_autonomy_claims():
    module = load_module()
    payload = module.build_payload(
        datetime(2026, 7, 29, 12, tzinfo=timezone.utc)
    )
    rendered = module.render_markdown(payload)
    blocked_phrases = (
        "$52",
        "valuation proxy",
        "live multi-asset",
        "government-grade",
        "grade-A lock",
        "autonomous grant lane",
        "annual preserved-value",
        "ready to scale from paper",
    )

    assert all(phrase.lower() not in rendered.lower() for phrase in blocked_phrases)
    assert "DRAFT ONLY" in rendered
    assert "Promotion gates passed: `0`" in rendered
    assert "The present scientific contribution is the governed comparison" in rendered


def test_investor_brief_fails_closed_when_a_canonical_source_is_missing(
    tmp_path,
):
    module = load_module()
    module.PRODUCT_PRIORITY = tmp_path / "missing.json"

    payload = module.build_payload(
        datetime(2026, 7, 29, 12, tzinfo=timezone.utc)
    )

    assert payload["status"] == "BLOCKED_MISSING_CANONICAL_EVIDENCE"
    assert payload["external_share_ready"] is False
    assert payload["all_canonical_sources_present"] is False
