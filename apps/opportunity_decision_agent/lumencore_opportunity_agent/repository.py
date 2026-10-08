from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .models import FreshnessState, SourceReceipt


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = APP_ROOT / "config" / "source_registry.json"

SECRET_KEY_FRAGMENTS = {
    "access_token",
    "api_key",
    "client_secret",
    "login_cookie",
    "one_time_password",
    "otp",
    "password",
    "private_key",
    "refresh_token",
    "session_cookie",
}
SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


class PublicSafeRepositoryError(ValueError):
    """Raised when an allowlist, path, record, or public-safety invariant fails."""


@dataclass(frozen=True)
class LoadedOpportunity:
    record_ref: str
    record: dict[str, Any]
    document_context: dict[str, Any]
    source_receipts: tuple[SourceReceipt, ...]
    allowed_source_paths: frozenset[str]

    def public_payload(self) -> dict[str, Any]:
        return {
            "record_ref": self.record_ref,
            "record": self.record,
            "document_context": self.document_context,
            "source_receipts": [
                receipt.model_dump(mode="json") for receipt in self.source_receipts
            ],
            "allowed_source_paths": sorted(self.allowed_source_paths),
            "external_action_capabilities": [],
        }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PublicSafeRepositoryError("timestamp must use canonical UTC with Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PublicSafeRepositoryError("timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise PublicSafeRepositoryError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")


def _assert_public_safe(value: Any, prefix: str = "record") -> None:
    if isinstance(value, dict):
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized = _normalize_key(key)
            if any(fragment in normalized for fragment in SECRET_KEY_FRAGMENTS):
                raise PublicSafeRepositoryError(
                    f"secret-shaped key rejected at {prefix}.{key}"
                )
            _assert_public_safe(item, f"{prefix}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_public_safe(item, f"{prefix}[{index}]")
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
            raise PublicSafeRepositoryError(
                f"secret-shaped value rejected at {prefix}"
            )


def _pointer_value(
    document: dict[str, Any], record: dict[str, Any], pointer: str
) -> Any:
    if not isinstance(pointer, str) or "." not in pointer:
        raise PublicSafeRepositoryError("registry pointer is invalid")
    root_name, *parts = pointer.split(".")
    current: Any
    if root_name == "document":
        current = document
    elif root_name == "record":
        current = record
    else:
        raise PublicSafeRepositoryError("registry pointer root is invalid")
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


class PublicSafeRepository:
    """Read only the exact repository artifacts named in the source registry."""

    def __init__(self, registry_path: Path = REGISTRY_PATH) -> None:
        self._registry_path = registry_path.resolve()
        self._registry = self._load_registry()
        self._records = {
            row["record_ref"]: row for row in self._registry["records"]
        }

    @property
    def record_refs(self) -> tuple[str, ...]:
        return tuple(sorted(self._records))

    @property
    def claim_boundary_path(self) -> str:
        return self._registry["policy_paths"]["claim_boundary"]

    @property
    def ip_boundary_path(self) -> str:
        return self._registry["policy_paths"]["ip_boundary"]

    def _load_registry(self) -> dict[str, Any]:
        try:
            payload = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PublicSafeRepositoryError("source registry is unreadable") from exc
        if not isinstance(payload, dict):
            raise PublicSafeRepositoryError("source registry must be an object")
        if payload.get("schema") != "lumencore.opportunity_agent_source_registry.v1":
            raise PublicSafeRepositoryError("source registry schema is unsupported")
        if set(payload) != {
            "schema",
            "max_source_bytes",
            "policy_paths",
            "records",
        }:
            raise PublicSafeRepositoryError("source registry fields are invalid")
        if not isinstance(payload["max_source_bytes"], int) or payload[
            "max_source_bytes"
        ] <= 0:
            raise PublicSafeRepositoryError("source size limit is invalid")
        records = payload.get("records")
        if not isinstance(records, list) or not records:
            raise PublicSafeRepositoryError("source registry has no records")
        refs: list[str] = []
        expected_record_fields = {
            "record_ref",
            "path",
            "collection",
            "selector_key",
            "selector_value",
            "observed_pointer",
            "stale_after_hours",
            "evidence_paths",
        }
        for row in records:
            if not isinstance(row, dict) or set(row) != expected_record_fields:
                raise PublicSafeRepositoryError("source registry record is invalid")
            ref = row.get("record_ref")
            if not isinstance(ref, str) or not ref:
                raise PublicSafeRepositoryError("record_ref is invalid")
            refs.append(ref)
            if not isinstance(row.get("stale_after_hours"), int) or row[
                "stale_after_hours"
            ] <= 0:
                raise PublicSafeRepositoryError("stale_after_hours is invalid")
            evidence_paths = row.get("evidence_paths")
            if not isinstance(evidence_paths, list) or not evidence_paths:
                raise PublicSafeRepositoryError("evidence_paths must be nonempty")
            all_paths = [row["path"], *evidence_paths]
            for candidate in all_paths:
                self._validate_relative_path_text(candidate)
        if len(refs) != len(set(refs)):
            raise PublicSafeRepositoryError("record_ref values must be unique")
        policy_paths = payload.get("policy_paths")
        if not isinstance(policy_paths, dict) or set(policy_paths) != {
            "claim_boundary",
            "ip_boundary",
        }:
            raise PublicSafeRepositoryError("policy_paths are invalid")
        for path in policy_paths.values():
            self._validate_relative_path_text(path)
        return payload

    @staticmethod
    def _validate_relative_path_text(value: Any) -> str:
        if not isinstance(value, str) or not value:
            raise PublicSafeRepositoryError("allowlisted path must be text")
        pure = PurePosixPath(value)
        if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
            raise PublicSafeRepositoryError("allowlisted path must be normalized and relative")
        if "\\" in value:
            raise PublicSafeRepositoryError("allowlisted paths must use forward slashes")
        return value

    def _read_allowlisted_bytes(self, relative_path: str) -> bytes:
        normalized = self._validate_relative_path_text(relative_path)
        resolved = (REPO_ROOT / Path(*PurePosixPath(normalized).parts)).resolve()
        try:
            resolved.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise PublicSafeRepositoryError("allowlisted path escaped repository") from exc
        if resolved.is_symlink() or not resolved.is_file():
            raise PublicSafeRepositoryError(f"allowlisted source unavailable: {normalized}")
        size = resolved.stat().st_size
        if size > self._registry["max_source_bytes"]:
            raise PublicSafeRepositoryError(f"allowlisted source is too large: {normalized}")
        return resolved.read_bytes()

    def read_policy_text(self, policy: str) -> dict[str, Any]:
        if policy not in {"claim_boundary", "ip_boundary"}:
            raise PublicSafeRepositoryError("policy name is not allowlisted")
        path = self._registry["policy_paths"][policy]
        raw = self._read_allowlisted_bytes(path)
        text = raw.decode("utf-8")
        _assert_public_safe(text, policy)
        return {
            "path": path,
            "sha256": _sha256_bytes(raw),
            "text": text,
        }

    def load(self, record_ref: str, as_of_utc: str) -> LoadedOpportunity:
        if record_ref not in self._records:
            raise PublicSafeRepositoryError("record_ref is not allowlisted")
        as_of = _parse_utc(as_of_utc)
        entry = self._records[record_ref]
        raw = self._read_allowlisted_bytes(entry["path"])
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PublicSafeRepositoryError("allowlisted record source is not valid JSON") from exc
        if not isinstance(document, dict):
            raise PublicSafeRepositoryError("allowlisted source must be a JSON object")
        collection = document.get(entry["collection"])
        if not isinstance(collection, list):
            raise PublicSafeRepositoryError("allowlisted collection is unavailable")
        matches = [
            row
            for row in collection
            if isinstance(row, dict)
            and row.get(entry["selector_key"]) == entry["selector_value"]
        ]
        if len(matches) != 1:
            raise PublicSafeRepositoryError("allowlisted selector did not resolve exactly once")
        record = matches[0]
        _assert_public_safe(record)

        observed_value = _pointer_value(document, record, entry["observed_pointer"])
        observed_utc: str | None = None
        age_hours: float | None = None
        freshness_state = FreshnessState.MISSING
        if isinstance(observed_value, str):
            observed = _parse_utc(observed_value)
            observed_utc = observed_value
            age_hours = round((as_of - observed).total_seconds() / 3600, 3)
            if age_hours < -5 / 60:
                freshness_state = FreshnessState.FUTURE
            elif age_hours > entry["stale_after_hours"]:
                freshness_state = FreshnessState.STALE
            else:
                freshness_state = FreshnessState.FRESH

        evidence_paths = tuple(dict.fromkeys(entry["evidence_paths"]))
        receipts: list[SourceReceipt] = []
        for path in evidence_paths:
            value = self._read_allowlisted_bytes(path)
            is_primary = path == entry["path"]
            receipts.append(
                SourceReceipt(
                    path=path,
                    sha256=_sha256_bytes(value),
                    size_bytes=len(value),
                    observed_utc=observed_utc if is_primary else None,
                    freshness_state=(
                        freshness_state
                        if is_primary
                        else FreshnessState.NOT_APPLICABLE
                    ),
                    age_hours=age_hours if is_primary else None,
                    evidence_role=(
                        "normalized opportunity record"
                        if is_primary
                        else "allowlisted public evidence or policy boundary"
                    ),
                )
            )
        allowed_paths = frozenset(receipt.path for receipt in receipts)
        document_context = {
            "schema": document.get("schema"),
            "environment": document.get("environment"),
            "evaluated_utc": document.get("evaluated_utc"),
            "generated_utc": document.get("generated_utc"),
            "updated_utc": document.get("updated_utc"),
        }
        _assert_public_safe(document_context, "document_context")
        return LoadedOpportunity(
            record_ref=record_ref,
            record=json.loads(_canonical_json(record)),
            document_context=document_context,
            source_receipts=tuple(receipts),
            allowed_source_paths=allowed_paths,
        )


def load_public_opportunity(record_ref: str, as_of_utc: str) -> LoadedOpportunity:
    return PublicSafeRepository().load(record_ref, as_of_utc)
