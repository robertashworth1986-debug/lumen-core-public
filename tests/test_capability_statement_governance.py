from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CAPABILITY_STATEMENT_GOVERNANCE.py"
CONFIG = ROOT / "config" / "capability_statement_governance_v1.json"
AS_OF_UTC = "2026-07-26T22:15:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("capability_governance", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_config_is_fail_closed():
    module = load_module()
    config = load_config()
    module.validate_config(config)

    assert config["controls"] == module.EXPECTED_CONTROLS
    assert config["controls"]["autonomous_email_send_allowed"] is False
    assert config["controls"]["autonomous_submission_allowed"] is False
    assert config["controls"]["closed_route_reuse_allowed"] is False
    assert config["controls"]["action_time_human_approval_required"] is True


def test_all_discovered_capability_artifacts_are_registered():
    module = load_module()
    config = load_config()

    discovered = set(module.discover_capability_artifacts(config))
    registered = {artifact["path"] for artifact in config["artifacts"]}
    assert discovered == registered


def test_registry_separates_current_from_historical_and_authorizes_nothing():
    module = load_module()
    payload = module.build_registry(CONFIG, as_of_utc=AS_OF_UTC)

    assert payload["status"] == "GOVERNED_CURRENT_PACKET_WITH_ARCHIVED_LEGACY"
    assert payload["summary"]["registered_artifact_count"] == 6
    assert payload["summary"]["current_public_safe_count"] == 1
    assert payload["summary"]["historical_or_closed_count"] == 4
    assert payload["summary"]["domain_boundary_refresh_count"] == 1
    assert payload["summary"]["external_release_authorized_count"] == 0
    assert not any(payload["blockers"].values())
    assert all(not row["send_eligible"] for row in payload["artifacts"])
    assert all(
        not row["external_release_authorized"] for row in payload["artifacts"]
    )


def test_historical_text_artifacts_have_visible_status_markers():
    module = load_module()
    payload = module.build_registry(CONFIG, as_of_utc=AS_OF_UTC)

    for row in payload["artifacts"]:
        assert row["missing_text_markers"] == []
    air_force = next(
        row for row in payload["artifacts"] if row["id"] == "air_force_aac_rfi_20260709"
    )
    assert air_force["deadline_closed"] is True
    assert air_force["status"] == "HISTORICAL_DO_NOT_SEND"


def test_current_pdf_is_bound_to_arc_seal_builder_and_science_receipts():
    module = load_module()
    payload = module.build_registry(CONFIG, as_of_utc=AS_OF_UTC)
    current = next(
        row
        for row in payload["artifacts"]
        if row["status"] == "CURRENT_PUBLIC_SAFE_HUMAN_REVIEW_REQUIRED"
    )
    dependency_paths = {item["path"] for item in current["dependencies"]}

    assert "assets/brand/lumaarc_eclipse_corona_concept_v1.png" in dependency_paths
    assert "code/ops/BUILD_MONDAY_FEDERAL_ACTION_PACKET.py" in dependency_paths
    assert "out/ops/source_native_family_baseline_ledger_latest.json" in dependency_paths
    assert (
        "docs/receipts/TIME_SERIES_SOURCE_NATIVE_PROSPECTIVE_V3_STATUS_2026-08-04.json"
        in dependency_paths
    )
    assert len(current["sha256"]) == 64


def test_relaxed_control_or_duplicate_path_is_rejected():
    module = load_module()
    relaxed = load_config()
    relaxed["controls"]["autonomous_email_send_allowed"] = True
    with pytest.raises(module.GovernanceError, match="fail-closed"):
        module.validate_config(relaxed)

    duplicate = copy.deepcopy(load_config())
    duplicate["artifacts"][1]["path"] = duplicate["artifacts"][0]["path"]
    with pytest.raises(module.GovernanceError, match="Duplicate"):
        module.validate_config(duplicate)
