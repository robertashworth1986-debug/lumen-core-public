"""Build a source-bound, fail-closed cross-agency capability matrix.

The builder reads local repository evidence, evaluates freshness, and emits only
the configured JSON and Markdown controls. It has no email, upload, portal,
certification, signing, or submission capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "cross_agency_capability_matrix_v1.json"
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUTPUT_JSON = SPRINT_DIR / "CROSS_AGENCY_CAPABILITY_MATRIX_2026-07-26.json"
OUTPUT_MD = SPRINT_DIR / "CROSS_AGENCY_CAPABILITY_MATRIX_2026-07-26.md"
WRITE_TARGETS = (OUTPUT_JSON, OUTPUT_MD)
EXTERNAL_ACTION_CAPABILITIES: tuple[str, ...] = ()

CONFIG_SCHEMA = "lumencore.cross_agency_capability_matrix_config.v1"
OUTPUT_SCHEMA = "lumencore.cross_agency_capability_matrix.v1"
CLAIM_CLASSES = {"PROVEN", "BOUNDED", "NOT_PROVEN", "ACTION_TIME"}
SOURCE_FORMATS = {"json", "text"}
SOURCE_ORIGINS = {
    "independent_receipt",
    "internal_receipt",
    "internal_statement",
    "official_receipt",
    "repository_control",
}
FRESHNESS_MODES = {"dated_context", "max_age", "timeless_control"}
FRESHNESS_POLICIES = {
    "action_time_only",
    "current_required",
    "dated_context_allowed",
}
CURRENT_SOURCE_STATES = {"FRESH", "TIMELESS_CONTROL"}
DATED_SOURCE_STATES = CURRENT_SOURCE_STATES | {"DATED_CONTEXT"}
BLOCKING_SOURCE_STATES = {
    "EMPTY",
    "FUTURE",
    "INVALID_JSON",
    "INVALID_TIMESTAMP",
    "MISSING",
    "MISSING_TIMESTAMP",
    "STALE",
    "SYMLINK_REJECTED",
}

REQUIRED_LANES = {
    "acquisition",
    "civilian",
    "defense",
    "energy_lab",
    "regulated_industry",
}
REQUIRED_RESTRICTED_CLAIMS = {
    "agency_endorsement",
    "ato",
    "cmmc_status",
    "federal_past_performance",
    "fedramp_authorization",
    "field_validation",
    "performance_or_superiority",
    "personnel_or_facility_clearance",
    "realized_savings",
}
REQUIRED_ACTION_TIME_FACTS = {
    "data_rights_privacy_and_licensing",
    "deadline_timezone_and_route",
    "deployment_environment_and_acceptance",
    "entity_and_submitter_authority",
    "official_opportunity_instructions",
    "partner_prime_commitments",
    "pricing_cost_and_offer_terms",
    "representations_and_certifications",
    "security_clearance_cui_and_export",
}
EXPECTED_CONTROLS = {
    "action_time_human_confirmation_required": True,
    "autonomous_certification_allowed": False,
    "autonomous_email_send_allowed": False,
    "autonomous_portal_action_allowed": False,
    "autonomous_submission_allowed": False,
    "autonomous_upload_allowed": False,
    "external_action_count": 0,
    "freshness_required": True,
    "independent_evidence_required_for_restricted_claims": True,
    "negative_and_inconclusive_results_preserved": True,
    "source_reference_required": True,
    "stale_or_missing_source_blocks_claim": True,
}

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
REUSABLE_CLAIM_FORBIDDEN_TERMS = {
    "agency endorsement",
    "agency approved",
    "ato",
    "cleared personnel",
    "cmmc",
    "facility clearance",
    "fedramp",
    "field validation",
    "field validated",
    "past performance",
    "performance",
    "realized savings",
    "security clearance",
    "savings",
    "superior",
    "superiority",
}
SENSITIVE_KEY_TOKENS = {
    "api_key",
    "application_number",
    "bank",
    "cage",
    "client_secret",
    "credential",
    "email_address",
    "meeting_credential",
    "otp",
    "password",
    "private_identifier",
    "refresh_token",
    "tax_identifier",
    "uei",
}
MISSING = object()


class MatrixError(ValueError):
    """Raised when the matrix cannot be built without weakening a control."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(value: Any, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise MatrixError(f"{field} must be a non-empty ISO-8601 timestamp")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MatrixError(f"{field} is not a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise MatrixError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MatrixError(f"unreadable JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise MatrixError(f"expected a JSON object: {path}")
    return payload


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
        if isinstance(current, list) and token.isdigit():
            index = int(token)
            if index >= len(current):
                return MISSING
            current = current[index]
            continue
        return MISSING
    return current


def resolve_repo_path(relative_path: str, *, root: Path = ROOT) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise MatrixError("source path must be a non-empty repository-relative path")
    if "\\" in relative_path:
        raise MatrixError(f"source path must use forward slashes: {relative_path}")
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or ".." in pure.parts or not pure.parts:
        raise MatrixError(f"unsafe source path: {relative_path}")
    candidate = root.joinpath(*pure.parts)
    resolved_root = root.resolve()
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise MatrixError(f"source escapes repository root: {relative_path}") from exc
    if resolved in {path.resolve() for path in WRITE_TARGETS}:
        raise MatrixError("matrix outputs cannot be used as matrix sources")
    return candidate


def contains_symlink(path: Path, *, root: Path = ROOT) -> bool:
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def reject_sensitive_keys(value: Any, *, location: str = "config") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in SENSITIVE_KEY_TOKENS):
                raise MatrixError(f"sensitive key is not allowed at {location}.{key}")
            reject_sensitive_keys(child, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reject_sensitive_keys(child, location=f"{location}[{index}]")


def require_nonempty_text(row: dict[str, Any], field: str, *, label: str) -> None:
    if not isinstance(row.get(field), str) or not row[field].strip():
        raise MatrixError(f"{label}.{field} must be non-empty")


def validate_config(config: dict[str, Any], *, root: Path = ROOT) -> None:
    required_top = {
        "action_time_facts",
        "claim_boundary",
        "claim_classes",
        "controls",
        "modules",
        "restricted_claims",
        "reviewer_lanes",
        "schema",
        "snapshot_utc",
        "sources",
        "title",
        "version",
    }
    missing_top = sorted(required_top - set(config))
    if missing_top:
        raise MatrixError(f"missing config fields: {missing_top}")
    if config.get("schema") != CONFIG_SCHEMA or config.get("version") != 1:
        raise MatrixError("unsupported cross-agency matrix config")
    parse_utc(config["snapshot_utc"], field="snapshot_utc")
    require_nonempty_text(config, "title", label="config")
    require_nonempty_text(config, "claim_boundary", label="config")
    if config.get("controls") != EXPECTED_CONTROLS:
        raise MatrixError("matrix controls are not fail-closed")
    if set(config.get("claim_classes", {})) != CLAIM_CLASSES:
        raise MatrixError("claim_classes must define all four controlled classes")
    if any(
        not isinstance(definition, str) or not definition.strip()
        for definition in config["claim_classes"].values()
    ):
        raise MatrixError("every claim class requires a definition")
    reject_sensitive_keys(config)

    sources = config["sources"]
    if not isinstance(sources, list) or not sources:
        raise MatrixError("sources must be a non-empty array")
    source_ids: list[str] = []
    source_paths: list[str] = []
    for source in sources:
        if not isinstance(source, dict):
            raise MatrixError("every source must be an object")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not ID_PATTERN.fullmatch(source_id):
            raise MatrixError(f"invalid source_id: {source_id!r}")
        source_ids.append(source_id)
        path = source.get("path")
        resolve_repo_path(path, root=root)
        source_paths.append(path)
        if source.get("format") not in SOURCE_FORMATS:
            raise MatrixError(f"invalid source format for {source_id}")
        if source.get("evidence_origin") not in SOURCE_ORIGINS:
            raise MatrixError(f"invalid evidence_origin for {source_id}")
        if source.get("required") is not True:
            raise MatrixError(f"source {source_id} must be required")
        require_nonempty_text(source, "authority", label=f"source {source_id}")
        freshness = source.get("freshness")
        if not isinstance(freshness, dict):
            raise MatrixError(f"source {source_id} requires freshness")
        mode = freshness.get("mode")
        if mode not in FRESHNESS_MODES:
            raise MatrixError(f"invalid freshness mode for {source_id}")
        if mode in {"dated_context", "max_age"}:
            pointer = freshness.get("timestamp_pointer")
            observed = freshness.get("observed_utc")
            if pointer is None and observed is None:
                raise MatrixError(f"source {source_id} requires a timestamp source")
            if pointer is not None:
                if source["format"] != "json":
                    raise MatrixError(
                        f"source {source_id} timestamp_pointer requires JSON"
                    )
                if not isinstance(pointer, str) or not pointer.startswith("/"):
                    raise MatrixError(
                        f"source {source_id} has invalid timestamp_pointer"
                    )
            if observed is not None:
                parse_utc(observed, field=f"source {source_id}.observed_utc")
        if mode == "max_age":
            max_age = freshness.get("max_age_hours")
            if not isinstance(max_age, (int, float)) or max_age <= 0:
                raise MatrixError(
                    f"source {source_id} requires positive max_age_hours"
                )
    if len(source_ids) != len(set(source_ids)):
        raise MatrixError("source ids must be unique")
    if len(source_paths) != len(set(source_paths)):
        raise MatrixError("source paths must be unique")
    source_id_set = set(source_ids)

    modules = config["modules"]
    if not isinstance(modules, list) or not modules:
        raise MatrixError("modules must be a non-empty array")
    module_ids: list[str] = []
    for module in modules:
        if not isinstance(module, dict):
            raise MatrixError("every module must be an object")
        module_id = module.get("module_id")
        if not isinstance(module_id, str) or not ID_PATTERN.fullmatch(module_id):
            raise MatrixError(f"invalid module_id: {module_id!r}")
        module_ids.append(module_id)
        for field in ("title", "reusable_claim", "boundary"):
            require_nonempty_text(module, field, label=f"module {module_id}")
        declared_class = module.get("declared_class")
        if declared_class not in CLAIM_CLASSES:
            raise MatrixError(f"invalid claim class for {module_id}")
        policy = module.get("freshness_policy")
        if policy not in FRESHNESS_POLICIES:
            raise MatrixError(f"invalid freshness policy for {module_id}")
        if declared_class == "PROVEN" and policy != "current_required":
            raise MatrixError(f"PROVEN module {module_id} must require current sources")
        if declared_class == "ACTION_TIME" and policy != "action_time_only":
            raise MatrixError(
                f"ACTION_TIME module {module_id} must be action_time_only"
            )
        refs = module.get("source_refs")
        if not isinstance(refs, list) or not refs or not set(refs) <= source_id_set:
            raise MatrixError(f"module {module_id} has invalid source_refs")
        if len(refs) != len(set(refs)):
            raise MatrixError(f"module {module_id} has duplicate source_refs")
        concerns = module.get("reviewer_concerns")
        if not isinstance(concerns, dict) or not concerns:
            raise MatrixError(f"module {module_id} requires reviewer_concerns")
        if not set(concerns) <= REQUIRED_LANES:
            raise MatrixError(f"module {module_id} has an invalid reviewer lane")
        if any(
            not isinstance(rows, list)
            or not rows
            or any(not isinstance(row, str) or not row.strip() for row in rows)
            for rows in concerns.values()
        ):
            raise MatrixError(f"module {module_id} has invalid reviewer concerns")
        deliverables = module.get("deliverables")
        if (
            not isinstance(deliverables, list)
            or not deliverables
            or any(not isinstance(row, str) or not row.strip() for row in deliverables)
        ):
            raise MatrixError(f"module {module_id} requires deliverables")
        if declared_class in {"PROVEN", "BOUNDED"}:
            claim_lower = module["reusable_claim"].lower()
            unsafe_terms = sorted(
                term
                for term in REUSABLE_CLAIM_FORBIDDEN_TERMS
                if term in claim_lower
            )
            if unsafe_terms:
                raise MatrixError(
                    f"module {module_id} contains restricted reusable terms: "
                    f"{unsafe_terms}"
                )
    if len(module_ids) != len(set(module_ids)):
        raise MatrixError("module ids must be unique")
    module_id_set = set(module_ids)
    if set(module["declared_class"] for module in modules) != CLAIM_CLASSES:
        raise MatrixError("modules must exercise all four claim classes")

    restricted = config["restricted_claims"]
    if not isinstance(restricted, list) or not restricted:
        raise MatrixError("restricted_claims must be a non-empty array")
    restricted_ids = [row.get("claim_id") for row in restricted if isinstance(row, dict)]
    if set(restricted_ids) != REQUIRED_RESTRICTED_CLAIMS:
        raise MatrixError("restricted_claims does not cover the required claim gates")
    if len(restricted_ids) != len(set(restricted_ids)):
        raise MatrixError("restricted claim ids must be unique")
    for claim in restricted:
        claim_id = claim["claim_id"]
        for field in ("label", "required_evidence", "current_boundary"):
            require_nonempty_text(claim, field, label=f"claim {claim_id}")
        if claim.get("current_state") not in {"NOT_PROVEN", "PROVEN"}:
            raise MatrixError(f"invalid current_state for {claim_id}")
        if claim.get("independent_evidence_required") is not True:
            raise MatrixError(f"{claim_id} must require independent evidence")
        if not isinstance(claim.get("official_authority_required"), bool):
            raise MatrixError(f"{claim_id} requires official_authority_required")
        refs = claim.get("source_refs")
        if not isinstance(refs, list) or not refs or not set(refs) <= source_id_set:
            raise MatrixError(f"claim {claim_id} has invalid source_refs")

    action_facts = config["action_time_facts"]
    if not isinstance(action_facts, list) or not action_facts:
        raise MatrixError("action_time_facts must be a non-empty array")
    action_ids = [row.get("fact_id") for row in action_facts if isinstance(row, dict)]
    if set(action_ids) != REQUIRED_ACTION_TIME_FACTS:
        raise MatrixError("action_time_facts does not cover the required fact gates")
    if len(action_ids) != len(set(action_ids)):
        raise MatrixError("action-time fact ids must be unique")
    for fact in action_facts:
        fact_id = fact["fact_id"]
        if fact.get("claim_class") != "ACTION_TIME":
            raise MatrixError(f"fact {fact_id} must be ACTION_TIME")
        if fact.get("human_confirmation_required") is not True:
            raise MatrixError(f"fact {fact_id} must require human confirmation")
        for field in ("fact", "required_action_time_evidence"):
            require_nonempty_text(fact, field, label=f"fact {fact_id}")
        refs = fact.get("source_refs")
        if not isinstance(refs, list) or not refs or not set(refs) <= source_id_set:
            raise MatrixError(f"fact {fact_id} has invalid source_refs")

    lanes = config["reviewer_lanes"]
    if not isinstance(lanes, list) or not lanes:
        raise MatrixError("reviewer_lanes must be a non-empty array")
    lane_ids = [row.get("lane_id") for row in lanes if isinstance(row, dict)]
    if set(lane_ids) != REQUIRED_LANES or len(lane_ids) != len(REQUIRED_LANES):
        raise MatrixError("reviewer_lanes must contain exactly five required lanes")
    referenced_modules: set[str] = set()
    for lane in lanes:
        lane_id = lane["lane_id"]
        require_nonempty_text(lane, "label", label=f"lane {lane_id}")
        require_nonempty_text(lane, "reusable_output", label=f"lane {lane_id}")
        concerns = lane.get("reviewer_concerns")
        if (
            not isinstance(concerns, list)
            or not concerns
            or any(not isinstance(row, str) or not row.strip() for row in concerns)
        ):
            raise MatrixError(f"lane {lane_id} requires reviewer_concerns")
        lane_modules = lane.get("module_ids")
        if (
            not isinstance(lane_modules, list)
            or not lane_modules
            or not set(lane_modules) <= module_id_set
        ):
            raise MatrixError(f"lane {lane_id} has invalid module_ids")
        referenced_modules.update(lane_modules)
        if not set(lane.get("restricted_claim_ids", [])) <= set(restricted_ids):
            raise MatrixError(f"lane {lane_id} has invalid restricted_claim_ids")
        if not set(lane.get("action_time_fact_ids", [])) <= set(action_ids):
            raise MatrixError(f"lane {lane_id} has invalid action_time_fact_ids")
    if referenced_modules != module_id_set:
        missing = sorted(module_id_set - referenced_modules)
        raise MatrixError(f"unmapped capability modules: {missing}")


def inspect_source(
    source: dict[str, Any],
    *,
    as_of: datetime,
    root: Path = ROOT,
) -> tuple[dict[str, Any], Any]:
    source_id = source["source_id"]
    path = resolve_repo_path(source["path"], root=root)
    row: dict[str, Any] = {
        "source_id": source_id,
        "path": source["path"],
        "format": source["format"],
        "evidence_origin": source["evidence_origin"],
        "authority": source["authority"],
        "required": source["required"],
        "present": False,
        "bytes": 0,
        "sha256": "",
        "parse_state": "NOT_READ",
        "freshness_mode": source["freshness"]["mode"],
        "freshness_state": "MISSING",
        "generated_utc": None,
        "age_hours": None,
        "max_age_hours": source["freshness"].get("max_age_hours"),
    }
    if contains_symlink(path, root=root):
        row["parse_state"] = "SYMLINK_REJECTED"
        row["freshness_state"] = "SYMLINK_REJECTED"
        return row, None
    if not path.is_file():
        return row, None
    row["present"] = True
    row["bytes"] = path.stat().st_size
    if row["bytes"] <= 0:
        row["parse_state"] = "EMPTY"
        row["freshness_state"] = "EMPTY"
        return row, None
    row["sha256"] = file_sha256(path)

    if source["format"] == "json":
        try:
            content: Any = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            row["parse_state"] = "INVALID_JSON"
            row["freshness_state"] = "INVALID_JSON"
            return row, None
        row["parse_state"] = "JSON_READY"
    else:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            row["parse_state"] = "NOT_READ"
            return row, None
        row["parse_state"] = "TEXT_READY"

    freshness = source["freshness"]
    mode = freshness["mode"]
    if mode == "timeless_control":
        row["freshness_state"] = "TIMELESS_CONTROL"
        return row, content

    timestamp_value: Any = freshness.get("observed_utc", MISSING)
    if "timestamp_pointer" in freshness:
        timestamp_value = json_pointer_get(content, freshness["timestamp_pointer"])
    if timestamp_value is MISSING:
        row["freshness_state"] = "MISSING_TIMESTAMP"
        return row, content
    try:
        generated = parse_utc(
            timestamp_value,
            field=f"source {source_id} timestamp",
        )
    except MatrixError:
        row["freshness_state"] = "INVALID_TIMESTAMP"
        return row, content

    row["generated_utc"] = utc_text(generated)
    age_hours = (as_of - generated).total_seconds() / 3600
    row["age_hours"] = round(max(0.0, age_hours), 3)
    if age_hours < -(5 / 60):
        row["freshness_state"] = "FUTURE"
    elif mode == "dated_context":
        row["freshness_state"] = "DATED_CONTEXT"
    elif age_hours <= float(freshness["max_age_hours"]):
        row["freshness_state"] = "FRESH"
    else:
        row["freshness_state"] = "STALE"
    return row, content


def source_states_allowed(module: dict[str, Any]) -> set[str]:
    policy = module["freshness_policy"]
    if policy == "current_required":
        return CURRENT_SOURCE_STATES
    if policy == "dated_context_allowed":
        return DATED_SOURCE_STATES
    return DATED_SOURCE_STATES


def validate_restricted_promotions(
    config: dict[str, Any],
    source_manifest: list[dict[str, Any]],
) -> None:
    source_by_id = {row["source_id"]: row for row in source_manifest}
    for claim in config["restricted_claims"]:
        if claim["current_state"] != "PROVEN":
            continue
        rows = [source_by_id[source_id] for source_id in claim["source_refs"]]
        if any(row["freshness_state"] not in CURRENT_SOURCE_STATES for row in rows):
            raise MatrixError(
                f"restricted claim {claim['claim_id']} lacks current evidence"
            )
        origins = {row["evidence_origin"] for row in rows}
        if "independent_receipt" not in origins:
            raise MatrixError(
                f"restricted claim {claim['claim_id']} lacks independent evidence"
            )
        if claim["official_authority_required"] and "official_receipt" not in origins:
            raise MatrixError(
                f"restricted claim {claim['claim_id']} lacks official authority"
            )


def build_matrix_from_config(
    config: dict[str, Any],
    *,
    as_of_utc: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    validate_config(config, root=root)
    as_of = parse_utc(as_of_utc, field="as_of_utc")

    source_manifest: list[dict[str, Any]] = []
    for source in config["sources"]:
        row, _ = inspect_source(source, as_of=as_of, root=root)
        source_manifest.append(row)
    source_manifest.sort(key=lambda row: row["source_id"])
    source_by_id = {row["source_id"]: row for row in source_manifest}
    validate_restricted_promotions(config, source_manifest)

    blockers: list[str] = []
    for row in source_manifest:
        if row["required"] and row["freshness_state"] in BLOCKING_SOURCE_STATES:
            blockers.append(
                f"source:{row['source_id']}:{row['freshness_state']}"
            )

    modules: list[dict[str, Any]] = []
    for source_module in config["modules"]:
        source_rows = [
            source_by_id[source_id] for source_id in source_module["source_refs"]
        ]
        allowed = source_states_allowed(source_module)
        evidence_blockers = [
            f"{row['source_id']}:{row['freshness_state']}"
            for row in source_rows
            if row["freshness_state"] not in allowed
        ]
        declared_class = source_module["declared_class"]
        if declared_class in {"PROVEN", "BOUNDED"} and evidence_blockers:
            effective_class = "NOT_PROVEN"
            blockers.extend(
                f"module:{source_module['module_id']}:{reason}"
                for reason in evidence_blockers
            )
        else:
            effective_class = declared_class
        modules.append(
            {
                **source_module,
                "effective_class": effective_class,
                "claim_usable": effective_class in {"PROVEN", "BOUNDED"}
                and not evidence_blockers,
                "external_action_authorized": False,
                "evidence_blockers": evidence_blockers,
                "resolved_sources": [
                    {
                        "source_id": row["source_id"],
                        "freshness_state": row["freshness_state"],
                        "sha256": row["sha256"],
                    }
                    for row in source_rows
                ],
            }
        )
    modules.sort(key=lambda row: row["module_id"])
    module_by_id = {row["module_id"]: row for row in modules}

    restricted_claims = []
    for claim in config["restricted_claims"]:
        proven = claim["current_state"] == "PROVEN"
        restricted_claims.append(
            {
                **claim,
                "claim_allowed": proven,
                "external_use_authorized": False,
                "resolved_sources": [
                    {
                        "source_id": source_id,
                        "freshness_state": source_by_id[source_id][
                            "freshness_state"
                        ],
                        "evidence_origin": source_by_id[source_id][
                            "evidence_origin"
                        ],
                    }
                    for source_id in claim["source_refs"]
                ],
            }
        )
    restricted_claims.sort(key=lambda row: row["claim_id"])

    action_time_facts = []
    for fact in config["action_time_facts"]:
        action_time_facts.append(
            {
                **fact,
                "resolved_state": "ACTION_TIME_REVERIFY_REQUIRED",
                "external_action_authorized": False,
                "resolved_sources": [
                    {
                        "source_id": source_id,
                        "freshness_state": source_by_id[source_id][
                            "freshness_state"
                        ],
                    }
                    for source_id in fact["source_refs"]
                ],
            }
        )
    action_time_facts.sort(key=lambda row: row["fact_id"])
    action_fact_by_id = {row["fact_id"]: row for row in action_time_facts}
    restricted_by_id = {row["claim_id"]: row for row in restricted_claims}

    reviewer_lanes = []
    for lane in config["reviewer_lanes"]:
        reviewer_lanes.append(
            {
                **lane,
                "modules": [
                    {
                        "module_id": module_id,
                        "effective_class": module_by_id[module_id][
                            "effective_class"
                        ],
                        "claim_usable": module_by_id[module_id]["claim_usable"],
                    }
                    for module_id in lane["module_ids"]
                ],
                "restricted_claims": [
                    {
                        "claim_id": claim_id,
                        "current_state": restricted_by_id[claim_id][
                            "current_state"
                        ],
                        "claim_allowed": restricted_by_id[claim_id][
                            "claim_allowed"
                        ],
                    }
                    for claim_id in lane["restricted_claim_ids"]
                ],
                "action_time_facts": [
                    {
                        "fact_id": fact_id,
                        "resolved_state": action_fact_by_id[fact_id][
                            "resolved_state"
                        ],
                    }
                    for fact_id in lane["action_time_fact_ids"]
                ],
                "external_action_authorized": False,
            }
        )
    reviewer_lanes.sort(key=lambda row: row["lane_id"])

    freshness_counts = Counter(
        row["freshness_state"] for row in source_manifest
    )
    effective_class_counts = Counter(row["effective_class"] for row in modules)
    declared_class_counts = Counter(row["declared_class"] for row in modules)
    status = (
        "CROSS_AGENCY_MATRIX_BLOCKED_SOURCE_OR_CONTROL"
        if blockers
        else "READY_BOUNDED_CROSS_AGENCY_REUSE_NO_EXTERNAL_ACTION"
    )
    source_chain_rows = [
        {
            "source_id": row["source_id"],
            "path": row["path"],
            "bytes": row["bytes"],
            "sha256": row["sha256"],
            "freshness_state": row["freshness_state"],
        }
        for row in source_manifest
    ]

    payload: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "version": 1,
        "title": config["title"],
        "status": status,
        "as_of_utc": utc_text(as_of),
        "summary": {
            "source_count": len(source_manifest),
            "freshness_counts": dict(sorted(freshness_counts.items())),
            "module_count": len(modules),
            "declared_class_counts": {
                claim_class: declared_class_counts.get(claim_class, 0)
                for claim_class in sorted(CLAIM_CLASSES)
            },
            "effective_class_counts": {
                claim_class: effective_class_counts.get(claim_class, 0)
                for claim_class in sorted(CLAIM_CLASSES)
            },
            "reviewer_lane_count": len(reviewer_lanes),
            "restricted_claim_count": len(restricted_claims),
            "restricted_claim_allowed_count": sum(
                row["claim_allowed"] for row in restricted_claims
            ),
            "action_time_fact_count": len(action_time_facts),
            "blocker_count": len(blockers),
            "external_action_count": 0,
        },
        "controls": config["controls"],
        "claim_classes": config["claim_classes"],
        "source_manifest": source_manifest,
        "modules": modules,
        "reviewer_lanes": reviewer_lanes,
        "restricted_claims": restricted_claims,
        "action_time_facts": action_time_facts,
        "blockers": sorted(set(blockers)),
        "claim_boundary": config["claim_boundary"],
        "integrity": {
            "config_sha256": canonical_sha256(config),
            "builder_sha256": file_sha256(Path(__file__)),
            "source_chain_sha256": canonical_sha256(source_chain_rows),
            "matrix_sha256": "",
        },
        "external_actions": {
            "capabilities": list(EXTERNAL_ACTION_CAPABILITIES),
            "performed": [],
            "send_allowed": False,
            "upload_allowed": False,
            "portal_action_allowed": False,
            "submission_allowed": False,
        },
    }
    payload["integrity"]["matrix_sha256"] = canonical_sha256(payload)
    return payload


def build_matrix(
    config_path: Path = CONFIG_PATH,
    *,
    as_of_utc: str,
    root: Path = ROOT,
) -> dict[str, Any]:
    return build_matrix_from_config(
        read_json(config_path),
        as_of_utc=as_of_utc,
        root=root,
    )


def verify_matrix_sha256(payload: dict[str, Any]) -> bool:
    expected = payload.get("integrity", {}).get("matrix_sha256")
    if not isinstance(expected, str) or not expected:
        return False
    candidate = json.loads(json.dumps(payload))
    candidate["integrity"]["matrix_sha256"] = ""
    return canonical_sha256(candidate) == expected


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# LumenCore Cross-Agency Capability Statement Control",
        "",
        f"- As of UTC: `{payload['as_of_utc']}`",
        f"- Status: `{payload['status']}`",
        f"- Sources: `{payload['summary']['source_count']}`",
        f"- Reusable modules: `{payload['summary']['module_count']}`",
        f"- Reviewer lanes: `{payload['summary']['reviewer_lane_count']}`",
        f"- Restricted claims allowed: `{payload['summary']['restricted_claim_allowed_count']}`",
        f"- External actions performed: `{payload['summary']['external_action_count']}`",
        f"- Matrix SHA-256: `{payload['integrity']['matrix_sha256']}`",
        "",
        "## Operating Rule",
        "",
        "Use only a module whose effective class is `PROVEN` or `BOUNDED`. "
        "Keep `NOT_PROVEN` conclusions blocked. Reverify every `ACTION_TIME` "
        "fact against its current authoritative source and obtain the required "
        "human decision before external use.",
        "",
        "This builder cannot send email, upload files, act in a portal, certify, "
        "sign, or submit.",
        "",
        "## Claim Classes",
        "",
        "| Class | Meaning |",
        "|---|---|",
    ]
    for claim_class in ("PROVEN", "BOUNDED", "NOT_PROVEN", "ACTION_TIME"):
        lines.append(
            f"| `{claim_class}` | {payload['claim_classes'][claim_class]} |"
        )

    lines.extend(
        [
            "",
            "## Source Freshness",
            "",
            "| Source | Origin | Freshness | Age hours | SHA-256 |",
            "|---|---|---|---:|---|",
        ]
    )
    for source in payload["source_manifest"]:
        age = "" if source["age_hours"] is None else f"{source['age_hours']:.3f}"
        lines.append(
            f"| `{source['path']}` | `{source['evidence_origin']}` | "
            f"`{source['freshness_state']}` | {age} | `{source['sha256']}` |"
        )

    lines.extend(
        [
            "",
            "## Reusable Modules",
            "",
            "| Module | Declared | Effective | Reusable statement | Boundary |",
            "|---|---|---|---|---|",
        ]
    )
    for module in payload["modules"]:
        lines.append(
            f"| `{module['module_id']}` | `{module['declared_class']}` | "
            f"`{module['effective_class']}` | {module['reusable_claim']} | "
            f"{module['boundary']} |"
        )

    lines.extend(["", "## Reviewer Lanes", ""])
    module_by_id = {row["module_id"]: row for row in payload["modules"]}
    claim_by_id = {
        row["claim_id"]: row for row in payload["restricted_claims"]
    }
    fact_by_id = {row["fact_id"]: row for row in payload["action_time_facts"]}
    for lane in payload["reviewer_lanes"]:
        lines.extend(
            [
                f"### {lane['label']}",
                "",
                f"Reusable output: {lane['reusable_output']}",
                "",
                "Reviewer concerns:",
                "",
            ]
        )
        lines.extend(f"- {concern}" for concern in lane["reviewer_concerns"])
        lines.extend(["", "Controlled modules:", ""])
        for module_id in lane["module_ids"]:
            module = module_by_id[module_id]
            lines.append(
                f"- `{module_id}` - `{module['effective_class']}` - "
                f"{module['reusable_claim']}"
            )
        lines.extend(["", "Restricted conclusions:", ""])
        for claim_id in lane["restricted_claim_ids"]:
            claim = claim_by_id[claim_id]
            lines.append(
                f"- `{claim_id}` - `{claim['current_state']}` - "
                f"{claim['current_boundary']}"
            )
        lines.extend(["", "Action-time facts:", ""])
        for fact_id in lane["action_time_fact_ids"]:
            fact = fact_by_id[fact_id]
            lines.append(f"- `{fact_id}` - {fact['fact']}")
        lines.append("")

    lines.extend(
        [
            "## Restricted Claim Gate",
            "",
            "| Claim | State | Allowed | Evidence required to change state |",
            "|---|---|---:|---|",
        ]
    )
    for claim in payload["restricted_claims"]:
        lines.append(
            f"| `{claim['claim_id']}` | `{claim['current_state']}` | "
            f"`{str(claim['claim_allowed']).lower()}` | "
            f"{claim['required_evidence']} |"
        )

    lines.extend(
        [
            "",
            "## Action-Time Fact Gate",
            "",
            "| Fact | State | Required action-time evidence |",
            "|---|---|---|",
        ]
    )
    for fact in payload["action_time_facts"]:
        lines.append(
            f"| `{fact['fact_id']}` | `{fact['resolved_state']}` | "
            f"{fact['required_action_time_evidence']} |"
        )

    lines.extend(["", "## Fail-Closed Blockers", ""])
    if payload["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in payload["blockers"])
    else:
        lines.append(
            "- None for generating this bounded matrix. External actions and "
            "restricted claims remain blocked by their separate controls."
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def write_outputs(payload: dict[str, Any]) -> None:
    OUTPUT_JSON.write_text(render_json(payload), encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")


def outputs_match(payload: dict[str, Any]) -> bool:
    if not OUTPUT_JSON.is_file() or not OUTPUT_MD.is_file():
        return False
    return (
        OUTPUT_JSON.read_text(encoding="utf-8") == render_json(payload)
        and OUTPUT_MD.read_text(encoding="utf-8") == render_markdown(payload)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed cross-agency capability matrix."
    )
    parser.add_argument(
        "--as-of-utc",
        help="UTC evaluation timestamp. Defaults to config snapshot_utc.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate that the generated files match without writing.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the machine-readable matrix without writing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = read_json(CONFIG_PATH)
    as_of_utc = args.as_of_utc or config["snapshot_utc"]
    payload = build_matrix_from_config(config, as_of_utc=as_of_utc)
    if args.stdout:
        print(render_json(payload), end="")
        return 0 if not payload["blockers"] else 1
    if args.check:
        print(
            json.dumps(
                {
                    "schema": payload["schema"],
                    "status": payload["status"],
                    "outputs_match": outputs_match(payload),
                    "matrix_sha256_valid": verify_matrix_sha256(payload),
                    "external_action_count": payload["summary"][
                        "external_action_count"
                    ],
                },
                indent=2,
            )
        )
        return 0 if outputs_match(payload) and verify_matrix_sha256(payload) else 1
    write_outputs(payload)
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "status": payload["status"],
                "json": OUTPUT_JSON.relative_to(ROOT).as_posix(),
                "markdown": OUTPUT_MD.relative_to(ROOT).as_posix(),
                "matrix_sha256": payload["integrity"]["matrix_sha256"],
                "external_action_count": payload["summary"][
                    "external_action_count"
                ],
            },
            indent=2,
        )
    )
    return 0 if not payload["blockers"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
