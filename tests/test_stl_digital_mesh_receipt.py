from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "BUILD_STL_DIGITAL_MESH_RECEIPT.py"
JSON_RECEIPT = ROOT / "evidence" / "lumenframe_v1_digital_mesh_receipt.json"
MD_RECEIPT = ROOT / "docs" / "LUMENFRAME_V1_DIGITAL_MESH_RECEIPT_2026-08-31.md"


def load_module():
    spec = importlib.util.spec_from_file_location("stl_receipt", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cube_stl() -> bytes:
    vertices = {
        "000": (0.0, 0.0, 0.0), "100": (1.0, 0.0, 0.0),
        "010": (0.0, 1.0, 0.0), "110": (1.0, 1.0, 0.0),
        "001": (0.0, 0.0, 1.0), "101": (1.0, 0.0, 1.0),
        "011": (0.0, 1.0, 1.0), "111": (1.0, 1.0, 1.0),
    }
    faces = [
        ("000", "110", "100"), ("000", "010", "110"),
        ("001", "101", "111"), ("001", "111", "011"),
        ("000", "100", "101"), ("000", "101", "001"),
        ("010", "011", "111"), ("010", "111", "110"),
        ("000", "001", "011"), ("000", "011", "010"),
        ("100", "110", "111"), ("100", "111", "101"),
    ]
    body = bytearray(b"test cube".ljust(80, b"\0"))
    body.extend(struct.pack("<I", len(faces)))
    for face in faces:
        values = (0.0, 0.0, 0.0, *vertices[face[0]], *vertices[face[1]], *vertices[face[2]], 0)
        body.extend(struct.pack("<12fH", *values))
    return bytes(body)


def test_closed_cube_is_measured_as_one_watertight_component():
    module = load_module()
    receipt = module.measure(cube_stl(), "cube.stl", "2026-08-31T00:00:00Z")
    mesh = receipt["mesh"]
    assert mesh["triangle_count"] == 12
    assert mesh["unique_vertex_count"] == 8
    assert mesh["connected_component_count"] == 1
    assert mesh["boundary_edge_count"] == 0
    assert mesh["non_manifold_edge_count"] == 0
    assert mesh["watertight_by_edge_incidence"] is True
    assert mesh["extents_source_units"] == [1.0, 1.0, 1.0]
    assert receipt["public_source_release_authorized"] is False
    assert receipt["receipt_sha256"] == module.canonical_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    )


def test_empty_ascii_stl_is_rejected():
    module = load_module()
    with pytest.raises(module.StlReceiptError, match="no complete triangle"):
        module.measure(b"solid empty\nendsolid empty\n", "empty.stl", "2026-08-31T00:00:00Z")


def test_public_receipt_has_no_private_absolute_path_and_matches_markdown():
    payload = json.loads(JSON_RECEIPT.read_text(encoding="utf-8"))
    text = JSON_RECEIPT.read_text(encoding="utf-8") + MD_RECEIPT.read_text(encoding="utf-8")
    assert payload["schema"] == "lumencore.stl_digital_mesh_receipt.v1"
    assert payload["mesh"]["triangle_count"] == 96
    assert payload["mesh"]["connected_component_count"] == 8
    assert payload["source"]["sha256"] == "28c96fbc19d032d0cfe70f4252b4abf8e5daa444fff825a706b01bca6fdd1ad4"
    assert "C:\\Users\\" not in text
    assert "iCloud" not in text
    assert "not authorized for public release" in text


def test_cli_rebuilds_identical_receipts(tmp_path):
    source = tmp_path / "cube.stl"
    source.write_bytes(cube_stl())
    first_json = tmp_path / "first.json"
    first_md = tmp_path / "first.md"
    second_json = tmp_path / "second.json"
    second_md = tmp_path / "second.md"
    base = [sys.executable, str(MODULE_PATH), "--input", str(source), "--as-of-utc", "2026-08-31T00:00:00Z"]
    subprocess.run([*base, "--json-out", str(first_json), "--md-out", str(first_md)], check=True, capture_output=True, text=True)
    subprocess.run([*base, "--json-out", str(second_json), "--md-out", str(second_md)], check=True, capture_output=True, text=True)
    assert first_json.read_bytes() == second_json.read_bytes()
    assert first_md.read_bytes() == second_md.read_bytes()
