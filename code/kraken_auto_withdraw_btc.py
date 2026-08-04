"""Manually gated BTC withdrawal utility.

This legacy script used to sweep every available BTC balance on execution. It
now has no exchange side effects by default and cannot submit a withdrawal
without an exact amount, an explicit confirmation, a fully live runtime, and
a private human action-time approval token.
"""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = Path(__file__).resolve().parent
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

from execution.live_runtime_guard import LiveRuntimeGuard


CONFIRMATION_PHRASE = "CONFIRM_CONFIGURED_BTC_WITHDRAWAL"
HUMAN_APPROVAL_ENV = "LUMA_HUMAN_UNLOCK_TOKEN"
DESTINATION_ENV = "KRAKEN_BTC_WITHDRAW_ADDRESS"
API_KEY_ENV = "KRAKEN_API_KEY"
API_SECRET_ENV = "KRAKEN_API_SECRET"


def parse_amount(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise argparse.ArgumentTypeError("amount must be a positive decimal BTC value") from exc
    if not amount.is_finite() or amount <= 0:
        raise argparse.ArgumentTypeError("amount must be a positive decimal BTC value")
    return amount


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Manually gated BTC withdrawal utility")
    command.add_argument("--execute", action="store_true", help="allow a withdrawal request after every gate passes")
    command.add_argument("--amount", type=parse_amount, help="exact BTC amount to request; balance sweeps are disabled")
    command.add_argument("--confirmation", default="", help=f"must equal {CONFIRMATION_PHRASE}")
    return command


def fully_live_runtime(root: Path) -> bool:
    runtime = LiveRuntimeGuard(root).load()
    return (
        runtime.get("mode") == "live"
        and bool(runtime.get("allow_live_orders"))
        and not bool(runtime.get("paper_enabled"))
        and not bool(runtime.get("kill_switch"))
    )


def execution_block_reason(args: argparse.Namespace, environ: Mapping[str, str], root: Path = ROOT) -> str | None:
    if not args.execute:
        return "--execute is required; no exchange request was made"
    if args.amount is None:
        return "--amount is required; automatic balance sweeps are disabled"
    if args.confirmation != CONFIRMATION_PHRASE:
        return "exact --confirmation phrase is required; no exchange request was made"

    # A private human approval token must be present at the moment of execution.
    if len(str(environ.get(HUMAN_APPROVAL_ENV, ""))) < 32:
        return "private human action-time approval is missing; no exchange request was made"
    if not fully_live_runtime(root):
        return "runtime is not fully live-armed; no exchange request was made"
    if not environ.get(DESTINATION_ENV):
        return "configured withdrawal destination is missing; no exchange request was made"
    if not environ.get(API_KEY_ENV) or not environ.get(API_SECRET_ENV):
        return "exchange credentials are unavailable; no exchange request was made"
    return None


def build_kraken_client(environ: Mapping[str, str]):
    # Delay both the optional dependency and credential use until every gate passes.
    import ccxt

    return ccxt.kraken(
        {
            "apiKey": environ[API_KEY_ENV],
            "secret": environ[API_SECRET_ENV],
            "enableRateLimit": True,
        }
    )


def execute_withdrawal(args: argparse.Namespace, environ: Mapping[str, str], root: Path = ROOT):
    blocked = execution_block_reason(args, environ, root)
    if blocked:
        raise RuntimeError(blocked)

    client = build_kraken_client(environ)
    return client.withdraw("BTC", str(args.amount), environ[DESTINATION_ENV])


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    blocked = execution_block_reason(args, os.environ)
    if blocked:
        print(f"BLOCKED: {blocked}")
        return 0 if not args.execute else 2

    try:
        result = execute_withdrawal(args, os.environ)
    except Exception as exc:
        print(f"WITHDRAWAL_REQUEST_FAILED: {type(exc).__name__}")
        return 1

    request_id = result.get("id") if isinstance(result, dict) else None
    print(f"WITHDRAWAL_REQUEST_SUBMITTED: amount_btc={args.amount} request_id={request_id or 'unavailable'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
