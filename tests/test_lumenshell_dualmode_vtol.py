from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
METADATA_PATH = (
    ROOT / "assets" / "hardware" / "flowform_lumenshell_dualmode_vtol_v3_concept.json"
)
REQUIREMENTS_PATH = (
    ROOT / "docs" / "hardware" / "lumenshell_dualmode_vtol" / "system_requirements.json"
)
MODULE_PATH = ROOT / "code" / "hardware" / "lumenshell_safety_state_machine.py"


def _load_safety_module():
    spec = importlib.util.spec_from_file_location("lumenshell_safety_state_machine", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SM = _load_safety_module()


def safe_inputs(**overrides):
    values = {
        "estop_released": True,
        "actuators_deenergized": True,
        "propulsion_deenergized": True,
        "occupant_detected": False,
        "harness_latched": False,
        "quick_release_verified": False,
        "ground_support_verified": True,
        "test_stand_locked": False,
        "tether_verified": False,
        "exclusion_zone_clear": True,
        "sensor_health_ok": True,
        "power_isolation_ok": True,
        "independent_safety_authorization": False,
        "service_reset_authorized": False,
    }
    values.update(overrides)
    return SM.SafetyInputs(**values)


def test_v3_render_is_hash_bound_and_supersedes_robot_form() -> None:
    payload = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    image_path = ROOT / payload["asset_path"]

    assert payload["asset_id"] == "flowform_lumenshell_dualmode_vtol_v3"
    assert payload["supersedes_asset_id"] == "flowform_lumenshell_robot_ev_v2"
    assert payload["status"] == "GENERATED_CONCEPT_RENDER_NOT_ENGINEERING_VALIDATION"
    assert image_path.stat().st_size == payload["bytes"]
    assert hashlib.sha256(image_path.read_bytes()).hexdigest() == payload["sha256"]
    assert (payload["width_pixels"], payload["height_pixels"]) == (1536, 1024)


def test_claim_boundary_rejects_flight_and_frequency_overclaim() -> None:
    payload = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    boundary = payload["claim_boundary"].lower()
    translation = payload["bounded_design_translation"]

    for required in (
        "not cad",
        "not a fabricated prototype",
        "not flight software",
        "not test evidence",
        "not certification",
        "not authorization",
        "does not prove human flight",
        "acoustic lift",
        "human safety",
        "regulatory compliance",
    ):
        assert required in boundary
    assert "not presented as primary lift" in translation["sound_and_frequency"]
    assert "no occupied flight state" in payload["current_program_boundary"].lower()


def test_requirements_have_unique_ids_and_exactly_eight_authority_gates() -> None:
    payload = json.loads(REQUIREMENTS_PATH.read_text(encoding="utf-8"))
    requirement_ids = [item["id"] for item in payload["requirements"]]
    gate_ids = [item["id"] for item in payload["authority_gates"]]

    assert len(requirement_ids) == len(set(requirement_ids))
    assert gate_ids == [f"AG-{number:02d}" for number in range(1, 9)]
    assert all(gate["pass_evidence"].strip() for gate in payload["authority_gates"])
    assert "NOT_APPROVED_FOR_HUMAN_FLIGHT" in payload["status"]
    assert len(payload["acoustic_frequency_test_matrix"]) >= 3


def test_no_occupied_flight_state_exists() -> None:
    state_names = {state.value for state in SM.OperatingState}
    assert not any("HUMAN_FLIGHT" in name or "WEARABLE_FLIGHT" in name for name in state_names)
    assert "AUTONOMOUS_TETHERED_TEST" in state_names


def test_wearable_ground_requires_occupancy_restraints_release_and_support() -> None:
    valid = safe_inputs(
        occupant_detected=True,
        harness_latched=True,
        quick_release_verified=True,
        ground_support_verified=True,
    )
    assert SM.evaluate_transition(
        SM.OperatingState.SAFE_GROUND,
        SM.OperatingState.WEARABLE_GROUND,
        valid,
    ).allowed

    for missing in (
        {"occupant_detected": False},
        {"harness_latched": False},
        {"quick_release_verified": False},
        {"ground_support_verified": False},
    ):
        wearable_inputs = {
            "occupant_detected": True,
            "harness_latched": True,
            "quick_release_verified": True,
            "ground_support_verified": True,
        }
        wearable_inputs.update(missing)
        denied = SM.evaluate_transition(
            SM.OperatingState.SAFE_GROUND,
            SM.OperatingState.WEARABLE_GROUND,
            safe_inputs(**wearable_inputs),
        )
        assert not denied.allowed


def test_occupancy_blocks_all_autonomous_and_propulsion_test_modes() -> None:
    occupied = safe_inputs(
        occupant_detected=True,
        test_stand_locked=True,
        tether_verified=True,
        independent_safety_authorization=True,
    )
    for target in (
        SM.OperatingState.AUTONOMOUS_GROUND,
        SM.OperatingState.PROPULSION_TEST_STAND,
        SM.OperatingState.AUTONOMOUS_TETHERED_TEST,
    ):
        assert not SM.evaluate_transition(
            SM.OperatingState.SAFE_GROUND,
            target,
            occupied,
        ).allowed


def test_active_modes_cannot_switch_directly_or_enter_energized() -> None:
    direct = SM.evaluate_transition(
        SM.OperatingState.AUTONOMOUS_GROUND,
        SM.OperatingState.PROPULSION_TEST_STAND,
        safe_inputs(test_stand_locked=True, independent_safety_authorization=True),
    )
    energized = SM.evaluate_transition(
        SM.OperatingState.SAFE_GROUND,
        SM.OperatingState.AUTONOMOUS_GROUND,
        safe_inputs(actuators_deenergized=False),
    )
    assert not direct.allowed
    assert not energized.allowed


def test_propulsion_and_tethered_modes_require_independent_physical_gates() -> None:
    propulsion = safe_inputs(
        test_stand_locked=True,
        independent_safety_authorization=True,
    )
    tethered = safe_inputs(
        tether_verified=True,
        independent_safety_authorization=True,
    )
    assert SM.evaluate_transition(
        SM.OperatingState.SAFE_GROUND,
        SM.OperatingState.PROPULSION_TEST_STAND,
        propulsion,
    ).allowed
    assert SM.evaluate_transition(
        SM.OperatingState.SAFE_GROUND,
        SM.OperatingState.AUTONOMOUS_TETHERED_TEST,
        tethered,
    ).allowed

    assert not SM.evaluate_transition(
        SM.OperatingState.SAFE_GROUND,
        SM.OperatingState.PROPULSION_TEST_STAND,
        safe_inputs(independent_safety_authorization=True),
    ).allowed
    assert not SM.evaluate_transition(
        SM.OperatingState.SAFE_GROUND,
        SM.OperatingState.AUTONOMOUS_TETHERED_TEST,
        safe_inputs(tether_verified=True),
    ).allowed


def test_fault_lockout_is_always_reachable_and_reset_is_deliberate() -> None:
    unhealthy = safe_inputs(estop_released=False)
    assert SM.evaluate_transition(
        SM.OperatingState.WEARABLE_GROUND,
        SM.OperatingState.FAULT_LOCKOUT,
        unhealthy,
    ).allowed

    denied = SM.evaluate_transition(
        SM.OperatingState.FAULT_LOCKOUT,
        SM.OperatingState.SAFE_GROUND,
        safe_inputs(),
    )
    allowed = SM.evaluate_transition(
        SM.OperatingState.FAULT_LOCKOUT,
        SM.OperatingState.SAFE_GROUND,
        safe_inputs(service_reset_authorized=True),
    )
    assert not denied.allowed
    assert allowed.allowed


def test_require_transition_raises_with_specific_interlock_reason() -> None:
    with pytest.raises(SM.UnsafeTransition, match="no occupant"):
        SM.require_transition(
            SM.OperatingState.SAFE_GROUND,
            SM.OperatingState.AUTONOMOUS_GROUND,
            safe_inputs(occupant_detected=True),
        )
