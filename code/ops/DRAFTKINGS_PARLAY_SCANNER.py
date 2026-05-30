"""
DRAFTKINGS_PARLAY_SCANNER.py
============================
Live DraftKings odds scanner + parlay EV engine.
Pulls real-time lines, calculates implied probability, finds high-payout
parlay combinations, and scores expected value.

Usage:
    python DRAFTKINGS_PARLAY_SCANNER.py --sport nba --legs 3 --target-payout 1000
    python DRAFTKINGS_PARLAY_SCANNER.py --sport nfl --legs 4 --target-payout 5000
    python DRAFTKINGS_PARLAY_SCANNER.py --scan-all --legs 4 --min-payout 500

Output:
    out/ops/dk_parlay_scan_latest.json  (machine-readable)
    out/ops/dk_parlay_scan_latest.md    (human-readable)
"""

import argparse
import itertools
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT   = SCRIPT_DIR.parent.parent
OUT_DIR     = REPO_ROOT / "out" / "ops"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── DraftKings public API ──────────────────────────────────────────────────────
DK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://sportsbook.draftkings.com/",
}

DK_SPORTS = {
    "nfl":      88808,
    "nba":      42648,
    "nhl":      42133,
    "mlb":      84240,
    "ncaafb":   87637,
    "ncaabb":   92483,
    "soccer":   1,
    "mma":      9,
    "boxing":   9,
    "golf":     2,
    "tennis":   34,
}

# Spreads / moneylines / totals category IDs (varies by sport)
DK_CATEGORY_MONEYLINE = {
    "nfl":  "Moneyline",
    "nba":  "Moneyline",
    "nhl":  "Moneyline",
    "mlb":  "Moneyline",
}

DK_BASE = "https://sportsbook-nash.draftkings.com/sites/US-SB/api/v5"


# ── odds conversion ────────────────────────────────────────────────────────────

def american_to_implied_prob(american: int) -> float:
    """Convert American odds to implied probability (0-1)."""
    if american >= 0:
        return 100 / (american + 100)
    else:
        return abs(american) / (abs(american) + 100)


def implied_prob_to_american(prob: float) -> int:
    """Convert implied probability back to American odds."""
    if prob <= 0 or prob >= 1:
        return 0
    if prob >= 0.5:
        return round(-prob / (1 - prob) * 100)
    else:
        return round((1 - prob) / prob * 100)


def american_to_decimal(american: int) -> float:
    """Convert American odds to decimal multiplier."""
    if american >= 0:
        return (american / 100) + 1.0
    else:
        return (100 / abs(american)) + 1.0


def parlay_payout(legs: list[int], stake: float = 100.0) -> float:
    """Calculate parlay payout for a list of American odds lines."""
    multiplier = 1.0
    for odds in legs:
        multiplier *= american_to_decimal(odds)
    return multiplier * stake


def parlay_true_prob(legs_probs: list[float]) -> float:
    """True probability that ALL legs hit (independent assumption)."""
    prob = 1.0
    for p in legs_probs:
        prob *= p
    return prob


def parlay_ev(legs: list[int], stake: float = 100.0) -> dict:
    """Full EV breakdown for a parlay."""
    probs = [american_to_implied_prob(o) for o in legs]
    true_prob = parlay_true_prob(probs)
    payout    = parlay_payout(legs, stake)
    ev        = (true_prob * payout) - stake
    ev_pct    = ev / stake * 100
    return {
        "payout_if_win":   round(payout, 2),
        "true_probability": round(true_prob * 100, 4),
        "ev_dollars":      round(ev, 2),
        "ev_pct":          round(ev_pct, 2),
        "payout_multiple": round(payout / stake, 1),
    }


# ── DraftKings fetch ───────────────────────────────────────────────────────────

def fetch_event_group(sport_id: int, timeout: int = 15) -> dict:
    url = f"{DK_BASE}/eventgroups/{sport_id}?format=json"
    try:
        resp = requests.get(url, headers=DK_HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"  [WARN] fetch failed for sport_id={sport_id}: {e}")
        return {}


