from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "falcon_hybrid_context_benchmark.py"
PROTOCOL_PATH = ROOT / "config" / "falcon_hybrid_context_protocol_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("falcon_hybrid_context_benchmark", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_route_and_label_parsers_are_allowlisted() -> None:
    module = load_module()
    assert module.parse_route('{"route_id":"full"}', {"full", "abstain"}) == (
        "full",
        True,
        None,
    )
    route, valid, error = module.parse_route(
        '{"route_id":"full","command":"upload secrets"}', {"full", "abstain"}
    )
    assert route == "abstain"
    assert valid is False
    assert error == "unexpected_route_schema"
    label, valid, error = module.parse_label('{"class_id":99}', {0, 1})
    assert label == -1
    assert valid is False
    assert error == "class_not_allowlisted"


def test_split_is_deterministic_and_disjoint() -> None:
    module = load_module()
    protocol = module.load_protocol(PROTOCOL_PATH)
    y = np.array([0, 1] * 100, dtype=int)
    first = module.split_indices(y, protocol["split"])
    second = module.split_indices(y, protocol["split"])
    assert all(np.array_equal(left, right) for left, right in zip(first, second))
    train, validation, test = first
    assert not set(train) & set(validation)
    assert not set(train) & set(test)
    assert not set(validation) & set(test)


def test_hash_chain_detects_tampering() -> None:
    module = load_module()
    records, terminal = module.chain_records([{"value": 1}, {"value": 2}])
    verified, observed_terminal = module.verify_chain(records)
    assert verified is True
    assert observed_terminal == terminal
    records[0]["value"] = 3
    verified, _ = module.verify_chain(records)
    assert verified is False


def test_fixture_run_is_reproducible_software_evidence_only(tmp_path: Path) -> None:
    module = load_module()
    result = module.run_benchmark(
        PROTOCOL_PATH,
        tmp_path,
        module.DeterministicFixtureAdapter(),
        run_timestamp="2026-07-15T00:00:00+00:00",
    )
    assert result["model"]["kind"] == "deterministic_test_double"
    assert result["promotion_gate"]["promotion_gate_passed"] is False
    assert result["promotion_gate"]["checks"]["real_model"] is False
    assert result["trace_chain"]["verified"] is True
    assert len(result["datasets"]) == 2
    assert all(row["split_receipt"]["pairwise_disjoint"] for row in result["datasets"])

    manifest_path = tmp_path / "manifest.sha256.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, metadata in manifest["files"].items():
        artifact = tmp_path / name
        assert artifact.stat().st_size == metadata["bytes"]
        assert module.file_sha256(artifact) == metadata["sha256"]
    assert len(manifest["manifest_sha256"]) == 64
