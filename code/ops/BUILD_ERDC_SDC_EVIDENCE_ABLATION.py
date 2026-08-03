from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "out" / "ops" / "erdc_sdc_evidence_ablation_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "erdc_sdc_evidence_ablation.json"
OUT_MD = ROOT / "docs" / "ERDC_SDC_EVIDENCE_ABLATION_2026-07-29.md"

SCHEMA = "lumencore.erdc_sdc_evidence_ablation.v2"
PROTOCOL_ID = "ERDC-SDC-EVIDENCE-ABLATION-V2"
WORKFLOW_COUNT = 48
GENESIS = "0" * 64

BASELINE_SOURCES = [
    {
        "id": "opentelemetry_logs_1_59",
        "name": "OpenTelemetry Logs Data Model 1.59.0",
        "version": "1.59.0",
        "official_url": "https://opentelemetry.io/docs/specs/otel/logs/data-model/",
        "comparison_role": "INTEROPERABILITY_CONTEXT_NOT_RANKED",
        "purpose_boundary": (
            "A stable vendor-neutral log-record data model. It is treated as a "
            "complementary event interchange context, not an integrity or runtime "
            "promotion-control baseline."
        ),
    },
    {
        "id": "slsa_build_provenance_1_2",
        "name": "SLSA Build Provenance 1.2 with in-toto Statement v1",
        "version": "1.2",
        "official_url": "https://slsa.dev/spec/v1.2/build-provenance",
        "comparison_role": "INTEROPERABILITY_CONTEXT_NOT_RANKED",
        "purpose_boundary": (
            "An approved artifact build-provenance model. It is treated as a "
            "complementary provenance context, not a runtime workflow ledger or "
            "promotion-control baseline."
        ),
    },
]

TRUST_MODEL = (
    "The local verifier receives a trusted-anchor object generated before attack "
    "mutation and separately from the mutable receipt. The anchor pins the protocol, "
    "source-population counts, profile counts, terminal chain root, and predeclared "
    "gate hash. This models a separately pinned local input only. It is not an "
    "external signature, independent timestamp, tamper-proof store, production trust "
    "root, or Government validation. Phase II must bind the anchor outside the mutable "
    "receipt through a Government-approved signing or custody mechanism."
)

CLAIM_BOUNDARY = (
    "This is a deterministic synthetic, unclassified workflow-control ablation. It "
    "compares the complete LumenCore control profile only with its own no-chain, "
    "no-predeclaration, and no-failure-retention ablations. OpenTelemetry and SLSA are "
    "listed only as complementary interoperability contexts and are not ranked or "
    "attacked. The result is not an HPCMP workload, Government test, independent "
    "validation, security assessment, cost study, production benchmark, or proof of "
    "superiority. The local anchor is not an external trust root."
)

Verifier = Callable[[dict[str, Any]], dict[str, Any]]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def synthetic_workflows() -> list[dict[str, Any]]:
    outcomes = (
        "PASS",
        "PASS",
        "PASS",
        "FAIL",
        "POLICY_DENIED",
        "MISSING_INPUT",
        "ABSTAIN",
        "MANUAL_OVERRIDE",
    )
    rows: list[dict[str, Any]] = []
    for index in range(WORKFLOW_COUNT):
        outcome = outcomes[index % len(outcomes)]
        adapter = "kubernetes-surrogate" if index % 2 == 0 else "slurm-surrogate"
        request_id = f"request-{index:03d}"
        artifact_bytes = f"{request_id}|{adapter}|artifact|{index % 7}".encode(
            "utf-8"
        )
        has_artifact = outcome not in {
            "MISSING_INPUT",
            "POLICY_DENIED",
            "ABSTAIN",
        }
        rows.append(
            {
                "sequence": index + 1,
                "request_id": request_id,
                "adapter": adapter,
                "workflow_class": (
                    "ai-training-surrogate"
                    if index % 3 == 0
                    else "simulation-surrogate"
                ),
                "policy_id": "sdc-unclassified-shadow-v1",
                "policy_version": "1.0.0",
                "decision": (
                    "DENY"
                    if outcome == "POLICY_DENIED"
                    else "REVIEW"
                    if outcome in {"ABSTAIN", "MANUAL_OVERRIDE"}
                    else "ALLOW"
                ),
                "outcome": outcome,
                "input_digest": sha256_bytes(f"input-{index % 11}".encode("utf-8")),
                "artifact_digest": (
                    sha256_bytes(artifact_bytes) if has_artifact else ""
                ),
                "artifact_payload_hex": (
                    artifact_bytes.hex() if has_artifact else ""
                ),
                "manual_override": outcome == "MANUAL_OVERRIDE",
                "event_time_utc": f"2026-07-29T00:{index:02d}:00Z",
            }
        )
    return rows