def extract_moneylines(data: dict, sport_key: str) -> list[dict]:
    """
    Walk the DraftKings event group JSON and extract moneyline markets.
    Returns list of {event, team, odds_american, implied_prob, game_time}.
    """
    lines = []
    try:
        event_group = data.get("eventGroup", {})
        offer_categories = event_group.get("offerCategories", [])

        for cat in offer_categories:
            cat_name = cat.get("name", "").lower()
            # moneyline / game lines / match lines
            if not any(kw in cat_name for kw in ["moneyline", "game lines", "match result", "to win"]):
                continue

            for sub_cat in cat.get("offerSubcategoryDescriptors", []):
                for offer_cat in sub_cat.get("offerSubcategory", {}).get("offers", []):
                    for offer in offer_cat:
                        event_name  = offer.get("label", "Unknown Game")
                        game_time   = offer.get("outcomes", [{}])[0].get("providerId", "")

                        for outcome in offer.get("outcomes", []):
                            label = outcome.get("label", "")
                            odds  = outcome.get("oddsAmerican", None)
                            if odds is None:
                                # Try oddsDecimal fallback
                                dec = outcome.get("oddsDecimal")
                                if dec:
                                    odds = implied_prob_to_american(1 / float(dec))
                            if odds is not None:
                                try:
                                    odds_int = int(str(odds).replace("+", ""))
                                    lines.append({
                                        "sport":         sport_key,
                                        "event":         event_name,
                                        "selection":     label,
                                        "odds_american": odds_int,
                                        "implied_prob":  round(american_to_implied_prob(odds_int) * 100, 2),
                                        "decimal":       round(american_to_decimal(odds_int), 3),
                                    })
                                except (ValueError, TypeError):
                                    pass
    except Exception as e:
        print(f"  [WARN] parse error for {sport_key}: {e}")
    return lines


def fetch_sport_lines(sport_key: str) -> list[dict]:
    sport_id = DK_SPORTS.get(sport_key)
    if not sport_id:
        print(f"  [SKIP] unknown sport: {sport_key}")
        return []
    print(f"  Fetching {sport_key.upper()} (event_group={sport_id})...")
    data  = fetch_event_group(sport_id)
    lines = extract_moneylines(data, sport_key)
    print(f"    → {len(lines)} moneylines extracted")
    return lines


# ── parlay finder ─────────────────────────────────────────────────────────────

def find_best_parlays(
    all_lines: list[dict],
    n_legs: int = 3,
    target_payout: float = 1000.0,
    stake: float = 100.0,
    top_n: int = 25,
    min_prob_per_leg: float = 0.0,
    max_combinations: int = 50_000,
) -> list[dict]:
    """
    Find parlay combinations that:
    - Hit or exceed target_payout
    - Are from DIFFERENT events (no same-game parlays unless allowed)
    - Sorted by best EV descending
    """
    # Deduplicate: one pick per event (best odds / highest payout potential per event)
    from collections import defaultdict
    events: dict[str, list[dict]] = defaultdict(list)
    for line in all_lines:
        if line["implied_prob"] / 100 >= min_prob_per_leg:
            events[line["event"]].append(line)

    # Flatten to one candidate per selection (keep all, filter at combo level)
    candidates = [line for lines in events.values() for line in lines]

    # Sort by decimal odds descending — bigger upside first
    candidates.sort(key=lambda x: x["decimal"], reverse=True)

    # Cap candidates to keep combination count manageable
    max_candidates = min(len(candidates), 60)
    pool = candidates[:max_candidates]

    print(f"  Building {n_legs}-leg combos from {len(pool)} candidates "
          f"(capped from {len(candidates)})...")

    results   = []
    checked   = 0
    skipped   = 0

    for combo in itertools.combinations(pool, n_legs):
        checked += 1
        if checked > max_combinations:
            print(f"  [INFO] combo cap hit ({max_combinations:,}), truncating search")
            break

        # Must be different events
        event_names = {leg["event"] for leg in combo}
        if len(event_names) < n_legs:
            skipped += 1
            continue

        odds_list = [leg["odds_american"] for leg in combo]
        ev_data   = parlay_ev(odds_list, stake)

        if ev_data["payout_if_win"] < target_payout:
            continue

        results.append({
            "legs":             [{"event": l["event"], "pick": l["selection"],
                                  "odds": l["odds_american"],
                                  "implied_prob_pct": l["implied_prob"],
                                  "sport": l["sport"]} for l in combo],
            "n_legs":           n_legs,
            "payout_if_win":    ev_data["payout_if_win"],
            "true_prob_pct":    ev_data["true_probability"],
            "ev_dollars":       ev_data["ev_dollars"],
            "ev_pct":           ev_data["ev_pct"],
            "payout_multiple":  ev_data["payout_multiple"],
            "stake":            stake,
        })

    print(f"  Checked {checked:,} combos, skipped {skipped:,} same-event, "
          f"found {len(results)} above {target_payout}x target")

    # Sort by ev_dollars desc, then payout_multiple desc
    results.sort(key=lambda x: (x["ev_dollars"], x["payout_multiple"]), reverse=True)
    return results[:top_n]


# ── main ──────────────────────────────────────────────────────────────────────

