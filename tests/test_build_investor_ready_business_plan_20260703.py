from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_INVESTOR_READY_BUSINESS_PLAN_20260703.py"
SPEC = importlib.util.spec_from_file_location("investor_plan_builder", MODULE_PATH)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def canonical_payloads() -> dict[str, dict]:
    generated = NOW.isoformat()
    return {
        "champion_metric_gauntlet.json": {
            "schema": "champion_metric_gauntlet_v2",
            "generated_utc": generated,
            "summary": {
                "champion_family": "kuramoto_phase_coupling",
                "named_baseline": "kalman_local_linear_trend",
                "holdout_wins": 482,
                "holdout_count": 1525,
                "mean_delta_vs_named_baseline": -0.508191,
                "internal_champion": False,
                "protocol_grade_internal_champion": False,
                "real_dollar_savings_claim_allowed": False,
                "safe_estimated_hourly_value_usd": 0.0,
                "safe_estimated_annual_value_usd": 0.0,
            },
        },
        "locked_source_baseline_replay_sweep.json": {
            "schema": "locked_source_baseline_replay_sweep_v2",
            "generated_utc": generated,
            "summary": {
                "adapter_backed_routes": 4,
                "baseline_comparison_count": 22,
                "direct_measured_routes_replayed": 2,
                "source_conditioned_routes_replayed": 2,
                "numeric_samples_read": 32608,
                "global_holm_positive_count": 0,
                "performance_superiority_claim_allowed": False,
                "real_dollar_savings_claim_allowed": False,
            },
        },
        "field_validated_dollar_claim_ladder.json": {
            "schema": "field_validated_dollar_claim_ladder_v2",
            "generated_utc": generated,
            "current_truth": {
                "current_performance_champion_present": False,
                "direct_all_baseline_global_holm_positive_count": 0,
                "cross_sector_gain_proven_count": 0,
                "cross_sector_sector_count": 6,
                "modeled_dollar_projection_allowed_now": False,
                "enterprise_valuation_asserted_now": False,
                "allowed_estimated_hourly_value_usd": 0.0,
                "allowed_estimated_annual_value_usd": 0.0,
            },
        },
        "dollar_claim_gate.json": {
            "schema": "dollar_claim_gate_v2",
            "generated_utc": generated,
            "summary": {
                "allowed_estimated_hourly_value_usd": 0.0,
                "allowed_estimated_annual_value_usd": 0.0,
            },
        },
        "valuation_proposal_target_packet.json": {
            "schema": "valuation_proposal_target_packet_v3",
            "generated_utc": generated,
            "current_truth": {
                "internal_performance_champion_present": False,
                "reference_candidate_was_protocol_selected": False,
                "safe_estimated_hourly_value_usd": 0.0,
                "safe_estimated_annual_value_usd": 0.0,
            },
            "valuation_state": {
                "enterprise_valuation_asserted": False,
            },
        },
        "proof_to_revenue_engine.json": {
            "schema": "proof_to_revenue_engine_v3",
            "generated_utc": generated,
            "summary": {
                "internal_performance_champion_present": False,
                "cross_sector_efficiency_claim_allowed": False,
                "model_performance_marketing_allowed": False,
                "modeled_dollar_projection_allowed": False,
                "enterprise_valuation_asserted": False,
                "cross_sector_gain_proven_count": 0,
                "cross_sector_sector_count": 6,
                "measured_reference_candidate": "kuramoto_phase_coupling",
                "reference_candidate_was_protocol_selected": False,
                "development_selected_candidate": "lissajous_phase_paths",
                "internal_replay_named_baseline": "kalman_local_linear_trend",
                "internal_replay_holdout_wins": 482,
                "internal_replay_holdout_count": 1525,
                "internal_replay_mean_delta": -0.508191,
                "safe_estimated_hourly_value_usd": 0.0,
                "safe_estimated_annual_value_usd": 0.0,
            },
            "commercial_offers": {
                "source_native_protocol_review": {
                    "price_usd": {"low": 2500, "high": 7500},
                },
                "benchmark_implementation": {
                    "price_usd": {"low": 7500, "high": 25000},
                },
                "product_process_discovery": {
                    "name": "ProofLock Opportunity Operations",
                    "product_process_scoping_allowed": True,
                    "model_performance_dependency": False,
                    "claim_boundary": (
                        "This offer does not inherit geometry performance, savings, "
                        "award, or field-validation claims."
                    ),
                },
            },
            "current_model_evidence": {
                "candidate_family": "kuramoto_phase_coupling",
                "candidate_was_protocol_selected": False,
            },
        },
    }


def write_payloads(directory: Path, payloads: dict[str, dict]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for filename, payload in payloads.items():
        (directory / filename).write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )


def test_build_uses_temp_outputs_and_only_safe_current_contract(tmp_path: Path) -> None:
    data_dir = tmp_path / "inputs"
    output_pdf = tmp_path / "outputs" / "plan.pdf"
    output_md = tmp_path / "outputs" / "plan.md"
    write_payloads(data_dir, canonical_payloads())

    result = BUILDER.build_pdf(
        data_dir=data_dir,
        output_pdf=output_pdf,
        output_md=output_md,
        now=NOW,
    )

    assert result == (output_pdf, output_md)
    assert output_pdf.is_file() and output_pdf.stat().st_size > 0
    text = output_md.read_text(encoding="utf-8")
    assert "Performance champion: **none**" in text
    assert "Direct all-baseline global Holm promotions: **0**" in text
    assert "Proven cross-sector gains: **0/6**" in text
    assert "**482/1525**" in text
    assert "**-0.508191**" in text
    assert "not development-selected" in text
    assert "Claimable modeled dollar outcome: **$0**" in text
    assert "Enterprise valuation: **not asserted**" in text
    assert "$2,500-$7,500" in text
    assert "$7,500-$25,000" in text
    assert "ProofLock Opportunity Operations" in text
    assert "inherits no geometry performance" in text
    lowered = text.lower()
    assert "strongest internal champion" not in lowered
    assert "target valuation" not in lowered
    assert "$10m" not in lowered
    assert "$39,595,200" not in text
    assert "$4,520" not in text


def test_missing_input_fails_before_outputs_are_created(tmp_path: Path) -> None:
    data_dir = tmp_path / "inputs"
    payloads = canonical_payloads()
    del payloads["proof_to_revenue_engine.json"]
    write_payloads(data_dir, payloads)
    output_pdf = tmp_path / "plan.pdf"
    output_md = tmp_path / "plan.md"

    with pytest.raises(FileNotFoundError, match="proof_to_revenue_engine.json"):
        BUILDER.build_pdf(
            data_dir=data_dir,
            output_pdf=output_pdf,
            output_md=output_md,
            now=NOW,
        )

    assert not output_pdf.exists()
    assert not output_md.exists()


@pytest.mark.parametrize(
    ("filename", "mutation", "match"),
    [
        (
            "champion_metric_gauntlet.json",
            lambda payload: payload.update(schema="champion_metric_gauntlet_v1"),
            "stale or unsupported schema",
        ),
        (
            "champion_metric_gauntlet.json",
            lambda payload: payload["summary"].update(internal_champion=True),
            "must be explicitly false",
        ),
        (
            "dollar_claim_gate.json",
            lambda payload: payload["summary"].update(
                allowed_estimated_annual_value_usd=1
            ),
            "must be zero",
        ),
        (
            "proof_to_revenue_engine.json",
            lambda payload: payload["summary"].update(
                cross_sector_gain_proven_count=1
            ),
            "must remain 0 proven gains",
        ),
        (
            "proof_to_revenue_engine.json",
            lambda payload: payload["summary"].update(
                enterprise_valuation_asserted=True
            ),
            "must be explicitly false",
        ),
    ],
)
def test_stale_or_contradictory_contract_fails_closed(
    filename: str,
    mutation,
    match: str,
) -> None:
    payloads = canonical_payloads()
    mutation(payloads[filename])
    data = {
        key: payloads[artifact_filename]
        for key, (artifact_filename, _schema) in BUILDER.INPUT_SCHEMAS.items()
    }

    with pytest.raises(BUILDER.ContractError, match=match):
        BUILDER.validate_contract(data, now=NOW)


def test_old_inputs_fail_closed() -> None:
    payloads = canonical_payloads()
    old_time = (NOW - timedelta(days=15)).isoformat()
    for payload in payloads.values():
        payload["generated_utc"] = old_time
    data = {
        key: payloads[artifact_filename]
        for key, (artifact_filename, _schema) in BUILDER.INPUT_SCHEMAS.items()
    }

    with pytest.raises(BUILDER.ContractError, match="is stale"):
        BUILDER.validate_contract(data, now=NOW)


def test_current_workspace_inputs_satisfy_contract_without_writing_outputs() -> None:
    data = BUILDER.get_data()
    contract = BUILDER.validate_contract(
        data,
        now=datetime.now(timezone.utc),
    )

    assert contract["performance_champion"] is None
    assert contract["global_holm_promotions"] == 0
    assert (contract["sector_gains"], contract["sector_count"]) == (0, 6)
    assert contract["claimable_modeled_dollar_outcome_usd"] == 0
    assert contract["enterprise_valuation_asserted"] is False
