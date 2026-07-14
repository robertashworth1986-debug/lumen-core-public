#!/usr/bin/env python3
"""One-shot, observation-only local system health collector.

The collector writes a tamper-evident v2 chain. It never repairs the legacy
chain and never mutates services, containers, software, accounts, or external
systems. Public records use aliases rather than host, user, or path identity.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL_PATH = ROOT / "config" / "local_system_health_observer_protocol_v2.json"
DEFAULT_STATE_DIR = Path(
    os.environ.get(
        "LUMA_LOCAL_SYSTEM_HEALTH_V2_STATE_DIR",
        "E:/LumaProofVault/PRIVATE_CONTEXT/SYSTEM_HEALTH_V2",
    )
)
TASK_STAGING_SCRIPT = ROOT / "code" / "ops" / "STAGE_LOCAL_SYSTEM_HEALTH_V2_TASK.ps1"
ZERO_HASH = "0" * 64
HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class LockUnavailable(RuntimeError):
    """Raised when another collector owns the single-writer lock."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("UTC timestamp must include an offset")
    return parsed.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_protocol(path: Path = DEFAULT_PROTOCOL_PATH) -> dict[str, Any]:
    raw = path.read_bytes()
    protocol = json.loads(raw)
    if protocol.get("schema") != "luma.local_system_health_observer_protocol.v2":
        raise ValueError("unexpected protocol schema")
    if protocol.get("mode") != "observation_only":
        raise ValueError("protocol is not observation-only")
    mutations = protocol.get("mutation_policy", {})
    if not mutations or any(value is not False for value in mutations.values()):
        raise ValueError("all mutation policy values must be false")
    if protocol.get("readiness", {}).get("legacy_dates_credited") != 0:
        raise ValueError("legacy dates must not be credited")
    if protocol.get("readiness", {}).get("horizons_observed_v2_dates") != [30, 90, 180]:
        raise ValueError("readiness horizons must remain frozen at 30/90/180")
    legacy = protocol.get("legacy_v1_genesis_reference", {})
    if legacy.get("repair_attempted") is not False:
        raise ValueError("v1 repair is prohibited")
    if legacy.get("declared_chain_break_count") != 288:
        raise ValueError("legacy break count changed")
    if legacy.get("declared_fork_count") != 6:
        raise ValueError("legacy fork count changed")
    for artifact in legacy.get("artifacts", []):
        if not HEX_64.fullmatch(str(artifact.get("sha256", ""))):
            raise ValueError("legacy artifact hash is invalid")
        if not artifact.get("alias") or any(key in artifact for key in ("path", "absolute_path")):
            raise ValueError("legacy artifacts must use aliases only")
    protocol["_protocol_sha256"] = sha256_bytes(raw)
    return protocol


class SingleWriterLock:
    """Advisory one-byte lock that works across Windows collector processes."""

    def __init__(self, path: Path):
        self.path = path
        self.handle = None
        self.backend = None

    def __enter__(self) -> "SingleWriterLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0, os.SEEK_END)
        if self.handle.tell() == 0:
            self.handle.write(b"\0")
            self.handle.flush()
            os.fsync(self.handle.fileno())
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                self.backend = msvcrt
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.backend = fcntl
        except OSError as exc:
            self.handle.close()
            self.handle = None
            raise LockUnavailable("collector already running") from exc
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.handle is None:
            return
        try:
            self.handle.seek(0)
            if os.name == "nt":
                self.backend.locking(self.handle.fileno(), self.backend.LK_UNLCK, 1)
            else:
                self.backend.flock(self.handle.fileno(), self.backend.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None


def _filetime_value(value: Any) -> int:
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def _system_and_process_times() -> tuple[int, int, int, int]:
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetSystemTimes.argtypes = [
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetSystemTimes.restype = wintypes.BOOL
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    idle = wintypes.FILETIME()
    kernel = wintypes.FILETIME()
    user = wintypes.FILETIME()
    if not kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    ):
        raise OSError("system timing query failed")
    creation = wintypes.FILETIME()
    exit_time = wintypes.FILETIME()
    process_kernel = wintypes.FILETIME()
    process_user = wintypes.FILETIME()
    if not kernel32.GetProcessTimes(
        kernel32.GetCurrentProcess(),
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(process_kernel),
        ctypes.byref(process_user),
    ):
        raise OSError("process timing query failed")
    return (
        _filetime_value(idle),
        _filetime_value(kernel),
        _filetime_value(user),
        _filetime_value(process_kernel) + _filetime_value(process_user),
    )


def observe_cpu(sample_seconds: float) -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "reason": "unsupported_platform"}
    try:
        before = _system_and_process_times()
        time.sleep(max(0.01, float(sample_seconds)))
        after = _system_and_process_times()
        idle_delta = after[0] - before[0]
        total_delta = (after[1] - before[1]) + (after[2] - before[2])
        process_delta = max(0, after[3] - before[3])
        busy_delta = max(0, total_delta - idle_delta)
        adjusted_busy = max(0, busy_delta - min(process_delta, busy_delta))
        percent = 0.0 if total_delta <= 0 else 100.0 * adjusted_busy / total_delta
        return {
            "available": True,
            "busy_percent_excluding_collector": round(min(100.0, max(0.0, percent)), 4),
            "sample_seconds": float(sample_seconds),
            "collector_process_time_excluded": True,
        }
    except (OSError, AttributeError):
        return {"available": False, "reason": "query_failed"}


