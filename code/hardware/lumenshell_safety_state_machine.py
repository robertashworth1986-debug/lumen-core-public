"""Deterministic reference monitor for the LumenShell dual-mode concept.

This module is a requirements executable. It does not command actuators, fans,
power electronics, or flight hardware. Its purpose is to make the proposed
mode-separation rules reviewable and testable before hardware exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OperatingState(str, Enum):
    POWERED_OFF = "POWERED_OFF"
    SAFE_GROUND = "SAFE_GROUND"
    WEARABLE_GROUND = "WEARABLE_GROUND"
    AUTONOMOUS_GROUND = "AUTONOMOUS_GROUND"
    PROPULSION_TEST_STAND = "PROPULSION_TEST_STAND"
    AUTONOMOUS_TETHERED_TEST = "AUTONOMOUS_TETHERED_TEST"
    FAULT_LOCKOUT = "FAULT_LOCKOUT"


ACTIVE_STATES = frozenset(
    {
        OperatingState.WEARABLE_GROUND,
        OperatingState.AUTONOMOUS_GROUND,
        OperatingState.PROPULSION_TEST_STAND,
        OperatingState.AUTONOMOUS_TETHERED_TEST,
    }
)


@dataclass(frozen=True)
class SafetyInputs:
    """Independent interlock observations used by the reference monitor."""

    estop_released: bool
    actuators_deenergized: bool
    propulsion_deenergized: bool
    occupant_detected: bool
    harness_latched: bool
    quick_release_verified: bool
    ground_support_verified: bool
    test_stand_locked: bool
    tether_verified: bool
    exclusion_zone_clear: bool
    sensor_health_ok: bool
    power_isolation_ok: bool
    independent_safety_authorization: bool
    service_reset_authorized: bool = False

    @property
    def all_motion_deenergized(self) -> bool:
        return self.actuators_deenergized and self.propulsion_deenergized

    @property
    def critical_health_ok(self) -> bool:
        return self.estop_released and self.sensor_health_ok and self.power_isolation_ok


@dataclass(frozen=True)
class TransitionDecision:
    allowed: bool
    reason: str


class UnsafeTransition(RuntimeError):
    pass


def evaluate_transition(
    current: OperatingState,
    target: OperatingState,
    inputs: SafetyInputs,
) -> TransitionDecision:
    """Evaluate one requested state transition without side effects."""

    if target is OperatingState.FAULT_LOCKOUT:
        return TransitionDecision(True, "fault lockout is always reachable")

    if current is OperatingState.FAULT_LOCKOUT:
        if target is not OperatingState.SAFE_GROUND:
            return TransitionDecision(False, "fault lockout can exit only to SAFE_GROUND")
        if not inputs.service_reset_authorized:
            return TransitionDecision(False, "manual service reset is not authorized")
        if not inputs.all_motion_deenergized or not inputs.critical_health_ok:
            return TransitionDecision(False, "reset requires healthy, deenergized hardware")
        return TransitionDecision(True, "manual reset conditions satisfied")

    if not inputs.critical_health_ok:
        return TransitionDecision(False, "critical safety health requires FAULT_LOCKOUT")

    if target is OperatingState.POWERED_OFF:
        if not inputs.all_motion_deenergized:
            return TransitionDecision(False, "power-off requires all motion deenergized")
        return TransitionDecision(True, "power-off conditions satisfied")

    if target is OperatingState.SAFE_GROUND:
        if not inputs.all_motion_deenergized:
            return TransitionDecision(False, "SAFE_GROUND requires all motion deenergized")
        return TransitionDecision(True, "safe-ground conditions satisfied")

    if current is not OperatingState.SAFE_GROUND:
        return TransitionDecision(False, "active modes may be entered only from SAFE_GROUND")

    if not inputs.all_motion_deenergized:
        return TransitionDecision(False, "active-mode entry begins with motion deenergized")

    if target is OperatingState.WEARABLE_GROUND:
        if not inputs.occupant_detected:
            return TransitionDecision(False, "wearable mode requires verified occupancy")
        if not inputs.harness_latched or not inputs.quick_release_verified:
            return TransitionDecision(False, "wearable restraints and quick release are not verified")
        if not inputs.ground_support_verified:
            return TransitionDecision(False, "wearable mode is limited to verified ground support")
        return TransitionDecision(True, "wearable ground interlocks satisfied")

    if inputs.occupant_detected:
        return TransitionDecision(False, "autonomous and propulsion-test modes require no occupant")

    if target is OperatingState.AUTONOMOUS_GROUND:
        if not inputs.exclusion_zone_clear:
            return TransitionDecision(False, "autonomous ground exclusion zone is not clear")
        return TransitionDecision(True, "autonomous ground interlocks satisfied")

    if target is OperatingState.PROPULSION_TEST_STAND:
        if not inputs.test_stand_locked:
            return TransitionDecision(False, "propulsion module is not locked to its test stand")
        if not inputs.exclusion_zone_clear:
            return TransitionDecision(False, "propulsion test exclusion zone is not clear")
        if not inputs.independent_safety_authorization:
            return TransitionDecision(False, "independent propulsion-test authorization is absent")
        return TransitionDecision(True, "propulsion test-stand interlocks satisfied")

    if target is OperatingState.AUTONOMOUS_TETHERED_TEST:
        if not inputs.tether_verified:
            return TransitionDecision(False, "independent physical tether is not verified")
        if not inputs.exclusion_zone_clear:
            return TransitionDecision(False, "tethered-test exclusion zone is not clear")
        if not inputs.independent_safety_authorization:
            return TransitionDecision(False, "independent tethered-test authorization is absent")
        return TransitionDecision(True, "unoccupied tethered-test interlocks satisfied")

    return TransitionDecision(False, f"unsupported target state: {target.value}")


def require_transition(
    current: OperatingState,
    target: OperatingState,
    inputs: SafetyInputs,
) -> OperatingState:
    """Return the target state or raise when an interlock rejects it."""

    decision = evaluate_transition(current, target, inputs)
    if not decision.allowed:
        raise UnsafeTransition(decision.reason)
    return target
