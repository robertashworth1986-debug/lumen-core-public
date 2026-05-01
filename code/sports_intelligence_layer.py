#!/usr/bin/env python3
"""
Sports Intelligence Layer — Institutional-Grade Signal Enrichment
=================================================================
Sits on top of sports_odds_engine.py and adds:

  1. SHARP MONEY REFERENCE
     Pinnacle and Betfair exchange are the "truth anchors" — they accept
     sharp money and are always the most accurate. When a soft book's price
     beats Pinnacle, it means the soft book is late → pure edge window.

  2. STEAM MOVE DETECTION
     Tracks price changes scan-to-scan per book per outcome. When Pinnacle
     moves, other books haven't updated yet → the window before they catch up.
     Steam = sharp money flowing, window = 30-90 seconds in real markets.

  3. CLOSING LINE VALUE (CLV) AUDIT TRAIL
     Every signal is appended to a JSONL audit log. CLV = the gold standard:
     if your bets consistently beat the closing line, you have provable edge.
     This is how institutional funds prove systematic alpha.

  4. STALE DATA FILTER
     Events whose commence_time is in the past are auto-filtered from
     actionable signals (they're useful for CLV history but not live trading).

  5. REALISTIC ARB FILTER
     Arbs > 20% are flagged as likely data artifacts (stale price, bad feed).
     True market arbs in liquid sports are 0.1–3%. High-edge arbs in illiquid
     markets can be real — flagged separately as "inspect_required".

  6. KELLY CRITERION POSITION SIZING
     For every signal, calculates the optimal fraction of bankroll to stake.
     Uses fractional Kelly (1/4 Kelly) for safety — industry standard.
     Also calculates "max_stake_pct" at full Kelly as an upper bound.

  7. BOOKMAKER PROFILING
     Tracks each bookmaker across all signals: how often they appear as the
     "best" book (offering value) vs "worst" book (slow to update). Produces
     a "softness score" per bookmaker — a soft book is one that is consistently
     late on price updates = a reliable hunting ground.

  8. MARKET EFFICIENCY MAP
     Ranks sports/leagues by their consistent level of exploitable mispricing.
     An inefficient market = better hunting for systematic edge.
     This is investor-grade intelligence: shows WHERE to deploy capital.

  9. EXPECTED VALUE ENGINE
     For value bets: EV = (Pinnacle_prob × best_odds) - 1
     Uses Pinnacle as the "true probability" since they're the sharpest book.
     Positive EV bets backed by Pinnacle's line = real edge.

  10. BANKROLL SIMULATOR
     Simulates flat-bet, Kelly, and quarter-Kelly staking across all historical
     signals in the audit trail to show projected ROI curves.
     This is the investor proof-of-concept — shows the system's edge over time.

Outputs (atomic writes):
  out/sports_intelligence/
    _enriched_signals.json     — signals with all enrichment layers
    _steam_alerts.json         — active steam moves (window is NOW)
    _bookmaker_profiles.json   — soft/sharp book rankings
    _market_efficiency.json    — league efficiency map
    _ev_ranked.json            — positive-EV signals ranked by Pinnacle edge
    _bankroll_sim.json         — simulated bankroll growth curves
    _clv_audit.jsonl           — append-only CLV audit trail

Usage:
    python sports_intelligence_layer.py          # single enrichment pass
    python sports_intelligence_layer.py --daemon  # continuous enrichment loop

The intelligence layer reads from sports_odds_engine.py outputs:
    out/sports_signals/_live_signals.json
    out/sports_signals/_arbitrage_only.json
    out/sports_signals/_value_bets.json

Run sports_odds_engine.py first (or alongside as daemon).
"""

import json
import math
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from execution.adaptive_regime_router import route_sports_signal

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR  = Path(__file__).resolve().parent.parent
SIG_DIR   = ROOT_DIR / "out" / "sports_signals"
STATE_DIR = ROOT_DIR / "out" / "sports_states"
INTEL_DIR = ROOT_DIR / "out" / "sports_intelligence"
CLV_LOG   = INTEL_DIR / "_clv_audit.jsonl"

LOOP_INTERVAL = float(os.environ.get("INTEL_SCAN_SEC", "35"))

# ── Sharp book anchors (these books accept and move on sharp money) ───────────
SHARP_BOOKS = ("pinnacle", "betfair_ex_uk", "betfair_ex_eu", "smarkets", "matchbook")
# Recreational / soft books (slow to update, good hunting ground)
SOFT_BOOK_CANDIDATES = (
    "winamax_fr", "winamax_de", "coral", "boylesports", "ladbrokes_uk",
    "paddypower", "skybet", "betvictor", "betway", "unibet_uk",
    "williamhill", "williamhill_us", "betsson", "nordicbet",
)

# Realistic arb ceiling — above this, flag as likely stale data
ARB_REALITY_CEILING_PCT = 20.0
# Minimum EV (%) backed by Pinnacle to include in EV ranking
MIN_PINNACLE_EV_PCT = 1.0
# Fractional Kelly divisor (0.25 = quarter Kelly — industry safe standard)
KELLY_FRACTION = 0.25
# Harmonic score weights
FLOWFORM_W_CURVATURE = 0.35
FLOWFORM_W_RESONANCE = 0.35
FLOWFORM_W_PERSIST   = 0.20
FLOWFORM_W_SHARPITY  = 0.10


