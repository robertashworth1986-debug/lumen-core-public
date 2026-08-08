import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "code" / "gov_snapshot_guard.py"
SPEC = importlib.util.spec_from_file_location("gov_snapshot_guard_test", MODULE_PATH)
guard = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(guard)


def test_capacity_guard_blocks_low_free_space_before_inventory(tmp_path):
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    with patch.object(guard.shutil, "disk_usage") as disk_usage:
        disk_usage.return_value = guard.shutil._ntuple_diskusage(100, 99, 1)
        status = guard.snapshot_capacity_status(
            snapshots,
            min_free_bytes=2,
            max_snapshot_files=10,
        )
    assert status["allowed"] is False
    assert status["reason"] == "minimum_free_space_not_met"


def test_capacity_guard_blocks_at_bounded_file_limit(tmp_path):
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    (snapshots / "one.json").write_text("{}", encoding="utf-8")
    (snapshots / "two.json").write_text("{}", encoding="utf-8")
    status = guard.snapshot_capacity_status(
        snapshots,
        min_free_bytes=0,
        max_snapshot_files=2,
    )
    assert status["allowed"] is False
    assert status["reason"] == "snapshot_file_limit_reached"
    assert status["snapshot_files_at_least"] == 2


def test_persistent_lease_survives_process_cache_reset(tmp_path):
    lease_path = tmp_path / "gov_collector_lease.json"
    first = guard.claim_persistent_lease(
        lease_path,
        min_interval_sec=900,
        now_epoch=1_000,
    )
    second = guard.claim_persistent_lease(
        lease_path,
        min_interval_sec=900,
        now_epoch=1_001,
    )
    third = guard.claim_persistent_lease(
        lease_path,
        min_interval_sec=900,
        now_epoch=1_901,
    )
    assert first["claimed"] is True
    assert second["claimed"] is False
    assert second["reason"] == "persistent_throttle"
    assert third["claimed"] is True
    payload = json.loads(lease_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "lumencore.gov_collector_lease.v1"
    assert payload["last_attempt_epoch"] == 1_901


def test_runtime_wires_guard_and_cleans_partial_lock_file():
    dashboard_source = (ROOT / "code" / "dashboard_unified_refresh.py").read_text(
        encoding="utf-8"
    )
    collector_source = (ROOT / "code" / "CANONICAL_GOV_DATA_COLLECTOR.py").read_text(
        encoding="utf-8"
    )
    assert "claim_persistent_lease(" in dashboard_source
    assert "snapshot_capacity_status(GOV_SNAP_DIR)" in dashboard_source
    assert "if created:" in dashboard_source
    assert "LOOP_LOCK_PATH.unlink(missing_ok=True)" in dashboard_source
    assert "snapshot_capacity_status(SNAP_DIR)" in collector_source


def test_partial_loop_lock_is_removed_when_payload_write_fails(tmp_path):
    stack_root = tmp_path / "stack"
    dashboard_dir = tmp_path / "dashboard"
    stack_root.mkdir()
    dashboard_dir.mkdir()
    old_root = os.environ.get("LUMA_STACK_ROOT")
    old_dash = os.environ.get("LUMA_DASHBOARD_DIR")
    os.environ["LUMA_STACK_ROOT"] = str(stack_root)
    os.environ["LUMA_DASHBOARD_DIR"] = str(dashboard_dir)
    sys.path.insert(0, str(ROOT / "code"))
    try:
        spec = importlib.util.spec_from_file_location(
            "dashboard_unified_refresh_lock_test",
            ROOT / "code" / "dashboard_unified_refresh.py",
        )
        dashboard = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(dashboard)
        dashboard.LOOP_LOCK_PATH = tmp_path / "partial.lock"
        with patch.object(dashboard.os, "write", side_effect=OSError("disk full")):
            assert dashboard.acquire_loop_lock() is False
        assert not dashboard.LOOP_LOCK_PATH.exists()
    finally:
        sys.path.remove(str(ROOT / "code"))
        if old_root is None:
            os.environ.pop("LUMA_STACK_ROOT", None)
        else:
            os.environ["LUMA_STACK_ROOT"] = old_root
        if old_dash is None:
            os.environ.pop("LUMA_DASHBOARD_DIR", None)
        else:
            os.environ["LUMA_DASHBOARD_DIR"] = old_dash


def test_vps_unit_does_not_restart_successful_duplicate_worker_forever():
    deploy_source = (ROOT / "code" / "deploy" / "deploy_vps.sh").read_text(
        encoding="utf-8"
    )
    service_block = deploy_source.split(
        'DASH_REFRESH_SERVICE="/etc/systemd/system/luma-dashboard-refresh.service"',
        1,
    )[1].split("mkdir -p", 1)[0]
    assert "Restart=on-failure" in service_block
    assert "Restart=always" not in service_block
    assert "StartLimitBurst=5" in service_block
