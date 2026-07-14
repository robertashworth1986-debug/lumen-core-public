from __future__ import annotations

import csv
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FAA_SDR_SOURCE_AUDIT.py"


def load_module():
    spec = importlib.util.spec_from_file_location("faa_sdr_source_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_fixture(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = sorted(load_module().REQUIRED_COLUMNS)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def test_faa_sdr_audit_forms_unique_holdout_and_keeps_rolls_exploratory(tmp_path: Path):
    module = load_module()
    development = tmp_path / "SDR-2025.csv"
    holdout = tmp_path / "SDR-2026.csv"
    write_fixture(
        development,
        [
            {
                "OperatorControlNumber": "DEV-1",
                "DifficultyDate": "12/31/2025",
                "JASCCode": "7200",
                "AircraftMake": "AIRBUS",
                "PartName": "ENGINE",
                "PartCondition": "FAILED",
                "Discrepancy": "fixture",
            }
        ],
    )
    write_fixture(
        holdout,
        [
            {
                "OperatorControlNumber": "TEST-1",
                "DifficultyDate": "01/01/2026",
                "JASCCode": "7200",
                "AircraftMake": "AIRBUS",
                "EngineMake": "RROYCE",
                "EngineModel": "RB211TRENT77",
                "PartName": "ENGINE",
                "PartCondition": "FAILED",
                "Discrepancy": "fixture",
            },
            {
                "OperatorControlNumber": "TEST-2",
                "DifficultyDate": "01/02/2026",
                "JASCCode": "5300",
                "AircraftMake": "BOEING",
                "PartName": "SKIN",
                "PartCondition": "CRACKED",
                "Discrepancy": "fixture",
            },
        ],
    )

    payload = module.build_payload([development, holdout], holdout_target=2)

    assert payload["summary"]["row_count"] == 3
    assert payload["summary"]["unique_nonempty_keys"] == 3
    assert payload["summary"]["duplicate_key_rows"] == 0
    assert payload["summary"]["rolls_royce_family_rows"] == 1
    assert payload["ten_thousand_protocol_readiness"]["selected_unique_rows"] == 2
    assert payload["ten_thousand_protocol_readiness"]["selection_feasible"] is True
    assert payload["ten_thousand_protocol_readiness"]["rolls_royce_specific_10k_gate"] is False
    assert payload["claim_matrix"]["faa_validation_claim_allowed"] is False
    assert payload["claim_matrix"]["oem_validation_claim_allowed"] is False
    assert len(payload["receipt_sha256"]) == 64


def test_faa_sdr_markdown_names_volume_and_claim_boundary(tmp_path: Path):
    module = load_module()
    source = tmp_path / "SDR-2026.csv"
    write_fixture(
        source,
        [
            {
                "OperatorControlNumber": "TEST-1",
                "DifficultyDate": "01/01/2026",
                "JASCCode": "7200",
                "PartName": "ENGINE",
                "PartCondition": "FAILED",
                "Discrepancy": "fixture",
            }
        ],
    )

    rendered = module.render_markdown(module.build_payload([source], holdout_target=1))

    assert "Report-level 10,000-row holdout feasible: `true`" in rendered
    assert "not estimate failure rates" in rendered
    assert "not a trusted-engine validation claim" in rendered
