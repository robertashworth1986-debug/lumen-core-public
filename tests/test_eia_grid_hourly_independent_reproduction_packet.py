from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = (
    ROOT / "code" / "ops" / "VERIFY_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py"
)
BUILDER_PATH = (
    ROOT / "code" / "ops" / "BUILD_EIA_GRID_HOURLY_REPRODUCTION_PACKET.py"
)
PUBLIC_HANDOFFS = (
    (
        ROOT
        / "evidence"
        / "external_validation"
        / "eia_grid_hourly_independent_reproduction_handoff_20260716.json",
        95,
        84,
    ),
    (
        ROOT
        / "evidence"
        / "external_validation"
        / "eia_grid_hourly_independent_reproduction_handoff_20260721.json",
        486,
        469,
    ),
)
EVALUATOR_TEMPLATE_PATH = (
    ROOT
    / "config"
    / "eia_grid_hourly_external_evaluator_protocol_template_v1.json"
)


def load_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_packet_source_bytes_match_current_commit() -> None:
    builder = load_path(BUILDER_PATH, "eia_reproduction_builder_source_state")

    state = builder.git_source_state()

    assert state["all_packet_sources_match_commit"] is True
    assert state["byte_exact_source_count"] == state["tracked_source_count"]


def test_publish_targets_are_explicit_distinct_and_append_only(tmp_path: Path) -> None:
    builder = load_path(BUILDER_PATH, "eia_reproduction_builder_publish_policy")
    public_manifest = ROOT / "out" / "reviewer_handoffs" / "new_handoff.json"
    receipt_template = ROOT / "out" / "reviewer_handoffs" / "new_template.json"

    builder.require_new_publish_targets(public_manifest, receipt_template)

    with pytest.raises(ValueError, match="distinct files"):
        builder.require_new_publish_targets(public_manifest, public_manifest)

    existing = tmp_path / "existing.json"
    existing.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="repository root"):
        builder.require_new_publish_targets(existing, receipt_template)

    existing = ROOT / "out" / "reviewer_handoffs" / "existing_test_target.json"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("{}\n", encoding="utf-8")
    try:
        with pytest.raises(FileExistsError, match="refusing to overwrite"):
            builder.require_new_publish_targets(existing, receipt_template)
    finally:
        existing.unlink()


def test_cli_requires_explicit_publish_targets() -> None:
    builder = load_path(BUILDER_PATH, "eia_reproduction_builder_cli_policy")

    with pytest.raises(SystemExit):
        builder.build_parser().parse_args([])

    args = builder.build_parser().parse_args(
        [
            "--public-manifest",
            "out/reviewer_handoffs/new_handoff.json",
            "--receipt-template-output",
            "out/reviewer_handoffs/new_template.json",
        ]
    )
    assert args.public_manifest == Path("out/reviewer_handoffs/new_handoff.json")
    assert args.receipt_template_output == Path(
        "out/reviewer_handoffs/new_template.json"
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_chain(path: Path, records: list[dict], verifier) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    previous = verifier.ZERO_HASH
    output = []
    for record in records:
        sealed = dict(record)
        sealed["prior_record_chain_sha256"] = previous
        sealed["record_sha256"] = verifier.canonical_sha256(sealed)
        output.append(sealed)
        previous = sealed["record_sha256"]
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in output),
        encoding="utf-8",
    )
    return output


