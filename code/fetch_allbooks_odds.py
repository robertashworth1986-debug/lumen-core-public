from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
SPORTS_DIR = ROOT / "sports_data"
SPORTS_DIR.mkdir(parents=True, exist_ok=True)

API_BASE = "https://api.the-odds-api.com/v4"

# Auto-load keys from project .env file if not already in environment
_ENV_FILE = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _k, _, _v = _line.partition("=")
        if _k.strip() and not os.getenv(_k.strip()):
            os.environ[_k.strip()] = _v.strip()


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


def fetch_sport_all_books(api_key: str, sport_key: str, regions: str, markets: str) -> list[dict[str, Any]]:
    """Fetch all bookmakers for a sport (needed for multi-book comparison)."""
    payload = http_get(
        f"{API_BASE}/sports/{sport_key}/odds",
        {
            "apiKey": api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        },
    )
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    return []


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch all-book odds for EV analysis")
    parser.add_argument("--sports", default="icehockey_nhl,basketball_nba,baseball_mlb",
                        help="Comma-separated sport keys or 'all'")
    parser.add_argument("--regions", default="us,uk,eu", help="Regions filter")
    parser.add_argument("--markets", default="h2h,spreads,totals")
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        print("ERROR: Missing odds API key")
        return 2

    if args.sports.strip().lower() == "all":
        sports = list_sports(api_key)
    else:
        sports = [s.strip() for s in args.sports.split(",") if s.strip()]
    manifest: dict[str, Any] = {"generated_utc": now_utc(), "sports": {}}

    for sport_key in sports:
        try:
            events = fetch_sport_all_books(api_key, sport_key, args.regions, args.markets)
        except Exception as exc:
            manifest["sports"][sport_key] = {"ok": False, "error": str(exc)}
            print(f"  SKIP {sport_key}: {exc}")
            continue

        out_path = SPORTS_DIR / f"{sport_key}_allbooks_live_odds.json"
        write_json(out_path, events)
        manifest["sports"][sport_key] = {"ok": True, "events": len(events), "path": str(out_path)}
        print(f"  {sport_key}: {len(events)} events -> {out_path.name}")

    write_json(SPORTS_DIR / "allbooks_manifest.json", manifest)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
