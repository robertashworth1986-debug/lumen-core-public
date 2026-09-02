from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MAX_TEXT_FILE_BYTES = 5 * 1024 * 1024
TEXT_EXTENSIONS = {
    "",
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".env",
    ".example",
    ".gitignore",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".jsx",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".rst",
    ".sh",
    ".sql",
    ".svg",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
QUERY_CREDENTIAL_RE = re.compile(
    r"(?i)[?&](?P<name>api[_-]?key|apikey|access[_-]?token|"
    r"client[_-]?secret|authorization|auth(?:[_-]?token)?|token|secret|"
    r"password)=(?P<value>[^&#\s\"'<>),]+)"
)
PLACEHOLDER_MARKERS = (
    "CHANGEME",
    "EXAMPLE",
    "PLACEHOLDER",
    "REDACTED",
    "REPLACE_ME",
    "YOUR_",
)
ENV_REFERENCE_RE = re.compile(r"^\$\{?[A-Z][A-Z0-9_]*\}?$")
TEMPLATE_REFERENCE_RE = re.compile(
    r"^(?:\{[^{}]+\}|%\([^)]+\)s|<[^<>]+>)$"
)


class SecretLiteralError(RuntimeError):
    pass


def git_tracked_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode != 0:
        raise SecretLiteralError("GIT_LS_FILES_FAILED")
    paths: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        try:
            relative = Path(raw.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise SecretLiteralError("TRACKED_PATH_DECODE_FAILED") from exc
        if relative.is_absolute() or ".." in relative.parts:
            raise SecretLiteralError("TRACKED_PATH_UNSAFE")
        paths.append(relative)
    return sorted(paths, key=lambda value: value.as_posix())


def is_placeholder_or_reference(value: str) -> bool:
    stripped = value.strip()
    if not stripped or stripped.casefold() in {"false", "none", "null"}:
        return True
    upper = stripped.upper()
    if any(marker in upper for marker in PLACEHOLDER_MARKERS):
        return True
    if ENV_REFERENCE_RE.fullmatch(stripped):
        return True
    if TEMPLATE_REFERENCE_RE.fullmatch(stripped):
        return True
    if any(marker in stripped for marker in ("$", "{", "}", "%(")):
        return True
    if re.fullmatch(r"\\+", stripped):
        return True
    return False


def scan_text(text: str, relative_path: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for match in QUERY_CREDENTIAL_RE.finditer(text):
        value = match.group("value")
        if is_placeholder_or_reference(value):
            continue
        findings.append(
            {
                "path": relative_path,
                "line": text.count("\n", 0, match.start()) + 1,
                "parameter": match.group("name").casefold(),
                "finding": "NON_PLACEHOLDER_QUERY_CREDENTIAL_LITERAL",
            }
        )
    return findings


def build_payload() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    scanned_file_count = 0
    skipped_non_text_file_count = 0
    for relative in git_tracked_paths():
        if relative.suffix.casefold() not in TEXT_EXTENSIONS:
            skipped_non_text_file_count += 1
            continue
        absolute = ROOT / relative
        try:
            data = absolute.read_bytes()
        except OSError:
            failures.append(
                {"path": relative.as_posix(), "failure": "READ_FAILED"}
            )
            continue
        if len(data) > MAX_TEXT_FILE_BYTES:
            failures.append(
                {"path": relative.as_posix(), "failure": "TEXT_FILE_TOO_LARGE"}
            )
            continue
        if b"\0" in data:
            failures.append(
                {"path": relative.as_posix(), "failure": "TEXT_FILE_HAS_NUL"}
            )
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            failures.append(
                {"path": relative.as_posix(), "failure": "UTF8_DECODE_FAILED"}
            )
            continue
        scanned_file_count += 1
        findings.extend(scan_text(text, relative.as_posix()))

    findings.sort(key=lambda row: (row["path"], row["line"], row["parameter"]))
    failures.sort(key=lambda row: (row["path"], row["failure"]))
    passed = not findings and not failures
    return {
        "schema": "lumencore.tracked_secret_literal_gate.v1",
        "decision": "PASS" if passed else "FAIL",
        "scope": "CURRENT_GIT_TRACKED_UTF8_TEXT_FILES",
        "scanned_file_count": scanned_file_count,
        "skipped_non_text_file_count": skipped_non_text_file_count,
        "scan_failure_count": len(failures),
        "finding_count": len(findings),
        "findings": findings,
        "failures": failures,
        "values_emitted": False,
        "external_action_performed": False,
        "claim_boundary": (
            "A pass establishes only that the current tracked UTF-8 text scope "
            "contains no detected non-placeholder credential literal in a URL "
            "query parameter. It does not establish provider rotation, history "
            "remediation, absence from non-text assets, or whole-repository secret "
            "absence."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail closed on literal credential values in URL query parameters "
            "across current Git-tracked UTF-8 text without printing values."
        )
    )
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        payload = build_payload()
    except SecretLiteralError as exc:
        payload = {
            "schema": "lumencore.tracked_secret_literal_gate.v1",
            "decision": "FAIL",
            "error": str(exc),
            "values_emitted": False,
            "external_action_performed": False,
        }
    print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    return 0 if payload.get("decision") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
