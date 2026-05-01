import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
ENV_FILE = ROOT / "config" / "luma_live_keys.env"
OUT_DIR = ROOT / "out" / "execution"
LOG_JSONL = OUT_DIR / "payout_webhook_received.jsonl"
LATEST_JSON = OUT_DIR / "payout_webhook_latest.json"


def _load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _resolve_shared_secret() -> str:
    env_values = _load_env_file(ENV_FILE)
    candidates = [
        os.environ.get("LUMA_PAYOUT_TOKEN", ""),
        os.environ.get("PAYOUT_WEBHOOK_AUTH_BEARER", ""),
        os.environ.get("WEBHOOK_SHARED_SECRET", ""),
        env_values.get("LUMA_PAYOUT_TOKEN", ""),
        env_values.get("PAYOUT_WEBHOOK_AUTH_BEARER", ""),
        env_values.get("WEBHOOK_SHARED_SECRET", ""),
    ]
    for candidate in candidates:
        token = str(candidate or "").strip()
        if token:
            return token
    return ""


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(path)


class PayoutWebhookHandler(BaseHTTPRequestHandler):
    server_version = "LumaPayoutWebhook/1.0"

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except Exception:
            length = 0
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except Exception:
            return None
        return parsed if isinstance(parsed, dict) else None

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": "payout_webhook_receiver",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                },
            )
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/payout-webhook":
            self._send_json(404, {"ok": False, "error": "not_found"})
            return

        expected_secret = _resolve_shared_secret()
        auth_header = str(self.headers.get("Authorization", "") or "").strip()
        provided_secret = ""
        if auth_header.lower().startswith("bearer "):
            provided_secret = auth_header[7:].strip()

        if expected_secret and provided_secret != expected_secret:
            self._send_json(401, {"ok": False, "error": "unauthorized"})
            return

        payload = self._read_json_body()
        if not payload:
            self._send_json(400, {"ok": False, "error": "invalid_json_payload"})
            return

        received = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "source": "payout_webhook_receiver",
            "payload": payload,
        }
        _append_jsonl(LOG_JSONL, received)
        _write_json(LATEST_JSON, received)

        self._send_json(
            200,
            {
                "ok": True,
                "received": True,
                "intent_id": str(payload.get("intent_id", "")),
                "timestamp_utc": received["timestamp_utc"],
            },
        )

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    host = os.environ.get("LUMA_PAYOUT_HOST", "127.0.0.1")
    port = int(os.environ.get("LUMA_PAYOUT_PORT", "8787"))
    try:
        server = ThreadingHTTPServer((host, port), PayoutWebhookHandler)
    except OSError as exc:
        print(f"[ERROR] Could not bind payout webhook receiver on {host}:{port} ({exc})")
        print("[HINT] Another receiver is likely already running on this port.")
        raise SystemExit(1)
    print(f"payout_webhook_receiver listening on http://{host}:{port}")
    print("health: /health")
    print("webhook: /payout-webhook")
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
