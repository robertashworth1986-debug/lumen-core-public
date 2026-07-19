#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "config" / "outage_second_economic_conversion_protocol_v1.json"
CASE_TEMPLATE_PATH = ROOT / "config" / "outage_second_economic_case_template_v1.json"
RECEIPT_TEMPLATE_PATH = (
    ROOT / "config" / "outage_second_economic_acceptance_receipt_template_v1.json"
)
BUILDER_SOURCE_PATH = Path(__file__).resolve()
VERIFIER_SOURCE_PATH = (
    BUILDER_SOURCE_PATH.parent / "VERIFY_OUTAGE_SECOND_ECONOMIC_VALUE_PACKET.py"
)
DEFAULT_OUTPUT_DIR = (
    ROOT / "evidence" / "private" / "outage_second_economic_value_packet_20260716"
)

PROTOCOL_BUNDLE_NAME = "protocol.json"
CASE_BUNDLE_NAME = "case.json"
PRIVATE_CALCULATION_NAME = "private_calculation.json"
RECEIPT_BUNDLE_NAME = "acceptance_receipt.json"
PUBLIC_JSON_NAME = "public_summary.json"
PUBLIC_MARKDOWN_NAME = "public_summary.md"
PUBLICATION_MANIFEST_NAME = "publication_manifest.json"
BUNDLE_FILE_NAMES = (
    PROTOCOL_BUNDLE_NAME,
    CASE_BUNDLE_NAME,
    PRIVATE_CALCULATION_NAME,
    RECEIPT_BUNDLE_NAME,
    PUBLIC_JSON_NAME,
    PUBLIC_MARKDOWN_NAME,
    PUBLICATION_MANIFEST_NAME,
)

SCENARIO_NAMES = ("low", "base", "high")
SIGNER_ROLES = ("economic_owner", "technical_reviewer")
SIGNER_FIELDS = (
    "signer_id",
    "name",
    "role",
    "organization",
    "independence_from_lumencore",
    "independence_from_other_signer",
    "independence_basis",
    "independence_evidence_artifact_sha256",
    "signed_utc",
)
SIGNATURE_FIELDS = (
    "algorithm",
    "public_key_artifact_sha256",
    "detached_signature_artifact_sha256",
    "signed_payload_sha256",
)
MAX_JSON_NUMBER_MAGNITUDE = Decimal("1e30")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

EVIDENCE_CHECK_NAMES = {
    "external_operator_case",
    "input_source_artifacts_recomputed",
    "technical_evidence_artifact_recomputed",
    "technical_support_artifacts_recomputed",
    "case_effects_match_technical_evidence",
    "receipt_bindings_exact",
    "receipt_outputs_exact",
    "receipt_scope_exact",
    "receipt_attestations_exact",
    "receipt_signers_verified",
    "receipt_independence_verified",
    "receipt_timestamps_valid",
    "receipt_decision_accepts",
    "receipt_signatures_verified",
    "receipt_release_decision_approves",
}


class EconomicProtocolError(ValueError):
    pass


def _reject_json_constant(token: str) -> None:
    raise EconomicProtocolError(f"non-finite JSON number is prohibited: {token}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EconomicProtocolError(f"duplicate JSON object key is prohibited: {key}")
        result[key] = value
    return result


def _validate_json_tree(
    value: Any,
    *,
    label: str,
    depth: int = 0,
    max_depth: int = 32,
    max_string_length: int = 4096,
    max_array_items: int = 256,
) -> None:
    if depth > max_depth:
        raise EconomicProtocolError(f"{label} exceeds maximum JSON depth")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        if len(value) > max_string_length:
            raise EconomicProtocolError(f"{label} contains an overlong string")
        return
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise EconomicProtocolError(f"{label} contains a non-finite number")
        if abs(value) > MAX_JSON_NUMBER_MAGNITUDE:
            raise EconomicProtocolError(f"{label} contains an excessive numeric magnitude")
        return
    if isinstance(value, int):
        if abs(value) > MAX_JSON_NUMBER_MAGNITUDE:
            raise EconomicProtocolError(f"{label} contains an excessive numeric magnitude")
        return
    if isinstance(value, float):
        raise EconomicProtocolError(
            f"{label} contains a binary float; exact JSON decimals are required"
        )
    if isinstance(value, list):
        if len(value) > max_array_items:
            raise EconomicProtocolError(f"{label} exceeds maximum JSON array length")
        for index, child in enumerate(value):
            _validate_json_tree(
                child,
                label=f"{label}[{index}]",
                depth=depth + 1,
                max_depth=max_depth,
                max_string_length=max_string_length,
                max_array_items=max_array_items,
            )
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise EconomicProtocolError(f"{label} contains a non-string key")
            _validate_json_tree(
                child,
                label=f"{label}.{key}",
                depth=depth + 1,
                max_depth=max_depth,
                max_string_length=max_string_length,
                max_array_items=max_array_items,
            )
        return
    raise EconomicProtocolError(f"{label} contains an unsupported JSON value")


def strict_json_loads(raw: bytes | str, *, label: str = "JSON") -> Any:
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EconomicProtocolError(f"{label} is not valid UTF-8") from exc
    else:
        text = raw
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=Decimal,
            parse_int=Decimal,
            parse_constant=_reject_json_constant,
        )
    except EconomicProtocolError:
        raise
    except (json.JSONDecodeError, ValueError) as exc:
        raise EconomicProtocolError(f"invalid strict JSON in {label}: {exc}") from exc
    _validate_json_tree(value, label=label)
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise EconomicProtocolError(f"JSON artifact is missing or is a symlink: {path}")
    value = strict_json_loads(path.read_bytes(), label=str(path))
    if not isinstance(value, dict):
        raise EconomicProtocolError(f"JSON root must be an object: {path}")
    return value


def canonical_decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise EconomicProtocolError("non-finite Decimal cannot be canonicalized")
    if value == 0:
        return "0"
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered


