from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GRANT_LIVE_BREADTH_PROVENANCE_ANNEX.py"


def load_module():
    spec = importlib.util.spec_from_file_location("grant_live_breadth_provenance_annex", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_annex_preserves_live_measured_and_context_boundaries() -> None:
    module = load_module()
    payload = module.build_annex()
    live = payload["live_breadth_state"]
    truth = payload["truth_chain_state"]

    assert payload["schema"] == "grant_live_breadth_provenance_annex_v1"
    assert live["primary_evidence_mode"] == "live_measured_delta_rows"
    assert live["live_measured_hourly_value_usd"] > 0
    assert live["live_measured_annual_value_usd"] > 0
    assert live["context_only_annual_value_usd"] >= live["live_measured_annual_value_usd"]
    assert truth["annual_value_signal_usd"] == truth["promoted_live_measured_annual_value_usd"]
    assert payload["claim_gate"]["context_only_promoted_as_live_proof"] is False
    assert payload["claim_gate"]["grant_merit_proven"] is False
    assert payload["claim_gate"]["field_performance_proven"] is False
    assert payload["claim_gate"]["trading_profit_proven"] is False


def test_annex_markdown_is_reviewer_safe() -> None:
    module = load_module()
    payload = module.build_annex()
    markdown = module.render_markdown(payload)
    serialized = json.dumps(payload).lower() + markdown.lower()

    assert "Promoted Live-Measured Surface" in markdown
    assert "Context-only annual surface" in markdown
    assert "not native ground truth" in markdown
    assert "ready_for_submit: `false`" in markdown
    assert "context_only_promoted_as_live_proof: `false`" in markdown
    assert "grant merit" in markdown.lower()
    assert "trading profit" in markdown.lower()
    assert "field performance" in markdown.lower()
    assert '"ready_for_submit": true' not in serialized
    assert "sk-" + "proj" not in serialized
    assert "uei " not in serialized
    assert "cage " not in serialized


def test_write_annex_outputs_files() -> None:
    module = load_module()
    payload = module.build_annex()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        old_out = module.OUT
        old_grants = module.GRANTS
        old_json = module.OUT_JSON
        old_md = module.OUT_MD
        try:
            module.OUT = temp / "out" / "ops"
            module.GRANTS = temp / "grant_submissions"
            module.OUT_JSON = module.OUT / "grant_live_breadth_provenance_annex_latest.json"
            module.OUT_MD = module.GRANTS / "LIVE_BREADTH_PROVENANCE_ANNEX_2026-06-21.md"
            module.write_annex(payload)
            assert module.OUT_JSON.exists()
            assert module.OUT_MD.exists()
        finally:
            module.OUT = old_out
            module.GRANTS = old_grants
            module.OUT_JSON = old_json
            module.OUT_MD = old_md
