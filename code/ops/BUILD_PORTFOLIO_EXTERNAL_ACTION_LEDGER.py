from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "portfolio_external_action_ledger_v1.json"
OUT_DIR = ROOT / "out" / "portfolio_external_action_ledger"
OUT_JSON = OUT_DIR / "portfolio_external_action_ledger_latest.json"
OUT_MD = OUT_DIR / "portfolio_external_action_ledger_latest.md"

CONFIG_SCHEMA = "lumencore.portfolio_external_action_ledger_config.v1"
OUTPUT_SCHEMA = "lumencore.portfolio_external_action_ledger.v1"
SOURCE_KINDS = {"engagement_register", "grant_queue", "json"}
PORTFOLIO_DOMAINS = {
    "AGREEMENT_AND_LICENSING",
    "GOVERNMENT_FUNDING_QUEUE",
    "GOVERNMENT_MARKET_RESEARCH",
    "GOVERNMENT_PARTNER_TEAMING",
    "LEGAL_AND_IP",
    "PARTNERSHIP_AND_PILOT",
    "VENTURE_AND_AWARD",
}
CATEGORIES = {
    "ACCOUNT_OR_ROUTE_CONTROL",
    "AGREEMENT_ACTION_RECORDED",
    "COMPLETED_MOU_PRIVATE_CUSTODY_REVIEW",
    "CLOSED_ROUTE",
    "EXTERNAL_COMMUNICATION_RECORDED",
    "EXTERNAL_SUBMISSION_CONFIRMED",
    "EXTERNAL_SUBMISSION_RECORDED_OUTBOUND",
    "EXTERNAL_SUBMISSION_RECEIPT_CONFIRMED",
    "DEADLINE_BOUND_PARTNER_OUTREACH_DRAFT",
    "FOLLOWUP_ACTION_STAGED",
    "LOCAL_PACKET_NOT_SUBMITTED",
    "LOCAL_PORTAL_PACKET_STAGED",
    "OFFICIAL_COHORT_SELECTION_ONBOARDING_DUE",
    "NOT_SUBMITTED_CLOSED",
    "USER_REPORTED_APPLICATION_NO_PORTAL_RECEIPT",
}
RECORD_ID_RE = re.compile(r"^[a-z0-9][a-z0-9:_-]+$")
ACTION_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9:_-]+$")
STATE_RE = re.compile(r"^[A-Z0-9][A-Z0-9_]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MISSING = object()

FORBIDDEN_OUTPUT_KEYS = {
    "access_code",
    "account_id",
    "application_number",
    "bcc",
    "cage",
    "cc",
    "credential",
    "email",
    "firm_pin",
    "gmail_message_id",
    "gmail_thread_id",
    "meeting_id",
    "otp",
    "passcode",
    "password",
    "phone",
    "recipient",
    "recipients",
    "security_code",
    "source_message_id",
    "tax_id",
    "thread_id",
    "to",
    "uei",
    "user_id",
}
FORBIDDEN_UNQUALIFIED_PHRASES = {
    "award guaranteed",
    "cmmc compliant",
    "government approved",
    "independently validated",
    "institutional grade",
    "itar compliant",
    "production ready",
    "profitable",
    "realized savings",
}


class LedgerConfigError(ValueError):
    """Raised when portfolio reconciliation would be ambiguous or unsafe."""


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
        raise LedgerConfigError(f"{field} must be a non-empty timestamp")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise LedgerConfigError(f"{field} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise LedgerConfigError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LedgerConfigError(f"cannot read JSON source: {path}") from exc
    if not isinstance(payload, dict):
        raise LedgerConfigError(f"expected a JSON object at {path}")
    return payload


def resolve_repo_path(root: Path, relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise LedgerConfigError("source path must be a non-empty repository path")
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise LedgerConfigError(f"source escapes repository root: {relative_path}") from exc
    normalized = candidate.relative_to(root.resolve()).as_posix()
    if normalized.startswith("out/portfolio_external_action_ledger/"):
        raise LedgerConfigError("ledger outputs cannot be ledger inputs")
    return candidate


def repo_path(path: Path, *, root: Path = ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


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


def _safe_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerConfigError(f"{field} must be a non-empty string")
    normalized = value.strip()
    lowered = normalized.lower()
    for phrase in FORBIDDEN_UNQUALIFIED_PHRASES:
        if phrase in lowered:
            raise LedgerConfigError(f"{field} contains an unsupported claim: {phrase}")
    return normalized


def validate_config(config: dict[str, Any], *, root: Path = ROOT) -> None:
    required = {
        "claim_boundary",
        "explicit_actions",
        "schema",
        "snapshot_utc",
        "sources",
        "title",
    }
    missing = sorted(required - set(config))
    if missing:
        raise LedgerConfigError(f"missing config fields: {missing}")
    if config.get("schema") != CONFIG_SCHEMA:
        raise LedgerConfigError(f"schema must be {CONFIG_SCHEMA}")
    parse_utc(config["snapshot_utc"], field="snapshot_utc")
    _safe_text(config["title"], "title")
    _safe_text(config["claim_boundary"], "claim_boundary")

    sources = config["sources"]
    if not isinstance(sources, list) or not sources:
        raise LedgerConfigError("sources must be a non-empty array")
    source_ids: set[str] = set()
    source_kinds: Counter[str] = Counter()
    for index, source in enumerate(sources):
        field = f"sources[{index}]"
        if not isinstance(source, dict):
            raise LedgerConfigError(f"{field} must be an object")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not RECORD_ID_RE.fullmatch(source_id):
            raise LedgerConfigError(f"{field}.source_id is invalid")
        if source_id in source_ids:
            raise LedgerConfigError(f"duplicate source_id: {source_id}")
        source_ids.add(source_id)
        kind = source.get("kind")
        if kind not in SOURCE_KINDS:
            raise LedgerConfigError(f"{field}.kind is invalid")
        source_kinds[kind] += 1
        resolve_repo_path(root, source.get("path"))
        _safe_text(source.get("authority"), f"{field}.authority")
    if source_kinds["grant_queue"] != 1 or source_kinds["engagement_register"] != 1:
        raise LedgerConfigError(
            "sources must contain exactly one grant_queue and one engagement_register"
        )

    actions = config["explicit_actions"]
    if not isinstance(actions, list) or not actions:
        raise LedgerConfigError("explicit_actions must be a non-empty array")
    record_ids: set[str] = set()
    action_keys: set[str] = set()
    for index, action in enumerate(actions):
        field = f"explicit_actions[{index}]"
        if not isinstance(action, dict):
            raise LedgerConfigError(f"{field} must be an object")
        required_action = {
            "action_key",
            "category",
            "channel",
            "claim_boundary",
            "duplicate_action_blocked",
            "evidence_assertions",
            "evidence_source_ids",
            "lane_id",
            "lifecycle_state",
            "name",
            "next_action",
            "organization",
            "portfolio_domain",
            "receipt_class",
            "record_id",
        }
        missing_action = sorted(required_action - set(action))
        if missing_action:
            raise LedgerConfigError(f"{field} missing fields: {missing_action}")
        record_id = action["record_id"]
        action_key = action["action_key"]
        if not isinstance(record_id, str) or not RECORD_ID_RE.fullmatch(record_id):
            raise LedgerConfigError(f"{field}.record_id is invalid")
        if not isinstance(action_key, str) or not ACTION_KEY_RE.fullmatch(action_key):
            raise LedgerConfigError(f"{field}.action_key is invalid")
        if record_id in record_ids:
            raise LedgerConfigError(f"duplicate explicit record_id: {record_id}")
        if action_key in action_keys:
            raise LedgerConfigError(f"duplicate explicit action_key: {action_key}")
        record_ids.add(record_id)
        action_keys.add(action_key)
        if action["portfolio_domain"] not in PORTFOLIO_DOMAINS:
            raise LedgerConfigError(f"{field}.portfolio_domain is invalid")
        if action["category"] not in CATEGORIES:
            raise LedgerConfigError(f"{field}.category is invalid")
        if not isinstance(action["lifecycle_state"], str) or not STATE_RE.fullmatch(
            action["lifecycle_state"]
        ):
            raise LedgerConfigError(f"{field}.lifecycle_state is invalid")
        if not isinstance(action["duplicate_action_blocked"], bool):
            raise LedgerConfigError(f"{field}.duplicate_action_blocked must be boolean")
        for text_field in (
            "channel",
            "claim_boundary",
            "lane_id",
            "name",
            "next_action",
            "organization",
            "receipt_class",
        ):
            _safe_text(action[text_field], f"{field}.{text_field}")
        overlay = action.get("overlay_record_id")
        if overlay is not None and (
            not isinstance(overlay, str) or not RECORD_ID_RE.fullmatch(overlay)
        ):
            raise LedgerConfigError(f"{field}.overlay_record_id is invalid")
        expected_state = action.get("expected_base_state")
        if expected_state is not None and (
            not isinstance(expected_state, str) or not STATE_RE.fullmatch(expected_state)
        ):
            raise LedgerConfigError(f"{field}.expected_base_state is invalid")
        evidence_ids = action["evidence_source_ids"]
        if not isinstance(evidence_ids, list) or not evidence_ids:
            raise LedgerConfigError(f"{field}.evidence_source_ids must be non-empty")
        if any(source_id not in source_ids for source_id in evidence_ids):
            raise LedgerConfigError(f"{field} references an unknown evidence source")
        primary = action.get("primary_receipt_source_id")
        if primary is not None and primary not in evidence_ids:
            raise LedgerConfigError(
                f"{field}.primary_receipt_source_id must be an evidence source"
            )
        primary_pointer = action.get("primary_receipt_pointer")
        if primary_pointer is not None:
            if primary is None:
                raise LedgerConfigError(
                    f"{field}.primary_receipt_pointer requires primary_receipt_source_id"
                )
            if (
                not isinstance(primary_pointer, str)
                or not primary_pointer.startswith("/")
            ):
                raise LedgerConfigError(
                    f"{field}.primary_receipt_pointer is invalid"
                )
        assertions = action["evidence_assertions"]
        if not isinstance(assertions, list) or not assertions:
            raise LedgerConfigError(f"{field}.evidence_assertions must be non-empty")
        for assertion_index, assertion in enumerate(assertions):
            assertion_field = f"{field}.evidence_assertions[{assertion_index}]"
            if not isinstance(assertion, dict) or set(assertion) != {
                "expected",
                "pointer",
                "source_id",
            }:
                raise LedgerConfigError(f"{assertion_field} has invalid fields")
            if assertion["source_id"] not in source_ids:
                raise LedgerConfigError(f"{assertion_field} has unknown source")
            if not isinstance(assertion["pointer"], str) or not assertion[
                "pointer"
            ].startswith("/"):
                raise LedgerConfigError(f"{assertion_field}.pointer is invalid")


def load_sources(
    config: dict[str, Any], *, root: Path
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    payloads: dict[str, dict[str, Any]] = {}
    manifest: list[dict[str, Any]] = []
    for source in config["sources"]:
        path = resolve_repo_path(root, source["path"])
        if not path.is_file():
            raise LedgerConfigError(f"required source is missing: {source['path']}")
        raw = path.read_bytes()
        payloads[source["source_id"]] = read_json(path)
        manifest.append(
            {
                "authority": source["authority"],
                "bytes": len(raw),
                "kind": source["kind"],
                "path": repo_path(path, root=root),
                "sha256": bytes_sha256(raw),
                "source_id": source["source_id"],
            }
        )
    return payloads, manifest


def grant_queue_state(item: dict[str, Any]) -> tuple[str, str]:
    effective = str(item.get("effective_state") or item.get("state") or "").strip()
    actionable = item.get("actionable") is True
    if effective == "stale_approved":
        return (
            "LOCAL_PACKET_STALE_APPROVED_NOT_SUBMITTED",
            "Refresh the official opportunity window and rebuild the packet before any portal action.",
        )
    if effective == "approved":
        if actionable:
            return (
                "LOCAL_PACKET_APPROVED_CURRENT_WINDOW_RECHECK_REQUIRED",
                "Verify the official source, eligibility, deadline, portal roles, and final packet before action-time review.",
            )
        return (
            "LOCAL_PACKET_APPROVED_NOT_SUBMITTED",
            "Keep staged until a current official opportunity and all authority gates are verified.",
        )
    if effective == "draft":
        return (
            "LOCAL_PACKET_DRAFT_NOT_SUBMITTED",
            "Resolve source, eligibility, budget, documentary, and portal gates before finalization.",
        )
    if effective == "submitted":
        raise LedgerConfigError(
            "grant queue claims a submission without an explicit receipt overlay"
        )
    return (
        "LOCAL_PACKET_STATE_UNRESOLVED_NOT_SUBMITTED",
        "Reconcile the local packet state before any external action.",
    )


def engagement_category(state: str, channel: str) -> tuple[str, str, str]:
    if state == "PORTAL_SUBMISSION_CONFIRMED":
        return (
            "EXTERNAL_SUBMISSION_CONFIRMED",
            "SUBMITTED_MONITOR_ONLY",
            "LOCAL_PORTAL_CONFIRMATION_RECORD",
        )
    if "PORTAL_PACKET" in state or channel == "PORTAL":
        return (
            "LOCAL_PORTAL_PACKET_STAGED",
            "STAGED_NOT_SUBMITTED",
            "STAGED_PACKET_RECORD",
        )
    if any(token in state for token in ("DECLINED", "NOT_OFFERED", "CLOSE_")):
        return ("CLOSED_ROUTE", "CLOSED_NO_DUPLICATE", "LOCAL_ROUTE_CLOSURE_RECORD")
    if any(token in state for token in ("SENT", "RECEIPT_CONFIRMED")):
        return (
            "EXTERNAL_COMMUNICATION_RECORDED",
            "TRANSMITTED_OR_ACKNOWLEDGED_MONITOR",
            "OUTBOUND_OR_ACKNOWLEDGMENT_RECORD",
        )
    return (
        "ACCOUNT_OR_ROUTE_CONTROL",
        "MONITOR_OR_HUMAN_ACCOUNT_ACTION",
        "LOCAL_RECONCILIATION_RECORD",
    )


def _reference_artifact(
    relative_path: str,
    *,
    lane_id: str,
    root: Path,
    manifest: list[dict[str, Any]],
) -> tuple[str, str]:
    path = resolve_repo_path(root, relative_path)
    if not path.is_file():
        raise LedgerConfigError(
            f"engagement response artifact is missing for {lane_id}: {relative_path}"
        )
    raw = path.read_bytes()
    digest = bytes_sha256(raw)
    source_id = f"engagement_artifact::{lane_id}"
    manifest.append(
        {
            "authority": "Referenced response artifact from the reconciled engagement register.",
            "bytes": len(raw),
            "kind": "referenced_artifact",
            "path": repo_path(path, root=root),
            "sha256": digest,
            "source_id": source_id,
        }
    )
    return source_id, digest


def _evaluate_assertions(
    action: dict[str, Any], payloads: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    results = []
    for assertion in action["evidence_assertions"]:
        observed = json_pointer_get(
            payloads[assertion["source_id"]], assertion["pointer"]
        )
        passed = observed is not MISSING and observed == assertion["expected"]
        results.append(
            {
                "expected": assertion["expected"],
                "passed": passed,
                "pointer": assertion["pointer"],
                "source_id": assertion["source_id"],
            }
        )
    if not all(result["passed"] for result in results):
        raise LedgerConfigError(
            f"evidence assertion failed for explicit action {action['record_id']}"
        )
    return results


def _record_hash(record: dict[str, Any]) -> str:
    bounded = {key: value for key, value in record.items() if key != "record_sha256"}
    return canonical_sha256(bounded)


def _scan_forbidden_keys(value: Any, *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_OUTPUT_KEYS:
                raise LedgerConfigError(f"private key exposed in output at {path}.{key}")
            _scan_forbidden_keys(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_forbidden_keys(child, path=f"{path}[{index}]")


def build_ledger(
    config: dict[str, Any],
    *,
    root: Path = ROOT,
    config_path: Path = CONFIG_PATH,
    generator_path: Path | None = None,
) -> dict[str, Any]:
    validate_config(config, root=root)
    snapshot = parse_utc(config["snapshot_utc"], field="snapshot_utc")
    payloads, manifest = load_sources(config, root=root)
    sources_by_kind = {
        source["kind"]: source["source_id"] for source in config["sources"]
    }
    queue_source_id = sources_by_kind["grant_queue"]
    register_source_id = sources_by_kind["engagement_register"]
    queue = payloads[queue_source_id]
    register = payloads[register_source_id]

    items = queue.get("items")
    if not isinstance(items, list) or not items:
        raise LedgerConfigError("grant queue items are missing")
    if queue.get("n_total") != len(items):
        raise LedgerConfigError("grant queue total does not match its items")
    if queue.get("n_submitted") != 0:
        raise LedgerConfigError(
            "grant queue submitted count changed; direct receipt reconciliation is required"
        )
    if register.get("schema") != "lumencore.external_engagement_response_register.v1":
        raise LedgerConfigError("engagement register schema is invalid")
    engagement_rows = register.get("records")
    if not isinstance(engagement_rows, list) or not engagement_rows:
        raise LedgerConfigError("engagement register records are missing")

    records: dict[str, dict[str, Any]] = {}
    queue_program_ids: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            raise LedgerConfigError("grant queue contains a non-object item")
        program_id = str(item.get("program_id") or "").strip()
        if not program_id or program_id in queue_program_ids:
            raise LedgerConfigError(f"grant queue program_id is missing or duplicated: {program_id}")
        queue_program_ids.add(program_id)
        lifecycle_state, next_action = grant_queue_state(item)
        record_id = f"grant_queue::{program_id}"
        record = {
            "action_allowed_by_builder": False,
            "action_key": f"submission::{program_id}",
            "action_time_human_review_required": True,
            "category": "LOCAL_PACKET_NOT_SUBMITTED",
            "channel": "OFFICIAL_ROUTE_UNRESOLVED",
            "claim_boundary": (
                "A local queue state is not a submission, agency receipt, eligibility "
                "determination, award, contract, or funding decision."
            ),
            "current_opportunity_actionable": item.get("actionable") is True,
            "duplicate_action_blocked": False,
            "evidence_source_ids": [queue_source_id],
            "external_evidence_state": "NO_EXTERNAL_RECEIPT_RECORDED_IN_CENTRAL_QUEUE",
            "lane_id": program_id,
            "lifecycle_state": lifecycle_state,
            "local_effective_state": str(item.get("effective_state") or ""),
            "local_state": str(item.get("state") or ""),
            "name": str(item.get("program") or program_id),
            "next_action": next_action,
            "organization": str(item.get("agency") or "Unresolved agency"),
            "portfolio_domain": "GOVERNMENT_FUNDING_QUEUE",
            "primary_receipt_sha256": None,
            "receipt_class": "NO_EXTERNAL_RECEIPT",
            "record_id": record_id,
            "source_scope": "CENTRAL_GRANT_QUEUE",
        }
        record["record_sha256"] = _record_hash(record)
        records[record_id] = record

    engagement_lane_ids: set[str] = set()
    for row in engagement_rows:
        if not isinstance(row, dict):
            raise LedgerConfigError("engagement register contains a non-object record")
        lane_id = str(row.get("lane_id") or "").strip()
        if not lane_id or lane_id in engagement_lane_ids:
            raise LedgerConfigError(
                f"engagement lane_id is missing or duplicated: {lane_id}"
            )
        engagement_lane_ids.add(lane_id)
        response_artifact = str(row.get("response_artifact") or "").strip()
        if not response_artifact:
            raise LedgerConfigError(f"engagement lane lacks response artifact: {lane_id}")
        normalized_path = Path(response_artifact).as_posix()
        artifact_source_id, artifact_sha = _reference_artifact(
            normalized_path,
            lane_id=lane_id,
            root=root,
            manifest=manifest,
        )
        state = str(row.get("state") or "").strip()
        channel = str(row.get("response_channel") or "UNRESOLVED").strip()
        category, lifecycle_state, receipt_class = engagement_category(state, channel)
        record_id = f"engagement::{lane_id}"
        record = {
            "action_allowed_by_builder": False,
            "action_key": f"engagement::{lane_id}::primary",
            "action_time_human_review_required": True,
            "category": category,
            "channel": channel,
            "claim_boundary": str(row.get("claim_boundary") or config["claim_boundary"]),
            "current_opportunity_actionable": row.get("send_now") is True,
            "duplicate_action_blocked": row.get("do_not_duplicate_send") is True,
            "evidence_source_ids": [register_source_id, artifact_source_id],
            "external_evidence_state": state,
            "lane_id": lane_id,
            "lifecycle_state": lifecycle_state,
            "name": str(row.get("organization") or lane_id),
            "next_action": str(row.get("next_action") or "Monitor the existing route."),
            "organization": str(row.get("organization") or "Unresolved organization"),
            "portfolio_domain": "PARTNERSHIP_AND_PILOT",
            "primary_receipt_sha256": artifact_sha,
            "receipt_class": receipt_class,
            "record_id": record_id,
            "source_scope": "CURRENT_ENGAGEMENT_REGISTER",
        }
        record["record_sha256"] = _record_hash(record)
        records[record_id] = record

    explicit_standalone_count = 0
    for action in config["explicit_actions"]:
        assertions = _evaluate_assertions(action, payloads)
        overlay_id = action.get("overlay_record_id")
        if overlay_id:
            if overlay_id not in records:
                raise LedgerConfigError(
                    f"explicit overlay target is missing: {overlay_id}"
                )
            record = dict(records.pop(overlay_id))
            expected_base_state = action.get("expected_base_state")
            if expected_base_state and record.get("external_evidence_state") != (
                expected_base_state
            ):
                raise LedgerConfigError(
                    f"explicit overlay base state drift: {action['record_id']}"
                )
        else:
            explicit_standalone_count += 1
            record = {
                "action_allowed_by_builder": False,
                "action_time_human_review_required": True,
                "current_opportunity_actionable": False,
                "external_evidence_state": action["lifecycle_state"],
                "source_scope": "EXPLICIT_RECONCILIATION_ACTION",
            }
        evidence_source_ids = list(
            dict.fromkeys(
                list(record.get("evidence_source_ids", []))
                + list(action["evidence_source_ids"])
            )
        )
        primary_source_id = action.get("primary_receipt_source_id")
        if primary_source_id:
            primary_pointer = action.get("primary_receipt_pointer")
            if primary_pointer:
                primary_value = json_pointer_get(
                    payloads[primary_source_id], primary_pointer
                )
                if primary_value is MISSING:
                    raise LedgerConfigError(
                        "primary receipt pointer is missing for explicit action "
                        f"{action['record_id']}"
                    )
                primary_receipt_sha256 = canonical_sha256(primary_value)
            else:
                primary_manifest = next(
                    row for row in manifest if row["source_id"] == primary_source_id
                )
                primary_receipt_sha256 = primary_manifest["sha256"]
        else:
            primary_pointer = None
            primary_receipt_sha256 = record.get("primary_receipt_sha256")
        record.update(
            {
                "action_key": action["action_key"],
                "category": action["category"],
                "channel": action["channel"],
                "claim_boundary": action["claim_boundary"],
                "duplicate_action_blocked": action["duplicate_action_blocked"],
                "evidence_assertions": assertions,
                "evidence_source_ids": evidence_source_ids,
                "lane_id": action["lane_id"],
                "lifecycle_state": action["lifecycle_state"],
                "name": action["name"],
                "next_action": action["next_action"],
                "organization": action["organization"],
                "portfolio_domain": action["portfolio_domain"],
                "primary_receipt_pointer": primary_pointer,
                "primary_receipt_sha256": primary_receipt_sha256,
                "receipt_class": action["receipt_class"],
                "record_id": action["record_id"],
            }
        )
        record["record_sha256"] = _record_hash(record)
        if action["record_id"] in records:
            raise LedgerConfigError(
                f"explicit record collides with an existing record: {action['record_id']}"
            )
        records[action["record_id"]] = record

    ordered_records = sorted(records.values(), key=lambda row: row["record_id"])
    action_keys: set[str] = set()
    receipt_owners: dict[str, str] = {}
    for record in ordered_records:
        action_key = record["action_key"]
        if action_key in action_keys:
            raise LedgerConfigError(f"duplicate action_key after reconciliation: {action_key}")
        action_keys.add(action_key)
        receipt_sha = record.get("primary_receipt_sha256")
        if receipt_sha:
            if not SHA256_RE.fullmatch(receipt_sha):
                raise LedgerConfigError(
                    f"invalid primary receipt digest: {record['record_id']}"
                )
            owner = receipt_owners.get(receipt_sha)
            if owner and owner != action_key:
                raise LedgerConfigError(
                    "one receipt is bound to multiple external action keys"
                )
            receipt_owners[receipt_sha] = action_key

    manifest = sorted(manifest, key=lambda row: row["source_id"])
    source_chain_sha256 = canonical_sha256(
        [
            {
                "bytes": row["bytes"],
                "path": row["path"],
                "sha256": row["sha256"],
                "source_id": row["source_id"],
            }
            for row in manifest
        ]
    )
    config_bytes = config_path.read_bytes()
    generator = generator_path or Path(__file__).resolve()
    generator_bytes = generator.read_bytes()
    queue_generated = parse_utc(
        queue.get("generated_utc"), field="grant_queue.generated_utc"
    )
    register_generated = parse_utc(
        register.get("generated_utc"), field="engagement_register.generated_utc"
    )
    queue_age_hours = int((snapshot - queue_generated).total_seconds() // 3600)
    register_age_hours = int((snapshot - register_generated).total_seconds() // 3600)

    category_counts = Counter(record["category"] for record in ordered_records)
    payload: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "title": config["title"],
        "generated_utc": utc_text(snapshot),
        "status": "RECONCILED_FAIL_CLOSED_LEDGER_READY",
        "claim_boundary": config["claim_boundary"],
        "coverage": {
            "central_grant_queue_item_count": len(items),
            "engagement_register_lane_count": len(engagement_rows),
            "explicit_standalone_action_count": explicit_standalone_count,
            "statement": (
                "The ledger covers every item in the configured central grant queue, "
                "every lane in the configured engagement register, and the declared "
                "standalone action records. It cannot discover an external action that "
                "was never registered or given a source record."
            ),
        },
        "freshness": {
            "central_grant_queue_age_hours": queue_age_hours,
            "central_grant_queue_state": (
                "STALE_RESEARCH_REQUIRED" if queue_age_hours > 24 else "CURRENT"
            ),
            "engagement_register_age_hours": register_age_hours,
            "engagement_register_state": (
                "DATED_RECHECK_REQUIRED" if register_age_hours > 24 else "CURRENT"
            ),
        },
        "summary": {
            "category_counts": dict(sorted(category_counts.items())),
            "confirmed_external_submission_count": (
                category_counts["EXTERNAL_SUBMISSION_CONFIRMED"]
                + category_counts["EXTERNAL_SUBMISSION_RECEIPT_CONFIRMED"]
            ),
            "duplicate_action_blocked_count": sum(
                record["duplicate_action_blocked"] for record in ordered_records
            ),
            "external_submission_recorded_count": sum(
                count
                for category, count in category_counts.items()
                if category.startswith("EXTERNAL_SUBMISSION")
            ),
            "local_not_submitted_count": (
                category_counts["LOCAL_PACKET_NOT_SUBMITTED"]
                + category_counts["NOT_SUBMITTED_CLOSED"]
                + category_counts["LOCAL_PORTAL_PACKET_STAGED"]
            ),
            "record_count": len(ordered_records),
            "unique_action_key_count": len(action_keys),
            "unique_primary_receipt_count": len(receipt_owners),
        },
        "controls": {
            "builder_can_apply": False,
            "builder_can_certify": False,
            "builder_can_email": False,
            "builder_can_log_in": False,
            "builder_can_sign": False,
            "builder_can_submit": False,
            "builder_can_upload": False,
            "duplicate_action_keys_fail_closed": True,
            "missing_or_changed_sources_fail_closed": True,
            "private_identifiers_prohibited": True,
        },
        "records": ordered_records,
        "source_manifest": manifest,
        "integrity": {
            "config_sha256": bytes_sha256(config_bytes),
            "generator_sha256": bytes_sha256(generator_bytes),
            "source_chain_sha256": source_chain_sha256,
        },
    }
    payload["integrity"]["ledger_sha256"] = canonical_sha256(payload)
    _scan_forbidden_keys(payload)
    return payload


def verify_ledger_hash(payload: dict[str, Any]) -> bool:
    integrity = payload.get("integrity")
    if not isinstance(integrity, dict):
        return False
    expected = integrity.get("ledger_sha256")
    if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
        return False
    bounded = json.loads(json.dumps(payload))
    del bounded["integrity"]["ledger_sha256"]
    return canonical_sha256(bounded) == expected


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    coverage = payload["coverage"]
    freshness = payload["freshness"]
    external_records = [
        record
        for record in payload["records"]
        if record["source_scope"] != "CENTRAL_GRANT_QUEUE"
    ]
    lines = [
        f"# {payload['title']}",
        "",
        f"Generated: `{payload['generated_utc']}`",
        f"Status: `{payload['status']}`",
        f"Ledger SHA-256: `{payload['integrity']['ledger_sha256']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"],
        "",
        "## Coverage",
        "",
        f"- Central grant queue items: `{coverage['central_grant_queue_item_count']}`",
        f"- Engagement-register lanes: `{coverage['engagement_register_lane_count']}`",
        f"- Explicit standalone actions: `{coverage['explicit_standalone_action_count']}`",
        f"- Reconciled action records: `{summary['record_count']}`",
        f"- Unique action keys: `{summary['unique_action_key_count']}`",
        f"- Unique primary receipts: `{summary['unique_primary_receipt_count']}`",
        f"- External submission records: `{summary['external_submission_recorded_count']}`",
        f"- Confirmed or receipt-confirmed submissions: `{summary['confirmed_external_submission_count']}`",
        f"- Local not-submitted or staged records: `{summary['local_not_submitted_count']}`",
        "",
        coverage["statement"],
        "",
        "## Freshness",
        "",
        f"- Central grant queue: `{freshness['central_grant_queue_state']}` ({freshness['central_grant_queue_age_hours']} hours old)",
        f"- Engagement register: `{freshness['engagement_register_state']}` ({freshness['engagement_register_age_hours']} hours old)",
        "",
        "## Reconciled External Actions",
        "",
        "| Action | Category | State | Duplicate blocked | Safest next action |",
        "|---|---|---|---:|---|",
    ]
    for record in external_records:
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | {} |".format(
                record["action_key"],
                record["category"],
                record["lifecycle_state"],
                str(record["duplicate_action_blocked"]).lower(),
                record["next_action"].replace("|", "\\|"),
            )
        )
    lines.extend(
        [
            "",
            "## Queue State Counts",
            "",
            "| Category | Count |",
            "|---|---:|",
        ]
    )
    for category, count in summary["category_counts"].items():
        lines.append(f"| `{category}` | {count} |")
    lines.extend(
        [
            "",
            "## Control Boundary",
            "",
            "This builder is read-only. It cannot log in, email, apply, upload, sign, certify, or submit. Any future external action still requires current official-source verification, complete documentary review, duplicate checking, and exact action-time human approval.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any], markdown: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    OUT_MD.write_text(markdown, encoding="utf-8")


def check_outputs(payload: dict[str, Any], markdown: str) -> None:
    expected_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if not OUT_JSON.is_file() or OUT_JSON.read_text(encoding="utf-8") != expected_json:
        raise LedgerConfigError(f"stale or missing output: {repo_path(OUT_JSON)}")
    if not OUT_MD.is_file() or OUT_MD.read_text(encoding="utf-8") != markdown:
        raise LedgerConfigError(f"stale or missing output: {repo_path(OUT_MD)}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed portfolio external-action ledger."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that generated outputs are current without rewriting them.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = read_json(CONFIG_PATH)
        payload = build_ledger(
            config,
            root=ROOT,
            config_path=CONFIG_PATH,
            generator_path=Path(__file__).resolve(),
        )
        if not verify_ledger_hash(payload):
            raise LedgerConfigError("generated ledger hash verification failed")
        markdown = render_markdown(payload)
        if args.check:
            check_outputs(payload, markdown)
            print("portfolio external-action ledger: CURRENT")
        else:
            write_outputs(payload, markdown)
            print(
                "portfolio external-action ledger: "
                f"{payload['summary']['record_count']} records, "
                f"{payload['summary']['external_submission_recorded_count']} "
                "external submission records"
            )
        return 0
    except LedgerConfigError as exc:
        print(f"portfolio external-action ledger: FAIL_CLOSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
