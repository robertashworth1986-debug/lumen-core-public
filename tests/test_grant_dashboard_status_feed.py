from __future__ import annotations

import importlib.util
import json
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
    freshness = feed["source_freshness"]
    assert freshness["time_sensitive_source_count"] == 4
    assert freshness["fresh_source_count"] + freshness["stale_or_missing_source_count"] == 4
    assert feed["summary"]["current_opportunity_status_allowed"] is freshness[
        "time_sensitive_sources_fresh"
    ]
    if freshness["time_sensitive_sources_fresh"]:
        assert feed["summary"]["dashboard_signal"] != "STALE_SOURCE_ABSTAIN"
        assert feed["top5_live_proof"]["current_status_allowed"] is True
    else:
        assert feed["summary"]["dashboard_signal"] == "STALE_SOURCE_ABSTAIN"
        assert feed["summary"]["ready_local_not_portal"] is False
        assert feed["top5_live_proof"]["snapshot_status"] == "HISTORICAL_STALE_ABSTAIN"
        assert feed["top5_live_proof"]["active_start_package"] == ""

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
    assert "path" not in json.dumps(harbor["ais_io_preflight"]).lower()
    injection = harbor["ais_injection_benchmark"]
    assert injection["posture"] == "PUBLIC_AIS_INJECTION_BENCHMARK_READY"
    assert injection["total_injected_segments"] > 0
    assert injection["motion_consistency_recall"] >= injection["speed_only_baseline_recall"]
    assert "operational detection performance" in injection["claim_boundary"]
    assert "path" not in json.dumps(injection).lower()
    support = feed["support_outreach"]
    assert support["available"] is True
    assert support["recommended_paid_data_now"] is False
    assert support["official_support_lanes"] >= 4
    assert any(row["site"] == "DARPA BAAT" for row in support["sign_in_queue"])
    assert any(row["site"] == "PIEE / SPRS" for row in support["sign_in_queue"])
    assert "does not authorize upload" in support["boundary"]
    top5 = feed["top5_live_proof"]
    assert top5["available"] is True
    assert top5["proposal_specific_live_proof_count"] == 2
    assert top5["proposal_specific_live_proof_total"] == 5
    if top5["current_status_allowed"]:
        assert top5["active_start_package"] == "DICE"
        assert top5["closest_action_gate_portal"] == "DSIP"
    else:
        assert top5["active_start_package"] == ""
        assert top5["closest_action_gate_portal"] == ""
    assert top5["ready_for_any_final_submit"] is False
    assert any(row["status"] == "DISCARD_NO_SUBMIT" for row in top5["discarded_workspaces"])
    assert any(card["key"] == "Live Proof Gate" and card["value"] == "2/5" for card in feed["priority_cards"])
    assert any("No grant is marked submitted" in item for item in feed["claim_boundaries"])
    assert any("proposal-specific live-proof gate" in item for item in feed["claim_boundaries"])


def test_builder_velocity_is_bounded_artifact_metric():
    module = load_module()
    feed = module.build_feed()
    velocity = feed["builder_velocity"]

    assert velocity["artifact_count"] >= 4
    assert velocity["per_hour"] >= 0
    assert "not a model benchmark" in velocity["measurement_boundary"]
    assert "revenue claim" in feed["priority_cards"][3]["sub"]


def test_io_preflight_summary_does_not_publish_private_paths(tmp_path):
    module = load_module()
    preflight = {
        "schema": "harbor_ais_io_preflight_v1",
        "posture": "PUBLIC_AIS_SPLIT_IO_BLOCKED",
        "timeout_seconds": 3,
        "sample_bytes": 4096,
        "full_hash": False,
        "summary": {
            "required_files": 2,
            "required_ok": 0,
            "all_required_ok": False,
            "any_timeout": True,
        },
        "probes": [
            {
                "label": "development",
                "path": "G:/Private/HarborSentinel/development.csv",
                "expected_bytes": 123,
                "status": "timeout",
                "ok": False,
                "timeout_seconds": 3,
            }
        ],
        "next_gate": "Run the benchmark only after split I/O is ready.",
        "claim_boundary": "This preflight does not establish HarborSentinel detection performance.",
    }
    path = tmp_path / "preflight.json"
    path.write_text(json.dumps(preflight), encoding="utf-8")
    module.HARBOR_AIS_IO_PREFLIGHT_JSON = path

    feed = module.build_feed()
    safe = feed["harbor"]["ais_io_preflight"]
    serialized = json.dumps(safe)

    assert safe["posture"] == "PUBLIC_AIS_SPLIT_IO_BLOCKED"
    assert safe["required_ok"] == 0
    assert safe["any_timeout"] is True
    assert "G:/Private" not in serialized
    assert '"path"' not in serialized
