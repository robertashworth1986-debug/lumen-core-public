import json, os, math, hashlib, datetime

ROOT = r"C:\LumaTrader\INSTITUTIONAL_STACK_V2"
CONF = os.path.join(ROOT, "config")
OUT  = os.path.join(ROOT, "out")
DASH = r"C:\LumaTrader\dashboard"

def now_utc():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

seed = load_json(os.path.join(OUT, "seed_validation_readout.json"), {})
live_sources = load_json(os.path.join(CONF, "live_sources.json"), {})
registry = load_json(os.path.join(CONF, "live_source_registry.json"), {})
truth = load_json(os.path.join(OUT, "source_truth_table.json"), {})
engine = load_json(os.path.join(OUT, "engine_truth_audit.json"), {})
paper_state = load_json(os.path.join(OUT, "paper_trade_state.json"), {})
paper_runtime = load_json(os.path.join(CONF, "paper_trader_runtime.json"), {})
paper_run = load_json(os.path.join(OUT, "paper_trade_runtime.json"), {})
ledger = load_json(os.path.join(OUT, "paper_trade_ledger.jsonl"), None)
paper_chain = load_json(os.path.join(OUT, "paper_trade_chain_of_custody_sha256.json"), {})
adaptive = load_json(os.path.join(OUT, "adaptive_universe_summary.json"), {})

sector_defaults = {
    "broker": {
        "constraint_type": "execution / routing / order acceptance",
        "money_drain_mode": "missed fills, slippage, capital idling, routing friction",
        "formula_basis": "baseline throughput / execution opportunity translated to $"
    },
    "market_data": {
        "constraint_type": "price discovery / latency / incomplete market context",
        "money_drain_mode": "bad entries, bad exits, missed momentum, stale reads",
        "formula_basis": "decision quality loss translated to $"
    },
    "macro": {
        "constraint_type": "regime misclassification / economic drift",
        "money_drain_mode": "wrong positioning across cycle changes",
        "formula_basis": "macro misread exposure translated to $"
    },
    "labor": {
        "constraint_type": "employment drift / wage pressure / scheduling mismatch",
        "money_drain_mode": "downtime, staffing mismatch, delayed response",
        "formula_basis": "labor friction translated to $"
    },
    "demographic": {
        "constraint_type": "demand misallocation / population shift misread",
        "money_drain_mode": "resources deployed to wrong place / wrong cohort",
        "formula_basis": "allocation inefficiency translated to $"
    },
    "energy": {
        "constraint_type": "capacity outage / generation constraint / dispatch inefficiency",
        "money_drain_mode": "downtime, curtailed output, outage losses",
        "formula_basis": "hourly outage or capacity loss translated to $"
    },
    "air_quality": {
        "constraint_type": "environmental compliance / health signal drift",
        "money_drain_mode": "avoidable penalties, exposure, degraded operations",
        "formula_basis": "environmental degradation translated to $"
    },
    "rates": {
        "constraint_type": "yield curve / funding cost / interest-rate drift",
        "money_drain_mode": "higher financing cost, wrong risk posture",
        "formula_basis": "rate sensitivity translated to $"
    },
    "crypto_exec": {
        "constraint_type": "exchange routing / pair selection / volatility execution",
        "money_drain_mode": "bad timing, spread bleed, missed moves",
        "formula_basis": "execution opportunity translated to $"
    },
    "space": {
        "constraint_type": "space weather / orbital environment / environmental hazard",
        "money_drain_mode": "signal disruption, infrastructure degradation",
        "formula_basis": "environmental risk translated to $"
    },
    "weather": {
        "constraint_type": "weather instability / forecast uncertainty / climate interference",
        "money_drain_mode": "avoidable disruption, planning failure, service loss",
        "formula_basis": "weather disruption translated to $"
    },
    "energy_lab": {
        "constraint_type": "R&D underutilization / energy optimization miss",
        "money_drain_mode": "missed efficiency gains, underused capacity",
        "formula_basis": "lab / resource underperformance translated to $"
    }
}

