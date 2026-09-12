#!/usr/bin/env python3
"""Measure an STL as a digital artifact without making physical-performance claims."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import struct
from typing import Iterable


SCHEMA = "lumencore.stl_digital_mesh_receipt.v1"
VERTEX_LINE = re.compile(
    rb"^\s*vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$",
    re.MULTILINE,
)

Vertex = tuple[float, float, float]
Triangle = tuple[Vertex, Vertex, Vertex]


class StlReceiptError(ValueError):
    """Raised when an STL cannot be measured safely."""


def sha256_bytes(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def canonical_sha256(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return sha256_bytes(encoded)


def normalize_vertex(vertex: Iterable[float]) -> Vertex:
    values = tuple(float(value) for value in vertex)
    if len(values) != 3 or not all(math.isfinite(value) for value in values):
        raise StlReceiptError("STL contains a non-finite or malformed vertex")
    return values  # type: ignore[return-value]


def parse_binary(body: bytes) -> tuple[list[Triangle], list[Vertex]] | None:
    if len(body) < 84:
        return None
    triangle_count = struct.unpack_from("<I", body, 80)[0]
    expected = 84 + triangle_count * 50
    if expected != len(body):
        return None
    triangles: list[Triangle] = []
    normals: list[Vertex] = []
    offset = 84
    for _ in range(triangle_count):
        values = struct.unpack_from("<12fH", body, offset)
        normal = normalize_vertex(values[0:3])
        triangle = (
            normalize_vertex(values[3:6]),
            normalize_vertex(values[6:9]),
            normalize_vertex(values[9:12]),
        )
        normals.append(normal)
        triangles.append(triangle)
        offset += 50
    return triangles, normals


def parse_ascii(body: bytes) -> tuple[list[Triangle], list[Vertex]]:
    vertices = [
        normalize_vertex(float(group) for group in match.groups())
        for match in VERTEX_LINE.finditer(body)
    ]
    if not vertices or len(vertices) % 3:
        raise StlReceiptError("ASCII STL contains no complete triangle set")
    triangles = [tuple(vertices[index : index + 3]) for index in range(0, len(vertices), 3)]
    return triangles, [(0.0, 0.0, 0.0)] * len(triangles)  # type: ignore[list-item]


def load_stl(body: bytes) -> tuple[str, list[Triangle], list[Vertex]]:
    parsed = parse_binary(body)
    if parsed is not None:
        triangles, normals = parsed
        if not triangles:
            raise StlReceiptError("binary STL contains zero triangles")
        return "binary", triangles, normals
    if body.lstrip().lower().startswith(b"solid"):
        triangles, normals = parse_ascii(body)
        return "ascii", triangles, normals
    raise StlReceiptError("STL is neither exact-length binary nor parseable ASCII")


def subtract(a: Vertex, b: Vertex) -> Vertex:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a: Vertex, b: Vertex) -> Vertex:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a: Vertex, b: Vertex) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def magnitude(vector: Vertex) -> float:
    return math.sqrt(dot(vector, vector))


def edge_key(a: Vertex, b: Vertex) -> tuple[Vertex, Vertex]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def triangle_metrics(triangle: Triangle) -> tuple[float, float, Vertex]:
    a, b, c = triangle
    computed = cross(subtract(b, a), subtract(c, a))
    area = magnitude(computed) / 2.0
    signed_volume = dot(a, cross(b, c)) / 6.0
    return area, signed_volume, computed


def connected_component_count(
    triangles: list[Triangle], edge_to_triangles: dict[tuple[Vertex, Vertex], list[int]]
) -> int:
    parent = list(range(len(triangles)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for members in edge_to_triangles.values():
        for member in members[1:]:
            union(members[0], member)
    return len({find(index) for index in range(len(triangles))})


def measure(body: bytes, source_name: str, measured_at_utc: str) -> dict[str, object]:
    stl_format, triangles, stored_normals = load_stl(body)
    vertices = [vertex for triangle in triangles for vertex in triangle]
    unique_vertices = set(vertices)
    edge_to_triangles: dict[tuple[Vertex, Vertex], list[int]] = defaultdict(list)
    areas: list[float] = []
    signed_volumes: list[float] = []
    degenerate = 0
    stored_normal_mismatch = 0

    for index, triangle in enumerate(triangles):
        for a, b in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
            edge_to_triangles[edge_key(a, b)].append(index)
        area, signed_volume, computed_normal = triangle_metrics(triangle)
        areas.append(area)
        signed_volumes.append(signed_volume)
        if area <= 1e-12:
            degenerate += 1
        stored = stored_normals[index]
        if magnitude(stored) > 0 and magnitude(computed_normal) > 0:
            alignment = dot(stored, computed_normal) / (
                magnitude(stored) * magnitude(computed_normal)
            )
            if alignment < 0.99:
                stored_normal_mismatch += 1

    incidence = Counter(len(members) for members in edge_to_triangles.values())
    boundary_edges = incidence.get(1, 0)
    manifold_edges = incidence.get(2, 0)
    non_manifold_edges = sum(count for degree, count in incidence.items() if degree > 2)
    minimum = tuple(min(vertex[axis] for vertex in vertices) for axis in range(3))
    maximum = tuple(max(vertex[axis] for vertex in vertices) for axis in range(3))
    extents = tuple(maximum[axis] - minimum[axis] for axis in range(3))
    component_count = connected_component_count(triangles, edge_to_triangles)
    watertight_by_edge_incidence = boundary_edges == 0 and non_manifold_edges == 0

    receipt: dict[str, object] = {
        "schema": SCHEMA,
        "measured_at_utc": measured_at_utc,
        "measurement_scope": "digital STL structure only",
        "source": {
            "name": source_name,
            "bytes": len(body),
            "sha256": sha256_bytes(body),
            "format": stl_format,
        },
        "mesh": {
            "triangle_count": len(triangles),
            "unique_vertex_count": len(unique_vertices),
            "unique_edge_count": len(edge_to_triangles),
            "connected_component_count": component_count,
            "degenerate_triangle_count": degenerate,
            "boundary_edge_count": boundary_edges,
            "two_incident_triangle_edge_count": manifold_edges,
            "non_manifold_edge_count": non_manifold_edges,
            "watertight_by_edge_incidence": watertight_by_edge_incidence,
            "stored_normal_mismatch_count": stored_normal_mismatch,
            "bounds_min_source_units": list(minimum),
            "bounds_max_source_units": list(maximum),
            "extents_source_units": list(extents),
            "surface_area_source_units_squared": sum(areas),
            "signed_volume_source_units_cubed": sum(signed_volumes),
            "absolute_signed_volume_source_units_cubed": abs(sum(signed_volumes)),
            "coordinate_unit_declared": False,
        },
        "quality_assessment": {
            "severity": "medium",
            "confidence": "high for digital structure; none for physical performance",
            "finding": (
                "The file is a non-empty parseable digital mesh. Multiple disconnected "
                "components and an undeclared coordinate unit require design-owner review "
                "before slicing, fabrication, or dimensional interpretation."
            ),
        },
        "allowed_claims": [
            "The exact source file exists at the recorded SHA-256 and byte count.",
            "The mesh contains the recorded number of triangles, vertices, edges, and connected components.",
            "The recorded bounds, extents, area, and signed-volume calculations are digital measurements in undeclared source units.",
            "Edge-incidence checks establish only the recorded digital topology result.",
        ],
        "not_proven": [
            "coordinate unit or intended physical scale",
            "design intent or source-CAD provenance",
            "printability, slicer success, or fabricated prototype",
            "dimensional accuracy or manufacturing tolerance",
            "material, structural, thermal, vibration, resonance, aerospace, or safety performance",
            "patent scope, public license, certification, or external validation",
        ],
        "next_gate": [
            "Founder declares units, intended function, and source-CAD provenance.",
            "Run qualified mesh checks for normals, self-intersections, minimum wall thickness, and intended component relationships.",
            "Generate a slicer receipt using declared printer, material, orientation, supports, and tolerances.",
            "Print a low-risk test article and preserve measurement photos, failures, settings, and hashes.",
            "Complete IP and public-license review before releasing the raw STL.",
        ],
        "public_source_release_authorized": False,
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt


def render_markdown(receipt: dict[str, object]) -> str:
    source = receipt["source"]
    mesh = receipt["mesh"]
    assessment = receipt["quality_assessment"]
    assert isinstance(source, dict) and isinstance(mesh, dict) and isinstance(assessment, dict)
    lines = [
        "# LumenFrame V1 Digital Mesh Measurement Receipt",
        "",
        f"**Measured UTC:** {receipt['measured_at_utc']}",
        f"**Source identity:** `{source['sha256']}` ({source['bytes']} bytes)",
        f"**Receipt identity:** `{receipt['receipt_sha256']}`",
        "",
        "## Measured digital structure",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| STL format | {source['format']} |",
        f"| Triangles | {mesh['triangle_count']} |",
        f"| Unique vertices | {mesh['unique_vertex_count']} |",
        f"| Unique edges | {mesh['unique_edge_count']} |",
        f"| Connected components | {mesh['connected_component_count']} |",
        f"| Degenerate triangles | {mesh['degenerate_triangle_count']} |",
        f"| Boundary edges | {mesh['boundary_edge_count']} |",
        f"| Non-manifold edges | {mesh['non_manifold_edge_count']} |",
        f"| Watertight by edge incidence | {str(mesh['watertight_by_edge_incidence']).lower()} |",
        f"| Bounds, source units | {mesh['bounds_min_source_units']} to {mesh['bounds_max_source_units']} |",
        f"| Extents, source units | {mesh['extents_source_units']} |",
        f"| Surface area, source units squared | {mesh['surface_area_source_units_squared']:.6f} |",
        f"| Absolute signed volume, source units cubed | {mesh['absolute_signed_volume_source_units_cubed']:.6f} |",
        "",
        "The coordinate unit is not declared. Area and volume therefore remain unitless source-coordinate calculations, not physical dimensions.",
        "",
        "## Quality assessment",
        "",
        f"- Severity: **{assessment['severity']}**",
        f"- Confidence: **{assessment['confidence']}**",
        f"- Finding: {assessment['finding']}",
        "",
        "## Allowed measured claims",
        "",
        *[f"- {item}" for item in receipt["allowed_claims"]],
        "",
        "## Not proven",
        "",
        *[f"- {item}" for item in receipt["not_proven"]],
        "",
        "## Next evidence gate",
        "",
        *[f"{index}. {item}" for index, item in enumerate(receipt["next_gate"], 1)],
        "",
        "The raw STL remains private and is not authorized for public release by this receipt.",
    ]
    return "\n".join(lines) + "\n"


def parse_utc(value: str) -> str:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must include UTC offset")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--json-out", required=True, type=Path)
    parser.add_argument("--md-out", required=True, type=Path)
    parser.add_argument("--as-of-utc", required=True, type=parse_utc)
    args = parser.parse_args()
    body = args.input.read_bytes()
    receipt = measure(body, args.input.name, args.as_of_utc)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    args.md_out.write_text(render_markdown(receipt), encoding="utf-8", newline="\n")
    print(json.dumps({"valid": True, "receipt_sha256": receipt["receipt_sha256"], "mesh": receipt["mesh"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
