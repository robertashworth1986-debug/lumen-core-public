"""Offline regressions for the existing local dashboard's evidence labels."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

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


@pytest.mark.skipif(os.name != "nt", reason="native Windows process-query regression")
def test_windows_liveness_and_live_lock_never_send_a_signal(tmp_path):
    # Run in our own no-console process group. The audit hook rejects a signal
    # before it is sent, including when this regression runs against old code.
    probe = r'''
import importlib.util, json, os, sys
from pathlib import Path
root = Path(sys.argv[2])
(root / "stack").mkdir()
(root / "pages").mkdir()
os.environ["LUMA_STACK_ROOT"] = str(root / "stack")
os.environ["LUMA_DASHBOARD_DIR"] = str(root / "pages")
sys.path.insert(0, str(Path(sys.argv[1]).parent))
def forbid_signal(event, args):
    if event == "os.kill":
        raise AssertionError("liveness check attempted to send a signal")
sys.addaudithook(forbid_signal)
spec = importlib.util.spec_from_file_location("dashboard_child", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert module.pid_is_running(os.getpid()) is True
module.LOOP_LOCK_PATH.write_text(json.dumps({"pid": os.getpid()}))
before = module.LOOP_LOCK_PATH.read_bytes()
assert module.acquire_loop_lock() is False
assert module.LOOP_LOCK_PATH.read_bytes() == before
print("LIVE_OWNER_PRESERVED_WITHOUT_SIGNALS", flush=True)
'''
    result = subprocess.run(
        [sys.executable, "-c", probe, str(ROOT / "code/dashboard_unified_refresh.py"), str(tmp_path)],
        capture_output=True, text=True, timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "LIVE_OWNER_PRESERVED_WITHOUT_SIGNALS"


@pytest.mark.parametrize("owner", [-1, 0, True, 1.5, "123", {}, []])
def test_malformed_owner_cannot_be_reclaimed_as_a_dead_process(dashboard, owner):
    put(dashboard.LOOP_LOCK_PATH, {"pid": owner})
    original = dashboard.LOOP_LOCK_PATH.read_bytes()
    assert dashboard.acquire_loop_lock() is False
    assert dashboard.LOOP_LOCK_PATH.read_bytes() == original


def _windows_process_api(monkeypatch, dashboard, *, open_error=0, query_error=0, exit_code=259):
    import ctypes

    calls = []
    errors = [open_error]

    class Function:
        def __init__(self, name, callback):
            self.name, self.callback = name, callback

        def __call__(self, *args):
            calls.append((self.name, args))
            return self.callback(*args)

    def query(handle, output):
        errors[0] = query_error
        output._obj.value = exit_code
        return not query_error

    kernel = SimpleNamespace(
        OpenProcess=Function("open", lambda *args: None if open_error else 42),
        GetExitCodeProcess=Function("query", query),
        CloseHandle=Function("close", lambda handle: True),
    )

    def forbidden_signal(*args):
        pytest.fail("Windows liveness must not call os.kill")

    monkeypatch.setattr(dashboard, "os", SimpleNamespace(**{**vars(os), "name": "nt", "kill": forbidden_signal}))
    monkeypatch.setattr(ctypes, "WinDLL", lambda name, **kwargs: kernel, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: errors[0], raising=False)
    return calls


@pytest.mark.parametrize("exit_code,expected", [(259, True), (0, False), (17, False)])
def test_windows_process_query_closes_handle_and_uses_query_only_access(dashboard, monkeypatch, exit_code, expected):
    calls = _windows_process_api(monkeypatch, dashboard, exit_code=exit_code)
    assert dashboard.pid_is_running(123) is expected
    assert calls[0] == ("open", (0x1000, False, 123))
    assert [name for name, _ in calls] == ["open", "query", "close"]
    assert calls[-1] == ("close", (42,))


@pytest.mark.parametrize("open_error,query_error,should_reclaim", [(87, 0, True), (5, 0, False), (8, 0, False), (0, 6, False)])
def test_windows_lock_reclaim_requires_confirmed_absent_owner(dashboard, monkeypatch, open_error, query_error, should_reclaim):
    calls = _windows_process_api(monkeypatch, dashboard, open_error=open_error, query_error=query_error)
    put(dashboard.LOOP_LOCK_PATH, {"pid": 123})
    original = dashboard.LOOP_LOCK_PATH.read_bytes()
    assert dashboard.acquire_loop_lock() is should_reclaim
    if should_reclaim:
        assert json.loads(dashboard.LOOP_LOCK_PATH.read_text())["pid"] == os.getpid()
    else:
        assert dashboard.LOOP_LOCK_PATH.read_bytes() == original
    assert sum(name == "close" for name, _ in calls) == (0 if open_error else 1)


def test_windows_pid_outside_dword_range_cannot_alias_another_owner(dashboard, monkeypatch):
    calls = _windows_process_api(monkeypatch, dashboard)
    put(dashboard.LOOP_LOCK_PATH, {"pid": 2**32 + 123})
    original = dashboard.LOOP_LOCK_PATH.read_bytes()
    assert dashboard.acquire_loop_lock() is False
    assert dashboard.LOOP_LOCK_PATH.read_bytes() == original
    assert calls == []


def test_posix_unexpected_probe_error_preserves_the_owner_lock(dashboard, monkeypatch):
    def unavailable(*args):
        raise OSError("temporary process-query failure")

    monkeypatch.setattr(dashboard, "os", SimpleNamespace(**{**vars(os), "name": "posix", "kill": unavailable}))
    put(dashboard.LOOP_LOCK_PATH, {"pid": 123})
    original = dashboard.LOOP_LOCK_PATH.read_bytes()
    assert dashboard.acquire_loop_lock() is False
    assert dashboard.LOOP_LOCK_PATH.read_bytes() == original
