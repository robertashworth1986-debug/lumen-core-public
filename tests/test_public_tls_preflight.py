from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "VERIFY_PUBLIC_TLS_RECEIPT.py"
FIXTURE = ROOT / "tests" / "fixtures" / "public_tls_leaf.pem"
SPEC = importlib.util.spec_from_file_location("public_tls_receipt", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

EXPECTED_HOSTS = (
    "lumen-core.invalid",
    "www.lumen-core.invalid",
    "app.lumen-core.invalid",
    "research.lumen-core.invalid",
)


def decoded_fixture():
    return MODULE.decode_pem_certificate(FIXTURE)


def validity_window():
    decoded, _ = decoded_fixture()
    return (
        MODULE.parse_certificate_time(decoded["notBefore"]),
        MODULE.parse_certificate_time(decoded["notAfter"]),
    )


def build_at(checked_at, expected_hosts=EXPECTED_HOSTS, chain_trust_ok=True):
    decoded, der_bytes = decoded_fixture()
    return MODULE.build_receipt(
        decoded=decoded,
        der_bytes=der_bytes,
        checked_at=checked_at,
        connect_host="lumen-core.invalid",
        expected_hosts=expected_hosts,
        warning_days=30,
        chain_trust_ok=chain_trust_ok,
    )


def test_local_pem_fixture_records_identity_sans_and_validity_window() -> None:
    not_before, not_after = validity_window()
    receipt = build_at(not_before + timedelta(days=120))

    assert receipt["schema"] == "lumencore.public_tls_preflight.v1"
    assert receipt["state"] == "operational"
    assert receipt["ok"] is True
    assert receipt["certificate_valid_now"] is True
    assert receipt["chain_trust_evaluated"] is True
    assert receipt["chain_trust_ok"] is True
    assert receipt["hostname_coverage_ok"] is True
    assert receipt["missing_expected_hosts"] == []
    assert receipt["covered_expected_hosts"] == sorted(EXPECTED_HOSTS)
    assert receipt["certificate"]["subject_common_name"] == "lumen-core.invalid"
    assert receipt["certificate"]["issuer_common_name"] == "lumen-core.invalid"
    assert receipt["certificate"]["not_before_utc"] == MODULE.utc_text(not_before)
    assert receipt["certificate"]["not_after_utc"] == MODULE.utc_text(not_after)
    assert set(receipt["certificate"]["dns_names"]) == set(EXPECTED_HOSTS)
    assert len(receipt["certificate"]["sha256_fingerprint"]) == 64


def test_warning_window_fails_closed_at_thirty_days_remaining() -> None:
    _, not_after = validity_window()
    receipt = build_at(not_after - timedelta(days=30))

    assert receipt["state"] == "degraded"
    assert receipt["verdict"] == "PUBLIC_TLS_DEGRADED_RENEWAL_WINDOW"
    assert receipt["ok"] is False
    assert receipt["certificate_valid_now"] is True
    assert receipt["renewal_window_entered"] is True
    assert receipt["remaining_days"] == 30
    assert receipt["reasons"] == ["certificate_inside_warning_window"]


def test_one_second_outside_warning_window_remains_operational() -> None:
    _, not_after = validity_window()
    receipt = build_at(not_after - timedelta(days=30, seconds=1))

    assert receipt["state"] == "operational"
    assert receipt["ok"] is True
    assert receipt["renewal_window_entered"] is False
    assert receipt["remaining_days"] == 30


def test_expired_certificate_is_an_outage() -> None:
    _, not_after = validity_window()
    receipt = build_at(not_after)

    assert receipt["state"] == "outage"
    assert receipt["ok"] is False
    assert receipt["certificate_valid_now"] is False
    assert receipt["remaining_seconds"] == 0
    assert receipt["reasons"] == ["certificate_expired"]


def test_not_yet_valid_certificate_is_an_outage() -> None:
    not_before, _ = validity_window()
    receipt = build_at(not_before - timedelta(seconds=1))

    assert receipt["state"] == "outage"
    assert receipt["certificate_valid_now"] is False
    assert receipt["reasons"] == ["certificate_not_yet_valid"]


def test_missing_expected_san_is_an_outage() -> None:
    not_before, _ = validity_window()
    receipt = build_at(
        not_before + timedelta(days=120),
        expected_hosts=EXPECTED_HOSTS + ("missing.lumen-core.invalid",),
    )

    assert receipt["state"] == "outage"
    assert receipt["hostname_coverage_ok"] is False
    assert receipt["missing_expected_hosts"] == ["missing.lumen-core.invalid"]
    assert receipt["reasons"] == ["expected_hostname_missing_from_san"]


def test_failed_chain_validation_is_an_outage_with_identity_preserved() -> None:
    not_before, _ = validity_window()
    receipt = build_at(
        not_before + timedelta(days=120),
        chain_trust_ok=False,
    )

    assert receipt["state"] == "outage"
    assert receipt["chain_trust_evaluated"] is True
    assert receipt["chain_trust_ok"] is False
    assert receipt["certificate"]["decoded"] is True
    assert receipt["reasons"] == ["certificate_chain_validation_failed"]


def test_probe_acquisition_failure_preserves_fail_closed_receipt() -> None:
    not_before, _ = validity_window()
    receipt = MODULE.build_probe_failure_receipt(
        checked_at=not_before + timedelta(days=120),
        connect_host="lumen-core.invalid",
        expected_hosts=EXPECTED_HOSTS,
        warning_days=30,
        probe_error="certificate_acquisition_failed",
    )

    assert receipt["state"] == "outage"
    assert receipt["ok"] is False
    assert receipt["certificate"]["decoded"] is False
    assert receipt["chain_trust_evaluated"] is False
    assert receipt["chain_trust_ok"] is False
    assert receipt["remaining_days"] is None
    assert receipt["missing_expected_hosts"] == sorted(EXPECTED_HOSTS)
    assert receipt["reasons"] == ["certificate_acquisition_failed"]


def test_receipt_serialization_is_deterministic(tmp_path: Path | None = None) -> None:
    # This test is callable both by pytest and the dependency-free workflow harness.
    import tempfile

    not_before, _ = validity_window()
    receipt = build_at(not_before + timedelta(days=120))
    with tempfile.TemporaryDirectory() as directory:
        first = Path(directory) / "first.json"
        second = Path(directory) / "second.json"
        MODULE.write_receipt(first, receipt)
        MODULE.write_receipt(second, receipt)
        assert first.read_bytes() == second.read_bytes()
        assert json.loads(first.read_text(encoding="utf-8")) == receipt


def test_cli_builds_receipt_from_local_fixture_without_network() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "tls_receipt.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(MODULE_PATH),
                "--certificate",
                str(FIXTURE),
                "--checked-at",
                "2026-06-01T00:00:00Z",
                "--connect-host",
                "lumen-core.invalid",
                "--hostname",
                "lumen-core.invalid",
                "--hostname",
                "www.lumen-core.invalid",
                "--hostname",
                "app.lumen-core.invalid",
                "--hostname",
                "research.lumen-core.invalid",
                "--warning-days",
                "30",
                "--chain-trust-status",
                "passed",
                "--output",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        receipt = json.loads(output.read_text(encoding="utf-8"))
        summary = json.loads(completed.stdout)
        assert receipt["state"] == "operational"
        assert receipt["chain_trust_ok"] is True
        assert summary["verdict"] == "PUBLIC_TLS_OPERATIONAL"


def test_health_workflow_remains_read_only_and_has_no_renewal_authority() -> None:
    workflow = (ROOT / ".github" / "workflows" / "health-probe.yml").read_text(
        encoding="utf-8"
    )

    assert "VERIFY_PUBLIC_TLS_RECEIPT.py" in workflow
    assert "TLS_WARNING_DAYS: '30'" in workflow
    assert "tls_receipt.json" in workflow
    assert "lumen-core.ai" in workflow
    assert "www.lumen-core.ai" in workflow
    assert "app.lumen-core.ai" in workflow
    assert "research.lumen-core.ai" in workflow
    assert "for tls_host in \\" in workflow
    assert '-verify_hostname "$tls_host" -verify_return_error' in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "persist-credentials: false" in workflow
    for forbidden in (
        "certbot",
        "contents: write",
        "git push ",
        "ssh ",
        "scp ",
        "wrangler deploy",
        "cloudflare api",
        "--apply",
    ):
        assert forbidden not in workflow.lower()