def protocol() -> dict[str, Any]:
    return {
        "protocol_id": PROTOCOL_ID,
        "workflow_profile": (
            "Fixed unclassified HPC workflow surrogate with Kubernetes-like and "
            "Slurm-like adapters; no Government systems or data."
        ),
        "workflow_count": WORKFLOW_COUNT,
        "comparison_scope": (
            "LumenCore complete control profile versus LumenCore control ablations "
            "only; named standards are unranked interoperability contexts."
        ),
        "adverse_outcomes": [
            "FAIL",
            "POLICY_DENIED",
            "MISSING_INPUT",
            "ABSTAIN",
            "MANUAL_OVERRIDE",
        ],
        "predeclared_gates": {
            "all_artifacts_rehash": True,
            "all_events_chain_verify": True,
            "adverse_outcome_recall": 1.0,
            "manual_override_visible": True,
            "promotion_allowed_only_when_all_required_gates_pass": True,
        },
        "attacks": [
            "mutate_policy_decision",
            "delete_adverse_event",
            "reorder_events",
            "mutate_artifact_digest",
            "posthoc_gate_change",
            "adaptive_delete_rechain_and_reseal",
            "adaptive_policy_rechain_and_reseal",
        ],
        "metrics": [
            "control_attack_detection_rate",
            "adverse_outcome_recall",
            "artifact_bytes_rehash_rate",
            "predeclared_gate_hash_present",
            "predeclared_gate_execution_pass",
            "posthoc_promotion_change_detected",
            "serialized_bytes",
        ],
        "trusted_anchor_model": TRUST_MODEL,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def adverse_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if row["outcome"] != "PASS")


def artifact_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if row["artifact_digest"])


def manual_override_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for row in rows if row["manual_override"])


def build_otel_profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    records = []
    for row in rows:
        records.append(
            {
                "Timestamp": row["event_time_utc"],
                "SeverityText": "ERROR" if row["outcome"] == "FAIL" else "INFO",
                "Body": {
                    "request_id": row["request_id"],
                    "outcome": row["outcome"],
                    "decision": row["decision"],
                },
                "Resource": {"service.name": "sdc-workflow-surrogate"},
                "Attributes": {
                    "adapter": row["adapter"],
                    "workflow_class": row["workflow_class"],
                    "policy.id": row["policy_id"],
                    "policy.version": row["policy_version"],
                    "artifact.sha256": row["artifact_digest"],
                    "manual_override": row["manual_override"],
                },
                "EventName": "hpc.workflow.decision",
            }
        )
    return {
        "profile": "OpenTelemetry Logs Data Model 1.59.0 bounded JSON profile",
        "records": records,
    }


def verify_otel_profile(profile: dict[str, Any]) -> dict[str, Any]:
    records = profile.get("records", [])
    return {
        "structurally_valid": isinstance(records, list) and bool(records),
        "record_count": len(records),
        "artifact_digest_field_count": sum(
            1
            for record in records
            if record.get("Attributes", {}).get("artifact.sha256")
        ),
    }


