from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
SPORTS_DIR = ROOT / "sports_data"

# Auto-load keys from the project .env file if not already in environment
_ENV_FILE = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        if _k.strip() and not os.getenv(_k.strip()):
            os.environ[_k.strip()] = _v.strip()
SPORTS_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = "https://api.the-odds-api.com/v4"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_api_key() -> str:
    for key_name in ("THEODDS_API_KEY", "ODDS_API_KEY", "SPORTS_ODDS_API_KEY"):
        value = (os.getenv(key_name) or "").strip()
        if value:
            return value
    return ""


def http_get(url: str, params: dict[str, Any]) -> Any:
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def list_sports(api_key: str) -> list[str]:
    payload = http_get(f"{API_BASE}/sports", {"apiKey": api_key})
    out: list[str] = []
    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key", "")).strip()
            active = bool(item.get("active", False))
            if key and active:
                out.append(key)
    return out


def fetch_sport(api_key: str, sport_key: str, regions: str, markets: str) -> list[dict[str, Any]]:
    payload = http_get(
        f"{API_BASE}/sports/{sport_key}/odds",
        {
            "apiKey": api_key,
            "regions": regions,
            "markets": markets,
            "bookmakers": "draftkings",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        },
    )
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def sanitize_error_message(message: str, api_key: str) -> str:
    text = str(message or "")
    if api_key:
        text = text.replace(api_key, "***")
    text = re.sub(r"([?&]apiKey=)[^&\s]+", r"\1***", text, flags=re.IGNORECASE)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull live DraftKings odds via The Odds API")
    parser.add_argument("--sport", default="basketball_nba", help="Sport key (e.g. basketball_nba) or 'all'")
    parser.add_argument("--regions", default="us", help="Regions filter, default: us")
    parser.add_argument("--markets", default="h2h,spreads,totals", help="Markets CSV")
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        print("ERROR: Missing THEODDS_API_KEY/ODDS_API_KEY/SPORTS_ODDS_API_KEY")
        return 2

    if args.sport.lower() == "all":
        sports = list_sports(api_key)
    else:
        sports = [args.sport]

    manifest: dict[str, Any] = {
        "generated_utc": now_utc(),
        "regions": args.regions,
        "markets": args.markets,
        "bookmaker": "draftkings",
        "sports": {},
    }

    for sport_key in sports:
        try:
            events = fetch_sport(api_key, sport_key, args.regions, args.markets)
        except Exception as exc:
            manifest["sports"][sport_key] = {
                "ok": False,
                "error": sanitize_error_message(str(exc), api_key),
                "events": 0,
            }
            continue

        out_path = SPORTS_DIR / f"{sport_key}_draftkings_live_odds.json"
        write_json(out_path, events)
        manifest["sports"][sport_key] = {
            "ok": True,
            "events": len(events),
            "path": str(out_path),
        }

    manifest_path = SPORTS_DIR / "draftkings_live_manifest.json"
    write_json(manifest_path, manifest)

    ok_count = sum(1 for v in manifest["sports"].values() if isinstance(v, dict) and v.get("ok"))
    print(f"DraftKings pull complete | sports_ok={ok_count} | manifest={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
