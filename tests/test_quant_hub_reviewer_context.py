from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_QUANT_HUB_REVIEWER_CONTEXT.py"
LEXICON = ROOT / "config" / "quant_hub_lexicon_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("build_quant_hub_reviewer_context", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_private_universe_receipt(module):
    payload = {
        "schema": "lumencore_private_universe_receipt_v1",
        "generation_id": "generation_0123456789abcdef0123456789abcdef",
        "generated_utc": "2026-07-14T00:00:00+00:00",
        "status": "PRIVATE_UNIVERSE_ZERO_COPY_FEDERATION_READY_LIMITED",
        "methodology": {
            "federation_mode": "zero_copy_manifest_federation",
            "freshness": "mixed_freshness",
            "full_live_reconciliation": False,
            "source_manifest_files_read_and_parsed": True,
            "manifest_referenced_file_bytes_read": False,
            "referenced_historical_asset_files_opened": False,
            "explicit_file_bytes_read_for_sha256": True,
            "explicit_file_contents_parsed_or_extracted": False,
            "referenced_historical_asset_contents_parsed_or_extracted": False,
            "broad_roots_scanned": False,
            "archives_unpacked": False,
            "historical_hashes_reverified": False,
            "explicit_user_supplied_files_hashed": True,
            "source_provenance_preserved": True,
            "manifest_initial_hash_stat_stable": True,
            "manifest_inputs_rehashed_after_import": True,
            "manifest_inputs_unchanged_after_import": True,
            "manifest_input_count_reverified": 1,
            "effective_root_attribution": "most_specific_declared_root",
            "lane_classification_method": "filename_extension_and_manifest_metadata_heuristics_only",
            "lane_counts_are_content_validated": False,
            "sqlite_temp_store": "memory_not_system_volume",
            "public_receipt_path_free": True,
            "output_volume_preflight": {
                "gate_passed": True,
                "minimum_free_percent": 10.0,
                "observed_free_percent": 40.0,
                "observed_free_bytes": 100_000,
                "estimated_database_bytes": 20_000,
                "absolute_reserve_bytes": 30_000,
                "required_free_bytes": 50_000,
                "database_estimate_multiplier": 3,
                "database_estimate_basis": "aggregate_manifest_bytes_times_multiplier_with_minimum_floor",
                "nearest_existing_ancestor_checked_before_output_creation": True,
                "output_volume_only": True,
                "input_volume_gate_required": False,
                "input_scope": "manifest_only_plus_individually_authorized_explicit_files",
            },
        },
        "transformation_identity": {
            "builder_sha256": "d" * 64,
            "parser_schema_version": "lumencore_private_universe_parser_v2",
            "sqlite_version": "3.49.1",
            "manifest_post_import_rehash_passed": True,
            "generation_id": "generation_0123456789abcdef0123456789abcdef",
            "builder_git_commit": "e" * 40,
            "builder_git_state": "tracked_clean",
            "builder_git_dirty": False,
            "builder_source_is_committed_snapshot": True,
            "sqlite_quick_check": "ok",
            "staged_database_quick_check_passed": True,
        },
        "summary": {
            "source_manifest_count": 1,
            "source_observation_count": 10,
            "unique_asset_count": 7,
            "duplicate_observation_count": 3,
            "historical_content_sha256_observation_count": 5,
            "historical_metadata_sha256_observation_count": 1,
            "historical_content_sha256_conflict_asset_count": 1,
            "explicit_file_count": 1,
            "explicit_file_sha256_coverage_count": 1,
            "root_alias_count": 2,
            "root_registry_entry_count": 1,
            "candidate_lane_count": 3,
            "archive_reference_asset_count": 1,
            "unmapped_observation_count": 0,
            "reported_root_mismatch_observation_count": 0,
        },
        "source_summary": [
            {
                "source_kind": "fixture_manifest",
                "source_sha256": "a" * 64,
                "source_bytes": 100,
                "source_modified_utc": "2026-07-13T00:00:00+00:00",
                "manifest_row_count": 10,
                "observation_count": 10,
                "invalid_observation_count": 0,
                "manifest_referenced_file_bytes_read": False,
                "historical_hashes_reverified": False,
            }
        ],
        "candidate_lane_counts": {
            "additive_manufacturing_3d": 2,
            "field_work_evidence": 1,
            "hardware_geometry": 4,
        },
        "root_summary": {
            "coverage_quality_counts": {"historical_manifest_only": 2},
            "registry_role_counts": {"ACTIVE_FIELD_LAB": 1},
            "coverage_is_current_live_truth": False,
        },
        "claim_boundaries": {
            "complete_universe_claim_allowed": False,
            "current_file_existence_claim_allowed": False,
            "content_ownership_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "technical_readiness_claim_allowed": False,
            "valuation_claim_allowed": False,
        },
        "private_index_custody": {
            "generation_id": "generation_0123456789abcdef0123456789abcdef",
            "database_sha256": "b" * 64,
            "database_bytes": 4_096,
            "locator_alias": "private_proof_vault_estate_index_latest",
            "publish_set_artifact_count": 4,
            "atomic_per_artifact_replace": True,
            "rollback_protected_publish_set": True,
            "staged_database_quick_check_passed": True,
            "prior_latest_database_present": False,
            "prior_latest_database_preserved": False,
            "prior_latest_database_sha256": "",
            "prior_latest_database_bytes": 0,
            "prior_latest_private_receipt_present": False,
            "prior_latest_private_receipt_preserved": False,
            "prior_latest_private_receipt_sha256": "",
            "prior_latest_private_receipt_bytes": 0,
        },
    }
    payload["receipt_sha256"] = module.stable_json_sha256(payload)
    return payload


