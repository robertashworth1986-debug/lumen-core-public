from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "ops" / "AUDIT_EIA_PROSPECTIVE_SOURCE_TIMING.py"


def load_module():
    spec = importlib.util.spec_from_file_location("eia_source_timing_audit", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def row(period: str, value: float, kind: str = "DF"):
    return {
        "period": period,
        "respondent": "ERCO",
        "type": kind,
        "value": value,
    }


def test_hour_ending_period_belongs_to_interval_start_local_day():
    module = load_module()
    assert (
        module.local_day_for_hour_ending("2026-07-15T05", "America/Chicago")
        == "2026-07-14"
    )
    assert (
        module.local_day_for_hour_ending("2026-07-15T06", "America/Chicago")
        == "2026-07-15"
    )


def test_expected_hours_are_dst_safe():
    module = load_module()
    assert len(module.expected_hour_endings("2026-03-08", "America/Chicago")) == 23
    assert len(module.expected_hour_endings("2026-07-14", "America/Chicago")) == 24
    assert len(module.expected_hour_endings("2026-11-01", "America/Chicago")) == 25


def test_aggregate_accepts_only_complete_local_days():
    module = load_module()
    periods = module.expected_hour_endings("2026-07-14", "America/Chicago")
    rows = [row(period, float(index + 1)) for index, period in enumerate(periods)]
    aggregates, diagnostics = module.aggregate_complete_local_days(
        rows, "ERCO", "America/Chicago"
    )
    assert aggregates[("2026-07-14", "DF")] == sum(range(1, 25))
    assert diagnostics[("2026-07-14", "DF")]["complete"] is True

    incomplete, incomplete_diagnostics = module.aggregate_complete_local_days(
        rows[:-1], "ERCO", "America/Chicago"
    )
    assert ("2026-07-14", "DF") not in incomplete
    assert incomplete_diagnostics[("2026-07-14", "DF")]["missing_periods"] == [
        periods[-1]
    ]


def test_canonical_receipt_never_needs_a_credential():
    module = load_module()
    observed = datetime(2026, 7, 15, 0, 0, tzinfo=timezone.utc)
    receipt = {
        "generated_utc": observed.isoformat(),
        "credential_serialized": False,
        "response_body_sha256": "a" * 64,
    }
    digest = module.canonical_sha256(receipt)
    assert len(digest) == 64
    assert "api_key" not in receipt
