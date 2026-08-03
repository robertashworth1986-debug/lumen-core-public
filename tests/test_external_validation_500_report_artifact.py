from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "code" / "ops" / "BUILD_EXTERNAL_VALIDATION_500_REPORT_ARTIFACT.py"
)
ARTIFACT = ROOT / "out" / "reports" / "external_validation_500_sprint" / "artifact.json"
REPORT_DATA = (
    ROOT / "out" / "reports" / "external_validation_500_sprint" / "report_data.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "external_validation_500_report_artifact", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_report_data_reconciles_budget_tests_and_validation_state():
    module = load_module()
    data = module.build_report_data(generated_utc="2026-07-16T00:00:00+00:00")
    sprint = json.loads(module.SPRINT_PATH.read_text(encoding="utf-8"))

    assert data["budget_usd"] == 500
    assert data["estimated_reviewer_hours"] == 10
    assert data["focused_test_receipt"]["tests"] == 33
    assert data["focused_test_receipt"]["clean"] is True
    assert data["current_state"]["repository_supported_level"] == 3
    assert data["current_state"]["authorities_with_valid_seals"] == 6
    assert data["current_state"]["common_settled_hour_count"] == sprint[
        "current_state"
    ]["common_settled_hour_count"]
    assert data["current_state"]["common_settled_hour_count"] >= 0
    assert sum(row["amount_usd"] for row in data["budget_allocation"]) == 500


def test_report_artifact_has_complete_reading_path_and_reproducible_sources():
    module = load_module()
    data = module.build_report_data(generated_utc="2026-07-16T00:00:00+00:00")
    artifact = module.build_artifact(data)
    manifest = artifact["manifest"]

    assert artifact["surface"] == "report"
    assert manifest["title"] == module.TITLE
    assert manifest["blocks"][0]["body"] == f"# {module.TITLE}"
    assert any(
        block.get("body", "").startswith("## Executive Summary")
        for block in manifest["blocks"]
    )
    assert any(block["type"] == "chart" for block in manifest["blocks"])
    assert any(block["type"] == "table" for block in manifest["blocks"])
    assert len(manifest["charts"]) == 1
    assert len(manifest["tables"]) == 1
    assert "read_json_auto" in manifest["charts"][0]["source"]["query"]["sql"]
    assert "read_json_auto" in manifest["tables"][0]["source"]["query"]["sql"]
    assert len(artifact["snapshot"]["datasets"]["gate_progress"]) == 5
    assert len(artifact["snapshot"]["datasets"]["budget_allocation"]) == 3


def test_published_artifact_matches_the_compiled_report_data():
    module = load_module()
    published_data = json.loads(REPORT_DATA.read_text(encoding="utf-8"))
    published_artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    rebuilt = module.build_artifact(published_data)

    assert published_artifact == rebuilt
