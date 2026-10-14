from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_health_probe", ROOT / "code/ops/probe_public_health.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)

NOW = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)
PUBLIC_FIELDS = {"status": "ok", "service": "luma-experience-gateway",
                 "access_boundary": "operator_api_v1", "public_surface": "minimal"}


def observation(endpoint, index, ok=True):
    name, url, contract = endpoint
    body = probe.MARKERS.get(contract, "").encode()
    content_type = "text/html"
    if contract not in probe.MARKERS:
        content_type = "application/json"
        payload = dict(PUBLIC_FIELDS)
        if contract == "gateway_health":
            payload["generated_utc"] = "2026-10-14T12:00:00Z"
        body = json.dumps(payload).encode()
    row = probe.classify(contract, 200 if ok else 502, content_type, body,
                         transport_ok=True, same_origin_ok=True, now=NOW)
    row.update({"name": name, "url": url, "sample_index": index,
                "started_utc": f"2026-10-03T23:0{index}:00Z", "completed_utc": f"2026-10-03T23:0{index}:01Z"})
    return row


def test_late_recovery_cannot_erase_first_failed_observation():
    endpoint = probe.ENDPOINTS[0]
    rows = [observation(endpoint, i, i != 2) for i in range(1, 5)]
    summary = probe.summarize(rows, 4, 60, rows[0]["started_utc"], endpoints=(endpoint,))
    assert summary["overall"] != "operational"
    assert summary["healthy_count"] == 0
    retained = summary["endpoints"]["portal"]
    assert retained["status"] == 502
    assert retained["first_failure_utc"] == rows[1]["started_utc"]
    assert retained["successful_count"] == 3
    assert retained["flapping_observed"] is True
    assert summary["observation_window"]["failed_observations"] == 1


def test_www_failure_controls_overall_verdict_without_hiding_healthy_apex():
    rows = [observation(endpoint, i, endpoint[0] != "www_portal" or i != 3)
            for endpoint in probe.ENDPOINTS for i in range(1, 5)]
    summary = probe.summarize(rows, 4, 60, rows[0]["started_utc"])
    assert summary["overall"] == "degraded"
    assert summary["endpoints"]["portal"]["ok"] is True
    assert summary["endpoints"]["www_portal"]["ok"] is False
    assert summary["healthy_count"] == 15
    assert summary["total_count"] == 16


def test_duplicate_or_missing_round_cannot_pass():
    endpoint = probe.ENDPOINTS[0]
    for indexes in ((1, 2, 4), (1, 2, 2, 4), ()):
        rows = [observation(endpoint, i) for i in indexes]
        summary = probe.summarize(rows, 4, 60, "2026-10-03T23:00:00Z", endpoints=(endpoint,))
        assert summary["overall"] != "operational"
        assert summary["observation_window"]["all_samples_complete"] is False


def test_contract_requires_html_marker_origin_and_completed_transport():
    for status, mime, body, transport, origin, expected in (
        (200, "text/html; charset=utf-8", b"proof-to-pilot-home-v1", True, True, True),
        (200, "text/plain", b"proof-to-pilot-home-v1", True, True, False),
        (200, "text/html", b"wrong release", True, True, False),
        (200, "text/html", b"proof-to-pilot-home-v1", False, True, False),
        (200, "text/html", b"proof-to-pilot-home-v1", True, False, False),
        (502, "text/html", b"proof-to-pilot-home-v1", True, True, False),
    ):
        row = probe.classify("home", status, mime, body, transport_ok=transport, same_origin_ok=origin)
        assert row["ok"] is expected


def test_gateway_requires_exact_public_contract_and_timestamp():
    payload = {"status": "ok", "service": "luma-experience-gateway",
               "access_boundary": "operator_api_v1", "public_surface": "minimal",
               "generated_utc": "2026-10-14T12:00:00Z"}
    for replacement in ({}, {"status": "degraded"}, {"service": "other"}, {"generated_utc": ""}):
        current = dict(payload, **replacement)
        row = probe.classify("gateway_health", 200, "application/json", json.dumps(current).encode(),
                             transport_ok=True, same_origin_ok=True, now=NOW)
        assert row["ok"] is (replacement == {})
    for body in (b"[]", b"{}", b"<html>healthy</html>"):
        row = probe.classify("public_status", 200, "text/html", body, transport_ok=True, same_origin_ok=True)
        assert row["ok"] is False


