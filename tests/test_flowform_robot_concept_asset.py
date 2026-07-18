from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METADATA = (
    ROOT / "assets" / "hardware" / "flowform_service_robot_v1_concept.json"
)


def test_flowform_robot_concept_asset_is_integrity_bound() -> None:
    payload = json.loads(METADATA.read_text(encoding="utf-8"))
    image_path = ROOT / payload["asset_path"]

    assert payload["schema"] == "lumencore.hardware_concept_asset.v1"
    assert payload["asset_id"] == "flowform_service_robot_v1"
    assert payload["status"] == "GENERATED_CONCEPT_RENDER_NOT_ENGINEERING_VALIDATION"
    assert image_path.is_file()
    assert image_path.stat().st_size == payload["bytes"]
    assert hashlib.sha256(image_path.read_bytes()).hexdigest() == payload["sha256"]
    assert (payload["width_pixels"], payload["height_pixels"]) == (1536, 1024)


def test_flowform_robot_concept_preserves_lineage_and_claim_boundary() -> None:
    payload = json.loads(METADATA.read_text(encoding="utf-8"))
    boundary = payload["claim_boundary"].lower()

    assert payload["generation_provenance"]["reference_asset_id"] == (
        "flowform_curved_motherboard_honeycomb_battery_v3"
    )
    assert any("v3_concept.json" in path for path in payload["source_concept_references"])
    for required in (
        "ai-generated",
        "not cad",
        "not a schematic",
        "not executable robot software",
        "not a fabricated prototype",
        "not test evidence",
        "not a safety assessment",
        "commercial readiness",
        "patentability",
    ):
        assert required in boundary

    next_steps = payload["required_engineering_next_steps"]
    assert len(next_steps) >= 7
    assert any("hazard analysis" in step for step in next_steps)
    assert any("emergency-stop" in step for step in next_steps)
    assert any("independent engineering review" in step for step in next_steps)
