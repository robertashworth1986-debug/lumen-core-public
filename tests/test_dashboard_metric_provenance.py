"""Offline regressions for the existing local dashboard's evidence labels."""

import importlib.util
import json
import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def dashboard(tmp_path, monkeypatch):
    stack = tmp_path / "stack"
    pages = tmp_path / "pages"
    stack.mkdir()
    pages.mkdir()
    monkeypatch.setenv("LUMA_STACK_ROOT", str(stack))
    monkeypatch.setenv("LUMA_DASHBOARD_DIR", str(pages))
    monkeypatch.syspath_prepend(str(ROOT / "code"))
    spec = importlib.util.spec_from_file_location(
        "dashboard_provenance_test", ROOT / "code/dashboard_unified_refresh.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def put(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.mark.parametrize("runtime", [{}, {"live": False}, {"live": "true"}, {"live": True}])
def test_configuration_and_historical_ledger_are_not_current_liveness(dashboard, runtime):
    put(dashboard.PAPER_RUNTIME_CANDIDATES[0], runtime)
    dashboard.PAPER_LEDGER_CANDIDATES[0].write_text(
        '{"equity": 99900, "pnl": -100}\n', encoding="utf-8"
    )
    result = dashboard.build_paper_metrics()
    assert result["live_now"] is False
    assert result["live_observation_status"] == "UNVERIFIED"
    assert result["runtime_live_requested"] is (runtime.get("live") is True)
    assert result["value_basis"] == "PAPER_REPORTED_UNRECONCILED"


@pytest.mark.parametrize("registry_key", ["rows", "sources"])
@pytest.mark.parametrize("config_key", ["providers", "sources", None])
def test_registry_wrappers_keep_sources_without_promoting_modeled_dollars(
    dashboard, registry_key, config_key
):
    configs = {"EIA": {"enabled": True}, "NREL": {"enabled": False}}
    put(dashboard.SRC_PATH, {config_key: configs} if config_key else configs)
    rows = [
        {"source": source, "sector": "energy", "rows": 250,
         "enabled": True, "status": "LIVE_KEY_PRESENT",
         "last_probe_utc": "2020-01-01T00:00:00Z", "dollar_basis": "MEASURED"}
        for source in ["EIA", "NREL", "UNCONFIGURED"]
    ]
    put(dashboard.REG_PATH, {registry_key: rows})
    result = dashboard.build_infra_metrics()
    assert result["registry_detected_sources"] == 3
    assert result["enabled_sources"] == 1
    assert result["live_measured_sources"] == 0
    assert result["economics_verified"] is False
    assert result["source_observation_status"] == "UNVERIFIED"
    assert result["sector_value_matrix"][0]["basis"] == "MODELED"
    assert all(row["value_basis"] == "MODELED" for row in result["source_truth_rows"])
    assert all(not row["live_measured"] for row in result["source_truth_rows"])
    assert result["estimated_hourly_preserved_value"] == 3913.75
    assert result["reported_source_rows"] == 750
    assert result["measured_source_rows"] == 0
    assert result["sources_with_measured_rows"] == 0
    dashboard.build_infra_dashboard(result, dashboard.build_paper_metrics())
    html = dashboard.INFRA_DASH_PATH.read_text(encoding="utf-8")
    assert "Production truth only" not in html
    assert "Modeled scenario sum" in html
    assert "not measured savings or revenue" in html


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 1.5, True, "unknown"])
def test_invalid_declared_counts_do_not_produce_truth_artifacts(dashboard, bad):
    put(dashboard.REG_PATH, {"rows": [{"source": "EIA", "rows": bad}]})
    with pytest.raises(ValueError, match="row count"):
        dashboard.build_infra_metrics()
    assert not dashboard.SOURCE_TRUTH_PATH.exists()
    assert not dashboard.SECTOR_MATRIX_PATH.exists()


def test_ambiguous_or_duplicate_registry_records_are_rejected(dashboard):
    for payload in [
        {"sources": [], "rows": []},
        {"rows": [None]},
        {"rows": [{"source": "EIA"}, {"source": "eia"}]},
    ]:
        put(dashboard.REG_PATH, payload)
        with pytest.raises(ValueError):
            dashboard.normalize_registry()


@pytest.mark.parametrize("count", [1000000000000000001, "1000000000000000001"])
def test_declared_integer_counts_are_not_rounded_through_binary_float(dashboard, count):
    put(dashboard.REG_PATH, {"rows": [{"source": "EIA", "rows": count}]})
    assert dashboard.normalize_registry()[0]["rows"] == 1000000000000000001


@pytest.mark.parametrize("owner", [None, os.getpid()])
def test_old_lock_cannot_evict_a_live_or_unknown_owner(dashboard, owner):
    path = dashboard.LOOP_LOCK_PATH
    put(path, {"pid": owner})
    os.utime(path, (1, 1))
    original = path.read_bytes()
    assert dashboard.acquire_loop_lock() is False
    assert path.read_bytes() == original


def test_release_does_not_unlink_another_owners_lock(dashboard):
    path = dashboard.LOOP_LOCK_PATH
    put(path, {"pid": os.getpid() + 1})
    original = path.read_bytes()
    dashboard.release_loop_lock()
    assert path.read_bytes() == original


def test_owned_loop_lock_can_be_acquired_and_released(dashboard):
    assert dashboard.acquire_loop_lock() is True
    dashboard.release_loop_lock()
    assert not dashboard.LOOP_LOCK_PATH.exists()
