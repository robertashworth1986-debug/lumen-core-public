from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "build_api_source_agent_monitor.py"
SPEC = importlib.util.spec_from_file_location("api_source_agent_monitor", SCRIPT)
monitor = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(monitor)
NOW = datetime(2026, 9, 25, 12, tzinfo=timezone.utc)


def inputs():
    return (
        {"rows": [{"source": "EIA", "last_probe_utc": NOW.isoformat(), "probe_ok": True}]},
        {"providers": {"EIA": {"enabled": True, "sector": "energy"}}},
    )


def evaluate(registry, config, **kwargs):
    return monitor.build_agent_rows(registry, config, {}, 24, now_dt=NOW, **kwargs)


def test_canonical_registry_and_provider_config_do_not_crash_or_reanimate_archived_sources():
    registry = monitor.read_json(ROOT / "config" / "live_source_registry.json")
    config = monitor.read_json(ROOT / "config" / "live_sources.json")
    rows, summary = evaluate(registry, config)
    assert summary["total_agents"] == 17
    assert summary["enabled_agents"] == 17
    assert summary["active_agents"] == 0
    assert summary["degraded_agents"] == 17
    assert summary["stale_probe_agents"] == 17
    assert all(row["dataset_review_readiness"] == "NOT_EVALUATED" for row in rows)
    assert {row["source"] for row in rows} == set(config["providers"])


@pytest.mark.parametrize("wrapper", [None, "sources", "providers"])
def test_legacy_and_current_config_shapes_preserve_one_source(wrapper):
    registry, config = inputs()
    sources = {"eia": config["providers"]["EIA"]}
    config = {wrapper: sources} if wrapper else {"generated_utc": NOW.isoformat(), **sources}
    registry["sources"] = registry.pop("rows")
    rows, summary = evaluate(registry, config)
    assert [row["source"] for row in rows] == ["EIA"]
    assert summary["active_agents"] == 1


@pytest.mark.parametrize("probe_ok", [False, None, "true", 1])
def test_archived_config_and_key_presence_cannot_replace_a_successful_registry_probe(probe_ok):
    registry, config = inputs()
    registry["rows"][0].update(probe_ok=probe_ok, status="LIVE_KEY_PRESENT", env="EIA_KEY")
    config["providers"]["EIA"].update(probe_ok=True, measured=True, rows=999)
    rows, summary = monitor.build_agent_rows(registry, config, {"EIA_KEY": "present"}, 24, now_dt=NOW)
    assert summary["active_agents"] == 0
    assert rows[0]["keys_complete"] is True
    assert "probe_not_successful" in rows[0]["blockers"]


def test_successful_public_probe_does_not_require_keys_and_does_not_establish_dataset_readiness():
    registry, config = inputs()
    rows, summary = evaluate(registry, config)
    assert summary["active_agents"] == 1
    assert rows[0]["keys_complete"] is None
    assert rows[0]["dataset_review_readiness"] == "NOT_EVALUATED"


def test_key_diagnostics_remain_separate_from_probe_health_and_split_registry_names():
    registry, config = inputs()
    registry["rows"][0]["env"] = " EIA_KEY , EIA_SECRET "
    config["providers"]["EIA"]["env_names"] = ["eia_key"]
    rows, summary = monitor.build_agent_rows(registry, config, {"EIA_KEY": "present"}, 24, now_dt=NOW)
    assert rows[0]["env_names"] == ["EIA_KEY", "EIA_SECRET"]
    assert rows[0]["env_present"] == ["EIA_KEY"]
    assert rows[0]["keys_complete"] is False
    assert summary["missing_key_agents"] == 1
    assert summary["active_agents"] == 1


@pytest.mark.parametrize(
    "timestamp,blocker",
    [
        (None, "probe_timestamp_missing_or_invalid"),
        ("bad timestamp", "probe_timestamp_missing_or_invalid"),
        ("2026-09-25T12:00:00", "probe_timestamp_missing_or_invalid"),
        ((NOW + timedelta(microseconds=1)).isoformat(), "probe_timestamp_in_future"),
        ((NOW - timedelta(hours=24, microseconds=1)).isoformat(), "probe_stale"),
    ],
)
def test_invalid_future_and_stale_probe_times_fail_closed(timestamp, blocker):
    registry, config = inputs()
    registry["rows"][0]["last_probe_utc"] = timestamp
    rows, summary = evaluate(registry, config)
    assert summary["active_agents"] == 0
    assert rows[0]["stale_probe"] is True
    assert blocker in rows[0]["blockers"]


