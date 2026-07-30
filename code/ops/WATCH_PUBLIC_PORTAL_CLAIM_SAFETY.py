"""Repair stale public-portal claim language left by an older refresh worker.

This is a temporary compatibility guard for a long-running dashboard worker
that imported an older portal builder before the claim-safe template shipped.
Once that worker restarts, BUILD_ALL_PREMIUM_DASHBOARDS reloads the current
builder and this watcher is no longer needed.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
PORTAL_PATH = ROOT / "dashboard" / "dashboard_portal.html"
DEFAULT_STATUS_PATH = ROOT / "out" / "runtime" / "public_portal_claim_safety_watchdog.json"

STALE_MARKERS = (
    "Reviewer-Safe Winner State",
    "Current strongest family",
)
REQUIRED_MARKERS = (
    "No Current Performance Champion",
    "No performance, savings, field-validation, or autonomous-execution claim is authorized.",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def portal_needs_repair(text: str) -> bool:
    return any(marker in text for marker in STALE_MARKERS) or not all(
        marker in text for marker in REQUIRED_MARKERS
    )


def write_status(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def repair_if_needed(status_path: Path) -> bool:
    text = PORTAL_PATH.read_text(encoding="utf-8") if PORTAL_PATH.exists() else ""
    repaired = False
    error: str | None = None

    if portal_needs_repair(text):
        try:
            if str(CODE) not in sys.path:
                sys.path.insert(0, str(CODE))
            import BUILD_DASHBOARD_PORTAL as portal

            importlib.reload(portal)
            portal.main()
            repaired_text = PORTAL_PATH.read_text(encoding="utf-8")
            if portal_needs_repair(repaired_text):
                raise RuntimeError("current portal builder did not produce a claim-safe surface")
            repaired = True
        except Exception as exc:  # keep the guard alive through transient write races
            error = f"{type(exc).__name__}: {exc}"

    write_status(
        status_path,
        {
            "checked_utc": utc_now(),
            "process_id": os.getpid(),
            "portal_path": str(PORTAL_PATH),
            "repaired": repaired,
            "claim_safe": error is None
            and PORTAL_PATH.exists()
            and not portal_needs_repair(PORTAL_PATH.read_text(encoding="utf-8")),
            "error": error,
            "temporary_guard": True,
            "retirement_condition": (
                "Restart the SYSTEM dashboard_unified_refresh --loop worker so it imports "
                "the current BUILD_ALL_PREMIUM_DASHBOARDS module."
            ),
        },
    )
    return repaired


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--status-path", type=Path, default=DEFAULT_STATUS_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    while True:
        repair_if_needed(args.status_path)
        if args.once:
            return 0
        time.sleep(max(args.interval_seconds, 0.25))


if __name__ == "__main__":
    raise SystemExit(main())
