from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CONTROLLER_PATH = ROOT / "code" / "hardware" / "lumaskin_safety_controller.py"
BUILDER_PATH = ROOT / "code" / "ops" / "BUILD_LUMASKIN_PROTOCOL_PACKET.py"
PROTOCOL_PATH = ROOT / "config" / "lumaskin_test_protocol_v1.json"
ASSET_METADATA_PATH = (
    ROOT / "assets" / "hardware" / "flowform_lumaskin_xr_research_v1_concept.json"
)
LAB_INDEX_PATH = ROOT / "build_week" / "lumaskin_lab" / "index.html"
LAB_APP_PATH = ROOT / "build_week" / "lumaskin_lab" / "app.js"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SC = _load_module("lumaskin_safety_controller", CONTROLLER_PATH)
BUILDER = _load_module("lumaskin_protocol_builder", BUILDER_PATH)


def safe_inputs(**overrides):
    values = {
        "estop_released": True,
        "outputs_zeroed": True,
        "occupant_detected": False,
        "fixture_locked": True,
        "quick_release_verified": False,
        "wearer_stop_signal_verified": False,
        "skin_contact_ok": True,
        "thermal_envelope_ok": True,
        "electrical_envelope_ok": True,
        "battery_health_ok": True,
        "communications_ok": True,
        "calibration_current": True,
        "session_timer_armed": False,
        "trained_supervisor_present": True,
        "ethics_or_irb_determination_recorded": False,
        "informed_consent_recorded": False,
        "single_zone_gate_passed": False,
        "cross_modal_sync_validated": False,
        "service_reset_authorized": False,
    }
    values.update(overrides)
    return SC.SafetyInputs(**values)


def human_inputs(**overrides):
    values = {
        "occupant_detected": True,
        "quick_release_verified": True,
        "wearer_stop_signal_verified": True,
        "session_timer_armed": True,
        "ethics_or_irb_determination_recorded": True,
        "informed_consent_recorded": True,
    }
    values.update(overrides)
    return safe_inputs(**values)


def artifact_binding(**overrides):
    values = {
        "expected_protocol_sha256": "a" * 64,
        "observed_protocol_sha256": "a" * 64,
        "expected_controller_sha256": "b" * 64,
        "observed_controller_sha256": "b" * 64,
        "expected_visual_sha256": "c" * 64,
        "observed_visual_sha256": "c" * 64,
    }
    values.update(overrides)
    return SC.ArtifactBinding(**values)


def authority_snapshot(**overrides):
    now_ms = overrides.pop("now_ms", 100_000)
    gates = overrides.pop(
        "gates",
        tuple(
            SC.AuthorityGateEvidence(
                gate_id=f"AG-{number:02d}",
                status="PASS",
                verified_at_ms=now_ms - 1_000,
                evidence_sha256=f"{number:x}" * 64,
            )
            for number in range(1, 7)
        ),
    )
    values = {
        "gates": gates,
        "artifact_binding": artifact_binding(),
        "now_ms": now_ms,
        "max_gate_age_ms": 5_000,
    }
    values.update(overrides)
    return SC.AuthoritySnapshot(**values)


def cue_context(**overrides):
    values = {
        "sensor_timestamp_ms": 99_900,
        "now_ms": 100_000,
        "max_sensor_age_ms": 250,
        "authorized_source": True,
        "conflicting_cue_active": False,
        "ambiguous_routing": False,
    }
    values.update(overrides)
    return SC.CueContext(**values)


def test_protocol_has_ordered_test_families_and_authority_gates() -> None:
    payload = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    BUILDER.validate_protocol(payload)

    assert [item["id"] for item in payload["test_families"]] == [
        f"TF-{number:02d}" for number in range(1, 9)
    ]
    assert [item["id"] for item in payload["authority_gates"]] == [
        f"AG-{number:02d}" for number in range(1, 9)
    ]
    assert payload["human_test_hold"]["blocked_until_gates_pass"] == [
        f"AG-{number:02d}" for number in range(1, 7)
    ]


def test_status_packet_never_implies_human_or_independent_validation() -> None:
    payload = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    packet = BUILDER.build_packet(payload)

    assert packet["status"] == "BENCH_PROTOCOL_READY_HUMAN_TESTS_BLOCKED"
    assert packet["summary"]["human_testing_authorized"] is False
    assert packet["summary"]["independent_validation_complete"] is False
    assert all(item["status"] == "OPEN" for item in packet["authority_gates"])
    assert all(
        item["status"] == "PROTOCOL_DEFINED_NOT_RUN"
        for item in packet["test_families"]
    )
    assert packet["artifact_manifest"]["artifact_count"] == 10
    assert packet["artifact_manifest"]["visual_lineage_verified"] is True
    assert packet["public_projection"] == {
        "program_status": "BENCH_PROTOCOL_READY_HUMAN_TESTS_BLOCKED",
        "asset_status": "CONCEPT_DIAGRAM_NOT_ENGINEERING_VALIDATION",
        "human_testing_authorized": False,
        "independent_validation_complete": False,
    }