def test_probe_preserves_http_code_and_failure_after_partial_body_timeout():
    recorded = []
    def fake_run(command, **kwargs):
        recorded.append(command)
        Path(command[command.index("--output") + 1]).write_bytes(b"proof-to-pilot-home-v1")
        url = command[-1]
        return subprocess.CompletedProcess(command, 28, f"200\ntext/html\n{url}\n10.001", "timeout")
    with patch.object(probe.subprocess, "run", side_effect=fake_run):
        row = probe.probe(probe.ENDPOINTS[0], 1, "test-token")
    assert row["status"] == 200
    assert row["ok"] is False
    assert row["curl_exit_code"] == 28
    assert row["transport_error"] == "timeout"
    assert len(row["response_sha256"]) == 64
    assert row["elapsed_ms"] >= 0
    command = recorded[0]
    assert "--retry" not in command
    assert "Cache-Control: no-cache, no-store" in command
    assert "_lc_health_probe=test-token-1-portal" in command[-1]


def test_wrong_origin_redirect_and_oversized_body_fail_closed():
    for body, effective_url in ((b"proof-to-pilot-home-v1", "https://example.invalid/"),
                                (b"proof-to-pilot-home-v1" + b"x" * 1100, probe.ENDPOINTS[0][1])):
        def fake_run(command, **kwargs):
            Path(command[command.index("--output") + 1]).write_bytes(body)
            return subprocess.CompletedProcess(command, 0, f"200\ntext/html\n{effective_url}\n0.01", "")
        with patch.object(probe.subprocess, "run", side_effect=fake_run):
            row = probe.probe(probe.ENDPOINTS[0], 1, "test", max_bytes=1024)
        assert row["ok"] is False
        assert row["response_bytes"] <= 1025


def test_process_timeout_is_a_retained_failure():
    with patch.object(probe.subprocess, "run", side_effect=subprocess.TimeoutExpired("curl", 13)):
        row = probe.probe(probe.ENDPOINTS[0], 1, "test")
    assert row["ok"] is False
    assert row["curl_exit_code"] == 124
    assert row["status"] == 0


def test_capture_preserves_all_samples_and_waits_between_four_rounds():
    sleeps = []
    def fake_probe(endpoint, index, token, timeout, max_bytes):
        return observation(endpoint, index, not (endpoint[0] == "portal" and index == 2))
    with tempfile.TemporaryDirectory() as directory:
        summary = probe.capture(Path(directory), probe_fn=fake_probe, sleep_fn=sleeps.append)
        journal = [json.loads(line) for line in (Path(directory) / "site_health_samples.jsonl").read_text().splitlines()]
        assert len(journal) == 64
        assert len([row for row in journal if not row["ok"]]) == 1
        assert json.loads((Path(directory) / "site_health.json").read_text()) == summary
        assert json.loads((Path(directory) / "uptime_badge.json").read_text())["color"] == "yellow"
    assert sleeps == [60, 60, 60]
    assert summary["overall"] == "degraded"


def test_interrupted_capture_preserves_preceding_observations_without_green_summary():
    def fake_probe(endpoint, index, token, timeout, max_bytes):
        if index == 2:
            raise RuntimeError("fixture interruption")
        return observation(endpoint, index)
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        (output / "site_health.json").write_text('{"overall":"operational"}')
        (output / "uptime_badge.json").write_text('{"color":"brightgreen"}')
        try:
            probe.capture(output, probe_fn=fake_probe, sleep_fn=lambda _: None)
        except RuntimeError:
            pass
        else:
            raise AssertionError("interrupted capture must propagate failure")
        assert len((output / "site_health_samples.jsonl").read_text().splitlines()) == 16
        assert not (output / "site_health.json").exists()
        assert not (output / "uptime_badge.json").exists()


def test_capture_refuses_zero_interval_or_single_round():
    with tempfile.TemporaryDirectory() as directory:
        for kwargs in ({"rounds": 1}, {"interval": 0}, {"rounds": 7}, {"timeout": 100}):
            try:
                probe.capture(Path(directory), **kwargs)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid sampling bounds were accepted")


def test_all_good_observations_preserve_existing_receipt_counts_and_bound_claims():
    rows = [observation(endpoint, i) for endpoint in probe.ENDPOINTS for i in range(1, 5)]
    summary = probe.summarize(rows, 4, 60, rows[0]["started_utc"])
    assert summary["overall"] == "operational"
    assert summary["healthy_count"] == summary["total_count"] == 16
    assert summary["static_healthy_count"] == summary["static_total_count"] == 14
    assert summary["dynamic_healthy_count"] == summary["dynamic_total_count"] == summary["dynamic_reachable_count"] == 2
    assert summary["observation_window"]["observations_recorded"] == 64
    assert "not continuous uptime" in summary["observation_window"]["claim_boundary"]


