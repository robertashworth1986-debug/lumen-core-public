import time
import os
from pathlib import Path
import datetime

# Paths to monitor
LOG_PATHS = [
    Path('out/execution/orchestrator_run_stdout.log'),
    Path('out/execution/orchestrator_run_stderr.log'),
    Path('out/execution/orchestrator_exceptions.log'),
]

WATCHDOG_STATUS = Path('dashboard/orchestrator_watchdog_status.txt')

# Configurable thresholds
STALL_THRESHOLD_MINUTES = 5
ERROR_THRESHOLD = 3


def get_last_line(path):
    if not path.exists():
        return None
    with open(path, 'rb') as f:
        try:
            f.seek(-512, os.SEEK_END)
        except OSError:
            f.seek(0)
        lines = f.readlines()
        if lines:
            return lines[-1].decode(errors='ignore').strip()
    return None

def get_last_mod_time(path):
    if not path.exists():
        return None
    return datetime.datetime.fromtimestamp(path.stat().st_mtime)

def main():
    now = datetime.datetime.utcnow()
    status = []
    issues = []
    for log in LOG_PATHS:
        last_mod = get_last_mod_time(log)
        if last_mod:
            delta = (now - last_mod).total_seconds() / 60
            if delta > STALL_THRESHOLD_MINUTES:
                issues.append(f'Stall detected in {log.name} (last update {delta:.1f} min ago)')
            status.append(f'{log.name}: last update {last_mod} UTC ({delta:.1f} min ago)')
        else:
            issues.append(f'{log.name} missing')
    # Check for repeated errors
    error_count = 0
    for log in LOG_PATHS:
        if 'stderr' in log.name or 'exceptions' in log.name:
            if log.exists():
                with open(log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()[-100:]
                    error_count += sum(1 for l in lines if 'error' in l.lower() or 'exception' in l.lower())
    if error_count >= ERROR_THRESHOLD:
        issues.append(f'High error rate detected: {error_count} errors/exceptions in recent logs')
    # Write status
    with open(WATCHDOG_STATUS, 'w', encoding='utf-8') as f:
        f.write('# Orchestrator Watchdog Status\n')
        f.write(f'Checked: {now} UTC\n')
        for s in status:
            f.write(s + '\n')
        if issues:
            f.write('ISSUES DETECTED:\n')
            for i in issues:
                f.write(i + '\n')
        else:
            f.write('No issues detected.\n')
    print('Watchdog check complete. Issues:', issues)

if __name__ == '__main__':
    main()
