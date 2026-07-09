from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_API_KEY_GOVERNANCE_FIREWALL.py"
API_REGISTRY = ROOT / "LamaScout" / "config" / "api_registry.yaml"


def load_module():
    spec = importlib.util.spec_from_file_location("key_governance_firewall", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_lamascout_api_registry_is_sanitized_and_deduplicated():
    registry = yaml.safe_load(API_REGISTRY.read_text(encoding="utf-8"))
    sources = registry["sources"]
    names = [source["name"] for source in sources]

    assert len(names) == len(set(names))
    assert {"youtube", "spotify", "meta"}.issubset(set(names))

    for source in sources:
        auth = source.get("auth", {}) or {}
        assert auth.get("api_key", "") == ""
        assert auth.get("client_secret", "") == ""
        assert auth.get("access_token", "") == ""
        assert auth.get("bearer_token", "") == ""
        assert source.get("access_mode")


def test_key_firewall_builds_without_secret_values_or_write_authority():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    by_name = {row["name"]: row for row in payload["lamascout_sources"]}

    assert payload["schema"] == "api_key_governance_firewall_v1"
    assert payload["status"] == "KEY_FIREWALL_READY_HUMAN_GATED"
    assert summary["registry_total_key_slots"] >= 30
    assert summary["registry_present_key_slots"] >= 1
    assert summary["lamascout_active_source_count"] >= 6
    assert summary["lamascout_inline_credential_hit_count"] == 0
    assert summary["write_or_spend_allowed_count"] == 0
    assert summary["raw_credential_values_stored"] is False
    assert summary["final_action_allowed_without_human"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["social_posting_allowed"] is False
    assert summary["ad_spend_allowed"] is False
    assert len(payload["key_firewall_sha256"]) == 64

    for name in ("youtube", "spotify", "meta"):
        assert by_name[name]["active"] is True
        assert by_name[name]["write_or_spend_allowed"] is False
        assert by_name[name]["human_action_required_for_account_mutation"] is True


def test_rendered_key_firewall_is_public_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Key Governance Firewall" in rendered
    assert "Raw credential values stored: `false`" in rendered
    assert "Social posting allowed: `false`" in rendered
    assert "Ad spend allowed: `false`" in rendered
    assert "client_secret" not in lowered
    assert "access_token:" not in lowered
    assert "bearer_token:" not in lowered
    assert "api_key:" not in lowered
    assert "private key" not in lowered
    assert "secret" not in lowered
