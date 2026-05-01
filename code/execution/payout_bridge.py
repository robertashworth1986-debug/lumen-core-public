import json
import time
import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG_FILE = ROOT / "config" / "runtime_control.json"
ENV_FILE = ROOT / "config" / "luma_live_keys.env"
PAYOUT_INTENTS_FILE = ROOT / "out" / "execution" / "payout_intents.json"
WALLET_TRANSFER_REQUESTS_FILE = ROOT / "out" / "execution" / "wallet_transfer_requests.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def _load_env_keys() -> Dict[str, str]:
    keys: Dict[str, str] = {}
    if not ENV_FILE.exists():
        return keys
    try:
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip() and "=" in line:
                key, value = line.split("=", 1)
                keys[key.strip()] = value.strip()
    except Exception:
        return {}
    return keys


def _is_valid_webhook_url(value: str) -> bool:
    txt = str(value or "").strip()
    if not txt:
        return False
    if " " in txt:
        return False
    return txt.startswith("https://") or txt.startswith("http://")


def _resolve_payout_credentials(cfg: Dict[str, Any]) -> Dict[str, str]:
    env_keys = _load_env_keys()

    cfg_url = str(cfg.get("payout_webhook_url", "") or "").strip()
    cfg_token = str(cfg.get("payout_webhook_auth_bearer", "") or "").strip()

    url_keys = [
        "LUMA_PAYOUT_WEBHOOK",
        "PAYOUT_WEBHOOK_URL",
        "CHIME_PAYOUT_WEBHOOK_URL",
        "CHIME_WEBHOOK_URL",
        "PAYOUT_WEBHOOK",
    ]
    token_keys = [
        "LUMA_PAYOUT_TOKEN",
        "PAYOUT_WEBHOOK_AUTH_BEARER",
        "CHIME_PAYOUT_BEARER_TOKEN",
        "CHIME_WEBHOOK_BEARER",
        "WEBHOOK_SHARED_SECRET",
    ]

    resolved_url = cfg_url if _is_valid_webhook_url(cfg_url) else ""
    if not resolved_url:
        for key in url_keys:
            candidate = str(env_keys.get(key, "") or "").strip()
            if _is_valid_webhook_url(candidate):
                resolved_url = candidate
                break

    resolved_token = cfg_token
    if not resolved_token:
        for key in token_keys:
            candidate = str(env_keys.get(key, "") or "").strip()
            if candidate:
                resolved_token = candidate
                break

    return {
        "payout_webhook_url": resolved_url,
        "payout_webhook_auth_bearer": resolved_token,
    }


