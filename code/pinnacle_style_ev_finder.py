"""
Pinnacle-style +EV finder.
Uses Pinnacle as the no-vig sharp reference. For each outcome DraftKings offers,
we strip Pinnacle's vig across ALL outcomes in the same market (handles 2-way AND
3-way soccer/draw markets correctly) and check if DK price > fair price.
"""
import json
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
SPORTS_DIR = ROOT / "sports_data"


def no_vig_fair_nway(prices: list[float], idx: int) -> float:
    """Return the no-vig fair price for outcome[idx] across an N-outcome market."""
    imps = [1 / p for p in prices]
    total = sum(imps)
    return 1 / (imps[idx] / total)


def to_american(d: float) -> str:
    if d >= 2.0:
        return f"+{int(round((d - 1) * 100))}"
    return f"-{int(round(100 / (d - 1)))}"


def scan_file(path: Path, sport_label: str, min_edge: float = 1.0) -> list[dict]:
    data = json.loads(path.read_text())
    results = []

    for ev in data:
        game = f"{ev.get('away_team', '')} @ {ev.get('home_team', '')}"

        # Index books: {bm_key: {mk::point: [(name, price), ...]}}
        books: dict[str, dict] = {}
        for bm in ev.get("bookmakers", []):
            bk = bm["key"]
            books[bk] = {}
            for mkt in bm.get("markets", []):
                mk = mkt["key"]
                if mk not in ("h2h", "spreads", "totals"):
                    continue
                for oc in mkt.get("outcomes", []):
                    name = oc["name"]
                    point = oc.get("point", "")
                    market_key = f"{mk}::{point}"
                    if market_key not in books[bk]:
                        books[bk][market_key] = []
                    books[bk][market_key].append((name, oc["price"]))

        dk = books.get("draftkings", {})
        pin = books.get("pinnacle", {})

        if not dk or not pin:
            continue

        # For each market Pinnacle covers, compute N-way no-vig fair prices
        for market_key, pin_outcomes in pin.items():
            if market_key not in dk:
                continue
            dk_outcomes = dk[market_key]

            if len(pin_outcomes) < 2:
                continue

            mk, point = market_key.split("::", 1)

            # Build name->fair from Pinnacle N-way no-vig
            pin_prices = [pr for _, pr in pin_outcomes]
            pin_fair = {
                name: no_vig_fair_nway(pin_prices, i)
                for i, (name, _) in enumerate(pin_outcomes)
            }

            # Compare each DK outcome to Pinnacle fair
            for name, dk_price in dk_outcomes:
                if name not in pin_fair:
                    continue
                fair = pin_fair[name]
                edge = (dk_price / fair - 1) * 100
                pin_this = next((pr for n, pr in pin_outcomes if n == name), None)
                if edge < min_edge:
                    continue
                results.append({
                    "sport": sport_label,
                    "game": game,
                    "market": mk,
                    "pick": name,
                    "point": point,
                    "dk_price": dk_price,
                    "pin_price": pin_this,
                    "fair_price": round(fair, 3),
                    "edge_pct": round(edge, 2),
                })

    return results


# ---- main -------------------------------------------------------------------

def main():
    all_edges = []

    # Auto-discover every allbooks file in sports_data/
    all_paths = sorted(SPORTS_DIR.glob("*_allbooks_live_odds.json"))

    for path in all_paths:
        sport_key = path.name.replace("_allbooks_live_odds.json", "")
        sport_label = sport_key.replace("_", " ").title()
        edges = scan_file(path, sport_label, min_edge=-99.0)
        all_edges.extend(edges)

    all_edges.sort(key=lambda x: -x["edge_pct"])

    pos = [e for e in all_edges if e["edge_pct"] >= 0]
    neg = [e for e in all_edges if e["edge_pct"] < 0]

    print(f"\n{'='*100}")
    print(f"  PINNACLE +EV FINDER  |  DraftKings vs Pinnacle No-Vig Fair")
    print(f"{'='*100}")
    if pos:
        print(f"\n  *** GENUINE +EV (DK beats Pinnacle fair price) ***")
        for e in pos:
            pt = f" ({e['point']})" if str(e["point"]) else ""
            print(
                f"  [{e['edge_pct']:+5.1f}%]  {e['sport']:14s}  {e['game'][:38]:38s}  "
                f"{e['market']:8s}  {e['pick'][:22]:22s}{pt}  "
                f"DK={e['dk_price']:.3f}({to_american(e['dk_price'])})  "
                f"PIN={e['pin_price']:.3f}  fair={e['fair_price']:.3f}"
            )
    else:
        print("\n  No outright +EV vs Pinnacle today (normal — DK prices below Pinnacle).")

    print(f"\n  --- CLOSEST TO FAIR VALUE (best DK lines, least vig vs Pinnacle) ---")
    for e in neg[:15]:
        pt = f" ({e['point']})" if str(e["point"]) else ""
        print(
            f"  [{e['edge_pct']:+5.1f}%]  {e['sport']:14s}  {e['game'][:38]:38s}  "
            f"{e['market']:8s}  {e['pick'][:22]:22s}{pt}  "
            f"DK={e['dk_price']:.3f}({to_american(e['dk_price'])})  "
            f"PIN={e['pin_price']:.3f}  fair={e['fair_price']:.3f}"
        )

    print(f"\n+EV spots: {len(pos)}  |  Total comparisons: {len(all_edges)}")


if __name__ == "__main__":
    main()
