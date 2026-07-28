from __future__ import annotations

import io
import json
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "code" / "ops"
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

import probe_production_surfaces as observer  # noqa: E402
from probe_production_surfaces import (  # noqa: E402
    MAX_BODY_BYTES,
    SURFACES,
    Surface,
    SurfaceProbeError,
    build_observation,
    build_observer_error_observation,
    canonical_object_sha256,
    open_without_redirects,
    probe_surface,
    validate_body,
    validate_surface_definition,
)


class _FakeResponse:
    def __init__(
        self,
        *,
        status: int,
        body: bytes,
        content_type: str,
        final_url: str,
    ) -> None:
        self._status = status
        self._body = body
        self._final_url = final_url
        self.headers = {"Content-Type": content_type}

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def getcode(self) -> int:
        return self._status

    def geturl(self) -> str:
        return self._final_url

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]


def _assert_probe_error(callback: object) -> None:
    try:
        callback()  # type: ignore[operator]
    except SurfaceProbeError:
        return
    raise AssertionError("expected SurfaceProbeError")


def _surface(name: str) -> Surface:
    return next(surface for surface in SURFACES if surface.name == name)


def _health_body(
    *,
    healthy: bool = True,
    generated_utc: str = "2026-07-27T23:00:00Z",
) -> bytes:
    return json.dumps(
        {
            "schema": "lumencore.public_gateway_health.v1",
            "generated_utc": generated_utc,
            "status": "ok" if healthy else "degraded",
            "all_healthy": healthy,
            "claim_boundary": "A current bounded process-health signal.",
        }
    ).encode("utf-8")


def _booth_body() -> bytes:
    return json.dumps(
        {
            "schema": "lumencore.public_booth_contract.v2",
            "supported_maturity_level": 3,
            "public_claim_allowed": False,
            "profit_claim_allowed": False,
            "live_execution_authority": False,
            "level_5_attained": False,
            "claim_boundary": "Bounded public Level 3 evidence only.",
        }
    ).encode("utf-8")


def _healthy_opener(request: object, *, timeout: float) -> _FakeResponse:
    assert 0.5 <= timeout <= 60.0
    url = request.full_url  # type: ignore[attr-defined]
    if url.endswith("/health"):
        return _FakeResponse(
            status=200,
            body=_health_body(),
            content_type="application/json; charset=utf-8",
            final_url=url,
        )
    if url.endswith("/api/master/booth-brief"):
        return _FakeResponse(
            status=200,
            body=_booth_body(),
            content_type="application/json",
            final_url=url,
        )
    surface = next(item for item in SURFACES if item.url == url)
    marker = surface.marker or "Bounded public surface."
    body = f"<html><body>{marker}</body></html>".encode("utf-8")
    return _FakeResponse(
        status=200,
        body=body,
        content_type="text/html; charset=utf-8",
        final_url=url,
    )


def test_surface_allowlist_is_exact_and_complete() -> None:
    assert [surface.name for surface in SURFACES] == [
        "portal",
        "evidence",
        "gateway_health",
        "public_booth_contract",
    ]
    for surface in SURFACES:
        validate_surface_definition(surface)

    for unsafe_url in (
        "http://lumen-core.ai/",
        "https://example.com/",
        "https://user@lumen-core.ai/",
        "https://lumen-core.ai:444/",
        "https://lumen-core.ai/?token=synthetic",
        "https://lumen-core.ai/#fragment",
    ):
        _assert_probe_error(
            lambda url=unsafe_url: validate_surface_definition(
                Surface("unsafe", url, "NONEMPTY_HTML")
            )
        )


def test_html_markers_match_the_deployable_source_files() -> None:
    source_by_surface = {
        "portal": ROOT / "dashboard" / "operator_home.html",
        "evidence": ROOT / "dashboard" / "evidence" / "index_bounded.html",
    }
    for name, path in source_by_surface.items():
        surface = _surface(name)
        assert surface.validation == "HTML_MARKER"
        assert surface.marker
        assert surface.marker in path.read_text(encoding="utf-8")


