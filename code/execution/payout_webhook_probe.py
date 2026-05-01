import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
from urllib import request, error

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
RUNTIME_FILE = ROOT / "config" / "runtime_control.json"
ENV_FILE = ROOT / "config" / "luma_live_keys.env"


def _load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _resolve_url_and_token() -> Dict[str, str]:
    runtime = _load_json(RUNTIME_FILE)
    env_values = _load_env_file(ENV_FILE)

    webhook_url = str(runtime.get("payout_webhook_url", "") or "").strip()
    if not webhook_url.startswith("http://") and not webhook_url.startswith("https://"):
        webhook_url = "http://127.0.0.1:8787/payout-webhook"

    token = str(runtime.get("payout_webhook_auth_bearer", "") or "").strip()
    if not token:
        token = str(os.environ.get("LUMA_PAYOUT_TOKEN", "") or "").strip()
    if not token:
        token = str(env_values.get("LUMA_PAYOUT_TOKEN", "") or env_values.get("WEBHOOK_SHARED_SECRET", "")).strip()

    return {"url": webhook_url, "token": token}


def main() -> None:
    resolved = _resolve_url_and_token()
    payload = {
        "intent_id": f"probe-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PENDING",
        "destination": "chime",
        "amount_usd": 1.23,
        "trigger": {"type": "probe"},
    }

    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if resolved["token"]:
        headers["Authorization"] = f"Bearer {resolved['token']}"

    req = request.Request(resolved["url"], data=body, method="POST", headers=headers)
    try:
        with request.urlopen(req, timeout=10) as resp:
            resp_text = resp.read().decode("utf-8")
            print(json.dumps({"ok": True, "status": resp.status, "url": resolved["url"], "response": resp_text}, indent=2))
    except error.HTTPError as http_err:
        err_body = http_err.read().decode("utf-8", errors="replace")
        print(json.dumps({"ok": False, "status": http_err.code, "url": resolved["url"], "error": err_body}, indent=2))
        raise
    except Exception as exc:
        print(json.dumps({"ok": False, "url": resolved["url"], "error": str(exc)}, indent=2))
        raise


if __name__ == "__main__":
    main()
