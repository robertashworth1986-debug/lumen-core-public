import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONF = ROOT / "config"
OUT  = ROOT / "out"

LIVE_REGISTRY = CONF / "live_source_registry.json"
SOURCE_TRUTH  = OUT / "source_truth_table.json"
PAPER_RUNTIME = CONF / "paper_trader_runtime.json"
RUNTIME_CTRL  = CONF / "runtime_control.json"
ADAPTIVE_UNI  = OUT  / "adaptive_universe.json"

ENGINE_AUDIT  = OUT  / "engine_truth_audit.json"
UNI_SUMMARY   = OUT  / "adaptive_universe_summary.json"

def now_utc():
    return datetime.now(timezone.utc).isoformat()

def load_json(path, default):
    try:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")

registry = load_json(LIVE_REGISTRY, {})
truth    = load_json(SOURCE_TRUTH, {})
paper    = load_json(PAPER_RUNTIME, {})
runtime  = load_json(RUNTIME_CTRL, {})
adaptive = load_json(ADAPTIVE_UNI, {})

registry_rows = []
if isinstance(registry, dict):
    registry_rows = registry.get("rows", registry.get("sources", []))
truth_rows = []
if isinstance(truth, dict):
    truth_rows = truth.get("rows", truth.get("sources", []))
uni_rows = adaptive.get("symbols", []) if isinstance(adaptive, dict) else []

# Build lookup from source_truth_table first
truth_map = {}
for r in truth_rows:
    if not isinstance(r, dict):
        continue
    src = str(r.get("source", "")).strip().upper()
    if not src:
        continue
    truth_map[src] = r

enabled_count = 0
measured_count = 0
enabled_sources = []
measured_sources = []
sector_rollup = {}

for r in registry_rows:
    if not isinstance(r, dict):
        continue

    src = str(r.get("source", "")).strip()
    src_key = src.upper()
    sector = str(r.get("sector", "unknown")).strip()
    status = str(r.get("status", "")).strip().upper()
    rows = int(r.get("rows", 0) or 0)

    t = truth_map.get(src_key, {})
    t_rows = int(t.get("rows", 0) or 0)
    evidence_basis = str(t.get("evidence_basis", r.get("evidence_basis", ""))).strip().upper()
    dollar_basis   = str(t.get("dollar_basis", r.get("dollar_basis", ""))).strip().upper()

    enabled = (
        status in ("LIVE_KEY_PRESENT", "KEY_PRESENT_UNMEASURED")
        or bool(r.get("enabled", False))
    )

    measured = (
        rows > 0
        or t_rows > 0
        or evidence_basis == "MEASURED_FILE_MATCH"
        or dollar_basis == "MEASURED"
    )

    if enabled:
        enabled_count += 1
        enabled_sources.append(src)

        sector_rollup.setdefault(sector, {"live_sources": 0, "rows": 0})
        sector_rollup[sector]["live_sources"] += 1
        sector_rollup[sector]["rows"] += max(rows, t_rows)

    if enabled and measured:
        measured_count += 1
        measured_sources.append(src)

adaptive_count = len(uni_rows) if isinstance(uni_rows, list) else 0

static_symbol_risk = False
audit_notes = []

for field in ["symbols", "static_symbols", "legacy_symbols", "manual_symbols"]:
    vals = paper.get(field, [])
    if isinstance(vals, list) and len(vals) > 0:
        static_symbol_risk = True
        audit_notes.append(f"{field}_count={len(vals)}")

if runtime.get("symbol") != "UNIVERSE":
    static_symbol_risk = True
    audit_notes.append(f"runtime_control.symbol={runtime.get('symbol')}")

if str(paper.get("selection_source", "")) != "engine_logic":
    static_symbol_risk = True
    audit_notes.append(f"selection_source={paper.get('selection_source')}")

if str(paper.get("symbol_mode", "")) != "ADAPTIVE_UNIVERSE":
    static_symbol_risk = True
    audit_notes.append(f"symbol_mode={paper.get('symbol_mode')}")

if not audit_notes:
    audit_notes.append("static basket cleared; engine now reads adaptive universe; measured-source audit rebuilt")

engine_audit = {
    "generated_utc": now_utc(),
    "engine_symbol": runtime.get("symbol"),
    "paper_enabled": bool(paper.get("paper_enabled", False)),
    "selection_source": paper.get("selection_source"),
    "symbol_mode": paper.get("symbol_mode"),
    "enabled_registry_sources": enabled_count,
    "measured_sources": measured_count,
    "adaptive_universe_count": adaptive_count,
    "static_symbol_risk": static_symbol_risk,
    "enabled_sources": enabled_sources,
    "measured_source_names": measured_sources,
    "audit_notes": audit_notes
}
save_json(ENGINE_AUDIT, engine_audit)

summary = {
    "generated_utc": now_utc(),
    "enabled_registry_sources": enabled_count,
    "measured_sources": measured_count,
    "sector_count": len(sector_rollup),
    "sector_rollup": sector_rollup,
    "adaptive_universe_count": adaptive_count,
    "top_symbols": [x.get("symbol") for x in uni_rows[:25]] if isinstance(uni_rows, list) else [],
    "measured_source_names": measured_sources
}
save_json(UNI_SUMMARY, summary)

print("MEASURED SOURCE AUDIT REBUILT")
print("enabled_registry_sources:", enabled_count)
print("measured_sources:", measured_count)
print("adaptive_universe_count:", adaptive_count)
print("engine_truth_audit:", ENGINE_AUDIT)
print("adaptive_universe_summary:", UNI_SUMMARY)