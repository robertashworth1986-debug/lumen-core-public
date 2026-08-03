from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EXTERNAL_VALIDATION_500_SPRINT.py"
CONFIG = ROOT / "config" / "external_validation_500_sprint_v1.json"
OUTPUT = ROOT / "out" / "ops" / "external_validation_500_sprint_latest.json"
MARKDOWN = ROOT / "docs" / "EXTERNAL_VALIDATION_500_SPRINT_2026-07-16.md"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "external_validation_500_sprint", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_budget_is_exact_and_outcome_independent():
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    validation = module.validate_config(config)

    assert validation["passed"] is True
    assert validation["milestone_total_usd"] == 500
    assert all(validation["checks"].values())
    assert all(row["result_contingent"] is False for row in config["milestones"])
    assert all(
        row["paid_if_result_is_negative"] is True for row in config["milestones"]
    )


def test_budget_does_not_authorize_spending_or_evaluator_impersonation():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    authority = config["human_authority"]

    assert authority["spending_automatically_authorized"] is False
    assert authority["external_contact_automatically_authorized"] is False
    assert authority["account_creation_automatically_authorized"] is False
    assert authority["operator_may_fill_evaluator_fields"] is False
    assert authority["operator_may_sign_for_evaluator"] is False
    assert "does not hire an evaluator" in config["claim_boundary"]


def test_current_packet_is_fail_closed_and_uses_active_hourly_lane():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-16T00:00:00+00:00")
    current = payload["current_state"]
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    runtime = json.loads(
        (ROOT / config["evidence_lane"]["runtime_projection_path"]).read_text(
            encoding="utf-8"
        )
    )

    assert payload["schema"] == "external_validation_500_sprint_packet.v1"
    assert current["runtime_integrity_gate_passed"] is True
    assert current["prediction_count"] == runtime["sample_state"]["prediction_count"]
    assert current["settlement_count"] == runtime["sample_state"]["settlement_count"]
    assert current["common_settled_hour_count"] == runtime["sample_state"][
        "common_settled_hour_count"
    ]
    assert current["prediction_count"] >= 95
    assert current["settlement_count"] >= 84
    assert current["authorities_total"] == 8
    assert current["authorities_with_valid_seals"] == 6
    assert current["zero_seal_authorities"] == ["SWPP", "TVA"]
    assert current["independent_reproduction_complete"] is False
    assert current["performance_promotion_allowed"] is False
    assert current["independent_evaluator_named"] is False
    assert payload["budget"]["total_usd"] == 500
    assert payload["budget"]["estimated_total_hours"] == 10


def test_source_chain_and_packet_hashes_are_reproducible():
    module = load_module()
    payload = module.build_payload(generated_utc="2026-07-16T00:00:00+00:00")

    assert payload["source_input_chain_sha256"] == module.canonical_sha256(
        payload["source_artifacts"]
    )
    without_hash = {
        key: value for key, value in payload.items() if key != "packet_sha256"
    }
    assert payload["packet_sha256"] == module.canonical_sha256(without_hash)
    for row in payload["source_artifacts"]:
        path = ROOT / row["path"]
        assert path.is_file()
        assert path.stat().st_size == row["bytes"]
        assert module.file_sha256(path) == row["sha256"]


def test_published_packet_and_markdown_match_stable_rebuild():
    module = load_module()
    published = json.loads(OUTPUT.read_text(encoding="utf-8"))
    rebuilt = module.build_payload(generated_utc=published["generated_utc"])
    rendered = MARKDOWN.read_text(encoding="utf-8")

    assert module.output_differences(rebuilt) == []
    assert "Put the full $500" in rendered
    assert "outcome-independent external evaluator" in rendered
    assert (
        "Common settled hours across the full panel: "
        f"`{published['current_state']['common_settled_hour_count']}`"
    ) in rendered
    assert "Live trading capital" in rendered
    assert "does not authorize live trading" in rendered
