from __future__ import annotations

import argparse
import atexit
import ctypes
import json
import math
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO

ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parent.parent))
).resolve()
CODE = ROOT / "code"
RUN_DIR = ROOT / "run"
OUT_DIR = ROOT / "out" / "execution"

HEALTH_FILE = OUT_DIR / "supervisor_health.json"
LOCK_FILE = RUN_DIR / "luma_supervisor.lock"
_LOCK_HANDLE: BinaryIO | None = None
# Windows byte locks are mandatory for reads too. Reserve a byte beyond the
# bounded PID record so existing status readers can still read that record.
_LOCK_BYTE_OFFSET = 1 << 30


class ProcessObservationError(RuntimeError):
    """An uncertain process inventory cannot authorize a duplicate launch."""


def _windows_process_snapshot(pid: int) -> tuple[bool | None, int | None]:
    """Passive process-object query; request no signal or termination rights."""
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    # SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION.
    handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)
    if not handle:
        return (False, None) if ctypes.get_last_error() == 87 else (None, None)
    try:
        state = kernel.WaitForSingleObject(handle, 0)
        if state == 0:  # Signaled process object: the process has exited.
            return False, None
        if state != 0x102:
            return None, None
        creation, exited, kernel_time, user_time = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exited),
                                      ctypes.byref(kernel_time), ctypes.byref(user_time)):
            return None, None
        return True, (creation.dwHighDateTime << 32) | creation.dwLowDateTime
    finally:
        kernel.CloseHandle(handle)


def _process_snapshot(pid: int) -> tuple[bool | None, int | None]:
    if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF:
        return False, None
    if os.name == "nt":
        return _windows_process_snapshot(pid)
    try:
        os.kill(pid, 0)  # POSIX only: the documented passive existence check.
        return True, None
    except ProcessLookupError:
        return False, None
    except (PermissionError, OSError):
        return None, None


def _process_alive(pid: int) -> bool | None:
    return _process_snapshot(pid)[0]


def resolve_python() -> Path:
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",
        CODE / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


VENV_PY = resolve_python()


def _acquire_lock() -> None:
    global _LOCK_HANDLE
    if _LOCK_HANDLE is not None:
        return
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.is_symlink() or (LOCK_FILE.exists() and not LOCK_FILE.is_file()):
        raise ProcessObservationError("supervisor lock must be a regular local file")
    handle = LOCK_FILE.open("a+b")
    locked = False
    try:
        handle.seek(_LOCK_BYTE_OFFSET if os.name == "nt" else 0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError:
            print("[supervisor] Another supervisor owns the process lock.", flush=True)
            raise SystemExit(0)
        handle.seek(0)
        raw = handle.read(65)
        if raw:
            try:
                pid = int(raw.decode("ascii").strip())
                if len(raw) > 64 or not 0 < pid <= 0xFFFFFFFF:
                    raise ValueError
            except (ValueError, UnicodeDecodeError) as exc:
                raise ProcessObservationError("malformed legacy supervisor lock; inspect before recovery") from exc
            if pid != os.getpid():
                state = _process_alive(pid)
                if state is True:
                    print(f"[supervisor] Existing lock PID {pid} is present; leaving it untouched.", flush=True)
                    raise SystemExit(0)
                if state is None:
                    raise ProcessObservationError("legacy lock process state is unknown; recovery is blocked")
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()).encode("ascii"))
        handle.flush()
        os.fsync(handle.fileno())
        _LOCK_HANDLE = handle
        atexit.register(_release_lock)
    finally:
        if _LOCK_HANDLE is not handle:
            if locked:
                _unlock_file(handle)
            handle.close()


