from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, NamedTuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "lumencore.public_reviewer_release_canary.v1"
DEFAULT_BASE_URL = "https://lumen-core.ai"
DEFAULT_OUTPUT = ROOT / "out" / "ops" / "public_reviewer_release_canary_latest.json"
MAX_RESPONSE_BYTES = 5_000_000


class EndpointSpec(NamedTuple):
    endpoint_id: str
    route: str
    local_path: str
    expected_mime_type: str
    required_marker: str
    expected_json_schema: str | None = None


class FetchResult(NamedTuple):
    status_code: int | None
    mime_type: str | None
    body: bytes
    error: str | None = None


DEFAULT_ENDPOINTS = (
    EndpointSpec(
        endpoint_id="proof_to_pilot",
        route="/proof_to_pilot.html",
        local_path="dashboard/proof_to_pilot.html",
        expected_mime_type="text/html",
        required_marker="data/quant_hub_reviewer_context.json",
    ),
    EndpointSpec(
        endpoint_id="quant_hub_reviewer_context_json",
        route="/data/quant_hub_reviewer_context.json",
        local_path="dashboard/data/quant_hub_reviewer_context.json",
        expected_mime_type="application/json",
        required_marker="quant_hub_reviewer_context.v1",
        expected_json_schema="quant_hub_reviewer_context.v1",
    ),
    EndpointSpec(
        endpoint_id="quant_hub_reviewer_context_markdown",
        route="/evidence/QUANT_HUB_REVIEWER_CONTEXT.md",
        local_path="docs/QUANT_HUB_REVIEWER_CONTEXT_2026-07-13.md",
        expected_mime_type="text/markdown",
        required_marker="# Quant Hub Reviewer Context",
    ),
    EndpointSpec(
        endpoint_id="model_geometry_evidence_ledger",
        route="/evidence/PUBLIC_SAFE_MODEL_AND_GEOMETRY_EVIDENCE_LEDGER.md",
        local_path="docs/PUBLIC_SAFE_MODEL_AND_GEOMETRY_EVIDENCE_LEDGER_2026-07-13.md",
        expected_mime_type="text/markdown",
        required_marker="# Public-Safe Model and Geometry Evidence Ledger",
    ),
)


FetchFunction = Callable[[str, float], FetchResult]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return sha256_bytes(encoded)


def normalized_base_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base URL must use http or https")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("base URL must have a host and no embedded credentials")
    if parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain a query or fragment")
    return value.rstrip("/") + "/"


