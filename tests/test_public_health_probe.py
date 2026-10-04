from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("public_health_probe", ROOT / "code/ops/probe_public_health.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def observation(endpoint, index, ok=True):
    name, url, contract = endpoint
    body = probe.MARKERS.get(contract, "").encode()
    content_type = "text/html"
    if contract not in probe.MARKERS:
        content_type = "application/json"
        body = json.dumps({"status": "ok", "service": "luma-experience-gateway",
                           "access_boundary": "operator_api_v1", "public_surface": "minimal",
                           "generated_utc": "2026-10-03T23:00:00Z"}).encode()
    row = probe.classify(contract, 200 if ok else 502, content_type, body,
                         transport_ok=True, same_origin_ok=True)
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
               "generated_utc": "2026-10-03T23:00:00Z"}
    for replacement in ({}, {"status": "degraded"}, {"service": "other"}, {"generated_utc": ""}):
        current = dict(payload, **replacement)
        row = probe.classify("gateway_health", 200, "application/json", json.dumps(current).encode(),
                             transport_ok=True, same_origin_ok=True)
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
