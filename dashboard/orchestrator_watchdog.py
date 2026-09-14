"""Bounded log observations for the legacy dashboard, not process-health proof."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
LOG_NAMES = ("orchestrator_run_stdout.log", "orchestrator_run_stderr.log", "orchestrator_exceptions.log")
LOG_PATHS = [ROOT / "out/execution" / name for name in LOG_NAMES]
WATCHDOG_STATUS = ROOT / "dashboard/orchestrator_watchdog_status.txt"
STALL_THRESHOLD_MINUTES = 5
ERROR_THRESHOLD = 3
MAX_TAIL_BYTES = 64 * 1024
CLOCK_TOLERANCE_SECONDS = 2


def _tail_lines(path, max_lines=100):
    with Path(path).open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        start = max(0, size - MAX_TAIL_BYTES)
        stream.seek(start)
        content = stream.read(MAX_TAIL_BYTES)
    # A tail read can begin mid-record. Do not classify that partial record.
    if start:
        content = content.partition(b"\n")[2]
    return content.decode("utf-8", errors="replace").splitlines()[-max_lines:]


def get_last_line(path):
    try:
        lines = _tail_lines(path, 1)
        return lines[-1] if lines else None
    except OSError:
        return None


def get_last_mod_time(path):
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime, timezone.utc)
    except OSError:
        return None


def assess_logs(log_paths=None, *, now=None):
    checked = now or datetime.now(timezone.utc)
    if not isinstance(checked, datetime) or checked.tzinfo is None:
        raise ValueError("Log observation timestamp must be timezone-aware")
    checked = checked.astimezone(timezone.utc)
    issues, logs = [], []
    for path in (LOG_PATHS if log_paths is None else log_paths):
        path = Path(path)
        is_stdout = path.name == LOG_NAMES[0]
        row = {"name": path.name, "available": False, "kind": "activity" if is_stdout else "error",
               "tail_indicator_count": 0, "tail_bytes_limit": MAX_TAIL_BYTES}
        try:
            metadata = path.stat()
            if not path.is_file() or path.is_symlink():
                raise OSError("Not a direct regular log file")
            age = checked.timestamp() - metadata.st_mtime
            if not math.isfinite(age):
                raise ValueError("Log age must be finite")
            row.update({"available": True, "bytes": metadata.st_size, "age_seconds": age,
                        "modified_utc": datetime.fromtimestamp(metadata.st_mtime, timezone.utc).isoformat()})
            if age < -CLOCK_TOLERANCE_SECONDS:
                issues.append(f"Future modification time observed: {path.name}; clock order is unverified")
            if is_stdout:
                if not metadata.st_size:
                    issues.append(f"Activity log is empty: {path.name}; successful work is unverified")
                elif age > STALL_THRESHOLD_MINUTES * 60:
                    issues.append(f"Activity log is stale: {path.name}; this does not establish a stalled process")
            else:
                lines = _tail_lines(path)
                indicators = sum("error" in line.lower() or "exception" in line.lower() for line in lines)
                row["tail_indicator_count"] = indicators
                row["tail_lines_observed"] = len(lines)
                if 0 <= age <= STALL_THRESHOLD_MINUTES * 60 and indicators >= ERROR_THRESHOLD:
                    issues.append(f"Error indicators in a recently modified log tail: {path.name} ({indicators} lines); event rate is unverified")
                # A quiet or absent error log is not a stalled execution signal.
        except OSError:
            row["available"] = False
            row["observation"] = "missing_or_unreadable"
            if is_stdout:
                issues.append(f"Activity log unavailable: {path.name}; runtime state is unknown")
        logs.append(row)
    return {
        "schema": "lumencore.bounded_log_observation.v2",
        "checked_utc": checked.isoformat(),
        "scope": "bounded_log_observations_only",
        "state": "LOG_ISSUES_REPORTED" if issues else "LOG_OBSERVATIONS_ONLY",
        "runtime_health_verified": False, "restart_authorized": False,
        "issues": issues, "logs": logs,
        "boundary": "File activity and tail indicators do not prove process identity, heartbeat continuity, successful work, or recovery.",
    }


def render_status(report):
    lines = [
        "# Orchestrator Log Observation",
        f"Checked: {report['checked_utc']}",
        f"State: {report['state']}",
        "Runtime health: UNVERIFIED; restart authorization: FALSE",
        report["boundary"],
    ]
    for row in report["logs"]:
        if row["available"]:
            lines.append(f"{row['name']}: modified {row['modified_utc']}; age {row['age_seconds']:.1f}s; tail indicators {row['tail_indicator_count']}")
        else:
            lines.append(f"{row['name']}: not observed or unreadable")
    if report["issues"]:
        lines.append("ISSUES DETECTED:")
        lines.extend(report["issues"])
    else:
        lines.append("No log issues detected within this bounded observation; process health remains unverified.")
    return "\n".join(lines) + "\n"


def _write_atomic(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path, help="Optional structured copy of the same log observation")
    args = parser.parse_args(argv)
    paths = LOG_PATHS if args.root == ROOT else [args.root / "out/execution" / name for name in LOG_NAMES]
    output = args.output or (WATCHDOG_STATUS if args.root == ROOT else args.root / "dashboard/orchestrator_watchdog_status.txt")
    report = assess_logs(paths)
    _write_atomic(output, render_status(report))
    if args.json_output:
        _write_atomic(args.json_output, json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Log observation complete: {report['state']}; runtime health unverified, restart not authorized.")
    return 2 if report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
