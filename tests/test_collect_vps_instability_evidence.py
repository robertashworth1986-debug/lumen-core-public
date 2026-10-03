import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code/ops/COLLECT_VPS_INSTABILITY_EVIDENCE.py"
SPEC = importlib.util.spec_from_file_location("collect_vps_instability", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
END = dt.datetime(2026, 10, 4, tzinfo=dt.timezone.utc)
START = END - dt.timedelta(days=1)


def record(timestamp, message):
    return json.dumps({"__REALTIME_TIMESTAMP": str(int(timestamp.timestamp() * 1e6)), "MESSAGE": message}).encode() + b"\n"


def summary(data, status="read_success", source="kernel_journal"):
    return MODULE.summarize_records(data, journal=True, start=START, end=END, status=status, source=source)


def test_only_in_window_counts_and_event_times_are_published():
    message = "Out of memory: Killed process 123 private-command token=secret-value"
    data = record(START - dt.timedelta(seconds=1), message)
    data += record(START + dt.timedelta(hours=3), message)
    data += record(START + dt.timedelta(hours=5), message)
    data += record(END + dt.timedelta(seconds=1), message)
    result = summary(data)
    assert result["records_in_window"] == 2
    assert result["signatures"]["oom_kill"] == {"count": 2, "first_utc": "2026-10-03T03:00:00Z", "last_utc": "2026-10-03T05:00:00Z"}
    assert "private-command" not in json.dumps(result)
    assert "secret-value" not in json.dumps(result)


def test_request_metadata_cannot_inject_an_outage_signature():
    data = record(START, 'open() failed, client: private-ip, request: "GET /upstream timed out?token=secret"')
    result = summary(data, source="nginx_journal")
    assert all(item["count"] == 0 for item in result["signatures"].values())
    assert "private-ip" not in json.dumps(result)
    assert "token" not in json.dumps(result)


def test_uri_derived_filename_cannot_inject_an_outage_signature():
    messages = [
        '[error] 1#1: *1 open() "/usr/share/nginx/html/upstream timed out" failed (2: No such file or directory), client: private-ip',
        '[error] 1#1: *1 open() "/usr/share/nginx/html/too many open files" failed (2: No such file or directory), client: private-ip',
        '[error] 1#1: *1 open() "/usr/share/nginx/html/upstream prematurely closed connection while reading" failed (2: No such file or directory), client: private-ip',
    ]
    result = summary(b"".join(record(START, message) for message in messages), source="nginx_journal")
    assert all(item["count"] == 0 for item in result["signatures"].values())
    assert "private-ip" not in json.dumps(result)


def test_genuine_nginx_errors_and_systemd_events_still_count():
    messages = [
        '[error] 1#1: *1 upstream timed out (110: Connection timed out) while reading response header from upstream, client: private-ip',
        '[error] 1#1: *1 upstream prematurely closed connection while reading response header from upstream, client: private-ip',
        '[alert] 1#1: socket() failed (24: Too many open files)',
        '[emerg] 1#1: open() "/private/path" failed (28: No space left on device)',
        '[alert] 1#1: worker process 123 exited on signal 9',
        "nginx.service: Failed with result 'exit-code'.",
    ]
    result = summary(b"".join(record(START, message) for message in messages), source="nginx_journal")
    assert result["signatures"]["upstream_timeout"]["count"] == 1
    assert result["signatures"]["upstream_closed"]["count"] == 1
    assert result["signatures"]["resource_exhaustion"]["count"] == 2
    assert result["signatures"]["worker_exit"]["count"] == 1
    assert result["signatures"]["service_failed"]["count"] == 1
    assert "private" not in json.dumps(result)


def test_signatures_are_specific_to_the_observed_source():
    result = summary(record(START, "Out of memory: Killed process 123"), source="nginx_journal")
    assert result["signatures"]["oom_kill"]["count"] == 0


def test_nginx_prefix_uses_local_log_time_and_hides_request():
    local_time = START.astimezone().strftime("%Y/%m/%d %H:%M:%S")
    data = (local_time + ' [error] 1#1: connect() failed (111: Connection refused) while connecting to upstream, client: private-ip, request: "GET /?secret=yes"\n').encode()
    result = MODULE.summarize_records(data, journal=False, start=START, end=END, status="read_success", source="nginx_error_current")
    assert result["signatures"]["upstream_connection_refused"]["count"] == 1
    assert result["first_record_utc"] == MODULE.utc(START)
    assert "secret" not in json.dumps(result)


def test_unavailable_malformed_and_limited_history_stay_visible(monkeypatch):
    assert summary(b"", "unavailable")["collection_status"] == "unavailable"
    malformed = b'{"MESSAGE":"secret","__REALTIME_TIMESTAMP":null}\n'
    assert summary(malformed)["unparsed_records"] == 1
    monkeypatch.setattr(MODULE, "MAX_RECORDS", 2)
    result = summary(record(START, "upstream timed out") * 3)
    assert result["collection_status"] == "record_limit"
    assert result["records_in_window"] == 2
    assert result["coverage"] == "bounded_tail_not_complete_history"


def test_reader_refuses_symlinks_and_bounds_tail(tmp_path, monkeypatch):
    source = tmp_path / "error.log"
    source.write_bytes(b"old line\n" + b"retained line\n")
    link = tmp_path / "alias"
    link.symlink_to(source)
    assert MODULE.bounded_log(str(link)) == (b"", "unavailable")
    monkeypatch.setattr(MODULE, "MAX_BYTES", 15)
    data, status = MODULE.bounded_log(str(source))
    assert status == "byte_limit"
    assert len(data) <= 15
    assert data == b"retained line\n"


def test_command_reader_has_byte_and_time_limits(monkeypatch):
    monkeypatch.setattr(MODULE, "MAX_BYTES", 32)
    data, status = MODULE.bounded_command([sys.executable, "-c", "print('x' * 100)"])
    assert status == "byte_limit"
    assert len(data) <= 32
    monkeypatch.setattr(MODULE, "COMMAND_SECONDS", 0.05)
    _, status = MODULE.bounded_command([sys.executable, "-c", "import time; time.sleep(1)"])
    assert status == "time_limit"


def test_collector_uses_only_fixed_read_sources(monkeypatch):
    commands, paths = [], []
    monkeypatch.setattr(MODULE, "bounded_command", lambda command: (commands.append(command) or b"", "unavailable"))
    monkeypatch.setattr(MODULE, "bounded_log", lambda path: (paths.append(path) or b"", "unavailable"))
    monkeypatch.setattr(MODULE, "memory_snapshot", lambda: {"collection_status": "unavailable"})
    result = MODULE.collect()
    assert len(commands) == 3
    assert all(command[0] == "journalctl" for command in commands)
    assert "_TRANSPORT=kernel" in commands[0]
    assert all("--dmesg" not in command for command in commands)
    assert paths == ["/var/log/nginx/error.log", "/var/log/nginx/error.log.1"]
    assert all("--lines=10001" in command for command in commands)
    assert all("--output-fields=__REALTIME_TIMESTAMP,MESSAGE" in command for command in commands)
    assert result["schema"] == MODULE.SCHEMA
    assert "No matches does not establish sustained availability" in result["claim_boundary"]
