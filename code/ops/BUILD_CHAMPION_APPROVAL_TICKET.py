from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT_EXEC = ROOT / "out" / "execution"
OUT_OPS = ROOT / "out" / "ops"
CONFIG = ROOT / "config"

HEARTBEAT_FILE = OUT_EXEC / "live_executor_heartbeat.json"
RUNTIME_FILE = CONFIG / "runtime_control.json"
FILTERED_PROOF_FILE = OUT_EXEC / "filtered_proof.json"
LATEST_TICKET_FILE = OUT_EXEC / "champion_approval_ticket_latest.json"

PAIR_QUOTES = ("USDT", "USDC", "USD", "EUR", "GBP", "AUD", "JPY")
SYMBOL_ALIAS = {
    "XBT": "BTC",
    "XDG": "DOGE",
    "XXRP": "XRP",
    "XETH": "ETH",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(value, hi))


def split_pair(pair: str) -> tuple[str, str]:
    raw = str(pair or "").upper().strip()
    for quote in PAIR_QUOTES:
        if raw.endswith(quote) and len(raw) > len(quote):
            base = raw[: -len(quote)]
            return SYMBOL_ALIAS.get(base, base), quote
    return SYMBOL_ALIAS.get(raw, raw), ""


def load_validation_scores() -> dict[str, float]:
    rows = load_json(FILTERED_PROOF_FILE, [])
    out: dict[str, float] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        if bool(row.get("suspicious", False)):
            continue
        pair = str(row.get("pair", "")).upper().strip()
        if not pair:
            continue
        score = safe_float(row.get("validation_score", 0.0), 0.0)
        if score <= 0.0:
            continue
        out[pair] = max(score, out.get(pair, 0.0))
    return out


