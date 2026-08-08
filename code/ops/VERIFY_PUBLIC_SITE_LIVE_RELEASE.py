#!/usr/bin/env python3
"""Verify that every public URL matches an exact release manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


SCHEMA = "lumencore.public_site_release_manifest.v1"
FULL_COMMIT = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
GIT_BLOB = re.compile(r"[0-9a-f]{40}")
MANIFEST_KEYS = {
    "archive_sha256",
    "file_count",
    "files",
    "schema",
    "source_commit",
    "target_directory",
}
FILE_KEYS = {
    "archive_name",
    "bytes",
    "git_blob_oid",
    "install_mode",
    "repo_path",
    "sha256",
}


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON value: {value}")


def load_manifest(path: Path) -> dict[str, object]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=_reject_constant,
    )
    if not isinstance(payload, dict):
        raise ValueError("release manifest must be a JSON object")
    if set(payload) != MANIFEST_KEYS:
        raise ValueError("release manifest fields do not match the strict schema")
    return payload


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def live_url(base_url: str, archive_name: str, source_commit: str) -> str:
    route_map = {
        "operator_home.html": "/",
        "evidence/index_bounded.html": "/evidence/",
        "build_week/prooflock_console/index.html": "/build_week/prooflock_console/",
    }
    path = route_map.get(archive_name)
    if path is None:
        path = "/" + quote(archive_name, safe="/")
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/")) + (
        f"?release={source_commit}"
    )


def verify(
    *, manifest_path: Path, source_commit: str, base_url: str, timeout: float
) -> dict[str, object]:
    manifest = load_manifest(manifest_path)
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unexpected public-site manifest schema")
    if not FULL_COMMIT.fullmatch(source_commit):
        raise ValueError("source commit must be a full lowercase SHA-1")
    if manifest.get("source_commit") != source_commit:
        raise ValueError("manifest source commit does not match requested commit")
    if manifest.get("target_directory") != "/opt/lumencore/dashboard":
        raise ValueError("manifest target directory is not the bounded dashboard root")
    if not SHA256.fullmatch(str(manifest.get("archive_sha256", ""))):
        raise ValueError("manifest archive hash is invalid")

    rows = manifest.get("files")
    file_count = manifest.get("file_count")
    if (
        not isinstance(rows, list)
        or isinstance(file_count, bool)
        or not isinstance(file_count, int)
        or file_count != len(rows)
    ):
        raise ValueError("manifest file rows are incomplete")

    results: list[dict[str, object]] = []
    seen_names: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != FILE_KEYS:
            raise ValueError("manifest file row must be an object")
        name = str(row.get("archive_name", ""))
        expected = str(row.get("sha256", ""))
        name_path = Path(name)
        byte_count = row.get("bytes")
        if (
            not name
            or name in seen_names
            or name_path.is_absolute()
            or ".." in name_path.parts
            or "\\" in name
            or not SHA256.fullmatch(expected)
            or not GIT_BLOB.fullmatch(str(row.get("git_blob_oid", "")))
            or row.get("install_mode") != "0644"
            or row.get("repo_path") != f"dashboard/{name}"
            or isinstance(byte_count, bool)
            or not isinstance(byte_count, int)
            or byte_count < 0
        ):
            raise ValueError(f"invalid manifest row: {name or '<missing>'}")
        seen_names.add(name)
        url = live_url(base_url, name, source_commit)
        request = Request(
            url,
            headers={
                "Accept-Encoding": "identity",
                "Cache-Control": "no-cache",
                "User-Agent": "LumenCore-Public-Release-Verifier/1.0",
            },
        )
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read()
                status = getattr(response, "status", 200)
        except (HTTPError, URLError, TimeoutError) as exc:
            results.append(
                {
                    "archive_name": name,
                    "expected_sha256": expected,
                    "status": "ERROR",
                    "detail": str(exc),
                    "url": url,
                }
            )
            continue

        actual = sha256(body)
        results.append(
            {
                "archive_name": name,
                "bytes": len(body),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "http_status": status,
                "status": "MATCH" if status == 200 and actual == expected else "MISMATCH",
                "url": url,
            }
        )

    matches = sum(row["status"] == "MATCH" for row in results)
    return {
        "base_url": base_url.rstrip("/"),
        "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "expected_file_count": len(rows),
        "matched_file_count": matches,
        "release_verified": matches == len(rows),
        "results": results,
        "schema": "lumencore.public_site_live_verification.v1",
        "source_commit": source_commit,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--base-url", default="https://lumen-core.ai")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        receipt = verify(
            manifest_path=args.manifest,
            source_commit=args.source_commit,
            base_url=args.base_url,
            timeout=args.timeout,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    return 0 if receipt["release_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