def synthetic_packet(tmp_path: Path, verifier) -> Path:
    packet = tmp_path / "packet"
    protocol = {
        "schema": "eia_grid_prospective_hourly_router_protocol.v1",
        "protocol_id": "SYNTHETIC_EIA_HOURLY_TEST",
        "balancing_authorities": ["A", "B"],
        "candidates": [
            {"id": "official", "definition": "fixture"},
            {"id": "alternate", "definition": "fixture"},
        ],
        "router": {
            "route_map": {"A": "official", "B": "official"},
            "dynamic_override_allowed": False,
        },
        "prospective_window": {
            "first_allowed_period_end_utc": "2026-07-16T00",
            "preliminary_gate_common_hours_per_authority": 2,
            "confirmatory_gate_common_hours_per_authority": 3,
            "durability_gate_common_hours_per_authority": 4,
            "backfilled_predictions_allowed": False,
        },
        "claim_boundary": "Synthetic unit-test fixture; no performance claim.",
    }
    protocol_path = packet / verifier.PROTOCOL_RELATIVE
    write_json(protocol_path, protocol)
    protocol_hash = verifier.normalized_text_sha256(protocol_path)
    source_rows = [
        {
            "period": "2026-07-16T00",
            "respondent": authority,
            "respondent_name": authority,
            "type": kind,
            "type_name": kind,
            "value": value,
            "value_units": "megawatthours",
        }
        for authority, base in (("A", 100.0), ("B", 200.0))
        for kind, value in (("D", base), ("DF", base + 1.0))
    ]
    source = {
        "schema": "eia_grid_hourly_source_cache.v1",
        "row_count": len(source_rows),
        "row_chain_sha256": verifier.canonical_sha256(source_rows),
        "rows": source_rows,
    }
    write_json(packet / verifier.SOURCE_CACHE_RELATIVE, source)
    prediction_records = write_chain(
        packet / verifier.PREDICTIONS_RELATIVE,
        [
            {
                "schema": "eia_grid_prospective_hourly_router_prediction.v1",
                "respondent": "A",
                "respondent_name": "Authority A",
                "target_period_end_utc": "2026-07-16T02",
                "target_interval_start_utc": "2026-07-16T01:00:00+00:00",
                "sealed_utc": "2026-07-16T00:30:00+00:00",
                "seal_lead_seconds": 1800.0,
                "source_receipt_sha256": "1" * 64,
                "source_panel_row_chain_sha256": source["row_chain_sha256"],
                "protocol_sha256": protocol_hash,
                "protocol_commit": "a" * 40,
                "candidate_predictions_mwh": {
                    "official": 100.0,
                    "alternate": 110.0,
                },
                "selected_candidate": "official",
                "router_prediction_mwh": 100.0,
                "scale_mwh": 10.0,
                "feature_sha256": "2" * 64,
                "training_rows_sha256": "3" * 64,
                "target_actual_present_at_seal": False,
                "backfilled": False,
            }
        ],
        verifier,
    )
    settlement_records = write_chain(
        packet / verifier.SETTLEMENTS_RELATIVE,
        [
            {
                "schema": "eia_grid_prospective_hourly_router_settlement.v1",
                "settled_utc": "2026-07-16T03:00:00+00:00",
                "respondent": "A",
                "target_period_end_utc": "2026-07-16T02",
                "prediction_record_sha256": prediction_records[0]["record_sha256"],
                "actual_mwh": 105.0,
                "candidate_metrics": {
                    "official": {
                        "absolute_error_mwh": 5.0,
                        "scaled_absolute_error": 0.5,
                    },
                    "alternate": {
                        "absolute_error_mwh": 5.0,
                        "scaled_absolute_error": 0.5,
                    },
                },
                "selected_candidate": "official",
                "router_scaled_absolute_error": 0.5,
                "oracle_candidate": "alternate",
                "oracle_scaled_absolute_error": 0.5,
                "router_regret_to_oracle": 0.0,
                "route_hit": False,
            }
        ],
        verifier,
    )
    status = {
        "schema": "eia_grid_prospective_hourly_router_status.v1",
        "generated_utc": "2026-07-16T03:00:01+00:00",
        "state": "PROSPECTIVE_COLLECTION_ACTIVE",
        "protocol_sha256": protocol_hash,
        "protocol_commit": "a" * 40,
        "prediction_count": 1,
        "settlement_count": 1,
        "common_settled_hour_count": 0,
        "first_common_settled_period": None,
        "latest_common_settled_period": None,
        "router_mean_scaled_absolute_error": 0.5,
        "fixed_candidate_mean_scaled_absolute_error": {
            "official": 0.5,
            "alternate": 0.5,
        },
        "current_best_fixed_candidate": "alternate",
        "router_skill_vs_current_best_fixed": 0.0,
        "sample_gates": {
            "preliminary_ready": False,
            "confirmatory_ready": False,
            "durability_ready": False,
            "note": "fixture",
        },
        "promotion_evaluation_complete": False,
        "claim_boundary": protocol["claim_boundary"],
    }
    receipt = {
        "schema": "eia_grid_prospective_hourly_router_operational_run.v1",
        "run_utc": "2026-07-16T03:00:02+00:00",
        "protocol_sha256": protocol_hash,
        "protocol_commit": "a" * 40,
        "source_panel_row_count": source["row_count"],
        "source_panel_row_chain_sha256": source["row_chain_sha256"],
        "prediction_count": 1,
        "prediction_terminal_sha256": prediction_records[-1]["record_sha256"],
        "settlement_count": 1,
        "settlement_terminal_sha256": settlement_records[-1]["record_sha256"],
        "status_sha256": verifier.canonical_sha256(status),
    }
    operation_records = write_chain(
        packet / verifier.OPERATIONS_RELATIVE,
        [receipt],
        verifier,
    )
    status["operational_receipt_sha256"] = operation_records[-1]["record_sha256"]
    write_json(packet / verifier.STATUS_RELATIVE, status)
    write_json(
        packet / verifier.CYCLE_RELATIVE,
        {
            "schema": "eia_grid_prospective_hourly_router_cycle.v1",
            "status": status,
            "operational_receipt": operation_records[-1],
        },
    )
    artifact_paths = [
        verifier.PROTOCOL_RELATIVE.as_posix(),
        verifier.SOURCE_CACHE_RELATIVE.as_posix(),
        verifier.PREDICTIONS_RELATIVE.as_posix(),
        verifier.SETTLEMENTS_RELATIVE.as_posix(),
        verifier.OPERATIONS_RELATIVE.as_posix(),
        verifier.STATUS_RELATIVE.as_posix(),
        verifier.CYCLE_RELATIVE.as_posix(),
    ]
    snapshot = verifier.audit_snapshot(packet)
    manifest = {
        "schema": verifier.EXPECTED_MANIFEST_SCHEMA,
        "created_utc": "2026-07-16T03:00:03+00:00",
        "packet_id": "SYNTHETIC_PACKET",
        "artifacts": [
            {
                "path": relative,
                "bytes": (packet / relative).stat().st_size,
                "sha256": verifier.file_sha256(packet / relative),
            }
            for relative in sorted(artifact_paths)
        ],
        "frozen_snapshot": snapshot,
        "manifest_payload_sha256": None,
    }
    manifest["manifest_payload_sha256"] = verifier.manifest_payload_sha256(manifest)
    write_json(packet / verifier.MANIFEST_NAME, manifest)
    return packet


