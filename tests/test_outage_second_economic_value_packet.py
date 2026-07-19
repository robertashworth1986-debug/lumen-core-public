from __future__ import annotations

import copy
import importlib.util
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = (
    ROOT / "code" / "ops" / "BUILD_OUTAGE_SECOND_ECONOMIC_VALUE_PACKET.py"
)
VERIFIER_PATH = (
    ROOT / "code" / "ops" / "VERIFY_OUTAGE_SECOND_ECONOMIC_VALUE_PACKET.py"
)
SYNTHETIC_NOW = datetime(2026, 7, 18, tzinfo=timezone.utc)


def load_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def modules():
    builder = load_path(
        BUILDER_PATH, "BUILD_OUTAGE_SECOND_ECONOMIC_VALUE_PACKET"
    )
    verifier = load_path(VERIFIER_PATH, "outage_second_economic_verifier_tests")
    return builder, verifier


def write_bytes(path: Path, raw: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def write_json(path: Path, payload: dict, builder) -> Path:
    return write_bytes(path, builder.json_bytes(payload))


def synthetic_external_case(tmp_path: Path, builder) -> dict:
    protocol, protocol_raw = builder.load_protocol()
    artifact_root = tmp_path / "synthetic_artifacts"
    source_path = write_json(
        artifact_root / "inputs" / "operator_source.json",
        {
            "schema": "synthetic_operator_source.v1",
            "description": "Synthetic fixture; no private evidence.",
        },
        builder,
    )
    support_payloads = {
        "BUYER_AUTHORIZATION": (
            "support/buyer_authorization.txt",
            b"Synthetic buyer authorization fixture.\n",
            "text/plain",
        ),
        "FROZEN_INCUMBENT_BASELINE": (
            "support/frozen_baseline.json",
            builder.json_bytes(
                {
                    "schema": "synthetic_frozen_baseline.v1",
                    "baseline": "synthetic incumbent",
                }
            ),
            "application/json",
        ),
        "FROZEN_PRIMARY_METRIC": (
            "support/frozen_metric.json",
            builder.json_bytes(
                {
                    "schema": "synthetic_frozen_metric.v1",
                    "metric": "synthetic avoided outage seconds and event count",
                }
            ),
            "application/json",
        ),
        "INDEPENDENT_REPRODUCTION_RECEIPT": (
            "support/reproduction_receipt.json",
            builder.json_bytes(
                {
                    "schema": "synthetic_reproduction_receipt.v1",
                    "decision": "SYNTHETIC_REPRODUCTION_COMPLETED",
                }
            ),
            "application/json",
        ),
    }
    support_rows = []
    for role, (relative, raw, media_type) in support_payloads.items():
        path = write_bytes(artifact_root / relative, raw)
        support_rows.append(
            {
                "role": role,
                "artifact_path": relative,
                "sha256": builder.file_sha256(path),
                "media_type": media_type,
            }
        )

    case = builder.illustrative_case(protocol)
    case.update(
        {
            "case_id": "SYNTHETIC_EXTERNAL_OPERATOR_CASE",
            "case_classification": "EXTERNAL_OPERATOR_CASE",
            "protocol_sha256": builder.bytes_sha256(protocol_raw),
            "prepared_utc": "2026-07-16T00:00:00Z",
            "counterfactual_frozen_utc": "2026-07-16T00:10:00Z",
            "operating_entity": {
                "legal_name": "Synthetic Operator Incorporated",
                "organization_id": "synthetic-operator-inc",
                "economic_owner_organization": "Synthetic Operator Incorporated",
            },
            "named_system": "synthetic_payment_switch",
            "named_outage_scenario": "synthetic_30_minute_switch_outage",
            "counterfactual_baseline": "Synthetic frozen incumbent operation without the intervention.",
            "input_sources": [
                {
                    "source_id": "synthetic_operator_source",
                    "artifact_path": "inputs/operator_source.json",
                    "sha256": builder.file_sha256(source_path),
                    "media_type": "application/json",
                    "owner_organization": "Synthetic Operator Incorporated",
                    "purpose": "Synthetic economic inputs for unit testing only.",
                }
            ],
            "limitations": [
                "All evidence, identities, amounts, and signatures are synthetic fixtures.",
                "No real customer, private evidence, or economic claim is represented.",
            ],
        }
    )
    technical = {
        "schema": "outage_second_technical_evidence.v1",
        "evidence_id": "SYNTHETIC_TECHNICAL_EVIDENCE",
        "case_id": case["case_id"],
        "named_system": case["named_system"],
        "named_outage_scenario": case["named_outage_scenario"],
        "counterfactual_baseline": case["counterfactual_baseline"],
        "protocol_frozen_utc": "2026-07-16T00:20:00Z",
        "scoring_started_utc": "2026-07-16T00:30:00Z",
        "evaluation_completed_utc": "2026-07-16T01:00:00Z",
        "evaluator_name": "Synthetic Technical Reviewer",
        "evaluator_organization": "Synthetic Independent Laboratory",
        "artifacts": support_rows,
        "measured_effects": {
            scenario: {
                "annual_avoided_outage_seconds": case["scenarios"][scenario][
                    "annual_avoided_outage_seconds"
                ],
                "annual_avoided_event_count": case["scenarios"][scenario][
                    "annual_avoided_event_count"
                ],
            }
            for scenario in builder.SCENARIO_NAMES
        },
    }
    technical_path = write_json(
        artifact_root / "technical" / "evidence.json", technical, builder
    )
    case["technical_evidence"] = {
        "artifact_path": "technical/evidence.json",
        "sha256": builder.file_sha256(technical_path),
    }
    case_path = write_json(artifact_root / "case.json", case, builder)
    return {
        "artifact_root": artifact_root,
        "case_path": case_path,
        "case": case,
        "source_path": source_path,
        "technical_path": technical_path,
    }


def create_signer_material(tmp_path: Path, builder) -> dict:
    materials = {}
    for role in builder.SIGNER_ROLES:
        private_key = Ed25519PrivateKey.generate()
        public_raw = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        public_path = write_bytes(tmp_path / "signers" / f"{role}.pem", public_raw)
        independence_path = write_bytes(
            tmp_path / "signers" / f"{role}_independence.txt",
            f"Synthetic independence evidence for {role}.\n".encode("ascii"),
        )
        signature_path = tmp_path / "signers" / f"{role}.sig"
        materials[role] = {
            "private_key": private_key,
            "public_key": public_path,
            "signature": signature_path,
            "independence": independence_path,
        }
    return materials


def sign_receipt(receipt: dict, materials: dict, builder) -> None:
    for role in builder.SIGNER_ROLES:
        receipt["signatures"][role]["public_key_artifact_sha256"] = (
            builder.file_sha256(materials[role]["public_key"])
        )
        receipt["signers"][role]["independence_evidence_artifact_sha256"] = (
            builder.file_sha256(materials[role]["independence"])
        )
    signing_raw = builder.receipt_signing_bytes(receipt)
    signing_sha = builder.bytes_sha256(signing_raw)
    for role in builder.SIGNER_ROLES:
        signature = materials[role]["private_key"].sign(signing_raw)
        write_bytes(materials[role]["signature"], signature)
        receipt["signatures"][role]["signed_payload_sha256"] = signing_sha
        receipt["signatures"][role]["detached_signature_artifact_sha256"] = (
            builder.file_sha256(materials[role]["signature"])
        )


def completed_receipt(
    prep_bundle: Path,
    tmp_path: Path,
    builder,
    *,
    approve_release: bool,
) -> dict:
    receipt = builder.read_json(prep_bundle / builder.RECEIPT_BUNDLE_NAME)
    receipt.update(
        {
            "receipt_status": "COMPLETED_EXTERNAL_RECEIPT",
            "receipt_id": "SYNTHETIC_EXTERNAL_ACCEPTANCE_RECEIPT",
            "decision": "ACCEPT_ESTIMATED_AVOIDED_COST",
            "release_decision": (
                "APPROVE_PUBLIC_RELEASE" if approve_release else "WITHHOLD"
            ),
            "decision_utc": "2026-07-16T01:10:00Z",
        }
    )
    receipt["signers"]["economic_owner"] = {
        "signer_id": "synthetic-economic-owner",
        "name": "Synthetic Economic Owner",
        "role": "ECONOMIC_OWNER",
        "organization": "Synthetic Operator Incorporated",
        "independence_from_lumencore": "ATTESTED_INDEPENDENT",
        "independence_from_other_signer": "NOT_APPLICABLE",
        "independence_basis": "Synthetic operator role with no LumenCore relationship.",
        "independence_evidence_artifact_sha256": None,
        "signed_utc": "2026-07-16T01:11:00Z",
    }
    receipt["signers"]["technical_reviewer"] = {
        "signer_id": "synthetic-technical-reviewer",
        "name": "Synthetic Technical Reviewer",
        "role": "INDEPENDENT_TECHNICAL_REVIEWER",
        "organization": "Synthetic Independent Laboratory",
        "independence_from_lumencore": "ATTESTED_INDEPENDENT",
        "independence_from_other_signer": "ATTESTED_INDEPENDENT",
        "independence_basis": "Synthetic independent lab role, separate from the operator.",
        "independence_evidence_artifact_sha256": None,
        "signed_utc": "2026-07-16T01:12:00Z",
    }
    materials = create_signer_material(tmp_path, builder)
    sign_receipt(receipt, materials, builder)
    receipt_path = write_json(tmp_path / "completed_receipt.json", receipt, builder)
    artifacts = {
        role: {
            "public_key": materials[role]["public_key"],
            "signature": materials[role]["signature"],
            "independence": materials[role]["independence"],
        }
        for role in builder.SIGNER_ROLES
    }
    trusted = {
        role: builder.file_sha256(materials[role]["public_key"])
        for role in builder.SIGNER_ROLES
    }
    return {
        "receipt": receipt,
        "receipt_path": receipt_path,
        "materials": materials,
        "artifacts": artifacts,
        "trusted": trusted,
    }


def accepted_fixture(tmp_path: Path, builder, *, approve_release: bool) -> dict:
    fixture = synthetic_external_case(tmp_path, builder)
    prep_bundle = tmp_path / "prepared_bundle"
    builder.build_bundle(
        output_dir=prep_bundle,
        case_path=fixture["case_path"],
        artifact_root=fixture["artifact_root"],
    )
    signed = completed_receipt(
        prep_bundle,
        tmp_path,
        builder,
        approve_release=approve_release,
    )
    final_bundle = tmp_path / "final_bundle"
    assembled = builder.build_bundle(
        output_dir=final_bundle,
        case_path=fixture["case_path"],
        artifact_root=fixture["artifact_root"],
        completed_receipt_path=signed["receipt_path"],
        receipt_artifacts=signed["artifacts"],
        trusted_key_sha256_by_role=signed["trusted"],
        now=SYNTHETIC_NOW,
    )
    return {
        **fixture,
        **signed,
        "prep_bundle": prep_bundle,
        "final_bundle": final_bundle,
        "assembled": assembled,
    }


def test_unsigned_bundle_is_private_redacted_recomputed_and_no_clobber(
    tmp_path: Path, modules
):
    builder, verifier = modules
    bundle = tmp_path / "unsigned_bundle"
    built = builder.build_bundle(output_dir=bundle)
    report = verifier.verify_packet(bundle)

    public = builder.read_json(bundle / builder.PUBLIC_JSON_NAME)
    private = builder.read_json(bundle / builder.PRIVATE_CALCULATION_NAME)
    markdown = (bundle / builder.PUBLIC_MARKDOWN_NAME).read_text(encoding="utf-8")
    protocol, _ = builder.load_protocol()

    assert report["accepted_estimated_avoided_cost_claim_allowed"] is False
    assert report["public_economic_release_allowed"] is False
    assert report["receipt_signature_count"] == 0
    assert public["scope"] is None
    assert public["scenario_outputs"] is None
    assert private["scenario_outputs"]["base"]["estimated_annual_avoided_cost_usd"]
    assert "$" not in markdown
    assert "Synthetic Example Entity" not in markdown
    assert protocol["release_control"]["default_public_release"] is False
    assert built["publication_manifest"]["artifacts"]
    with pytest.raises(FileExistsError, match="clobber"):
        builder.build_bundle(output_dir=bundle)


def test_fixed_event_cost_uses_avoided_event_count_not_avoided_seconds(modules):
    builder, _ = modules
    protocol, _ = builder.load_protocol()
    row = {
        field: 0 for field in protocol["scenario_fields"]
    }
    row.update(
        {
            "reporting_period_seconds": 1,
            "outage_duration_seconds": 10,
            "fixed_incremental_costs_per_event_usd": 100,
            "annual_avoided_outage_seconds": 999,
            "annual_avoided_event_count": 3,
            "attribution_fraction": 1,
            "confidence_factor": 1,
        }
    )
    outputs = builder.calculate_scenario(row, protocol)

    assert outputs["net_time_flow_cost_per_second_usd"] == "0.000000"
    assert outputs["incremental_outage_cost_per_event_usd"] == "100.000000"
    assert outputs["annual_avoided_time_flow_cost_usd"] == "0.000000"
    assert outputs["annual_avoided_fixed_event_cost_usd"] == "300.000000"
    assert outputs["estimated_annual_avoided_cost_usd"] == "300.000000"


def test_protocol_formula_plan_is_executed_from_config(modules):
    builder, _ = modules
    protocol, _ = builder.load_protocol()
    row = {field: 0 for field in protocol["scenario_fields"]}
    row.update(
        {
            "reporting_period_seconds": 1,
            "outage_duration_seconds": 1,
            "fixed_incremental_costs_per_event_usd": 100,
            "annual_avoided_event_count": 3,
            "attribution_fraction": 1,
            "confidence_factor": 1,
        }
    )
    original = builder.calculate_scenario(row, protocol)
    changed = copy.deepcopy(protocol)
    step = next(
        item
        for item in changed["calculation_steps"]
        if item["output"] == "annual_avoided_fixed_event_cost_usd"
    )
    step["operation"] = "add"
    builder.validate_protocol(changed)
    altered = builder.calculate_scenario(row, changed)

    assert original["annual_avoided_fixed_event_cost_usd"] == "300.000000"
    assert altered["annual_avoided_fixed_event_cost_usd"] == "103.000000"


def test_v1_rejects_other_perspectives_bool_magnitude_and_extra_fields(modules):
    builder, _ = modules
    protocol, protocol_raw = builder.load_protocol()

    perspective = builder.illustrative_case(protocol)
    perspective["valuation_perspective"] = "FEDERAL_SOCIAL_BENEFIT_COST"
    with pytest.raises(builder.EconomicProtocolError, match="non-private"):
        builder.validate_case(
            perspective,
            protocol,
            protocol_sha256=builder.bytes_sha256(protocol_raw),
        )

    bool_case = builder.illustrative_case(protocol)
    bool_case["scenarios"]["low"]["annual_revenue_usd"] = True
    with pytest.raises(builder.EconomicProtocolError, match="not bool"):
        builder.validate_case(
            bool_case, protocol, protocol_sha256=builder.bytes_sha256(protocol_raw)
        )

    magnitude = builder.illustrative_case(protocol)
    magnitude["scenarios"]["low"]["annual_revenue_usd"] = 10**20
    with pytest.raises(builder.EconomicProtocolError, match="exceeds"):
        builder.validate_case(
            magnitude, protocol, protocol_sha256=builder.bytes_sha256(protocol_raw)
        )

    extra = builder.illustrative_case(protocol)
    extra["economic_owner_signed"] = True
    with pytest.raises(builder.EconomicProtocolError, match="schema mismatch"):
        builder.validate_case(
            extra, protocol, protocol_sha256=builder.bytes_sha256(protocol_raw)
        )


@pytest.mark.parametrize(
    "raw,match",
    [
        (b'{"x":1,"x":2}', "duplicate"),
        (b'{"x":NaN}', "non-finite"),
        (b'{"x":Infinity}', "non-finite"),
        (b'{"x":1e31}', "magnitude"),
    ],
)
def test_strict_json_rejects_duplicate_nonfinite_and_excessive_numbers(
    raw: bytes, match: str, modules
):
    builder, _ = modules
    with pytest.raises(builder.EconomicProtocolError, match=match):
        builder.strict_json_loads(raw, label="synthetic attack")


def test_hash_shaped_source_claim_is_recomputed_and_fails_closed(
    tmp_path: Path, modules
):
    builder, _ = modules
    fixture = synthetic_external_case(tmp_path, builder)
    case = builder.read_json(fixture["case_path"])
    case["input_sources"][0]["sha256"] = "a" * 64
    write_json(fixture["case_path"], case, builder)

    with pytest.raises(builder.EconomicProtocolError, match="SHA-256 mismatch"):
        builder.assemble_bundle(
            case_path=fixture["case_path"],
            artifact_root=fixture["artifact_root"],
        )


def test_json_source_is_strictly_parsed_after_its_hash_is_recomputed(
    tmp_path: Path, modules
):
    builder, _ = modules
    fixture = synthetic_external_case(tmp_path, builder)
    duplicate_raw = b'{"schema":"synthetic","schema":"duplicate"}\n'
    fixture["source_path"].write_bytes(duplicate_raw)
    case = builder.read_json(fixture["case_path"])
    case["input_sources"][0]["sha256"] = builder.file_sha256(
        fixture["source_path"]
    )
    write_json(fixture["case_path"], case, builder)

    with pytest.raises(builder.EconomicProtocolError, match="duplicate"):
        builder.assemble_bundle(
            case_path=fixture["case_path"],
            artifact_root=fixture["artifact_root"],
        )


def test_two_valid_external_signatures_accept_but_withhold_by_default(
    tmp_path: Path, modules
):
    builder, verifier = modules
    fixture = accepted_fixture(tmp_path, builder, approve_release=False)
    report = verifier.verify_packet(
        fixture["final_bundle"],
        artifact_root=fixture["artifact_root"],
        receipt_artifacts=fixture["artifacts"],
        trusted_key_sha256_by_role=fixture["trusted"],
        now=SYNTHETIC_NOW,
    )
    public = builder.read_json(fixture["final_bundle"] / builder.PUBLIC_JSON_NAME)
    markdown = (
        fixture["final_bundle"] / builder.PUBLIC_MARKDOWN_NAME
    ).read_text(encoding="utf-8")
    manifest = builder.read_json(
        fixture["final_bundle"] / builder.PUBLICATION_MANIFEST_NAME
    )

    assert report["accepted_estimated_avoided_cost_claim_allowed"] is True
    assert report["public_economic_release_allowed"] is False
    assert report["receipt_signature_count"] == 2
    assert public["status"] == "ACCEPTED_PRIVATE_ECONOMICS_WITHHELD"
    assert public["scope"] is None
    assert public["scenario_outputs"] is None
    assert "$" not in markdown
    assert len(manifest["external_verification_artifacts"]) == 6


def test_signed_public_release_publishes_only_exact_accepted_outputs(
    tmp_path: Path, modules
):
    builder, verifier = modules
    fixture = accepted_fixture(tmp_path, builder, approve_release=True)
    report = verifier.verify_packet(
        fixture["final_bundle"],
        artifact_root=fixture["artifact_root"],
        receipt_artifacts=fixture["artifacts"],
        trusted_key_sha256_by_role=fixture["trusted"],
        now=SYNTHETIC_NOW,
    )
    public = builder.read_json(fixture["final_bundle"] / builder.PUBLIC_JSON_NAME)
    private = builder.read_json(
        fixture["final_bundle"] / builder.PRIVATE_CALCULATION_NAME
    )
    markdown = (
        fixture["final_bundle"] / builder.PUBLIC_MARKDOWN_NAME
    ).read_text(encoding="utf-8")

    assert report["accepted_estimated_avoided_cost_claim_allowed"] is True
    assert report["public_economic_release_allowed"] is True
    assert public["scope"] == private["scope"]
    assert public["scenario_outputs"] == private["scenario_outputs"]
    assert "$" in markdown


def test_signature_hash_match_without_valid_signature_fails_closed(
    tmp_path: Path, modules
):
    builder, _ = modules
    fixture = synthetic_external_case(tmp_path, builder)
    prep = tmp_path / "prepared"
    builder.build_bundle(
        output_dir=prep,
        case_path=fixture["case_path"],
        artifact_root=fixture["artifact_root"],
    )
    signed = completed_receipt(prep, tmp_path, builder, approve_release=False)
    role = "economic_owner"
    signature_path = signed["materials"][role]["signature"]
    tampered = bytearray(signature_path.read_bytes())
    tampered[0] ^= 1
    signature_path.write_bytes(bytes(tampered))
    receipt = builder.read_json(signed["receipt_path"])
    receipt["signatures"][role]["detached_signature_artifact_sha256"] = (
        builder.file_sha256(signature_path)
    )
    write_json(signed["receipt_path"], receipt, builder)

    with pytest.raises(builder.EconomicProtocolError, match="cryptographically invalid"):
        builder.assemble_bundle(
            case_path=fixture["case_path"],
            artifact_root=fixture["artifact_root"],
            completed_receipt_path=signed["receipt_path"],
            receipt_artifacts=signed["artifacts"],
            trusted_key_sha256_by_role=signed["trusted"],
            now=SYNTHETIC_NOW,
        )


def test_hash_shaped_but_untrusted_public_key_fails_closed(tmp_path: Path, modules):
    builder, _ = modules
    fixture = synthetic_external_case(tmp_path, builder)
    prep = tmp_path / "prepared"
    builder.build_bundle(
        output_dir=prep,
        case_path=fixture["case_path"],
        artifact_root=fixture["artifact_root"],
    )
    signed = completed_receipt(prep, tmp_path, builder, approve_release=False)
    untrusted = dict(signed["trusted"])
    untrusted["economic_owner"] = "a" * 64

    with pytest.raises(builder.EconomicProtocolError, match="out-of-band trusted"):
        builder.assemble_bundle(
            case_path=fixture["case_path"],
            artifact_root=fixture["artifact_root"],
            completed_receipt_path=signed["receipt_path"],
            receipt_artifacts=signed["artifacts"],
            trusted_key_sha256_by_role=untrusted,
            now=SYNTHETIC_NOW,
        )


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("output", "accepted outputs"),
        ("scope", "accepted scope"),
        ("independence", "independence"),
        ("timestamp", "timestamp"),
    ],
)
def test_exact_outputs_scope_independence_and_timestamps_are_enforced(
    tmp_path: Path, modules, mutation: str, match: str
):
    builder, _ = modules
    fixture = synthetic_external_case(tmp_path, builder)
    prep = tmp_path / "prepared"
    builder.build_bundle(
        output_dir=prep,
        case_path=fixture["case_path"],
        artifact_root=fixture["artifact_root"],
    )
    signed = completed_receipt(prep, tmp_path, builder, approve_release=False)
    receipt = builder.read_json(signed["receipt_path"])
    if mutation == "output":
        receipt["accepted_outputs"]["base"]["estimated_annual_avoided_cost_usd"] = (
            "999.000000"
        )
    elif mutation == "scope":
        receipt["accepted_scope"]["named_system"] = "different_system"
    elif mutation == "independence":
        receipt["signers"]["technical_reviewer"][
            "independence_from_other_signer"
        ] = "NOT_APPLICABLE"
    else:
        receipt["signers"]["technical_reviewer"]["signed_utc"] = (
            "2026-07-18T01:12:00Z"
        )
    if mutation in {"independence", "timestamp"}:
        sign_receipt(receipt, signed["materials"], builder)
    write_json(signed["receipt_path"], receipt, builder)

    with pytest.raises(builder.EconomicProtocolError, match=match):
        builder.assemble_bundle(
            case_path=fixture["case_path"],
            artifact_root=fixture["artifact_root"],
            completed_receipt_path=signed["receipt_path"],
            receipt_artifacts=signed["artifacts"],
            trusted_key_sha256_by_role=signed["trusted"],
            now=SYNTHETIC_NOW,
        )


