#!/usr/bin/env python3
"""Fail-closed paper orchestration for LumenCore market-data research.

The previous universal entrypoint mixed research orchestration with direct
private-exchange order transports. Repository history preserves that code for
forensic review. This canonical surface runs paper/research subprocesses only,
never loads exchange credentials, and rejects every request for live mode.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
CODE = Path(__file__).resolve().parent
RUNTIME_CONTROL_PATH = ROOT / "config" / "runtime_control.json"
PAPER_ONLY_POLICY = "live_order_submission_disabled"


def env_bool(name: str) -> bool | None:
    if name not in os.environ:
        return None
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def load_runtime_control() -> dict[str, Any]:
    try:
        value = json.loads(RUNTIME_CONTROL_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def live_mode_requested(args: argparse.Namespace, runtime: dict[str, Any]) -> bool:
    runtime_mode = str(runtime.get("mode", "paper") or "paper").strip().lower()
    runtime_allows_orders = runtime.get("allow_live_orders") is True
    return any(
        (
            args.live,
            args.force_live,
            env_bool("LIVE_MODE") is True,
            env_bool("FORCE_LIVE") is True,
            env_bool("PAPER_MODE") is False,
            runtime_mode == "live",
            runtime_allows_orders,
        )
    )


def run_step(path: Path, label: str, env: dict[str, str], *, required: bool) -> int:
    if not path.is_file():
        if required:
            print(f"[ORCH] REQUIRED_STEP_MISSING: {label}")
            return 3
        print(f"[ORCH] OPTIONAL_STEP_SKIPPED: {label}")
        return 0

    result = subprocess.run(
        [sys.executable, str(path)],
        cwd=str(CODE),
        env=env,
        check=False,
    )
    print(f"[ORCH] STEP_COMPLETE: {label} return_code={result.returncode}")
    return int(result.returncode)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--force-live", action="store_true")
    parser.add_argument("--audit-live-keys", action="store_true")
    parser.add_argument("--audit-credentials", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.audit_live_keys or args.audit_credentials:
        print("[ORCH] CREDENTIAL_AUDIT_BLOCKED: paper_entrypoint_loads_no_credentials")
        return 2

    runtime = load_runtime_control()
    if live_mode_requested(args, runtime):
        print(f"[ORCH] LIVE_REQUEST_BLOCKED: {PAPER_ONLY_POLICY}")
        print("[ORCH] This canonical entrypoint supports paper evidence only.")
        return 2

    env = os.environ.copy()
    env["PAPER_MODE"] = "true"
    env["LUMA_NO_LIVE_TRADES"] = "true"
    steps = (
        (CODE / "BUILD_ADAPTIVE_UNIVERSE_FROM_LIVE_KEYS.py", "adaptive_universe", False),
        (CODE / "CUTOVER_TO_ADAPTIVE_ENGINE_LOGIC.py", "adaptive_cutover", False),
        (CODE / "alpaca_paper_loop_builder.py", "alpaca_paper_evidence", True),
    )
    for path, label, required in steps:
        return_code = run_step(path, label, env, required=required)
        if return_code != 0:
            print(f"[ORCH] PAPER_PIPELINE_FAILED: {label} return_code={return_code}")
            return return_code

    print("[ORCH] PAPER_PIPELINE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
