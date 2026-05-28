#!/usr/bin/env python3
"""
Build institutional sports edge artifact from existing DK/flowform outputs.

Outputs:
  INSTITUTIONAL_STACK_V2/out/ops/sports_monte_carlo_edge/sports_monte_carlo_edge_<UTC>.json
  INSTITUTIONAL_STACK_V2/out/ops/sports_monte_carlo_edge/sports_monte_carlo_edge_latest.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
DK_BOARD = ROOT / "out" / "sports_intelligence" / "_dk_alpha_board.json"
EV_RANKED = ROOT / "out" / "sports_intelligence" / "_ev_ranked.json"
OUT_DIR = ROOT / "out" / "ops" / "sports_monte_carlo_edge"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def parse_ts(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def candidate_from_board(row: Dict[str, Any], generated_utc: str) -> Dict[str, Any]:
    odds = max(1.01, to_float(row.get("dk_price_decimal"), 0.0))
    fair = max(1.01, to_float(row.get("fair_price_decimal"), odds))
    edge_pct = to_float(row.get("edge_pct"), 0.0)

    base_p = 1.0 / fair
    # Conservative shrink: cut edge optimism and cap probability realism.
    p_est = clamp(base_p * (1.0 - min(abs(edge_pct), 180.0) / 1000.0), 0.03, 0.88)
    ev_pct = ((p_est * odds) - 1.0) * 100.0

    return {
        "source": "dk_alpha_board",
        "generated_utc": generated_utc,
        "sport": row.get("sport"),
        "sport_key": row.get("sport_key"),
        "game": row.get("game"),
        "pick": row.get("pick"),
        "market": row.get("market"),
        "commence_time": row.get("commence_time"),
        "odds_decimal": round(odds, 4),
        "fair_decimal": round(fair, 4),
        "edge_pct_raw": round(edge_pct, 4),
        "p_est": round(p_est, 6),
        "ev_pct": round(ev_pct, 4),
        "alpha_score": round(to_float(row.get("alpha_score_v2"), 0.0), 4),
        "kalisha_score": round(to_float(row.get("kalisha_prediction_score"), 0.0), 4),
    }


def candidate_from_ev(sig: Dict[str, Any], generated_utc: str) -> Dict[str, Any]:
    odds = max(1.01, to_float(sig.get("best_odds"), 0.0))
    fair = max(1.01, to_float(sig.get("pinnacle_price"), odds))
    p_est = clamp(1.0 / fair, 0.03, 0.9)
    ev_pct = ((p_est * odds) - 1.0) * 100.0

    game = f"{sig.get('away_team','?')} @ {sig.get('home_team','?')}"
    pick = sig.get("outcome") or sig.get("signal_type")

    return {
        "source": "ev_ranked",
        "generated_utc": generated_utc,
        "sport": sig.get("sport_title"),
        "sport_key": sig.get("sport_key"),
        "game": game,
        "pick": pick,
        "market": sig.get("market"),
        "commence_time": sig.get("commence_time"),
        "odds_decimal": round(odds, 4),
        "fair_decimal": round(fair, 4),
        "edge_pct_raw": round(to_float(sig.get("edge_pct"), 0.0), 4),
        "p_est": round(p_est, 6),
        "ev_pct": round(ev_pct, 4),
        "alpha_score": round(to_float(sig.get("score"), 0.0), 4),
        "kalisha_score": round(to_float(sig.get("adaptive_router", {}).get("family_confidence"), 0.0) * 100.0, 4),
    }


def make_key(c: Dict[str, Any]) -> str:
    return "|".join(
        str(c.get(k, "")).strip().lower()
        for k in ("sport_key", "game", "market", "pick")
    )


def utility_single(c: Dict[str, Any], bankroll: float) -> float:
    odds = to_float(c.get("odds_decimal"), 1.01)
    p = clamp(to_float(c.get("p_est"), 0.0), 0.01, 0.95)
    stake = max(0.25, min(1.5, bankroll * 0.08))
    f = stake / max(bankroll, 1e-9)
    win_mult = 1.0 + f * (odds - 1.0)
    lose_mult = 1.0 - f
    if lose_mult <= 0:
        return -999.0
    return p * math.log(win_mult) + (1.0 - p) * math.log(lose_mult)


def combo_metrics(combo: List[Dict[str, Any]], stake: float) -> Dict[str, Any]:
    p = 1.0
    payout = 1.0
    for c in combo:
        p *= clamp(to_float(c.get("p_est"), 0.0), 0.01, 0.95)
        payout *= max(1.01, to_float(c.get("odds_decimal"), 1.01))
    ev = stake * ((p * payout) - 1.0)
    score = ev * (0.35 + min(p, 0.65))
    return {
        "legs": [
            {
                "sport": c.get("sport"),
                "game": c.get("game"),
                "pick": c.get("pick"),
                "market": c.get("market"),
                "odds_decimal": c.get("odds_decimal"),
                "p_est": c.get("p_est"),
            }
            for c in combo
        ],
        "p_hit": round(p, 8),
        "payout_multiple": round(payout, 6),
        "stake_usd": round(stake, 2),
        "expected_profit_usd": round(ev, 4),
        "risk_adjusted_score": round(score, 6),
    }


def build(bankroll: float, top_n: int, pick6_limit: int) -> Dict[str, Any]:
    board = load_json(DK_BOARD) or {}
    ev = load_json(EV_RANKED) or {}

    board_rows = board.get("rows") if isinstance(board, dict) else []
    ev_rows = ev.get("signals") if isinstance(ev, dict) else []

    cand: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    for row in board_rows if isinstance(board_rows, list) else []:
        c = candidate_from_board(row, str(board.get("generated_utc") or ""))
        ts = parse_ts(str(c.get("commence_time") or ""))
        if ts and ts < now:
            continue
        cand.append(c)

    for sig in ev_rows if isinstance(ev_rows, list) else []:
        c = candidate_from_ev(sig, str(ev.get("generated_utc") or ""))
        ts = parse_ts(str(c.get("commence_time") or ""))
        if ts and ts < now:
            continue
        cand.append(c)

    dedup: Dict[str, Dict[str, Any]] = {}
    for c in cand:
        k = make_key(c)
        score = utility_single(c, bankroll) + to_float(c.get("ev_pct"), 0.0) / 1000.0
        c["single_utility"] = round(score, 8)
        prev = dedup.get(k)
        if prev is None or to_float(c.get("single_utility"), -999) > to_float(prev.get("single_utility"), -999):
            dedup[k] = c

    pool = list(dedup.values())
    pool.sort(key=lambda x: (to_float(x.get("single_utility"), -999), to_float(x.get("ev_pct"), -999)), reverse=True)

    elite = pool[: max(1, top_n)]

    combos: List[Dict[str, Any]] = []
    combo_pool = elite[: min(10, len(elite))]
    if len(combo_pool) >= 6:
        for combo in itertools.combinations(combo_pool, 6):
            combos.append(combo_metrics(list(combo), stake=1.0))

    combos.sort(key=lambda x: x["risk_adjusted_score"], reverse=True)
    combos = combos[: max(1, pick6_limit)]

    master = elite[0] if elite else None
    teaser = elite[2:4] if len(elite) >= 4 else elite[:2]

    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "bankroll_usd": bankroll,
        "candidate_count": len(pool),
        "elite_count": len(elite),
        "pick6_count": len(combos),
        "master_bet": master,
        "public_teaser": teaser,
        "elite_singles": elite,
        "pick6_elite": combos,
        "notes": [
            "Conservative probability shrink is applied to avoid overfit edges.",
            "Pick-6 combos are ranked by risk-adjusted expected value, not payout hype.",
            "This is a decision support artifact, not guaranteed outcomes.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build sports Monte Carlo elite edge artifact")
    parser.add_argument("--bankroll", type=float, default=10.0)
    parser.add_argument("--top-n", type=int, default=12)
    parser.add_argument("--pick6-limit", type=int, default=6)
    args = parser.parse_args()

    payload = build(bankroll=args.bankroll, top_n=args.top_n, pick6_limit=args.pick6_limit)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now_utc()
    stamped = OUT_DIR / f"sports_monte_carlo_edge_{stamp}.json"
    latest = OUT_DIR / "sports_monte_carlo_edge_latest.json"

    stamped.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    latest.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"SPORTS_MONTE_CARLO_EDGE_JSON={stamped}")
    print(f"SPORTS_MONTE_CARLO_EDGE_LATEST={latest}")
    print(f"SPORTS_MONTE_CARLO_EDGE_COUNTS candidates={payload['candidate_count']} elite={payload['elite_count']} pick6={payload['pick6_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
