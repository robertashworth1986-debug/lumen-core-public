from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARDWARE_DIR = ROOT / "assets" / "hardware"
V1_METADATA = HARDWARE_DIR / "flowform_service_robot_v1_concept.json"
V2_METADATA = HARDWARE_DIR / "flowform_lumenshell_robot_ev_v2_concept.json"
V3_METADATA = HARDWARE_DIR / "flowform_lumenshell_dualmode_vtol_v3_concept.json"


def test_flowform_robot_v1_concept_asset_is_integrity_bound() -> None:
    payload = json.loads(V1_METADATA.read_text(encoding="utf-8"))
    image_path = ROOT / payload["asset_path"]

    assert payload["schema"] == "lumencore.hardware_concept_asset.v1"
    assert payload["asset_id"] == "flowform_service_robot_v1"
    assert payload["status"] == "GENERATED_CONCEPT_RENDER_NOT_ENGINEERING_VALIDATION"
    assert image_path.is_file()
    assert image_path.stat().st_size == payload["bytes"]
    assert hashlib.sha256(image_path.read_bytes()).hexdigest() == payload["sha256"]
    assert (payload["width_pixels"], payload["height_pixels"]) == (1536, 1024)


def test_flowform_robot_v1_concept_preserves_lineage_and_claim_boundary() -> None:
    payload = json.loads(V1_METADATA.read_text(encoding="utf-8"))
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


def test_lumenshell_robot_ev_v2_is_integrity_bound() -> None:
    payload = json.loads(V2_METADATA.read_text(encoding="utf-8"))
    image_path = ROOT / payload["asset_path"]

    assert payload["schema"] == "lumencore.hardware_concept_asset.v1"
    assert payload["asset_id"] == "flowform_lumenshell_robot_ev_v2"
    assert payload["status"] == "GENERATED_CONCEPT_RENDER_NOT_ENGINEERING_VALIDATION"
    assert image_path.is_file()
    assert image_path.stat().st_size == payload["bytes"]
    assert hashlib.sha256(image_path.read_bytes()).hexdigest() == payload["sha256"]
    assert (payload["width_pixels"], payload["height_pixels"]) == (1536, 1024)


def test_lumenshell_robot_ev_v2_restores_source_semantics_without_physics_claims() -> None:
    v1 = json.loads(V1_METADATA.read_text(encoding="utf-8"))
    v2 = json.loads(V2_METADATA.read_text(encoding="utf-8"))
    translation = v2["bounded_design_translation"]
    boundary = v2["claim_boundary"].lower()

    assert v2["supersedes_asset_id"] == v1["asset_id"]
    assert v2["private_source_audit"]["source_document_content_published"] is False
    assert v2["private_source_audit"]["source_claims_accepted_without_test"] is False
    assert "hypothesis requiring" in translation["cymatic_wave_channels"]
    assert "source/sink routing metaphor" in translation["whitehole_blackhole_logic"]
    assert "separate electric-vehicle" in translation["honeycomb_battery"]
    for required in (
        "not cad",
        "not a schematic",
        "not executable robot or vehicle software",
        "not a fabricated prototype",
        "not test evidence",
        "not a safety assessment",
        "not patentability evidence",
        "not literal astrophysics",
        "not a validated resonance or energy-dissipation result",
        "commercial readiness",
        "regulatory compliance",
    ):
        assert required in boundary

    next_steps = v2["required_engineering_next_steps"]
    assert len(next_steps) >= 9
    assert any("modal response" in step for step in next_steps)
    assert any("flat-shell" in step for step in next_steps)
    assert any("conservation rules" in step for step in next_steps)
    assert any("ev cell chemistry" in step.lower() for step in next_steps)
    assert any("qualified independent" in step for step in next_steps)


def test_lumenshell_dualmode_vtol_v3_corrects_the_operating_concept() -> None:
    v2 = json.loads(V2_METADATA.read_text(encoding="utf-8"))
    v3 = json.loads(V3_METADATA.read_text(encoding="utf-8"))
    boundary = v3["claim_boundary"].lower()

    assert v3["supersedes_asset_id"] == v2["asset_id"]
    assert "wearable" in v3["bounded_design_translation"]["dual_mode"].lower()
    assert "unoccupied" in v3["bounded_design_translation"]["dual_mode"].lower()
    assert "detachable propulsion" in v3["bounded_design_translation"]["jet_pack"].lower()
    assert "not presented as primary lift" in v3["bounded_design_translation"][
        "sound_and_frequency"
    ]
    assert "not authorization" in boundary
    assert "does not prove human flight" in boundary
    assert any("FAA" in step for step in v3["required_engineering_next_steps"])
