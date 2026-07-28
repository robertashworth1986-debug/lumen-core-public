from __future__ import annotations

import argparse
import hashlib
import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


SCHEMA = "lumencore.production_surface_observation.v2"
ALLOWED_HOST = "lumen-core.ai"
MAX_BODY_BYTES = 2 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 15.0
MAX_HEALTH_AGE_SECONDS = 300.0
MAX_HEALTH_FUTURE_SKEW_SECONDS = 60.0
USER_AGENT = "LumenCore-Production-Surface-Observer/2"


@dataclass(frozen=True)
class Surface:
    name: str
    url: str
    validation: str
    marker: str | None = None


SURFACES = (
    Surface(
        "portal",
        "https://lumen-core.ai/",
        "HTML_MARKER",
        "One proof path. One bounded decision.",
    ),
    Surface(
        "evidence",
        "https://lumen-core.ai/evidence/",
        "HTML_MARKER",
        'name="lumencore-surface" content="proof-to-pilot-evidence-v1"',
    ),
    Surface(
        "gateway_health",
        "https://lumen-core.ai/health",
        "GATEWAY_HEALTH_JSON",
    ),
    Surface(
        "public_booth_contract",
        "https://lumen-core.ai/api/master/booth-brief",
        "PUBLIC_BOOTH_JSON",
    ),
)


class SurfaceProbeError(ValueError):
    pass


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Any,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


def open_without_redirects(request: Any, *, timeout: float) -> Any:
    opener = urllib.request.build_opener(_NoRedirectHandler())
    return opener.open(request, timeout=timeout)


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SurfaceProbeError("timestamp must be timezone-aware")
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def canonical_object_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_surface_definition(surface: Surface) -> None:
    parsed = urlsplit(surface.url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != ALLOWED_HOST
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.fragment
    ):
        raise SurfaceProbeError(f"unsafe surface URL: {surface.name}")
    if parsed.query:
        raise SurfaceProbeError(f"surface URL must not contain a query: {surface.name}")
    if surface.validation not in {
        "HTML_MARKER",
        "GATEWAY_HEALTH_JSON",
        "PUBLIC_BOOTH_JSON",
        "NONEMPTY_HTML",
    }:
        raise SurfaceProbeError(f"unsupported validation: {surface.validation}")
    if surface.validation == "HTML_MARKER" and not surface.marker:
        raise SurfaceProbeError(f"missing HTML marker: {surface.name}")


def _canonical_public_url(url: str) -> tuple[str, str, int, str] | None:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    try:
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme == "https"
        and parsed.hostname == ALLOWED_HOST
        and parsed.username is None
        and parsed.password is None
        and port in (None, 443)
        and not parsed.query
        and not parsed.fragment
        and "\\" not in path
        and path.startswith("/")
    ):
        return ("https", ALLOWED_HOST, 443, path)
    return None


def is_allowed_observed_url(url: str, expected_url: str) -> bool:
    observed = _canonical_public_url(url)
    expected = _canonical_public_url(expected_url)
    return observed is not None and expected is not None and observed == expected


def _content_type(headers: Any) -> str:
    if headers is None:
        return ""
    value = headers.get("Content-Type", "")
    return str(value).split(";", 1)[0].strip().lower()


def _read_bounded(response: Any) -> bytes:
    body = response.read(MAX_BODY_BYTES + 1)
    if len(body) > MAX_BODY_BYTES:
        raise SurfaceProbeError("response body exceeds bounded read limit")
    return body