def test_lexicon_defines_level_five_as_external_validation():
    payload = json.loads(LEXICON.read_text(encoding="utf-8"))
    assert payload["schema"] == "quant_hub_lexicon.v1"
    assert payload["identity"]["repository_display_name"] == "Quant Hub Repo"
    assert payload["level_policy"]["current_repository_wide_level"] == 3
    assert payload["level_policy"]["level_5_attained"] is False

    levels = {row["level"]: row for row in payload["evidence_maturity"]}
    assert set(levels) == {0, 1, 2, 3, 4, 5}
    assert "independent" in levels[5]["label"]
    assert "dated validation receipt" in levels[5]["minimum_evidence"]

    terms = [row["term"] for row in payload["terms"]]
    assert len(terms) == len(set(terms))
    assert {"LumenCore", "LumaTrader", "NovaStack", "ProofLock", "HumanUnlock", "EconomicRichness"}.issubset(
        terms
    )


def test_context_preserves_positive_negative_and_waiting_evidence():
    module = load_module()
    context = module.build_context()

    assert context["schema"] == "quant_hub_reviewer_context.v1"
    assert context["current_evidence_posture"]["highest_repository_wide_supported_level"] == 3
    assert context["current_evidence_posture"]["level_5_attained"] is False
    assert context["human_authority_policy"]["final_submission_allowed_without_human"] is False
    assert context["human_authority_policy"]["legal_or_ip_action_allowed_without_human"] is False

    cards = {row["proof_id"]: row for row in context["proof_cards"]}
    assert cards["prooflock_prior_vault"]["facts"]["all_copied_hashes_verified"] is True
    hardware = cards["hardware_3d_design_prior_custody"]
    assert hardware["evidence_class"] == "internal_metadata_custody"
    assert hardware["attained_maturity_level"] == 1
    assert hardware["status"] == "candidate_design_priors_only"
    assert hardware["facts"] == {
        "intake_records": 8_252,
        "geometry_hardware_candidates": 343,
        "design_prior_candidates": 36,
        "distinct_valid_sha256_count": 114,
        "valid_sha256_record_count": 343,
        "extension_counts": {
            ".csv": 204,
            ".docx": 9,
            ".json": 4,
            ".md": 1,
            ".pdf": 72,
            ".png": 8,
            ".ps1": 6,
            ".stl": 10,
            ".txt": 23,
            ".zip": 6,
        },
        "stl_record_count": 10,
        "pdf_record_count": 72,
        "earliest_last_write_utc": "2025-07-12T20:08:21+00:00",
        "latest_last_write_utc": "2026-06-16T01:04:29.498853+00:00",
        "stub_record_count_below_100_bytes": 72,
        "metadata_intake_only": True,
        "contains_secret_values": False,
        "field_validation_proven": False,
        "ready_for_portal_upload": False,
        "ready_for_submit": False,
        "source_receipt_sha256": next(
            row["sha256"]
            for row in context["source_artifacts"]
            if row["source_id"] == "local_icloud_evidence_intake"
        ),
    }
    assert "no hardware build" in hardware["claim_boundary"]
    assert "independent evaluation" in hardware["claim_boundary"]
    health_source = json.loads(
        module.SOURCE_PATHS["local_system_health_history_audit"].read_text(encoding="utf-8")
    )
    health = cards["local_system_health_history_observation"]
    health_facts = health["facts"]
    assert health["evidence_class"] == "internal_observational_evidence"
    assert health["attained_maturity_level"] == 2
    assert health["status"] == health_source["integrity"]["status"] == "defects_present"
    assert health_facts["valid_snapshot_count"] == health_source["summary"][
        "valid_snapshot_count"
    ]
    assert health_facts["active_utc_date_count"] == health_source["summary"][
        "active_utc_date_count"
    ]
    assert health_facts["elapsed_days"] == health_source["summary"]["elapsed_days"]
    assert set(health_facts["trailing_windows"]) == {"30", "90", "180"}
    assert all(
        row["cpu_sample_seconds_each"] == 1.0
        for row in health_facts["trailing_windows"].values()
    )
    assert health_facts["hardware_degradation_claim_allowed"] is False
    assert health_facts["field_validation_claim_allowed"] is False
    assert health_facts["independent_validation_claim_allowed"] is False
    assert "hardware degradation" in health["claim_boundary"]
    assert "No independent evaluator" in health["claim_boundary"]
    assert cards["locked_source_baseline_replay"]["facts"]["candidate_win_count"] > 0
    assert cards["locked_source_baseline_replay"]["facts"]["candidate_loss_or_tie_count"] > 0
    residual = cards["eia_residual_holm_holdout"]
    residual_facts = residual["facts"]
    assert residual["attained_maturity_level"] == 3
    assert residual["status"] == "all_internal_comparisons_holm_positive_full_protocol_gate_closed"
    assert list(residual_facts)[:4] == [
        "holm_result",
        "full_protocol_gate",
        "coverage_result",
        "selected_candidate",
    ]
    assert residual_facts["selected_candidate"] == "xgboost_residual"
    assert residual_facts["holdout_rows"] == 1_176
    assert residual_facts["holdout_authorities"] == 8
    assert residual_facts["authority_month_pairs"] == 52
    assert residual_facts["holm_positive_comparison_count"] == 6
    assert residual_facts["holm_comparison_total"] == 6
    assert residual_facts["holm_result"] == "6/6 Holm-positive internal comparisons"
    assert residual_facts["minimum_coverage_days"] == 90
    assert residual_facts["coverage_target_days"] == 150
    assert residual_facts["coverage_result"] == "90/150 minimum common days"
    assert residual_facts["worst_authority"] == "SWPP"
    assert residual_facts["worst_baseline"] == "autoregressive_ridge_p14"
    assert residual_facts["worst_authority_mean_skill"] == pytest.approx(-0.07997287044685936)
    assert residual_facts["coverage_pass"] is False
    assert residual_facts["all_baseline_comparisons_pass"] is False
    assert residual_facts["protocol_grade_internal_champion"] is False
    assert residual_facts["full_protocol_gate"] == "CLOSED"
    assert residual_facts["external_replication_complete"] is False
    assert residual_facts["field_validation_complete"] is False
    assert residual_facts["dollar_conversion_allowed"] is False
    assert cards["eia_prospective_router"]["facts"]["prediction_count"] == 0
    assert cards["eia_prospective_router"]["facts"]["settlement_count"] == 0
    assert cards["eia_prospective_router"]["facts"]["promotion_evaluation_complete"] is False
    hourly = cards["eia_prospective_hourly_router"]
    assert hourly["attained_maturity_level"] == 1
    assert hourly["target_maturity_level"] == 4
    assert hourly["status"] == "PROSPECTIVE_COLLECTION_ACTIVE"
    assert hourly["facts"]["prediction_count"] == 95
    assert hourly["facts"]["settlement_count"] == 72
    assert hourly["facts"]["common_settled_hour_count"] == 0
    assert hourly["facts"]["preliminary_ready"] is False
    assert hourly["facts"]["confirmatory_ready"] is False
    assert hourly["facts"]["durability_ready"] is False
    assert hourly["facts"]["promotion_evaluation_complete"] is False
    assert hourly["facts"]["preliminary_threshold_common_hours_per_authority"] == 168
    assert hourly["facts"]["confirmatory_threshold_common_hours_per_authority"] == 720
    assert hourly["facts"]["durability_threshold_common_hours_per_authority"] == 2160
    assert hourly["facts"]["protocol_source_sha256"] == next(
        row["sha256"]
        for row in context["source_artifacts"]
        if row["source_id"] == "eia_hourly_protocol"
    )
    assert cards["mda_synthetic_feasibility_v1"]["facts"]["gate_passed"] is False
    assert cards["mda_open_set_v2"]["facts"]["gate_passed"] is False
    assert cards["mda_open_set_v2"]["facts"]["unsupported_mapping_rate"] == 0.0
    assert cards["faa_sdr_frozen_10k"]["facts"]["holdout_rows"] == 10_000
    assert cards["faa_sdr_frozen_10k"]["facts"]["development_key_overlap"] == 0
    assert cards["faa_sdr_frozen_10k"]["facts"]["candidate_promoted"] is False
    assert cards["faa_sdr_frozen_10k"]["facts"]["rolls_royce_exploratory_rows"] == 28

    blocked = context["claim_controls"]["blocked_without_new_evidence"]
    assert all(blocked.values())
    assert len(context["source_input_chain_sha256"]) == 64
    assert all(len(row["sha256"]) == 64 for row in context["source_artifacts"])

    serialized = json.dumps(context).casefold().replace("\\", "/")
    assert "private_estate" not in serialized
    assert "patent_19_281_546" not in serialized
    assert "cp575notice" not in serialized
    assert "c:/users/" not in serialized


