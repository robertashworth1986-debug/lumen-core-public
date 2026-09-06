#!/usr/bin/env python3
"""Build a bounded, read-only receipt for one public TLS leaf certificate.

The workflow that calls this verifier is responsible only for capturing the
public leaf certificate. This module performs no networking, renewal, DNS,
deployment, or server mutation. A warning-window certificate is deliberately
not considered healthy: the scheduled job must fail closed while there is
still time for a separately approved repair.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "lumencore.public_tls_preflight.v1"
DEFAULT_WARNING_DAYS = 30
MAX_CERTIFICATE_BYTES = 65_536
UTC_TEXT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
WARNING_THRESHOLD_BASIS = (
    "Thirty days preserves thirty daily observation windows before expiry "
    "and leaves one third of a 90-day certificate lifetime for a separately "
    "approved renewal or recovery."
)


class TlsReceiptError(ValueError):
    """Raised when local receipt inputs are malformed or unsafe."""


def parse_checked_utc(value: str) -> datetime:
    if not UTC_TEXT_RE.fullmatch(value):
        raise TlsReceiptError("checked_at must use YYYY-MM-DDTHH:MM:SSZ")
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return parsed.replace(tzinfo=timezone.utc)


def utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        raise TlsReceiptError("certificate time must be timezone-aware")
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_certificate_time(value: str) -> datetime:
    try:
        timestamp = ssl.cert_time_to_seconds(value)
    except (TypeError, ValueError) as exc:
        raise TlsReceiptError("certificate validity time is malformed") from exc
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def normalize_hostname(value: str) -> str:
    normalized = value.strip().rstrip(".").lower()
    if not normalized or any(char.isspace() for char in normalized):
        raise TlsReceiptError("expected hostname is malformed")
    try:
        return normalized.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise TlsReceiptError("expected hostname is malformed") from exc


def dns_name_matches(pattern: str, hostname: str) -> bool:
    pattern_normalized = normalize_hostname(pattern)
    host_normalized = normalize_hostname(hostname)
    if not pattern_normalized.startswith("*."):
        return pattern_normalized == host_normalized
    if pattern_normalized.count("*") != 1:
        return False
    suffix = pattern_normalized[1:]
    return host_normalized.endswith(suffix) and (
        host_normalized.count(".") == pattern_normalized.count(".")
    )


def name_to_mapping(value: Iterable[Iterable[Sequence[str]]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for relative_name in value:
        for item in relative_name:
            if len(item) != 2:
                continue
            key, entry_value = str(item[0]), str(item[1])
            result.setdefault(key, []).append(entry_value)
    return result


def first_name_value(name: Mapping[str, list[str]], key: str) -> str | None:
    values = name.get(key, [])
    return values[0] if values else None


def empty_certificate_identity() -> dict[str, Any]:
    return {
        "decoded": False,
        "version": None,
        "serial_number": None,
        "sha256_fingerprint": None,
        "subject": {},
        "subject_common_name": None,
        "issuer": {},
        "issuer_common_name": None,
        "subject_alt_names": [],
        "dns_names": [],
        "not_before_utc": None,
        "not_after_utc": None,
    }


def decode_pem_certificate(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file() or path.is_symlink():
        raise TlsReceiptError("certificate input must be a regular file")
    size = path.stat().st_size
    if size <= 0 or size > MAX_CERTIFICATE_BYTES:
        raise TlsReceiptError("certificate input size is outside the allowed bound")
    pem = path.read_text(encoding="ascii")
    try:
        der = ssl.PEM_cert_to_DER_cert(pem)
    except ValueError as exc:
        raise TlsReceiptError("certificate input is not one PEM certificate") from exc
    decoder = getattr(ssl._ssl, "_test_decode_cert", None)
    if not callable(decoder):
        raise TlsReceiptError("local Python runtime cannot decode a PEM certificate")
    try:
        decoded = decoder(str(path))
    except (OSError, ssl.SSLError) as exc:
        raise TlsReceiptError("certificate input could not be decoded") from exc
    if not isinstance(decoded, dict):
        raise TlsReceiptError("certificate decoder returned an invalid result")
    return decoded, der


def certificate_identity(
    decoded: Mapping[str, Any],
    der_bytes: bytes,
) -> tuple[dict[str, Any], datetime, datetime]:
    subject = name_to_mapping(decoded.get("subject", ()))
    issuer = name_to_mapping(decoded.get("issuer", ()))
    not_before = parse_certificate_time(str(decoded.get("notBefore", "")))
    not_after = parse_certificate_time(str(decoded.get("notAfter", "")))
    if not_after <= not_before:
        raise TlsReceiptError("certificate validity window is not increasing")

    subject_alt_names: list[dict[str, str]] = []
    dns_names: set[str] = set()
    for item in decoded.get("subjectAltName", ()):
        if len(item) != 2:
            continue
        entry_type, entry_value = str(item[0]), str(item[1])
        subject_alt_names.append({"type": entry_type, "value": entry_value})
        if entry_type.upper() == "DNS":
            dns_names.add(normalize_hostname(entry_value))

    identity = {
        "decoded": True,
        "version": int(decoded.get("version", 0)),
        "serial_number": str(decoded.get("serialNumber", "")),
        "sha256_fingerprint": hashlib.sha256(der_bytes).hexdigest(),
        "subject": subject,
        "subject_common_name": first_name_value(subject, "commonName"),
        "issuer": issuer,
        "issuer_common_name": first_name_value(issuer, "commonName"),
        "subject_alt_names": subject_alt_names,
        "dns_names": sorted(dns_names),
        "not_before_utc": utc_text(not_before),
        "not_after_utc": utc_text(not_after),
    }
    return identity, not_before, not_after


def target_record(connect_host: str, expected_hosts: Iterable[str]) -> dict[str, Any]:
    normalized_hosts = sorted({normalize_hostname(host) for host in expected_hosts})
    if not normalized_hosts:
        raise TlsReceiptError("at least one expected hostname is required")
    return {
        "connect_host": normalize_hostname(connect_host),
        "port": 443,
        "sni": normalize_hostname(connect_host),
        "expected_hosts": normalized_hosts,
    }


def build_receipt(
    *,
    decoded: Mapping[str, Any],
    der_bytes: bytes,
    checked_at: datetime,
    connect_host: str,
    expected_hosts: Iterable[str],
    warning_days: int = DEFAULT_WARNING_DAYS,
    chain_trust_ok: bool = True,
) -> dict[str, Any]:
    if warning_days < 1 or warning_days > 89:
        raise TlsReceiptError("warning_days must be between 1 and 89")
    target = target_record(connect_host, expected_hosts)
    identity, not_before, not_after = certificate_identity(decoded, der_bytes)
    checked_at = checked_at.astimezone(timezone.utc)
    remaining_seconds = math.floor((not_after - checked_at).total_seconds())
    remaining_days = math.floor(remaining_seconds / 86_400)
    warning_seconds = warning_days * 86_400

    dns_names = identity["dns_names"]
    covered = sorted(
        host
        for host in target["expected_hosts"]
        if any(dns_name_matches(pattern, host) for pattern in dns_names)
    )
    missing = sorted(set(target["expected_hosts"]) - set(covered))
    currently_valid = not_before <= checked_at < not_after
    hostname_coverage_ok = not missing
    renewal_window_entered = currently_valid and remaining_seconds <= warning_seconds

    reasons: list[str] = []
    state = "operational"
    verdict = "PUBLIC_TLS_OPERATIONAL"
    if checked_at < not_before:
        reasons.append("certificate_not_yet_valid")
    if checked_at >= not_after:
        reasons.append("certificate_expired")
    if not chain_trust_ok:
        reasons.append("certificate_chain_validation_failed")
    if missing:
        reasons.append("expected_hostname_missing_from_san")
    if reasons:
        state = "outage"
        verdict = "PUBLIC_TLS_OUTAGE"
    elif renewal_window_entered:
        reasons.append("certificate_inside_warning_window")
        state = "degraded"
        verdict = "PUBLIC_TLS_DEGRADED_RENEWAL_WINDOW"

    return {
        "schema": SCHEMA,
        "checked_utc": utc_text(checked_at),
        "source": "public_tls_handshake_leaf",
        "target": target,
        "warning_threshold_days": warning_days,
        "warning_threshold_basis": WARNING_THRESHOLD_BASIS,
        "state": state,
        "verdict": verdict,
        "ok": state == "operational",
        "chain_trust_evaluated": True,
        "chain_trust_ok": chain_trust_ok,
        "certificate_valid_now": currently_valid,
        "hostname_coverage_ok": hostname_coverage_ok,
        "renewal_window_entered": renewal_window_entered,
        "remaining_seconds": remaining_seconds,
        "remaining_days": remaining_days,
        "covered_expected_hosts": covered,
        "missing_expected_hosts": missing,
        "reasons": reasons,
        "certificate": identity,
        "action_boundary": (
            "Read-only evidence only. This receipt cannot renew a certificate, "
            "change DNS, access a VPS, deploy code, or authorize production mutation."
        ),
    }


def build_probe_failure_receipt(
    *,
    checked_at: datetime,
    connect_host: str,
    expected_hosts: Iterable[str],
    warning_days: int,
    probe_error: str,
) -> dict[str, Any]:
    if warning_days < 1 or warning_days > 89:
        raise TlsReceiptError("warning_days must be between 1 and 89")
    if not re.fullmatch(r"[a-z0-9_:-]{1,80}", probe_error):
        raise TlsReceiptError("probe_error is malformed")
    target = target_record(connect_host, expected_hosts)
    return {
        "schema": SCHEMA,
        "checked_utc": utc_text(checked_at.astimezone(timezone.utc)),
        "source": "public_tls_handshake_leaf",
        "target": target,
        "warning_threshold_days": warning_days,
        "warning_threshold_basis": WARNING_THRESHOLD_BASIS,
        "state": "outage",
        "verdict": "PUBLIC_TLS_OUTAGE",
        "ok": False,
        "chain_trust_evaluated": False,
        "chain_trust_ok": False,
        "certificate_valid_now": False,
        "hostname_coverage_ok": False,
        "renewal_window_entered": False,
        "remaining_seconds": None,
        "remaining_days": None,
        "covered_expected_hosts": [],
        "missing_expected_hosts": target["expected_hosts"],
        "reasons": [probe_error],
        "certificate": empty_certificate_identity(),
        "action_boundary": (
            "Read-only evidence only. This receipt cannot renew a certificate, "
            "change DNS, access a VPS, deploy code, or authorize production mutation."
        ),
    }


def write_receipt(path: Path, receipt: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a read-only public TLS certificate receipt."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--certificate", type=Path)
    source.add_argument("--probe-error")
    parser.add_argument("--checked-at", required=True)
    parser.add_argument("--connect-host", required=True)
    parser.add_argument("--hostname", action="append", required=True)
    parser.add_argument("--warning-days", type=int, default=DEFAULT_WARNING_DAYS)
    parser.add_argument(
        "--chain-trust-status",
        choices=("passed", "failed", "not_run"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checked_at = parse_checked_utc(args.checked_at)
    if args.probe_error:
        receipt = build_probe_failure_receipt(
            checked_at=checked_at,
            connect_host=args.connect_host,
            expected_hosts=args.hostname,
            warning_days=args.warning_days,
            probe_error=args.probe_error,
        )
    else:
        if args.chain_trust_status == "not_run":
            raise TlsReceiptError(
                "chain trust must be evaluated when a certificate was captured"
            )
        try:
            decoded, der_bytes = decode_pem_certificate(args.certificate)
            receipt = build_receipt(
                decoded=decoded,
                der_bytes=der_bytes,
                checked_at=checked_at,
                connect_host=args.connect_host,
                expected_hosts=args.hostname,
                warning_days=args.warning_days,
                chain_trust_ok=args.chain_trust_status == "passed",
            )
        except TlsReceiptError:
            receipt = build_probe_failure_receipt(
                checked_at=checked_at,
                connect_host=args.connect_host,
                expected_hosts=args.hostname,
                warning_days=args.warning_days,
                probe_error="certificate_decode_failed",
            )
    write_receipt(args.output, receipt)
    print(
        json.dumps(
            {
                "state": receipt["state"],
                "verdict": receipt["verdict"],
                "remaining_days": receipt["remaining_days"],
                "missing_expected_hosts": receipt["missing_expected_hosts"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
