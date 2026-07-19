from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "config" / "cloud_redundancy_policy_v1.json"
DEFAULT_JSON = ROOT / "out" / "ops" / "CLOUD_REDUNDANCY_MANIFEST_2026-07-18.json"
DEFAULT_DOC = ROOT / "docs" / "CLOUD_REDUNDANCY_PLAN_2026-07-18.md"

SCHEMA = "lumencore.cloud_redundancy_manifest.v1"
POLICY_SCHEMA = "lumencore.cloud_redundancy_policy.v1"
MODE = "LOCAL_MANIFEST_ONLY"
PUBLIC_CLASSIFICATION = "PUBLIC_SAFE_NON_SECRET_RECEIPT"
HARD_MAX_SOURCE_BYTES = 1024 * 1024
MAX_ALLOWLIST_ITEMS = 16

HARD_ALLOWED_SOURCE_ROOTS = frozenset(
    {
        "build_week/prooflock_console",
        "evidence/falcon",
    }
)
HARD_DENIED_PATH_TERMS = frozenset(
    {
        ".env",
        ".git",
        "api-key",
        "api_key",
        "api_keys",
        "apikey",
        "client_secret",
        "credential",
        "credentials",
        "email",
        "grant_submissions",
        "inbox",
        "mail",
        "mailbox",
        "oauth",
        "password",
        "patent",
        "portal",
        "private",
        "raw",
        "raw_evidence",
        "registry",
        "secret",
        "secrets",
        "source_attachments",
        "token",
    }
)
REQUIRED_ACTION_BOUNDARY = {
    "api_key_reads": "PROHIBITED",
    "credential_store_reads": "PROHIBITED",
    "file_copies": "PROHIBITED_IN_THIS_LANE",
    "network_actions": "PROHIBITED",
    "publication": "PROHIBITED",
    "registry_reads": "PROHIBITED",
    "uploads": "PROHIBITED_IN_THIS_LANE",
}
REQUIRED_STORAGE_TOPOLOGY = {
    "c_drive": {
        "label": "C:",
        "role": "REPOSITORY_SOURCE_VOLUME",
        "physical_disk_id": "LOCAL_PHYSICAL_DISK_0",
        "off_device": False,
    },
    "e_drive": {
        "label": "E:",
        "role": "LOCAL_VAULT_VOLUME",
        "physical_disk_id": "LOCAL_PHYSICAL_DISK_0",
        "relationship_to_c": "C_AND_E_ARE_VOLUMES_ON_THE_SAME_PHYSICAL_DISK",
        "counts_as_independent_redundancy": False,
    },
    "icloud": {
        "label": "iCloud Drive local folder",
        "local_folder": "USERPROFILE/iCloudDrive/LumaTrader/PublicSafeReceipts",
        "role": "LOCAL_SYNC_CANDIDATE_ONLY",
        "remote_completion": "NOT_PROVEN",
        "readback_verification": "NOT_PERFORMED",
        "counts_as_verified_off_device_redundancy": False,
    },
    "google_drive": {
        "label": "Google Drive",
        "role": "OFF_DEVICE_TARGET",
        "connector_action": "SEPARATE_UPLOAD_AND_READBACK_REQUIRED",
        "upload": "NOT_PERFORMED",
        "readback_verification": "NOT_PERFORMED",
        "counts_as_verified_off_device_redundancy": False,
    },
}