raw_sector_rollup = seed.get("sector_rollup_truth", {}) if isinstance(seed, dict) else {}
sector_rollup = {}
if isinstance(raw_sector_rollup, dict):
    sector_rollup = raw_sector_rollup
elif isinstance(raw_sector_rollup, list):
    # Backward/variant schema: list of sector rows -> normalize to dict keyed by sector.
    for row in raw_sector_rollup:
        if not isinstance(row, dict):
            continue
        sector_key = str(row.get("sector", "unknown")).strip() or "unknown"
        sector_rollup[sector_key] = {
            "live_sources": row.get("live_sources", 0),
            "rows": row.get("rows", 0),
            "hour": row.get("hour", 0),
            "day": row.get("day", 0),
            "week": row.get("week", 0),
            "month": row.get("month", 0),
            "year": row.get("year", 0),
        }

sector_explainer = {}
total_year = 0.0

if not sector_rollup:
    print("[WARNING] sector_rollup is empty. No sector data found in seed_validation_readout.json. Upstream pipeline may not have generated sector rollup data.")

for sector, vals in sector_rollup.items():
    live_count = float(vals.get("live_sources", 0) or 0)
    rows = float(vals.get("rows", 0) or 0)
    hour = float(vals.get("hour", 0) or 0)
    day = float(vals.get("day", 0) or 0)
    week = float(vals.get("week", 0) or 0)
    month = float(vals.get("month", 0) or 0)
    year = float(vals.get("year", 0) or 0)
    total_year += year

    meta = sector_defaults.get(sector, {
        "constraint_type": "unknown operational drift / unclassified constraint",
        "money_drain_mode": "unclassified value leakage",
        "formula_basis": "translated sector value"
    })

    status = "MEASURED" if live_count > 0 else "UNMEASURED"
    if rows <= 0 and live_count > 0:
        status = "KEY_PRESENT_BUT_THIN_ROWS"

    sector_explainer[sector] = {
        "status": status,
        "live_sources": live_count,
        "rows": rows,
        "constraint_type": meta["constraint_type"],
        "money_drain_mode": meta["money_drain_mode"],
        "formula_basis": meta["formula_basis"],
        "translated_value": {
            "hour": hour,
            "day": day,
            "week": week,
            "month": month,
            "year": year
        },
        "audit_interpretation": (
            f"This sector is being interpreted as a {meta['constraint_type']} layer. "
            f"Its current modeled money drain / opportunity surface is {meta['money_drain_mode']}. "
            f"The translated yearly value shown is ${year:,.2f}."
        )
    }

trade_evidence = {
    "paper_enabled": bool(paper_runtime.get("paper_enabled", False)) if isinstance(paper_runtime, dict) else False,
    "allow_live_orders": bool(paper_runtime.get("allow_live_orders", False)) if isinstance(paper_runtime, dict) else False,
    "runtime_symbol": paper_runtime.get("runtime_symbol", "UNKNOWN") if isinstance(paper_runtime, dict) else "UNKNOWN",
    "selection_source": paper_runtime.get("selection_source", "UNKNOWN") if isinstance(paper_runtime, dict) else "UNKNOWN",
    "symbol_mode": paper_runtime.get("symbol_mode", "UNKNOWN") if isinstance(paper_runtime, dict) else "UNKNOWN",
    "symbol_count": paper_runtime.get("symbol_count", 0) if isinstance(paper_runtime, dict) else 0,
    "open_positions_count": len(paper_state.get("open_positions", [])) if isinstance(paper_state, dict) else 0,
    "reported_pnl_usd": float(paper_state.get("pnl_usd", 0.0) or 0.0) if isinstance(paper_state, dict) else 0.0,
    "ledger_present": os.path.exists(os.path.join(OUT, "paper_trade_ledger.jsonl")),
    "ledger_sha_present": os.path.exists(os.path.join(OUT, "paper_trade_chain_of_custody_sha256.json")),
    "status": paper_state.get("status", "UNKNOWN") if isinstance(paper_state, dict) else "UNKNOWN"
}

