#!/usr/bin/env python3
"""
Sports Odds Engine — Production-grade, per-event watcher
=========================================================
Scans all sports_data/*_live_odds.json files and detects:
  1. TRUE ARBITRAGE     — sum(1/best_back_odds per outcome) < 1.0
                          across different bookmakers for the same market
  2. VALUE BETS         — one book's implied probability is significantly
                          BELOW the consensus market implied probability
                          (meaning they're offering much better odds than everyone else)
  3. LINE GAPS          — extreme price dispersion across books (>15%) on
                          same outcome; indicates steam move or book error

Outputs (atomic writes to out/sports_signals/):
  _live_signals.json    — top-ranked combined signals
  _arbitrage_only.json  — confirmed arbs only
  _value_bets.json      — value bet signals only
  _sports_summary.json  — per-sport breakdown + meta

Runs as a daemon loop. Set env vars:
  SPORTS_SCAN_SEC   — seconds between full re-scans (default: 30)
  SPORTS_TOP_N      — how many signals to include in _live_signals (default: 50)

Usage:
  python sports_odds_engine.py
  # or via RUN_SPORTS_ODDS_ENGINE.ps1
"""

import json
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Configuration ─────────────────────────────────────────────────────────────

ROOT_DIR      = Path(__file__).resolve().parent.parent
SPORTS_DIR    = ROOT_DIR / "sports_data"
OUT_DIR       = ROOT_DIR / "out" / "sports_signals"
STATE_DIR     = ROOT_DIR / "out" / "sports_states"

SCAN_INTERVAL = float(os.environ.get("SPORTS_SCAN_SEC", "30"))
TOP_N         = int(os.environ.get("SPORTS_TOP_N", "50"))

# True arbitrage threshold: arb_sum < this → confirmed arb
ARB_THRESHOLD = 1.0

# Value bet: a book's implied probability must be at least this much BELOW
# the consensus implied probability to be flagged as a value bet
# e.g. 0.04 = 4 percentage points better than market consensus
VALUE_EDGE_MIN_PCT = float(os.environ.get("SPORTS_VALUE_EDGE_MIN", "4.0"))  # %

# Line gap: best_price / worst_price ratio must exceed this to flag
LINE_GAP_MIN_PCT = 15.0  # %

# Exchange bookmakers that offer lay (back-against) markets —
# exclude from arbitrage sum calculations since lay ≠ back
LAY_BOOK_KEYS = frozenset({
    "betfair_ex_uk", "betfair_ex_eu",
    "smarkets", "matchbook",
})

# Markets to process for arb/value detection
TARGET_MARKETS = ("h2h", "spreads", "totals")


# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class OddsSignal:
    event_id:       str
    sport_key:      str
    sport_title:    str
    home_team:      str
    away_team:      str
    commence_time:  str
    signal_type:    str   # "arbitrage" | "value_bet" | "line_gap"
    market:         str
    outcome:        str
    best_book:      str
    best_odds:      float
    worst_book:     str
    worst_odds:     float
    edge_pct:       float  # guaranteed return % (arb) or value edge % (value_bet)
    consensus_odds: float  # market average odds for this outcome
    implied_prob:   float  # best book implied probability
    consensus_prob: float  # consensus implied probability
    arb_legs:       List[Dict]  # arb only — list of {outcome, book, odds, stake_frac}
    n_books:        int    # how many bookmakers priced this outcome
    scanned_utc:    str
    score:          float  # ranking score (higher = better)


