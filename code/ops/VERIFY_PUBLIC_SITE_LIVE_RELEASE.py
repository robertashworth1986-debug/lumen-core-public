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


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def live_url(base_url: str, archive_name: str, source_commit: str) -> str:
    path = "/" if archive_name == "operator_home.html" else "/" + quote(
        archive_name, safe="/"
    )
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/")) + (
        f"?release={source_commit}"
    )


def verify(
    *, manifest_path: Path, source_commit: str, base_url: str, timeout: float
) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unexpected public-site manifest schema")
    if not FULL_COMMIT.fullmatch(source_commit):
        raise ValueError("source commit must be a full lowercase SHA-1")
    if manifest.get("source_commit") != source_commit:
        raise ValueError("manifest source commit does not match requested commit")

    rows = manifest.get("files")
    if not isinstance(rows, list) or manifest.get("file_count") != len(rows):
        raise ValueError("manifest file rows are incomplete")

    results: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("manifest file row must be an object")
        name = str(row.get("archive_name", ""))
        expected = str(row.get("sha256", ""))
        if not name or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"invalid manifest row: {name or '<missing>'}")
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