def latest_symbol_metrics_csv() -> Path | None:
    candidates = sorted(
        OUT_OPS.glob("symbol_spike_study_*/symbol_metrics.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load_trap_rates() -> dict[tuple[str, str], float]:
    metrics_path = latest_symbol_metrics_csv()
    out: dict[tuple[str, str], float] = {}
    if metrics_path is None:
        return out
    try:
        with metrics_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = str(row.get("symbol", "")).upper().strip()
                quote = str(row.get("quote", "")).upper().strip()
                if not symbol or not quote:
                    continue
                trap_rate = safe_float(row.get("trap_rate_pct", 0.0), 0.0)
                out[(SYMBOL_ALIAS.get(symbol, symbol), quote)] = trap_rate
    except Exception:
        return {}
    return out


def load_symbol_metrics() -> dict[tuple[str, str], dict[str, float]]:
    metrics_path = latest_symbol_metrics_csv()
    out: dict[tuple[str, str], dict[str, float]] = {}
    if metrics_path is None:
        return out
    try:
        with metrics_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                symbol = str(row.get("symbol", "")).upper().strip()
                quote = str(row.get("quote", "")).upper().strip()
                if not symbol or not quote:
                    continue
                key = (SYMBOL_ALIAS.get(symbol, symbol), quote)
                out[key] = {
                    "quick_gain_score": safe_float(row.get("quick_gain_score", 0.0), 0.0),
                    "spike_power_score": safe_float(row.get("spike_power_score", 0.0), 0.0),
                    "best_buy_win_rate_pct": safe_float(row.get("best_buy_win_rate_pct", 0.0), 0.0),
                    "trap_rate_pct": safe_float(row.get("trap_rate_pct", 0.0), 0.0),
                }
    except Exception:
        return {}
    return out


def build_ticket() -> dict[str, Any]:
    heartbeat = load_json(HEARTBEAT_FILE, {})
    runtime = load_json(RUNTIME_FILE, {})
    validation_scores = load_validation_scores()
    trap_rates = load_trap_rates()
    symbol_metrics = load_symbol_metrics()

    status = str(heartbeat.get("status", "")).lower()
    reason = str(heartbeat.get("reason", "")).lower()
    error_text = str(heartbeat.get("error", "")).lower()

    pair = str(heartbeat.get("pair", "")).upper().strip()
    symbol = str(heartbeat.get("symbol", heartbeat.get("selected_symbol", ""))).upper().strip()
    side = str(heartbeat.get("side", "buy")).lower().strip()

    if not pair and symbol:
        pair = f"{symbol}USD"

    base_symbol, quote_symbol = split_pair(pair)
    if not symbol:
        symbol = base_symbol

    metrics = symbol_metrics.get((SYMBOL_ALIAS.get(base_symbol, base_symbol), quote_symbol), {})
    metrics_quick = safe_float(metrics.get("quick_gain_score", 0.0), 0.0)
    metrics_spike = safe_float(metrics.get("spike_power_score", 0.0), 0.0)
    metrics_win = safe_float(metrics.get("best_buy_win_rate_pct", 0.0), 0.0)

    edge_score = clamp(safe_float(heartbeat.get("edge_score", 0.0), 0.0), 0.0, 1.5)
    if edge_score <= 0.0 and metrics_quick > 0.0:
        edge_score = clamp((metrics_quick / 2.2), 0.0, 1.2)

    spread_bps = max(
        safe_float(heartbeat.get("spread_bps", heartbeat.get("selected_spread_bps", 0.0)), 0.0),
        0.0,
    )
    last_price = max(safe_float(heartbeat.get("entry_price", 0.0), 0.0), 0.0)

    validation_score = validation_scores.get(pair, 0.0)
    if validation_score <= 0.0 and metrics_spike > 0.0:
        validation_score = metrics_spike * 25.0

    val_norm = clamp(math.log10(1.0 + max(validation_score, 0.0)) / 2.8, 0.0, 1.0)

    approval_min_edge_score = clamp(safe_float(runtime.get("approval_min_edge_score", 0.86), 0.86), 0.0, 2.0)
    approval_max_spread_bps = max(safe_float(runtime.get("approval_max_spread_bps", 8.0), 8.0), 0.5)
    approval_max_trap_rate_pct = clamp(safe_float(runtime.get("approval_max_trap_rate_pct", 42.0), 42.0), 1.0, 100.0)
    approval_min_validation_score = max(safe_float(runtime.get("approval_min_validation_score", 40.0), 40.0), 0.0)
    approval_min_winner_score = clamp(safe_float(runtime.get("approval_min_winner_score", 0.82), 0.82), 0.0, 1.0)

    trap_rate = trap_rates.get((SYMBOL_ALIAS.get(base_symbol, base_symbol), quote_symbol), 0.0)
    if trap_rate <= 35.0:
        trap_factor = 1.0
    elif trap_rate <= 45.0:
        trap_factor = 0.85
    else:
        trap_factor = 0.70

    spread_factor = clamp(1.0 - (spread_bps / 40.0), 0.35, 1.0)
    edge_factor = clamp(0.45 + (0.90 * edge_score) + (0.45 * val_norm), 0.45, 1.60)

    size_hint = max(safe_float(heartbeat.get("size_usd", 0.0), 0.0), 0.0)
    min_notional = max(
        safe_float(heartbeat.get("selected_min_order_notional_effective", 0.0), 0.0),
        safe_float(heartbeat.get("selected_min_order_notional", 0.0), 0.0),
    )

    config_cap = max(safe_float(runtime.get("max_notional_per_trade_usd", 0.0), 0.0), 0.0)
    cap_floor = max(safe_float(runtime.get("pilot_cap_floor_usd", 1.0), 1.0), min_notional)
    cap_ceiling = max(safe_float(runtime.get("pilot_cap_ceiling_usd", 6.0), 6.0), cap_floor)

    base_cap = config_cap if config_cap > 0.0 else max(size_hint, min_notional, cap_floor)
    scored_cap = base_cap * edge_factor * spread_factor * trap_factor

    if size_hint > 0.0:
        scored_cap = min(scored_cap, size_hint * 1.35)

    recommended_cap_usd = clamp(scored_cap, cap_floor, cap_ceiling)

    if last_price > 0.0:
        recommended_qty = recommended_cap_usd / last_price
    else:
        recommended_qty = 0.0

    edge_component = clamp((edge_score - 0.60) / 0.40, 0.0, 1.0)
    spread_component = clamp((approval_max_spread_bps - spread_bps) / approval_max_spread_bps, 0.0, 1.0)
    trap_component = clamp((approval_max_trap_rate_pct - trap_rate) / approval_max_trap_rate_pct, 0.0, 1.0)
    validation_component = 1.0 if validation_score >= approval_min_validation_score else 0.0
    winner_score = (
        (0.38 * edge_component)
        + (0.24 * spread_component)
        + (0.24 * trap_component)
        + (0.14 * validation_component)
    )

    passes_edge = edge_score >= approval_min_edge_score
    passes_spread = spread_bps <= approval_max_spread_bps
    passes_trap = trap_rate <= approval_max_trap_rate_pct
    passes_validation = validation_score >= approval_min_validation_score
    passes_winner_score = winner_score >= approval_min_winner_score

    recommendation_ready = bool(
        pair
        and symbol
        and side in {"buy", "sell"}
        and status in {"ok", "degraded", "blocked"}
        and ("live_orders_disabled" in error_text or reason in {"risk", "order_failed", "blocked"})
        and recommended_cap_usd > 0.0
        and passes_edge
        and passes_spread
        and passes_trap
        and passes_validation
        and passes_winner_score
    )

    decision = "APPROVE" if recommendation_ready else "HOLD"

    return {
        "generated_utc": now_utc(),
        "scope": "champion_approval_ticket",
        "evidence": {
            "heartbeat": str(HEARTBEAT_FILE),
            "runtime_control": str(RUNTIME_FILE),
            "filtered_proof": str(FILTERED_PROOF_FILE),
            "symbol_metrics": str(latest_symbol_metrics_csv() or ""),
        },
        "status": {
            "heartbeat_status": status,
            "heartbeat_reason": reason,
            "heartbeat_error": error_text,
            "allow_live_orders": bool(runtime.get("allow_live_orders", False)),
            "kill_switch": bool(runtime.get("kill_switch", False)),
            "ready_for_approval": recommendation_ready,
            "decision": decision,
        },
        "candidate": {
            "symbol": symbol,
            "pair": pair,
            "side": side,
            "edge_score": round(edge_score, 6),
            "metrics_quick_gain_score": round(metrics_quick, 6),
            "metrics_spike_power_score": round(metrics_spike, 6),
            "metrics_best_buy_win_rate_pct": round(metrics_win, 6),
            "spread_bps": round(spread_bps, 6),
            "validation_score": round(validation_score, 6),
            "trap_rate_pct": round(trap_rate, 6),
            "size_hint_usd": round(size_hint, 6),
            "min_order_notional_usd": round(min_notional, 6),
            "recommended_cap_usd": round(recommended_cap_usd, 6),
            "recommended_qty": round(recommended_qty, 10),
            "winner_score": round(float(winner_score), 6),
            "thresholds": {
                "approval_min_edge_score": round(float(approval_min_edge_score), 6),
                "approval_max_spread_bps": round(float(approval_max_spread_bps), 6),
                "approval_max_trap_rate_pct": round(float(approval_max_trap_rate_pct), 6),
                "approval_min_validation_score": round(float(approval_min_validation_score), 6),
                "approval_min_winner_score": round(float(approval_min_winner_score), 6),
            },
            "checks": {
                "passes_edge": bool(passes_edge),
                "passes_spread": bool(passes_spread),
                "passes_trap": bool(passes_trap),
                "passes_validation": bool(passes_validation),
                "passes_winner_score": bool(passes_winner_score),
            },
            "cap_factors": {
                "edge_factor": round(edge_factor, 6),
                "spread_factor": round(spread_factor, 6),
                "trap_factor": round(trap_factor, 6),
                "base_cap_usd": round(base_cap, 6),
                "cap_floor_usd": round(cap_floor, 6),
                "cap_ceiling_usd": round(cap_ceiling, 6),
            },
        },
        "approval_note": "Manual approval required before placing this order.",
    }


def write_outputs(ticket: dict[str, Any]) -> tuple[Path, Path, Path]:
    OUT_OPS.mkdir(parents=True, exist_ok=True)
    OUT_EXEC.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_json = OUT_OPS / f"champion_approval_ticket_{stamp}.json"
    out_md = OUT_OPS / f"champion_approval_ticket_{stamp}.md"

    out_json.write_text(json.dumps(ticket, indent=2), encoding="utf-8")
    LATEST_TICKET_FILE.write_text(json.dumps(ticket, indent=2), encoding="utf-8")

    candidate = ticket.get("candidate", {})
    status = ticket.get("status", {})
    lines = [
        "# Champion Approval Ticket",
        "",
        f"Generated UTC: {ticket.get('generated_utc', '')}",
        f"Ready For Approval: {status.get('ready_for_approval', False)}",
        f"Decision: {status.get('decision', 'HOLD')}",
        f"Heartbeat Status: {status.get('heartbeat_status', '')} / {status.get('heartbeat_reason', '')}",
        "",
        "## Candidate",
        f"- Symbol: {candidate.get('symbol', '')}",
        f"- Pair: {candidate.get('pair', '')}",
        f"- Side: {candidate.get('side', '')}",
        f"- Edge Score: {candidate.get('edge_score', 0)}",
        f"- Spread (bps): {candidate.get('spread_bps', 0)}",
        f"- Validation Score: {candidate.get('validation_score', 0)}",
        f"- Trap Rate (%): {candidate.get('trap_rate_pct', 0)}",
        f"- Winner Score: {candidate.get('winner_score', 0)}",
        f"- Recommended Cap USD: {candidate.get('recommended_cap_usd', 0)}",
        f"- Recommended Qty: {candidate.get('recommended_qty', 0)}",
        "",
        "## Notes",
        "- Live execution is guarded by runtime_control allow_live_orders and kill_switch.",
        "- This ticket is for manual approve/reject workflow.",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_json, out_md, LATEST_TICKET_FILE


def main() -> None:
    ticket = build_ticket()
    out_json, out_md, latest = write_outputs(ticket)
    print(
        json.dumps(
            {
                "status": "ok",
                "ready_for_approval": bool(ticket.get("status", {}).get("ready_for_approval", False)),
                "symbol": str(ticket.get("candidate", {}).get("symbol", "")),
                "pair": str(ticket.get("candidate", {}).get("pair", "")),
                "recommended_cap_usd": ticket.get("candidate", {}).get("recommended_cap_usd", 0.0),
                "out_json": str(out_json),
                "out_md": str(out_md),
                "latest_ticket": str(latest),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