def observe_uptime() -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "reason": "unsupported_platform"}
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetTickCount64.argtypes = []
        kernel32.GetTickCount64.restype = ctypes.c_ulonglong
        return {
            "available": True,
            "uptime_seconds": round(int(kernel32.GetTickCount64()) / 1000.0, 3),
        }
    except (OSError, AttributeError):
        return {"available": False, "reason": "query_failed"}


def _collector_working_set_bytes() -> int:
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    ok = psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(),
        ctypes.byref(counters),
        counters.cb,
    )
    if not ok:
        raise OSError("process memory query failed")
    return int(counters.WorkingSetSize)


def observe_memory() -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "reason": "unsupported_platform"}
    try:
        from ctypes import wintypes

        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", wintypes.DWORD),
                ("dwMemoryLoad", wintypes.DWORD),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(status)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MemoryStatusEx)]
        kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
        if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("memory query failed")
        collector_bytes = _collector_working_set_bytes()
        total = int(status.ullTotalPhys)
        used = max(0, total - int(status.ullAvailPhys) - collector_bytes)
        return {
            "available": True,
            "total_physical_bytes": total,
            "used_physical_bytes_excluding_collector": used,
            "available_physical_bytes": int(status.ullAvailPhys),
            "collector_working_set_excluded_bytes": collector_bytes,
            "exclusion_adjustment_is_estimate": True,
            "used_percent_excluding_collector": round(100.0 * used / total, 4) if total else None,
        }
    except (OSError, AttributeError):
        return {"available": False, "reason": "query_failed"}


def directory_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for root, directories, files in os.walk(path, followlinks=False):
        directories[:] = [
            name for name in directories if not Path(root, name).is_symlink()
        ]
        for name in files:
            candidate = Path(root, name)
            if candidate.is_symlink():
                continue
            try:
                total += candidate.stat().st_size
            except OSError:
                continue
    return total


def observe_disk(state_dir: Path) -> dict[str, Any]:
    excluded_bytes = directory_bytes(state_dir)
    state_root = Path(state_dir.resolve().anchor)
    system_drive = os.environ.get("SystemDrive", state_root.drive or "C:")
    system_root = Path(system_drive + os.sep)
    roots: list[tuple[str, Path, bool]] = [("system_volume", system_root, False)]
    if os.path.normcase(str(system_root)) == os.path.normcase(str(state_root)):
        roots[0] = ("system_volume", system_root, True)
    else:
        roots.append(("state_volume", state_root, True))
    volumes = []
    for alias, root, contains_state in roots:
        try:
            usage = shutil.disk_usage(root)
            excluded = excluded_bytes if contains_state else 0
            adjusted_used = max(0, int(usage.used) - excluded)
            volumes.append(
                {
                    "volume_alias": alias,
                    "available": True,
                    "total_bytes": int(usage.total),
                    "free_bytes": int(usage.free),
                    "used_bytes_excluding_collector_outputs": adjusted_used,
                    "collector_output_bytes_excluded": excluded,
                    "exclusion_adjustment_uses_logical_file_bytes": True,
                    "used_percent_excluding_collector_outputs": round(
                        100.0 * adjusted_used / int(usage.total), 4
                    )
                    if usage.total
                    else None,
                }
            )
        except OSError:
            volumes.append({"volume_alias": alias, "available": False, "reason": "query_failed"})
    return {"available": any(item.get("available") for item in volumes), "volumes": volumes}


