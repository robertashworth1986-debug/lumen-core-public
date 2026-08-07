from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TARGET_RELATIVE = Path("LamaScout/config/api_registry.yaml")
TARGET = ROOT / TARGET_RELATIVE
STATUS_PATH = ROOT / "config" / "public_credential_remediation_status_v1.json"
DEFAULT_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "ONC_ARGOS_20260730"
    / "ARGOS_PUBLIC_REPOSITORY_SECURITY_GATE_2026-07-28.json"
)

STATUS_SCHEMA = "lumencore.public_credential_remediation_status.v1"
RECEIPT_SCHEMA = "lumencore.public_repository_security_gate.v1"
SENSITIVE_FIELD_RE = re.compile(
    r"^\s*([A-Za-z0-9_.-]*(?:api_key|token|secret|password|credential|"
    r"client_id)[A-Za-z0-9_.-]*)\s*:\s*(.*)$",
    re.IGNORECASE,
)
ENV_REFERENCE_RE = re.compile(r"^\$\{([A-Z][A-Z0-9_]*)\}$")
REQUIRED_ENV_REFERENCES = {
    "SPOTIFY_CLIENT_ID",
    "SPOTIFY_CLIENT_SECRET",
    "YOUTUBE_API_KEY",
}
PLACEHOLDER_MARKERS = {
    "CHANGEME",
    "EXAMPLE",
    "PLACEHOLDER",
    "REDACTED",
    "YOUR_",
}
PROVIDER_KEYS = {"spotify", "youtube"}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
GIT_OBJECT_RE = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
EVIDENCE_FIELDS = {
    "status",
    "verified_utc",
    "receipt_sha256",
    "reference",
}
RECORDED_EVIDENCE_STATUS = "RECORDED_NON_SECRET_RECEIPT"
MISSING_EVIDENCE_STATUS = "NOT_RECORDED"