def _canonical_json_text(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    if isinstance(value, Decimal):
        return canonical_decimal_text(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        raise EconomicProtocolError("binary floats cannot be canonicalized")
    if isinstance(value, list):
        return "[" + ",".join(_canonical_json_text(item) for item in value) + "]"
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise EconomicProtocolError("canonical JSON object keys must be strings")
        return "{" + ",".join(
            _canonical_json_text(key) + ":" + _canonical_json_text(value[key])
            for key in sorted(value)
        ) + "}"
    raise EconomicProtocolError(
        f"unsupported canonical JSON type: {type(value).__name__}"
    )


def canonical_json_bytes(value: Any) -> bytes:
    return _canonical_json_text(value).encode("ascii")


def stable_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def json_bytes(payload: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(dict(payload)) + b"\n"


def markdown_bytes(text: str) -> bytes:
    return (text.rstrip("\r\n") + "\n").encode("utf-8")


def require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EconomicProtocolError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise EconomicProtocolError(
            f"{label} schema mismatch; missing={missing}, extra={extra}"
        )
    return value


def require_nonempty_text(value: Any, label: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EconomicProtocolError(f"{label} must be nonempty text")
    if value != value.strip():
        raise EconomicProtocolError(f"{label} cannot contain leading or trailing space")
    if len(value) > maximum:
        raise EconomicProtocolError(f"{label} is too long")
    return value


def require_identifier(value: Any, label: str) -> str:
    text = require_nonempty_text(value, label, maximum=128)
    if not IDENTIFIER_PATTERN.fullmatch(text):
        raise EconomicProtocolError(f"{label} is not a strict identifier")
    return text


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise EconomicProtocolError(f"{label} must be a lowercase SHA-256 digest")
    return value


def as_decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or value is None or isinstance(value, float):
        raise EconomicProtocolError(f"{label} must be an exact JSON number, not bool")
    if not isinstance(value, (Decimal, int)):
        raise EconomicProtocolError(f"{label} must be an exact JSON number")
    try:
        converted = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise EconomicProtocolError(f"{label} must be numeric") from exc
    if not converted.is_finite():
        raise EconomicProtocolError(f"{label} must be finite")
    if abs(converted) > MAX_JSON_NUMBER_MAGNITUDE:
        raise EconomicProtocolError(f"{label} exceeds the numeric magnitude limit")
    return converted


def as_integer(value: Any, label: str) -> int:
    numeric = as_decimal(value, label)
    if numeric != numeric.to_integral_value():
        raise EconomicProtocolError(f"{label} must be an integer")
    return int(numeric)


def decimal_control(value: Any, label: str) -> Decimal:
    if not isinstance(value, str):
        raise EconomicProtocolError(f"{label} must be a decimal string")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise EconomicProtocolError(f"{label} is not a decimal string") from exc
    if not result.is_finite() or abs(result) > MAX_JSON_NUMBER_MAGNITUDE:
        raise EconomicProtocolError(f"{label} is outside the numeric control range")
    return result


def parse_utc_timestamp(value: Any, label: str) -> datetime:
    text = require_nonempty_text(value, label, maximum=64)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EconomicProtocolError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise EconomicProtocolError(f"{label} must be timezone-aware UTC")
    return parsed.astimezone(timezone.utc)


def protocol_numeric_limits(protocol: dict[str, Any]) -> tuple[int, int, int]:
    controls = protocol["numeric_controls"]
    return (
        as_integer(controls["maximum_json_depth"], "maximum_json_depth"),
        as_integer(controls["maximum_string_length"], "maximum_string_length"),
        as_integer(controls["maximum_array_items"], "maximum_array_items"),
    )


def _validate_loaded_json_against_protocol(
    value: Any, protocol: dict[str, Any], label: str
) -> None:
    max_depth, max_string, max_array = protocol_numeric_limits(protocol)
    _validate_json_tree(
        value,
        label=label,
        max_depth=max_depth,
        max_string_length=max_string,
        max_array_items=max_array,
    )


def validate_protocol(protocol: dict[str, Any]) -> None:
    top_keys = {
        "schema",
        "protocol_id",
        "version",
        "status",
        "purpose",
        "valuation_perspective",
        "currency",
        "claim_boundary",
        "case_classifications",
        "required_scenarios",
        "scenario_fields",
        "calculation_steps",
        "monotonic_outputs",
        "numeric_controls",
        "artifact_controls",
        "technical_evidence_controls",
        "receipt_controls",
        "required_receipt_attestations",
        "claim_gates",
        "release_control",
        "prohibited_inputs_or_shortcuts",
        "standards_alignment",
        "operator_fields_may_be_filled_by_lumencore",
    }
    require_exact_keys(protocol, top_keys, "protocol")
    if protocol["schema"] != "outage_second_economic_conversion_protocol.v1":
        raise EconomicProtocolError("unexpected protocol schema")
    require_identifier(protocol["protocol_id"], "protocol.protocol_id")
    require_nonempty_text(protocol["version"], "protocol.version", maximum=32)
    require_nonempty_text(protocol["status"], "protocol.status", maximum=128)
    require_nonempty_text(protocol["purpose"], "protocol.purpose", maximum=1024)
    require_nonempty_text(
        protocol["claim_boundary"], "protocol.claim_boundary", maximum=2048
    )
    if protocol["valuation_perspective"] != "PRIVATE_ENTITY_INCREMENTAL_COST":
        raise EconomicProtocolError("v1 must be restricted to private-entity cost")
    if protocol["currency"] != "USD":
        raise EconomicProtocolError("v1 currency must be USD")
    if protocol["case_classifications"] != [
        "SYNTHETIC_ILLUSTRATIVE",
        "EXTERNAL_OPERATOR_CASE",
    ]:
        raise EconomicProtocolError("case classifications are not frozen")
    if protocol["required_scenarios"] != list(SCENARIO_NAMES):
        raise EconomicProtocolError("scenario names must be low/base/high")

    fields = protocol["scenario_fields"]
    if not isinstance(fields, dict) or not fields:
        raise EconomicProtocolError("scenario_fields must be a nonempty object")
    for name, control in fields.items():
        require_identifier(name, f"scenario_fields.{name}")
        expected = {"kind", "minimum", "maximum"}
        if isinstance(control, dict) and "exclusive_minimum" in control:
            expected.add("exclusive_minimum")
        require_exact_keys(control, expected, f"scenario_fields.{name}")
        if control["kind"] not in {"decimal", "integer"}:
            raise EconomicProtocolError(f"unsupported numeric kind for {name}")
        minimum = decimal_control(control["minimum"], f"{name}.minimum")
        maximum = decimal_control(control["maximum"], f"{name}.maximum")
        if minimum > maximum:
            raise EconomicProtocolError(f"invalid numeric bounds for {name}")
        if "exclusive_minimum" in control and not isinstance(
            control["exclusive_minimum"], bool
        ):
            raise EconomicProtocolError(f"{name}.exclusive_minimum must be boolean")

    steps = protocol["calculation_steps"]
    if not isinstance(steps, list) or not steps:
        raise EconomicProtocolError("calculation_steps must be a nonempty list")
    available = set(fields)
    outputs: list[str] = []
    for index, step in enumerate(steps):
        require_exact_keys(
            step, {"output", "operation", "operands"}, f"calculation_steps[{index}]"
        )
        output = require_identifier(step["output"], f"calculation_steps[{index}].output")
        if output in available:
            raise EconomicProtocolError(f"duplicate calculation symbol: {output}")
        if step["operation"] not in {"add", "subtract", "multiply", "divide"}:
            raise EconomicProtocolError(f"unsupported operation: {step['operation']}")
        operands = step["operands"]
        if not isinstance(operands, list) or len(operands) < 2:
            raise EconomicProtocolError(f"calculation step {output} needs operands")
        if step["operation"] in {"subtract", "divide"} and len(operands) != 2:
            raise EconomicProtocolError(f"{step['operation']} requires two operands")
        for operand in operands:
            if operand not in available:
                raise EconomicProtocolError(
                    f"calculation step {output} references unavailable {operand}"
                )
        available.add(output)
        outputs.append(output)
    required_formula_outputs = {
        "net_time_flow_cost_per_second_usd",
        "net_fixed_incremental_cost_per_event_usd",
        "annual_avoided_time_flow_cost_usd",
        "annual_avoided_fixed_event_cost_usd",
        "estimated_annual_avoided_cost_usd",
    }
    if not required_formula_outputs.issubset(outputs):
        raise EconomicProtocolError("fixed-event and time-flow formulas are incomplete")
    monotonic = protocol["monotonic_outputs"]
    if not isinstance(monotonic, list) or not monotonic:
        raise EconomicProtocolError("monotonic_outputs must be nonempty")
    if len(monotonic) != len(set(monotonic)) or not set(monotonic).issubset(outputs):
        raise EconomicProtocolError("monotonic_outputs reference invalid calculations")

    numeric = require_exact_keys(
        protocol["numeric_controls"],
        {
            "intermediate_decimal_precision",
            "output_decimal_places",
            "rounding",
            "maximum_calculated_absolute_magnitude",
            "maximum_json_depth",
            "maximum_string_length",
            "maximum_array_items",
        },
        "numeric_controls",
    )
    if not 28 <= as_integer(
        numeric["intermediate_decimal_precision"], "intermediate_decimal_precision"
    ) <= 200:
        raise EconomicProtocolError("intermediate precision is outside the safe range")
    if not 0 <= as_integer(numeric["output_decimal_places"], "output_decimal_places") <= 18:
        raise EconomicProtocolError("output decimal places are outside the safe range")
    if numeric["rounding"] != "ROUND_HALF_UP":
        raise EconomicProtocolError("unsupported rounding control")
    decimal_control(
        numeric["maximum_calculated_absolute_magnitude"],
        "maximum_calculated_absolute_magnitude",
    )
    if not 8 <= as_integer(numeric["maximum_json_depth"], "maximum_json_depth") <= 64:
        raise EconomicProtocolError("maximum_json_depth is outside the safe range")
    if not 256 <= as_integer(
        numeric["maximum_string_length"], "maximum_string_length"
    ) <= 65536:
        raise EconomicProtocolError("maximum_string_length is outside the safe range")
    if not 8 <= as_integer(numeric["maximum_array_items"], "maximum_array_items") <= 4096:
        raise EconomicProtocolError("maximum_array_items is outside the safe range")

    artifacts = require_exact_keys(
        protocol["artifact_controls"],
        {
            "hash_algorithm",
            "relative_artifact_paths_only",
            "reject_symlinks",
            "strict_json_media_types",
            "atomic_bundle_required",
            "no_clobber_required",
        },
        "artifact_controls",
    )
    if artifacts["hash_algorithm"] != "sha256":
        raise EconomicProtocolError("only SHA-256 artifacts are supported")
    for name in (
        "relative_artifact_paths_only",
        "reject_symlinks",
        "atomic_bundle_required",
        "no_clobber_required",
    ):
        if artifacts[name] is not True:
            raise EconomicProtocolError(f"artifact control must remain true: {name}")
    if artifacts["strict_json_media_types"] != ["application/json"]:
        raise EconomicProtocolError("strict JSON media types are not frozen")

    technical = require_exact_keys(
        protocol["technical_evidence_controls"],
        {
            "schema",
            "required_artifact_roles",
            "measured_effect_fields",
            "counterfactual_must_precede_scoring",
        },
        "technical_evidence_controls",
    )
    if technical["schema"] != "outage_second_technical_evidence.v1":
        raise EconomicProtocolError("technical evidence schema is not frozen")
    if technical["required_artifact_roles"] != [
        "BUYER_AUTHORIZATION",
        "FROZEN_INCUMBENT_BASELINE",
        "FROZEN_PRIMARY_METRIC",
        "INDEPENDENT_REPRODUCTION_RECEIPT",
    ]:
        raise EconomicProtocolError("technical artifact roles are not frozen")
    if technical["measured_effect_fields"] != [
        "annual_avoided_outage_seconds",
        "annual_avoided_event_count",
    ]:
        raise EconomicProtocolError("technical measured effects are not frozen")
    if technical["counterfactual_must_precede_scoring"] is not True:
        raise EconomicProtocolError("counterfactual ordering control must remain true")

    receipt = require_exact_keys(
        protocol["receipt_controls"],
        {
            "schema",
            "template_status",
            "completed_status",
            "signature_algorithm",
            "required_signer_roles",
            "decision_values",
            "acceptance_decision",
            "release_decision_values",
            "release_approval_decision",
            "maximum_signature_delay_seconds",
            "maximum_future_skew_seconds",
            "forbidden_signer_organization_tokens",
            "trusted_key_source",
        },
        "receipt_controls",
    )
    if receipt["schema"] != "outage_second_economic_acceptance_receipt.v1":
        raise EconomicProtocolError("receipt schema is not frozen")
    if receipt["signature_algorithm"] != "Ed25519":
        raise EconomicProtocolError("receipt signatures must use Ed25519")
    if receipt["required_signer_roles"] != list(SIGNER_ROLES):
        raise EconomicProtocolError("required receipt signers are not frozen")
    if receipt["acceptance_decision"] not in receipt["decision_values"]:
        raise EconomicProtocolError("acceptance decision is not allowed")
    if receipt["release_approval_decision"] not in receipt["release_decision_values"]:
        raise EconomicProtocolError("release approval decision is not allowed")
    if as_integer(
        receipt["maximum_signature_delay_seconds"], "maximum_signature_delay_seconds"
    ) <= 0:
        raise EconomicProtocolError("signature delay must be positive")
    if as_integer(receipt["maximum_future_skew_seconds"], "maximum_future_skew_seconds") < 0:
        raise EconomicProtocolError("future skew cannot be negative")
    if receipt["trusted_key_source"] != "OUT_OF_BAND_CALLER_SUPPLIED_SHA256":
        raise EconomicProtocolError("trusted signer keys must remain out-of-band")
    forbidden_tokens = receipt["forbidden_signer_organization_tokens"]
    if not isinstance(forbidden_tokens, list) or "lumencore" not in forbidden_tokens:
        raise EconomicProtocolError("LumenCore signer exclusion is missing")

    attestations = protocol["required_receipt_attestations"]
    if not isinstance(attestations, list) or not attestations:
        raise EconomicProtocolError("receipt attestations must be nonempty")
    if len(attestations) != len(set(attestations)):
        raise EconomicProtocolError("receipt attestations cannot repeat")
    for index, attestation in enumerate(attestations):
        require_identifier(attestation, f"required_receipt_attestations[{index}]")

    gates = require_exact_keys(
        protocol["claim_gates"], {"evaluation_order", "definitions"}, "claim_gates"
    )
    definitions = gates["definitions"]
    if not isinstance(definitions, dict) or gates["evaluation_order"] != list(definitions):
        raise EconomicProtocolError("claim gate evaluation order must match definitions")
    prior_gates: set[str] = set()
    for gate in gates["evaluation_order"]:
        require_identifier(gate, f"claim gate {gate}")
        requirements = definitions.get(gate)
        if not isinstance(requirements, list) or not requirements:
            raise EconomicProtocolError(f"claim gate {gate} has no requirements")
        if len(requirements) != len(set(requirements)):
            raise EconomicProtocolError(f"claim gate {gate} repeats a requirement")
        allowed = EVIDENCE_CHECK_NAMES | prior_gates
        unknown = set(requirements) - allowed
        if unknown:
            raise EconomicProtocolError(
                f"claim gate {gate} has unknown requirements: {sorted(unknown)}"
            )
        prior_gates.add(gate)
    if gates["evaluation_order"] != [
        "accepted_estimated_avoided_cost_claim_allowed",
        "public_economic_release_allowed",
    ]:
        raise EconomicProtocolError("v1 claim gates are not frozen")

    release = require_exact_keys(
        protocol["release_control"],
        {
            "default_public_release",
            "closed_gate_summary_status",
            "accepted_private_summary_status",
            "released_summary_status",
            "redact_scope_when_release_closed",
            "redact_outputs_when_release_closed",
        },
        "release_control",
    )
    if release["default_public_release"] is not False:
        raise EconomicProtocolError("public release must default false")
    if release["redact_scope_when_release_closed"] is not True:
        raise EconomicProtocolError("closed-gate scope redaction must remain enabled")
    if release["redact_outputs_when_release_closed"] is not True:
        raise EconomicProtocolError("closed-gate output redaction must remain enabled")
    for name in (
        "closed_gate_summary_status",
        "accepted_private_summary_status",
        "released_summary_status",
    ):
        require_identifier(release[name], f"release_control.{name}")

    prohibited = protocol["prohibited_inputs_or_shortcuts"]
    required_prohibitions = {
        "market_capitalization_as_loss_basis",
        "federal_social_benefit_in_v1",
        "mission_cost_effectiveness_in_v1",
        "fixed_event_cost_divided_by_seconds_for_annualization",
        "self_asserted_acceptance_boolean",
        "hash_shaped_string_without_artifact_rehash",
        "unsigned_or_hash_only_signature_artifact",
    }
    if not isinstance(prohibited, list) or not required_prohibitions.issubset(prohibited):
        raise EconomicProtocolError("required prohibited shortcuts are incomplete")
    standards = protocol["standards_alignment"]
    if not isinstance(standards, list) or not standards:
        raise EconomicProtocolError("standards alignment is missing")
    for index, row in enumerate(standards):
        require_exact_keys(
            row,
            {"authority", "reference", "url", "compliance_or_endorsement_claimed"},
            f"standards_alignment[{index}]",
        )
        if row["compliance_or_endorsement_claimed"] is not False:
            raise EconomicProtocolError("standards cannot claim compliance or endorsement")
    if protocol["operator_fields_may_be_filled_by_lumencore"] is not False:
        raise EconomicProtocolError("LumenCore cannot fill external fields")
    _validate_loaded_json_against_protocol(protocol, protocol, "protocol")


def load_protocol(path: Path = PROTOCOL_PATH) -> tuple[dict[str, Any], bytes]:
    if not path.is_file() or path.is_symlink():
        raise EconomicProtocolError(f"protocol artifact is unavailable: {path}")
    raw = path.read_bytes()
    value = strict_json_loads(raw, label=str(path))
    if not isinstance(value, dict):
        raise EconomicProtocolError("protocol root must be an object")
    validate_protocol(value)
    return value, raw


def validate_relative_artifact_path(value: Any, label: str) -> str:
    text = require_nonempty_text(value, label, maximum=512)
    if "\\" in text:
        raise EconomicProtocolError(f"{label} must use POSIX separators")
    pure = PurePosixPath(text)
    if pure.is_absolute() or not pure.parts:
        raise EconomicProtocolError(f"{label} must be a relative artifact path")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise EconomicProtocolError(f"{label} contains a prohibited path component")
    if ":" in pure.parts[0]:
        raise EconomicProtocolError(f"{label} cannot contain a drive prefix")
    return pure.as_posix()


def validate_case(
    case: dict[str, Any],
    protocol: dict[str, Any] | None = None,
    *,
    protocol_sha256: str | None = None,
) -> None:
    if protocol is None:
        protocol, protocol_raw = load_protocol()
        protocol_sha256 = bytes_sha256(protocol_raw)
    elif protocol_sha256 is None:
        protocol_sha256 = file_sha256(PROTOCOL_PATH)
    top_keys = {
        "schema",
        "case_id",
        "case_classification",
        "protocol_id",
        "protocol_sha256",
        "prepared_utc",
        "counterfactual_frozen_utc",
        "valuation_perspective",
        "currency",
        "base_year",
        "operating_entity",
        "named_system",
        "named_outage_scenario",
        "counterfactual_baseline",
        "analysis_period",
        "scenarios",
        "input_sources",
        "technical_evidence",
        "limitations",
    }
    require_exact_keys(case, top_keys, "case")
    if case["schema"] != "outage_second_economic_case.v1":
        raise EconomicProtocolError("unexpected case schema")
    require_identifier(case["case_id"], "case.case_id")
    classification = case["case_classification"]
    if classification not in protocol["case_classifications"]:
        raise EconomicProtocolError("unsupported case classification")
    if case["protocol_id"] != protocol["protocol_id"]:
        raise EconomicProtocolError("case protocol_id does not match the exact protocol")
    if case["protocol_sha256"] != protocol_sha256:
        raise EconomicProtocolError("case protocol hash does not match recomputed bytes")
    if case["valuation_perspective"] != protocol["valuation_perspective"]:
        raise EconomicProtocolError("v1 rejects non-private valuation perspectives")
    if case["currency"] != protocol["currency"]:
        raise EconomicProtocolError("case currency does not match the protocol")
    prepared = parse_utc_timestamp(case["prepared_utc"], "case.prepared_utc")
    counterfactual_frozen = parse_utc_timestamp(
        case["counterfactual_frozen_utc"], "case.counterfactual_frozen_utc"
    )
    if counterfactual_frozen < prepared:
        raise EconomicProtocolError("counterfactual cannot be frozen before case preparation")
    base_year = as_integer(case["base_year"], "case.base_year")
    if not 1900 <= base_year <= 3000:
        raise EconomicProtocolError("case.base_year is outside the supported range")

    entity = require_exact_keys(
        case["operating_entity"],
        {"legal_name", "organization_id", "economic_owner_organization"},
        "case.operating_entity",
    )
    require_nonempty_text(entity["legal_name"], "operating_entity.legal_name")
    require_identifier(entity["organization_id"], "operating_entity.organization_id")
    require_nonempty_text(
        entity["economic_owner_organization"],
        "operating_entity.economic_owner_organization",
    )
    require_nonempty_text(case["named_system"], "case.named_system")
    require_nonempty_text(
        case["named_outage_scenario"], "case.named_outage_scenario"
    )
    require_nonempty_text(
        case["counterfactual_baseline"], "case.counterfactual_baseline", maximum=2048
    )
    period = require_exact_keys(
        case["analysis_period"], {"start_utc", "end_utc"}, "case.analysis_period"
    )
    period_start = parse_utc_timestamp(period["start_utc"], "analysis_period.start_utc")
    period_end = parse_utc_timestamp(period["end_utc"], "analysis_period.end_utc")
    if period_end <= period_start:
        raise EconomicProtocolError("analysis period end must be after its start")

    scenarios = require_exact_keys(case["scenarios"], set(SCENARIO_NAMES), "case.scenarios")
    field_names = set(protocol["scenario_fields"])
    for scenario_name in SCENARIO_NAMES:
        row = require_exact_keys(
            scenarios[scenario_name], field_names, f"case.scenarios.{scenario_name}"
        )
        for field_name, control in protocol["scenario_fields"].items():
            numeric = as_decimal(row[field_name], f"{scenario_name}.{field_name}")
            minimum = decimal_control(control["minimum"], f"{field_name}.minimum")
            maximum = decimal_control(control["maximum"], f"{field_name}.maximum")
            if control.get("exclusive_minimum") is True:
                if numeric <= minimum:
                    raise EconomicProtocolError(
                        f"{scenario_name}.{field_name} must be greater than {minimum}"
                    )
            elif numeric < minimum:
                raise EconomicProtocolError(
                    f"{scenario_name}.{field_name} must be at least {minimum}"
                )
            if numeric > maximum:
                raise EconomicProtocolError(
                    f"{scenario_name}.{field_name} exceeds {maximum}"
                )
            if control["kind"] == "integer" and numeric != numeric.to_integral_value():
                raise EconomicProtocolError(f"{scenario_name}.{field_name} must be integral")

    sources = case["input_sources"]
    if not isinstance(sources, list):
        raise EconomicProtocolError("case.input_sources must be a list")
    source_ids: set[str] = set()
    source_paths: set[str] = set()
    for index, source in enumerate(sources):
        require_exact_keys(
            source,
            {
                "source_id",
                "artifact_path",
                "sha256",
                "media_type",
                "owner_organization",
                "purpose",
            },
            f"case.input_sources[{index}]",
        )
        source_id = require_identifier(source["source_id"], f"input_sources[{index}].source_id")
        artifact_path = validate_relative_artifact_path(
            source["artifact_path"], f"input_sources[{index}].artifact_path"
        )
        require_sha256(source["sha256"], f"input_sources[{index}].sha256")
        if source["media_type"] not in {"application/json", "text/plain", "application/pdf"}:
            raise EconomicProtocolError("unsupported input source media_type")
        require_nonempty_text(
            source["owner_organization"], f"input_sources[{index}].owner_organization"
        )
        require_nonempty_text(source["purpose"], f"input_sources[{index}].purpose")
        if source_id in source_ids or artifact_path in source_paths:
            raise EconomicProtocolError("input source IDs and paths must be unique")
        source_ids.add(source_id)
        source_paths.add(artifact_path)

    technical_ref = case["technical_evidence"]
    if classification == "SYNTHETIC_ILLUSTRATIVE":
        if sources or technical_ref is not None:
            raise EconomicProtocolError(
                "synthetic illustrative cases cannot bind external evidence"
            )
    else:
        if not sources:
            raise EconomicProtocolError("external operator cases require input artifacts")
        require_exact_keys(
            technical_ref, {"artifact_path", "sha256"}, "case.technical_evidence"
        )
        validate_relative_artifact_path(
            technical_ref["artifact_path"], "technical_evidence.artifact_path"
        )
        require_sha256(technical_ref["sha256"], "technical_evidence.sha256")

    limitations = case["limitations"]
    if not isinstance(limitations, list) or not limitations:
        raise EconomicProtocolError("case.limitations must be a nonempty list")
    for index, limitation in enumerate(limitations):
        require_nonempty_text(limitation, f"case.limitations[{index}]", maximum=1024)
    _validate_loaded_json_against_protocol(case, protocol, "case")


def decimal_output_text(value: Decimal, protocol: dict[str, Any]) -> str:
    places = as_integer(
        protocol["numeric_controls"]["output_decimal_places"], "output_decimal_places"
    )
    quantum = Decimal(1).scaleb(-places)
    precision = as_integer(
        protocol["numeric_controls"]["intermediate_decimal_precision"],
        "intermediate_decimal_precision",
    )
    with localcontext() as context:
        context.prec = precision
        rounded = value.quantize(quantum, rounding=ROUND_HALF_UP)
    if rounded == 0:
        rounded = abs(rounded)
    return format(rounded, "f")


def calculate_scenario(
    row: dict[str, Any], protocol: dict[str, Any] | None = None
) -> dict[str, str]:
    if protocol is None:
        protocol, _ = load_protocol()
    field_names = set(protocol["scenario_fields"])
    require_exact_keys(row, field_names, "scenario")
    values: dict[str, Decimal] = {}
    for name, control in protocol["scenario_fields"].items():
        numeric = as_decimal(row[name], name)
        minimum = decimal_control(control["minimum"], f"{name}.minimum")
        maximum = decimal_control(control["maximum"], f"{name}.maximum")
        if control.get("exclusive_minimum") is True:
            if numeric <= minimum:
                raise EconomicProtocolError(f"{name} must be greater than {minimum}")
        elif numeric < minimum:
            raise EconomicProtocolError(f"{name} must be at least {minimum}")
        if numeric > maximum:
            raise EconomicProtocolError(f"{name} exceeds {maximum}")
        if control["kind"] == "integer" and numeric != numeric.to_integral_value():
            raise EconomicProtocolError(f"{name} must be integral")
        values[name] = numeric
    maximum = decimal_control(
        protocol["numeric_controls"]["maximum_calculated_absolute_magnitude"],
        "maximum_calculated_absolute_magnitude",
    )
    precision = as_integer(
        protocol["numeric_controls"]["intermediate_decimal_precision"],
        "intermediate_decimal_precision",
    )
    calculated: dict[str, Decimal] = {}
    with localcontext() as context:
        context.prec = precision
        for step in protocol["calculation_steps"]:
            operands = [
                calculated.get(name, values.get(name)) for name in step["operands"]
            ]
            if any(item is None for item in operands):
                raise EconomicProtocolError(
                    f"calculation step {step['output']} has an unresolved operand"
                )
            numeric_operands = [item for item in operands if isinstance(item, Decimal)]
            operation = step["operation"]
            if operation == "add":
                result = sum(numeric_operands, Decimal(0))
            elif operation == "subtract":
                result = numeric_operands[0] - numeric_operands[1]
            elif operation == "multiply":
                result = Decimal(1)
                for operand in numeric_operands:
                    result *= operand
            elif operation == "divide":
                if numeric_operands[1] == 0:
                    raise EconomicProtocolError(
                        f"calculation step {step['output']} divides by zero"
                    )
                result = numeric_operands[0] / numeric_operands[1]
            else:
                raise EconomicProtocolError(f"unsupported operation: {operation}")
            if not result.is_finite() or abs(result) > maximum:
                raise EconomicProtocolError(
                    f"calculation step {step['output']} exceeded its magnitude bound"
                )
            calculated[step["output"]] = result
    return {
        step["output"]: decimal_output_text(calculated[step["output"]], protocol)
        for step in protocol["calculation_steps"]
    }


def calculate_case(
    case: dict[str, Any], protocol: dict[str, Any] | None = None
) -> dict[str, Any]:
    if protocol is None:
        protocol, protocol_raw = load_protocol()
    else:
        protocol_raw = PROTOCOL_PATH.read_bytes()
    validate_case(case, protocol, protocol_sha256=bytes_sha256(protocol_raw))
    outputs = {
        name: calculate_scenario(case["scenarios"][name], protocol)
        for name in SCENARIO_NAMES
    }
    for field in protocol["monotonic_outputs"]:
        values = [Decimal(outputs[name][field]) for name in SCENARIO_NAMES]
        if values != sorted(values):
            raise EconomicProtocolError(
                f"low/base/high outputs are not monotonic for {field}: {values}"
            )
    return {
        "schema": "outage_second_economic_calculation.v1",
        "case_id": case["case_id"],
        "scenario_outputs": outputs,
    }


def illustrative_case(protocol: dict[str, Any] | None = None) -> dict[str, Any]:
    if protocol is None:
        protocol, protocol_raw = load_protocol()
    else:
        protocol_raw = PROTOCOL_PATH.read_bytes()
    template = read_json(CASE_TEMPLATE_PATH)
    case = copy.deepcopy(template)
    case.update(
        {
            "case_id": "SYNTHETIC_OUTAGE_SECOND_METHOD_FIXTURE",
            "case_classification": "SYNTHETIC_ILLUSTRATIVE",
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": bytes_sha256(protocol_raw),
            "prepared_utc": "2026-07-16T00:00:00Z",
            "counterfactual_frozen_utc": "2026-07-16T00:01:00Z",
            "valuation_perspective": protocol["valuation_perspective"],
            "currency": protocol["currency"],
            "base_year": 2026,
            "operating_entity": {
                "legal_name": "Synthetic Example Entity",
                "organization_id": "synthetic-example-entity",
                "economic_owner_organization": "Synthetic Example Entity",
            },
            "named_system": "synthetic_order_processing_system",
            "named_outage_scenario": "synthetic_30_minute_interruption",
            "counterfactual_baseline": "Synthetic normal operation without the named interruption.",
            "analysis_period": {
                "start_utc": "2026-01-01T00:00:00Z",
                "end_utc": "2027-01-01T00:00:00Z",
            },
            "input_sources": [],
            "technical_evidence": None,
            "limitations": [
                "Every input is synthetic and exists only to exercise the calculation method.",
                "No customer, LumenCore, technical, savings, pricing, or public-release claim is made.",
            ],
        }
    )
    common = {
        "reporting_period_seconds": 31536000,
        "outage_duration_seconds": 1800,
    }
    case["scenarios"] = {
        "low": {
            **common,
            "annual_revenue_usd": 100000000,
            "affected_scope_fraction": Decimal("0.10"),
            "nonrecoverable_fraction": Decimal("0.10"),
            "contribution_margin_fraction": Decimal("0.20"),
            "fixed_incremental_costs_per_event_usd": 50000,
            "variable_incremental_costs_per_second_usd": 5,
            "interruption_related_savings_per_event_usd": 5000,
            "interruption_related_savings_per_second_usd": 1,
            "annual_avoided_outage_seconds": 100,
            "annual_avoided_event_count": 1,
            "attribution_fraction": Decimal("0.20"),
            "confidence_factor": Decimal("0.50"),
        },
        "base": {
            **common,
            "annual_revenue_usd": 250000000,
            "affected_scope_fraction": Decimal("0.40"),
            "nonrecoverable_fraction": Decimal("0.25"),
            "contribution_margin_fraction": Decimal("0.30"),
            "fixed_incremental_costs_per_event_usd": 200000,
            "variable_incremental_costs_per_second_usd": 25,
            "interruption_related_savings_per_event_usd": 10000,
            "interruption_related_savings_per_second_usd": 2,
            "annual_avoided_outage_seconds": 1000,
            "annual_avoided_event_count": 4,
            "attribution_fraction": Decimal("0.50"),
            "confidence_factor": Decimal("0.50"),
        },
        "high": {
            **common,
            "annual_revenue_usd": 500000000,
            "affected_scope_fraction": Decimal("0.80"),
            "nonrecoverable_fraction": Decimal("0.40"),
            "contribution_margin_fraction": Decimal("0.40"),
            "fixed_incremental_costs_per_event_usd": 1000000,
            "variable_incremental_costs_per_second_usd": 100,
            "interruption_related_savings_per_event_usd": 0,
            "interruption_related_savings_per_second_usd": 0,
            "annual_avoided_outage_seconds": 5000,
            "annual_avoided_event_count": 10,
            "attribution_fraction": Decimal("0.80"),
            "confidence_factor": Decimal("0.80"),
        },
    }
    return case


def _ensure_regular_file(path: Path, label: str) -> Path:
    if not path.exists() or not path.is_file():
        raise EconomicProtocolError(f"{label} is not a regular file: {path}")
    if path.is_symlink():
        raise EconomicProtocolError(f"{label} cannot be a symlink: {path}")
    return path


def resolve_relative_artifact(root: Path, relative: str, label: str) -> Path:
    normalized = validate_relative_artifact_path(relative, label)
    if root.is_symlink():
        raise EconomicProtocolError(f"artifact root cannot be a symlink: {root}")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise EconomicProtocolError(f"artifact root is not a real directory: {root}")
    cursor = root
    for part in PurePosixPath(normalized).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise EconomicProtocolError(f"{label} traverses a symlink: {normalized}")
    resolved = cursor.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise EconomicProtocolError(f"{label} escapes the artifact root") from exc
    return _ensure_regular_file(resolved, label)


def validate_artifact_root(root: Path) -> Path:
    if root.is_symlink():
        raise EconomicProtocolError(f"artifact root cannot be a symlink: {root}")
    resolved = root.resolve(strict=True)
    if not resolved.is_dir():
        raise EconomicProtocolError(f"artifact root is not a directory: {root}")
    return resolved


def verify_referenced_artifact(
    *,
    root: Path,
    artifact_path: str,
    expected_sha256: str,
    media_type: str,
    logical_role: str,
    protocol: dict[str, Any],
) -> tuple[dict[str, Any], bytes, Any | None]:
    expected = require_sha256(expected_sha256, f"{logical_role}.sha256")
    resolved = resolve_relative_artifact(root, artifact_path, f"{logical_role}.path")
    raw = resolved.read_bytes()
    actual = bytes_sha256(raw)
    if actual != expected:
        raise EconomicProtocolError(
            f"{logical_role} SHA-256 mismatch: expected {expected}, recomputed {actual}"
        )
    parsed: Any | None = None
    if media_type in protocol["artifact_controls"]["strict_json_media_types"]:
        parsed = strict_json_loads(raw, label=f"{logical_role}:{artifact_path}")
        _validate_loaded_json_against_protocol(parsed, protocol, logical_role)
    return (
        {
            "logical_role": logical_role,
            "artifact_path": artifact_path,
            "media_type": media_type,
            "bytes": len(raw),
            "sha256": actual,
        },
        raw,
        parsed,
    )


def _validate_effect_value(
    value: Any,
    field: str,
    label: str,
    protocol: dict[str, Any],
) -> Decimal:
    control = protocol["scenario_fields"][field]
    numeric = as_decimal(value, label)
    minimum = decimal_control(control["minimum"], f"{field}.minimum")
    maximum = decimal_control(control["maximum"], f"{field}.maximum")
    if numeric < minimum or numeric > maximum:
        raise EconomicProtocolError(f"{label} is outside the configured range")
    if control["kind"] == "integer" and numeric != numeric.to_integral_value():
        raise EconomicProtocolError(f"{label} must be integral")
    return numeric


def validate_technical_evidence(
    evidence: dict[str, Any],
    *,
    case: dict[str, Any],
    artifact_root: Path,
    protocol: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    require_exact_keys(
        evidence,
        {
            "schema",
            "evidence_id",
            "case_id",
            "named_system",
            "named_outage_scenario",
            "counterfactual_baseline",
            "protocol_frozen_utc",
            "scoring_started_utc",
            "evaluation_completed_utc",
            "evaluator_name",
            "evaluator_organization",
            "artifacts",
            "measured_effects",
        },
        "technical_evidence",
    )
    controls = protocol["technical_evidence_controls"]
    if evidence["schema"] != controls["schema"]:
        raise EconomicProtocolError("technical evidence schema mismatch")
    require_identifier(evidence["evidence_id"], "technical_evidence.evidence_id")
    for field in (
        "case_id",
        "named_system",
        "named_outage_scenario",
        "counterfactual_baseline",
    ):
        if evidence[field] != case[field]:
            raise EconomicProtocolError(f"technical evidence scope mismatch: {field}")
    evaluator_name = require_nonempty_text(
        evidence["evaluator_name"], "technical_evidence.evaluator_name"
    )
    evaluator_organization = require_nonempty_text(
        evidence["evaluator_organization"],
        "technical_evidence.evaluator_organization",
    )
    protocol_frozen = parse_utc_timestamp(
        evidence["protocol_frozen_utc"], "technical_evidence.protocol_frozen_utc"
    )
    scoring_started = parse_utc_timestamp(
        evidence["scoring_started_utc"], "technical_evidence.scoring_started_utc"
    )
    evaluation_completed = parse_utc_timestamp(
        evidence["evaluation_completed_utc"],
        "technical_evidence.evaluation_completed_utc",
    )
    counterfactual_frozen = parse_utc_timestamp(
        case["counterfactual_frozen_utc"], "case.counterfactual_frozen_utc"
    )
    if not counterfactual_frozen <= protocol_frozen <= scoring_started < evaluation_completed:
        raise EconomicProtocolError(
            "counterfactual/protocol/scoring/evaluation timestamps are out of order"
        )

    artifact_rows = evidence["artifacts"]
    required_roles = controls["required_artifact_roles"]
    if not isinstance(artifact_rows, list) or len(artifact_rows) != len(required_roles):
        raise EconomicProtocolError("technical evidence artifact count is not exact")
    role_rows: dict[str, dict[str, Any]] = {}
    paths: set[str] = set()
    manifest: list[dict[str, Any]] = []
    for index, row in enumerate(artifact_rows):
        require_exact_keys(
            row,
            {"role", "artifact_path", "sha256", "media_type"},
            f"technical_evidence.artifacts[{index}]",
        )
        role = row["role"]
        if role not in required_roles or role in role_rows:
            raise EconomicProtocolError(f"invalid or duplicate technical role: {role}")
        path = validate_relative_artifact_path(
            row["artifact_path"], f"technical_evidence.artifacts[{index}].artifact_path"
        )
        if path in paths:
            raise EconomicProtocolError("technical support artifact paths must be unique")
        if row["media_type"] not in {"application/json", "text/plain", "application/pdf"}:
            raise EconomicProtocolError("unsupported technical artifact media_type")
        manifest_row, _, _ = verify_referenced_artifact(
            root=artifact_root,
            artifact_path=path,
            expected_sha256=row["sha256"],
            media_type=row["media_type"],
            logical_role=f"TECHNICAL_SUPPORT:{role}",
            protocol=protocol,
        )
        role_rows[role] = row
        paths.add(path)
        manifest.append(manifest_row)
    if set(role_rows) != set(required_roles):
        raise EconomicProtocolError("technical support artifact roles are incomplete")

    effects = require_exact_keys(
        evidence["measured_effects"], set(SCENARIO_NAMES), "technical_evidence.measured_effects"
    )
    normalized_effects: dict[str, dict[str, str]] = {}
    effects_match = True
    effect_fields = controls["measured_effect_fields"]
    for scenario_name in SCENARIO_NAMES:
        row = require_exact_keys(
            effects[scenario_name],
            set(effect_fields),
            f"technical_evidence.measured_effects.{scenario_name}",
        )
        normalized_effects[scenario_name] = {}
        for field in effect_fields:
            measured = _validate_effect_value(
                row[field],
                field,
                f"technical_evidence.{scenario_name}.{field}",
                protocol,
            )
            case_value = as_decimal(
                case["scenarios"][scenario_name][field], f"case.{scenario_name}.{field}"
            )
            if measured != case_value:
                effects_match = False
            normalized_effects[scenario_name][field] = canonical_decimal_text(measured)
    if not effects_match:
        raise EconomicProtocolError(
            "case avoided seconds/event counts do not match technical evidence"
        )
    summary = {
        "evidence_id": evidence["evidence_id"],
        "evaluator_name": evaluator_name,
        "evaluator_organization": evaluator_organization,
        "protocol_frozen_utc": evidence["protocol_frozen_utc"],
        "scoring_started_utc": evidence["scoring_started_utc"],
        "evaluation_completed_utc": evidence["evaluation_completed_utc"],
        "measured_effects": normalized_effects,
        "support_artifact_manifest_sha256": stable_sha256(
            sorted(manifest, key=lambda item: item["logical_role"])
        ),
    }
    return summary, manifest


def bind_case_artifacts(
    case: dict[str, Any],
    *,
    artifact_root: Path,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    manifest: list[dict[str, Any]] = []
    paths: set[str] = set()
    for source in case["input_sources"]:
        row, _, _ = verify_referenced_artifact(
            root=artifact_root,
            artifact_path=source["artifact_path"],
            expected_sha256=source["sha256"],
            media_type=source["media_type"],
            logical_role=f"INPUT_SOURCE:{source['source_id']}",
            protocol=protocol,
        )
        if row["artifact_path"] in paths:
            raise EconomicProtocolError("artifact path is reused across input sources")
        paths.add(row["artifact_path"])
        manifest.append(row)

    technical_summary: dict[str, Any] | None = None
    technical_artifact_sha256: str | None = None
    if case["technical_evidence"] is not None:
        reference = case["technical_evidence"]
        technical_row, _, parsed = verify_referenced_artifact(
            root=artifact_root,
            artifact_path=reference["artifact_path"],
            expected_sha256=reference["sha256"],
            media_type="application/json",
            logical_role="TECHNICAL_EVIDENCE",
            protocol=protocol,
        )
        if not isinstance(parsed, dict):
            raise EconomicProtocolError("technical evidence JSON root must be an object")
        if technical_row["artifact_path"] in paths:
            raise EconomicProtocolError("technical evidence path duplicates an input source")
        paths.add(technical_row["artifact_path"])
        manifest.append(technical_row)
        technical_summary, support_manifest = validate_technical_evidence(
            parsed,
            case=case,
            artifact_root=artifact_root,
            protocol=protocol,
        )
        for row in support_manifest:
            if row["artifact_path"] in paths:
                raise EconomicProtocolError(
                    "an artifact path is reused across evidence roles"
                )
            paths.add(row["artifact_path"])
            manifest.append(row)
        technical_artifact_sha256 = technical_row["sha256"]

    ordered = sorted(manifest, key=lambda item: item["logical_role"])
    external = case["case_classification"] == "EXTERNAL_OPERATOR_CASE"
    return {
        "manifest": ordered,
        "manifest_sha256": stable_sha256(ordered),
        "technical_summary": technical_summary,
        "technical_artifact_sha256": technical_artifact_sha256,
        "evidence_checks": {
            "external_operator_case": external,
            "input_source_artifacts_recomputed": external
            and len(case["input_sources"]) > 0,
            "technical_evidence_artifact_recomputed": external
            and technical_summary is not None,
            "technical_support_artifacts_recomputed": external
            and technical_summary is not None,
            "case_effects_match_technical_evidence": external
            and technical_summary is not None,
        },
    }


def scope_from_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "operating_entity": copy.deepcopy(case["operating_entity"]),
        "named_system": case["named_system"],
        "named_outage_scenario": case["named_outage_scenario"],
        "counterfactual_baseline": case["counterfactual_baseline"],
        "analysis_period": copy.deepcopy(case["analysis_period"]),
        "valuation_perspective": case["valuation_perspective"],
        "currency": case["currency"],
        "base_year": as_integer(case["base_year"], "case.base_year"),
    }


def scenario_input_snapshot(
    case: dict[str, Any], protocol: dict[str, Any]
) -> dict[str, dict[str, str]]:
    return {
        scenario_name: {
            field: canonical_decimal_text(
                as_decimal(case["scenarios"][scenario_name][field], field)
            )
            for field in protocol["scenario_fields"]
        }
        for scenario_name in SCENARIO_NAMES
    }


def build_private_calculation(
    *,
    case: dict[str, Any],
    case_raw: bytes,
    protocol: dict[str, Any],
    protocol_raw: bytes,
    artifact_binding: dict[str, Any],
) -> dict[str, Any]:
    calculation = calculate_case(case, protocol)
    payload: dict[str, Any] = {
        "schema": "outage_second_private_calculation_store.v1",
        "classification": "PRIVATE_CALCULATION_DO_NOT_PUBLISH_BY_DEFAULT",
        "protocol": {
            "protocol_id": protocol["protocol_id"],
            "artifact_bytes": len(protocol_raw),
            "artifact_sha256": bytes_sha256(protocol_raw),
            "executable_controls_sha256": stable_sha256(
                {
                    "scenario_fields": protocol["scenario_fields"],
                    "calculation_steps": protocol["calculation_steps"],
                    "monotonic_outputs": protocol["monotonic_outputs"],
                    "numeric_controls": protocol["numeric_controls"],
                    "claim_gates": protocol["claim_gates"],
                    "release_control": protocol["release_control"],
                }
            ),
        },
        "case": {
            "case_id": case["case_id"],
            "case_classification": case["case_classification"],
            "artifact_bytes": len(case_raw),
            "artifact_sha256": bytes_sha256(case_raw),
            "prepared_utc": case["prepared_utc"],
            "counterfactual_frozen_utc": case["counterfactual_frozen_utc"],
        },
        "template_bindings": {
            "case_template_artifact_sha256": file_sha256(CASE_TEMPLATE_PATH),
            "receipt_template_artifact_sha256": file_sha256(RECEIPT_TEMPLATE_PATH),
        },
        "implementation_bindings": {
            "builder_source_artifact_sha256": file_sha256(BUILDER_SOURCE_PATH),
            "verifier_source_artifact_sha256": file_sha256(VERIFIER_SOURCE_PATH),
        },
        "scope": scope_from_case(case),
        "scenario_inputs": scenario_input_snapshot(case, protocol),
        "scenario_outputs": calculation["scenario_outputs"],
        "input_artifact_manifest": artifact_binding["manifest"],
        "input_artifact_manifest_sha256": artifact_binding["manifest_sha256"],
        "technical_evidence": artifact_binding["technical_summary"],
        "limitations": copy.deepcopy(case["limitations"]),
        "claim_boundary": protocol["claim_boundary"],
        "calculation_payload_sha256": None,
    }
    payload["calculation_payload_sha256"] = stable_sha256(payload)
    return payload


def _assert_no_booleans(value: Any, label: str) -> None:
    if isinstance(value, bool):
        raise EconomicProtocolError(f"{label} cannot contain self-asserted booleans")
    if isinstance(value, dict):
        for key, child in value.items():
            _assert_no_booleans(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_booleans(child, f"{label}[{index}]")


def validate_receipt_shape(receipt: dict[str, Any], label: str = "receipt") -> None:
    require_exact_keys(
        receipt,
        {
            "schema",
            "receipt_status",
            "receipt_id",
            "bindings",
            "accepted_scope",
            "accepted_outputs",
            "attestations",
            "decision",
            "release_decision",
            "decision_utc",
            "signers",
            "signatures",
            "claim_boundary",
        },
        label,
    )
    require_exact_keys(
        receipt["bindings"],
        {
            "protocol_id",
            "protocol_artifact_sha256",
            "case_id",
            "case_artifact_sha256",
            "private_calculation_artifact_sha256",
            "input_artifact_manifest_sha256",
            "technical_evidence_artifact_sha256",
        },
        f"{label}.bindings",
    )
    signers = require_exact_keys(receipt["signers"], set(SIGNER_ROLES), f"{label}.signers")
    signatures = require_exact_keys(
        receipt["signatures"], set(SIGNER_ROLES), f"{label}.signatures"
    )
    for role in SIGNER_ROLES:
        require_exact_keys(signers[role], set(SIGNER_FIELDS), f"{label}.signers.{role}")
        require_exact_keys(
            signatures[role], set(SIGNATURE_FIELDS), f"{label}.signatures.{role}"
        )
    _assert_no_booleans(receipt, label)


def validate_static_receipt_template(
    template: dict[str, Any], protocol: dict[str, Any]
) -> None:
    validate_receipt_shape(template, "receipt_template")
    controls = protocol["receipt_controls"]
    if template["schema"] != controls["schema"]:
        raise EconomicProtocolError("receipt template schema mismatch")
    if template["receipt_status"] != "UNSIGNED_TEMPLATE":
        raise EconomicProtocolError("static receipt template status is invalid")
    if template["receipt_id"] is not None:
        raise EconomicProtocolError("static receipt template receipt_id must be null")
    bindings = template["bindings"]
    if bindings["protocol_id"] != protocol["protocol_id"]:
        raise EconomicProtocolError("receipt template protocol_id mismatch")
    if any(
        value is not None
        for key, value in bindings.items()
        if key != "protocol_id"
    ):
        raise EconomicProtocolError("static receipt template bindings must be null")
    if template["accepted_scope"] is not None or template["accepted_outputs"] is not None:
        raise EconomicProtocolError("static receipt accepted values must be null")
    if template["attestations"] != [] or template["decision"] is not None:
        raise EconomicProtocolError("static receipt decision fields must be blank")
    if template["release_decision"] != "WITHHOLD" or template["decision_utc"] is not None:
        raise EconomicProtocolError("static receipt must default release to WITHHOLD")
    for role in SIGNER_ROLES:
        if any(value is not None for value in template["signers"][role].values()):
            raise EconomicProtocolError("static receipt signer fields must be null")
        signature = template["signatures"][role]
        if signature["algorithm"] != controls["signature_algorithm"]:
            raise EconomicProtocolError("static receipt signature algorithm mismatch")
        if any(
            value is not None
            for key, value in signature.items()
            if key != "algorithm"
        ):
            raise EconomicProtocolError("static receipt signature fields must be null")


def build_bound_receipt_template(
    *,
    private_payload: dict[str, Any],
    private_raw: bytes,
    protocol: dict[str, Any],
    protocol_raw: bytes,
    artifact_binding: dict[str, Any],
) -> dict[str, Any]:
    template = read_json(RECEIPT_TEMPLATE_PATH)
    validate_static_receipt_template(template, protocol)
    receipt = copy.deepcopy(template)
    receipt["receipt_status"] = protocol["receipt_controls"]["template_status"]
    receipt["bindings"] = {
        "protocol_id": protocol["protocol_id"],
        "protocol_artifact_sha256": bytes_sha256(protocol_raw),
        "case_id": private_payload["case"]["case_id"],
        "case_artifact_sha256": private_payload["case"]["artifact_sha256"],
        "private_calculation_artifact_sha256": bytes_sha256(private_raw),
        "input_artifact_manifest_sha256": private_payload[
            "input_artifact_manifest_sha256"
        ],
        "technical_evidence_artifact_sha256": artifact_binding[
            "technical_artifact_sha256"
        ],
    }
    receipt["accepted_scope"] = copy.deepcopy(private_payload["scope"])
    receipt["accepted_outputs"] = copy.deepcopy(private_payload["scenario_outputs"])
    receipt["attestations"] = copy.deepcopy(protocol["required_receipt_attestations"])
    return receipt


def prepare_calculation(
    *,
    case: dict[str, Any],
    case_raw: bytes,
    protocol: dict[str, Any],
    protocol_raw: bytes,
    artifact_root: Path,
) -> dict[str, Any]:
    validate_case(
        case,
        protocol,
        protocol_sha256=bytes_sha256(protocol_raw),
    )
    artifact_binding = bind_case_artifacts(
        case, artifact_root=artifact_root, protocol=protocol
    )
    private_payload = build_private_calculation(
        case=case,
        case_raw=case_raw,
        protocol=protocol,
        protocol_raw=protocol_raw,
        artifact_binding=artifact_binding,
    )
    private_raw = json_bytes(private_payload)
    bound_receipt = build_bound_receipt_template(
        private_payload=private_payload,
        private_raw=private_raw,
        protocol=protocol,
        protocol_raw=protocol_raw,
        artifact_binding=artifact_binding,
    )
    return {
        "case": case,
        "case_raw": case_raw,
        "artifact_binding": artifact_binding,
        "private_payload": private_payload,
        "private_raw": private_raw,
        "bound_receipt": bound_receipt,
        "bound_receipt_raw": json_bytes(bound_receipt),
    }


def receipt_signing_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    validate_receipt_shape(payload)
    for role in SIGNER_ROLES:
        payload["signatures"][role]["detached_signature_artifact_sha256"] = None
        payload["signatures"][role]["signed_payload_sha256"] = None
    return payload


def receipt_signing_bytes(receipt: dict[str, Any]) -> bytes:
    return canonical_json_bytes(receipt_signing_payload(receipt))


def receipt_signing_payload_sha256(receipt: dict[str, Any]) -> str:
    return bytes_sha256(receipt_signing_bytes(receipt))


def _read_external_artifact(path: Path, label: str) -> bytes:
    unresolved = _ensure_regular_file(path, label)
    resolved = unresolved.resolve(strict=True)
    raw = resolved.read_bytes()
    if not raw:
        raise EconomicProtocolError(f"{label} cannot be empty")
    if resolved.suffix.lower() == ".json":
        strict_json_loads(raw, label=label)
    return raw


def _validate_receipt_signer_identity(
    *,
    role: str,
    signer: dict[str, Any],
    private_payload: dict[str, Any],
    technical_summary: dict[str, Any],
    protocol: dict[str, Any],
) -> None:
    require_identifier(signer["signer_id"], f"receipt.signers.{role}.signer_id")
    name = require_nonempty_text(signer["name"], f"receipt.signers.{role}.name")
    organization = require_nonempty_text(
        signer["organization"], f"receipt.signers.{role}.organization"
    )
    expected_role = (
        "ECONOMIC_OWNER" if role == "economic_owner" else "INDEPENDENT_TECHNICAL_REVIEWER"
    )
    if signer["role"] != expected_role:
        raise EconomicProtocolError(f"receipt signer role mismatch: {role}")
    forbidden = protocol["receipt_controls"]["forbidden_signer_organization_tokens"]
    if any(token.lower() in organization.lower() for token in forbidden):
        raise EconomicProtocolError(f"receipt signer cannot be a LumenCore organization: {role}")
    if signer["independence_from_lumencore"] != "ATTESTED_INDEPENDENT":
        raise EconomicProtocolError(f"{role} did not attest independence from LumenCore")
    expected_other = (
        "NOT_APPLICABLE" if role == "economic_owner" else "ATTESTED_INDEPENDENT"
    )
    if signer["independence_from_other_signer"] != expected_other:
        raise EconomicProtocolError(
            f"{role} independence signer-separation attestation is invalid"
        )
    require_nonempty_text(
        signer["independence_basis"],
        f"receipt.signers.{role}.independence_basis",
        maximum=1024,
    )
    require_sha256(
        signer["independence_evidence_artifact_sha256"],
        f"receipt.signers.{role}.independence_evidence_artifact_sha256",
    )
    parse_utc_timestamp(signer["signed_utc"], f"receipt.signers.{role}.signed_utc")
    if role == "economic_owner":
        expected_organization = private_payload["scope"]["operating_entity"][
            "economic_owner_organization"
        ]
        if organization != expected_organization:
            raise EconomicProtocolError(
                "economic owner organization does not match the accepted entity"
            )
    else:
        if name != technical_summary["evaluator_name"]:
            raise EconomicProtocolError("technical reviewer name does not match evidence")
        if organization != technical_summary["evaluator_organization"]:
            raise EconomicProtocolError(
                "technical reviewer organization does not match evidence"
            )


def verify_completed_receipt(
    receipt: dict[str, Any],
    *,
    bound_template: dict[str, Any],
    private_payload: dict[str, Any],
    artifact_binding: dict[str, Any],
    protocol: dict[str, Any],
    receipt_artifacts: Mapping[str, Mapping[str, Path]],
    trusted_key_sha256_by_role: Mapping[str, str],
    now: datetime | None = None,
) -> dict[str, Any]:
    validate_receipt_shape(receipt)
    _validate_loaded_json_against_protocol(receipt, protocol, "receipt")
    controls = protocol["receipt_controls"]
    if receipt["schema"] != controls["schema"]:
        raise EconomicProtocolError("completed receipt schema mismatch")
    if receipt["receipt_status"] != controls["completed_status"]:
        raise EconomicProtocolError("completed receipt status is invalid")
    require_identifier(receipt["receipt_id"], "receipt.receipt_id")
    if receipt["bindings"] != bound_template["bindings"]:
        raise EconomicProtocolError("receipt bindings do not match exact artifacts")
    if receipt["accepted_scope"] != bound_template["accepted_scope"]:
        raise EconomicProtocolError("receipt accepted scope is not exact")
    if receipt["accepted_outputs"] != bound_template["accepted_outputs"]:
        raise EconomicProtocolError("receipt accepted outputs are not exact")
    if receipt["attestations"] != protocol["required_receipt_attestations"]:
        raise EconomicProtocolError("receipt attestations are not the exact required set")
    if receipt["claim_boundary"] != bound_template["claim_boundary"]:
        raise EconomicProtocolError("receipt claim boundary changed")
    if receipt["decision"] not in controls["decision_values"]:
        raise EconomicProtocolError("receipt decision is unsupported")
    if receipt["release_decision"] not in controls["release_decision_values"]:
        raise EconomicProtocolError("receipt release decision is unsupported")
    if (
        receipt["decision"] != controls["acceptance_decision"]
        and receipt["release_decision"] != "WITHHOLD"
    ):
        raise EconomicProtocolError("a rejected receipt cannot approve public release")
    technical_summary = artifact_binding["technical_summary"]
    if not isinstance(technical_summary, dict):
        raise EconomicProtocolError(
            "completed receipt requires recomputed technical evidence"
        )

    decision_utc = parse_utc_timestamp(receipt["decision_utc"], "receipt.decision_utc")
    evaluation_completed = parse_utc_timestamp(
        technical_summary["evaluation_completed_utc"],
        "technical_evidence.evaluation_completed_utc",
    )
    if decision_utc < evaluation_completed:
        raise EconomicProtocolError("receipt decision predates technical evaluation")
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    future_skew = timedelta(
        seconds=as_integer(
            controls["maximum_future_skew_seconds"], "maximum_future_skew_seconds"
        )
    )
    if decision_utc > current + future_skew:
        raise EconomicProtocolError("receipt decision timestamp is in the future")
    maximum_delay = timedelta(
        seconds=as_integer(
            controls["maximum_signature_delay_seconds"],
            "maximum_signature_delay_seconds",
        )
    )

    signers = receipt["signers"]
    for role in SIGNER_ROLES:
        _validate_receipt_signer_identity(
            role=role,
            signer=signers[role],
            private_payload=private_payload,
            technical_summary=technical_summary,
            protocol=protocol,
        )
        signed_utc = parse_utc_timestamp(
            signers[role]["signed_utc"], f"receipt.signers.{role}.signed_utc"
        )
        if not decision_utc <= signed_utc <= decision_utc + maximum_delay:
            raise EconomicProtocolError(f"{role} signature timestamp is out of order")
        if signed_utc > current + future_skew:
            raise EconomicProtocolError(f"{role} signature timestamp is in the future")
    economic = signers["economic_owner"]
    technical = signers["technical_reviewer"]
    if economic["signer_id"] == technical["signer_id"]:
        raise EconomicProtocolError("receipt signers must have distinct signer IDs")
    if economic["name"].casefold() == technical["name"].casefold():
        raise EconomicProtocolError("receipt signers must be distinct people")
    if economic["organization"].casefold() == technical["organization"].casefold():
        raise EconomicProtocolError("technical reviewer must be organizationally independent")

    if set(receipt_artifacts) != set(SIGNER_ROLES):
        raise EconomicProtocolError("actual receipt artifacts are required for both signers")
    if set(trusted_key_sha256_by_role) != set(SIGNER_ROLES):
        raise EconomicProtocolError("out-of-band trusted key hashes are required for both signers")
    signing_bytes = receipt_signing_bytes(receipt)
    signing_sha256 = bytes_sha256(signing_bytes)
    external_manifest: list[dict[str, Any]] = []
    public_key_hashes: dict[str, str] = {}

    for role in SIGNER_ROLES:
        paths = receipt_artifacts[role]
        if set(paths) != {"public_key", "signature", "independence"}:
            raise EconomicProtocolError(f"{role} actual artifact paths are incomplete")
        signature_record = receipt["signatures"][role]
        if signature_record["algorithm"] != controls["signature_algorithm"]:
            raise EconomicProtocolError(f"{role} signature algorithm is invalid")
        expected_signing_sha = require_sha256(
            signature_record["signed_payload_sha256"],
            f"receipt.signatures.{role}.signed_payload_sha256",
        )
        if expected_signing_sha != signing_sha256:
            raise EconomicProtocolError(f"{role} signed payload hash does not match")

        key_raw = _read_external_artifact(paths["public_key"], f"{role} public key")
        key_sha = bytes_sha256(key_raw)
        trusted_sha = require_sha256(
            trusted_key_sha256_by_role[role], f"trusted_key_sha256.{role}"
        )
        if key_sha != trusted_sha:
            raise EconomicProtocolError(f"{role} public key is not the out-of-band trusted key")
        if signature_record["public_key_artifact_sha256"] != key_sha:
            raise EconomicProtocolError(f"{role} receipt public-key binding mismatch")
        try:
            loaded_key = serialization.load_pem_public_key(key_raw)
        except (ValueError, TypeError) as exc:
            raise EconomicProtocolError(f"{role} public key is not valid PEM") from exc
        if not isinstance(loaded_key, Ed25519PublicKey):
            raise EconomicProtocolError(f"{role} public key is not Ed25519")

        signature_raw = _read_external_artifact(
            paths["signature"], f"{role} detached signature"
        )
        if len(signature_raw) != 64:
            raise EconomicProtocolError(f"{role} Ed25519 signature must be 64 bytes")
        signature_sha = bytes_sha256(signature_raw)
        if signature_record["detached_signature_artifact_sha256"] != signature_sha:
            raise EconomicProtocolError(f"{role} detached-signature hash mismatch")
        try:
            loaded_key.verify(signature_raw, signing_bytes)
        except InvalidSignature as exc:
            raise EconomicProtocolError(
                f"{role} detached signature is cryptographically invalid"
            ) from exc

        independence_raw = _read_external_artifact(
            paths["independence"], f"{role} independence evidence"
        )
        independence_sha = bytes_sha256(independence_raw)
        if (
            signers[role]["independence_evidence_artifact_sha256"]
            != independence_sha
        ):
            raise EconomicProtocolError(f"{role} independence artifact hash mismatch")
        public_key_hashes[role] = key_sha
        external_manifest.extend(
            [
                {
                    "logical_role": f"{role.upper()}_PUBLIC_KEY",
                    "bytes": len(key_raw),
                    "sha256": key_sha,
                },
                {
                    "logical_role": f"{role.upper()}_DETACHED_SIGNATURE",
                    "bytes": len(signature_raw),
                    "sha256": signature_sha,
                },
                {
                    "logical_role": f"{role.upper()}_INDEPENDENCE_EVIDENCE",
                    "bytes": len(independence_raw),
                    "sha256": independence_sha,
                },
            ]
        )
    if public_key_hashes["economic_owner"] == public_key_hashes["technical_reviewer"]:
        raise EconomicProtocolError("receipt signers cannot share a public key")

    checks = {
        "receipt_bindings_exact": True,
        "receipt_outputs_exact": True,
        "receipt_scope_exact": True,
        "receipt_attestations_exact": True,
        "receipt_signers_verified": True,
        "receipt_independence_verified": True,
        "receipt_timestamps_valid": True,
        "receipt_decision_accepts": receipt["decision"]
        == controls["acceptance_decision"],
        "receipt_signatures_verified": True,
        "receipt_release_decision_approves": receipt["release_decision"]
        == controls["release_approval_decision"],
    }
    return {
        "schema": "outage_second_external_receipt_verification.v1",
        "receipt_status": receipt["receipt_status"],
        "decision": receipt["decision"],
        "release_decision": receipt["release_decision"],
        "signing_payload_sha256": signing_sha256,
        "checks": checks,
        "external_artifact_manifest": sorted(
            external_manifest, key=lambda item: item["logical_role"]
        ),
    }


def evaluate_configured_gates(
    protocol: dict[str, Any], evidence_checks: Mapping[str, bool]
) -> dict[str, bool]:
    values: dict[str, bool] = {
        name: evidence_checks.get(name) is True for name in EVIDENCE_CHECK_NAMES
    }
    gates: dict[str, bool] = {}
    gate_config = protocol["claim_gates"]
    for gate_name in gate_config["evaluation_order"]:
        requirements = gate_config["definitions"][gate_name]
        gates[gate_name] = all(
            gates.get(requirement, values.get(requirement, False))
            for requirement in requirements
        )
    return gates


def build_gate_report(
    *,
    protocol: dict[str, Any],
    artifact_binding: dict[str, Any],
    receipt_verification: dict[str, Any] | None,
) -> dict[str, Any]:
    checks = {name: False for name in EVIDENCE_CHECK_NAMES}
    checks.update(artifact_binding["evidence_checks"])
    if receipt_verification is not None:
        checks.update(receipt_verification["checks"])
    gates = evaluate_configured_gates(protocol, checks)
    if gates["public_economic_release_allowed"]:
        state = "PUBLIC_RELEASE_APPROVED_ACCEPTED_ESTIMATE"
    elif gates["accepted_estimated_avoided_cost_claim_allowed"]:
        state = "ACCEPTED_PRIVATE_ESTIMATE_WITHHELD"
    else:
        state = "ALL_ECONOMIC_CLAIM_GATES_CLOSED"
    return {
        "schema": "outage_second_economic_gate_report.v1",
        "state": state,
        "checks": checks,
        "gates": gates,
        "gate_control_sha256": stable_sha256(protocol["claim_gates"]),
    }


def build_public_summary(
    *,
    private_payload: dict[str, Any],
    private_raw: bytes,
    receipt_raw: bytes,
    gate_report: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    accepted = gate_report["gates"][
        "accepted_estimated_avoided_cost_claim_allowed"
    ]
    released = gate_report["gates"]["public_economic_release_allowed"]
    release = protocol["release_control"]
    if released:
        status = release["released_summary_status"]
    elif accepted:
        status = release["accepted_private_summary_status"]
    else:
        status = release["closed_gate_summary_status"]
    publication_id = stable_sha256(
        {
            "protocol_sha256": private_payload["protocol"]["artifact_sha256"],
            "case_sha256": private_payload["case"]["artifact_sha256"],
            "private_calculation_sha256": bytes_sha256(private_raw),
            "receipt_sha256": bytes_sha256(receipt_raw),
        }
    )
    summary: dict[str, Any] = {
        "schema": "outage_second_public_summary.v1",
        "publication_id": publication_id,
        "status": status,
        "accepted_claim_state": "ACCEPTED" if accepted else "CLOSED",
        "public_release_state": "APPROVED" if released else "WITHHELD",
        "scope": copy.deepcopy(private_payload["scope"]) if released else None,
        "scenario_outputs": (
            copy.deepcopy(private_payload["scenario_outputs"]) if released else None
        ),
        "redaction": {
            "scope": "RELEASED_BY_SIGNED_RECEIPT" if released else "REDACTED",
            "economics": "RELEASED_BY_SIGNED_RECEIPT" if released else "REDACTED",
        },
        "claim_boundary": protocol["claim_boundary"],
        "private_artifact_bindings": {
            "private_calculation_artifact_sha256": bytes_sha256(private_raw),
            "acceptance_receipt_artifact_sha256": bytes_sha256(receipt_raw),
        },
        "summary_payload_sha256": None,
    }
    summary["summary_payload_sha256"] = stable_sha256(summary)
    return summary


def render_public_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Outage-Second Economic Value Summary",
        "",
        f"Status: `{summary['status']}`",
        "",
    ]
    if summary["public_release_state"] != "APPROVED":
        lines.extend(
            [
                "No economic outputs or private scope are published.",
                "",
                "The private calculation remains unavailable for public use until exact external acceptance and public release are cryptographically verified.",
                "",
                f"Claim boundary: {summary['claim_boundary']}",
            ]
        )
        return "\n".join(lines)
    scope = summary["scope"]
    outputs = summary["scenario_outputs"]
    lines.extend(
        [
            f"Entity: {scope['operating_entity']['legal_name']}",
            "",
            f"System: `{scope['named_system']}`",
            "",
            f"Scenario: `{scope['named_outage_scenario']}`",
            "",
            "| Band | Time-flow cost/sec | Fixed cost/event | Event cost | Annual avoided time-flow cost | Annual avoided fixed-event cost | Estimated annual avoided cost |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for name in SCENARIO_NAMES:
        row = outputs[name]
        lines.append(
            "| {name} | ${flow} | ${fixed} | ${event} | ${annual_flow} | ${annual_fixed} | ${annual} |".format(
                name=name,
                flow=row["net_time_flow_cost_per_second_usd"],
                fixed=row["net_fixed_incremental_cost_per_event_usd"],
                event=row["incremental_outage_cost_per_event_usd"],
                annual_flow=row["annual_avoided_time_flow_cost_usd"],
                annual_fixed=row["annual_avoided_fixed_event_cost_usd"],
                annual=row["estimated_annual_avoided_cost_usd"],
            )
        )
    lines.extend(["", f"Claim boundary: {summary['claim_boundary']}"])
    return "\n".join(lines)


def validate_public_redaction(
    *,
    summary: dict[str, Any],
    markdown: str,
    private_payload: dict[str, Any],
) -> None:
    released = summary["public_release_state"] == "APPROVED"
    if released:
        if summary["scope"] != private_payload["scope"]:
            raise EconomicProtocolError("released public scope is not exact")
        if summary["scenario_outputs"] != private_payload["scenario_outputs"]:
            raise EconomicProtocolError("released public outputs are not exact")
        return
    if summary["scope"] is not None or summary["scenario_outputs"] is not None:
        raise EconomicProtocolError("closed-gate public summary leaked private economics")
    if "$" in markdown:
        raise EconomicProtocolError("closed-gate Markdown contains economic amounts")
    private_scope_values = (
        private_payload["scope"]["operating_entity"]["legal_name"],
        private_payload["scope"]["named_system"],
        private_payload["scope"]["named_outage_scenario"],
        private_payload["scope"]["counterfactual_baseline"],
    )
    if any(value in markdown for value in private_scope_values):
        raise EconomicProtocolError("closed-gate Markdown leaked private scope")
    if "estimated_annual_avoided_cost_usd" in markdown:
        raise EconomicProtocolError("closed-gate Markdown leaked an economic output field")


def bundle_mode(
    receipt: dict[str, Any], gate_report: dict[str, Any], protocol: dict[str, Any]
) -> str:
    if receipt["receipt_status"] == protocol["receipt_controls"]["template_status"]:
        return "PREPARED_UNSIGNED"
    if gate_report["gates"]["accepted_estimated_avoided_cost_claim_allowed"]:
        return "FINALIZED_ACCEPTED"
    return "FINALIZED_REJECTED_OR_CLOSED"


def build_publication_manifest(
    *,
    files_without_manifest: Mapping[str, bytes],
    public_summary: dict[str, Any],
    receipt: dict[str, Any],
    gate_report: dict[str, Any],
    receipt_verification: dict[str, Any] | None,
    protocol: dict[str, Any],
) -> dict[str, Any]:
    classifications = {
        PROTOCOL_BUNDLE_NAME: "CONTROL",
        CASE_BUNDLE_NAME: "PRIVATE",
        PRIVATE_CALCULATION_NAME: "PRIVATE",
        RECEIPT_BUNDLE_NAME: "PRIVATE",
        PUBLIC_JSON_NAME: "PUBLIC",
        PUBLIC_MARKDOWN_NAME: "PUBLIC",
    }
    expected_names = set(BUNDLE_FILE_NAMES) - {PUBLICATION_MANIFEST_NAME}
    if set(files_without_manifest) != expected_names:
        raise EconomicProtocolError("publication artifact set is not exact")
    artifacts = [
        {
            "name": name,
            "classification": classifications[name],
            "bytes": len(files_without_manifest[name]),
            "sha256": bytes_sha256(files_without_manifest[name]),
        }
        for name in sorted(files_without_manifest)
    ]
    manifest: dict[str, Any] = {
        "schema": "outage_second_publication_manifest.v1",
        "publication_id": public_summary["publication_id"],
        "bundle_mode": bundle_mode(receipt, gate_report, protocol),
        "accepted_claim_state": public_summary["accepted_claim_state"],
        "public_release_state": public_summary["public_release_state"],
        "artifacts": artifacts,
        "external_verification_artifacts": (
            copy.deepcopy(receipt_verification["external_artifact_manifest"])
            if receipt_verification is not None
            else []
        ),
        "manifest_payload_sha256": None,
    }
    manifest["manifest_payload_sha256"] = stable_sha256(manifest)
    return manifest


def _prepared_receipt_checks() -> dict[str, bool]:
    return {
        "receipt_bindings_exact": False,
        "receipt_outputs_exact": False,
        "receipt_scope_exact": False,
        "receipt_attestations_exact": False,
        "receipt_signers_verified": False,
        "receipt_independence_verified": False,
        "receipt_timestamps_valid": False,
        "receipt_decision_accepts": False,
        "receipt_signatures_verified": False,
        "receipt_release_decision_approves": False,
    }


def assemble_bundle(
    *,
    case_path: Path | None = None,
    artifact_root: Path | None = None,
    completed_receipt_path: Path | None = None,
    receipt_artifacts: Mapping[str, Mapping[str, Path]] | None = None,
    trusted_key_sha256_by_role: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    protocol, protocol_raw = load_protocol()
    if case_path is None:
        generated_case = illustrative_case(protocol)
        case_raw = json_bytes(generated_case)
        loaded_case = strict_json_loads(case_raw, label="synthetic illustrative case")
        if not isinstance(loaded_case, dict):
            raise EconomicProtocolError("synthetic case root must be an object")
        case = loaded_case
        root = validate_artifact_root(artifact_root or ROOT)
    else:
        unresolved_case = _ensure_regular_file(case_path, "case")
        resolved_case = unresolved_case.resolve(strict=True)
        case_raw = resolved_case.read_bytes()
        loaded_case = strict_json_loads(case_raw, label=str(resolved_case))
        if not isinstance(loaded_case, dict):
            raise EconomicProtocolError("case root must be an object")
        case = loaded_case
        root = validate_artifact_root(artifact_root or resolved_case.parent)
    preparation = prepare_calculation(
        case=case,
        case_raw=case_raw,
        protocol=protocol,
        protocol_raw=protocol_raw,
        artifact_root=root,
    )

    receipt_verification: dict[str, Any] | None = None
    if completed_receipt_path is None:
        receipt = preparation["bound_receipt"]
        receipt_raw = preparation["bound_receipt_raw"]
        receipt_checks = _prepared_receipt_checks()
    else:
        unresolved_receipt = _ensure_regular_file(
            completed_receipt_path, "completed receipt"
        )
        resolved_receipt = unresolved_receipt.resolve(strict=True)
        receipt_raw = resolved_receipt.read_bytes()
        loaded_receipt = strict_json_loads(receipt_raw, label=str(resolved_receipt))
        if not isinstance(loaded_receipt, dict):
            raise EconomicProtocolError("receipt root must be an object")
        receipt = loaded_receipt
        if receipt_artifacts is None or trusted_key_sha256_by_role is None:
            raise EconomicProtocolError(
                "completed receipt requires actual signer artifacts and out-of-band trusted keys"
            )
        receipt_verification = verify_completed_receipt(
            receipt,
            bound_template=preparation["bound_receipt"],
            private_payload=preparation["private_payload"],
            artifact_binding=preparation["artifact_binding"],
            protocol=protocol,
            receipt_artifacts=receipt_artifacts,
            trusted_key_sha256_by_role=trusted_key_sha256_by_role,
            now=now,
        )
        receipt_checks = receipt_verification["checks"]
    combined_receipt_report = (
        receipt_verification
        if receipt_verification is not None
        else {"checks": receipt_checks}
    )
    gate_report = build_gate_report(
        protocol=protocol,
        artifact_binding=preparation["artifact_binding"],
        receipt_verification=combined_receipt_report,
    )
    public_summary = build_public_summary(
        private_payload=preparation["private_payload"],
        private_raw=preparation["private_raw"],
        receipt_raw=receipt_raw,
        gate_report=gate_report,
        protocol=protocol,
    )
    public_json_raw = json_bytes(public_summary)
    public_markdown = render_public_markdown(public_summary)
    validate_public_redaction(
        summary=public_summary,
        markdown=public_markdown,
        private_payload=preparation["private_payload"],
    )
    public_markdown_raw = markdown_bytes(public_markdown)
    files: dict[str, bytes] = {
        PROTOCOL_BUNDLE_NAME: protocol_raw,
        CASE_BUNDLE_NAME: case_raw,
        PRIVATE_CALCULATION_NAME: preparation["private_raw"],
        RECEIPT_BUNDLE_NAME: receipt_raw,
        PUBLIC_JSON_NAME: public_json_raw,
        PUBLIC_MARKDOWN_NAME: public_markdown_raw,
    }
    manifest = build_publication_manifest(
        files_without_manifest=files,
        public_summary=public_summary,
        receipt=receipt,
        gate_report=gate_report,
        receipt_verification=receipt_verification,
        protocol=protocol,
    )
    files[PUBLICATION_MANIFEST_NAME] = json_bytes(manifest)
    return {
        "files": files,
        "protocol": protocol,
        "case": case,
        "private_payload": preparation["private_payload"],
        "receipt": receipt,
        "receipt_verification": receipt_verification,
        "gate_report": gate_report,
        "public_summary": public_summary,
        "publication_manifest": manifest,
        "artifact_root": root,
    }


def _cleanup_temporary_bundle(path: Path, known_names: set[str]) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.name not in known_names or not child.is_file() or child.is_symlink():
            raise EconomicProtocolError(
                f"refusing to clean unexpected temporary artifact: {child}"
            )
        child.unlink()
    path.rmdir()


def atomic_publish_bundle(output_dir: Path, files: Mapping[str, bytes]) -> None:
    if set(files) != set(BUNDLE_FILE_NAMES):
        raise EconomicProtocolError("atomic bundle file set is not exact")
    output_dir = output_dir.absolute()
    if os.path.lexists(output_dir):
        raise FileExistsError(f"refusing to clobber existing bundle: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    parent = output_dir.parent.resolve(strict=True)
    output_dir = parent / output_dir.name
    if os.path.lexists(output_dir):
        raise FileExistsError(f"refusing to clobber existing bundle: {output_dir}")
    temporary: Path | None = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=str(parent))
    )
    known_names = set(files)
    try:
        os.chmod(temporary, 0o700)
        for name in BUNDLE_FILE_NAMES:
            if name != Path(name).name:
                raise EconomicProtocolError(f"unsafe bundle filename: {name}")
            destination = temporary / name
            with destination.open("xb") as handle:
                handle.write(files[name])
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(destination, 0o600)
            if destination.read_bytes() != files[name]:
                raise EconomicProtocolError(f"atomic staging verification failed: {name}")
        if os.path.lexists(output_dir):
            raise FileExistsError(f"refusing to clobber existing bundle: {output_dir}")
        os.rename(temporary, output_dir)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            _cleanup_temporary_bundle(temporary, known_names)


def build_bundle(
    *,
    output_dir: Path,
    case_path: Path | None = None,
    artifact_root: Path | None = None,
    completed_receipt_path: Path | None = None,
    receipt_artifacts: Mapping[str, Mapping[str, Path]] | None = None,
    trusted_key_sha256_by_role: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    assembled = assemble_bundle(
        case_path=case_path,
        artifact_root=artifact_root,
        completed_receipt_path=completed_receipt_path,
        receipt_artifacts=receipt_artifacts,
        trusted_key_sha256_by_role=trusted_key_sha256_by_role,
        now=now,
    )
    atomic_publish_bundle(output_dir, assembled["files"])
    return assembled


def _require_bundle_directory(bundle_dir: Path) -> Path:
    if bundle_dir.is_symlink():
        raise EconomicProtocolError(f"bundle cannot be a symlink: {bundle_dir}")
    resolved = bundle_dir.resolve(strict=True)
    if not resolved.is_dir() or resolved.is_symlink():
        raise EconomicProtocolError(f"bundle is not a real directory: {bundle_dir}")
    actual = {child.name for child in resolved.iterdir()}
    expected = set(BUNDLE_FILE_NAMES)
    if actual != expected:
        raise EconomicProtocolError(
            f"bundle artifact set mismatch; missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    for name in BUNDLE_FILE_NAMES:
        _ensure_regular_file(resolved / name, f"bundle artifact {name}")
    return resolved


def _verify_self_payload_hash(
    payload: dict[str, Any], field: str, label: str
) -> None:
    stored = require_sha256(payload.get(field), f"{label}.{field}")
    unsigned = copy.deepcopy(payload)
    unsigned[field] = None
    recomputed = stable_sha256(unsigned)
    if stored != recomputed:
        raise EconomicProtocolError(f"{label} internal payload hash mismatch")


def verify_bundle(
    bundle_dir: Path,
    *,
    artifact_root: Path | None = None,
    receipt_artifacts: Mapping[str, Mapping[str, Path]] | None = None,
    trusted_key_sha256_by_role: Mapping[str, str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    bundle = _require_bundle_directory(bundle_dir)
    actual_files = {
        name: (bundle / name).read_bytes() for name in BUNDLE_FILE_NAMES
    }
    current_protocol, current_protocol_raw = load_protocol()
    if actual_files[PROTOCOL_BUNDLE_NAME] != current_protocol_raw:
        raise EconomicProtocolError(
            "bundled protocol bytes differ from the frozen executable protocol"
        )
    bundled_protocol = strict_json_loads(
        actual_files[PROTOCOL_BUNDLE_NAME], label="bundled protocol"
    )
    if not isinstance(bundled_protocol, dict):
        raise EconomicProtocolError("bundled protocol root must be an object")
    validate_protocol(bundled_protocol)
    if bundled_protocol != current_protocol:
        raise EconomicProtocolError("bundled protocol semantics differ from current protocol")

    loaded_case = strict_json_loads(actual_files[CASE_BUNDLE_NAME], label="bundled case")
    if not isinstance(loaded_case, dict):
        raise EconomicProtocolError("bundled case root must be an object")
    if loaded_case.get("case_classification") == "EXTERNAL_OPERATOR_CASE":
        if artifact_root is None:
            raise EconomicProtocolError(
                "external bundles require the original artifact root for rehashing"
            )
        root = validate_artifact_root(artifact_root)
    else:
        root = validate_artifact_root(artifact_root or ROOT)
    preparation = prepare_calculation(
        case=loaded_case,
        case_raw=actual_files[CASE_BUNDLE_NAME],
        protocol=current_protocol,
        protocol_raw=current_protocol_raw,
        artifact_root=root,
    )
    if actual_files[PRIVATE_CALCULATION_NAME] != preparation["private_raw"]:
        raise EconomicProtocolError(
            "private calculation artifact does not exactly match recomputation"
        )
    private_loaded = strict_json_loads(
        actual_files[PRIVATE_CALCULATION_NAME], label="private calculation"
    )
    if not isinstance(private_loaded, dict):
        raise EconomicProtocolError("private calculation root must be an object")
    if private_loaded != preparation["private_payload"]:
        raise EconomicProtocolError("private calculation JSON is not exact")
    _verify_self_payload_hash(
        private_loaded, "calculation_payload_sha256", "private calculation"
    )

    loaded_receipt = strict_json_loads(
        actual_files[RECEIPT_BUNDLE_NAME], label="bundled acceptance receipt"
    )
    if not isinstance(loaded_receipt, dict):
        raise EconomicProtocolError("acceptance receipt root must be an object")
    validate_receipt_shape(loaded_receipt)
    receipt_verification: dict[str, Any] | None = None
    controls = current_protocol["receipt_controls"]
    if loaded_receipt["receipt_status"] == controls["template_status"]:
        if actual_files[RECEIPT_BUNDLE_NAME] != preparation["bound_receipt_raw"]:
            raise EconomicProtocolError("unsigned bound receipt template is not exact")
        if loaded_receipt != preparation["bound_receipt"]:
            raise EconomicProtocolError("unsigned bound receipt content changed")
        receipt_report = {"checks": _prepared_receipt_checks()}
    elif loaded_receipt["receipt_status"] == controls["completed_status"]:
        if receipt_artifacts is None or trusted_key_sha256_by_role is None:
            raise EconomicProtocolError(
                "completed bundle requires actual signer artifacts and trusted key hashes"
            )
        receipt_verification = verify_completed_receipt(
            loaded_receipt,
            bound_template=preparation["bound_receipt"],
            private_payload=preparation["private_payload"],
            artifact_binding=preparation["artifact_binding"],
            protocol=current_protocol,
            receipt_artifacts=receipt_artifacts,
            trusted_key_sha256_by_role=trusted_key_sha256_by_role,
            now=now,
        )
        receipt_report = receipt_verification
    else:
        raise EconomicProtocolError("receipt status is neither bound template nor completed")

    gate_report = build_gate_report(
        protocol=current_protocol,
        artifact_binding=preparation["artifact_binding"],
        receipt_verification=receipt_report,
    )
    expected_public_summary = build_public_summary(
        private_payload=preparation["private_payload"],
        private_raw=preparation["private_raw"],
        receipt_raw=actual_files[RECEIPT_BUNDLE_NAME],
        gate_report=gate_report,
        protocol=current_protocol,
    )
    expected_public_json = json_bytes(expected_public_summary)
    if actual_files[PUBLIC_JSON_NAME] != expected_public_json:
        raise EconomicProtocolError("public JSON summary does not exactly match recomputation")
    loaded_public = strict_json_loads(
        actual_files[PUBLIC_JSON_NAME], label="public summary"
    )
    if not isinstance(loaded_public, dict) or loaded_public != expected_public_summary:
        raise EconomicProtocolError("public JSON summary schema or content changed")
    _verify_self_payload_hash(loaded_public, "summary_payload_sha256", "public summary")
    expected_markdown_text = render_public_markdown(expected_public_summary)
    validate_public_redaction(
        summary=expected_public_summary,
        markdown=expected_markdown_text,
        private_payload=preparation["private_payload"],
    )
    expected_markdown = markdown_bytes(expected_markdown_text)
    if actual_files[PUBLIC_MARKDOWN_NAME] != expected_markdown:
        raise EconomicProtocolError("public Markdown does not exactly match recomputation")

    files_without_manifest = {
        name: raw
        for name, raw in actual_files.items()
        if name != PUBLICATION_MANIFEST_NAME
    }
    expected_manifest = build_publication_manifest(
        files_without_manifest=files_without_manifest,
        public_summary=expected_public_summary,
        receipt=loaded_receipt,
        gate_report=gate_report,
        receipt_verification=receipt_verification,
        protocol=current_protocol,
    )
    expected_manifest_raw = json_bytes(expected_manifest)
    if actual_files[PUBLICATION_MANIFEST_NAME] != expected_manifest_raw:
        raise EconomicProtocolError(
            "publication manifest or an exact artifact hash is stale"
        )
    loaded_manifest = strict_json_loads(
        actual_files[PUBLICATION_MANIFEST_NAME], label="publication manifest"
    )
    if not isinstance(loaded_manifest, dict) or loaded_manifest != expected_manifest:
        raise EconomicProtocolError("publication manifest schema or content changed")
    _verify_self_payload_hash(
        loaded_manifest, "manifest_payload_sha256", "publication manifest"
    )

    return {
        "schema": "outage_second_economic_bundle_verification.v1",
        "status": "VERIFIED_FAIL_CLOSED_BUNDLE",
        "bundle_mode": expected_manifest["bundle_mode"],
        "gate_state": gate_report["state"],
        "accepted_estimated_avoided_cost_claim_allowed": gate_report["gates"][
            "accepted_estimated_avoided_cost_claim_allowed"
        ],
        "public_economic_release_allowed": gate_report["gates"][
            "public_economic_release_allowed"
        ],
        "publication_id": expected_public_summary["publication_id"],
        "private_calculation_artifact_sha256": bytes_sha256(
            actual_files[PRIVATE_CALCULATION_NAME]
        ),
        "acceptance_receipt_artifact_sha256": bytes_sha256(
            actual_files[RECEIPT_BUNDLE_NAME]
        ),
        "public_json_artifact_sha256": bytes_sha256(actual_files[PUBLIC_JSON_NAME]),
        "public_markdown_artifact_sha256": bytes_sha256(
            actual_files[PUBLIC_MARKDOWN_NAME]
        ),
        "publication_manifest_artifact_sha256": bytes_sha256(
            actual_files[PUBLICATION_MANIFEST_NAME]
        ),
        "artifact_hash_count": len(expected_manifest["artifacts"]),
        "receipt_signature_count": 2 if receipt_verification is not None else 0,
    }


def build_payload(
    case: dict[str, Any] | None = None,
    *,
    artifact_root: Path = ROOT,
    require_committed_sources: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    del require_committed_sources
    protocol, protocol_raw = load_protocol()
    active_case = case if case is not None else illustrative_case(protocol)
    case_raw = json_bytes(active_case)
    reparsed = strict_json_loads(case_raw, label="in-process case")
    if not isinstance(reparsed, dict):
        raise EconomicProtocolError("in-process case root must be an object")
    prepared = prepare_calculation(
        case=reparsed,
        case_raw=case_raw,
        protocol=protocol,
        protocol_raw=protocol_raw,
        artifact_root=validate_artifact_root(artifact_root),
    )
    return prepared["private_payload"], prepared["bound_receipt"]


def _receipt_cli_artifacts(args: argparse.Namespace) -> dict[str, dict[str, Path]] | None:
    values = {
        "economic_owner": {
            "public_key": args.economic_owner_public_key,
            "signature": args.economic_owner_signature,
            "independence": args.economic_owner_independence,
        },
        "technical_reviewer": {
            "public_key": args.technical_reviewer_public_key,
            "signature": args.technical_reviewer_signature,
            "independence": args.technical_reviewer_independence,
        },
    }
    flattened = [path for role in values.values() for path in role.values()]
    if all(path is None for path in flattened):
        return None
    if any(path is None for path in flattened):
        raise EconomicProtocolError("all six signer artifact paths are required")
    return {
        role: {name: path for name, path in paths.items() if path is not None}
        for role, paths in values.items()
    }


def _trusted_cli_hashes(args: argparse.Namespace) -> dict[str, str] | None:
    values = {
        "economic_owner": args.trusted_economic_owner_key_sha256,
        "technical_reviewer": args.trusted_technical_reviewer_key_sha256,
    }
    if all(value is None for value in values.values()):
        return None
    if any(value is None for value in values.values()):
        raise EconomicProtocolError("both out-of-band trusted key hashes are required")
    return {role: require_sha256(value, f"trusted key {role}") for role, value in values.items()}


def add_receipt_cli_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--economic-owner-public-key", type=Path)
    parser.add_argument("--economic-owner-signature", type=Path)
    parser.add_argument("--economic-owner-independence", type=Path)
    parser.add_argument("--technical-reviewer-public-key", type=Path)
    parser.add_argument("--technical-reviewer-signature", type=Path)
    parser.add_argument("--technical-reviewer-independence", type=Path)
    parser.add_argument("--trusted-economic-owner-key-sha256")
    parser.add_argument("--trusted-technical-reviewer-key-sha256")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an atomic, no-clobber outage-second economic bundle. "
            "Public economics remain redacted unless two trusted Ed25519 signatures "
            "accept the exact artifacts and approve release."
        )
    )
    parser.add_argument("--case", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check-only", action="store_true")
    add_receipt_cli_arguments(parser)
    args = parser.parse_args()
    receipt_artifacts = _receipt_cli_artifacts(args)
    trusted_hashes = _trusted_cli_hashes(args)
    if args.check_only:
        report = verify_bundle(
            args.output_dir,
            artifact_root=args.artifact_root,
            receipt_artifacts=receipt_artifacts,
            trusted_key_sha256_by_role=trusted_hashes,
        )
    else:
        assembled = build_bundle(
            output_dir=args.output_dir,
            case_path=args.case,
            artifact_root=args.artifact_root,
            completed_receipt_path=args.receipt,
            receipt_artifacts=receipt_artifacts,
            trusted_key_sha256_by_role=trusted_hashes,
        )
        report = {
            "schema": "outage_second_economic_build_result.v1",
            "status": "ATOMIC_NO_CLOBBER_BUNDLE_WRITTEN",
            "output_dir": str(args.output_dir.resolve()),
            "bundle_mode": assembled["publication_manifest"]["bundle_mode"],
            "gate_state": assembled["gate_report"]["state"],
            "accepted_estimated_avoided_cost_claim_allowed": assembled[
                "gate_report"
            ]["gates"]["accepted_estimated_avoided_cost_claim_allowed"],
            "public_economic_release_allowed": assembled["gate_report"]["gates"][
                "public_economic_release_allowed"
            ],
            "publication_id": assembled["public_summary"]["publication_id"],
            "publication_manifest_artifact_sha256": bytes_sha256(
                assembled["files"][PUBLICATION_MANIFEST_NAME]
            ),
        }
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
