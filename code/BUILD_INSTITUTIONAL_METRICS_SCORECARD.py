from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC = OUT / "execution"
CONF = ROOT / "config"

DAILY_REPORT = OUT / "institutional_daily_report.json"
INVESTOR_PERF = EXEC / "investor_performance_report.json"
CHAMPION_LINEAGES = EXEC / "institutional_champion_lineages.json"
SEED_VALIDATION = OUT / "seed_validation_readout.json"
REGISTRY = CONF / "live_source_registry.json"
OPPORTUNITY_BRIEF = EXEC / "institutional_opportunity_executive_brief.json"
SOURCE_BREADTH = OUT / "approved_source_breadth_registry.json"
EDGE_TRUTH = EXEC / "edge_truth_report.json"

SCORECARD_JSON = EXEC / "institutional_metrics_scorecard.json"
SCORECARD_MD = EXEC / "institutional_metrics_scorecard.md"
KPI_SUMMARY_JSON = EXEC / "kpi_summary.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def registry_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("rows")
    if isinstance(rows, list):
        return [r for r in rows if isinstance(r, dict)]
    sources = payload.get("sources")
    if isinstance(sources, list):
        return [r for r in sources if isinstance(r, dict)]
    return []


def build_scorecard() -> dict[str, Any]:
    daily = load_json(DAILY_REPORT, {})
    perf = load_json(INVESTOR_PERF, {})
    lineages = load_json(CHAMPION_LINEAGES, {})
    seed = load_json(SEED_VALIDATION, {})
    registry = load_json(REGISTRY, {})
    opp = load_json(OPPORTUNITY_BRIEF, {})
    breadth = load_json(SOURCE_BREADTH, {})
    edge = load_json(EDGE_TRUTH, {})

    account = daily.get("account", {}) if isinstance(daily, dict) else {}
    risk = daily.get("risk", {}) if isinstance(daily, dict) else {}
    daily_perf = daily.get("performance", {}) if isinstance(daily, dict) else {}

    rows = registry_rows(registry)
    enabled_rows = [r for r in rows if bool(r.get("enabled", False))]
    measured_rows = [
        r
        for r in rows
        if str(r.get("dollar_basis", "")).upper() == "MEASURED"
        or str(r.get("evidence_basis", "")).upper() == "MEASURED_FILE_MATCH"
        or as_int(r.get("rows"), 0) > 0
    ]

    top_lineages = lineages.get("top_lineages", []) if isinstance(lineages, dict) else []
    best_lineage = top_lineages[0] if isinstance(top_lineages, list) and top_lineages else {}

    realized_roi_pct = as_float(account.get("return_total_pct"), 0.0)
    win_rate_pct = as_float(daily_perf.get("win_rate_pct"), as_float(perf.get("win_rate_pct"), 0.0))
    sharpe_proxy = as_float(daily_perf.get("annualized_sharpe_proxy"), as_float(perf.get("sharpe"), 0.0))
    max_drawdown_pct = as_float(risk.get("max_drawdown_pct"), abs(as_float(perf.get("max_drawdown"), 0.0)) * 100.0)

    walkforward_sharpe = as_float(best_lineage.get("wf_sharpe_mean"), 0.0)
    walkforward_stability = as_float(best_lineage.get("wf_stability"), 0.0)
    test_sharpe = as_float(best_lineage.get("test_sharpe"), as_float(seed.get("champion", {}).get("test_sharpe"), 0.0))
    institutional_score = as_float(best_lineage.get("institutional_score"), as_float(seed.get("champion", {}).get("institutional_score"), 0.0))

    measured_hour = as_float(opp.get("measured_total_hour_usd"), 0.0)
    rolling_hour = as_float(opp.get("rolling_total_hour_usd"), 0.0)
    lane_alerts = opp.get("lane_alerts", {}) if isinstance(opp, dict) else {}
    critical_alerts = as_int(lane_alerts.get("critical_count"), 0) if isinstance(lane_alerts, dict) else 0
    key_backed = as_int(breadth.get("key_backed_enabled_sources"), len(enabled_rows)) if isinstance(breadth, dict) else len(enabled_rows)
    open_access = as_int(breadth.get("open_access_approved_sources"), 0) if isinstance(breadth, dict) else 0
    combined_sources = as_int(breadth.get("combined_approved_sources"), key_backed + open_access) if isinstance(breadth, dict) else key_backed + open_access
    breadth_target = 60.0
    edge_quality_score = as_float(edge.get("edge_quality_score"), 0.0) if isinstance(edge, dict) else 0.0
    edge_verdict = str(edge.get("verdict", "UNKNOWN")).upper() if isinstance(edge, dict) else "UNKNOWN"

    score_components = {
        "coverage": min(100.0, (len(enabled_rows) / max(len(rows), 1)) * 100.0),
        "measurement": min(100.0, (len(measured_rows) / max(len(rows), 1)) * 100.0),
        "walkforward": max(0.0, min(100.0, walkforward_sharpe * 20.0)),
        "risk": max(0.0, 100.0 - min(100.0, max_drawdown_pct * 2.5)),
        "ops": max(0.0, 100.0 - min(100.0, critical_alerts * 20.0)),
        "realized_roi": max(0.0, min(100.0, 50.0 + (realized_roi_pct * 2.0))),
        "win_rate": max(0.0, min(100.0, win_rate_pct)),
        "breadth": max(0.0, min(100.0, (combined_sources / breadth_target) * 100.0)),
        "edge_truth": max(0.0, min(100.0, edge_quality_score)),
    }
    readiness_score = round(sum(score_components.values()) / len(score_components), 2)

    readiness_tier = "RED"
    if (
        readiness_score >= 75.0
        and measured_hour > 0.0
        and test_sharpe > 1.0
        and max_drawdown_pct <= 25.0
        and realized_roi_pct > 0.0
        and win_rate_pct >= 45.0
        and edge_verdict != "FAIL"
    ):
        readiness_tier = "GREEN"
    elif readiness_score >= 55.0 and measured_hour > 0.0 and (realized_roi_pct > -10.0):
        readiness_tier = "YELLOW"

    gaps: list[str] = []
    if realized_roi_pct <= 0.0:
        gaps.append("Realized ROI is non-positive; continue accumulating validated trade sample.")
    if win_rate_pct <= 45.0:
        gaps.append("Win rate is below institutional comfort band (45%+).")
    if max_drawdown_pct > 20.0:
        gaps.append("Max drawdown exceeds 20%; tighten risk controls before live capital scaling.")
    if walkforward_stability < 0.35:
        gaps.append("Walk-forward stability is weak; favor more robust champion blends.")
    if critical_alerts > 0:
        gaps.append("Critical lane alerts are active; stabilize measured feeds before investor broadcast.")
    if edge_verdict == "FAIL":
        gaps.append("Edge truth guard is FAIL; champion likely overfit or insufficiently robust versus baseline.")

    return {
        "generated_utc": now_utc(),
        "readiness_tier": readiness_tier,
        "readiness_score": readiness_score,
        "score_components": score_components,
        "trading_kpis": {
            "equity_usd": as_float(account.get("equity_usd"), 0.0),
            "pnl_total_usd": as_float(account.get("pnl_total_usd"), 0.0),
            "realized_roi_pct": realized_roi_pct,
            "win_rate_pct": win_rate_pct,
            "annualized_sharpe_proxy": sharpe_proxy,
            "max_drawdown_pct": max_drawdown_pct,
        },
        "research_kpis": {
            "top_test_sharpe": test_sharpe,
            "top_walkforward_sharpe_mean": walkforward_sharpe,
            "top_walkforward_stability": walkforward_stability,
            "top_institutional_score": institutional_score,
            "edge_truth_score": edge_quality_score,
            "edge_truth_verdict": edge_verdict,
            "champion_flow": str(best_lineage.get("flow", seed.get("champion", {}).get("flow", "unknown"))),
            "champion_strategy": str(best_lineage.get("strategy", seed.get("champion", {}).get("strategy", "unknown"))),
            "champion_algo": str(best_lineage.get("algo", seed.get("champion", {}).get("algo", "unknown"))),
        },
        "source_coverage": {
            "registry_total": len(rows),
            "enabled_sources": len(enabled_rows),
            "measured_sources": len(measured_rows),
            "coverage_pct": round((len(enabled_rows) / max(len(rows), 1)) * 100.0, 2),
            "measurement_pct": round((len(measured_rows) / max(len(rows), 1)) * 100.0, 2),
            "open_access_approved_sources": open_access,
            "combined_approved_sources": combined_sources,
        },
        "opportunity_kpis": {
            "rolling_total_hour_usd": rolling_hour,
            "measured_total_hour_usd": measured_hour,
            "critical_lane_alerts": critical_alerts,
            "warning_lane_alerts": as_int(lane_alerts.get("warning_count"), 0) if isinstance(lane_alerts, dict) else 0,
            "top_sector": str(opp.get("top_sector", "n/a")),
            "sector_count": as_int(opp.get("sectors"), 0),
        },
        "gaps": gaps,
        "artifact_sources": {
            "daily_report": str(DAILY_REPORT),
            "investor_performance": str(INVESTOR_PERF),
            "champion_lineages": str(CHAMPION_LINEAGES),
            "seed_validation": str(SEED_VALIDATION),
            "source_registry": str(REGISTRY),
            "opportunity_brief": str(OPPORTUNITY_BRIEF),
            "approved_source_breadth": str(SOURCE_BREADTH),
            "edge_truth_report": str(EDGE_TRUTH),
        },
    }


