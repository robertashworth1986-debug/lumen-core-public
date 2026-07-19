from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "config" / "public_release_sync_policy_v1.json"
DEFAULT_JSON = ROOT / "out" / "ops" / "PUBLIC_RELEASE_SYNC_PLAN_2026-07-18.json"
DEFAULT_MD = ROOT / "docs" / "PUBLIC_RELEASE_SYNC_PLAN_2026-07-18.md"

SCHEMA = "lumencore.public_release_sync_plan.v1"
POLICY_SCHEMA = "lumencore.public_release_sync_policy.v1"
HUMAN_GATE = "HUMAN_UNLOCK_REQUIRED"
NETWORK_ACTIONS = ("deploy", "email", "post", "publish", "push")

HARD_DENIED_PATH_TOKENS = frozenset(
    {
        ".env",
        ".git",
        "api_key",
        "apikey",
        "credential",
        "gmail",
        "grant_submissions",
        "inbox",
        "mailbox",
        "oauth",
        "otp",
        "patent",
        "personally_identifiable",
        "pii",
        "portal",
        "private",
        "raw_email",
        "registry",
        "secret",
        "session",
        "token",
    }
)
HARD_ALLOWED_EXTENSION_MIME = {
    ".css": "text/css",
    ".html": "text/html",
    ".js": "text/javascript",
    ".json": "application/json",
    ".md": "text/markdown",
    ".svg": "image/svg+xml",
    ".txt": "text/plain",
}
HARD_ALLOWED_CLAIM_STATES = frozenset(
    {
        "BOUNDED_INTERNAL_EVIDENCE",
        "NO_PERFORMANCE_CLAIM",
        "PROCESS_RECEIPT",
        "PROVENANCE_AND_REPRODUCIBILITY",
    }
)

