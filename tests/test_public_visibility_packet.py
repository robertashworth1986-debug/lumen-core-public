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
    assert any("controlled-injection benchmark" in item["claim"] for item in payload["proof_claims"])
    assert any("Geometry Championship" in item["claim"] for item in payload["proof_claims"])
    assert any("Geometry Proof Frontier" in item["claim"] for item in payload["proof_claims"])
    geometry_claims = [item for item in payload["proof_claims"] if "Geometry Championship" in item["claim"]]
    assert geometry_claims
    assert "brachistochrone_descent" in geometry_claims[0]["evidence"]
    assert "kuramoto_phase_coupling" in geometry_claims[0]["evidence"]
    assert "Live-breadth-backed geometry lanes: none" in geometry_claims[0]["evidence"]
    assert "synthetic-only generated lanes" in geometry_claims[0]["evidence"]
    assert "field" in geometry_claims[0]["boundary"]
    assert "real-dollar" in geometry_claims[0]["boundary"]
    assert "lane-specific frozen input manifests" in geometry_claims[0]["boundary"]
    assert "baselines" in geometry_claims[0]["boundary"]
    injection_claims = [
        item for item in payload["proof_claims"] if "controlled-injection benchmark" in item["claim"]
    ]
    assert injection_claims
    assert "best single-axis baseline" in injection_claims[0]["evidence"]
    assert any("controlled-injection" in item for item in payload["do_not_claim"])
    assert any("Geometry Championship" in item for item in payload["do_not_claim"])
    assert any("Geometry Proof Frontier" in item for item in payload["do_not_claim"])
    assert any("Guaranteed awards" in item for item in payload["do_not_claim"])
    assert payload["source_backed_artifacts"]["geometry_championship_bridge"].endswith(".json")
    assert payload["source_backed_artifacts"]["geometry_proof_frontier_board"].endswith(".json")
    frontier_claims = [item for item in payload["proof_claims"] if "Geometry Proof Frontier" in item["claim"]]
    assert frontier_claims
    assert "brachistochrone_descent" in frontier_claims[0]["evidence"]
    assert "crack_propagation_paths" in frontier_claims[0]["evidence"]
    assert "Ready for live geometry claim: False" in frontier_claims[0]["boundary"]
    assert "real-dollar" in frontier_claims[0]["boundary"]
    assert payload["geometry_frontier_summary"]["generated_benchmark_champion"]["family"] == "brachistochrone_descent"
    assert "not equity" in payload["lumenstock_boundary"]


def test_goal_prompt_prioritizes_proof_over_hype():
    module = load_module()
    payload = module.build_payload()
    prompt = payload["outreach_copy"]["goal_prompt"]

    assert "verifiable artifact" in prompt
    assert "Do not chase fame directly" in prompt
    assert "private submission materials" in prompt
    assert "proof surface" in prompt
