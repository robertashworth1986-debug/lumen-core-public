from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CURRENT_REVIEWER_FRONT_DOOR.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "current_reviewer_front_door",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_current_reviewer_front_door_is_fail_closed_and_hash_backed():
    module = load_module()
    payload = module.build_payload("2026-07-29T10:20:00Z")

    assert payload["schema"] == "lumencore.current_reviewer_front_door.v1"
    assert payload["status"] == (
        "CURRENT_REVIEWER_FRONT_DOOR_READY_HUMAN_RELEASE_REQUIRED"
    )
    summary = payload["summary"]
    assert summary["registered_family_count"] == 140
    assert summary["implementation_present_count"] == 35
    assert summary["implementation_required_count"] == 105
    assert summary["executed_direct_source_baseline_comparison_count"] == 126
    assert summary["individual_comparison_global_holm_positive_count"] == 0
    assert summary["market_signal_candidate_count"] == 4
    assert summary["market_signal_source_count"] == 3
    assert summary["market_signal_comparison_count"] == 48
    assert summary["market_signal_inference_insufficient_count"] == 48
    assert summary["market_signal_global_holm_positive_count"] == 0
    assert summary["market_signal_promoted_candidate_count"] == 0
    assert summary["market_signal_panel_pair_count"] == 12
    assert summary["market_signal_panel_comparison_count"] == 16
    assert summary["market_signal_panel_global_holm_positive_count"] == 1
    assert (
        summary["market_signal_panel_all_baseline_mean_winner_count"]
        == 0
    )
    assert summary["market_signal_panel_promoted_candidate_count"] == 0
    assert summary["promoted_champion_count"] == 0
    assert summary["eligible_future_observation_count"] == 0
    assert summary["artifact_count"] == 13
    assert summary["external_release_authorized_count"] == 0
    assert summary["human_release_review_required"] is True

    for row in payload["artifacts"]:
        path = ROOT / row["path"]
        assert path.is_file()
        assert row["sha256"] == module.sha256_file(path)
        assert row["bytes"] == path.stat().st_size
        assert row["external_release_authorized"] is False

    controls = payload["release_controls"]
    assert controls["external_release_authorized"] is False
    assert controls["autonomous_send_or_submit_allowed"] is False
    assert len(payload["front_door_sha256"]) == 64
    assert payload["outputs"]["public_artifact_manifest"].startswith(
        "docs/receipts/"
    )

    manifest = module.build_public_artifact_manifest(payload)
    assert manifest["schema"] == (
        "lumencore.current_reviewer_public_artifact_manifest.v1"
    )
    assert manifest["artifact_count"] == 4
    assert manifest["external_release_authorized"] is False
    assert manifest["network_action_performed"] is False
    assert {row["id"] for row in manifest["artifacts"]} == set(
        module.PUBLIC_ARTIFACT_IDS
    )
    assert all(len(row["sha256"]) == 64 for row in manifest["artifacts"])
    assert len(manifest["manifest_sha256"]) == 64


def test_current_reviewer_front_door_renders_only_bounded_claims():
    module = load_module()
    payload = module.build_payload("2026-07-29T10:20:00Z")
    rendered = module.render_markdown(payload)

    assert "# LumenCore Current Reviewer Front Door" in rendered
    assert "LumenCore_Federal_Capability_Statement_CURRENT.pdf" in rendered
    assert "LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pptx" in rendered
    assert "LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pdf" in rendered
    assert "LumenCore_Source_Native_Benchmark_Whitepaper_CURRENT.pdf" in rendered
    assert "Global Holm-positive comparisons: `0`" in rendered
    assert "Market-signal comparisons: `48`" in rendered
    assert "Market-signal inferentially insufficient: `48`" in rendered
    assert "Kraken-panel pairs: `12`" in rendered
    assert "Kraken-panel comparisons: `16`" in rendered
    assert "Kraken-panel exploratory Holm positives: `1`" in rendered
    assert "Kraken-panel all-baseline mean winners: `0`" in rendered
    assert "Promoted champions: `0`" in rendered
    assert "Eligible future observations: `0`" in rendered
    assert "External release authorized: `false`" in rendered
    assert "does not establish model superiority, alpha, field performance" in rendered