SECRET_PATTERNS = (
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("OPENAI_KEY", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}\b")),
    ("AWS_ACCESS_KEY", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{20,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("BEARER_TOKEN", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}")),
    (
        "SECRET_ASSIGNMENT",
        re.compile(
            r"(?i)\b(?:api[_ -]?key|access[_ -]?token|client[_ -]?secret|password|passwd)"
            r"\b\s*[:=]\s*[\"']?[A-Za-z0-9._~+/=-]{8,}"
        ),
    ),
    ("URL_CREDENTIALS", re.compile(r"(?i)https?://[^/\s:@]+:[^/\s@]+@")),
)
PII_PATTERNS = (
    ("EMAIL_ADDRESS", re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")),
    ("US_SSN", re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")),
    (
        "US_PHONE",
        re.compile(r"(?<!\d)(?:\+?1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\d)"),
    ),
)
UNSUPPORTED_CLAIM_PATTERNS = (
    ("SUPERLATIVE", re.compile(r"(?i)\b(?:world(?:'s)?|industry|market)\s+(?:best|leading)\b")),
    ("NUMBER_ONE", re.compile(r"(?i)(?:#\s*1\b|\bnumber\s+one\b)")),
    (
        "GOVERNMENT_APPROVAL",
        re.compile(r"(?i)\b(?:government|federal|dod)\s+(?:approved|certified|validated)\b"),
    ),
    ("GUARANTEE", re.compile(r"(?i)\b(?:guaranteed|unbeatable|flawless)\b")),
    (
        "ALL_BASELINES",
        re.compile(r"(?i)\b(?:beats?|outperforms?)\s+(?:all|every)\s+(?:approved\s+)?baselines?\b"),
    ),
    (
        "SPECULATIVE_VALUATION",
        re.compile(r"(?i)\b(?:billion|trillion)[ -]dollar\s+(?:company|estate|platform|valuation)\b"),
    ),
    (
        "ASSERTED_STATUS_BOOLEAN",
        re.compile(
            r'(?i)"(?:field_validation_proven|government_approved|externally_validated|certified|compliant)"\s*:\s*true'
        ),
    ),
)
RAW_EMAIL_HEADER = re.compile(r"(?im)^(?:from|to|cc|bcc|subject|message-id|date):\s+.+$")
CLAIM_NEGATION = re.compile(
    r"(?i)(?:"
    r"\b(?:cannot|can't|does\s+not|do\s+not|did\s+not|never)\s+(?:by\s+itself\s+)?"
    r"(?:claim|establish|prove|assert|represent|mean|imply|guarantee)\b|"
    r"\bno\s+claim\s+of\b|\bnot\s+claimed\b|\bunsupported\b|\bprohibited\b"
    r")[^.\n]{0,1000}$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"{field} must be a nonempty UTC timestamp")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise PolicyError(f"{field} is not ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PolicyError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_relative(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PathSafetyError(f"{field}:EMPTY")
    raw = value.strip()
    if "\\" in raw or ":" in raw or raw.startswith(("/", "~")):
        raise PathSafetyError(f"{field}:ABSOLUTE_OR_PLATFORM_PATH")
    candidate = PurePosixPath(raw)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise PathSafetyError(f"{field}:TRAVERSAL_OR_NONCANONICAL")
    normalized = candidate.as_posix()
    if normalized != raw:
        raise PathSafetyError(f"{field}:NONCANONICAL")
    return normalized


def path_under_any(rel: str, roots: list[str]) -> bool:
    return any(rel == root or rel.startswith(f"{root}/") for root in roots)


def denied_path_tokens(rel: str, tokens: set[str]) -> list[str]:
    lowered = rel.casefold()
    return sorted(token for token in tokens if token.casefold() in lowered)


def secure_existing_file(root: Path, rel: str) -> Path:
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise PathSafetyError("ROOT_NOT_SECURE_DIRECTORY")
    root_resolved = root.resolve(strict=True)
    current = root
    for part in PurePosixPath(rel).parts:
        current = current / part
        if current.is_symlink():
            raise PathSafetyError("SYMLINK_IN_PATH")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root_resolved)
    except (OSError, ValueError) as exc:
        raise PathSafetyError("PATH_OUTSIDE_ROOT_OR_MISSING") from exc
    if not current.is_file():
        raise PathSafetyError("NOT_A_REGULAR_FILE")
    return current


def probe_target(root: Path, rel: str, source_sha256: str) -> dict[str, Any]:
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise PathSafetyError("TARGET_ROOT_NOT_SECURE_DIRECTORY")
    root_resolved = root.resolve(strict=True)
    current = root
    for part in PurePosixPath(rel).parts:
        current = current / part
        if current.is_symlink():
            raise PathSafetyError("TARGET_SYMLINK_IN_PATH")
        if current.exists():
            try:
                current.resolve(strict=True).relative_to(root_resolved)
            except (OSError, ValueError) as exc:
                raise PathSafetyError("TARGET_PATH_OUTSIDE_ROOT") from exc
    if not current.exists():
        return {
            "state": "TARGET_ABSENT",
            "sha256": None,
            "exact_hash_match": False,
            "overwrite_allowed": False,
        }
    if not current.is_file():
        raise PathSafetyError("TARGET_NOT_A_REGULAR_FILE")
    target_sha = sha256_file(current)
    return {
        "state": "EXACT_HASH_MATCH" if target_sha == source_sha256 else "HASH_MISMATCH",
        "sha256": target_sha,
        "exact_hash_match": target_sha == source_sha256,
        "overwrite_allowed": False,
    }


def git_provenance_state(root: Path, commit: str, source_rel: str) -> tuple[str, list[str]]:
    errors: list[str] = []
    commands = (
        (["git", "-C", str(root), "cat-file", "-e", f"{commit}^{{commit}}"], "SOURCE_COMMIT_MISSING"),
        (["git", "-C", str(root), "cat-file", "-e", f"{commit}:{source_rel}"], "SOURCE_PATH_MISSING_AT_COMMIT"),
        (["git", "-C", str(root), "diff", "--quiet", commit, "--", source_rel], "SOURCE_DIFFERS_FROM_COMMIT"),
    )
    for command, code in commands:
        try:
            result = subprocess.run(command, capture_output=True, check=False, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            errors.append("GIT_PROVENANCE_CHECK_FAILED")
            break
        if result.returncode != 0:
            errors.append(code)
    return ("VERIFIED" if not errors else "FAILED", sorted(set(errors)))


def scan_content(path: Path, mime_type: str, max_bytes: int) -> dict[str, Any]:
    size = path.stat().st_size
    if size > max_bytes:
        return {"state": "BLOCKED", "findings": ["SOURCE_EXCEEDS_MAX_BYTES"], "bytes": size}
    raw = path.read_bytes()
    findings: list[str] = []
    if b"\x00" in raw:
        findings.append("NUL_BYTE_CONTENT")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
        findings.append("NON_UTF8_CONTENT")
    if text:
        findings.extend(f"SECRET_CONTENT_{name}" for name, pattern in SECRET_PATTERNS if pattern.search(text))
        findings.extend(f"PII_CONTENT_{name}" for name, pattern in PII_PATTERNS if pattern.search(text))
        for name, pattern in UNSUPPORTED_CLAIM_PATTERNS:
            for match in pattern.finditer(text):
                line_start = text.rfind("\n", 0, match.start()) + 1
                sentence_context = text[line_start : match.start()].rsplit(".", 1)[-1]
                context = re.split(r"(?i)\b(?:although|but|however|yet)\b", sentence_context)[-1]
                if not CLAIM_NEGATION.search(context):
                    findings.append(f"UNSUPPORTED_CLAIM_{name}")
                    break
        if len(RAW_EMAIL_HEADER.findall(text)) >= 2:
            findings.append("RAW_EMAIL_CONTENT")
        if mime_type == "application/json":
            try:
                json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
            except (ValueError, json.JSONDecodeError):
                findings.append("INVALID_JSON_CONTENT")
    findings = sorted(set(findings))
    return {"state": "PASS" if not findings else "BLOCKED", "findings": findings, "bytes": size}


def validate_public_url(value: Any, allowed_hosts: set[str], allowed_prefixes: list[str]) -> list[str]:
    if not isinstance(value, str):
        return ["PUBLIC_URL_MISSING"]
    parsed = urlparse(value)
    errors: list[str] = []
    if parsed.scheme != "https":
        errors.append("PUBLIC_URL_NOT_HTTPS")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        errors.append("PUBLIC_URL_HAS_FORBIDDEN_COMPONENT")
    if (parsed.hostname or "").casefold() not in allowed_hosts:
        errors.append("PUBLIC_URL_HOST_NOT_ALLOWLISTED")
    if not any(parsed.path == prefix.rstrip("/") or parsed.path.startswith(prefix) for prefix in allowed_prefixes):
        errors.append("PUBLIC_URL_PATH_NOT_ALLOWLISTED")
    return sorted(set(errors))


def load_policy(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PolicyError("policy must be readable UTF-8 JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != POLICY_SCHEMA:
        raise PolicyError(f"policy schema must be {POLICY_SCHEMA}")
    if payload.get("status") != "frozen":
        raise PolicyError("policy status must be frozen")
    if payload.get("mode") != "DRY_RUN_ONLY":
        raise PolicyError("policy mode must be DRY_RUN_ONLY")
    controls = payload.get("network_actions")
    if not isinstance(controls, dict) or any(controls.get(action) != HUMAN_GATE for action in NETWORK_ACTIONS):
        raise PolicyError("every network action must be HUMAN_UNLOCK_REQUIRED")

    denied = payload.get("denied_path_tokens")
    if not isinstance(denied, list) or not HARD_DENIED_PATH_TOKENS.issubset({str(v).casefold() for v in denied}):
        raise PolicyError("denied_path_tokens may not weaken the hard deny boundary")
    extension_mime = payload.get("allowed_extension_mime")
    if not isinstance(extension_mime, dict) or not extension_mime:
        raise PolicyError("allowed_extension_mime must be a nonempty object")
    for extension, mime_type in extension_mime.items():
        if HARD_ALLOWED_EXTENSION_MIME.get(str(extension)) != mime_type:
            raise PolicyError(f"unsupported extension/MIME pair: {extension}")
    claim_states = payload.get("allowed_claim_states")
    if not isinstance(claim_states, list) or not claim_states:
        raise PolicyError("allowed_claim_states must be nonempty")
    if not set(map(str, claim_states)).issubset(HARD_ALLOWED_CLAIM_STATES):
        raise PolicyError("policy contains an unsupported claim state")
    if not isinstance(payload.get("allowlist"), list) or not payload["allowlist"]:
        raise PolicyError("allowlist must be nonempty")
    return payload


def _validate_policy_roots(values: Any, field: str) -> list[str]:
    if not isinstance(values, list) or not values:
        raise PolicyError(f"{field} must be nonempty")
    roots: list[str] = []
    for value in values:
        roots.append(normalize_relative(value, field))
    if len(roots) != len(set(roots)):
        raise PolicyError(f"{field} contains duplicates")
    return sorted(roots)


def evaluate_item(
    entry: dict[str, Any],
    *,
    root: Path,
    target_root: Path,
    policy: dict[str, Any],
    as_of: datetime,
) -> dict[str, Any]:
    blockers: list[str] = []
    source_rel = ""
    target_rel = ""
    source_sha: str | None = None
    source_bytes: int | None = None
    content_scan: dict[str, Any] = {"state": "NOT_SCANNED", "findings": [], "bytes": None}
    target_probe: dict[str, Any] = {
        "state": "NOT_PROBED",
        "sha256": None,
        "exact_hash_match": False,
        "overwrite_allowed": False,
    }
    provenance = {"source_commit": entry.get("source_commit"), "state": "NOT_CHECKED", "findings": []}
    test_receipts: list[dict[str, Any]] = []

    item_id = entry.get("id")
    if not isinstance(item_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", item_id):
        blockers.append("INVALID_ITEM_ID")
        item_id = str(item_id or "invalid")

    try:
        source_rel = normalize_relative(entry.get("source_path"), "source_path")
    except PathSafetyError as exc:
        blockers.append(str(exc))
    try:
        target_rel = normalize_relative(entry.get("target_path"), "target_path")
    except PathSafetyError as exc:
        blockers.append(str(exc))

    allowed_source_roots = policy["_allowed_source_roots"]
    allowed_target_roots = policy["_allowed_target_roots"]
    deny_tokens = policy["_deny_tokens"]
    if source_rel:
        if not path_under_any(source_rel, allowed_source_roots):
            blockers.append("SOURCE_PATH_NOT_EXPLICITLY_ALLOWLISTED")
        blockers.extend(f"SOURCE_PATH_DENIED_{token.upper()}" for token in denied_path_tokens(source_rel, deny_tokens))
    if target_rel:
        if not path_under_any(target_rel, allowed_target_roots):
            blockers.append("TARGET_PATH_NOT_EXPLICITLY_ALLOWLISTED")
        blockers.extend(f"TARGET_PATH_DENIED_{token.upper()}" for token in denied_path_tokens(target_rel, deny_tokens))

    expected_sha = str(entry.get("expected_source_sha256") or "").casefold()
    if not SHA256_RE.fullmatch(expected_sha):
        blockers.append("EXPECTED_SOURCE_SHA256_INVALID")
    source_commit = str(entry.get("source_commit") or "").casefold()
    if not COMMIT_RE.fullmatch(source_commit) or source_commit == "0" * 40:
        blockers.append("SOURCE_COMMIT_INVALID")

    extension = PurePosixPath(source_rel).suffix.casefold() if source_rel else ""
    mime_type = entry.get("mime_type")
    expected_mime = policy["allowed_extension_mime"].get(extension)
    if expected_mime is None or mime_type != expected_mime:
        blockers.append("EXTENSION_MIME_NOT_ALLOWLISTED")

    claim_state = entry.get("claim_state")
    if claim_state not in policy["allowed_claim_states"]:
        blockers.append("CLAIM_STATE_NOT_ALLOWLISTED")
    claim_boundary = entry.get("claim_boundary")
    if not isinstance(claim_boundary, str) or len(claim_boundary.strip()) < 24:
        blockers.append("CLAIM_BOUNDARY_MISSING")

    blockers.extend(
        validate_public_url(
            entry.get("public_url"),
            policy["_allowed_public_hosts"],
            policy["allowed_public_url_prefixes"],
        )
    )

    try:
        last_validated = parse_utc(entry.get("last_validated_utc"), "last_validated_utc")
        max_age_hours = float(entry.get("max_age_hours"))
        if not (0 < max_age_hours <= float(policy["max_source_age_hours"])):
            raise ValueError
        age_hours = (as_of - last_validated).total_seconds() / 3600
        freshness = {
            "last_validated_utc": utc_text(last_validated),
            "max_age_hours": max_age_hours,
            "age_hours": round(age_hours, 6),
            "state": "FRESH" if 0 <= age_hours <= max_age_hours else "STALE",
        }
        if freshness["state"] != "FRESH":
            blockers.append("STALE_SOURCE_AGE")
    except (PolicyError, TypeError, ValueError):
        freshness = {"state": "INVALID", "last_validated_utc": entry.get("last_validated_utc")}
        blockers.append("SOURCE_FRESHNESS_INVALID")

    source_path: Path | None = None
    if source_rel and not any(
        code.startswith(("source_path:", "SOURCE_PATH_DENIED_"))
        or code == "SOURCE_PATH_NOT_EXPLICITLY_ALLOWLISTED"
        for code in blockers
    ):
        try:
            source_path = secure_existing_file(root, source_rel)
            source_sha = sha256_file(source_path)
            source_bytes = source_path.stat().st_size
            if source_sha != expected_sha:
                blockers.append("STALE_SOURCE_HASH")
            content_scan = scan_content(source_path, str(mime_type), int(policy["max_source_bytes"]))
            blockers.extend(content_scan["findings"])
        except PathSafetyError as exc:
            blockers.append(f"SOURCE_{exc}")

    if source_rel and COMMIT_RE.fullmatch(source_commit):
        state, findings = git_provenance_state(root, source_commit, source_rel)
        provenance = {"source_commit": source_commit, "state": state, "findings": findings}
        blockers.extend(findings)

    refs = entry.get("test_receipt_refs")
    if not isinstance(refs, list) or not refs:
        blockers.append("TEST_RECEIPT_REFS_MISSING")
    else:
        for ref in refs:
            row = {"path": None, "expected_sha256": None, "observed_sha256": None, "state": "BLOCKED"}
            if not isinstance(ref, dict):
                blockers.append("TEST_RECEIPT_REF_INVALID")
                test_receipts.append(row)
                continue
            try:
                ref_rel = normalize_relative(ref.get("path"), "test_receipt_ref")
                row["path"] = ref_rel
                hits = denied_path_tokens(ref_rel, deny_tokens)
                if hits:
                    raise PathSafetyError("TEST_RECEIPT_PATH_DENIED")
                expected_ref_sha = str(ref.get("expected_sha256") or "").casefold()
                row["expected_sha256"] = expected_ref_sha
                if not SHA256_RE.fullmatch(expected_ref_sha):
                    raise PathSafetyError("TEST_RECEIPT_SHA256_INVALID")
                ref_path = secure_existing_file(root, ref_rel)
                observed_ref_sha = sha256_file(ref_path)
                row["observed_sha256"] = observed_ref_sha
                row["state"] = "VERIFIED" if observed_ref_sha == expected_ref_sha else "STALE"
                if row["state"] != "VERIFIED":
                    blockers.append("TEST_RECEIPT_STALE")
            except PathSafetyError as exc:
                blockers.append(str(exc))
            test_receipts.append(row)

    if target_rel and source_sha:
        try:
            target_probe = probe_target(target_root, target_rel, source_sha)
            if target_probe["state"] == "HASH_MISMATCH":
                blockers.append("TARGET_EXISTS_HASH_MISMATCH")
        except PathSafetyError as exc:
            blockers.append(str(exc))

    blockers = sorted(set(blockers))
    if blockers:
        planned_action = "BLOCK"
    elif target_probe["state"] == "EXACT_HASH_MATCH":
        planned_action = "NOOP_EXACT_MATCH"
    elif target_probe["state"] == "TARGET_ABSENT":
        planned_action = "PLAN_NEW_LOCAL_STAGE_COPY"
    else:
        planned_action = "BLOCK"
        blockers.append("TARGET_STATE_NOT_ACTIONABLE")

    return {
        "id": item_id,
        "source_path": source_rel or None,
        "source_sha256": source_sha,
        "source_bytes": source_bytes,
        "expected_source_sha256": expected_sha or None,
        "target_path": target_rel or None,
        "mime_type": mime_type,
        "claim_state": claim_state,
        "claim_boundary": claim_boundary,
        "provenance": provenance,
        "freshness": freshness,
        "test_receipt_refs": test_receipts,
        "content_scan": content_scan,
        "target_probe": target_probe,
        "public_url_verification": {
            "url": entry.get("public_url"),
            "state": "PENDING_HUMAN_UNLOCK_AND_PUBLICATION",
            "network_request_performed": False,
            "checks_after_unlock": [
                "HTTPS_HEAD_STATUS_200",
                "HTTPS_GET_CONTENT_TYPE_MATCH",
                "HTTPS_GET_BODY_SHA256_MATCH",
                "CACHE_BYPASS_REPEAT_HASH_MATCH",
            ],
            "expected_mime_type": mime_type,
            "expected_sha256": source_sha,
        },
        "planned_action": planned_action,
        "copy_performed": False,
        "network_action_performed": False,
        "blockers": sorted(set(blockers)),
    }


def build_plan(
    policy_path: Path = DEFAULT_POLICY,
    *,
    root: Path = ROOT,
    target_root: Path | None = None,
    as_of_utc: str,
) -> dict[str, Any]:
    root = Path(root)
    target_root = Path(target_root) if target_root is not None else root
    try:
        root_absolute = Path(os.path.abspath(root))
        policy_absolute = Path(os.path.abspath(policy_path))
        policy_rel = normalize_relative(policy_absolute.relative_to(root_absolute).as_posix(), "policy_path")
        secure_policy_path = secure_existing_file(root, policy_rel)
    except (OSError, ValueError, PathSafetyError) as exc:
        raise PolicyError("policy must be a regular non-symlink file inside root") from exc
    policy = load_policy(secure_policy_path)
    as_of = parse_utc(as_of_utc, "as_of_utc")

    policy["_allowed_source_roots"] = _validate_policy_roots(policy.get("allowed_source_roots"), "allowed_source_roots")
    policy["_allowed_target_roots"] = _validate_policy_roots(policy.get("allowed_target_roots"), "allowed_target_roots")
    policy["_deny_tokens"] = {str(value).casefold() for value in policy["denied_path_tokens"]}
    hosts = policy.get("allowed_public_hosts")
    if not isinstance(hosts, list) or not hosts:
        raise PolicyError("allowed_public_hosts must be nonempty")
    policy["_allowed_public_hosts"] = {str(value).casefold() for value in hosts}
    prefixes = policy.get("allowed_public_url_prefixes")
    if not isinstance(prefixes, list) or not prefixes or any(not str(value).startswith("/") for value in prefixes):
        raise PolicyError("allowed_public_url_prefixes must contain absolute URL path prefixes")
    if not isinstance(policy.get("max_source_bytes"), int) or not (0 < policy["max_source_bytes"] <= 25_000_000):
        raise PolicyError("max_source_bytes is invalid")
    if not isinstance(policy.get("max_source_age_hours"), (int, float)) or not (
        0 < float(policy["max_source_age_hours"]) <= 8760
    ):
        raise PolicyError("max_source_age_hours is invalid")

    item_ids = [entry.get("id") for entry in policy["allowlist"] if isinstance(entry, dict)]
    if len(item_ids) != len(policy["allowlist"]) or len(item_ids) != len(set(item_ids)):
        raise PolicyError("allowlist items must be objects with unique ids")

    items = [
        evaluate_item(entry, root=root, target_root=target_root, policy=policy, as_of=as_of)
        for entry in sorted(policy["allowlist"], key=lambda row: str(row["id"]))
    ]
    blocked = [row["id"] for row in items if row["blockers"]]
    exact = [row["id"] for row in items if row["planned_action"] == "NOOP_EXACT_MATCH"]
    planned_new = [row["id"] for row in items if row["planned_action"] == "PLAN_NEW_LOCAL_STAGE_COPY"]

    public_url_plan = [
        {
            "id": row["id"],
            "url": row["public_url_verification"]["url"],
            "expected_sha256": row["public_url_verification"]["expected_sha256"],
            "expected_mime_type": row["public_url_verification"]["expected_mime_type"],
            "state": row["public_url_verification"]["state"],
        }
        for row in items
    ]
    clean_policy = {key: value for key, value in policy.items() if not key.startswith("_")}
    plan: dict[str, Any] = {
        "schema": SCHEMA,
        "as_of_utc": utc_text(as_of),
        "mode": "DRY_RUN_ONLY",
        "purpose": "Build a deterministic reviewer-safe public release sync plan without copying or performing network actions.",
        "claim_boundary": (
            "This plan is a local safety and provenance preflight. It is not proof that an artifact is public, "
            "externally validated, government approved, compliant, deployed, or accepted by a reviewer."
        ),
        "policy_path": policy_rel,
        "policy_sha256": stable_sha256(clean_policy),
        "planner_sha256": sha256_file(Path(__file__)),
        "capability_boundary": {
            "registry_accessed": False,
            "credential_store_accessed": False,
            "api_key_source_accessed": False,
            "allowlisted_candidate_bytes_scanned_locally": True,
            "secret_or_pii_values_emitted": False,
            "files_copied": False,
            "deploy_performed": False,
            "email_sent": False,
            "post_performed": False,
            "publish_performed": False,
            "push_performed": False,
        },
        "network_actions": {action: HUMAN_GATE for action in NETWORK_ACTIONS},
        "human_gate": HUMAN_GATE,
        "overwrite_policy": "Never overwrite. Existing exact-hash targets are no-ops; mismatches are blocked.",
        "items": items,
        "public_url_verification_plan": public_url_plan,
        "summary": {
            "item_count": len(items),
            "blocked_count": len(blocked),
            "blocked_item_ids": blocked,
            "exact_match_noop_count": len(exact),
            "exact_match_noop_item_ids": exact,
            "planned_new_local_stage_count": len(planned_new),
            "planned_new_local_stage_item_ids": planned_new,
            "plan_state": "BLOCKED" if blocked else "DRY_RUN_READY_HUMAN_UNLOCK_REQUIRED",
            "local_copy_performed": False,
            "network_action_performed": False,
            "public_release_completed": False,
        },
    }
    plan["plan_sha256"] = stable_sha256(plan)
    return plan


def render_markdown(plan: dict[str, Any]) -> str:
    summary = plan["summary"]
    lines = [
        "# Public Release Sync Plan",
        "",
        f"As of UTC: `{plan['as_of_utc']}`",
        f"Plan state: `{summary['plan_state']}`",
        f"Plan SHA-256: `{plan['plan_sha256']}`",
        "",
        "## Decision",
        "",
        (
            "The dry-run plan is blocked. Resolve every listed blocker and regenerate before any local staging or public action."
            if summary["blocked_count"]
            else "The dry-run plan passed local preflight. No files were copied and every network action still requires a human unlock."
        ),
        "",
        "## Safety Boundary",
        "",
        f"- Human gate: `{plan['human_gate']}`",
        "- Files copied: `false`",
        "- Network action performed: `false`",
        "- Registry, credential stores, and API-key sources accessed: `false`",
        "- Allowlisted candidate bytes scanned locally for unsafe patterns: `true`",
        "- Secret or PII values emitted: `false`",
        "- Overwrite behavior: exact-hash targets are no-ops; mismatches are blocked",
        "",
        "## Candidates",
        "",
        "| ID | Source | Target | Claim state | Action | Blockers | SHA-256 |",
        "|---|---|---|---|---|---:|---|",
    ]
    for row in plan["items"]:
        blockers = ", ".join(row["blockers"]) if row["blockers"] else "none"
        lines.append(
            f"| `{row['id']}` | `{row['source_path']}` | `{row['target_path']}` | "
            f"`{row['claim_state']}` | `{row['planned_action']}` | `{blockers}` | "
            f"`{(row['source_sha256'] or '')[:16]}` |"
        )
    lines.extend(
        [
            "",
            "## Public URL Verification",
            "",
            "No URL was contacted. After an explicit human unlock and a separate publish action, verify HTTPS status, "
            "content type, full body SHA-256, and a cache-bypass repeat hash for each URL.",
            "",
        ]
    )
    for row in plan["public_url_verification_plan"]:
        lines.append(f"- `{row['id']}`: {row['url']} (`{row['state']}`)")
    lines.extend(["", "## Claim Boundary", "", plan["claim_boundary"]])
    return "\n".join(lines) + "\n"


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


def write_outputs(plan: dict[str, Any], json_path: Path = DEFAULT_JSON, md_path: Path = DEFAULT_MD) -> None:
    for path, parent in ((json_path, ROOT / "out" / "ops"), (md_path, ROOT / "docs")):
        if path.parent.resolve() != parent.resolve() or "PUBLIC_RELEASE_SYNC" not in path.name:
            raise PathSafetyError("output path is outside the bounded PUBLIC_RELEASE_SYNC contract")
    atomic_write(json_path, json.dumps(plan, indent=2, sort_keys=True, ensure_ascii=True).encode("utf-8") + b"\n")
    atomic_write(md_path, render_markdown(plan).encode("utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a dry-run-only public release sync plan.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--target-root", type=Path, default=ROOT)
    parser.add_argument("--as-of-utc", required=True, help="Explicit ISO-8601 evaluation instant for deterministic freshness checks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_plan(args.policy, root=args.root, target_root=args.target_root, as_of_utc=args.as_of_utc)
    write_outputs(plan)
    print(f"Wrote {DEFAULT_JSON}")
    print(f"Wrote {DEFAULT_MD}")
    print(f"Plan state: {plan['summary']['plan_state']}")
    print(f"Human gate: {plan['human_gate']}")
    return 0 if plan["summary"]["blocked_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
