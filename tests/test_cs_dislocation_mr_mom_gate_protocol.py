from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_CS_DISLOCATION_MR_MOM_GATE_PROTOCOL.py"
PROTOCOL = ROOT / "config" / "cs_dislocation_mr_mom_gate_paper_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "verify_cs_dislocation_mr_mom_gate_protocol", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def module():
    return load_module()


@pytest.fixture
def protocol(module):
    return module.read_json(PROTOCOL)


def reseal(module, protocol):
    """Recompute attacker-visible seals while preserving semantic mutations."""
    for binding in protocol["immutable_bindings"]["inline_payloads"]:
        value = module.resolve_json_pointer(protocol, binding["json_pointer"])
        binding["sha256"] = module.canonical_sha256(value)
    protocol["immutable_bindings"]["protocol_payload_sha256"] = (
        module.protocol_payload_sha256(protocol)
    )
    return protocol


def set_pointer(module, protocol, pointer, value):
    tokens = pointer.strip("/").split("/")
    parent_pointer = "/" + "/".join(tokens[:-1])
    parent = module.resolve_json_pointer(protocol, parent_pointer)
    token = tokens[-1]
    if isinstance(parent, list):
        parent[int(token)] = value
    else:
        parent[token] = value


def assert_invalid(module, protocol, message):
    errors = module.validate_protocol(protocol, root=ROOT)
    assert errors, "adversarial protocol unexpectedly validated"
    assert any(message in error for error in errors), errors


def test_happy_path_is_exactly_sealed_paper_only(module, protocol):
    assert module.validate_protocol(protocol, root=ROOT) == []

    report = module.validation_report(PROTOCOL)
    assert report["valid"] is True
    assert report["error_count"] == 0
    assert report["mode"] == "PAPER_ONLY"
    assert report["declared_result_label"] == "NO_PROSPECTIVE_RESULT"
    assert report["maximum_claim_label"] == "PROSPECTIVE_PAPER_EDGE_SUPPORTED"
    assert report["registered_variant_count"] == 18
    assert report["promotion_gate_count"] == 11
    assert report["validation_only"] is True
    assert report["network_or_execution_performed"] is False


def test_happy_path_contains_exact_variant_and_baseline_families(module, protocol):
    variants = protocol["candidate_family"]["variants"]
    full = [row for row in variants if row["class"] == "FULL_VARIANT"]
    additional = [row for row in variants if row["class"] != "FULL_VARIANT"]

    assert len(variants) == 18
    assert len(full) == 12
    assert len(additional) == 6
    assert len({row["id"] for row in variants}) == 18
    assert [row["id"] for row in variants if row["promotion_eligible"]] == [
        "full_e2p0_m3_h12"
    ]
    assert protocol["baselines"]["count"] == 6
    assert protocol["uncertainty_and_multiplicity"]["fwer"]["contrast_count"] == 36


def test_missing_and_extra_keys_are_rejected(module, protocol):
    missing = copy.deepcopy(protocol)
    del missing["primary_signal"]["entry"]["z_lte"]
    reseal(module, missing)
    assert_invalid(module, missing, "missing keys at $.primary_signal.entry")

    extra = copy.deepcopy(protocol)
    extra["execution_model"]["fee_model"]["negotiated_discount_allowed"] = True
    reseal(module, extra)
    assert_invalid(module, extra, "extra keys at $.execution_model.fee_model")