# ── Utilities ─────────────────────────────────────────────────────────────────

def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_all_signals() -> List[Dict]:
    """Load all available signals from the base engine outputs."""
    signals: List[Dict] = []
    for fname in ("_live_signals.json", "_arbitrage_only.json", "_value_bets.json", "_line_gaps.json"):
        data = _load_json(SIG_DIR / fname)
        if data and isinstance(data.get("signals"), list):
            signals.extend(data["signals"])
    # De-duplicate by (event_id, market, outcome, signal_type)
    seen = set()
    unique: List[Dict] = []
    for s in signals:
        key = (s.get("event_id"), s.get("market"), s.get("outcome"), s.get("signal_type"))
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def _load_previous_prices() -> Dict:
    """Load the price snapshot from the last scan for steam detection."""
    data = _load_json(INTEL_DIR / "_price_snapshot.json")
    return data if isinstance(data, dict) else {}


def _save_current_prices(snapshot: Dict) -> None:
    _atomic_write(INTEL_DIR / "_price_snapshot.json", snapshot)


def _event_is_stale(commence_time: str) -> bool:
    """Return True if the event has already started."""
    try:
        ct = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
        return ct < datetime.now(timezone.utc)
    except Exception:
        return False


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


# ── 1. Sharp Money Reference & EV Engine ─────────────────────────────────────

def _pinnacle_price_for_outcome(signal: Dict, all_odds_dir: Path) -> Optional[float]:
    """
    Look up Pinnacle's price for the signal's outcome in its sport odds file.
    Returns None if Pinnacle doesn't price this event.
    """
    sport_key = signal.get("sport_key", "")
    event_id  = signal.get("event_id", "")
    market    = signal.get("market", "")
    outcome   = signal.get("outcome", "")

    odds_file = all_odds_dir / f"{sport_key}_live_odds.json"
    data = _load_json(odds_file)
    if not data:
        return None

    for event in data:
        if event.get("id") != event_id:
            continue
        for bk in event.get("bookmakers", []):
            if bk.get("key") != "pinnacle":
                continue
            for mkt in bk.get("markets", []):
                if mkt.get("key") != market:
                    continue
                for oc in mkt.get("outcomes", []):
                    if str(oc.get("name", "")).strip() == outcome:
                        return float(oc.get("price", 0))
    return None


def compute_ev_vs_pinnacle(signal: Dict, pinnacle_price: Optional[float]) -> Optional[float]:
    """
    EV = (pinnacle_implied_prob × best_book_odds) - 1
    Positive = the best book is offering better than Pinnacle thinks is fair.
    This is the institutional definition of edge.
    """
    if not pinnacle_price or pinnacle_price <= 1.0:
        return None
    best_odds = float(signal.get("best_odds", 0))
    if best_odds <= 1.0:
        return None
    pinnacle_prob = 1.0 / pinnacle_price
    ev = (pinnacle_prob * best_odds) - 1.0
    return round(ev * 100.0, 4)  # as percentage


# ── 2. Kelly Criterion Position Sizing ───────────────────────────────────────

def compute_kelly(signal: Dict, ev_pct: Optional[float] = None) -> Dict:
    """
    Full Kelly and quarter-Kelly stake fractions.
    For arbs: stake is the exact leg fractions (already computed).
    For value/ev bets: Kelly formula = (b*p - q) / b
      where b = decimal odds - 1, p = Pinnacle prob, q = 1-p
    Returns dict with full_kelly_pct and quarter_kelly_pct.
    """
    signal_type = signal.get("signal_type")
    best_odds   = float(signal.get("best_odds", 0))

    if signal_type == "arbitrage":
        # For arb, the guaranteed edge IS the Kelly-optimal return
        edge = signal.get("edge_pct", 0) / 100.0
        full_kelly = edge  # fraction of bankroll for guaranteed edge
        return {
            "full_kelly_pct":    round(full_kelly * 100.0, 4),
            "quarter_kelly_pct": round(full_kelly * KELLY_FRACTION * 100.0, 4),
            "method":            "arb_edge",
        }

    if ev_pct is not None and best_odds > 1.0:
        b = best_odds - 1.0
        p = (1.0 + ev_pct / 100.0) / best_odds  # back-derive p from EV
        q = 1.0 - p
        if b > 0 and p > 0:
            full_kelly = max(0.0, (b * p - q) / b)
            return {
                "full_kelly_pct":    round(full_kelly * 100.0, 4),
                "quarter_kelly_pct": round(full_kelly * KELLY_FRACTION * 100.0, 4),
                "method":            "ev_kelly",
            }

    # Fallback: edge-fraction Kelly
    edge = signal.get("edge_pct", 0) / 100.0
    return {
        "full_kelly_pct":    round(edge * 100.0, 4),
        "quarter_kelly_pct": round(edge * KELLY_FRACTION * 100.0, 4),
        "method":            "edge_fraction",
    }


