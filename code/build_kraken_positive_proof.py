from __future__ import annotations

import csv
import argparse
import hashlib
import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
DASH = ROOT / "dashboard"

EVENT_SOURCES = [
    ROOT / "execution_events.jsonl",
    OUT / "execution_events.jsonl",
    ROOT / "data" / "out" / "execution_events.jsonl",
    EXEC_OUT / "execution_events.jsonl",
]

LEADERBOARD_SOURCES = [
    ROOT / "institutional_leaderboard.csv",
    OUT / "institutional_leaderboard.csv",
    EXEC_OUT / "institutional_leaderboard.csv",
    ROOT / "data" / "out" / "institutional_leaderboard.csv",
]

ROLLING_PERFORMANCE_SOURCES = [
    ROOT / "rolling_performance.json",
    OUT / "rolling_performance.json",
    ROOT / "data" / "out" / "rolling_performance.json",
]

REALIZED_OUTCOME_SOURCES = [
    OUT / "execution" / "investor_performance_report.json",
    OUT / "execution" / "institutional_crypto_paper_report.json",
    OUT / "rolling_performance.json",
    ROOT / "data" / "out" / "rolling_performance.json",
    ROOT / "rolling_performance.json",
]

CHAIN_FILES = [
    OUT / "CHAIN_OF_CUSTODY_SHA256.json",
    OUT / "paper_trade_chain_of_custody_sha256.json",
    EXEC_OUT / "institutional_crypto_paper_report_sha256.json",
    OUT / "unified_dashboard_chain_of_custody_sha256.json",
]

OUTPUT_JSON = EXEC_OUT / "kraken_positive_proof.json"
OUTPUT_MD = EXEC_OUT / "kraken_positive_proof.md"
OUTPUT_HTML = DASH / "kraken_positive_proof.html"
OUTPUT_HASH = EXEC_OUT / "kraken_positive_proof_sha256.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def pick_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return list(csv.DictReader(text.splitlines()))
    except Exception:
        return []