def _decode_json(body: bytes) -> dict[str, Any] | None:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _parse_timestamp(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def validate_body(
    surface: Surface,
    *,
    body: bytes,
    content_type: str,
    checked_utc: datetime | None = None,
) -> tuple[bool, str]:
    if surface.validation in {"HTML_MARKER", "NONEMPTY_HTML"}:
        if content_type not in {"text/html", "application/xhtml+xml"}:
            return False, "UNEXPECTED_CONTENT_TYPE"
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            return False, "INVALID_UTF8_HTML"
        if not text.strip():
            return False, "EMPTY_HTML"
        if surface.validation == "HTML_MARKER" and surface.marker not in text:
            return False, "REQUIRED_MARKER_MISSING"
        return True, "EXPECTED_HTML_PRESENT"

    if content_type not in {"application/json", "text/json"}:
        return False, "UNEXPECTED_CONTENT_TYPE"
    payload = _decode_json(body)
    if payload is None:
        return False, "INVALID_JSON_OBJECT"

    if surface.validation == "GATEWAY_HEALTH_JSON":
        if payload.get("schema") != "lumencore.public_gateway_health.v1":
            return False, "HEALTH_SCHEMA_MISMATCH"
        generated_raw = payload.get("generated_utc")
        if not isinstance(generated_raw, str):
            return False, "HEALTH_TIMESTAMP_MISSING"
        generated = _parse_timestamp(generated_raw)
        if generated is None:
            return False, "HEALTH_TIMESTAMP_INVALID"
        checked = checked_utc or datetime.now(timezone.utc)
        if checked.tzinfo is None or checked.utcoffset() is None:
            raise SurfaceProbeError("checked_utc must be timezone-aware")
        checked_timestamp = checked.astimezone(timezone.utc)
        age_seconds = (checked_timestamp - generated).total_seconds()
        if age_seconds > MAX_HEALTH_AGE_SECONDS:
            return False, "HEALTH_TIMESTAMP_STALE"
        if age_seconds < -MAX_HEALTH_FUTURE_SKEW_SECONDS:
            return False, "HEALTH_TIMESTAMP_IN_FUTURE"
        if payload.get("status") not in {"ok", "degraded"}:
            return False, "HEALTH_STATUS_INVALID"
        if not isinstance(payload.get("all_healthy"), bool):
            return False, "HEALTH_BOOLEAN_MISSING"
        if payload["status"] != "ok" or payload["all_healthy"] is not True:
            return False, "GATEWAY_REPORTS_DEGRADED"
        claim_boundary = payload.get("claim_boundary")
        if not isinstance(claim_boundary, str) or "bounded" not in claim_boundary:
            return False, "HEALTH_CLAIM_BOUNDARY_MISSING"
        return True, "GATEWAY_REPORTS_HEALTHY"

    if payload.get("schema") != "lumencore.public_booth_contract.v2":
        return False, "PUBLIC_CONTRACT_SCHEMA_MISMATCH"
    expected = {
        "supported_maturity_level": 3,
        "public_claim_allowed": False,
        "profit_claim_allowed": False,
        "live_execution_authority": False,
        "level_5_attained": False,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        return False, "PUBLIC_CONTRACT_BOUNDARY_MISMATCH"
    claim_boundary = payload.get("claim_boundary")
    if not isinstance(claim_boundary, str) or "Level 3" not in claim_boundary:
        return False, "PUBLIC_CONTRACT_CLAIM_BOUNDARY_MISSING"
    return True, "PUBLIC_CONTRACT_BOUNDARY_PRESENT"


def probe_surface(
    surface: Surface,
    *,
    timeout_seconds: float,
    checked_utc: datetime | None = None,
    open_url: Callable[..., Any] = open_without_redirects,
) -> dict[str, Any]:
    validate_surface_definition(surface)
    if not (0.5 <= timeout_seconds <= 60.0):
        raise SurfaceProbeError("timeout_seconds must be between 0.5 and 60")

    request = urllib.request.Request(
        surface.url,
        headers={
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.1",
            "User-Agent": USER_AGENT,
        },
        method="GET",
    )
    status = 0
    content_type = ""
    body = b""
    transport_state = "RESPONSE_RECEIVED"
    body_read_state = "BODY_READ_OK"
    final_url_allowed = True

    try:
        with open_url(request, timeout=timeout_seconds) as response:
            status = int(response.getcode())
            content_type = _content_type(response.headers)
            observed_url = (
                response.geturl()
                if callable(getattr(response, "geturl", None))
                else surface.url
            )
            final_url_allowed = is_allowed_observed_url(
                str(observed_url),
                surface.url,
            )
            try:
                body = _read_bounded(response)
            except SurfaceProbeError:
                body_read_state = "RESPONSE_BODY_LIMIT_EXCEEDED"
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        content_type = _content_type(exc.headers)
        observed_url = exc.geturl() or surface.url
        final_url_allowed = is_allowed_observed_url(
            str(observed_url),
            surface.url,
        )
        try:
            body = _read_bounded(exc)
        except SurfaceProbeError:
            body_read_state = "RESPONSE_BODY_LIMIT_EXCEEDED"
            body = b""
        except OSError:
            body_read_state = "RESPONSE_BODY_READ_ERROR"
            body = b""
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        transport_state = f"TRANSPORT_ERROR_{type(exc).__name__.upper()}"

    status_ok = 200 <= status < 300
    body_valid = False
    body_state = "HTTP_STATUS_NOT_SUCCESS"
    if 300 <= status < 400:
        body_state = "REDIRECT_NOT_FOLLOWED"
    elif not final_url_allowed:
        body_state = "REDIRECT_TARGET_NOT_ALLOWED"
    elif body_read_state != "BODY_READ_OK":
        body_state = body_read_state
    elif status_ok:
        try:
            body_valid, body_state = validate_body(
                surface,
                body=body,
                content_type=content_type,
                checked_utc=checked_utc,
            )
        except SurfaceProbeError as exc:
            body_state = str(exc).upper().replace(" ", "_")

    return {
        "url": surface.url,
        "status": status,
        "status_text": f"{status:03d}",
        "status_ok": status_ok,
        "final_url_allowed": final_url_allowed,
        "content_type": content_type,
        "bytes_observed": len(body),
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_valid": body_valid,
        "validation": surface.validation,
        "validation_state": body_state,
        "transport_state": transport_state,
        "ok": status_ok and body_valid,
    }


def build_observation(
    *,
    checked_utc: datetime | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    open_url: Callable[..., Any] = open_without_redirects,
) -> dict[str, Any]:
    checked = checked_utc or datetime.now(timezone.utc)
    endpoints = {
        surface.name: probe_surface(
            surface,
            timeout_seconds=timeout_seconds,
            checked_utc=checked,
            open_url=open_url,
        )
        for surface in SURFACES
    }
    healthy_count = sum(bool(row["ok"]) for row in endpoints.values())
    total_count = len(endpoints)
    if healthy_count == total_count:
        overall = "operational"
    elif healthy_count > total_count // 2:
        overall = "degraded"
    else:
        overall = "outage"

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "checked_utc": utc_iso(checked),
        "overall": overall,
        "healthy_count": healthy_count,
        "total_count": total_count,
        "endpoints": endpoints,
        "controls": {
            "read_only": True,
            "exact_public_url_allowlist": True,
            "redirects_followed": False,
            "final_response_url_allowlist_enforced": True,
            "response_body_sha256_recorded": True,
            "bounded_response_bytes": MAX_BODY_BYTES,
            "max_health_age_seconds": MAX_HEALTH_AGE_SECONDS,
            "max_health_future_skew_seconds": MAX_HEALTH_FUTURE_SKEW_SECONDS,
            "credentials_used": False,
            "production_mutation_performed": False,
            "status_code_alone_is_sufficient": False,
        },
        "claim_boundary": (
            "This receipt observes public reachability and expected response "
            "shape at one timestamp. It does not prove availability outside the "
            "probe, production readiness, security, performance, savings, "
            "validation, endorsement, contract eligibility, or award."
        ),
    }
    payload["observation_sha256"] = canonical_object_sha256(payload)
    return payload


def build_observer_error_observation(
    *,
    checked_utc: datetime | None = None,
) -> dict[str, Any]:
    checked = checked_utc or datetime.now(timezone.utc)
    empty_hash = hashlib.sha256(b"").hexdigest()
    endpoints = {
        surface.name: {
            "url": surface.url,
            "status": 0,
            "status_text": "000",
            "status_ok": False,
            "final_url_allowed": True,
            "content_type": "",
            "bytes_observed": 0,
            "body_sha256": empty_hash,
            "body_valid": False,
            "validation": surface.validation,
            "validation_state": "OBSERVER_INTERNAL_ERROR",
            "transport_state": "OBSERVER_INTERNAL_ERROR",
            "ok": False,
        }
        for surface in SURFACES
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "checked_utc": utc_iso(checked),
        "overall": "observer_error",
        "healthy_count": 0,
        "total_count": len(SURFACES),
        "endpoints": endpoints,
        "controls": {
            "read_only": True,
            "credentials_used": False,
            "production_mutation_performed": False,
            "exception_detail_recorded": False,
        },
        "claim_boundary": (
            "The observer failed before it could produce a complete public "
            "surface observation. This receipt is fail-closed and contains no "
            "exception detail."
        ),
    }
    payload["observation_sha256"] = canonical_object_sha256(payload)
    return payload


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Observe bounded LumenCore public production surfaces."
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--require-healthy",
        action="store_true",
        help="Return nonzero unless every surface passes status and body checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checked = datetime.now(timezone.utc)
    exit_code = 0
    try:
        payload = build_observation(
            checked_utc=checked,
            timeout_seconds=args.timeout_seconds,
        )
    except Exception:
        payload = build_observer_error_observation(checked_utc=checked)
        exit_code = 3
    rendered = render_json(payload)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    if exit_code:
        return exit_code
    if args.require_healthy and payload["overall"] != "operational":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
