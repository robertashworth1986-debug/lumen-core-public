from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


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
    assert summary["public_artifact_upstream_dependency_fresh_count"] == 4
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
    assert manifest["all_upstream_dependencies_fresh"] is True
    assert manifest["external_release_authorized"] is False
    assert manifest["network_action_performed"] is False
    assert {row["id"] for row in manifest["artifacts"]} == set(
        module.PUBLIC_ARTIFACT_IDS
    )
    assert all(len(row["sha256"]) == 64 for row in manifest["artifacts"])
    by_id = {row["id"]: row for row in manifest["artifacts"]}
    assert by_id["current_evidence_to_pilot_deck"]["local_only"] is True
    assert (
        by_id["current_evidence_to_pilot_deck"]["publication_state"]
        == "LOCAL_ONLY_SOURCE_NOT_PUBLICATION_CANDIDATE"
    )
    for artifact_id in (
        "current_capability_statement",
        "current_evidence_to_pilot_deck_pdf",
        "current_source_native_whitepaper",
    ):
        row = by_id[artifact_id]
        assert row["release_item_id"]
        assert row["immutable_target_path"].startswith("dashboard/evidence/")
        assert row["public_url"].startswith("https://lumen-core.ai/evidence/")
        assert row["publication_state"] in {
            "LOCAL_TARGET_ABSENT_NOT_PUBLISHED",
            "LOCAL_STAGE_PRESENT_PUBLIC_URL_UNVERIFIED",
        }
        assert row["upstream_dependency_fresh"] is True
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


def test_front_door_rejects_stale_transitive_governance_dependency(
    tmp_path: Path,
):
    module = load_module()
    pitch = json.loads(module.PITCH_GOVERNANCE.read_text(encoding="utf-8"))
    pitch["current_deck"]["dependencies"][0]["sha256"] = "0" * 64
    stale_pitch = tmp_path / "pitch_deck_governance_latest.json"
    stale_pitch.write_text(json.dumps(pitch), encoding="utf-8")
    module.PITCH_GOVERNANCE = stale_pitch

    with pytest.raises(
        module.FrontDoorError,
        match="stale governance dependencies",
    ):
        module.build_payload("2026-07-29T10:20:00Z")