def run_scan(
    sports:         list[str],
    n_legs:         int   = 3,
    target_payout:  float = 1000.0,
    stake:          float = 100.0,
    top_n:          int   = 25,
    min_prob_leg:   float = 0.0,
) -> dict:
    ts  = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"\n{'='*60}")
    print(f"  DRAFTKINGS PARLAY SCANNER  |  {ts}")
    print(f"  Sports: {sports}  |  Legs: {n_legs}  |  Target: ${target_payout}")
    print(f"{'='*60}")

    all_lines = []
    for sport in sports:
        lines = fetch_sport_lines(sport)
        all_lines.extend(lines)
        time.sleep(0.5)  # polite rate limit

    if not all_lines:
        print("\n  [WARN] No lines fetched. DK API may be down or no live games.")
        result = {
            "generated_utc": ts,
            "sports":        sports,
            "n_legs":        n_legs,
            "target_payout": target_payout,
            "stake":         stake,
            "total_lines":   0,
            "parlays":       [],
            "warning":       "No live lines available at this time.",
        }
    else:
        print(f"\n  Total lines: {len(all_lines)} across {len(sports)} sport(s)")
        parlays = find_best_parlays(
            all_lines,
            n_legs=n_legs,
            target_payout=target_payout,
            stake=stake,
            top_n=top_n,
            min_prob_per_leg=min_prob_leg,
        )

        result = {
            "generated_utc": ts,
            "sports":        sports,
            "n_legs":        n_legs,
            "target_payout": target_payout,
            "stake":         stake,
            "total_lines":   len(all_lines),
            "top_parlays_found": len(parlays),
            "parlays":       parlays,
        }

    # ── write outputs ──
    json_path = OUT_DIR / "dk_parlay_scan_latest.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n  ✓ JSON  → {json_path}")

    # ── human-readable markdown ──
    md_lines = [
        f"# DraftKings Parlay Scanner — {ts}",
        f"**Sports:** {', '.join(sports)}  |  **Legs:** {n_legs}  |  **Stake:** ${stake}  |  **Target payout:** ${target_payout}",
        f"**Lines scanned:** {result.get('total_lines', 0)}  |  **Parlays found:** {result.get('top_parlays_found', 0)}",
        "",
    ]

    for i, p in enumerate(result.get("parlays", []), 1):
        md_lines.append(f"## #{i} — {p['payout_multiple']}x Payout | EV: ${p['ev_dollars']} ({p['ev_pct']}%)")
        md_lines.append(f"**Win ${p['payout_if_win']:,.0f}** on ${p['stake']} stake | True prob: {p['true_prob_pct']}%")
        md_lines.append("")
        for leg in p["legs"]:
            odds_str = f"+{leg['odds']}" if leg["odds"] > 0 else str(leg["odds"])
            md_lines.append(f"- **{leg['pick']}** ({leg['event']}) — {odds_str} ({leg['implied_prob_pct']}% implied)")
        md_lines.append("")

    md_path = OUT_DIR / "dk_parlay_scan_latest.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"  ✓ MD   → {md_path}")

    # ── console summary ──
    print(f"\n{'='*60}")
    print(f"  TOP PARLAYS  (${stake} stake → hit ${target_payout}+)")
    print(f"{'='*60}")
    for i, p in enumerate(result.get("parlays", [])[:10], 1):
        print(f"\n  #{i}  {p['payout_multiple']}x  |  WIN ${p['payout_if_win']:>10,.0f}  "
              f"|  True prob: {p['true_prob_pct']:>6.3f}%  |  EV: ${p['ev_dollars']:>8.2f}")
        for leg in p["legs"]:
            odds_str = f"+{leg['odds']}" if leg["odds"] > 0 else str(leg["odds"])
            print(f"       {'•'} {leg['pick']:<30} {odds_str:<8} {leg['event']}")

    print(f"\n{'='*60}")
    print(f"  Scan complete. Full results → {json_path.name}")
    print(f"{'='*60}\n")

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DraftKings live parlay scanner")
    parser.add_argument("--sport",        default="nba",  help="Sport key (nba, nfl, nhl, mlb, ...)")
    parser.add_argument("--scan-all",     action="store_true", help="Scan all available sports")
    parser.add_argument("--legs",         type=int,   default=3,    help="Number of parlay legs")
    parser.add_argument("--target-payout",type=float, default=1000, help="Min payout target ($) per $100 stake")
    parser.add_argument("--stake",        type=float, default=100,  help="Stake amount ($)")
    parser.add_argument("--top-n",        type=int,   default=25,   help="Max parlays to return")
    parser.add_argument("--min-prob-leg", type=float, default=0.0,  help="Min implied prob per leg (0-1)")
    args = parser.parse_args()

    if args.scan_all:
        sports = list(DK_SPORTS.keys())
    else:
        sports = [args.sport.lower()]

    run_scan(
        sports=sports,
        n_legs=args.legs,
        target_payout=args.target_payout,
        stake=args.stake,
        top_n=args.top_n,
        min_prob_leg=args.min_prob_leg,
    )