def completed_receipt(builder, verifier, report: dict, tmp_path: Path):
    receipt = builder.build_receipt_template(report)
    independence = tmp_path / "independence.txt"
    signature = tmp_path / "signature.txt"
    independence.write_text("independent reviewer evidence", encoding="utf-8")
    signature.write_text("reviewer signature artifact", encoding="utf-8")
    receipt["reviewer"] = {
        "name": "Independent Reviewer",
        "organization": "Independent Laboratory",
        "technical_role": "Reproduction evaluator",
        "contact_channel": "reviewer@example.invalid",
        "conflict_of_interest_disclosure": "No financial relationship disclosed.",
        "independence_basis": "No role in protocol design or original execution.",
        "independence_evidence_sha256": verifier.file_sha256(independence),
    }
    snapshot = report["snapshot"]
    receipt["reproduction"] = {
        "executed_utc": "2026-07-16T04:00:00Z",
        "decision": "REPRODUCED_FROZEN_SNAPSHOT",
        "environment_summary": "Fresh Python standard-library environment.",
        "packet_rehashed": True,
        "packet_hashes_match": True,
        "source_cache_chain_verified": True,
        "prediction_chain_verified": True,
        "settlement_chain_verified": True,
        "operational_chain_verified": True,
        "settlement_metrics_recomputed": True,
        "authority_coverage_recomputed": True,
        "prediction_count": snapshot["prediction_count"],
        "settlement_count": snapshot["settlement_count"],
        "common_settled_hour_count": snapshot["common_settled_hour_count"],
        "zero_prospective_seal_authorities": snapshot[
            "zero_prospective_seal_authorities"
        ],
        "prediction_terminal_sha256": snapshot["prediction_terminal_sha256"],
        "settlement_terminal_sha256": snapshot["settlement_terminal_sha256"],
        "operational_terminal_sha256": snapshot["operational_terminal_sha256"],
        "notes": "Frozen snapshot and incomplete panel reproduced.",
        "operator_filled_reviewer_fields": False,
    }
    receipt["signature"] = {
        "method": "signed_email",
        "signed_payload_sha256": None,
        "detached_signature_artifact_sha256": verifier.file_sha256(signature),
    }
    receipt["signature"]["signed_payload_sha256"] = (
        verifier.receipt_signing_payload_sha256(receipt)
    )
    return receipt, independence, signature


def test_packet_and_unsigned_receipt_verify_offline(tmp_path: Path):
    verifier = load_path(VERIFIER_PATH, "eia_reproduction_verifier_packet")
    builder = load_path(BUILDER_PATH, "eia_reproduction_builder_packet")
    packet = synthetic_packet(tmp_path, verifier)

    report = verifier.verify_packet(packet)
    receipt = builder.build_receipt_template(report)
    receipt_report = verifier.validate_receipt(receipt, report, expect_template=True)

    assert report["packet_integrity_passed"] is True
    assert report["snapshot"]["zero_prospective_seal_authorities"] == ["B"]
    assert report["snapshot"]["common_settled_hour_count"] == 0
    assert receipt_report["independent_reproduction_complete"] is False
    assert receipt_report["performance_promotion_allowed"] is False