def load_events(paths: list[Path]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            try:
                key = json.dumps(row, sort_keys=True)
            except Exception:
                key = str(row)
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
    merged.sort(key=lambda x: str(x.get("timestamp", x.get("generated_utc", ""))))
    return merged


def extract_txids(events: list[dict[str, Any]]) -> list[str]:
    txids: list[str] = []
    for e in events:
        direct = e.get("txid")
        if direct:
            txids.extend(str(x) for x in (direct if isinstance(direct, list) else [direct]) if x)
        vr = e.get("validation_result", {})
        if isinstance(vr, dict) and vr.get("txid"):
            payload = vr.get("txid")
            if isinstance(payload, list):
                txids.extend(str(x) for x in payload if str(x).strip())
            else:
                txids.append(str(payload))
    uniq: list[str] = []
    seen: set[str] = set()
    for t in txids:
        if t in seen:
            continue
        seen.add(t)
        uniq.append(t)
    return uniq


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def compute_wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    denom = 1.0 + (z * z) / total
    center = p + (z * z) / (2.0 * total)
    margin = z * (((p * (1.0 - p) / total) + (z * z) / (4.0 * total * total)) ** 0.5)
    return max(0.0, (center - margin) / denom)


def get_first_non_empty_timestamp(events: list[dict[str, Any]]) -> str | None:
    for row in events:
        ts = row.get("timestamp") or row.get("generated_utc")
        if ts:
            return str(ts)
    return None


def get_last_non_empty_timestamp(events: list[dict[str, Any]]) -> str | None:
    for row in reversed(events):
        ts = row.get("timestamp") or row.get("generated_utc")
        if ts:
            return str(ts)
    return None


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def classify_outcome(data: dict[str, Any], source: str) -> dict[str, Any]:
    """Require explicit closed-fill reconciliation before reporting realized PnL.

    Historical paper/portfolio summaries are not exchange accounting. An absent
    result remains null; a reconciled zero remains a real zero. All reconciliation
    metadata is first-party reported, never described as independently verified.
    """
    mode = str(data.get("mode", data.get("execution_mode", ""))).lower()
    is_paper = "paper" in source.lower() or mode in {"paper", "shadow", "simulation", "backtest"} or "paper_profit" in data
    result = {"realized_source": source, "rolling_performance_net_pnl": None,
              "unit": None, "status": "PAPER_ONLY" if is_paper else "UNRECONCILED",
              "note": "Historical paper, shadow and unjoined summaries are not realized exchange PnL."}
    if is_paper:
        return result
    rec = data.get("reconciliation")
    value = finite_number(data.get("realized_net_pnl"))
    window = data.get("time_window")
    if (mode != "live" or not isinstance(rec, dict) or
        rec.get("status") != "MATCHED" or rec.get("fees_included") is not True or
        rec.get("cost_basis_complete") is not True or
        not isinstance(rec.get("closed_trade_count"), int) or
        isinstance(rec.get("closed_trade_count"), bool) or rec["closed_trade_count"] <= 0 or
        not rec.get("fills_source") or not isinstance(window, dict) or
        not window.get("start_utc") or not window.get("end_utc") or
        not isinstance(data.get("quote_currency"), str) or not data["quote_currency"].strip() or value is None):
        return result
    result.update(rolling_performance_net_pnl=value, unit=data["quote_currency"],
                  time_window=window, reconciliation=rec,
                  status="REPORTED_RECONCILED", note="First-party closed-fill accounting with explicit fees, cost basis, currency and window; independent review pending.")
    return result


def pick_realized_outcome() -> dict[str, Any]:
    seen = []
    for p in REALIZED_OUTCOME_SOURCES:
        data = load_json(p, {})
        if not isinstance(data, dict) or not data:
            continue
        candidate = classify_outcome(data, str(p))
        seen.append({"source": str(p), "status": candidate["status"]})
        if candidate["status"] == "REPORTED_RECONCILED":
            candidate["sources_reviewed"] = seen
            return candidate
    return {"realized_source": None, "rolling_performance_net_pnl": None,
            "unit": None, "status": "UNKNOWN", "sources_reviewed": seen,
            "note": "No complete closed-fill reconciliation located. Paper profit and missing results are not realized profit or a measured zero."}


def mode_conflicts(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts = []
    for event in events:
        payload = event.get("payload", {})
        validate = payload.get("validate") if isinstance(payload, dict) else None
        declared = str(event.get("mode", event.get("event", ""))).lower()
        if "validate" in declared and (validate is False or str(validate).lower() == "false"):
            conflicts.append({"timestamp": event.get("timestamp"),
                              "reason": "validate-only label conflicts with validate=false payload",
                              "txids": extract_txids([event])})
    return conflicts


def build_payload() -> dict[str, Any]:
    events = load_events(EVENT_SOURCES)
    trade_log = load_json(ROOT / "investor_txids" / "trade_log.json", [])
    if not isinstance(trade_log, list):
        trade_log = []
    txids = extract_txids(events + [row for row in trade_log if isinstance(row, dict)])

    submit_events = [e for e in events if e.get("event") in {"submit_order", "submit_order_validate_only"}]
    deadman_events = [e for e in events if e.get("event") == "deadman_armed"]
    ticket_events = [e for e in events if e.get("event") == "approval_ticket_created"]
    env_events = [e for e in events if e.get("event") == "verify_env_only"]

    has_deadman = len(deadman_events) > 0
    has_tickets = len(ticket_events) > 0
    has_txids = len(txids) > 0
    has_env_checks = len(env_events) > 0

    chain_present = [str(p) for p in CHAIN_FILES if p.exists()]
    has_chain = len(chain_present) > 0

    controls = {
        "deadman_switch_evidence": has_deadman,
        "approval_ticket_evidence": has_tickets,
        "kraken_txid_evidence": has_txids,
        "env_verification_evidence": has_env_checks,
        "chain_of_custody_evidence": has_chain,
    }
    controls_successes = sum(1 for v in controls.values() if v)
    controls_total = len(controls)
    controls_coverage_pct = 100.0 * (controls_successes / controls_total if controls_total else 0.0)
    txid_depth_bonus = min(15.0, len(txids) * 2.0)
    event_depth_bonus = min(15.0, len(submit_events) * 1.5)
    control_score = round(min(100.0, controls_coverage_pct * 0.7 + txid_depth_bonus + event_depth_bonus), 2)

    leaderboard_path = pick_existing(LEADERBOARD_SOURCES)
    leaderboard_rows = load_csv_rows(leaderboard_path) if leaderboard_path else []
    top_rows = leaderboard_rows[:10]
    top_test_sharpes = [n for r in top_rows if (n := finite_number(r.get("test_sharpe", r.get("test_sharpe_clean")))) is not None]
    top_win_rates = [n for r in top_rows if (n := finite_number(r.get("test_win_rate"))) is not None]

    edge_quality = {
        "leaderboard_source": str(leaderboard_path) if leaderboard_path else None,
        "top10_count": len(top_rows),
        "mean_test_sharpe_top10": round(mean(top_test_sharpes), 4) if top_test_sharpes else None,
        "mean_test_win_rate_top10": round(mean(top_win_rates), 4) if top_win_rates else None,
        "evidence_basis": "historical leaderboard diagnostics; not verified net trading performance",
    }

    rolling_path = pick_existing(ROLLING_PERFORMANCE_SOURCES)
    realized_outcome = pick_realized_outcome()

    first_ts = get_first_non_empty_timestamp(events)
    last_ts = get_last_non_empty_timestamp(events)

    return {
        "generated_utc": now_utc(),
        "proof_type": "kraken_execution_evidence_v2",
        "time_window": {
            "first_event_utc": first_ts,
            "last_event_utc": last_ts,
            "event_count": len(events),
        },
        "kraken_execution_evidence": {
            "submit_events": len(submit_events),
            "deadman_events": len(deadman_events),
            "approval_ticket_events": len(ticket_events),
            "env_verification_events": len(env_events),
            "txid_count": len(txids),
            "txids": txids,
            "evidence_basis": "first_party_order_records_not_reconciled_exchange_fills",
            "mode_conflicts": mode_conflicts(events),
        },
        "control_integrity": {
            "controls": controls,
            "controls_success_count": controls_successes,
            "controls_total": controls_total,
            "controls_coverage_pct": round(controls_coverage_pct, 2),
            "wilson_lower_bound": None,
            "statistical_confidence_0_100": None,
            "score_basis": "heuristic artifact-presence checklist; not statistical confidence or verified control effectiveness",
            "control_integrity_score_0_100": control_score,
            "chain_files": chain_present,
        },
        "edge_quality": edge_quality,
        "realized_outcome": {
            **realized_outcome,
            "rolling_performance_source": str(rolling_path) if rolling_path else None,
        },
        "institutional_narrative": {
            "claim": "The stack contains historical order IDs, control artifacts and research results; each has a distinct evidence basis.",
            "caveat": "An order ID does not establish a completed fill, strategy attribution, profitability, current authority or independent verification.",
            "next_milestone": "Reconcile existing order IDs to closed fills, fees and strategy decisions; preserve paper/live boundaries and dated holdouts.",
        },
    }


def write_markdown(payload: dict[str, Any]) -> None:
    ev = payload.get("kraken_execution_evidence", {})
    ci = payload.get("control_integrity", {})
    eq = payload.get("edge_quality", {})
    ro = payload.get("realized_outcome", {})
    lines = [
        "# Kraken Execution Evidence",
        "",
        f"Generated UTC: {payload.get('generated_utc')}",
        "",
        "## Core Evidence",
        f"- TXIDs: {ev.get('txid_count', 0)}",
        f"- Submit events: {ev.get('submit_events', 0)}",
        f"- Deadman events: {ev.get('deadman_events', 0)}",
        f"- Approval ticket events: {ev.get('approval_ticket_events', 0)}",
        f"- Control integrity score (0-100): {ci.get('control_integrity_score_0_100', 0)}",
        "",
        "## Edge Quality",
        f"- Mean test Sharpe (top10): {eq.get('mean_test_sharpe_top10', 0.0)}",
        f"- Mean test win-rate (top10): {eq.get('mean_test_win_rate_top10', 0.0)}",
        "",
        "## Realized Outcome",
        f"- Net PnL: {format_pnl(ro)}",
        f"- Status: {ro.get('status', 'UNKNOWN')}",
        f"- Note: {ro.get('note', '')}",
        "",
        "## TXID List",
    ]
    for txid in ev.get("txids", []):
        lines.append(f"- {txid}")
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def format_pnl(outcome: dict[str, Any]) -> str:
    value = finite_number(outcome.get("rolling_performance_net_pnl"))
    return "Unknown / not reconciled" if value is None else f"{value:.2f} {outcome.get('unit', '')}"


def write_html(payload: dict[str, Any]) -> None:
    ev = payload.get("kraken_execution_evidence", {})
    ci = payload.get("control_integrity", {})
    eq = payload.get("edge_quality", {})
    ro = payload.get("realized_outcome", {})

    txid_html = "".join(f"<li>{html.escape(str(x))}</li>" for x in ev.get("txids", []))
    if not txid_html:
        txid_html = "<li>No TXIDs found</li>"

    pnl = finite_number(ro.get("rolling_performance_net_pnl"))
    pnl_class = "acc" if pnl is None else "neg" if pnl < 0 else "pos"

    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
<title>Kraken Execution Evidence</title>
<style>
:root {{ --bg:#0b0f14; --panel:#111826; --line:#23314c; --text:#eaf0ff; --muted:#9fb0d1; --pos:#1dd1a1; --neg:#ff6b6b; --acc:#ffd166; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:Segoe UI,Arial,sans-serif; color:var(--text); background:radial-gradient(circle at 10% 10%, #172035 0%, transparent 35%), radial-gradient(circle at 90% 0%, #272340 0%, transparent 35%), var(--bg); }}
.wrap {{ max-width:1200px; margin:0 auto; padding:24px; }}
.hero, .card {{ background:linear-gradient(180deg, rgba(19,28,43,.95), rgba(12,18,30,.96)); border:1px solid var(--line); border-radius:16px; padding:18px; }}
.hero h1 {{ margin:0 0 8px 0; font-size:32px; }}
.hero p {{ margin:0; color:var(--muted); }}
.grid {{ display:grid; gap:14px; grid-template-columns:repeat(4,minmax(0,1fr)); margin-top:14px; }}
.big {{ font-size:30px; font-weight:800; margin-top:8px; }}
.kicker {{ font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.9px; }}
.pos {{ color:var(--pos); }}
.neg {{ color:var(--neg); }}
.acc {{ color:var(--acc); }}
.section {{ margin-top:14px; }}
ul {{ margin:8px 0 0 18px; }}
@media (max-width:980px) {{ .grid {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
@media (max-width:620px) {{ .grid {{ grid-template-columns:1fr; }} .hero h1 {{ font-size:26px; }} }}
</style>
</head>
<body>
<div class=\"wrap\">
  <div class=\"hero\">
    <h1>Kraken Execution Evidence</h1>
    <p>Historical order records, research diagnostics and explicit accounting provenance.</p>
    <p><a href="/mission_control.html">Mission Control</a> · <a href="/quant_lab.html">Quant Lab</a> · <a href="/kraken_execution_dashboard.html">Kraken research</a></p>
  </div>

  <div class=\"grid\">
    <div class=\"card\"><div class=\"kicker\">TXID Count</div><div class=\"big\">{ev.get('txid_count',0)}</div></div>
    <div class=\"card\"><div class=\"kicker\">Artifact checklist score (heuristic)</div><div class=\"big acc\">{ci.get('control_integrity_score_0_100',0)}</div></div>
    <div class=\"card\"><div class=\"kicker\">Mean Top10 Sharpe</div><div class=\"big\">{eq.get('mean_test_sharpe_top10',0.0)}</div></div>
    <div class=\"card\"><div class=\"kicker\">Reported reconciled Net PnL</div><div class=\"big {pnl_class}\">{html.escape(format_pnl(ro))}</div></div>
  </div>

  <div class=\"card section\">
    <div class=\"kicker\">Narrative</div>
    <div style=\"margin-top:8px;\">{html.escape(str(payload.get('institutional_narrative', {}).get('claim', '')))}</div>
    <div style=\"margin-top:8px;color:var(--muted);\">{html.escape(str(payload.get('institutional_narrative', {}).get('caveat', '')))}</div>
    <div style=\"margin-top:8px;color:var(--muted);\">Next milestone: {html.escape(str(payload.get('institutional_narrative', {}).get('next_milestone', '')))}</div>
  </div>

  <div class=\"card section\">
    <div class=\"kicker\">Recorded order IDs — fill reconciliation pending</div>
    <ul>{txid_html}</ul>
  </div>
</div>
</body>
</html>
"""
    OUTPUT_HTML.write_text(html_doc, encoding="utf-8")


def write_hash_manifest() -> None:
    artifacts = [OUTPUT_JSON, OUTPUT_MD, OUTPUT_HTML]
    rows: list[dict[str, str]] = []
    for path in artifacts:
        data = path.read_bytes()
        rows.append(
            {
                "path": str(path),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": str(len(data)),
            }
        )
    OUTPUT_HASH.write_text(json.dumps({"generated_utc": now_utc(), "artifacts": rows}, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Read local evidence and write a report; no exchange calls.")
    parser.parse_args()
    EXEC_OUT.mkdir(parents=True, exist_ok=True)
    DASH.mkdir(parents=True, exist_ok=True)

    payload = build_payload()
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(payload)
    write_html(payload)
    write_hash_manifest()

    print(str(OUTPUT_JSON))
    print(str(OUTPUT_MD))
    print(str(OUTPUT_HTML))
    print(str(OUTPUT_HASH))


if __name__ == "__main__":
    main()
