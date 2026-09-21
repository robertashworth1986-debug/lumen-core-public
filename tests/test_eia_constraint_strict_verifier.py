from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("strict_eia", ROOT / "code/ops/VERIFY_EIA_CONSTRAINT_REVIEW.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


@pytest.fixture
def packet(tmp_path, monkeypatch):
    output = tmp_path / "packet"
    output.mkdir()
    source = tmp_path / "source.txt"
    source.write_text("frozen input")
    result = output / "result.json"
    result.write_text('{"mae": 1}')
    def identity(path):
        return {"sha256": module.file_digest(path), "bytes": path.stat().st_size}
    manifest = {"schema": "test.v1", "inputs": {"source.txt": identity(source)}, "outputs": {"result.json": identity(result)}}
    path = output / "manifest.json"
    def write(value, repin=False):
        path.write_text(json.dumps(value))
        if repin:
            module.PACKETS["test"]["manifest_sha256"] = module.file_digest(path)
    monkeypatch.setattr(module, "PACKETS", {"test": {"directory": "packet", "schema": "test.v1", "manifest_sha256": "", "inputs": frozenset({"source.txt"}), "outputs": frozenset({"result.json"})}})
    write(manifest, repin=True)
    return tmp_path, manifest, write


def test_real_reviewed_packets_have_complete_matching_identities():
    original = module.verify_packet("original")
    later = module.verify_packet("later")
    assert (original["input_count"], original["output_count"]) == (6, 4)
    assert (later["input_count"], later["output_count"]) == (9, 2)


@pytest.mark.parametrize("mutation", ["empty", "deleted", "extra", "schema", "boolean_size", "bad_hash"])
def test_rejects_incomplete_or_invalid_records_even_if_repinning(mutation, packet):
    root, manifest, write = packet
    if mutation == "empty": manifest.update(inputs={}, outputs={})
    elif mutation == "deleted": manifest["outputs"].pop("result.json")
    elif mutation == "extra": manifest["outputs"]["other.json"] = manifest["outputs"]["result.json"]
    elif mutation == "schema": manifest["schema"] = "unreviewed.v1"
    elif mutation == "boolean_size": manifest["outputs"]["result.json"]["bytes"] = True
    else: manifest["outputs"]["result.json"]["sha256"] = "not-a-hash"
    write(manifest, repin=True)
    with pytest.raises(ValueError): module.verify_packet("test", root)


def test_rejects_changed_manifest_with_matching_rehashed_artifact(packet):
    root, manifest, write = packet
    result = root / "packet/result.json"
    result.write_text('{"mae": 0}')
    manifest["outputs"]["result.json"]["sha256"] = module.file_digest(result)
    write(manifest)
    with pytest.raises(ValueError, match="repository pin"):
        module.verify_packet("test", root)


@pytest.mark.parametrize("mutation", ["tamper", "missing", "symlink", "duplicate_key"])
def test_rejects_damaged_or_ambiguous_packet(mutation, packet):
    root, manifest, write = packet
    result = root / "packet/result.json"
    if mutation == "tamper": result.write_text('{"mae": 0}')
    elif mutation == "missing": result.unlink()
    elif mutation == "symlink":
        actual = root / "moved.json"
        result.rename(actual)
        result.symlink_to(actual)
    else:
        path = root / "packet/manifest.json"
        path.write_text(path.read_text().replace('"schema": "test.v1"', '"schema": "test.v1", "schema": "test.v1"'))
    with pytest.raises(ValueError): module.verify_packet("test", root)


@pytest.mark.parametrize("relative", ["../outside", "/absolute", "a/../source.txt", "a\\source.txt", "./source.txt"])
def test_path_must_be_canonical_and_contained(tmp_path, relative):
    with pytest.raises(ValueError): module.contained_file(tmp_path, relative)
