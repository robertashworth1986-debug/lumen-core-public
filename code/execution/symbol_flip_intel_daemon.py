from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analyze_symbol_flip_windows import (
    OUTPUT_INTEL_JSON,
    OUTPUT_JSON,
    OUTPUT_MD,
    _build_markdown,
    analyze,
)

STATUS_FILE = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\out\execution\symbol_flip_intel_daemon_status.json")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_status(payload: dict[str, Any]) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_once(
    interval_minutes: int,
    ledger_tail: int,
    exclude_stablecoins: bool,
    action_min_long_flip_pct: float,
    action_min_range_pct: float,
    action_top_n: int,
) -> dict[str, Any]:
    started_utc = now_utc()
    payload = analyze(
        interval_minutes=max(int(interval_minutes), 1),
        ledger_tail=max(int(ledger_tail), 50),
        exclude_stablecoins=bool(exclude_stablecoins),
        action_min_long_flip_pct=max(float(action_min_long_flip_pct), 0.0),
        action_min_range_pct=max(float(action_min_range_pct), 0.0),
        action_top_n=max(int(action_top_n), 1),
    )

    intel_payload = payload.get("intel", {}) if isinstance(payload.get("intel", {}), dict) else {}

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(payload), encoding="utf-8")
    OUTPUT_INTEL_JSON.write_text(json.dumps(intel_payload, indent=2), encoding="utf-8")

    focus_symbols = intel_payload.get("focus_symbols", []) if isinstance(intel_payload, dict) else []
    if not isinstance(focus_symbols, list):
        focus_symbols = []

    status = {
        "status": "ok",
        "started_utc": started_utc,
        "finished_utc": now_utc(),
        "symbol_count": int(payload.get("symbol_count", 0) or 0),
        "focus_symbols": [str(s).upper().strip() for s in focus_symbols if str(s).strip()],
        "output_json": str(OUTPUT_JSON.as_posix()),
        "output_markdown": str(OUTPUT_MD.as_posix()),
        "output_intel_json": str(OUTPUT_INTEL_JSON.as_posix()),
    }
    _write_status(status)
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description="Continuously refresh symbol flip intelligence artifacts.")
    parser.add_argument("--refresh-seconds", type=float, default=240.0, help="Seconds between refresh cycles.")
    parser.add_argument("--interval-minutes", type=int, default=5, help="Kraken OHLC interval minutes.")
    parser.add_argument("--ledger-tail", type=int, default=3000, help="Recent live ledger rows to inspect.")
    parser.add_argument("--exclude-stablecoins", action="store_true", default=True, help="Exclude stable symbols from actionable ranks.")
    parser.add_argument("--include-stablecoins", action="store_true", help="Include stable symbols.")
    parser.add_argument("--action-min-long-flip-pct", type=float, default=2.2, help="Actionable long flip threshold.")
    parser.add_argument("--action-min-range-pct", type=float, default=3.2, help="Actionable 72h range threshold.")
    parser.add_argument("--action-top-n", type=int, default=5, help="Candidates per side to keep.")
    parser.add_argument("--run-once", action="store_true", help="Run one refresh cycle then exit.")
    args = parser.parse_args()

    exclude_stablecoins = bool(args.exclude_stablecoins)
    if args.include_stablecoins:
        exclude_stablecoins = False

    if args.run_once:
        status = run_once(
            interval_minutes=args.interval_minutes,
            ledger_tail=args.ledger_tail,
            exclude_stablecoins=exclude_stablecoins,
            action_min_long_flip_pct=args.action_min_long_flip_pct,
            action_min_range_pct=args.action_min_range_pct,
            action_top_n=args.action_top_n,
        )
        print(json.dumps(status, indent=2))
        return

    while True:
        try:
            status = run_once(
                interval_minutes=args.interval_minutes,
                ledger_tail=args.ledger_tail,
                exclude_stablecoins=exclude_stablecoins,
                action_min_long_flip_pct=args.action_min_long_flip_pct,
                action_min_range_pct=args.action_min_range_pct,
                action_top_n=args.action_top_n,
            )
            print(json.dumps(status, indent=2))
        except Exception as exc:
            fail = {
                "status": "error",
                "timestamp_utc": now_utc(),
                "error": str(exc),
            }
            _write_status(fail)
            print(json.dumps(fail, indent=2))

        sleep_sec = max(float(args.refresh_seconds), 10.0)
        time.sleep(sleep_sec)


if __name__ == "__main__":
    main()
