from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
CONF = ROOT / "config"
OUT_FILE = ROOT / "out" / "execution" / "api_key_registry_report.json"

ENV_CANDIDATES = [
    CONF / "luma_live_keys.env",
    CODE / "execution" / "config" / "luma_live_keys.env",
    ROOT / ".env.live",
    ROOT / ".env.sports",
    ROOT / ".env",
]

# Canonical key-purpose registry (safe: never stores key values).
KEY_PURPOSES: Dict[str, Dict[str, Any]] = {
    "ALPACA_API_KEY": {
        "purpose": "Alpaca broker market/trading API auth",
        "used_by": ["execution/alpaca_paper_orchestrator.py", "alpaca_paper_loop_builder.py"],
        "aliases": ["APCA_API_KEY_ID", "ALPACA_KEY"],
    },
    "ALPACA_API_SECRET": {
        "purpose": "Alpaca broker secret",
        "used_by": ["execution/alpaca_paper_orchestrator.py", "alpaca_paper_loop_builder.py"],
        "aliases": ["APCA_API_SECRET_KEY", "ALPACA_SECRET"],
    },
    "KRAKEN_API_KEY": {
        "purpose": "Kraken execution/auth API key",
        "used_by": ["execution/live_executor.py", "kraken_execution.py"],
        "aliases": [],
    },
    "KRAKEN_API_SECRET": {
        "purpose": "Kraken execution/auth secret",
        "used_by": ["execution/live_executor.py", "kraken_execution.py"],
        "aliases": [],
    },
    "FRED_API_KEY": {
        "purpose": "FRED macroeconomic data retrieval",
        "used_by": ["CANONICAL_GOV_DATA_COLLECTOR.py", "audit_and_leverage_packages.py"],
        "aliases": ["FRED_KEY"],
    },
    "EIA_API_KEY": {
        "purpose": "EIA grid demand/outage datasets",
        "used_by": ["CANONICAL_GOV_DATA_COLLECTOR.py", "cross-sector intelligence"],
        "aliases": ["EIA_KEY"],
    },
    "NOAA_API_TOKEN": {
        "purpose": "NOAA climate/weather feeds for infra risk",
        "used_by": ["CANONICAL_GOV_DATA_COLLECTOR.py"],
        "aliases": ["NCDC_NOAA_API_TOKEN"],
    },
    "CENSUS_API_KEY": {
        "purpose": "Census demographic/economic enrichment",
        "used_by": ["CANONICAL_GOV_DATA_COLLECTOR.py"],
        "aliases": ["CENSUS_KEY"],
    },
    "BEA_API_KEY": {
        "purpose": "BEA macro data for economic models",
        "used_by": ["canonical_extended_universe.py"],
        "aliases": [],
    },
    "BLS_API_KEY": {
        "purpose": "BLS labor/economic data feeds",
        "used_by": ["canonical_extended_universe.py"],
        "aliases": [],
    },
    "NASA_API_KEY": {
        "purpose": "NASA open data feeds (environment/space datasets)",
        "used_by": ["canonical_extended_universe.py"],
        "aliases": [],
    },
    "NREL_API_KEY": {
        "purpose": "NREL energy data feeds",
        "used_by": ["canonical_extended_universe.py"],
        "aliases": [],
    },
    "OPENAI_API_KEY": {
        "purpose": "AI explainers, scoring narratives, model calls",
        "used_by": ["audit_and_leverage_packages.py", "gateway explainer helpers"],
        "aliases": [],
    },
    "YOUTUBE_API_KEY": {
        "purpose": "YouTube Data API read-only video/channel metrics for LumaScout talent discovery",
        "used_by": ["LamaScout/src/api_clients.py"],
        "aliases": ["GOOGLE_YOUTUBE_API_KEY", "GOOGLE_API_KEY"],
    },
    "SPOTIFY_CLIENT_ID": {
        "purpose": "Spotify client-credentials identifier for LumaScout read-only artist metrics",
        "used_by": ["LamaScout/src/api_clients.py"],
        "aliases": ["SPOTIFY_API_CLIENT_ID"],
    },
    "SPOTIFY_CLIENT_SECRET": {
        "purpose": "Spotify client-credentials secret for LumaScout read-only artist metrics",
        "used_by": ["LamaScout/src/api_clients.py"],
        "aliases": ["SPOTIFY_API_CLIENT_SECRET"],
    },
    "META_ACCESS_TOKEN": {
        "purpose": "Meta/Facebook/Instagram read-only creator signal for LumaScout",
        "used_by": ["LamaScout/src/api_clients.py"],
        "aliases": ["FACEBOOK_ACCESS_TOKEN", "FACEBOOK_GRAPH_ACCESS_TOKEN", "INSTAGRAM_ACCESS_TOKEN"],
    },
    "AZURE_OPENAI_API_KEY": {
        "purpose": "Azure-hosted OpenAI integration",
        "used_by": ["premium AI helper routes"],
        "aliases": [],
    },
    "THEODDS_API_KEY": {
        "purpose": "Sports odds data for EV scanning",
        "used_by": ["dk_alpha_autopilot.py", "sports_odds_engine.py"],
        "aliases": ["ODDS_API_KEY", "SPORTS_ODDS_API_KEY"],
    },
    "FINNHUB_API_KEY": {
        "purpose": "Market data / fundamentals",
        "used_by": ["adaptive universe + research signals"],
        "aliases": [],
    },
    "ALPHAVANTAGE_API_KEY": {
        "purpose": "Market/economic time series backup feed",
        "used_by": ["adaptive universe + feed fallback"],
        "aliases": [],
    },
    "TWELVE_DATA_API_KEY": {
        "purpose": "Alternative market data feed",
        "used_by": ["adaptive universe + feed fallback"],
        "aliases": [],
    },
    "BINANCE_API_KEY": {
        "purpose": "Binance market/execution data",
        "used_by": ["binance_get_deposit_address.py", "multi-exchange research"],
        "aliases": [],
    },
    "BINANCE_API_SECRET": {
        "purpose": "Binance secret",
        "used_by": ["binance_get_deposit_address.py", "multi-exchange research"],
        "aliases": [],
    },
    "PAYOUT_WEBHOOK_AUTH_BEARER": {
        "purpose": "Authenticates payout webhook receiver",
        "used_by": ["execution/payout_webhook_receiver.py"],
        "aliases": [],
    },
    "LUMA_PAYOUT_TOKEN": {
        "purpose": "Payout bridge auth token",
        "used_by": ["execution/payout_bridge.py"],
        "aliases": [],
    },
    "LUMA_LIVE_SYNC_WEBHOOK": {
        "purpose": "Pushes live sync events between engines",
        "used_by": ["sync hooks + automations"],
        "aliases": ["LIVE_SYNC_WEBHOOK_URL"],
    },
    "WEBHOOK_SHARED_SECRET": {
        "purpose": "Shared secret for signed webhook events",
        "used_by": ["execution webhook handlers"],
        "aliases": [],
    },
    "MASSIVE_API_KEY": {
        "purpose": "Custom premium source or internal service auth",
        "used_by": ["premium source integrations"],
        "aliases": [],
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env_nonsecret() -> Dict[str, str]:
    env: Dict[str, str] = {}
    for key, value in os.environ.items():
        if isinstance(value, str) and value.strip():
            env[key] = value

    for path in ENV_CANDIDATES:
        if not path.exists():
            continue
        try:
            for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            continue
    return env


def discover_keys_from_code() -> List[str]:
    keys: set[str] = set()
    rx = re.compile(r"(?:os\.environ\.get|os\.getenv|env\.get)\(\s*['\"]([A-Z0-9_]+)['\"]")
    for path in CODE.rglob("*.py"):
        if any(part in {".venv", "venv", "archive", "__pycache__"} for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for match in rx.finditer(text):
            key = match.group(1).strip()
            if key:
                keys.add(key)
    return sorted(keys)


def key_present(env: Dict[str, str], key: str, aliases: List[str]) -> bool:
    names = [key] + list(aliases)
    for name in names:
        value = str(env.get(name, "") or "").strip()
        if value:
            return True
    return False


def build_report() -> Dict[str, Any]:
    env = load_env_nonsecret()
    discovered = discover_keys_from_code()

    merged = dict(KEY_PURPOSES)
    for key in discovered:
        if key not in merged and any(t in key for t in ("API", "KEY", "SECRET", "TOKEN", "WEBHOOK", "PASS")):
            merged[key] = {
                "purpose": "Discovered in code scan; classify and map to owner engine",
                "used_by": ["auto-discovered"],
                "aliases": [],
            }

    rows: List[Dict[str, Any]] = []
    for key in sorted(merged.keys()):
        meta = merged[key]
        aliases = list(meta.get("aliases", []))
        rows.append(
            {
                "key": key,
                "present": key_present(env, key, aliases),
                "aliases": aliases,
                "purpose": str(meta.get("purpose", "")),
                "used_by": list(meta.get("used_by", [])),
            }
        )

    present_count = sum(1 for row in rows if row.get("present"))

    return {
        "generated_utc": now_utc(),
        "schema": "api_key_registry_report_v1",
        "total_keys": len(rows),
        "present_keys": present_count,
        "missing_keys": len(rows) - present_count,
        "coverage_pct": round((present_count / max(len(rows), 1)) * 100.0, 2),
        "rows": rows,
        "notes": [
            "Values are never stored here; only presence booleans and purpose mapping.",
            "Use this for route ownership and avoiding crossed engine roots.",
        ],
    }


def main() -> int:
    payload = build_report()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[api-keys] wrote {OUT_FILE}")
    print(
        f"[api-keys] present={payload['present_keys']}/{payload['total_keys']} "
        f"coverage={payload['coverage_pct']:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
