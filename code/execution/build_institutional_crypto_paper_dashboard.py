from __future__ import annotations

import argparse
import json
import math
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import panel as pn
import plotly.graph_objects as go


ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
EXEC_OUT = ROOT / "out" / "execution"
DASH = ROOT / "dashboard"

REPORT_FILE = EXEC_OUT / "institutional_crypto_paper_report.json"
HASH_FILE = EXEC_OUT / "institutional_crypto_paper_report_sha256.json"
STATUS_FILE = EXEC_OUT / "multi_exchange_paper_ticker_status.json"
PAPER_LEDGER_FILE = EXEC_OUT / "binanceus_paper_ledger.jsonl"
HTML_OUT = DASH / "institutional_crypto_paper_dashboard.html"
PDF_BRIEF_FILE = EXEC_OUT / "institutional_crypto_executive_brief.pdf"
HEARTBEAT_FILE = EXEC_OUT / "institutional_crypto_dashboard_heartbeat.json"
REGIME_HISTORY_FILE = EXEC_OUT / "institutional_crypto_regime_history.jsonl"
SECTOR_MATRIX_FILE = ROOT / "out" / "sector_value_matrix.json"
SOURCE_TRUTH_FILE = ROOT / "out" / "source_truth_table.json"
INFRA_FROZEN_DELTAS_FILE = ROOT / "out" / "infra_frozen_deltas.jsonl"
OPPORTUNITY_HISTORY_FILE = EXEC_OUT / "institutional_sector_opportunity_history.jsonl"
LANE_ALERTS_LATEST_FILE = EXEC_OUT / "institutional_sector_lane_alerts_latest.json"
LANE_ALERTS_HISTORY_FILE = EXEC_OUT / "institutional_sector_lane_alerts_history.jsonl"
OPPORTUNITY_EXECUTIVE_JSON = EXEC_OUT / "institutional_opportunity_executive_brief.json"
OPPORTUNITY_EXECUTIVE_MD = EXEC_OUT / "institutional_opportunity_executive_brief.md"
LIVE_ENGINE_HEARTBEAT_FILE = EXEC_OUT / "live_engine_heartbeat.json"
INSTITUTIONAL_SCORECARD_FILE = EXEC_OUT / "institutional_metrics_scorecard.json"

DELTA_ROWS_SCAN_LIMIT = 50000
OPPORTUNITY_TABLE_MAX_ROWS = 500
TOP_SECTOR_CHART_MAX_ROWS = 40

pn.extension("plotly", sizing_mode="stretch_width")

INVESTOR_THEME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
    --bg-main: #060b12;
    --bg-panel: rgba(12, 19, 29, 0.82);
    --bg-panel-soft: rgba(16, 24, 36, 0.7);
    --line-soft: rgba(126, 172, 214, 0.26);
    --gold: #dfbb6b;
    --teal: #56d7cb;
    --ice: #d8e6f7;
    --warn: #ffbd66;
    --crit: #ff7a66;
}

body, .bk-root {
    background: radial-gradient(1200px 700px at 15% -5%, rgba(223, 187, 107, 0.14), transparent 55%),
                            radial-gradient(900px 520px at 90% 15%, rgba(86, 215, 203, 0.12), transparent 50%),
                            linear-gradient(145deg, #060b12 0%, #0a121d 100%);
    color: var(--ice);
    font-family: 'IBM Plex Sans', sans-serif;
}

* {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

.bk-root, .bk-root * {
    color: var(--ice);
}

.bk-Column, .bk-Row {
    color: var(--ice);
}

.bk-markdown, .bk-markup, .bk-panel-models-markup-Markdown, .bk-panel-models-markup-HTML {
    color: var(--ice) !important;
    font-size: 15px;
    line-height: 1.5;
}

.bk-markdown p, .bk-markdown li, .bk-markdown span, .bk-markdown strong {
    color: var(--ice) !important;
}

.bk-markdown h2 {
    font-size: 30px;
    font-weight: 700;
}

.bk-markdown h3 {
    font-size: 22px;
    font-weight: 700;
}

.bk-Row, .bk-Column {
    gap: 14px;
}

.bk-markdown h1, .bk-markdown h2, .bk-markdown h3 {
    font-family: 'Space Grotesk', sans-serif;
    letter-spacing: 0.2px;
}

.investor-hero {
    background: linear-gradient(120deg, rgba(223, 187, 107, 0.17), rgba(86, 215, 203, 0.14) 42%, rgba(10, 18, 29, 0.88));
    border: 1px solid rgba(223, 187, 107, 0.34);
    border-radius: 20px;
    padding: 20px 24px;
    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.35);
    position: relative;
    overflow: hidden;
}

.investor-hero::after {
    content: '';
    position: absolute;
    right: -70px;
    top: -70px;
    width: 220px;
    height: 220px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(223, 187, 107, 0.34), transparent 65%);
    animation: pulseOrb 4.2s ease-in-out infinite;
}

.hero-kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(120px, 1fr));
    gap: 12px;
    margin-top: 12px;
}

.hero-kpi {
    background: rgba(6, 11, 18, 0.48);
    border: 1px solid var(--line-soft);
    border-radius: 12px;
    padding: 10px;
}

.hero-kpi-label {
    font-size: 11px;
    opacity: 0.8;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

.hero-kpi-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 22px;
    font-weight: 700;
    margin-top: 4px;
}

.hero-kpi-value, .hero-kpi-label {
    color: var(--ice);
}

.lane-badge {
    display: inline-block;
    margin-top: 8px;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 600;
    border: 1px solid var(--line-soft);
}

.lane-high { background: rgba(86, 215, 203, 0.18); color: var(--teal); }
.lane-medium { background: rgba(223, 187, 107, 0.18); color: var(--gold); }
.lane-low { background: rgba(255, 189, 102, 0.16); color: var(--warn); }

.alert-banner {
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 13px;
    font-weight: 600;
    border: 1px solid var(--line-soft);
    background: rgba(10, 17, 27, 0.7);
}

.alert-critical {
    border-color: rgba(255, 122, 102, 0.56);
    color: var(--crit);
    background: rgba(255, 122, 102, 0.12);
}

.alert-watch {
    border-color: rgba(255, 189, 102, 0.52);
    color: var(--warn);
    background: rgba(255, 189, 102, 0.1);
}

.alert-clean {
    border-color: rgba(86, 215, 203, 0.52);
    color: var(--teal);
    background: rgba(86, 215, 203, 0.1);
}

.marquee-wrap {
    overflow: hidden;
    border: 1px solid var(--line-soft);
    border-radius: 10px;
    background: rgba(7, 12, 18, 0.64);
}

.marquee-track {
    white-space: nowrap;
    display: inline-block;
    padding: 8px 0;
    animation: tickerSlide 24s linear infinite;
    font-size: 13px;
}

.marquee-track span {
    margin-right: 26px;
    color: var(--ice);
}

.bk-header {
    border-bottom: 1px solid rgba(126, 172, 214, 0.3);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
}

.bk-header .bk-toolbar-button, .bk-header .bk-toolbar-icon {
    color: var(--ice) !important;
}

.bk-sidebar {
    background: linear-gradient(180deg, rgba(4, 9, 15, 0.98), rgba(8, 15, 24, 0.95)) !important;
    border-right: 1px solid rgba(126, 172, 214, 0.25);
}

.bk-panel-models-tabulator-DataTabulator,
.bk-data-table,
.slickgrid-container,
.slick-viewport,
.slick-row,
.slick-cell,
.slick-header-columns,
.slick-header-column {
    background: rgba(11, 19, 30, 0.95) !important;
    color: var(--ice) !important;
    border-color: rgba(126, 172, 214, 0.2) !important;
}

.slick-header-column {
    font-size: 14px !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.slick-cell {
    font-size: 13px !important;
    font-weight: 500 !important;
}

.tabulator,
.tabulator .tabulator-header,
.tabulator .tabulator-col,
.tabulator .tabulator-row,
.tabulator .tabulator-cell {
    background: rgba(11, 19, 30, 0.95) !important;
    color: var(--ice) !important;
    border-color: rgba(126, 172, 214, 0.2) !important;
}

.tabulator .tabulator-header .tabulator-col {
    font-size: 14px !important;
    font-weight: 700 !important;
}

.tabulator .tabulator-row .tabulator-cell {
    font-size: 13px !important;
    font-weight: 500 !important;
}

.bk-input, .bk-text-input, .bk-select {
    color: var(--ice) !important;
    background: rgba(11, 19, 30, 0.95) !important;
    border-color: rgba(126, 172, 214, 0.3) !important;
}

.bk-panel-models-markup-Markdown a,
.bk-markdown a {
    color: var(--gold) !important;
    font-weight: 600;
}

@keyframes tickerSlide {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}

@keyframes pulseOrb {
    0%, 100% { opacity: 0.7; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.08); }
}

@media (max-width: 960px) {
    .hero-kpis {
        grid-template-columns: repeat(2, minmax(120px, 1fr));
    }
}

