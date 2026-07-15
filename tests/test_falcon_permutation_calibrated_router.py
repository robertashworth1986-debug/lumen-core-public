from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "falcon_permutation_calibrated_router.py"
PROTOCOL_PATH = (
    ROOT / "config" / "falcon_permutation_calibrated_router_protocol_v3.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "falcon_permutation_calibrated_router", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_protocol_is_prospective_and_has_a_distinct_identity() -> None:
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    assert protocol["schema"] == "falcon_permutation_calibrated_router_protocol.v3"
    assert protocol["development_history"]["prior_gate_passed"] is False
    assert (
        protocol["development_history"]["prospective_status"]
        == "frozen_before_first_real_model_run"
    )
    assert protocol["model"]["model_id"] == "Qwen/Qwen2.5-1.5B-Instruct"
    assert protocol["model"]["device"] == "cuda"
    expected = len(protocol["datasets"]) * sum(
        len(row["evaluation_note_templates"])
        for row in protocol["context_classes"].values()
    )
    assert expected == protocol["qualification_gate"]["required_decision_count"] == 30


def test_all_six_label_permutations_are_balanced() -> None:
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    mappings = module.build_label_mappings(protocol)
    assert len(mappings) == 6
    assert len({tuple(sorted(row.items())) for row in mappings}) == 6
    assignments = Counter(
        (label, context) for mapping in mappings for label, context in mapping.items()
    )
    assert set(assignments.values()) == {2}


def test_prompt_contains_no_expected_context_identifier() -> None:
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    mapping = module.build_label_mappings(protocol)[0]
    note = "Two channels are absent and remain explicit nulls."
    prompt = module.build_prompt("test domain", note, protocol, mapping)
    assert "EXPECTED_CONTEXT_CLASS" not in prompt
    assert "EVALUATION_NOTE_START\n" + note + "\nEVALUATION_NOTE_END" in prompt
    assert prompt.count(note) == 1
    assert not any(context in prompt for context in protocol["context_classes"])


def test_permutation_aggregation_cancels_label_assignment() -> None:
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    records = []
    for mapping in module.build_label_mappings(protocol):
        semantic_scores = {
            context: 2.0 if context == "noise" else 0.5
            for context in mapping.values()
        }
        records.append(
            {
                "semantic_scores": semantic_scores,
                "selected_context_class": "noise",
            }
        )
    selected, scores, margin, agreement = module.aggregate_permutation_scores(records)
    assert selected == "noise"
    assert scores["noise"] == 2.0
    assert margin == 1.5
    assert agreement == 1.0


def test_fixture_run_is_reproducible_and_cannot_qualify_real_model(
    tmp_path: Path,
) -> None:
    module = load_module()
    result = module.run_qualification(
        PROTOCOL_PATH,
        tmp_path,
        module.DeterministicCalibrationFixture(),
        run_timestamp="2026-07-15T00:00:00+00:00",
    )
    aggregate = result["aggregate_metrics"]
    assert aggregate["decision_count"] == 30
    assert aggregate["overall_accuracy"] == 1.0
    assert aggregate["unsupported_output_rate"] == 0.0
    assert aggregate["mean_permutation_agreement"] == 1.0
    assert result["trace_chain"]["verified"] is True
    assert result["qualification_gate"]["checks"]["real_model"] is False
    assert result["qualification_gate"]["checks"]["cuda_execution"] is False
    assert result["qualification_gate"]["qualification_gate_passed"] is False

    traces = [
        json.loads(line)
        for line in (tmp_path / "traces.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(traces) == 30
    assert all(len(row["permutation_records"]) == 6 for row in traces)
    assert all("EXPECTED_CONTEXT_CLASS" not in row["note"] for row in traces)

    manifest = json.loads(
        (tmp_path / "manifest.sha256.json").read_text(encoding="utf-8")
    )
    for name, metadata in manifest["files"].items():
        artifact = tmp_path / name
        assert artifact.stat().st_size == metadata["bytes"]
        assert module.core.file_sha256(artifact) == metadata["sha256"]
    for relative, expected_hash in manifest["source_files"].items():
        assert module.core.file_sha256(ROOT / relative) == expected_hash
    assert len(manifest["manifest_sha256"]) == 64
