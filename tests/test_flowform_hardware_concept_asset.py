from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METADATA = (
    ROOT
    / "assets"
    / "hardware"
    / "flowform_curved_motherboard_honeycomb_battery_v2_concept.json"
)


def test_flowform_hardware_concept_asset_is_integrity_bound() -> None:
    payload = json.loads(METADATA.read_text(encoding="utf-8"))
    image_path = ROOT / payload["asset_path"]

    assert payload["schema"] == "lumencore.hardware_concept_asset.v1"
    assert payload["status"] == (
        "GENERATED_CONCEPT_RENDER_NOT_ENGINEERING_VALIDATION"
    )
    assert image_path.is_file()
    assert image_path.stat().st_size == payload["bytes"]
    assert hashlib.sha256(image_path.read_bytes()).hexdigest() == payload["sha256"]
    assert payload["width_pixels"] == 1536
    assert payload["height_pixels"] == 1024


def test_flowform_hardware_concept_asset_preserves_claim_boundary() -> None:
    payload = json.loads(METADATA.read_text(encoding="utf-8"))
    boundary = payload["claim_boundary"].lower()

    for required in (
        "ai-generated",
        "not cad",
        "not a schematic",
        "not a fabricated prototype",
        "not proof of improved signal integrity",
        "safety certification",
        "commercial readiness",
    ):
        assert required in boundary

    next_steps = payload["required_engineering_next_steps"]
    assert len(next_steps) >= 5
    assert any("signal-integrity" in step for step in next_steps)
    assert any("battery-safety" in step for step in next_steps)
