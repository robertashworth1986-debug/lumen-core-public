from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PUBLIC_VISIBILITY_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("public_visibility_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_visibility_packet_is_public_safe_and_source_backed():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "public_visibility_packet_v1"
    assert payload["author"]["name"] == "Robert Ashworth"
    assert payload["author"]["public_repository"].startswith("https://github.com/")
    assert len(payload["primary_sources"]) >= 5
    assert any("NOAA" in source["name"] for source in payload["primary_sources"])
    assert any("DARPA DICE" in source["name"] for source in payload["primary_sources"])
    assert any("HarborSentinel now has public AIS" in item["claim"] for item in payload["proof_claims"])
    assert any("Guaranteed awards" in item for item in payload["do_not_claim"])
    assert "not equity" in payload["lumenstock_boundary"]


def test_goal_prompt_prioritizes_proof_over_hype():
    module = load_module()
    payload = module.build_payload()
    prompt = payload["outreach_copy"]["goal_prompt"]

    assert "verifiable artifact" in prompt
    assert "Do not chase fame directly" in prompt
    assert "private submission materials" in prompt
