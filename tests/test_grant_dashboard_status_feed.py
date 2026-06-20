from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GRANT_DASHBOARD_STATUS_FEED.py"


def load_module():
    spec = importlib.util.spec_from_file_location("grant_dashboard_status_feed", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_dashboard_feed_exposes_acquisition_without_overclaiming():
    module = load_module()
    feed = module.build_feed()

    assert feed["schema"] == "grant_dashboard_status_feed_v1"
    assert feed["summary"]["local_blockers"] == 0
    assert feed["summary"]["portal_user_blockers"] > 0
    assert feed["summary"]["submitted_by_feed"] == 0

    harbor = feed["harbor"]
    acquisition = harbor["ais_acquisition"]
    assert acquisition["posture"] == "PUBLIC_AIS_RAW_ACQUIRED_HASHED_PROFILED"
    assert acquisition["source_url"].startswith("https://")
    assert "raw_file_path" not in acquisition
    assert acquisition["raw_file_sha256"]
    assert acquisition["sample_rows"] == 10000
    assert "does not prove HarborSentinel performance" in acquisition["claim_boundary"]
    assert harbor["ais_heldout_splits"]["posture"] == "PUBLIC_AIS_HELDOUT_SPLITS_FROZEN"
    assert harbor["ais_heldout_splits"]["development_rows"] == 50000
    assert harbor["ais_heldout_splits"]["validation_rows"] == 50000
    assert harbor["public_ais_gate"]["posture"] == "PUBLIC_AIS_SINGLE_LANE_GATE_READY"
    assert harbor["public_ais_gate"]["overlap_mmsi"] >= 100
    assert "does not establish HarborSentinel detection performance" in harbor["public_ais_gate"]["claim_boundary"]
    assert any("No grant is marked submitted" in item for item in feed["claim_boundaries"])


def test_builder_velocity_is_bounded_artifact_metric():
    module = load_module()
    feed = module.build_feed()
    velocity = feed["builder_velocity"]

    assert velocity["artifact_count"] >= 4
    assert velocity["per_hour"] >= 0
    assert "not a model benchmark" in velocity["measurement_boundary"]
    assert "revenue claim" in feed["priority_cards"][3]["sub"]
