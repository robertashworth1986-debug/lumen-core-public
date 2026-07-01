from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LIVE_SOURCE_MEASUREMENT_MAXIMIZER.py"


def load_module():
    spec = importlib.util.spec_from_file_location("live_source_measurement_maximizer", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_sanitize_redacts_secret_values(monkeypatch) -> None:
    module = load_module()
    monkeypatch.setenv("FINNHUB_API_KEY", "super-secret-token")

    text = module.sanitize_text("url=https://x.test/?token=super-secret-token&email=a@b.com", ["FINNHUB_API_KEY"])

    assert "super-secret-token" not in text
    assert "a@b.com" not in text
    assert "[REDACTED]" in text


def test_merge_registry_preserves_existing_and_replaces_current_source() -> None:
    module = load_module()
    existing = {
        "rows": [
            {"source": "OLD_ONLY", "enabled": True, "measured": True, "rows": 1},
            {"source": "FRED", "enabled": True, "measured": False, "rows": 0},
        ]
    }
    merged = module.merge_registry(
        existing,
        [
            {
                "source": "FRED",
                "enabled": True,
                "measured": True,
                "rows": 4,
                "translated_value": {"hour": 1.0, "year": 8760.0},
            }
        ],
    )

    rows = {row["source"]: row for row in merged["rows"]}
    assert rows["OLD_ONLY"]["rows"] == 1
    assert rows["FRED"]["measured"] is True
    assert rows["FRED"]["rows"] == 4


def test_source_truth_contains_snapshot_hash_and_no_secret() -> None:
    module = load_module()
    registry = {
        "rows": [
            {
                "source": "FRED",
                "sector": "rates",
                "status": "MEASURED",
                "rows": 2,
                "enabled": True,
                "measured": True,
                "translated_value": {"hour": 12.0},
                "last_probe_utc": "2026-06-22T00:00:00+00:00",
                "probe_note": "ok",
                "snapshot_json": "data/live_measured/fred/fred_latest.json",
                "snapshot_sha256": "abc123",
            }
        ]
    }

    truth = module.source_truth_from_registry(registry)
    dumped = json.dumps(truth)

    assert truth["rows"][0]["source"] == "FRED"
    assert truth["rows"][0]["snapshot_sha256"] == "abc123"
    assert "secret" not in dumped.lower()


def test_build_summary_counts_measured_sources_and_value_surface() -> None:
    module = load_module()
    rows = [
        {"source": "A", "sector": "rates", "enabled": True, "measured": True, "rows": 3, "translated_value": {"year": 10.0}},
        {"source": "B", "sector": "energy", "enabled": True, "measured": False, "rows": 0, "translated_value": {"year": 0.0}},
        {"source": "C", "sector": "market_data", "enabled": False, "measured": False, "rows": 0, "translated_value": {"year": 0.0}},
    ]

    summary = module.build_summary(rows)

    assert summary["enabled_sources"] == 2
    assert summary["measured_sources"] == 1
    assert summary["failed_or_thin_sources"] == 1
    assert summary["total_measured_rows"] == 3
    assert summary["estimated_annual_value_surface_usd"] == 10.0
    assert "realized savings" in summary["claim_boundary"]


def test_airnow_provider_is_registered_as_separate_air_quality_lane() -> None:
    module = load_module()
    providers = {row["source"]: row for row in module.PROVIDERS}

    assert "AIRNOW" in providers
    assert providers["AIRNOW"]["sector"] == "air_quality"
    assert providers["AIRNOW"]["env_names"] == ["AIRNOW_API_KEY"]
    assert providers["AIRNOW"]["collector"].__name__ == "rows_from_airnow"
