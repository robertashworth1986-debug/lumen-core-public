"""Fail-closed reference controller for the LumaSkin research platform.

This module is a reviewable requirements model. It does not drive wearable
hardware, establish biological safety, authorize human research, or replace a
qualified electrical, human-factors, or ethics review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ResearchState(str, Enum):
    POWERED_OFF = "POWERED_OFF"
    BENCH_SAFE = "BENCH_SAFE"
    MANNEQUIN_FIXTURE = "MANNEQUIN_FIXTURE"
    PASSIVE_FIT = "PASSIVE_FIT"
    SINGLE_ZONE_HAPTIC = "SINGLE_ZONE_HAPTIC"
    XR_MULTIMODAL = "XR_MULTIMODAL"
    FAULT_LOCKOUT = "FAULT_LOCKOUT"


ACTIVE_STATES = frozenset(
    {
        ResearchState.MANNEQUIN_FIXTURE,
        ResearchState.PASSIVE_FIT,
        ResearchState.SINGLE_ZONE_HAPTIC,
        ResearchState.XR_MULTIMODAL,
    }
)

HUMAN_STATES = frozenset(
    {
        ResearchState.PASSIVE_FIT,
        ResearchState.SINGLE_ZONE_HAPTIC,
        ResearchState.XR_MULTIMODAL,
    }
)

ENERGIZED_HUMAN_STATES = frozenset(
    {
        ResearchState.SINGLE_ZONE_HAPTIC,
        ResearchState.XR_MULTIMODAL,
    }
)

SUPPORTED_ZONES = frozenset(
    {
        "left_shoulder",
        "right_shoulder",
        "left_forearm",
        "right_forearm",
        "upper_back",
        "lower_back",
        "left_hip",
        "right_hip",
        "left_thigh",
        "right_thigh",
        "left_calf",
        "right_calf",
    }
)

REQUIRED_HUMAN_GATE_IDS = tuple(f"AG-{number:02d}" for number in range(1, 7))
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class CueLimits:
    """Preliminary command caps, not universal human-safety limits."""

    max_normalized_intensity: float = 0.25
    max_duration_ms: int = 250
    min_frequency_hz: float = 20.0
    max_frequency_hz: float = 180.0
    max_active_zones: int = 2


@dataclass(frozen=True)
class SafetyInputs:
    estop_released: bool
    outputs_zeroed: bool
    occupant_detected: bool
    fixture_locked: bool
    quick_release_verified: bool
    wearer_stop_signal_verified: bool
    skin_contact_ok: bool
    thermal_envelope_ok: bool
    electrical_envelope_ok: bool
    battery_health_ok: bool
    communications_ok: bool
    calibration_current: bool
    session_timer_armed: bool
    trained_supervisor_present: bool
    ethics_or_irb_determination_recorded: bool
    informed_consent_recorded: bool
    single_zone_gate_passed: bool
    cross_modal_sync_validated: bool
    service_reset_authorized: bool = False

    @property
    def critical_health_ok(self) -> bool:
        return (
            self.estop_released
            and self.thermal_envelope_ok
            and self.electrical_envelope_ok
            and self.battery_health_ok
            and self.communications_ok
        )

    @property
    def human_authority_ok(self) -> bool:
        return (
            self.occupant_detected
            and self.quick_release_verified
            and self.wearer_stop_signal_verified
            and self.skin_contact_ok
            and self.calibration_current
            and self.session_timer_armed
            and self.trained_supervisor_present
            and self.ethics_or_irb_determination_recorded
            and self.informed_consent_recorded
        )


@dataclass(frozen=True)
class CueRequest:
    zones: tuple[str, ...]
    normalized_intensity: float
    duration_ms: int
    frequency_hz: float

    @classmethod
    def from_values(
        cls,
        zones: Iterable[str],
        normalized_intensity: float,
        duration_ms: int,
        frequency_hz: float,
    ) -> "CueRequest":
        return cls(
            zones=tuple(zones),
            normalized_intensity=float(normalized_intensity),
            duration_ms=int(duration_ms),
            frequency_hz=float(frequency_hz),
        )


@dataclass(frozen=True)
class ArtifactBinding:
    expected_protocol_sha256: str
    observed_protocol_sha256: str
    expected_controller_sha256: str
    observed_controller_sha256: str
    expected_visual_sha256: str
    observed_visual_sha256: str


@dataclass(frozen=True)
class AuthorityGateEvidence:
    gate_id: str
    status: str
    verified_at_ms: int
    evidence_sha256: str


@dataclass(frozen=True)
class AuthoritySnapshot:
    gates: tuple[AuthorityGateEvidence, ...]
    artifact_binding: ArtifactBinding
    now_ms: int
    max_gate_age_ms: int


@dataclass(frozen=True)
class CueContext:
    sensor_timestamp_ms: int
    now_ms: int
    max_sensor_age_ms: int = 250
    authorized_source: bool = False
    conflicting_cue_active: bool = False
    ambiguous_routing: bool = False


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


class UnsafeTransition(RuntimeError):
    pass


class UnsafeCue(RuntimeError):
    pass


def evaluate_artifact_binding(binding: ArtifactBinding) -> Decision:
    """Require exact, well-formed hashes across the canonical research artifacts."""

    pairs = (
        (
            "protocol",
            binding.expected_protocol_sha256,
            binding.observed_protocol_sha256,
        ),
        (
            "controller",
            binding.expected_controller_sha256,
            binding.observed_controller_sha256,
        ),
        ("visual", binding.expected_visual_sha256, binding.observed_visual_sha256),
    )
    for name, expected, observed in pairs:
        expected = expected.lower()
        observed = observed.lower()
        if not _SHA256_PATTERN.fullmatch(expected):
            return Decision(False, f"{name} expected SHA-256 is malformed")
        if not _SHA256_PATTERN.fullmatch(observed):
            return Decision(False, f"{name} observed SHA-256 is malformed")
        if expected != observed:
            return Decision(False, f"{name} SHA-256 mismatch")
    return Decision(True, "canonical artifact hashes match")


def evaluate_authority_snapshot(snapshot: AuthoritySnapshot | None) -> Decision:
    """Validate current, evidenced authority gates before any participant state."""

    if snapshot is None:
        return Decision(False, "participant testing requires an authority snapshot")
    if snapshot.max_gate_age_ms <= 0:
        return Decision(False, "authority gate age limit must be positive")

    binding = evaluate_artifact_binding(snapshot.artifact_binding)
    if not binding.allowed:
        return binding

    by_id: dict[str, AuthorityGateEvidence] = {}
    for gate in snapshot.gates:
        if gate.gate_id in by_id:
            return Decision(False, f"duplicate authority gate: {gate.gate_id}")
        by_id[gate.gate_id] = gate

    missing = [gate_id for gate_id in REQUIRED_HUMAN_GATE_IDS if gate_id not in by_id]
    if missing:
        return Decision(False, f"missing authority gate: {missing[0]}")

    for gate_id in REQUIRED_HUMAN_GATE_IDS:
        gate = by_id[gate_id]
        if gate.status != "PASS":
            return Decision(False, f"authority gate is not PASS: {gate_id}")
        if not _SHA256_PATTERN.fullmatch(gate.evidence_sha256.lower()):
            return Decision(False, f"authority evidence SHA-256 is malformed: {gate_id}")
        age_ms = snapshot.now_ms - gate.verified_at_ms
        if age_ms < 0:
            return Decision(False, f"authority gate timestamp is in the future: {gate_id}")
        if age_ms > snapshot.max_gate_age_ms:
            return Decision(False, f"authority gate is stale: {gate_id}")

    return Decision(True, "all participant authority gates are current and hash-bound")


def evaluate_cue_context(context: CueContext | None) -> Decision:
    """Reject stale, ambiguous, conflicting, or unauthorized cue context."""

    if context is None:
        return Decision(False, "cue context is required")
    if not context.authorized_source:
        return Decision(False, "cue source is not authorized")
    if context.conflicting_cue_active:
        return Decision(False, "conflicting cue is active")
    if context.ambiguous_routing:
        return Decision(False, "cue routing is ambiguous")
    if context.max_sensor_age_ms <= 0:
        return Decision(False, "sensor age limit must be positive")

    sensor_age_ms = context.now_ms - context.sensor_timestamp_ms
    if sensor_age_ms < 0:
        return Decision(False, "sensor timestamp is in the future")
    if sensor_age_ms > context.max_sensor_age_ms:
        return Decision(False, "sensor timestamp is stale")
    return Decision(True, "cue context is current and unambiguous")


def _human_gate_reason(inputs: SafetyInputs) -> str | None:
    checks = (
        (inputs.occupant_detected, "human modes require verified occupancy"),
        (inputs.quick_release_verified, "quick release is not verified"),
        (inputs.wearer_stop_signal_verified, "wearer stop signal is not verified"),
        (inputs.skin_contact_ok, "skin-contact inspection is not current"),
        (inputs.calibration_current, "device calibration is not current"),
        (inputs.session_timer_armed, "session timer is not armed"),
        (inputs.trained_supervisor_present, "trained supervisor is absent"),
        (
            inputs.ethics_or_irb_determination_recorded,
            "ethics or IRB determination is not recorded",
        ),
        (inputs.informed_consent_recorded, "informed consent is not recorded"),
    )
    for passed, reason in checks:
        if not passed:
            return reason
    return None


def evaluate_transition(
    current: ResearchState,
    target: ResearchState,
    inputs: SafetyInputs,
    authority: AuthoritySnapshot | None = None,
) -> Decision:
    """Evaluate a requested research-state transition without side effects."""

    if target is ResearchState.FAULT_LOCKOUT:
        return Decision(True, "fault lockout is always reachable")

    if current is ResearchState.FAULT_LOCKOUT:
        if target is not ResearchState.POWERED_OFF:
            return Decision(False, "fault lockout can exit only to POWERED_OFF")
        if not inputs.service_reset_authorized:
            return Decision(False, "manual service reset is not authorized")
        if not inputs.outputs_zeroed or not inputs.critical_health_ok:
            return Decision(False, "reset requires healthy, zero-output hardware")
        return Decision(True, "manual reset conditions satisfied")

    if not inputs.critical_health_ok:
        return Decision(False, "critical health failure requires FAULT_LOCKOUT")

    if target is ResearchState.POWERED_OFF:
        if not inputs.outputs_zeroed:
            return Decision(False, "power-off requires zeroed outputs")
        return Decision(True, "power-off conditions satisfied")

    if target is ResearchState.BENCH_SAFE:
        if current is not ResearchState.POWERED_OFF:
            return Decision(False, "BENCH_SAFE may be entered only from POWERED_OFF")
        if inputs.occupant_detected:
            return Decision(False, "BENCH_SAFE entry requires no occupant")
        if not inputs.outputs_zeroed or not inputs.fixture_locked:
            return Decision(False, "bench entry requires zero outputs and a locked fixture")
        return Decision(True, "bench-safe interlocks satisfied")

    if current is not ResearchState.BENCH_SAFE:
        return Decision(False, "active test modes may be entered only from BENCH_SAFE")

    if not inputs.outputs_zeroed:
        return Decision(False, "active-mode entry begins with zeroed outputs")

    if target is ResearchState.MANNEQUIN_FIXTURE:
        if inputs.occupant_detected:
            return Decision(False, "mannequin testing requires no occupant")
        if not inputs.fixture_locked:
            return Decision(False, "mannequin fixture is not locked")
        if not inputs.calibration_current or not inputs.trained_supervisor_present:
            return Decision(False, "fixture testing requires calibration and supervision")
        return Decision(True, "mannequin-fixture interlocks satisfied")

    if target in HUMAN_STATES:
        reason = _human_gate_reason(inputs)
        if reason:
            return Decision(False, reason)
        authority_decision = evaluate_authority_snapshot(authority)
        if not authority_decision.allowed:
            return authority_decision

    if target is ResearchState.PASSIVE_FIT:
        return Decision(True, "passive-fit interlocks satisfied; outputs remain zero")

    if target is ResearchState.SINGLE_ZONE_HAPTIC:
        return Decision(True, "single-zone human-research interlocks satisfied")

    if target is ResearchState.XR_MULTIMODAL:
        if not inputs.single_zone_gate_passed:
            return Decision(False, "single-zone evidence gate has not passed")
        if not inputs.cross_modal_sync_validated:
            return Decision(False, "cross-modal synchronization is not validated")
        return Decision(True, "XR multimodal interlocks satisfied")

    return Decision(False, f"unsupported target state: {target.value}")


def evaluate_cue(
    state: ResearchState,
    request: CueRequest,
    inputs: SafetyInputs,
    limits: CueLimits | None = None,
    *,
    authority: AuthoritySnapshot | None = None,
    context: CueContext | None = None,
) -> Decision:
    """Authorize a bounded vibrotactile command or fail closed."""

    limits = limits or CueLimits()

    if state not in ENERGIZED_HUMAN_STATES:
        return Decision(False, "haptic cues require an energized human-test state")
    if not inputs.critical_health_ok:
        return Decision(False, "critical health failure requires zero output")

    reason = _human_gate_reason(inputs)
    if reason:
        return Decision(False, reason)

    authority_decision = evaluate_authority_snapshot(authority)
    if not authority_decision.allowed:
        return authority_decision

    context_decision = evaluate_cue_context(context)
    if not context_decision.allowed:
        return context_decision

    if not request.zones:
        return Decision(False, "at least one actuator zone is required")
    if len(set(request.zones)) != len(request.zones):
        return Decision(False, "duplicate actuator zones are not allowed")
    unsupported = sorted(set(request.zones) - SUPPORTED_ZONES)
    if unsupported:
        return Decision(False, f"unsupported actuator zone: {unsupported[0]}")

    zone_limit = 1 if state is ResearchState.SINGLE_ZONE_HAPTIC else limits.max_active_zones
    if len(request.zones) > zone_limit:
        return Decision(False, f"state permits at most {zone_limit} active zone(s)")

    if not 0.0 < request.normalized_intensity <= limits.max_normalized_intensity:
        return Decision(False, "requested intensity exceeds the preliminary command cap")
    if not 0 < request.duration_ms <= limits.max_duration_ms:
        return Decision(False, "requested duration exceeds the preliminary command cap")
    if not limits.min_frequency_hz <= request.frequency_hz <= limits.max_frequency_hz:
        return Decision(False, "requested frequency is outside the preliminary command band")

    if state is ResearchState.XR_MULTIMODAL:
        if not inputs.single_zone_gate_passed or not inputs.cross_modal_sync_validated:
            return Decision(False, "XR cue prerequisites are incomplete")

    return Decision(True, "cue is inside the bounded command envelope")


def require_transition(
    current: ResearchState,
    target: ResearchState,
    inputs: SafetyInputs,
    authority: AuthoritySnapshot | None = None,
) -> ResearchState:
    decision = evaluate_transition(current, target, inputs, authority)
    if not decision.allowed:
        raise UnsafeTransition(decision.reason)
    return target


def require_cue(
    state: ResearchState,
    request: CueRequest,
    inputs: SafetyInputs,
    limits: CueLimits | None = None,
    *,
    authority: AuthoritySnapshot | None = None,
    context: CueContext | None = None,
) -> CueRequest:
    decision = evaluate_cue(
        state,
        request,
        inputs,
        limits,
        authority=authority,
        context=context,
    )
    if not decision.allowed:
        raise UnsafeCue(decision.reason)
    return request
