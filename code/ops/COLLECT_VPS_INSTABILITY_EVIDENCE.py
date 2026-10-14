#!/usr/bin/env python3
"""Read-only, bounded origin evidence; never emit journal or request text.

Runs through SSH stdin using the system Python standard library. Fixed paths
and commands only. Zero signature counts are not proof of an outage-free day:
journal retention, rotated logs, byte limits and collection gaps are explicit.
"""

import datetime as dt
import json
import os
import re
import select
import stat
import subprocess
import time

SCHEMA = "lumencore.vps_instability_evidence.v1"
MAX_BYTES = 2 * 1024 * 1024
MAX_ERROR_BYTES = 4096
MAX_RECORDS = 10000
COMMAND_SECONDS = 15
MEMORY_KEYS = ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree")
SIGNATURES = {
    "oom_kill": r"^(?:out of memory:|oom-kill:|killed process \d+\b|memory cgroup out of memory:)",
    "upstream_connection_refused": r"^connect\(\) failed \(111: connection refused\) while connecting to upstream\b",
    "upstream_timeout": r"^upstream timed out \(\d+: [^)]+\) while ",
    "upstream_closed": r"^upstream prematurely closed connection while ",
    "resource_exhaustion": r"^(?:worker_connections are not enough\b|(?:open|openat|socket|accept|accept4|epoll_create|pipe|write|writev|sendfile|malloc|calloc)\(\)(?: \[quoted\])? failed \((?:12: cannot allocate memory|24: too many open files|28: no space left on device)\)|(?:OSError|MemoryError): \[Errno (?:12|24|28)\])",
    "worker_exit": r"^worker process \d+ exited on signal\b",
    "service_failed": r"^(?:main process exited\b|failed with result\b|start request repeated too quickly\b|failed at step\b)",
    "service_started": r"^started |^starting ",
}
SOURCE_SIGNATURES = {
    "kernel_journal": {"oom_kill"},
    "nginx_journal": set(SIGNATURES) - {"oom_kill"},
    "gateway_journal": {"service_failed", "service_started", "resource_exhaustion"},
    "nginx_error_current": {"upstream_connection_refused", "upstream_timeout", "upstream_closed", "resource_exhaustion", "worker_exit"},
    "nginx_error_previous": {"upstream_connection_refused", "upstream_timeout", "upstream_closed", "resource_exhaustion", "worker_exit"},
}


def diagnostic_message(message):
    """Recognize diagnostic prefixes; quoted operands cannot create signatures."""
    message = message.split(", client:", 1)[0].split(", request:", 1)[0]
    message = re.sub(r'^\s*\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\s+', '', message)
    message = re.sub(r'^\s*(?:nginx: )?\[(?:emerg|alert|crit|error|warn|notice|info|debug)\]\s*(?:\d+#\d+:\s*(?:\*\d+\s*)?)?', '', message)
    message = re.sub(r'^(?:nginx|luma-gateway)\.service:\s*', '', message)
    return re.sub(r'"(?:\\.|[^"\\])*"', '[quoted]', message).strip()


def utc(value):
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def journal_time(value):
    # Older systemd parsers require spaces and an explicit UTC suffix rather
    # than the ISO T/Z form used in our JSON receipt.
    return value.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def command_error(data):
    """Classify a bounded stderr prefix; never return its text or operands."""
    message = data.decode("utf-8", errors="replace").lower()
    if "failed to parse timestamp" in message:
        return "invalid_time"
    if any(term in message for term in ("unrecognized option", "unknown option", "invalid option")):
        return "unsupported_option"
    if "permission denied" in message or "operation not permitted" in message:
        return "permission_denied"
    if "no journal files" in message or "failed to open" in message:
        return "journal_unavailable"
    return "command_failed"


def bounded_command(command):
    """Limit elapsed time and bytes without printing command output or errors."""
    data = bytearray()
    error_data = bytearray()
    error_reason = None
    status = "read_success"
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(os.environ, LC_ALL="C"))
    except OSError:
        return b"", "unavailable", "command_unavailable"
    deadline = time.monotonic() + COMMAND_SECONDS
    pending = [process.stdout, process.stderr]
    try:
        while pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                status = "time_limit"
                break
            ready, _, _ = select.select(pending, [], [], remaining)
            if not ready:
                status = "time_limit"
                break
            for stream in ready:
                target = data if stream is process.stdout else error_data
                limit = MAX_BYTES if stream is process.stdout else MAX_ERROR_BYTES
                chunk = os.read(stream.fileno(), min(65536, limit + 1 - len(target)))
                if not chunk:
                    pending.remove(stream)
                    continue
                target.extend(chunk)
                if len(target) > limit:
                    status = "byte_limit"
                    error_reason = "stderr_limit" if stream is process.stderr else "stdout_limit"
                    break
            if status != "read_success":
                break
        if status != "read_success":
            process.kill()
        code = None
        try:
            code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            status = "time_limit"
        if code != 0 and status == "read_success":
            status = "unavailable"
            error_reason = command_error(error_data)
        elif status == "time_limit":
            error_reason = "time_limit"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()
    # Discard an incomplete last record instead of parsing partial data.
    if status != "read_success":
        data = data[:data.rfind(b"\n") + 1]
    return bytes(data[:MAX_BYTES]), status, error_reason