def test_context_outputs_are_identical_and_public_safe(tmp_path):
    module = load_module()
    context = module.build_context()
    out_json = tmp_path / "out.json"
    dashboard_json = tmp_path / "dashboard.json"
    out_md = tmp_path / "reviewer.md"

    module.write_outputs(
        context,
        output_json=out_json,
        dashboard_json=dashboard_json,
        output_markdown=out_md,
    )

    assert out_json.read_bytes() == dashboard_json.read_bytes()
    markdown = out_md.read_text(encoding="utf-8")
    assert "Level 5 attained: `false`" in markdown
    assert "MDA mapping independent open-set v2" in markdown
    assert "FAA SDR frozen 10,000-report triage benchmark" in markdown
    assert "EIA residual hybrid frozen holdout" in markdown
    assert "Frozen EIA prospective hourly router" in markdown
    assert "prediction_count=95" in markdown
    assert "common_settled_hour_count=0" in markdown
    assert "Hardware and 3D design-prior metadata custody" in markdown
    assert "Local system-health history custody audit" in markdown
    assert "holm_result=6/6 Holm-positive internal comparisons" in markdown
    assert "coverage_result=90/150 minimum common days" in markdown
    assert "all_internal_comparisons_holm_positive_full_protocol_gate_closed" in markdown
    assert "full protocol gate is CLOSED" in markdown
    assert "no hardware build" in markdown
    assert "not hardware-degradation proof" in markdown
    assert "no fresh full universe scan" in markdown
    assert "Patent And Privacy Boundary" in markdown
    assert "private_estate" not in markdown.casefold()


