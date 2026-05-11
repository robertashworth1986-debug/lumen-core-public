from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
OUT_EXEC = ROOT / "out" / "execution"
STATUS_JSON = OUT_EXEC / "vps_growth_controller_status.json"
HISTORY_JSONL = OUT_EXEC / "vps_growth_controller_history.jsonl"
STATUS_DASH_JSON = ROOT / "dashboard" / "data" / "vps_growth_controller_status.json"
TRADE_LOG = OUT_EXEC / "trade_log.json"
BALANCE_FILE = OUT_EXEC / "live_balance_snapshot.json"

HEARTBEAT_FILES = {
    "executor": OUT_EXEC / "live_executor_heartbeat.json",
    "engine": OUT_EXEC / "live_engine_heartbeat.json",
}

FATAL_HEARTBEAT_STATUSES = {"error", "fatal", "stopped"}

CODE_ROOT = ROOT / "code"
if str(CODE_ROOT) not in sys.path:
    sys.path.insert(0, str(CODE_ROOT))

import auto_ticket_producer as atp  # noqa: E402


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def load_trade_rows() -> List[Dict[str, Any]]:
    data = read_json(TRADE_LOG, [])
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def today_live_realized(rows: List[Dict[str, Any]]) -> float:
    today = datetime.now(timezone.utc).date().isoformat()
    total = 0.0
    for row in rows:
        mode = str(row.get("execution_mode", "")).upper()
        if mode and mode != "LIVE":
            continue
        ts = parse_dt(row.get("timestamp"))
        if ts is None or ts.date().isoformat() != today:
            continue
        total += safe_float(row.get("net_pnl"), 0.0)
    return total


def count_open_lots(rows: List[Dict[str, Any]]) -> int:
    open_count = 0
    for row in rows:
        mode = str(row.get("execution_mode", "")).upper()
        if mode and mode != "LIVE":
            continue
        if str(row.get("status", "")).upper() != "CLOSED":
            open_count += 1
    return open_count


def read_portfolio_estimate() -> float:
    payload = read_json(BALANCE_FILE, {})
    if not isinstance(payload, dict):
        return 0.0
    if "portfolio_est_total_usd" in payload:
        return safe_float(payload.get("portfolio_est_total_usd"), 0.0)
    return safe_float(payload.get("usd_balance"), 0.0)


def evaluate_heartbeat_source(source: str, path: Path, max_age_minutes: float) -> Dict[str, Any]:
    payload = read_json(path, {})
    now = datetime.now(timezone.utc)

    details: Dict[str, Any] = {
        "source": source,
        "path": str(path),
        "present": False,
        "status": "missing",
        "timestamp_utc": None,
        "age_minutes": None,
        "fresh": False,
        "alive": False,
        "reason": "missing",
    }

    if not isinstance(payload, dict) or not payload:
        return details

    details["present"] = True
    status = str(payload.get("status", "unknown") or "unknown").strip().lower()
    details["status"] = status
    details["reason"] = str(payload.get("reason") or payload.get("error") or "")

    ts = parse_dt(payload.get("timestamp_utc") or payload.get("generated_utc") or payload.get("timestamp"))
    if ts is not None:
        age = (now - ts).total_seconds() / 60.0
        details["timestamp_utc"] = ts.isoformat()
        details["age_minutes"] = round(age, 3)
        details["fresh"] = age <= max_age_minutes

    details["alive"] = bool(details["fresh"] and status not in FATAL_HEARTBEAT_STATUSES)
    return details


def heartbeat_state(max_age_minutes: float) -> Dict[str, Any]:
    checks = [
        evaluate_heartbeat_source(name, path, max_age_minutes)
        for name, path in HEARTBEAT_FILES.items()
    ]

    alive_checks = [c for c in checks if c.get("alive")]
    present_checks = [c for c in checks if c.get("present")]

    def sort_key(row: Dict[str, Any]) -> float:
        age = row.get("age_minutes")
        if isinstance(age, (int, float)):
            return float(age)
        return 1_000_000.0

    primary = None
    if alive_checks:
        primary = sorted(alive_checks, key=sort_key)[0]
    elif present_checks:
        primary = sorted(present_checks, key=sort_key)[0]
    elif checks:
        primary = checks[0]

    return {
        "ok": bool(alive_checks),
        "primary": primary or {},
        "checks": checks,
    }


