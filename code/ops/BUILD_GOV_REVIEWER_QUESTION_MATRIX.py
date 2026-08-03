from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "gov_reviewer_question_matrix_v1.json"
OUT_DIR = ROOT / "out" / "gov_reviewer_question_matrix"
OUT_JSON = OUT_DIR / "gov_reviewer_question_matrix_latest.json"
OUT_MD = OUT_DIR / "gov_reviewer_question_matrix_latest.md"

CONFIG_SCHEMA = "lumencore.gov_reviewer_question_matrix_config.v1"
OUTPUT_SCHEMA = "lumencore.gov_reviewer_question_matrix.v1"
REQUIRED_ROLE_IDS = {
    "contracting_officer",
    "cybersecurity_reviewer",
    "federal_reviewer",
    "licensing_officer",
    "technical_evaluator",
}
ANSWER_CLASSES = {
    "BLOCKED",
    "PARTIAL_DATED",
    "SUPPORTED",
    "SUPPORTED_NEGATIVE",
}
PRIORITIES = {"critical", "high", "medium"}
SOURCE_FORMATS = {"json", "text"}
FRESHNESS_MODES = {"dated_evidence", "max_age", "timeless"}
SELECTOR_TYPES = {"json_pointer", "source_metadata", "text"}
OPERATORS = {
    "before_snapshot",
    "contains",
    "equals",
    "gte",
    "is_false",
    "is_true",
    "lte",
    "matches_regex",
    "nonempty",
    "not_contains",
    "not_equals",
}
SOURCE_METADATA_FIELDS = {
    "age_hours",
    "freshness_state",
    "generated_utc",
    "parse_state",
    "present",
    "sha256",
}
SENSITIVE_SELECTOR_TOKENS = {
    "api_key",
    "application_number",
    "cage",
    "client_secret",
    "credential",
    "email",
    "firm_pin",
    "meeting",
    "password",
    "private_path",
    "refresh_token",
    "tax",
    "uei",
}
FORBIDDEN_UNQUALIFIED_PHRASES = {
    "award eligible",
    "cmmc compliant",
    "ear compliant",
    "freedom to operate",
    "government approved",
    "guaranteed",
    "independently validated",
    "itar compliant",
    "patent protected",
    "production ready",
    "realized savings",
}
QUESTION_ID_PATTERN = re.compile(r"^[A-Z]{2,4}-\d{3}$")
SOURCE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
ASSERTION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MISSING = object()