def test_context_hashes_the_same_single_read_snapshot_it_parses(monkeypatch):
    module = load_module()
    original_read_bytes = Path.read_bytes
    reads: dict[Path, int] = {}

    def counted_read_bytes(path: Path) -> bytes:
        resolved = path.resolve()
        reads[resolved] = reads.get(resolved, 0) + 1
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", counted_read_bytes)
    context = module.build_context()
    expected_paths = {
        module.LEXICON.resolve(),
        *(path.resolve() for path in module.SOURCE_PATHS.values()),
        *(
            path.resolve()
            for path in module.OPTIONAL_SOURCE_PATHS.values()
            if path.is_file()
        ),
    }

    assert {path for path in reads if path in expected_paths} == expected_paths
    assert all(reads[path] == 1 for path in expected_paths)
    receipts = {row["source_id"]: row for row in context["source_artifacts"]}
    assert receipts["prior_proof_vault"]["sha256"] == context["proof_cards"][0]["facts"][
        "manifest_source_sha256"
    ]
    residual = next(
        row for row in context["proof_cards"] if row["proof_id"] == "eia_residual_holm_holdout"
    )
    assert receipts["eia_residual_benchmark"]["sha256"] == residual["facts"][
        "benchmark_source_sha256"
    ]
    assert receipts["eia_residual_protocol"]["sha256"] == residual["facts"][
        "protocol_source_sha256"
    ]
    hardware = next(
        row for row in context["proof_cards"] if row["proof_id"] == "hardware_3d_design_prior_custody"
    )
    assert receipts["local_icloud_evidence_intake"]["sha256"] == hardware["facts"][
        "source_receipt_sha256"
    ]
    health = next(
        row
        for row in context["proof_cards"]
        if row["proof_id"] == "local_system_health_history_observation"
    )
    assert receipts["local_system_health_history_audit"]["sha256"] == health["facts"][
        "source_receipt_sha256"
    ]