def observe_battery() -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "reason": "unsupported_platform"}
    try:
        from ctypes import wintypes

        class SystemPowerStatus(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_ubyte),
                ("BatteryFlag", ctypes.c_ubyte),
                ("BatteryLifePercent", ctypes.c_ubyte),
                ("SystemStatusFlag", ctypes.c_ubyte),
                ("BatteryLifeTime", wintypes.DWORD),
                ("BatteryFullLifeTime", wintypes.DWORD),
            ]

        status = SystemPowerStatus()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            raise OSError("power query failed")
        battery_present = status.BatteryFlag not in (128, 255)
        percent = None if status.BatteryLifePercent == 255 else int(status.BatteryLifePercent)
        return {
            "available": True,
            "battery_present": battery_present,
            "charge_percent": percent if battery_present else None,
            "ac_line": {0: "offline", 1: "online"}.get(status.ACLineStatus, "unknown"),
            "battery_saver_active": bool(status.SystemStatusFlag),
        }
    except (OSError, AttributeError):
        return {"available": False, "reason": "query_failed"}


def run_command(command: list[str], *, timeout: float) -> subprocess.CompletedProcess[str]:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        creationflags=flags,
    )


def observe_windows_update_service(
    runner: Callable[..., Any] = run_command,
) -> dict[str, Any]:
    if os.name != "nt":
        return {"available": False, "reason": "unsupported_platform"}
    start_mode = "unknown"
    try:
        import winreg

        key_path = r"SYSTEM\CurrentControlSet\Services\wuauserv"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            start_value, _ = winreg.QueryValueEx(key, "Start")
        start_mode = {
            0: "boot",
            1: "system",
            2: "automatic",
            3: "manual",
            4: "disabled",
        }.get(int(start_value), "unknown")
    except (OSError, ValueError):
        pass
    executable = shutil.which("sc.exe")
    if not executable:
        return {
            "available": start_mode != "unknown",
            "service_alias": "windows_update_service",
            "status": "unknown",
            "start_mode": start_mode,
        }
    try:
        result = runner([executable, "query", "wuauserv"], timeout=5.0)
        match = re.search(r"STATE\s*:\s*\d+\s+([A-Z_]+)", result.stdout or "", re.IGNORECASE)
        service_status = match.group(1).lower() if match else "unknown"
        return {
            "available": bool(result.returncode == 0 or start_mode != "unknown"),
            "service_alias": "windows_update_service",
            "status": service_status,
            "start_mode": start_mode,
        }
    except (OSError, subprocess.SubprocessError):
        return {
            "available": start_mode != "unknown",
            "service_alias": "windows_update_service",
            "status": "unknown",
            "start_mode": start_mode,
        }


def _docker_backoff(previous: dict[str, Any] | None, now: datetime) -> str | None:
    if not previous:
        return None
    value = previous.get("next_probe_utc")
    if not value:
        return None
    try:
        next_probe = parse_utc(value)
    except (TypeError, ValueError):
        return None
    return iso_utc(next_probe) if now < next_probe else None


