from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
ENV = ROOT / "code" / "execution" / "config" / "luma_live_keys.env"
OUT = ROOT / "sports_data" / "props_ev_results.json"


if ENV.exists():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key and not os.getenv(key):
            os.environ[key] = value


API_KEY = (
    os.getenv("THEODDS_API_KEY")
    or os.getenv("ODDS_API_KEY")
    or os.getenv("SPORTS_ODDS_API_KEY")
    or ""
)
API_BASE = "https://api.the-odds-api.com/v4"


SPORT_MARKETS: dict[str, str] = {
    "basketball_nba": "h2h,spreads,totals",
    "baseball_mlb": "h2h,spreads,totals",
    "americanfootball_ufl": "h2h,spreads,totals",
    "icehockey_nhl": "h2h,spreads,totals",
    "mma_mixed_martial_arts": "h2h",
    "boxing_boxing": "h2h",
    "aussierules_afl": "h2h,spreads,totals",
    "rugbyleague_nrl": "h2h,spreads,totals",
    "soccer_epl": "h2h,spreads,totals",
    "soccer_usa_mls": "h2h,spreads,totals",
    "soccer_uefa_champs_league": "h2h,spreads,totals",
    "tennis_atp_madrid_open": "h2h",
    "tennis_wta_madrid_open": "h2h",
}


def fetch_events(sport: str, markets: str) -> list[dict[str, Any]]:
    r = requests.get(
        f"{API_BASE}/sports/{sport}/odds",
        params={
            "apiKey": API_KEY,
            "regions": "us,uk,eu",
            "markets": markets,
            "bookmakers": "draftkings,pinnacle",
            "oddsFormat": "decimal",
            "dateFormat": "iso",
        },
        timeout=40,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def no_vig_nway(prices: list[float], idx: int) -> float:
    implied = [1.0 / p for p in prices]
    total = sum(implied)
    return 1.0 / (implied[idx] / total)


def main() -> int:
    if not API_KEY:
        print("ERROR: Missing ODDS API KEY")
        return 2

    now = datetime.now(timezone.utc)
    edges: list[dict[str, Any]] = []

    for sport, markets in SPORT_MARKETS.items():
        try:
            events = fetch_events(sport, markets)
        except Exception as exc:
            print(f"SKIP {sport}: {exc}")
            continue

        for ev in events:
            commence = ev.get("commence_time")
            if not commence:
                continue
            start = datetime.fromisoformat(commence.replace("Z", "+00:00"))
            hours = (start - now).total_seconds() / 3600

            books: dict[str, dict[str, dict[str, float]]] = {}
            for bm in ev.get("bookmakers", []):
                bk = bm.get("key", "")
                books[bk] = {}
                for market in bm.get("markets", []):
                    mk = market.get("key", "")
                    for oc in market.get("outcomes", []):
                        name = oc.get("name", "")
                        if not name:
                            continue
                        price = oc.get("price")
                        if not isinstance(price, (int, float)):
                            continue
                        desc = oc.get("description", "")
                        point = oc.get("point", "")
                        group = f"{mk}::{desc}::{point}"
                        books[bk].setdefault(group, {})[name] = float(price)

            dk = books.get("draftkings", {})
            pin = books.get("pinnacle", {})
            if not dk or not pin:
                continue

            away = ev.get("away_team", "")
            home = ev.get("home_team", "")
            game = f"{away} @ {home}".strip()

            for group, pin_map in pin.items():
                if group not in dk:
                    continue
                dk_map = dk[group]
                if len(pin_map) < 2:
                    continue

                names = list(pin_map.keys())
                pin_prices = [pin_map[n] for n in names]
                fair = {n: no_vig_nway(pin_prices, i) for i, n in enumerate(names)}

                for pick, dk_price in dk_map.items():
                    if pick not in fair:
                        continue
                    edge = (dk_price / fair[pick] - 1.0) * 100.0
                    if edge < 1.0:
                        continue

                    mk, desc, point = group.split("::", 2)
                    status = "LIVE/STARTED" if hours <= 0 else (
                        "TONIGHT" if start.date() == now.date() else "UPCOMING"
                    )

                    edges.append(
                        {
                            "edge_pct": round(edge, 2),
                            "sport": sport,
                            "game": game,
                            "market": mk,
                            "description": desc,
                            "pick": pick,
                            "point": point,
                            "dk_price": round(float(dk_price), 3),
                            "pin_price": round(float(pin_map.get(pick, 0.0)), 3),
                            "fair_price": round(float(fair[pick]), 3),
                            "commence_time": commence,
                            "hours_to_start": round(hours, 2),
                            "status": status,
                        }
                    )

    edges.sort(key=lambda x: (-x["edge_pct"], x["hours_to_start"]))
    OUT.write_text(json.dumps({"generated_utc": now.isoformat(), "rows": edges}, indent=2), encoding="utf-8")

    print(f"FOUND={len(edges)}")
    print("TOP_25")
    for row in edges[:25]:
        d = (row["description"] + " ").strip()
        print(
            f"[{row['edge_pct']:>5.1f}%] {row['status']:12} {row['hours_to_start']:>7.2f}h "
            f"{row['sport']} {row['game']} {row['market']} {d}{row['pick']} "
            f"pt={row['point']} DK={row['dk_price']} fair={row['fair_price']} UTC={row['commence_time']}"
        )

    print("NEXT_12H_TOP_20")
    near = [x for x in edges if x["hours_to_start"] <= 12]
    for row in near[:20]:
        d = (row["description"] + " ").strip()
        print(
            f"[{row['edge_pct']:>5.1f}%] {row['status']:12} {row['hours_to_start']:>7.2f}h "
            f"{row['sport']} {row['game']} {row['market']} {d}{row['pick']} "
            f"pt={row['point']} DK={row['dk_price']} fair={row['fair_price']} UTC={row['commence_time']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