@media (min-width: 1920px) {
    .bk-markdown, .bk-markup {
        font-size: 17px;
    }
    .hero-kpi-value {
        font-size: 26px;
    }
    .slick-cell, .tabulator .tabulator-row .tabulator-cell {
        font-size: 14px !important;
    }
}
"""


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def load_jsonl(path: Path, limit: int = 220):
    rows = []
    try:
        if path.exists():
            for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]:
                raw = raw.strip()
                if raw:
                    rows.append(json.loads(raw))
    except Exception:
        pass
    return rows


def append_jsonl(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def load_artifacts() -> tuple[dict, dict, dict, list[dict]]:
    report = load_json(REPORT_FILE, {})
    hashes = load_json(HASH_FILE, {})
    status = load_json(STATUS_FILE, {})
    ledger = load_jsonl(PAPER_LEDGER_FILE, limit=220)
    if not report:
        raise SystemExit("Missing institutional crypto paper report")
    return report, hashes, status, ledger


def _f(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _fmt_usd(value: float) -> str:
    return f"${value:,.0f}"


def _fmt_pct(value: float) -> str:
    return f"{value * 100.0:,.2f}%"


def _pct_delta(current: float, baseline: float) -> float:
    base = _f(baseline, 0.0)
    if abs(base) < 1e-9:
        return 0.0
    return ((_f(current, 0.0) - base) / base) * 100.0


def _compute_optimization_live_state(data: dict) -> dict:
    summary = data.get("opportunity_summary", {}) if isinstance(data.get("opportunity_summary", {}), dict) else {}
    history_df = data.get("opportunity_history_df") if isinstance(data.get("opportunity_history_df"), pd.DataFrame) else pd.DataFrame()

    rolling_total = _f(summary.get("rolling_total_hour_usd"), 0.0)
    measured_total = _f(summary.get("measured_total_hour_usd"), 0.0)
    modeled_total = _f(summary.get("modeled_total_hour_usd"), 0.0)

    base_gain_pct = _pct_delta(rolling_total, modeled_total)
    base_better_pct = _pct_delta(measured_total, modeled_total)

    slope_gain_pct_per_sec = 0.0
    slope_better_pct_per_sec = 0.0
    if not history_df.empty and len(history_df) >= 2:
        try:
            prev = history_df.iloc[-2]
            curr = history_df.iloc[-1]
            prev_ts = datetime.fromisoformat(str(prev.get("timestamp_utc")))
            curr_ts = datetime.fromisoformat(str(curr.get("timestamp_utc")))
            dt = max((curr_ts - prev_ts).total_seconds(), 1.0)

            prev_modeled = _f(prev.get("modeled_total_hour_usd"), 0.0)
            prev_gain = _pct_delta(_f(prev.get("rolling_total_hour_usd"), 0.0), prev_modeled)
            prev_better = _pct_delta(_f(prev.get("measured_total_hour_usd"), 0.0), prev_modeled)

            slope_gain_pct_per_sec = (base_gain_pct - prev_gain) / dt
            slope_better_pct_per_sec = (base_better_pct - prev_better) / dt
        except Exception:
            slope_gain_pct_per_sec = 0.0
            slope_better_pct_per_sec = 0.0

    # Guardrail to keep 1-second live movement readable.
    slope_gain_pct_per_sec = max(min(slope_gain_pct_per_sec, 1.5), -1.5)
    slope_better_pct_per_sec = max(min(slope_better_pct_per_sec, 1.5), -1.5)

    return {
        "base_gain_pct": base_gain_pct,
        "base_better_pct": base_better_pct,
        "current_gain_pct": base_gain_pct,
        "current_better_pct": base_better_pct,
        "slope_gain_pct_per_sec": slope_gain_pct_per_sec,
        "slope_better_pct_per_sec": slope_better_pct_per_sec,
        "pulse_phase": 0.0,
        "last_tick_ts": time.time(),
        "last_gain_pct": base_gain_pct,
        "last_better_pct": base_better_pct,
        "gain_direction": "FLAT",
        "better_direction": "FLAT",
    }


def _render_optimization_live_html(state: dict) -> str:
    gain = _f(state.get("current_gain_pct"), 0.0)
    better = _f(state.get("current_better_pct"), 0.0)
    gain_dir = str(state.get("gain_direction", "FLAT")).upper()
    better_dir = str(state.get("better_direction", "FLAT")).upper()

    gain_color = "#56d7cb" if gain >= 0.0 else "#ff7a66"
    better_color = "#56d7cb" if better >= 0.0 else "#ff7a66"

    return (
        "<div style='border:1px solid rgba(126,172,214,0.28);border-radius:12px;padding:10px 12px;"
        "background:rgba(8,14,22,0.76)'>"
        "<div style='font-size:12px;opacity:0.85;text-transform:uppercase;letter-spacing:0.5px'>"
        "Live Optimization Gain (1s)</div>"
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px'>"
        f"<div style='border:1px solid rgba(86,215,203,0.22);border-radius:10px;padding:8px'>"
        "<div style='font-size:11px;opacity:0.8'>Optimization vs Modeled Baseline</div>"
        f"<div style='font-size:22px;font-weight:700;color:{gain_color}'>{gain:+.2f}%</div>"
        f"<div style='font-size:11px;opacity:0.85'>Direction: {gain_dir}</div>"
        "</div>"
        f"<div style='border:1px solid rgba(223,187,107,0.30);border-radius:10px;padding:8px'>"
        "<div style='font-size:11px;opacity:0.8'>Measured Edge vs Modeled Baseline</div>"
        f"<div style='font-size:22px;font-weight:700;color:{better_color}'>{better:+.2f}%</div>"
        f"<div style='font-size:11px;opacity:0.85'>Direction: {better_dir}</div>"
        "</div>"
        "</div>"
        "</div>"
    )


def _lane_css_class(label: str) -> str:
    lane = str(label).upper()
    if lane == "HIGH":
        return "lane-high"
    if lane == "MEDIUM":
        return "lane-medium"
    return "lane-low"


def _orchestrator_status_rows(heartbeat: dict) -> list[dict]:
    hb = heartbeat if isinstance(heartbeat, dict) else {}
    reselection = hb.get("reselection_status", {}) if isinstance(hb.get("reselection_status", {}), dict) else {}
    stream = hb.get("stream_status", {}) if isinstance(hb.get("stream_status", {}), dict) else {}
    return [
        {"metric": "Heartbeat Time", "value": str(hb.get("timestamp_utc", "n/a"))},
        {"metric": "Orchestrator Status", "value": str(hb.get("status", "unknown")).upper()},
        {"metric": "Selection Symbol", "value": str(hb.get("symbol", "n/a"))},
        {"metric": "Runtime Mode", "value": str(hb.get("runtime_mode", "n/a")).upper()},
        {"metric": "Signal Source", "value": str(hb.get("signal_source", "n/a"))},
        {"metric": "Stream State", "value": str(stream.get("status", "n/a")).upper()},
        {"metric": "Reselection State", "value": str(reselection.get("status", "n/a")).upper()},
        {"metric": "Engine Lock", "value": str(hb.get("execution_lock", "n/a")).upper()},
    ]


def _position_concentration(status: dict) -> dict:
    state = status.get("binanceus_paper_engine", {}).get("state", {}) if isinstance(status, dict) else {}
    positions = state.get("positions", {}) if isinstance(state, dict) else {}
    notionals = []
    total = 0.0
    for sym, pos in positions.items():
        qty = _f(pos.get("qty"), 0.0)
        entry = _f(pos.get("entry"), 0.0)
        notional = qty * entry
        if notional > 0.0:
            notionals.append((sym, notional))
            total += notional
    if total <= 0.0:
        return {"weights": [], "max_weight": 0.0, "max_symbol": "none", "risk_level": "LOW", "risk_warning": "No active concentration."}
    weights = []
    max_weight = 0.0
    max_symbol = "none"
    for sym, notional in sorted(notionals, key=lambda item: item[1], reverse=True):
        weight = notional / total
        weights.append({"symbol": sym, "notional": notional, "weight": weight})
        if weight > max_weight:
            max_weight = weight
            max_symbol = sym
    if max_weight >= 0.60:
        risk_level = "CRITICAL"
        risk_warning = "Single-name concentration is above 60%."
    elif max_weight >= 0.40:
        risk_level = "HIGH"
        risk_warning = "Single-name concentration is above 40%."
    elif max_weight >= 0.25:
        risk_level = "ELEVATED"
        risk_warning = "Concentration is elevated."
    else:
        risk_level = "LOW"
        risk_warning = "Concentration is within the controlled band."
    return {"weights": weights, "max_weight": max_weight, "max_symbol": max_symbol, "risk_level": risk_level, "risk_warning": risk_warning}


def _equity_figure(seed: float, equity_curve: list[float]) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=equity_curve, mode="lines+markers", line={"color": "#d5b26d", "width": 3}, name="Equity"))
    fig.add_hline(y=seed, line_dash="dot", line_color="#61cfc0")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f6f2e8", "size": 16},
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        title="Equity Trajectory",
        xaxis_title="Observation",
        yaxis_title="USD",
    )
    return fig


def _concentration_figure(weights: list[dict]) -> go.Figure:
    fig = go.Figure()
    if weights:
        fig.add_trace(
            go.Bar(
                x=[item.get("symbol", "") for item in weights],
                y=[_f(item.get("weight"), 0.0) * 100.0 for item in weights],
                marker_color="#61cfc0",
                name="Weight %",
            )
        )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f6f2e8", "size": 16},
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        title="Position Concentration",
        yaxis_title="Weight %",
    )
    return fig


def _frontier_figure(frontier_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not frontier_df.empty:
        fig.add_trace(
            go.Scatter(
                x=(frontier_df["vol_proxy"] * 100.0),
                y=frontier_df["hybrid_score"],
                mode="markers+text",
                text=frontier_df["symbol"],
                textposition="top center",
                marker={
                    "size": 12,
                    "color": (frontier_df["pct24"] * 100.0),
                    "colorscale": "Viridis",
                    "showscale": True,
                    "colorbar": {"title": "%24h"},
                },
                name="Candidates",
            )
        )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f6f2e8", "size": 16},
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        title="Optimizer Frontier (Edge vs Vol)",
        xaxis_title="Vol Proxy %",
        yaxis_title="Hybrid Score",
    )
    return fig


def _regime_history_figure(regime_history_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not regime_history_df.empty:
        xvals = regime_history_df["timestamp_utc"]
        fig.add_trace(go.Scatter(x=xvals, y=(regime_history_df["realized_vol_pct"] * 100.0), mode="lines+markers", name="Realized Vol %", line={"color": "#f5a623"}))
        fig.add_trace(go.Scatter(x=xvals, y=(regime_history_df["breadth_pos_pct24"] * 100.0), mode="lines+markers", name="Breadth %", line={"color": "#61cfc0"}))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f6f2e8", "size": 16},
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        title="Regime History",
        xaxis_title="Timestamp",
        yaxis_title="Percent",
    )
    return fig


def _confidence_lane(measured_hour: float, modeled_hour: float, measured_sources: int) -> str:
    if measured_hour > 0.0 and modeled_hour > 0.0 and measured_sources >= 2:
        return "HIGH"
    if measured_hour > 0.0:
        return "MEDIUM"
    if modeled_hour > 0.0:
        return "LOW"
    return "UNKNOWN"


def _sector_opportunity_data() -> tuple[pd.DataFrame, dict]:
    matrix_payload = load_json(SECTOR_MATRIX_FILE, {})
    truth_payload = load_json(SOURCE_TRUTH_FILE, {})
    delta_rows = load_jsonl(INFRA_FROZEN_DELTAS_FILE, limit=DELTA_ROWS_SCAN_LIMIT)

    matrix_rows: list[dict] = []
    if isinstance(matrix_payload, list):
        matrix_rows = matrix_payload
    elif isinstance(matrix_payload, dict):
        matrix_rows = matrix_payload.get("sector_value_matrix", []) if isinstance(matrix_payload.get("sector_value_matrix", []), list) else []

    truth_rows: list[dict] = []
    if isinstance(truth_payload, dict):
        raw_rows = truth_payload.get("sources", truth_payload.get("rows", []))
        if isinstance(raw_rows, list):
            truth_rows = raw_rows

    modeled_by_sector: dict[str, float] = {}
    for row in matrix_rows:
        sector = str(row.get("sector", "unknown")).strip() or "unknown"
        modeled_by_sector[sector] = modeled_by_sector.get(sector, 0.0) + _f(row.get("hour"), 0.0)

    measured_hour_by_sector: dict[str, float] = {}
    measured_sources_by_sector: dict[str, set[str]] = {}
    for row in delta_rows:
        sector = str(row.get("sector", "unknown")).strip() or "unknown"
        source = str(row.get("source", "unknown")).strip() or "unknown"
        key_present = bool(row.get("key_present", False))
        rows_written = int(_f(row.get("rows_written"), 0.0))
        est_hour = _f(row.get("estimated_hourly_value_usd"), 0.0)
        if key_present and rows_written > 0 and est_hour > 0.0:
            measured_hour_by_sector[sector] = measured_hour_by_sector.get(sector, 0.0) + est_hour
            measured_sources_by_sector.setdefault(sector, set()).add(source)

    measured_truth_rows_by_sector: dict[str, int] = {}
    for row in truth_rows:
        sector = str(row.get("sector", "unknown")).strip() or "unknown"
        rows = int(_f(row.get("rows"), 0.0))
        enabled = bool(row.get("enabled", False)) or str(row.get("status", "")).upper() in ("LIVE_KEY_PRESENT", "ENABLED", "ACTIVE", "OK")
        if rows > 0 or enabled:
            measured_truth_rows_by_sector[sector] = measured_truth_rows_by_sector.get(sector, 0) + rows

    sectors = set(modeled_by_sector.keys()) | set(measured_hour_by_sector.keys()) | set(measured_truth_rows_by_sector.keys())
    board_rows = []
    for sector in sectors:
        modeled = modeled_by_sector.get(sector, 0.0)
        measured = measured_hour_by_sector.get(sector, 0.0)
        measured_sources = len(measured_sources_by_sector.get(sector, set()))
        truth_rows = measured_truth_rows_by_sector.get(sector, 0)
        lane = _confidence_lane(measured, modeled, measured_sources)
        rolling_hour = measured if measured > 0.0 else modeled
        basis = "MEASURED" if measured > 0.0 else "MODELED_TRANSLATION"
        board_rows.append(
            {
                "sector": sector,
                "rolling_hour_usd": round(rolling_hour, 2),
                "measured_hour_usd": round(measured, 2),
                "modeled_hour_usd": round(modeled, 2),
                "modeled_only_hour_usd": round(max(modeled - measured, 0.0), 2),
                "measured_sources": measured_sources,
                "measured_truth_rows": truth_rows,
                "confidence_lane": lane,
                "value_basis": basis,
            }
        )

    board_rows.sort(key=lambda item: _f(item.get("rolling_hour_usd"), 0.0), reverse=True)
    board_df = pd.DataFrame(board_rows)
    if board_df.empty:
        board_df = pd.DataFrame(
            columns=[
                "sector",
                "rolling_hour_usd",
                "measured_hour_usd",
                "modeled_hour_usd",
                "modeled_only_hour_usd",
                "measured_sources",
                "measured_truth_rows",
                "confidence_lane",
                "value_basis",
            ]
        )

    summary = {
        "sectors": int(len(board_df)),
        "rolling_total_hour_usd": float(board_df["rolling_hour_usd"].sum()) if not board_df.empty else 0.0,
        "measured_total_hour_usd": float(board_df["measured_hour_usd"].sum()) if not board_df.empty else 0.0,
        "modeled_total_hour_usd": float(board_df["modeled_hour_usd"].sum()) if not board_df.empty else 0.0,
        "modeled_only_hour_usd": float(board_df["modeled_only_hour_usd"].sum()) if not board_df.empty else 0.0,
        "top_sector": str(board_df.iloc[0]["sector"]) if not board_df.empty else "n/a",
    }
    return board_df, summary


def _sector_opportunity_figure(opportunity_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not opportunity_df.empty:
        top_df = opportunity_df.head(TOP_SECTOR_CHART_MAX_ROWS)
        fig.add_trace(
            go.Bar(
                x=top_df["sector"],
                y=top_df["measured_hour_usd"],
                name="Measured $/hr",
                marker_color="#61cfc0",
            )
        )
        fig.add_trace(
            go.Bar(
                x=top_df["sector"],
                y=top_df["modeled_only_hour_usd"],
                name="Modeled-only $/hr",
                marker_color="#d5b26d",
            )
        )
    fig.update_layout(
        barmode="stack",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f6f2e8", "size": 16},
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        title="Sector Rolling Opportunity Gain ($/hr)",
        xaxis_title="Sector",
        yaxis_title="USD per hour",
    )
    return fig


def _opportunity_history_figure(history_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if not history_df.empty:
        fig.add_trace(
            go.Scatter(
                x=history_df["timestamp_utc"],
                y=history_df["rolling_total_hour_usd"],
                mode="lines+markers",
                name="Rolling total $/hr",
                line={"color": "#61cfc0", "width": 3},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=history_df["timestamp_utc"],
                y=history_df["measured_total_hour_usd"],
                mode="lines+markers",
                name="Measured $/hr",
                line={"color": "#f5a623", "width": 2},
            )
        )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#f6f2e8", "size": 16},
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        title="Rolling Opportunity Gain History",
        xaxis_title="Timestamp",
        yaxis_title="USD per hour",
    )
    return fig


def _lane_rank(lane: str) -> int:
    order = {"UNKNOWN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    return order.get(str(lane).upper(), 0)


def _compute_lane_alerts(opportunity_df: pd.DataFrame, opportunity_history_df: pd.DataFrame) -> dict:
    alerts: list[dict] = []
    previous_rows: list[dict] = []
    if not opportunity_history_df.empty and "top_rows" in opportunity_history_df.columns:
        try:
            last_top_rows = opportunity_history_df.iloc[-1].get("top_rows")
            if isinstance(last_top_rows, list):
                previous_rows = [row for row in last_top_rows if isinstance(row, dict)]
        except Exception:
            previous_rows = []

    current_by_sector: dict[str, dict] = {}
    if not opportunity_df.empty:
        for row in opportunity_df.to_dict(orient="records"):
            sector = str(row.get("sector", "unknown"))
            current_by_sector[sector] = row

    for prev in previous_rows:
        sector = str(prev.get("sector", "unknown"))
        curr = current_by_sector.get(sector)
        if curr is None:
            alerts.append(
                {
                    "severity": "warning",
                    "type": "sector_missing",
                    "sector": sector,
                    "message": "Sector dropped out of the current opportunity board.",
                }
            )
            continue

        prev_lane = str(prev.get("confidence_lane", "UNKNOWN"))
        curr_lane = str(curr.get("confidence_lane", "UNKNOWN"))
        if _lane_rank(curr_lane) < _lane_rank(prev_lane):
            alerts.append(
                {
                    "severity": "critical",
                    "type": "lane_downgrade",
                    "sector": sector,
                    "message": f"Lane downgraded from {prev_lane} to {curr_lane}.",
                    "previous_lane": prev_lane,
                    "current_lane": curr_lane,
                }
            )

        prev_measured = _f(prev.get("measured_hour_usd"), 0.0)
        curr_measured = _f(curr.get("measured_hour_usd"), 0.0)
        if prev_measured > 0.0 and curr_measured < (prev_measured * 0.80):
            drop_pct = ((prev_measured - curr_measured) / prev_measured) * 100.0
            alerts.append(
                {
                    "severity": "warning",
                    "type": "measured_drop",
                    "sector": sector,
                    "message": f"Measured hourly value dropped by {drop_pct:.2f}%.",
                    "previous_measured_hour_usd": round(prev_measured, 2),
                    "current_measured_hour_usd": round(curr_measured, 2),
                }
            )

        prev_sources = int(_f(prev.get("measured_sources"), 0.0))
        curr_sources = int(_f(curr.get("measured_sources"), 0.0))
        if prev_sources > 0 and curr_sources < prev_sources:
            alerts.append(
                {
                    "severity": "warning",
                    "type": "source_coverage_drop",
                    "sector": sector,
                    "message": f"Measured source coverage dropped from {prev_sources} to {curr_sources}.",
                    "previous_measured_sources": prev_sources,
                    "current_measured_sources": curr_sources,
                }
            )

    critical_count = sum(1 for item in alerts if str(item.get("severity", "")).lower() == "critical")
    warning_count = sum(1 for item in alerts if str(item.get("severity", "")).lower() == "warning")
    return {
        "generated_utc": now_utc(),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "total_alerts": len(alerts),
        "alerts": alerts,
    }


def _write_opportunity_operating_pack(data: dict, snapshot_key: str) -> None:
    summary = data.get("opportunity_summary", {})
    opportunity_df = data.get("opportunity_df")
    lane_alerts = data.get("lane_alerts", {})
    top_rows: list[dict] = []
    if isinstance(opportunity_df, pd.DataFrame) and not opportunity_df.empty:
        top_rows = opportunity_df.to_dict(orient="records")

    payload = {
        "timestamp_utc": now_utc(),
        "snapshot_key": snapshot_key,
        "rolling_total_hour_usd": round(_f(summary.get("rolling_total_hour_usd"), 0.0), 2),
        "measured_total_hour_usd": round(_f(summary.get("measured_total_hour_usd"), 0.0), 2),
        "modeled_total_hour_usd": round(_f(summary.get("modeled_total_hour_usd"), 0.0), 2),
        "modeled_only_hour_usd": round(_f(summary.get("modeled_only_hour_usd"), 0.0), 2),
        "top_sector": str(summary.get("top_sector", "n/a")),
        "sectors": int(_f(summary.get("sectors"), 0.0)),
        "lane_alerts": lane_alerts,
        "top_rows": top_rows,
    }
    OPPORTUNITY_EXECUTIVE_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines = [
        "# Institutional Opportunity Executive Brief",
        "",
        f"Generated UTC: {payload['timestamp_utc']}",
        f"Snapshot Key: {snapshot_key}",
        "",
        "## Totals",
        f"- Rolling total hourly value: {_fmt_usd(_f(payload['rolling_total_hour_usd']))}/hr",
        f"- Measured total hourly value: {_fmt_usd(_f(payload['measured_total_hour_usd']))}/hr",
        f"- Modeled-only hourly value: {_fmt_usd(_f(payload['modeled_only_hour_usd']))}/hr",
        f"- Top sector: {payload['top_sector']}",
        "",
        "## Lane Alerts",
        f"- Critical alerts: {int(_f(lane_alerts.get('critical_count'), 0.0))}",
        f"- Warning alerts: {int(_f(lane_alerts.get('warning_count'), 0.0))}",
        f"- Total alerts: {int(_f(lane_alerts.get('total_alerts'), 0.0))}",
        "",
        "## Top Sectors",
    ]
    for row in top_rows[: min(20, len(top_rows))]:
        md_lines.append(
            "- "
            f"{row.get('sector', 'n/a')}: rolling={_fmt_usd(_f(row.get('rolling_hour_usd')))}"
            f"/hr, measured={_fmt_usd(_f(row.get('measured_hour_usd')))}"
            f"/hr, lane={row.get('confidence_lane', 'n/a')}"
        )
    if not top_rows:
        md_lines.append("- No sectors available.")

    OPPORTUNITY_EXECUTIVE_MD.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    alerts_payload = {
        "timestamp_utc": payload["timestamp_utc"],
        "snapshot_key": snapshot_key,
        "critical_count": int(_f(lane_alerts.get("critical_count"), 0.0)),
        "warning_count": int(_f(lane_alerts.get("warning_count"), 0.0)),
        "total_alerts": int(_f(lane_alerts.get("total_alerts"), 0.0)),
        "alerts": lane_alerts.get("alerts", []),
    }
    LANE_ALERTS_LATEST_FILE.write_text(json.dumps(alerts_payload, indent=2), encoding="utf-8")
    append_jsonl(LANE_ALERTS_HISTORY_FILE, alerts_payload)


def _dashboard_data(report: dict, hashes: dict, status: dict, ledger: list[dict], include_cross_sector: bool) -> dict:
    portfolio = report.get("portfolio", {})
    audit = report.get("decision_audit", {})
    allocator = audit.get("scientific_allocator", {}) if isinstance(audit, dict) else {}
    regime = audit.get("regime_controller", {}) if isinstance(audit, dict) else {}
    event = audit.get("last_event", {}) if isinstance(audit, dict) else {}
    candidates = audit.get("top_candidates", {}).get("hybrid", []) if isinstance(audit, dict) else []

    seed = _f(report.get("seed_request", {}).get("active_initial_cash_usd"), 0.0)
    equity = _f(portfolio.get("equity_usd"), 0.0)
    cash = _f(portfolio.get("cash_usd"), 0.0)
    gross = _f(portfolio.get("gross_position_value_usd"), 0.0)
    ret = _f(portfolio.get("return_pct"), 0.0)

    equity_curve = [seed]
    realized = 0.0
    for row in ledger:
        if str(row.get("side", "")).lower() == "sell":
            realized += _f(row.get("pnl_usd"), 0.0)
            equity_curve.append(seed + realized)
    if len(equity_curve) == 1:
        equity_curve.append(equity)

    concentration = _position_concentration(status)
    candidate_df = pd.DataFrame(candidates[:10]) if candidates else pd.DataFrame(columns=["symbol", "hybrid_score", "pct24", "quote_volume", "r2", "r4", "r8"])
    if not candidate_df.empty:
        for column in ["hybrid_score", "pct24", "quote_volume", "r2", "r4", "r8"]:
            if column in candidate_df.columns:
                candidate_df[column] = candidate_df[column].map(lambda x: round(_f(x, 0.0), 6))
        candidate_df["vol_proxy"] = candidate_df.apply(
            lambda row: max(abs(_f(row.get("r2"), 0.0)), abs(_f(row.get("r4"), 0.0)) / 2.0, abs(_f(row.get("r8"), 0.0)) / 4.0, abs(_f(row.get("pct24"), 0.0)) / 8.0, 0.005),
            axis=1,
        )
    else:
        candidate_df["vol_proxy"] = []

    frontier_df = pd.DataFrame(columns=["symbol", "hybrid_score", "vol_proxy", "pct24"])
    if not candidate_df.empty:
        frontier_cols = [col for col in ["symbol", "hybrid_score", "vol_proxy", "pct24"] if col in candidate_df.columns]
        frontier_df = candidate_df[frontier_cols].copy()

    ledger_df = pd.DataFrame(ledger[-20:]) if ledger else pd.DataFrame(columns=["timestamp_utc", "side", "symbol", "notional_usd", "pnl_usd"])
    hash_df = pd.DataFrame(hashes.get("files", [])) if isinstance(hashes, dict) else pd.DataFrame(columns=["path", "sha256"])
    if not hash_df.empty:
        hash_df["path"] = hash_df["path"].map(lambda x: Path(str(x)).name)
        hash_df["sha256"] = hash_df["sha256"].map(lambda x: str(x)[:20] + "...")

    regime_history_rows = load_jsonl(REGIME_HISTORY_FILE, limit=240)
    regime_history_df = pd.DataFrame(regime_history_rows) if regime_history_rows else pd.DataFrame(columns=["timestamp_utc", "regime", "realized_vol_pct", "breadth_pos_pct24", "heat_multiplier"])
    if not regime_history_df.empty:
        for col in ["realized_vol_pct", "breadth_pos_pct24", "heat_multiplier", "risk_aversion_multiplier", "confidence_multiplier"]:
            if col in regime_history_df.columns:
                regime_history_df[col] = regime_history_df[col].map(lambda x: _f(x, 0.0))

    if include_cross_sector:
        opportunity_df, opportunity_summary = _sector_opportunity_data()
        opportunity_history_rows = load_jsonl(OPPORTUNITY_HISTORY_FILE, limit=360)
        opportunity_history_df = pd.DataFrame(opportunity_history_rows) if opportunity_history_rows else pd.DataFrame(columns=["timestamp_utc", "rolling_total_hour_usd", "measured_total_hour_usd", "modeled_total_hour_usd"])
        if not opportunity_history_df.empty:
            for col in ["rolling_total_hour_usd", "measured_total_hour_usd", "modeled_total_hour_usd", "modeled_only_hour_usd"]:
                if col in opportunity_history_df.columns:
                    opportunity_history_df[col] = opportunity_history_df[col].map(lambda x: _f(x, 0.0))
        lane_alerts = _compute_lane_alerts(opportunity_df, opportunity_history_df)
        institutional_scorecard = load_json(INSTITUTIONAL_SCORECARD_FILE, {})
    else:
        opportunity_df = pd.DataFrame(
            columns=[
                "sector",
                "rolling_hour_usd",
                "measured_hour_usd",
                "modeled_hour_usd",
                "modeled_only_hour_usd",
                "measured_sources",
                "measured_truth_rows",
                "confidence_lane",
                "value_basis",
            ]
        )
        opportunity_summary = {
            "sectors": 0,
            "rolling_total_hour_usd": 0.0,
            "measured_total_hour_usd": 0.0,
            "modeled_total_hour_usd": 0.0,
            "modeled_only_hour_usd": 0.0,
            "top_sector": "n/a",
        }
        opportunity_history_df = pd.DataFrame(columns=["timestamp_utc", "rolling_total_hour_usd", "measured_total_hour_usd", "modeled_total_hour_usd"])
        lane_alerts = {"generated_utc": now_utc(), "critical_count": 0, "warning_count": 0, "total_alerts": 0, "alerts": []}
        institutional_scorecard = {}

    live_engine_heartbeat = load_json(LIVE_ENGINE_HEARTBEAT_FILE, {})

    return {
        "report": report,
        "portfolio": portfolio,
        "audit": audit,
        "allocator": allocator,
        "regime": regime,
        "event": event,
        "seed": seed,
        "equity": equity,
        "cash": cash,
        "gross": gross,
        "ret": ret,
        "equity_curve": equity_curve,
        "concentration": concentration,
        "candidate_df": candidate_df,
        "frontier_df": frontier_df,
        "ledger_df": ledger_df,
        "hash_df": hash_df,
        "regime_history_df": regime_history_df,
        "opportunity_df": opportunity_df,
        "opportunity_summary": opportunity_summary,
        "opportunity_history_df": opportunity_history_df,
        "lane_alerts": lane_alerts,
        "live_engine_heartbeat": live_engine_heartbeat,
        "institutional_scorecard": institutional_scorecard,
    }


def _record_regime_snapshot(data: dict, snapshot_key: str) -> None:
    report = data.get("report", {})
    audit = data.get("audit", {})
    regime = data.get("regime", {})
    append_jsonl(
        REGIME_HISTORY_FILE,
        {
            "timestamp_utc": now_utc(),
            "snapshot_key": snapshot_key,
            "report_generated_utc": str(report.get("generated_utc", "n/a")),
            "cycle": audit.get("cycle"),
            "regime": str(regime.get("regime", "n/a")),
            "realized_vol_pct": _f(regime.get("realized_vol_pct"), 0.0),
            "breadth_pos_pct24": _f(regime.get("breadth_pos_pct24"), 0.0),
            "heat_multiplier": _f(regime.get("heat_multiplier"), 0.0),
            "risk_aversion_multiplier": _f(regime.get("risk_aversion_multiplier"), 0.0),
            "confidence_multiplier": _f(regime.get("confidence_multiplier"), 0.0),
        },
    )


def _record_opportunity_snapshot(data: dict, snapshot_key: str) -> None:
    summary = data.get("opportunity_summary", {})
    top_rows = []
    df = data.get("opportunity_df")
    if isinstance(df, pd.DataFrame) and not df.empty:
        top_rows = df.to_dict(orient="records")
    append_jsonl(
        OPPORTUNITY_HISTORY_FILE,
        {
            "timestamp_utc": now_utc(),
            "snapshot_key": snapshot_key,
            "rolling_total_hour_usd": round(_f(summary.get("rolling_total_hour_usd"), 0.0), 2),
            "measured_total_hour_usd": round(_f(summary.get("measured_total_hour_usd"), 0.0), 2),
            "modeled_total_hour_usd": round(_f(summary.get("modeled_total_hour_usd"), 0.0), 2),
            "modeled_only_hour_usd": round(_f(summary.get("modeled_only_hour_usd"), 0.0), 2),
            "top_sector": str(summary.get("top_sector", "n/a")),
            "sectors": int(_f(summary.get("sectors"), 0.0)),
            "top_rows": top_rows,
        },
    )


def _set_metric_value(pane: pn.pane.HTML, value: str) -> None:
    pane.object = f"<div style='font-size:42px;font-weight:700;color:#f6f2e8'>{value}</div>"


def _metric_card(title: str, note: str) -> tuple[pn.Column, pn.pane.HTML]:
    value_pane = pn.pane.HTML("<div style='font-size:42px;font-weight:700;color:#f6f2e8'>--</div>")
    card = pn.Column(
        pn.pane.Markdown(f"### {title}"),
        value_pane,
        pn.pane.Markdown(note),
        styles={
            "background": "rgba(16,21,29,0.82)",
            "border": "1px solid rgba(222,203,166,0.16)",
            "border-radius": "18px",
            "padding": "16px",
        },
    )
    return card, value_pane


def _build_template(include_cross_sector: bool) -> tuple[pn.template.FastListTemplate, dict]:
    seed_card, seed_value = _metric_card("Seed Capital", "Reset-aware base capital.")
    equity_card, equity_value = _metric_card("Equity", "Marked portfolio equity.")
    cash_card, cash_value = _metric_card("Cash", "Undeployed reserve.")
    return_card, return_value = _metric_card("Return Since Seed", "Compounded marked return.")

    equity_plot = pn.pane.Plotly(go.Figure(), config={"displayModeBar": False}, sizing_mode="stretch_width")
    concentration_plot = pn.pane.Plotly(go.Figure(), config={"displayModeBar": False}, sizing_mode="stretch_width")
    frontier_plot = pn.pane.Plotly(go.Figure(), config={"displayModeBar": False}, sizing_mode="stretch_width")
    regime_history_plot = pn.pane.Plotly(go.Figure(), config={"displayModeBar": False}, sizing_mode="stretch_width")
    opportunity_plot = pn.pane.Plotly(go.Figure(), config={"displayModeBar": False}, sizing_mode="stretch_width")
    opportunity_history_plot = pn.pane.Plotly(go.Figure(), config={"displayModeBar": False}, sizing_mode="stretch_width")

    command_status = pn.pane.Markdown("### Command Status")
    hero_banner = pn.pane.HTML("<div class='investor-hero'><h2>Institutional Optimization Command Center</h2></div>")
    investor_signal = pn.pane.Markdown("### Investor Signal\nNarrative loading...")
    proof_surface = pn.pane.Markdown("### Proof Surface\nValidation loading...")
    optimization_live = pn.pane.HTML("<div style='border:1px solid rgba(126,172,214,0.28);border-radius:12px;padding:10px 12px;background:rgba(8,14,22,0.76)'>Live optimization telemetry initializing...</div>")
    alert_banner = pn.pane.HTML("<div class='alert-banner alert-clean'>Initializing risk lane telemetry...</div>")
    opportunity_marquee = pn.pane.HTML("<div class='marquee-wrap'><div class='marquee-track'><span>Loading sector lanes...</span></div></div>")
    pdf_link = pn.pane.Markdown("")
    optimizer_table = pn.pane.DataFrame(pd.DataFrame(columns=["metric", "value"]), index=False)
    concentration_status = pn.pane.Markdown("")
    regime_table = pn.pane.DataFrame(pd.DataFrame(columns=["metric", "value"]), index=False)
    regime_rationale = pn.pane.Markdown("")
    opportunity_status = pn.pane.Markdown("")
    scorecard_summary = pn.pane.Markdown("### Institutional Readiness\nLoading scorecard...")
    scorecard_table = pn.pane.DataFrame(pd.DataFrame(columns=["metric", "value"]), index=False, sizing_mode="stretch_width")
    candidates_table = pn.pane.DataFrame(pd.DataFrame(columns=["symbol", "hybrid_score", "pct24", "quote_volume"]), index=False, sizing_mode="stretch_width")
    opportunity_table = pn.pane.DataFrame(
        pd.DataFrame(columns=["sector", "rolling_hour_usd", "measured_hour_usd", "modeled_hour_usd", "confidence_lane", "value_basis"]),
        index=False,
        sizing_mode="stretch_width",
    )
    orchestrator_table = pn.pane.DataFrame(pd.DataFrame(columns=["metric", "value"]), index=False, sizing_mode="stretch_width")
    ledger_table = pn.pane.DataFrame(pd.DataFrame(columns=["timestamp_utc", "side", "symbol", "notional_usd", "pnl_usd"]), index=False, sizing_mode="stretch_width")
    hash_table = pn.pane.DataFrame(pd.DataFrame(columns=["path", "sha256"]), index=False, sizing_mode="stretch_width")
    generated_info = pn.pane.Markdown("**Generated**: n/a")
    scored_info = pn.pane.Markdown("**Scored Symbols**: n/a")
    positions_info = pn.pane.Markdown("**Positions Open**: n/a")
    gross_info = pn.pane.Markdown("**Gross Exposure**: n/a")
    top_symbol_info = pn.pane.Markdown("**Top Symbol**: none")
    refresh_info = pn.pane.Markdown("**Last Refresh**: pending")

    overview = pn.Column(
        hero_banner,
        pn.Row(seed_card, equity_card, cash_card, return_card),
        pn.Row(
            equity_plot,
            pn.Column(
                command_status,
                investor_signal,
                proof_surface,
                optimization_live,
                alert_banner,
                opportunity_marquee,
                pdf_link,
                styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
            ),
        ),
    )

    allocator_panel = pn.Row(
        pn.Column(
            pn.pane.Markdown("### Optimizer Controls"),
            optimizer_table,
            styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
        ),
        pn.Column(
            concentration_plot,
            concentration_status,
            styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
        ),
    )

    regime_panel = pn.Row(
        pn.Column(
            pn.pane.Markdown("### Regime Controller"),
            regime_table,
            regime_rationale,
            styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
        ),
        pn.Column(
            pn.pane.Markdown("### Top Candidates"),
            candidates_table,
            styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
        ),
    )

    analytics_panel = pn.Row(
        pn.Column(
            frontier_plot,
            styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
        ),
        pn.Column(
            regime_history_plot,
            styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
        ),
    )

    opportunity_panel = pn.Row(
        pn.Column(
            opportunity_plot,
            opportunity_status,
            styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
        ),
        pn.Column(
            pn.pane.Markdown("### Sector Confidence Lanes"),
            scorecard_summary,
            scorecard_table,
            opportunity_table,
            opportunity_history_plot,
            styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
        ),
    )

    execution_panel = pn.Row(
        pn.Column(pn.pane.Markdown("### Recent Execution Trail"), ledger_table, styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"}),
        pn.Column(
            pn.pane.Markdown("### Execution Orchestrator Telemetry"),
            orchestrator_table,
            pn.pane.Markdown("### Chain Of Custody"),
            hash_table,
            styles={"background": "rgba(16,21,29,0.82)", "border": "1px solid rgba(222,203,166,0.16)", "border-radius": "18px", "padding": "16px"},
        ),
    )

    main_panels = [overview, allocator_panel, regime_panel, analytics_panel, execution_panel]
    if include_cross_sector:
        main_panels.insert(4, opportunity_panel)

    template = pn.template.FastListTemplate(
        title="Nobel Tier Institutional Crypto Deck",
        accent_base_color="#d5b26d",
        header_background="#121722",
        theme_toggle=False,
        main=main_panels,
        sidebar=[
            pn.pane.Markdown("## Nobel Tier Institutional Command Deck"),
            generated_info,
            scored_info,
            positions_info,
            gross_info,
            top_symbol_info,
            refresh_info,
        ],
    )
    template.config.raw_css.append(INVESTOR_THEME_CSS)
    refs = {
        "seed_value": seed_value,
        "equity_value": equity_value,
        "cash_value": cash_value,
        "return_value": return_value,
        "equity_plot": equity_plot,
        "hero_banner": hero_banner,
        "investor_signal": investor_signal,
        "proof_surface": proof_surface,
        "optimization_live": optimization_live,
        "optimization_live_state": {},
        "alert_banner": alert_banner,
        "opportunity_marquee": opportunity_marquee,
        "command_status": command_status,
        "pdf_link": pdf_link,
        "optimizer_table": optimizer_table,
        "concentration_plot": concentration_plot,
        "concentration_status": concentration_status,
        "regime_table": regime_table,
        "regime_rationale": regime_rationale,
        "opportunity_plot": opportunity_plot,
        "opportunity_history_plot": opportunity_history_plot,
        "opportunity_status": opportunity_status,
        "scorecard_summary": scorecard_summary,
        "scorecard_table": scorecard_table,
        "opportunity_table": opportunity_table,
        "orchestrator_table": orchestrator_table,
        "candidates_table": candidates_table,
        "frontier_plot": frontier_plot,
        "regime_history_plot": regime_history_plot,
        "ledger_table": ledger_table,
        "hash_table": hash_table,
        "generated_info": generated_info,
        "scored_info": scored_info,
        "positions_info": positions_info,
        "gross_info": gross_info,
        "top_symbol_info": top_symbol_info,
        "refresh_info": refresh_info,
    }
    return template, refs


def _apply_dashboard_data(refs: dict, data: dict, refresh_label: str, include_cross_sector: bool) -> None:
    report = data["report"]
    portfolio = data["portfolio"]
    audit = data["audit"]
    allocator = data["allocator"]
    regime = data["regime"]
    event = data["event"]
    concentration = data["concentration"]
    orch = data.get("live_engine_heartbeat", {}) if isinstance(data.get("live_engine_heartbeat", {}), dict) else {}
    orch_status = str(orch.get("status", "unknown")).upper()
    orch_symbol = str(orch.get("symbol", "n/a"))
    orch_stream_brief = str(orch.get("stream_brief", "n/a"))

    _set_metric_value(refs["seed_value"], _fmt_usd(data["seed"]))
    _set_metric_value(refs["equity_value"], _fmt_usd(data["equity"]))
    _set_metric_value(refs["cash_value"], _fmt_usd(data["cash"]))
    _set_metric_value(refs["return_value"], _fmt_pct(data["ret"]))
    refs["equity_plot"].object = _equity_figure(data["seed"], data["equity_curve"])
    refs["command_status"].object = (
        "### Command Status\n"
        f"**Profile**: {report.get('profile', 'n/a')}  \n"
        f"**Regime**: {audit.get('regime', 'n/a')}  \n"
        f"**Last Action**: {event.get('action', 'HOLD')} {event.get('symbol', '')}  \n"
        f"**Execution Orchestrator**: {orch_status} ({orch_symbol})  \n"
        f"**Live Stream**: {orch_stream_brief}"
    )
    refs["pdf_link"].object = f"**PDF Brief**: [{PDF_BRIEF_FILE.name}](../out/execution/{PDF_BRIEF_FILE.name})"
    refs["optimizer_table"].object = pd.DataFrame([
        {"metric": "Allocator Mode", "value": allocator.get("mode", "n/a")},
        {"metric": "Optimizer Status", "value": allocator.get("optimizer_status", "n/a")},
        {"metric": "Solver", "value": allocator.get("optimizer_solver", "n/a")},
        {"metric": "Max Single Position", "value": _fmt_pct(_f(allocator.get("max_single_position_pct"), 0.0))},
        {"metric": "Max Gross Heat", "value": _fmt_pct(_f(allocator.get("max_gross_heat_pct"), 0.0))},
        {"metric": "Target Position Vol", "value": _fmt_pct(_f(allocator.get("target_position_vol_pct"), 0.0))},
        {"metric": "Available Heat", "value": _fmt_pct(_f(allocator.get("available_heat_pct"), 0.0))},
    ])
    refs["concentration_plot"].object = _concentration_figure(concentration.get("weights", []))
    refs["concentration_status"].object = (
        f"**Concentration Level**: {concentration.get('risk_level', 'LOW')}  \n"
        f"{concentration.get('risk_warning', '')}"
    )
    refs["regime_table"].object = pd.DataFrame([
        {"metric": "Regime", "value": regime.get("regime", "n/a")},
        {"metric": "Breadth Positive 24h", "value": _fmt_pct(_f(regime.get("breadth_pos_pct24"), 0.0))},
        {"metric": "Realized Vol", "value": _fmt_pct(_f(regime.get("realized_vol_pct"), 0.0))},
        {"metric": "ARCH Vol", "value": _fmt_pct(_f(regime.get("arch_vol_pct"), 0.0))},
        {"metric": "Heat Multiplier", "value": f"{_f(regime.get('heat_multiplier'), 0.0):.2f}"},
        {"metric": "Risk Aversion Multiplier", "value": f"{_f(regime.get('risk_aversion_multiplier'), 0.0):.2f}"},
    ])
    refs["regime_rationale"].object = f"**Rationale**: {regime.get('rationale', 'n/a')}"
    refs["candidates_table"].object = data["candidate_df"]
    refs["frontier_plot"].object = _frontier_figure(data["frontier_df"])
    refs["regime_history_plot"].object = _regime_history_figure(data["regime_history_df"])
    refs["opportunity_plot"].object = _sector_opportunity_figure(data["opportunity_df"])
    refs["opportunity_history_plot"].object = _opportunity_history_figure(data["opportunity_history_df"])
    opp_summary = data["opportunity_summary"]
    lane_alerts = data.get("lane_alerts", {})
    scorecard = data.get("institutional_scorecard", {}) if isinstance(data.get("institutional_scorecard", {}), dict) else {}
    top_lane = "LOW"
    opp_df = data["opportunity_df"]
    if not opp_df.empty and "confidence_lane" in opp_df.columns:
        top_lane = str(opp_df.iloc[0].get("confidence_lane", "LOW"))

    if include_cross_sector:
        hero_html = (
            "<div class='investor-hero'>"
            "<h2 style='margin:0 0 6px 0'>Institutional Optimization Command Center</h2>"
            "<div style='font-size:14px;opacity:0.9'>Measured execution intelligence, sector-scale opportunity translation, and audit-grade continuity proof.</div>"
            "<div class='hero-kpis'>"
            f"<div class='hero-kpi'><div class='hero-kpi-label'>Rolling $/hr</div><div class='hero-kpi-value'>{_fmt_usd(_f(opp_summary.get('rolling_total_hour_usd'), 0.0))}</div></div>"
            f"<div class='hero-kpi'><div class='hero-kpi-label'>Measured $/hr</div><div class='hero-kpi-value'>{_fmt_usd(_f(opp_summary.get('measured_total_hour_usd'), 0.0))}</div></div>"
            f"<div class='hero-kpi'><div class='hero-kpi-label'>Top Sector</div><div class='hero-kpi-value'>{opp_summary.get('top_sector', 'n/a')}</div></div>"
            f"<div class='hero-kpi'><div class='hero-kpi-label'>Lane Posture</div><div class='hero-kpi-value'>{top_lane}</div></div>"
            "</div>"
            f"<span class='lane-badge {_lane_css_class(top_lane)}'>Confidence Lane: {top_lane}</span>"
            "</div>"
        )
    else:
        hero_html = (
            "<div class='investor-hero'>"
            "<h2 style='margin:0 0 6px 0'>Trading Master Command Center</h2>"
            "<div style='font-size:14px;opacity:0.9'>Trading-only surface. Cross-sector intelligence is intentionally isolated.</div>"
            "<div class='hero-kpis'>"
            f"<div class='hero-kpi'><div class='hero-kpi-label'>Equity</div><div class='hero-kpi-value'>{_fmt_usd(data['equity'])}</div></div>"
            f"<div class='hero-kpi'><div class='hero-kpi-label'>Return</div><div class='hero-kpi-value'>{_fmt_pct(data['ret'])}</div></div>"
            f"<div class='hero-kpi'><div class='hero-kpi-label'>Scored</div><div class='hero-kpi-value'>{audit.get('scored_count', 'n/a')}</div></div>"
            f"<div class='hero-kpi'><div class='hero-kpi-label'>Open Positions</div><div class='hero-kpi-value'>{portfolio.get('positions_open', 'n/a')}</div></div>"
            "</div>"
            "<span class='lane-badge lane-high'>Mode: TRADING_ONLY</span>"
            "</div>"
        )
    refs["hero_banner"].object = hero_html

    readiness_tier = str(scorecard.get("readiness_tier", "UNKNOWN")).upper()
    readiness_score = _f(scorecard.get("readiness_score"), 0.0)
    roi_pct = _f(scorecard.get("trading_kpis", {}).get("realized_roi_pct"), 0.0)
    win_rate_pct = _f(scorecard.get("trading_kpis", {}).get("win_rate_pct"), 0.0)
    source_coverage = scorecard.get("source_coverage", {}) if isinstance(scorecard.get("source_coverage", {}), dict) else {}
    research_kpis = scorecard.get("research_kpis", {}) if isinstance(scorecard.get("research_kpis", {}), dict) else {}
    combined_sources = int(_f(source_coverage.get("combined_approved_sources"), 0.0))
    key_backed_sources = int(_f(source_coverage.get("enabled_sources"), 0.0))
    open_access_sources = int(_f(source_coverage.get("open_access_approved_sources"), 0.0))
    measured_pct = _f(source_coverage.get("measurement_pct"), 0.0)
    top_test_sharpe = _f(research_kpis.get("top_test_sharpe"), 0.0)
    top_walkforward_sharpe = _f(research_kpis.get("top_walkforward_sharpe_mean"), 0.0)
    champion_flow = str(research_kpis.get("champion_flow", "n/a"))
    champion_strategy = str(research_kpis.get("champion_strategy", "n/a"))
    champion_algo = str(research_kpis.get("champion_algo", "n/a"))
    if include_cross_sector:
        refs["investor_signal"].object = (
            "### Investor Signal\n"
            f"**System Readout**: {_fmt_usd(_f(opp_summary.get('rolling_total_hour_usd'), 0.0))}/hr rolling opportunity with "
            f"{_fmt_usd(_f(opp_summary.get('measured_total_hour_usd'), 0.0))}/hr from measured lanes.  \n"
            f"**Institutional Readiness**: {readiness_tier} ({readiness_score:,.2f}) | ROI {roi_pct:,.2f}% | Win Rate {win_rate_pct:,.2f}%"
        )
        refs["proof_surface"].object = (
            "### Proof Surface\n"
            f"**Breadth Proven Now**: {combined_sources} approved sources live in registry ({key_backed_sources} key-backed + {open_access_sources} open-access).  \n"
            f"**Measurement Coverage**: {measured_pct:,.2f}% of enabled tracked sources are measured in the scorecard.  \n"
            f"**Validation Readout**: top test Sharpe {top_test_sharpe:,.2f} | top walk-forward mean Sharpe {top_walkforward_sharpe:,.2f}.  \n"
            f"**Current Champion**: {champion_flow} -> {champion_strategy} -> {champion_algo}."
        )
    else:
        refs["investor_signal"].object = (
            "### Investor Signal\n"
            f"**Trading Readout**: Equity {_fmt_usd(data['equity'])}, cash {_fmt_usd(data['cash'])}, return {_fmt_pct(data['ret'])}.  \n"
            f"**Execution Health**: regime {audit.get('regime', 'n/a')} | scored {audit.get('scored_count', 'n/a')} symbols | orchestrator {orch_status}."
        )
        refs["proof_surface"].object = (
            "### Proof Surface\n"
            f"**Recent Execution**: {len(data['ledger_df'])} latest ledger rows on surface.  \n"
            f"**Hash Coverage**: {len(data['hash_df'])} hash entries loaded.  \n"
            "**Boundary**: Cross-sector opportunity and infrastructure intelligence are not rendered in this dashboard mode."
        )
    refs["optimization_live_state"] = _compute_optimization_live_state(data)
    refs["optimization_live"].object = _render_optimization_live_html(refs["optimization_live_state"])

    crit = int(_f(lane_alerts.get("critical_count"), 0.0))
    warn = int(_f(lane_alerts.get("warning_count"), 0.0))
    if include_cross_sector:
        if crit > 0:
            refs["alert_banner"].object = f"<div class='alert-banner alert-critical'>Critical lane pressure: {crit} critical / {warn} warning alerts.</div>"
        elif warn > 0:
            refs["alert_banner"].object = f"<div class='alert-banner alert-watch'>Watchlist active: {warn} warning alerts across sector lanes.</div>"
        else:
            refs["alert_banner"].object = "<div class='alert-banner alert-clean'>All lanes clean. No critical or warning pressure detected.</div>"
    else:
        refs["alert_banner"].object = "<div class='alert-banner alert-clean'>Trading-only mode active. Cross-sector telemetry routed to separate dashboards.</div>"

    marquee_items = []
    if include_cross_sector:
        if not opp_df.empty:
            for row in opp_df.head(8).to_dict(orient="records"):
                marquee_items.append(
                    f"<span>{row.get('sector', 'n/a').upper()} | {_fmt_usd(_f(row.get('rolling_hour_usd'), 0.0))}/hr | lane {row.get('confidence_lane', 'LOW')}</span>"
                )
        if not marquee_items:
            marquee_items = ["<span>Opportunity feed initializing...</span>"]
    else:
        if not data["candidate_df"].empty:
            for row in data["candidate_df"].head(8).to_dict(orient="records"):
                marquee_items.append(
                    f"<span>{row.get('symbol', 'n/a')} | hybrid {_f(row.get('hybrid_score'), 0.0):.4f} | pct24 {_fmt_pct(_f(row.get('pct24'), 0.0))}</span>"
                )
        if not marquee_items:
            marquee_items = ["<span>Trading candidate feed initializing...</span>"]
    repeated = "".join(marquee_items + marquee_items)
    refs["opportunity_marquee"].object = f"<div class='marquee-wrap'><div class='marquee-track'>{repeated}</div></div>"

    if include_cross_sector:
        refs["opportunity_status"].object = (
            f"**Rolling Total**: {_fmt_usd(_f(opp_summary.get('rolling_total_hour_usd'), 0.0))}/hr  \n"
            f"**Measured**: {_fmt_usd(_f(opp_summary.get('measured_total_hour_usd'), 0.0))}/hr  \n"
            f"**Modeled-only**: {_fmt_usd(_f(opp_summary.get('modeled_only_hour_usd'), 0.0))}/hr  \n"
            f"**Top Sector**: {opp_summary.get('top_sector', 'n/a')}  \n"
            f"**Lane Alerts**: {int(_f(lane_alerts.get('critical_count'), 0.0))} critical / {int(_f(lane_alerts.get('warning_count'), 0.0))} warning"
        )
    else:
        refs["opportunity_status"].object = "**Cross-sector panel disabled in trading-only mode.**"
    score_components = scorecard.get("score_components", {}) if isinstance(scorecard.get("score_components", {}), dict) else {}
    if include_cross_sector:
        refs["scorecard_summary"].object = (
            "### Institutional Readiness\n"
            f"**Tier**: {readiness_tier}  \n"
            f"**Score**: {readiness_score:,.2f}  \n"
            f"**Coverage**: {_f(scorecard.get('source_coverage', {}).get('measurement_pct'), 0.0):,.2f}% measured"
        )
        refs["scorecard_table"].object = pd.DataFrame([
            {"metric": "Coverage", "value": f"{_f(score_components.get('coverage'), 0.0):,.2f}"},
            {"metric": "Measurement", "value": f"{_f(score_components.get('measurement'), 0.0):,.2f}"},
            {"metric": "Walk-Forward", "value": f"{_f(score_components.get('walkforward'), 0.0):,.2f}"},
            {"metric": "Risk", "value": f"{_f(score_components.get('risk'), 0.0):,.2f}"},
            {"metric": "Operations", "value": f"{_f(score_components.get('ops'), 0.0):,.2f}"},
        ])
    else:
        refs["scorecard_summary"].object = "### Trading Readiness\n**Boundary**: cross-sector scoring is rendered in dedicated intel dashboards."
        refs["scorecard_table"].object = pd.DataFrame([
            {"metric": "Equity", "value": _fmt_usd(data["equity"])},
            {"metric": "Cash", "value": _fmt_usd(data["cash"])},
            {"metric": "Gross Exposure", "value": _fmt_usd(data["gross"])},
            {"metric": "Return", "value": _fmt_pct(data["ret"])},
            {"metric": "Scored Symbols", "value": str(audit.get("scored_count", "n/a"))},
        ])
    opportunity_cols = [
        "sector",
        "rolling_hour_usd",
        "measured_hour_usd",
        "modeled_hour_usd",
        "confidence_lane",
        "value_basis",
    ]
    refs["opportunity_table"].object = opp_df[opportunity_cols].head(OPPORTUNITY_TABLE_MAX_ROWS) if not opp_df.empty else opp_df
    refs["orchestrator_table"].object = pd.DataFrame(_orchestrator_status_rows(orch))
    refs["ledger_table"].object = data["ledger_df"]
    refs["hash_table"].object = data["hash_df"]
    refs["generated_info"].object = f"**Generated**: {report.get('generated_utc', 'n/a')}"
    refs["scored_info"].object = f"**Scored Symbols**: {audit.get('scored_count', 'n/a')}"
    refs["positions_info"].object = f"**Positions Open**: {portfolio.get('positions_open', 'n/a')}"
    refs["gross_info"].object = f"**Gross Exposure**: {_fmt_usd(data['gross'])}"
    refs["top_symbol_info"].object = f"**Top Symbol**: {concentration.get('max_symbol', 'none')}"
    refs["refresh_info"].object = f"**Last Refresh**: {refresh_label}"


def _write_heartbeat(mode: str, status: str, refresh_count: int, host: str | None = None, port: int | None = None, report_generated_utc: str | None = None, error: str | None = None) -> None:
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": now_utc(),
        "mode": mode,
        "status": status,
        "refresh_count": int(refresh_count),
        "host": host,
        "port": port,
        "report_generated_utc": report_generated_utc,
        "heartbeat_file": str(HEARTBEAT_FILE),
    }
    if error:
        payload["error"] = error
    HEARTBEAT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _start_background_heartbeat(host: str, port: int, refresh_seconds: float) -> None:
    interval_seconds = max(float(refresh_seconds), 5.0)

    def _runner() -> None:
        refresh_count = 0
        while True:
            try:
                report, _, _, _ = load_artifacts()
                refresh_count += 1
                _write_heartbeat(
                    mode="serve",
                    status="ok",
                    refresh_count=refresh_count,
                    host=host,
                    port=port,
                    report_generated_utc=str(report.get("generated_utc", "n/a")),
                )
            except Exception as exc:
                refresh_count += 1
                _write_heartbeat(mode="serve", status="error", refresh_count=refresh_count, host=host, port=port, error=str(exc))
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_runner, name="institutional-dashboard-heartbeat", daemon=True)
    thread.start()


def build_app(report: dict, hashes: dict, status: dict, ledger: list[dict], include_cross_sector: bool) -> pn.template.FastListTemplate:
    template, refs = _build_template(include_cross_sector=include_cross_sector)
    data = _dashboard_data(report, hashes, status, ledger, include_cross_sector=include_cross_sector)
    _apply_dashboard_data(refs, data, refresh_label=now_utc(), include_cross_sector=include_cross_sector)
    return template


def _build_live_app(host: str, port: int, refresh_seconds: float, include_cross_sector: bool):
    template, refs = _build_template(include_cross_sector=include_cross_sector)
    refresh_state = {"count": 0, "last_snapshot_key": "", "last_opportunity_key": ""}

    def refresh() -> None:
        try:
            report, hashes, status, ledger = load_artifacts()
            data = _dashboard_data(report, hashes, status, ledger, include_cross_sector=include_cross_sector)
            refresh_state["count"] += 1
            _apply_dashboard_data(refs, data, refresh_label=now_utc(), include_cross_sector=include_cross_sector)
            snapshot_key = f"{data['report'].get('generated_utc', 'n/a')}|{data['audit'].get('cycle', 'n/a')}|{data['regime'].get('regime', 'n/a')}"
            if snapshot_key != refresh_state["last_snapshot_key"]:
                _record_regime_snapshot(data, snapshot_key)
                refresh_state["last_snapshot_key"] = snapshot_key
            if include_cross_sector:
                opp_summary = data.get("opportunity_summary", {})
                opportunity_key = f"{snapshot_key}|{opp_summary.get('rolling_total_hour_usd', 0.0)}|{opp_summary.get('measured_total_hour_usd', 0.0)}"
                if opportunity_key != refresh_state["last_opportunity_key"]:
                    _write_opportunity_operating_pack(data, opportunity_key)
                    _record_opportunity_snapshot(data, opportunity_key)
                    refresh_state["last_opportunity_key"] = opportunity_key
            _write_heartbeat(
                mode="serve",
                status="ok",
                refresh_count=refresh_state["count"],
                host=host,
                port=port,
                report_generated_utc=str(report.get("generated_utc", "n/a")),
            )
        except Exception as exc:
            refresh_state["count"] += 1
            refs["refresh_info"].object = f"**Last Refresh**: error at {now_utc()}"
            _write_heartbeat(mode="serve", status="error", refresh_count=refresh_state["count"], host=host, port=port, error=str(exc))

    refresh()

    def tick_optimization_live() -> None:
        state = refs.get("optimization_live_state", {})
        if not isinstance(state, dict) or not state:
            return

        now_ts = time.time()
        last_ts = _f(state.get("last_tick_ts"), now_ts)
        elapsed = max(0.0, min(now_ts - last_ts, 2.5))

        phase = _f(state.get("pulse_phase"), 0.0) + elapsed
        base_gain = _f(state.get("base_gain_pct"), 0.0)
        base_better = _f(state.get("base_better_pct"), 0.0)
        slope_gain = _f(state.get("slope_gain_pct_per_sec"), 0.0)
        slope_better = _f(state.get("slope_better_pct_per_sec"), 0.0)

        current_gain = base_gain + (slope_gain * elapsed) + (0.08 * math.sin(phase * 1.8))
        current_better = base_better + (slope_better * elapsed) + (0.08 * math.cos(phase * 1.6))

        last_gain = _f(state.get("last_gain_pct"), current_gain)
        last_better = _f(state.get("last_better_pct"), current_better)
        gain_delta = current_gain - last_gain
        better_delta = current_better - last_better

        if gain_delta > 0.001:
            gain_direction = "UP"
        elif gain_delta < -0.001:
            gain_direction = "DOWN"
        else:
            gain_direction = "FLAT"

        if better_delta > 0.001:
            better_direction = "UP"
        elif better_delta < -0.001:
            better_direction = "DOWN"
        else:
            better_direction = "FLAT"

        state.update(
            {
                "pulse_phase": phase,
                "last_tick_ts": now_ts,
                "last_gain_pct": current_gain,
                "last_better_pct": current_better,
                "current_gain_pct": current_gain,
                "current_better_pct": current_better,
                "gain_direction": gain_direction,
                "better_direction": better_direction,
            }
        )
        refs["optimization_live"].object = _render_optimization_live_html(state)

    def _start_periodic() -> None:
        period_ms = max(int(float(refresh_seconds) * 1000.0), 5000)
        pn.state.add_periodic_callback(refresh, period=period_ms)
        pn.state.add_periodic_callback(tick_optimization_live, period=1000)

    pn.state.onload(_start_periodic)
    return template


def export_dashboard(include_cross_sector: bool) -> int:
    report, hashes, status, ledger = load_artifacts()
    DASH.mkdir(parents=True, exist_ok=True)
    app = build_app(report, hashes, status, ledger, include_cross_sector=include_cross_sector)
    app.save(str(HTML_OUT), resources="inline")
    data = _dashboard_data(report, hashes, status, ledger, include_cross_sector=include_cross_sector)
    snapshot_key = f"{data['report'].get('generated_utc', 'n/a')}|{data['audit'].get('cycle', 'n/a')}|{data['regime'].get('regime', 'n/a')}"
    _record_regime_snapshot(data, snapshot_key)
    if include_cross_sector:
        _write_opportunity_operating_pack(data, snapshot_key)
        _record_opportunity_snapshot(data, snapshot_key)
    _write_heartbeat(mode="export", status="ok", refresh_count=1, report_generated_utc=str(report.get("generated_utc", "n/a")))
    print(f"Wrote {HTML_OUT}")
    return 0


def serve_dashboard(host: str, port: int, autoreload: bool, refresh_seconds: float, include_cross_sector: bool) -> int:
    app_factory = lambda: _build_live_app(host, port, refresh_seconds, include_cross_sector=include_cross_sector)
    _write_heartbeat(mode="serve", status="starting", refresh_count=0, host=host, port=port)
    _start_background_heartbeat(host, port, refresh_seconds)
    print(f"Serving institutional crypto dashboard on http://{host}:{port}")
    pn.serve(
        {"/": app_factory},
        address=host,
        port=int(port),
        websocket_origin=[f"{host}:{port}", f"localhost:{port}", f"127.0.0.1:{port}"],
        show=False,
        autoreload=bool(autoreload),
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Institutional crypto Panel dashboard builder and live server")
    parser.add_argument("--mode", choices=["export", "serve"], default="export", help="Export HTML artifact or serve the Panel app live")
    parser.add_argument("--host", default="127.0.0.1", help="Host address used for serve mode")
    parser.add_argument("--port", type=int, default=5016, help="Port used for serve mode")
    parser.add_argument("--refresh-seconds", type=float, default=30.0, help="Refresh cadence for live serve mode")
    parser.add_argument("--autoreload", action="store_true", help="Enable Panel autoreload in serve mode")
    parser.add_argument("--include-cross-sector", action="store_true", help="Include cross-sector opportunity and institutional scorecard panels")
    args = parser.parse_args()

    if args.mode == "serve":
        return serve_dashboard(args.host, args.port, args.autoreload, args.refresh_seconds, include_cross_sector=bool(args.include_cross_sector))
    return export_dashboard(include_cross_sector=bool(args.include_cross_sector))


if __name__ == "__main__":
    raise SystemExit(main())
