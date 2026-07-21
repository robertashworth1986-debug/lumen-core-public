from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "mda_control_mapping_open_set_benchmark.py"


def load_module():
    spec = importlib.util.spec_from_file_location("mda_control_open_set", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v2_fixtures_are_independent_deterministic_and_stratified():
    module = load_module()
    protocol = module.load_protocol()
    first = module.generate_fixtures(protocol)
    second = module.generate_fixtures(protocol)
    assert first == second
    assert len(first) == 128
    assert sum(row["split"] == "development" for row in first) == 56
    assert sum(row["split"] == "validation" for row in first) == 36
    assert sum(row["split"] == "blind_holdout" for row in first) == 36
    assert sum(row["label_status"] == "unsupported" for row in first) == 32
    assert all(row["fixture_id"].startswith("V2-") for row in first)
    assert not [row for row in first if module.validate_fixture(row, protocol)]


def test_open_set_metrics_separate_supported_coverage_from_unsupported_mapping():
    module = load_module()
    records = [
        {
            "fixture_id": "supported",
            "expected_controls": ["AC-2"],
            "label_status": "supported",
        },
        {
            "fixture_id": "unsupported",
            "expected_controls": [],
            "label_status": "unsupported",
        },
    ]
    metrics = module.score_predictions(
        records,
        {"supported": ["AC-2"], "unsupported": ["AC-2"]},
        ["AC-2"],
    )
    assert metrics["supported_coverage"] == 1.0
    assert metrics["overall_coverage"] == 1.0
    assert metrics["unsupported_mapping_rate"] == 1.0
    assert metrics["micro_f1"] == pytest.approx(2 / 3)


def test_v2_benchmark_emits_complete_reproducible_receipts(tmp_path):
    module = load_module()
    output = tmp_path / "out"
    doc_path = tmp_path / "result.md"
    result = module.run_benchmark(output_dir=output, doc_path=doc_path)
    repeated = module.run_benchmark(
        output_dir=tmp_path / "repeat",
        doc_path=tmp_path / "repeat.md",
    )
    assert result["protocol_commit"] == "ff610a147b79350a37f92cfa65853cd402885922"
    assert result["thresholds"]["fit_split"] == "development"
    assert result["thresholds"]["selection_split"] == "validation"
    assert result["thresholds"]["holdout_used_for_selection"] is False
    assert result["gate"]["operational_or_field_claim_allowed"] is False
    rendered = doc_path.read_text(encoding="utf-8")
    assert result["protocol_commit"] in rendered
    assert result["protocol_sha256"] in rendered
    assert result["fixture_chain_sha256"] in rendered
    assert result["fixture_counts"] == {
        "total": 128,
        "development": 56,
        "validation": 36,
        "blind_holdout": 36,
        "supported": 96,
        "unsupported": 32,
        "parser_rejections": 0,
    }
    for field in ("fixture_chain_sha256", "thresholds", "holdout_metrics", "gate"):
        assert repeated[field] == result[field]

    required = {
        "synthetic_open_set_fixtures_latest.jsonl",
        "fixture_manifest_latest.json",
        "split_manifest_latest.json",
        "threshold_selection_receipt_latest.json",
        "holdout_predictions_latest.jsonl",
        "failure_and_abstention_log_latest.jsonl",
        "mda_control_mapping_open_set_latest.json",
    }
    manifest = json.loads(
        (output / "mda_control_mapping_open_set_manifest_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert set(manifest["artifacts"]) == required
    threshold_receipt = json.loads(
        (output / "threshold_selection_receipt_latest.json").read_text(encoding="utf-8")
    )
    assert threshold_receipt["holdout_used_for_selection"] is False
    events = [
        json.loads(line)
        for line in (output / "failure_and_abstention_log_latest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events
    assert any("ABSTAIN" in row["reason_codes"] for row in events)