def _unlock_file(handle: BinaryIO) -> None:
    handle.seek(_LOCK_BYTE_OFFSET if os.name == "nt" else 0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _release_lock() -> None:
    global _LOCK_HANDLE
    handle, _LOCK_HANDLE = _LOCK_HANDLE, None
    if handle is not None:
        try:
            _unlock_file(handle)
        finally:
            handle.close()
    # Keep the stable lock inode. Removing it can let a successor lock another
    # file while another process still holds the old inode.


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _split_windows_command(command: str) -> list[str]:
    from ctypes import wintypes

    shell = ctypes.WinDLL("shell32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    shell.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel.LocalFree.restype = wintypes.HLOCAL
    count = ctypes.c_int()
    argv = shell.CommandLineToArgvW(command, ctypes.byref(count))
    if not argv:
        raise ProcessObservationError("cannot parse the observed process command")
    try:
        return [argv[i] for i in range(count.value)]
    finally:
        kernel.LocalFree(argv)


def _python_process_inventory() -> list[dict]:
    if os.name != "nt":
        return []  # POSIX services are owned children; no foreign adoption.
    query = (
        "$ErrorActionPreference='Stop'; "
        "[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false); "
        "@(Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | "
        "Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine) | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", query],
            capture_output=True, timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0 or len(result.stdout) > 8 * 1024 * 1024:
            raise ProcessObservationError("process inventory query failed or exceeded its limit")
        payload = json.loads(result.stdout.decode("utf-8-sig")) if result.stdout.strip() else []
        rows = [payload] if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ProcessObservationError("invalid process inventory shape")
        return rows
    except (OSError, subprocess.TimeoutExpired, ValueError, UnicodeError) as exc:
        raise ProcessObservationError("process inventory unavailable; launch is blocked") from exc


def wmi_find_pid(script_fragment: str, expected_args: list[str] | None = None) -> int | None:
    """Compatibility name: match a CIM command vector, never a substring alone."""
    if not expected_args:
        raise ProcessObservationError("process adoption requires the expected command vector")
    normalize = lambda value: os.path.normcase(os.path.normpath(value)) if os.path.isabs(value) else value
    expected = [normalize(arg) for arg in expected_args]
    allowed_interpreters = {expected[0]}
    if expected[0] == normalize(sys.executable):
        allowed_interpreters.add(normalize(sys._base_executable))
    candidates = []
    unreadable_inventory = False
    for row in _python_process_inventory():
        command = row.get("CommandLine")
        if not isinstance(command, str) or not command.strip():
            unreadable_inventory = True
            continue
        if script_fragment.casefold() not in command.casefold():
            continue
        parsed = _split_windows_command(command)
        # Similar scripts in another checkout are not this stack's services.
        if not any(Path(arg).is_absolute() and Path(arg).resolve().is_relative_to(ROOT) for arg in parsed):
            continue
        observed = [normalize(arg) for arg in parsed]
        if not observed or observed[1:] != expected[1:] or observed[0] not in allowed_interpreters:
            raise ProcessObservationError("an existing stack service has different arguments; review required")
        if normalize(str(row.get("ExecutablePath") or "")) != observed[0]:
            raise ProcessObservationError("existing stack service interpreter identity is unverified")
        pid = row.get("ProcessId")
        if type(pid) is not int or pid == os.getpid():
            raise ProcessObservationError("invalid existing service process identity")
        state = _process_alive(pid)
        if state is None:
            raise ProcessObservationError("existing service liveness is unknown")
        if state:
            candidates.append({"pid": pid, "parent": row.get("ParentProcessId"), "interpreter": observed[0]})
    # The current Windows venv redirector starts a child using this interpreter's
    # known base executable. Require the observed parent relationship and the
    # same remaining argv; unrelated base-Python instances are not substitutes.
    redirector_pids = {row["pid"] for row in candidates if row["interpreter"] == expected[0]}
    redirected_parents = set()
    for row in candidates:
        if row["interpreter"] != expected[0]:
            if row["parent"] not in redirector_pids:
                raise ProcessObservationError("base interpreter has no matching venv redirector")
            redirected_parents.add(row["parent"])
    matches = [row["pid"] for row in candidates if row["pid"] not in redirected_parents]
    if len(matches) > 1:
        raise ProcessObservationError("multiple matching service processes; adoption is blocked")
    if not matches and unreadable_inventory:
        raise ProcessObservationError("Python process command is unreadable; absence is unverified")
    return matches[0] if matches else None


class Service:
    def __init__(
        self,
        name: str,
        args: list[str],
        detect: str,
        cwd: Path | None = None,
        base_delay: float = 5.0,
        max_delay: float = 300.0,
    ) -> None:
        self.name = name
        self.args = args
        self.detect = detect
        self.cwd = cwd or CODE
        self.base_delay = base_delay
        self.max_delay = max_delay

        self._proc: subprocess.Popen | None = None
        self._adopted_pid: int | None = None
        self._adopted_created: int | None = None
        self._blocked_reason: str | None = None
        self._restart_count = 0
        self._backoff = base_delay
        self._next_start: float = 0.0
        self._last_rc: int | None = None
        self._started_at: str | None = None

    def _try_adopt(self) -> bool:
        pid = wmi_find_pid(self.detect, self.args)
        if pid:
            alive, created = _process_snapshot(pid)
            if alive is not True:
                raise ProcessObservationError("process changed during adoption; retry observation")
            print(f"[supervisor] ADOPT   {self.name} pid={pid}", flush=True)
            self._adopted_pid = pid
            self._adopted_created = created
            self._started_at = now_utc()
            return True
        return False

    def start(self) -> None:
        if self._proc is not None or self._adopted_pid is not None:
            return
        try:
            if self._try_adopt():
                self._blocked_reason = None
                return
        except ProcessObservationError as exc:
            self._blocked_reason = str(exc)
            self._next_start = time.monotonic() + self._backoff
            print(f"[supervisor] HOLD    {self.name}: {exc}", flush=True)
            return
        self._blocked_reason = None
        print(f"[supervisor] START   {self.name}", flush=True)
        self._proc = subprocess.Popen(self.args, cwd=self.cwd, stdin=subprocess.DEVNULL)
        self._started_at = now_utc()

    def stop(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=8)
        except (OSError, subprocess.TimeoutExpired) as exc:
            if self._proc.poll() is None:
                self._blocked_reason = "owned child termination could not be verified"
                raise ProcessObservationError(self._blocked_reason) from exc
        self._proc = None

    def _adopted_state(self) -> bool | None:
        if self._adopted_created is None:
            return _process_alive(self._adopted_pid)
        alive, created = _process_snapshot(self._adopted_pid)
        if alive is True and created != self._adopted_created:
            return False  # PID reuse does not inherit the previous observation.
        return alive

    def poll(self) -> None:
        # Watching adopted external process
        if self._adopted_pid is not None:
            state = self._adopted_state()
            if state is True:
                self._blocked_reason = None
                return
            if state is None:
                self._blocked_reason = "adopted process state is unknown; no replacement launch"
                return
            print(f"[supervisor] ADOPTED-DIED {self.name} pid={self._adopted_pid} -- taking over", flush=True)
            self._adopted_pid = None
            self._adopted_created = None
            self._restart_count += 1
            self._next_start = time.monotonic() + self._backoff
            self._backoff = min(self._backoff * 2, self.max_delay)
            return

        if self._proc is None:
            if time.monotonic() >= self._next_start:
                self.start()
            return

        rc = self._proc.poll()
        if rc is None:
            return  # still running

        self._last_rc = rc
        self._proc = None
        self._restart_count += 1

        if rc == 0:
            # Singleton bailed -- check if something is already running
            try:
                if self._try_adopt():
                    self._blocked_reason = None
                    return
            except ProcessObservationError as exc:
                self._blocked_reason = str(exc)
            print(f"[supervisor] CLEAN-EXIT {self.name} rc=0; recheck in {self._backoff:.0f}s", flush=True)
        else:
            print(f"[supervisor] CRASHED {self.name} rc={rc} restart#{self._restart_count} backoff={self._backoff:.0f}s", flush=True)

        self._next_start = time.monotonic() + self._backoff
        self._backoff = min(self._backoff * 2, self.max_delay)

    def status(self) -> dict:
        if self._adopted_pid is not None:
            running = self._adopted_state()
            pid = self._adopted_pid if running is not False else None
        elif self._proc is not None:
            running = self._proc.poll() is None
            pid = self._proc.pid if running else None
        else:
            running, pid = False, None

        return {
            "name": self.name,
            "running": running,
            "pid": pid,
            "adopted": self._adopted_pid is not None,
            "ownership": "observed_external" if self._adopted_pid is not None else ("owned_child" if self._proc is not None else "none"),
            "process_observation": "present" if running is True else ("absent" if running is False else "unknown"),
            "application_health_verified": False,
            "blocked_reason": self._blocked_reason,
            "restart_count": self._restart_count,
            "last_exit_code": self._last_rc,
            "started_at": self._started_at,
            "backoff_sec": round(self._backoff, 1),
        }


def free_port(port: int) -> None:
    """Retired compatibility entry: a port number is not process ownership."""
    raise ProcessObservationError(f"automatic termination of port {port} owners is disabled")


def build_services(include_icloud: bool = False, no_orders: bool = False) -> list[Service]:
    py = str(VENV_PY)

    eco_root_args: list[str] = ["--include-root", str(ROOT)]
    if include_icloud:
        eco_root_args += ["--include-root", r"C:\Users\Novac\iCloudDrive"]

    orch_args = [
        py, str(CODE / "execution" / "alpaca_paper_orchestrator.py"),
        "--max-symbols", "5000", "--top-n", "300",
        "--loop", "--interval-sec", "45", "--status-only-when-closed",
    ]
    if no_orders:
        orch_args.append("--no-orders")

    return [
        Service("gateway",
                [py, "-m", "uvicorn", "luma_experience_gateway:app",
                 "--app-dir", str(CODE), "--host", "0.0.0.0", "--port", "8787"],
                detect="luma_experience_gateway:app"),
        Service("ecosystem",
                [py, str(CODE / "ecosystem_fabric_engine.py"),
                 "--daemon", "--interval-sec", "300", "--include-only-roots"] + eco_root_args,
                detect="ecosystem_fabric_engine.py"),
        Service("orchestrator",
                orch_args,
                detect="alpaca_paper_orchestrator.py"),
        Service("dashboard",
                [py, str(CODE / "dashboard_unified_refresh.py"), "--loop"],
                detect="dashboard_unified_refresh.py"),
        Service("sector-api",
                [py, "-m", "uvicorn", "execution.sector_opp_gain_server:app",
                 "--app-dir", str(CODE), "--host", "127.0.0.1", "--port", "7701"],
                detect="sector_opp_gain_server"),
        Service("infra-loop",
                [py, str(CODE / "execution" / "build_infra_audit_dashboard.py"),
                 "--loop", "--interval", "30"],
                detect="build_infra_audit_dashboard.py"),
        Service("ml-signals",
                [py, str(CODE / "luma_ml_signals.py"), "--loop", "--interval", "120"],
                detect="luma_ml_signals.py"),
        Service("live-truth-fabric",
            [py, str(CODE / "live_truth_fabric_daemon.py"), "--loop", "--interval", "30"],
            detect="live_truth_fabric_daemon.py"),
        Service(
            "kraken-history",
            [
                py,
                str(CODE / "ops" / "collect_kraken_hourly_history.py"),
                "--daemon",
                "--cycle-sec",
                "21600",
                "--pair-limit",
                "80",
                "--rebuild-timing",
            ],
            detect="collect_kraken_hourly_history.py",
            base_delay=30.0,
            max_delay=900.0,
        ),
        Service(
            "symbol-awareness",
            [
                py,
                str(CODE / "execution" / "luma_symbol_awareness_daemon.py"),
                "--loop-seconds",
                "1.0",
            ],
            detect="luma_symbol_awareness_daemon.py",
            base_delay=10.0,
            max_delay=300.0,
        ),
    ]


def run_supervisor(services: list[Service], poll_interval: float = 5.0) -> None:
    if not math.isfinite(poll_interval) or not 0.1 <= poll_interval <= 3600:
        raise ValueError("poll interval must be finite and between 0.1 and 3600 seconds")
    shutdown = [False]

    def handle_signal(sig, frame):
        print(f"\n[supervisor] Signal {sig} -- shutting down...", flush=True)
        shutdown[0] = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"[supervisor] Starting {len(services)} services...", flush=True)
    try:
        for svc in services:
            svc.start()

        tick = 0
        while not shutdown[0]:
            time.sleep(poll_interval)
            if shutdown[0]:
                break
            tick += 1
            for svc in services:
                svc.poll()

            statuses = [s.status() for s in services]
            all_running = bool(statuses) and all(s["running"] is True for s in statuses)
            write_json(HEALTH_FILE, {
                "schema": "lumencore.supervisor_process_observation.v2",
                "timestamp_utc": now_utc(),
                "all_running": all_running,
                "all_healthy": False,
                "application_health_verified": False,
                "scope": "process_presence_only",
                "supervisor_pid": os.getpid(),
                "tick": tick,
                "services": statuses,
            })

            if tick % 12 == 0:
                up = sum(1 for s in statuses if s["running"] is True)
                print(f"[supervisor] tick={tick}  present={up}/{len(services)}  {now_utc()}", flush=True)
    finally:
        print("[supervisor] Stopping owned child processes...", flush=True)
        stop_errors = []
        for svc in reversed(services):
            try:
                svc.stop()
            except Exception as exc:
                stop_errors.append(exc)
        if stop_errors:
            raise ProcessObservationError("one or more owned child stops could not be verified") from stop_errors[0]
        print("[supervisor] Stopped.", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="LumaTrader unified process supervisor")
    parser.add_argument("--include-icloud", action="store_true")
    parser.add_argument("--no-orders", action="store_true")
    parser.add_argument("--poll-sec", type=float, default=5.0)
    args = parser.parse_args()
    if not math.isfinite(args.poll_sec) or not 0.1 <= args.poll_sec <= 3600:
        parser.error("--poll-sec must be finite and between 0.1 and 3600")
    _acquire_lock()
    try:
        services = build_services(include_icloud=args.include_icloud, no_orders=args.no_orders)
        run_supervisor(services, poll_interval=args.poll_sec)
    finally:
        _release_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
