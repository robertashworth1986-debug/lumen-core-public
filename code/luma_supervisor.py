from __future__ import annotations

import argparse
import atexit
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
RUN_DIR = ROOT / "run"
OUT_DIR = CODE / "out" / "execution"

RUN_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEALTH_FILE = OUT_DIR / "supervisor_health.json"
LOCK_FILE = RUN_DIR / "luma_supervisor.lock"


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
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            if pid != os.getpid():
                os.kill(pid, 0)
                print(f"[supervisor] Already running as PID {pid} -- exiting.", flush=True)
                raise SystemExit(0)
        except (ValueError, OSError):
            pass
    LOCK_FILE.write_text(str(os.getpid()))
    atexit.register(lambda: LOCK_FILE.unlink(missing_ok=True))


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def wmi_find_pid(script_fragment: str) -> int | None:
    """Use wmic to find an existing python.exe whose CommandLine contains script_fragment."""
    try:
        result = subprocess.run(
            [
                "wmic", "process", "where",
                f"Name='python.exe' and CommandLine like '%{script_fragment}%'",
                "get", "ProcessId", "/format:csv",
            ],
            capture_output=True, text=True, timeout=8,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.lower().startswith("node"):
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                try:
                    pid = int(parts[-1])
                    if pid and pid != os.getpid():
                        try:
                            os.kill(pid, 0)
                            return pid
                        except OSError:
                            pass
                except ValueError:
                    pass
    except Exception:
        pass
    return None


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
        self._restart_count = 0
        self._backoff = base_delay
        self._next_start: float = 0.0
        self._last_rc: int | None = None
        self._started_at: str | None = None

    def _try_adopt(self) -> bool:
        pid = wmi_find_pid(self.detect)
        if pid:
            print(f"[supervisor] ADOPT   {self.name} pid={pid}", flush=True)
            self._adopted_pid = pid
            self._started_at = now_utc()
            return True
        return False

    def start(self) -> None:
        if self._try_adopt():
            return
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
        except OSError:
            pass
        self._proc = None

    def poll(self) -> None:
        # Watching adopted external process
        if self._adopted_pid is not None:
            try:
                os.kill(self._adopted_pid, 0)
                return  # alive
            except OSError:
                pass
            print(f"[supervisor] ADOPTED-DIED {self.name} pid={self._adopted_pid} -- taking over", flush=True)
            self._adopted_pid = None
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
            existing = wmi_find_pid(self.detect)
            if existing:
                print(f"[supervisor] SINGLETON-OK {self.name} rc=0, pid={existing} -- adopting", flush=True)
                self._adopted_pid = existing
                return
            print(f"[supervisor] CLEAN-EXIT {self.name} rc=0, no instance found -- restarting in {self._backoff:.0f}s", flush=True)
        else:
            print(f"[supervisor] CRASHED {self.name} rc={rc} restart#{self._restart_count} backoff={self._backoff:.0f}s", flush=True)

        self._next_start = time.monotonic() + self._backoff
        self._backoff = min(self._backoff * 2, self.max_delay)

    def status(self) -> dict:
        if self._adopted_pid is not None:
            try:
                os.kill(self._adopted_pid, 0)
                running, pid = True, self._adopted_pid
            except OSError:
                running, pid = False, None
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
            "restart_count": self._restart_count,
            "last_exit_code": self._last_rc,
            "started_at": self._started_at,
            "backoff_sec": round(self._backoff, 1),
        }


def free_port(port: int) -> None:
    """Kill any process listening on the given TCP port (Windows only)."""
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=8,
        )
        for line in result.stdout.splitlines():
            if f":{port}" in line and "LISTENING" in line:
                parts = line.split()
                pid = int(parts[-1])
                if pid and pid != os.getpid():
                    try:
                        subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                                       capture_output=True, timeout=5)
                        print(f"[supervisor] freed port {port} by killing PID {pid}", flush=True)
                    except Exception:
                        pass
    except Exception:
        pass


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
    ]


def run_supervisor(services: list[Service], poll_interval: float = 5.0) -> None:
    shutdown = [False]

    def handle_signal(sig, frame):
        print(f"\n[supervisor] Signal {sig} -- shutting down...", flush=True)
        shutdown[0] = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print(f"[supervisor] Starting {len(services)} services...", flush=True)
    # Free known ports before binding so stale holders don't block us
    free_port(8787)
    free_port(7701)
    time.sleep(1)  # brief settle after kills
    for svc in services:
        svc.start()

    tick = 0
    while not shutdown[0]:
        time.sleep(poll_interval)
        tick += 1
        for svc in services:
            svc.poll()

        statuses = [s.status() for s in services]
        all_ok = all(s["running"] for s in statuses)
        write_json(HEALTH_FILE, {
            "timestamp_utc": now_utc(),
            "all_healthy": all_ok,
            "supervisor_pid": os.getpid(),
            "tick": tick,
            "services": statuses,
        })

        if tick % 12 == 0:
            up = sum(1 for s in statuses if s["running"])
            print(f"[supervisor] tick={tick}  up={up}/{len(services)}  {now_utc()}", flush=True)

    print("[supervisor] Stopping all services...", flush=True)
    for svc in reversed(services):
        svc.stop()
    print("[supervisor] Stopped.", flush=True)


def main() -> int:
    _acquire_lock()
    parser = argparse.ArgumentParser(description="LumaTrader unified process supervisor")
    parser.add_argument("--include-icloud", action="store_true")
    parser.add_argument("--no-orders", action="store_true")
    parser.add_argument("--poll-sec", type=float, default=5.0)
    args = parser.parse_args()
    services = build_services(include_icloud=args.include_icloud, no_orders=args.no_orders)
    run_supervisor(services, poll_interval=args.poll_sec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