def dynamic_row(contract="gateway_health", payload=None, *, raw=None, now=NOW,
                status=200, content_type="application/json", transport_ok=True, origin_ok=True):
    if raw is None:
        current = dict(PUBLIC_FIELDS) if payload is None else payload
        if payload is None and contract == "gateway_health":
            current["generated_utc"] = "2026-10-14T12:00:00Z"
        raw = json.dumps(current).encode()
    return probe.classify(contract, status, content_type, raw,
                          transport_ok=transport_ok, same_origin_ok=origin_ok, now=now)


def test_dynamic_contract_matches_actual_minimal_gateway_payloads():
    spec = importlib.util.spec_from_file_location("health_fixture_operator", ROOT / "code/operator_api_access.py")
    operator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(operator)
    status = dynamic_row("public_status", operator.public_status_payload())
    assert status["ok"] is True
    assert status["freshness"] == "not_provided_by_contract"
    assert status["age_seconds"] is None
    assert status["validation_error"] is None
    health_payload = operator.public_health_payload()
    source_time = datetime.fromisoformat(health_payload["generated_utc"].replace("Z", "+00:00"))
    health = dynamic_row(payload=health_payload, now=source_time)
    assert health["ok"] is True
    assert health["freshness"] == "fresh"
    assert health["age_seconds"] == 0


def test_dynamic_contract_rejects_duplicate_nonfinite_and_non_utf8_json():
    encoded = json.dumps(dict(PUBLIC_FIELDS, generated_utc="2026-10-14T12:00:00Z"))
    invalid = [
        ('{"status":"error",' + encoded[1:]).encode(),
        ('{"extra":{"same":1,"same":2},' + encoded[1:]).encode(),
        encoded.encode("utf-16"),
        b'{"status":"ok",',
        b"\xff",
        b"[" * 2000 + b"0" + b"]" * 2000,
    ]
    for token in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999"):
        invalid.append((encoded[:-1] + ',"extra":' + token + "}").encode())
    for raw in invalid:
        row = dynamic_row(raw=raw)
        assert row["ok"] is False
        assert row["json_ok"] is False
        assert row["validation_error"] == "invalid_json_object"
        assert row["freshness"] == "unknown"
        # A retained failure contains no fetched field names or values.
        assert "same" not in json.dumps(row)
        assert "extra" not in json.dumps(row)


def test_public_status_has_no_health_timestamp_or_private_extra_fields():
    assert dynamic_row("public_status")["ok"] is True
    for payload in (
        dict(PUBLIC_FIELDS, generated_utc="2026-10-14T12:00:00Z"),
        dict(PUBLIC_FIELDS, configuration={"fictional-private": True}),
        dict(PUBLIC_FIELDS, status=True),
        dict(PUBLIC_FIELDS, service=None),
        dict(PUBLIC_FIELDS, access_boundary=["operator_api_v1"]),
        {key: value for key, value in PUBLIC_FIELDS.items() if key != "status"},
    ):
        row = dynamic_row("public_status", payload)
        assert row["ok"] is False
        assert row["json_ok"] is True
        assert row["validation_error"] == "public_schema_mismatch"
        assert row["freshness"] == "not_provided_by_contract"
        assert "fictional-private" not in json.dumps(row)
    for payload in ([], "ok", 1, None):
        raw = json.dumps(payload).encode()
        row = dynamic_row("public_status", raw=raw)
        assert row["ok"] is False
        assert row["json_ok"] is False


def test_health_timestamp_precision_timezone_calendar_and_age_fail_closed():
    cases = (
        ("2026-10-14T12:00:00Z", True, "fresh", 0),
        ("2026-10-14T11:55:00Z", True, "fresh", 300),
        ("2026-10-14T13:00:00+01:00", True, "fresh", 0),
        ("2026-10-14T07:00:00-05:00", True, "fresh", 0),
        ("2026-10-14T11:59:59.999999Z", True, "fresh", 0.000001),
        ("2026-10-14T11:54:59.999999Z", False, "stale", 300.000001),
        ("2026-10-14T12:00:00.000001Z", False, "future", -0.000001),
        ("2099-01-01T00:00:00Z", False, "future", None),
        ("2020-01-01T00:00:00Z", False, "stale", None),
        ("2026-10-14T12:00:00.0000001Z", False, "invalid", None),
        ("2026-10-14T11:59:59.9999999Z", False, "invalid", None),
        ("2026-10-14T12:00:00", False, "invalid", None),
        ("2026-10-14", False, "invalid", None),
        ("2026-02-30T12:00:00Z", False, "invalid", None),
        ("2026-10-14T12:00:60Z", False, "invalid", None),
        ("2026-10-14T12:00:00+00:60", False, "invalid", None),
        ("2026-10-14T12:00:00+24:00", False, "invalid", None),
        ("2026-10-14 12:00:00Z", False, "invalid", None),
        ("not-a-timestamp", False, "invalid", None),
        ("", False, "invalid", None),
        (None, False, "invalid", None),
        (True, False, "invalid", None),
    )
    for timestamp, accepted, freshness, age in cases:
        row = dynamic_row(payload=dict(PUBLIC_FIELDS, generated_utc=timestamp))
        assert row["ok"] is accepted, timestamp
        assert row["freshness"] == freshness, timestamp
        if age is not None:
            assert row["age_seconds"] == age, timestamp
        assert row["validation_error"] == (None if accepted else "health_timestamp_" + freshness), timestamp
    row = dynamic_row(now=NOW.replace(tzinfo=None))
    assert row["ok"] is False
    assert row["validation_error"] == "health_timestamp_invalid_reference_time"


