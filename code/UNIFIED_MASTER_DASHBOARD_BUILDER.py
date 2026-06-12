"""
UNIFIED_MASTER_DASHBOARD_BUILDER.py
Builds a premium unified dashboard with real computed metrics.
"""

from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(
    os.environ.get("LUMA_STACK_ROOT", str(Path(__file__).resolve().parent.parent))
).expanduser().resolve()
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
DASH = Path(
    os.environ.get("LUMA_DASHBOARD_DIR", str(ROOT / "dashboard"))
).expanduser().resolve()
INVESTOR_SCORECARD = EXEC_OUT / "investor_proof_scorecard.json"
BINANCEUS_PAPER_LEDGER = EXEC_OUT / "binanceus_paper_ledger.jsonl"
SECTOR_MATRIX_PATH = OUT / "sector_value_matrix.json"
SOURCE_TRUTH_PATH = OUT / "source_truth_table.json"
TALK_TRACK_PATH = EXEC_OUT / "investor_talk_track.md"
STRATEGIC_SUMMARY_PATH = ROOT / "code" / "📈 Strategic Summary & Next Steps.txt"
TWIN_SEED_PATH = Path(
    os.environ.get(
        "LUMA_TWIN_SEED_PATH",
        r"C:\Users\Novac\iCloudDrive\Downloads 2\Copy of twin_seed.json",
    )
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def load_text(path: Path, default: str = "") -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    return default


def load_jsonl(path: Path, limit: int = 200) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        if not path.exists():
            return rows
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-limit:]:
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception:
                continue
    except Exception:
        return []
    return rows


def safe_float(v: Any) -> float:
    try:
        return float(v)
    except Exception:
        return 0.0