POLICY_KEYS = frozenset(
    {
        "schema",
        "policy_id",
        "status",
        "mode",
        "purpose",
        "max_source_bytes",
        "allowed_source_roots",
        "denied_path_terms",
        "action_boundary",
        "storage_topology",
        "allowlist",
    }
)
ENTRY_KEYS = frozenset(
    {
        "id",
        "source_path",
        "expected_sha256",
        "receipt_schema",
        "classification",
        "public_safety_basis",
    }
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
SCHEMA_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
DENY_TERM_RE = re.compile(r"^[a-z0-9_.-]{2,32}$")

SECRET_PATTERNS = (
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("OPENAI_API_KEY", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b")),
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{20,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("BEARER_TOKEN", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")),
    (
        "SECRET_ASSIGNMENT",
        re.compile(
            r"(?i)[\"']?(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|"
            r"client[_ -]?secret|password|passwd)[\"']?\s*[:=]\s*[\"']"
            r"[A-Za-z0-9._~+/=-]{8,}"
        ),
    ),
    ("URL_CREDENTIALS", re.compile(r"(?i)https?://[^/\s:@]+:[^/\s@]+@")),
)
EMAIL_ADDRESS_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
US_SSN_RE = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
RAW_EMAIL_HEADER_RE = re.compile(r"(?im)^(?:from|to|cc|bcc|subject|message-id|date):\s+.+$")
SENSITIVE_KEY_RE = re.compile(
    r"(?i)(?:^|_)(?:api_?keys?|access_?tokens?|refresh_?tokens?|client_?secret|"
    r"credentials?|password|passwd|private_?key|secret|tokens?)(?:$|_)"
)
SAFE_EMPTY_SENSITIVE_VALUES = frozenset(
    {"", "false", "none", "not_present", "not_provided", "null", "redacted"}
)
PATH_HINT_RE = re.compile(r"(?i)(?:path|file|filename|location|uri|url)$")


class PolicyError(ValueError):
    pass


class PathSafetyError(ValueError):
    pass


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def parse_utc(value: Any, field: str = "as_of_utc") -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"{field} must be a nonempty timezone-aware timestamp")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PolicyError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PolicyError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_relative(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PathSafetyError(f"{field}:EMPTY")
    raw = value.strip()
    if raw != value or "\\" in raw or ":" in raw or raw.startswith(("/", "~")):
        raise PathSafetyError(f"{field}:ABSOLUTE_OR_PLATFORM_PATH")
    if any(character in raw for character in "*?[]{}\x00"):
        raise PathSafetyError(f"{field}:PATTERN_OR_NUL")
    candidate = PurePosixPath(raw)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise PathSafetyError(f"{field}:TRAVERSAL_OR_NONCANONICAL")
    if candidate.as_posix() != raw:
        raise PathSafetyError(f"{field}:NONCANONICAL")
    return raw


def _normalized_token_text(value: str) -> tuple[str, set[str]]:
    lowered = value.casefold()
    normalized = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    words = set(re.findall(r"[a-z0-9]+", lowered))
    return normalized, words


def denied_path_terms(value: str, terms: set[str] | frozenset[str]) -> list[str]:
    lowered = value.casefold()
    normalized, words = _normalized_token_text(value)
    findings: list[str] = []
    for term in terms:
        folded = term.casefold()
        term_normalized = re.sub(r"[^a-z0-9]+", "_", folded).strip("_")
        term_words = re.findall(r"[a-z0-9]+", folded)
        if folded.startswith("."):
            matched = folded in lowered
        elif len(term_words) == 1:
            matched = term_words[0] in words
        else:
            matched = term_normalized in normalized
        if matched:
            findings.append(term)
    return sorted(set(findings))


def path_under_any(relative_path: str, roots: list[str]) -> bool:
    return any(relative_path == root or relative_path.startswith(f"{root}/") for root in roots)


def _root_path(root: Path) -> Path:
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise PathSafetyError("ROOT_NOT_A_SECURE_DIRECTORY")
    return root.resolve(strict=True)


def _relative_to_root(root: Path, path: Path, field: str) -> str:
    root_resolved = _root_path(root)
    candidate = path if path.is_absolute() else root_resolved / path
    try:
        relative = candidate.absolute().relative_to(root_resolved).as_posix()
    except ValueError as exc:
        raise PathSafetyError(f"{field}:OUTSIDE_ROOT") from exc
    return normalize_relative(relative, field)


def secure_existing_file(root: Path, relative_path: str, *, field: str) -> Path:
    root_resolved = _root_path(root)
    current = root_resolved
    for part in PurePosixPath(relative_path).parts:
        current = current / part
        if current.is_symlink():
            raise PathSafetyError(f"{field}:SYMLINK_IN_PATH")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (OSError, ValueError) as exc:
        raise PathSafetyError(f"{field}:MISSING_OR_OUTSIDE_ROOT") from exc
    if not current.is_file():
        raise PathSafetyError(f"{field}:NOT_A_REGULAR_FILE")
    return current


def _validate_policy_text(value: Any, field: str, *, max_length: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise PolicyError(f"{field} must be nonempty canonical text")
    if len(value) > max_length or any(ord(character) < 32 for character in value):
        raise PolicyError(f"{field} is outside the bounded text contract")
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(value):
            raise PolicyError(f"{field} contains blocked content: {name}")
    if EMAIL_ADDRESS_RE.search(value) or US_SSN_RE.search(value):
        raise PolicyError(f"{field} contains blocked personal data")
    return value


def validate_policy(policy: Any) -> dict[str, Any]:
    if not isinstance(policy, dict):
        raise PolicyError("policy must be a JSON object")
    if set(policy) != POLICY_KEYS:
        raise PolicyError("policy fields do not match the frozen schema")
    if policy.get("schema") != POLICY_SCHEMA:
        raise PolicyError(f"policy schema must be {POLICY_SCHEMA}")
    if policy.get("status") != "frozen" or policy.get("mode") != MODE:
        raise PolicyError("policy must be frozen and LOCAL_MANIFEST_ONLY")
    if not ID_RE.fullmatch(str(policy.get("policy_id", ""))):
        raise PolicyError("policy_id is invalid")
    _validate_policy_text(policy.get("purpose"), "purpose")

    max_bytes = policy.get("max_source_bytes")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or not 1 <= max_bytes <= HARD_MAX_SOURCE_BYTES:
        raise PolicyError("max_source_bytes is outside the hard bound")

    roots_raw = policy.get("allowed_source_roots")
    if not isinstance(roots_raw, list) or not roots_raw:
        raise PolicyError("allowed_source_roots must be nonempty")
    try:
        roots = [normalize_relative(value, "allowed_source_roots") for value in roots_raw]
    except PathSafetyError as exc:
        raise PolicyError(str(exc)) from exc
    if len(roots) != len(set(roots)) or not set(roots).issubset(HARD_ALLOWED_SOURCE_ROOTS):
        raise PolicyError("allowed_source_roots broaden or duplicate the hard allowlist")

    denied_raw = policy.get("denied_path_terms")
    if not isinstance(denied_raw, list) or not denied_raw:
        raise PolicyError("denied_path_terms must be nonempty")
    denied = [str(value).casefold() for value in denied_raw]
    if any(not DENY_TERM_RE.fullmatch(value) for value in denied):
        raise PolicyError("denied_path_terms contains an invalid term")
    if len(denied) != len(set(denied)) or not HARD_DENIED_PATH_TERMS.issubset(set(denied)):
        raise PolicyError("denied_path_terms weaken or duplicate the hard deny boundary")

    if policy.get("action_boundary") != REQUIRED_ACTION_BOUNDARY:
        raise PolicyError("action_boundary does not match the no-I/O contract")
    if policy.get("storage_topology") != REQUIRED_STORAGE_TOPOLOGY:
        raise PolicyError("storage_topology does not match the frozen failure-domain contract")

    entries = policy.get("allowlist")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_ALLOWLIST_ITEMS:
        raise PolicyError("allowlist size is outside the bounded contract")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_names: set[str] = set()
    deny_set = set(denied)
    for index, entry in enumerate(entries):
        field = f"allowlist[{index}]"
        if not isinstance(entry, dict) or set(entry) != ENTRY_KEYS:
            raise PolicyError(f"{field} fields do not match the frozen schema")
        item_id = entry.get("id")
        if not isinstance(item_id, str) or not ID_RE.fullmatch(item_id) or item_id in seen_ids:
            raise PolicyError(f"{field}.id is invalid or duplicated")
        try:
            source_path = normalize_relative(entry.get("source_path"), f"{field}.source_path")
        except PathSafetyError as exc:
            raise PolicyError(str(exc)) from exc
        denied_hits = denied_path_terms(source_path, deny_set | HARD_DENIED_PATH_TERMS)
        if denied_hits:
            raise PolicyError(f"{field}.source_path denied: {denied_hits[0].upper().replace('-', '_')}")
        if not path_under_any(source_path, roots):
            raise PolicyError(f"{field}.source_path is outside allowed_source_roots")
        source_name = PurePosixPath(source_path).name.casefold()
        if not source_name.endswith(".json") or "receipt" not in source_name:
            raise PolicyError(f"{field}.source_path is not a receipt JSON")
        expected_sha = entry.get("expected_sha256")
        if not isinstance(expected_sha, str) or not SHA256_RE.fullmatch(expected_sha):
            raise PolicyError(f"{field}.expected_sha256 is invalid")
        receipt_schema = entry.get("receipt_schema")
        if not isinstance(receipt_schema, str) or not SCHEMA_RE.fullmatch(receipt_schema):
            raise PolicyError(f"{field}.receipt_schema is invalid")
        if entry.get("classification") != PUBLIC_CLASSIFICATION:
            raise PolicyError(f"{field}.classification is not public-safe")
        _validate_policy_text(entry.get("public_safety_basis"), f"{field}.public_safety_basis")
        if item_id in seen_ids or source_path in seen_paths or source_name in seen_names:
            raise PolicyError(f"{field} duplicates an allowlisted identity, path, or target name")
        seen_ids.add(item_id)
        seen_paths.add(source_path)
        seen_names.add(source_name)

    return policy


def load_policy(policy_path: Path, *, root: Path) -> tuple[dict[str, Any], bytes, str]:
    policy_relative = _relative_to_root(root, policy_path, "policy_path")
    if not policy_relative.startswith("config/"):
        raise PathSafetyError("policy_path:OUTSIDE_CONFIG")
    if denied_path_terms(policy_relative, HARD_DENIED_PATH_TERMS):
        raise PathSafetyError("policy_path:DENIED_PATH_CLASS")
    path = secure_existing_file(root, policy_relative, field="policy_path")
    try:
        raw = path.read_bytes()
        policy = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (OSError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise PolicyError("policy must be readable strict UTF-8 JSON") from exc
    return validate_policy(policy), raw, policy_relative


def _walk_values(value: Any, key_hint: str = "") -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            yield key_text, child
            yield from _walk_values(child, key_text)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_values(child, key_hint)


def _sensitive_value_present(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return value.strip().casefold() not in SAFE_EMPTY_SENSITIVE_VALUES
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _looks_like_path(key_hint: str, value: str) -> bool:
    return bool(PATH_HINT_RE.search(key_hint)) or "/" in value or "\\" in value


def scan_receipt_content(raw: bytes, expected_schema: str, denied_terms: set[str]) -> dict[str, Any]:
    findings: list[str] = []
    if b"\x00" in raw:
        findings.append("NUL_BYTE_CONTENT")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return {"state": "BLOCKED", "findings": ["NON_UTF8_CONTENT"]}

    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"SECRET_CONTENT_{name}")
    if EMAIL_ADDRESS_RE.search(text):
        findings.append("PERSONAL_DATA_EMAIL_ADDRESS")
    if US_SSN_RE.search(text):
        findings.append("PERSONAL_DATA_US_SSN")
    if len(RAW_EMAIL_HEADER_RE.findall(text)) >= 2:
        findings.append("RAW_EMAIL_CONTENT")

    try:
        payload = json.loads(
            text,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (ValueError, json.JSONDecodeError):
        payload = None
        findings.append("INVALID_JSON_CONTENT")

    if not isinstance(payload, dict):
        findings.append("RECEIPT_NOT_AN_OBJECT")
    else:
        if payload.get("schema") != expected_schema:
            findings.append("RECEIPT_SCHEMA_MISMATCH")
        for key, value in _walk_values(payload):
            normalized_key = re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")
            if SENSITIVE_KEY_RE.search(normalized_key) and _sensitive_value_present(value):
                findings.append("SENSITIVE_FIELD_HAS_VALUE")
            if isinstance(value, str):
                if len(RAW_EMAIL_HEADER_RE.findall(value)) >= 2:
                    findings.append("RAW_EMAIL_CONTENT")
                if _looks_like_path(key, value):
                    candidate = re.sub(r"(?i)^[a-z][a-z0-9+.-]*://[^/]*", "", value)
                    for term in denied_path_terms(candidate, denied_terms | HARD_DENIED_PATH_TERMS):
                        code = term.upper().replace("-", "_").replace(".", "DOT_")
                        findings.append(f"EMBEDDED_DENIED_PATH_{code}")

    unique = sorted(set(findings))
    return {"state": "PASS" if not unique else "BLOCKED", "findings": unique}


def read_source_bytes(path: Path, max_bytes: int) -> tuple[bytes | None, list[str], int | None]:
    try:
        before_size = path.stat().st_size
    except OSError:
        return None, ["SOURCE_STAT_FAILED"], None
    if before_size > max_bytes:
        return None, ["SOURCE_EXCEEDS_MAX_BYTES"], before_size
    try:
        raw = path.read_bytes()
        after_size = path.stat().st_size
    except OSError:
        return None, ["SOURCE_READ_FAILED"], before_size
    blockers: list[str] = []
    if len(raw) != before_size or after_size != before_size:
        blockers.append("SOURCE_CHANGED_DURING_READ")
    if len(raw) > max_bytes:
        blockers.append("SOURCE_EXCEEDS_MAX_BYTES")
    return raw, blockers, len(raw)


def evaluate_source(entry: dict[str, Any], *, root: Path, max_bytes: int, denied_terms: set[str]) -> dict[str, Any]:
    blockers: list[str] = []
    source_sha256: str | None = None
    source_bytes: int | None = None
    content_scan = {"state": "NOT_SCANNED", "findings": []}
    try:
        path = secure_existing_file(root, entry["source_path"], field="source_path")
    except PathSafetyError as exc:
        blockers.append(str(exc).split(":", 1)[-1])
    else:
        raw, read_blockers, source_bytes = read_source_bytes(path, max_bytes)
        blockers.extend(read_blockers)
        if raw is not None:
            source_sha256 = sha256_bytes(raw)
            if source_sha256 != entry["expected_sha256"]:
                blockers.append("SOURCE_SHA256_MISMATCH")
            content_scan = scan_receipt_content(raw, entry["receipt_schema"], denied_terms)
            blockers.extend(content_scan["findings"])

    blockers = sorted(set(blockers))
    source_name = PurePosixPath(entry["source_path"]).name
    return {
        "id": entry["id"],
        "source_path": entry["source_path"],
        "classification": entry["classification"],
        "receipt_schema": entry["receipt_schema"],
        "public_safety_basis": entry["public_safety_basis"],
        "bytes": source_bytes,
        "sha256": source_sha256,
        "expected_sha256": entry["expected_sha256"],
        "hash_matches": source_sha256 == entry["expected_sha256"],
        "content_scan": content_scan,
        "candidate_destinations": {
            "icloud_local_folder": f"{REQUIRED_STORAGE_TOPOLOGY['icloud']['local_folder']}/{source_name}",
            "icloud_state": "SYNC_CANDIDATE_REMOTE_COMPLETION_NOT_PROVEN",
            "google_drive_object_name": source_name,
            "google_drive_state": "SEPARATE_CONNECTOR_UPLOAD_AND_READBACK_NOT_PERFORMED",
        },
        "state": "ELIGIBLE_LOCAL_SOURCE" if not blockers else "BLOCKED_FAIL_CLOSED",
        "blockers": blockers,
    }


def build_manifest(policy_path: Path, *, root: Path = ROOT, as_of_utc: str) -> dict[str, Any]:
    as_of = parse_utc(as_of_utc)
    root_resolved = _root_path(root)
    policy, policy_raw, policy_relative = load_policy(policy_path, root=root_resolved)
    denied_terms = {str(value).casefold() for value in policy["denied_path_terms"]}
    sources = sorted(
        (
            evaluate_source(
                entry,
                root=root_resolved,
                max_bytes=policy["max_source_bytes"],
                denied_terms=denied_terms,
            )
            for entry in policy["allowlist"]
        ),
        key=lambda row: row["id"],
    )
    blocked_count = sum(bool(row["blockers"]) for row in sources)
    hashed_count = sum(row["sha256"] is not None for row in sources)
    all_sources_hashed = hashed_count == len(sources)
    all_hashes_match = all(row["hash_matches"] for row in sources)
    local_manifest_ready = blocked_count == 0 and all_sources_hashed and all_hashes_match
    source_hash_chain = [
        {"id": row["id"], "source_path": row["source_path"], "sha256": row["sha256"]}
        for row in sources
    ]

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "mode": MODE,
        "as_of_utc": utc_text(as_of),
        "policy": {
            "id": policy["policy_id"],
            "path": policy_relative,
            "sha256": sha256_bytes(policy_raw),
            "status": policy["status"],
        },
        "storage_topology": copy.deepcopy(REQUIRED_STORAGE_TOPOLOGY),
        "source_artifacts": sources,
        "source_hash_chain_sha256": stable_sha256(source_hash_chain),
        "connector_actions": {
            "icloud_remote_completion_verification": {
                "state": "NOT_PERFORMED",
                "remote_completion": "NOT_PROVEN",
                "separate_action_required": True,
                "required_evidence": "Provider-side presence plus remote readback SHA-256 match.",
            },
            "google_drive_upload_and_readback": {
                "state": "NOT_PERFORMED",
                "target_kind": "OFF_DEVICE_TARGET",
                "separate_connector_action_required": True,
                "required_evidence": "Connector upload receipt plus remote readback SHA-256 match.",
            },
        },
        "capability_boundary": {
            "policy_file_read": True,
            "allowlisted_source_bytes_read_locally": True,
            "directory_discovery_performed": False,
            "c_or_e_topology_probe_performed": False,
            "icloud_folder_probe_performed": False,
            "google_drive_connector_called": False,
            "registry_read_performed": False,
            "api_key_read_performed": False,
            "credential_store_read_performed": False,
            "file_copy_performed": False,
            "upload_performed": False,
            "remote_readback_performed": False,
            "network_action_performed": False,
            "publication_performed": False,
            "commit_or_push_performed": False,
        },
        "summary": {
            "selected_source_count": len(sources),
            "hashed_source_count": hashed_count,
            "blocked_source_count": blocked_count,
            "all_sources_hashed": all_sources_hashed,
            "all_hashes_match": all_hashes_match,
            "local_manifest_ready": local_manifest_ready,
            "independent_redundant_copy_proven": False,
            "manifest_state": (
                "LOCAL_MANIFEST_READY_REMOTE_REDUNDANCY_NOT_PROVEN"
                if local_manifest_ready
                else "BLOCKED_FAIL_CLOSED"
            ),
        },
        "claim_boundary": (
            "This local manifest proves only the byte identity and policy eligibility of the exact allowlisted "
            "source receipts. C: and E: share one physical disk and do not form independent redundancy. The "
            "iCloud folder is only a local sync candidate whose remote completion is not proven. Google Drive "
            "is an off-device target, but upload and hash readback require a separate connector action that this "
            "lane does not perform."
        ),
    }
    manifest["manifest_sha256"] = stable_sha256(manifest)
    return manifest


def render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    topology = manifest["storage_topology"]
    lines = [
        "# Cloud Redundancy Plan",
        "",
        f"As of UTC: `{manifest['as_of_utc']}`",
        f"Manifest state: `{summary['manifest_state']}`",
        f"Manifest SHA-256: `{manifest['manifest_sha256']}`",
        "",
        "## Decision",
        "",
        (
            "The allowlisted receipt bytes passed local hashing and safety checks. Remote redundancy remains "
            "unproven; this lane performed no copy, sync, upload, readback, network, registry, credential, "
            "publication, commit, or push action."
            if summary["local_manifest_ready"]
            else "The local manifest is blocked fail-closed. No transfer or external action was attempted."
        ),
        "",
        "## Storage Failure Domains",
        "",
        "| Surface | Role | State | Redundancy credit |",
        "|---|---|---|---|",
        (
            f"| `{topology['c_drive']['label']}` | Repository source volume | "
            f"`{topology['c_drive']['physical_disk_id']}` | none by itself |"
        ),
        (
            f"| `{topology['e_drive']['label']}` | Local vault volume | "
            "same physical disk as `C:` | none; a disk failure can affect both volumes |"
        ),
        (
            "| iCloud Drive local folder | Local sync candidate only | remote completion `NOT_PROVEN` | "
            "none until provider-side presence and hash readback are verified |"
        ),
        (
            "| Google Drive | Off-device target | separate connector upload/readback `NOT_PERFORMED` | "
            "none until upload receipt and remote hash readback exist |"
        ),
        "",
        "## Exact Allowlist",
        "",
        "| ID | Source | Bytes | SHA-256 | State |",
        "|---|---|---:|---|---|",
    ]
    for row in manifest["source_artifacts"]:
        lines.append(
            f"| `{row['id']}` | `{row['source_path']}` | {row['bytes'] or 0} | "
            f"`{row['sha256'] or 'NOT_HASHED'}` | `{row['state']}` |"
        )
    lines.extend(
        [
            "",
            "## Connector Boundary",
            "",
            "- iCloud: the named local folder is a sync candidate. Local presence does not prove remote completion.",
            "- Google Drive: it is the intended off-device target. Upload and readback are a separate connector action.",
            "- Completion evidence: provider-side presence and a SHA-256 readback matching each source are required.",
            "- This builder imports no connector client and does not enumerate cloud folders or local drives.",
            "",
            "## Claim Boundary",
            "",
            manifest["claim_boundary"],
        ]
    )
    return "\n".join(lines) + "\n"


def _validate_output_path(root: Path, path: Path, expected_parent: str, prefix: str) -> Path:
    root_resolved = _root_path(root)
    relative = _relative_to_root(root_resolved, path, "output_path")
    candidate = PurePosixPath(relative)
    if candidate.parent.as_posix() != expected_parent or not candidate.name.startswith(prefix):
        raise PathSafetyError("output_path:OUTSIDE_BOUNDED_DESTINATION")
    parent = root_resolved / expected_parent
    if parent.exists() and (not parent.is_dir() or parent.is_symlink()):
        raise PathSafetyError("output_path:INSECURE_PARENT")
    return root_resolved / Path(*candidate.parts)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def write_outputs(
    manifest: dict[str, Any],
    *,
    root: Path = ROOT,
    json_path: Path = DEFAULT_JSON,
    doc_path: Path = DEFAULT_DOC,
) -> None:
    bounded_json = _validate_output_path(root, json_path, "out/ops", "CLOUD_REDUNDANCY_MANIFEST_")
    bounded_doc = _validate_output_path(root, doc_path, "docs", "CLOUD_REDUNDANCY_PLAN_")
    atomic_write(
        bounded_json,
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8") + b"\n",
    )
    atomic_write(bounded_doc, render_markdown(manifest).encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic, local-only cloud redundancy manifest for exact public receipt paths."
    )
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--as-of-utc",
        required=True,
        help="Explicit timezone-aware ISO-8601 timestamp; no wall clock is read.",
    )
    parser.add_argument("--check-only", action="store_true", help="Validate and print state without writing outputs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args.policy, root=args.root, as_of_utc=args.as_of_utc)
    if not args.check_only:
        write_outputs(manifest, root=args.root)
        print(f"Wrote {DEFAULT_JSON}")
        print(f"Wrote {DEFAULT_DOC}")
    print(f"Manifest state: {manifest['summary']['manifest_state']}")
    print(f"Remote redundancy proven: {str(manifest['summary']['independent_redundant_copy_proven']).lower()}")
    return 0 if manifest["summary"]["local_manifest_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