def test_bench_and_mannequin_modes_require_zero_output_and_no_occupant() -> None:
    assert SC.evaluate_transition(
        SC.ResearchState.POWERED_OFF,
        SC.ResearchState.BENCH_SAFE,
        safe_inputs(),
    ).allowed
    assert not SC.evaluate_transition(
        SC.ResearchState.POWERED_OFF,
        SC.ResearchState.BENCH_SAFE,
        safe_inputs(occupant_detected=True),
    ).allowed
    assert SC.evaluate_transition(
        SC.ResearchState.BENCH_SAFE,
        SC.ResearchState.MANNEQUIN_FIXTURE,
        safe_inputs(),
    ).allowed
    assert not SC.evaluate_transition(
        SC.ResearchState.BENCH_SAFE,
        SC.ResearchState.MANNEQUIN_FIXTURE,
        safe_inputs(occupant_detected=True),
    ).allowed


@pytest.mark.parametrize(
    "missing",
    [
        "occupant_detected",
        "quick_release_verified",
        "wearer_stop_signal_verified",
        "skin_contact_ok",
        "calibration_current",
        "session_timer_armed",
        "trained_supervisor_present",
        "ethics_or_irb_determination_recorded",
        "informed_consent_recorded",
    ],
)
def test_human_modes_require_every_authority_interlock(missing: str) -> None:
    inputs = human_inputs(**{missing: False})
    decision = SC.evaluate_transition(
        SC.ResearchState.BENCH_SAFE,
        SC.ResearchState.SINGLE_ZONE_HAPTIC,
        inputs,
    )
    assert not decision.allowed


def test_xr_mode_requires_single_zone_and_cross_modal_gates() -> None:
    assert not SC.evaluate_transition(
        SC.ResearchState.BENCH_SAFE,
        SC.ResearchState.XR_MULTIMODAL,
        human_inputs(),
    ).allowed
    assert not SC.evaluate_transition(
        SC.ResearchState.BENCH_SAFE,
        SC.ResearchState.XR_MULTIMODAL,
        human_inputs(single_zone_gate_passed=True),
    ).allowed
    assert SC.evaluate_transition(
        SC.ResearchState.BENCH_SAFE,
        SC.ResearchState.XR_MULTIMODAL,
        human_inputs(
            single_zone_gate_passed=True,
            cross_modal_sync_validated=True,
        ),
        authority_snapshot(),
    ).allowed


def test_cue_controller_rejects_unsupported_or_over_limit_commands() -> None:
    inputs = human_inputs()
    allowed = SC.CueRequest.from_values(["left_forearm"], 0.2, 120, 90)
    assert SC.evaluate_cue(
        SC.ResearchState.SINGLE_ZONE_HAPTIC,
        allowed,
        inputs,
        authority=authority_snapshot(),
        context=cue_context(),
    ).allowed

    denied = (
        SC.CueRequest.from_values(["unknown_zone"], 0.2, 120, 90),
        SC.CueRequest.from_values(["left_forearm"], 0.5, 120, 90),
        SC.CueRequest.from_values(["left_forearm"], 0.2, 500, 90),
        SC.CueRequest.from_values(["left_forearm"], 0.2, 120, 400),
        SC.CueRequest.from_values(
            ["left_forearm", "right_forearm"], 0.2, 120, 90
        ),
    )
    for request in denied:
        assert not SC.evaluate_cue(
            SC.ResearchState.SINGLE_ZONE_HAPTIC,
            request,
            inputs,
            authority=authority_snapshot(),
            context=cue_context(),
        ).allowed


def test_all_authority_gates_missing_fails_closed() -> None:
    snapshot = authority_snapshot(gates=())
    decision = SC.evaluate_authority_snapshot(snapshot)
    assert not decision.allowed
    assert decision.reason == "missing authority gate: AG-01"


def test_one_stale_authority_gate_fails_closed() -> None:
    snapshot = authority_snapshot()
    gates = list(snapshot.gates)
    gates[3] = SC.AuthorityGateEvidence(
        gate_id="AG-04",
        status="PASS",
        verified_at_ms=snapshot.now_ms - snapshot.max_gate_age_ms - 1,
        evidence_sha256="4" * 64,
    )
    decision = SC.evaluate_authority_snapshot(
        SC.AuthoritySnapshot(
            gates=tuple(gates),
            artifact_binding=snapshot.artifact_binding,
            now_ms=snapshot.now_ms,
            max_gate_age_ms=snapshot.max_gate_age_ms,
        )
    )
    assert not decision.allowed
    assert decision.reason == "authority gate is stale: AG-04"


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("observed_protocol_sha256", "protocol SHA-256 mismatch"),
        ("observed_controller_sha256", "controller SHA-256 mismatch"),
        ("observed_visual_sha256", "visual SHA-256 mismatch"),
    ],
)
def test_artifact_hash_mismatch_fails_closed(field: str, reason: str) -> None:
    binding = artifact_binding(**{field: "f" * 64})
    decision = SC.evaluate_artifact_binding(binding)
    assert not decision.allowed
    assert decision.reason == reason


