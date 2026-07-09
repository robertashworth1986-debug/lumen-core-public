from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out"
OUT_OPS = OUT / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"
CONFIG = ROOT / "config"

ALPHA_MAP = OUT_OPS / "kraken_multi_tf_alpha_map_latest.json"
PAPER_CONTROL = OUT_OPS / "kraken_paper_innovation_control_room_latest.json"
TRADING_AUDIT = OUT_OPS / "trading_stack_safety_audit_latest.json"
GLOBAL_RUNTIME = CONFIG / "runtime_control.json"
KRAKEN_RUNTIME = CONFIG / "accounts" / "KRAKEN_PRIMARY" / "runtime_control.json"

OUT_JSON = OUT_OPS / "kraken_institutional_alpha_gauntlet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "kraken_institutional_alpha_gauntlet.json"
OUT_MD = DOCS / "KRAKEN_INSTITUTIONAL_ALPHA_GAUNTLET_2026-07-09.md"

SENSITIVE_MARKERS = [
    "password",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "live", "enabled"}
    return False


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def score_log_turnover(turnover_usd: float) -> float:
    if turnover_usd <= 0:
        return 0.0
    return clamp((math.log10(turnover_usd) - 5.0) / 4.0 * 100.0)


def execution_score(spread_bps: float) -> float:
    if spread_bps <= 5:
        return 100.0
    if spread_bps >= 60:
        return 0.0
    return clamp(100.0 - ((spread_bps - 5.0) / 55.0 * 100.0))


def stress_score(range_24h_pct: float, change_24h_pct: float, hv_24h_pct: float) -> float:
    range_penalty = clamp(range_24h_pct / 80.0 * 45.0, 0.0, 45.0)
    move_penalty = clamp(abs(change_24h_pct) / 45.0 * 35.0, 0.0, 35.0)
    hv_penalty = clamp(hv_24h_pct / 10.0 * 20.0, 0.0, 20.0)
    return clamp(100.0 - range_penalty - move_penalty - hv_penalty)


def signal_score(row: dict[str, Any]) -> float:
    alpha = safe_float(row.get("alpha_edge_score"))
    momentum = abs(safe_float(row.get("momentum_score")))
    trend = abs(safe_float(row.get("trend_score")))
    reversion = abs(safe_float(row.get("reversion_score")))
    strategy = str(row.get("strategy_mode") or "")
    raw = (
        clamp(alpha / 25.0 * 50.0, 0.0, 50.0)
        + clamp(max(momentum, trend, reversion) / 55.0 * 35.0, 0.0, 35.0)
        + (15.0 if strategy in {"momentum_snipe", "mean_reversion_snapback", "trend_follow_swing"} else 4.0)
    )
    return clamp(raw)


def replay_score(row: dict[str, Any]) -> float:
    best_buy = int(safe_float(row.get("best_buy_hour_utc"), -1))
    best_sell = int(safe_float(row.get("best_sell_hour_utc"), -1))
    if best_buy < 0 or best_sell < 0:
        return 20.0
    if best_buy == best_sell:
        return 45.0
    return 80.0


def capacity_status(turnover_usd: float, spread_bps: float) -> dict[str, Any]:
    conservative_participation = turnover_usd * 0.00005
    replay_notional_cap = round(max(min(conservative_participation, 250.0), 0.0), 2)
    if turnover_usd >= 25_000_000 and spread_bps <= 10.0:
        tier = "institutional_capacity_research_candidate"
    elif turnover_usd >= 2_500_000 and spread_bps <= 20.0:
        tier = "small_fund_capacity_research_candidate"
    elif turnover_usd >= 500_000:
        tier = "micro_paper_capacity_only"
    else:
        tier = "watch_only_capacity"
    return {
        "capacity_tier": tier,
        "conservative_paper_notional_cap_usd": replay_notional_cap,
        "large_fund_capacity_proven": False,
        "large_fund_gap": "needs depth, impact, fill-quality, venue-fragmentation, and multi-month capacity evidence",
    }


