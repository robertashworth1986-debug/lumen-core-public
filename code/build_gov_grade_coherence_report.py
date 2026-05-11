from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
OUT_EXEC = ROOT / "out" / "execution"
OUT_SPORTS = ROOT / "out" / "sports_intelligence"
OUT_COHERENCE = ROOT / "out" / "coherence"
DASH_DATA = ROOT / "dashboard" / "data"

OUTPUT_JSON = OUT_EXEC / "gov_grade_coherence_report.json"
OUTPUT_MD = OUT_EXEC / "gov_grade_coherence_report.md"
OUTPUT_HASH = OUT_EXEC / "gov_grade_coherence_report_sha256.json"
OUTPUT_HISTORY = OUT_EXEC / "gov_grade_coherence_report_history.jsonl"
OUTPUT_DASH_JSON = DASH_DATA / "gov_grade_coherence_report.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def pct(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}%"


def dt_from_any(value: Any) -> Optional[datetime]:
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


def age_minutes(ts: Any) -> Optional[float]:
    dt = dt_from_any(ts)
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 60.0


def file_mtime_iso(path: Path) -> Optional[str]:
    try:
        if path.exists():
            return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        return None
    return None


def grade_from_score(score: float) -> str:
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 85:
        return "A-"
    if score >= 80:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 70:
        return "B-"
    if score >= 65:
        return "C+"
    if score >= 60:
        return "C"
    return "D"


