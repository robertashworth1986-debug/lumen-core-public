from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PRODUCT_LANE_PRIORITY_ENGINE.py"
HYPERCORE_RUNNER = ROOT / "code" / "ops" / "run_hypercore_v8_offline_replay.py"


def load_module():
    spec = importlib.util.spec_from_file_location("product_lane_priority_engine", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_hypercore_runner():
    spec = importlib.util.spec_from_file_location(
        "hypercore_v8_offline_replay_for_product_lane_test", HYPERCORE_RUNNER
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def stage_hypercore_evidence(tmp_path: Path, *, include_preflight_receipt: bool) -> None:
    relative_paths = (
        "config/hypercore_v8_validation_protocol_v1.json",
        "dashboard/data/reviewer_evidence_gate.json",
        "docs/ROOT_EVIDENCE_VALUATION_BRIDGE_2026-06-22.md",
        "code/ops/BUILD_LOCAL_ICLOUD_EVIDENCE_INTAKE.py",
        "code/ops/run_hypercore_v8_offline_replay.py",
    )
    for relative_path in relative_paths:
        source = ROOT / relative_path
        destination = tmp_path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())

    if not include_preflight_receipt:
        return

    # Produce the generated receipt in the isolated test root, never from an ignored local output.
    runner = load_hypercore_runner()
    protocol = tmp_path / "config" / "hypercore_v8_validation_protocol_v1.json"
    bundle = runner.build_synthetic_fixture(tmp_path / "fixture", seed=20260802)
    receipt = (
        tmp_path
        / "dashboard"
        / "evidence"
        / "hypercore"
        / "HYPERCORE_V8_SYNTHETIC_PREFLIGHT_2026-08-02.json"
    )
    result = runner.run_replay(
        protocol_path=protocol,
        bundle_path=bundle,
        output_path=receipt,
        generated_utc="2026-08-02T10:30:00Z",
        seed=20260802,
        null_replicates=None,
    )
    assert result["status"] == "SYNTHETIC_PREFLIGHT_COMPLETE_NOT_EXTERNAL_VALIDATION"


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


def test_harmonic_backprop_legacy_claim_is_audited_and_blocked():
    module = load_module()
    payload = module.build_payload(datetime(2026, 8, 2, tzinfo=timezone.utc))
    audit = payload["evidence_audit"]["harmonic_backprop_legacy_claim"]
    result = audit["historical_result"]

    assert audit["comparison"] == "harmonic_vs_backprop"
    assert audit["status"] == "HISTORICAL_EXPLORATORY_ONLY_NOT_CLAIM_READY"
    assert result["benchmark_rows"] == 400
    assert result["harmonic_beats_backprop_rows"] == 362
    assert result["wins_file_rows"] == 362
    assert result["harmonic_beats_baseline_rows"] == 383
    assert result["harmonic_beats_both_rows"] == 354
    assert result["negative_backprop_r2_rows"] == 318
    assert result["period_est_equals_series_length_rows"] == 186
    assert result["historical_result_consistent"] is True
    assert audit["protocol_findings"][
        "full_series_refit_before_holdout_scoring_detected"
    ] is True
    assert audit["protocol_findings"][
        "train_only_predictions_unused_for_test_scoring_detected"
    ] is True
    assert audit["protocol_findings"]["target_scaling_detected_for_mlp"] is False
    assert audit["external_claim_allowed"] is False
    assert audit["bounded_corrective_runs"]["synthetic_dataset_count"] == 4
    assert audit["bounded_corrective_runs"]["real_eia_series_count"] == 4
    assert all(item["exists"] for item in audit["source_receipts"])
    assert any(
        "362/400 harmonic-versus-backprop" in claim
        for claim in payload["claim_controls"]["blocked_now"]
    )


def test_productization_matrix_is_complete_and_fail_closed():
    module = load_module()
    payload = module.build_payload(datetime.now(timezone.utc))
    matrix = payload["productization_matrix"]

    assert len(matrix) == len(payload["ranking"])
    assert {row["lane_id"] for row in matrix} == {
        row["id"] for row in payload["ranking"]
    }
    assert all(row["product_ready"] is False for row in matrix)
    assert all(row["external_send_allowed"] is False for row in matrix)
    assert all(row["buyer_acceptance_proven"] is False for row in matrix)

    top = matrix[0]
    assert top["lane_id"] == "prooflock_opportunity_ops"
    assert top["current_stage"] == (
        "PAID_PROOF_SPRINT_SCOPE_READY_HUMAN_APPROVAL_REQUIRED"
    )
    assert "fixed-scope proof sprint" in top["minimum_honest_sale"]

    lumascout = next(row for row in matrix if row["lane_id"] == "lumascout_ar_intelligence")
    assert lumascout["internal_evidence_gate_passed"] is False
    assert lumascout["current_stage"] == "INTERNAL_EVIDENCE_REPAIR_REQUIRED"
    assert lumascout["minimum_honest_sale"].startswith("No external offer")

    markdown = module.render_markdown(payload)
    assert "Build and sell" not in markdown
    assert "first human-approved paid proof-sprint candidate" in markdown
    assert "Legacy Harmonic/Backprop Claim Gate" in markdown
    assert "362" in markdown
    assert "WhiteHoleLab Remediation Gate" in markdown


def test_whiteholelab_remediation_is_fail_closed_and_archive_preserving():
    module = load_module()
    payload = module.build_payload(datetime(2026, 8, 2, 23, tzinfo=timezone.utc))
    gate = payload["evidence_audit"]["whiteholelab_remediation"]

    assert gate["status"] == "REMEDIATION_SPEC_READY_ARCHIVE_FROZEN"
    assert gate["audit_current"] is True
    assert gate["archive_mutation_allowed"] is False
    assert gate["legacy_site_deploy_allowed"] is False
    assert gate["performance_claim_allowed"] is False
    assert gate["alpha_claim_allowed"] is False
    assert gate["external_send_allowed"] is False
    assert gate["promotion_gate_passed"] is False
    assert {defect["id"] for defect in gate["defects"]} == {
        "ticker_alias_fallback_noop",
        "universe_manifest_omits_report",
        "current_state_ignores_fracture_flag",
    }
    assert gate["audit_marker_checks"]["ignores the emitted fracture state"] is True

    guarded = next(
        row for row in payload["ranking"] if row["id"] == "guarded_market_research"
    )
    audit_check = next(
        check
        for check in guarded["evidence_checks"]
        if check["path"] == "docs/WHITEHOLE_WHITEHOLELAB_AUDIT_2026-08-02.md"
    )
    assert audit_check["valid"] is True
    assert "alpha" in audit_check["claim_scope"]


def test_whiteholelab_remediation_rejects_stale_audit(tmp_path, monkeypatch):
    module = load_module()
    audit = tmp_path / "docs" / "WHITEHOLE_WHITEHOLELAB_AUDIT_2026-08-02.md"
    audit.parent.mkdir(parents=True)
    audit.write_text("incomplete audit", encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "WHITEHOLE_AUDIT", audit)

    gate = module.build_whiteholelab_remediation_gate()

    assert gate["status"] == "BLOCKED_AUDIT_MISSING_OR_STALE"
    assert gate["audit_current"] is False
    assert gate["promotion_gate_passed"] is False


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


def test_hypercore_lane_is_registered_and_requires_external_buyer_validation(
    tmp_path, monkeypatch
):
    module = load_module()
    stage_hypercore_evidence(tmp_path, include_preflight_receipt=True)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    config = module.read_json(ROOT / "config" / "product_lane_priority_v1.json")
    lane_config = next(
        row
        for row in config["lanes"]
        if row["id"] == "hypercore_readonly_resilience_evaluation"
    )
    ranked = module.rank_lanes(
        {"weights": config["weights"], "lanes": [lane_config]},
        datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
    )
    lane = next(
        row
        for row in ranked
        if row["id"] == "hypercore_readonly_resilience_evaluation"
    )

    assert lane["internal_evidence_gate_passed"] is True
    assert lane["buyer_readiness_gate"]["passed"] is False
    assert (
        lane["buyer_readiness_gate"]["status"]
        == "requires_external_buyer_validation"
    )
    assert lane["validated_evidence_count"] == 6
    assert lane["required_evidence_count"] == 6
    assert lane["validated_evidence_coverage"] == 1.0
    assert (
        lane["evidence_checks"][-1]["path"]
        == "dashboard/evidence/hypercore/HYPERCORE_V8_SYNTHETIC_PREFLIGHT_2026-08-02.json"
    )
    assert lane["evidence_checks"][-1]["valid"] is True
    assert "realized energy, outage, or operating savings" in lane["blocked_claims"]

    protocol = json.loads(
        (tmp_path / "config" / "hypercore_v8_validation_protocol_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert protocol["schema"] == "hypercore_v8_validation_protocol_v1"
    assert protocol["status"] == (
        "draft_runner_implemented_synthetic_preflight_only_buyer_source_required"
    )
    assert "custody anchor only" in protocol["lineage"]["v7_role"]
    assert protocol["chronology"]["minimum_blocked_walk_forward_folds"] == 5
    assert (
        protocol["required_falsification"]["minimum_seeded_replicates_per_null"]
        == 999
    )
    assert (
        "risk_forecast_v9_only_unless_v8_emits_probabilities"
        in protocol["required_metrics"]
    )
    assert (
        protocol["promotion_gates"][
            "incident_clustered_bootstrap_confidence_level"
        ]
        == 0.95
    )
    assert protocol["promotion_gates"]["underpowered_result_status"] == (
        "descriptive_only"
    )
    assert protocol["commercial_boundary"]["external_send_allowed"] is False
    assert protocol["promotion_gates"]["independent_reproduction_required_for_external_validation"] is True


def test_hypercore_lane_fails_closed_without_preflight_receipt(tmp_path, monkeypatch):
    module = load_module()
    stage_hypercore_evidence(tmp_path, include_preflight_receipt=False)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    config = module.read_json(ROOT / "config" / "product_lane_priority_v1.json")
    lane_config = next(
        row
        for row in config["lanes"]
        if row["id"] == "hypercore_readonly_resilience_evaluation"
    )

    lane = module.rank_lanes(
        {"weights": config["weights"], "lanes": [lane_config]},
        datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
    )[0]

    assert lane["internal_evidence_gate_passed"] is False
    assert lane["evidence_checks"][-1]["valid"] is False
    assert "artifact_missing" in lane["evidence_checks"][-1]["reasons"]


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


def test_mindwise_reactivation_draft_uses_bounded_paid_entry_offer():
    module = load_module()
    payload = module.build_payload(datetime(2026, 8, 2, tzinfo=timezone.utc))
    pilot = payload["mindwise_pilot"]
    offer = pilot["commercial_entry_offer"]
    draft = module.render_mindwise_email(payload)

    assert offer["duration"] == "10 business days"
    assert offer["candidate_fixed_fee_usd"] == 3500
    assert offer["candidate_kickoff_deposit_usd"] == 1750
    assert offer["candidate_delivery_balance_usd"] == 1750
    assert offer["price_status"] == "candidate_not_committed"
    assert offer["external_send_allowed"] is False
    assert offer["buyer_price_acceptance_proven"] is False
    assert offer["buyer_state"] == (
        "historical_warm_reactivation_candidate_recent_interest_unconfirmed"
    )
    assert len(offer["deliverables"]) == 5
    assert "EXACT SEND AND PRICE APPROVAL REQUIRED" in draft
    assert "Hi [Authorized MindWise contact]" in draft
    assert "paid proof sprint lasting 10 business days" in draft
    assert "candidate fixed fee is $3,500" in draft
    assert "$1,750 kickoff deposit" in draft
    assert "$1,750 on delivery" in draft
    assert "not committed" in draft
    assert "no PHI or credentials" in draft
    assert "no autonomous certifications or submissions" in draft
    assert "30-day pilot" in draft
    assert "next week" not in draft.lower()
    assert "guaranteed" not in draft.lower()


def test_candidate_commercial_terms_fail_closed(monkeypatch):
    module = load_module()
    valid = module.read_json(module.HYPERCORE_PROTOCOL)

    monkeypatch.setattr(module, "read_json", lambda path: valid)
    terms = module.load_candidate_commercial_terms()
    assert terms["candidate_fixed_fee_usd"] == 3500
    assert terms["external_send_allowed"] is False

    unsafe = deepcopy(valid)
    unsafe["commercial_boundary"]["external_send_allowed"] = True
    monkeypatch.setattr(module, "read_json", lambda path: unsafe)
    try:
        module.load_candidate_commercial_terms()
    except ValueError as exc:
        assert "fail closed" in str(exc)
    else:
        raise AssertionError("Unsafe external-send state must fail closed")


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
    assert manifest["artifact_count"] == 17
    assert manifest["all_artifacts_present"] is True
    assert all(len(item["sha256"]) == 64 for item in manifest["artifacts"])
    assert any(
        item["path"]
        == "dashboard/evidence/hypercore/HYPERCORE_V8_SYNTHETIC_PREFLIGHT_2026-08-02.json"
        for item in manifest["artifacts"]
    )
    assert all(
        not item["path"].startswith(("out/", "clean_data/", "data/"))
        for item in manifest["artifacts"]
    )
    assert len(manifest["excluded_local_only_inputs"]) == 5
    assert "non-versioned local historical inputs" in manifest[
        "public_reproducibility_status"
    ]
    assert "byte identity and presence only" in manifest["boundary"]
    unsealed = dict(manifest)
    receipt = unsealed.pop("manifest_payload_sha256")
    assert module.stable_hash(unsealed) == receipt


def test_latest_aliases_match_current_payload_and_manifest(tmp_path, monkeypatch):
    module = load_module()
    latest_payload = tmp_path / "out" / "ops" / "priority_latest.json"
    latest_manifest = tmp_path / "out" / "ops" / "manifest_latest.json"
    monkeypatch.setattr(module, "LATEST_OUT_JSON", latest_payload)
    monkeypatch.setattr(module, "LATEST_BUNDLE_MANIFEST", latest_manifest)
    payload = {"schema": "product_lane_priority_engine_v1", "rank": 1}
    manifest = {"schema": "product_lane_priority_bundle_manifest_v1", "count": 1}

    module.write_latest_aliases(payload, manifest)

    assert json.loads(latest_payload.read_text(encoding="utf-8")) == payload
    assert json.loads(latest_manifest.read_text(encoding="utf-8")) == manifest


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
