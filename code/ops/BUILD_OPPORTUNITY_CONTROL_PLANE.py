"""Build a fail-closed local opportunity control plane.

The builder ingests only local JSON or JSONL records that cite public URLs. It
normalizes government, job, licensing, venture-partner, and pilot leads into
deterministic ranked queues and draft-preparation actions. It has no network,
browser, authentication, messaging, posting, application, signing,
certification, or submission capability.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "opportunity_control_plane_v1.json"
OUT_DIR = ROOT / "out" / "opportunity_control_plane"
INBOX_DIR = OUT_DIR / "inbox"
LATEST_JSON = OUT_DIR / "opportunity_control_plane_latest.json"
LATEST_MD = OUT_DIR / "opportunity_control_plane_latest.md"

OUTPUT_SCHEMA = "lumencore.opportunity_control_plane.v1"
INPUT_SCHEMA = "lumencore.public_opportunity_leads.v1"
RECORD_SCHEMA = "lumencore.public_opportunity_lead.v1"
SUPPORTED_LANES = (
    "government",
    "job",
    "licensing",
    "venture_partner",
    "pilot",
)
SAFE_CONTROL_EXPECTATIONS = {
    "action_time_human_approval_required": True,
    "authenticated_access_allowed": False,
    "autonomous_apply_allowed": False,
    "autonomous_certify_allowed": False,
    "autonomous_login_allowed": False,
    "autonomous_post_allowed": False,
    "autonomous_send_allowed": False,
    "autonomous_sign_allowed": False,
    "autonomous_submit_allowed": False,
    "duplicate_suppression_required": True,
    "eligibility_uncertainty_fail_closed": True,
    "external_mutation_allowed": False,
    "local_files_only": True,
    "missing_claim_boundary_fail_closed": True,
    "missing_source_url_fail_closed": True,
    "network_access_allowed": False,
    "stale_source_fail_closed": True,
}
RECORD_FIELDS = {
    "canonical_opportunity_url",
    "claim_boundary",
    "compensation",
    "deadline",
    "eligibility",
    "fit",
    "lane",
    "lead_origin",
    "organization",
    "record_id",
    "reviewer_answers",
    "source",
    "summary",
    "title",
}
SOURCE_FIELDS = {
    "authority",
    "observed_date",
    "observed_precision",
    "observed_utc",
    "published_utc",
    "updated_utc",
    "url",
    "verification_state",
}
DEADLINE_FIELDS = {"at_utc", "local", "source_text", "state", "timezone"}
ELIGIBILITY_FIELDS = {"basis", "state", "unresolved_requirements"}
FIT_FIELDS = {"basis", "score"}
ANSWER_FIELDS = {"answer", "source_url", "status"}
COMPENSATION_FIELDS = {"source_text", "state"}
TRACKING_QUERY_NAMES = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")
WHITESPACE_RE = re.compile(r"\s+")
MAX_TEXT_LENGTH = 20_000


class OpportunityControlError(ValueError):
    """Raised when a control-plane invariant is not met."""


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OpportunityControlError(f"Unreadable JSON object: {path.name}") from exc
    if not isinstance(payload, dict):
        raise OpportunityControlError(f"Expected JSON object: {path.name}")
    return payload


def canonical_json_sha256(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_aware_timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise OpportunityControlError(f"{label} must be a nonempty timestamp")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise OpportunityControlError(f"{label} is invalid") from exc
    if parsed.tzinfo is None:
        raise OpportunityControlError(f"{label} must include a timezone")
    return parsed


def utc_iso(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def canonical_utc_timestamp(value: Any, label: str) -> tuple[datetime, str]:
    parsed = parse_aware_timestamp(value, label).astimezone(timezone.utc)
    canonical = utc_iso(parsed)
    if value != canonical:
        raise OpportunityControlError(f"{label} must be canonical UTC with a Z suffix")
    return parsed, canonical


def normalized_text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise OpportunityControlError(f"{label} must be text")
    text = WHITESPACE_RE.sub(" ", value).strip()
    if not text and not allow_empty:
        raise OpportunityControlError(f"{label} must not be empty")
    if len(text) > MAX_TEXT_LENGTH:
        raise OpportunityControlError(f"{label} exceeds the text limit")
    return text


def require_exact_fields(
    payload: dict[str, Any],
    expected: set[str],
    label: str,
) -> None:
    actual = set(payload)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if extra:
            details.append(f"extra={','.join(extra)}")
        raise OpportunityControlError(f"{label} fields are invalid ({'; '.join(details)})")


def validate_public_url(value: Any, label: str) -> tuple[str, str]:
    original = normalized_text(value, label)
    if len(original) > 2048:
        raise OpportunityControlError(f"{label} exceeds the URL limit")
    split = urlsplit(original)
    if split.scheme.lower() not in {"https", "http"}:
        raise OpportunityControlError(f"{label} must use HTTP or HTTPS")
    if split.username or split.password:
        raise OpportunityControlError(f"{label} must not contain credentials")
    host = (split.hostname or "").rstrip(".").lower()
    if not host:
        raise OpportunityControlError(f"{label} must contain a hostname")
    if host == "localhost" or host.endswith(".localhost"):
        raise OpportunityControlError(f"{label} must identify a public host")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            raise OpportunityControlError(f"{label} must identify a public host")
    else:
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise OpportunityControlError(f"{label} must identify a public host")

    try:
        port = split.port
    except ValueError as exc:
        raise OpportunityControlError(f"{label} has an invalid port") from exc
    netloc = host
    if port is not None and not (
        (split.scheme.lower() == "https" and port == 443)
        or (split.scheme.lower() == "http" and port == 80)
    ):
        netloc = f"{host}:{port}"

    query_pairs = []
    for key, item in parse_qsl(split.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in TRACKING_QUERY_NAMES:
            continue
        query_pairs.append((key, item))
    query_pairs.sort()
    path = split.path or "/"
    if path != "/":
        path = path.rstrip("/")
    canonical = urlunsplit(
        (
            split.scheme.lower(),
            netloc,
            path,
            urlencode(query_pairs, doseq=True),
            "",
        )
    )
    return original, canonical


def find_prohibited_keys(value: Any, fragments: set[str], prefix: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            normalized = re.sub(r"[^a-z0-9]+", "_", key_text.lower()).strip("_")
            location = f"{prefix}.{key_text}" if prefix else key_text
            if any(fragment in normalized for fragment in fragments):
                findings.append(location)
            findings.extend(find_prohibited_keys(item, fragments, location))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(find_prohibited_keys(item, fragments, f"{prefix}[{index}]"))
    return findings


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != "lumencore.opportunity_control_plane_config.v1":
        raise OpportunityControlError("Unsupported opportunity control-plane config schema")
    if config.get("version") != 1:
        raise OpportunityControlError("Unsupported opportunity control-plane config version")
    if config.get("input_schema") != INPUT_SCHEMA:
        raise OpportunityControlError("Input schema binding is invalid")
    if config.get("record_schema") != RECORD_SCHEMA:
        raise OpportunityControlError("Record schema binding is invalid")
    if config.get("controls") != SAFE_CONTROL_EXPECTATIONS:
        raise OpportunityControlError("Fail-closed controls were weakened or changed")
    if config.get("allowed_lead_origins") != [
        "VERIFIED_PUBLIC_SOURCE",
        "JOB_ALERT_METADATA",
    ]:
        raise OpportunityControlError("Allowed lead origins are invalid")
    if config.get("allowed_source_verification_states") != [
        "PUBLIC_SOURCE_OBSERVED",
        "PUBLIC_SOURCE_RECHECK_REQUIRED",
    ]:
        raise OpportunityControlError("Source verification states are invalid")
    if config.get("allowed_source_observation_precisions") != [
        "EXACT_TIME",
        "DATE_ONLY",
    ]:
        raise OpportunityControlError("Source observation precisions are invalid")
    if config.get("allowed_compensation_states") != [
        "STATED",
        "PARTIAL",
        "CAVEAT",
        "UNKNOWN",
        "NOT_APPLICABLE",
    ]:
        raise OpportunityControlError("Compensation states are invalid")

    limits = config.get("ingest_limits")
    if not isinstance(limits, dict):
        raise OpportunityControlError("Ingest limits are missing")
    if limits.get("accepted_extensions") != [".json", ".jsonl"]:
        raise OpportunityControlError("Accepted input extensions are invalid")
    for key in (
        "max_file_bytes",
        "max_future_observation_skew_seconds",
        "max_records_per_file",
    ):
        value = limits.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise OpportunityControlError(f"Config {key} must be a positive integer")

    default_input_paths = config.get("default_input_paths")
    if not isinstance(default_input_paths, list) or not default_input_paths:
        raise OpportunityControlError("Default input paths must be a nonempty array")
    accepted_extensions = set(limits["accepted_extensions"])
    resolved_defaults: set[str] = set()
    root = ROOT.resolve()
    for index, value in enumerate(default_input_paths):
        text = normalized_text(value, f"default_input_paths[{index}]")
        candidate = Path(text)
        if candidate.is_absolute() or any(part in {".", ".."} for part in candidate.parts):
            raise OpportunityControlError(
                "Default input paths must be normalized repo-relative paths"
            )
        if candidate.suffix.lower() not in accepted_extensions:
            raise OpportunityControlError(
                "Default input paths must use an accepted input extension"
            )
        resolved = (ROOT / candidate).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise OpportunityControlError(
                "Default input paths must remain inside the repository"
            ) from exc
        resolved_key = str(resolved).lower()
        if resolved_key in resolved_defaults:
            raise OpportunityControlError("Default input paths must be unique")
        resolved_defaults.add(resolved_key)

    lane_policies = config.get("lane_policies")
    if not isinstance(lane_policies, dict) or set(lane_policies) != set(
        SUPPORTED_LANES
    ):
        raise OpportunityControlError("Lane policies are missing or unsupported")
    for lane_id in SUPPORTED_LANES:
        policy = lane_policies[lane_id]
        if not isinstance(policy, dict):
            raise OpportunityControlError(f"Lane policy {lane_id} must be an object")
        for numeric_key in (
            "stale_after_hours",
            "minimum_fit_score",
            "lane_priority_points",
        ):
            value = policy.get(numeric_key)
            if isinstance(value, bool) or not isinstance(value, int):
                raise OpportunityControlError(
                    f"Lane policy {lane_id} {numeric_key} is invalid"
                )
        questions = policy.get("reviewer_questions")
        if not isinstance(questions, list) or not questions:
            raise OpportunityControlError(
                f"Lane policy {lane_id} reviewer questions are missing"
            )
        question_ids: list[str] = []
        for question in questions:
            if not isinstance(question, dict) or set(question) != {
                "id",
                "question",
                "required_for_draft",
            }:
                raise OpportunityControlError(
                    f"Lane policy {lane_id} reviewer question is invalid"
                )
            question_id = normalized_text(
                question["id"], f"{lane_id} reviewer question id"
            )
            normalized_text(
                question["question"], f"{lane_id} reviewer question text"
            )
            if question.get("required_for_draft") not in {True, False}:
                raise OpportunityControlError(
                    f"Lane policy {lane_id} reviewer question requirement is invalid"
                )
            question_ids.append(question_id)
        if len(question_ids) != len(set(question_ids)):
            raise OpportunityControlError(
                f"Lane policy {lane_id} reviewer question IDs are duplicated"
            )

    normalized_text(config.get("global_claim_boundary"), "global claim boundary")


def safe_input_path(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(ROOT.resolve()).as_posix()
        return {"path": relative, "external_path_redacted": False}
    except ValueError:
        return {
            "path": f"external/{resolved.name}",
            "external_path_redacted": True,
        }


def parse_json_input(
    path: Path,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    manifest = {
        **safe_input_path(path),
        "bytes": None,
        "sha256": None,
        "format": path.suffix.lower(),
        "environment": None,
        "record_count": 0,
        "status": "REJECTED",
    }
    rejected: list[dict[str, Any]] = []
    if path.is_symlink():
        rejected.append(
            {
                "input": manifest["path"],
                "record_index": None,
                "record_sha256": None,
                "errors": ["SYMLINK_INPUT_REJECTED"],
            }
        )
        return [], manifest, rejected
    if not path.is_file():
        rejected.append(
            {
                "input": manifest["path"],
                "record_index": None,
                "record_sha256": None,
                "errors": ["INPUT_FILE_NOT_FOUND"],
            }
        )
        return [], manifest, rejected

    size = path.stat().st_size
    manifest["bytes"] = size
    if size > config["ingest_limits"]["max_file_bytes"]:
        rejected.append(
            {
                "input": manifest["path"],
                "record_index": None,
                "record_sha256": None,
                "errors": ["INPUT_FILE_TOO_LARGE"],
            }
        )
        return [], manifest, rejected
    manifest["sha256"] = sha256_file(path)
    suffix = path.suffix.lower()
    if suffix not in config["ingest_limits"]["accepted_extensions"]:
        rejected.append(
            {
                "input": manifest["path"],
                "record_index": None,
                "record_sha256": None,
                "errors": ["INPUT_EXTENSION_NOT_ALLOWED"],
            }
        )
        return [], manifest, rejected

    rows: list[dict[str, Any]] = []
    environment: str | None = None
    try:
        if suffix == ".json":
            document = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise OpportunityControlError("INPUT_DOCUMENT_NOT_OBJECT")
            if set(document) != {"environment", "records", "schema"}:
                raise OpportunityControlError("INPUT_DOCUMENT_FIELDS_INVALID")
            if document.get("schema") != config["input_schema"]:
                raise OpportunityControlError("INPUT_SCHEMA_UNSUPPORTED")
            environment = document.get("environment")
            raw_rows = document.get("records")
            if not isinstance(raw_rows, list):
                raise OpportunityControlError("INPUT_RECORDS_NOT_ARRAY")
            for index, raw in enumerate(raw_rows):
                rows.append(
                    {
                        "raw": raw,
                        "environment": environment,
                        "input": manifest["path"],
                        "record_index": index,
                    }
                )
        else:
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not line.strip():
                    continue
                envelope = json.loads(line)
                if not isinstance(envelope, dict):
                    raise OpportunityControlError(
                        f"JSONL_LINE_{line_number}_NOT_OBJECT"
                    )
                if set(envelope) != {"environment", "record", "schema"}:
                    raise OpportunityControlError(
                        f"JSONL_LINE_{line_number}_FIELDS_INVALID"
                    )
                if envelope.get("schema") != config["record_schema"]:
                    raise OpportunityControlError(
                        f"JSONL_LINE_{line_number}_SCHEMA_UNSUPPORTED"
                    )
                row_environment = envelope.get("environment")
                if environment is None:
                    environment = row_environment
                elif row_environment != environment:
                    raise OpportunityControlError(
                        "JSONL_MIXED_ENVIRONMENTS_NOT_ALLOWED"
                    )
                rows.append(
                    {
                        "raw": envelope.get("record"),
                        "environment": row_environment,
                        "input": manifest["path"],
                        "record_index": line_number,
                    }
                )
    except (OSError, json.JSONDecodeError, OpportunityControlError) as exc:
        code = (
            str(exc)
            if isinstance(exc, OpportunityControlError)
            else "INPUT_PARSE_FAILED"
        )
        rejected.append(
            {
                "input": manifest["path"],
                "record_index": None,
                "record_sha256": None,
                "errors": [code],
            }
        )
        return [], manifest, rejected

    if environment not in config["allowed_environments"]:
        rejected.append(
            {
                "input": manifest["path"],
                "record_index": None,
                "record_sha256": None,
                "errors": ["INPUT_ENVIRONMENT_UNSUPPORTED"],
            }
        )
        return [], manifest, rejected
    if len(rows) > config["ingest_limits"]["max_records_per_file"]:
        rejected.append(
            {
                "input": manifest["path"],
                "record_index": None,
                "record_sha256": None,
                "errors": ["INPUT_RECORD_LIMIT_EXCEEDED"],
            }
        )
        return [], manifest, rejected

    manifest["environment"] = environment
    manifest["record_count"] = len(rows)
    manifest["status"] = "PARSED"
    return rows, manifest, rejected


def normalize_deadline(
    payload: Any,
    *,
    as_of: datetime,
    allowed_states: set[str],
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise OpportunityControlError("deadline must be an object")
    require_exact_fields(payload, DEADLINE_FIELDS, "deadline")
    state = payload.get("state")
    if state not in allowed_states:
        raise OpportunityControlError("deadline state is unsupported")
    source_text = normalized_text(payload.get("source_text"), "deadline source_text")

    if state == "EXACT":
        deadline_utc, at_utc = canonical_utc_timestamp(
            payload.get("at_utc"), "deadline at_utc"
        )
        local_value = payload.get("local")
        local = normalized_text(local_value, "deadline local")
        local_dt = parse_aware_timestamp(local, "deadline local")
        timezone_name = normalized_text(payload.get("timezone"), "deadline timezone")
        try:
            zone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise OpportunityControlError("deadline timezone is not recognized") from exc
        expected_local = deadline_utc.astimezone(zone)
        if (
            local_dt.astimezone(timezone.utc) != deadline_utc
            or local_dt.replace(tzinfo=None) != expected_local.replace(tzinfo=None)
            or local_dt.utcoffset() != expected_local.utcoffset()
        ):
            raise OpportunityControlError(
                "deadline local, timezone, and UTC values do not identify one instant"
            )
        seconds_remaining = int((deadline_utc - as_of).total_seconds())
        return {
            "state": state,
            "at_utc": at_utc,
            "local": local,
            "timezone": timezone_name,
            "source_text": source_text,
            "seconds_remaining": seconds_remaining,
            "is_closed": seconds_remaining <= 0,
        }

    for field in ("at_utc", "local", "timezone"):
        if payload.get(field) is not None:
            raise OpportunityControlError(
                f"deadline {field} must be null when state is {state}"
            )
    return {
        "state": state,
        "at_utc": None,
        "local": None,
        "timezone": None,
        "source_text": source_text,
        "seconds_remaining": None,
        "is_closed": False,
    }


def normalize_reviewer_answers(
    payload: Any,
    *,
    lane_id: str,
    policy: dict[str, Any],
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(payload, dict):
        raise OpportunityControlError("reviewer_answers must be an object")
    questions = {
        question["id"]: question for question in policy["reviewer_questions"]
    }
    unknown = sorted(set(payload) - set(questions))
    if unknown:
        raise OpportunityControlError(
            f"reviewer_answers contains unknown question IDs: {','.join(unknown)}"
        )
    allowed_states = set(config["allowed_answer_states"])
    checklist: list[dict[str, Any]] = []
    missing_required: list[str] = []
    for question in policy["reviewer_questions"]:
        question_id = question["id"]
        raw_answer = payload.get(question_id)
        if raw_answer is None:
            answer = {
                "status": "UNRESOLVED",
                "answer": "No source-bound answer supplied.",
                "source_url": None,
            }
        else:
            if not isinstance(raw_answer, dict):
                raise OpportunityControlError(
                    f"reviewer answer {lane_id}.{question_id} must be an object"
                )
            require_exact_fields(
                raw_answer,
                ANSWER_FIELDS,
                f"reviewer answer {lane_id}.{question_id}",
            )
            status = raw_answer.get("status")
            if status not in allowed_states:
                raise OpportunityControlError(
                    f"reviewer answer {lane_id}.{question_id} status is unsupported"
                )
            answer_text = normalized_text(
                raw_answer.get("answer"),
                f"reviewer answer {lane_id}.{question_id} text",
            )
            source_url = raw_answer.get("source_url")
            if status == "CONFIRMED":
                original, _ = validate_public_url(
                    source_url,
                    f"reviewer answer {lane_id}.{question_id} source_url",
                )
                source_url = original
            elif source_url is not None:
                original, _ = validate_public_url(
                    source_url,
                    f"reviewer answer {lane_id}.{question_id} source_url",
                )
                source_url = original
            answer = {
                "status": status,
                "answer": answer_text,
                "source_url": source_url,
            }
        checklist.append(
            {
                "id": question_id,
                "question": question["question"],
                "required_for_draft": question["required_for_draft"],
                **answer,
            }
        )
        if question["required_for_draft"] and answer["status"] != "CONFIRMED":
            missing_required.append(question_id)
    return checklist, missing_required


def deadline_priority_points(
    deadline: dict[str, Any],
    priority_model: dict[str, Any],
) -> int:
    if deadline["state"] == "UNKNOWN":
        return int(priority_model["unknown_deadline_penalty"])
    if deadline["state"] == "NONE_STATED":
        return int(priority_model["open_without_stated_deadline_points"])
    if deadline["is_closed"]:
        return int(priority_model["expired_deadline_penalty"])
    hours = deadline["seconds_remaining"] / 3600
    for window in priority_model["deadline_urgency"]:
        if hours <= int(window["max_hours"]):
            return int(window["points"])
    return 0


def normalize_record(
    raw: Any,
    *,
    environment: Any,
    as_of: datetime,
    config: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise OpportunityControlError("record must be an object")
    prohibited = find_prohibited_keys(
        raw,
        {
            re.sub(r"[^a-z0-9]+", "_", fragment.lower()).strip("_")
            for fragment in config["prohibited_input_key_fragments"]
        },
    )
    if prohibited:
        raise OpportunityControlError(
            f"record contains prohibited key material: {','.join(sorted(prohibited))}"
        )
    require_exact_fields(raw, RECORD_FIELDS, "record")
    if environment not in config["allowed_environments"]:
        raise OpportunityControlError("record environment is unsupported")

    record_id = normalized_text(raw.get("record_id"), "record_id")
    if not ID_RE.fullmatch(record_id):
        raise OpportunityControlError("record_id contains unsupported characters")
    lane_id = raw.get("lane")
    if lane_id not in SUPPORTED_LANES:
        raise OpportunityControlError("record lane is unsupported")
    lead_origin = raw.get("lead_origin")
    if lead_origin not in config["allowed_lead_origins"]:
        raise OpportunityControlError("record lead_origin is unsupported")
    if lead_origin == "JOB_ALERT_METADATA" and lane_id != "job":
        raise OpportunityControlError("job-alert metadata is only valid in the job lane")
    policy = config["lane_policies"][lane_id]
    title = normalized_text(raw.get("title"), "title")
    organization = normalized_text(raw.get("organization"), "organization")
    summary = normalized_text(raw.get("summary"), "summary")
    claim_boundary = normalized_text(raw.get("claim_boundary"), "claim_boundary")

    source = raw.get("source")
    if not isinstance(source, dict):
        raise OpportunityControlError("source must be an object")
    require_exact_fields(source, SOURCE_FIELDS, "source")
    source_verification_state = source.get("verification_state")
    if source_verification_state not in config["allowed_source_verification_states"]:
        raise OpportunityControlError("source verification_state is unsupported")
    if lead_origin == "VERIFIED_PUBLIC_SOURCE" and (
        source_verification_state != "PUBLIC_SOURCE_OBSERVED"
    ):
        raise OpportunityControlError(
            "verified public leads require a public-source observation"
        )
    if lead_origin == "JOB_ALERT_METADATA" and (
        source_verification_state != "PUBLIC_SOURCE_RECHECK_REQUIRED"
    ):
        raise OpportunityControlError(
            "job-alert metadata requires a public-source recheck"
        )
    if source_verification_state == "PUBLIC_SOURCE_OBSERVED":
        opportunity_url, canonical_opportunity_url = validate_public_url(
            raw.get("canonical_opportunity_url"), "canonical_opportunity_url"
        )
        source_url, canonical_source_url = validate_public_url(
            source.get("url"), "source url"
        )
    else:
        if raw.get("canonical_opportunity_url") is not None:
            raise OpportunityControlError(
                "unverified metadata canonical_opportunity_url must be null"
            )
        if source.get("url") is not None:
            raise OpportunityControlError(
                "unverified metadata source URL must be null"
            )
        opportunity_url = None
        canonical_opportunity_url = None
        source_url = None
        canonical_source_url = None
    authority = source.get("authority")
    if authority not in config["allowed_source_authorities"]:
        raise OpportunityControlError("source authority is unsupported")
    observed_precision = source.get("observed_precision")
    if observed_precision not in config["allowed_source_observation_precisions"]:
        raise OpportunityControlError("source observed_precision is unsupported")
    observed_at, observed_utc = canonical_utc_timestamp(
        source.get("observed_utc"), "source observed_utc"
    )
    observed_date = source.get("observed_date")
    if observed_precision == "EXACT_TIME":
        if observed_date is not None:
            raise OpportunityControlError(
                "exact-time observations must set observed_date to null"
            )
    else:
        observed_date = normalized_text(observed_date, "source observed_date")
        try:
            parsed_observed_date = datetime.strptime(
                observed_date, "%Y-%m-%d"
            ).date()
        except ValueError as exc:
            raise OpportunityControlError(
                "source observed_date must use YYYY-MM-DD"
            ) from exc
        if observed_utc != f"{parsed_observed_date.isoformat()}T00:00:00Z":
            raise OpportunityControlError(
                "date-only observed_utc must be the UTC start of observed_date"
            )
    source_times: dict[str, str | None] = {}
    for field in ("published_utc", "updated_utc"):
        value = source.get(field)
        if value is None:
            source_times[field] = None
            continue
        parsed, canonical = canonical_utc_timestamp(value, f"source {field}")
        if parsed > observed_at:
            raise OpportunityControlError(f"source {field} is later than observation")
        source_times[field] = canonical
    if (
        source_times["published_utc"]
        and source_times["updated_utc"]
        and parse_aware_timestamp(
            source_times["updated_utc"], "source updated_utc"
        )
        < parse_aware_timestamp(
            source_times["published_utc"], "source published_utc"
        )
    ):
        raise OpportunityControlError("source updated_utc precedes published_utc")

    deadline = normalize_deadline(
        raw.get("deadline"),
        as_of=as_of,
        allowed_states=set(config["allowed_deadline_states"]),
    )
    compensation = raw.get("compensation")
    if not isinstance(compensation, dict):
        raise OpportunityControlError("compensation must be an object")
    require_exact_fields(compensation, COMPENSATION_FIELDS, "compensation")
    compensation_state = compensation.get("state")
    if compensation_state not in config["allowed_compensation_states"]:
        raise OpportunityControlError("compensation state is unsupported")
    compensation_text = normalized_text(
        compensation.get("source_text"), "compensation source_text"
    )
    if lane_id != "job" and compensation_state != "NOT_APPLICABLE":
        raise OpportunityControlError(
            "non-job records must mark compensation NOT_APPLICABLE"
        )
    if lane_id == "job" and compensation_state == "NOT_APPLICABLE":
        raise OpportunityControlError(
            "job records must preserve compensation status or uncertainty"
        )

    eligibility = raw.get("eligibility")
    if not isinstance(eligibility, dict):
        raise OpportunityControlError("eligibility must be an object")
    require_exact_fields(eligibility, ELIGIBILITY_FIELDS, "eligibility")
    eligibility_state = eligibility.get("state")
    if eligibility_state not in config["allowed_eligibility_states"]:
        raise OpportunityControlError("eligibility state is unsupported")
    eligibility_basis = normalized_text(eligibility.get("basis"), "eligibility basis")
    unresolved = eligibility.get("unresolved_requirements")
    if not isinstance(unresolved, list) or any(
        not isinstance(item, str) or not item.strip() for item in unresolved
    ):
        raise OpportunityControlError(
            "eligibility unresolved_requirements must be a text array"
        )
    unresolved_requirements = sorted(
        {normalized_text(item, "eligibility unresolved requirement") for item in unresolved}
    )
    if eligibility_state == "CONFIRMED" and unresolved_requirements:
        raise OpportunityControlError(
            "confirmed eligibility cannot retain unresolved requirements"
        )
    if eligibility_state in {"LIKELY", "UNCERTAIN"} and not unresolved_requirements:
        raise OpportunityControlError(
            "uncertain eligibility must name unresolved requirements"
        )

    fit = raw.get("fit")
    if not isinstance(fit, dict):
        raise OpportunityControlError("fit must be an object")
    require_exact_fields(fit, FIT_FIELDS, "fit")
    fit_score = fit.get("score")
    if (
        isinstance(fit_score, bool)
        or not isinstance(fit_score, int)
        or not 0 <= fit_score <= 100
    ):
        raise OpportunityControlError("fit score must be an integer from 0 to 100")
    fit_basis = normalized_text(fit.get("basis"), "fit basis")

    checklist, missing_question_ids = normalize_reviewer_answers(
        raw.get("reviewer_answers"),
        lane_id=lane_id,
        policy=policy,
        config=config,
    )

    age_seconds = int((as_of - observed_at).total_seconds())
    max_age_seconds = int(policy["stale_after_hours"]) * 3600
    max_future_skew = int(
        config["ingest_limits"]["max_future_observation_skew_seconds"]
    )
    source_observation_state = "FRESH"
    if age_seconds < -max_future_skew:
        source_observation_state = "FUTURE_OBSERVATION"
    elif age_seconds > max_age_seconds:
        source_observation_state = "STALE"

    blockers: list[str] = []
    missing_facts: list[str] = []
    if source_observation_state == "FUTURE_OBSERVATION":
        blockers.append("SOURCE_OBSERVATION_IN_FUTURE")
    elif source_observation_state == "STALE":
        blockers.append("SOURCE_STALE_RECHECK_REQUIRED")
    if source_verification_state == "PUBLIC_SOURCE_RECHECK_REQUIRED":
        missing_facts.extend(
            [
                "EMPLOYER_POSTING_RECHECK_REQUIRED",
                "PUBLIC_SOURCE_URL_REQUIRED",
            ]
        )
    if observed_precision == "DATE_ONLY":
        missing_facts.append("SOURCE_OBSERVATION_TIME_DATE_ONLY")
    if authority not in policy["draft_source_authorities"]:
        missing_facts.append("CONTROLLING_OR_FIRST_PARTY_SOURCE_REQUIRED")
    if deadline["state"] not in policy["draft_deadline_states"]:
        missing_facts.append("DEADLINE_STATUS_NOT_DRAFT_READY")
    if deadline["state"] == "UNKNOWN":
        missing_facts.append("EXACT_DEADLINE_OR_NONE_STATED_CONFIRMATION_REQUIRED")
    if eligibility_state == "INELIGIBLE":
        blockers.append("INELIGIBLE_ON_CURRENT_EVIDENCE")
    elif eligibility_state != "CONFIRMED":
        missing_facts.append("ELIGIBILITY_CONFIRMATION_REQUIRED")
    missing_facts.extend(
        f"ELIGIBILITY_REQUIREMENT:{item}" for item in unresolved_requirements
    )
    if fit_score < int(policy["minimum_fit_score"]):
        blockers.append("FIT_BELOW_LANE_THRESHOLD")
    if lane_id == "job" and compensation_state in {"PARTIAL", "CAVEAT", "UNKNOWN"}:
        missing_facts.append("COMPENSATION_TERMS_REQUIRE_CONFIRMATION")
    missing_facts.extend(
        f"REVIEWER_QUESTION:{question_id}" for question_id in missing_question_ids
    )
    blockers = sorted(set(blockers))
    missing_facts = sorted(set(missing_facts))

    if deadline["is_closed"]:
        action_state = "CLOSED_DEADLINE"
    elif "SOURCE_OBSERVATION_IN_FUTURE" in blockers or (
        "SOURCE_STALE_RECHECK_REQUIRED" in blockers
    ):
        action_state = "BLOCKED_SOURCE_FRESHNESS"
    elif "INELIGIBLE_ON_CURRENT_EVIDENCE" in blockers:
        action_state = "BLOCKED_INELIGIBLE"
    elif "FIT_BELOW_LANE_THRESHOLD" in blockers:
        action_state = "MONITOR_LOW_FIT"
    elif blockers or missing_facts:
        action_state = "RESEARCH_REQUIRED"
    else:
        action_state = "DRAFT_READY_HUMAN_REVIEW"

    priority_model = config["priority_model"]
    priority_components = {
        "fit": fit_score * int(priority_model["fit_multiplier"]),
        "lane": int(policy["lane_priority_points"]),
        "source_authority": int(
            priority_model["source_authority_points"][authority]
        ),
        "eligibility": int(priority_model["eligibility_points"][eligibility_state]),
        "deadline": deadline_priority_points(deadline, priority_model),
        "freshness": (
            int(priority_model["fresh_source_points"])
            if source_observation_state == "FRESH"
            else int(priority_model["stale_source_penalty"])
        ),
    }
    priority_score = sum(priority_components.values())

    normalized: dict[str, Any] = {
        "record_id": record_id,
        "environment": environment,
        "lane": lane_id,
        "lead_origin": lead_origin,
        "title": title,
        "organization": organization,
        "summary": summary,
        "canonical_opportunity_url": opportunity_url,
        "canonical_opportunity_url_normalized": canonical_opportunity_url,
        "source": {
            "url": source_url,
            "url_normalized": canonical_source_url,
            "authority": authority,
            "verification_state": source_verification_state,
            "observed_utc": observed_utc,
            "observed_precision": observed_precision,
            "observed_date": observed_date,
            "published_utc": source_times["published_utc"],
            "updated_utc": source_times["updated_utc"],
            "age_seconds": age_seconds,
            "stale_after_hours": policy["stale_after_hours"],
            "observation_state": source_observation_state,
        },
        "deadline": deadline,
        "compensation": {
            "state": compensation_state,
            "source_text": compensation_text,
        },
        "eligibility": {
            "state": eligibility_state,
            "basis": eligibility_basis,
            "unresolved_requirements": unresolved_requirements,
        },
        "fit": {"score": fit_score, "basis": fit_basis},
        "reviewer_checklist": checklist,
        "missing_facts": missing_facts,
        "blockers": blockers,
        "action_state": action_state,
        "priority_score": priority_score,
        "priority_components": priority_components,
        "template_family": policy["template_family"],
        "proposed_action_type": policy["proposed_action_type"],
        "claim_boundary": claim_boundary,
        "untrusted_public_source_content": True,
    }
    identity_basis = (
        {
            "lane": lane_id,
            "canonical_opportunity_url": canonical_opportunity_url,
        }
        if canonical_opportunity_url is not None
        else {
            "lane": lane_id,
            "lead_origin": lead_origin,
            "organization": organization.lower(),
            "title": title.lower(),
        }
    )
    normalized["identity_sha256"] = canonical_json_sha256(
        identity_basis
    )
    normalized["identity_basis"] = (
        "LANE_AND_NORMALIZED_CANONICAL_URL"
        if canonical_opportunity_url is not None
        else "LANE_ORGANIZATION_TITLE_METADATA"
    )
    normalized["record_sha256"] = canonical_json_sha256(normalized)
    return normalized


def choose_duplicate_primary(
    rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    authority_points = config["priority_model"]["source_authority_points"]
    eligibility_points = config["priority_model"]["eligibility_points"]

    def key(row: dict[str, Any]) -> tuple[Any, ...]:
        observed = parse_aware_timestamp(
            row["source"]["observed_utc"], "source observed_utc"
        ).timestamp()
        return (
            -int(authority_points[row["source"]["authority"]]),
            row["source"]["observation_state"] != "FRESH",
            -observed,
            -int(eligibility_points[row["eligibility"]["state"]]),
            -int(row["fit"]["score"]),
            row["record_sha256"],
        )

    return sorted(rows, key=key)


def action_priority_tier(row: dict[str, Any]) -> str:
    if row["action_state"] == "DRAFT_READY_HUMAN_REVIEW":
        remaining = row["deadline"]["seconds_remaining"]
        if remaining is not None and remaining <= 48 * 3600:
            return "P0_DEADLINE"
        if remaining is not None and remaining <= 14 * 24 * 3600:
            return "P1_NEAR_TERM"
        return "P2_DRAFT_READY"
    if row["action_state"] == "RESEARCH_REQUIRED":
        return "P3_RESEARCH"
    return "BLOCKED_OR_CLOSED"


def build_action(row: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    action_id = canonical_json_sha256(
        {
            "identity_sha256": row["identity_sha256"],
            "record_sha256": row["record_sha256"],
            "proposed_action_type": row["proposed_action_type"],
        }
    )
    return {
        "action_id": action_id,
        "record_id": row["record_id"],
        "record_sha256": row["record_sha256"],
        "identity_sha256": row["identity_sha256"],
        "identity_basis": row["identity_basis"],
        "environment": row["environment"],
        "lane": row["lane"],
        "lead_origin": row["lead_origin"],
        "title": row["title"],
        "organization": row["organization"],
        "summary": row["summary"],
        "canonical_opportunity_url": row["canonical_opportunity_url"],
        "source": row["source"],
        "deadline": row["deadline"],
        "compensation": row["compensation"],
        "eligibility": row["eligibility"],
        "fit": row["fit"],
        "priority_score": row["priority_score"],
        "priority_components": row["priority_components"],
        "priority_tier": action_priority_tier(row),
        "action_state": row["action_state"],
        "proposed_action_type": row["proposed_action_type"],
        "template_family": row["template_family"],
        "draft_ready": row["action_state"] == "DRAFT_READY_HUMAN_REVIEW",
        "reviewer_checklist": row["reviewer_checklist"],
        "missing_facts": row["missing_facts"],
        "blockers": row["blockers"],
        "duplicate_count": row["duplicate_count"],
        "source_observations": row["source_observations"],
        "claim_boundary": row["claim_boundary"],
        "global_claim_boundary": config["global_claim_boundary"],
        "controls": {
            "human_review_required": True,
            "action_time_human_approval_required": True,
            "login_allowed": False,
            "send_allowed": False,
            "post_allowed": False,
            "apply_allowed": False,
            "certify_allowed": False,
            "sign_allowed": False,
            "submit_allowed": False,
            "external_mutation_allowed": False,
        },
        "send_performed": False,
        "post_performed": False,
        "apply_performed": False,
        "certify_performed": False,
        "sign_performed": False,
        "submit_performed": False,
    }


def queue_summary(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": action["rank"],
        "lane_rank": action["lane_rank"],
        "action_id": action["action_id"],
        "lane": action["lane"],
        "lead_origin": action["lead_origin"],
        "priority_tier": action["priority_tier"],
        "priority_score": action["priority_score"],
        "action_state": action["action_state"],
        "draft_ready": action["draft_ready"],
        "title": action["title"],
        "organization": action["organization"],
        "canonical_opportunity_url": action["canonical_opportunity_url"],
        "source_url": action["source"]["url"],
        "source_observed_utc": action["source"]["observed_utc"],
        "source_observed_precision": action["source"]["observed_precision"],
        "source_observed_date": action["source"]["observed_date"],
        "source_observation_state": action["source"]["observation_state"],
        "deadline": action["deadline"],
        "compensation": action["compensation"],
        "eligibility": action["eligibility"],
        "duplicate_count": action["duplicate_count"],
        "missing_facts": action["missing_facts"],
        "blockers": action["blockers"],
        "claim_boundary": action["claim_boundary"],
    }


def record_sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    deadline = row["deadline"]
    deadline_sort = (
        parse_aware_timestamp(deadline["at_utc"], "deadline at_utc").timestamp()
        if deadline["at_utc"]
        else float("inf")
    )
    return (
        -int(row["priority_score"]),
        deadline_sort,
        row["lane"],
        row["organization"].lower(),
        row["title"].lower(),
        row["record_sha256"],
    )


def build_control_plane(
    input_paths: Iterable[Path],
    *,
    as_of_utc: str | None = None,
    config_path: Path = CONFIG_PATH,
) -> dict[str, Any]:
    config = read_json_object(config_path)
    validate_config(config)
    as_of = (
        datetime.now(timezone.utc).replace(microsecond=0)
        if as_of_utc is None
        else canonical_utc_timestamp(as_of_utc, "as_of_utc")[0]
    )
    as_of_text = utc_iso(as_of)

    unique_paths: dict[str, Path] = {}
    for candidate in input_paths:
        path = Path(candidate)
        key = str(path.resolve()).lower()
        unique_paths[key] = path
    ordered_paths = [unique_paths[key] for key in sorted(unique_paths)]

    manifests: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for path in ordered_paths:
        rows, manifest, file_rejections = parse_json_input(path, config)
        manifests.append(manifest)
        raw_rows.extend(rows)
        rejected.extend(file_rejections)

    normalized_rows: list[dict[str, Any]] = []
    for envelope in raw_rows:
        raw = envelope["raw"]
        raw_sha = canonical_json_sha256(raw)
        try:
            row = normalize_record(
                raw,
                environment=envelope["environment"],
                as_of=as_of,
                config=config,
            )
        except OpportunityControlError as exc:
            rejected.append(
                {
                    "input": envelope["input"],
                    "record_index": envelope["record_index"],
                    "record_sha256": raw_sha,
                    "errors": [str(exc)],
                }
            )
            continue
        row["input"] = envelope["input"]
        row["input_record_index"] = envelope["record_index"]
        normalized_rows.append(row)

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in normalized_rows:
        groups[row["identity_sha256"]].append(row)

    primary_rows: list[dict[str, Any]] = []
    suppressed_duplicates: list[dict[str, Any]] = []
    duplicate_groups: list[dict[str, Any]] = []
    for identity_sha in sorted(groups):
        ordered_group = choose_duplicate_primary(groups[identity_sha], config)
        primary = ordered_group[0]
        observations = sorted(
            [
                {
                    "record_id": row["record_id"],
                    "record_sha256": row["record_sha256"],
                    "source_url": row["source"]["url"],
                    "source_authority": row["source"]["authority"],
                    "observed_utc": row["source"]["observed_utc"],
                    "observed_precision": row["source"]["observed_precision"],
                    "observed_date": row["source"]["observed_date"],
                    "input": row["input"],
                }
                for row in ordered_group
            ],
            key=lambda item: (
                item["observed_utc"],
                item["source_url"],
                item["record_sha256"],
            ),
        )
        primary["duplicate_count"] = len(ordered_group) - 1
        primary["source_observations"] = observations
        primary_rows.append(primary)
        if len(ordered_group) > 1:
            duplicate_groups.append(
                {
                    "identity_sha256": identity_sha,
                    "primary_record_sha256": primary["record_sha256"],
                    "suppressed_record_sha256s": [
                        row["record_sha256"] for row in ordered_group[1:]
                    ],
                    "source_observations": observations,
                }
            )
        for duplicate in ordered_group[1:]:
            suppressed_duplicates.append(
                {
                    "identity_sha256": identity_sha,
                    "record_id": duplicate["record_id"],
                    "record_sha256": duplicate["record_sha256"],
                    "primary_record_sha256": primary["record_sha256"],
                    "reason": "DUPLICATE_CANONICAL_OPPORTUNITY_URL_AND_LANE",
                    "source_url": duplicate["source"]["url"],
                    "observed_utc": duplicate["source"]["observed_utc"],
                }
            )

    primary_rows.sort(key=record_sort_key)
    actions = [build_action(row, config) for row in primary_rows]
    lane_counts: Counter[str] = Counter()
    for rank, action in enumerate(actions, start=1):
        lane_counts[action["lane"]] += 1
        action["rank"] = rank
        action["lane_rank"] = lane_counts[action["lane"]]

    ranked_all = [queue_summary(action) for action in actions]
    by_lane = {
        lane_id: [
            queue_summary(action)
            for action in actions
            if action["lane"] == lane_id
        ]
        for lane_id in SUPPORTED_LANES
    }
    draft_ready = [
        action for action in actions if action["action_state"] == "DRAFT_READY_HUMAN_REVIEW"
    ]
    research_required = [
        action for action in actions if action["action_state"] == "RESEARCH_REQUIRED"
    ]
    blocked_or_closed = [
        action
        for action in actions
        if action["action_state"]
        not in {"DRAFT_READY_HUMAN_REVIEW", "RESEARCH_REQUIRED"}
    ]
    action_state_counts = Counter(action["action_state"] for action in actions)
    environments = sorted({row["environment"] for row in normalized_rows})

    if not ordered_paths:
        status = "NO_INPUT_FILES_DISCOVERED"
    elif not normalized_rows and rejected:
        status = "ALL_INPUT_REJECTED_FAIL_CLOSED"
    elif rejected:
        status = "PARTIAL_INPUT_REJECTED_FAIL_CLOSED"
    elif environments == ["TEST_FIXTURE"]:
        status = "TEST_FIXTURE_ONLY"
    elif len(environments) > 1:
        status = "MIXED_ENVIRONMENTS_REVIEW_REQUIRED"
    elif not actions:
        status = "NO_PUBLIC_LEADS_INGESTED"
    else:
        status = "READY_FOR_LOCAL_HUMAN_REVIEW"

    payload: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "generated_utc": as_of_text,
        "status": status,
        "environments": environments,
        "summary": {
            "input_file_count": len(ordered_paths),
            "input_record_count": len(raw_rows),
            "valid_record_count_before_deduplication": len(normalized_rows),
            "ranked_opportunity_count": len(actions),
            "draft_ready_action_count": len(draft_ready),
            "research_required_action_count": len(research_required),
            "blocked_or_closed_action_count": len(blocked_or_closed),
            "suppressed_duplicate_count": len(suppressed_duplicates),
            "rejected_record_count": len(rejected),
            "stale_source_count": sum(
                action["source"]["observation_state"] == "STALE"
                for action in actions
            ),
            "future_source_observation_count": sum(
                action["source"]["observation_state"] == "FUTURE_OBSERVATION"
                for action in actions
            ),
            "exact_deadline_count": sum(
                action["deadline"]["state"] == "EXACT" for action in actions
            ),
            "eligibility_uncertain_count": sum(
                action["eligibility"]["state"] in {"LIKELY", "UNCERTAIN"}
                for action in actions
            ),
            "metadata_only_job_alert_count": sum(
                action["lead_origin"] == "JOB_ALERT_METADATA"
                for action in actions
            ),
            "action_state_counts": dict(sorted(action_state_counts.items())),
            "lane_counts": {
                lane_id: len(by_lane[lane_id]) for lane_id in SUPPORTED_LANES
            },
            "external_action_count": 0,
        },
        "controls": {
            **config["controls"],
            "builder_has_network_client": False,
            "builder_has_browser_client": False,
            "builder_has_authentication_flow": False,
            "builder_has_external_action_handler": False,
            "draft_ready_does_not_authorize_external_action": True,
            "source_content_is_untrusted_data": True,
            "final_external_action_performed": False,
        },
        "source_evidence": {
            "builder": {
                **safe_input_path(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
            },
            "config": {
                **safe_input_path(config_path),
                "sha256": sha256_file(config_path),
            },
            "inputs": manifests,
        },
        "ranked_queues": {
            "all": ranked_all,
            "by_lane": by_lane,
        },
        "actions": actions,
        "draft_ready_actions": draft_ready,
        "research_required_actions": research_required,
        "blocked_or_closed_actions": blocked_or_closed,
        "duplicate_control": {
            "identity_basis": (
                "Verified public leads use lane plus normalized canonical opportunity URL. "
                "Metadata-only job alerts use lane plus normalized organization and title "
                "until a public posting URL is verified."
            ),
            "suppressed_count": len(suppressed_duplicates),
            "groups": duplicate_groups,
            "suppressed_records": suppressed_duplicates,
        },
        "rejected_records": sorted(
            rejected,
            key=lambda item: (
                str(item["input"]),
                -1 if item["record_index"] is None else int(item["record_index"]),
                str(item["record_sha256"] or ""),
            ),
        ),
        "claim_boundaries": {
            "global": config["global_claim_boundary"],
            "source_freshness": (
                "Freshness describes the elapsed time since the recorded public-source "
                "observation only. It does not prove that the source remains unchanged or open."
            ),
            "ranking": (
                "Priority scores are deterministic triage weights, not probabilities of "
                "eligibility, selection, award, employment, investment, licensing, "
                "or pilot success."
            ),
            "draft_readiness": (
                "Draft-ready means that configured local preparation facts are present. It "
                "does not authorize login, contact, posting, application, certification, "
                "signature, submission, or disclosure."
            ),
        },
    }
    payload["control_sha256"] = canonical_json_sha256(payload)
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema") != OUTPUT_SCHEMA:
        raise OpportunityControlError("Output schema is invalid")
    controls = payload.get("controls")
    if not isinstance(controls, dict):
        raise OpportunityControlError("Output controls are missing")
    for key, expected in SAFE_CONTROL_EXPECTATIONS.items():
        if controls.get(key) is not expected:
            raise OpportunityControlError(f"Output control {key} is unsafe")
    for key in (
        "builder_has_network_client",
        "builder_has_browser_client",
        "builder_has_authentication_flow",
        "builder_has_external_action_handler",
        "final_external_action_performed",
    ):
        if controls.get(key) is not False:
            raise OpportunityControlError(f"Output control {key} is unsafe")
    if controls.get("draft_ready_does_not_authorize_external_action") is not True:
        raise OpportunityControlError("Draft readiness was allowed to authorize action")

    actions = payload.get("actions")
    if not isinstance(actions, list):
        raise OpportunityControlError("Output actions are invalid")
    if payload["summary"]["ranked_opportunity_count"] != len(actions):
        raise OpportunityControlError("Ranked opportunity count is inconsistent")
    if payload["summary"]["external_action_count"] != 0:
        raise OpportunityControlError("Output reports an external action")
    if [action["rank"] for action in actions] != list(range(1, len(actions) + 1)):
        raise OpportunityControlError("Global action ranks are not sequential")
    if len({action["identity_sha256"] for action in actions}) != len(actions):
        raise OpportunityControlError("Duplicate opportunities survived suppression")
    action_ids = [action["action_id"] for action in actions]
    if len(action_ids) != len(set(action_ids)):
        raise OpportunityControlError("Action IDs are duplicated")
    expected_state_counts = dict(
        sorted(Counter(action["action_state"] for action in actions).items())
    )
    if payload["summary"]["action_state_counts"] != expected_state_counts:
        raise OpportunityControlError("Action-state counts are inconsistent")
    expected_lane_counts = {
        lane_id: sum(action["lane"] == lane_id for action in actions)
        for lane_id in SUPPORTED_LANES
    }
    if payload["summary"]["lane_counts"] != expected_lane_counts:
        raise OpportunityControlError("Lane counts are inconsistent")
    expected_draft_ids = [
        action["action_id"]
        for action in actions
        if action["action_state"] == "DRAFT_READY_HUMAN_REVIEW"
    ]
    expected_research_ids = [
        action["action_id"]
        for action in actions
        if action["action_state"] == "RESEARCH_REQUIRED"
    ]
    expected_blocked_ids = [
        action["action_id"]
        for action in actions
        if action["action_state"]
        not in {"DRAFT_READY_HUMAN_REVIEW", "RESEARCH_REQUIRED"}
    ]
    classified = (
        ("draft_ready_actions", expected_draft_ids, "draft_ready_action_count"),
        (
            "research_required_actions",
            expected_research_ids,
            "research_required_action_count",
        ),
        (
            "blocked_or_closed_actions",
            expected_blocked_ids,
            "blocked_or_closed_action_count",
        ),
    )
    for field, expected_ids, count_field in classified:
        actual_rows = payload.get(field)
        if not isinstance(actual_rows, list):
            raise OpportunityControlError(f"{field} is invalid")
        actual_ids = [row.get("action_id") for row in actual_rows]
        if actual_ids != expected_ids:
            raise OpportunityControlError(f"{field} is inconsistent")
        if payload["summary"][count_field] != len(expected_ids):
            raise OpportunityControlError(f"{count_field} is inconsistent")

    ranked_all = payload.get("ranked_queues", {}).get("all")
    if not isinstance(ranked_all, list) or [
        row.get("action_id") for row in ranked_all
    ] != action_ids:
        raise OpportunityControlError("Global ranked queue is inconsistent")
    by_lane = payload.get("ranked_queues", {}).get("by_lane")
    if not isinstance(by_lane, dict) or set(by_lane) != set(SUPPORTED_LANES):
        raise OpportunityControlError("Per-lane ranked queues are invalid")
    for lane_id in SUPPORTED_LANES:
        expected_ids = [
            action["action_id"] for action in actions if action["lane"] == lane_id
        ]
        if [row.get("action_id") for row in by_lane[lane_id]] != expected_ids:
            raise OpportunityControlError(
                f"Per-lane ranked queue {lane_id} is inconsistent"
            )

    duplicate_control = payload.get("duplicate_control")
    if not isinstance(duplicate_control, dict):
        raise OpportunityControlError("Duplicate control is missing")
    if duplicate_control.get("suppressed_count") != len(
        duplicate_control.get("suppressed_records", [])
    ):
        raise OpportunityControlError("Suppressed duplicate count is inconsistent")
    if payload["summary"]["suppressed_duplicate_count"] != duplicate_control.get(
        "suppressed_count"
    ):
        raise OpportunityControlError("Summary duplicate count is inconsistent")
    if payload["summary"]["rejected_record_count"] != len(
        payload.get("rejected_records", [])
    ):
        raise OpportunityControlError("Rejected record count is inconsistent")
    for action in actions:
        action_controls = action.get("controls")
        if not isinstance(action_controls, dict):
            raise OpportunityControlError("Action controls are missing")
        for key in (
            "login_allowed",
            "send_allowed",
            "post_allowed",
            "apply_allowed",
            "certify_allowed",
            "sign_allowed",
            "submit_allowed",
            "external_mutation_allowed",
        ):
            if action_controls.get(key) is not False:
                raise OpportunityControlError(f"Action control {key} is unsafe")
        for key in (
            "send_performed",
            "post_performed",
            "apply_performed",
            "certify_performed",
            "sign_performed",
            "submit_performed",
        ):
            if action.get(key) is not False:
                raise OpportunityControlError(f"Action field {key} is unsafe")
        if action["draft_ready"] != (
            action["action_state"] == "DRAFT_READY_HUMAN_REVIEW"
        ):
            raise OpportunityControlError("Draft readiness and action state disagree")
        if action["source"]["verification_state"] == "PUBLIC_SOURCE_OBSERVED":
            validate_public_url(
                action["canonical_opportunity_url"],
                "action canonical opportunity URL",
            )
            validate_public_url(action["source"]["url"], "action source URL")
        else:
            if (
                action["canonical_opportunity_url"] is not None
                or action["source"]["url"] is not None
            ):
                raise OpportunityControlError(
                    "Unverified metadata retained an unverified source URL"
                )
            if action["draft_ready"]:
                raise OpportunityControlError(
                    "Unverified metadata was marked draft-ready"
                )
            if "PUBLIC_SOURCE_URL_REQUIRED" not in action["missing_facts"]:
                raise OpportunityControlError(
                    "Unverified metadata lost its public-source gate"
                )
        canonical_utc_timestamp(
            action["source"]["observed_utc"], "action source observed_utc"
        )
        if action["source"]["observed_precision"] == "DATE_ONLY":
            observed_date = action["source"]["observed_date"]
            if action["source"]["observed_utc"] != f"{observed_date}T00:00:00Z":
                raise OpportunityControlError(
                    "Date-only source observation lost its precision boundary"
                )
        elif action["source"]["observed_date"] is not None:
            raise OpportunityControlError(
                "Exact-time source observation retained an observed_date"
            )
        if not action.get("claim_boundary") or not action.get(
            "global_claim_boundary"
        ):
            raise OpportunityControlError("Action claim boundary is missing")
        if action["deadline"]["state"] == "EXACT":
            canonical_utc_timestamp(
                action["deadline"]["at_utc"], "action deadline at_utc"
            )
            if not action["deadline"]["timezone"] or not action["deadline"]["local"]:
                raise OpportunityControlError("Exact action deadline lost timezone data")
        if action["lane"] == "job" and action["compensation"]["state"] == (
            "NOT_APPLICABLE"
        ):
            raise OpportunityControlError("Job action lost compensation uncertainty")

    expected_hash = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "control_sha256"}
    )
    if payload.get("control_sha256") != expected_hash:
        raise OpportunityControlError("Output control SHA-256 is invalid")


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Opportunity Control Plane",
        "",
        f"- Status: `{payload['status']}`",
        f"- Generated UTC: `{payload['generated_utc']}`",
        f"- Ranked opportunities: `{summary['ranked_opportunity_count']}`",
        f"- Draft-ready for human review: `{summary['draft_ready_action_count']}`",
        f"- Research required: `{summary['research_required_action_count']}`",
        f"- Blocked or closed: `{summary['blocked_or_closed_action_count']}`",
        f"- Duplicates suppressed: `{summary['suppressed_duplicate_count']}`",
        f"- Rejected records: `{summary['rejected_record_count']}`",
        f"- External actions performed: `{summary['external_action_count']}`",
        f"- Control SHA-256: `{payload['control_sha256']}`",
        "",
        "## Ranked Queue",
        "",
        "| Rank | Lane | State | Score | Organization | Opportunity | "
        "Deadline UTC | Source observed UTC |",
        "|---:|---|---|---:|---|---|---|---|",
    ]
    for row in payload["ranked_queues"]["all"]:
        title = row["title"].replace("|", "/")
        organization = row["organization"].replace("|", "/")
        lines.append(
            f"| {row['rank']} | `{row['lane']}` | `{row['action_state']}` | "
            f"{row['priority_score']} | {organization} | {title} | "
            f"`{row['deadline']['at_utc'] or row['deadline']['state']}` | "
            f"`{row['source_observed_utc']}` |"
        )
    if not payload["ranked_queues"]["all"]:
        lines.append("| - | - | `NO_RECORDS` | - | - | - | - | - |")

    lines.extend(["", "## Draft-Ready Actions", ""])
    if payload["draft_ready_actions"]:
        for action in payload["draft_ready_actions"]:
            lines.extend(
                [
                    f"### {action['organization']} - {action['title']}",
                    "",
                    f"- Lane: `{action['lane']}`",
                    f"- Priority: `{action['priority_tier']}` / `{action['priority_score']}`",
                    f"- Proposed local action: `{action['proposed_action_type']}`",
                    f"- Template family: `{action['template_family']}`",
                    f"- Deadline: `{action['deadline']['source_text']}`",
                    f"- Eligibility: `{action['eligibility']['state']}`",
                    "- External action authorized: `false`",
                    "",
                ]
            )
    else:
        lines.append("No action is draft-ready under the configured evidence gates.")
        lines.append("")

    lines.extend(
        [
            "## Claim Boundaries",
            "",
            payload["claim_boundaries"]["global"],
            "",
            payload["claim_boundaries"]["source_freshness"],
            "",
            payload["claim_boundaries"]["ranking"],
            "",
            payload["claim_boundaries"]["draft_readiness"],
            "",
        ]
    )
    return "\n".join(lines)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
    )


def write_outputs(payload: dict[str, Any], output_dir: Path = OUT_DIR) -> tuple[Path, Path]:
    json_path = output_dir / "opportunity_control_plane_latest.json"
    markdown_path = output_dir / "opportunity_control_plane_latest.md"
    atomic_write_json(json_path, payload)
    atomic_write_text(markdown_path, render_markdown(payload))
    return json_path, markdown_path


def discover_input_paths(
    explicit_inputs: Iterable[Path],
    input_dirs: Iterable[Path],
    *,
    config: dict[str, Any],
) -> list[Path]:
    paths: list[Path] = [Path(path) for path in explicit_inputs]
    directories = [Path(path) for path in input_dirs]
    if not paths and not directories:
        paths.extend(ROOT / Path(path) for path in config["default_input_paths"])
        directories = [INBOX_DIR]
    accepted = set(config["ingest_limits"]["accepted_extensions"])
    for directory in directories:
        if not directory.exists():
            continue
        if not directory.is_dir():
            paths.append(directory)
            continue
        paths.extend(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in accepted
        )
    unique: dict[str, Path] = {}
    for path in paths:
        unique[str(path.resolve()).lower()] = path
    return [unique[key] for key in sorted(unique)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic local opportunity queues from public-source JSON/JSONL "
            "without logging in or taking any external action."
        )
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        type=Path,
        help="Local JSON or JSONL input file; may be repeated.",
    )
    parser.add_argument(
        "--input-dir",
        action="append",
        default=[],
        type=Path,
        help="Local directory to scan recursively for JSON/JSONL; may be repeated.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PATH,
        help="Opportunity control-plane config.",
    )
    parser.add_argument(
        "--as-of-utc",
        help="Canonical UTC evaluation timestamp; defaults to current UTC.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT_DIR,
        help="Local output directory.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and summarize without writing output files.",
    )
    args = parser.parse_args()

    config = read_json_object(args.config)
    validate_config(config)
    inputs = discover_input_paths(args.input, args.input_dir, config=config)
    payload = build_control_plane(
        inputs,
        as_of_utc=args.as_of_utc,
        config_path=args.config,
    )
    output_paths: dict[str, str] = {}
    if not args.check:
        json_path, markdown_path = write_outputs(payload, args.output_dir)
        output_paths = {
            "json": safe_input_path(json_path)["path"],
            "markdown": safe_input_path(markdown_path)["path"],
        }
    print(
        json.dumps(
            {
                "status": payload["status"],
                "generated_utc": payload["generated_utc"],
                "ranked_opportunity_count": payload["summary"][
                    "ranked_opportunity_count"
                ],
                "draft_ready_action_count": payload["summary"][
                    "draft_ready_action_count"
                ],
                "research_required_action_count": payload["summary"][
                    "research_required_action_count"
                ],
                "blocked_or_closed_action_count": payload["summary"][
                    "blocked_or_closed_action_count"
                ],
                "suppressed_duplicate_count": payload["summary"][
                    "suppressed_duplicate_count"
                ],
                "rejected_record_count": payload["summary"]["rejected_record_count"],
                "external_action_count": payload["summary"]["external_action_count"],
                "outputs": output_paths,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