def test_hardware_design_prior_card_fails_closed_on_claim_inflation():
    module = load_module()
    intake = {
        "schema": "local_icloud_evidence_intake_v1",
        "summary": {
            "records": 0,
            "by_category": {"geometry_hardware": 0},
            "by_recommended_use": {
                "usable_as_concept_visual_or_design_prior_artifact_not_performance_proof": 0,
            },
        },
        "records": [],
        "claim_gate": {
            "boundary": "Metadata intake only.",
            "contains_secret_values": False,
            "field_validation_proven": True,
            "ready_for_portal_upload": False,
            "ready_for_submit": False,
        },
    }

    with pytest.raises(ValueError, match="exceeds the allowed design-prior evidence boundary"):
        module.derive_hardware_design_prior_evidence(intake)


def test_hardware_design_prior_card_reconciles_summary_to_records():
    module = load_module()
    intake = json.loads(
        module.SOURCE_PATHS["local_icloud_evidence_intake"].read_text(encoding="utf-8")
    )
    intake["summary"]["by_category"]["geometry_hardware"] -= 1

    with pytest.raises(ValueError, match="geometry_hardware does not reconcile to records"):
        module.derive_hardware_design_prior_evidence(intake)


def test_health_history_card_fails_closed_when_receipt_hash_is_stale():
    module = load_module()
    audit = json.loads(
        module.SOURCE_PATHS["local_system_health_history_audit"].read_text(encoding="utf-8")
    )
    audit["summary"]["valid_snapshot_count"] += 1

    with pytest.raises(ValueError, match="audit_receipt_sha256 does not verify"):
        module.derive_local_system_health_history_evidence(audit)


def test_private_universe_receipt_is_optional_until_import_runs(tmp_path, monkeypatch):
    module = load_module()
    monkeypatch.setitem(
        module.OPTIONAL_SOURCE_PATHS,
        "private_universe_receipt",
        tmp_path / "not_generated.json",
    )

    context = module.build_context()
    proof_ids = {row["proof_id"] for row in context["proof_cards"]}
    assert "private_universe_zero_copy_custody" not in proof_ids
    assert context["optional_source_status"]["private_universe_receipt"] == "not_generated"
    assert any(
        "no fresh full universe scan" in statement.casefold()
        for statement in context["claim_controls"]["currently_supported"]
    )


