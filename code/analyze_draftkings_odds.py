import json
from pathlib import Path

data = json.loads(Path(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\sports_data\basketball_nba_draftkings_live_odds.json').read_text())
print(f"Events loaded: {len(data)}")

rows = []
for ev in data:
    home = ev.get("home_team", "")
    away = ev.get("away_team", "")
    ct = ev.get("commence_time", "")
    for bm in ev.get("bookmakers", []):
        if bm["key"] != "draftkings":
            continue
        for mkt in bm.get("markets", []):
            mk = mkt["key"]
            for oc in mkt.get("outcomes", []):
                rows.append({
                    "game": f"{away} @ {home}",
                    "commence": ct,
                    "market": mk,
                    "name": oc["name"],
                    "price": oc.get("price", 0),
                    "point": oc.get("point", ""),
                })

# TOP MONEYLINE VALUE (highest underdog odds worth watching)
print("\n=== TOP H2H MONEYLINES (dogs / value) ===")
h2h = [r for r in rows if r["market"] == "h2h"]
h2h.sort(key=lambda x: -x["price"])
for r in h2h[:15]:
    pt = f"  ({r['point']})" if r["point"] != "" else ""
    print(f"  {r['game'][:42]:42s} | {r['name']:25s} | {r['price']:.2f}{pt}")

# BEST SPREAD LINES — both sides priced 1.85-1.96 = market agrees, good action
print("\n=== BALANCED SPREAD LINES (both sides 1.85-1.96) ===")
spreads = {}
for r in rows:
    if r["market"] != "spreads":
        continue
    spreads.setdefault(r["game"], []).append(r)

count = 0
for g, sides in spreads.items():
    if len(sides) < 2:
        continue
    p1, p2 = sides[0]["price"], sides[1]["price"]
    if 1.85 <= p1 <= 1.96 and 1.85 <= p2 <= 1.96:
        print(
            f"  {g[:42]:42s} | "
            f"{sides[0]['name']:22s} {p1:.2f} ({sides[0]['point']}) vs "
            f"{sides[1]['name']:22s} {p2:.2f} ({sides[1]['point']})"
        )
        count += 1
if count == 0:
    print("  None found.")

# BEST TOTALS — both sides near equal (market consensus)
print("\n=== CONSENSUS TOTALS (both sides 1.85-1.96) ===")
totals = {}
for r in rows:
    if r["market"] != "totals":
        continue
    totals.setdefault(r["game"], []).append(r)

count = 0
for g, sides in totals.items():
    if len(sides) < 2:
        continue
    p1, p2 = sides[0]["price"], sides[1]["price"]
    if 1.85 <= p1 <= 1.96 and 1.85 <= p2 <= 1.96:
        print(
            f"  {g[:42]:42s} | "
            f"{sides[0]['name']:10s} {p1:.2f} ({sides[0]['point']}) vs "
            f"{sides[1]['name']:10s} {p2:.2f} ({sides[1]['point']})"
        )
        count += 1
if count == 0:
    print("  None found.")

# SUMMARY
print(f"\nTotal DK odds records: {len(rows)}")