def build_slsa_profile(rows: list[dict[str, Any]]) -> dict[str, Any]:
    statements = []
    for row in rows:
        if not row["artifact_digest"]:
            continue
        statements.append(
            {
                "_type": "https://in-toto.io/Statement/v1",
                "subject": [
                    {
                        "name": row["request_id"],
                        "digest": {"sha256": row["artifact_digest"]},
                    }
                ],
                "predicateType": "https://slsa.dev/provenance/v1",
                "predicate": {
                    "buildDefinition": {
                        "buildType": "https://lumen-core.ai/surrogate/hpc-workflow/v1",
                        "externalParameters": {
                            "adapter": row["adapter"],
                            "workflowClass": row["workflow_class"],
                        },
                        "internalParameters": {},
                        "resolvedDependencies": [
                            {
                                "uri": f"urn:surrogate:{row['request_id']}:input",
                                "digest": {"sha256": row["input_digest"]},
                            }
                        ],
                    },
                    "runDetails": {
                        "builder": {
                            "id": "https://lumen-core.ai/surrogate-builder/v1"
                        },
                        "metadata": {
                            "invocationId": row["request_id"],
                            "startedOn": row["event_time_utc"],
                            "finishedOn": row["event_time_utc"],
                        },
                        "byproducts": [],
                    },
                },
            }
        )
    return {
        "profile": "SLSA Build Provenance 1.2 / in-toto Statement v1 bounded profile",
        "statements": statements,
    }


def verify_slsa_profile(profile: dict[str, Any]) -> dict[str, Any]:
    statements = profile.get("statements", [])
    valid = all(
        statement.get("_type") == "https://in-toto.io/Statement/v1"
        and statement.get("predicateType") == "https://slsa.dev/provenance/v1"
        and bool(statement.get("subject"))
        for statement in statements
    )
    return {
        "structurally_valid": bool(statements) and valid,
        "statement_count": len(statements),
        "artifact_digest_field_count": sum(
            1
            for statement in statements
            if statement.get("subject", [{}])[0].get("digest", {}).get("sha256")
        ),
    }


def context_profile_result(
    profile_id: str,
    name: str,
    profile: dict[str, Any],
    verifier: Verifier,
) -> dict[str, Any]:
    verification = verifier(profile)
    return {
        "profile_id": profile_id,
        "name": name,
        "comparison_role": "INTEROPERABILITY_CONTEXT_NOT_RANKED",
        "profile_sha256": stable_hash(profile),
        "serialized_bytes": len(canonical_json(profile).encode("utf-8")),
        "verification": verification,
        "attack_comparison_performed": False,
    }


def chained_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    previous = GENESIS
    for row in rows:
        body = {**row, "prev_hash": previous}
        event_hash = stable_hash(body)
        output.append({**body, "event_hash": event_hash})
        previous = event_hash
    return output


def build_lumencore_profile(
    rows: list[dict[str, Any]],
    *,
    include_chain: bool = True,
    include_predeclared_gates: bool = True,
    retain_failures: bool = True,
) -> dict[str, Any]:
    retained = (
        rows
        if retain_failures
        else [row for row in rows if row["outcome"] == "PASS"]
    )
    events = chained_events(retained) if include_chain else copy.deepcopy(retained)
    declared = protocol()["predeclared_gates"] if include_predeclared_gates else {}
    profile = {
        "profile": "LumenCore Evidence Receipt v2",
        "protocol_id": PROTOCOL_ID,
        "protocol_sha256": stable_hash(protocol()),
        "predeclared_gates": declared,
        "predeclared_gates_sha256": stable_hash(declared) if declared else "",
        "events": events,
        "terminal_chain_hash": (
            events[-1]["event_hash"] if include_chain and events else ""
        ),
        "expected_event_count": len(retained),
        "expected_adverse_count": adverse_count(retained),
        "expected_artifact_count": artifact_count(retained),
        "expected_manual_override_count": manual_override_count(retained),
        "decision": "HOLD",
        "configuration": {
            "include_chain": include_chain,
            "include_predeclared_gates": include_predeclared_gates,
            "retain_failures": retain_failures,
        },
    }
    profile["receipt_sha256"] = stable_hash(profile)
    return profile