if trade_evidence["ledger_present"]:
    ledger_path = os.path.join(OUT, "paper_trade_ledger.jsonl")
    trade_evidence["ledger_sha256"] = sha256_file(ledger_path)
else:
    trade_evidence["ledger_sha256"] = None

if trade_evidence["ledger_present"] and trade_evidence["reported_pnl_usd"] != 0:
    trade_evidence["pnl_audit_status"] = "REALIZED_OR_MARKED_PNL_PRESENT"
elif trade_evidence["ledger_present"]:
    trade_evidence["pnl_audit_status"] = "LEDGER_PRESENT_BUT_NO_REALIZED_PNL_YET"
else:
    trade_evidence["pnl_audit_status"] = "NO_TRADE_PROOF_YET"

champ = seed.get("champion", {}) if isinstance(seed, dict) else {}
metric_derivation = {
    "test_sharpe": champ.get("test_sharpe_clean", champ.get("test_sharpe")),
    "test_vs_baseline": champ.get("test_vs_baseline_clean", champ.get("test_vs_baseline")),
    "test_cagr": champ.get("test_cagr_clean", champ.get("test_cagr")),
    "test_max_dd": champ.get("test_max_dd_clean", champ.get("test_max_dd")),
    "investor_score": champ.get("investor_score_clean", champ.get("institutional_score")),
    "credibility_flag": champ.get("credible", "UNKNOWN"),
    "audit_comment": (
        "These metrics are derived backtest-style performance statistics until tied to a persistent paper-trade ledger. "
        "Treat them as research evidence, not live-performance evidence."
    )
}

pack = {
    "generated_utc": now_utc(),
    "headline": "LumenCore audit-grade derivation pack",
    "what_this_proves": [
        "which sectors are populated",
        "how each sector is interpreted",
        "what money drain / constraint each sector represents",
        "what translated value is being claimed",
        "whether paper trading has actual evidence of fills / pnl or not",
        "whether performance metrics are research-derived or ledger-derived"
    ],
    "summary": {
        "enabled_registry_sources": seed.get("enabled_registry_sources", 0),
        "measured_sources": seed.get("measured_sources", 0),
        "adaptive_universe_count": seed.get("adaptive_universe_count", 0),
        "translated_yearly_value_total": total_year
    },
    "sector_explainer": sector_explainer,
    "paper_trade_evidence": trade_evidence,
    "metric_derivation": metric_derivation,
    "files_used": {
        "seed_validation_readout_json": os.path.join(OUT, "seed_validation_readout.json"),
        "live_sources_json": os.path.join(CONF, "live_sources.json"),
        "live_source_registry_json": os.path.join(CONF, "live_source_registry.json"),
        "source_truth_table_json": os.path.join(OUT, "source_truth_table.json"),
        "engine_truth_audit_json": os.path.join(OUT, "engine_truth_audit.json"),
        "paper_trade_state_json": os.path.join(OUT, "paper_trade_state.json"),
        "paper_trader_runtime_json": os.path.join(CONF, "paper_trader_runtime.json"),
        "paper_trade_runtime_json": os.path.join(OUT, "paper_trade_runtime.json")
    }
}

pack_path = os.path.join(OUT, "AUDIT_GRADE_DERIVATION_PACK.json")
save_json(pack_path, pack)

ledger_path = os.path.join(OUT, "CHAIN_OF_CUSTODY_256.txt")
hash_lines = []
for p in [
    pack_path,
    os.path.join(OUT, "seed_validation_readout.json"),
    os.path.join(CONF, "live_sources.json"),
    os.path.join(CONF, "live_source_registry.json"),
    os.path.join(OUT, "engine_truth_audit.json"),
    os.path.join(OUT, "paper_trade_state.json"),
    os.path.join(CONF, "paper_trader_runtime.json"),
]:
    if os.path.exists(p):
        hash_lines.append(f"{sha256_file(p)}  {p}")