class CredentialHygieneError(RuntimeError):
    pass


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CredentialHygieneError(f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CredentialHygieneError(f"JSON_READ_FAILED:{path}") from exc
    if not isinstance(payload, dict):
        raise CredentialHygieneError(f"JSON_ROOT_NOT_OBJECT:{path}")
    return payload


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_text_bytes(path: Path) -> bytes:
    text = path.read_text(encoding="utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(canonical_text_bytes(path)).hexdigest()


def normalized_value(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()


def is_placeholder(value: str) -> bool:
    if not value or value.lower() in {"false", "none", "null"}:
        return True
    if ENV_REFERENCE_RE.fullmatch(value):
        return True
    upper = value.upper()
    return any(marker in upper for marker in PLACEHOLDER_MARKERS)


def scan_text(text: str) -> dict[str, Any]:
    sensitive_fields: list[dict[str, Any]] = []
    non_placeholder_fields: list[dict[str, Any]] = []
    env_references: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        match = SENSITIVE_FIELD_RE.match(line)
        if not match:
            continue
        key = match.group(1)
        value = normalized_value(match.group(2))
        placeholder = is_placeholder(value) or (
            key.lower().endswith("_env")
            and re.fullmatch(r"[A-Z][A-Z0-9_]*", value) is not None
        )
        row = {
            "line": line_number,
            "key": key,
            "placeholder_like": placeholder,
        }
        sensitive_fields.append(row)
        if not placeholder:
            non_placeholder_fields.append(row)
        env_match = ENV_REFERENCE_RE.fullmatch(value)
        if env_match:
            env_references.add(env_match.group(1))
    return {
        "sensitive_fields": sensitive_fields,
        "non_placeholder_fields": non_placeholder_fields,
        "env_references": sorted(env_references),
    }


def parse_utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise CredentialHygieneError(f"{label}_UTC_INVALID") from exc
    if parsed.tzinfo is None:
        raise CredentialHygieneError(f"{label}_UTC_INVALID")
    return parsed.astimezone(timezone.utc)


def validate_evidence_receipt(
    payload: Any,
    *,
    confirmed: bool,
    label: str,
) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != EVIDENCE_FIELDS:
        raise CredentialHygieneError(f"{label}_EVIDENCE_SHAPE_INVALID")
    status = payload.get("status")
    verified_utc = payload.get("verified_utc")
    receipt_sha256 = payload.get("receipt_sha256")
    reference = payload.get("reference")
    if not confirmed:
        if payload != {
            "status": MISSING_EVIDENCE_STATUS,
            "verified_utc": None,
            "receipt_sha256": None,
            "reference": None,
        }:
            raise CredentialHygieneError(
                f"{label}_UNCONFIRMED_EVIDENCE_INVALID"
            )
        return payload
    if status != RECORDED_EVIDENCE_STATUS:
        raise CredentialHygieneError(f"{label}_EVIDENCE_STATUS_INVALID")
    parse_utc(verified_utc, f"{label}_EVIDENCE")
    if not isinstance(receipt_sha256, str) or not SHA256_RE.fullmatch(
        receipt_sha256
    ):
        raise CredentialHygieneError(f"{label}_EVIDENCE_SHA256_INVALID")
    if (
        not isinstance(reference, str)
        or not reference.strip()
        or len(reference) > 200
        or any(character in reference for character in ("?", "#", "@"))
        or re.search(
            r"(?:api[_-]?key|token|secret|password|credential)",
            reference,
            re.IGNORECASE,
        )
    ):
        raise CredentialHygieneError(f"{label}_EVIDENCE_REFERENCE_INVALID")
    return payload


def validate_status(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != STATUS_SCHEMA:
        raise CredentialHygieneError("STATUS_SCHEMA_MISMATCH")
    updated = payload.get("updated_utc")
    if not isinstance(updated, str) or not updated.endswith("Z"):
        raise CredentialHygieneError("STATUS_UPDATED_UTC_INVALID")
    providers = payload.get("providers")
    if not isinstance(providers, dict) or set(providers) != PROVIDER_KEYS:
        raise CredentialHygieneError("STATUS_PROVIDER_SET_INVALID")
    for provider, row in providers.items():
        if not isinstance(row, dict):
            raise CredentialHygieneError(f"STATUS_PROVIDER_INVALID:{provider}")
        if not isinstance(row.get("rotation_confirmed"), bool):
            raise CredentialHygieneError(
                f"STATUS_ROTATION_FLAG_INVALID:{provider}"
            )
        validate_evidence_receipt(
            row.get("evidence_receipt"),
            confirmed=row["rotation_confirmed"],
            label=f"STATUS_ROTATION_{provider.upper()}",
        )
    if not isinstance(payload.get("git_history_remediation_confirmed"), bool):
        raise CredentialHygieneError("STATUS_HISTORY_FLAG_INVALID")
    validate_evidence_receipt(
        payload.get("git_history_remediation_evidence"),
        confirmed=payload["git_history_remediation_confirmed"],
        label="STATUS_HISTORY_REMEDIATION",
    )
    remote_confirmed = payload.get(
        "remote_public_history_verification_confirmed"
    )
    if not isinstance(remote_confirmed, bool):
        raise CredentialHygieneError(
            "STATUS_REMOTE_HISTORY_VERIFICATION_FLAG_INVALID"
        )
    validate_evidence_receipt(
        payload.get("remote_public_history_verification_evidence"),
        confirmed=remote_confirmed,
        label="STATUS_REMOTE_HISTORY_VERIFICATION",
    )
    claim_boundary = payload.get("claim_boundary")
    if not isinstance(claim_boundary, str) or not claim_boundary.strip():
        raise CredentialHygieneError("STATUS_CLAIM_BOUNDARY_MISSING")
    return payload


def git_output(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if check and result.returncode != 0:
        raise CredentialHygieneError(
            f"GIT_COMMAND_FAILED:{' '.join(args[:2])}"
        )
    return result.stdout


def historical_exposure_summary() -> dict[str, Any]:
    relative = TARGET_RELATIVE.as_posix()
    shallow = git_output("rev-parse", "--is-shallow-repository").strip()
    if shallow != "false":
        raise CredentialHygieneError("HISTORY_SCAN_REQUIRES_COMPLETE_CLONE")
    if not git_output("rev-parse", "--verify", "HEAD").strip():
        raise CredentialHygieneError("HISTORY_SCAN_HAS_NO_HEAD")
    commits = [
        line.strip()
        for line in git_output("rev-list", "HEAD", "--", relative).splitlines()
        if line.strip()
    ]
    if not commits:
        raise CredentialHygieneError("HISTORY_SCAN_HAS_NO_TARGET_HISTORY")
    blob_ids: set[str] = set()
    for commit in commits:
        blob_id = git_output("rev-parse", f"{commit}:{relative}").strip()
        if not GIT_OBJECT_RE.fullmatch(blob_id):
            raise CredentialHygieneError(
                f"HISTORY_BLOB_ID_INVALID:{commit[:12]}"
            )
        blob_ids.add(blob_id.lower())

    exposed_blob_count = 0
    exposed_keys: set[str] = set()
    for blob_id in sorted(blob_ids):
        result = subprocess.run(
            ["git", "-C", str(ROOT), "cat-file", "blob", blob_id],
            capture_output=True,
            check=False,
            timeout=30,
        )
        if result.returncode != 0:
            raise CredentialHygieneError(
                f"HISTORY_OBJECT_READ_FAILED:{blob_id[:12]}"
            )
        try:
            text = result.stdout.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CredentialHygieneError(
                f"HISTORY_OBJECT_DECODE_FAILED:{blob_id[:12]}"
            ) from exc
        scan = scan_text(text)
        if scan["non_placeholder_fields"]:
            exposed_blob_count += 1
            exposed_keys.update(
                row["key"] for row in scan["non_placeholder_fields"]
            )
    blob_set_sha256 = hashlib.sha256(
        ("\n".join(sorted(blob_ids)) + "\n").encode("ascii")
    ).hexdigest()
    return {
        "scan_complete": True,
        "scan_scope": "HEAD_REACHABLE_UNIQUE_BLOBS_FOR_TARGET_PATH",
        "target_history_blob_count": len(blob_ids),
        "target_history_blob_set_sha256": blob_set_sha256,
        "scan_failure_count": 0,
        "historical_exposure_detected": exposed_blob_count > 0,
        "historical_exposed_blob_count": exposed_blob_count,
        "historical_sensitive_field_names": sorted(exposed_keys),
    }


def build_payload() -> dict[str, Any]:
    if not TARGET.is_file():
        raise CredentialHygieneError("TARGET_FILE_MISSING")
    status = validate_status(read_json(STATUS_PATH))
    current_scan = scan_text(TARGET.read_text(encoding="utf-8"))
    current_safe = not current_scan["non_placeholder_fields"]
    required_env_refs_present = REQUIRED_ENV_REFERENCES.issubset(
        set(current_scan["env_references"])
    )
    history = historical_exposure_summary()
    rotations_confirmed = all(
        row["rotation_confirmed"] for row in status["providers"].values()
    )
    history_remediated = bool(status["git_history_remediation_confirmed"])
    remote_history_verified = bool(
        status["remote_public_history_verification_confirmed"]
    )
    all_gates_clear = (
        current_safe
        and required_env_refs_present
        and rotations_confirmed
        and history_remediated
        and remote_history_verified
        and not history["historical_exposure_detected"]
    )
    sanitized_external_response_allowed = (
        current_safe
        and required_env_refs_present
        and history["scan_complete"]
        and history["scan_failure_count"] == 0
    )
    return {
        "schema": RECEIPT_SCHEMA,
        "generated_utc": status["updated_utc"],
        "target_path": TARGET_RELATIVE.as_posix(),
        "target_sha256": file_sha256(TARGET),
        "current_file": {
            "sensitive_field_count": len(current_scan["sensitive_fields"]),
            "non_placeholder_value_count": len(
                current_scan["non_placeholder_fields"]
            ),
            "non_placeholder_field_names": sorted(
                {
                    row["key"]
                    for row in current_scan["non_placeholder_fields"]
                }
            ),
            "environment_references": current_scan["env_references"],
            "required_environment_references_present": required_env_refs_present,
            "placeholder_only": current_safe,
        },
        "history": {
            **history,
            "remediation_confirmed": history_remediated,
            "remediation_evidence": status[
                "git_history_remediation_evidence"
            ],
            "remote_public_history_verification_confirmed": (
                remote_history_verified
            ),
            "remote_public_history_verification_evidence": status[
                "remote_public_history_verification_evidence"
            ],
        },
        "provider_rotation": {
            provider: {
                "confirmed": row["rotation_confirmed"],
                "evidence_receipt": row["evidence_receipt"],
            }
            for provider, row in sorted(status["providers"].items())
        },
        "decision": (
            "PASS_TARGETED_CREDENTIAL_AND_REMOTE_HISTORY_GATE"
            if all_gates_clear
            else "ALLOW_SANITIZED_EXTERNAL_RESPONSE_BLOCK_PUBLIC_REPO_LINK"
            if sanitized_external_response_allowed
            else "BLOCK_PUBLIC_REPO_LINK_AND_EXTERNAL_RESPONSE"
        ),
        "public_repository_link_allowed": all_gates_clear,
        "sanitized_external_response_allowed": (
            sanitized_external_response_allowed
        ),
        "final_argos_send_allowed_by_security_gate": (
            all_gates_clear or sanitized_external_response_allowed
        ),
        "external_action_performed": False,
        "claim_boundary": status["claim_boundary"],
        "safest_next_action": (
            "Use only a self-contained, link-free external response while rotating "
            "the affected provider credentials, recording non-secret receipts, "
            "remediating reachable public Git history, and independently verifying "
            "the public remote."
            if sanitized_external_response_allowed and not all_gates_clear
            else "Rotate the affected provider credentials, record non-secret "
            "provider receipts, remove exposed Git objects from every reachable "
            "public reference, independently verify the public remote history, "
            "and rebuild this targeted gate."
            if not all_gates_clear
            else "Preserve the receipts and continue the remaining Argos gates."
        ),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify placeholder-only current credential configuration and "
            "record provider-rotation and Git-history blockers without exposing "
            "credential values."
        )
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_RECEIPT)
    args = parser.parse_args()
    try:
        payload = build_payload()
        if args.check:
            if not args.output.is_file():
                raise CredentialHygieneError("COMMITTED_RECEIPT_MISSING")
            committed = read_json(args.output)
            if canonical_json_bytes(committed) != canonical_json_bytes(payload):
                raise CredentialHygieneError("COMMITTED_RECEIPT_STALE")
            status = "CURRENT"
        else:
            write_json(args.output, payload)
            status = "BUILT"
        print(
            json.dumps(
                {
                    "status": status,
                    "decision": payload["decision"],
                    "current_file_placeholder_only": payload["current_file"][
                        "placeholder_only"
                    ],
                    "historical_exposure_detected": payload["history"][
                        "historical_exposure_detected"
                    ],
                    "historical_scan_complete": payload["history"][
                        "scan_complete"
                    ],
                    "provider_rotations_confirmed": all(
                        row["confirmed"]
                        for row in payload["provider_rotation"].values()
                    ),
                    "remote_public_history_verification_confirmed": payload[
                        "history"
                    ]["remote_public_history_verification_confirmed"],
                    "public_repository_link_allowed": payload[
                        "public_repository_link_allowed"
                    ],
                    "final_argos_send_allowed_by_security_gate": payload[
                        "final_argos_send_allowed_by_security_gate"
                    ],
                    "external_action_performed": False,
                },
                indent=2,
            )
        )
        return 0
    except CredentialHygieneError as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error": str(exc),
                    "external_action_performed": False,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
