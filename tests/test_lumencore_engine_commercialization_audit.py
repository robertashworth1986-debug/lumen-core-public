from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_LUMENCORE_ENGINE_COMMERCIALIZATION_AUDIT.py"
CONFIG_PATH = ROOT / "config" / "lumencore_engine_commercialization_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("engine_commercialization_audit", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_has_exactly_fifteen_unique_engines():
    payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    ids = [engine["id"] for engine in payload["engines"]]
    assert len(ids) == 15
    assert len(set(ids)) == 15


def test_audit_is_fail_closed_for_subscription_readiness():
    module = load_module()
    config = module.read_json(CONFIG_PATH)
    payload = module.build_payload(config, "2026-07-28T02:45:00+00:00")

    assert payload["summary"]["engine_count"] == 15
    assert payload["summary"]["subscription_ready_count"] == 0
    assert all(
        engine["commercial_posture"] in {"design_partner_ready", "research_only", "concept_only"}
        for engine in payload["engines"]
    )


def test_design_partner_lanes_have_offer_acceptance_and_boundary():
    module = load_module()
    config = module.read_json(CONFIG_PATH)
    payload = module.build_payload(config, "2026-07-28T02:45:00+00:00")
    lanes = [
        engine for engine in payload["engines"] if engine["commercial_posture"] == "design_partner_ready"
    ]

    assert lanes
    for engine in lanes:
        assert engine["bounded_offer"].strip()
        assert engine["payer"].strip()
        assert engine["acceptance_gate"].strip()
        assert engine["claim_boundary"].strip()


def test_observed_maturity_uses_present_files_not_email_language():
    module = load_module()
    config = module.read_json(CONFIG_PATH)
    payload = module.build_payload(config, "2026-07-28T02:45:00+00:00")
    by_id = {engine["id"]: engine for engine in payload["engines"]}

    assert by_id["lumengov_grant_factory"]["observed_maturity"] == "evidence_backed_candidate"
    assert by_id["echoform_identity_engine"]["observed_maturity"] == "concept_only"
    assert by_id["smart_city_node_engine"]["observed_maturity"] == "concept_only"
    assert by_id["luma_xr_command_room"]["evidence"]["public_surface"][0]["exists"] is False


def test_markdown_never_calls_an_engine_subscription_ready():
    module = load_module()
    config = module.read_json(CONFIG_PATH)
    payload = module.build_payload(config, "2026-07-28T02:45:00+00:00")
    markdown = module.render_markdown(payload)

    assert "Subscription-ready lanes: `0`" in markdown
    assert "guaranteed awards" not in markdown.lower()
    assert "15 finished products" in markdown
