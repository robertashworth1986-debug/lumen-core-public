"""Native OS-lock checks use the actual source class without operator imports."""
from __future__ import annotations

import ast
import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[1] / "code" / "luma_experience_gateway_legacy.py"


def load_lock_classes():
    nodes = [node for node in ast.parse(SOURCE.read_text()).body if isinstance(node, ast.ClassDef)
             and node.name in {"GatewayAlreadyRunning", "GatewayLifetimeLock"}]
    namespace = {"Path": Path, "os": os, "stat": stat}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["GatewayLifetimeLock"], namespace["GatewayAlreadyRunning"]


def test_native_lock_rejects_second_owner_and_allows_restart(tmp_path):
    Lock, Busy = load_lock_classes()
    path = tmp_path / "run" / "gateway.lock"
    owner, second = Lock(path), Lock(path)
    owner.acquire()
    try:
        assert path.read_text() == str(os.getpid())
        with pytest.raises(Busy):
            second.acquire()
    finally:
        owner.release()
    # A persistent guard and stale diagnostic PID are intentional and safe.
    assert owner.guard_path.is_file()
    second.acquire()
    second.release()
    second.release()  # Idempotent cleanup.


def test_cleanup_never_removes_replacement_owner_pid_record(tmp_path):
    Lock, _ = load_lock_classes()
    path = tmp_path / "gateway.lock"
    owner = Lock(path)
    owner.acquire()
    replacement = tmp_path / "replacement"
    replacement.write_text("999999999")
    try:
        replacement.replace(path)
    except PermissionError:
        # Some Windows filesystems disallow replacement; a content replacement
        # is enough to reproduce the historical owner-blind cleanup defect.
        path.write_text("999999999")
    owner.release()
    assert path.read_text() == "999999999"
    assert owner.guard_path.is_file()


def test_live_preupgrade_pid_is_not_overwritten(tmp_path):
    Lock, Busy = load_lock_classes()
    path = tmp_path / "gateway.lock"
    code = "import time; time.sleep(20)"
    prior = subprocess.Popen([sys.executable, "-c", code])
    try:
        path.write_text(str(prior.pid))
        owner = Lock(path)
        with pytest.raises(Busy):
            owner.acquire()
        assert prior.poll() is None, "liveness inspection must not signal/terminate the owner"
        assert path.read_text() == str(prior.pid)
        assert owner._fd is None
    finally:
        prior.terminate()
        prior.wait(timeout=5)


def test_native_lock_excludes_another_process(tmp_path):
    Lock, _ = load_lock_classes()
    path = tmp_path / "gateway.lock"
    owner = Lock(path)
    owner.acquire()
    probe = '''
import importlib.util, sys
spec = importlib.util.spec_from_file_location("lock_tests", sys.argv[1])
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
Lock, Busy = module.load_lock_classes()
try:
    Lock(module.Path(sys.argv[2])).acquire()
except Busy:
    print("BUSY")
else:
    raise SystemExit("second process acquired an owned lock")
'''
    try:
        result = subprocess.run([sys.executable, "-c", probe, __file__, str(path)],
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "BUSY"
    finally:
        owner.release()


def test_stale_pid_record_allows_restart(tmp_path):
    Lock, _ = load_lock_classes()
    path = tmp_path / "gateway.lock"
    prior = subprocess.Popen([sys.executable, "-c", "pass"])
    prior.wait(timeout=5)
    path.write_text(str(prior.pid))
    owner = Lock(path)
    owner.acquire()
    try:
        assert path.read_text() == str(os.getpid())
    finally:
        owner.release()


@pytest.mark.skipif(os.name != "posix", reason="POSIX symlink fixture")
def test_lock_refuses_symlinked_guard_and_pid_paths(tmp_path):
    Lock, _ = load_lock_classes()
    target = tmp_path / "target"
    target.write_text("preserve")
    for field in ("guard_path", "pid_path"):
        lock = Lock(tmp_path / field)
        getattr(lock, field).symlink_to(target)
        with pytest.raises(RuntimeError, match="symbolic links"):
            lock.acquire()
        assert target.read_text() == "preserve"