def test_private_universe_receipt_adds_bounded_card_and_source_chain(tmp_path, monkeypatch):
    module = load_module()
    receipt = make_private_universe_receipt(module)
    receipt_path = tmp_path / "universe_receipt.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setitem(
        module.OPTIONAL_SOURCE_PATHS,
        "private_universe_receipt",
        receipt_path,
    )
    original_repo_path = module.repo_path

    def test_repo_path(path: Path) -> str:
        try:
            return original_repo_path(path)
        except ValueError:
            return f"tmp/{path.name}"

    monkeypatch.setattr(module, "repo_path", test_repo_path)
    context = module.build_context()
    cards = {row["proof_id"]: row for row in context["proof_cards"]}
    card = cards["private_universe_zero_copy_custody"]
    facts = card["facts"]
    receipts = {row["source_id"]: row for row in context["source_artifacts"]}

    assert card["evidence_class"] == "internal_custody_evidence"
    assert card["attained_maturity_level"] == 1
    assert facts["fresh_full_scan_completed"] is False
    assert facts["full_live_reconciliation"] is False
    assert facts["manifest_referenced_file_bytes_read"] is False
    assert facts["explicit_file_bytes_read_for_sha256"] is True
    assert facts["explicit_user_supplied_files_hashed"] is True
    assert facts["explicit_file_contents_parsed_or_extracted"] is False
    assert facts["referenced_historical_asset_contents_parsed_or_extracted"] is False
    assert facts["broad_roots_scanned"] is False
    assert facts["historical_hashes_reverified"] is False
    assert facts["private_index_custody"] == receipt["private_index_custody"]
    assert facts["candidate_lane_counts"] == receipt["candidate_lane_counts"]
    assert facts["candidate_lane_counts"]["field_work_evidence"] == 1
    assert facts["lane_counts_are_content_validated"] is False
    assert facts["historical_content_sha256_observation_count"] == 5
    assert facts["historical_metadata_sha256_observation_count"] == 1
    assert facts["transformation_identity"]["sqlite_quick_check"] == "ok"
    assert facts["source_receipt_sha256"] == receipts["private_universe_receipt"]["sha256"]
    assert context["optional_source_status"]["private_universe_receipt"] == "available"
    assert "not a fresh full scan" in card["claim_boundary"]
    assert "field or performance validation" in card["claim_boundary"]
    assert "independent evaluation" in card["claim_boundary"]


def test_private_universe_receipt_rejects_live_scan_inflation():
    module = load_module()
    receipt = make_private_universe_receipt(module)
    receipt["methodology"]["full_live_reconciliation"] = True
    receipt["receipt_sha256"] = module.stable_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )

    with pytest.raises(ValueError, match="full_live_reconciliation exceeds the receipt boundary"):
        module.derive_private_universe_evidence(receipt)


def test_private_universe_receipt_reconciles_explicit_file_hash_reads():
    module = load_module()
    receipt = make_private_universe_receipt(module)
    receipt["summary"]["explicit_file_count"] = 0
    receipt["summary"]["explicit_file_sha256_coverage_count"] = 0
    receipt["receipt_sha256"] = module.stable_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )

    with pytest.raises(
        ValueError,
        match="explicit_file_bytes_read_for_sha256 does not reconcile",
    ):
        module.derive_private_universe_evidence(receipt)


def test_private_universe_receipt_rejects_unpreserved_prior_database():
    module = load_module()
    receipt = make_private_universe_receipt(module)
    custody = receipt["private_index_custody"]
    custody["prior_latest_database_present"] = True
    custody["prior_latest_database_preserved"] = False
    custody["prior_latest_database_sha256"] = "c" * 64
    custody["prior_latest_database_bytes"] = 2_048
    receipt["receipt_sha256"] = module.stable_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )

    with pytest.raises(ValueError, match="did not preserve the prior database"):
        module.derive_private_universe_evidence(receipt)


def test_private_universe_receipt_rejects_manifest_referenced_asset_reads():
    module = load_module()
    receipt = make_private_universe_receipt(module)
    receipt["source_summary"][0]["manifest_referenced_file_bytes_read"] = True
    receipt["receipt_sha256"] = module.stable_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )

    with pytest.raises(ValueError, match="manifest_referenced_file_bytes_read exceeds"):
        module.derive_private_universe_evidence(receipt)


def test_private_universe_receipt_rejects_failed_sqlite_quick_check():
    module = load_module()
    receipt = make_private_universe_receipt(module)
    receipt["transformation_identity"]["sqlite_quick_check"] = "corrupt"
    receipt["receipt_sha256"] = module.stable_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )

    with pytest.raises(ValueError, match="SQLite quick_check did not pass"):
        module.derive_private_universe_evidence(receipt)


