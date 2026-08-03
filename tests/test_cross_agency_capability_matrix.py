from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CROSS_AGENCY_CAPABILITY_MATRIX.py"
CONFIG = ROOT / "config" / "cross_agency_capability_matrix_v1.json"
OUTPUT_JSON = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "CROSS_AGENCY_CAPABILITY_MATRIX_2026-07-26.json"
)
OUTPUT_MD = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "CROSS_AGENCY_CAPABILITY_MATRIX_2026-07-26.md"
)
AS_OF_UTC = "2026-07-26T22:30:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("cross_agency_matrix", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_config_is_fail_closed_and_covers_all_claim_classes_and_lanes():
    module = load_module()
    config = load_config()
    module.validate_config(config)

    assert config["controls"] == module.EXPECTED_CONTROLS
    assert config["controls"]["autonomous_email_send_allowed"] is False
    assert config["controls"]["autonomous_upload_allowed"] is False
    assert config["controls"]["autonomous_portal_action_allowed"] is False
    assert config["controls"]["autonomous_submission_allowed"] is False
    assert config["controls"]["action_time_human_confirmation_required"] is True
    assert config["controls"]["external_action_count"] == 0
    assert set(config["claim_classes"]) == {
        "PROVEN",
        "BOUNDED",
        "NOT_PROVEN",
        "ACTION_TIME",
    }
    assert {row["lane_id"] for row in config["reviewer_lanes"]} == {
        "civilian",
        "defense",
        "energy_lab",
        "acquisition",
        "regulated_industry",
    }


def test_every_controlled_object_has_known_sources_and_freshness_rules():
    module = load_module()
    config = load_config()
    source_ids = {source["source_id"] for source in config["sources"]}

    assert source_ids
    for source in config["sources"]:
        assert source["required"] is True
        assert source["freshness"]["mode"] in module.FRESHNESS_MODES
        assert (ROOT / source["path"]).is_file()
    for collection in (
        config["modules"],
        config["restricted_claims"],
        config["action_time_facts"],
    ):
        for row in collection:
            assert row["source_refs"]
            assert set(row["source_refs"]) <= source_ids


def test_current_matrix_is_bounded_ready_with_no_external_action():
    module = load_module()
    payload = module.build_matrix(CONFIG, as_of_utc=AS_OF_UTC)

    assert payload["status"] == (
        "READY_BOUNDED_CROSS_AGENCY_REUSE_NO_EXTERNAL_ACTION"
    )
    assert payload["summary"]["source_count"] == 10
    assert payload["summary"]["freshness_counts"] == {
        "DATED_CONTEXT": 5,
        "FRESH": 4,
        "TIMELESS_CONTROL": 1,
    }
    assert payload["summary"]["declared_class_counts"] == {
        "ACTION_TIME": 1,
        "BOUNDED": 4,
        "NOT_PROVEN": 3,
        "PROVEN": 2,
    }
    assert payload["summary"]["effective_class_counts"] == {
        "ACTION_TIME": 1,
        "BOUNDED": 4,
        "NOT_PROVEN": 3,
        "PROVEN": 2,
    }
    assert payload["summary"]["restricted_claim_allowed_count"] == 0
    assert payload["summary"]["external_action_count"] == 0
    assert payload["blockers"] == []
    assert payload["external_actions"] == {
        "capabilities": [],
        "performed": [],
        "send_allowed": False,
        "upload_allowed": False,
        "portal_action_allowed": False,
        "submission_allowed": False,
    }
    assert module.verify_matrix_sha256(payload)


def test_each_lane_maps_concerns_modules_restrictions_and_action_time_facts():
    module = load_module()
    payload = module.build_matrix(CONFIG, as_of_utc=AS_OF_UTC)

    assert len(payload["reviewer_lanes"]) == 5
    for lane in payload["reviewer_lanes"]:
        assert lane["reviewer_concerns"]
        assert lane["modules"]
        assert lane["restricted_claims"]
        assert lane["action_time_facts"]
        assert lane["external_action_authorized"] is False
        assert all(
            row["effective_class"] in module.CLAIM_CLASSES
            for row in lane["modules"]
        )
        assert all(
            row["claim_allowed"] is False for row in lane["restricted_claims"]
        )
        assert all(
            row["resolved_state"] == "ACTION_TIME_REVERIFY_REQUIRED"
            for row in lane["action_time_facts"]
        )