def test_exact_freshness_boundary_is_inclusive_without_rounding():
    registry, config = inputs()
    registry["rows"][0]["last_probe_utc"] = (NOW - timedelta(hours=24)).isoformat()
    rows, summary = evaluate(registry, config)
    assert summary["active_agents"] == 1
    assert rows[0]["last_probe_age_hours"] == 24


@pytest.mark.parametrize("enabled", [False, "true", 1, None])
def test_source_enablement_requires_explicit_true(enabled):
    registry, config = inputs()
    config["providers"]["EIA"]["enabled"] = enabled
    rows, summary = evaluate(registry, config)
    assert rows[0]["agent_state"] == "DISABLED"
    assert "source_not_enabled" in rows[0]["blockers"]
    assert summary["active_agents"] == 0


@pytest.mark.parametrize("threshold", [0, -1, float("inf"), float("-inf"), float("nan"), True, "24"])
def test_invalid_freshness_threshold_is_rejected(threshold):
    registry, config = inputs()
    with pytest.raises(ValueError, match="finite and positive"):
        monitor.build_agent_rows(registry, config, {}, threshold, now_dt=NOW)


def test_naive_evaluation_time_is_rejected():
    registry, config = inputs()
    with pytest.raises(ValueError, match="timezone"):
        monitor.build_agent_rows(registry, config, {}, 24, now_dt=NOW.replace(tzinfo=None))


@pytest.mark.parametrize(
    "registry",
    [None, {}, {"rows": {}}, {"rows": ["EIA"]}, {"rows": [{}]}, {"rows": [{"source": 123}]},
     {"rows": [], "sources": []}, {"rows": [{"source": "EIA"}, {"source": " eia "}]}],
)
def test_malformed_and_duplicate_registry_rows_are_rejected(registry):
    _, config = inputs()
    with pytest.raises(ValueError):
        evaluate(registry, config)


@pytest.mark.parametrize(
    "config",
    [None, {"providers": []}, {"providers": {"EIA": True}}, {"providers": {"": {}}},
     {"providers": {"EIA": {}, " eia ": {}}}, {"providers": {}, "sources": {}}],
)
def test_malformed_and_duplicate_config_sources_are_rejected(config):
    registry, _ = inputs()
    with pytest.raises(ValueError):
        evaluate(registry, config)


def run_cli(tmp_path, *extra):
    registry, config = inputs()
    registry_path, config_path = tmp_path / "registry.json", tmp_path / "config.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    config_path.write_text(json.dumps(config), encoding="utf-8")
    output_dir = tmp_path / "reports"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--registry", str(registry_path),
         "--live-sources", str(config_path), "--key-status", str(tmp_path / "absent-keys.txt"),
         "--output-dir", str(output_dir), "--generated-at", NOW.isoformat(), *extra],
        capture_output=True, text=True, timeout=20, check=False,
    )
    return result, output_dir


def test_cli_explicit_inputs_output_and_time_create_a_bounded_report(tmp_path):
    result, output_dir = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr
    dated = output_dir / "api_source_agent_monitor_20260925T120000Z.json"
    latest = output_dir / "api_source_agent_monitor_latest.json"
    assert latest.read_bytes() == dated.read_bytes()
    payload = json.loads(dated.read_text(encoding="utf-8"))
    assert payload["generated_utc"] == NOW.isoformat()
    assert payload["summary"]["active_agents"] == 1
    assert "No network probe" in payload["claim_boundary"]
    assert "does not establish a usable dataset" in (output_dir / "api_source_agent_monitor_latest.md").read_text()


@pytest.mark.parametrize("extra", [("--stale-after-hours", "inf"), ("--generated-at", "2026-09-25T12:00:00")])
def test_cli_rejects_invalid_contract_before_writing(tmp_path, extra):
    result, output_dir = run_cli(tmp_path, *extra)
    assert result.returncode == 2
    assert not output_dir.exists()
    assert "Traceback" not in result.stderr


def test_exact_duplicate_json_members_are_not_silently_overwritten(tmp_path):
    source = tmp_path / "duplicate.json"
    source.write_text('{"providers":{"EIA":{"enabled":false},"EIA":{"enabled":true}}}', encoding="utf-8")
    assert monitor.read_json(source) is None
