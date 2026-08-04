from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PUBLICATION_APPROVAL_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("publication_approval_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_packet_binds_the_exact_current_public_review_set():
    module = load_module()
    payload = module.build_payload("2026-08-02T18:00:00Z")

    assert payload["schema"] == "lumencore.publication_approval_packet.v4"
    assert payload["status"] == "CURRENT_ARTIFACT_SET_HASH_BOUND_RELEASE_BLOCKED"
    assert payload["publication_policy"]["external_release_authorized"] is False
    assert payload["publication_policy"]["vps_mutation_allowed"] is False
    assert payload["publication_policy"]["no_auto_posting"] is True
    assert payload["release_readiness"]["public_release_allowed"] is False
    assert payload["human_action_gate"]["approval_state"] == "NOT_APPROVED"
    assert payload["human_action_gate"]["bound_artifact_set_sha256"] is None
    assert len(payload["artifact_set_sha256"]) == 64
    assert len(payload["packet_payload_sha256"]) == 64

    by_id = {row["artifact_id"]: row for row in payload["release_artifacts"]}
    assert set(by_id) == {
        "current_capability_statement",
        "current_evidence_to_pilot_deck_pdf",
        "current_source_native_whitepaper",
    }
    for row in by_id.values():
        source = ROOT / row["source_path"]
        assert source.is_file()
        assert row["source_sha256"] == module.sha256_file(source)
        assert row["source_bytes"] == source.stat().st_size
        assert row["binding_state"] == "HASH_MATCHED_CURRENT"
        assert row["immutable_target_path"].startswith("dashboard/evidence/")
        assert row["public_url"].startswith("https://lumen-core.ai/evidence/")
        assert row["external_release_authorized"] is False

    assert "github" not in payload
    assert "geometry-coverage-audit-20260623" not in module.render_markdown(payload)


def test_public_copy_reports_negative_results_and_no_promotion():
    module = load_module()
    payload = module.build_payload("2026-08-02T18:00:00Z")
    snapshot = payload["evidence_snapshot"]
    rendered = module.render_markdown(payload).lower()

    assert snapshot["registered_family_count"] == 140
    assert snapshot["implementation_present_count"] == 35
    assert snapshot["executed_comparison_count"] == 126
    assert snapshot["primary_global_holm_positive_count"] == 0
    assert snapshot["panel_exploratory_global_holm_positive_count"] == 1
    assert snapshot["panel_complete_baseline_winner_count"] == 0
    assert snapshot["promotion_count"] == 0
    assert snapshot["eligible_future_observation_count"] == 0
    assert snapshot["performance_claim_allowed"] is False

    linkedin = payload["public_copy_drafts"]["linkedin_post"]["copy"]
    assert "140 candidate families" in linkedin
    assert "35 current implementations" in linkedin
    assert "126 source-native comparisons" in linkedin
    assert "0 complete-baseline winners" in linkedin
    assert "0 promotions" in linkedin
    assert "awaits future observations" in linkedin
    assert "not a claim of external validation" in rendered


def test_packet_rejects_a_stale_release_policy_binding(tmp_path, monkeypatch):
    module = load_module()
    policy = json.loads(module.PUBLIC_RELEASE_POLICY.read_text(encoding="utf-8"))
    target = next(
        row
        for row in policy["allowlist"]
        if row["id"] == "source_native_benchmark_whitepaper_pdf"
    )
    target["expected_source_sha256"] = "0" * 64
    stale = tmp_path / "stale_policy.json"
    stale.write_text(json.dumps(policy), encoding="utf-8")
    monkeypatch.setattr(module, "PUBLIC_RELEASE_POLICY", stale)

    with pytest.raises(module.PublicationPacketError, match="source binding is stale"):
        module.build_payload("2026-08-02T18:00:00Z")


def test_packet_rejects_a_rebound_front_door(tmp_path, monkeypatch):
    module = load_module()
    front = json.loads(module.FRONT_DOOR_JSON.read_text(encoding="utf-8"))
    front["status"] = "REBOUND_WITHOUT_NEW_HASH"
    stale = tmp_path / "stale_front_door.json"
    stale.write_text(json.dumps(front), encoding="utf-8")
    monkeypatch.setattr(module, "FRONT_DOOR_JSON", stale)

    with pytest.raises(module.PublicationPacketError, match="not release-review ready"):
        module.build_payload("2026-08-02T18:00:00Z")


def test_packet_copy_excludes_secrets_and_unsupported_claims():
    module = load_module()
    payload = module.build_payload("2026-08-02T18:00:00Z")
    rendered = module.render_markdown(payload).lower()

    forbidden = [
        "guaranteed funding",
        "guaranteed profit",
        "api_key",
        "bearer ",
        "private key",
        "github_pat",
        "field validated",
        "institutional grade",
        "world best",
    ]
    for term in forbidden:
        assert term not in rendered
    assert "external release remains disabled" in rendered
    assert "action_time_human_approval_required" in rendered
    assert "private_human_unlock_receipt_required" in rendered
