from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
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
    assert payload["evidence_contract_version"] == "typed_evidence_contract_v1"
    assert payload["ranking"][0]["evidence_coverage"] == payload["ranking"][0]["validated_evidence_coverage"]
    assert payload["ranking"][0]["buyer_readiness_gate"]["passed"] is False
    assert len(payload["product_lane_priority_sha256"]) == 64
    unsealed = dict(payload)
    receipt = unsealed.pop("product_lane_priority_sha256")
    assert module.stable_hash(unsealed) == receipt


def test_typed_evidence_contracts_fail_closed(tmp_path):
    module = load_module()
    module.ROOT = tmp_path
    at = datetime(2026, 7, 29, 12, tzinfo=timezone.utc)

    valid = tmp_path / "valid.json"
    valid.write_text(
        json.dumps(
            {
                "schema": "evidence.v1",
                "generated_utc": "2026-07-29T11:00:00Z",
                "rows": [],
            }
        ),
        encoding="utf-8",
    )
    stale = tmp_path / "stale.json"
    stale.write_text(
        json.dumps(
            {
                "schema": "evidence.v1",
                "generated_utc": "2026-07-27T11:00:00Z",
                "rows": [],
            }
        ),
        encoding="utf-8",
    )
    wrong_schema = tmp_path / "wrong.json"
    wrong_schema.write_text(
        json.dumps(
            {
                "schema": "evidence.v0",
                "generated_utc": "2026-07-29T11:00:00Z",
                "rows": [],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "empty.json").write_bytes(b"")

    base = {
        "required": True,
        "kind": "test_receipt",
        "min_bytes": 2,
        "expected_schema": "evidence.v1",
        "required_keys": ["generated_utc", "rows"],
        "max_age_hours": 24,
        "claim_scope": "Fixture proves only the typed evidence validator behavior.",
    }
    checks = {
        name: module.validate_evidence_contract({**base, "path": path}, at)
        for name, path in {
            "valid": "valid.json",
            "stale": "stale.json",
            "wrong_schema": "wrong.json",
            "empty": "empty.json",
            "missing": "missing.json",
        }.items()
    }

    assert checks["valid"]["valid"] is True
    assert checks["stale"]["valid"] is False
    assert "artifact_stale" in checks["stale"]["reasons"]
    assert checks["wrong_schema"]["valid"] is False
    assert "artifact_schema_mismatch" in checks["wrong_schema"]["reasons"]
    assert checks["empty"]["valid"] is False
    assert "artifact_below_min_bytes" in checks["empty"]["reasons"]
    assert checks["missing"]["valid"] is False
    assert "artifact_missing" in checks["missing"]["reasons"]

    config = {
        "weights": {"evidence": 100},
        "lanes": [
            {
                "id": "fixture",
                "name": "Fixture",
                "offer": "Fixture",
                "scores": {"evidence": 90},
                "evidence_paths": [
                    {**base, "path": path}
                    for path in (
                        "valid.json",
                        "stale.json",
                        "wrong.json",
                        "empty.json",
                        "missing.json",
                    )
                ],
                "first_validation": "External buyer validation.",
            }
        ],
    }
    lane = module.rank_lanes(config, at)[0]
    assert lane["validated_evidence_count"] == 1
    assert lane["required_evidence_count"] == 5
    assert lane["validated_evidence_coverage"] == 0.2
    assert lane["internal_evidence_gate_passed"] is False
    assert lane["buyer_readiness_gate"]["passed"] is False
    assert lane["buyer_readiness_gate"]["status"] == "blocked_internal_evidence"


def test_legacy_path_does_not_count_as_validated_evidence(tmp_path):
    module = load_module()
    module.ROOT = tmp_path
    (tmp_path / "legacy.txt").write_text("present", encoding="utf-8")

    check = module.validate_evidence_contract(
        "legacy.txt",
        datetime(2026, 7, 29, tzinfo=timezone.utc),
    )

    assert check["exists"] is True
    assert check["valid"] is False
    assert "contract_legacy_untyped" in check["reasons"]
    assert "contract_missing_claim_scope" in check["reasons"]


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
    generated = module.parse_utc_datetime(
        module.read_json(module.MINDWISE_DEMO_FEED).get("generated_utc")
    )
    assert generated is not None
    payload = module.build_payload(generated + timedelta(hours=12))

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
    generated = module.parse_utc_datetime(
        module.read_json(module.MINDWISE_DEMO_FEED).get("generated_utc")
    )
    assert generated is not None
    payload = module.build_payload(generated + timedelta(hours=48))

    feed = payload["evidence_audit"]["healthcare_feed"]
    assert feed["status"] == "stale_or_unverifiable"
    assert feed["freshness_label_allowed"] is False
    assert "current-feed language until the candidate feed is refreshed within the freshness SLA" in payload["claim_controls"]["blocked_now"]


def test_mindwise_pilot_keeps_final_submission_human_controlled():
    module = load_module()
    payload = module.build_payload(datetime(2026, 7, 18, tzinfo=timezone.utc))
    pilot = payload["mindwise_pilot"]

    assert pilot["buyer_selected"] is False
    assert pilot["buyer"] is None
    assert "non-PHI" in pilot["scope_boundary"]
    assert len(pilot["acceptance_metrics"]) == 6
    assert all(
        {"metric", "numerator", "denominator"} <= set(metric)
        for metric in pilot["acceptance_metrics"]
    )
    assert pilot["minimum_sample"]["reviewed_opportunities"] == 30
    assert pilot["minimum_sample"]["pursued_packages"] == 5
    assert pilot["pricing"]["founder_approved"] is False
    assert any(
        "authorized official certifies, signs, uploads, sends, and submits" in gate
        for gate in pilot["human_gates"]
    )
    assert payload["pilot_protocol_receipts"]["golden_replay_verified"] is True
    assert "guaranteed awards or autonomous final submission" in payload["claim_controls"]["blocked_now"]


def test_golden_replay_is_deterministic_and_tamper_evident():
    module = load_module()
    config = module.load_pilot_config()

    first = module.build_golden_replay(config)
    second = module.build_golden_replay(config)

    assert first == second
    assert module.verify_golden_replay(first) is True
    assert first["fixture_data_class"] == "synthetic_no_phi_no_credentials"
    assert {event["decision"] for event in first["events"]} == {
        "QUALIFIED_FOR_BUYER_REVIEW",
        "DISQUALIFIED",
        "ABSTAIN_INSUFFICIENT_EVIDENCE",
    }
    assert first["receipt"]["event_count"] == 3
    assert len(first["replay_sha256"]) == 64

    tampered = deepcopy(first)
    tampered["events"][0]["decision"] = "QUALIFIED_FOR_AUTONOMOUS_SUBMISSION"
    assert module.verify_golden_replay(tampered) is False


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
    assert manifest["artifact_count"] == 14
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