def _dispatch_webhook(cfg: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    resolved = _resolve_payout_credentials(cfg)
    webhook_url = str(resolved.get("payout_webhook_url", "") or "").strip()
    if not _is_valid_webhook_url(webhook_url):
        return {"attempted": False, "ok": False, "reason": "missing_payout_webhook_url"}

    auth_bearer = str(resolved.get("payout_webhook_auth_bearer", "") or "").strip()
    timeout_sec = float(cfg.get("payout_webhook_timeout_sec", 10.0) or 10.0)

    headers = {"Content-Type": "application/json"}
    if auth_bearer:
        headers["Authorization"] = f"Bearer {auth_bearer}"

    start = time.time()
    try:
        response = requests.post(
            webhook_url,
            json=intent,
            headers=headers,
            timeout=max(1.0, timeout_sec),
        )
        latency_ms = (time.time() - start) * 1000.0
        ok = 200 <= int(response.status_code) < 300
        return {
            "attempted": True,
            "ok": bool(ok),
            "reason": "ok" if ok else f"http_{int(response.status_code)}",
            "status_code": int(response.status_code),
            "latency_ms": round(latency_ms, 2),
            "response_excerpt": (response.text or "")[:240],
        }
    except Exception as exc:
        latency_ms = (time.time() - start) * 1000.0
        return {
            "attempted": True,
            "ok": False,
            "reason": f"exception:{type(exc).__name__}",
            "latency_ms": round(latency_ms, 2),
            "response_excerpt": str(exc)[:240],
        }


def _dispatch_wallet_file(cfg: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    def _looks_like_card_number(value: str) -> bool:
        digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
        if not (12 <= len(digits) <= 19):
            return False
        try:
            checksum = 0
            parity = len(digits) % 2
            for idx, ch in enumerate(digits):
                num = int(ch)
                if idx % 2 == parity:
                    num *= 2
                    if num > 9:
                        num -= 9
                checksum += num
            return checksum % 10 == 0
        except Exception:
            return False

    def _is_valid_wallet_address(address: str, network: str) -> bool:
        addr = str(address or '').strip()
        net = str(network or '').strip().upper()
        if not addr:
            return False
        if _looks_like_card_number(addr):
            return False
        if net == 'TRC20':
            return bool(re.match(r'^T[1-9A-HJ-NP-Za-km-z]{33}$', addr))
        if net in ('ERC20', 'BEP20'):
            return bool(re.match(r'^0x[a-fA-F0-9]{40}$', addr))
        if net in ('BTC', 'BITCOIN'):
            return bool(re.match(r'^(bc1[ac-hj-np-z02-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$', addr))
        return len(addr) >= 20

    wallet_address = str(cfg.get("payout_wallet_address", "") or "").strip()
    wallet_network = str(cfg.get("payout_wallet_network", "TRC20") or "TRC20").strip().upper()
    wallet_asset = str(cfg.get("payout_wallet_asset", "USDT") or "USDT").strip().upper()
    wallet_label = str(cfg.get("payout_wallet_label", "self_custody_wallet") or "self_custody_wallet").strip()
    if not wallet_address:
        return {"attempted": False, "ok": False, "reason": "missing_payout_wallet_address"}
    if _looks_like_card_number(wallet_address):
        return {"attempted": False, "ok": False, "reason": "wallet_address_looks_like_card_number"}
    if not _is_valid_wallet_address(wallet_address, wallet_network):
        return {"attempted": False, "ok": False, "reason": f"invalid_payout_wallet_address_for_network:{wallet_network}"}

    existing = _load_json(WALLET_TRANSFER_REQUESTS_FILE, [])
    if not isinstance(existing, list):
        existing = []

    request_id = f"wallet-{int(time.time() * 1000)}"
    request = {
        "request_id": request_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source": "payout_bridge",
        "intent_id": str(intent.get("intent_id", "") or ""),
        "destination_type": "wallet",
        "wallet_label": wallet_label,
        "asset": wallet_asset,
        "network": wallet_network,
        "address": wallet_address,
        "amount_usd": float(intent.get("amount_usd", 0.0) or 0.0),
        "destination": str(intent.get("destination", "") or ""),
        "destination_label": str(intent.get("destination_label", "") or ""),
        "account_hint": str(intent.get("account_hint", "") or ""),
        "status": "REQUESTED",
    }
    existing.append(request)
    _save_json(WALLET_TRANSFER_REQUESTS_FILE, existing)
    return {
        "attempted": True,
        "ok": True,
        "reason": "wallet_transfer_requested",
        "mode": "wallet_file",
        "request_id": request_id,
        "request_file": str(WALLET_TRANSFER_REQUESTS_FILE),
    }


def run_once(max_items: int = 20, dry_run: bool = False) -> int:
    cfg = _load_json(CONFIG_FILE, {})
    intents = _load_json(PAYOUT_INTENTS_FILE, [])
    if not isinstance(intents, list):
        intents = []

    auto_enabled = bool(cfg.get("payout_auto_dispatch_enabled", False))
    if not auto_enabled:
        print("payout_auto_dispatch_enabled=false; nothing to dispatch")
        return 0

    pending = [it for it in intents if str(it.get("status", "")).upper() == "PENDING"]
    if not pending:
        print("No pending payout intents")
        return 0

    processed = 0
    for intent in pending[: max(1, int(max_items))]:
        intent_id = str(intent.get("intent_id", ""))
        if dry_run:
            print(f"[dry-run] would dispatch intent={intent_id} amount={intent.get('amount_usd')} destination={intent.get('destination')}")
            processed += 1
            continue

        dispatch_mode = str(cfg.get("payout_dispatch_mode", "webhook") or "webhook").strip().lower()
        if dispatch_mode == "wallet_file":
            result = _dispatch_wallet_file(cfg, intent)
        else:
            result = _dispatch_webhook(cfg, intent)
        for item in intents:
            if str(item.get("intent_id", "")) == intent_id:
                item["status"] = "DISPATCHED" if bool(result.get("ok", False)) else "DISPATCH_FAILED"
                item["dispatch"] = {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "mode": str(cfg.get("payout_dispatch_mode", "webhook") or "webhook"),
                    "result": result,
                }
                break
        print(f"intent={intent_id} status={('DISPATCHED' if bool(result.get('ok', False)) else 'DISPATCH_FAILED')} reason={result.get('reason')}")
        processed += 1

    if not dry_run and processed > 0:
        _save_json(PAYOUT_INTENTS_FILE, intents)

    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Dispatch pending payout intents to configured webhook")
    parser.add_argument("--max-items", type=int, default=20, help="Max pending intents to process")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without network calls")
    args = parser.parse_args()

    processed = run_once(max_items=args.max_items, dry_run=args.dry_run)
    print(f"processed={processed}")


if __name__ == "__main__":
    main()