def fetch_public_url(url: str, timeout_seconds: float) -> FetchResult:
    request = Request(
        url,
        headers={
            "Accept-Encoding": "identity",
            "User-Agent": "LumenCore-Public-Reviewer-Release-Canary/1.0",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            mime_type = response.headers.get_content_type().lower()
            return FetchResult(
                status_code=int(response.status),
                mime_type=mime_type,
                body=body,
            )
    except HTTPError as exc:
        return FetchResult(
            status_code=int(exc.code),
            mime_type=None,
            body=b"",
            error=f"HTTP_{exc.code}",
        )
    except (URLError, TimeoutError, OSError) as exc:
        return FetchResult(
            status_code=None,
            mime_type=None,
            body=b"",
            error=type(exc).__name__,
        )


def validate_json_schema(data: bytes, expected_schema: str) -> bool:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("schema") == expected_schema


def check_endpoint(
    *,
    root: Path,
    base_url: str,
    spec: EndpointSpec,
    timeout_seconds: float,
    fetcher: FetchFunction,
) -> dict[str, object]:
    local_file = root / spec.local_path
    url = urljoin(base_url, spec.route.lstrip("/"))
    checks: dict[str, bool] = {
        "local_file_exists": local_file.is_file(),
        "local_marker_present": False,
        "local_json_schema_matches": spec.expected_json_schema is None,
        "http_status_200": False,
        "mime_type_matches": False,
        "response_within_size_limit": False,
        "remote_marker_present": False,
        "remote_json_schema_matches": spec.expected_json_schema is None,
        "sha256_matches_local": False,
    }
    expected_sha256: str | None = None
    observed_sha256: str | None = None
    observed_status: int | None = None
    observed_mime: str | None = None
    fetch_error: str | None = None

    if local_file.is_file():
        local_body = local_file.read_bytes()
        expected_sha256 = sha256_bytes(local_body)
        marker_bytes = spec.required_marker.encode("utf-8")
        checks["local_marker_present"] = marker_bytes in local_body
        if spec.expected_json_schema is not None:
            checks["local_json_schema_matches"] = validate_json_schema(
                local_body, spec.expected_json_schema
            )

        result = fetcher(url, timeout_seconds)
        observed_status = result.status_code
        observed_mime = result.mime_type
        fetch_error = result.error
        checks["http_status_200"] = result.status_code == 200
        checks["mime_type_matches"] = (
            result.mime_type == spec.expected_mime_type
        )
        checks["response_within_size_limit"] = (
            len(result.body) <= MAX_RESPONSE_BYTES
        )
        if checks["response_within_size_limit"]:
            observed_sha256 = sha256_bytes(result.body)
            checks["remote_marker_present"] = marker_bytes in result.body
            checks["sha256_matches_local"] = observed_sha256 == expected_sha256
            if spec.expected_json_schema is not None:
                checks["remote_json_schema_matches"] = validate_json_schema(
                    result.body, spec.expected_json_schema
                )

    failed_checks = sorted(key for key, passed in checks.items() if not passed)
    return {
        "endpoint_id": spec.endpoint_id,
        "public_url": url,
        "local_path": spec.local_path.replace("\\", "/"),
        "expected_mime_type": spec.expected_mime_type,
        "observed_mime_type": observed_mime,
        "expected_sha256": expected_sha256,
        "observed_sha256": observed_sha256,
        "observed_status_code": observed_status,
        "fetch_error": fetch_error,
        "checks": checks,
        "failed_checks": failed_checks,
        "status": "PASS" if not failed_checks else "BLOCKED",
    }


def build_receipt(
    *,
    root: Path = ROOT,
    base_url: str = DEFAULT_BASE_URL,
    endpoints: Iterable[EndpointSpec] = DEFAULT_ENDPOINTS,
    timeout_seconds: float = 15.0,
    fetcher: FetchFunction = fetch_public_url,
) -> dict[str, object]:
    normalized_url = normalized_base_url(base_url)
    rows = [
        check_endpoint(
            root=root,
            base_url=normalized_url,
            spec=spec,
            timeout_seconds=timeout_seconds,
            fetcher=fetcher,
        )
        for spec in endpoints
    ]
    passed_count = sum(row["status"] == "PASS" for row in rows)
    receipt: dict[str, object] = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        "mode": "READ_ONLY_PUBLIC_RELEASE_CANARY",
        "base_url": normalized_url.rstrip("/"),
        "capability_boundary": {
            "network_get_only": True,
            "response_bodies_persisted": False,
            "credentials_used": False,
            "remote_mutation_performed": False,
            "deployment_performed": False,
        },
        "claim_boundary": (
            "A passing receipt proves only that named public files matched the "
            "checked-out bytes, MIME types, markers, and schemas at check time. "
            "It does not establish model performance, external validation, uptime, "
            "security certification, agency approval, or commercial adoption."
        ),
        "endpoints": rows,
        "summary": {
            "endpoint_count": len(rows),
            "passed_count": passed_count,
            "blocked_count": len(rows) - passed_count,
            "status": "PASS" if passed_count == len(rows) else "BLOCKED",
        },
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt


def write_receipt(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail closed when public reviewer files differ from local evidence."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout_seconds <= 0:
        raise SystemExit("--timeout-seconds must be positive")
    receipt = build_receipt(
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
    )
    write_receipt(args.output, receipt)
    summary = receipt["summary"]
    print(
        f"{summary['status']}: {summary['passed_count']}/"
        f"{summary['endpoint_count']} reviewer endpoints matched"
    )
    print(f"WROTE: {args.output}")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
