#!/usr/bin/env python3
"""Interactive-only emergency liquidation facade.

The historical implementation is preserved in LIQUIDATE_ALL_TO_USD_legacy.py.
Live use requires an exact command-line phrase, an operator reason, a real TTY,
and a second exact typed confirmation. Dry-run remains available without them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, TextIO

CONFIRM_PHRASE = "LIQUIDATE_ALL_TO_USD"
MIN_REASON_LENGTH = 8


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_manual_emergency_confirmation(
    *,
    execute: bool,
    confirm: str,
    reason: str,
    stdin: TextIO,
    prompt: Callable[[str], str] = input,
) -> dict[str, object]:
    if not execute:
        return {"authorized": False, "execute": False, "reason": "dry_run"}

    clean_reason = str(reason or "").strip()
    if str(confirm or "").strip() != CONFIRM_PHRASE:
        raise RuntimeError(f"--execute requires --confirm {CONFIRM_PHRASE}")
    if len(clean_reason) < MIN_REASON_LENGTH:
        raise RuntimeError(f"--reason must contain at least {MIN_REASON_LENGTH} characters")
    if not bool(getattr(stdin, "isatty", lambda: False)()):
        raise RuntimeError("live emergency liquidation is interactive-only; daemon, pipe, scheduler, and CI use are blocked")
    typed = prompt(f"Type {CONFIRM_PHRASE} again to authorize immediate market sells: ")
    if str(typed or "").strip() != CONFIRM_PHRASE:
        raise RuntimeError("interactive emergency confirmation did not match")

    material = {
        "authorized_utc": _utc_now(),
        "scope": "manual_emergency_liquidation_to_usd",
        "reason": clean_reason,
        "interactive_terminal": True,
        "command_line_confirmation": True,
        "interactive_confirmation": True,
    }
    digest = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    return {**material, "authorized": True, "execute": True, "authorization_sha256": digest}


def _append_authorization(record: dict[str, object]) -> Path:
    root = Path(os.environ.get("LUMA_STACK_ROOT", r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")).expanduser()
    path = root / "out" / "ops" / "emergency_liquidation_authorizations.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True, default=str) + "\n")
    return path


def _load_authorized_legacy():
    code_dir = Path(__file__).resolve().parents[1]
    if str(code_dir) not in sys.path:
        sys.path.insert(0, str(code_dir))
    import kraken_execution_legacy as kraken_legacy
    from ops import LIQUIDATE_ALL_TO_USD_legacy as liquidate_legacy

    # The only live-order exception in the current no-orders lane. Rebinding is
    # delayed until after the interactive authorization gate succeeds.
    liquidate_legacy._private_post = kraken_legacy._private_post
    liquidate_legacy.arm_deadman_switch = kraken_legacy.arm_deadman_switch
    liquidate_legacy.get_balance = kraken_legacy.get_balance
    return liquidate_legacy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dry-run or manually authorize emergency Kraken liquidation")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--include-fiat", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--reason", default="")
    args = parser.parse_args(argv)

    try:
        authorization = require_manual_emergency_confirmation(
            execute=bool(args.execute),
            confirm=str(args.confirm),
            reason=str(args.reason),
            stdin=sys.stdin,
        )
    except RuntimeError as exc:
        parser.error(str(exc))

    if args.execute:
        ledger = _append_authorization(authorization)
        print(json.dumps({
            "status": "manual_emergency_authorized",
            "authorization_sha256": authorization["authorization_sha256"],
            "authorization_ledger": str(ledger),
        }, indent=2))

    legacy = _load_authorized_legacy()
    legacy_args: list[str] = []
    if args.execute:
        legacy_args.append("--execute")
    if args.include_fiat:
        legacy_args.append("--include-fiat")

    original_argv = list(sys.argv)
    sys.argv = [Path(legacy.__file__).name, *legacy_args]
    try:
        legacy.main()
    finally:
        sys.argv = original_argv
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
