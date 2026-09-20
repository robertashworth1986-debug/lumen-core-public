"""Supervisor observation must not signal or terminate an unowned process."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "code/luma_supervisor.py"


def load_subject(tmp_path, monkeypatch):
    monkeypatch.setenv("LUMA_STACK_ROOT", str(tmp_path / "isolated-stack"))
    spec = importlib.util.spec_from_file_location("supervisor_ownership_subject", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_import_and_help_do_not_create_runtime_state(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    assert not module.ROOT.exists()
    calls = []
    monkeypatch.setattr(module, "_acquire_lock", lambda: calls.append("lock"))
    monkeypatch.setattr(module.sys, "argv", [str(SOURCE), "--help"])
    with pytest.raises(SystemExit) as stopped:
        module.main()
    assert stopped.value.code == 0
    assert calls == []
    assert not module.ROOT.exists()


def test_legacy_live_pid_lock_is_not_signaled_or_overwritten(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    module.RUN_DIR.mkdir(parents=True, exist_ok=True)
    module.LOCK_FILE.write_text("98765")
    signals = []
    monkeypatch.setattr(module.os, "kill", lambda *args: signals.append(args))
    monkeypatch.setattr(module, "_process_alive", lambda pid: True, raising=False)
    with pytest.raises(SystemExit):
        module._acquire_lock()
    assert signals == []
    assert module.LOCK_FILE.read_text() == "98765"


@pytest.mark.parametrize("operation", ["poll", "status"])
def test_adopted_process_observation_never_sends_a_signal(tmp_path, monkeypatch, operation):
    module = load_subject(tmp_path, monkeypatch)
    service = module.Service("fixture", ["python", "fixture.py"], "fixture.py")
    service._adopted_pid = 98765
    signals = []
    monkeypatch.setattr(module.os, "kill", lambda *args: signals.append(args))
    monkeypatch.setattr(module, "_process_alive", lambda pid: True, raising=False)
    getattr(service, operation)()
    assert signals == []
    assert service._adopted_pid == 98765


def test_port_conflict_never_authorizes_taskkill(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    calls = []

    def observed(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout="TCP 127.0.0.1:8787 0.0.0.0:0 LISTENING 98765\n", returncode=0)

    monkeypatch.setattr(module.subprocess, "run", observed)
    try:
        module.free_port(8787)
    except RuntimeError:
        pass
    assert not any(command[0] == "taskkill" for command in calls)


class FakeService:
    def __init__(self, fail=False):
        self.fail = fail
        self.stopped = False

    def start(self):
        if self.fail:
            raise RuntimeError("owned fixture startup failed")

    def stop(self):
        self.stopped = True

    def poll(self):
        pass

    def status(self):
        return {"name": "fixture", "running": True, "pid": 98765}


def test_startup_failure_stops_only_services_owned_by_this_run(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    first, broken = FakeService(), FakeService(fail=True)
    monkeypatch.setattr(module, "free_port", lambda port: None)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(module.signal, "signal", lambda *args: None)
    with pytest.raises(RuntimeError, match="fixture startup"):
        module.run_supervisor([first, broken])
    assert first.stopped


def test_process_presence_is_not_application_health(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    handlers = []
    records = []
    monkeypatch.setattr(module, "free_port", lambda port: None)
    monkeypatch.setattr(module.signal, "signal", lambda sig, handler: handlers.append(handler))
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    def record_and_stop(path, record):
        records.append(record)
        handlers[0](2, None)
    monkeypatch.setattr(module, "write_json", record_and_stop)
    module.run_supervisor([FakeService()])
    assert records
    assert records[-1]["all_healthy"] is False
    assert records[-1]["all_running"] is True
    assert records[-1]["application_health_verified"] is False


@pytest.mark.parametrize("raw", [b"not-a-pid", b"-1", b"0", b"1" * 65, b"\xff"])
def test_malformed_legacy_locks_are_preserved_for_review(tmp_path, monkeypatch, raw):
    module = load_subject(tmp_path, monkeypatch)
    module.RUN_DIR.mkdir(parents=True)
    module.LOCK_FILE.write_bytes(raw)
    with pytest.raises(module.ProcessObservationError):
        module._acquire_lock()
    assert module.LOCK_FILE.read_bytes() == raw
    assert module._LOCK_HANDLE is None


def test_unknown_legacy_pid_blocks_recovery_without_rewriting_lock(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    module.RUN_DIR.mkdir(parents=True)
    module.LOCK_FILE.write_bytes(b"98765")
    monkeypatch.setattr(module, "_process_alive", lambda pid: None)
    with pytest.raises(module.ProcessObservationError, match="unknown"):
        module._acquire_lock()
    assert module.LOCK_FILE.read_bytes() == b"98765"


def test_concurrent_supervisor_cannot_take_an_owned_os_lock(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    program = (
        "import importlib.util,sys; "
        f"s=importlib.util.spec_from_file_location('owned_lock_fixture',{str(SOURCE)!r}); "
        "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
        "m._acquire_lock(); print('locked',flush=True); sys.stdin.readline(); m._release_lock()"
    )
    # Use the base executable so this is one disposable process, not a Windows
    # venv redirector plus a second process. No stack service is launched.
    child = subprocess.Popen([sys._base_executable, "-u", "-c", program], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        assert child.stdout.readline().strip() == "locked"
        with pytest.raises(SystemExit):
            module._acquire_lock()
        assert module._LOCK_HANDLE is None
        output, error = child.communicate("\n", timeout=10)
        assert child.returncode == 0, error
        module._acquire_lock()
        assert module.LOCK_FILE.read_text() == str(os.getpid())
        module._release_lock()
        assert module.LOCK_FILE.exists()
        module._release_lock()  # Repeated cleanup never deletes a successor file.
    finally:
        module._release_lock()
        if child.poll() is None:
            child.terminate()
        child.communicate(timeout=10)


@pytest.mark.skipif(os.name != "nt", reason="native passive Windows process observation")
def test_native_windows_probe_preserves_owned_child_and_reports_its_exit(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    child = subprocess.Popen([sys._base_executable, "-u", "-c",
        "import sys; print('ready',flush=True); sys.stdin.readline()"], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        assert child.stdout.readline().strip() == "ready"
        identities = {module._windows_process_snapshot(child.pid) for _ in range(30)}
        assert len(identities) == 1
        alive, created = identities.pop()
        assert alive is True and type(created) is int and created > 0
        assert child.poll() is None
        child.communicate("\n", timeout=10)
        assert module._windows_process_snapshot(child.pid)[0] is False
    finally:
        if child.poll() is None:
            child.terminate()
        child.communicate(timeout=10)


@pytest.mark.skipif(os.name != "nt", reason="native Windows command parsing and CIM inventory")
@pytest.mark.parametrize("interpreter", ["base", "venv"])
def test_native_adoption_identifies_owned_fixture_without_stopping_it(tmp_path, monkeypatch, interpreter):
    module = load_subject(tmp_path, monkeypatch)
    fixture = module.ROOT / "code/owned_fixture.py"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("import os,sys\nprint(os.getpid(),flush=True)\nsys.stdin.readline()\n")
    args = [sys._base_executable if interpreter == "base" else sys.executable, str(fixture)]
    child = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        actual_pid = int(child.stdout.readline().strip())
        service = module.Service("fixture", args, "owned_fixture.py")
        service.start()
        assert service._blocked_reason is None, json.dumps([row for row in module._python_process_inventory()
            if str(fixture).casefold() in str(row.get("CommandLine")).casefold()], indent=2)
        assert service._adopted_pid == actual_pid
        assert service._proc is None
        assert service.status()["ownership"] == "observed_external"
        service.stop()
        assert child.poll() is None
        child.communicate("\n", timeout=10)
        assert child.returncode == 0
    finally:
        if child.poll() is None:
            # Only the directly owned redirector is terminated on failure. Its
            # child receives EOF when communicate closes the test input pipe.
            child.communicate("\n", timeout=10)


@pytest.mark.skipif(os.name != "nt", reason="Windows native command-line parser")
def test_windows_command_vector_round_trip_handles_spaces_and_quotes(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    args = [r"C:\Program Files\Python\python.exe", r"C:\stack with spaces\code\worker.py",
            "--label", 'quoted "name"', "", "tail\\", "--no-orders"]
    assert module._split_windows_command(subprocess.list2cmdline(args)) == args


def test_unknown_adopted_process_does_not_trigger_a_replacement(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    service = module.Service("fixture", ["python", "fixture.py"], "fixture.py")
    service._adopted_pid = 98765
    monkeypatch.setattr(module, "_process_alive", lambda pid: None)
    launched = []
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: launched.append(args))
    service.poll()
    assert service._adopted_pid == 98765
    assert service._restart_count == 0
    assert service.status()["running"] is None
    assert service.status()["process_observation"] == "unknown"
    assert launched == []


def test_reused_pid_does_not_inherit_an_adopted_identity(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    service = module.Service("fixture", ["python", "fixture.py"], "fixture.py")
    service._adopted_pid, service._adopted_created = 98765, 100
    monkeypatch.setattr(module, "_process_snapshot", lambda pid: (True, 200))
    assert service.status()["running"] is False
    service.poll()
    assert service._adopted_pid is None
    assert service._proc is None
    assert service._restart_count == 1


def test_foreign_adoption_is_observation_only_and_stop_does_not_terminate_it(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    service = module.Service("fixture", ["python", "fixture.py"], "fixture.py")
    service._adopted_pid = 98765
    signals = []
    monkeypatch.setattr(module.os, "kill", lambda *args: signals.append(args))
    service.stop()
    assert signals == []
    assert service._adopted_pid == 98765


@pytest.mark.parametrize("mutation", ["arguments", "interpreter", "duplicate", "unknown"])
def test_ambiguous_adoption_cannot_start_another_service(tmp_path, monkeypatch, mutation):
    module = load_subject(tmp_path, monkeypatch)
    args = [str(Path(sys.executable)), str(module.ROOT / "code/fixture.py"), "--no-orders"]
    service = module.Service("fixture", args, "fixture.py")
    row = {"ProcessId": 98765, "ExecutablePath": args[0], "CommandLine": json.dumps(args)}
    if mutation == "arguments":
        row["CommandLine"] = json.dumps(args[:-1])
    elif mutation == "interpreter":
        row["ExecutablePath"] = str(module.ROOT / "other-python.exe")
    rows = [row]
    if mutation == "duplicate":
        rows += [{**row, "ProcessId": 98766}]
    monkeypatch.setattr(module, "_python_process_inventory", lambda: rows)
    monkeypatch.setattr(module, "_split_windows_command", json.loads)
    monkeypatch.setattr(module, "_process_alive", lambda pid: None if mutation == "unknown" else True)
    launched = []
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: launched.append(args))
    service.start()
    assert service._blocked_reason is not None
    assert service._adopted_pid is None
    assert launched == []


def test_inventory_failure_does_not_mean_no_service_exists(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    service = module.Service("fixture", ["python", "fixture.py"], "fixture.py")
    def unavailable():
        raise module.ProcessObservationError("fixture inventory unavailable")
    monkeypatch.setattr(module, "_python_process_inventory", unavailable)
    launched = []
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: launched.append(args))
    service.start()
    assert "unavailable" in service.status()["blocked_reason"]
    assert launched == []


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1.0, 0.0, 0.01, 3601.0])
def test_invalid_poll_interval_never_starts_a_service(tmp_path, monkeypatch, value):
    module = load_subject(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="poll interval"):
        module.run_supervisor([FakeService(fail=True)], poll_interval=value)
    assert not module.ROOT.exists()


def test_shutdown_during_wait_never_restarts_a_service(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    handlers = []
    service = FakeService()
    def unexpected_poll():
        raise AssertionError("shutdown must be checked before polling or restarting")
    service.poll = unexpected_poll
    monkeypatch.setattr(module.signal, "signal", lambda sig, handler: handlers.append(handler))
    monkeypatch.setattr(module.time, "sleep", lambda seconds: handlers[0](2, None))
    module.run_supervisor([service])
    assert service.stopped


def test_cleanup_failure_does_not_skip_other_owned_children(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    first, second = FakeService(fail=True), FakeService()
    def failed_stop():
        raise OSError("fixture stop failed")
    second.stop = failed_stop
    monkeypatch.setattr(module.signal, "signal", lambda *args: None)
    with pytest.raises(module.ProcessObservationError, match="stops could not be verified"):
        module.run_supervisor([first, second])
    assert first.stopped


def test_failed_owned_stop_preserves_the_unverified_process_reference(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    service = module.Service("fixture", ["python", "fixture.py"], "fixture.py")
    def denied():
        raise PermissionError("owned fixture termination denied")
    child = SimpleNamespace(terminate=denied, poll=lambda: None)
    service._proc = child
    with pytest.raises(module.ProcessObservationError, match="could not be verified"):
        service.stop()
    assert service._proc is child


def test_unreadable_process_command_blocks_adoption_and_launch(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "_python_process_inventory", lambda: [{"ProcessId": 98765, "CommandLine": None}])
    with pytest.raises(module.ProcessObservationError, match="unreadable"):
        module.wmi_find_pid("fixture.py", [sys.executable, str(module.ROOT / "fixture.py")])


def test_same_script_in_another_checkout_is_not_adopted(tmp_path, monkeypatch):
    module = load_subject(tmp_path, monkeypatch)
    args = [sys.executable, str(module.ROOT / "code/fixture.py")]
    foreign = [sys.executable, str(module.ROOT.with_name(module.ROOT.name + "-other") / "code/fixture.py")]
    monkeypatch.setattr(module, "_python_process_inventory", lambda: [
        {"ProcessId": 98765, "ExecutablePath": sys.executable, "CommandLine": json.dumps(foreign)}])
    monkeypatch.setattr(module, "_split_windows_command", json.loads)
    assert module.wmi_find_pid("fixture.py", args) is None


@pytest.mark.skipif(os.name != "nt", reason="Windows native API failure contract")
@pytest.mark.parametrize("case", ["access_denied", "absent", "wait_failed", "times_failed", "exited"])
def test_windows_api_unknowns_are_not_reported_as_absent(tmp_path, monkeypatch, case):
    module = load_subject(tmp_path, monkeypatch)
    calls = []
    def opened(rights, inherit, pid):
        calls.append(("open", rights, inherit, pid))
        return None if case in {"access_denied", "absent"} else 123
    def waited(handle, millis):
        calls.append(("wait", handle, millis))
        return 0xFFFFFFFF if case == "wait_failed" else (0 if case == "exited" else 0x102)
    def times(*args):
        return False
    def closed(handle):
        calls.append(("close", handle))
        return True
    kernel = SimpleNamespace(OpenProcess=opened, WaitForSingleObject=waited,
                             GetProcessTimes=times, CloseHandle=closed)
    monkeypatch.setattr(module.ctypes, "WinDLL", lambda *args, **kwargs: kernel)
    monkeypatch.setattr(module.ctypes, "get_last_error", lambda: 87 if case == "absent" else 5)
    alive, created = module._windows_process_snapshot(98765)
    assert alive is (False if case in {"absent", "exited"} else None)
    assert created is None
    assert calls[0] == ("open", 0x00101000, False, 98765)
    if case not in {"access_denied", "absent"}:
        assert calls[-1] == ("close", 123)
        assert calls[1] == ("wait", 123, 0)