@pytest.mark.parametrize(
    "artifact_name",
    [
        "protocol.json",
        "case.json",
        "private_calculation.json",
        "acceptance_receipt.json",
        "public_summary.json",
        "public_summary.md",
        "publication_manifest.json",
    ],
)
def test_every_bundle_artifact_is_exactly_hashed_and_reconstructed(
    tmp_path: Path, modules, artifact_name: str
):
    builder, verifier = modules
    bundle = tmp_path / "bundle"
    builder.build_bundle(output_dir=bundle)
    path = bundle / artifact_name
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(builder.EconomicProtocolError):
        verifier.verify_packet(bundle)


def test_rejected_signed_decision_cannot_open_claim_or_release_gates(
    tmp_path: Path, modules
):
    builder, verifier = modules
    fixture = synthetic_external_case(tmp_path, builder)
    prep = tmp_path / "prepared"
    builder.build_bundle(
        output_dir=prep,
        case_path=fixture["case_path"],
        artifact_root=fixture["artifact_root"],
    )
    signed = completed_receipt(prep, tmp_path, builder, approve_release=False)
    receipt = builder.read_json(signed["receipt_path"])
    receipt["decision"] = "REJECT_ECONOMIC_CONVERSION"
    sign_receipt(receipt, signed["materials"], builder)
    write_json(signed["receipt_path"], receipt, builder)
    bundle = tmp_path / "rejected"
    builder.build_bundle(
        output_dir=bundle,
        case_path=fixture["case_path"],
        artifact_root=fixture["artifact_root"],
        completed_receipt_path=signed["receipt_path"],
        receipt_artifacts=signed["artifacts"],
        trusted_key_sha256_by_role=signed["trusted"],
        now=SYNTHETIC_NOW,
    )
    report = verifier.verify_packet(
        bundle,
        artifact_root=fixture["artifact_root"],
        receipt_artifacts=signed["artifacts"],
        trusted_key_sha256_by_role=signed["trusted"],
        now=SYNTHETIC_NOW,
    )
    public = builder.read_json(bundle / builder.PUBLIC_JSON_NAME)

    assert report["accepted_estimated_avoided_cost_claim_allowed"] is False
    assert report["public_economic_release_allowed"] is False
    assert public["scenario_outputs"] is None