def observe_docker(
    protocol: dict[str, Any],
    previous: dict[str, Any] | None,
    now: datetime,
    *,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = run_command,
) -> dict[str, Any]:
    settings = protocol["observations"]["docker"]
    safe_names = set(settings["public_safe_container_names"])
    backoff_until = _docker_backoff(previous, now)
    if backoff_until:
        return {
            "status": "backoff",
            "cli_available": bool(previous.get("cli_available")) if previous else False,
            "daemon_reachable": False,
            "next_probe_utc": backoff_until,
            "configured_containers": [],
        }
    backoff_minutes = int(protocol["cadence"]["docker_unavailable_backoff_minutes"])
    next_probe = iso_utc(now + timedelta(minutes=backoff_minutes))
    executable = which("docker")
    if not executable:
        return {
            "status": "unavailable",
            "cli_available": False,
            "daemon_reachable": False,
            "next_probe_utc": next_probe,
            "configured_containers": [],
        }
    try:
        daemon = runner(
            [executable, "version", "--format", "{{.Server.Version}}"],
            timeout=8.0,
        )
    except (OSError, subprocess.SubprocessError):
        daemon = None
    if daemon is None or daemon.returncode != 0:
        return {
            "status": "unavailable",
            "cli_available": True,
            "daemon_reachable": False,
            "next_probe_utc": next_probe,
            "configured_containers": [],
        }
    try:
        inventory = runner(
            [executable, "ps", "-a", "--format", "{{json .}}"],
            timeout=8.0,
        )
    except (OSError, subprocess.SubprocessError):
        inventory = None
    if inventory is None or inventory.returncode != 0:
        return {
            "status": "inventory_unavailable",
            "cli_available": True,
            "daemon_reachable": True,
            "next_probe_utc": next_probe,
            "configured_containers": [],
        }
    allowed_states = {"created", "running", "paused", "restarting", "removing", "exited", "dead"}
    configured = []
    for line in (inventory.stdout or "").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = str(row.get("Names", ""))
        if name not in safe_names:
            continue
        state = str(row.get("State", "unknown")).lower()
        configured.append(
            {
                "name": name,
                "state": state if state in allowed_states else "unknown",
            }
        )
    configured.sort(key=lambda item: item["name"])
    observed_names = {item["name"] for item in configured}
    return {
        "status": "observed",
        "cli_available": True,
        "daemon_reachable": True,
        "next_probe_utc": None,
        "configured_containers": configured,
        "configured_names_missing": sorted(safe_names - observed_names),
    }