def test_restricted_claims_cannot_be_promoted_without_independent_evidence():
    module = load_module()
    config = load_config()

    assert {row["claim_id"] for row in config["restricted_claims"]} == (
        module.REQUIRED_RESTRICTED_CLAIMS
    )
    assert all(
        row["current_state"] == "NOT_PROVEN"
        and row["independent_evidence_required"] is True
        for row in config["restricted_claims"]
    )

    tampered = copy.deepcopy(config)
    tampered["restricted_claims"][0]["current_state"] = "PROVEN"
    with pytest.raises(module.MatrixError, match="lacks independent evidence"):
        module.build_matrix_from_config(tampered, as_of_utc=AS_OF_UTC)


def test_stale_current_sources_downgrade_reusable_claims_and_block_matrix():
    module = load_module()
    payload = module.build_matrix(
        CONFIG,
        as_of_utc="2026-08-10T22:30:00Z",
    )

    assert payload["status"] == "CROSS_AGENCY_MATRIX_BLOCKED_SOURCE_OR_CONTROL"
    assert payload["summary"]["freshness_counts"]["STALE"] == 4
    assert any(blocker.startswith("source:") for blocker in payload["blockers"])
    assert next(
        row
        for row in payload["modules"]
        if row["module_id"] == "fail_closed_review_control"
    )["effective_class"] == "NOT_PROVEN"
    assert next(
        row
        for row in payload["modules"]
        if row["module_id"] == "measured_source_intake"
    )["claim_usable"] is False


def test_missing_required_source_fails_closed_without_promoting_claim():
    module = load_module()
    tampered = copy.deepcopy(load_config())
    domain_source = next(
        row
        for row in tampered["sources"]
        if row["source_id"] == "live_domain_service_contract"
    )
    domain_source["path"] = "out/ops/does_not_exist_cross_agency_matrix.json"

    payload = module.build_matrix_from_config(tampered, as_of_utc=AS_OF_UTC)

    assert payload["status"] == "CROSS_AGENCY_MATRIX_BLOCKED_SOURCE_OR_CONTROL"
    assert "source:live_domain_service_contract:MISSING" in payload["blockers"]
    module_row = next(
        row
        for row in payload["modules"]
        if row["module_id"] == "full_live_domain_chain"
    )
    assert module_row["effective_class"] == "NOT_PROVEN"
    assert module_row["external_action_authorized"] is False


def test_relaxed_control_or_restricted_reusable_phrase_is_rejected():
    module = load_module()
    relaxed = copy.deepcopy(load_config())
    relaxed["controls"]["autonomous_submission_allowed"] = True
    with pytest.raises(module.MatrixError, match="not fail-closed"):
        module.validate_config(relaxed)

    unsafe = copy.deepcopy(load_config())
    unsafe["modules"][0]["reusable_claim"] = (
        "The module establishes CMMC status and performance."
    )
    with pytest.raises(module.MatrixError, match="restricted reusable terms"):
        module.validate_config(unsafe)


def test_builder_has_no_network_or_external_action_imports_and_fixed_writes():
    module = load_module()
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert imports.isdisjoint(
        {
            "ftplib",
            "playwright",
            "requests",
            "selenium",
            "smtplib",
            "socket",
            "subprocess",
            "urllib",
            "webbrowser",
        }
    )
    assert module.EXTERNAL_ACTION_CAPABILITIES == ()
    assert module.WRITE_TARGETS == (OUTPUT_JSON, OUTPUT_MD)


def test_generated_outputs_match_builder_and_preserve_claim_boundaries():
    module = load_module()
    payload = module.build_matrix(CONFIG, as_of_utc=AS_OF_UTC)
    markdown = module.render_markdown(payload)

    assert OUTPUT_JSON.read_text(encoding="utf-8") == module.render_json(payload)
    assert OUTPUT_MD.read_text(encoding="utf-8") == markdown
    assert "## Restricted Claim Gate" in markdown
    assert "## Action-Time Fact Gate" in markdown
    assert "cannot send email, upload files, act in a portal" in markdown
    assert "`agency_endorsement` | `NOT_PROVEN` | `false`" in markdown
    assert "External actions performed: `0`" in markdown
    assert module.outputs_match(payload)
