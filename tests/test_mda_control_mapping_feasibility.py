from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "mda_control_mapping_feasibility.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mda_control_feasibility", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fixture_generation_is_deterministic_and_matches_frozen_splits():
    module = load_module()
    protocol = module.load_protocol()
    first = module.generate_fixtures(protocol)
    second = module.generate_fixtures(protocol)
    assert first == second
    assert len(first) == 96
    assert sum(row["split"] == "development" for row in first) == 48
    assert sum(row["split"] == "validation" for row in first) == 24
    assert sum(row["split"] == "blind_holdout" for row in first) == 24
    assert sum(row["label_status"] == "ambiguous" for row in first) == 16
    assert sum(row["label_status"] == "unsupported" for row in first) == 8
    assert not [row for row in first if module.validate_fixture(row, protocol)]


def test_score_predictions_penalizes_unsupported_mapping():
    module = load_module()
    records = [
        {
            "fixture_id": "a",
            "expected_controls": ["AC-2"],
            "label_status": "supported",
        },
        {
            "fixture_id": "b",
            "expected_controls": [],
            "label_status": "unsupported",
        },
    ]
    metrics = module.score_predictions(
        records,
        {"a": ["AC-2"], "b": ["AC-2"]},
        ["AC-2"],
    )
    assert metrics["micro_f1"] == pytest.approx(2 / 3)
    assert metrics["unsupported_mapping_rate"] == 1.0


def test_benchmark_uses_validation_for_thresholds_and_emits_receipts(tmp_path):
    module = load_module()
    output = tmp_path / "out"
    doc = tmp_path / "result.md"
    result = module.run_benchmark(output_dir=output, doc_path=doc)
    repeated = module.run_benchmark(
        output_dir=tmp_path / "repeat",
        doc_path=tmp_path / "repeat.md",
    )
    assert result["protocol_commit"]
    assert result["thresholds"]["selection_split"] == "validation"
    assert result["fixture_counts"] == {
        "total": 96,
        "development": 48,
        "validation": 24,
        "blind_holdout": 24,
        "parser_rejections": 0,
    }
    assert result["gate"]["operational_or_field_claim_allowed"] is False
    for field in ("fixture_chain_sha256", "thresholds", "holdout_metrics", "gate"):
        assert repeated[field] == result[field]
    assert (output / "synthetic_fixtures_latest.jsonl").exists()
    assert (output / "fixture_manifest_latest.json").exists()
    assert (output / "split_manifest_latest.json").exists()
    assert (output / "threshold_selection_receipt_latest.json").exists()
    assert (output / "holdout_predictions_latest.jsonl").exists()
    assert (output / "mda_control_mapping_feasibility_manifest_latest.json").exists()
    threshold_receipt = json.loads(
        (output / "threshold_selection_receipt_latest.json").read_text(encoding="utf-8")
    )
    assert threshold_receipt["selection_split"] == "validation"
    assert threshold_receipt["holdout_used_for_selection"] is False
    split_manifest = json.loads(
        (output / "split_manifest_latest.json").read_text(encoding="utf-8")
    )
    assert split_manifest["split_counts"] == {
        "development": 48,
        "validation": 24,
        "blind_holdout": 24,
    }
    events = [
        json.loads(line)
        for line in (output / "failure_and_abstention_log_latest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events
    assert any("UNSUPPORTED_MAPPING" in row["reason_codes"] for row in events)
    assert doc.exists()
