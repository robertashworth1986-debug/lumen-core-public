from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    # Import only defines collector functions/constants. Tests never call main,
    # load credentials, fetch providers or write collection summaries.
    sys.path.insert(0, str(ROOT / "code"))
    try:
        spec = importlib.util.spec_from_file_location(
            "canonical_gov_collector_test", ROOT / "code/CANONICAL_GOV_DATA_COLLECTOR.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def test_archived_registry_cannot_mask_current_failure_or_add_live_sources(tmp_path, monkeypatch):
    module = load_module()
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({
        "generated_utc": "2026-06-01T00:00:00Z",
        "rows": [
            {"source": "EIA", "rows": 1000, "probe_ok": True, "measured": True,
             "last_probe_utc": "2026-06-01T00:00:00Z"},
            {"source": "NREL", "rows": 100, "probe_ok": True, "measured": True},
        ],
    }))
    monkeypatch.setattr(module, "REGISTRY_PATH", registry)
    context = module.load_registry_gov_rows()
    current = {"source": "EIA", "ok": False, "rows": 0, "error": "current timeout"}
    result = module.build_collection_summary([current], context)

    assert result["sources_total"] == 1
    assert result["sources_ok"] == 0
    assert result["rows_total"] == 0
    assert result["checks"][0]["error"] == "current timeout"
    assert result["checks"][0]["ok"] is False
    assert len(result["historical_registry_context"]) == 2
    assert all(row["ok"] is False for row in context)
    assert context[0]["reported_rows"] == 1000
    assert context[0]["last_probe_utc"] == "2026-06-01T00:00:00Z"
    assert current == {"source": "EIA", "ok": False, "rows": 0, "error": "current timeout"}


@pytest.mark.parametrize("count", [0, -1, True, None, "10", 1.5])
def test_http_success_without_valid_positive_count_is_not_collection_success(count):
    module = load_module()
    result = module.build_collection_summary([{"source": "EIA", "ok": True, "rows": count}], [])
    assert result["checks"][0]["transport_ok"] is True
    assert result["checks"][0]["ok"] is False
    assert result["sources_ok"] == 0
    assert result["rows_total"] == 0


def test_metadata_and_content_counts_do_not_become_measured_data_rows():
    module = load_module()
    result = module.build_collection_summary([
        {"source": "NOAA", "ok": True, "rows": 10},
        {"source": "EPA_AQS", "ok": True, "rows": 50},
        {"source": "BEA", "ok": True, "rows": 20},
        {"source": "NASA", "ok": True, "rows": 1},
        {"source": "NREL", "ok": True, "rows": 3},
        {"source": "EIA", "ok": True, "rows": 500},
    ], [])
    assert result["sources_ok"] == 6
    assert result["rows_total"] == 500
    assert result["response_items_total"] == 584
    assert result["dataset_review_ready"] is False
    assert all(row["dataset_review_ready"] is False for row in result["checks"])


def test_success_requires_explicit_boolean_and_keeps_provider_failure():
    module = load_module()
    result = module.build_collection_summary([
        {"source": "EIA", "ok": "false", "rows": 500},
        {"source": "FRED", "ok": False, "rows": 240, "error": "partial response"},
    ], [])
    assert result["sources_ok"] == 0
    assert result["rows_total"] == 0
    assert result["response_items_total"] == 0
    assert result["checks"][1]["error"] == "partial response"


def test_success_retains_snapshot_reference_and_redacts_query_credentials():
    module = load_module()
    result = module.build_collection_summary([
        {"source": "EIA", "ok": True, "rows": 500, "snapshot": "private/eia.json",
         "url": "https://example.test/data?api_key=secret&frequency=hourly"},
    ], [])
    assert result["sources_ok"] == 1
    assert result["checks"][0]["snapshot"] == "private/eia.json"
    assert "secret" not in result["checks"][0]["url"]
    assert "frequency=hourly" in result["checks"][0]["url"]


@pytest.mark.parametrize("assignment", [
    "api_key=private-value&frequency=hourly",
    "API_KEY=private-value",
    "ApiKey=private-value",
    "email=private-value&key=another-secret",
    '"registrationkey": "private-value"',
    "token='private-value with whitespace'",
])
def test_error_redaction_removes_the_whole_credential_value(assignment):
    module = load_module()
    result = module.build_collection_summary([
        {"source": "EIA", "ok": False, "rows": 0,
         "error": f"request failed: {assignment}"},
    ], [])
    error = result["checks"][0]["error"]
    assert "private-value" not in error
    assert "another-secret" not in error
    assert "with whitespace" not in error
    assert "REDACTED" in error
    assert result["checks"][0]["ok"] is False


def test_malformed_url_never_falls_back_to_unredacted_input():
    module = load_module()
    assert module.redact_url("https://[invalid?api_key=private-value") == "[invalid URL withheld]"


def test_import_does_not_fetch_read_credentials_or_write_files(monkeypatch, tmp_path):
    import urllib.request

    monkeypatch.setenv("LUMA_STACK_ROOT", str(tmp_path))
    def forbidden(*args, **kwargs):
        raise AssertionError("import performed I/O")
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    module = load_module()
    assert module.ROOT == tmp_path
    assert list(tmp_path.iterdir()) == []
