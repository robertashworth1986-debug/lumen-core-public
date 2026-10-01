from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "build_public_live_breadth_manifest.py"
PUBLIC_JSON = ROOT / "dashboard" / "data" / "public_live_breadth_manifest.json"
PUBLIC_MD = ROOT / "docs" / "PUBLIC_LIVE_BREADTH_MANIFEST_2026-08-08.md"


def load_module():
    spec = importlib.util.spec_from_file_location("public_live_breadth_manifest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def fixture_registry() -> dict:
    return {
        "generated_utc": "2026-08-08T09:00:00+00:00",
        "rows": [
            {
                "source": "PRIVATE_PROVIDER_A",
                "sector": "energy",
                "enabled": True,
                "measured": True,
                "probe_ok": True,
                "rows": 150,
                "last_probe_utc": "2026-08-08T09:30:00+00:00",
                "env_names": ["PRIVATE_API_KEY"],
                "present_env_names": ["PRIVATE_API_KEY"],
                "translated_value": {"year": 999999999},
            },
            {
                "source": "PRIVATE_PROVIDER_B",
                "sector": "market_data",
                "enabled": True,
                "measured": True,
                "probe_ok": True,
                "rows": 1,
                "last_probe_utc": "2026-08-07T00:00:00+00:00",
                "env": "OTHER_PRIVATE_KEY",
            },
        ],
    }


def fixture_governance(module) -> dict:
    governance = {
        "schema": "public_live_breadth_governance_v1",
        "registry_sha256": "b" * 64,
        "registry_max_age_hours": 2,
        "protocol": {
            "approval_status": "approved",
            "reviewed_by_role": "data_governance_owner",
            "reviewed_utc": "2026-08-08T09:45:00+00:00",
            "worklist_sha256": "c" * 64,
        },
        "sources": {
            "PRIVATE_PROVIDER_A": {
                "rights_status": "verified_for_review",
                "relevance_status": "verified",
                "minimum_rows": 100,
                "max_age_hours": 2,
                "dataset_snapshot_sha256": "a" * 64,
                "dataset_snapshot_observed_utc": "2026-08-08T09:15:00+00:00",
            },
            "PRIVATE_PROVIDER_B": {
                "rights_status": "unknown",
                "relevance_status": "unknown",
                "minimum_rows": 10,
                "max_age_hours": 2,
            },
        },
    }
    return module.seal_governance(governance)


def test_manifest_separates_probe_success_from_review_readiness() -> None:
    module = load_module()
    manifest = module.build_manifest(
        fixture_registry(),
        registry_sha256="b" * 64,
        governance=fixture_governance(module),
        generated_utc="2026-08-08T10:00:00+00:00",
    )

    assert manifest["summary"]["configured_enabled_sources"] == 2
    assert manifest["summary"]["first_party_measured_flag_sources"] == 2
    assert manifest["summary"]["probe_success_sources"] == 2
    assert manifest["summary"]["material_row_depth_sources"] == 1
    assert manifest["summary"]["fresh_sources"] == 1
    assert manifest["summary"]["fresh_dataset_sources"] == 1
    assert manifest["summary"]["review_ready_sources"] == 1
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is True
    assert manifest["claim_gate"]["performance_claim_allowed"] is False
    assert manifest["claim_gate"]["economic_value_claim_allowed"] is False
    assert manifest["claim_gate"]["live_capital_recommendation_allowed"] is False


def test_manifest_is_public_safe_and_omits_provider_and_credential_names() -> None:
    module = load_module()
    manifest = module.build_manifest(
        fixture_registry(),
        registry_sha256="b" * 64,
        governance=fixture_governance(module),
        generated_utc="2026-08-08T10:00:00+00:00",
    )
    serialized = json.dumps(manifest).lower()
    markdown = module.render_markdown(manifest).lower()

    assert "private_provider" not in serialized
    assert "private_api_key" not in serialized
    assert "other_private_key" not in serialized
    assert "translated_value" not in serialized
    assert "999999999" not in serialized
    assert "annual_value" not in serialized
    assert "$" not in markdown
    assert manifest["source_snapshot"]["source_names_disclosed"] is False
    assert manifest["source_snapshot"]["credential_field_names_disclosed"] is False


@pytest.mark.parametrize(
    ("observed", "expected_status"),
    [
        (None, "unknown"),
        ("", "unknown"),
        ("not-a-date", "unknown"),
        ("2026-08-08T09:00:00", "unknown"),
        ("2020-01-01T00:00:00Z", "stale"),
        ("2026-08-08T07:59:59.999Z", "stale"),
        ("2027-01-01T00:00:00Z", "invalid_future_timestamp"),
    ],
)
def test_fresh_probe_cannot_promote_an_unfresh_or_unclocked_dataset(
    observed, expected_status
) -> None:
    module = load_module()
    governance = fixture_governance(module)
    governance["sources"]["PRIVATE_PROVIDER_A"]["dataset_snapshot_observed_utc"] = observed
    governance = module.seal_governance(governance)
    manifest = module.build_manifest(
        fixture_registry(), "b" * 64, governance, "2026-08-08T10:00:00Z"
    )
    source = next(row for row in manifest["sources"] if row["sector"] == "energy")

    assert source["probe_status"] == "passed"
    assert source["freshness_status"] == "passed"
    assert source["dataset_snapshot_bound"] is True
    assert source["dataset_freshness_status"] == expected_status
    assert source["review_ready"] is False
    assert manifest["summary"]["fresh_sources"] == 1
    assert manifest["summary"]["fresh_dataset_sources"] == 0
    assert manifest["summary"]["review_ready_sources"] == 0
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is False
    assert module.verify_manifest(manifest) is True


@pytest.mark.parametrize("observed", ["2026-08-08T08:00:00Z", "2026-08-08T03:00:00-05:00"])
def test_dataset_freshness_includes_exact_threshold_and_normalizes_timezone(observed) -> None:
    module = load_module()
    governance = fixture_governance(module)
    governance["sources"]["PRIVATE_PROVIDER_A"]["dataset_snapshot_observed_utc"] = observed
    manifest = module.build_manifest(
        fixture_registry(), "b" * 64, module.seal_governance(governance), "2026-08-08T10:00:00Z"
    )
    source = next(row for row in manifest["sources"] if row["sector"] == "energy")
    assert source["dataset_snapshot_observed_utc"] == "2026-08-08T08:00:00+00:00"
    assert source["dataset_snapshot_age_hours"] == 2
    assert source["dataset_freshness_status"] == "passed"
    assert source["review_ready"] is True


@pytest.mark.parametrize("threshold", [float("inf"), float("nan"), "Infinity", 0, -1, True])
def test_unbounded_or_invalid_max_age_cannot_promote_dataset(threshold) -> None:
    module = load_module()
    governance = fixture_governance(module)
    governance["sources"]["PRIVATE_PROVIDER_A"]["max_age_hours"] = threshold
    manifest = module.build_manifest(
        fixture_registry(), "b" * 64, module.seal_governance(governance), "2026-08-08T10:00:00Z"
    )
    source = next(row for row in manifest["sources"] if row["sector"] == "energy")
    assert source["max_age_hours"] is None
    assert source["dataset_freshness_status"] == "threshold_missing"
    assert manifest["summary"]["review_ready_sources"] == 0
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is False


def test_fresh_dataset_cannot_hide_stale_probe() -> None:
    module = load_module()
    registry = fixture_registry()
    registry["rows"][0]["last_probe_utc"] = "2026-08-07T10:00:00Z"
    manifest = module.build_manifest(
        registry, "b" * 64, fixture_governance(module), "2026-08-08T10:00:00Z"
    )
    source = next(row for row in manifest["sources"] if row["sector"] == "energy")
    assert source["freshness_status"] == "stale"
    assert source["dataset_freshness_status"] == "passed"
    assert source["review_ready"] is False
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is False


@pytest.mark.parametrize("field", ["rows", "minimum_rows"])
def test_fractional_row_count_or_threshold_cannot_be_rounded_into_a_pass(field) -> None:
    module = load_module()
    registry = fixture_registry()
    governance = fixture_governance(module)
    if field == "rows":
        registry["rows"][0][field] = 100.5
    else:
        governance["sources"]["PRIVATE_PROVIDER_A"][field] = 99.5
    manifest = module.build_manifest(
        registry, "b" * 64, module.seal_governance(governance), "2026-08-08T10:00:00Z"
    )
    assert manifest["summary"]["review_ready_sources"] == 0
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is False


def test_registry_age_is_not_rounded_down_into_a_pass() -> None:
    module = load_module()
    registry = fixture_registry()
    registry["generated_utc"] = "2026-08-08T07:59:59.999Z"
    manifest = module.build_manifest(
        registry, "b" * 64, fixture_governance(module), "2026-08-08T10:00:00Z"
    )
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is False


def test_missing_governance_fails_closed() -> None:
    module = load_module()
    manifest = module.build_manifest(
        fixture_registry(),
        registry_sha256="b" * 64,
        governance={"sources": {}},
        generated_utc="2026-08-08T10:00:00+00:00",
    )

    assert manifest["summary"]["probe_success_sources"] == 2
    assert manifest["summary"]["material_row_depth_sources"] == 0
    assert manifest["summary"]["fresh_sources"] == 0
    assert manifest["summary"]["rights_verified_sources"] == 0
    assert manifest["summary"]["relevance_verified_sources"] == 0
    assert manifest["summary"]["snapshot_bound_sources"] == 0
    assert manifest["summary"]["governance_complete_sources"] == 0
    assert manifest["summary"]["review_ready_sources"] == 0
    assert manifest["source_snapshot"]["registry_freshness_status"] == "threshold_missing"
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is False


def test_manifest_hash_detects_tampering() -> None:
    module = load_module()
    manifest = module.build_manifest(
        fixture_registry(),
        registry_sha256="b" * 64,
        governance=fixture_governance(module),
        generated_utc="2026-08-08T10:00:00+00:00",
    )

    assert module.verify_manifest(manifest) is True
    manifest["summary"]["review_ready_sources"] = 99
    assert module.verify_manifest(manifest) is False


def test_duplicate_source_identifiers_fail_the_claim_gate() -> None:
    module = load_module()
    registry = fixture_registry()
    registry["rows"].append(dict(registry["rows"][0]))
    manifest = module.build_manifest(
        registry,
        registry_sha256="b" * 64,
        governance=fixture_governance(module),
        generated_utc="2026-08-08T10:00:00+00:00",
    )

    assert manifest["data_quality"]["structurally_valid"] is False
    assert manifest["data_quality"]["duplicate_source_refs"]
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is False


def test_future_probe_timestamp_fails_structural_and_claim_gates() -> None:
    module = load_module()
    registry = fixture_registry()
    registry["rows"][0]["last_probe_utc"] = "2026-08-09T00:00:00+00:00"
    manifest = module.build_manifest(
        registry,
        registry_sha256="b" * 64,
        governance=fixture_governance(module),
        generated_utc="2026-08-08T10:00:00+00:00",
    )

    assert manifest["data_quality"]["structurally_valid"] is False
    assert "last_probe_after_manifest" in manifest["sources"][0]["quality_issues"] or any(
        "last_probe_after_manifest" in row["quality_issues"] for row in manifest["sources"]
    )
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is False


def test_committed_manifest_is_hash_valid_and_fail_closed() -> None:
    module = load_module()
    manifest = json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))
    markdown = PUBLIC_MD.read_text(encoding="utf-8")

    assert manifest["schema"] == "public_live_breadth_manifest_v1"
    assert module.verify_manifest(manifest) is True
    assert manifest["summary"]["registry_rows"] == 17
    assert manifest["summary"]["probe_success_sources"] == 14
    assert manifest["summary"]["review_ready_sources"] == 0
    assert manifest["claim_gate"]["review_ready_source_count_claim_allowed"] is False
    assert manifest["source_snapshot"]["governance_protocol_valid"] is False
    assert manifest["source_snapshot"]["governance_protocol_issues"] == [
        "governance_not_supplied"
    ]
    assert "Review-ready sources | 0" in markdown
    assert "PRIVATE" not in json.dumps(manifest)


def test_committed_source_rows_follow_the_public_allowlist() -> None:
    manifest = json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))
    allowed = {
        "source_ref",
        "sector",
        "configured_enabled",
        "first_party_measured_flag",
        "probe_status",
        "last_probe_utc",
        "probe_age_hours",
        "observed_rows",
        "minimum_rows",
        "row_depth_status",
        "max_age_hours",
        "freshness_status",
        "rights_status",
        "relevance_status",
        "dataset_snapshot_sha256",
        "dataset_snapshot_bound",
        "review_ready",
        "quality_issues",
        "registry_row_sha256",
    }
    forbidden = {
        "source",
        "env",
        "env_names",
        "present_env_names",
        "translated_value",
        "dollar_basis",
        "money_drain_mode",
        "formula_basis",
        "probe_note",
    }

    for row in manifest["sources"]:
        assert set(row) == allowed
        assert not (set(row) & forbidden)
        assert re.fullmatch(r"source-[0-9a-f]{16}", row["source_ref"])