def collect_snapshot(
    protocol: dict[str, Any],
    state_dir: Path,
    previous_event: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    previous_docker = None
    if previous_event:
        previous_docker = previous_event.get("snapshot", {}).get("docker")
    return {
        "schema": "luma.local_system_health_snapshot.v2",
        "observed_at_utc": iso_utc(now),
        "scope": {
            "host_identity_included": False,
            "user_identity_included": False,
            "absolute_paths_included": False,
            "collector_outputs_excluded": True,
            "collector_process_excluded_where_measurable": True,
            "observation_only": True,
        },
        "cpu": observe_cpu(protocol["observations"]["cpu"]["sample_seconds"]),
        "uptime": observe_uptime(),
        "memory": observe_memory(),
        "disk": observe_disk(state_dir),
        "battery": observe_battery(),
        "windows_update_service": observe_windows_update_service(),
        "docker": observe_docker(protocol, previous_docker, now),
    }


def segment_paths(state_dir: Path, protocol: dict[str, Any]) -> list[Path]:
    contract = protocol["output_contract"]
    pattern = f'{contract["daily_segment_prefix"]}*{contract["daily_segment_suffix"]}'
    return sorted(state_dir.glob(pattern))


def read_last_event(state_dir: Path, protocol: dict[str, Any]) -> dict[str, Any] | None:
    for path in reversed(segment_paths(state_dir, protocol)):
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            position = handle.tell()
            buffer = b""
            while position > 0:
                read_size = min(8192, position)
                position -= read_size
                handle.seek(position)
                buffer = handle.read(read_size) + buffer
                lines = [line for line in buffer.splitlines() if line.strip()]
                if lines and (position == 0 or len(lines) > 1):
                    return json.loads(lines[-1])
        if path.stat().st_size:
            raise ValueError("daily segment contains no valid event")
    return None


def validate_event_integrity(event: dict[str, Any], protocol: dict[str, Any]) -> None:
    if event.get("schema") != "luma.local_system_health_event.v2":
        raise ValueError("previous event schema is invalid")
    if not isinstance(event.get("sequence"), int) or int(event["sequence"]) < 1:
        raise ValueError("previous event sequence is invalid")
    if not HEX_64.fullmatch(str(event.get("prior_event_hash", ""))):
        raise ValueError("previous prior event hash is invalid")
    if event.get("protocol_sha256") != protocol["_protocol_sha256"]:
        raise ValueError("frozen protocol hash changed after v2 genesis")
    if event.get("snapshot_content_sha256") != sha256_bytes(
        canonical_bytes(event.get("snapshot"))
    ):
        raise ValueError("previous snapshot content hash mismatch")
    expected_legacy_hash = sha256_bytes(
        canonical_bytes(protocol["legacy_v1_genesis_reference"])
    )
    if event.get("legacy_v1_reference_sha256") != expected_legacy_hash:
        raise ValueError("previous legacy reference hash mismatch")
    claimed_hash = event.get("event_hash")
    unhashed = dict(event)
    unhashed.pop("event_hash", None)
    if claimed_hash != sha256_bytes(canonical_bytes(unhashed)):
        raise ValueError("previous event hash mismatch")
    parse_utc(str(event.get("event_time_utc", "")))


def compute_readiness(
    previous_event: dict[str, Any] | None,
    observed_at: datetime,
    horizons: list[int],
) -> dict[str, Any]:
    observed_date = observed_at.astimezone(timezone.utc).date().isoformat()
    if previous_event is None:
        first_date = observed_date
        last_date = observed_date
        observed_day_count = 1
    else:
        previous = previous_event["readiness"]
        first_date = previous["first_v2_observed_date_utc"]
        last_date = previous["last_v2_observed_date_utc"]
        if observed_date < last_date:
            raise ValueError("observation time would move v2 readiness backward")
        observed_day_count = int(previous["distinct_v2_observed_date_count"])
        if observed_date != last_date:
            observed_day_count += 1
            last_date = observed_date
    gates = {
        str(days): {
            "ready": observed_day_count >= days,
            "required_distinct_v2_dates": days,
            "remaining_distinct_v2_dates": max(0, days - observed_day_count),
        }
        for days in horizons
    }
    return {
        "basis": "distinct_utc_dates_with_v2_observations_only",
        "legacy_dates_credited": 0,
        "first_v2_observed_date_utc": first_date,
        "last_v2_observed_date_utc": last_date,
        "distinct_v2_observed_date_count": observed_day_count,
        "gates": gates,
    }


def make_event(
    protocol: dict[str, Any],
    snapshot: dict[str, Any],
    previous_event: dict[str, Any] | None,
    observed_at: datetime,
    *,
    collector_path: Path = Path(__file__).resolve(),
    task_script_path: Path = TASK_STAGING_SCRIPT,
) -> dict[str, Any]:
    sequence = 1 if previous_event is None else int(previous_event["sequence"]) + 1
    prior_hash = ZERO_HASH if previous_event is None else previous_event["event_hash"]
    if not HEX_64.fullmatch(prior_hash):
        raise ValueError("prior event hash is invalid")
    event = {
        "schema": "luma.local_system_health_event.v2",
        "record_type": "v2_genesis_observation" if sequence == 1 else "v2_observation",
        "sequence": sequence,
        "event_time_utc": iso_utc(observed_at),
        "prior_event_hash": prior_hash,
        "snapshot_content_sha256": sha256_bytes(canonical_bytes(snapshot)),
        "protocol_sha256": protocol["_protocol_sha256"],
        "collector_script_sha256": sha256_file(collector_path),
        "task_staging_script_sha256": sha256_file(task_script_path),
        "readiness": compute_readiness(
            previous_event,
            observed_at,
            protocol["readiness"]["horizons_observed_v2_dates"],
        ),
        "snapshot": snapshot,
    }
    legacy = protocol["legacy_v1_genesis_reference"]
    legacy_hash = sha256_bytes(canonical_bytes(legacy))
    event["legacy_v1_reference_sha256"] = legacy_hash
    if sequence == 1:
        event["legacy_v1_genesis_reference"] = legacy
    event["event_hash"] = sha256_bytes(canonical_bytes(event))
    return event


def append_event(path: Path, event: dict[str, Any]) -> None:
    encoded = canonical_bytes(event) + b"\n"
    with path.open("ab") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        with temporary.open("wb") as handle:
            handle.write(canonical_bytes(value) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def run_once(
    protocol_path: Path = DEFAULT_PROTOCOL_PATH,
    state_dir: Path = DEFAULT_STATE_DIR,
    *,
    now: datetime | None = None,
    snapshot_factory: Callable[[dict[str, Any], Path, dict[str, Any] | None, datetime], dict[str, Any]] = collect_snapshot,
    collector_path: Path = Path(__file__).resolve(),
    task_script_path: Path = TASK_STAGING_SCRIPT,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    state_dir.mkdir(parents=True, exist_ok=True)
    observed_at = (now or utc_now()).astimezone(timezone.utc)
    lock_path = state_dir / protocol["output_contract"]["single_writer_lock_filename"]
    with SingleWriterLock(lock_path):
        previous = read_last_event(state_dir, protocol)
        if previous:
            validate_event_integrity(previous, protocol)
        if previous and observed_at < parse_utc(previous["event_time_utc"]):
            raise ValueError("observation time is not monotonic")
        snapshot = snapshot_factory(protocol, state_dir, previous, observed_at)
        if snapshot.get("observed_at_utc") != iso_utc(observed_at):
            raise ValueError("snapshot time does not match event time")
        event = make_event(
            protocol,
            snapshot,
            previous,
            observed_at,
            collector_path=collector_path,
            task_script_path=task_script_path,
        )
        contract = protocol["output_contract"]
        date_token = observed_at.date().isoformat()
        segment = state_dir / f'{contract["daily_segment_prefix"]}{date_token}{contract["daily_segment_suffix"]}'
        append_event(segment, event)
        latest = {
            "schema": "luma.local_system_health_latest.v2",
            "segment_alias": segment.name,
            "event": event,
        }
        atomic_write_json(state_dir / contract["latest_filename"], latest)
        return event


def verify_chain(
    protocol_path: Path = DEFAULT_PROTOCOL_PATH,
    state_dir: Path = DEFAULT_STATE_DIR,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    expected_sequence = 1
    prior_hash = ZERO_HASH
    row_count = 0
    tail_hash = ZERO_HASH
    legacy_reference_hash = sha256_bytes(
        canonical_bytes(protocol["legacy_v1_genesis_reference"])
    )
    for path in segment_paths(state_dir, protocol):
        with path.open("rb") as handle:
            for raw_line in handle:
                if not raw_line.strip():
                    continue
                event = json.loads(raw_line)
                if event.get("sequence") != expected_sequence:
                    raise ValueError("non-monotonic sequence")
                if event.get("prior_event_hash") != prior_hash:
                    raise ValueError("prior event hash mismatch")
                if event.get("snapshot_content_sha256") != sha256_bytes(
                    canonical_bytes(event.get("snapshot"))
                ):
                    raise ValueError("snapshot content hash mismatch")
                if event.get("protocol_sha256") != protocol["_protocol_sha256"]:
                    raise ValueError("frozen protocol hash mismatch")
                if not HEX_64.fullmatch(str(event.get("collector_script_sha256", ""))):
                    raise ValueError("collector script hash is invalid")
                if not HEX_64.fullmatch(str(event.get("task_staging_script_sha256", ""))):
                    raise ValueError("task staging script hash is invalid")
                if event.get("legacy_v1_reference_sha256") != legacy_reference_hash:
                    raise ValueError("legacy reference hash mismatch")
                claimed = event.get("event_hash")
                unhashed = dict(event)
                unhashed.pop("event_hash", None)
                if claimed != sha256_bytes(canonical_bytes(unhashed)):
                    raise ValueError("event hash mismatch")
                if expected_sequence == 1:
                    if event.get("record_type") != "v2_genesis_observation":
                        raise ValueError("first record is not the v2 genesis")
                    if event.get("legacy_v1_genesis_reference") != protocol["legacy_v1_genesis_reference"]:
                        raise ValueError("v2 genesis legacy reference mismatch")
                prior_hash = claimed
                tail_hash = claimed
                expected_sequence += 1
                row_count += 1
    return {
        "status": "verified",
        "row_count": row_count,
        "tail_event_hash": tail_hash,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL_PATH)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--verify-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.verify_only:
            result = verify_chain(args.protocol, args.state_dir)
        else:
            event = run_once(args.protocol, args.state_dir)
            result = {
                "status": "recorded",
                "sequence": event["sequence"],
                "event_time_utc": event["event_time_utc"],
                "event_hash": event["event_hash"],
                "readiness": event["readiness"],
            }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except LockUnavailable:
        print('{"status":"skipped","reason":"collector_already_running"}')
        return 3
    except Exception as exc:
        print(
            json.dumps(
                {"status": "error", "error_type": type(exc).__name__},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