with open(ledger_path, "w", encoding="utf-8") as f:
    f.write("\n".join(hash_lines) + "\n")

html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>LumenCore Audit Derivation Pack</title>
<style>
body {{
  font-family: Arial, sans-serif;
  background:#08152b; color:#f2f6ff; margin:0; padding:24px;
}}
h1,h2 {{ margin:0 0 14px 0; }}
.card {{
  background:#0d2450; border:1px solid #2f61ff; border-radius:16px;
  padding:16px; margin:14px 0;
}}
.small {{ color:#b8c8ff; }}
pre {{
  white-space:pre-wrap; word-wrap:break-word; background:#07162f; padding:12px; border-radius:12px;
}}
table {{
  width:100%; border-collapse:collapse; margin-top:12px;
}}
th,td {{
  border-bottom:1px solid #244a9d; padding:10px; text-align:left; vertical-align:top;
}}
.badge {{
  display:inline-block; padding:6px 12px; border-radius:999px; background:#f2b300; color:#111; font-weight:bold;
}}
</style>
</head>
<body>
<h1>LumenCore — Audit Grade Derivation Pack</h1>
<div class="small">{pack["generated_utc"]}</div>

<div class="card">
  <div class="badge">RESEARCH / PAPER AUDIT</div>
  <p>This page explains where claimed sector values come from, what each sector means, and whether paper trading has actual trade proof.</p>
</div>

<div class="card">
  <h2>Summary</h2>
  <pre>{json.dumps(pack["summary"], indent=2)}</pre>
</div>

<div class="card">
  <h2>Paper trade evidence</h2>
  <pre>{json.dumps(pack["paper_trade_evidence"], indent=2)}</pre>
</div>

<div class="card">
  <h2>Metric derivation warning</h2>
  <pre>{json.dumps(pack["metric_derivation"], indent=2)}</pre>
</div>

<div class="card">
  <h2>Sector explainer</h2>
  <table>
    <tr>
      <th>Sector</th>
      <th>Status</th>
      <th>Constraint</th>
      <th>Money Drain</th>
      <th>Year Value</th>
      <th>Interpretation</th>
    </tr>
"""
for sector, vals in sector_explainer.items():
    html += f"""
    <tr>
      <td>{sector}</td>
      <td>{vals["status"]}</td>
      <td>{vals["constraint_type"]}</td>
      <td>{vals["money_drain_mode"]}</td>
      <td>${vals["translated_value"]["year"]:,.2f}</td>
      <td>{vals["audit_interpretation"]}</td>
    </tr>
"""
html += f"""
  </table>
</div>

<div class="card">
  <h2>Chain of custody file</h2>
  <pre>{ledger_path}</pre>
</div>

</body>
</html>
"""

html_path = os.path.join(DASH, "audit_derivation_pack.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)

txt_path = os.path.join(OUT, "audit_derivation_pack_readout.txt")
with open(txt_path, "w", encoding="utf-8") as f:
    f.write(
        "LUMENCORE AUDIT DERIVATION PACK\\n"
        "===============================\\n"
        f"generated_utc: {pack['generated_utc']}\\n"
        f"enabled_registry_sources: {pack['summary']['enabled_registry_sources']}\\n"
        f"measured_sources: {pack['summary']['measured_sources']}\\n"
        f"adaptive_universe_count: {pack['summary']['adaptive_universe_count']}\\n"
        f"translated_yearly_value_total: {pack['summary']['translated_yearly_value_total']}\\n"
        f"paper_trade_pnl_audit_status: {pack['paper_trade_evidence']['pnl_audit_status']}\\n"
    )

print("WROTE:", pack_path)
print("WROTE:", ledger_path)
print("WROTE:", html_path)
print("WROTE:", txt_path)
print("DONE")