from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EXTERNAL_VALIDATION_AUTHORITY_DOCKET.py"
CONFIG = ROOT / "config" / "external_validation_authority_docket_v1.json"
OUTPUT = (
    ROOT
    / "evidence"
    / "external_validation"
    / "eia_router_validation_authority_docket_20260714.json"
)
MARKDOWN = ROOT / "docs" / "EXTERNAL_VALIDATION_AUTHORITY_DOCKET_2026-07-14.md"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "external_validation_authority_docket", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_protocol_uses_official_sources_and_keeps_authority_external():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert config["schema"] == "external_validation_authority_protocol.v1"
    assert config["current_repository_maturity_level"] == 3
    assert config["evidence_lane"]["backfill_allowed"] is False
    assert config["reviewer_decision_request"]["operator_may_not_answer_for_reviewer"] is True
    assert {row["function"] for row in config["nist_ai_rmf_informative_crosswalk"]} == {
        "GOVERN",
        "MAP",
        "MEASURE",
        "MANAGE",
    }
    urls = {row["url"] for row in config["standards_references"]}
    assert any(url.startswith("https://www.nist.gov/") for url in urls)
    assert any(url.startswith("https://www.eia.gov/") for url in urls)
    assert "not a NIST certification" in json.dumps(config)
    assert "does not prove Level 4 or Level 5" in config["claim_boundary"]


def test_archived_clean_runner_bundle_is_complete_and_hash_verified():
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    archive = ROOT / config["clean_runner_verification"]["archive_path"]

    verification = module.verify_ci_bundle(archive, config)

    assert verification["verified"] is True
    assert verification["checksum_entry_count"] == 6
    assert verification["checksum_pass_count"] == 6
    assert verification["complete_file_coverage"] is True
    assert verification["archive_privacy_pattern_hit_count"] == 0
    assert all(verification["identity_checks"].values())
    assert verification["receipt_projection"]["suite_pass_count"] == 3
    assert verification["receipt_projection"]["assertion_pass_count"] == 31
    assert verification["receipt_projection"]["external_validation_complete"] is False
    assert verification["receipt_projection"]["agency_certification_complete"] is False


def test_maturity_requires_prospective_gate_then_independent_replication():
    module = load_module()
    runtime = {
        "available": True,
        "protocol_identity_matched": True,
        "sample_gates": {
            "confirmatory_90_days_ready": True,
            "durability_180_days_ready": False,
        },
        "promotion_evaluation_complete": True,
        "confirmatory_gate_passed": True,
        "external_partner_replication_complete": False,
    }

    level_4 = module.derive_maturity(runtime)
    assert level_4["current_supported_level"] == 4
    assert level_4["level_4_gate_passed"] is True
    assert level_4["level_5_gate_passed"] is False

    runtime["sample_gates"]["durability_180_days_ready"] = True
    runtime["external_partner_replication_complete"] = True
    level_5 = module.derive_maturity(
        runtime,
        evaluator_signoff_complete=True,
        independent_hash_verification_complete=True,
    )
    assert level_5["current_supported_level"] == 5
    assert level_5["level_5_gate_passed"] is True
    assert level_5["external_validation_complete"] is True


def test_missing_private_runtime_stays_reviewable_and_fail_closed(tmp_path):
    module = load_module()
    runtime = module.project_runtime_status(tmp_path / "missing.json", "a" * 64)
    maturity = module.derive_maturity(runtime)
    status = module.derive_status(
        integrity_passed=True,
        runtime=runtime,
        maturity=maturity,
    )

    assert runtime["available"] is False
    assert maturity["current_supported_level"] == 3
    assert maturity["level_4_gate_passed"] is False
    assert maturity["level_5_gate_passed"] is False
    assert status == "EVALUATOR_DOCKET_READY_RUNTIME_SNAPSHOT_UNAVAILABLE"


def test_portable_input_hash_normalizes_windows_and_linux_line_endings(tmp_path):
    module = load_module()
    path = tmp_path / "portable.txt"
    path.write_bytes(b"alpha\r\nbeta\r\n")
    windows_row = module.artifact_row(path, root=tmp_path)
    path.write_bytes(b"alpha\nbeta\n")
    linux_row = module.artifact_row(path, root=tmp_path)

    assert windows_row == linux_row
    assert windows_row["hash_mode"] == "utf8_lf"
    assert windows_row["bytes"] == len(b"alpha\nbeta\n")


def test_current_docket_is_integrity_ready_but_keeps_level_5_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "external_validation_authority_docket.v1"
    assert summary["integrity_gate_passed"] is True
    assert summary["clean_runner_bundle_verified"] is True
    assert summary["current_supported_level"] == 3
    assert summary["level_4_gate_passed"] is False
    assert summary["level_5_gate_passed"] is False
    assert summary["external_validation_complete"] is False
    assert summary["independent_evaluator_named"] is False
    assert summary["ready_to_invite_independent_evaluator"] is True
    assert summary["evaluator_acceptance_template_ready"] is True
    assert summary["agency_certification_complete"] is False
    assert summary["field_validation_complete"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert payload["evaluator_acceptance"]["complete"] is False
    package = payload["evaluator_acceptance_package"]
    assert package["template_ready"] is True
    assert package["external_identity_verified"] is False
    assert package["evaluator_independence_verified"] is False
    assert package["result_signoff_complete"] is False
    assert package["level_5_promotion_allowed"] is False
    assert all(package["checks"].values())
    assert all(
        value is None
        for key, value in payload["evaluator_acceptance"].items()
        if key != "complete"
    )
    assert payload["privacy_scan"]["passed"] is True
    assert all(len(row["sha256"]) == 64 for row in payload["portable_inputs"])
    without_hash = {
        key: value for key, value in payload.items() if key != "docket_sha256"
    }
    assert payload["docket_sha256"] == module.canonical_sha256(without_hash)


def test_published_docket_and_markdown_reconcile_without_overclaiming():
    module = load_module()
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    rendered = MARKDOWN.read_text(encoding="utf-8")

    assert payload["summary"]["integrity_gate_passed"] is True
    assert payload["summary"]["current_supported_level"] == 3
    assert payload["summary"]["external_validation_complete"] is False
    assert payload["privacy_scan"]["passed"] is True
    assert payload["portable_input_chain_sha256"] == module.canonical_sha256(
        payload["portable_inputs"]
    )
    without_hash = {
        key: value for key, value in payload.items() if key != "docket_sha256"
    }
    assert payload["docket_sha256"] == module.canonical_sha256(without_hash)
    for row in payload["portable_inputs"]:
        path = ROOT / row["path"]
        assert path.is_file()
        content = module.portable_file_bytes(path, row["hash_mode"])
        assert len(content) == row["bytes"]
        assert module.hashlib.sha256(content).hexdigest() == row["sha256"]

    assert "External Validation Authority Docket" in rendered
    assert "Current supported level: `3`" in rendered
    assert "Level 5 gate passed: `false`" in rendered
    assert "External validation complete: `false`" in rendered
    assert "Evaluator acceptance template ready: `true`" in rendered
    assert "Level 5 promotion allowed: `false`" in rendered
    assert "not a NIST certification" in rendered