def compute_guardrail_state(
    live_requested: bool,
    max_daily_loss_usd: float,
    max_open_lots: int,
    min_portfolio_usd: float,
    heartbeat_max_age_min: float,
) -> Dict[str, Any]:
    rows = load_trade_rows()
    realized_today = today_live_realized(rows)
    open_lots = count_open_lots(rows)
    portfolio_est = read_portfolio_estimate()
    hb = heartbeat_state(heartbeat_max_age_min)
    hb_ok = bool(hb.get("ok"))
    hb_primary = hb.get("primary") if isinstance(hb.get("primary"), dict) else {}
    hb_checks = hb.get("checks") if isinstance(hb.get("checks"), list) else []

    reasons: List[str] = []
    if realized_today <= -abs(max_daily_loss_usd):
        reasons.append("daily_loss_limit_triggered")
    if open_lots >= max_open_lots:
        reasons.append("open_lot_cap_reached")
    if portfolio_est < min_portfolio_usd:
        reasons.append("portfolio_below_minimum")
    if not hb_ok:
        for row in hb_checks:
            if not isinstance(row, dict):
                continue
            source = str(row.get("source", "unknown") or "unknown")
            status = str(row.get("status", "unknown") or "unknown")
            if not row.get("present"):
                reasons.append(f"{source}_heartbeat_missing")
            elif not row.get("fresh"):
                reasons.append(f"{source}_heartbeat_stale")
            elif status in FATAL_HEARTBEAT_STATUSES:
                reasons.append(f"{source}_heartbeat_{status}")
        if not reasons:
            reasons.append("heartbeat_unhealthy")

    heartbeat_warnings: List[str] = []
    for row in hb_checks:
        if not isinstance(row, dict):
            continue
        if not row.get("present"):
            continue
        status = str(row.get("status", "unknown") or "unknown")
        if status in FATAL_HEARTBEAT_STATUSES:
            source = str(row.get("source", "unknown") or "unknown")
            heartbeat_warnings.append(f"{source}_heartbeat_{status}")

    # Dedupe reasons/warnings while preserving order.
    reasons = list(dict.fromkeys(reasons))
    heartbeat_warnings = list(dict.fromkeys(heartbeat_warnings))

    allow_live = bool(live_requested and not reasons)

    return {
        "live_requested": bool(live_requested),
        "allow_live": allow_live,
        "reasons": reasons,
        "daily_realized_usd": round(realized_today, 6),
        "open_lots": int(open_lots),
        "portfolio_est_usd": round(portfolio_est, 6),
        "heartbeat_ok": hb_ok,
        "heartbeat_source": hb_primary.get("source"),
        "heartbeat_status": hb_primary.get("status"),
        "heartbeat_age_minutes": hb_primary.get("age_minutes"),
        "heartbeat_warnings": heartbeat_warnings,
        "heartbeat_checks": hb_checks,
        "trade_rows_total": len(rows),
    }


def run_cycle(args: argparse.Namespace) -> Dict[str, Any]:
    guard = compute_guardrail_state(
        live_requested=args.live,
        max_daily_loss_usd=args.max_daily_loss_usd,
        max_open_lots=args.max_open_lots,
        min_portfolio_usd=args.min_portfolio_usd,
        heartbeat_max_age_min=args.heartbeat_max_age_min,
    )

    allow_live = bool(guard["allow_live"])
    validate_mode = not allow_live

    auto_fire_score = args.auto_fire_score if allow_live else None

    summary = atp.emit_tickets(
        use_cached=args.cached,
        validate=validate_mode,
        controller=args.controller,
        bankroll=args.bankroll,
        top_n=args.top_n,
        auto_fire_score=auto_fire_score,
        gateway_url=args.gateway_url,
    )

    result = {
        "generated_utc": now_utc(),
        "schema": "kraken_live_growth_controller_v1",
        "guard": guard,
        "mode": "LIVE" if allow_live else "SAFE_DRY_RUN",
        "auto_fire_score": auto_fire_score,
        "summary": summary,
    }

    write_json(STATUS_JSON, result)
    write_json(STATUS_DASH_JSON, result)
    append_jsonl(HISTORY_JSONL, {
        "generated_utc": result["generated_utc"],
        "mode": result["mode"],
        "daily_realized_usd": guard["daily_realized_usd"],
        "open_lots": guard["open_lots"],
        "portfolio_est_usd": guard["portfolio_est_usd"],
        "allow_live": guard["allow_live"],
        "reasons": guard["reasons"],
        "emitted": summary.get("emitted_count", 0),
        "auto_fired": summary.get("auto_fired_count", 0),
    })

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Guarded Kraken growth controller: emits and optionally auto-fires live tickets only when risk constraints pass."
    )
    parser.add_argument("--daemon", action="store_true", help="Run continuously.")
    parser.add_argument("--interval-min", type=int, default=8, help="Loop interval in minutes when daemon mode is on.")
    parser.add_argument("--cached", action="store_true", help="Use cached spike-hunter snapshot instead of re-scanning.")
    parser.add_argument("--live", action="store_true", help="Request live ticket mode (still guarded).")
    parser.add_argument("--controller", default="Robert")
    parser.add_argument("--bankroll", type=float, default=150.0)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--auto-fire-score", type=float, default=86.0)
    parser.add_argument("--gateway-url", default="http://127.0.0.1:8787")
    parser.add_argument("--max-daily-loss-usd", type=float, default=20.0)
    parser.add_argument("--max-open-lots", type=int, default=2)
    parser.add_argument("--min-portfolio-usd", type=float, default=40.0)
    parser.add_argument("--heartbeat-max-age-min", type=float, default=20.0)
    args = parser.parse_args()

    while True:
        result = run_cycle(args)
        guard = result["guard"]
        summary = result["summary"]

        print(
            "[GROWTH-CTRL]"
            + f" mode={result['mode']}"
            + f" allow_live={guard['allow_live']}"
            + f" daily_realized={guard['daily_realized_usd']:.4f}"
            + f" open_lots={guard['open_lots']}"
            + f" portfolio={guard['portfolio_est_usd']:.2f}"
            + f" heartbeat={guard.get('heartbeat_source', 'none')}:{guard.get('heartbeat_status', 'unknown')}"
            + f" emitted={summary.get('emitted_count', 0)}"
            + f" auto_fired={summary.get('auto_fired_count', 0)}"
        )

        if guard["reasons"]:
            print("[GROWTH-CTRL] guard reasons=" + ",".join(guard["reasons"]))
        if guard.get("heartbeat_warnings"):
            print("[GROWTH-CTRL] heartbeat warnings=" + ",".join(guard["heartbeat_warnings"]))

        if not args.daemon:
            return 0

        time.sleep(max(60, int(args.interval_min * 60)))


if __name__ == "__main__":
    raise SystemExit(main())