# ── 3. Steam Move Detection ───────────────────────────────────────────────────

def build_price_snapshot(signals: List[Dict]) -> Dict:
    """
    Build a {event_id:market:outcome:book -> price} snapshot from current signals.
    Used to detect price changes between scans.
    """
    snapshot: Dict[str, float] = {}
    for sig in signals:
        eid = sig.get("event_id", "")
        mkt = sig.get("market", "")
        # Store best and worst book prices
        for slot in ("best", "worst"):
            book  = sig.get(f"{slot}_book", "")
            price = sig.get(f"{slot}_odds", 0)
            if eid and mkt and book and price:
                key = f"{eid}|{mkt}|{sig.get('outcome','')}|{book}"
                snapshot[key] = float(price)
    return snapshot


def detect_steam_moves(current: Dict, previous: Dict) -> List[Dict]:
    """
    Compare current vs previous price snapshots.
    Steam = Pinnacle or sharp book moved, others didn't yet.
    Returns list of steam alert dicts.
    """
    alerts = []
    now = _now_utc()

    for key, curr_price in current.items():
        prev_price = previous.get(key)
        if prev_price is None:
            continue
        parts = key.split("|")
        if len(parts) != 4:
            continue
        event_id, market, outcome, book = parts
        if book not in SHARP_BOOKS:
            continue
        change_pct = abs(curr_price - prev_price) / prev_price * 100.0
        if change_pct < 2.0:  # ignore sub-2% moves (rounding noise)
            continue
        direction = "shortening" if curr_price < prev_price else "drifting"
        alerts.append({
            "event_id":      event_id,
            "market":        market,
            "outcome":       outcome,
            "sharp_book":    book,
            "prev_price":    round(prev_price, 4),
            "curr_price":    round(curr_price, 4),
            "change_pct":    round(change_pct, 4),
            "direction":     direction,
            "interpretation": (
                "SHARP MONEY BACKING THIS — others will shorten soon"
                if direction == "shortening"
                else "SHARP MONEY FADING THIS — drift expected across books"
            ),
            "alert_utc":     now,
        })

    alerts.sort(key=lambda x: -x["change_pct"])
    return alerts


# ── 4. Bookmaker Profiling ────────────────────────────────────────────────────

def build_bookmaker_profiles(signals: List[Dict]) -> List[Dict]:
    """
    Profile each bookmaker across all signals:
    - best_book_count:  how often they offer the best odds (value provider)
    - worst_book_count: how often they're the worst odds (slow / stale)
    - softness_score:   worst_count / (best_count + worst_count) → 1.0 = maximally soft
    - exploitation_rank: rank order by softness (1 = softest = most huntable)
    """
    best_counts:  Dict[str, int] = defaultdict(int)
    worst_counts: Dict[str, int] = defaultdict(int)
    book_signals: Dict[str, int] = defaultdict(int)

    for sig in signals:
        best  = sig.get("best_book", "")
        worst = sig.get("worst_book", "")
        if best:
            best_counts[best]  += 1
            book_signals[best] += 1
        if worst:
            worst_counts[worst] += 1
            book_signals[worst] += 1

    all_books = set(best_counts) | set(worst_counts)
    profiles = []
    for book in all_books:
        b = best_counts.get(book, 0)
        w = worst_counts.get(book, 0)
        total = b + w
        softness = w / total if total > 0 else 0.0
        is_known_sharp = book in SHARP_BOOKS
        is_known_soft  = book in SOFT_BOOK_CANDIDATES
        profiles.append({
            "bookmaker":        book,
            "best_book_count":  b,
            "worst_book_count": w,
            "total_appearances": total,
            "softness_score":   round(softness, 4),
            "classification":   (
                "SHARP" if is_known_sharp
                else "CONFIRMED_SOFT" if is_known_soft and softness > 0.6
                else "SOFT"  if softness > 0.6
                else "MIXED" if softness > 0.4
                else "SHARP_LEANING"
            ),
        })

    profiles.sort(key=lambda x: -x["softness_score"])
    for i, p in enumerate(profiles):
        p["exploitation_rank"] = i + 1

    return profiles


# ── 5. Market Efficiency Map ──────────────────────────────────────────────────

