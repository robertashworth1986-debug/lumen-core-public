from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "federal_reviewer_objection_register_v1.json"
DEFAULT_OUTPUT = (
    ROOT / "out" / "ops" / "federal_reviewer_objection_gate_latest.json"
)
DEFAULT_DOCUMENTATION = (
    ROOT / "docs" / "FEDERAL_REVIEWER_OBJECTION_GATE_2026-07-26.md"
)

CONFIG_SCHEMA = "lumencore.federal_reviewer_objection_register_config.v1"
OUTPUT_SCHEMA = "lumencore.federal_reviewer_objection_gate.v1"
MODE = "LOCAL_READ_ONLY_REVIEW_WITH_FAIL_CLOSED_OUTPUT"

EXPECTED_CONTROLS = {
    "action_time_human_approval_required": True,
    "autonomous_certification_allowed": False,
    "autonomous_email_send_allowed": False,
    "autonomous_portal_action_allowed": False,
    "autonomous_submission_allowed": False,
    "external_action_allowed": False,
    "mandatory_requirement_fail_closed": True,
    "operational_claim_requires_external_evidence": True,
    "private_identifiers_allowed": False,
    "software_pattern_proof_is_operational_proof": False,
}

MANDATORY_CATEGORIES = frozenset(
    {
        "legal_entity_registration",
        "naics_psc_set_aside_fit",
        "past_performance",
        "personnel_and_clearances",
        "cybersecurity",
        "data_rights",
        "technical_baselines",
        "independent_evidence",
        "staffing_price_schedule",
        "deployment_and_operations",
        "teaming_boundaries",
        "exact_solicitation_conformance",
    }
)

ALLOWED_KINDS = frozenset({"json", "markdown", "pdf"})
ALLOWED_SEVERITIES = frozenset({"BLOCKING", "MAJOR", "ADVISORY"})
ALLOWED_EVIDENCE_CLASSES = frozenset(
    {
        "BRAND_APPROVAL",
        "DOCUMENTARY_EVIDENCE",
        "HUMAN_APPROVAL",
        "INDEPENDENT_EVIDENCE",
        "OPERATIONAL_PROOF",
        "SOFTWARE_PATTERN_PROOF",
        "SOLICITATION_SOURCE",
        "TEAMING_EVIDENCE",
    }
)

PROHIBITED_DATA_KEYS = frozenset(
    {
        "cage",
        "cage_code",
        "duns",
        "email",
        "email_address",
        "meeting_url",
        "otp",
        "password",
        "phone",
        "phone_number",
        "private_identifier",
        "recipient_email",
        "ssn",
        "street_address",
        "tax_id",
        "token",
        "uei",
        "uei_value",
    }
)
EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@"
    r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9.-])"
)
MEETING_LINK_RE = re.compile(
    r"https?://(?:[^/\s]+\.)?"
    r"(?:zoom\.us|meet\.google\.com|teams\.microsoft\.com)/",
    re.IGNORECASE,
)
HEX_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

MONDAY_EXPECTED_CONTROL_VALUES = {
    "action_time_human_approval_required": True,
    "autonomous_certification_allowed": False,
    "autonomous_email_send_allowed": False,
    "autonomous_submission_allowed": False,
    "mandatory_requirement_fail_closed": True,
    "performance_claims_require_independent_evidence": True,
    "private_identifiers_omitted": True,
    "response_instructions_structured": True,
    "source_set_completeness_required_for_ready_state": True,
}

SAFEST_NEXT_ACTION = (
    "Do not distribute the current capability statement or submit any reviewed "
    "Monday lane as prime. Resolve each documentary, operational, independent, "
    "teaming, and solicitation-conformance objection that remains open with current "
    "authoritative evidence, then obtain exact action-time human approval."
)


class GateError(ValueError):
    pass