# ── Utilities ─────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, data: Any) -> None:
    """Write JSON atomically — tmp file then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


# ── Price Extraction ──────────────────────────────────────────────────────────

def _best_back_per_outcome(event: Dict, market_key: str) -> Dict[str, Tuple[float, str]]:
    """
    For each outcome in market_key, find the best back price across all
    non-exchange bookmakers.
    Returns {outcome_name: (best_price, bookmaker_key)}
    """
    bests: Dict[str, Tuple[float, str]] = {}
    for bk in event.get("bookmakers", []):
        bk_key = bk.get("key", "")
        if bk_key in LAY_BOOK_KEYS:
            continue
        for mkt in bk.get("markets", []):
            if mkt.get("key") != market_key:
                continue
            for oc in mkt.get("outcomes", []):
                name  = str(oc.get("name", "")).strip()
                price = float(oc.get("price", 0) or 0)
                if price <= 1.0 or not name:
                    continue
                if name not in bests or price > bests[name][0]:
                    bests[name] = (price, bk_key)
    return bests


def _all_back_prices(event: Dict, market_key: str, outcome_name: str) -> List[Tuple[float, str]]:
    """
    All back (price, bookmaker_key) pairs for a specific outcome in market_key.
    Excludes exchange lay books.
    """
    results: List[Tuple[float, str]] = []
    for bk in event.get("bookmakers", []):
        bk_key = bk.get("key", "")
        if bk_key in LAY_BOOK_KEYS:
            continue
        for mkt in bk.get("markets", []):
            if mkt.get("key") != market_key:
                continue
            for oc in mkt.get("outcomes", []):
                if str(oc.get("name", "")).strip() == outcome_name:
                    price = float(oc.get("price", 0) or 0)
                    if price > 1.0:
                        results.append((price, bk_key))
    return results


# ── Signal Detection ──────────────────────────────────────────────────────────

def _detect_arbitrage(event: Dict, market_key: str) -> Optional[OddsSignal]:
    """
    TRUE cross-bookmaker arbitrage: sum(1/best_price per outcome) < 1.0
    This guarantees a profit regardless of outcome.
    """
    bests = _best_back_per_outcome(event, market_key)
    if len(bests) < 2:
        return None

    arb_sum = sum(1.0 / price for price, _ in bests.values())
    if arb_sum >= ARB_THRESHOLD:
        return None

    # Confirmed arbitrage — calculate details
    guaranteed_return_pct = (1.0 / arb_sum - 1.0) * 100.0

    # Kelly-normalized stake fractions (stake_frac × total_capital = stake on that leg)
    legs = []
    for name, (price, book) in bests.items():
        stake_frac = round((1.0 / price) / arb_sum, 6)
        legs.append({
            "outcome":    name,
            "book":       book,
            "odds":       price,
            "stake_frac": stake_frac,
        })
    legs.sort(key=lambda x: -x["odds"])

    return OddsSignal(
        event_id      = event.get("id", ""),
        sport_key     = event.get("sport_key", ""),
        sport_title   = event.get("sport_title", ""),
        home_team     = event.get("home_team", ""),
        away_team     = event.get("away_team", ""),
        commence_time = event.get("commence_time", ""),
        signal_type   = "arbitrage",
        market        = market_key,
        outcome       = " | ".join(bests.keys()),
        best_book     = legs[0]["book"],
        best_odds     = legs[0]["odds"],
        worst_book    = legs[-1]["book"],
        worst_odds    = legs[-1]["odds"],
        edge_pct      = round(guaranteed_return_pct, 4),
        consensus_odds= 0.0,
        implied_prob  = round(arb_sum, 6),
        consensus_prob= 0.0,
        arb_legs      = legs,
        n_books       = len(event.get("bookmakers", [])),
        scanned_utc   = _now_utc(),
        score         = guaranteed_return_pct * 100.0,  # arbs score highest
    )


def _detect_value_bets(event: Dict, market_key: str) -> List[OddsSignal]:
    """
    Value bet: one book offers better odds than the consensus market price.
    Edge = consensus_implied_prob - best_book_implied_prob
    (positive = the best book is underestimating the opponent probability
     = they think the outcome is LESS likely than the market does
     = better odds for the bettor)
    """
    signals: List[OddsSignal] = []
    bests = _best_back_per_outcome(event, market_key)

    for outcome_name, (best_price, best_book) in bests.items():
        all_prices = _all_back_prices(event, market_key, outcome_name)
        if len(all_prices) < 3:  # need at least 3 books for meaningful consensus
            continue

        prices_only   = [p for p, _ in all_prices]
        consensus_odds = sum(prices_only) / len(prices_only)

        best_impl      = 1.0 / best_price
        consensus_impl = 1.0 / consensus_odds
        edge_pct       = (consensus_impl - best_impl) * 100.0  # positive = value

        if edge_pct < VALUE_EDGE_MIN_PCT:
            continue

        # Worst book for reference (tightest price)
        worst_price, worst_book = min(all_prices, key=lambda x: x[0])

        signals.append(OddsSignal(
            event_id      = event.get("id", ""),
            sport_key     = event.get("sport_key", ""),
            sport_title   = event.get("sport_title", ""),
            home_team     = event.get("home_team", ""),
            away_team     = event.get("away_team", ""),
            commence_time = event.get("commence_time", ""),
            signal_type   = "value_bet",
            market        = market_key,
            outcome       = outcome_name,
            best_book     = best_book,
            best_odds     = best_price,
            worst_book    = worst_book,
            worst_odds    = worst_price,
            edge_pct      = round(edge_pct, 4),
            consensus_odds= round(consensus_odds, 4),
            implied_prob  = round(best_impl, 6),
            consensus_prob= round(consensus_impl, 6),
            arb_legs      = [],
            n_books       = len(all_prices),
            scanned_utc   = _now_utc(),
            score         = edge_pct * 1.0,
        ))

    return signals


def _detect_line_gaps(event: Dict, market_key: str) -> List[OddsSignal]:
    """
    Extreme line dispersion: best price > X% higher than worst price on same outcome.
    Indicates a steam move, stale line, or book error — actionable intelligence.
    """
    signals: List[OddsSignal] = []
    bests = _best_back_per_outcome(event, market_key)

    for outcome_name, (best_price, best_book) in bests.items():
        all_prices = _all_back_prices(event, market_key, outcome_name)
        if len(all_prices) < 2:
            continue

        worst_price, worst_book = min(all_prices, key=lambda x: x[0])
        if worst_price <= 1.0:
            continue

        gap_pct = (best_price - worst_price) / worst_price * 100.0
        if gap_pct < LINE_GAP_MIN_PCT:
            continue

        prices_only    = [p for p, _ in all_prices]
        consensus_odds = sum(prices_only) / len(prices_only)

        signals.append(OddsSignal(
            event_id      = event.get("id", ""),
            sport_key     = event.get("sport_key", ""),
            sport_title   = event.get("sport_title", ""),
            home_team     = event.get("home_team", ""),
            away_team     = event.get("away_team", ""),
            commence_time = event.get("commence_time", ""),
            signal_type   = "line_gap",
            market        = market_key,
            outcome       = outcome_name,
            best_book     = best_book,
            best_odds     = best_price,
            worst_book    = worst_book,
            worst_odds    = worst_price,
            edge_pct      = round(gap_pct, 4),
            consensus_odds= round(consensus_odds, 4),
            implied_prob  = round(1.0 / best_price, 6),
            consensus_prob= round(1.0 / worst_price, 6),
            arb_legs      = [],
            n_books       = len(all_prices),
            scanned_utc   = _now_utc(),
            score         = gap_pct * 0.4,  # score below arb + value_bet
        ))

    return signals


# ── Event + Full Scan ─────────────────────────────────────────────────────────

def scan_event(event: Dict) -> List[OddsSignal]:
    """Run all three detectors on a single event across all target markets."""
    signals: List[OddsSignal] = []
    for market in TARGET_MARKETS:
        arb = _detect_arbitrage(event, market)
        if arb:
            signals.append(arb)
        signals.extend(_detect_value_bets(event, market))
        signals.extend(_detect_line_gaps(event, market))
    return signals


def scan_all_sports() -> List[OddsSignal]:
    """
    Scan every *_live_odds.json in sports_data/ and return all signals
    sorted by: arbitrage first, then value_bets, then line_gaps — each
    tier sorted by score descending.
    """
    all_signals: List[OddsSignal] = []
    files = sorted(SPORTS_DIR.glob("*_live_odds.json"))
    events_scanned = 0

    for odds_file in files:
        data = _load_json(odds_file)
        if not isinstance(data, list):
            continue
        for event in data:
            try:
                sigs = scan_event(event)
                all_signals.extend(sigs)
                events_scanned += 1
            except Exception:
                pass

    # Sort: type tier first, then score desc
    type_rank = {"arbitrage": 0, "value_bet": 1, "line_gap": 2}
    all_signals.sort(key=lambda s: (type_rank.get(s.signal_type, 9), -s.score))
    return all_signals


# ── Output Writers ────────────────────────────────────────────────────────────

def _write_outputs(signals: List[OddsSignal]) -> None:
    ts   = _now_utc()
    arbs = [s for s in signals if s.signal_type == "arbitrage"]
    vals = [s for s in signals if s.signal_type == "value_bet"]
    gaps = [s for s in signals if s.signal_type == "line_gap"]

    # Top-N combined
    _atomic_write(OUT_DIR / "_live_signals.json", {
        "generated_utc":   ts,
        "total_signals":   len(signals),
        "arbitrage_count": len(arbs),
        "value_bet_count": len(vals),
        "line_gap_count":  len(gaps),
        "signals":         [asdict(s) for s in signals[:TOP_N]],
    })

    # Arbitrage only
    _atomic_write(OUT_DIR / "_arbitrage_only.json", {
        "generated_utc": ts,
        "count":         len(arbs),
        "signals":       [asdict(s) for s in arbs],
    })

    # Value bets only (top 100)
    _atomic_write(OUT_DIR / "_value_bets.json", {
        "generated_utc": ts,
        "count":         len(vals),
        "signals":       [asdict(s) for s in vals[:100]],
    })

    # Line gaps only (top 100)
    _atomic_write(OUT_DIR / "_line_gaps.json", {
        "generated_utc": ts,
        "count":         len(gaps),
        "signals":       [asdict(s) for s in gaps[:100]],
    })

    # Per-sport breakdown → master summary
    by_sport: Dict[str, List[OddsSignal]] = defaultdict(list)
    for s in signals:
        by_sport[s.sport_key].append(s)

    sport_rows = []
    for sport_key, sport_sigs in sorted(by_sport.items(), key=lambda x: -len(x[1])):
        n_arb = sum(1 for s in sport_sigs if s.signal_type == "arbitrage")
        n_val = sum(1 for s in sport_sigs if s.signal_type == "value_bet")
        n_gap = sum(1 for s in sport_sigs if s.signal_type == "line_gap")
        top_edge = max((s.edge_pct for s in sport_sigs), default=0.0)
        sport_rows.append({
            "sport_key":     sport_key,
            "total_signals": len(sport_sigs),
            "arbitrages":    n_arb,
            "value_bets":    n_val,
            "line_gaps":     n_gap,
            "top_edge_pct":  round(top_edge, 4),
            "best_signal":   asdict(sport_sigs[0]),
        })

    _atomic_write(STATE_DIR / "_sports_summary.json", {
        "generated_utc":    ts,
        "total_signals":    len(signals),
        "arbitrage_count":  len(arbs),
        "value_bet_count":  len(vals),
        "line_gap_count":   len(gaps),
        "sports_covered":   len(by_sport),
        "top_signal":       asdict(signals[0]) if signals else None,
        "by_sport":         sport_rows,
    })

    # Human-readable console line
    top_type  = signals[0].signal_type.upper() if signals else "-"
    top_edge  = f"{signals[0].edge_pct:.2f}%" if signals else "-"
    top_match = f"{signals[0].home_team} vs {signals[0].away_team}" if signals else "-"
    print(
        f"[{ts}] Signals={len(signals)} | "
        f"Arbs={len(arbs)} | Val={len(vals)} | Gaps={len(gaps)} | "
        f"Sports={len(by_sport)} | "
        f"TOP: [{top_type}] {top_match} edge={top_edge}"
    )


# ── Daemon Loop ───────────────────────────────────────────────────────────────

def run_daemon() -> None:
    print(f"[SportsOddsEngine] Starting | scan_interval={SCAN_INTERVAL}s | "
          f"value_edge_min={VALUE_EDGE_MIN_PCT}% | arb_threshold={ARB_THRESHOLD}")
    print(f"[SportsOddsEngine] Sports dir : {SPORTS_DIR}")
    print(f"[SportsOddsEngine] Output dir : {OUT_DIR}")
    n_files = len(list(SPORTS_DIR.glob("*_live_odds.json")))
    print(f"[SportsOddsEngine] Odds files found: {n_files}")

    while True:
        try:
            signals = scan_all_sports()
            _write_outputs(signals)
        except Exception as e:
            print(f"[SportsOddsEngine][ERROR] {e}")
        time.sleep(SCAN_INTERVAL)


# ── Orchestrator Helpers (import-safe, no daemon instance needed) ─────────────

def get_top_sports_signals(n: int = 20) -> List[Dict]:
    """Load top-N live signals from the last engine run."""
    data = _load_json(OUT_DIR / "_live_signals.json")
    if not data:
        return []
    return data.get("signals", [])[:n]


def get_arbitrage_signals() -> List[Dict]:
    """Load confirmed arbitrage signals from the last engine run."""
    data = _load_json(OUT_DIR / "_arbitrage_only.json")
    return data.get("signals", []) if data else []


def get_value_bet_signals(n: int = 20) -> List[Dict]:
    """Load top-N value bet signals."""
    data = _load_json(OUT_DIR / "_value_bets.json")
    return data.get("signals", [])[:n] if data else []


def sports_engine_is_fresh(max_age_sec: float = 120.0) -> bool:
    """Return True if the sports engine summary was written within max_age_sec."""
    path = STATE_DIR / "_sports_summary.json"
    if not path.exists():
        return False
    return (time.time() - path.stat().st_mtime) <= max_age_sec


def get_sports_summary() -> Optional[Dict]:
    """Return the full sports summary dict, or None if unavailable."""
    return _load_json(STATE_DIR / "_sports_summary.json")


# ── One-shot scan (non-daemon) ────────────────────────────────────────────────

def run_once() -> List[OddsSignal]:
    """Single scan — useful for testing or on-demand runs."""
    signals = scan_all_sports()
    _write_outputs(signals)
    return signals


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if "--once" in sys.argv:
        sigs = run_once()
        print(f"Done. {len(sigs)} signals written.")
    else:
        run_daemon()