def tier_for(score: float, execution: float, stress: float, capacity: dict[str, Any]) -> str:
    if score >= 85.0 and execution >= 75.0 and stress >= 70.0 and capacity["capacity_tier"].startswith("institutional"):
        return "institutional_research_candidate_paper_only"
    if score >= 70.0 and execution >= 55.0 and stress >= 55.0:
        return "priority_paper_replay"
    if score >= 55.0:
        return "watchlist_paper_research"
    return "reject_until_better_evidence"


def fail_reasons(row: dict[str, Any], execution: float, stress: float, capacity: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if execution < 55.0:
        reasons.append("execution_spread_too_weak_for_promotion")
    if stress < 55.0:
        reasons.append("volatility_or_move_stress_too_high")
    if capacity["capacity_tier"] in {"micro_paper_capacity_only", "watch_only_capacity"}:
        reasons.append("capacity_not_institutional_yet")
    if str(row.get("strategy_mode") or "") == "watch":
        reasons.append("strategy_mode_watch_only")
    if not reasons:
        reasons.append("no_research_fail_reason_but_live_still_blocked")
    return reasons


def gauntlet_rows(alpha_map: dict[str, Any]) -> list[dict[str, Any]]:
    leaders = alpha_map.get("alpha_leaderboard") if isinstance(alpha_map.get("alpha_leaderboard"), list) else []
    rows: list[dict[str, Any]] = []
    for rank, row in enumerate(leaders, start=1):
        if not isinstance(row, dict):
            continue
        spread = safe_float(row.get("spread_bps"))
        turnover = safe_float(row.get("turnover_24h_usd"))
        range_24h = safe_float(row.get("range_24h_pct"))
        change_24h = safe_float(row.get("change_24h_pct"))
        hv_24h = safe_float(row.get("hv_24h_pct"))
        sig = signal_score(row)
        exe = execution_score(spread)
        cap_score = score_log_turnover(turnover)
        stress = stress_score(range_24h, change_24h, hv_24h)
        replay = replay_score(row)
        capacity = capacity_status(turnover, spread)
        institutional = round(sig * 0.35 + exe * 0.18 + cap_score * 0.17 + stress * 0.18 + replay * 0.12, 6)
        item = {
            "rank": rank,
            "pair": row.get("pair"),
            "wsname": row.get("wsname"),
            "strategy_mode": row.get("strategy_mode"),
            "signal_quality_score": round(sig, 6),
            "execution_quality_score": round(exe, 6),
            "capacity_quality_score": round(cap_score, 6),
            "stress_survivability_score": round(stress, 6),
            "replay_readiness_score": round(replay, 6),
            "institutional_alpha_score": institutional,
            "institutional_tier": tier_for(institutional, exe, stress, capacity),
            "promotion_fail_reasons": fail_reasons(row, exe, stress, capacity),
            "capacity": capacity,
            "raw_market_metrics": {
                "alpha_edge_score": safe_float(row.get("alpha_edge_score")),
                "spread_bps": spread,
                "turnover_24h_usd": turnover,
                "range_24h_pct": range_24h,
                "change_24h_pct": change_24h,
                "hv_24h_pct": hv_24h,
                "best_buy_hour_utc": int(safe_float(row.get("best_buy_hour_utc"), -1)),
                "best_sell_hour_utc": int(safe_float(row.get("best_sell_hour_utc"), -1)),
            },
            "allowed_next_step": "paper_replay_and_slippage_stress_only",
            "live_order_allowed": False,
        }
        item["gauntlet_row_sha256"] = stable_sha256(item)
        rows.append(item)
    rows.sort(key=lambda r: safe_float(r.get("institutional_alpha_score")), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["gauntlet_rank"] = idx
        row["gauntlet_row_sha256"] = stable_sha256(row)
    return rows


def artifact_status(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def runtime_summary(global_runtime: dict[str, Any], kraken_runtime: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "global_mode": str(global_runtime.get("mode") or "").lower(),
        "kraken_mode": str(kraken_runtime.get("mode") or "").lower(),
        "global_allow_live_orders": truthy(global_runtime.get("allow_live_orders")),
        "kraken_allow_live_orders": truthy(kraken_runtime.get("allow_live_orders")),
        "audit_posture": str(audit.get("posture") or ""),
        "audit_blockers": list(audit.get("blockers") or []),
    }


def build_payload() -> dict[str, Any]:
    alpha_map = read_json(ALPHA_MAP)
    paper_control = read_json(PAPER_CONTROL)
    audit = read_json(TRADING_AUDIT)
    global_runtime = read_json(GLOBAL_RUNTIME)
    kraken_runtime = read_json(KRAKEN_RUNTIME)
    rows = gauntlet_rows(alpha_map)
    runtime = runtime_summary(global_runtime, kraken_runtime, audit)
    priority = [row for row in rows if row["institutional_tier"] == "priority_paper_replay"]
    institutional_research = [row for row in rows if row["institutional_tier"] == "institutional_research_candidate_paper_only"]
    blocked_live = (
        not runtime["global_allow_live_orders"]
        and not runtime["kraken_allow_live_orders"]
        and runtime["global_mode"] == "paper"
        and runtime["kraken_mode"] == "paper"
    )

    payload = {
        "schema": "kraken_institutional_alpha_gauntlet_v1",
        "generated_utc": now_utc(),
        "status": "INSTITUTIONAL_ALPHA_GAUNTLET_READY_LIVE_BLOCKED" if rows and blocked_live else "INSTITUTIONAL_ALPHA_GAUNTLET_BLOCKED",
        "summary": {
            "gauntlet_row_count": len(rows),
            "priority_paper_replay_count": len(priority),
            "institutional_research_candidate_count": len(institutional_research),
            "large_fund_ready_count": 0,
            "pairs_discovered": int(safe_float(alpha_map.get("pairs_discovered"))),
            "pairs_analyzed": int(safe_float(alpha_map.get("pairs_analyzed"))),
            "paper_control_status": str(paper_control.get("status") or ""),
            "global_runtime_paper": runtime["global_mode"] == "paper",
            "kraken_runtime_paper": runtime["kraken_mode"] == "paper",
            "global_live_orders_disabled": runtime["global_allow_live_orders"] is False,
            "kraken_live_orders_disabled": runtime["kraken_allow_live_orders"] is False,
            "trading_audit_posture": runtime["audit_posture"],
            "trading_audit_blocker_count": len(runtime["audit_blockers"]),
            "trusted_with_large_fund_now": False,
            "order_placement_allowed": False,
            "capital_movement_allowed": False,
            "private_credential_use_allowed_without_human": False,
        },
        "runtime_summary": runtime,
        "gauntlet_rows": rows,
        "institutional_standard": {
            "current_level": "public_market_scan_plus_paper_gauntlet",
            "target_level": "institutional_multi_month_replay_capacity_audit_before_any_live_promotion",
            "promotion_requirements": [
                "multi-month walk-forward replay across regimes",
                "independent data replay receipt",
                "depth and slippage model using live order book snapshots",
                "capacity and participation-rate limits",
                "drawdown, VaR, tail, liquidity, and exchange-outage stress tests",
                "fresh paper-trading heartbeats",
                "zero live-promotion blockers",
                "separate human action-time approval",
                "legal, tax, compliance, and custody review before outside capital",
            ],
        },
        "top_research_candidates": rows[:5],
        "source_artifacts": [
            artifact_status(ALPHA_MAP),
            artifact_status(PAPER_CONTROL),
            artifact_status(TRADING_AUDIT),
            artifact_status(GLOBAL_RUNTIME),
            artifact_status(KRAKEN_RUNTIME),
        ],
        "claim_boundary": [
            "This gauntlet ranks paper research candidates only.",
            "No row is approved for live orders or capital movement.",
            "No row is represented as suitable for a hedge fund without external audit, capacity evidence, and compliance review.",
            "No performance or profit claim is made.",
        ],
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["institutional_alpha_gauntlet_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Kraken Institutional Alpha Gauntlet - 2026-07-09",
        "",
        "Purpose: harden Kraken alpha discovery toward institutional review by scoring signal quality, execution quality, liquidity/capacity, stress survivability, and replay readiness.",
        "",
        "This gauntlet is paper research only. It is not investment advice and does not authorize live trading.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Gauntlet rows: `{summary['gauntlet_row_count']}`",
        f"- Priority paper replay candidates: `{summary['priority_paper_replay_count']}`",
        f"- Institutional research candidates: `{summary['institutional_research_candidate_count']}`",
        f"- Large-fund ready now: `{summary['large_fund_ready_count']}`",
        f"- Pairs discovered: `{summary['pairs_discovered']}`",
        f"- Pairs analyzed: `{summary['pairs_analyzed']}`",
        f"- Paper control status: `{summary['paper_control_status']}`",
        f"- Global runtime paper: `{str(summary['global_runtime_paper']).lower()}`",
        f"- Kraken runtime paper: `{str(summary['kraken_runtime_paper']).lower()}`",
        f"- Global live orders disabled: `{str(summary['global_live_orders_disabled']).lower()}`",
        f"- Kraken live orders disabled: `{str(summary['kraken_live_orders_disabled']).lower()}`",
        f"- Trading audit posture: `{summary['trading_audit_posture']}`",
        f"- Trading audit blockers: `{summary['trading_audit_blocker_count']}`",
        f"- Trusted with large fund now: `{str(summary['trusted_with_large_fund_now']).lower()}`",
        f"- Order placement allowed: `{str(summary['order_placement_allowed']).lower()}`",
        f"- Capital movement allowed: `{str(summary['capital_movement_allowed']).lower()}`",
        f"- Private credential use without human: `{str(summary['private_credential_use_allowed_without_human']).lower()}`",
        f"- Gauntlet SHA-256: `{payload['institutional_alpha_gauntlet_sha256']}`",
        "",
        "## Top Research Candidates",
        "",
    ]
    for row in payload["top_research_candidates"]:
        lines.extend(
            [
                f"### {row['gauntlet_rank']}. {row['wsname'] or row['pair']}",
                "",
                f"- Pair: `{row['pair']}`",
                f"- Strategy mode: `{row['strategy_mode']}`",
                f"- Institutional tier: `{row['institutional_tier']}`",
                f"- Institutional alpha score: `{row['institutional_alpha_score']}`",
                f"- Signal / execution / capacity / stress / replay: `{row['signal_quality_score']}` / `{row['execution_quality_score']}` / `{row['capacity_quality_score']}` / `{row['stress_survivability_score']}` / `{row['replay_readiness_score']}`",
                f"- Capacity tier: `{row['capacity']['capacity_tier']}`",
                f"- Conservative paper notional cap USD: `{row['capacity']['conservative_paper_notional_cap_usd']}`",
                f"- Large-fund capacity proven: `{str(row['capacity']['large_fund_capacity_proven']).lower()}`",
                f"- Promotion fail reasons: `{', '.join(row['promotion_fail_reasons'])}`",
                f"- Allowed next step: `{row['allowed_next_step']}`",
                f"- Live order allowed: `{str(row['live_order_allowed']).lower()}`",
                f"- Row SHA-256: `{row['gauntlet_row_sha256']}`",
                "",
            ]
        )

    standard = payload["institutional_standard"]
    lines.extend(
        [
            "## Institutional Standard",
            "",
            f"- Current level: `{standard['current_level']}`",
            f"- Target level: `{standard['target_level']}`",
            "",
            "Promotion requirements:",
        ]
    )
    for item in standard["promotion_requirements"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Source Artifacts", ""])
    for row in payload["source_artifacts"]:
        lines.append(
            f"- `{row['path']}` present=`{str(row['present']).lower()}` bytes=`{row['bytes']}` sha256=`{row['sha256']}`"
        )

    lines.extend(["", "## Claim Boundary", ""])
    for item in payload["claim_boundary"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> int:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive Kraken gauntlet markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "gauntlet_rows": payload["summary"]["gauntlet_row_count"],
                "priority_paper_replay": payload["summary"]["priority_paper_replay_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0 if payload["status"] == "INSTITUTIONAL_ALPHA_GAUNTLET_READY_LIVE_BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