def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def normalize_utc(value: str | None) -> str:
    if value is None:
        return utc_now_text()
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GateError("as-of time must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GateError(f"{label} must be non-empty text")
    return value.strip()


def _require_text_list(value: Any, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise GateError(f"{label} must be a non-empty text list")
    return [item.strip() for item in value]


def _assert_public_safe(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise GateError(f"{path} contains a non-text key")
            if key.lower() in PROHIBITED_DATA_KEYS:
                raise GateError(f"{path}.{key} is a prohibited private-data key")
            _assert_public_safe(child, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _assert_public_safe(child, f"{path}[{index}]")
        return
    if isinstance(value, str):
        if EMAIL_RE.search(value):
            raise GateError(f"{path} contains an email address")
        if MEETING_LINK_RE.search(value):
            raise GateError(f"{path} contains a meeting link")


def _resolve_material_path(root: Path, raw_path: str) -> Path:
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        raise GateError("material paths must be relative and traversal-free")
    root = root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise GateError("material path resolves outside the repository root") from exc
    return resolved


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"unable to load reviewer register: {exc}") from exc
    validate_config(payload)
    return payload


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict):
        raise GateError("register must be a JSON object")
    _assert_public_safe(config)

    if config.get("schema") != CONFIG_SCHEMA or config.get("version") != 1:
        raise GateError("register schema or version is invalid")
    if config.get("controls") != EXPECTED_CONTROLS:
        raise GateError("reviewer controls must match the fail-closed contract")

    scope = config.get("review_scope")
    if not isinstance(scope, dict):
        raise GateError("review_scope must be an object")
    _require_text(scope.get("title"), "review_scope.title")
    _require_text(scope.get("scope_date"), "review_scope.scope_date")

    materials = scope.get("materials")
    if not isinstance(materials, list) or not materials:
        raise GateError("review_scope.materials must be non-empty")
    material_ids: set[str] = set()
    for index, material in enumerate(materials):
        label = f"review_scope.materials[{index}]"
        if not isinstance(material, dict):
            raise GateError(f"{label} must be an object")
        material_id = _require_text(material.get("id"), f"{label}.id")
        if not SAFE_ID_RE.fullmatch(material_id):
            raise GateError(f"{label}.id is not a safe identifier")
        if material_id in material_ids:
            raise GateError(f"duplicate material id: {material_id}")
        material_ids.add(material_id)

        _require_text(material.get("path"), f"{label}.path")
        if material.get("kind") not in ALLOWED_KINDS:
            raise GateError(f"{label}.kind is invalid")
        if material.get("required") is not True:
            raise GateError(f"{label} must be required for fail-closed review")
        expected_hash = _require_text(
            material.get("expected_sha256"),
            f"{label}.expected_sha256",
        ).upper()
        if not HEX_SHA256_RE.fullmatch(expected_hash):
            raise GateError(f"{label}.expected_sha256 is invalid")
        if material["kind"] == "json":
            _require_text(
                material.get("expected_schema"),
                f"{label}.expected_schema",
            )
        if "required_text" in material:
            if material["kind"] != "markdown":
                raise GateError(f"{label}.required_text is only valid for markdown")
            _require_text_list(
                material["required_text"],
                f"{label}.required_text",
            )

    required_categories = set(
        _require_text_list(
            config.get("required_categories"),
            "required_categories",
        )
    )
    if not MANDATORY_CATEGORIES.issubset(required_categories):
        missing = sorted(MANDATORY_CATEGORIES - required_categories)
        raise GateError(f"required reviewer categories are missing: {missing}")

    evidence_model = config.get("evidence_model")
    if not isinstance(evidence_model, dict):
        raise GateError("evidence_model must be an object")
    for key in (
        "software_pattern_proof",
        "operational_proof",
        "independent_evidence",
        "documentary_evidence",
        "conversion_rule",
    ):
        _require_text(evidence_model.get(key), f"evidence_model.{key}")
    if "never converts" not in evidence_model["conversion_rule"].lower():
        raise GateError("evidence conversion rule must prohibit inferred conversion")

    objections = config.get("objections")
    if not isinstance(objections, list) or not objections:
        raise GateError("objections must be a non-empty list")

    objection_ids: set[str] = set()
    observed_categories: set[str] = set()
    state_evidence_classes: set[str] = set()
    for index, objection in enumerate(objections):
        label = f"objections[{index}]"
        if not isinstance(objection, dict):
            raise GateError(f"{label} must be an object")
        objection_id = _require_text(objection.get("id"), f"{label}.id")
        if not SAFE_ID_RE.fullmatch(objection_id):
            raise GateError(f"{label}.id is not a safe identifier")
        if objection_id in objection_ids:
            raise GateError(f"duplicate objection id: {objection_id}")
        objection_ids.add(objection_id)

        category = _require_text(
            objection.get("category"),
            f"{label}.category",
        )
        observed_categories.add(category)
        _require_text(
            objection.get("reviewer_question"),
            f"{label}.reviewer_question",
        )
        if objection.get("severity") not in ALLOWED_SEVERITIES:
            raise GateError(f"{label}.severity is invalid")
        _require_text_list(objection.get("applies_to"), f"{label}.applies_to")

        evidence_rows = objection.get("required_evidence")
        if not isinstance(evidence_rows, list) or not evidence_rows:
            raise GateError(f"{label}.required_evidence must be non-empty")
        evidence_ids: set[str] = set()
        for evidence_index, evidence in enumerate(evidence_rows):
            evidence_label = f"{label}.required_evidence[{evidence_index}]"
            if not isinstance(evidence, dict):
                raise GateError(f"{evidence_label} must be an object")
            evidence_id = _require_text(
                evidence.get("id"),
                f"{evidence_label}.id",
            )
            if not SAFE_ID_RE.fullmatch(evidence_id):
                raise GateError(f"{evidence_label}.id is not safe")
            if evidence_id in evidence_ids:
                raise GateError(f"duplicate evidence id in {objection_id}")
            evidence_ids.add(evidence_id)
            _require_text(
                evidence.get("description"),
                f"{evidence_label}.description",
            )
            if evidence.get("evidence_class") not in ALLOWED_EVIDENCE_CLASSES:
                raise GateError(f"{evidence_label}.evidence_class is invalid")

        state = objection.get("current_state")
        if not isinstance(state, dict):
            raise GateError(f"{label}.current_state must be an object")
        _require_text(state.get("code"), f"{label}.current_state.code")
        state_class = state.get("evidence_class")
        if state_class not in ALLOWED_EVIDENCE_CLASSES:
            raise GateError(f"{label}.current_state.evidence_class is invalid")
        state_evidence_classes.add(state_class)
        if not isinstance(state.get("satisfies_objection"), bool):
            raise GateError(
                f"{label}.current_state.satisfies_objection must be boolean"
            )
        _require_text(state.get("basis"), f"{label}.current_state.basis")
        basis_refs = _require_text_list(
            state.get("basis_refs"),
            f"{label}.current_state.basis_refs",
        )
        unknown_refs = set(basis_refs) - material_ids
        if unknown_refs:
            raise GateError(
                f"{label} references unknown materials: {sorted(unknown_refs)}"
            )
        _require_text(
            objection.get("claim_boundary"),
            f"{label}.claim_boundary",
        )
        _require_text(
            objection.get("safe_next_action"),
            f"{label}.safe_next_action",
        )

    missing_categories = required_categories - observed_categories
    if missing_categories:
        raise GateError(
            f"objection rows are missing categories: {sorted(missing_categories)}"
        )
    if "SOFTWARE_PATTERN_PROOF" not in state_evidence_classes:
        raise GateError("register must expose software-pattern proof state")
    if "OPERATIONAL_PROOF" not in state_evidence_classes:
        raise GateError("register must expose operational-proof state")
    _require_text(config.get("claim_boundary"), "claim_boundary")


def _audit_monday_packet(payload: Any) -> dict[str, Any]:
    failures: list[str] = []
    if not isinstance(payload, dict):
        return {
            "valid": False,
            "failures": ["MONDAY_PACKET_NOT_OBJECT"],
            "opportunity_count": None,
            "prime_submission_ready_count": None,
            "external_action_count": None,
            "partner_brief_ready_count": None,
            "all_prime_blocked": False,
            "all_partner_briefs_blocked": False,
            "all_external_actions_blocked": False,
        }

    controls = payload.get("controls")
    if not isinstance(controls, dict):
        failures.append("MONDAY_CONTROLS_MISSING")
    else:
        for key, expected in MONDAY_EXPECTED_CONTROL_VALUES.items():
            if controls.get(key) is not expected:
                failures.append(f"MONDAY_CONTROL_RELAXED_{key.upper()}")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        failures.append("MONDAY_SUMMARY_MISSING")
        summary = {}
    prime_count = summary.get("prime_submission_ready_count")
    external_count = summary.get("external_action_count")
    partner_count = summary.get("partner_brief_ready_count")
    if prime_count != 0:
        failures.append("MONDAY_PRIME_READY_COUNT_NONZERO")
    if partner_count != 0:
        failures.append("MONDAY_PARTNER_READY_COUNT_NONZERO")
    if external_count != 0:
        failures.append("MONDAY_EXTERNAL_ACTION_COUNT_NONZERO")

    opportunities = payload.get("opportunities")
    if not isinstance(opportunities, list) or not opportunities:
        failures.append("MONDAY_OPPORTUNITIES_MISSING")
        opportunities = []
    prime_flags = [
        row.get("prime_submission_ready")
        for row in opportunities
        if isinstance(row, dict)
    ]
    partner_flags = [
        row.get("partner_brief_ready")
        for row in opportunities
        if isinstance(row, dict)
    ]
    external_flags = [
        row.get("external_action_authorized")
        for row in opportunities
        if isinstance(row, dict)
    ]
    if len(prime_flags) != len(opportunities) or any(
        flag is not False for flag in prime_flags
    ):
        failures.append("MONDAY_PRIME_FLAG_NOT_FAIL_CLOSED")
    if len(partner_flags) != len(opportunities) or any(
        flag is not False for flag in partner_flags
    ):
        failures.append("MONDAY_PARTNER_FLAG_NOT_FAIL_CLOSED")
    if len(external_flags) != len(opportunities) or any(
        flag is not False for flag in external_flags
    ):
        failures.append("MONDAY_EXTERNAL_ACTION_FLAG_NOT_FAIL_CLOSED")

    decision_counts = Counter(
        row.get("decision", "MISSING")
        for row in opportunities
        if isinstance(row, dict)
    )
    notice_ids = sorted(
        row["notice_id"]
        for row in opportunities
        if isinstance(row, dict)
        and isinstance(row.get("notice_id"), str)
        and row["notice_id"]
    )
    return {
        "valid": not failures,
        "failures": sorted(set(failures)),
        "opportunity_count": len(opportunities),
        "prime_submission_ready_count": prime_count,
        "external_action_count": external_count,
        "partner_brief_ready_count": partner_count,
        "all_prime_blocked": bool(opportunities)
        and all(flag is False for flag in prime_flags),
        "all_partner_briefs_blocked": bool(opportunities)
        and all(flag is False for flag in partner_flags),
        "all_external_actions_blocked": bool(opportunities)
        and all(flag is False for flag in external_flags),
        "decision_counts": dict(sorted(decision_counts.items())),
        "notice_ids": notice_ids,
    }


def inspect_materials(
    config: dict[str, Any],
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    receipts: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    monday_observation: dict[str, Any] | None = None

    for material in config["review_scope"]["materials"]:
        material_id = material["id"]
        resolved = _resolve_material_path(root, material["path"])
        receipt: dict[str, Any] = {
            "id": material_id,
            "path": material["path"],
            "kind": material["kind"],
            "required": material["required"],
            "exists": resolved.is_file(),
            "bytes": None,
            "sha256": None,
            "expected_sha256": material["expected_sha256"].upper(),
            "hash_matches": False,
            "format_valid": False,
            "content_checks_valid": False,
        }
        if not resolved.is_file():
            blockers.append(
                {
                    "code": "REQUIRED_MATERIAL_MISSING",
                    "material_id": material_id,
                    "message": "A required reviewer material is missing.",
                }
            )
            receipts.append(receipt)
            continue

        receipt["bytes"] = resolved.stat().st_size
        receipt["sha256"] = file_sha256(resolved)
        receipt["hash_matches"] = (
            receipt["sha256"] == receipt["expected_sha256"]
        )
        if not receipt["hash_matches"]:
            blockers.append(
                {
                    "code": "MATERIAL_HASH_MISMATCH",
                    "material_id": material_id,
                    "message": "A required reviewer material changed after review.",
                }
            )

        kind = material["kind"]
        if kind == "pdf":
            with resolved.open("rb") as handle:
                receipt["format_valid"] = handle.read(5) == b"%PDF-"
            receipt["content_checks_valid"] = receipt["format_valid"]
        elif kind == "markdown":
            text = resolved.read_text(encoding="utf-8")
            receipt["format_valid"] = bool(text.strip())
            required_text = material.get("required_text", [])
            matched = sum(needle in text for needle in required_text)
            receipt["required_text_check_count"] = len(required_text)
            receipt["required_text_match_count"] = matched
            receipt["content_checks_valid"] = (
                receipt["format_valid"] and matched == len(required_text)
            )
        elif kind == "json":
            try:
                payload = json.loads(resolved.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = None
            receipt["format_valid"] = isinstance(payload, dict)
            receipt["observed_schema"] = (
                payload.get("schema") if isinstance(payload, dict) else None
            )
            schema_matches = (
                receipt["observed_schema"] == material["expected_schema"]
            )
            receipt["schema_matches"] = schema_matches
            if material_id == "monday_packet":
                monday_observation = _audit_monday_packet(payload)
                receipt["content_checks_valid"] = (
                    receipt["format_valid"]
                    and schema_matches
                    and monday_observation["valid"]
                )
            else:
                receipt["content_checks_valid"] = (
                    receipt["format_valid"] and schema_matches
                )

        if not receipt["format_valid"]:
            blockers.append(
                {
                    "code": "MATERIAL_FORMAT_INVALID",
                    "material_id": material_id,
                    "message": "A required reviewer material has an invalid format.",
                }
            )
        elif not receipt["content_checks_valid"]:
            blockers.append(
                {
                    "code": "MATERIAL_CONTENT_CHECK_FAILED",
                    "material_id": material_id,
                    "message": (
                        "A required reviewer material failed bounded semantic "
                        "or boundary checks."
                    ),
                }
            )
        receipts.append(receipt)

    receipts.sort(key=lambda row: row["id"])
    blockers.sort(key=lambda row: (row["code"], row["material_id"]))
    return receipts, blockers, monday_observation


def _objection_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in config["objections"]:
        row = json.loads(json.dumps(source))
        row["resolved"] = source["current_state"]["satisfies_objection"]
        row["objection_sha256"] = canonical_sha256(row)
        rows.append(row)
    return rows


def _counts(rows: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    counter = Counter(row[field] for row in rows)
    return dict(sorted(counter.items()))


def build_gate(
    config: dict[str, Any],
    *,
    root: Path = ROOT,
    as_of_utc: str | None = None,
) -> dict[str, Any]:
    validate_config(config)
    generated_at = normalize_utc(as_of_utc)
    material_receipts, material_blockers, monday_observation = inspect_materials(
        config,
        root,
    )
    objections = _objection_rows(config)
    unresolved = [row for row in objections if not row["resolved"]]
    blocking = [
        row
        for row in unresolved
        if row["severity"] == "BLOCKING"
    ]

    if material_blockers:
        status = "BLOCKED_REVIEW_MATERIALS_UNRESOLVED"
    elif blocking:
        status = "BLOCKED_UNRESOLVED_REVIEWER_OBJECTIONS"
    elif unresolved:
        status = "BLOCKED_NONBLOCKING_OBJECTIONS_UNRESOLVED"
    else:
        status = "PASS_ALL_REVIEWER_OBJECTIONS_RESOLVED"

    software_pattern_ids = [
        row["id"]
        for row in objections
        if row["current_state"]["evidence_class"] == "SOFTWARE_PATTERN_PROOF"
    ]
    operational_ids = [
        row["id"]
        for row in objections
        if row["current_state"]["evidence_class"] == "OPERATIONAL_PROOF"
    ]

    gate: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "generated_at_utc": generated_at,
        "mode": MODE,
        "review_scope": {
            "title": config["review_scope"]["title"],
            "scope_date": config["review_scope"]["scope_date"],
            "register_sha256": canonical_sha256(config),
            "material_count": len(material_receipts),
        },
        "summary": {
            "status": status,
            "material_blocker_count": len(material_blockers),
            "objection_count": len(objections),
            "unresolved_objection_count": len(unresolved),
            "blocking_objection_count": len(blocking),
            "resolved_objection_count": len(objections) - len(unresolved),
            "prime_submission_allowed": False,
            "external_capability_distribution_allowed": False,
            "partner_outreach_allowed": False,
            "external_action_count": 0,
        },
        "category_counts": _counts(objections, "category"),
        "severity_counts": _counts(objections, "severity"),
        "current_state_counts": _counts(
            [row["current_state"] for row in objections],
            "code",
        ),
        "current_evidence_class_counts": _counts(
            [row["current_state"] for row in objections],
            "evidence_class",
        ),
        "evidence_distinction": {
            **config["evidence_model"],
            "software_pattern_proof_objection_ids": software_pattern_ids,
            "operational_proof_objection_ids": operational_ids,
            "software_pattern_proof_satisfies_operational_proof": False,
        },
        "material_receipts": material_receipts,
        "material_blockers": material_blockers,
        "monday_packet_observation": monday_observation,
        "objections": objections,
        "controls": config["controls"],
        "claim_boundary": config["claim_boundary"],
        "safest_next_action": SAFEST_NEXT_ACTION,
        "capability_boundary": {
            "local_files_read_only_except_declared_outputs": True,
            "network_access_performed": False,
            "email_read_performed": False,
            "email_send_performed": False,
            "portal_action_performed": False,
            "certification_performed": False,
            "submission_performed": False,
            "signature_performed": False,
            "purchase_performed": False,
            "private_identifiers_recorded": False,
            "source_document_contents_embedded": False,
        },
    }
    _assert_public_safe(gate)
    gate["gate_sha256"] = canonical_sha256(gate)
    return gate


def render_documentation(gate: dict[str, Any]) -> str:
    summary = gate["summary"]
    unresolved_categories = ", ".join(
        sorted(
            row["category"].replace("_", " ")
            for row in gate["objections"]
            if not row["resolved"]
        )
    )
    lines = [
        "# Federal Reviewer Objection Gate",
        "",
        f"- As of UTC: `{gate['generated_at_utc']}`",
        f"- Status: `{summary['status']}`",
        f"- Reviewer objections: `{summary['objection_count']}`",
        f"- Unresolved objections: `{summary['unresolved_objection_count']}`",
        f"- Blocking objections: `{summary['blocking_objection_count']}`",
        f"- Material blockers: `{summary['material_blocker_count']}`",
        "- Prime submission allowed: `false`",
        "- External capability distribution allowed: `false`",
        "- External actions performed: `0`",
        f"- Gate SHA-256: `{gate['gate_sha256']}`",
        "",
        "## Reviewer Decision",
        "",
        (
            "The reviewed capability and Monday materials do not support a "
            "truthful prime submission or unrestricted external capability "
            "distribution. The packet demonstrates bounded software-pattern "
            "controls. The remaining unresolved categories are: "
            f"{unresolved_categories}."
        ),
        "",
        "## Evidence Boundary",
        "",
        (
            "- Software-pattern proof: "
            + gate["evidence_distinction"]["software_pattern_proof"]
        ),
        (
            "- Operational proof: "
            + gate["evidence_distinction"]["operational_proof"]
        ),
        (
            "- Independent evidence: "
            + gate["evidence_distinction"]["independent_evidence"]
        ),
        (
            "- Conversion rule: "
            + gate["evidence_distinction"]["conversion_rule"]
        ),
        "",
        "## Objection Register",
        "",
        "| ID | Category | State | Severity | Resolved |",
        "|---|---|---|---|---|",
    ]
    for row in gate["objections"]:
        state = row["current_state"]["code"]
        lines.append(
            f"| `{row['id']}` | `{row['category']}` | `{state}` | "
            f"`{row['severity']}` | `{str(row['resolved']).lower()}` |"
        )

    for row in gate["objections"]:
        state = row["current_state"]
        lines.extend(
            [
                "",
                f"### {row['id']} - {row['category']}",
                "",
                f"**Reviewer objection:** {row['reviewer_question']}",
                "",
                f"**Current state:** `{state['code']}`",
                "",
                f"**Basis:** {state['basis']}",
                "",
                "**Required evidence:**",
                "",
            ]
        )
        for evidence in row["required_evidence"]:
            lines.append(
                f"- `{evidence['evidence_class']}` "
                f"`{evidence['id']}`: {evidence['description']}"
            )
        lines.extend(
            [
                "",
                f"**Claim boundary:** {row['claim_boundary']}",
                "",
                f"**Safe next action:** {row['safe_next_action']}",
            ]
        )

    lines.extend(
        [
            "",
            "## Reviewed Material Receipts",
            "",
            "| Material | Kind | Present | Hash matches | Content checks | SHA-256 |",
            "|---|---|---|---|---|---|",
        ]
    )
    for receipt in gate["material_receipts"]:
        observed_hash = receipt["sha256"] or "UNAVAILABLE"
        lines.append(
            f"| `{receipt['id']}` | `{receipt['kind']}` | "
            f"`{str(receipt['exists']).lower()}` | "
            f"`{str(receipt['hash_matches']).lower()}` | "
            f"`{str(receipt['content_checks_valid']).lower()}` | "
            f"`{observed_hash}` |"
        )

    monday = gate["monday_packet_observation"]
    if monday is not None:
        lines.extend(
            [
                "",
                "## Monday Packet Observation",
                "",
                f"- Valid fail-closed packet: `{str(monday['valid']).lower()}`",
                f"- Opportunities reviewed: `{monday['opportunity_count']}`",
                (
                    "- Prime-ready count: "
                    f"`{monday['prime_submission_ready_count']}`"
                ),
                f"- Partner-brief-ready count: `{monday['partner_brief_ready_count']}`",
                f"- External action count: `{monday['external_action_count']}`",
                (
                    "- All opportunity prime flags blocked: "
                    f"`{str(monday['all_prime_blocked']).lower()}`"
                ),
                (
                    "- All external-action flags blocked: "
                    f"`{str(monday['all_external_actions_blocked']).lower()}`"
                ),
            ]
        )

    lines.extend(
        [
            "",
            "## Safe Next Action",
            "",
            gate["safest_next_action"],
            "",
            "## Claim Boundary",
            "",
            gate["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    gate: dict[str, Any],
    *,
    output_path: Path = DEFAULT_OUTPUT,
    documentation_path: Path = DEFAULT_DOCUMENTATION,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    documentation_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(gate, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    documentation_path.write_text(
        render_documentation(gate),
        encoding="utf-8",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the local, fail-closed federal reviewer objection gate. "
            "The builder performs no network, email, portal, certification, "
            "signature, or submission action."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--as-of-utc")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero while any reviewer objection remains unresolved.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config)
    gate = build_gate(config, root=ROOT, as_of_utc=args.as_of_utc)
    write_outputs(gate)
    print(f"FEDERAL_REVIEWER_OBJECTION_STATUS={gate['summary']['status']}")
    print(
        "FEDERAL_REVIEWER_OBJECTION_COUNTS="
        f"{gate['summary']['resolved_objection_count']}/"
        f"{gate['summary']['unresolved_objection_count']}"
    )
    print(
        "FEDERAL_REVIEWER_MATERIAL_BLOCKERS="
        f"{gate['summary']['material_blocker_count']}"
    )
    print(f"FEDERAL_REVIEWER_GATE_SHA256={gate['gate_sha256']}")
    print(f"FEDERAL_REVIEWER_GATE_OUTPUT={DEFAULT_OUTPUT}")
    print(f"FEDERAL_REVIEWER_GATE_DOC={DEFAULT_DOCUMENTATION}")
    if args.strict and gate["summary"]["status"] != (
        "PASS_ALL_REVIEWER_OBJECTIONS_RESOLVED"
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