def test_participant_state_is_denied_without_canonical_authority() -> None:
    decision = SC.evaluate_transition(
        SC.ResearchState.BENCH_SAFE,
        SC.ResearchState.PASSIVE_FIT,
        human_inputs(),
    )
    assert not decision.allowed
    assert decision.reason == "participant testing requires an authority snapshot"


def test_missing_wearer_stop_path_blocks_participant_state() -> None:
    decision = SC.evaluate_transition(
        SC.ResearchState.BENCH_SAFE,
        SC.ResearchState.SINGLE_ZONE_HAPTIC,
        human_inputs(wearer_stop_signal_verified=False),
        authority_snapshot(),
    )
    assert not decision.allowed
    assert decision.reason == "wearer stop signal is not verified"


@pytest.mark.parametrize(
    ("context", "reason"),
    [
        (cue_context(sensor_timestamp_ms=99_000), "sensor timestamp is stale"),
        (cue_context(conflicting_cue_active=True), "conflicting cue is active"),
        (cue_context(ambiguous_routing=True), "cue routing is ambiguous"),
        (cue_context(authorized_source=False), "cue source is not authorized"),
    ],
)
def test_runtime_cue_context_fails_closed(context, reason: str) -> None:
    decision = SC.evaluate_cue(
        SC.ResearchState.SINGLE_ZONE_HAPTIC,
        SC.CueRequest.from_values(["left_forearm"], 0.2, 120, 90),
        human_inputs(),
        authority=authority_snapshot(),
        context=context,
    )
    assert not decision.allowed
    assert decision.reason == reason


def test_fault_lockout_is_always_reachable_and_requires_manual_reset() -> None:
    assert SC.evaluate_transition(
        SC.ResearchState.XR_MULTIMODAL,
        SC.ResearchState.FAULT_LOCKOUT,
        safe_inputs(estop_released=False),
    ).allowed
    assert not SC.evaluate_transition(
        SC.ResearchState.FAULT_LOCKOUT,
        SC.ResearchState.POWERED_OFF,
        safe_inputs(),
    ).allowed
    assert SC.evaluate_transition(
        SC.ResearchState.FAULT_LOCKOUT,
        SC.ResearchState.POWERED_OFF,
        safe_inputs(service_reset_authorized=True),
    ).allowed


def test_no_powered_assist_or_medical_state_exists() -> None:
    state_names = {state.value for state in SC.ResearchState}
    assert not any(
        token in state
        for state in state_names
        for token in ("FLIGHT", "STRENGTH", "MEDICAL", "MUSCLE_STIM")
    )
    boundary = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))[
        "claim_boundary"
    ].lower()
    for phrase in (
        "not protective equipment",
        "not a medical device",
        "no strength amplification",
        "no electrical muscle stimulation",
    ):
        assert phrase in boundary


def test_concept_visual_is_hash_bound_and_publicly_bounded() -> None:
    payload = json.loads(ASSET_METADATA_PATH.read_text(encoding="utf-8"))
    visual_path = ROOT / payload["asset_path"]

    assert payload["asset_id"] == "flowform_lumaskin_xr_research_v1"
    assert payload["status"] == "CONCEPT_DIAGRAM_NOT_ENGINEERING_VALIDATION"
    assert visual_path.stat().st_size == payload["bytes"]
    assert hashlib.sha256(visual_path.read_bytes()).hexdigest() == payload["sha256"]
    assert payload["media_type"] == "image/svg+xml"
    assert (payload["width_pixels"], payload["height_pixels"]) == (1600, 1000)

    boundary = payload["claim_boundary"].lower()
    for phrase in (
        "not cad",
        "not a fabricated prototype",
        "not a medical device",
        "not human-test authorization",
        "does not prove cue accuracy",
        "reduced motion sickness",
        "regulatory compliance",
    ):
        assert phrase in boundary


def test_reviewer_lab_is_a_projection_of_the_canonical_status_record() -> None:
    page = LAB_INDEX_PATH.read_text(encoding="utf-8")
    app = LAB_APP_PATH.read_text(encoding="utf-8")
    assert 'data-program-status="BENCH_PROTOCOL_READY_HUMAN_TESTS_BLOCKED"' in page
    assert 'data-asset-status="CONCEPT_DIAGRAM_NOT_ENGINEERING_VALIDATION"' in page
    assert "UI controls cannot authorize participant testing" in app
    assert "canonical status packet failed to load" in app


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("program_status", "HUMAN_TESTS_APPROVED"),
        ("asset_status", "VALIDATED_PROTOTYPE"),
        ("human_testing_authorized", True),
        ("independent_validation_complete", True),
    ],
)
def test_public_projection_cannot_promote_beyond_canonical_record(
    field: str, value
) -> None:
    payload = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    packet = BUILDER.build_packet(payload)
    projection = dict(packet["public_projection"])
    projection[field] = value
    with pytest.raises(BUILDER.ProtocolError, match="public projection mismatch"):
        BUILDER.validate_public_projection(packet, projection)
