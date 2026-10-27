import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("mime_services", Path(__file__).resolve().parents[1] / "code/ops/VERIFY_PUBLIC_MIME_SERVICE_CONTRACTS.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


@pytest.mark.parametrize("body", [b"", b"[]", b"null", b'{"status":"ok","status":"bad"}', b'{"a":NaN}'])
def test_invalid_health_json_never_passes(body):
    assert not gate.evaluate(gate.SPECS[2], 200, "application/json", "", body)["passed"]


def test_wrong_subdomain_redirect_not_masked_by_html_or_http_success():
    assert not gate.evaluate(gate.SPECS[3], 302, "text/html", gate.DOMAIN + "/", b"")["passed"]
    assert not gate.evaluate(gate.SPECS[3], 200, "text/html", gate.DOMAIN + "/proof_to_pilot.html", b"")["passed"]
    assert gate.evaluate(gate.SPECS[3], 302, "text/html", gate.DOMAIN + "/proof_to_pilot.html", b"")["passed"]


def test_correct_status_does_not_override_bad_mime_or_incomplete_subset():
    spec = gate.SPECS[1]
    assert not gate.evaluate(spec, 200, "application/octet-stream", "", b'{"status":"ok","platform":"nginx"}')["passed"]
    assert not gate.evaluate(spec, 200, "application/json", "", b'{"status":"ok"}')["passed"]
    assert gate.evaluate(spec, 200, "application/json; charset=utf-8", "", b'{"status":"ok","platform":"nginx"}')["passed"]


def test_oversized_body_fails_even_with_successful_status():
    assert not gate.evaluate(gate.SPECS[0], 200, "text/html", "", b"x" * 262145)["passed"]


def test_transport_timeout_is_failed_observation(monkeypatch):
    def timeout(*args, **kwargs):
        raise gate.subprocess.TimeoutExpired("curl", 15)
    monkeypatch.setattr(gate.subprocess, "run", timeout)
    row = gate.probe(gate.SPECS[0])
    assert row["passed"] is False
    assert row["error"] == "BOUNDED_TRANSPORT_OR_RESPONSE_FAILURE"
