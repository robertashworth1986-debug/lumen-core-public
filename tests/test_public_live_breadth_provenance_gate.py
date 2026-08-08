from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PUBLIC_LIVE_BREADTH_PROVENANCE_GATE.py"
PUBLIC_MD = ROOT / "docs" / "LIVE_BREADTH_PROVENANCE_GATE_CAPSULE_2026-06-21.md"
PUBLIC_JSON = ROOT / "dashboard" / "data" / "live_breadth_provenance_gate.json"


def load_module():
    spec = importlib.util.spec_from_file_location("public_live_breadth_provenance_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_public_live_breadth_gate_is_bounded_and_public_safe():
    module = load_module()
    payload = module.build_payload()
    metrics = payload["public_safe_metrics"]
    gate = payload["claim_gate"]

    assert payload["schema"] == "public_live_breadth_provenance_gate_v2"
    assert metrics["enabled_live_sources"] == 17
    assert metrics["measured_live_sources"] == 12
    assert metrics["promoted_live_measured_source_rows"] == 11
    assert metrics["context_only_source_rows"] == 8
    assert payload["snapshot"]["status"] == "historical_not_current_runtime_evidence"
    assert payload["snapshot"]["source_registry_included"] is False
    assert payload["snapshot"]["manifest_bound"] is False
    assert payload["truth_chain_interpretation"]["economic_estimates_included"] is False
    assert gate["ready_for_portal_upload"] is False
    assert gate["ready_for_submit"] is False
    assert gate["grant_merit_proven"] is False
    assert gate["field_performance_proven"] is False
    assert gate["trading_profit_proven"] is False
    assert gate["current_runtime_state_proven"] is False
    assert gate["economic_value_claim_allowed"] is False
    assert gate["performance_claim_allowed"] is False
    assert gate["probe_success_is_dataset_fitness"] is False
    assert gate["context_only_promoted_as_live_proof"] is False


def test_public_live_breadth_gate_markdown_names_truth_chain_and_boundaries():
    module = load_module()
    payload = module.build_payload()
    markdown = module.render_markdown(payload)
    serialized = json.dumps(payload).lower() + markdown.lower()

    assert "Truth-Chain Interpretation" in markdown
    assert "Economic estimates included: `false`" in markdown
    assert "historical_not_current_runtime_evidence" in markdown
    assert "not proof of dataset fitness" in markdown
    assert "Historical first-party source-classification evidence only" in markdown
    assert "not native DICE ground truth" in markdown
    assert "HarborSentinel" in markdown
    assert "context_only_promoted_as_live_proof: `false`" in markdown
    assert "grant merit" in serialized
    assert "trading profit" in serialized
    assert "field performance" in serialized
    assert "$" not in markdown
    assert "_usd" not in json.dumps(payload).lower()
    assert "sk-" + "proj" not in serialized
    assert "ready_for_submit\": true" not in serialized
    assert "ready_for_portal_upload\": true" not in serialized


def test_generated_public_live_breadth_gate_files_exist_after_builder_run():
    assert PUBLIC_MD.exists()
    assert PUBLIC_JSON.exists()
    payload = json.loads(PUBLIC_JSON.read_text(encoding="utf-8"))
    assert payload["schema"] == "public_live_breadth_provenance_gate_v2"
