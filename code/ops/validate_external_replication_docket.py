#!/usr/bin/env python3
"""Validate a LumenCore external-replication docket and emit a bounded receipt."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "lumencore.external_replication_docket.v1"
VERSION = "1.0.0"
DEFAULT_MAX_BYTES = 1_048_576

STATUS_VALUES = {
    "template_unassigned",
    "preregistered",
    "internal_complete",
    "external_complete",
    "rejected",
    "retired",
}
DECISION_VALUES = {
    "hold",
    "reject",
    "rerun",
    "independent_replication",
    "pilot_candidate",
}
RIGHTS_VALUES = {"pending", "public", "synthetic", "buyer_authorized", "private_authorized"}
DIRECTION_VALUES = {"higher", "lower", "target"}
EVIDENCE_VALUES = {"template", "preregistered", "internal", "external"}

TOP_LEVEL_KEYS = {
    "schema",
    "version",
    "status",
    "docket_id",
    "title",
    "owner",
    "purpose",
    "evaluation",
    "independence",
    "reproducibility",
    "reporting",
    "gates",
    "decision",
    "claim_boundary",
    "custody",
}
EVALUATION_KEYS = {"hypothesis", "source", "design", "analysis", "freeze"}
HYPOTHESIS_KEYS = {"id", "primary", "null", "falsification_condition"}
SOURCE_KEYS = {"name", "rights_status", "authority", "unit_of_analysis", "population"}
DESIGN_KEYS = {
    "baseline",
    "candidate",
    "inclusion_rules",
    "exclusion_rules",
    "holdout_strategy",
    "temporal_or_seed_split",
    "no_post_outcome_tuning",
    "contamination_controls",
}
ANALYSIS_KEYS = {
    "primary_metric",
    "metric_definition",
    "direction",
    "acceptance_threshold",
    "uncertainty_method",
    "confidence_level",
    "sample_adequacy_plan",
    "multiplicity_policy",
    "missing_data_policy",
    "outlier_policy",
    "failure_rules",
    "incomplete_run_rules",
    "stop_rules",
}
FREEZE_KEYS = {"protocol_hash", "code_commit", "dependency_lock", "environment_spec", "frozen_utc"}
INDEPENDENCE_KEYS = {
    "evaluator_name",
    "organization",
    "role",
    "relationship",
    "conflict_disclosure",
    "data_control",
    "run_control",
    "analysis_control",
    "publication_permission",
}
REPRODUCIBILITY_KEYS = {
    "input_manifest",
    "output_manifest",
    "run_receipt",
    "second_environment_required",
    "tolerance_definition",
    "negative_results_required",
    "deviations_register_required",
    "offline_verifier_required",
}
REPORTING_KEYS = {
    "evidence_class",
    "results_summary",
    "primary_result",
    "uncertainty_interval",
    "sample_size",
    "negative_results",
    "failure_notes",
    "deviations",
    "limitations",
}
GATE_KEYS = {
    "source_rights_resolved",
    "evaluator_assigned",
    "protocol_frozen",
    "holdout_locked",
    "code_pinned",
    "environment_locked",
    "analysis_plan_locked",
    "external_run_complete",
    "reviewer_attestation_present",
}
DECISION_KEYS = {"status", "owner", "next_gate", "decided_utc"}
CLAIM_KEYS = {"proves", "does_not_prove", "safe_sentence"}
CUSTODY_KEYS = {"hash_algorithm", "payload_sha256", "public_safe"}

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
FORBIDDEN_KEYS = {
    "portal_submission_authorized",
    "action_authority",
    "certification_authorized",
    "payment_authorized",
    "deployment_authorized",
    "legal_approval",
}
FORBIDDEN_POSITIVE_PHRASES = {
    "independently validated",
    "external validation established",
    "field validated",
    "certified safe",
    "guaranteed performance",
    "guaranteed roi",
    "agency endorsed",
    "customer deployment confirmed",
    "award guaranteed",
}
NON_EXTERNAL_BOUNDARY_TERMS = (
    "external validation",
    "independent validation",
    "field validation",
    "operational validation",
)


class DocketError(ValueError):
    """Raised when a replication docket fails closed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise DocketError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_nonfinite(value: Any, path: str = "root") -> None:
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        raise DocketError(f"non-finite number at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                raise DocketError(f"forbidden authority field at {path}.{key}")
            _reject_nonfinite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_nonfinite(child, f"{path}[{index}]")


def load_docket(path: Path, *, max_bytes: int = DEFAULT_MAX_BYTES) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DocketError(f"cannot read docket: {exc}") from exc
    if len(raw) > max_bytes:
        raise DocketError(f"docket exceeds maximum size of {max_bytes} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DocketError("docket must be valid UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda token: (_ for _ in ()).throw(
                DocketError(f"non-finite JSON value: {token}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise DocketError(f"invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DocketError("docket root must be an object")
    _reject_nonfinite(value)
    return value


def _mapping(parent: dict[str, Any], key: str, *, context: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise DocketError(f"{context}.{key} must be an object")
    return value


def _exact_keys(value: dict[str, Any], allowed: set[str], *, context: str) -> None:
    missing = sorted(allowed - set(value))
    extra = sorted(set(value) - allowed)
    if missing or extra:
        raise DocketError(f"{context} key mismatch; missing={missing}, extra={extra}")


def _string(parent: dict[str, Any], key: str, *, context: str, allow_pending: bool = True) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DocketError(f"{context}.{key} must be a non-empty string")
    value = value.strip()
    if not allow_pending and value.casefold() in {"pending", "unknown", "unassigned", "not_run"}:
        raise DocketError(f"{context}.{key} cannot remain {value!r}")
    return value


def _bool(parent: dict[str, Any], key: str, *, context: str) -> bool:
    value = parent.get(key)
    if not isinstance(value, bool):
        raise DocketError(f"{context}.{key} must be boolean")
    return value


def _string_list(
    parent: dict[str, Any],
    key: str,
    *,
    context: str,
    require_nonempty: bool = True,
) -> list[str]:
    value = parent.get(key)
    if not isinstance(value, list):
        raise DocketError(f"{context}.{key} must be an array")
    if require_nonempty and not value:
        raise DocketError(f"{context}.{key} must not be empty")
    out: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise DocketError(f"{context}.{key}[{index}] must be a non-empty string")
        normalized = item.strip()
        marker = normalized.casefold()
        if marker in seen:
            raise DocketError(f"{context}.{key} contains duplicate entry: {normalized}")
        seen.add(marker)
        out.append(normalized)
    return out


def _utc_or_pending(value: str, *, context: str, allow_pending: bool) -> str:
    if value.casefold() == "pending" and allow_pending:
        return value
    if not value.endswith("Z"):
        raise DocketError(f"{context} must use explicit UTC Z notation")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DocketError(f"{context} is not a valid ISO-8601 UTC timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise DocketError(f"{context} must be UTC")
    return value


def _hash_or_pending(value: str, *, context: str, allow_pending: bool) -> str:
    if value.casefold() == "pending" and allow_pending:
        return value
    lowered = value.casefold()
    if not SHA256_RE.fullmatch(lowered):
        raise DocketError(f"{context} must be a SHA-256 digest or pending")
    return lowered


def _git_sha_or_pending(value: str, *, context: str, allow_pending: bool) -> str:
    if value.casefold() == "pending" and allow_pending:
        return value
    if not GIT_SHA_RE.fullmatch(value):
        raise DocketError(f"{context} must be a 7-40 character Git SHA or pending")
    return value.lower()


def _payload_for_hash(payload: dict[str, Any]) -> dict[str, Any]:
    cloned = copy.deepcopy(payload)
    custody = cloned.get("custody")
    if not isinstance(custody, dict):
        raise DocketError("custody must be an object")
    custody["payload_sha256"] = "0" * 64
    return cloned


def compute_payload_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        _payload_for_hash(payload),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _serialized_claim_text(payload: dict[str, Any]) -> str:
    reporting = payload["reporting"]
    boundary = payload["claim_boundary"]
    values: list[str] = [payload["title"], payload["purpose"]]
    values.extend(
        str(reporting[key])
        for key in ("results_summary", "primary_result", "uncertainty_interval")
    )
    values.append(boundary["safe_sentence"])
    values.extend(boundary["proves"])
    return " ".join(values).casefold()


def _all_true(gates: dict[str, Any], keys: Iterable[str]) -> bool:
    return all(gates.get(key) is True for key in keys)


def validate_docket(payload: dict[str, Any]) -> dict[str, Any]:
    _reject_nonfinite(payload)
    _exact_keys(payload, TOP_LEVEL_KEYS, context="root")
    if payload.get("schema") != SCHEMA:
        raise DocketError(f"schema must be {SCHEMA}")
    if payload.get("version") != VERSION:
        raise DocketError(f"version must be {VERSION}")

    status = _string(payload, "status", context="root")
    if status not in STATUS_VALUES:
        raise DocketError(f"unsupported status: {status}")
    docket_id = _string(payload, "docket_id", context="root")
    if not ID_RE.fullmatch(docket_id):
        raise DocketError("docket_id is not canonical")
    for key in ("title", "owner", "purpose"):
        _string(payload, key, context="root")

    evaluation = _mapping(payload, "evaluation", context="root")
    _exact_keys(evaluation, EVALUATION_KEYS, context="evaluation")

    hypothesis = _mapping(evaluation, "hypothesis", context="evaluation")
    _exact_keys(hypothesis, HYPOTHESIS_KEYS, context="evaluation.hypothesis")
    hypothesis_id = _string(hypothesis, "id", context="evaluation.hypothesis")
    if not ID_RE.fullmatch(hypothesis_id):
        raise DocketError("evaluation.hypothesis.id is not canonical")
    for key in ("primary", "null", "falsification_condition"):
        _string(hypothesis, key, context="evaluation.hypothesis")

    source = _mapping(evaluation, "source", context="evaluation")
    _exact_keys(source, SOURCE_KEYS, context="evaluation.source")
    for key in ("name", "authority", "unit_of_analysis", "population"):
        _string(source, key, context="evaluation.source")
    rights_status = _string(source, "rights_status", context="evaluation.source")
    if rights_status not in RIGHTS_VALUES:
        raise DocketError(f"unsupported source rights status: {rights_status}")

    design = _mapping(evaluation, "design", context="evaluation")
    _exact_keys(design, DESIGN_KEYS, context="evaluation.design")
    for key in ("baseline", "candidate", "holdout_strategy", "temporal_or_seed_split"):
        _string(design, key, context="evaluation.design")
    for key in ("inclusion_rules", "exclusion_rules", "contamination_controls"):
        _string_list(design, key, context="evaluation.design")
    if _bool(design, "no_post_outcome_tuning", context="evaluation.design") is not True:
        raise DocketError("evaluation.design.no_post_outcome_tuning must be true")

    analysis = _mapping(evaluation, "analysis", context="evaluation")
    _exact_keys(analysis, ANALYSIS_KEYS, context="evaluation.analysis")
    for key in (
        "primary_metric",
        "metric_definition",
        "acceptance_threshold",
        "uncertainty_method",
        "sample_adequacy_plan",
        "multiplicity_policy",
        "missing_data_policy",
        "outlier_policy",
    ):
        _string(analysis, key, context="evaluation.analysis")
    direction = _string(analysis, "direction", context="evaluation.analysis")
    if direction not in DIRECTION_VALUES:
        raise DocketError(f"unsupported metric direction: {direction}")
    confidence = analysis.get("confidence_level")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise DocketError("evaluation.analysis.confidence_level must be numeric")
    if not 0 < float(confidence) < 1:
        raise DocketError("evaluation.analysis.confidence_level must be between 0 and 1")
    for key in ("failure_rules", "incomplete_run_rules", "stop_rules"):
        _string_list(analysis, key, context="evaluation.analysis")

    freeze = _mapping(evaluation, "freeze", context="evaluation")
    _exact_keys(freeze, FREEZE_KEYS, context="evaluation.freeze")
    allow_pending = status in {"template_unassigned", "rejected", "retired"}
    protocol_hash = _hash_or_pending(
        _string(freeze, "protocol_hash", context="evaluation.freeze"),
        context="evaluation.freeze.protocol_hash",
        allow_pending=allow_pending,
    )
    code_commit = _git_sha_or_pending(
        _string(freeze, "code_commit", context="evaluation.freeze"),
        context="evaluation.freeze.code_commit",
        allow_pending=allow_pending,
    )
    _string(freeze, "dependency_lock", context="evaluation.freeze", allow_pending=allow_pending)
    _string(freeze, "environment_spec", context="evaluation.freeze", allow_pending=allow_pending)
    _utc_or_pending(
        _string(freeze, "frozen_utc", context="evaluation.freeze"),
        context="evaluation.freeze.frozen_utc",
        allow_pending=allow_pending,
    )

    independence = _mapping(payload, "independence", context="root")
    _exact_keys(independence, INDEPENDENCE_KEYS, context="independence")
    for key in INDEPENDENCE_KEYS:
        _string(independence, key, context="independence")

    reproducibility = _mapping(payload, "reproducibility", context="root")
    _exact_keys(reproducibility, REPRODUCIBILITY_KEYS, context="reproducibility")
    for key in ("input_manifest", "output_manifest", "run_receipt", "tolerance_definition"):
        _string(reproducibility, key, context="reproducibility")
    for key in (
        "second_environment_required",
        "negative_results_required",
        "deviations_register_required",
        "offline_verifier_required",
    ):
        if _bool(reproducibility, key, context="reproducibility") is not True:
            raise DocketError(f"reproducibility.{key} must be true")

    reporting = _mapping(payload, "reporting", context="root")
    _exact_keys(reporting, REPORTING_KEYS, context="reporting")
    evidence_class = _string(reporting, "evidence_class", context="reporting")
    if evidence_class not in EVIDENCE_VALUES:
        raise DocketError(f"unsupported evidence_class: {evidence_class}")
    for key in ("results_summary", "primary_result", "uncertainty_interval", "sample_size"):
        _string(reporting, key, context="reporting")
    for key in ("negative_results", "failure_notes", "deviations", "limitations"):
        _string_list(reporting, key, context="reporting")

    gates = _mapping(payload, "gates", context="root")
    _exact_keys(gates, GATE_KEYS, context="gates")
    for key in GATE_KEYS:
        _bool(gates, key, context="gates")

    decision = _mapping(payload, "decision", context="root")
    _exact_keys(decision, DECISION_KEYS, context="decision")
    decision_status = _string(decision, "status", context="decision")
    if decision_status not in DECISION_VALUES:
        raise DocketError(f"unsupported decision status: {decision_status}")
    _string(decision, "owner", context="decision")
    _string(decision, "next_gate", context="decision")
    _utc_or_pending(
        _string(decision, "decided_utc", context="decision"),
        context="decision.decided_utc",
        allow_pending=allow_pending,
    )

    boundary = _mapping(payload, "claim_boundary", context="root")
    _exact_keys(boundary, CLAIM_KEYS, context="claim_boundary")
    _string_list(boundary, "proves", context="claim_boundary")
    does_not_prove = _string_list(boundary, "does_not_prove", context="claim_boundary")
    _string(boundary, "safe_sentence", context="claim_boundary")

    custody = _mapping(payload, "custody", context="root")
    _exact_keys(custody, CUSTODY_KEYS, context="custody")
    if custody.get("hash_algorithm") != "sha256":
        raise DocketError("custody.hash_algorithm must be sha256")
    if custody.get("public_safe") is not True:
        raise DocketError("custody.public_safe must be true")
    expected_hash = _string(custody, "payload_sha256", context="custody").casefold()
    if not SHA256_RE.fullmatch(expected_hash):
        raise DocketError("custody.payload_sha256 must be a SHA-256 digest")
    actual_hash = compute_payload_sha256(payload)
    if actual_hash != expected_hash:
        raise DocketError(f"payload hash mismatch: expected {expected_hash}, got {actual_hash}")

    claim_text = _serialized_claim_text(payload)
    unsafe_hits = sorted(phrase for phrase in FORBIDDEN_POSITIVE_PHRASES if phrase in claim_text)
    if unsafe_hits:
        raise DocketError("unsafe positive claim(s): " + ", ".join(unsafe_hits))

    if status == "template_unassigned":
        if any(gates.values()):
            raise DocketError("template_unassigned cannot assert completed gates")
        if decision_status != "hold":
            raise DocketError("template_unassigned decision must be hold")
        if evidence_class != "template":
            raise DocketError("template_unassigned evidence_class must be template")
        if protocol_hash != "pending" or code_commit != "pending":
            raise DocketError("template_unassigned freeze identifiers must remain pending")

    preregistration_gates = {
        "source_rights_resolved",
        "evaluator_assigned",
        "protocol_frozen",
        "holdout_locked",
        "code_pinned",
        "environment_locked",
        "analysis_plan_locked",
    }
    if status in {"preregistered", "internal_complete", "external_complete"}:
        if not _all_true(gates, preregistration_gates):
            raise DocketError(f"{status} requires all preregistration gates")
        if rights_status == "pending":
            raise DocketError(f"{status} requires resolved source rights")
        if protocol_hash == "pending" or code_commit == "pending":
            raise DocketError(f"{status} requires frozen protocol and code identifiers")

    if status == "preregistered":
        if gates["external_run_complete"] or gates["reviewer_attestation_present"]:
            raise DocketError("preregistered cannot claim completed external review")
        if evidence_class != "preregistered":
            raise DocketError("preregistered evidence_class must be preregistered")
        if decision_status not in {"hold", "independent_replication"}:
            raise DocketError("preregistered decision must be hold or independent_replication")

    if status == "internal_complete":
        if gates["external_run_complete"] or gates["reviewer_attestation_present"]:
            raise DocketError("internal_complete cannot claim external completion")
        if evidence_class != "internal":
            raise DocketError("internal_complete evidence_class must be internal")
        boundary_text = " ".join(does_not_prove).casefold()
        if not any(term in boundary_text for term in NON_EXTERNAL_BOUNDARY_TERMS):
            raise DocketError("internal_complete must explicitly retain an external-validation boundary")
        if decision_status == "pilot_candidate":
            raise DocketError("internal_complete cannot promote directly to pilot_candidate")

    if status == "external_complete":
        if not all(gates.values()):
            raise DocketError("external_complete requires every gate")
        if evidence_class != "external":
            raise DocketError("external_complete evidence_class must be external")
        for key in INDEPENDENCE_KEYS:
            _string(independence, key, context="independence", allow_pending=False)
        if independence["relationship"].casefold() in {"founder", "self", "founder-controlled"}:
            raise DocketError("external evaluator relationship cannot be founder-controlled")
        for key in ("input_manifest", "output_manifest", "run_receipt"):
            _string(reproducibility, key, context="reproducibility", allow_pending=False)
        for key in ("results_summary", "primary_result", "uncertainty_interval", "sample_size"):
            _string(reporting, key, context="reporting", allow_pending=False)

    if status == "rejected" and decision_status != "reject":
        raise DocketError("rejected status requires reject decision")

    return {
        "valid": True,
        "schema": SCHEMA,
        "version": VERSION,
        "docket_id": docket_id,
        "status": status,
        "evidence_class": evidence_class,
        "decision": decision_status,
        "payload_sha256": actual_hash,
        "preregistration_gates_passed": sum(1 for key in preregistration_gates if gates[key]),
        "total_preregistration_gates": len(preregistration_gates),
        "external_gates_passed": int(gates["external_run_complete"]) + int(gates["reviewer_attestation_present"]),
        "total_external_gates": 2,
        "claim_boundary_count": len(does_not_prove),
        "negative_result_entries": len(reporting["negative_results"]),
        "limitation_entries": len(reporting["limitations"]),
        "safe_for_external_validation_claim": status == "external_complete" and all(gates.values()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "docket",
        type=Path,
        nargs="?",
        default=Path("config/external_replication_docket_v1.json"),
    )
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    args = parser.parse_args(argv)

    try:
        payload = load_docket(args.docket, max_bytes=args.max_bytes)
        receipt = validate_docket(payload)
    except (DocketError, OSError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