def test_html_marker_and_content_type_validation_fail_closed() -> None:
    surface = _surface("portal")
    valid, state = validate_body(
        surface,
        body=b"<html>One proof path. One bounded decision.</html>",
        content_type="text/html",
    )
    assert valid is True
    assert state == "EXPECTED_HTML_PRESENT"

    valid, state = validate_body(
        surface,
        body=b"<html>generic page</html>",
        content_type="text/html",
    )
    assert valid is False
    assert state == "REQUIRED_MARKER_MISSING"

    valid, state = validate_body(
        surface,
        body=b"<html>One proof path. One bounded decision.</html>",
        content_type="text/plain",
    )
    assert valid is False
    assert state == "UNEXPECTED_CONTENT_TYPE"


def test_gateway_health_requires_an_explicit_healthy_body() -> None:
    surface = _surface("gateway_health")
    checked = datetime(2026, 7, 27, 23, 0, tzinfo=timezone.utc)
    valid, state = validate_body(
        surface,
        body=_health_body(),
        content_type="application/json",
        checked_utc=checked,
    )
    assert valid is True
    assert state == "GATEWAY_REPORTS_HEALTHY"

    payload = json.loads(_health_body())
    payload["schema"] = "unexpected"
    valid, state = validate_body(
        surface,
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
        checked_utc=checked,
    )
    assert valid is False
    assert state == "HEALTH_SCHEMA_MISMATCH"

    valid, state = validate_body(
        surface,
        body=_health_body(healthy=False),
        content_type="application/json",
        checked_utc=checked,
    )
    assert valid is False
    assert state == "GATEWAY_REPORTS_DEGRADED"

    valid, state = validate_body(
        surface,
        body=(
            b'{"schema":"lumencore.public_gateway_health.v1",'
            b'"status":"ok","all_healthy":true}'
        ),
        content_type="application/json",
        checked_utc=checked,
    )
    assert valid is False
    assert state == "HEALTH_TIMESTAMP_MISSING"

    for generated_utc, expected_state in (
        ("not-a-timestamp", "HEALTH_TIMESTAMP_INVALID"),
        ("2026-07-27T22:54:59Z", "HEALTH_TIMESTAMP_STALE"),
        ("2026-07-27T23:01:01Z", "HEALTH_TIMESTAMP_IN_FUTURE"),
    ):
        valid, state = validate_body(
            surface,
            body=_health_body(generated_utc=generated_utc),
            content_type="application/json",
            checked_utc=checked,
        )
        assert valid is False
        assert state == expected_state


def test_public_booth_contract_requires_level_three_claim_boundaries() -> None:
    surface = _surface("public_booth_contract")
    valid, state = validate_body(
        surface,
        body=_booth_body(),
        content_type="application/json",
    )
    assert valid is True
    assert state == "PUBLIC_CONTRACT_BOUNDARY_PRESENT"

    payload = json.loads(_booth_body())
    payload["schema"] = "unexpected"
    valid, state = validate_body(
        surface,
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
    )
    assert valid is False
    assert state == "PUBLIC_CONTRACT_SCHEMA_MISMATCH"

    payload = json.loads(_booth_body())
    payload["public_claim_allowed"] = True
    valid, state = validate_body(
        surface,
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
    )
    assert valid is False
    assert state == "PUBLIC_CONTRACT_BOUNDARY_MISMATCH"

    payload = json.loads(_booth_body())
    payload["claim_boundary"] = "Unbounded"
    valid, state = validate_body(
        surface,
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
    )
    assert valid is False
    assert state == "PUBLIC_CONTRACT_CLAIM_BOUNDARY_MISSING"


def test_http_502_is_a_probe_result_not_an_exception() -> None:
    surface = _surface("gateway_health")

    def opener(request: object, *, timeout: float) -> object:
        raise urllib.error.HTTPError(
            request.full_url,  # type: ignore[attr-defined]
            502,
            "Bad Gateway",
            {"Content-Type": "text/html"},
            io.BytesIO(b"bad gateway"),
        )

    result = probe_surface(surface, timeout_seconds=3.0, open_url=opener)
    assert result["status"] == 502
    assert result["status_text"] == "502"
    assert result["status_ok"] is False
    assert result["body_valid"] is False
    assert result["validation_state"] == "HTTP_STATUS_NOT_SUCCESS"
    assert result["ok"] is False