def bounded_log(path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            metadata = os.fstat(handle.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                return b"", "unavailable"
            limited = metadata.st_size > MAX_BYTES
            handle.seek(max(0, metadata.st_size - MAX_BYTES))
            data = handle.read(MAX_BYTES)
            if limited:
                data = data.split(b"\n", 1)[-1] if b"\n" in data else b""
            return data, "byte_limit" if limited else "read_success"
    except OSError:
        return b"", "unavailable"


def summarize_records(data, *, journal, start, end, status, source):
    result = {
        "collection_status": status,
        "coverage": "bounded_tail_not_complete_history",
        "records_in_window": 0,
        "unparsed_records": 0,
        "first_record_utc": None,
        "last_record_utc": None,
        "signatures": {key: {"count": 0, "first_utc": None, "last_utc": None} for key in SIGNATURES},
    }
    lines = data.decode("utf-8", errors="replace").splitlines()
    if len(lines) > MAX_RECORDS:
        result["collection_status"] = "record_limit"
        lines = lines[-MAX_RECORDS:]
    for line in lines:
        try:
            if journal:
                record = json.loads(line)
                timestamp = dt.datetime.fromtimestamp(int(record["__REALTIME_TIMESTAMP"]) / 1e6, dt.timezone.utc)
                message = record["MESSAGE"]
                if not isinstance(message, str):
                    raise ValueError("nontext")
            else:
                timestamp = dt.datetime.strptime(line[:19], "%Y/%m/%d %H:%M:%S").astimezone(dt.timezone.utc)
                message = line[19:]
        except (ValueError, KeyError, TypeError, OverflowError, OSError):
            result["unparsed_records"] += 1
            continue
        if not start <= timestamp <= end:
            continue
        stamp = utc(timestamp)
        result["records_in_window"] += 1
        result["first_record_utc"] = min(result["first_record_utc"] or stamp, stamp)
        result["last_record_utc"] = max(result["last_record_utc"] or stamp, stamp)
        message = diagnostic_message(message)
        for key, pattern in SIGNATURES.items():
            if key in SOURCE_SIGNATURES.get(source, set()) and re.search(pattern, message, re.IGNORECASE):
                item = result["signatures"][key]
                item["count"] += 1
                item["first_utc"] = min(item["first_utc"] or stamp, stamp)
                item["last_utc"] = max(item["last_utc"] or stamp, stamp)
    return result


def memory_snapshot():
    result = {"collection_status": "unavailable", "memory_kib": {}, "oom_kill_since_boot": None}
    try:
        with open("/proc/meminfo", encoding="ascii") as handle:
            for line in handle.read(16384).splitlines():
                match = re.fullmatch(r"([A-Za-z_]+):\s+(\d+) kB", line)
                if match and match.group(1) in MEMORY_KEYS:
                    result["memory_kib"][match.group(1)] = int(match.group(2))
        result["collection_status"] = "read_success" if len(result["memory_kib"]) == len(MEMORY_KEYS) else "partial"
    except OSError:
        pass
    try:
        with open("/proc/vmstat", encoding="ascii") as handle:
            match = re.search(r"^oom_kill (\d+)$", handle.read(32768), re.MULTILINE)
            result["oom_kill_since_boot"] = int(match.group(1)) if match else None
    except OSError:
        pass
    return result


def collect():
    end = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    start = end - dt.timedelta(hours=24)
    sources = {}
    # A transport match includes retained previous boots; journalctl --dmesg
    # would silently restrict this diagnostic to the current boot.
    for name, selector in (("kernel_journal", ["_TRANSPORT=kernel"]), ("nginx_journal", ["--unit=nginx"]), ("gateway_journal", ["--unit=luma-gateway"])):
        command = ["journalctl", *selector, "--since=" + journal_time(start), "--until=" + journal_time(end), "--no-pager", "--output=json", "--output-fields=__REALTIME_TIMESTAMP,MESSAGE", "--lines=" + str(MAX_RECORDS + 1)]
        data, status, error_reason = bounded_command(command)
        sources[name] = summarize_records(data, journal=True, start=start, end=end, status=status, source=name)
        sources[name]["collection_error"] = error_reason
    for name, path in (("nginx_error_current", "/var/log/nginx/error.log"), ("nginx_error_previous", "/var/log/nginx/error.log.1")):
        data, status = bounded_log(path)
        sources[name] = summarize_records(data, journal=False, start=start, end=end, status=status, source=name)
    return {
        "schema": SCHEMA,
        "observed_at_utc": utc(end),
        "requested_window_start_utc": utc(start),
        "requested_window_end_utc": utc(end),
        "bounds": {"bytes_per_source": MAX_BYTES, "stderr_bytes_per_command": MAX_ERROR_BYTES, "records_per_source": MAX_RECORDS, "seconds_per_command": COMMAND_SECONDS},
        "memory": memory_snapshot(),
        "sources": sources,
        "claim_boundary": "Signature counts are observations, not a root-cause finding. Sources can overlap; do not sum them. Journal retention and fixed current/previous error logs may not cover the requested day. Compressed or custom-path logs are not read. No matches does not establish sustained availability. Memory is a current snapshot; the OOM counter is cumulative since boot.",
    }


if __name__ == "__main__":
    print(json.dumps(collect(), sort_keys=True))
