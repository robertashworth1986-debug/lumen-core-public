from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_EIA_HOURLY_RUNTIME_PROJECTION.py"
SPEC = importlib.util.spec_from_file_location("eia_hourly_runtime_projection", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    protocol = {
        "schema": "eia_grid_prospective_hourly_router_protocol.v1",
        "protocol_id": "TEST_HOURLY_PROTOCOL",
        "prospective_window": {
            "preliminary_gate_common_hours_per_authority": 168,
            "confirmatory_gate_common_hours_per_authority": 720,
            "durability_gate_common_hours_per_authority": 2160,
        },
    }
    protocol_path = root / MODULE.PROTOCOL_RELATIVE
    write_json(protocol_path, protocol)
    protocol_sha256 = MODULE.sha256_file(protocol_path)
    status = {
        "schema": "eia_grid_prospective_hourly_router_status.v1",
        "generated_utc": "2026-07-16T02:00:00+00:00",
        "state": "PROSPECTIVE_COLLECTION_ACTIVE",
        "prediction_count": 16,
        "settlement_count": 8,
        "common_settled_hour_count": 1,
        "first_common_settled_period": "2026-07-16T01",
        "latest_common_settled_period": "2026-07-16T01",
        "sample_gates": {
            "preliminary_ready": False,
            "confirmatory_ready": False,
            "durability_ready": False,
        },
        "promotion_evaluation_complete": False,
        "current_best_fixed_candidate": "fixed_a",
        "fixed_candidate_mean_scaled_absolute_error": {"fixed_a": 0.8},
        "router_mean_scaled_absolute_error": 0.7,
        "router_skill_vs_current_best_fixed": 0.1,
        "operational_receipt_sha256": "a" * 64,
        "protocol_sha256": protocol_sha256,
        "protocol_commit": "b" * 40,
        "claim_boundary": "Incomplete prospective evidence; no field or economic claim.",
    }
    receipt = {
        "schema": "eia_grid_prospective_hourly_router_operational_run.v1",
        "record_sha256": "a" * 64,
        "prediction_count": 16,
        "settlement_count": 8,
        "prediction_terminal_sha256": "c" * 64,
        "settlement_terminal_sha256": "d" * 64,
        "source_panel_row_chain_sha256": "e" * 64,
        "source_panel_row_count": 1000,
        "protocol_sha256": protocol_sha256,
        "protocol_commit": "b" * 40,
    }
    cycle = {
        "schema": "eia_grid_prospective_hourly_router_cycle.v1",
        "status": status,
        "operational_receipt": receipt,
    }
    write_json(root / MODULE.STATUS_RELATIVE, status)
    write_json(root / MODULE.CYCLE_RELATIVE, cycle)
    return root


def test_projection_reconciles_counts_protocol_and_terminal_chains(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    projection = MODULE.build_projection(root=root)

    assert projection["integrity"]["gate_passed"] is True
    assert all(projection["integrity"]["checks"].values())
    assert projection["sample_state"]["prediction_count"] == 16
    assert projection["sample_state"]["settlement_count"] == 8
    assert projection["sample_state"]["common_settled_hour_count"] == 1
    assert projection["descriptive_metrics"]["sample_gate_open"] is False
    assert projection["runtime_snapshot"]["raw_runtime_in_public_repository"] is False

    target = MODULE.write_projection(projection, root=root)
    assert json.loads(target.read_text(encoding="utf-8")) == projection


def test_projection_fails_closed_on_count_drift(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    cycle_path = root / MODULE.CYCLE_RELATIVE
    cycle = json.loads(cycle_path.read_text(encoding="utf-8"))
    cycle["operational_receipt"]["settlement_count"] = 7
    write_json(cycle_path, cycle)

    with pytest.raises(ValueError, match="settlement_count_reconciled"):
        MODULE.build_projection(root=root)


def test_projection_fails_closed_on_protocol_drift(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    status_path = root / MODULE.STATUS_RELATIVE
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["protocol_sha256"] = "f" * 64
    write_json(status_path, status)
    cycle_path = root / MODULE.CYCLE_RELATIVE
    cycle = json.loads(cycle_path.read_text(encoding="utf-8"))
    cycle["status"] = status
    write_json(cycle_path, cycle)

    with pytest.raises(ValueError, match="protocol_identity_matched"):
        MODULE.build_projection(root=root)


def test_projection_rejects_private_path_content(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    status_path = root / MODULE.STATUS_RELATIVE
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["claim_boundary"] = "C:/Users/private/path"
    write_json(status_path, status)
    cycle_path = root / MODULE.CYCLE_RELATIVE
    cycle = json.loads(cycle_path.read_text(encoding="utf-8"))
    cycle["status"] = status
    write_json(cycle_path, cycle)

    with pytest.raises(ValueError, match="public-safety scan"):
        MODULE.build_projection(root=root)


def test_projection_writes_explicit_immutable_output_inside_repository(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    projection = MODULE.build_projection(root=root)
    output = Path(
        "evidence/external_validation/eia_grid_prospective_hourly_runtime_projection_20260721.json"
    )

    target = MODULE.write_projection(projection, root=root, output=output)

    assert target == root / output
    assert json.loads(target.read_text(encoding="utf-8")) == projection


def test_projection_rejects_output_outside_repository(tmp_path: Path) -> None:
    root = fixture_root(tmp_path)
    projection = MODULE.build_projection(root=root)

    with pytest.raises(ValueError, match="must remain inside"):
        MODULE.write_projection(
            projection,
            root=root,
            output=root.parent / "escaped_projection.json",
        )


def test_committed_projection_is_protocol_bound_and_public_safe() -> None:
    projection = MODULE.read_json(ROOT / MODULE.OUTPUT_RELATIVE)
    protocol_path = ROOT / MODULE.PROTOCOL_RELATIVE
    protocol = MODULE.read_json(protocol_path)

    MODULE.validate_public_projection(
        projection,
        protocol,
        protocol_sha256=MODULE.sha256_file(protocol_path),
    )
    assert projection["sample_state"]["prediction_count"] == 95
    assert projection["sample_state"]["settlement_count"] == 84
    assert projection["sample_state"]["common_settled_hour_count"] == 0
    assert projection["descriptive_metrics"]["sample_gate_open"] is False
