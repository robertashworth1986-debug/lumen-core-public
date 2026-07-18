from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PRODUCT_LANE_PRIORITY_ENGINE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("product_lane_priority_engine", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_priority_engine_ranks_sellable_grant_lane_first():
    module = load_module()
    payload = module.build_payload(datetime(2026, 7, 18, tzinfo=timezone.utc))

    assert payload["schema"] == "product_lane_priority_engine_v1"
    assert sum(payload["weights"].values()) == 100
    assert payload["ranking"][0]["id"] == "prooflock_opportunity_ops"
    assert payload["recommendation"]["technical_wedge"] == "prooflock_evidence_router_api"
    assert payload["ranking"][0]["evidence_coverage"] == 1.0
    assert len(payload["product_lane_priority_sha256"]) == 64
    unsealed = dict(payload)
    receipt = unsealed.pop("product_lane_priority_sha256")
    assert module.stable_hash(unsealed) == receipt


def test_priority_engine_blocks_broken_latest_run_from_headline_use():
    module = load_module()
    payload = module.build_payload(datetime(2026, 7, 18, tzinfo=timezone.utc))
    audits = {row["run_id"]: row for row in payload["evidence_audit"]["runs"]}

    latest = audits["20260526T050639Z"]
    assert latest["all_models_complete"] is False
    assert latest["model_failures"]["i_sarima"]["invalid_rows"] == 1118
    assert latest["reviewer_use"] == "blocked_from_comparative_headline"
    assert payload["evidence_audit"]["best_bounded_exploratory_run"] == "20260505T121657Z"
    assert payload["evidence_audit"]["best_bounded_exploratory_dataset_count"] == 673


def test_priority_engine_exposes_router_and_feed_gates():
    module = load_module()
    module.HEALTHCARE_FEED = module.MINDWISE_DEMO_FEED
    payload = module.build_payload(datetime(2026, 7, 18, 12, tzinfo=timezone.utc))

    assert "full series" in payload["evidence_audit"]["router_risk"]
    assert "train-only" in payload["evidence_audit"]["router_risk"]
    feed = payload["evidence_audit"]["healthcare_feed"]
    assert feed["status"] == "fresh"
    assert feed["freshness_label_allowed"] is True
    assert feed["eligibility_label_allowed"] is False
    assert feed["submission_ready_label_allowed"] is False
    assert "organizational eligibility from relevance scores alone" in payload["claim_controls"]["blocked_now"]
    assert "prospective router superiority until train-only features pass" in payload["claim_controls"]["blocked_now"]


def test_priority_engine_blocks_stale_feed_language():
    module = load_module()
    module.HEALTHCARE_FEED = module.MINDWISE_DEMO_FEED
    payload = module.build_payload(datetime(2026, 7, 20, 12, tzinfo=timezone.utc))

    feed = payload["evidence_audit"]["healthcare_feed"]
    assert feed["status"] == "stale_or_unverifiable"
    assert feed["freshness_label_allowed"] is False
    assert "current-feed language until the candidate feed is refreshed within the freshness SLA" in payload["claim_controls"]["blocked_now"]


def test_mindwise_pilot_keeps_final_submission_human_controlled():
    module = load_module()
    payload = module.build_payload(datetime(2026, 7, 18, tzinfo=timezone.utc))
    pilot = payload["mindwise_pilot"]

    assert "no PHI" in pilot["scope_boundary"]
    assert len(pilot["acceptance_metrics"]) == 6
    assert "authorized official certifies and submits" in pilot["human_gates"]
    assert "guaranteed awards or autonomous final submission" in payload["claim_controls"]["blocked_now"]


def test_healthcare_widget_uses_review_language_and_displays_boundary():
    widget = (ROOT / "dashboard" / "js" / "luma_healthcare_grants_embed.js").read_text(encoding="utf-8")

    assert "'Immediate Submit'" not in widget
    assert "'Fast Track'" not in widget
    assert ">Open Submit Route<" not in widget
    assert ">AI Fill<" not in widget
    assert "Urgent Review" in widget
    assert "Review Official Source" in widget
    assert "Draft Workspace" in widget
    assert "Discovery candidates only" in widget
    assert "eligibility" in widget


def test_bundle_manifest_receipts_are_complete_and_bounded():
    module = load_module()
    module.HEALTHCARE_FEED = module.MINDWISE_DEMO_FEED
    payload = module.build_payload(datetime(2026, 7, 18, 12, tzinfo=timezone.utc))
    manifest = module.build_bundle_manifest(payload)

    assert manifest["schema"] == "product_lane_priority_bundle_manifest_v1"
    assert manifest["artifact_count"] == 12
    assert manifest["all_artifacts_present"] is True
    assert all(len(item["sha256"]) == 64 for item in manifest["artifacts"])
    assert "byte identity and presence only" in manifest["boundary"]
    unsealed = dict(manifest)
    receipt = unsealed.pop("manifest_payload_sha256")
    assert module.stable_hash(unsealed) == receipt


def test_mindwise_demo_feed_is_frozen_and_claim_bounded():
    module = load_module()
    snapshot = module.build_mindwise_demo_feed()

    assert snapshot["schema"] == "mindwise_healthcare_candidate_feed_demo_v1"
    assert len(snapshot["records"]) == 6
    assert snapshot["summary"]["snapshot_records"] == 6
    assert "do not establish organizational eligibility" in snapshot["boundary"]
    unsealed = dict(snapshot)
    receipt = unsealed.pop("snapshot_payload_sha256")
    assert module.stable_hash(unsealed) == receipt
