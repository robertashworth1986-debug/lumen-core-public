"""Regression tests for separating public liveness from unmapped operator feeds."""
from datetime import datetime, timedelta, timezone
from http.client import IncompleteRead
import importlib.util
import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_metrics", ROOT / "code/ops/capture_public_metrics.py")
METRICS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(METRICS)
NOW = datetime(2026, 10, 3, 23, 50, tzinfo=timezone.utc)


def receipt(status=200, content_type="application/json"):
    return {"transport": "response", "http_status": status, "content_type": content_type}


def public_payload(health=False):
    return dict(METRICS.PUBLIC_FIELDS, **({"generated_utc": NOW.isoformat()} if health else {}))


@pytest.mark.parametrize("status,payload,expected", [
    (401, {"detail": "operator API authentication required"}, "authentication_required"),
    (503, {"detail": "operator API access unavailable"}, "operator_access_unconfigured"),
    (503, {"detail": "backend unavailable"}, "http_error"),
    (403, {}, "forbidden"), (404, {}, "route_not_found"),
    (302, None, "redirect_refused"), (200, {"detail": "failure"}, "unverified_object"),
    (200, {"generated_utc": NOW.isoformat(), "secret": "do-not-retain"}, "unverified_object"),
    (200, [], "invalid_feed_response"), (502, None, "http_error"),
])
def test_feed_status_is_not_silently_discarded_or_accepted(status, payload, expected):
    result = METRICS.assess_feed(receipt(status), payload)
    assert result["disposition"] == expected
    assert result["data_available"] is False
    assert result["freshness"] == "unknown"
    assert "do-not-retain" not in json.dumps(result)


@pytest.mark.parametrize("value,expected", [
    (NOW.isoformat(), "fresh"),
    ((NOW - timedelta(minutes=5)).isoformat(), "fresh"),
    ((NOW - timedelta(minutes=5, seconds=1)).isoformat(), "stale"),
    ((NOW + timedelta(seconds=1)).isoformat(), "future"),
    ("2026-10-03T23:50:00", "unknown"), (None, "unknown"), ("bad", "unknown"),
])
def test_public_health_age_is_explicit_and_bounded(value, expected):
    payload = dict(public_payload(True), generated_utc=value)
    result = METRICS.assess_public("/health", receipt(), payload, NOW)
    assert result["freshness"] == expected
    assert result["ok"] is (expected == "fresh")


def test_minimal_gateway_cannot_substitute_for_data_products():
    def fake(path, **kwargs):
        if path == "/":
            return receipt(content_type="text/html"), None
        if path in ("/health", "/api/public/status"):
            return receipt(), public_payload(path == "/health")
        return receipt(503), {"detail": "operator API access unavailable"}
    result = METRICS.capture(fetcher=fake, now=NOW)
    assert result["public_gateway_state"] == "operational"
    assert result["site_reachability"] == "reachable"
    assert result["state"] == "degraded"
    assert result["available_objects"] == 0
    assert result["legacy_feed_freshness"] == "unknown"
    assert "operator_access_unconfigured" in METRICS.summary(result)


def test_arbitrary_json_at_all_four_routes_still_fails_closed():
    def fake(path, **kwargs):
        if path in ("/health", "/api/public/status"):
            return receipt(), public_payload(path == "/health")
        return receipt(), {"generated_utc": NOW.isoformat(), "secret": "never-publish"}
    result = METRICS.capture(fetcher=fake, now=NOW)
    assert result["legacy_feed_state"] == "unverified"
    assert result["available_objects"] == 0
    assert result["state"] == "degraded"
    assert "never-publish" not in json.dumps(result)


def test_root_failure_and_gateway_failure_remain_separate():
    def fake(path, **kwargs):
        return receipt(502), None
    result = METRICS.capture(fetcher=fake, now=NOW)
    assert result["state"] == "outage"
    assert result["public_gateway_state"] == "degraded"


@pytest.mark.parametrize("change", [{"status": "failed"}, {"private": "sensitive"}])
def test_public_schema_does_not_accept_extra_fields_or_wrong_status(change):
    assert not METRICS.assess_public("/api/public/status", receipt(), dict(public_payload(), **change), NOW)["ok"]


class Response(io.BytesIO):
    code = 200
    headers = {"Content-Type": "application/json; charset=utf-8"}

    def geturl(self):
        return METRICS.ORIGIN + "/health"


class Opener:
    def __init__(self, body=b'{}', error=None):
        self.body, self.error, self.request = body, error, None

    def open(self, request, timeout):
        self.request = request
        assert timeout == 10
        if self.error:
            raise self.error
        return Response(self.body)


def test_capture_bounds_response_size_and_sends_no_authentication():
    opener = Opener(b"x" * (METRICS.MAX_BYTES + 2))
    row, body = METRICS.fetch("/health", now=NOW, opener=opener)
    assert row["transport"] == "oversized" and body is None
    assert row["body_bytes"] == METRICS.MAX_BYTES + 1
    assert opener.request.headers["Cache-control"] == "no-cache"
    assert "metrics_probe=" in opener.request.full_url
    assert not any("auth" in key.lower() or "token" in key.lower() for key in opener.request.headers)


def test_http_error_retains_only_safe_metadata():
    error = HTTPError(METRICS.ORIGIN + "/health", 503, "Error", {"Content-Type": "application/json"}, io.BytesIO(b'{"detail":"operator API access unavailable"}'))
    row, body = METRICS.fetch("/health", now=NOW, opener=Opener(error=error))
    assert row["http_status"] == 503 and row["json_object"]
    assert "detail" not in row
    assert METRICS.assess_feed(row, body)["disposition"] == "operator_access_unconfigured"


@pytest.mark.parametrize("error", [URLError("https://secret:credential@proxy/"), IncompleteRead(b"partial")])
def test_network_errors_do_not_publish_sensitive_messages(error):
    row, body = METRICS.fetch("/health", now=NOW, opener=Opener(error=error))
    assert row["transport"] == "unavailable" and body is None
    assert "credential" not in json.dumps(row)
    assert "partial" not in json.dumps(row)


def test_unknown_paths_and_redirects_are_refused():
    with pytest.raises(ValueError):
        METRICS.fetch("/api/snapshot")
    assert METRICS.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.test/private") is None


def test_health_timestamp_after_capture_start_uses_response_completion_time(monkeypatch):
    times = iter((NOW, NOW + timedelta(seconds=3), NOW + timedelta(seconds=4)))
    monkeypatch.setattr(METRICS, "utc_now", lambda: next(times))
    def fake(path, **kwargs):
        if path == "/health":
            return receipt(), dict(public_payload(), generated_utc=(NOW + timedelta(seconds=2)).isoformat())
        if path == "/api/public/status":
            return receipt(), public_payload()
        return receipt(503), {"detail": "operator API access unavailable"}
    result = METRICS.capture(fetcher=fake)
    assert result["public_gateway_state"] == "operational"
    assert result["public_gateway"]["/health"]["age_seconds"] == 1