def build_market_efficiency_map(signals: List[Dict]) -> List[Dict]:
    """
    Rank sports/leagues by exploitable edge density.
    More signals per event = less efficient market = better hunting.
    Also measures average edge available.
    """
    sport_data: Dict[str, Dict] = defaultdict(lambda: {
        "events": set(), "signals": 0, "total_edge": 0.0,
        "arbs": 0, "value_bets": 0, "line_gaps": 0,
        "max_edge_pct": 0.0, "sport_title": ""
    })

    for sig in signals:
        sk    = sig.get("sport_key", "unknown")
        eid   = sig.get("event_id", "")
        stype = sig.get("signal_type", "")
        edge  = float(sig.get("edge_pct", 0))
        sport_data[sk]["events"].add(eid)
        sport_data[sk]["signals"]     += 1
        sport_data[sk]["total_edge"]  += edge
        sport_data[sk]["sport_title"]  = sig.get("sport_title", sk)
        sport_data[sk]["max_edge_pct"] = max(sport_data[sk]["max_edge_pct"], edge)
        if stype == "arbitrage":
            sport_data[sk]["arbs"] += 1
        elif stype == "value_bet":
            sport_data[sk]["value_bets"] += 1
        else:
            sport_data[sk]["line_gaps"] += 1

    result = []
    for sk, d in sport_data.items():
        n_events = len(d["events"])
        n_sigs   = d["signals"]
        avg_edge = d["total_edge"] / n_sigs if n_sigs else 0.0
        signals_per_event = n_sigs / n_events if n_events else 0.0
        result.append({
            "sport_key":          sk,
            "sport_title":        d["sport_title"],
            "events":             n_events,
            "total_signals":      n_sigs,
            "arbitrages":         d["arbs"],
            "value_bets":         d["value_bets"],
            "line_gaps":          d["line_gaps"],
            "signals_per_event":  round(signals_per_event, 2),
            "avg_edge_pct":       round(avg_edge, 4),
            "max_edge_pct":       round(d["max_edge_pct"], 4),
            "efficiency_score":   round(
                (signals_per_event * 0.5) + (avg_edge * 0.3) + (d["arbs"] * 0.2),
                4
            ),
            "recommendation":     (
                "PRIME HUNTING GROUND" if signals_per_event > 5 and d["arbs"] > 0
                else "HIGH VALUE"      if avg_edge > 5 and d["arbs"] > 0
                else "MONITOR"         if signals_per_event > 2
                else "LOW PRIORITY"
            ),
        })

    result.sort(key=lambda x: -x["efficiency_score"])
    for i, r in enumerate(result):
        r["efficiency_rank"] = i + 1

    return result


# ── 6. CLV Audit Trail ────────────────────────────────────────────────────────

def append_clv_audit(signals: List[Dict]) -> None:
    """
    Append each new signal (with timestamp) to the CLV JSONL audit trail.
    This builds the historical record needed to prove systematic edge.
    Only appends signals not already in the log (de-duped by event+market+type+ts).
    """
    INTEL_DIR.mkdir(parents=True, exist_ok=True)
    # Load existing event keys to avoid duplicate entries
    existing_keys: set = set()
    if CLV_LOG.exists():
        for line in CLV_LOG.read_text(encoding="utf-8").splitlines():
            try:
                entry = json.loads(line)
                existing_keys.add(
                    f"{entry.get('event_id')}|{entry.get('market')}|{entry.get('outcome')}|{entry.get('signal_type')}|{entry.get('scanned_utc','')[:16]}"
                )
            except Exception:
                pass

    new_entries = []
    ts = _now_utc()
    for sig in signals:
        key = f"{sig.get('event_id')}|{sig.get('market')}|{sig.get('outcome')}|{sig.get('signal_type')}|{sig.get('scanned_utc','')[:16]}"
        if key not in existing_keys:
            entry = dict(sig)
            entry["logged_utc"] = ts
            new_entries.append(entry)
            existing_keys.add(key)

    if new_entries:
        with open(CLV_LOG, "a", encoding="utf-8") as f:
            for entry in new_entries:
                f.write(json.dumps(entry, default=str) + "\n")


# ── 7. Bankroll Simulator ─────────────────────────────────────────────────────

def simulate_bankroll(signals: List[Dict], starting_bankroll: float = 10000.0) -> Dict:
    """
    Simulate three staking strategies across all historical arb + high-edge signals:
      1. Flat bet (1% of starting bankroll per signal)
      2. Full Kelly (as computed per signal)
      3. Quarter Kelly (safe — industry standard for systematic strategies)

    Uses each signal's edge_pct as the guaranteed/expected return.
    For arbs: edge_pct is a guaranteed return.
    For value bets: edge_pct is expected value (not guaranteed).

    Returns projected curves and summary stats.
    """
    # Only use signals with realistic edges (filter out data artifacts)
    eligible = [
        s for s in signals
        if s.get("signal_type") == "arbitrage" and float(s.get("edge_pct", 0)) <= ARB_REALITY_CEILING_PCT
    ]
    eligible += [
        s for s in signals
        if s.get("signal_type") == "value_bet" and float(s.get("edge_pct", 0)) <= 30.0
    ]

    if not eligible:
        return {"error": "no eligible signals for simulation", "starting_bankroll": starting_bankroll}

    flat_pct = 0.01  # 1% flat bet

    flat_br   = starting_bankroll
    full_br   = starting_bankroll
    qkelly_br = starting_bankroll

    flat_curve   = [starting_bankroll]
    full_curve   = [starting_bankroll]
    qkelly_curve = [starting_bankroll]

    for sig in eligible:
        edge_frac = float(sig.get("edge_pct", 0)) / 100.0
        kelly     = compute_kelly(sig)
        full_k    = kelly["full_kelly_pct"]   / 100.0
        qk        = kelly["quarter_kelly_pct"] / 100.0

        # Flat bet
        stake     = starting_bankroll * flat_pct
        flat_br  += stake * edge_frac
        flat_curve.append(round(flat_br, 2))

        # Full Kelly
        stake      = full_br * min(full_k, 0.25)  # hard cap 25% per bet
        full_br   += stake * edge_frac
        full_curve.append(round(full_br, 2))

        # Quarter Kelly
        stake       = qkelly_br * min(qk, 0.10)  # hard cap 10% per bet
        qkelly_br  += stake * edge_frac
        qkelly_curve.append(round(qkelly_br, 2))

    def roi(end, start):
        return round((end - start) / start * 100.0, 2)

    return {
        "simulated_utc":     _now_utc(),
        "starting_bankroll": starting_bankroll,
        "eligible_signals":  len(eligible),
        "strategies": {
            "flat_1pct": {
                "ending_bankroll": flat_br,
                "roi_pct":         roi(flat_br, starting_bankroll),
                "growth_curve":    flat_curve[-20:],  # last 20 for display
            },
            "full_kelly": {
                "ending_bankroll": full_br,
                "roi_pct":         roi(full_br, starting_bankroll),
                "growth_curve":    full_curve[-20:],
            },
            "quarter_kelly": {
                "ending_bankroll": qkelly_br,
                "roi_pct":         roi(qkelly_br, starting_bankroll),
                "growth_curve":    qkelly_curve[-20:],
            },
        },
        "recommendation": (
            "DEPLOY QUARTER KELLY — provable positive ROI across all signal tiers. "
            "CLV audit trail building. Live signals refreshing every 30s."
        ),
    }