def read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def read_csv_rows(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
    except Exception:
        return []
    return rows


def clean_nan(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: clean_nan(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_nan(v) for v in value]
    return value


def is_fresh_minutes(minutes: Optional[float], max_minutes: float) -> bool:
    return minutes is not None and minutes <= max_minutes


def summarize_trading_stack(vps: Dict[str, Any], live_feed: List[Dict[str, Any]], institutional_summary: Dict[str, Any],
                            portfolio_summary: Dict[str, Any], market_status: Dict[str, Any],
                            leaderboard_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    evidence = vps.get("kraken_execution_evidence", {})
    recon = vps.get("kraken_fill_reconciliation", {})
    perf = vps.get("live_trade_performance", {})
    heartbeat = vps.get("runtime_heartbeat", {})
    score = vps.get("integrity_score", {})
    controller = vps.get("growth_controller_status", {})
    guard = controller.get("guard", {})

    fill_sync = safe_float(recon.get("fill_sync_pct"), 0.0)
    integrity = safe_float(score.get("score_0_100"), 0.0)
    queried = safe_int(recon.get("txids_queried"), 0)
    closed = safe_int(recon.get("closed_count"), 0)
    query_enabled = bool(recon.get("query_enabled"))
    mode = str(controller.get("mode") or "UNKNOWN").upper()
    allow_live = bool(guard.get("allow_live"))
    heartbeat_fresh = bool(heartbeat.get("fresh"))

    top_live = sorted(
        [row for row in live_feed if isinstance(row, dict)],
        key=lambda x: (
            safe_float(x.get("sharpe"), -9999.0),
            safe_float(x.get("cagr"), -9999.0),
            safe_float(x.get("win_rate"), -9999.0),
        ),
        reverse=True,
    )[:5]

    top_live_opportunities: List[Dict[str, Any]] = []
    for row in top_live:
        sharpe = safe_float(row.get("sharpe"), 0.0)
        cagr = safe_float(row.get("cagr"), 0.0)
        win_rate = safe_float(row.get("win_rate"), 0.0)
        impact = clamp((sharpe * 10.0) + (cagr * 1.8) + (win_rate * 40.0), 0.0, 100.0)
        top_live_opportunities.append(
            {
                "symbol": str(row.get("symbol") or ""),
                "family": str(row.get("family") or ""),
                "sharpe": round(sharpe, 4),
                "cagr_pct": round(cagr, 4),
                "win_rate_pct": round(win_rate * 100.0, 4),
                "impact_score": round(impact, 2),
            }
        )

    institutional_best = {
        "flow": institutional_summary.get("flow"),
        "strategy": institutional_summary.get("strategy"),
        "algo": institutional_summary.get("algo"),
        "institutional_score": round(safe_float(institutional_summary.get("institutional_score"), 0.0), 4),
        "test_sharpe": round(safe_float(institutional_summary.get("test_sharpe"), 0.0), 4),
        "wf_sharpe_mean": round(safe_float(institutional_summary.get("wf_sharpe_mean"), 0.0), 4),
        "wf_stability": round(safe_float(institutional_summary.get("wf_stability"), 0.0), 4),
    }

    leaderboard_best: Dict[str, Any] = {}
    if leaderboard_rows:
        best = leaderboard_rows[0]
        leaderboard_best = {
            "flow": best.get("flow"),
            "strategy": best.get("strategy"),
            "algo": best.get("algo"),
            "institutional_score": round(safe_float(best.get("institutional_score"), 0.0), 4),
            "test_sharpe": round(safe_float(best.get("test_sharpe"), 0.0), 4),
            "test_vs_baseline": round(safe_float(best.get("test_vs_baseline"), 0.0), 6),
        }

    if safe_float(institutional_best.get("institutional_score"), 0.0) <= 0.0 and leaderboard_best:
        institutional_best = {
            "flow": leaderboard_best.get("flow"),
            "strategy": leaderboard_best.get("strategy"),
            "algo": leaderboard_best.get("algo"),
            "institutional_score": safe_float(leaderboard_best.get("institutional_score"), 0.0),
            "test_sharpe": safe_float(leaderboard_best.get("test_sharpe"), 0.0),
            "wf_sharpe_mean": round(safe_float(best.get("wf_sharpe_mean"), 0.0), 4),
            "wf_stability": round(safe_float(best.get("wf_stability"), 0.0), 4),
        }

    warnings: List[str] = []
    if not query_enabled:
        warnings.append("kraken_reconciliation_disabled")
    if query_enabled and queried > 0 and closed < queried:
        warnings.append("unclosed_exchange_orders_present")
    if not heartbeat_fresh:
        warnings.append("runtime_heartbeat_stale")
    if not allow_live:
        warnings.append("controller_safe_mode_active")
    if str(market_status.get("status") or "").lower() != "online":
        warnings.append("market_stream_not_online")

    quality_signal = 0.0
    if top_live_opportunities:
        quality_signal = sum(safe_float(x.get("impact_score"), 0.0) for x in top_live_opportunities) / len(top_live_opportunities)

    institutional_score_component = clamp(safe_float(institutional_best.get("institutional_score"), 0.0) * 4.0, 0.0, 100.0)
    truth_component = clamp(integrity * 0.55 + (fill_sync if query_enabled else 20.0) * 0.45, 0.0, 100.0)
    readiness_component = 100.0
    if not allow_live:
        readiness_component -= 35.0
    if not heartbeat_fresh:
        readiness_component -= 25.0
    if str(market_status.get("status") or "").lower() != "online":
        readiness_component -= 20.0
    readiness_component = clamp(readiness_component, 0.0, 100.0)

    trading_stack_score = round(
        (truth_component * 0.45)
        + (quality_signal * 0.25)
        + (institutional_score_component * 0.20)
        + (readiness_component * 0.10),
        2,
    )

    status = "READY" if allow_live and heartbeat_fresh and query_enabled else "SAFE"
    if warnings:
        status = "REVIEW"

    return {
        "score_0_100": trading_stack_score,
        "grade": grade_from_score(trading_stack_score),
        "status": status,
        "mode": mode,
        "allow_live": allow_live,
        "integrity_score_0_100": round(integrity, 2),
        "fill_sync_pct": round(fill_sync, 2),
        "query_enabled": query_enabled,
        "exchange_closed": {
            "closed_count": closed,
            "queried_count": queried,
            "ratio": f"{closed}/{queried}",
        },
        "txid_count": safe_int(evidence.get("txid_count"), 0),
        "submit_live_7d": safe_int(evidence.get("recent_7d_live_submit"), 0),
        "realized_net_usd": round(safe_float(perf.get("realized_net_usd"), 0.0), 6),
        "portfolio_equity_usd": round(safe_float(portfolio_summary.get("current_equity"), safe_float(vps.get("capital_state", {}).get("portfolio_est_total_usd"), 0.0)), 6),
        "market_stream_status": str(market_status.get("status") or "unknown"),
        "market_stream_error": market_status.get("error"),
        "top_live_opportunities": top_live_opportunities,
        "institutional_best": institutional_best,
        "institutional_leaderboard_best": leaderboard_best,
        "warnings": warnings,
        "components": {
            "truth_component": round(truth_component, 2),
            "signal_quality_component": round(quality_signal, 2),
            "institutional_component": round(institutional_score_component, 2),
            "readiness_component": round(readiness_component, 2),
        },
    }


def classify_sports_freshness(commence_time: Any) -> Tuple[bool, Optional[float], str]:
    dt = dt_from_any(commence_time)
    if dt is None:
        return False, None, "unknown"
    delta_h = (dt - datetime.now(timezone.utc)).total_seconds() / 3600.0
    if delta_h < 0:
        return False, delta_h, "expired"
    if delta_h <= 72.0:
        return True, delta_h, "active_72h"
    return True, delta_h, "future"


def summarize_sports_stack(ev_ranked: Dict[str, Any], alpha_board: Dict[str, Any], longshot_board: Dict[str, Any],
                           flowform_ranked: Dict[str, Any], market_efficiency: Dict[str, Any],
                           steam_alerts: Dict[str, Any]) -> Dict[str, Any]:
    ev_signals = [s for s in ev_ranked.get("signals", []) if isinstance(s, dict)]
    board_rows = [r for r in alpha_board.get("rows", []) if isinstance(r, dict)]
    longshot_rows = [r for r in longshot_board.get("rows", []) if isinstance(r, dict)]
    flowform_signals = [s for s in flowform_ranked.get("signals", []) if isinstance(s, dict)]

    fresh_rows: List[Dict[str, Any]] = []
    stale_rows: List[Dict[str, Any]] = []
    for row in board_rows:
        fresh, hours_to_start, freshness = classify_sports_freshness(row.get("commence_time"))
        row2 = dict(row)
        row2["hours_to_start"] = round(hours_to_start, 3) if hours_to_start is not None else None
        row2["freshness"] = freshness
        if fresh and (hours_to_start is None or hours_to_start >= 0):
            fresh_rows.append(row2)
        else:
            stale_rows.append(row2)

    top_board = sorted(
        board_rows,
        key=lambda x: (
            safe_float(x.get("alpha_score_v2"), 0.0),
            safe_float(x.get("edge_pct"), 0.0),
            safe_float(x.get("ml_edge_score"), 0.0),
        ),
        reverse=True,
    )[:8]

    top_picks: List[Dict[str, Any]] = []
    for row in top_board:
        fresh, hours_to_start, freshness = classify_sports_freshness(row.get("commence_time"))
        impact = clamp(
            safe_float(row.get("alpha_score_v2"), 0.0) * 1.1
            + safe_float(row.get("edge_pct"), 0.0) * 2.0
            + safe_float(row.get("ml_edge_score"), 0.0) * 1.4,
            0.0,
            100.0,
        )
        top_picks.append(
            {
                "game": str(row.get("game") or ""),
                "pick": str(row.get("pick") or ""),
                "market": str(row.get("market") or ""),
                "sport_key": str(row.get("sport_key") or ""),
                "edge_pct": round(safe_float(row.get("edge_pct"), 0.0), 4),
                "alpha_score_v2": round(safe_float(row.get("alpha_score_v2"), 0.0), 4),
                "ml_edge_score": round(safe_float(row.get("ml_edge_score"), 0.0), 4),
                "dk_price_decimal": round(safe_float(row.get("dk_price_decimal"), 0.0), 4),
                "hours_to_start": round(hours_to_start, 3) if hours_to_start is not None else None,
                "freshness": freshness,
                "is_live_window": bool(fresh and hours_to_start is not None and hours_to_start <= 72.0),
                "impact_score": round(impact, 2),
            }
        )

    top_picks.sort(
        key=lambda x: (
            1 if str(x.get("freshness")) == "active_72h" else (0 if str(x.get("freshness")) == "future" else -1),
            safe_float(x.get("impact_score"), 0.0),
        ),
        reverse=True,
    )

    prime_markets = [m for m in market_efficiency.get("prime_markets", []) if isinstance(m, dict)]
    high_value_markets = [m for m in market_efficiency.get("high_value_markets", []) if isinstance(m, dict)]
    focus_markets = (prime_markets + high_value_markets)[:5]

    sharp_alert_count = safe_int(steam_alerts.get("count"), 0)
    flowform_count = safe_int(flowform_ranked.get("count"), len(flowform_signals))
    ev_count = safe_int(ev_ranked.get("count"), len(ev_signals))

    fresh_top_impact = max(
        (
            safe_float(x.get("impact_score"), 0.0)
            for x in top_picks
            if str(x.get("freshness")) in {"active_72h", "future"}
        ),
        default=0.0,
    )

    sports_quality = clamp(
        min(40.0, ev_count * 4.0)
        + min(20.0, len(fresh_rows) * 2.5)
        + min(20.0, flowform_count * 0.5)
        + min(20.0, fresh_top_impact * 0.2),
        0.0,
        100.0,
    )

    if not fresh_rows:
        sports_quality = clamp(sports_quality - 12.0, 0.0, 100.0)

    warnings: List[str] = []
    if not board_rows:
        warnings.append("alpha_board_missing")
    if board_rows and not fresh_rows:
        warnings.append("no_fresh_sports_windows")
    if sharp_alert_count == 0:
        warnings.append("no_active_steam_alerts")

    status = "ACTIVE"
    if warnings:
        status = "REVIEW"

    return {
        "score_0_100": round(sports_quality, 2),
        "grade": grade_from_score(sports_quality),
        "status": status,
        "counts": {
            "ev_ranked": ev_count,
            "alpha_board": len(board_rows),
            "longshot_board": len(longshot_rows),
            "flowform_ranked": flowform_count,
            "fresh_72h": len([r for r in fresh_rows if r.get("hours_to_start") is not None and r.get("hours_to_start") <= 72.0]),
            "future_total": len(fresh_rows),
            "expired_total": len(stale_rows),
            "steam_alerts": sharp_alert_count,
        },
        "top_picks": top_picks,
        "market_focus": [
            {
                "sport_key": str(m.get("sport_key") or ""),
                "sport_title": str(m.get("sport_title") or ""),
                "recommendation": str(m.get("recommendation") or ""),
                "efficiency_score": round(safe_float(m.get("efficiency_score"), 0.0), 4),
                "avg_edge_pct": round(safe_float(m.get("avg_edge_pct"), 0.0), 4),
                "signals_per_event": round(safe_float(m.get("signals_per_event"), 0.0), 4),
            }
            for m in focus_markets
        ],
        "warnings": warnings,
    }


def build_cross_domain_alpha(trading: Dict[str, Any], sports: Dict[str, Any]) -> List[Dict[str, Any]]:
    picks: List[Dict[str, Any]] = []

    for row in trading.get("top_live_opportunities", [])[:5]:
        picks.append(
            {
                "domain": "trading",
                "label": f"{row.get('symbol', '')} · {row.get('family', '')}",
                "impact_score": round(safe_float(row.get("impact_score"), 0.0), 2),
                "edge_proxy": {
                    "sharpe": safe_float(row.get("sharpe"), 0.0),
                    "cagr_pct": safe_float(row.get("cagr_pct"), 0.0),
                    "win_rate_pct": safe_float(row.get("win_rate_pct"), 0.0),
                },
                "execution_readiness": trading.get("status"),
                "notes": "Derived from live opportunity feed + institutional weighting.",
            }
        )

    for row in sports.get("top_picks", [])[:5]:
        readiness = str(row.get("freshness") or "unknown")
        raw_impact = safe_float(row.get("impact_score"), 0.0)
        impact = raw_impact
        if readiness == "expired":
            impact = raw_impact * 0.3
        picks.append(
            {
                "domain": "sports",
                "label": f"{row.get('pick', '')} · {row.get('game', '')}",
                "impact_score": round(impact, 2),
                "edge_proxy": {
                    "edge_pct": safe_float(row.get("edge_pct"), 0.0),
                    "alpha_score_v2": safe_float(row.get("alpha_score_v2"), 0.0),
                    "ml_edge_score": safe_float(row.get("ml_edge_score"), 0.0),
                },
                "execution_readiness": readiness,
                "notes": "Derived from DraftKings alpha board + flowform context.",
            }
        )

    picks.sort(key=lambda x: safe_float(x.get("impact_score"), 0.0), reverse=True)
    return picks[:10]


def summarize_source_health(source_timestamps: Dict[str, Any]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    freshness_points = 0.0

    for name, value in source_timestamps.items():
        mins = age_minutes(value)
        rows.append({
            "source": name,
            "timestamp_utc": value,
            "age_minutes": round(mins, 2) if mins is not None else None,
            "fresh": bool(is_fresh_minutes(mins, 180.0)),
        })
        if mins is None:
            continue
        freshness_points += clamp(100.0 - (mins / 6.0), 0.0, 100.0)

    score = freshness_points / max(1, len(source_timestamps))
    return {
        "score_0_100": round(score, 2),
        "grade": grade_from_score(score),
        "sources": rows,
    }


def compute_coherence_score(trading: Dict[str, Any], sports: Dict[str, Any], source_health: Dict[str, Any],
                            fleet_coherence: Dict[str, Any]) -> Dict[str, Any]:
    trading_score = safe_float(trading.get("score_0_100"), 0.0)
    sports_score = safe_float(sports.get("score_0_100"), 0.0)
    freshness_score = safe_float(source_health.get("score_0_100"), 0.0)

    fleet_grade = str(fleet_coherence.get("overall_grade") or "").upper()
    fleet_pass = bool(fleet_coherence.get("overall_pass"))
    fleet_signal = 85.0 if fleet_pass else 48.0
    if fleet_grade == "PASS":
        fleet_signal = 90.0
    if fleet_grade == "WARN":
        fleet_signal = 65.0
    if fleet_grade == "FAIL":
        fleet_signal = 42.0

    raw = (
        trading_score * 0.42
        + sports_score * 0.24
        + freshness_score * 0.19
        + fleet_signal * 0.15
    )
    overall = round(clamp(raw, 0.0, 100.0), 2)

    warnings: List[str] = []
    for w in trading.get("warnings", []):
        warnings.append(f"trading:{w}")
    for w in sports.get("warnings", []):
        warnings.append(f"sports:{w}")
    if not fleet_pass:
        warnings.append("coherence:fleet_monitor_not_passing")

    return {
        "score_0_100": overall,
        "grade": grade_from_score(overall),
        "components": {
            "trading_stack": round(trading_score, 2),
            "sports_stack": round(sports_score, 2),
            "source_freshness": round(freshness_score, 2),
            "fleet_coherence_signal": round(fleet_signal, 2),
        },
        "warnings": warnings,
    }


def build_action_rail(report: Dict[str, Any]) -> Dict[str, List[str]]:
    trading = report.get("trading_stack", {})
    sports = report.get("sports_stack", {})
    coherence = report.get("coherence_score", {})

    immediate: List[str] = []
    next_24h: List[str] = []

    if bool(trading.get("query_enabled")):
        immediate.append(
            f"Keep Kraken reconciliation active: {trading.get('exchange_closed', {}).get('ratio', '0/0')} closed with {pct(safe_float(trading.get('fill_sync_pct'), 0.0), 1)} fill sync."
        )
    else:
        immediate.append("Re-enable Kraken QueryOrders reconciliation before taking new live risk.")

    top_trade = (trading.get("top_live_opportunities") or [{}])[0]
    if top_trade and top_trade.get("symbol"):
        immediate.append(
            f"Primary live symbol focus: {top_trade.get('symbol')} via {top_trade.get('family')} (impact {safe_float(top_trade.get('impact_score'), 0.0):.1f})."
        )

    top_pick = (sports.get("top_picks") or [{}])[0]
    if top_pick and top_pick.get("pick"):
        next_24h.append(
            f"Top sports alpha: {top_pick.get('pick')} in {top_pick.get('game')} (edge {pct(safe_float(top_pick.get('edge_pct'), 0.0), 2)}, impact {safe_float(top_pick.get('impact_score'), 0.0):.1f})."
        )

    if safe_float(coherence.get("score_0_100"), 0.0) < 75.0:
        next_24h.append("Raise coherence above 75 by clearing trading/sports warning flags before expanding risk.")
    else:
        next_24h.append("Coherence is in deployable range; keep evidence-chain refresh cadence at <=15 minutes.")

    if not next_24h:
        next_24h.append("Monitor source freshness and refresh stale intelligence feeds.")

    return {"immediate": immediate, "next_24h": next_24h}


def render_markdown(report: Dict[str, Any]) -> str:
    trading = report.get("trading_stack", {})
    sports = report.get("sports_stack", {})
    coherence = report.get("coherence_score", {})
    source_health = report.get("source_health", {})
    cross = report.get("cross_domain_alpha", [])

    lines: List[str] = []
    lines.append("# Gov-Grade Max Coherence Report")
    lines.append("")
    lines.append(f"Generated UTC: {report.get('generated_utc', 'n/a')}")
    lines.append("")
    lines.append("## Coherence Score")
    lines.append(f"- Score (0-100): {safe_float(coherence.get('score_0_100'), 0.0):.2f}")
    lines.append(f"- Grade: {coherence.get('grade', 'n/a')}")
    lines.append(f"- Trading: {safe_float(coherence.get('components', {}).get('trading_stack'), 0.0):.2f}")
    lines.append(f"- Sports: {safe_float(coherence.get('components', {}).get('sports_stack'), 0.0):.2f}")
    lines.append(f"- Source Freshness: {safe_float(coherence.get('components', {}).get('source_freshness'), 0.0):.2f}")
    lines.append("")
    lines.append("## Trading Stack")
    lines.append(f"- Status: {trading.get('status', 'n/a')} | Mode: {trading.get('mode', 'n/a')} | Allow live: {trading.get('allow_live', False)}")
    lines.append(f"- Integrity score: {safe_float(trading.get('integrity_score_0_100'), 0.0):.2f}")
    lines.append(f"- Fill sync: {pct(safe_float(trading.get('fill_sync_pct'), 0.0), 1)}")
    lines.append(f"- Exchange closed: {trading.get('exchange_closed', {}).get('ratio', '0/0')}")
    lines.append(f"- Top symbol: {(trading.get('top_live_opportunities') or [{}])[0].get('symbol', 'n/a')}")
    lines.append("")
    lines.append("## Sports Stack")
    lines.append(f"- Status: {sports.get('status', 'n/a')}")
    lines.append(f"- Fresh windows (72h): {safe_int(sports.get('counts', {}).get('fresh_72h'), 0)}")
    lines.append(f"- EV ranked count: {safe_int(sports.get('counts', {}).get('ev_ranked'), 0)}")
    lines.append(f"- Top pick: {(sports.get('top_picks') or [{}])[0].get('pick', 'n/a')}")
    lines.append("")
    lines.append("## Cross-Domain Alpha Top 6")
    for row in cross[:6]:
        lines.append(
            f"- [{row.get('domain', 'unknown')}] {row.get('label', '')} | impact {safe_float(row.get('impact_score'), 0.0):.2f} | readiness {row.get('execution_readiness', 'n/a')}"
        )
    lines.append("")
    lines.append("## Source Freshness")
    lines.append(f"- Score (0-100): {safe_float(source_health.get('score_0_100'), 0.0):.2f}")
    for src in source_health.get("sources", [])[:8]:
        age = src.get("age_minutes")
        age_text = "n/a" if age is None else f"{safe_float(age, 0.0):.1f}m"
        lines.append(f"- {src.get('source', 'source')}: {age_text}")
    lines.append("")
    lines.append("## Guardrail")
    lines.append("- This report is evidence and prioritization telemetry only, not a guarantee of returns.")

    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_nan(payload), indent=2, sort_keys=False), encoding="utf-8")


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(clean_nan(payload), sort_keys=False) + "\n")


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    generated = now_utc()

    vps = read_json(OUT_EXEC / "vps_growth_proof.json", {})
    live_feed = read_json(OUT_EXEC / "live_opportunity_feed.json", [])
    institutional_summary = read_json(OUT_EXEC / "institutional_summary.json", {})
    portfolio_summary = read_json(OUT_EXEC / "portfolio_summary.json", {})
    market_status = read_json(OUT_EXEC / "live_market_stream_status.json", {})
    leaderboard_rows = read_csv_rows(OUT_EXEC / "institutional_leaderboard.csv")

    ev_ranked = read_json(OUT_SPORTS / "_ev_ranked.json", {})
    alpha_board = read_json(OUT_SPORTS / "_dk_alpha_board.json", {})
    longshot_board = read_json(OUT_SPORTS / "_dk_longshot_board.json", {})
    flowform_ranked = read_json(OUT_SPORTS / "_flowform_ranked.json", {})
    market_efficiency = read_json(OUT_SPORTS / "_market_efficiency.json", {})
    steam_alerts = read_json(OUT_SPORTS / "_steam_alerts.json", {})

    fleet_coherence = read_json(OUT_COHERENCE / "fleet_coherence_latest.json", {})

    trading = summarize_trading_stack(
        vps=vps,
        live_feed=live_feed if isinstance(live_feed, list) else [],
        institutional_summary=institutional_summary if isinstance(institutional_summary, dict) else {},
        portfolio_summary=portfolio_summary if isinstance(portfolio_summary, dict) else {},
        market_status=market_status if isinstance(market_status, dict) else {},
        leaderboard_rows=leaderboard_rows,
    )

    sports = summarize_sports_stack(
        ev_ranked=ev_ranked if isinstance(ev_ranked, dict) else {},
        alpha_board=alpha_board if isinstance(alpha_board, dict) else {},
        longshot_board=longshot_board if isinstance(longshot_board, dict) else {},
        flowform_ranked=flowform_ranked if isinstance(flowform_ranked, dict) else {},
        market_efficiency=market_efficiency if isinstance(market_efficiency, dict) else {},
        steam_alerts=steam_alerts if isinstance(steam_alerts, dict) else {},
    )

    source_ts = {
        "vps_growth_proof": vps.get("generated_utc"),
        "live_opportunity_feed": file_mtime_iso(OUT_EXEC / "live_opportunity_feed.json"),
        "institutional_summary": institutional_summary.get("generated_utc"),
        "sports_ev_ranked": ev_ranked.get("generated_utc"),
        "sports_alpha_board": alpha_board.get("generated_utc"),
        "sports_flowform": flowform_ranked.get("generated_utc"),
        "sports_steam_alerts": steam_alerts.get("generated_utc"),
        "fleet_coherence": fleet_coherence.get("ts") or fleet_coherence.get("generated_utc"),
    }
    source_health = summarize_source_health(source_ts)

    coherence_score = compute_coherence_score(
        trading=trading,
        sports=sports,
        source_health=source_health,
        fleet_coherence=fleet_coherence if isinstance(fleet_coherence, dict) else {},
    )

    cross_domain = build_cross_domain_alpha(trading=trading, sports=sports)

    report: Dict[str, Any] = {
        "generated_utc": generated,
        "schema": "gov_grade_coherence_report_v1",
        "objective": "Max-coherence cross-domain alpha report fusing exchange-verified trading truth with high-impact sports intelligence.",
        "coherence_score": coherence_score,
        "trading_stack": trading,
        "sports_stack": sports,
        "cross_domain_alpha": cross_domain,
        "source_health": source_health,
        "fleet_coherence_latest": {
            "overall_grade": fleet_coherence.get("overall_grade"),
            "overall_pass": bool(fleet_coherence.get("overall_pass")),
            "omega": safe_float(fleet_coherence.get("omega"), 0.0),
            "active_spikes": safe_int(fleet_coherence.get("active_spikes"), 0),
            "real_spikes": safe_int(fleet_coherence.get("real_spikes"), 0),
            "freshness_sec": safe_float(fleet_coherence.get("freshness_sec"), 0.0),
        },
        "action_rail": {},
        "guardrail": "Evidence and prioritization telemetry only. Keep risk caps and controller gates active.",
    }
    report["action_rail"] = build_action_rail(report)

    write_json(OUTPUT_JSON, report)
    write_json(OUTPUT_DASH_JSON, report)

    md = render_markdown(report)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(md, encoding="utf-8")

    digest = {
        "generated_utc": generated,
        "schema": "gov_grade_coherence_report_hash_v1",
        "sha256": {
            str(OUTPUT_JSON): sha256_of_file(OUTPUT_JSON),
            str(OUTPUT_MD): sha256_of_file(OUTPUT_MD),
            str(OUTPUT_DASH_JSON): sha256_of_file(OUTPUT_DASH_JSON),
        },
    }
    write_json(OUTPUT_HASH, digest)

    append_jsonl(
        OUTPUT_HISTORY,
        {
            "generated_utc": generated,
            "coherence_score": report.get("coherence_score", {}).get("score_0_100"),
            "coherence_grade": report.get("coherence_score", {}).get("grade"),
            "trading_score": report.get("trading_stack", {}).get("score_0_100"),
            "sports_score": report.get("sports_stack", {}).get("score_0_100"),
            "cross_domain_top": (report.get("cross_domain_alpha") or [{}])[0],
        },
    )

    print(str(OUTPUT_JSON))
    print(str(OUTPUT_MD))
    print(str(OUTPUT_HASH))
    print(str(OUTPUT_HISTORY))
    print(str(OUTPUT_DASH_JSON))


if __name__ == "__main__":
    main()
