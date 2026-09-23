from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("economic_bridge", ROOT / "code/ops/BUILD_CHAMPION_SAMPLE_EXPANSION_AND_ECONOMIC_BRIDGE.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_examples_use_annual_pool_and_percentage_units_once():
    examples = module.economic_bridge([])["illustrative_only_examples"]
    # $1bn/year * 0.01/100 * 10/100 * 50/100 * 50/100 = $2,500/year.
    assert [row["illustrative_annual_value_usd"] for row in examples] == [2500.0, 25000.0, 250000.0]
    for row in examples:
        assert row["addressable_pool_unit"] == "USD/year"
        assert row["owner_accepted_inputs"] is False
        assert row["effect_measured"] is False
        assert row["illustrative_annual_net_value_usd"] is None
        assert row["implementation_and_operating_costs_usd_per_year"] is None
        assert "gross annual scenario" in row["boundary"]
    assert examples[0]["accepted_lift_fraction"] == 0.0001
    assert examples[1]["accepted_lift_fraction"] == 0.001


def test_zero_and_adverse_hypotheses_are_not_clamped_to_positive_savings():
    assert module.illustrative_annual_example(1_000_000_000, "0")["illustrative_annual_value_usd"] == 0
    assert module.illustrative_annual_example(1_000_000_000, "-0.1")["illustrative_annual_value_usd"] == -25000


@pytest.mark.parametrize("pool,lift", [(True, "1"), (-1, "1"), (100, True), (100, "NaN"), (100, "Infinity"), (100, "101"), (100, "-101"), (100, "bad")])
def test_invalid_scenario_inputs_are_rejected(pool, lift):
    with pytest.raises(ValueError):
        module.illustrative_annual_example(pool, lift)


def test_negative_wave_record_cannot_become_a_600_of_600_champion():
    sweep = {"lane_scoreboard": [{"lane": "wave_resonance_timing", "routes_replayed": 1, "baseline_comparison_count": 6, "candidate_win_count": 0, "mean_score_delta": -0.52947, "best_score_delta": -0.218205}]}
    diagnostics = module.build_lane_diagnostics(sweep, {})
    wave = next(row for row in diagnostics if row["lane"] == "wave_resonance_timing")
    assert wave["status"] == "mixed_or_not_promoted"
    assert wave["mean_score_delta"] == -0.52947
    econ = module.economic_bridge(diagnostics)
    text = econ["what_600_of_600_means"]
    assert "1 routes, 6 baseline comparisons and 0 candidate wins" in text
    assert "beat every" not in text
    assert "not a direct percent savings claim" in text
    assert "strongest lane is wave" not in econ["current_safe_claim"]
    action = next(row for row in module.ranked_next_tests(diagnostics) if row["lane"] == "wave_resonance_timing")
    assert "Retain the best feasible baseline" in action["next_action"]
    assert "do not select a winning subset" in action["next_action"]


def test_large_counts_alone_do_not_promote_a_champion():
    record = {"routes_replayed": 150, "baseline_comparison_count": 600, "candidate_win_count": 600, "mean_score_delta": 0.1}
    assert module.status_for_lane("wave_resonance_timing", record, {}) == "internal_replay_review_required"


def test_private_manifest_paths_and_comparison_bodies_are_excluded():
    private_path = "E:/PRIVATE_PATENT/client-record.pdf"
    manifest = {"manifest_rows": [{"lane": "PRIVATE_LANE", "source_path": private_path, "system": "PRIVATE_SYSTEM", "adapter_status": "PRIVATE_NOTES"}]}
    sweep = {"top_positive_comparisons": [{
        "lane": "thermal_ventilation", "source_path": private_path,
        "candidate_family": "PRIVATE_CANDIDATE", "baseline_family": "PRIVATE_BASELINE",
        "patent_notes": "PRIVATE_BODY", "score_delta": 0.125,
        "paired_unit_count": 18, "candidate_beats_baseline": True,
        "statistically_positive_after_global_holm": False,
    }]}
    rows = module.top_comparisons(sweep)
    assert rows[0]["score_delta"] == 0.125
    assert rows[0]["paired_unit_count"] == 18
    assert rows[0]["statistically_positive_after_global_holm"] is False
    public = json.dumps({"lanes": module.build_lane_diagnostics(sweep, manifest), "comparisons": rows})
    for private in ["PRIVATE_LANE", "PRIVATE_PATENT", "PRIVATE_SYSTEM", "PRIVATE_NOTES", "PRIVATE_CANDIDATE", "PRIVATE_BASELINE", "PRIVATE_BODY", "client-record.pdf"]:
        assert private not in public


def test_main_writes_only_isolated_fixture_outputs_with_correct_gross_math(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    sources = {"LOCKED_SWEEP_JSON": {"summary": {}, "lane_scoreboard": []}, "MANIFEST_JSON": {}, "LIVE_DOMAIN_JSON": {}}
    for name, value in sources.items():
        path = tmp_path / (name + ".json")
        path.write_text(json.dumps(value))
        monkeypatch.setattr(module, name, path)
    for name in ["OUT_JSON", "DASHBOARD_JSON", "OUT_MD"]:
        monkeypatch.setattr(module, name, tmp_path / (name + ".out"))
    module.main()
    payload = json.loads(module.OUT_JSON.read_text())
    assert payload["schema"] == "champion_sample_expansion_and_economic_bridge_v1"
    assert payload["summary"]["field_validation_claim_allowed"] is False
    assert payload["summary"]["real_dollar_savings_claim_allowed"] is False
    assert json.loads(module.DASHBOARD_JSON.read_text()) == payload
    rendered = module.OUT_MD.read_text()
    assert "$2,500.00" in rendered
    assert "$25,000.00" in rendered
    assert "$250,000.00" in rendered
    assert "$2,500,000" not in rendered
    assert "gross annual illustrative value" in rendered
    assert "## What 600/600 Means" not in rendered