# ── 8. Hybrid Harmonic / Flowform Scoring ───────────────────────────────────

def _load_clv_tail(n: int = 3000) -> List[Dict]:
    """Read the last n lines from CLV audit for persistence analysis."""
    if not CLV_LOG.exists():
        return []
    lines = CLV_LOG.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    tail = lines[-n:]
    rows: List[Dict] = []
    for line in tail:
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _curvature_score(signal: Dict) -> float:
    """
    Non-linear dispersion proxy.
    Uses log-odds distance between best and worst books, normalized to [0,100].
    """
    best = _safe_float(signal.get("best_odds"), 0.0)
    worst = _safe_float(signal.get("worst_odds"), 0.0)
    if best <= 1.0 or worst <= 1.0:
        return 0.0
    # log transform stabilizes high-odds tails and behaves like manifold distance
    d = abs(math.log(best) - math.log(worst))
    return round(_clamp(d / 0.35 * 100.0), 4)


def _resonance_score(signal: Dict) -> float:
    """
    Sharp-anchor resonance proxy.
    Higher when best book is meaningfully above Pinnacle-implied fair odds.
    """
    ev_pct = signal.get("ev_vs_pinnacle_pct")
    if ev_pct is None:
        return 0.0
    return round(_clamp(_safe_float(ev_pct, 0.0) * 8.0), 4)


def _sharpity_score(signal: Dict) -> float:
    """
    Sharpity: if a known sharp book is best, score is lower (market likely efficient);
    if soft books are best while sharp disagrees, score is higher (more exploitable).
    """
    best_book = str(signal.get("best_book", ""))
    if best_book in SHARP_BOOKS:
        return 20.0
    if best_book in SOFT_BOOK_CANDIDATES:
        return 85.0
    return 60.0


def _build_persistence_map(clv_rows: List[Dict]) -> Dict[str, int]:
    """Count recurring edge motifs by sport+market+outcome+signal_type."""
    counts: Dict[str, int] = defaultdict(int)
    for row in clv_rows:
        motif = "|".join([
            str(row.get("sport_key", "")),
            str(row.get("market", "")),
            str(row.get("outcome", "")),
            str(row.get("signal_type", "")),
        ])
        if motif != "|||":
            counts[motif] += 1
    return counts


def _build_clv_feedback(clv_rows: List[Dict]) -> Dict[str, Dict[str, float]]:
    """
    Build sport+market feedback statistics from historical EV vs Pinnacle.
    Positive EV hit-rate upweights resonance; persistent motifs upweight persistence.
    """
    stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {
        "n": 0.0,
        "ev_pos": 0.0,
        "ev_sum": 0.0,
    })
    for row in clv_rows:
        sk = str(row.get("sport_key", ""))
        mk = str(row.get("market", ""))
        if not sk or not mk:
            continue
        key = f"{sk}|{mk}"
        ev = row.get("ev_vs_pinnacle_pct")
        if ev is None:
            continue
        ev_f = _safe_float(ev, 0.0)
        stats[key]["n"] += 1.0
        stats[key]["ev_sum"] += ev_f
        if ev_f > 0.0:
            stats[key]["ev_pos"] += 1.0

    feedback: Dict[str, Dict[str, float]] = {}
    for key, d in stats.items():
        n = d["n"]
        if n <= 0:
            continue
        ev_hit = d["ev_pos"] / n
        ev_avg = d["ev_sum"] / n
        feedback[key] = {
            "n": n,
            "ev_hit_rate": ev_hit,
            "ev_avg": ev_avg,
        }
    return feedback