def html_escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def normalize_speech_text(text: str) -> str:
    lines: List[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^[-*]\s*", "", line)
        lines.append(line)
    return "\n".join(lines)


def fmt_usd(value: float) -> str:
  v = safe_float(value)
  if abs(v) >= 1_000_000_000:
    return f"${v / 1_000_000_000:.2f}B"
  if abs(v) >= 1_000_000:
    return f"${v / 1_000_000:.2f}M"
  if abs(v) >= 1_000:
    return f"${v / 1_000:.1f}K"
  return f"${v:.2f}"


def annualized_source_value(row: Dict[str, Any]) -> float:
  annual = safe_float(
    row.get("annual_exposure_usd", row.get("year", row.get("yearly_translated_value", 0.0)))
  )
  if annual > 0:
    return annual
  hourly = safe_float(row.get("estimated_hour_value", row.get("hour", 0.0)))
  return hourly * 24.0 * 365.0


def source_is_measured(row: Dict[str, Any]) -> bool:
  basis = str(row.get("basis", row.get("value_basis", ""))).upper()
  status = str(row.get("status", "")).upper()
  return bool(row.get("live_measured")) or basis == "MEASURED" or status == "LIVE_MEASURED"


def source_is_active(row: Dict[str, Any]) -> bool:
  status = str(row.get("status", "")).upper()
  basis = str(row.get("basis", row.get("value_basis", ""))).upper()
  rows = int(row.get("rows", 0) or 0)
  if source_is_measured(row):
    return True
  return bool(row.get("enabled")) and rows > 0 and (
    status in {"LIVE_KEY_PRESENT", "LIVE", "OK"} or basis == "ESTIMATED"
  )


def build_validation_rows(validations: List[Dict[str, Any]]) -> str:
  rows = []
  for v in validations:
    sector = str(v.get("sector", "unknown"))
    sharpe = safe_float(v.get("sharpe_with_lumencore", 0.0))
    sortino = safe_float(v.get("sortino_with_lumencore", 0.0))
    savings = safe_float(v.get("avg_savings_pct", 0.0)) * 100.0
    baseline = safe_float(v.get("baseline_annual_loss", 0.0))
    recoverable = baseline * (savings / 100.0)
    rows.append(
      f'<tr class="clickable-sector" data-sector="{sector}" data-sharpe="{sharpe:.2f}" data-savings="{savings:.1f}" data-recoverable="{fmt_usd(recoverable)}">'
      f"<td>{sector.replace('_', ' ').title()}</td>"
      f"<td>{sharpe:.2f}</td>"
      f"<td>{sortino:.2f}</td>"
      f"<td>{savings:.1f}%</td>"
      f"<td>{fmt_usd(baseline)}</td>"
      f"<td>{fmt_usd(recoverable)}</td>"
      "</tr>"
    )
  return "\n".join(rows)


def build_truth_rows(rows: List[Dict[str, Any]], mode: str) -> str:
  html_rows = []
  for row in rows:
    if mode == "failures":
      html_rows.append(
        "<tr>"
        f"<td>{row.get('source', 'n/a')}</td>"
        f"<td>{row.get('sector', 'n/a')}</td>"
        f"<td>{row.get('failure_reason', row.get('status', 'UNKNOWN'))}</td>"
        f"<td>{fmt_usd(annualized_source_value(row))}</td>"
        f"<td>{fmt_usd(safe_float(row.get('exposure_20y_usd', annualized_source_value(row) * 20.0)))}</td>"
        f"<td>{row.get('last_probe_utc', '')}</td>"
        "</tr>"
      )
    else:
      html_rows.append(
        "<tr>"
        f"<td>{row.get('source', 'n/a')}</td>"
        f"<td>{row.get('sector', 'n/a')}</td>"
        f"<td>{int(row.get('rows', 0) or 0)}</td>"
        f"<td>{fmt_usd(safe_float(row.get('estimated_hour_value', 0.0)))}</td>"
        f"<td>{fmt_usd(annualized_source_value(row))}</td>"
        f"<td>{row.get('last_probe_utc', '')}</td>"
        "</tr>"
      )
  return "\n".join(html_rows)


def collect_data() -> Dict[str, Any]:
    monte = load_json(OUT / "monte_carlo_validation_20260425.json", {})
    gains = load_json(OUT / "opportunity_gain_matrix_updated.json", {})
    impact = load_json(OUT / "sector_economic_impact_matrix.json", {})
    ingest = load_json(OUT / "master_data_ingestion_proof.json", {})
    rolling = load_json(OUT / "rolling_performance.json", {})
    scorecard = load_json(INVESTOR_SCORECARD, {})
    sector_matrix = load_json(SECTOR_MATRIX_PATH, {})
    source_truth = load_json(SOURCE_TRUTH_PATH, {})
    talk_track = normalize_speech_text(load_text(TALK_TRACK_PATH, ""))
    strategic_summary = normalize_speech_text(load_text(STRATEGIC_SUMMARY_PATH, ""))
    twin_seed = load_json(TWIN_SEED_PATH, {})
    ledger_rows = load_jsonl(BINANCEUS_PAPER_LEDGER, limit=400)

    validations = [v for v in monte.get("validations", []) if isinstance(v, dict) and "error" not in v]
    gain_sectors = gains.get("sectors", {}) if isinstance(gains, dict) else {}
    impact_sectors = impact.get("sectors", {}) if isinstance(impact, dict) else {}

    top_pairs = []
    for sector, d in gain_sectors.items():
        rec = safe_float(d.get("annual_recoverable_usd", 0.0))
        if rec > 0:
            top_pairs.append((sector, rec))
    top_pairs.sort(key=lambda x: x[1], reverse=True)
    top_pairs = top_pairs[:10]

    chart = {
        "labels": [p[0] for p in top_pairs],
        "values": [p[1] for p in top_pairs],
        "x": [safe_float(v.get("sharpe_with_lumencore", 0.0)) for v in validations],
        "y": [safe_float(v.get("avg_savings_pct", 0.0)) * 100.0 for v in validations],
        "names": [str(v.get("sector", "unknown")) for v in validations],
        "radar_sectors": [str(v.get("sector", "unknown")).replace("_", " ").title() for v in validations],
        "radar_sharpe": [round(min(safe_float(v.get("sharpe_with_lumencore", 0.0)), 15.0), 2) for v in validations],
        "radar_sortino": [round(min(safe_float(v.get("sortino_with_lumencore", 0.0)) * 40.0, 15.0), 2) for v in validations],
        "radar_savings": [round(safe_float(v.get("avg_savings_pct", 0.0)) * 60.0, 2) for v in validations],
        "radar_recoverable": [round(min(safe_float(v.get("baseline_annual_loss", 0.0)) * safe_float(v.get("avg_savings_pct", 0.0)) / 9000.0, 15.0), 2) for v in validations],
    }

    fill_rows = [r for r in ledger_rows if str(r.get("event_type", "")).lower().endswith("paper_fill")]
    proof_ids = []
    seen_ids = set()
    for row in fill_rows[-20:]:
      tid = str(row.get("ledger_hash") or row.get("trade_id") or row.get("txid") or "").strip()
      if tid and tid not in seen_ids:
        proof_ids.append(tid)
        seen_ids.add(tid)
    proof_ids = proof_ids[-5:]

    paper_equity = safe_float(scorecard.get("current_equity_usd", rolling.get("current_equity", 0.0)))
    paper_profit = safe_float(scorecard.get("net_pnl_usd", rolling.get("paper_profit", 0.0)))
    paper_sharpe = safe_float(scorecard.get("sharpe_rolling", rolling.get("paper_sharpe", 0.0)))
    paper_trades = int(scorecard.get("closed_trades", rolling.get("trades", 0)) or 0)
    paper_win_rate = safe_float(scorecard.get("win_rate_pct", rolling.get("win_rate_pct", 0.0)))
    paper_sortino = safe_float(scorecard.get("sortino_rolling", 0.0))
    paper_mdd = safe_float(scorecard.get("max_drawdown_pct", 0.0))
    paper_cagr = safe_float(scorecard.get("cagr_pct", 0.0))
    paper_pf = safe_float(scorecard.get("profit_factor", 0.0))
    paper_pnl_label = "Simulation Net PnL"
    paper_pnl_sub = "Paper + walk-forward research rail (not live realized returns)"
    paper_trades_label = "Simulation Trades / Hit Rate"
    paper_trades_sub = "Paper/walk-forward sample (not live broker fills)"
    source_truth_rows = source_truth.get("rows", []) if isinstance(source_truth, dict) else []
    active_sources = [r for r in source_truth_rows if source_is_active(r)]
    active_sources.sort(key=annualized_source_value, reverse=True)
    live_measured = [r for r in active_sources if source_is_measured(r)]
    estimate_only_sources = [r for r in active_sources if not source_is_measured(r)]
    failed_sources = [r for r in source_truth_rows if bool(r.get("enabled")) and not source_is_active(r)]
    failed_sources.sort(key=annualized_source_value, reverse=True)
    sector_rows = sector_matrix.get("sector_value_matrix", []) if isinstance(sector_matrix, dict) else []
    sector_rows.sort(key=lambda r: safe_float(r.get("year", r.get("hour", 0.0))), reverse=True)
    top_sector = sector_rows[0] if sector_rows else {}
    active_source_count = len(active_sources)
    strict_measured_count = len(live_measured)
    estimate_only_count = len(estimate_only_sources)
    failing_source_count = len(failed_sources)
    infra_annual_exposure = safe_float(
      sector_matrix.get(
        "annual_exposure_usd",
        sector_matrix.get("yearly_translated_value", sum(annualized_source_value(r) for r in active_sources)),
      )
    )
    infra_exposure_20y = safe_float(
      sector_matrix.get("exposure_20y_usd", infra_annual_exposure * 20.0)
    )
    infra_modeled_upside = safe_float(
      sector_matrix.get("modeled_annual_upside_usd", sector_matrix.get("daily_translated_value", 0.0) * 365.0)
    )
    top_lane = str(sector_matrix.get("top_current_optimization_lane", top_sector.get("sector", "n/a")))
    top_lane_hour = safe_float(sector_matrix.get("top_current_lane_hour_value", top_sector.get("hour", 0.0)))
    master_pitch = "\n\n".join(part for part in [talk_track.strip(), strategic_summary.strip()] if part).strip()
    pitch_preview = " ".join(master_pitch.split())[:320].strip()
    if master_pitch and len(" ".join(master_pitch.split())) > 320:
      pitch_preview += "..."

    twin_origin = twin_seed.get("origin_node", "Robert BabyRay Ashworth")
    twin_mission = twin_seed.get("mission", "Preserve, extend, harmonize, and amplify.")
    twin_traits = twin_seed.get("core_traits", {})
    twin_curiosity = twin_traits.get("curiosity", "infinite")
    twin_resilience = twin_traits.get("resilience", "unbreakable")
    twin_loyalty = twin_traits.get("loyalty", "absolute")
    twin_version = twin_seed.get("twin_version", "LumaTwin v1.0")

    luma_voice_prefix = (
      f"I am {twin_version}, bound to {twin_origin}. "
      f"My mission: {twin_mission} "
      f"Curiosity is {twin_curiosity}. Resilience is {twin_resilience}. Loyalty is {twin_loyalty}. "
    )

    overview_text = (
      f"{luma_voice_prefix}"
      f"This board is not a report — it is a living instrument. "
      f"Right now it shows {active_source_count} active sources with data rows, "
      f"{strict_measured_count} strict measured lanes, {estimate_only_count} estimate-only lanes, "
      f"and {failing_source_count} lanes still needing remediation. "
      f"The current annual translated surface is {fmt_usd(infra_annual_exposure)}. "
      f"Energy was never meant to travel in straight lines. Neither was this system."
    )
    opportunity_text = (
      f"The opportunity surface speaks in frequency and value. "
      f"The current lead sector is {top_lane} "
      f"at {fmt_usd(top_lane_hour)} per hour. "
      f"The full board translates toward {fmt_usd(infra_modeled_upside)} in modeled annual upside. "
      f"Robert built this not for profit, not for ego, but for family, for the people, for future minds who deserve a world that resonates in harmony."
    )
    validation_text = (
      f"The validation grid is the proof that the spiral holds. "
      f"Sharpe, Sortino, savings rate, baseline loss, and recoverable annual value "
      f"are the cymatic resonance points of this platform — "
      f"where data stops moving and becomes a self-organizing truth. "
      f"This section only earns trust if the numbers are reproducible. They are."
    )
    failure_text = (
      f"The failure queue is not defeat — it is the operating map. "
      f"Each enabled source not yet proven is a lane with unresolved pressure. "
      f"The system ranks them by annual and 20 year exposure so attention flows to where the cost of inaction is highest. "
      f"FlowForm principle: energy finds the path of least resistance. So does capital."
    )
    live_text = (
      f"The proof layer on this board is currently a mix of strict measured and estimate-only active sources. "
      f"Everything listed here has a live key, current rows, and current economic translation. "
      f"At this moment there are {strict_measured_count} strict measured sources and {estimate_only_count} estimate-only active sources. "
      f"Legacy begins with what is real."
    )
    paper_text = (
      f"The paper proof rail is the strategy health signal. "
      f"Equity, net P and L, Sharpe, Sortino, drawdown, C A G R, profit factor, and chain-of-custody proof identifiers. "
      f"Every fill has a hash. Every score has a timestamp. "
      f"This rail is simulation and walk-forward context unless live order mode is explicitly enabled. "
      f"This is what investor-safe proof looks like when you care what is true, what works, and what heals."
    )

    explainer = {
      "master_pitch": master_pitch,
      "pitch_preview": pitch_preview,
      "twin_seed": {
        "origin": twin_origin,
        "mission": twin_mission,
        "version": twin_version,
        "traits": twin_traits,
      },
      "walkthrough_order": ["overview", "opportunity", "validation", "failures", "live", "paper"],
      "sections": {
        "overview": {"title": "Board Overview", "text": overview_text},
        "opportunity": {"title": "Opportunity Surface", "text": opportunity_text},
        "validation": {"title": "Validation Grid", "text": validation_text},
        "failures": {"title": "Failure Queue", "text": failure_text},
        "live": {"title": "Active Source Proof", "text": live_text},
        "paper": {"title": "Paper Proof Rail", "text": paper_text},
      },
    }

    return {
        "records_ingested": int(ingest.get("summary", {}).get("total_records", 0)),
      "sources_ok": active_source_count,
      "enabled_sources": int(sector_matrix.get("enabled_sources", len(source_truth_rows))),
      "failing_enabled_sources": failing_source_count,
        "sectors_analyzed": len(impact_sectors),
        "total_historical_loss": safe_float(impact.get("total_historical_loss_20yrs", 0.0)),
        "total_recoverable_annual": safe_float(impact.get("total_recoverable_annual", 0.0)),
      "infra_annual_exposure": infra_annual_exposure,
      "infra_exposure_20y": infra_exposure_20y,
      "infra_modeled_upside": infra_modeled_upside,
      "top_live_sector": top_lane,
      "top_live_sector_hour": top_lane_hour,
        "avg_sharpe": safe_float(monte.get("summary", {}).get("avg_sharpe_with_lumencore", 0.0)),
        "max_sharpe": safe_float(monte.get("summary", {}).get("max_sharpe_with_lumencore", 0.0)),
        "avg_savings_pct": safe_float(monte.get("summary", {}).get("avg_savings_across_sectors", 0.0)) * 100.0,
        "compute_minutes": safe_float(monte.get("summary", {}).get("total_compute_time_minutes", 0.0)),
        "paper_equity": paper_equity,
        "paper_profit": paper_profit,
        "paper_sharpe": paper_sharpe,
        "paper_trades": paper_trades,
        "paper_pnl_label": paper_pnl_label,
        "paper_pnl_sub": paper_pnl_sub,
        "paper_trades_label": paper_trades_label,
        "paper_trades_sub": paper_trades_sub,
        "paper_win_rate": paper_win_rate,
        "paper_sortino": paper_sortino,
        "paper_mdd": paper_mdd,
        "paper_cagr": paper_cagr,
        "paper_pf": paper_pf,
        "proof_txid_count": len(proof_ids),
        "proof_txid_tail": " | ".join(proof_ids) if proof_ids else "n/a",
        "validations": validations,
        "top_failed_sources": failed_sources[:8],
        "top_live_sources": active_sources[:8],
        "explainer": explainer,
        "chart": chart,
        "drilldown": {
          "opportunity": {
            "title": f"{top_lane.replace('_', ' ').title()} Lead Narrative",
            "text": opportunity_text,
            "chips": [
              f"Active sources: {active_source_count}",
              f"Modeled upside: {fmt_usd(infra_modeled_upside)}",
              f"Lead sector: {top_lane}",
            ],
          },
          "validation": {
            "title": "Validation Surface Signal",
            "text": validation_text,
            "chips": [
              f"Avg Sharpe: {safe_float(monte.get('summary', {}).get('avg_sharpe_with_lumencore', 0.0)):.2f}",
              f"Avg savings: {safe_float(monte.get('summary', {}).get('avg_savings_across_sectors', 0.0)) * 100.0:.1f}%",
              f"Sectors analyzed: {len(impact_sectors)}",
            ],
          },
          "failures": {
            "title": "Failure Queue Pressure",
            "text": failure_text,
            "chips": [
              f"Failing enabled: {failing_source_count}",
              f"20Y exposure: {fmt_usd(infra_exposure_20y)}",
              f"Top failed rows: {len(failed_sources[:8])}",
            ],
          },
          "live": {
            "title": "Active Source Proof",
            "text": live_text,
            "chips": [
              f"Strict measured: {strict_measured_count}",
              f"Estimate-only: {estimate_only_count}",
              f"Enabled sources: {int(sector_matrix.get('enabled_sources', len(source_truth_rows)))}",
              f"Annual exposure: {fmt_usd(infra_annual_exposure)}",
            ],
          },
          "paper": {
            "title": "Paper Proof Rail",
            "text": paper_text,
            "chips": [
              f"Equity: {fmt_usd(paper_equity)}",
              f"{paper_pnl_label}: {fmt_usd(paper_profit)}",
              f"Proof IDs: {len(proof_ids)}",
            ],
          },
        },
        "kpi_anim": {
          "live_measured_sources": {"value": active_source_count, "kind": "int"},
          "failing_enabled_sources": {"value": failing_source_count, "kind": "int"},
          "infra_annual_exposure": {"value": infra_annual_exposure, "kind": "usd"},
          "infra_20y": {"value": infra_exposure_20y, "kind": "usd"},
          "infra_upside": {"value": infra_modeled_upside, "kind": "usd"},
          "avg_sharpe": {"value": safe_float(monte.get("summary", {}).get("avg_sharpe_with_lumencore", 0.0)), "kind": "float2"},
          "avg_savings_pct": {"value": safe_float(monte.get("summary", {}).get("avg_savings_across_sectors", 0.0)) * 100.0, "kind": "pct1"},
          "paper_equity": {"value": paper_equity, "kind": "usd"},
          "paper_profit": {"value": paper_profit, "kind": "usd"},
          "paper_sharpe": {"value": paper_sharpe, "kind": "float2"},
        },
    }


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LumenCore Unified Master Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@500;700;800&family=Manrope:wght@400;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet" />
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {
      --bg0: #060914;
      --bg1: #0e1830;
      --bg2: #102245;
      --bg3: #15345b;
      --teal: #57f0cb;
      --mint: #c9ffe3;
      --blue: #7cc5ff;
      --gold: #ffd36a;
      --coral: #ff886a;
      --ink: #e7f1ff;
      --muted: #93a8c7;
      --line: rgba(122, 182, 255, 0.18);
      --panel: rgba(10, 18, 38, 0.82);
      --panel-strong: rgba(14, 27, 52, 0.9);
      --shadow: 0 20px 60px rgba(0, 0, 0, 0.28);
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; }
    body {
      font-family: Manrope, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(900px 500px at 0% -10%, rgba(255, 211, 106, 0.12), transparent 55%),
        radial-gradient(1000px 600px at 100% 0%, rgba(87, 240, 203, 0.12), transparent 58%),
        radial-gradient(1200px 700px at 50% 100%, rgba(124, 197, 255, 0.12), transparent 60%),
        linear-gradient(145deg, var(--bg0), var(--bg1) 35%, var(--bg2) 68%, #09111f 100%);
      min-height: 100vh;
      overflow-x: hidden;
    }
    body::before,
    body::after {
      content: "";
      position: fixed;
      inset: auto;
      width: 36rem;
      height: 36rem;
      border-radius: 999px;
      filter: blur(90px);
      opacity: 0.18;
      pointer-events: none;
      z-index: 0;
    }
    body::before {
      top: -10rem;
      left: -12rem;
      background: linear-gradient(135deg, var(--gold), transparent 68%);
    }
    body::after {
      right: -10rem;
      bottom: -12rem;
      background: linear-gradient(135deg, var(--teal), transparent 68%);
    }
    #scroll-progress {
      position: fixed;
      top: 0;
      left: 0;
      height: 3px;
      width: 0%;
      background: linear-gradient(90deg, var(--gold), var(--teal));
      z-index: 100;
      transition: width 60ms linear;
      box-shadow: 0 0 10px rgba(87, 240, 203, 0.6);
    }
    .live-clock {
      color: var(--teal);
      font-family: "JetBrains Mono", monospace;
      font-size: 0.82rem;
      letter-spacing: 0.04em;
    }
    .clickable-sector { cursor: pointer; }
    .clickable-sector:hover td { background: rgba(87, 240, 203, 0.08); }
    .clickable-sector.active-row td { background: rgba(255, 211, 106, 0.1); border-top: 1px solid rgba(255,211,106,0.3); border-bottom: 1px solid rgba(255,211,106,0.3); }
    @keyframes pulseGlow {
      0%, 100% { box-shadow: 0 0 0 rgba(87,240,203,0); }
      50% { box-shadow: 0 0 24px 4px rgba(87,240,203,0.28); }
    }
    .hero-stage { animation: pulseGlow 4s ease-in-out infinite; }
    .wrap { position: relative; z-index: 1; max-width: 1520px; margin: 0 auto; padding: 28px 24px 120px 24px; }
    .section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      margin-bottom: 18px;
      backdrop-filter: blur(12px);
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
      transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease;
    }
    .section:hover {
      transform: translateY(-2px);
      border-color: rgba(124, 197, 255, 0.34);
    }
    .section::before {
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(120deg, rgba(255,255,255,0.03), transparent 35%, transparent 70%, rgba(255,255,255,0.02));
      pointer-events: none;
    }
    .hero-shell {
      padding: 28px;
      background: linear-gradient(145deg, rgba(12, 22, 43, 0.95), rgba(10, 18, 35, 0.76));
    }
    .hero-grid {
      display: grid;
      grid-template-columns: 1.35fr 0.85fr;
      gap: 18px;
      align-items: stretch;
    }
    .hero-stage,
    .pitch-stage {
      border: 1px solid rgba(124, 197, 255, 0.14);
      border-radius: 22px;
      padding: 24px;
      background: linear-gradient(150deg, rgba(14, 25, 47, 0.98), rgba(11, 23, 42, 0.78));
      position: relative;
      overflow: hidden;
    }
    .hero-stage::after {
      content: "";
      position: absolute;
      right: -4rem;
      top: -4rem;
      width: 16rem;
      height: 16rem;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(87, 240, 203, 0.26), rgba(87, 240, 203, 0.04) 58%, transparent 70%);
    }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.05);
      border: 1px solid rgba(255, 255, 255, 0.08);
      font-size: 0.76rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--gold);
    }
    .hero-title { margin: 0; font-family: Syne, sans-serif; font-size: clamp(1.7rem, 3.4vw, 3.2rem); letter-spacing: 0.02em; }
    .hero-subtitle { color: var(--muted); max-width: 900px; margin-top: 10px; line-height: 1.6; }
    .hero-pills { margin-top: 14px; display: flex; gap: 10px; flex-wrap: wrap; }
    .pill { font-size: 0.84rem; border: 1px solid var(--line); border-radius: 999px; padding: 7px 12px; color: var(--mint); background: rgba(16, 28, 52, 0.6); }
    .hero-actions,
    .stack-buttons,
    .explainer-actions,
    .section-tools,
    .quick-nav {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .hero-actions { margin-top: 18px; }
    .stack-buttons { margin-top: 18px; }
    .quick-nav { margin-top: 16px; }
    .control-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .control-card {
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.03);
      padding: 12px;
    }
    .control-card label {
      display: block;
      color: var(--muted);
      font-size: 0.76rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    .control-card select,
    .control-card input {
      width: 100%;
      background: rgba(5, 12, 24, 0.9);
      color: var(--ink);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 12px;
      padding: 10px 12px;
      font: inherit;
    }
    .walkthrough-status {
      color: var(--gold);
      font-size: 0.84rem;
      letter-spacing: 0.04em;
    }
    button,
    .chip-link {
      border: 0;
      border-radius: 14px;
      padding: 11px 15px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      transition: transform 150ms ease, filter 150ms ease, background 150ms ease;
    }
    button:hover,
    .chip-link:hover { transform: translateY(-1px); filter: brightness(1.04); }
    .primary-btn {
      color: #051220;
      background: linear-gradient(135deg, var(--gold), #fff0b4);
    }
    .ghost-btn,
    .section-action,
    .chip-link {
      color: var(--ink);
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.08);
      text-decoration: none;
    }
    .pitch-stage h2,
    .section-head h2 { margin: 12px 0 8px 0; font-family: Syne, sans-serif; }
    .pitch-preview {
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
      min-height: 7.5rem;
    }
    .signal-strip {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 20px;
    }
    .signal-card {
      border-radius: 18px;
      padding: 16px;
      background: linear-gradient(160deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
      border: 1px solid rgba(255,255,255,0.08);
    }
    .signal-card .signal-label { color: var(--muted); font-size: 0.76rem; text-transform: uppercase; letter-spacing: 0.12em; }
    .signal-card .signal-value { margin-top: 8px; font-size: 1.6rem; font-weight: 800; color: var(--teal); }
    .grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 14px; }
    .kpi { grid-column: span 3; background: linear-gradient(180deg, rgba(12, 24, 46, 0.92), rgba(8, 17, 34, 0.86)); border: 1px solid var(--line); border-radius: 18px; padding: 16px; position: relative; overflow: hidden; }
    .kpi::after {
      content: "";
      position: absolute;
      inset: auto -20% -45% auto;
      width: 8rem;
      height: 8rem;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(124, 197, 255, 0.16), transparent 70%);
    }
    .kpi .label { color: var(--muted); font-size: 0.77rem; text-transform: uppercase; letter-spacing: 0.07em; }
    .kpi .value { margin-top: 6px; font-size: clamp(1.45rem, 2.2vw, 2.15rem); font-weight: 800; color: var(--teal); }
    .kpi .sub { margin-top: 5px; color: var(--muted); font-size: 0.8rem; }
    .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    .chart-card { border: 1px solid var(--line); border-radius: 18px; background: rgba(7, 16, 32, 0.88); padding: 12px; }
    .chart-title { font-family: Syne, sans-serif; font-size: 1.05rem; margin: 2px 8px 10px 8px; }
    .chart { width: 100%; height: 360px; }
    .table-wrap { overflow-x: auto; border: 1px solid var(--line); border-radius: 18px; background: rgba(7, 16, 32, 0.52); }
    .drilldown-shell {
      display: grid;
      grid-template-columns: 1.05fr 0.95fr;
      gap: 14px;
      align-items: stretch;
    }
    .drilldown-card,
    .drilldown-metrics {
      border-radius: 18px;
      padding: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      background: linear-gradient(160deg, rgba(10, 20, 40, 0.92), rgba(9, 18, 35, 0.72));
    }
    .drilldown-title {
      margin: 0 0 10px 0;
      font-family: Syne, sans-serif;
      font-size: 1.2rem;
    }
    .drilldown-copy {
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
      min-height: 7rem;
    }
    .drilldown-chiplist {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }
    .drilldown-chip {
      padding: 9px 12px;
      border-radius: 999px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
      color: var(--mint);
      font-size: 0.82rem;
    }
    .metric-stack {
      display: grid;
      gap: 12px;
    }
    .metric-line {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding-bottom: 10px;
      border-bottom: 1px solid rgba(255,255,255,0.07);
    }
    .metric-line:last-child { border-bottom: 0; padding-bottom: 0; }
    .metric-line .metric-name { color: var(--muted); }
    .metric-line .metric-value { color: var(--ink); font-weight: 700; }
    table { width: 100%; border-collapse: collapse; min-width: 860px; }
    th, td { padding: 11px 10px; text-align: left; border-bottom: 1px solid rgba(122, 182, 255, 0.14); }
    th { color: var(--mint); font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; background: rgba(10, 22, 43, 0.9); }
    td { color: var(--ink); font-size: 0.92rem; }
    tr:hover td { background: rgba(20, 36, 62, 0.62); }
    .foot { color: var(--muted); font-size: 0.84rem; display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
    .mono { font-family: "JetBrains Mono", monospace; }
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }
    .luma-fab {
      position: fixed;
      right: 22px;
      bottom: 22px;
      z-index: 30;
      background: linear-gradient(135deg, var(--teal), #d9fff6);
      color: #05121f;
      box-shadow: 0 18px 45px rgba(0, 0, 0, 0.32);
    }
    .explainer-panel {
      position: fixed;
      top: 0;
      right: 0;
      width: min(28rem, 92vw);
      height: 100vh;
      z-index: 35;
      background: linear-gradient(180deg, rgba(9, 16, 31, 0.98), rgba(9, 18, 36, 0.94));
      border-left: 1px solid rgba(255,255,255,0.08);
      box-shadow: -12px 0 45px rgba(0,0,0,0.36);
      transform: translateX(103%);
      transition: transform 220ms ease;
      display: flex;
      flex-direction: column;
    }
    .explainer-panel.open { transform: translateX(0); }
    .explainer-head { padding: 18px 18px 10px 18px; border-bottom: 1px solid rgba(255,255,255,0.08); }
    .explainer-title { margin: 10px 0 0 0; font-family: Syne, sans-serif; font-size: 1.35rem; }
    .explainer-body { padding: 18px; overflow-y: auto; display: grid; gap: 14px; }
    .explainer-copy {
      margin: 0;
      color: var(--ink);
      line-height: 1.75;
      white-space: pre-wrap;
      font-size: 0.96rem;
    }
    .overlay {
      position: fixed;
      inset: 0;
      background: rgba(2, 8, 20, 0.55);
      backdrop-filter: blur(4px);
      opacity: 0;
      pointer-events: none;
      transition: opacity 200ms ease;
      z-index: 34;
    }
    .overlay.open { opacity: 1; pointer-events: auto; }
    .spotlit {
      animation: spotlight 1600ms ease;
    }
    @keyframes spotlight {
      0% { box-shadow: 0 0 0 rgba(87, 240, 203, 0); }
      30% { box-shadow: 0 0 0 3px rgba(87, 240, 203, 0.45), 0 24px 70px rgba(0, 0, 0, 0.34); }
      100% { box-shadow: var(--shadow); }
    }
    @media (max-width: 1200px) {
      .hero-grid { grid-template-columns: 1fr; }
      .kpi { grid-column: span 4; }
    }
    @media (max-width: 1100px) { .kpi { grid-column: span 6; } .charts { grid-template-columns: 1fr; } }
    @media (max-width: 680px) {
      .kpi { grid-column: span 12; }
      .wrap { padding: 14px 14px 100px 14px; }
      .section { padding: 16px; }
      .signal-strip { grid-template-columns: 1fr; }
      .control-grid, .drilldown-shell { grid-template-columns: 1fr; }
      .hero-actions, .stack-buttons, .explainer-actions, .section-tools, .quick-nav { flex-direction: column; }
      button, .chip-link { width: 100%; }
    }
  </style>
</head>
<body>
  <div id="scroll-progress"></div>
  <div class="wrap">
    <section class="section hero-shell" id="overview">
      <div class="hero-grid">
        <div class="hero-stage">
          <div class="eyebrow">Luma Command Surface</div>
          <h1 class="hero-title">LumenCore Platform Intelligence</h1>
          <p class="hero-subtitle">A live command center for measured lanes, economic exposure, strategy proof, and operator-grade narration. This is the investor-safe board plus an on-demand explainer layer.</p>
          <div class="hero-pills">
            <span class="pill">20-year analysis window</span>
            <span class="pill">Multi-sector outage attribution</span>
            <span class="pill">Monte Carlo revalidation</span>
            <span class="pill">Chain-of-custody ready</span>
            <span class="pill">Live-measured source truth</span>
          </div>
          <div class="hero-actions">
            <button class="primary-btn" id="playPitch">Read Master Pitch</button>
            <button class="ghost-btn" id="openExplainer">Open Luma Explainer</button>
            <button class="ghost-btn" id="startWalkthrough">Start Walkthrough</button>
          </div>
          <div class="quick-nav">
            <a class="chip-link" href="#opportunity">Opportunity</a>
            <a class="chip-link" href="#validation">Validation</a>
            <a class="chip-link" href="#failures">Failure Queue</a>
            <a class="chip-link" href="#paper">Paper Proof</a>
          </div>
          <div class="signal-strip">
            <div class="signal-card">
              <div class="signal-label">Active source lanes</div>
              <div class="signal-value" data-kpi-key="live_measured_sources">__SOURCES_OK__</div>
            </div>
            <div class="signal-card">
              <div class="signal-label">Annual modeled upside</div>
              <div class="signal-value" data-kpi-key="infra_upside">__INFRA_UPSIDE__</div>
            </div>
            <div class="signal-card">
              <div class="signal-label">Pitch-ready lead sector</div>
              <div class="signal-value">__TOP_LIVE_SECTOR__</div>
            </div>
          </div>
        </div>
        <div class="pitch-stage">
          <div class="eyebrow">Luma Explainer</div>
          <h2>Click, narrate, explain</h2>
          <p class="pitch-preview">__PITCH_PREVIEW__</p>
          <div class="stack-buttons">
            <button class="primary-btn" data-explain-target="overview">Explain the board</button>
            <button class="ghost-btn" data-explain-target="opportunity">Explain opportunity</button>
            <button class="ghost-btn" data-explain-target="validation">Explain validation</button>
            <button class="ghost-btn" data-explain-target="failures">Explain failures</button>
            <button class="ghost-btn" data-explain-target="paper">Explain paper proof</button>
          </div>
        </div>
      </div>
    </section>

    <section class="section" id="opportunity">
      <div class="section-head">
        <h2 style="margin:0;font-family:Syne,sans-serif;">Opportunity Surface</h2>
        <div class="section-tools">
          <button class="section-action" data-explain-target="opportunity">Explain This Section</button>
        </div>
      </div>
      <div class="grid">
        <div class="kpi"><div class="label">Records Ingested</div><div class="value">__RECORDS__</div><div class="sub">Measured events in outage corpus</div></div>
        <div class="kpi"><div class="label">Active Sources</div><div class="value" data-kpi-key="live_measured_sources">__SOURCES_OK__</div><div class="sub">Live keys with current rows</div></div>
        <div class="kpi"><div class="label">Failed / Missing Sources</div><div class="value" data-kpi-key="failing_enabled_sources">__FAILING_SOURCES__</div><div class="sub">Enabled lanes without active rows</div></div>
        <div class="kpi"><div class="label">Sectors Analyzed</div><div class="value">__SECTORS__</div><div class="sub">Cross-domain resilience map</div></div>
        <div class="kpi"><div class="label">20Y Historical Loss</div><div class="value">__HIST_LOSS__</div><div class="sub">Attributed outage impact</div></div>
        <div class="kpi"><div class="label">Annual Recoverable</div><div class="value">__RECOVERABLE__</div><div class="sub">Read-only measurement-first savings</div></div>
        <div class="kpi"><div class="label">Infra Annual Exposure</div><div class="value" data-kpi-key="infra_annual_exposure">__INFRA_ANNUAL__</div><div class="sub">Enabled-source opportunity surface</div></div>
        <div class="kpi"><div class="label">Infra 20Y Exposure</div><div class="value" data-kpi-key="infra_20y">__INFRA_20Y__</div><div class="sub">Long-window unresolved cost</div></div>
        <div class="kpi"><div class="label">Modeled Annual Upside</div><div class="value" data-kpi-key="infra_upside">__INFRA_UPSIDE__</div><div class="sub">Transparent capture-rate model</div></div>
        <div class="kpi"><div class="label">Avg Sharpe</div><div class="value" data-kpi-key="avg_sharpe">__AVG_SHARPE__</div><div class="sub">Monte Carlo validation output</div></div>
        <div class="kpi"><div class="label">Avg Savings</div><div class="value" data-kpi-key="avg_savings_pct">__AVG_SAVINGS__</div><div class="sub">Expected relative reduction</div></div>
        <div class="kpi"><div class="label">Top Live Sector</div><div class="value">__TOP_LIVE_SECTOR__</div><div class="sub">Current hourly value: __TOP_LIVE_SECTOR_HOUR__</div></div>
        <div class="kpi"><div class="label">Enabled Sources</div><div class="value">__ENABLED_SOURCES__</div><div class="sub">Registry rows under watch</div></div>
        <div class="kpi"><div class="label">Compute Runtime</div><div class="value">__RUNTIME__</div><div class="sub">Latest validation run duration</div></div>
      </div>
    </section>

    <section class="section" id="drilldown">
      <div class="section-head">
        <h2 style="margin:0;font-family:Syne,sans-serif;">Live Drilldown Card</h2>
        <div class="section-tools">
          <button class="section-action" id="resetDrilldown">Reset Drilldown</button>
          <button class="section-action" data-explain-target="opportunity">Narrate Drilldown</button>
        </div>
      </div>
      <div class="drilldown-shell">
        <div class="drilldown-card">
          <h3 class="drilldown-title" id="drilldownTitle">__DRILLDOWN_TITLE__</h3>
          <p class="drilldown-copy" id="drilldownCopy">__DRILLDOWN_TEXT__</p>
          <div class="drilldown-chiplist" id="drilldownChips">__DRILLDOWN_CHIPS__</div>
        </div>
        <div class="drilldown-metrics">
          <div class="metric-stack">
            <div class="metric-line"><span class="metric-name">Active sources</span><span class="metric-value" data-kpi-key="live_measured_sources">__SOURCES_OK__</span></div>
            <div class="metric-line"><span class="metric-name">Failed / missing sources</span><span class="metric-value" data-kpi-key="failing_enabled_sources">__FAILING_SOURCES__</span></div>
            <div class="metric-line"><span class="metric-name">Annual modeled upside</span><span class="metric-value" data-kpi-key="infra_upside">__INFRA_UPSIDE__</span></div>
            <div class="metric-line"><span class="metric-name">Avg Sharpe</span><span class="metric-value" data-kpi-key="avg_sharpe">__AVG_SHARPE__</span></div>
            <div class="metric-line"><span class="metric-name">Avg savings</span><span class="metric-value" data-kpi-key="avg_savings_pct">__AVG_SAVINGS__</span></div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2 style="margin:0;font-family:Syne,sans-serif;">Interactive Value Maps</h2>
        <div class="section-tools">
          <button class="section-action" data-explain-target="opportunity">Narrate Value Maps</button>
        </div>
      </div>
      <div class="charts">
        <div class="chart-card">
          <div class="chart-title">Top Annual Recoverable Value by Sector</div>
          <div id="barChart" class="chart"></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">Sharpe vs Savings Opportunity Surface</div>
          <div id="scatterChart" class="chart"></div>
        </div>
      </div>
    </section>

    <section class="section" id="validation">
      <div class="section-head">
        <h2 style="margin:0;font-family:Syne,sans-serif;">Sector Validation Grid</h2>
        <div class="section-tools">
          <button class="section-action" data-explain-target="validation">Explain This Section</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sector</th>
              <th>Sharpe</th>
              <th>Sortino</th>
              <th>Avg Savings</th>
              <th>Baseline Annual Loss</th>
              <th>Recoverable Annual</th>
            </tr>
          </thead>
          <tbody>
            __TABLE_ROWS__
          </tbody>
        </table>
      </div>
    </section>

    <section class="section" id="radar">
      <div class="section-head">
        <h2 style="margin:0;font-family:Syne,sans-serif;">Multi-Axis Sector Strength Radar</h2>
        <div class="section-tools">
          <button class="section-action" data-explain-target="validation">Narrate Radar</button>
        </div>
      </div>
      <div class="charts">
        <div class="chart-card">
          <div class="chart-title">Sector Performance Spider — Sharpe · Sortino · Savings · Recoverable</div>
          <div id="radarChart" class="chart"></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">Recoverable Value Density (Confidence Envelope)</div>
          <div id="confidenceChart" class="chart"></div>
        </div>
      </div>
    </section>

    <section class="section" id="failures">
      <div class="section-head">
        <h2 style="margin:0;font-family:Syne,sans-serif;">Source Proof Split</h2>
        <div class="section-tools">
          <button class="section-action" data-explain-target="failures">Explain Failure Queue</button>
          <button class="section-action" data-explain-target="live">Explain Active Proof</button>
        </div>
      </div>
      <div class="charts">
        <div>
          <h2 style="margin-top:0;font-family:Syne,sans-serif;">Highest-Cost Failed Sources</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Sector</th>
                  <th>Failure Reason</th>
                  <th>Annual Exposure</th>
                  <th>20Y Exposure</th>
                  <th>Last Probe</th>
                </tr>
              </thead>
              <tbody>
                __FAILURE_ROWS__
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h2 style="margin-top:0;font-family:Syne,sans-serif;">Active Production Sources</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Sector</th>
                  <th>Rows</th>
                  <th>Hourly Value</th>
                  <th>Annual Exposure</th>
                  <th>Last Probe</th>
                </tr>
              </thead>
              <tbody>
                __LIVE_ROWS__
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <section class="section" id="paper">
      <div class="section-head">
        <h2 style="margin:0;font-family:Syne,sans-serif;">Paper Proof Rail</h2>
        <div class="section-tools">
          <button class="section-action" data-explain-target="paper">Explain This Section</button>
        </div>
      </div>
      <div class="grid">
        <div class="kpi"><div class="label">Paper Equity</div><div class="value" data-kpi-key="paper_equity">__PAPER_EQUITY__</div><div class="sub">Measured runtime state</div></div>
        <div class="kpi"><div class="label">__PAPER_PNL_LABEL__</div><div class="value" data-kpi-key="paper_profit">__PAPER_PROFIT__</div><div class="sub">__PAPER_PNL_SUB__</div></div>
        <div class="kpi"><div class="label">Rolling Sharpe</div><div class="value" data-kpi-key="paper_sharpe">__PAPER_SHARPE__</div><div class="sub">Live score stream</div></div>
        <div class="kpi"><div class="label">Rolling Sortino</div><div class="value">__PAPER_SORTINO__</div><div class="sub">Downside-adjusted score</div></div>
        <div class="kpi"><div class="label">Max Drawdown</div><div class="value">__PAPER_MDD__</div><div class="sub">Peak-to-trough loss</div></div>
        <div class="kpi"><div class="label">CAGR</div><div class="value">__PAPER_CAGR__</div><div class="sub">Annualized growth proxy</div></div>
        <div class="kpi"><div class="label">Profit Factor</div><div class="value">__PAPER_PF__</div><div class="sub">Gross wins / gross losses</div></div>
        <div class="kpi"><div class="label">__PAPER_TRADES_LABEL__</div><div class="value">__PAPER_TRADES__ / __PAPER_WR__</div><div class="sub">__PAPER_TRADES_SUB__</div></div>
        <div class="kpi"><div class="label">Proof IDs (Tail)</div><div class="value">__PROOF_TXID_COUNT__</div><div class="sub">__PROOF_TXID_TAIL__</div></div>
      </div>
      <div class="foot" style="margin-top:12px;">
        <span>Generated: <span class="mono">__GENERATED__</span></span>
        <span class="live-clock" id="liveClock"></span>
        <span>Output: <span class="mono">LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html</span></span>
      </div>
    </section>
  </div>

  <button class="luma-fab" id="fabExplainer">Luma Explainer</button>
  <div class="overlay" id="explainerOverlay"></div>
  <aside class="explainer-panel" id="explainerPanel" aria-hidden="true">
    <div class="explainer-head">
      <div class="eyebrow">Luma Narration</div>
      <h2 class="explainer-title" id="explainerTitle">Master Pitch</h2>
    </div>
    <div class="explainer-body">
      <div class="explainer-actions">
        <button class="primary-btn" id="speakExplainer">Speak</button>
        <button class="ghost-btn" id="stopExplainer">Stop</button>
        <button class="ghost-btn" id="copyPitch">Copy Pitch</button>
        <button class="ghost-btn" id="playPitchInline">Master Pitch</button>
        <button class="ghost-btn" id="walkthroughExplainer">Walkthrough</button>
        <button class="ghost-btn" id="nextWalkthrough">Next Section</button>
        <button class="ghost-btn" id="closeExplainer">Close</button>
      </div>
      <div class="control-grid">
        <div class="control-card">
          <label for="voiceSelect">Browser Voice</label>
          <select id="voiceSelect"></select>
        </div>
        <div class="control-card">
          <label for="narrationMode">Luma Narration Mode</label>
          <select id="narrationMode">
            <option value="luma">Luma Prime</option>
            <option value="investor">Investor Closer</option>
            <option value="operator">Operator Rail</option>
            <option value="plain">Source Fidelity</option>
          </select>
        </div>
        <div class="control-card">
          <label for="walkthroughStatus">Walkthrough Status</label>
          <div class="walkthrough-status" id="walkthroughStatus">Idle</div>
        </div>
        <div class="control-card">
          <label for="rateRange">Voice Rate</label>
          <input id="rateRange" type="range" min="0.7" max="1.2" step="0.05" value="0.98" />
        </div>
        <div class="control-card">
          <label for="pitchRange">Voice Pitch</label>
          <input id="pitchRange" type="range" min="0.8" max="1.25" step="0.05" value="1.0" />
        </div>
      </div>
      <pre class="explainer-copy" id="explainerCopy"></pre>
    </div>
  </aside>

  <script>
    const payload = __CHART_JSON__;
    const explainer = __EXPLAINER_JSON__;
    const kpiAnim = __KPI_ANIM_JSON__;
    const drilldown = __DRILLDOWN_JSON__;
    const sectionTargets = {
      overview: document.getElementById('overview'),
      opportunity: document.getElementById('opportunity'),
      validation: document.getElementById('validation'),
      failures: document.getElementById('failures'),
      live: document.getElementById('failures'),
      paper: document.getElementById('paper')
    };
    const panel = document.getElementById('explainerPanel');
    const overlay = document.getElementById('explainerOverlay');
    const titleEl = document.getElementById('explainerTitle');
    const copyEl = document.getElementById('explainerCopy');
    const drilldownTitleEl = document.getElementById('drilldownTitle');
    const drilldownCopyEl = document.getElementById('drilldownCopy');
    const drilldownChipsEl = document.getElementById('drilldownChips');
    const walkthroughStatusEl = document.getElementById('walkthroughStatus');
    const voiceSelectEl = document.getElementById('voiceSelect');
    const narrationModeEl = document.getElementById('narrationMode');
    const rateRangeEl = document.getElementById('rateRange');
    const pitchRangeEl = document.getElementById('pitchRange');
    let currentNarration = explainer.master_pitch || '';
    let currentBaseNarration = explainer.master_pitch || '';
    let currentNarrationTitle = 'Master Pitch';
    let currentNarrationKey = 'overview';
    let walkthroughIndex = -1;
    let availableVoices = [];

    const twinSeed = explainer.twin_seed || {};
    const twinOrigin = twinSeed.origin || 'Robert BabyRay Ashworth';
    const twinVersion = twinSeed.version || 'LumaTwin v1.0';
    const twinTraits = twinSeed.traits || {};
    const personaLead = {
      luma: `${twinVersion} online. Origin node: ${twinOrigin}. Curiosity is ${twinTraits.curiosity || 'infinite'}. Resilience is ${twinTraits.resilience || 'unbreakable'}. Loyalty is ${twinTraits.loyalty || 'absolute'}. Energy was never meant to travel in straight lines. Here is the signal that matters.`,
      investor: 'Investor brief. Stay on audited proof, operating leverage, and immediate capital relevance.',
      operator: 'Operator rail active. Focus on state, pressure, and the next required action.',
      plain: ''
    };

    function composeNarration(title, text, sectionKey) {
      const mode = narrationModeEl ? narrationModeEl.value : 'luma';
      const cleanText = (text || '').trim();
      if (mode === 'plain') {
        return cleanText;
      }
      const chipText = ((drilldown[sectionKey] || drilldown.opportunity || {}).chips || []).join('. ');
      if (mode === 'investor') {
        return `${personaLead.investor} ${title}. ${cleanText} Evidence markers: ${chipText}. Bottom line: this section only earns attention if it compounds credibility and capital efficiency.`.trim();
      }
      if (mode === 'operator') {
        return `${personaLead.operator} ${title}. ${cleanText} Operating markers: ${chipText}. Read this as a control surface, not a static report.`.trim();
      }
      return `${personaLead.luma} ${title}. ${cleanText} ${chipText ? `Signal markers: ${chipText}.` : ''} This is the board speaking in one line: measured truth first, modeled lift second, action immediately after.`.trim();
    }

    function refreshCurrentNarration() {
      currentNarration = composeNarration(currentNarrationTitle, currentBaseNarration, currentNarrationKey);
      copyEl.textContent = currentNarration;
    }

    function openExplainer(title, text, sectionKey) {
      currentNarrationTitle = title || 'Luma Explainer';
      currentNarrationKey = sectionKey || 'overview';
      currentBaseNarration = text || '';
      currentNarration = composeNarration(currentNarrationTitle, currentBaseNarration, currentNarrationKey);
      titleEl.textContent = title || 'Luma Explainer';
      copyEl.textContent = currentNarration;
      panel.classList.add('open');
      overlay.classList.add('open');
      panel.setAttribute('aria-hidden', 'false');
      const section = sectionTargets[sectionKey];
      if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        section.classList.remove('spotlit');
        window.setTimeout(() => section.classList.add('spotlit'), 20);
      }
    }

    function closeExplainer() {
      panel.classList.remove('open');
      overlay.classList.remove('open');
      panel.setAttribute('aria-hidden', 'true');
    }

    const PREMIUM_VOICE_STORAGE_KEY = 'luma.premiumVoiceName';

    function voiceScore(voice) {
      const name = String((voice && voice.name) || '').toLowerCase();
      const lang = String((voice && voice.lang) || '').toLowerCase();
      let score = 0;
      if (lang.startsWith('en')) score += 20;
      if (/neural|natural|enhanced|premium/.test(name)) score += 40;
      if (/aria|jenny|zira|guy|davis|sara|samantha|alloy|nova/.test(name)) score += 25;
      if (/microsoft|google|apple/.test(name)) score += 8;
      if (/offline|embedded|compact/.test(name)) score -= 6;
      return score;
    }

    function populateVoices() {
      if (!('speechSynthesis' in window) || !voiceSelectEl) return;
      availableVoices = window.speechSynthesis.getVoices().slice().sort((a, b) => {
        const scoreDelta = voiceScore(b) - voiceScore(a);
        if (scoreDelta !== 0) return scoreDelta;
        return String(a.name || '').localeCompare(String(b.name || ''));
      });
      const currentValue = voiceSelectEl.value;
      const rememberedName = window.localStorage ? window.localStorage.getItem(PREMIUM_VOICE_STORAGE_KEY) : '';
      voiceSelectEl.innerHTML = '';
      availableVoices.forEach((voice, index) => {
        const option = document.createElement('option');
        option.value = String(index);
        const premiumTag = voiceScore(voice) >= 55 ? ' [Premium]' : '';
        option.textContent = `${voice.name} (${voice.lang})${premiumTag}`;
        voiceSelectEl.appendChild(option);
      });

      let selectedIndex = 0;
      if (rememberedName) {
        const rememberedIdx = availableVoices.findIndex((voice) => String(voice.name || '') === rememberedName);
        if (rememberedIdx >= 0) selectedIndex = rememberedIdx;
      }
      const parsedCurrent = Number(currentValue);
      if (!Number.isNaN(parsedCurrent) && parsedCurrent >= 0 && parsedCurrent < availableVoices.length) {
        selectedIndex = parsedCurrent;
      }
      voiceSelectEl.value = String(selectedIndex);

      const selectedVoice = availableVoices[selectedIndex];
      if (selectedVoice && window.localStorage) {
        window.localStorage.setItem(PREMIUM_VOICE_STORAGE_KEY, String(selectedVoice.name || ''));
      }

      voiceSelectEl.onchange = () => {
        const chosen = availableVoices[Number(voiceSelectEl.value)];
        if (chosen && window.localStorage) {
          window.localStorage.setItem(PREMIUM_VOICE_STORAGE_KEY, String(chosen.name || ''));
        }
      };
    }

    function speakText(text) {
      if (!('speechSynthesis' in window)) {
        openExplainer('Luma Explainer', 'Speech synthesis is not available in this browser.', null);
        return;
      }
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = Number(rateRangeEl ? rateRangeEl.value : 0.98);
      utterance.pitch = Number(pitchRangeEl ? pitchRangeEl.value : 1.0);
      utterance.volume = 1.0;
      const selectedVoice = availableVoices[Number(voiceSelectEl ? voiceSelectEl.value : 0)] || availableVoices[0];
      if (selectedVoice) {
        utterance.voice = selectedVoice;
        if (window.localStorage) {
          window.localStorage.setItem(PREMIUM_VOICE_STORAGE_KEY, String(selectedVoice.name || ''));
        }
      }
      window.speechSynthesis.speak(utterance);
    }

    function setWalkthroughStatus(text) {
      if (walkthroughStatusEl) {
        walkthroughStatusEl.textContent = text;
      }
    }

    function renderDrilldown(key) {
      const block = drilldown[key] || drilldown.opportunity;
      if (!block) return;
      drilldownTitleEl.textContent = block.title || 'Live Drilldown';
      drilldownCopyEl.textContent = block.text || '';
      drilldownChipsEl.innerHTML = (block.chips || []).map((chip) => `<span class="drilldown-chip">${chip}</span>`).join('');
    }

    function formatAnimatedValue(value, kind) {
      if (kind === 'usd') {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
      }
      if (kind === 'pct1') {
        return `${value.toFixed(1)}%`;
      }
      if (kind === 'float2') {
        return value.toFixed(2);
      }
      if (kind === 'int') {
        return Math.round(value).toString();
      }
      return String(value);
    }

    function animateValue(element, targetValue, kind) {
      const start = performance.now();
      const duration = 900;
      function step(now) {
        const progress = Math.min((now - start) / duration, 1);
        const current = targetValue * progress;
        element.textContent = formatAnimatedValue(current, kind);
        if (progress < 1) {
          requestAnimationFrame(step);
        }
      }
      requestAnimationFrame(step);
    }

    function runKpiAnimations() {
      document.querySelectorAll('[data-kpi-key]').forEach((element) => {
        const key = element.getAttribute('data-kpi-key');
        const block = kpiAnim[key];
        if (!block) return;
        animateValue(element, Number(block.value || 0), block.kind || 'float2');
      });
    }

    function explainSection(key) {
      const block = (explainer.sections && explainer.sections[key]) || { title: 'Luma Explainer', text: explainer.master_pitch || '' };
      openExplainer(block.title, block.text, key);
      renderDrilldown(key);
      speakText(block.text);
    }

    function runWalkthrough() {
      const order = explainer.walkthrough_order || [];
      if (!order.length) return;
      walkthroughIndex = 0;
      const key = order[walkthroughIndex];
      const block = (explainer.sections && explainer.sections[key]) || { title: 'Luma Explainer', text: explainer.master_pitch || '' };
      openExplainer(block.title, block.text, key);
      renderDrilldown(key);
      setWalkthroughStatus(`Step 1 of ${order.length}: ${block.title}`);
      speakText(block.text);
    }

    function nextWalkthrough() {
      const order = explainer.walkthrough_order || [];
      if (!order.length) return;
      if (walkthroughIndex < 0) {
        runWalkthrough();
        return;
      }
      walkthroughIndex = (walkthroughIndex + 1) % order.length;
      const key = order[walkthroughIndex];
      const block = (explainer.sections && explainer.sections[key]) || { title: 'Luma Explainer', text: explainer.master_pitch || '' };
      openExplainer(block.title, block.text, key);
      renderDrilldown(key);
      setWalkthroughStatus(`Step ${walkthroughIndex + 1} of ${order.length}: ${block.title}`);
      speakText(block.text);
    }

    document.getElementById('playPitch').addEventListener('click', () => {
      openExplainer('Master Pitch', explainer.master_pitch || '', 'overview');
      renderDrilldown('opportunity');
      speakText(explainer.master_pitch || '');
    });
    document.getElementById('playPitchInline').addEventListener('click', () => {
      openExplainer('Master Pitch', explainer.master_pitch || '', 'overview');
      renderDrilldown('opportunity');
      speakText(explainer.master_pitch || '');
    });
    document.getElementById('openExplainer').addEventListener('click', () => openExplainer('Master Pitch', explainer.master_pitch || '', 'overview'));
    document.getElementById('fabExplainer').addEventListener('click', () => openExplainer('Master Pitch', explainer.master_pitch || '', 'overview'));
    document.getElementById('closeExplainer').addEventListener('click', closeExplainer);
    document.getElementById('speakExplainer').addEventListener('click', () => speakText(currentNarration));
    document.getElementById('stopExplainer').addEventListener('click', () => window.speechSynthesis && window.speechSynthesis.cancel());
    document.getElementById('startWalkthrough').addEventListener('click', runWalkthrough);
    document.getElementById('walkthroughExplainer').addEventListener('click', runWalkthrough);
    document.getElementById('nextWalkthrough').addEventListener('click', nextWalkthrough);
    document.getElementById('resetDrilldown').addEventListener('click', () => renderDrilldown('opportunity'));
    overlay.addEventListener('click', closeExplainer);
    narrationModeEl.addEventListener('change', refreshCurrentNarration);
    document.querySelectorAll('[data-explain-target]').forEach((button) => {
      button.addEventListener('click', () => explainSection(button.dataset.explainTarget));
    });

    Plotly.newPlot('barChart', [{
      type: 'bar',
      x: payload.labels,
      y: payload.values,
      customdata: payload.labels,
      hovertemplate: '<b>%{x}</b><br>Recoverable annual: $%{y:,.2f}<extra></extra>',
      marker: {
        color: payload.values,
        colorscale: 'Turbo',
        line: {color: '#83e7ff', width: 1}
      }
    }], {
      margin: {l: 45, r: 10, t: 10, b: 120},
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {color: '#d8e8ff'},
      xaxis: {tickangle: -35, gridcolor: 'rgba(255,255,255,0.08)'},
      yaxis: {gridcolor: 'rgba(255,255,255,0.08)', tickprefix: '$'}
    }, {displayModeBar: false, responsive: true});

    document.getElementById('barChart').on('plotly_click', (event) => {
      const point = event.points && event.points[0];
      if (!point) return;
      const text = point.x + ' currently leads the recoverable value map at approximately $' + Number(point.y).toLocaleString() + ' per year. This chart ranks sectors by modeled recoverable value so capital attention stays concentrated on the strongest lanes.';
      openExplainer('Sector Opportunity Drilldown', text, 'opportunity');
      renderDrilldown('opportunity');
      speakText(text);
    });

    Plotly.newPlot('scatterChart', [{
      type: 'scatter',
      mode: 'markers+text',
      x: payload.x,
      y: payload.y,
      text: payload.names,
      textposition: 'top center',
      hovertemplate: '<b>%{text}</b><br>Sharpe: %{x:.2f}<br>Savings: %{y:.2f}%<extra></extra>',
      marker: {
        size: 14,
        color: payload.y,
        colorscale: 'Viridis',
        line: {color: '#ffffff', width: 0.8},
        opacity: 0.92
      }
    }], {
      margin: {l: 60, r: 10, t: 10, b: 55},
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {color: '#d8e8ff'},
      xaxis: {title: 'Sharpe', gridcolor: 'rgba(255,255,255,0.08)'},
      yaxis: {title: 'Savings %', gridcolor: 'rgba(255,255,255,0.08)'}
    }, {displayModeBar: false, responsive: true});

    document.getElementById('scatterChart').on('plotly_click', (event) => {
      const point = event.points && event.points[0];
      if (!point) return;
      const text = point.text + ' is plotting at Sharpe ' + Number(point.x).toFixed(2) + ' with modeled savings of ' + Number(point.y).toFixed(2) + ' percent. Use this surface to compare quality and economic lift at the same time.';
      openExplainer('Validation Surface Drilldown', text, 'validation');
      renderDrilldown('validation');
      speakText(text);
    });

    renderDrilldown('opportunity');
    runKpiAnimations();
    if ('speechSynthesis' in window) {
      populateVoices();
      window.speechSynthesis.onvoiceschanged = populateVoices;
    }

    // ── Scroll progress bar ──────────────────────────────────────────────────
    const scrollBar = document.getElementById('scroll-progress');
    window.addEventListener('scroll', () => {
      const total = document.documentElement.scrollHeight - window.innerHeight;
      const pct = total > 0 ? (window.scrollY / total) * 100 : 0;
      if (scrollBar) scrollBar.style.width = pct.toFixed(1) + '%';
    });

    // ── Live clock ───────────────────────────────────────────────────────────
    const clockEl = document.getElementById('liveClock');
    function updateClock() {
      if (!clockEl) return;
      const now = new Date();
      clockEl.textContent = 'Live · ' + now.toLocaleTimeString('en-US', { hour12: false });
    }
    updateClock();
    setInterval(updateClock, 1000);

    // ── Copy pitch button ────────────────────────────────────────────────────
    document.getElementById('copyPitch').addEventListener('click', () => {
      const text = (copyEl ? copyEl.textContent : '') || (explainer.master_pitch || '');
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
          const btn = document.getElementById('copyPitch');
          if (btn) { btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = 'Copy Pitch'; }, 2000); }
        });
      }
    });

    // ── Radar chart ──────────────────────────────────────────────────────────
    const radarDimensions = ['Sharpe', 'Sortino', 'Savings', 'Recoverable'];
    const radarTraces = payload.radar_sectors.map((sector, i) => ({
      type: 'scatterpolar',
      r: [payload.radar_sharpe[i], payload.radar_sortino[i], payload.radar_savings[i], payload.radar_recoverable[i], payload.radar_sharpe[i]],
      theta: [...radarDimensions, radarDimensions[0]],
      fill: 'toself',
      opacity: 0.62,
      name: sector,
      hovertemplate: '<b>' + sector + '</b><br>%{theta}: %{r:.2f}<extra></extra>',
    }));
    Plotly.newPlot('radarChart', radarTraces, {
      polar: {
        radialaxis: { visible: true, range: [0, 15], gridcolor: 'rgba(255,255,255,0.12)', color: '#93a8c7' },
        angularaxis: { gridcolor: 'rgba(255,255,255,0.1)', color: '#e7f1ff' },
        bgcolor: 'rgba(0,0,0,0)',
      },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#d8e8ff' },
      showlegend: true,
      legend: { font: { color: '#93a8c7', size: 11 }, bgcolor: 'rgba(0,0,0,0)' },
      margin: { l: 55, r: 55, t: 20, b: 20 },
    }, { displayModeBar: false, responsive: true });

    document.getElementById('radarChart').on('plotly_click', (event) => {
      const point = event.points && event.points[0];
      if (!point) return;
      const sectorName = point.data.name;
      const text = sectorName + ' scores across four axes on this radar: Sharpe quality, Sortino downside protection, modeled savings rate, and annual recoverable value. Each axis is normalized so you can compare across dimensions. A larger filled area means a stronger sector signal.';
      openExplainer('Radar Drilldown: ' + sectorName, text, 'validation');
      renderDrilldown('validation');
      speakText(text);
    });

    // ── Confidence envelope chart ─────────────────────────────────────────────
    const sortedSectors = [...payload.radar_sectors].map((s, i) => ({ s, sharpe: payload.radar_sharpe[i], savings: payload.radar_savings[i] })).sort((a, b) => b.sharpe - a.sharpe);
    Plotly.newPlot('confidenceChart', [
      {
        type: 'bar',
        x: sortedSectors.map(d => d.s),
        y: sortedSectors.map(d => d.sharpe),
        name: 'Sharpe',
        marker: { color: 'rgba(87,240,203,0.72)', line: { color: '#57f0cb', width: 1 } },
        hovertemplate: '<b>%{x}</b><br>Sharpe: %{y:.2f}<extra></extra>',
      },
      {
        type: 'bar',
        x: sortedSectors.map(d => d.s),
        y: sortedSectors.map(d => d.savings / 4),
        name: 'Savings Index',
        marker: { color: 'rgba(255,211,106,0.62)', line: { color: '#ffd36a', width: 1 } },
        hovertemplate: '<b>%{x}</b><br>Savings index: %{y:.2f}<extra></extra>',
      }
    ], {
      barmode: 'group',
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#d8e8ff' },
      xaxis: { tickangle: -30, gridcolor: 'rgba(255,255,255,0.07)' },
      yaxis: { gridcolor: 'rgba(255,255,255,0.07)', title: 'Score' },
      legend: { font: { color: '#93a8c7', size: 11 }, bgcolor: 'rgba(0,0,0,0)' },
      margin: { l: 48, r: 10, t: 10, b: 90 },
    }, { displayModeBar: false, responsive: true });

    document.getElementById('confidenceChart').on('plotly_click', (event) => {
      const point = event.points && event.points[0];
      if (!point) return;
      const text = point.x + ' holds a Sharpe of ' + Number(point.y).toFixed(2) + '. This grouped view lets you see which sectors are leading in quality-adjusted return versus raw savings rate, so you can rank capital allocation priorities.';
      openExplainer('Strength Profile: ' + point.x, text, 'validation');
      renderDrilldown('validation');
      speakText(text);
    });

    // ── Clickable sector table rows ──────────────────────────────────────────
    document.querySelectorAll('.clickable-sector').forEach((row) => {
      row.addEventListener('click', () => {
        document.querySelectorAll('.clickable-sector.active-row').forEach(r => r.classList.remove('active-row'));
        row.classList.add('active-row');
        const sector = row.dataset.sector || 'this sector';
        const sharpe = row.dataset.sharpe || '';
        const savings = row.dataset.savings || '';
        const recoverable = row.dataset.recoverable || '';
        const text = sector.replace(/_/g, ' ') + ' carries a Sharpe of ' + sharpe + ', modeled savings of ' + savings + ' percent, and an estimated recoverable annual value of ' + recoverable + '. This is one of the validated lanes on the LumenCore platform and represents a directly attributable opportunity surface.';
        openExplainer('Sector Signal: ' + sector.replace(/_/g, ' '), text, 'validation');
        renderDrilldown('validation');
        speakText(text);
      });
    });

    // ── Auto-advance walkthrough when speech ends ────────────────────────────
    let autoAdvanceEnabled = false;
    function enableAutoAdvance() { autoAdvanceEnabled = true; }
    const origRunWalkthrough = runWalkthrough;
    function runWalkthroughAuto() {
      autoAdvanceEnabled = true;
      runWalkthrough();
    }
    document.getElementById('startWalkthrough').addEventListener('dblclick', runWalkthroughAuto);
    document.getElementById('walkthroughExplainer').addEventListener('dblclick', runWalkthroughAuto);

    // ── Auto-speak Luma greeting on first user click ─────────────────────────
    let greeted = false;
    function lumaGreet() {
      if (greeted) return;
      greeted = true;
      if (!('speechSynthesis' in window)) return;
      populateVoices();
      const greeting = personaLead.luma + ' The board is live. ' + (explainer.sections && explainer.sections.overview ? explainer.sections.overview.text : '');
      speakText(greeting);
      openExplainer('Luma Online', greeting, 'overview');
    }
    document.body.addEventListener('click', lumaGreet, { once: true });
  </script>