def test_health_requires_the_complete_minimal_schema_without_private_fields():
    valid = dict(PUBLIC_FIELDS, generated_utc="2026-10-14T12:00:00Z")
    for payload in (
        dict(PUBLIC_FIELDS),
        dict(valid, worker_state="fictional-private-state"),
        dict(valid, status=False),
        dict(valid, public_surface={"name": "minimal"}),
    ):
        row = dynamic_row(payload=payload)
        assert row["ok"] is False
        assert row["validation_error"] == "public_schema_mismatch"
        assert "fictional-private-state" not in json.dumps(row)


def test_dynamic_response_requires_exact_status_media_type_origin_and_transport():
    for status, mime, transport, origin, reason in (
        (201, "application/json", True, True, "unexpected_http_status"),
        (502, "application/json", True, True, "unexpected_http_status"),
        (200, "text/plain", True, True, "unexpected_media_type"),
        (200, "application/problem+json", True, True, "unexpected_media_type"),
        (200, "application/jsonp", True, True, "unexpected_media_type"),
        (200, "", True, True, "unexpected_media_type"),
        (200, "application/json", False, True, "transport_failure"),
        (200, "application/json", True, False, "unexpected_origin"),
    ):
        row = dynamic_row(status=status, content_type=mime, transport_ok=transport, origin_ok=origin)
        assert row["ok"] is False
        assert row["status"] == status
        assert row["validation_error"] == reason
    assert dynamic_row(content_type="Application/JSON; charset=utf-8")["ok"] is True


def test_invalid_gateway_observation_cannot_be_hidden_by_later_valid_rounds():
    endpoint = probe.ENDPOINTS[-1]
    rows = []
    for index in range(1, 5):
        row = dynamic_row(payload=dict(PUBLIC_FIELDS, generated_utc=
                          "2026-10-14T11:54:59Z" if index == 2 else "2026-10-14T12:00:00Z"))
        row.update({"name": endpoint[0], "url": endpoint[1], "sample_index": index,
                    "started_utc": f"2026-10-14T12:0{index}:00Z", "completed_utc": "2026-10-14T12:04:01Z"})
        rows.append(row)
    summary = probe.summarize(rows, 4, 60, rows[0]["started_utc"], endpoints=(endpoint,))
    assert summary["overall"] != "operational"
    retained = summary["endpoints"]["gateway_health"]
    assert retained["validation_error"] == "health_timestamp_stale"
    assert retained["successful_count"] == 3
    assert retained["flapping_observed"] is True
    assert summary["observation_window"]["failed_observations"] == 1


def test_mocked_http_probe_retains_strict_failure_and_does_not_persist_payload():
    marker = "fictional-private-field-value"
    payload = dict(PUBLIC_FIELDS, configuration=marker)
    raw = json.dumps(payload).encode()
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command)
        Path(command[command.index("--output") + 1]).write_bytes(raw)
        Path(command[command.index("--dump-header") + 1]).write_text(
            "HTTP/1.1 200 OK\nSet-Cookie: fictional-cookie\nAge: 12\n"
        )
        return subprocess.CompletedProcess(command, 0, f"200\napplication/json\n{command[-1]}\n0.01\n192.0.2.1", "")
    with patch.object(probe.subprocess, "run", side_effect=fake_run):
        row = probe.probe(probe.ENDPOINTS[-2], 1, "fixture")
    assert row["status"] == 200
    assert row["http_ok"] is True
    assert row["ok"] is False
    assert row["validation_error"] == "public_schema_mismatch"
    assert row["response_bytes"] == len(raw)
    assert len(row["response_sha256"]) == 64
    assert row["response_headers"] == {"age": "12"}
    assert marker not in json.dumps(row)
    assert "fictional-cookie" not in json.dumps(row)
    assert len(calls) == 1
    assert "--retry" not in calls[0]