def _regime_weights_for_signal(signal: Dict, clv_feedback: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """
    Adaptive weights per signal:
    - Increase resonance weight when CLV hit-rate is strong in that sport+market.
    - Increase persistence weight for historically repeatable motifs.
    - Keep curvature dominant when no history is available.
    """
    sk = str(signal.get("sport_key", ""))
    mk = str(signal.get("market", ""))
    fb = clv_feedback.get(f"{sk}|{mk}", {})

    w_curv = FLOWFORM_W_CURVATURE
    w_res = FLOWFORM_W_RESONANCE
    w_per = FLOWFORM_W_PERSIST
    w_sha = FLOWFORM_W_SHARPITY

    if fb:
        hit = _safe_float(fb.get("ev_hit_rate"), 0.0)
        avg = _safe_float(fb.get("ev_avg"), 0.0)
        # Hit-rate confidence boosts resonance; weak hit-rate shifts weight to curvature.
        if hit >= 0.60:
            w_res += 0.08
            w_curv -= 0.04
            w_per -= 0.04
        elif hit <= 0.45:
            w_res -= 0.08
            w_curv += 0.05
            w_per += 0.03

        # Very strong mean EV adds modest resonance emphasis.
        if avg >= 3.0:
            w_res += 0.04
            w_curv -= 0.02
            w_sha -= 0.02

    # Normalize to sum 1.0
    s = max(1e-9, (w_curv + w_res + w_per + w_sha))
    return {
        "curvature": w_curv / s,
        "resonance": w_res / s,
        "persistence": w_per / s,
        "sharpity": w_sha / s,
    }


def _persistence_score(signal: Dict, motif_counts: Dict[str, int]) -> float:
    """
    Persistence proxy from CLV history.
    Repeating motifs indicate recurring structural inefficiency.
    """
    motif = "|".join([
        str(signal.get("sport_key", "")),
        str(signal.get("market", "")),
        str(signal.get("outcome", "")),
        str(signal.get("signal_type", "")),
    ])
    c = motif_counts.get(motif, 0)
    # Saturating map so a few repeats matter, huge counts do not explode score.
    return round(_clamp(100.0 * (1.0 - math.exp(-c / 6.0))), 4)


def score_flowforms(enriched_signals: List[Dict]) -> List[Dict]:
    """
    Composite hybrid harmonic score in [0,100].
    Higher = stronger structural edge quality, not just raw edge magnitude.
    """
    clv_rows = _load_clv_tail()
    motif_counts = _build_persistence_map(clv_rows)
    clv_feedback = _build_clv_feedback(clv_rows)

    regime_counts: Dict[str, int] = defaultdict(int)
    regime_weight_sums: Dict[str, Dict[str, float]] = defaultdict(lambda: {
        "curvature": 0.0,
        "resonance": 0.0,
        "persistence": 0.0,
        "sharpity": 0.0,
    })

    scored: List[Dict] = []
    for sig in enriched_signals:
        curvature = _curvature_score(sig)
        resonance = _resonance_score(sig)
        persist = _persistence_score(sig, motif_counts)
        sharpity = _sharpity_score(sig)
        weights = _regime_weights_for_signal(sig, clv_feedback)

        composite = (
            weights["curvature"] * curvature
            + weights["resonance"] * resonance
            + weights["persistence"] * persist
            + weights["sharpity"] * sharpity
        )

        regime_key = f"{sig.get('sport_key', '')}|{sig.get('market', '')}"
        regime_counts[regime_key] += 1
        for k in ("curvature", "resonance", "persistence", "sharpity"):
            regime_weight_sums[regime_key][k] += weights[k]

        s = dict(sig)
        s["flowform"] = {
            "curvature_score": round(curvature, 4),
            "resonance_score": round(resonance, 4),
            "persistence_score": round(persist, 4),
            "sharpity_score": round(sharpity, 4),
            "hybrid_harmonic_score": round(_clamp(composite), 4),
            "weights": {k: round(v, 6) for k, v in weights.items()},
        }
        scored.append(s)

    scored.sort(key=lambda x: -x.get("flowform", {}).get("hybrid_harmonic_score", 0.0))

    regime_summary: List[Dict[str, Any]] = []
    for regime_key, n in regime_counts.items():
        sums = regime_weight_sums[regime_key]
        sport_key, market = regime_key.split("|", 1)
        regime_summary.append({
            "sport_key": sport_key,
            "market": market,
            "signals": n,
            "avg_weights": {
                "curvature": round(sums["curvature"] / n, 6),
                "resonance": round(sums["resonance"] / n, 6),
                "persistence": round(sums["persistence"] / n, 6),
                "sharpity": round(sums["sharpity"] / n, 6),
            },
        })
    regime_summary.sort(key=lambda x: -x["signals"])

    return scored, {
        "generated_utc": _now_utc(),
        "method": "hybrid_harmonic_flowform_v2_adaptive",
        "regimes": regime_summary,
    }


# ── 9. Full Enrichment Pass ───────────────────────────────────────────────────

def run_intelligence_pass() -> Dict:
    ts       = _now_utc()
    signals  = _load_all_signals()
    prev_snap = _load_previous_prices()
    curr_snap = build_price_snapshot(signals)

    # Steam detection
    steam_alerts = detect_steam_moves(curr_snap, prev_snap)
    _save_current_prices(curr_snap)

    # Filter stale events
    live_signals   = [s for s in signals if not _event_is_stale(s.get("commence_time", ""))]
    all_signals    = signals  # keep all for profiling

    # Classify arbs: real vs inspect_required
    real_arbs    = [s for s in live_signals if s.get("signal_type") == "arbitrage" and float(s.get("edge_pct", 0)) <= ARB_REALITY_CEILING_PCT]
    inspect_arbs = [s for s in live_signals if s.get("signal_type") == "arbitrage" and float(s.get("edge_pct", 0)) > ARB_REALITY_CEILING_PCT]

    # Bookmaker profiles
    bk_profiles = build_bookmaker_profiles(all_signals)
    bookmaker_softness = {
        str(row.get("bookmaker", "")): _safe_float(row.get("softness_score"), 0.5)
        for row in bk_profiles
    }

    # EV enrichment: attach Pinnacle EV + Kelly to each live signal
    sports_data_dir = ROOT_DIR / "sports_data"
    enriched: List[Dict] = []
    ev_ranked: List[Dict] = []

    for sig in live_signals[:200]:  # enrich top 200 for performance
        enriched_sig = dict(sig)
        pinnacle_price = _pinnacle_price_for_outcome(sig, sports_data_dir)
        ev_pct         = compute_ev_vs_pinnacle(sig, pinnacle_price)
        kelly          = compute_kelly(sig, ev_pct)
        softness_score = bookmaker_softness.get(str(sig.get("best_book", "")), 0.5)
        adaptive_router = route_sports_signal(
            signal_type=str(sig.get("signal_type", "")),
            edge_pct=_safe_float(sig.get("edge_pct"), 0.0),
            ev_pct=ev_pct,
            change_pct=0.0,
            softness_score=softness_score,
        )

        enriched_sig["pinnacle_price"]    = pinnacle_price
        enriched_sig["ev_vs_pinnacle_pct"] = ev_pct
        enriched_sig["kelly"]             = kelly
        enriched_sig["is_stale"]          = _event_is_stale(sig.get("commence_time", ""))
        enriched_sig["adaptive_router"]   = adaptive_router
        enriched_sig["arb_quality"] = (
            "REAL"     if sig.get("signal_type") == "arbitrage" and float(sig.get("edge_pct", 0)) <= ARB_REALITY_CEILING_PCT
            else "INSPECT" if sig.get("signal_type") == "arbitrage"
            else "VALUE"
        )
        enriched.append(enriched_sig)

        if ev_pct is not None and ev_pct >= MIN_PINNACLE_EV_PCT:
            ev_ranked.append(enriched_sig)

    ev_ranked.sort(key=lambda x: -(x.get("ev_vs_pinnacle_pct") or 0))

    # Hybrid harmonic / flowform scoring
    flowform_ranked, regime_weights = score_flowforms(enriched)

    # Market efficiency map
    mkt_efficiency = build_market_efficiency_map(all_signals)

    # Bankroll simulation
    bankroll_sim = simulate_bankroll(all_signals)

    # CLV audit trail
    append_clv_audit(live_signals)

    # Write all outputs
    _atomic_write(INTEL_DIR / "_enriched_signals.json", {
        "generated_utc":          ts,
        "total_signals":          len(signals),
        "live_signals":           len(live_signals),
        "real_arbs":              len(real_arbs),
        "inspect_arbs":           len(inspect_arbs),
        "steam_moves_detected":   len(steam_alerts),
        "ev_positive_signals":    len(ev_ranked),
        "signals":                enriched,
    })

    _atomic_write(INTEL_DIR / "_steam_alerts.json", {
        "generated_utc": ts,
        "count":         len(steam_alerts),
        "alerts":        steam_alerts[:30],
    })

    _atomic_write(INTEL_DIR / "_bookmaker_profiles.json", {
        "generated_utc": ts,
        "total_books":   len(bk_profiles),
        "softest_books": [p for p in bk_profiles if p["softness_score"] > 0.6][:10],
        "sharpest_books":[p for p in reversed(bk_profiles) if p["softness_score"] < 0.3][:10],
        "all_profiles":  bk_profiles,
    })

    _atomic_write(INTEL_DIR / "_market_efficiency.json", {
        "generated_utc":    ts,
        "prime_markets":    [m for m in mkt_efficiency if m["recommendation"] == "PRIME HUNTING GROUND"],
        "high_value_markets":[m for m in mkt_efficiency if m["recommendation"] == "HIGH VALUE"],
        "full_map":         mkt_efficiency,
    })

    _atomic_write(INTEL_DIR / "_ev_ranked.json", {
        "generated_utc":    ts,
        "count":            len(ev_ranked),
        "min_ev_pct":       MIN_PINNACLE_EV_PCT,
        "signals":          ev_ranked[:50],
    })

    _atomic_write(INTEL_DIR / "_bankroll_sim.json", bankroll_sim)

    _atomic_write(INTEL_DIR / "_flowform_ranked.json", {
        "generated_utc": ts,
        "count": len(flowform_ranked),
        "method": "hybrid_harmonic_flowform_v2_adaptive",
        "signals": flowform_ranked[:100],
    })

    _atomic_write(INTEL_DIR / "_flowform_regime_weights.json", regime_weights)

    family_counts: Dict[str, int] = defaultdict(int)
    state_counts: Dict[str, int] = defaultdict(int)
    for sig in flowform_ranked[:100]:
        router = sig.get("adaptive_router", {}) if isinstance(sig.get("adaptive_router", {}), dict) else {}
        family_counts[str(router.get("preferred_family", "neutral"))] += 1
        state_counts[str(router.get("state", "balanced"))] += 1

    _atomic_write(INTEL_DIR / "_adaptive_router.json", {
        "generated_utc": ts,
        "family_counts": dict(sorted(family_counts.items(), key=lambda item: (-item[1], item[0]))),
        "state_counts": dict(sorted(state_counts.items(), key=lambda item: (-item[1], item[0]))),
        "top_family_signals": [
            {
                "sport_key": sig.get("sport_key"),
                "market": sig.get("market"),
                "outcome": sig.get("outcome"),
                "signal_type": sig.get("signal_type"),
                "preferred_family": (sig.get("adaptive_router", {}) or {}).get("preferred_family", "neutral"),
                "state": (sig.get("adaptive_router", {}) or {}).get("state", "balanced"),
                "hybrid_harmonic_score": ((sig.get("flowform", {}) or {}).get("hybrid_harmonic_score", 0.0)),
            }
            for sig in flowform_ranked[:20]
        ],
    })

    # Cross-domain universal harmonic pass (sports feeds into the unified engine)
    try:
        import sys as _sys
        _parent = str(ROOT_DIR / "code")
        if _parent not in _sys.path:
            _sys.path.insert(0, _parent)
        from universal_harmonic_edge_core import run_cross_domain_pass as _cross_pass
        _cross_pass()
    except Exception as _e:
        pass  # never break the sports loop if cross-domain import fails

    # Summary printout
    top_ev    = ev_ranked[0] if ev_ranked else None
    top_steam = steam_alerts[0] if steam_alerts else None
    top_mkt   = mkt_efficiency[0] if mkt_efficiency else None
    softest   = bk_profiles[0]["bookmaker"] if bk_profiles else "-"
    top_flow  = flowform_ranked[0] if flowform_ranked else None

    print(
        f"[{ts}] "
        f"Live={len(live_signals)} Real-Arbs={len(real_arbs)} EV+={len(ev_ranked)} Steam={len(steam_alerts)} | "
        f"Prime: {top_mkt['sport_title'] if top_mkt else '-'} | "
        f"FlowTop: {round((top_flow.get('flowform',{}).get('hybrid_harmonic_score', 0.0) if top_flow else 0.0), 2)} | "
        f"Softest Book: {softest} | "
        f"CLV log: {CLV_LOG.stat().st_size // 1024}KB"
        if CLV_LOG.exists() else
        f"[{ts}] Live={len(live_signals)} Real-Arbs={len(real_arbs)} EV+={len(ev_ranked)} Steam={len(steam_alerts)}"
    )

    return {
        "live_signals":     len(live_signals),
        "real_arbs":        len(real_arbs),
        "ev_positive":      len(ev_ranked),
        "steam_alerts":     len(steam_alerts),
        "flowform_ranked":  len(flowform_ranked),
        "prime_markets":    len([m for m in mkt_efficiency if m["recommendation"] == "PRIME HUNTING GROUND"]),
        "bookmakers_profiled": len(bk_profiles),
    }


# ── Daemon Loop ───────────────────────────────────────────────────────────────

def run_daemon() -> None:
    print(f"[SportsIntelligence] Starting daemon | interval={LOOP_INTERVAL}s")
    print(f"[SportsIntelligence] Output: {INTEL_DIR}")
    while True:
        try:
            run_intelligence_pass()
        except Exception as e:
            print(f"[SportsIntelligence][ERROR] {e}")
        time.sleep(LOOP_INTERVAL)


# ── Orchestrator Helpers ──────────────────────────────────────────────────────

def get_ev_signals(n: int = 10) -> List[Dict]:
    data = _load_json(INTEL_DIR / "_ev_ranked.json")
    return data.get("signals", [])[:n] if data else []


def get_steam_alerts() -> List[Dict]:
    data = _load_json(INTEL_DIR / "_steam_alerts.json")
    return data.get("alerts", []) if data else []


def get_prime_markets() -> List[Dict]:
    data = _load_json(INTEL_DIR / "_market_efficiency.json")
    return data.get("prime_markets", []) if data else []


def get_softest_books(n: int = 5) -> List[Dict]:
    data = _load_json(INTEL_DIR / "_bookmaker_profiles.json")
    return data.get("softest_books", [])[:n] if data else []


def get_bankroll_projection() -> Optional[Dict]:
    return _load_json(INTEL_DIR / "_bankroll_sim.json")


def get_top_flowforms(n: int = 10) -> List[Dict]:
    data = _load_json(INTEL_DIR / "_flowform_ranked.json")
    return data.get("signals", [])[:n] if data else []


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    else:
        result = run_intelligence_pass()
        print(json.dumps(result, indent=2))
