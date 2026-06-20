"""
One-shot Kraken open-order inspection/cancel tool.

Default behavior is DRY RUN: list balances and open orders only. Cancelling is a
live account mutation and requires both:

    --execute --confirm CANCEL_ALL_OPEN_ORDERS
"""
import argparse
import base64
import hashlib
import hmac
import json
import sys
import time
import urllib.parse
from pathlib import Path

import requests

ENV_FILE = Path(__file__).parents[2] / "config" / "luma_live_keys.env"
CONFIRM_PHRASE = "CANCEL_ALL_OPEN_ORDERS"


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f"Kraken env file not found: {path}")
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def kraken_private(endpoint: str, api_key: str, api_secret: str, data: dict | None = None) -> dict:
    if not api_key or not api_secret:
        raise RuntimeError("KRAKEN_API_KEY/KRAKEN_API_SECRET missing")
    data = dict(data or {})
    nonce = str(int(time.time_ns()))
    data["nonce"] = nonce
    post = urllib.parse.urlencode(data)
    msg = endpoint.encode() + hashlib.sha256((nonce + post).encode()).digest()
    secret = api_secret.strip()
    missing_padding = len(secret) % 4
    if missing_padding:
        secret += "=" * (4 - missing_padding)
    sig = base64.b64encode(
        hmac.new(base64.b64decode(secret), msg, hashlib.sha512).digest()
    ).decode()
    response = requests.post(
        "https://api.kraken.com" + endpoint,
        data=data,
        headers={"API-Key": api_key, "API-Sign": sig},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and optionally cancel all open Kraken orders.")
    parser.add_argument("--execute", action="store_true", help="Actually cancel all open orders.")
    parser.add_argument("--confirm", default="", help=f"Required phrase for --execute: {CONFIRM_PHRASE}")
    parser.add_argument("--skip-balances", action="store_true", help="Do not print live balances.")
    args = parser.parse_args()

    if args.execute and args.confirm != CONFIRM_PHRASE:
        print(f"ERROR: --execute requires --confirm {CONFIRM_PHRASE}", file=sys.stderr)
        return 2

    env = load_env_file(ENV_FILE)
    api_key = env.get("KRAKEN_API_KEY", "").strip()
    api_secret = env.get("KRAKEN_API_SECRET", "").strip()

    if not args.skip_balances:
        balance = kraken_private("/0/private/Balance", api_key, api_secret)
        if balance.get("error"):
            print("Balance error:", balance["error"])
        else:
            nonzero = {
                k: float(v)
                for k, v in balance.get("result", {}).items()
                if float(v) > 0.001
            }
            print("LIVE BALANCES:")
            for key, value in sorted(nonzero.items(), key=lambda x: -x[1]):
                print(f"  {key:12} {value:.6f}")

    orders_resp = kraken_private("/0/private/OpenOrders", api_key, api_secret)
    if orders_resp.get("error"):
        print("OpenOrders error:", orders_resp["error"])
        return 1

    open_orders = orders_resp.get("result", {}).get("open", {})
    print(f"\nOpen orders: {len(open_orders)}")
    for txid, order in open_orders.items():
        descr = order.get("descr", {})
        print(
            f"  {txid}: {descr.get('order', '?')} | "
            f"status={order.get('status')} | vol_exec={order.get('vol_exec', 0)}"
        )

    if not open_orders:
        print("No open orders to cancel.")
        return 0

    if not args.execute:
        print("DRY RUN: no orders cancelled. Re-run with --execute --confirm CANCEL_ALL_OPEN_ORDERS to cancel.")
        return 0

    print("\nCancelling all open orders...")
    cancel_resp = kraken_private("/0/private/CancelAll", api_key, api_secret)
    if cancel_resp.get("error"):
        print("CancelAll error:", cancel_resp["error"])
        return 1

    count = cancel_resp.get("result", {}).get("count", 0)
    print(f"Cancelled {count} orders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
