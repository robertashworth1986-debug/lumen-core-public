from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_MONEY_TRUTH_SWEEP.py"


def load_module():
    spec = importlib.util.spec_from_file_location("field_money_truth_sweep", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_field_money_truth_sweep_reports_current_value_without_overclaiming():
    module = load_module()
    payload = module.build_payload(run_steps=False)
    summary = payload["summary"]
    gates = payload["gates"]

    assert payload["schema"] == "field_money_truth_sweep_v2"
    assert summary["registered_family_count"] >= 140
    assert summary["measured_sources"] >= 3
    assert summary["total_measured_rows"] > 0
    assert summary["safe_estimated_annual_value_usd"] == 0
    assert summary["blocked_context_annual_value_usd"] == 0

    assert gates["live_data_available_for_benchmarking"] is True
    assert gates["bounded_estimated_value_claim_allowed"] is False
    assert gates["paid_pilot_scoping_allowed"] is True
    assert gates["field_validation_claim_allowed"] is False
    assert gates["real_dollar_savings_claim_allowed"] is False
    assert gates["fixed_dollar_delta_sale_claim_allowed"] is False
    assert gates["live_trading_or_autonomous_execution_allowed"] is False
    assert len(payload["truth_sweep_sha256"]) == 64


def test_field_money_truth_sweep_defines_all_family_and_champion_blockers():
    module = load_module()
    payload = module.build_payload(run_steps=False)
    summary = payload["summary"]
    gates = payload["gates"]
    blocker_text = "\n".join(payload["blockers"])

    assert gates["registry_has_all_candidate_families"] is True
    assert gates["all_registered_families_live_benchmarked"] is False
    assert summary["adapter_replay_count"] < summary["registered_family_count"]
    assert summary["triple_source_champion_count"] >= 1
    assert gates["triple_dataset_frozen_assets_present"] is True
    assert isinstance(gates["rolling_champion_present"], bool)
    assert gates["field_validation_claim_allowed"] is False
    assert "blocks all-family validation language" in blocker_text
    assert "Field validation requires buyer or agency authorized operational data" in blocker_text
    assert "No current lane clears the buyer-approved dollar-projection gate" in blocker_text


def test_field_money_truth_sweep_markdown_and_commands_are_safe():
    module = load_module()
    payload = module.build_payload(run_steps=False)
    rendered = module.render_markdown(payload)

    assert "Field Money Truth Sweep" in rendered
    assert "field_validation_claim_allowed: `false`" in rendered
    assert "real_dollar_savings_claim_allowed: `false`" in rendered
    assert "bounded_estimated_value_claim_allowed: `false`" in rendered
    assert "bounded workflow pilot scoping with no dollar projection" in rendered
    assert "Run-FieldMoneyTruthSweep.ps1" in rendered
    assert "-FreshLivePull -StageGlyphVault" in rendered
    assert ("api" + "_key") not in rendered.lower()
    assert "client" + "_sec" + "ret" not in rendered.lower()
    assert "pass" + "word" not in rendered.lower()
