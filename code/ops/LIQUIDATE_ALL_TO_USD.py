#!/usr/bin/env python3
"""Quarantined legacy liquidation utility with a narrow, manual execution path.

The historical implementation could enumerate balances and liquidate an entire
portfolio. That behavior is intentionally removed. This utility now supports
only one user-named asset and one exact amount after every live-action gate
passes. With no arguments it performs no network, exchange, or account action.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
CODE_DIR = ROOT / "code"
OUT_EXEC_DIR = ROOT / "out" / "execution"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from execution.live_runtime_guard import LiveRuntimeGuard


KRAKEN_PUBLIC_URL = "https://api.kraken.com/0/public/AssetPairs"
USD_QUOTES = {"ZUSD", "USD"}
USD_ASSETS = {"ZUSD", "USD"}
CONFIRMATION_PHRASE = "CONFIRM_SPECIFIED_ASSET_LIQUIDATION"
HUMAN_APPROVAL_ENV = "LUMA_HUMAN_UNLOCK_TOKEN"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def floor_to_decimals(value: float, decimals: int) -> float:
    if decimals <= 0:
        return math.floor(value)
    factor = 10**decimals
    return math.floor(value * factor) / factor


def parse_amount(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise argparse.ArgumentTypeError("amount must be a positive decimal asset quantity") from exc
    if not amount.is_finite() or amount <= 0:
        raise argparse.ArgumentTypeError("amount must be a positive decimal asset quantity")
    return amount


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Narrow, manually gated USD liquidation utility")
    command.add_argument("--execute", action="store_true", help="submit one market sell only after every gate passes")
    command.add_argument("--asset", default="", help="exact non-USD asset symbol to sell")
    command.add_argument("--amount", type=parse_amount, help="exact asset amount to sell; portfolio balance sweeps are disabled")
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
    asset = str(args.asset or "").upper().strip()
    if not args.execute:
        return "--execute is required; no account or exchange action was made"
    if not asset:
        return "--asset is required; portfolio-wide liquidation is disabled"
    if asset in USD_ASSETS:
        return "USD assets cannot be liquidated by this utility"
    if args.amount is None:
        return "--amount is required; portfolio balance sweeps are disabled"
    if args.confirmation != CONFIRMATION_PHRASE:
        return "exact --confirmation phrase is required; no exchange action was made"
    # Private human approval must exist at the precise time an exchange action is attempted.
    if len(str(environ.get(HUMAN_APPROVAL_ENV, ""))) < 32:
        return "private human action-time approval is missing; no exchange action was made"
    if not fully_live_runtime(root):
        return "runtime is not fully live-armed; no exchange action was made"
    return None


def fetch_asset_pairs() -> dict[str, dict[str, Any]]:
    import requests

    response = requests.get(KRAKEN_PUBLIC_URL, timeout=30)
    response.raise_for_status()
    payload = response.json()
    errors = payload.get("error") or []
    if errors:
        raise RuntimeError("Kraken AssetPairs error: " + "; ".join(str(error) for error in errors))
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("Kraken AssetPairs result missing")
    return result


def pick_usd_pair(asset: str, all_pairs: Mapping[str, Mapping[str, Any]]) -> dict[str, Any] | None:
    target = str(asset).upper().strip()
    candidates: list[dict[str, Any]] = []
    for meta in all_pairs.values():
        if not isinstance(meta, Mapping):
            continue
        if str(meta.get("base", "")).upper().strip() != target:
            continue
        if str(meta.get("quote", "")).upper().strip() not in USD_QUOTES:
            continue
        pair = str(meta.get("altname", "")).strip() or str(meta.get("wsname", "")).split("/")[0]
        if pair:
            candidates.append(
                {
                    "pair": pair,
                    "ordermin": safe_float(meta.get("ordermin", 0.0)),
                    "lot_decimals": int(meta.get("lot_decimals", 8) or 8),
                }
            )
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: row["pair"])[0]


def build_sell_order(amount: Decimal, pair_meta: Mapping[str, Any]) -> tuple[float, str | None]:
    volume = floor_to_decimals(float(amount), int(pair_meta.get("lot_decimals", 8) or 8))
    if volume <= 0.0:
        return 0.0, "volume_zero_after_rounding"
    ordermin = max(safe_float(pair_meta.get("ordermin", 0.0)), 0.0)
    if ordermin > 0.0 and volume + 1e-12 < ordermin:
        return 0.0, f"below_ordermin({ordermin})"
    return volume, None


def submit_market_sell(pair: str, volume: float) -> dict[str, Any]:
    # The Kraken private client is intentionally imported only after every local gate passes.
    from kraken_execution import _private_post

    return _private_post(
        "/0/private/AddOrder",
        {"pair": pair, "type": "sell", "ordertype": "market", "volume": f"{volume:.8f}"},
    )


def execute_liquidation(args: argparse.Namespace, environ: Mapping[str, str], root: Path = ROOT) -> dict[str, Any]:
    blocked = execution_block_reason(args, environ, root)
    if blocked:
        raise RuntimeError(blocked)

    asset = str(args.asset).upper().strip()
    pair_meta = pick_usd_pair(asset, fetch_asset_pairs())
    if pair_meta is None:
        raise RuntimeError("no direct USD pair is available for the requested asset")
    volume, issue = build_sell_order(args.amount, pair_meta)
    if issue:
        raise RuntimeError(issue)
    result = submit_market_sell(str(pair_meta["pair"]), volume)
    return {"asset": asset, "amount": str(args.amount), "pair": pair_meta["pair"], "volume": volume, "result": result}


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    blocked = execution_block_reason(args, os.environ)
    if blocked:
        print(f"BLOCKED: {blocked}")
        return 0 if not args.execute else 2

    try:
        action = execute_liquidation(args, os.environ)
    except Exception as exc:
        print(f"LIQUIDATION_REQUEST_FAILED: {type(exc).__name__}")
        return 1

    OUT_EXEC_DIR.mkdir(parents=True, exist_ok=True)
    receipt = {
        "generated_utc": utc_now().isoformat(),
        "scope": "single_asset_exact_amount_liquidation",
        "asset": action["asset"],
        "amount": action["amount"],
        "pair": action["pair"],
        "volume": action["volume"],
        "exchange_request_id": action["result"].get("txid") if isinstance(action["result"], dict) else None,
    }
    (OUT_EXEC_DIR / "liquidate_all_to_usd_latest.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"LIQUIDATION_REQUEST_SUBMITTED: asset={receipt['asset']} amount={receipt['amount']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