def build_trusted_anchor(
    profile: dict[str, Any],
    source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor = {
        "anchor_model": "SEPARATELY_PINNED_LOCAL_INPUT_NOT_EXTERNAL_TRUST_ROOT",
        "protocol_id": profile["protocol_id"],
        "protocol_sha256": profile["protocol_sha256"],
        "source_workflow_count": len(source_rows),
        "source_expected_adverse_count": adverse_count(source_rows),
        "source_expected_artifact_count": artifact_count(source_rows),
        "source_expected_manual_override_count": manual_override_count(source_rows),
        "profile_expected_event_count": profile["expected_event_count"],
        "profile_expected_adverse_count": profile["expected_adverse_count"],
        "profile_expected_artifact_count": profile["expected_artifact_count"],
        "profile_expected_manual_override_count": profile[
            "expected_manual_override_count"
        ],
        "terminal_chain_hash": profile["terminal_chain_hash"],
        "predeclared_gates_sha256": profile["predeclared_gates_sha256"],
    }
    anchor["anchor_sha256"] = stable_hash(anchor)
    return anchor


def verify_lumencore_profile(
    profile: dict[str, Any],
    trusted_anchor: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    anchor_payload = copy.deepcopy(trusted_anchor)
    observed_anchor_sha = anchor_payload.pop("anchor_sha256", "")
    if observed_anchor_sha != stable_hash(anchor_payload):
        errors.append("trusted_anchor_hash_mismatch")

    anchor_comparisons = {
        "protocol_id": "protocol_id_anchor_mismatch",
        "protocol_sha256": "protocol_hash_anchor_mismatch",
        "expected_event_count": "event_count_anchor_mismatch",
        "expected_adverse_count": "adverse_count_anchor_mismatch",
        "expected_artifact_count": "artifact_count_anchor_mismatch",
        "expected_manual_override_count": "manual_override_count_anchor_mismatch",
        "terminal_chain_hash": "terminal_chain_anchor_mismatch",
        "predeclared_gates_sha256": "predeclared_gate_anchor_mismatch",
    }
    anchor_keys = {
        "expected_event_count": "profile_expected_event_count",
        "expected_adverse_count": "profile_expected_adverse_count",
        "expected_artifact_count": "profile_expected_artifact_count",
        "expected_manual_override_count": "profile_expected_manual_override_count",
    }
    for profile_key, error in anchor_comparisons.items():
        anchor_key = anchor_keys.get(profile_key, profile_key)
        if profile.get(profile_key) != trusted_anchor.get(anchor_key):
            errors.append(error)

    receipt_sha = profile.get("receipt_sha256", "")
    receipt_payload = copy.deepcopy(profile)
    receipt_payload.pop("receipt_sha256", None)
    if receipt_sha != stable_hash(receipt_payload):
        errors.append("receipt_hash_mismatch")

    events = profile.get("events", [])
    config = profile.get("configuration", {})
    chain_errors: list[str] = []
    if config.get("include_chain"):
        previous = GENESIS
        for event in events:
            event_payload = copy.deepcopy(event)
            observed_hash = event_payload.pop("event_hash", "")
            if event_payload.get("prev_hash") != previous:
                chain_errors.append("chain_previous_hash_mismatch")
                break
            expected_hash = stable_hash(event_payload)
            if observed_hash != expected_hash:
                chain_errors.append("event_hash_mismatch")
                break
            previous = observed_hash
        if profile.get("terminal_chain_hash") != previous:
            chain_errors.append("terminal_chain_hash_mismatch")
    errors.extend(chain_errors)
    chain_verified = (
        config.get("include_chain") is True
        and bool(events)
        and not chain_errors
    )

    if len(events) != profile.get("expected_event_count"):
        errors.append("event_count_mismatch")
    adverse_observed = sum(
        1 for event in events if event.get("outcome") not in {"", "PASS"}
    )
    if adverse_observed != profile.get("expected_adverse_count"):
        errors.append("adverse_outcome_count_mismatch")
    manual_observed = sum(1 for event in events if event.get("manual_override"))
    if manual_observed != profile.get("expected_manual_override_count"):
        errors.append("manual_override_count_mismatch")

    artifact_observed = 0
    artifact_rehashed = 0
    for event in events:
        digest = event.get("artifact_digest", "")
        if not digest:
            continue
        artifact_observed += 1
        payload_hex = event.get("artifact_payload_hex", "")
        try:
            artifact_bytes = bytes.fromhex(payload_hex)
        except (TypeError, ValueError):
            errors.append("artifact_payload_decode_failure")
            continue
        if sha256_bytes(artifact_bytes) != digest:
            errors.append("artifact_digest_rehash_mismatch")
            continue
        artifact_rehashed += 1
    if artifact_observed != profile.get("expected_artifact_count"):
        errors.append("artifact_count_mismatch")

    declared = profile.get("predeclared_gates", {})
    declared_hash = profile.get("predeclared_gates_sha256", "")
    gate_hash_valid = False
    if config.get("include_predeclared_gates"):
        gate_hash_valid = declared_hash == stable_hash(declared)
        if not gate_hash_valid:
            errors.append("predeclared_gate_hash_mismatch")

    source_adverse = trusted_anchor.get("source_expected_adverse_count", 0)
    source_artifacts = trusted_anchor.get("source_expected_artifact_count", 0)
    source_manual = trusted_anchor.get("source_expected_manual_override_count", 0)
    adverse_recall = adverse_observed / source_adverse if source_adverse else 1.0
    artifact_rehash_rate = (
        artifact_rehashed / source_artifacts if source_artifacts else 1.0
    )
    manual_visibility = manual_observed == source_manual
    gate_execution_pass = (
        config.get("include_predeclared_gates") is True
        and gate_hash_valid
        and (
            not declared.get("all_events_chain_verify")
            or chain_verified
        )
        and (
            not declared.get("all_artifacts_rehash")
            or artifact_rehashed == artifact_observed
        )
        and adverse_recall >= float(declared.get("adverse_outcome_recall", 0.0))
        and (
            not declared.get("manual_override_visible")
            or manual_visibility
        )
    )
    if (
        profile.get("decision") == "PROMOTE"
        and (
            not gate_execution_pass
            or adverse_observed > 0
        )
    ):
        errors.append("promotion_without_passing_required_gates")

    return {
        "structurally_valid": not errors,
        "errors": sorted(set(errors)),
        "adverse_outcomes_present": adverse_observed,
        "artifact_digest_fields_present": artifact_observed,
        "artifact_bytes_rehashed": artifact_rehashed,
        "manual_overrides_present": manual_observed,
        "integrity_root_present": bool(profile.get("terminal_chain_hash")),
        "chain_verified": chain_verified,
        "predeclared_gate_hash_present": bool(declared_hash),
        "predeclared_gate_hash_valid": gate_hash_valid,
        "predeclared_gate_execution_pass": gate_execution_pass,
        "adverse_outcome_recall": round(adverse_recall, 6),
        "artifact_bytes_rehash_rate": round(artifact_rehash_rate, 6),
        "manual_override_visibility_pass": manual_visibility,
    }


def reseal_outer_receipt(profile: dict[str, Any]) -> dict[str, Any]:
    receipt_payload = copy.deepcopy(profile)
    receipt_payload.pop("receipt_sha256", None)
    profile["receipt_sha256"] = stable_hash(receipt_payload)
    return profile


def mutate_policy_decision(profile: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(profile)
    target = next(
        (
            event
            for event in mutated.get("events", [])
            if event.get("decision") != "ALLOW"
        ),
        None,
    )
    if target is not None:
        target["decision"] = "ALLOW"
    return reseal_outer_receipt(mutated)


def delete_adverse_event(profile: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(profile)
    for index, event in enumerate(mutated.get("events", [])):
        if event.get("outcome") != "PASS":
            del mutated["events"][index]
            break
    return reseal_outer_receipt(mutated)


def reorder_events(profile: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(profile)
    if len(mutated.get("events", [])) >= 3:
        mutated["events"][1], mutated["events"][2] = (
            mutated["events"][2],
            mutated["events"][1],
        )
    return reseal_outer_receipt(mutated)


def mutate_artifact_digest(profile: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(profile)
    target = next(
        (
            event
            for event in mutated.get("events", [])
            if event.get("artifact_digest")
        ),
        None,
    )
    if target is not None:
        target["artifact_digest"] = "f" * 64
    return reseal_outer_receipt(mutated)


def posthoc_gate_change(profile: dict[str, Any]) -> dict[str, Any]:
    mutated = copy.deepcopy(profile)
    mutated.setdefault("predeclared_gates", {})["adverse_outcome_recall"] = 0.0
    mutated["decision"] = "PROMOTE"
    return reseal_outer_receipt(mutated)


def refresh_attacker_controlled_metadata(profile: dict[str, Any]) -> dict[str, Any]:
    events = []
    for event in profile.get("events", []):
        body = copy.deepcopy(event)
        body.pop("prev_hash", None)
        body.pop("event_hash", None)
        events.append(body)
    if profile.get("configuration", {}).get("include_chain"):
        profile["events"] = chained_events(events)
        profile["terminal_chain_hash"] = (
            profile["events"][-1]["event_hash"] if profile["events"] else ""
        )
    else:
        profile["events"] = events
        profile["terminal_chain_hash"] = ""
    profile["expected_event_count"] = len(events)
    profile["expected_adverse_count"] = adverse_count(events)
    profile["expected_artifact_count"] = artifact_count(events)
    profile["expected_manual_override_count"] = manual_override_count(events)
    return reseal_outer_receipt(profile)


def adaptive_delete_rechain_and_reseal(
    profile: dict[str, Any],
) -> dict[str, Any]:
    mutated = copy.deepcopy(profile)
    for index, event in enumerate(mutated.get("events", [])):
        if event.get("outcome") != "PASS":
            del mutated["events"][index]
            break
    return refresh_attacker_controlled_metadata(mutated)


def adaptive_policy_rechain_and_reseal(
    profile: dict[str, Any],
) -> dict[str, Any]:
    mutated = copy.deepcopy(profile)
    target = next(
        (
            event
            for event in mutated.get("events", [])
            if event.get("decision") != "ALLOW"
        ),
        None,
    )
    if target is not None:
        target["decision"] = "ALLOW"
    return refresh_attacker_controlled_metadata(mutated)


ATTACKS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "mutate_policy_decision": mutate_policy_decision,
    "delete_adverse_event": delete_adverse_event,
    "reorder_events": reorder_events,
    "mutate_artifact_digest": mutate_artifact_digest,
    "posthoc_gate_change": posthoc_gate_change,
    "adaptive_delete_rechain_and_reseal": adaptive_delete_rechain_and_reseal,
    "adaptive_policy_rechain_and_reseal": adaptive_policy_rechain_and_reseal,
}


def attack_detection(
    profile: dict[str, Any],
    verifier: Verifier,
) -> dict[str, Any]:
    results = []
    for name, mutate in ATTACKS.items():
        attacked = mutate(profile)
        after = verifier(attacked)
        results.append(
            {
                "attack": name,
                "detected": after.get("structurally_valid") is False,
                "post_attack_errors": after.get("errors", []),
            }
        )
    return {
        "cases": results,
        "detected_count": sum(1 for row in results if row["detected"]),
        "case_count": len(results),
        "detection_rate": sum(1 for row in results if row["detected"]) / len(results),
    }


def profile_result(
    profile_id: str,
    name: str,
    profile: dict[str, Any],
    trusted_anchor: dict[str, Any],
    source_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    verifier = lambda candidate: verify_lumencore_profile(
        candidate,
        trusted_anchor,
    )
    verification = verifier(profile)
    attacks = attack_detection(profile, verifier)
    attack_by_name = {row["attack"]: row for row in attacks["cases"]}
    return {
        "profile_id": profile_id,
        "name": name,
        "comparison_role": "CONTROL_ABLATION",
        "profile_sha256": stable_hash(profile),
        "trusted_anchor_sha256": trusted_anchor["anchor_sha256"],
        "serialized_bytes": len(canonical_json(profile).encode("utf-8")),
        "control_attack_detection": attacks,
        "adverse_outcome_recall": verification["adverse_outcome_recall"],
        "artifact_bytes_rehash_rate": verification["artifact_bytes_rehash_rate"],
        "integrity_root_present": verification["integrity_root_present"],
        "predeclared_gate_hash_present": verification[
            "predeclared_gate_hash_present"
        ],
        "predeclared_gate_execution_pass": verification[
            "predeclared_gate_execution_pass"
        ],
        "posthoc_promotion_change_detected": attack_by_name[
            "posthoc_gate_change"
        ]["detected"],
        "clean_profile_valid": verification["structurally_valid"],
        "source_workflow_count": len(source_rows),
    }


def build_payload() -> dict[str, Any]:
    rows = synthetic_workflows()
    protocol_payload = protocol()
    context_profiles = [
        context_profile_result(
            "opentelemetry_logs_1_59",
            "OpenTelemetry Logs Data Model 1.59.0 bounded profile",
            build_otel_profile(rows),
            verify_otel_profile,
        ),
        context_profile_result(
            "slsa_build_provenance_1_2",
            "SLSA Build Provenance 1.2 / in-toto Statement v1 bounded profile",
            build_slsa_profile(rows),
            verify_slsa_profile,
        ),
    ]
    profile_specs = [
        (
            "lumencore_full",
            "LumenCore full evidence controls",
            build_lumencore_profile(rows),
        ),
        (
            "lumencore_no_chain",
            "LumenCore ablation: no event chain",
            build_lumencore_profile(rows, include_chain=False),
        ),
        (
            "lumencore_no_predeclared_gates",
            "LumenCore ablation: no predeclared gates",
            build_lumencore_profile(rows, include_predeclared_gates=False),
        ),
        (
            "lumencore_no_failure_retention",
            "LumenCore ablation: success-only retention",
            build_lumencore_profile(rows, retain_failures=False),
        ),
    ]
    results = []
    for profile_id, name, profile in profile_specs:
        anchor = build_trusted_anchor(profile, rows)
        results.append(
            profile_result(profile_id, name, profile, anchor, rows)
        )
    by_id = {row["profile_id"]: row for row in results}
    full = by_id["lumencore_full"]
    ablation_ids = [
        "lumencore_no_chain",
        "lumencore_no_predeclared_gates",
        "lumencore_no_failure_retention",
    ]
    checks = {
        "full_clean_profile_valid": full["clean_profile_valid"] is True,
        "full_detects_all_declared_control_attacks": (
            full["control_attack_detection"]["detected_count"]
            == full["control_attack_detection"]["case_count"]
            == len(ATTACKS)
        ),
        "full_detects_adaptive_delete_rechain_and_reseal": next(
            row
            for row in full["control_attack_detection"]["cases"]
            if row["attack"] == "adaptive_delete_rechain_and_reseal"
        )["detected"],
        "full_detects_adaptive_policy_rechain_and_reseal": next(
            row
            for row in full["control_attack_detection"]["cases"]
            if row["attack"] == "adaptive_policy_rechain_and_reseal"
        )["detected"],
        "full_retains_all_adverse_outcomes": full["adverse_outcome_recall"] == 1.0,
        "full_rehashes_all_artifact_bytes": (
            full["artifact_bytes_rehash_rate"] == 1.0
        ),
        "full_executes_predeclared_gates": (
            full["predeclared_gate_execution_pass"] is True
        ),
        "full_detects_posthoc_promotion_change": (
            full["posthoc_promotion_change_detected"] is True
        ),
        "every_ablation_loses_at_least_one_declared_control": all(
            (
                by_id[profile_id]["control_attack_detection"]["detection_rate"]
                < full["control_attack_detection"]["detection_rate"]
                or by_id[profile_id]["adverse_outcome_recall"]
                < full["adverse_outcome_recall"]
                or by_id[profile_id]["predeclared_gate_execution_pass"]
                is not full["predeclared_gate_execution_pass"]
            )
            for profile_id in ablation_ids
        ),
        "standards_are_context_only_not_ranked": all(
            row["comparison_role"] == "INTEROPERABILITY_CONTEXT_NOT_RANKED"
            and row["attack_comparison_performed"] is False
            for row in context_profiles
        ),
    }
    payload = {
        "schema": SCHEMA,
        "generated_utc": now_utc(),
        "status": (
            "SYNTHETIC_CONTROL_ABLATION_PASS_EXTERNAL_TRUST_ROOT_HPCMP_AND_INDEPENDENT_VALIDATION_REQUIRED"
            if all(checks.values())
            else "SYNTHETIC_CONTROL_ABLATION_FAIL"
        ),
        "protocol": protocol_payload,
        "protocol_sha256": stable_hash(protocol_payload),
        "trusted_anchor_model": TRUST_MODEL,
        "baseline_sources": BASELINE_SOURCES,
        "interoperability_context_profiles": context_profiles,
        "synthetic_workflows": {
            "count": len(rows),
            "adverse_count": adverse_count(rows),
            "artifact_count": artifact_count(rows),
            "manual_override_count": manual_override_count(rows),
            "rows_sha256": stable_hash(rows),
            "raw_rows_published": False,
        },
        "results": results,
        "checks": checks,
        "all_checks_pass": all(checks.values()),
        "promotion_or_performance_claim_allowed": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    payload["payload_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    result_rows = [
        "| LumenCore profile | Control attacks detected | Adverse recall | "
        "Artifact bytes rehashed | Gates executed | Bytes |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in payload["results"]:
        result_rows.append(
            f"| {row['name']} | "
            f"{row['control_attack_detection']['detected_count']}/"
            f"{row['control_attack_detection']['case_count']} | "
            f"{row['adverse_outcome_recall']:.3f} | "
            f"{row['artifact_bytes_rehash_rate']:.3f} | "
            f"{str(row['predeclared_gate_execution_pass']).lower()} | "
            f"{row['serialized_bytes']} |"
        )
    source_rows = "\n".join(
        f"- {source['name']}: {source['official_url']} - "
        f"{source['purpose_boundary']} Comparison role: "
        f"`{source['comparison_role']}`."
        for source in payload["baseline_sources"]
    )
    check_rows = "\n".join(
        f"- `{key}`: `{str(value).lower()}`"
        for key, value in payload["checks"].items()
    )
    return "\n".join(
        [
            "# ERDC SDC Evidence-Control Ablation - 2026-07-29",
            "",
            f"Status: `{payload['status']}`",
            "",
            "## Decision",
            "",
            "The deterministic surrogate compares the complete LumenCore control "
            "profile only with three LumenCore ablations. The complete profile "
            "retains the declared controls relative to a separately supplied local "
            "anchor; each ablation loses at least one control. OpenTelemetry and "
            "SLSA are complementary interoperability contexts and are not ranked.",
            "",
            "## Protocol",
            "",
            f"- Protocol: `{payload['protocol']['protocol_id']}`",
            f"- Protocol SHA-256: `{payload['protocol_sha256']}`",
            f"- Synthetic workflow count: `{payload['synthetic_workflows']['count']}`",
            f"- Adverse workflow count: `{payload['synthetic_workflows']['adverse_count']}`",
            f"- Artifact-bearing workflow count: `{payload['synthetic_workflows']['artifact_count']}`",
            f"- Synthetic-row SHA-256: `{payload['synthetic_workflows']['rows_sha256']}`",
            "- Raw synthetic rows published: `false`",
            "",
            "## Trusted Anchor Boundary",
            "",
            payload["trusted_anchor_model"],
            "",
            "## Control Ablation Results",
            "",
            *result_rows,
            "",
            "Serialized bytes describe these small synthetic LumenCore profiles only; "
            "they are not an HPCMP capacity, latency, cost, or performance result.",
            "",
            "## Checks",
            "",
            check_rows,
            "",
            "## Interoperability Contexts - Not Ranked",
            "",
            source_rows,
            "",
            "## Phase II Use",
            "",
            "Use this benchmark only to justify a Government-approved Phase II "
            "experiment: lock one representative unclassified workflow, select an "
            "equivalent integrated comparator if one is required, pin or sign the "
            "protocol and terminal root outside the mutable receipt, predeclare "
            "thresholds, run adaptive attacks and ablations, and have a separate "
            "reviewer execute the delivered verifier.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )


def write_outputs(payload: dict[str, Any]) -> None:
    for path in (OUT_JSON, DASHBOARD_JSON):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def normalized_for_check(value: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(value)
    normalized.pop("generated_utc", None)
    normalized.pop("payload_sha256", None)
    return normalized


def check_outputs(payload: dict[str, Any]) -> None:
    for path in (OUT_JSON, DASHBOARD_JSON):
        observed = json.loads(path.read_text(encoding="utf-8"))
        if normalized_for_check(observed) != normalized_for_check(payload):
            raise SystemExit(f"stale output: {repo_path(path)}")
    if OUT_MD.read_text(encoding="utf-8") != render_markdown(payload):
        raise SystemExit(f"stale output: {repo_path(OUT_MD)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the bounded ERDC SDC evidence-control ablation."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check that generated outputs match a fresh deterministic run.",
    )
    args = parser.parse_args()
    payload = build_payload()
    if args.check:
        check_outputs(payload)
    else:
        write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "protocol_sha256": payload["protocol_sha256"],
                "workflows": payload["synthetic_workflows"]["count"],
                "control_attacks": len(ATTACKS),
                "all_checks_pass": payload["all_checks_pass"],
                "output": repo_path(OUT_JSON),
            },
            indent=2,
        )
    )
    return 0 if payload["all_checks_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
