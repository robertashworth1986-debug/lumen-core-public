"""
One-shot script: list and cancel all open Kraken orders.
Reads credentials from luma_live_keys.env.
"""
import sys, requests, hashlib, hmac, base64, time, urllib.parse, json
from pathlib import Path

ENV_FILE = Path(__file__).parents[2] / "config" / "luma_live_keys.env"
env = dict(line.strip().split("=", 1) for line in ENV_FILE.read_text().splitlines() if "=" in line and not line.startswith("#"))
API_KEY = env.get("KRAKEN_API_KEY", "").strip()
API_SECRET = env.get("KRAKEN_API_SECRET", "").strip()


def kraken_private(endpoint, data=None):
    data = dict(data or {})
    nonce = str(int(time.time_ns()))
    data["nonce"] = nonce
    post = urllib.parse.urlencode(data)
    msg = endpoint.encode() + hashlib.sha256((nonce + post).encode()).digest()
    sig = base64.b64encode(
        hmac.new(base64.b64decode(API_SECRET), msg, hashlib.sha512).digest()
    ).decode()
    r = requests.post(
        "https://api.kraken.com" + endpoint, data=data,
        headers={"API-Key": API_KEY, "API-Sign": sig}, timeout=15
    )
    return r.json()


# 1. Get live balance
bal = kraken_private("/0/private/Balance")
if bal.get("error"):
    print("Balance error:", bal["error"])
else:
    b = {k: float(v) for k, v in bal.get("result", {}).items() if float(v) > 0.001}
    print("LIVE BALANCES:")
    for k, v in sorted(b.items(), key=lambda x: -x[1]):
        print(f"  {k:12} {v:.6f}")

# 2. Get open orders
orders_resp = kraken_private("/0/private/OpenOrders")
if orders_resp.get("error"):
    print("OpenOrders error:", orders_resp["error"])
    sys.exit(1)
open_orders = orders_resp.get("result", {}).get("open", {})
print(f"\nOpen orders: {len(open_orders)}")
for txid, order in open_orders.items():
    descr = order.get("descr", {})
    print(f"  {txid}: {descr.get('order', '?')} | status={order.get('status')} | vol_exec={order.get('vol_exec', 0)}")

# 3. Cancel all open orders
if open_orders:
    print("\nCancelling all open orders...")
    cancel_resp = kraken_private("/0/private/CancelAll")
    if cancel_resp.get("error"):
        print("CancelAll error:", cancel_resp["error"])
    else:
        count = cancel_resp.get("result", {}).get("count", 0)
        print(f"Cancelled {count} orders.")
else:
    print("No open orders to cancel.")