def test_private_universe_receipt_rejects_inconsistent_git_identity():
    module = load_module()
    receipt = make_private_universe_receipt(module)
    receipt["transformation_identity"]["builder_git_dirty"] = True
    receipt["receipt_sha256"] = module.stable_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )

    with pytest.raises(ValueError, match="Git snapshot flags do not reconcile"):
        module.derive_private_universe_evidence(receipt)


def test_private_universe_candidate_lanes_cannot_claim_content_validation():
    module = load_module()
    receipt = make_private_universe_receipt(module)
    receipt["methodology"]["lane_counts_are_content_validated"] = True
    receipt["receipt_sha256"] = module.stable_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )

    with pytest.raises(ValueError, match="candidate lane counts overstate validation"):
        module.derive_private_universe_evidence(receipt)


def test_context_fails_closed_when_required_source_is_missing(tmp_path, monkeypatch):
    module = load_module()
    missing = tmp_path / "missing.json"
    monkeypatch.setitem(module.SOURCE_PATHS, "eia_residual_benchmark", missing)
    with pytest.raises(FileNotFoundError, match="required reviewer-context input is missing"):
        module.build_context()


def test_hourly_projection_rejects_premature_readiness():
    module = load_module()
    projection = json.loads(
        module.SOURCE_PATHS["eia_hourly_runtime_projection"].read_text(encoding="utf-8")
    )
    protocol = json.loads(
        module.SOURCE_PATHS["eia_hourly_protocol"].read_text(encoding="utf-8")
    )
    projection["sample_state"]["preliminary_ready"] = True

    with pytest.raises(ValueError, match="preliminary_ready does not reconcile"):
        module.derive_eia_hourly_prospective_evidence(
            projection,
            protocol,
            protocol_path=module.repo_path(module.SOURCE_PATHS["eia_hourly_protocol"]),
            protocol_sha256=module.sha256_file(module.SOURCE_PATHS["eia_hourly_protocol"]),
        )


def test_eia_residual_card_is_derived_from_required_snapshots(tmp_path, monkeypatch):
    module = load_module()
    benchmark = json.loads(module.SOURCE_PATHS["eia_residual_benchmark"].read_text(encoding="utf-8"))
    protocol = json.loads(module.SOURCE_PATHS["eia_residual_protocol"].read_text(encoding="utf-8"))

    protocol["promotion_gate"]["minimum_common_holdout_days_per_authority"] = 88
    protocol_bytes = (json.dumps(protocol, indent=2, sort_keys=True) + "\n").encode("utf-8")
    protocol_path = tmp_path / "derived_protocol.json"
    protocol_path.write_bytes(protocol_bytes)

    benchmark["selection"]["selected_candidate"] = "derived_candidate_v2"
    selected_row = next(
        row for row in benchmark["holdout_leaderboard"] if row["strategy"] == "xgboost_residual"
    )
    selected_row["strategy"] = "derived_candidate_v2"
    selected_row["row_count"] = 999
    selected_row["authority_count"] = 7
    for index, comparison in enumerate(benchmark["baseline_comparisons"]):
        comparison["paired_authority_month_count"] = 41
        comparison["holm_adjusted_p_value"] = 0.01 if index < 2 else 0.20
        comparison["authority_mean_skill"] = {"TEST_AUTHORITY": -0.125 if index == 0 else 0.25}
    benchmark["holdout_coverage"]["minimum_common_holdout_days"] = 73
    benchmark["protocol"]["path"] = "tmp/derived_protocol.json"
    benchmark["protocol"]["sha256"] = hashlib.sha256(protocol_bytes).hexdigest()
    benchmark_path = tmp_path / "derived_benchmark.json"
    benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")

    original_repo_path = module.repo_path

    def test_repo_path(path: Path) -> str:
        try:
            return original_repo_path(path)
        except ValueError:
            return f"tmp/{path.name}"

    monkeypatch.setattr(module, "repo_path", test_repo_path)
    monkeypatch.setitem(module.SOURCE_PATHS, "eia_residual_benchmark", benchmark_path)
    monkeypatch.setitem(module.SOURCE_PATHS, "eia_residual_protocol", protocol_path)

    context = module.build_context()
    card = next(row for row in context["proof_cards"] if row["proof_id"] == "eia_residual_holm_holdout")
    facts = card["facts"]
    assert facts["selected_candidate"] == "derived_candidate_v2"
    assert facts["holdout_rows"] == 999
    assert facts["holdout_authorities"] == 7
    assert facts["authority_month_pairs"] == 41
    assert facts["holm_positive_comparison_count"] == 2
    assert facts["holm_comparison_total"] == 6
    assert facts["minimum_coverage_days"] == 73
    assert facts["coverage_target_days"] == 88
    assert facts["coverage_result"] == "73/88 minimum common days"
    assert facts["worst_authority"] == "TEST_AUTHORITY"
    assert facts["worst_baseline"] == benchmark["baseline_comparisons"][0]["baseline"]
    assert facts["worst_authority_mean_skill"] == pytest.approx(-0.125)


