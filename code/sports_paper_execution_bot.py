from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
OUT = ROOT / "out" / "sports_intelligence"
ALPHA_BOARD_FILE = OUT / "_dk_alpha_board.json"
LEDGER_FILE = OUT / "paper_bets_ledger.jsonl"
STATE_FILE = OUT / "paper_betting_state.json"
SUMMARY_FILE = OUT / "paper_betting_summary.json"
ENV_FILE = CODE / "execution" / "config" / "luma_live_keys.env"
API_BASE = "https://api.the-odds-api.com/v4"


@dataclass
class Config:
    bankroll: float
    max_bet: float
    min_edge: float
    kelly_fraction: float
    days_from: int


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            raw = path.read_text(encoding="utf-8")
            raw = raw.replace(": NaN", ": null").replace(":NaN", ":null")
            return json.loads(raw)
    except Exception:
        pass
    return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            if isinstance(rec, dict):
                out.append(rec)
        except Exception:
            continue
    return out


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        if k and not os.getenv(k):
            os.environ[k] = v


def get_odds_api_key() -> str:
    for name in ("THEODDS_API_KEY", "ODDS_API_KEY", "SPORTS_ODDS_API_KEY"):
        val = (os.getenv(name) or "").strip()
        if val:
            return val
    return ""


def parse_dt(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def ticket_id(alert_id: str, commence_time: str) -> str:
    digest = hashlib.sha1(f"{alert_id}|{commence_time}".encode("utf-8")).hexdigest()[:16]
    return f"PAPER-{digest.upper()}"


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def score_winner(event: dict[str, Any]) -> str | None:
    scores = event.get("scores")
    if not isinstance(scores, list):
        return None
    parsed: list[tuple[str, float]] = []
    for row in scores:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        score = safe_float(row.get("score"), -1e9)
        if name:
            parsed.append((name, score))
    if len(parsed) < 2:
        return None
    parsed.sort(key=lambda x: x[1], reverse=True)
    if parsed[0][1] == parsed[1][1]:
        return None
    return parsed[0][0]


def normalize_text(x: Any) -> str:
    return " ".join(str(x or "").lower().replace("@", " ").replace("-", " ").split())


def match_event_for_ticket(ticket: dict[str, Any], events: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    event_id = str(ticket.get("event_id") or "")
    if event_id and event_id in events:
        return events[event_id]

    pick = normalize_text(ticket.get("pick"))
    commence_ticket = str(ticket.get("commence_time") or "")

    for ev in events.values():
        if not isinstance(ev, dict):
            continue
        home = normalize_text(ev.get("home_team"))
        away = normalize_text(ev.get("away_team"))
        teams_blob = f"{home} {away}"
        commence_ev = str(ev.get("commence_time") or "")

        if pick and pick not in teams_blob:
            continue
        if commence_ticket and commence_ev and commence_ticket[:16] != commence_ev[:16]:
            continue
        return ev
    return None


def fetch_scores_for_sport(api_key: str, sport_key: str, days_from: int) -> dict[str, dict[str, Any]]:
    url = f"{API_BASE}/sports/{sport_key}/scores"
    params = {"apiKey": api_key, "daysFrom": days_from}
    try:
        resp = requests.get(url, params=params, timeout=45)
        resp.raise_for_status()
        payload = resp.json()
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(payload, list):
        return out
    for ev in payload:
        if isinstance(ev, dict) and ev.get("id"):
            out[str(ev["id"])] = ev
    return out


def place_paper_bets(rows: list[dict[str, Any]], state: dict[str, Any], cfg: Config) -> list[dict[str, Any]]:
    open_tickets = state.setdefault("open_tickets", [])
    existing_ids = {str(t.get("ticket_id")) for t in open_tickets if isinstance(t, dict)}

    placed: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        edge = safe_float(row.get("edge_pct"))
        if edge < cfg.min_edge:
            continue

        alert_id = str(row.get("alert_id") or "")
        commence = str(row.get("commence_time") or "")
        sport_key = str(row.get("sport_key") or "")
        event_id = str(row.get("event_id") or "")
        if not alert_id or not commence or not sport_key:
            continue

        t_id = ticket_id(alert_id, commence)
        if t_id in existing_ids:
            continue

        base_stake = safe_float(row.get("optimized_stake"), 0.0)
        kelly_go_f = safe_float(row.get("kelly_go_f"), 0.0)
        kelly_stake = state["bankroll"] * kelly_go_f * cfg.kelly_fraction
        stake = min(cfg.max_bet, max(base_stake, kelly_stake))
        if stake <= 0:
            continue

        ticket = {
            "ticket_id": t_id,
            "status": "OPEN",
            "placed_utc": now_utc(),
            "sport_key": sport_key,
            "event_id": event_id,
            "commence_time": commence,
            "market": row.get("market", "h2h"),
            "pick": row.get("pick"),
            "dk_price_decimal": safe_float(row.get("dk_price_decimal"), 0.0),
            "dk_price_american": row.get("dk_price_american"),
            "edge_pct": edge,
            "alpha_score_v2": safe_float(row.get("alpha_score_v2"), 0.0),
            "stake": round(stake, 2),
            "alert_id": alert_id,
        }
        open_tickets.append(ticket)
        append_jsonl(LEDGER_FILE, {"event": "PAPER_BET_PLACED", **ticket})
        existing_ids.add(t_id)
        placed.append(ticket)
    return placed


def settle_open_tickets(state: dict[str, Any], scores_cache: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    open_tickets = [t for t in state.get("open_tickets", []) if isinstance(t, dict)]
    still_open: list[dict[str, Any]] = []
    settled: list[dict[str, Any]] = []

    for t in open_tickets:
        sport_key = str(t.get("sport_key") or "")
        event = match_event_for_ticket(t, scores_cache.get(sport_key, {}))

        if not event or not bool(event.get("completed", False)):
            still_open.append(t)
            continue

        winner = score_winner(event)
        pick = str(t.get("pick") or "")
        stake = safe_float(t.get("stake"), 0.0)
        dec = safe_float(t.get("dk_price_decimal"), 0.0)

        if winner is None:
            pnl = 0.0
            outcome = "PUSH"
        elif winner == pick:
            pnl = stake * (dec - 1.0)
            outcome = "WIN"
        else:
            pnl = -stake
            outcome = "LOSS"

        settlement = {
            **t,
            "status": "SETTLED",
            "settled_utc": now_utc(),
            "outcome": outcome,
            "winner": winner,
            "pnl": round(pnl, 2),
        }
        settled.append(settlement)
        append_jsonl(LEDGER_FILE, {"event": "PAPER_BET_SETTLED", **settlement})
        state["bankroll"] = round(state.get("bankroll", 0.0) + pnl, 2)

    state["open_tickets"] = still_open
    history = state.setdefault("settled_tickets", [])
    history.extend(settled)
    return settled


def summarize(state: dict[str, Any], placed: list[dict[str, Any]], settled: list[dict[str, Any]]) -> dict[str, Any]:
    settled_all = [t for t in state.get("settled_tickets", []) if isinstance(t, dict)]
    wins = sum(1 for t in settled_all if t.get("outcome") == "WIN")
    losses = sum(1 for t in settled_all if t.get("outcome") == "LOSS")
    pushes = sum(1 for t in settled_all if t.get("outcome") == "PUSH")
    pnl = round(sum(safe_float(t.get("pnl"), 0.0) for t in settled_all), 2)
    n = wins + losses
    win_rate = round((wins / n * 100.0), 2) if n > 0 else 0.0

    return {
        "generated_utc": now_utc(),
        "bankroll": round(safe_float(state.get("bankroll"), 0.0), 2),
        "open_count": len(state.get("open_tickets", [])),
        "placed_this_run": len(placed),
        "settled_this_run": len(settled),
        "settled_total": len(settled_all),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate_pct": win_rate,
        "pnl_total": pnl,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Institutional sports paper execution bot")
    p.add_argument("--bankroll", type=float, default=100000.0)
    p.add_argument("--max-bet", type=float, default=2500.0)
    p.add_argument("--min-edge", type=float, default=1.0)
    p.add_argument("--kelly-fraction", type=float, default=0.25)
    p.add_argument("--days-from", type=int, default=3)
    return p


def main() -> None:
    args = build_parser().parse_args()
    cfg = Config(
        bankroll=args.bankroll,
        max_bet=args.max_bet,
        min_edge=args.min_edge,
        kelly_fraction=args.kelly_fraction,
        days_from=args.days_from,
    )

    load_env_file(ENV_FILE)
    api_key = get_odds_api_key()

    board = load_json(ALPHA_BOARD_FILE, {})
    rows = board.get("rows", []) if isinstance(board, dict) else []

    state = load_json(STATE_FILE, {
        "created_utc": now_utc(),
        "bankroll": cfg.bankroll,
        "open_tickets": [],
        "settled_tickets": [],
    })
    state.setdefault("bankroll", cfg.bankroll)

    placed = place_paper_bets(rows, state, cfg)

    scores_cache: dict[str, dict[str, dict[str, Any]]] = {}
    if api_key:
        sport_keys = sorted({str(t.get("sport_key")) for t in state.get("open_tickets", []) if isinstance(t, dict) and t.get("sport_key")})
        for sk in sport_keys:
            scores_cache[sk] = fetch_scores_for_sport(api_key, sk, cfg.days_from)

    settled = settle_open_tickets(state, scores_cache)

    summary = summarize(state, placed, settled)
    write_json(STATE_FILE, state)
    write_json(SUMMARY_FILE, summary)

    print("PAPER BOT OK")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
