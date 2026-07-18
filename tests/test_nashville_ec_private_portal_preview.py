from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NASHVILLE_EC_PRIVATE_PORTAL_PREVIEW.py"
MANIFEST_PATH = (
    ROOT
    / "grant_submissions"
    / "NASHVILLE_EC_FALL_2026"
    / "NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("nashville_ec_private_preview", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sample_maps(module, manifest):
    founder_values = {
        38: "Yes",
        31: "1 to 3 years",
        28: "Yes",
        29: "30+",
        84: "1 to 10",
        66: "$0",
        36: "$0",
        63: "$0",
        64: "$0",
        62: "$10000",
        65: "$0",
    }
    assert set(founder_values) == {
        row["question_id"]
        for row in manifest["fields"]
        if row["status"] == "HUMAN_CONFIRM_REQUIRED"
    }
    founder = {
        "schema": module.FOUNDER_MAP_SCHEMA,
        "question_answers": [
            {"question_id": question_id, "value": value}
            for question_id, value in founder_values.items()
        ],
    }
    contact = {
        "schema": module.CONTACT_MAP_SCHEMA,
        "question_answers": [
            {"question_id": 4, "value": "founder@example.com"},
            {"question_id": 75, "value": None, "disposition": "OMIT_OPTIONAL"},
        ],
    }
    return founder, contact


def test_private_preview_assembles_all_required_answers_and_classifies_founder_cash():
    module = load_module()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    founder, contact = sample_maps(module, manifest)
    result = module.build_preview(
        manifest,
        founder,
        contact,
        generated_utc="2026-07-18T01:00:00+00:00",
    )
    answers = {row["question_id"]: row for row in result["fields"]}

    assert result["status"] == "PORTAL_FILL_ASSEMBLED_FINAL_HUMAN_ACTION_GATED"
    assert result["private_portal_only"] is True
    assert result["public_repo_publish_allowed"] is False
    assert result["summary"]["field_count"] == 41
    assert result["summary"]["required_ready_count"] == 30
    assert result["summary"]["required_unresolved_count"] == 0
    assert answers[4]["answer"] == "founder@example.com"
    assert answers[62]["answer"] == "$10000"
    assert answers[63]["answer"] == "$0"
    assert answers[64]["answer"] == "$0"
    assert answers[75]["entry_status"] == "OPTIONAL_OMITTED"
    assert "not outside funding" in result["financial_classification_guardrail"][
        "question_62_founder_cash"
    ]
    assert result["final_action_gate"]["all_required_answers_assembled"] is True
    assert result["final_action_gate"]["submission_performed"] is False
    assert len(result["portal_preview_sha256"]) == 64


def test_missing_required_contact_and_founder_coverage_fail_closed():
    module = load_module()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    founder, contact = sample_maps(module, manifest)
    contact["question_answers"] = [
        {"question_id": 75, "value": None, "disposition": "OMIT_OPTIONAL"}
    ]
    result = module.build_preview(manifest, founder, contact)
    assert result["status"] == "REQUIRED_PRIVATE_FIELDS_MISSING"
    assert result["summary"]["required_unresolved_question_ids"] == [4]

    founder["question_answers"] = founder["question_answers"][:-1]
    with pytest.raises(ValueError, match="Founder answer coverage mismatch"):
        module.build_preview(manifest, founder, contact)


def test_duplicate_or_unexpected_private_answers_fail_closed():
    module = load_module()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    founder, contact = sample_maps(module, manifest)
    founder["question_answers"].append({"question_id": 38, "value": "Yes"})
    with pytest.raises(ValueError, match="Duplicate founder_map question_id"):
        module.build_preview(manifest, founder, contact)

    founder, contact = sample_maps(module, manifest)
    contact["question_answers"].append({"question_id": 3, "value": "Private"})
    with pytest.raises(ValueError, match="Unexpected private contact"):
        module.build_preview(manifest, founder, contact)


def test_output_boundary_and_fixed_time_hash_are_deterministic(tmp_path):
    module = load_module()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    founder, contact = sample_maps(module, manifest)
    first = module.build_preview(
        manifest, founder, contact, generated_utc="2026-07-18T01:00:00+00:00"
    )
    second = module.build_preview(
        manifest, founder, contact, generated_utc="2026-07-18T01:00:00+00:00"
    )

    public_path = (
        ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026" / "preview.json"
    )
    private_path = module.PRIVATE_DIR / "preview.private.json"
    assert module.output_path_allowed(public_path) is False
    assert module.output_path_allowed(private_path) is True
    assert module.output_path_allowed(tmp_path / "preview.private.json") is True
    assert first["portal_preview_sha256"] == second["portal_preview_sha256"]
