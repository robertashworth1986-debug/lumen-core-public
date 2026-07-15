from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "falcon_constrained_context_router.py"
PROTOCOL_PATH = ROOT / "config" / "falcon_constrained_context_router_protocol_v2.json"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "falcon_constrained_context_router", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_protocol_has_a_distinct_identity_and_predeclared_decision_count() -> None:
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    assert protocol["schema"] == "falcon_constrained_context_router_protocol.v2"
    assert protocol["development_history"]["prior_gate_passed"] is False
    assert protocol["future_full_benchmark_holdout"][
        "must_exclude_prior_v1_test_rows"
    ] is True
    expected = len(protocol["datasets"]) * sum(
        len(row["evaluation_note_templates"])
        for row in protocol["context_classes"].values()
    )
    assert expected == protocol["qualification_gate"]["required_decision_count"] == 30


def test_prompt_omits_the_expected_context_label() -> None:
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    note = "Two channels are unavailable and appear as missing values."
    prompt = module.build_prompt("test domain", note, protocol)
    assert "EXPECTED_CONTEXT_CLASS" not in prompt
    assert "EVALUATION_NOTE_START\n" + note + "\nEVALUATION_NOTE_END" in prompt
    assert prompt.count(note) == 1


def test_candidate_selection_is_finite_and_deterministic() -> None:
    module = load_module()
    selected, margin = module.select_candidate(
        {"noise": -1.0, "dropout": -0.5, "nominal": -0.5}
    )
    assert selected == "dropout"
    assert margin == 0.0
    selected, margin = module.select_candidate(
        {"noise": float("nan"), "dropout": -0.7, "nominal": -1.2}
    )
    assert selected == "dropout"
    assert math.isclose(margin, 0.5)
    assert module.select_candidate({"noise": float("nan")}) == ("abstain", 0.0)


def test_fixture_run_is_reproducible_and_cannot_qualify_real_model(
    tmp_path: Path,
) -> None:
    module = load_module()
    result = module.run_qualification(
        PROTOCOL_PATH,
        tmp_path,
        module.DeterministicQualificationFixture(),
        run_timestamp="2026-07-15T00:00:00+00:00",
    )
    assert result["aggregate_metrics"]["decision_count"] == 30
    assert result["aggregate_metrics"]["overall_accuracy"] == 1.0
    assert result["aggregate_metrics"]["unsupported_output_rate"] == 0.0
    assert result["trace_chain"]["verified"] is True
    assert result["qualification_gate"]["checks"]["real_model"] is False
    assert result["qualification_gate"]["qualification_gate_passed"] is False

    traces = [
        json.loads(line)
        for line in (tmp_path / "traces.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(traces) == 30
    assert all("EXPECTED_CONTEXT_CLASS" not in row["prompt"] for row in traces)

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