def test_eia_residual_holm_positive_count_requires_candidate_favoring_direction():
    module = load_module()
    benchmark = json.loads(module.SOURCE_PATHS["eia_residual_benchmark"].read_text(encoding="utf-8"))
    protocol = json.loads(module.SOURCE_PATHS["eia_residual_protocol"].read_text(encoding="utf-8"))
    comparisons = benchmark["baseline_comparisons"]
    for comparison in comparisons:
        comparison["holm_adjusted_p_value"] = 0.20

    comparisons[0]["holm_adjusted_p_value"] = 0.01
    comparisons[0]["mean_skill_delta"] = -0.01
    comparisons[0]["cluster_bootstrap_mean_skill_ci95"] = [0.01, 0.20]

    comparisons[1]["holm_adjusted_p_value"] = 0.01
    comparisons[1]["mean_skill_delta"] = 0.10
    comparisons[1]["cluster_bootstrap_mean_skill_ci95"] = [-0.01, 0.20]

    comparisons[2]["holm_adjusted_p_value"] = 0.01
    comparisons[2]["mean_skill_delta"] = 0.10
    comparisons[2]["cluster_bootstrap_mean_skill_ci95"] = [0.01, 0.20]

    derived = module.derive_eia_residual_evidence(
        benchmark,
        protocol,
        protocol_path=benchmark["protocol"]["path"],
        protocol_sha256=benchmark["protocol"]["sha256"],
    )

    assert derived["holm_positive_comparison_count"] == 1
    assert derived["holm_comparison_total"] == 6
    assert derived["holm_result"] == "1/6 Holm-positive internal comparisons"
    assert derived["all_internal_comparisons_holm_positive"] is False


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("mean_skill_delta", "not-a-number", r"mean_skill_delta must be numeric"),
        (
            "cluster_bootstrap_mean_skill_ci95",
            [0.1],
            r"cluster_bootstrap_mean_skill_ci95 must contain two bounds",
        ),
    ],
)
def test_eia_residual_direction_evidence_fails_closed_when_malformed(field, value, message):
    module = load_module()
    benchmark = json.loads(module.SOURCE_PATHS["eia_residual_benchmark"].read_text(encoding="utf-8"))
    protocol = json.loads(module.SOURCE_PATHS["eia_residual_protocol"].read_text(encoding="utf-8"))
    benchmark["baseline_comparisons"][0][field] = value

    with pytest.raises(ValueError, match=message):
        module.derive_eia_residual_evidence(
            benchmark,
            protocol,
            protocol_path=benchmark["protocol"]["path"],
            protocol_sha256=benchmark["protocol"]["sha256"],
        )


def test_context_fails_closed_when_eia_residual_source_is_malformed(tmp_path, monkeypatch):
    module = load_module()
    malformed = tmp_path / "malformed_eia_residual.json"
    malformed.write_text(
        json.dumps({"schema": "eia_grid_residual_moe_benchmark.v1"}),
        encoding="utf-8",
    )
    original_repo_path = module.repo_path

    def test_repo_path(path: Path) -> str:
        try:
            return original_repo_path(path)
        except ValueError:
            return f"tmp/{path.name}"

    monkeypatch.setattr(module, "repo_path", test_repo_path)
    monkeypatch.setitem(module.SOURCE_PATHS, "eia_residual_benchmark", malformed)
    with pytest.raises(ValueError, match=r"eia_residual_benchmark\.protocol"):
        module.build_context()
