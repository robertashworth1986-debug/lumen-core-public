from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
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
        result = float(value)
        return result if not isinstance(value, bool) and math.isfinite(result) else default
    except Exception:
        return default


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
    shape_issues = []
    def mapping(value, label):
        if isinstance(value, dict):
            return value
        shape_issues.append(label + ': expected an object')
        return {}
    daily = mapping(load_json(DAILY_REPORT, {}), 'daily_report')
    perf = mapping(load_json(INVESTOR_PERF, {}), 'investor_performance')
    lineages = mapping(load_json(CHAMPION_LINEAGES, {}), 'champion_lineages')
    seed = mapping(load_json(SEED_VALIDATION, {}), 'seed_validation')
    registry = mapping(load_json(REGISTRY, {}), 'registry')
    opp = mapping(load_json(OPPORTUNITY_BRIEF, {}), 'opportunity_brief')
    breadth = mapping(load_json(SOURCE_BREADTH, {}), 'source_breadth')
    edge = mapping(load_json(EDGE_TRUTH, {}), 'edge_truth')

    account = mapping(daily.get('account', {}), 'daily_report.account')
    risk = mapping(daily.get('risk', {}), 'daily_report.risk')
    daily_perf = mapping(daily.get('performance', {}), 'daily_report.performance')
    champion = mapping(seed.get('champion', {}), 'seed_validation.champion')

    rows = registry_rows(registry)
    enabled_rows = [r for r in rows if r.get('enabled') is True]
    measured_rows = [
        r
        for r in rows
        if str(r.get("dollar_basis", "")).upper() == "MEASURED"
        or str(r.get("evidence_basis", "")).upper() == "MEASURED_FILE_MATCH"
        or as_int(r.get("rows"), 0) > 0
    ]

    top_lineages = lineages.get("top_lineages", []) if isinstance(lineages, dict) else []
    best_lineage = mapping(top_lineages[0], 'champion_lineages.top_lineages[0]') if isinstance(top_lineages, list) and top_lineages else {}
    if not isinstance(top_lineages, list):
        shape_issues.append('champion_lineages.top_lineages: expected a list')

    realized_roi_pct = as_float(account.get("return_total_pct"), 0.0)
    win_rate_pct = as_float(daily_perf.get("win_rate_pct"), as_float(perf.get("win_rate_pct"), 0.0))
    sharpe_proxy = as_float(daily_perf.get("annualized_sharpe_proxy"), as_float(perf.get("sharpe"), 0.0))
    max_drawdown_pct = as_float(risk.get("max_drawdown_pct"), abs(as_float(perf.get("max_drawdown"), 0.0)) * 100.0)

    walkforward_sharpe = as_float(best_lineage.get("wf_sharpe_mean"), 0.0)
    walkforward_stability = as_float(best_lineage.get("wf_stability"), 0.0)
    test_sharpe = as_float(best_lineage.get("test_sharpe"), as_float(champion.get("test_sharpe"), 0.0))
    institutional_score = as_float(best_lineage.get("institutional_score"), as_float(champion.get("institutional_score"), 0.0))

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

    payload = {
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
            "champion_flow": str(best_lineage.get("flow", champion.get("flow", "unknown"))),
            "champion_strategy": str(best_lineage.get("strategy", champion.get("strategy", "unknown"))),
            "champion_algo": str(best_lineage.get("algo", champion.get("algo", "unknown"))),
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
    # These legacy inputs contain no authenticated account-reconciliation or
    # buyer-acceptance contract. A score assembled from them cannot authorize
    # institutional promotion, even when all heuristic thresholds are met.
    payload['legacy_heuristic_diagnostic'] = {
        'score': readiness_score, 'tier': readiness_tier,
        'boundary': 'Unverified legacy arithmetic only; not investment or production readiness.',
    }
    payload['readiness_tier'] = 'HOLD'
    payload['readiness_score'] = None
    payload['score_components'] = None
    payload['trading_kpis'] = {key: None for key in payload['trading_kpis']}
    payload['broker_reconciled'] = False
    payload['investment_ready'] = False
    payload['source_shape_issues'] = shape_issues
    payload['source_completeness_verified'] = False
    payload['source_freshness_verified'] = False
    payload['source_coverage']['measured_sources'] = None
    payload['source_coverage']['measurement_pct'] = None
    payload['source_coverage']['declared_row_presence_sources'] = sum(type(row.get('rows')) is int and row['rows'] > 0 for row in rows)
    payload['declared_opportunity_inputs'] = {
        'rolling_total_hour_usd': as_float(opp.get('rolling_total_hour_usd'), None),
        'measured_total_hour_usd': as_float(opp.get('measured_total_hour_usd'), None),
        'boundary': 'Unverified legacy declarations; no realized savings or financial effect established.',
    }
    payload['opportunity_kpis']['measured_total_hour_usd'] = None
    payload['opportunity_kpis']['rolling_total_hour_usd'] = None
    payload['gaps'] = [
        'Account performance is unknown: authenticated initial balances, external flows, fills, fees, and final balances are not reconciled here.',
        'Source coverage and modeled opportunity amounts do not establish institutional investment readiness.',
        'Use the existing buyer-owned baseline validation and acceptance gate for commercial decisions.',
    ]
    return payload


def render_markdown(scorecard: dict[str, Any]) -> str:
    t = scorecard.get("trading_kpis", {})
    r = scorecard.get("research_kpis", {})
    s = scorecard.get("source_coverage", {})
    o = scorecard.get("opportunity_kpis", {})
    gaps = scorecard.get("gaps", [])

    lines = [
        "# Legacy Input Diagnostics - Investment Readiness Held",
        "",
        f"Generated UTC: {scorecard.get('generated_utc', 'n/a')}",
        f"Readiness Tier: {scorecard.get('readiness_tier', 'n/a')} | Score: {scorecard.get('readiness_score', 0)}",
        "",
        "## Trading KPIs",
        '- Equity, PnL, realized ROI, win rate, Sharpe, drawdown: Unknown / not reconciled',
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
        f"- Declared Enabled Sources: {as_int(s.get('enabled_sources'))}",
        f"- Declared Row-Presence Sources: {as_int(s.get('declared_row_presence_sources'))}",
        f"- Declared Enabled Share %: {as_float(s.get('coverage_pct')):.2f}",
        '- Validated measurement sources and coverage: Unknown / not established',
        f"- Open-Access Approved Sources: {as_int(s.get('open_access_approved_sources'))}",
        f"- Combined Approved Sources: {as_int(s.get('combined_approved_sources'))}",
        "",
        "## Opportunity KPIs",
        '- Realized or measured USD/hour: Unknown / not established',
        '- Legacy opportunity declarations are retained separately in JSON and are not financial actuals.',
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

    if scorecard.get('source_shape_issues'):
        lines += ['', '## Input shape holds', '']
        lines += ['- ' + issue for issue in scorecard['source_shape_issues']]

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    EXEC.mkdir(parents=True, exist_ok=True)
    scorecard = build_scorecard()
    SCORECARD_JSON.write_text(json.dumps(scorecard, indent=2, allow_nan=False), encoding="utf-8")
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
    KPI_SUMMARY_JSON.write_text(json.dumps(kpi_summary, indent=2, allow_nan=False), encoding="utf-8")

    print("INSTITUTIONAL METRICS SCORECARD WRITTEN")
    print(SCORECARD_JSON)
    print(SCORECARD_MD)
    print(KPI_SUMMARY_JSON)
    print(f"Readiness: {scorecard.get('readiness_tier')} ({scorecard.get('readiness_score')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
