import base64
import hashlib
import hmac
import time
import urllib.parse
from pathlib import Path

import requests


def load_env(path: Path):
    env = {}
    for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def sign(path: str, data: dict, secret: str) -> str:
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data["nonce"]) + postdata).encode()
    msg = path.encode() + hashlib.sha256(encoded).digest()
    sig = hmac.new(base64.b64decode(secret), msg, hashlib.sha512).digest()
    return base64.b64encode(sig).decode()


def post(path: str, data: dict, key: str, secret: str) -> dict:
    payload = dict(data)
    payload["nonce"] = str(int(time.time() * 1000))
    headers = {
        "API-Key": key,
        "API-Sign": sign(path, payload, secret),
    }
    return requests.post(
        "https://api.kraken.com" + path,
        headers=headers,
        data=payload,
        timeout=20,
    ).json()


def main():
    env_path = Path(r"c:\LumaTrader\INSTITUTIONAL_STACK_V2\code\execution\config\luma_live_keys.env")
    env = load_env(env_path)
    key = env.get("KRAKEN_API_KEY", "")
    secret = env.get("KRAKEN_API_SECRET", "")

    open_orders = post("/0/private/OpenOrders", {}, key, secret)
    balance = post("/0/private/Balance", {}, key, secret)

    print("OPEN_ERRORS", open_orders.get("error"))
    open_map = (open_orders.get("result") or {}).get("open", {})
    print("OPEN_COUNT", len(open_map))
    print("OPEN_TXIDS", list(open_map.keys())[:20])

    print("BAL_ERRORS", balance.get("error"))
    res = balance.get("result") or {}
    for k in ["ZUSD", "USDT", "RAVE", "XXBT", "PEPE", "ADA", "SOL"]:
        print(k, res.get(k, "0"))


if __name__ == "__main__":
    main()
