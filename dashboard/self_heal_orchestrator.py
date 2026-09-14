"""Retired legacy restart entry point.

A dashboard status phrase cannot authorize starting the full stack. Inspect the
existing runtime manager instead: code/ops/MANAGE_LOCAL_STACK.ps1 -Action status.
This module never launches a process, alters runtime controls, or writes a
successful-recovery record.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REASON = (
    "Legacy automatic restart is retired: log observations do not establish "
    "process failure or restart authority. Inspect the existing runtime manager "
    "with code/ops/MANAGE_LOCAL_STACK.ps1 -Action status before a governed runtime change."
)


def restart_orchestrator():
    """Fail closed for callers that still import the former launch wrapper."""
    raise RuntimeError(REASON)


def main():
    print(REASON, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
