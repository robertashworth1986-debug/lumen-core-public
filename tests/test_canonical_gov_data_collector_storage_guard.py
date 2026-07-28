from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "CANONICAL_GOV_DATA_COLLECTOR.py"


def _load_collector():
    spec = importlib.util.spec_from_file_location(
        "canonical_gov_data_collector_storage_test",
        MODULE_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_content_addressed_snapshots_deduplicate_identical_payloads(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = _load_collector()
    snapshot_dir = tmp_path / "gov_live_snapshots"
    monkeypatch.setattr(collector, "SNAP_DIR", snapshot_dir)
    monkeypatch.setenv(collector.SNAPSHOT_MIN_FREE_BYTES_ENV, "1024")
    monkeypatch.setattr(
        collector.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=10_000, used=1_000, free=9_000),
    )

    first = collector.write_content_addressed_snapshot(
        "eia_rto",
        {"response": {"data": [{"period": "2026-07-27T23"}]}},
    )
    second = collector.write_content_addressed_snapshot(
        "eia_rto",
        {"response": {"data": [{"period": "2026-07-27T23"}]}},
    )

    assert first["snapshot_new"] is True
    assert second["snapshot_new"] is False
    assert first["snapshot"] == second["snapshot"]
    assert first["snapshot_sha256"] == second["snapshot_sha256"]
    assert len(list(snapshot_dir.glob("*.json"))) == 1
    assert list(snapshot_dir.glob("*.tmp")) == []


def test_new_snapshot_fails_closed_before_reserved_headroom_is_crossed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = _load_collector()
    snapshot_dir = tmp_path / "gov_live_snapshots"
    monkeypatch.setattr(collector, "SNAP_DIR", snapshot_dir)
    monkeypatch.setenv(collector.SNAPSHOT_MIN_FREE_BYTES_ENV, "4096")
    monkeypatch.setattr(
        collector.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(total=10_000, used=7_000, free=3_000),
    )

    with pytest.raises(
        collector.SnapshotWriteBlocked,
        match="reserved storage headroom",
    ):
        collector.write_content_addressed_snapshot("fred_unrate", {"rows": [1]})

    assert list(snapshot_dir.glob("*.json")) == []
    assert list(snapshot_dir.glob("*.tmp")) == []


def test_existing_snapshot_remains_readable_when_storage_is_under_pressure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collector = _load_collector()
    snapshot_dir = tmp_path / "gov_live_snapshots"
    monkeypatch.setattr(collector, "SNAP_DIR", snapshot_dir)
    monkeypatch.setenv(collector.SNAPSHOT_MIN_FREE_BYTES_ENV, "4096")
    free_bytes = {"value": 9_000}
    monkeypatch.setattr(
        collector.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(
            total=10_000,
            used=10_000 - free_bytes["value"],
            free=free_bytes["value"],
        ),
    )

    first = collector.write_content_addressed_snapshot(
        "usgs_iv",
        {"value": {"timeSeries": []}},
    )
    free_bytes["value"] = 0
    second = collector.write_content_addressed_snapshot(
        "usgs_iv",
        {"value": {"timeSeries": []}},
    )

    assert first["snapshot_new"] is True
    assert second["snapshot_new"] is False
    assert Path(second["snapshot"]).is_file()


def test_collector_has_no_timestamp_named_government_snapshot_writes() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")

    assert "int(time.time())" not in text
    assert "write_text(json.dumps(data" not in text
    for prefix in (
        "fred_unrate",
        "usgs_iv",
        "noaa_datasets",
        "bls_unrate",
        "nasa_apod",
        "nrel_solar",
        "epa_aqs_states",
        "bea_dataset_list",
        "census_acs",
        "eia_rto",
    ):
        assert f'write_content_addressed_snapshot("{prefix}", data)' in text