def test_settlement_metric_tamper_fails_closed(tmp_path: Path):
    verifier = load_path(VERIFIER_PATH, "eia_reproduction_verifier_tamper")
    packet = synthetic_packet(tmp_path, verifier)
    settlement_path = packet / verifier.SETTLEMENTS_RELATIVE
    settlement = json.loads(settlement_path.read_text(encoding="utf-8").splitlines()[0])
    settlement["candidate_metrics"]["official"]["absolute_error_mwh"] = 0.0
    unsigned = dict(settlement)
    unsigned.pop("record_sha256")
    settlement["record_sha256"] = verifier.canonical_sha256(unsigned)
    settlement_path.write_text(json.dumps(settlement) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        verifier.verify_packet(packet)


def test_completed_reviewer_receipt_binds_exact_snapshot(tmp_path: Path):
    verifier = load_path(VERIFIER_PATH, "eia_reproduction_verifier_receipt")
    builder = load_path(BUILDER_PATH, "eia_reproduction_builder_receipt")
    packet = synthetic_packet(tmp_path, verifier)
    report = verifier.verify_packet(packet)
    receipt, independence, signature = completed_receipt(
        builder, verifier, report, tmp_path
    )

    receipt_report = verifier.validate_receipt(
        receipt,
        report,
        expect_template=False,
        independence_artifact=independence,
        signature_artifact=signature,
    )

    assert receipt_report["receipt_integrity_passed"] is True
    assert receipt_report["independent_reproduction_complete"] is True
    assert receipt_report["performance_promotion_allowed"] is False


def test_operator_cannot_promote_performance(tmp_path: Path):
    verifier = load_path(VERIFIER_PATH, "eia_reproduction_verifier_promotion")
    builder = load_path(BUILDER_PATH, "eia_reproduction_builder_promotion")
    packet = synthetic_packet(tmp_path, verifier)
    report = verifier.verify_packet(packet)
    receipt = builder.build_receipt_template(report)
    receipt["performance_promotion_allowed"] = True

    with pytest.raises(ValueError, match="performance promotion"):
        verifier.validate_receipt(receipt, report, expect_template=True)


@pytest.mark.parametrize(
    ("manifest_path", "expected_predictions", "expected_settlements"),
    PUBLIC_HANDOFFS,
)
def test_public_handoff_keeps_raw_runtime_private_and_template_blank(
    manifest_path: Path,
    expected_predictions: int,
    expected_settlements: int,
):
    verifier = load_path(VERIFIER_PATH, "eia_reproduction_verifier_public")
    handoff = json.loads(manifest_path.read_text(encoding="utf-8"))
    template_path = ROOT / handoff["receipt_template"]["path"]
    template = json.loads(template_path.read_text(encoding="utf-8"))

    assert handoff["status"] == "UNSIGNED_REVIEWER_HANDOFF_READY"
    assert handoff["packet"]["private_runtime_payload_published_in_repository"] is False
    assert handoff["frozen_snapshot"]["independent_reproduction_complete"] is False
    assert handoff["frozen_snapshot"]["prediction_count"] == expected_predictions
    assert handoff["frozen_snapshot"]["settlement_count"] == expected_settlements
    assert handoff["frozen_snapshot"]["common_settled_hour_count"] == 0
    assert not any(handoff["frozen_snapshot"]["sample_gates"].values())
    assert handoff["performance_promotion_allowed"] is False
    assert verifier.file_sha256(template_path) == handoff["receipt_template"][
        "sha256"
    ]
    assert all(value is None for value in template["reviewer"].values())
    assert all(value is None for value in template["reproduction"].values())
    assert all(value is None for value in template["signature"].values())


def test_external_evaluator_template_locks_scientific_floors():
    verifier = load_path(VERIFIER_PATH, "eia_reproduction_verifier_evaluator")
    evaluator = json.loads(EVALUATOR_TEMPLATE_PATH.read_text(encoding="utf-8"))

    report = verifier.validate_evaluator_protocol(evaluator, expect_template=True)

    assert report["protocol_integrity_passed"] is True
    assert report["evaluation_design_frozen"] is False
    assert report["performance_promotion_allowed"] is False

    evaluator["scientific_floors"]["minimum_common_hours_per_authority"] = 24
    with pytest.raises(ValueError, match="scientific floors"):
        verifier.validate_evaluator_protocol(evaluator, expect_template=True)