def test_duplicate_json_object_keys_are_rejected(module, tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"protocol_id":"A","protocol_id":"B"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        module.read_json(path)


def test_malformed_hash_and_timestamp_are_rejected(module, protocol):
    malformed_hash = copy.deepcopy(protocol)
    malformed_hash["immutable_bindings"]["external_files"][0]["sha256"] = "ABC123"
    reseal(module, malformed_hash)
    assert_invalid(module, malformed_hash, "malformed SHA-256")

    malformed_timestamp = copy.deepcopy(protocol)
    malformed_timestamp["registration"]["t0_utc"] = "2026-08-01 00:00:00"
    reseal(module, malformed_timestamp)
    assert_invalid(
        module,
        malformed_timestamp,
        "registration.t0_utc must be exact UTC ISO-8601 seconds",
    )


@pytest.mark.parametrize(
    ("pointer", "weakened_value", "section"),
    [
        ("/point_in_time_universe/eligibility/minimum_listing_age_days", 179, "point_in_time_universe"),
        ("/clock_and_no_lookahead/earliest_fill_seconds_after_bar_end", 89, "clock_and_no_lookahead"),
        ("/primary_signal/entry/z_lte", -1.9, "primary_signal"),
        ("/execution_model/fee_model/minimum_per_side_fee_bps", 39, "execution_model"),
        ("/execution_model/capacity/maximum_order_usd", 10001, "execution_model"),
        ("/uncertainty_and_multiplicity/bootstrap/resamples", 19999, "uncertainty_and_multiplicity"),
        ("/uncertainty_and_multiplicity/fwer/alpha", 0.06, "uncertainty_and_multiplicity"),
        ("/sample_gates/gates/2/minimum_closes", 249, "sample_gates"),
        ("/promotion_policy/gates/1/conditions/0/value", 0.99, "promotion_policy"),
        ("/kill_criteria/harm_stop/prospective_drawdown_reaches_fraction", 0.16, "kill_criteria"),
    ],
)
def test_resealed_threshold_weakening_is_rejected(
    module, protocol, pointer, weakened_value, section
):
    mutation = copy.deepcopy(protocol)
    set_pointer(module, mutation, pointer, weakened_value)
    reseal(module, mutation)
    assert_invalid(module, mutation, f"sealed semantic section mismatch: {section}")


def test_duplicate_and_replaced_variants_are_rejected_after_resealing(module, protocol):
    duplicate = copy.deepcopy(protocol)
    duplicate["candidate_family"]["variants"][-1]["id"] = duplicate[
        "candidate_family"
    ]["variants"][0]["id"]
    reseal(module, duplicate)
    assert_invalid(module, duplicate, "duplicate candidate variant id")

    omitted = copy.deepcopy(protocol)
    omitted["candidate_family"]["variants"].pop()
    omitted["candidate_family"]["attempt_count"] = 17
    reseal(module, omitted)
    assert_invalid(module, omitted, "exactly 18 attempted variants")


def test_malformed_value_types_fail_closed_without_validator_crash(module, protocol):
    mutation = copy.deepcopy(protocol)
    mutation["candidate_family"]["variants"][0]["id"] = ["not", "a", "string"]
    reseal(module, mutation)
    assert_invalid(module, mutation, "duplicate candidate variant id")


@pytest.mark.parametrize(
    ("key", "forbidden_value"),
    [
        ("mode", "LIVE"),
        ("private_or_authenticated_api_allowed", True),
        ("order_endpoint_allowed", True),
        ("exchange_sandbox_order_allowed", True),
        ("capital_exposure_allowed", True),
    ],
)
def test_forbidden_modes_and_capabilities_are_rejected(
    module, protocol, key, forbidden_value
):
    mutation = copy.deepcopy(protocol)
    mutation["boundaries"][key] = forbidden_value
    reseal(module, mutation)
    expected = "forbidden mode" if key == "mode" else "forbidden capability enabled"
    assert_invalid(module, mutation, expected)


def test_romano_wolf_holm_and_optional_stopping_cannot_be_weakened(module, protocol):
    multiplicity = copy.deepcopy(protocol)
    multiplicity["uncertainty_and_multiplicity"]["fwer"]["fallback_method"] = (
        "HOLM_PRIMARY_ONLY"
    )
    reseal(module, multiplicity)
    assert_invalid(module, multiplicity, "Romano-Wolf/Holm 36-contrast")

    optional_stop = copy.deepcopy(protocol)
    optional_stop["uncertainty_and_multiplicity"]["optional_stopping_allowed"] = True
    reseal(module, optional_stop)
    assert_invalid(module, optional_stop, "optional stopping is forbidden")


def test_promotion_gate_count_must_be_exactly_11(module, protocol):
    mutation = copy.deepcopy(protocol)
    mutation["promotion_policy"]["gates"].pop()
    mutation["promotion_policy"]["required_gate_count"] = 10
    reseal(module, mutation)
    assert_invalid(module, mutation, "promotion gate count must be exactly 11")


@pytest.mark.parametrize(
    ("key", "forbidden_claim", "expected_error"),
    [
        (
            "declared_result_label",
            "VALIDATED_LIVE_ALPHA",
            "cannot declare a prospective result",
        ),
        (
            "allowed_success_label",
            "INSTITUTIONAL_ALPHA_SUPPORTED",
            "allowed success label exceeds",
        ),
        (
            "maximum_claim_label",
            "PROFITABLE_LIVE_TRADING_SUPPORTED",
            "claim ceiling must be PROSPECTIVE_PAPER_EDGE_SUPPORTED",
        ),
    ],
)
def test_claims_beyond_prospective_paper_edge_are_rejected(
    module, protocol, key, forbidden_claim, expected_error
):
    mutation = copy.deepcopy(protocol)
    mutation["claim_policy"][key] = forbidden_claim
    reseal(module, mutation)
    assert_invalid(module, mutation, expected_error)


def test_unresealed_mutation_breaks_protocol_payload_hash(module, protocol):
    mutation = copy.deepcopy(protocol)
    mutation["primary_signal"]["entry"]["z_lte"] = -1.5
    assert_invalid(module, mutation, "protocol payload SHA-256 mismatch")


def test_external_file_hash_binding_is_enforced(module, protocol):
    mutation = copy.deepcopy(protocol)
    mutation["immutable_bindings"]["external_files"][1]["sha256"] = "0" * 64
    reseal(module, mutation)
    assert_invalid(module, mutation, "bound external file hash mismatch")