def test_transport_error_is_normalized_without_error_text() -> None:
    surface = _surface("evidence")

    def opener(_request: object, *, timeout: float) -> object:
        raise urllib.error.URLError("synthetic private error detail")

    result = probe_surface(surface, timeout_seconds=3.0, open_url=opener)
    assert result["status"] == 0
    assert result["status_text"] == "000"
    assert result["transport_state"] == "TRANSPORT_ERROR_URLERROR"
    assert "synthetic" not in json.dumps(result)
    assert result["ok"] is False


def test_cross_host_redirect_and_oversized_body_fail_closed() -> None:
    surface = _surface("portal")

    def redirecting_opener(request: object, *, timeout: float) -> _FakeResponse:
        return _FakeResponse(
            status=200,
            body=b"<html>One proof path. One bounded decision.</html>",
            content_type="text/html",
            final_url="https://example.com/",
        )

    result = probe_surface(
        surface,
        timeout_seconds=3.0,
        open_url=redirecting_opener,
    )
    assert result["status_ok"] is True
    assert result["final_url_allowed"] is False
    assert result["validation_state"] == "REDIRECT_TARGET_NOT_ALLOWED"
    assert result["ok"] is False

    def oversized_opener(request: object, *, timeout: float) -> _FakeResponse:
        return _FakeResponse(
            status=200,
            body=b"x" * (MAX_BODY_BYTES + 1),
            content_type="text/html",
            final_url=request.full_url,  # type: ignore[attr-defined]
        )

    result = probe_surface(
        surface,
        timeout_seconds=3.0,
        open_url=oversized_opener,
    )
    assert result["status_ok"] is True
    assert result["validation_state"] == "RESPONSE_BODY_LIMIT_EXCEEDED"
    assert result["ok"] is False


def test_default_transport_refuses_redirect_before_second_request() -> None:
    surface = _surface("portal")
    calls = []
    handlers = []

    class RecordingOpener:
        def open(self, request: object, *, timeout: float) -> object:
            calls.append(request.full_url)  # type: ignore[attr-defined]
            raise urllib.error.HTTPError(
                request.full_url,  # type: ignore[attr-defined]
                302,
                "Found",
                {
                    "Content-Type": "text/html",
                    "Location": "https://example.com/private-target",
                },
                io.BytesIO(b"redirect"),
            )

    original = observer.urllib.request.build_opener

    def build_opener(handler: object) -> RecordingOpener:
        handlers.append(handler)
        return RecordingOpener()

    observer.urllib.request.build_opener = build_opener
    try:
        result = probe_surface(
            surface,
            timeout_seconds=3.0,
            open_url=open_without_redirects,
        )
    finally:
        observer.urllib.request.build_opener = original

    assert calls == [surface.url]
    assert len(handlers) == 1
    assert handlers[0].redirect_request(
        None,
        None,
        302,
        "Found",
        {},
        "https://example.com/private-target",
    ) is None
    assert result["status"] == 302
    assert result["validation_state"] == "REDIRECT_NOT_FOLLOWED"
    assert result["ok"] is False


def test_same_host_path_redirect_is_not_an_allowed_final_url() -> None:
    surface = _surface("portal")

    def redirecting_opener(request: object, *, timeout: float) -> _FakeResponse:
        return _FakeResponse(
            status=200,
            body=b"<html>One proof path. One bounded decision.</html>",
            content_type="text/html",
            final_url="https://lumen-core.ai/other-path",
        )

    result = probe_surface(
        surface,
        timeout_seconds=3.0,
        open_url=redirecting_opener,
    )
    assert result["final_url_allowed"] is False
    assert result["validation_state"] == "REDIRECT_TARGET_NOT_ALLOWED"
    assert result["ok"] is False


