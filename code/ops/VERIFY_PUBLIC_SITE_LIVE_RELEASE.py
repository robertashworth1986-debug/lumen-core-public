#!/usr/bin/env python3
"""Verify that every public URL matches an exact release manifest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import ipaddress
import json
from pathlib import Path
import re
import socket
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse, urlunsplit
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
REQUEST_HEADERS = {
    "Accept-Encoding": "identity",
    "Cache-Control": "no-cache",
    "User-Agent": "LumenCore-Public-Release-Verifier/1.0",
}


def content_type_allowed(archive_name: str, content_type: str) -> bool:
    """Require standards-safe MIME types for public JSON review contracts."""
    if archive_name not in {"manifest.json", "reviewer_docket.json"}:
        return True
    if archive_name == "manifest.json":
        return content_type in {"application/json", "application/manifest+json"}
    return content_type == "application/json"


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


def normalize_resolve_address(value: str | None) -> str | None:
    """Return one normalized literal IP without performing a DNS lookup."""
    if value is None:
        return None
    if "%" in value:
        raise ValueError("resolve address must be one literal IPv4 or IPv6 address")
    try:
        return ipaddress.ip_address(value).compressed
    except ValueError as exc:
        raise ValueError("resolve address must be one literal IPv4 or IPv6 address") from exc


class ResolvedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to one IP while retaining the canonical Host and TLS SNI name."""

    def __init__(
        self,
        host: str,
        *,
        resolve_address: str,
        port: int = 443,
        timeout: float,
        context: ssl.SSLContext | None = None,
    ) -> None:
        self.resolve_address = normalize_resolve_address(resolve_address)
        super().__init__(host, port=port, timeout=timeout, context=context)

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (str(self.resolve_address), self.port),
            self.timeout,
            self.source_address,
        )
        if self._tunnel_host:
            self._tunnel()
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def fetch_url(
    url: str, *, timeout: float, resolve_address: str | None
) -> tuple[bytes, int, str]:
    """Fetch one URL, optionally pinning the connection without weakening TLS."""
    if resolve_address is None:
        request = Request(url, headers=REQUEST_HEADERS)
        with urlopen(request, timeout=timeout) as response:
            return (
                response.read(),
                getattr(response, "status", 200),
                response.headers.get_content_type().casefold(),
            )

    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError(
            "resolve-address verification requires a credential-free HTTPS URL"
        )
    port = parsed.port or 443
    host_header = parsed.hostname if port == 443 else f"{parsed.hostname}:{port}"
    target = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
    connection = ResolvedHTTPSConnection(
        parsed.hostname,
        resolve_address=resolve_address,
        port=port,
        timeout=timeout,
        context=ssl.create_default_context(),
    )
    try:
        connection.request(
            "GET",
            target,
            headers={**REQUEST_HEADERS, "Host": host_header},
        )
        response = connection.getresponse()
        body = response.read()
        if response.status >= 400:
            raise HTTPError(
                url,
                response.status,
                response.reason,
                response.headers,
                None,
            )
        return body, response.status, response.headers.get_content_type().casefold()
    finally:
        connection.close()


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
    *,
    manifest_path: Path,
    source_commit: str,
    base_url: str,
    timeout: float,
    resolve_address: str | None = None,
) -> dict[str, object]:
    resolve_address = normalize_resolve_address(resolve_address)
    parsed_base = urlparse(base_url)
    if resolve_address is not None and (
        parsed_base.scheme != "https"
        or not parsed_base.hostname
        or parsed_base.username is not None
        or parsed_base.password is not None
        or parsed_base.query
        or parsed_base.fragment
    ):
        raise ValueError(
            "resolve-address verification requires a credential-free HTTPS base URL"
        )
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
        try:
            body, status, content_type = fetch_url(
                url,
                timeout=timeout,
                resolve_address=resolve_address,
            )
        except (
            HTTPError,
            URLError,
            TimeoutError,
            OSError,
            http.client.HTTPException,
        ) as exc:
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
        mime_ok = content_type_allowed(name, content_type)
        results.append(
            {
                "archive_name": name,
                "bytes": len(body),
                "content_type": content_type,
                "content_type_allowed": mime_ok,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "http_status": status,
                "status": (
                    "MATCH"
                    if status == 200 and actual == expected and mime_ok
                    else "MISMATCH"
                ),
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
    parser.add_argument(
        "--resolve-address",
        help=(
            "Connect to this literal IP while preserving the URL hostname for "
            "the Host header, TLS SNI, and certificate verification"
        ),
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        receipt = verify(
            manifest_path=args.manifest,
            source_commit=args.source_commit,
            base_url=args.base_url,
            timeout=args.timeout,
            resolve_address=args.resolve_address,
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
