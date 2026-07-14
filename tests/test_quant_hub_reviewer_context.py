from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_QUANT_HUB_REVIEWER_CONTEXT.py"
LEXICON = ROOT / "config" / "quant_hub_lexicon_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("build_quant_hub_reviewer_context", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_lexicon_defines_level_five_as_external_validation():
    payload = json.loads(LEXICON.read_text(encoding="utf-8"))
    assert payload["schema"] == "quant_hub_lexicon.v1"
    assert payload["identity"]["repository_display_name"] == "Quant Hub Repo"
    assert payload["level_policy"]["current_repository_wide_level"] == 3
    assert payload["level_policy"]["level_5_attained"] is False

    levels = {row["level"]: row for row in payload["evidence_maturity"]}
    assert set(levels) == {0, 1, 2, 3, 4, 5}
    assert "independent" in levels[5]["label"]
    assert "dated validation receipt" in levels[5]["minimum_evidence"]

    terms = [row["term"] for row in payload["terms"]]
    assert len(terms) == len(set(terms))
    assert {"LumenCore", "LumaTrader", "NovaStack", "ProofLock", "HumanUnlock", "EconomicRichness"}.issubset(
        terms
    )


def test_context_preserves_positive_negative_and_waiting_evidence():
    module = load_module()
    context = module.build_context()

    assert context["schema"] == "quant_hub_reviewer_context.v1"
    assert context["current_evidence_posture"]["highest_repository_wide_supported_level"] == 3
    assert context["current_evidence_posture"]["level_5_attained"] is False
    assert context["human_authority_policy"]["final_submission_allowed_without_human"] is False
    assert context["human_authority_policy"]["legal_or_ip_action_allowed_without_human"] is False

    cards = {row["proof_id"]: row for row in context["proof_cards"]}
    assert cards["prooflock_prior_vault"]["facts"]["all_copied_hashes_verified"] is True
    assert cards["locked_source_baseline_replay"]["facts"]["candidate_win_count"] > 0
    assert cards["locked_source_baseline_replay"]["facts"]["candidate_loss_or_tie_count"] > 0
    assert cards["eia_prospective_router"]["facts"]["prediction_count"] == 0
    assert cards["eia_prospective_router"]["facts"]["settlement_count"] == 0
    assert cards["eia_prospective_router"]["facts"]["promotion_evaluation_complete"] is False
    assert cards["mda_synthetic_feasibility_v1"]["facts"]["gate_passed"] is False
    assert cards["mda_open_set_v2"]["facts"]["gate_passed"] is False
    assert cards["mda_open_set_v2"]["facts"]["unsupported_mapping_rate"] == 0.0
    assert cards["faa_sdr_frozen_10k"]["facts"]["holdout_rows"] == 10_000
    assert cards["faa_sdr_frozen_10k"]["facts"]["development_key_overlap"] == 0
    assert cards["faa_sdr_frozen_10k"]["facts"]["candidate_promoted"] is False
    assert cards["faa_sdr_frozen_10k"]["facts"]["rolls_royce_exploratory_rows"] == 28

    blocked = context["claim_controls"]["blocked_without_new_evidence"]
    assert all(blocked.values())
    assert len(context["source_input_chain_sha256"]) == 64
    assert all(len(row["sha256"]) == 64 for row in context["source_artifacts"])

    serialized = json.dumps(context).casefold().replace("\\", "/")
    assert "private_estate" not in serialized
    assert "patent_19_281_546" not in serialized
    assert "cp575notice" not in serialized


def test_context_outputs_are_identical_and_public_safe(tmp_path):
    module = load_module()
    context = module.build_context()
    out_json = tmp_path / "out.json"
    dashboard_json = tmp_path / "dashboard.json"
    out_md = tmp_path / "reviewer.md"

    module.write_outputs(
        context,
        output_json=out_json,
        dashboard_json=dashboard_json,
        output_markdown=out_md,
    )

    assert out_json.read_bytes() == dashboard_json.read_bytes()
    markdown = out_md.read_text(encoding="utf-8")
    assert "Level 5 attained: `false`" in markdown
    assert "MDA mapping independent open-set v2" in markdown
    assert "FAA SDR frozen 10,000-report triage benchmark" in markdown
    assert "Patent And Privacy Boundary" in markdown
    assert "private_estate" not in markdown.casefold()


def test_context_fails_closed_when_required_source_is_missing(tmp_path, monkeypatch):
    module = load_module()
    missing = tmp_path / "missing.json"
    monkeypatch.setitem(module.SOURCE_PATHS, "locked_replay", missing)
    with pytest.raises(FileNotFoundError, match="required reviewer-context input is missing"):
        module.build_context()