def render_markdown(scorecard: dict[str, Any]) -> str:
    t = scorecard.get("trading_kpis", {})
    r = scorecard.get("research_kpis", {})
    s = scorecard.get("source_coverage", {})
    o = scorecard.get("opportunity_kpis", {})
    gaps = scorecard.get("gaps", [])

    lines = [
        "# Institutional Metrics Scorecard",
        "",
        f"Generated UTC: {scorecard.get('generated_utc', 'n/a')}",
        f"Readiness Tier: {scorecard.get('readiness_tier', 'n/a')} | Score: {scorecard.get('readiness_score', 0)}",
        "",
        "## Trading KPIs",
        f"- Equity USD: {as_float(t.get('equity_usd')):,.2f}",
        f"- PnL USD: {as_float(t.get('pnl_total_usd')):,.2f}",
        f"- Realized ROI %: {as_float(t.get('realized_roi_pct')):.4f}",
        f"- Win Rate %: {as_float(t.get('win_rate_pct')):.2f}",
        f"- Annualized Sharpe Proxy: {as_float(t.get('annualized_sharpe_proxy')):.4f}",
        f"- Max Drawdown %: {as_float(t.get('max_drawdown_pct')):.2f}",
        "",
        "## Research KPIs",
        f"- Top Test Sharpe: {as_float(r.get('top_test_sharpe')):.4f}",
        f"- Walk-Forward Sharpe Mean: {as_float(r.get('top_walkforward_sharpe_mean')):.4f}",
        f"- Walk-Forward Stability: {as_float(r.get('top_walkforward_stability')):.4f}",
        f"- Top Institutional Score: {as_float(r.get('top_institutional_score')):.4f}",
        f"- Edge Truth Score: {as_float(r.get('edge_truth_score')):.2f}",
        f"- Edge Truth Verdict: {r.get('edge_truth_verdict', 'UNKNOWN')}",
        f"- Champion: {r.get('champion_flow', 'unknown')} / {r.get('champion_strategy', 'unknown')} / {r.get('champion_algo', 'unknown')}",
        "",
        "## Coverage KPIs",
        f"- Registry Sources: {as_int(s.get('registry_total'))}",
        f"- Enabled Sources: {as_int(s.get('enabled_sources'))}",
        f"- Measured Sources: {as_int(s.get('measured_sources'))}",
        f"- Coverage %: {as_float(s.get('coverage_pct')):.2f}",
        f"- Measurement %: {as_float(s.get('measurement_pct')):.2f}",
        f"- Open-Access Approved Sources: {as_int(s.get('open_access_approved_sources'))}",
        f"- Combined Approved Sources: {as_int(s.get('combined_approved_sources'))}",
        "",
        "## Opportunity KPIs",
        f"- Rolling $/hr: {as_float(o.get('rolling_total_hour_usd')):,.2f}",
        f"- Measured $/hr: {as_float(o.get('measured_total_hour_usd')):,.2f}",
        f"- Top Sector: {o.get('top_sector', 'n/a')}",
        f"- Sector Count: {as_int(o.get('sector_count'))}",
        f"- Critical Alerts: {as_int(o.get('critical_lane_alerts'))}",
        f"- Warning Alerts: {as_int(o.get('warning_lane_alerts'))}",
        "",
        "## Gaps",
    ]

    if isinstance(gaps, list) and gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- No blocking gaps detected in the latest scorecard snapshot.")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    EXEC.mkdir(parents=True, exist_ok=True)
    scorecard = build_scorecard()
    SCORECARD_JSON.write_text(json.dumps(scorecard, indent=2), encoding="utf-8")
    SCORECARD_MD.write_text(render_markdown(scorecard), encoding="utf-8")
    kpi_summary = {
        "timestamp_utc": scorecard.get("generated_utc"),
        "readiness_tier": scorecard.get("readiness_tier"),
        "readiness_score": scorecard.get("readiness_score"),
        "equity_usd": scorecard.get("trading_kpis", {}).get("equity_usd"),
        "realized_roi_pct": scorecard.get("trading_kpis", {}).get("realized_roi_pct"),
        "win_rate_pct": scorecard.get("trading_kpis", {}).get("win_rate_pct"),
        "annualized_sharpe_proxy": scorecard.get("trading_kpis", {}).get("annualized_sharpe_proxy"),
        "max_drawdown_pct": scorecard.get("trading_kpis", {}).get("max_drawdown_pct"),
        "top_test_sharpe": scorecard.get("research_kpis", {}).get("top_test_sharpe"),
        "top_walkforward_sharpe_mean": scorecard.get("research_kpis", {}).get("top_walkforward_sharpe_mean"),
        "top_institutional_score": scorecard.get("research_kpis", {}).get("top_institutional_score"),
        "measured_total_hour_usd": scorecard.get("opportunity_kpis", {}).get("measured_total_hour_usd"),
        "rolling_total_hour_usd": scorecard.get("opportunity_kpis", {}).get("rolling_total_hour_usd"),
        "enabled_sources": scorecard.get("source_coverage", {}).get("enabled_sources"),
        "measured_sources": scorecard.get("source_coverage", {}).get("measured_sources"),
        "open_access_approved_sources": scorecard.get("source_coverage", {}).get("open_access_approved_sources"),
        "combined_approved_sources": scorecard.get("source_coverage", {}).get("combined_approved_sources"),
    }
    KPI_SUMMARY_JSON.write_text(json.dumps(kpi_summary, indent=2), encoding="utf-8")

    print("INSTITUTIONAL METRICS SCORECARD WRITTEN")
    print(SCORECARD_JSON)
    print(SCORECARD_MD)
    print(KPI_SUMMARY_JSON)
    print(f"Readiness: {scorecard.get('readiness_tier')} ({scorecard.get('readiness_score')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