def test_observation_is_deterministic_and_hash_bound() -> None:
    checked = datetime(2026, 7, 27, 23, 0, tzinfo=timezone.utc)
    first = build_observation(checked_utc=checked, open_url=_healthy_opener)
    second = build_observation(checked_utc=checked, open_url=_healthy_opener)

    assert first == second
    assert first["overall"] == "operational"
    assert first["healthy_count"] == len(SURFACES)
    assert first["total_count"] == len(SURFACES)
    assert first["metric_semantics"] == {
        "metric_name": "point_in_time_public_surface_contract_pass_count",
        "numerator_field": "healthy_count",
        "denominator_field": "total_count",
        "scope": "selected_public_endpoints_at_checked_utc",
        "repository_quality_score": False,
        "cross_repository_comparison": False,
        "valuation_signal": False,
        "scientific_performance_evidence": False,
        "external_validation_evidence": False,
    }
    assert "repository quality relative to peers" in first["claim_boundary"]
    assert "valuation" in first["claim_boundary"]
    assert all(row["ok"] for row in first["endpoints"].values())
    assert first["controls"]["production_mutation_performed"] is False
    assert first["controls"]["credentials_used"] is False
    assert first["controls"]["redirects_followed"] is False
    assert all(
        len(row["body_sha256"]) == 64
        for row in first["endpoints"].values()
    )

    without_hash = dict(first)
    observed_hash = without_hash.pop("observation_sha256")
    assert observed_hash == canonical_object_sha256(without_hash)


def test_equal_length_response_changes_are_bound_by_body_hash() -> None:
    surface = _surface("portal")

    def opener_for(body: bytes):
        def opener(request: object, *, timeout: float) -> _FakeResponse:
            return _FakeResponse(
                status=200,
                body=body,
                content_type="text/html",
                final_url=request.full_url,  # type: ignore[attr-defined]
            )

        return opener

    first_body = b"<html>One proof path. One bounded decision.A</html>"
    second_body = b"<html>One proof path. One bounded decision.B</html>"
    assert len(first_body) == len(second_body)
    first = probe_surface(
        surface,
        timeout_seconds=3.0,
        open_url=opener_for(first_body),
    )
    second = probe_surface(
        surface,
        timeout_seconds=3.0,
        open_url=opener_for(second_body),
    )
    assert first["ok"] is True
    assert second["ok"] is True
    assert first["bytes_observed"] == second["bytes_observed"]
    assert first["body_sha256"] != second["body_sha256"]


def test_observer_error_receipt_is_fail_closed_and_hash_bound() -> None:
    checked = datetime(2026, 7, 27, 23, 0, tzinfo=timezone.utc)
    receipt = build_observer_error_observation(checked_utc=checked)
    assert receipt["overall"] == "observer_error"
    assert receipt["healthy_count"] == 0
    assert receipt["total_count"] == len(SURFACES)
    assert receipt["metric_semantics"]["repository_quality_score"] is False
    assert receipt["metric_semantics"]["cross_repository_comparison"] is False
    assert receipt["metric_semantics"]["valuation_signal"] is False
    assert all(not row["ok"] for row in receipt["endpoints"].values())
    serialized = json.dumps(receipt)
    assert "synthetic private error" not in serialized
    without_hash = dict(receipt)
    observed_hash = without_hash.pop("observation_sha256")
    assert observed_hash == canonical_object_sha256(without_hash)


def test_require_healthy_returns_nonzero_for_degraded_observation() -> None:
    original = observer.build_observation
    observer.build_observation = lambda **_kwargs: {
        "overall": "degraded",
        "observation_sha256": "synthetic",
    }
    try:
        assert observer.main(["--require-healthy"]) == 2
    finally:
        observer.build_observation = original


def test_health_workflow_uses_body_validating_observer() -> None:
    workflow = (ROOT / ".github" / "workflows" / "health-probe.yml").read_text(
        encoding="utf-8"
    )
    assert "code/ops/probe_production_surfaces.py" in workflow
    assert "check_endpoint()" not in workflow
    assert "body_valid" in workflow
    assert "validation_state" in workflow
    assert "body_sha256" in workflow
    assert "outputs.total" in workflow
    assert "/6 endpoints healthy" not in workflow
    assert "contents: read" in workflow
    assert "actions/upload-artifact@" in workflow
    assert "git push" not in workflow
    assert "contents: write" not in workflow
    assert "--require-healthy" in workflow
    assert "Fail on non-operational observation" in workflow
    assert "steps.probe.outputs.observer_rc == '2'" in workflow