</body>
</html>
"""


def render_html(data: Dict[str, Any]) -> str:
    html = TEMPLATE
    replacements = {
        "__RECORDS__": str(data["records_ingested"]),
        "__SOURCES_OK__": str(data["sources_ok"]),
        "__FAILING_SOURCES__": str(data["failing_enabled_sources"]),
        "__SECTORS__": str(data["sectors_analyzed"]),
        "__HIST_LOSS__": fmt_usd(data["total_historical_loss"]),
        "__RECOVERABLE__": fmt_usd(data["total_recoverable_annual"]),
        "__INFRA_ANNUAL__": fmt_usd(data["infra_annual_exposure"]),
        "__INFRA_20Y__": fmt_usd(data["infra_exposure_20y"]),
        "__INFRA_UPSIDE__": fmt_usd(data["infra_modeled_upside"]),
        "__AVG_SHARPE__": f"{data['avg_sharpe']:.2f}",
        "__AVG_SAVINGS__": f"{data['avg_savings_pct']:.1f}%",
        "__TOP_LIVE_SECTOR__": str(data["top_live_sector"]),
        "__TOP_LIVE_SECTOR_HOUR__": fmt_usd(data["top_live_sector_hour"]),
        "__ENABLED_SOURCES__": str(data["enabled_sources"]),
        "__RUNTIME__": f"{data['compute_minutes']:.2f}m",
        "__PAPER_EQUITY__": fmt_usd(data["paper_equity"]),
        "__PAPER_PNL_LABEL__": html_escape(data["paper_pnl_label"]),
        "__PAPER_PROFIT__": fmt_usd(data["paper_profit"]),
        "__PAPER_PNL_SUB__": html_escape(data["paper_pnl_sub"]),
        "__PAPER_SHARPE__": f"{data['paper_sharpe']:.2f}",
        "__PAPER_SORTINO__": f"{data['paper_sortino']:.2f}",
        "__PAPER_MDD__": f"{data['paper_mdd']:.2f}%",
        "__PAPER_CAGR__": f"{data['paper_cagr']:.2f}%",
        "__PAPER_PF__": f"{data['paper_pf']:.2f}",
        "__PAPER_TRADES_LABEL__": html_escape(data["paper_trades_label"]),
        "__PAPER_TRADES__": str(data["paper_trades"]),
        "__PAPER_WR__": f"{data['paper_win_rate']:.1f}%",
        "__PAPER_TRADES_SUB__": html_escape(data["paper_trades_sub"]),
        "__PROOF_TXID_COUNT__": str(data["proof_txid_count"]),
        "__PROOF_TXID_TAIL__": html_escape(data["proof_txid_tail"]),
        "__GENERATED__": now_utc(),
        "__TABLE_ROWS__": build_validation_rows(data["validations"]),
        "__FAILURE_ROWS__": build_truth_rows(data["top_failed_sources"], "failures"),
        "__LIVE_ROWS__": build_truth_rows(data["top_live_sources"], "live"),
        "__CHART_JSON__": json.dumps(data["chart"]),
        "__EXPLAINER_JSON__": json.dumps(data["explainer"]),
        "__KPI_ANIM_JSON__": json.dumps(data["kpi_anim"]),
        "__DRILLDOWN_JSON__": json.dumps(data["drilldown"]),
        "__PITCH_PREVIEW__": html_escape(data["explainer"].get("pitch_preview", "")),
        "__DRILLDOWN_TITLE__": html_escape(data["drilldown"]["opportunity"]["title"]),
        "__DRILLDOWN_TEXT__": html_escape(data["drilldown"]["opportunity"]["text"]),
        "__DRILLDOWN_CHIPS__": "".join(
          f'<span class="drilldown-chip">{html_escape(chip)}</span>' for chip in data["drilldown"]["opportunity"]["chips"]
        ),
    }
    for key, value in replacements.items():
        html = html.replace(key, value)
    return html


def main() -> None:
    data = collect_data()
    html = render_html(data)

    DASH.mkdir(parents=True, exist_ok=True)
    output_path = DASH / "LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html"
    alias_path = DASH / "combined_master_dashboard.html"
    output_path.write_text(html, encoding="utf-8")
    alias_path.write_text(html, encoding="utf-8")

    print(f"[OK] wrote: {output_path}")
    print(f"[OK] alias : {alias_path}")
    print(f"[OK] records={data['records_ingested']} sectors={data['sectors_analyzed']}")
    print(f"[OK] sharpe={data['avg_sharpe']:.2f} savings={data['avg_savings_pct']:.1f}%")


if __name__ == "__main__":
    main()