class MatrixConfigError(ValueError):
    """Raised when the matrix registry is structurally unsafe or ambiguous."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise MatrixConfigError(f"{field} must be a non-empty UTC timestamp")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MatrixConfigError(f"{field} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise MatrixConfigError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise MatrixConfigError(f"expected a JSON object at {path}")
    return payload


def repo_path(path: Path, *, root: Path = ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def resolve_repo_source(root: Path, relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise MatrixConfigError("source path must be a non-empty repository path")
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise MatrixConfigError(f"source escapes repository root: {relative_path}") from exc
    normalized = candidate.relative_to(root.resolve()).as_posix()
    if normalized.startswith("out/gov_reviewer_question_matrix/"):
        raise MatrixConfigError("matrix outputs cannot be used as matrix sources")
    return candidate


def json_pointer_get(payload: Any, pointer: str) -> Any:
    if pointer == "":
        return payload
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return MISSING
    current = payload
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                return MISSING
            current = current[token]
            continue
        if isinstance(current, list):
            if not token.isdigit():
                return MISSING
            index = int(token)
            if index >= len(current):
                return MISSING
            current = current[index]
            continue
        return MISSING
    return current


def validate_config(config: dict[str, Any], *, root: Path = ROOT) -> None:
    required_top = {
        "claim_boundary",
        "questions",
        "roles",
        "schema",
        "snapshot_utc",
        "sources",
        "title",
    }
    missing_top = sorted(required_top - set(config))
    if missing_top:
        raise MatrixConfigError(f"missing config fields: {missing_top}")
    if config.get("schema") != CONFIG_SCHEMA:
        raise MatrixConfigError(f"schema must be {CONFIG_SCHEMA}")
    parse_utc(config["snapshot_utc"], field="snapshot_utc")

    roles = config["roles"]
    if not isinstance(roles, list) or not roles:
        raise MatrixConfigError("roles must be a non-empty array")
    role_ids = [row.get("role_id") for row in roles if isinstance(row, dict)]
    if set(role_ids) != REQUIRED_ROLE_IDS or len(role_ids) != len(REQUIRED_ROLE_IDS):
        raise MatrixConfigError(
            f"roles must contain exactly {sorted(REQUIRED_ROLE_IDS)}"
        )
    if any(not str(row.get("name", "")).strip() for row in roles):
        raise MatrixConfigError("every role requires a name")

    sources = config["sources"]
    if not isinstance(sources, list) or not sources:
        raise MatrixConfigError("sources must be a non-empty array")
    source_ids: list[str] = []
    source_paths: list[str] = []
    source_formats: dict[str, str] = {}
    for source in sources:
        if not isinstance(source, dict):
            raise MatrixConfigError("every source must be an object")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not SOURCE_ID_PATTERN.fullmatch(source_id):
            raise MatrixConfigError(f"invalid source_id: {source_id!r}")
        source_ids.append(source_id)
        path = source.get("path")
        resolve_repo_source(root, path)
        source_paths.append(path)
        source_format = source.get("format")
        if source_format not in SOURCE_FORMATS:
            raise MatrixConfigError(f"invalid source format for {source_id}")
        source_formats[source_id] = source_format
        if not str(source.get("authority", "")).strip():
            raise MatrixConfigError(f"source {source_id} requires an authority note")
        freshness = source.get("freshness")
        if not isinstance(freshness, dict):
            raise MatrixConfigError(f"source {source_id} requires freshness rules")
        mode = freshness.get("mode")
        if mode not in FRESHNESS_MODES:
            raise MatrixConfigError(f"invalid freshness mode for {source_id}")
        if mode in {"dated_evidence", "max_age"}:
            pointer = freshness.get("timestamp_pointer")
            if not isinstance(pointer, str) or not pointer.startswith("/"):
                raise MatrixConfigError(
                    f"source {source_id} requires timestamp_pointer"
                )
        if mode == "max_age":
            max_age = freshness.get("max_age_hours")
            if not isinstance(max_age, (int, float)) or max_age <= 0:
                raise MatrixConfigError(
                    f"source {source_id} requires positive max_age_hours"
                )
    if len(source_ids) != len(set(source_ids)):
        raise MatrixConfigError("source ids must be unique")
    if len(source_paths) != len(set(source_paths)):
        raise MatrixConfigError("source paths must be unique")

    questions = config["questions"]
    if not isinstance(questions, list) or not questions:
        raise MatrixConfigError("questions must be a non-empty array")
    question_ids: list[str] = []
    role_counts: Counter[str] = Counter()
    for question in questions:
        if not isinstance(question, dict):
            raise MatrixConfigError("every question must be an object")
        question_id = question.get("question_id")
        if not isinstance(question_id, str) or not QUESTION_ID_PATTERN.fullmatch(
            question_id
        ):
            raise MatrixConfigError(f"invalid question_id: {question_id!r}")
        question_ids.append(question_id)
        role_id = question.get("role_id")
        if role_id not in REQUIRED_ROLE_IDS:
            raise MatrixConfigError(f"invalid role for {question_id}: {role_id!r}")
        role_counts[role_id] += 1
        if question.get("priority") not in PRIORITIES:
            raise MatrixConfigError(f"invalid priority for {question_id}")
        text = question.get("question")
        if not isinstance(text, str) or not text.strip().endswith("?"):
            raise MatrixConfigError(f"{question_id} must contain a question")
        if question.get("answer_class") not in ANSWER_CLASSES:
            raise MatrixConfigError(f"invalid answer class for {question_id}")
        for field in ("answer", "decision_use", "next_receipt"):
            if not str(question.get(field, "")).strip():
                raise MatrixConfigError(f"{question_id} requires {field}")
        missing_evidence = question.get("missing_evidence")
        if not isinstance(missing_evidence, list):
            raise MatrixConfigError(f"{question_id} missing_evidence must be an array")
        if (
            question["answer_class"] in {"BLOCKED", "PARTIAL_DATED"}
            and not missing_evidence
        ):
            raise MatrixConfigError(
                f"{question_id} requires explicit missing evidence"
            )
        prohibited = question.get("prohibited_claims")
        if not isinstance(prohibited, list) or not prohibited:
            raise MatrixConfigError(f"{question_id} requires prohibited_claims")
        answer_lower = question["answer"].lower()
        unsafe = sorted(
            phrase
            for phrase in FORBIDDEN_UNQUALIFIED_PHRASES
            if phrase in answer_lower
        )
        if unsafe:
            raise MatrixConfigError(
                f"{question_id} contains unqualified claim phrases: {unsafe}"
            )
        assertions = question.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            raise MatrixConfigError(f"{question_id} requires evidence assertions")
        assertion_ids: list[str] = []
        for assertion in assertions:
            if not isinstance(assertion, dict):
                raise MatrixConfigError(
                    f"{question_id} contains a non-object assertion"
                )
            assertion_id = assertion.get("assertion_id")
            if not isinstance(assertion_id, str) or not ASSERTION_ID_PATTERN.fullmatch(
                assertion_id
            ):
                raise MatrixConfigError(
                    f"{question_id} has invalid assertion_id {assertion_id!r}"
                )
            assertion_ids.append(assertion_id)
            source_id = assertion.get("source_id")
            if source_id not in source_formats:
                raise MatrixConfigError(
                    f"{question_id}/{assertion_id} references unknown source"
                )
            selector = assertion.get("selector")
            if not isinstance(selector, dict):
                raise MatrixConfigError(
                    f"{question_id}/{assertion_id} requires selector"
                )
            selector_type = selector.get("type")
            if selector_type not in SELECTOR_TYPES:
                raise MatrixConfigError(
                    f"{question_id}/{assertion_id} has invalid selector type"
                )
            selector_value = selector.get("value")
            if selector_type == "json_pointer":
                if source_formats[source_id] != "json":
                    raise MatrixConfigError(
                        f"{question_id}/{assertion_id} JSON pointer needs JSON source"
                    )
                if not isinstance(selector_value, str) or not selector_value.startswith(
                    "/"
                ):
                    raise MatrixConfigError(
                        f"{question_id}/{assertion_id} has invalid JSON pointer"
                    )
                pointer_lower = selector_value.lower()
                if any(token in pointer_lower for token in SENSITIVE_SELECTOR_TOKENS):
                    raise MatrixConfigError(
                        f"{question_id}/{assertion_id} selects sensitive material"
                    )
            elif selector_type == "source_metadata":
                if selector_value not in SOURCE_METADATA_FIELDS:
                    raise MatrixConfigError(
                        f"{question_id}/{assertion_id} has invalid metadata selector"
                    )
            elif source_formats[source_id] != "text":
                raise MatrixConfigError(
                    f"{question_id}/{assertion_id} text selector needs text source"
                )
            operator = assertion.get("operator")
            if operator not in OPERATORS:
                raise MatrixConfigError(
                    f"{question_id}/{assertion_id} has invalid operator"
                )
            if operator in {
                "contains",
                "equals",
                "gte",
                "lte",
                "matches_regex",
                "not_contains",
                "not_equals",
            } and "expected" not in assertion:
                raise MatrixConfigError(
                    f"{question_id}/{assertion_id} requires expected"
                )
            if not str(assertion.get("meaning", "")).strip():
                raise MatrixConfigError(
                    f"{question_id}/{assertion_id} requires meaning"
                )
        if len(assertion_ids) != len(set(assertion_ids)):
            raise MatrixConfigError(
                f"{question_id} assertion ids must be unique"
            )
    if len(question_ids) != len(set(question_ids)):
        raise MatrixConfigError("question ids must be unique")
    sparse_roles = sorted(role for role, count in role_counts.items() if count < 5)
    if sparse_roles:
        raise MatrixConfigError(
            f"each role requires at least five questions: {sparse_roles}"
        )


def load_source(
    root: Path,
    source: dict[str, Any],
    *,
    snapshot: datetime,
) -> tuple[dict[str, Any], Any]:
    path = resolve_repo_source(root, source["path"])
    row: dict[str, Any] = {
        "source_id": source["source_id"],
        "path": repo_path(path, root=root),
        "authority": source["authority"],
        "format": source["format"],
        "present": path.is_file(),
        "parse_state": "MISSING",
        "bytes": 0,
        "sha256": None,
        "freshness_mode": source["freshness"]["mode"],
        "freshness_state": "MISSING",
        "generated_utc": None,
        "age_hours": None,
        "max_age_hours": source["freshness"].get("max_age_hours"),
    }
    if not path.is_file():
        return row, MISSING

    raw = path.read_bytes()
    row["bytes"] = len(raw)
    row["sha256"] = bytes_sha256(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        row["parse_state"] = "INVALID_UTF8"
        row["freshness_state"] = "INVALID"
        return row, MISSING

    if source["format"] == "json":
        try:
            content = json.loads(text)
        except json.JSONDecodeError:
            row["parse_state"] = "INVALID_JSON"
            row["freshness_state"] = "INVALID"
            return row, MISSING
        if not isinstance(content, dict):
            row["parse_state"] = "INVALID_JSON_ROOT"
            row["freshness_state"] = "INVALID"
            return row, MISSING
    else:
        content = text
    row["parse_state"] = "PARSED"

    freshness = source["freshness"]
    mode = freshness["mode"]
    if mode == "timeless":
        row["freshness_state"] = "TIMELESS_CONTROL"
        return row, content

    generated = json_pointer_get(content, freshness["timestamp_pointer"])
    if generated is MISSING:
        row["freshness_state"] = "MISSING_TIMESTAMP"
        return row, content
    try:
        generated_dt = parse_utc(
            generated,
            field=f"{source['source_id']}.generated_utc",
        )
    except MatrixConfigError:
        row["freshness_state"] = "INVALID_TIMESTAMP"
        return row, content
    row["generated_utc"] = utc_text(generated_dt)
    age_hours = (snapshot - generated_dt).total_seconds() / 3600
    row["age_hours"] = round(age_hours, 3)
    if mode == "dated_evidence":
        row["freshness_state"] = (
            "FUTURE" if age_hours < 0 else "DATED_EVIDENCE"
        )
    elif age_hours < 0:
        row["freshness_state"] = "FUTURE"
    elif age_hours <= float(freshness["max_age_hours"]):
        row["freshness_state"] = "FRESH"
    else:
        row["freshness_state"] = "STALE"
    return row, content


def contains_value(observed: Any, expected: Any) -> bool:
    if isinstance(observed, str):
        return str(expected) in observed
    if isinstance(observed, list):
        return expected in observed
    if isinstance(observed, dict):
        return expected in observed
    return False


def evaluate_operator(
    operator: str,
    observed: Any,
    expected: Any,
    *,
    snapshot: datetime,
) -> bool:
    if operator == "equals":
        return observed == expected
    if operator == "not_equals":
        return observed != expected
    if operator == "is_true":
        return observed is True
    if operator == "is_false":
        return observed is False
    if operator == "nonempty":
        return observed is not None and observed != "" and bool(observed)
    if operator == "contains":
        return contains_value(observed, expected)
    if operator == "not_contains":
        return not contains_value(observed, expected)
    if operator == "matches_regex":
        return isinstance(observed, str) and re.fullmatch(str(expected), observed) is not None
    if operator == "gte":
        try:
            return observed >= expected
        except TypeError:
            return False
    if operator == "lte":
        try:
            return observed <= expected
        except TypeError:
            return False
    if operator == "before_snapshot":
        try:
            observed_dt = parse_utc(observed, field="assertion observation")
        except MatrixConfigError:
            return False
        return observed_dt < snapshot
    raise MatrixConfigError(f"unsupported operator: {operator}")


def safe_observation(operator: str, observed: Any, passed: bool) -> Any:
    if observed is MISSING:
        return {"present": False}
    if operator in {"contains", "not_contains"}:
        size = len(observed) if isinstance(observed, (dict, list, str)) else None
        return {"condition_met": passed, "observed_size": size}
    if isinstance(observed, (dict, list)):
        return {
            "type": "object" if isinstance(observed, dict) else "array",
            "item_count": len(observed),
        }
    if isinstance(observed, str) and len(observed) > 240:
        return {
            "text_sha256": hashlib.sha256(observed.encode("utf-8")).hexdigest(),
            "character_count": len(observed),
        }
    return observed


def evaluate_assertion(
    assertion: dict[str, Any],
    source_state: dict[str, tuple[dict[str, Any], Any]],
    *,
    snapshot: datetime,
) -> dict[str, Any]:
    source_id = assertion["source_id"]
    source_row, source_content = source_state[source_id]
    selector = assertion["selector"]
    selector_type = selector["type"]
    if source_content is MISSING:
        observed = MISSING
    elif selector_type == "json_pointer":
        observed = json_pointer_get(source_content, selector["value"])
    elif selector_type == "source_metadata":
        observed = source_row.get(selector["value"], MISSING)
    else:
        observed = source_content

    if observed is MISSING:
        passed = False
        reason = (
            f"source_{source_row['parse_state'].lower()}"
            if source_content is MISSING
            else "selector_not_found"
        )
    else:
        passed = evaluate_operator(
            assertion["operator"],
            observed,
            assertion.get("expected"),
            snapshot=snapshot,
        )
        reason = "matched" if passed else "assertion_mismatch"

    return {
        "assertion_id": assertion["assertion_id"],
        "source_id": source_id,
        "source_path": source_row["path"],
        "source_sha256": source_row["sha256"],
        "selector": selector,
        "operator": assertion["operator"],
        "expected": assertion.get("expected"),
        "observed": safe_observation(assertion["operator"], observed, passed),
        "passed": passed,
        "reason": reason,
        "meaning": assertion["meaning"],
    }


def build_matrix(
    config: dict[str, Any],
    *,
    root: Path = ROOT,
    config_path: Path | None = None,
    generator_path: Path | None = None,
) -> dict[str, Any]:
    validate_config(config, root=root)
    snapshot = parse_utc(config["snapshot_utc"], field="snapshot_utc")
    source_state: dict[str, tuple[dict[str, Any], Any]] = {}
    for source in config["sources"]:
        source_state[source["source_id"]] = load_source(
            root,
            source,
            snapshot=snapshot,
        )
    source_manifest = [source_state[row["source_id"]][0] for row in config["sources"]]

    role_questions: dict[str, list[dict[str, Any]]] = {
        role["role_id"]: [] for role in config["roles"]
    }
    gap_register: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    for question in config["questions"]:
        assertions = [
            evaluate_assertion(row, source_state, snapshot=snapshot)
            for row in question["assertions"]
        ]
        verified = all(row["passed"] for row in assertions)
        status = question["answer_class"] if verified else "UNRESOLVED"
        status_counts[status] += 1
        unresolved_reasons = [
            f"{row['source_id']}:{row['assertion_id']}:{row['reason']}"
            for row in assertions
            if not row["passed"]
        ]
        answer = (
            question["answer"]
            if verified
            else "The configured answer could not be verified from the current source set. Treat this question as unresolved until the cited source or assertion is repaired."
        )
        output_question = {
            "question_id": question["question_id"],
            "role_id": question["role_id"],
            "priority": question["priority"],
            "question": question["question"],
            "decision_use": question["decision_use"],
            "proof_state": "VERIFIED_ANSWER" if verified else "UNRESOLVED",
            "status": status,
            "answer": answer,
            "evidence_assertions": assertions,
            "missing_evidence": question["missing_evidence"],
            "next_receipt": question["next_receipt"],
            "prohibited_claims": question["prohibited_claims"],
            "unresolved_reasons": unresolved_reasons,
        }
        role_questions[question["role_id"]].append(output_question)
        if (
            status in {"BLOCKED", "PARTIAL_DATED", "SUPPORTED_NEGATIVE", "UNRESOLVED"}
            and (question["missing_evidence"] or unresolved_reasons)
        ):
            gap_register.append(
                {
                    "gap_id": f"GAP-{question['question_id']}",
                    "question_id": question["question_id"],
                    "role_id": question["role_id"],
                    "priority": question["priority"],
                    "status": status,
                    "missing_evidence": question["missing_evidence"],
                    "next_receipt": question["next_receipt"],
                    "unresolved_reasons": unresolved_reasons,
                }
            )

    roles: list[dict[str, Any]] = []
    for role in config["roles"]:
        questions = role_questions[role["role_id"]]
        role_status_counts = Counter(row["status"] for row in questions)
        roles.append(
            {
                "role_id": role["role_id"],
                "name": role["name"],
                "mandate": role["mandate"],
                "summary": {
                    "question_count": len(questions),
                    "status_counts": dict(sorted(role_status_counts.items())),
                },
                "questions": questions,
            }
        )

    unresolved_count = status_counts["UNRESOLVED"]
    blocked_count = status_counts["BLOCKED"]
    matrix_status = (
        "MATRIX_HAS_UNRESOLVED_QUESTIONS"
        if unresolved_count
        else "SOURCE_BOUND_MATRIX_READY_WITH_EXPLICIT_GAPS"
        if blocked_count
        else "SOURCE_BOUND_MATRIX_READY"
    )
    question_count = len(config["questions"])
    source_rows_for_chain = [
        {
            "source_id": row["source_id"],
            "path": row["path"],
            "sha256": row["sha256"],
            "parse_state": row["parse_state"],
            "freshness_state": row["freshness_state"],
            "generated_utc": row["generated_utc"],
        }
        for row in source_manifest
    ]
    resolved_config_path = config_path or CONFIG_PATH
    resolved_generator_path = generator_path or Path(__file__)
    config_sha256 = (
        file_sha256(resolved_config_path)
        if resolved_config_path.is_file()
        else canonical_sha256(config)
    )
    generator_sha256 = (
        file_sha256(resolved_generator_path)
        if resolved_generator_path.is_file()
        else None
    )

    payload: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "title": config["title"],
        "snapshot_utc": utc_text(snapshot),
        "status": matrix_status,
        "claim_boundary": config["claim_boundary"],
        "controls": {
            "external_action_performed": False,
            "email_sent": False,
            "browser_login_performed": False,
            "portal_action_performed": False,
            "upload_performed": False,
            "certification_performed": False,
            "submission_performed": False,
            "private_identifiers_included": False,
        },
        "summary": {
            "role_count": len(roles),
            "question_count": question_count,
            "verified_answer_count": question_count - unresolved_count,
            "unresolved_question_count": unresolved_count,
            "answer_coverage_pct": round(
                ((question_count - unresolved_count) / question_count) * 100,
                2,
            ),
            "status_counts": dict(sorted(status_counts.items())),
            "gap_count": len(gap_register),
            "source_count": len(source_manifest),
            "missing_source_count": sum(
                1 for row in source_manifest if not row["present"]
            ),
            "stale_source_count": sum(
                1 for row in source_manifest if row["freshness_state"] == "STALE"
            ),
            "invalid_source_count": sum(
                1
                for row in source_manifest
                if row["parse_state"]
                not in {"PARSED", "MISSING"}
            ),
        },
        "roles": roles,
        "proof_gap_register": gap_register,
        "source_manifest": source_manifest,
        "integrity": {
            "hash_algorithm": "sha256",
            "config_sha256": config_sha256,
            "generator_sha256": generator_sha256,
            "source_chain_sha256": canonical_sha256(source_rows_for_chain),
        },
    }
    payload["integrity"]["matrix_sha256"] = canonical_sha256(payload)
    return payload


def verify_matrix_hash(payload: dict[str, Any]) -> bool:
    integrity = payload.get("integrity")
    if not isinstance(integrity, dict):
        return False
    expected = integrity.get("matrix_sha256")
    if not isinstance(expected, str) or not SHA256_PATTERN.fullmatch(expected):
        return False
    candidate = json.loads(json.dumps(payload))
    candidate["integrity"].pop("matrix_sha256", None)
    return canonical_sha256(candidate) == expected


def md_cell(value: Any) -> str:
    if isinstance(value, bool):
        text = "true" if value else "false"
    elif value is None:
        text = ""
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, sort_keys=True, separators=(",", ":"))
    else:
        text = str(value)
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# {payload['title']}",
        "",
        f"Snapshot UTC: `{payload['snapshot_utc']}`",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Executive Boundary",
        "",
        payload["claim_boundary"],
        "",
        "This packet performed no email send, browser login, portal action, upload, certification, signature, or submission.",
        "",
        "## Coverage",
        "",
        "| Measure | Value |",
        "| --- | ---: |",
        f"| Reviewer roles | {summary['role_count']} |",
        f"| Questions | {summary['question_count']} |",
        f"| Verified answers | {summary['verified_answer_count']} |",
        f"| Unresolved questions | {summary['unresolved_question_count']} |",
        f"| Proof gaps | {summary['gap_count']} |",
        f"| Stale sources | {summary['stale_source_count']} |",
        f"| Missing sources | {summary['missing_source_count']} |",
        "",
        "Answer classes: `SUPPORTED` is a bounded affirmative answer; `SUPPORTED_NEGATIVE` is a source-backed no; `PARTIAL_DATED` is usable only with its date and limitation; `BLOCKED` names a gate that is not cleared; `UNRESOLVED` means a cited assertion did not reconcile.",
        "",
    ]

    for role in payload["roles"]:
        lines.extend(
            [
                f"## {role['name']}",
                "",
                role["mandate"],
                "",
            ]
        )
        for question in role["questions"]:
            lines.extend(
                [
                    f"### {question['question_id']} - {question['question']}",
                    "",
                    f"- **Priority:** `{question['priority']}`",
                    f"- **Status:** `{question['status']}`",
                    f"- **Proof state:** `{question['proof_state']}`",
                    f"- **Decision use:** {question['decision_use']}",
                    f"- **Answer:** {question['answer']}",
                    "",
                    "| Evidence assertion | Source | Observation | Result |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for assertion in question["evidence_assertions"]:
                lines.append(
                    "| "
                    + md_cell(assertion["meaning"])
                    + " | `"
                    + md_cell(assertion["source_path"])
                    + "` | `"
                    + md_cell(assertion["observed"])
                    + "` | `"
                    + ("PASS" if assertion["passed"] else "FAIL")
                    + "` |"
                )
            lines.extend(["", "**Missing evidence or remaining gate:**"])
            if question["missing_evidence"]:
                lines.extend(f"- {row}" for row in question["missing_evidence"])
            else:
                lines.append("- None for this bounded answer.")
            lines.extend(
                [
                    "",
                    f"**Next acceptable receipt:** {question['next_receipt']}",
                    "",
                    "**Do not infer:** " + "; ".join(question["prohibited_claims"]),
                    "",
                ]
            )
            if question["unresolved_reasons"]:
                lines.extend(
                    [
                        "**Unresolved assertion codes:** "
                        + ", ".join(
                            f"`{row}`" for row in question["unresolved_reasons"]
                        ),
                        "",
                    ]
                )

    lines.extend(
        [
            "## Proof-Gap Register",
            "",
            "| Gap | Role | Priority | Status | Next acceptable receipt |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    role_names = {row["role_id"]: row["name"] for row in payload["roles"]}
    for gap in payload["proof_gap_register"]:
        lines.append(
            f"| `{gap['gap_id']}` | {md_cell(role_names[gap['role_id']])} | "
            f"`{gap['priority']}` | `{gap['status']}` | {md_cell(gap['next_receipt'])} |"
        )

    lines.extend(
        [
            "",
            "## Source Manifest",
            "",
            "| Source | Freshness | Generated UTC | SHA-256 | Authority |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for source in payload["source_manifest"]:
        sha = source["sha256"] or "missing"
        lines.append(
            f"| `{source['path']}` | `{source['freshness_state']}` | "
            f"`{source['generated_utc'] or ''}` | `{sha}` | {md_cell(source['authority'])} |"
        )
    integrity = payload["integrity"]
    lines.extend(
        [
            "",
            "## Integrity",
            "",
            f"- Config SHA-256: `{integrity['config_sha256']}`",
            f"- Generator SHA-256: `{integrity['generator_sha256']}`",
            f"- Source-chain SHA-256: `{integrity['source_chain_sha256']}`",
            f"- Matrix SHA-256: `{integrity['matrix_sha256']}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    payload: dict[str, Any],
    *,
    out_json: Path = OUT_JSON,
    out_md: Path = OUT_MD,
) -> None:
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    out_md.write_text(render_markdown(payload), encoding="utf-8")


def output_differences(
    payload: dict[str, Any],
    *,
    out_json: Path = OUT_JSON,
    out_md: Path = OUT_MD,
) -> list[str]:
    expected_json = (
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    )
    expected_md = render_markdown(payload)
    differences: list[str] = []
    if not out_json.is_file() or out_json.read_text(encoding="utf-8") != expected_json:
        differences.append(f"stale:{out_json}")
    if not out_md.is_file() or out_md.read_text(encoding="utf-8") != expected_md:
        differences.append(f"stale:{out_md}")
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build the deterministic, source-bound government reviewer "
            "question and proof-gap matrix."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when generated JSON or Markdown is missing or stale.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help="Matrix config path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT_DIR,
        help="Output directory.",
    )
    args = parser.parse_args()

    config_path = args.config.resolve()
    config = read_json(config_path)
    payload = build_matrix(config, root=ROOT, config_path=config_path)
    out_json = args.output_dir / OUT_JSON.name
    out_md = args.output_dir / OUT_MD.name
    if args.check:
        differences = output_differences(
            payload,
            out_json=out_json,
            out_md=out_md,
        )
        if differences:
            raise RuntimeError(", ".join(differences))
        print("government reviewer question matrix outputs are current")
        return 0

    write_outputs(payload, out_json=out_json, out_md=out_md)
    print(repo_path(out_json))
    print(repo_path(out_md))
    print(payload["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
