import os
import time
from pathlib import Path

# Self-healing: restart orchestrator if watchdog detects a stall or error
WATCHDOG_STATUS = Path('dashboard/orchestrator_watchdog_status.txt')
ORCH_LAUNCH_SCRIPT = Path('launch_all_engines.ps1')
RESTART_LOG = Path('dashboard/self_heal_log.txt')

CHECK_INTERVAL = 300  # seconds (5 min)


def restart_orchestrator():
    # This assumes PowerShell launch script is in workspace root
    os.system(f'powershell -ExecutionPolicy Bypass -File "{ORCH_LAUNCH_SCRIPT}"')
    with open(RESTART_LOG, 'a') as f:
        f.write(f'Restarted orchestrator at {time.ctime()}\n')

def main():
    while True:
        if WATCHDOG_STATUS.exists():
            txt = WATCHDOG_STATUS.read_text()
            if "ISSUES DETECTED" in txt:
                restart_orchestrator()
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
