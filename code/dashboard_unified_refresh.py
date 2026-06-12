from pathlib import Path
from datetime import datetime, timezone
import json, math, statistics, time, os, traceback, sys, shutil, subprocess

def _pick_existing_path(candidates):
    resolved = [Path(p).expanduser() for p in candidates if p]
    for cand in resolved:
        if cand.exists():
            return cand
    return resolved[0] if resolved else Path.cwd().resolve()


def _resolve_stack_root() -> Path:
    env_root = os.getenv("LUMA_STACK_ROOT")
    return _pick_existing_path(
        [
            env_root,
            Path(__file__).resolve().parent.parent,
            Path.cwd().resolve(),
            r"C:\LumaTrader\INSTITUTIONAL_STACK_V2",
        ]
    )


def _resolve_dashboard_dir(stack_root: Path) -> Path:
    env_dash = os.getenv("LUMA_DASHBOARD_DIR")
    return _pick_existing_path(
        [
            env_dash,
            stack_root.parent / "dashboard",
            stack_root / "dashboard",
            r"C:\LumaTrader\dashboard",
        ]
    )


ROOT = _resolve_stack_root()
CONF = ROOT / "config"
OUT  = ROOT / "out"
DASH = _resolve_dashboard_dir(ROOT)

# Allow dashboard refresh to import engine/dashboard builders from the code folder
sys.path.insert(0, str(ROOT / "code"))

for p in [CONF, OUT, DASH]:
    p.mkdir(parents=True, exist_ok=True)

REG_PATH   = CONF / "live_source_registry.json"
SRC_PATH   = CONF / "live_sources.json"
CTRL_PATH  = CONF / "runtime_control.json"

PAPER_STATE_CANDIDATES = [
    OUT / "paper_trade_state.json",
    OUT / "paper_trader_state.json",
    OUT / "paper_state.json",
]
PAPER_LEDGER_CANDIDATES = [
    OUT / "paper_trade_real_api_ledger.jsonl",
    OUT / "paper_trade_ledger.jsonl",
    OUT / "paper_ledger.jsonl",
    OUT / "trade_ledger.jsonl",
]
PAPER_RUNTIME_CANDIDATES = [
    CONF / "paper_trader_runtime.json",
    CONF / "paper_trade_runtime.json",
    OUT / "paper_trade_runtime.json",
]

ROLLING_PERF_PATH   = OUT / "rolling_performance.json"
SECTOR_MATRIX_PATH  = OUT / "sector_value_matrix.json"
SOURCE_TRUTH_PATH   = OUT / "source_truth_table.json"
CHAIN_PATH          = OUT / "unified_dashboard_chain_of_custody_sha256.json"
GOV_SUMMARY_PATH    = OUT / "gov_live_canonical_summary.json"
ADV_VALIDATION_JSON = OUT / "advanced_fleet_validation.json"
ADV_VALIDATION_DASH = DASH / "advanced_fleet_validation.html"
MASTER_UNIFIED_DASH = DASH / "LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html"
PORTAL_DASH = DASH / "dashboard_portal.html"
PORTAL_INDEX = DASH / "index.html"
LUMA_EXPERIENCE_DASH = DASH / "luma_experience.html"
IIS_WWWROOT = Path(r"C:\inetpub\wwwroot")
IIS_MASTER_INDEX = IIS_WWWROOT / "index.html"
IIS_MASTER_COPY = IIS_WWWROOT / "LUMENCORE_MASTER_DASHBOARD_UNIFIED_20260425.html"
IIS_PORTAL_COPY = IIS_WWWROOT / "dashboard_portal.html"
IIS_PAPER_COPY = IIS_WWWROOT / "alpaca_paper_live_dashboard.html"
IIS_LAMASCOUT_COPY = IIS_WWWROOT / "lumascout_dashboard.html"
IIS_LUMA_EXPERIENCE_COPY = IIS_WWWROOT / "luma_experience.html"
IIS_PUBLISH_ACL_HELPER = ROOT / "code" / "GRANT_IIS_DASHBOARD_PUBLISH_ACCESS.ps1"
LANE_AUDIT_JSON = OUT / "lane_separation_audit.json"
LANE_AUDIT_DASH = DASH / "lane_separation_audit.html"
GOV_SNAP_DIR = OUT / "gov_live_snapshots"

GOV_COLLECTOR_CACHE = {"last_epoch": 0.0, "min_interval_sec": 900.0}
GOV_COLLECTOR_TIMEOUT_SEC = 45
LOOP_LOCK_PATH = OUT / "dashboard_unified_refresh.loop.lock"

PAPER_DASH_PATH     = DASH / "alpaca_paper_live_dashboard.html"
INFRA_DASH_PATH     = DASH / "infra_institutional_live_dashboard.html"
LUMASCOUT_SUMMARY_PATH = ROOT / "out" / "lumascout" / "artist_scout_summary.json"
LUMASCOUT_SUMMARY_EXPORT = ROOT / "out" / "lumascout" / "lumascout_summary.json"
LUMASCOUT_DASH_PATH     = DASH / "lumascout_dashboard.html"
LUMASCOUT_ROOT          = ROOT / "LamaScout"
LUMASCOUT_OUT           = LUMASCOUT_ROOT / "out"

PREMIUM_BUILDER_PATH = ROOT / "code" / "BUILD_ALL_PREMIUM_DASHBOARDS.py"
ADV_VALIDATION_BUILDER_PATH = ROOT / "code" / "ADVANCED_FLEET_VALIDATION.py"
MASTER_DASH_BUILDER_PATH = ROOT / "code" / "UNIFIED_MASTER_DASHBOARD_BUILDER.py"
LANE_AUDIT_BUILDER_PATH = ROOT / "code" / "VERIFY_LANE_SEPARATION.py"
CANONICAL_GOV_COLLECTOR_PATH = ROOT / "code" / "CANONICAL_GOV_DATA_COLLECTOR.py"

DEFAULT_SECTOR_VALUES = {
    "energy": 3913.75,
    "market_data": 646.40,
    "crypto_exec": 959.50,
    "broker": 707.00,
    "rates": 934.25,
    "weather": 888.80,
    "energy_lab": 858.50,
    "air_quality": 424.20,
    "macro": 555.50,
    "water": 505.00,
    "labor": 343.40,
    "space": 303.00,
    "demographic": 262.60,
    "internal": 250.00,
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def safe_float(x, default=0.0):
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def first_present(mapping, keys, default=None):
    if not isinstance(mapping, dict):
        return default
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return default


def first_present_multi(mappings, keys, default=None):
    for mapping in mappings:
        value = first_present(mapping, keys, None)
        if value is not None:
            return value
    return default

def read_json(path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def read_jsonl(path):
    rows = []
    try:
        if not path.exists():
            return rows
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        pass
    return rows

def pick_first_existing(candidates):
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]

def pct_returns(vals):
    out = []
    for i in range(1, len(vals)):
        a = safe_float(vals[i-1], 0.0)
        b = safe_float(vals[i], 0.0)
        if a != 0:
            out.append((b - a) / a)
    return out

def sharpe_from_equity(vals):
    rets = pct_returns(vals)
    if len(rets) < 2:
        return 0.0
    mu = statistics.mean(rets)
    sd = statistics.pstdev(rets)
    if sd == 0:
        return 0.0
    return round((mu / sd) * math.sqrt(len(rets)), 4)

def max_drawdown_from_equity(vals):
    if not vals:
        return 0.0
    peak = vals[0]
    max_dd = 0.0
    for v in vals:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return round(max_dd * 100.0, 4)

def sha256_file(path):
    import hashlib
    h = hashlib.sha256()
    if not Path(path).exists():
        return None
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def html_escape(s):
    return (
        str(s).replace("&","&amp;").replace("<","&lt;")
        .replace(">","&gt;").replace('"',"&quot;")
    )

def load_enabled_sources():
    cfg = read_json(SRC_PATH, {})
    enabled = {}
    if isinstance(cfg, dict):
        for k, v in cfg.items():
            if isinstance(v, dict):
                enabled[k] = bool(v.get("enabled", False))
    return enabled

def normalize_registry():
    reg = read_json(REG_PATH, {"sources": []})
    rows = reg.get("sources", []) if isinstance(reg, dict) else []
    out = []
    enabled_map = load_enabled_sources()

    for r in rows:
        source = str(r.get("source", "UNKNOWN"))
        sector = str(r.get("sector", "unknown"))
        status = str(r.get("status", "UNKNOWN"))
        row_count = int(safe_float(r.get("rows", 0), 0))
        last_probe_utc = str(r.get("last_probe_utc", ""))
        env = str(r.get("env", ""))
        enabled = enabled_map.get(source.lower(), enabled_map.get(source.replace("_SECRET","").replace("_KEY","").lower(), True))

        est_per_hour = round(DEFAULT_SECTOR_VALUES.get(sector, 250.0), 2)
        measured_flag = row_count > 1
        value_basis = "MEASURED" if measured_flag else "ESTIMATED"

        out.append({
            "source": source,
            "sector": sector,
            "status": status,
            "rows": row_count,
            "last_probe_utc": last_probe_utc,
            "env": env,
            "enabled": enabled,
            "estimated_hour_value": est_per_hour,
            "value_basis": value_basis
        })
    return out

def build_paper_metrics():
    state_path = pick_first_existing(PAPER_STATE_CANDIDATES)
    ledger_path = pick_first_existing(PAPER_LEDGER_CANDIDATES)
    runtime_path = pick_first_existing(PAPER_RUNTIME_CANDIDATES)

    state = read_json(state_path, {})
    runtime = read_json(runtime_path, {})
    ledger = read_jsonl(ledger_path)

    sources = [state, runtime]

    starting = safe_float(
        first_present_multi(
            sources,
            [
                "starting_capital",
                "starting_equity",
                "starting_capital_usd",
                "starting_equity_usd",
            ],
            100000.0,
        ),
        100000.0,
    )
    equity = safe_float(
        first_present_multi(
            sources,
            [
                "current_equity",
                "equity",
                "equity_usd",
                "current_equity_usd",
            ],
            starting,
        ),
        starting,
    )
    explicit_pnl = first_present_multi(
        sources,
        ["paper_profit", "paper_profit_usd", "pnl_usd", "pnl"],
        None,
    )
    pnl = round(safe_float(explicit_pnl, equity - starting), 2) if explicit_pnl is not None else round(equity - starting, 2)

    wins = int(safe_float(first_present_multi(sources, ["wins", "win_count"], 0), 0))
    losses = int(safe_float(first_present_multi(sources, ["losses", "loss_count"], 0), 0))
    trades = int(
        safe_float(
            first_present_multi(sources, ["trades", "trade_count", "total_trades"], wins + losses),
            wins + losses,
        )
    )
    last_symbol = str(first_present_multi(sources, ["last_symbol"], ""))
    last_side = str(first_present_multi(sources, ["last_side"], ""))

    eq_curve = []
    pnl_values = []
    closed_trade_pnls = []

    for row in ledger[-1000:]:
        eq = first_present(
            row,
            ["equity_after", "equity", "equity_usd", "account_equity", "current_equity"],
            None,
        )
        if eq is not None:
            eq_curve.append(safe_float(eq))
        row_pnl = first_present(row, ["pnl", "pnl_usd", "realized_pnl", "net_pnl"], None)
        if row_pnl is not None:
            pnl_values.append(safe_float(row_pnl))
            closed_trade_pnls.append(safe_float(row_pnl))

    if not eq_curve:
        eq_curve = [starting, equity]

    if wins == 0 and losses == 0 and closed_trade_pnls:
        wins = sum(1 for x in closed_trade_pnls if x > 0)
        losses = sum(1 for x in closed_trade_pnls if x < 0)
        trades = len(closed_trade_pnls)

    win_rate = round((wins / trades) * 100.0, 4) if trades > 0 else 0.0
    sharpe = sharpe_from_equity(eq_curve)
    max_dd = max_drawdown_from_equity(eq_curve)

    live_now = bool(runtime.get("live", True) or state or ledger)

    out = {
        "generated_utc": now_iso(),
        "live_now": live_now,
        "state_path": str(state_path),
        "ledger_path": str(ledger_path),
        "runtime_path": str(runtime_path),
        "starting_capital": round(starting, 2),
        "current_equity": round(equity, 2),
        "paper_profit": round(pnl, 2),
        "wins": wins,
        "losses": losses,
        "trades": trades,
        "win_rate_pct": win_rate,
        "paper_sharpe": sharpe,
        "paper_max_drawdown_pct": max_dd,
        "last_symbol": last_symbol,
        "last_side": last_side,
        "ledger_rows_scanned": len(ledger),
        "equity_curve_points": len(eq_curve),
        "value_basis": "MEASURED" if len(ledger) > 0 else "ESTIMATED"
    }
    ROLLING_PERF_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out

def build_infra_metrics():
    rows = normalize_registry()
    source_rows = []
    by_sector = {}

    for r in rows:
        source = str(r.get("source", "UNKNOWN"))
        sector = str(r.get("sector", "unknown"))
        status = str(r.get("status", "UNKNOWN"))
        row_count = int(r.get("rows", 0) or 0)
        est_hour = safe_float(r.get("estimated_hour_value", 0.0), 0.0)
        enabled = bool(r.get("enabled", False))
        live_key = status == "LIVE_KEY_PRESENT"
        measured = row_count > 1
        live_measured = enabled and live_key and measured

        if not enabled:
            failure_reason = "DISABLED"
        elif not live_key:
            failure_reason = "KEY_MISSING_OR_INVALID"
        elif not measured:
            failure_reason = "NO_USABLE_ROWS"
        else:
            failure_reason = "NONE"

        modeled_capture_pct = 0.35 if sector in {"energy", "rates", "market_data", "crypto_exec"} else 0.22
        annual_exposure = est_hour * 24.0 * 365.0
        exposure_20y = annual_exposure * 20.0
        modeled_annual_upside = annual_exposure * modeled_capture_pct

        source_row = {
            "source": source,
            "sector": sector,
            "status": status,
            "rows": row_count,
            "last_probe_utc": str(r.get("last_probe_utc", "")),
            "env": str(r.get("env", "")),
            "enabled": enabled,
            "estimated_hour_value": round(est_hour, 2),
            "value_basis": "MEASURED" if measured else "ESTIMATED",
            "live_key": live_key,
            "live_measured": live_measured,
            "failure_reason": failure_reason,
            "annual_exposure_usd": round(annual_exposure, 2),
            "exposure_20y_usd": round(exposure_20y, 2),
            "modeled_capture_pct": round(modeled_capture_pct * 100.0, 2),
            "modeled_annual_upside_usd": round(modeled_annual_upside, 2),
        }
        source_rows.append(source_row)

        s = by_sector.setdefault(sector, {
            "sector": sector,
            "enabled_sources": 0,
            "live_key_sources": 0,
            "live_measured_sources": 0,
            "failing_sources": 0,
            "rows": 0,
            "hour": 0.0,
            "annual_exposure_usd": 0.0,
            "exposure_20y_usd": 0.0,
            "modeled_annual_upside_usd": 0.0,
        })
        s["enabled_sources"] += 1 if enabled else 0
        s["live_key_sources"] += 1 if live_key else 0
        s["live_measured_sources"] += 1 if live_measured else 0
        s["failing_sources"] += 1 if enabled and not live_measured else 0
        s["rows"] += row_count
        s["hour"] += est_hour
        s["annual_exposure_usd"] += annual_exposure
        s["exposure_20y_usd"] += exposure_20y
        s["modeled_annual_upside_usd"] += modeled_annual_upside

    sector_matrix = []
    for item in by_sector.values():
        hour = round(item["hour"], 2)
        day = round(hour * 24.0, 2)
        week = round(day * 7.0, 2)
        month = round(day * 30.0, 2)
        year = round(day * 365.0, 2)
        sector_matrix.append({
            "sector": item["sector"],
            "site": "ALL",
            "live_sources": item["live_measured_sources"],
            "rows": item["rows"],
            "hour": hour,
            "day": day,
            "week": week,
            "month": month,
            "year": year,
            "basis": "MEASURED" if item["live_measured_sources"] > 0 else "ESTIMATED",
            "failure_count": item["failing_sources"],
            "annual_exposure_usd": round(item["annual_exposure_usd"], 2),
            "exposure_20y_usd": round(item["exposure_20y_usd"], 2),
            "modeled_annual_upside_usd": round(item["modeled_annual_upside_usd"], 2),
        })

    sector_matrix.sort(key=lambda x: x["annual_exposure_usd"], reverse=True)
    high_priority_failures = [x for x in source_rows if x["enabled"] and not x["live_measured"]]
    high_priority_failures.sort(key=lambda x: x["annual_exposure_usd"], reverse=True)
    live_measured_sources = [x for x in source_rows if x["live_measured"]]
    live_measured_sources.sort(key=lambda x: x["annual_exposure_usd"], reverse=True)

    totals = {
        "generated_utc": now_iso(),
        "enabled_sources": sum(1 for r in source_rows if r["enabled"]),
        "registry_detected_sources": len(source_rows),
        "sector_count": len(sector_matrix),
        "live_key_sources": sum(1 for r in source_rows if r["live_key"]),
        "live_measured_sources": sum(1 for r in source_rows if r["live_measured"]),
        "failing_enabled_sources": len(high_priority_failures),
        "estimated_hourly_preserved_value": round(sum(x["hour"] for x in sector_matrix), 2),
        "daily_translated_value": round(sum(x["day"] for x in sector_matrix), 2),
        "weekly_translated_value": round(sum(x["week"] for x in sector_matrix), 2),
        "monthly_translated_value": round(sum(x["month"] for x in sector_matrix), 2),
        "yearly_translated_value": round(sum(x["year"] for x in sector_matrix), 2),
        "annual_exposure_usd": round(sum(x["annual_exposure_usd"] for x in source_rows), 2),
        "exposure_20y_usd": round(sum(x["exposure_20y_usd"] for x in source_rows), 2),
        "modeled_annual_upside_usd": round(sum(x["modeled_annual_upside_usd"] for x in source_rows), 2),
        "top_current_optimization_lane": sector_matrix[0]["sector"] if sector_matrix else "n/a",
        "top_current_lane_hour_value": sector_matrix[0]["hour"] if sector_matrix else 0.0,
        "measured_source_rows": sum(int(r["rows"]) for r in source_rows),
        "sources_with_measured_rows": sum(1 for r in source_rows if int(r["rows"]) > 1),
        "sources_with_estimate_only": sum(1 for r in source_rows if int(r["rows"]) <= 1),
        "sector_value_matrix": sector_matrix,
        "source_truth_rows": source_rows,
        "high_priority_failures": high_priority_failures[:20],
        "live_measured_source_table": live_measured_sources[:20],
    }

    SECTOR_MATRIX_PATH.write_text(json.dumps(totals, indent=2), encoding="utf-8")
    SOURCE_TRUTH_PATH.write_text(json.dumps({"generated_utc": now_iso(), "rows": source_rows}, indent=2), encoding="utf-8")
    return totals


def build_lumascout_metrics():
    summary = read_json(LUMASCOUT_SUMMARY_PATH, None)
    if summary is None and LUMASCOUT_OUT.exists():
        summary = read_json(LUMASCOUT_OUT / "artist_scout_summary.json", None)
    if summary is None and LUMASCOUT_SUMMARY_EXPORT.exists():
        summary = read_json(LUMASCOUT_SUMMARY_EXPORT, None)
    if summary is None:
        return {
            "generated_utc": now_iso(),
            "total_artists": 0,
            "live_artists": 0,
            "champions": 0,
            "watchlist": 0,
            "portfolio_size": 0,
            "top_artist": "n/a",
            "top_live_artist": "n/a",
            "hot_radar_count": 0,
            "top_prospect_count": 0,
            "delta_runs": 0,
            "last_checksum": "n/a",
            "previous_checksum": "n/a",
            "source": "LumaScout",
            "status": "missing",
        }
    return {
        "generated_utc": summary.get("generated_utc", now_iso()),
        "total_artists": int(summary.get("total_artists", 0)),
        "live_artists": int(summary.get("live_artists", 0)),
        "champions": int(summary.get("champions", 0)),
        "watchlist": int(summary.get("watchlist", 0)),
        "portfolio_size": int(summary.get("portfolio_size", 0)),
        "top_artist": str(summary.get("top_artist", "n/a")),
        "top_live_artist": str(summary.get("top_live_artist", "n/a")),
        "hot_radar_count": int(summary.get("hot_radar_count", 0)),
        "top_prospect_count": int(summary.get("top_prospect_count", 0)),
        "delta_runs": int(summary.get("delta_runs", 0)),
        "last_checksum": str(summary.get("last_checksum", "n/a")),
        "previous_checksum": str(summary.get("previous_checksum", "n/a")),
        "status": str(summary.get("status", "ready")),
        "source": "LumaScout",
    }


def build_lumascout_dashboard(summary: dict):
    html = f"""
    <html><head><meta charset='utf-8'><title>LumaScout Integration Dashboard</title>{css()}</head><body>
    <h1>LumaScout — Talent Discovery Summary</h1>
    <div class='sub'>Embedded LumaScout run proof and champion discovery signals integrated into the root dashboard pipeline.</div>
    <div class='grid'>
      <div class='card'><div class='label'>Total artists scanned</div><div class='value'>{summary['total_artists']}</div></div>
      <div class='card'><div class='label'>Live artists</div><div class='value'>{summary['live_artists']}</div></div>
      <div class='card'><div class='label'>Champions</div><div class='value'>{summary['champions']}</div></div>
      <div class='card'><div class='label'>Watchlist</div><div class='value'>{summary['watchlist']}</div></div>
      <div class='card'><div class='label'>Portfolio size</div><div class='value'>{summary['portfolio_size']}</div></div>
      <div class='card'><div class='label'>Hot radar count</div><div class='value'>{summary['hot_radar_count']}</div></div>
      <div class='card'><div class='label'>Top prospect count</div><div class='value'>{summary['top_prospect_count']}</div></div>
      <div class='card'><div class='label'>Top artist</div><div class='value'>{html_escape(summary['top_artist'])}</div></div>
      <div class='card'><div class='label'>Top live artist</div><div class='value'>{html_escape(summary['top_live_artist'])}</div></div>
      <div class='card'><div class='label'>Status</div><div class='value'>{html_escape(summary['status'])}</div></div>
      <div class='card'><div class='label'>Delta runs</div><div class='value'>{summary['delta_runs']}</div></div>
    </div>
    <div class='grid'>
      <div class='card'><div class='label'>Last checksum</div><div class='value'>{html_escape(summary['last_checksum'])}</div></div>
      <div class='card'><div class='label'>Previous checksum</div><div class='value'>{html_escape(summary['previous_checksum'])}</div></div>
    </div>
    <div class='card'><div class='small'>Generated UTC: {html_escape(summary['generated_utc'])}</div>
    <div class='small'>Source: {html_escape(summary.get('source', 'LumaScout'))}</div></div>
    </body></html>
    """
    LUMASCOUT_DASH_PATH.write_text(html, encoding='utf-8')
    return summary


def build_chain():
    files = [
        REG_PATH, SRC_PATH, CTRL_PATH,
        ROLLING_PERF_PATH, SECTOR_MATRIX_PATH, SOURCE_TRUTH_PATH,
        PAPER_DASH_PATH, INFRA_DASH_PATH, LUMASCOUT_DASH_PATH, PORTAL_DASH, PORTAL_INDEX,
        ADV_VALIDATION_JSON, ADV_VALIDATION_DASH, MASTER_UNIFIED_DASH,
        LANE_AUDIT_JSON, LANE_AUDIT_DASH,
        GOV_SUMMARY_PATH,
    ]
    payload = {"generated_utc": now_iso(), "files": []}
    for f in files:
        payload["files"].append({
            "path": str(f),
            "exists": f.exists(),
            "sha256": sha256_file(f) if f.exists() else None
        })
    CHAIN_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_external_dashboards():
    if not PREMIUM_BUILDER_PATH.exists():
        lumascout = build_lumascout_dashboard(build_lumascout_metrics())
        return {
            "status": "skipped",
            "reason": "premium_builder_missing",
            "builder": str(PREMIUM_BUILDER_PATH),
            "lumascout": lumascout,
        }

    try:
        import BUILD_ALL_PREMIUM_DASHBOARDS as premium_dashboards
        premium_dashboards.main()
        return {
            "status": "ok",
            "portal": str(PORTAL_DASH),
            "paper": str(PAPER_DASH_PATH),
            "lumascout": str(LUMASCOUT_DASH_PATH),
        }
    except (Exception, SystemExit) as e:
        print(f"[PREMIUM] Failed to build premium dashboards: {e}")
        traceback.print_exc()
        lumascout = build_lumascout_dashboard(build_lumascout_metrics())
        return {
            "status": "fallback",
            "lumascout": lumascout,
            "error": str(e),
        }


def build_advanced_validation_dashboard():
    if not ADV_VALIDATION_BUILDER_PATH.exists():
        return {
            "status": "skipped",
            "reason": "advanced_validation_builder_missing",
            "builder": str(ADV_VALIDATION_BUILDER_PATH),
        }

    try:
        import ADVANCED_FLEET_VALIDATION as adv
        return adv.main()
    except Exception as e:
        print(f"[ADVANCED] Failed to build advanced validation dashboard: {e}")
        traceback.print_exc()
        return {}


def build_master_unified_dashboard():
    if not MASTER_DASH_BUILDER_PATH.exists():
        return {
            "status": "skipped",
            "reason": "master_dashboard_builder_missing",
            "builder": str(MASTER_DASH_BUILDER_PATH),
        }

    try:
        import UNIFIED_MASTER_DASHBOARD_BUILDER as master_builder
        master_builder.main()
        return {"status": "ok", "path": str(MASTER_UNIFIED_DASH)}
    except Exception as e:
        print(f"[MASTER] Failed to build master unified dashboard: {e}")
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def publish_master_dashboard_to_iis() -> dict:
    """Best-effort copy of the portal and dashboard artifacts into IIS webroot."""
    try:
        if not PORTAL_INDEX.exists():
            return {"status": "skipped", "reason": "portal_index_missing"}
        if not IIS_WWWROOT.exists():
            return {"status": "skipped", "reason": "iis_webroot_missing"}

        if PORTAL_DASH.exists():
            shutil.copy2(PORTAL_DASH, IIS_PORTAL_COPY)
        shutil.copy2(PORTAL_INDEX, IIS_MASTER_INDEX)
        shutil.copy2(MASTER_UNIFIED_DASH, IIS_MASTER_COPY)
        if PAPER_DASH_PATH.exists():
            shutil.copy2(PAPER_DASH_PATH, IIS_PAPER_COPY)
        if LUMASCOUT_DASH_PATH.exists():
            shutil.copy2(LUMASCOUT_DASH_PATH, IIS_LAMASCOUT_COPY)
        if LUMA_EXPERIENCE_DASH.exists():
            shutil.copy2(LUMA_EXPERIENCE_DASH, IIS_LUMA_EXPERIENCE_COPY)
        return {
            "status": "ok",
            "index": str(IIS_MASTER_INDEX),
            "portal": str(IIS_PORTAL_COPY),
            "unified": str(IIS_MASTER_COPY),
            "paper": str(IIS_PAPER_COPY),
            "lumascout": str(IIS_LAMASCOUT_COPY),
            "immersive": str(IIS_LUMA_EXPERIENCE_COPY),
        }
    except PermissionError as e:
        return {
            "status": "error",
            "reason": "iis_webroot_acl_denied",
            "error": str(e),
            "helper": str(IIS_PUBLISH_ACL_HELPER),
        }
    except Exception as e:
        # Keep refresh loop alive even if IIS publish permissions are restricted.
        return {"status": "error", "error": str(e)}


def build_lane_audit_dashboard():
    if not LANE_AUDIT_BUILDER_PATH.exists():
        return {
            "status": "skipped",
            "reason": "lane_audit_builder_missing",
            "builder": str(LANE_AUDIT_BUILDER_PATH),
        }

    try:
        import VERIFY_LANE_SEPARATION as lane
        lane.main()
        return {"status": "ok", "json": str(LANE_AUDIT_JSON), "dash": str(LANE_AUDIT_DASH)}
    except Exception as e:
        print(f"[LANE] Failed to build lane separation audit: {e}")
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def run_canonical_gov_collector_throttled():
    now = time.time()
    if now - GOV_COLLECTOR_CACHE["last_epoch"] < GOV_COLLECTOR_CACHE["min_interval_sec"]:
        return {"status": "skipped", "reason": "throttled"}

    if not CANONICAL_GOV_COLLECTOR_PATH.exists():
        return {
            "status": "skipped",
            "reason": "collector_missing",
            "collector": str(CANONICAL_GOV_COLLECTOR_PATH),
        }

    try:
        completed = subprocess.run(
            [sys.executable, str(CANONICAL_GOV_COLLECTOR_PATH)],
            capture_output=True,
            text=True,
            timeout=GOV_COLLECTOR_TIMEOUT_SEC,
            check=False,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            detail = stderr or stdout or f"collector exited with code {completed.returncode}"
            print(f"[GOV] Collector non-zero exit: {detail}")
            return {"status": "error", "error": detail}

        result = read_json(GOV_SUMMARY_PATH, {})
        if not isinstance(result, dict) or not result:
            return {"status": "error", "error": "collector completed without summary payload"}
        GOV_COLLECTOR_CACHE["last_epoch"] = now
        return {"status": "ok", "rows_total": result.get("rows_total", 0), "sources_ok": result.get("sources_ok", 0)}
    except subprocess.TimeoutExpired:
        print(f"[GOV] Collector timed out after {GOV_COLLECTOR_TIMEOUT_SEC}s; continuing refresh without new gov snapshot")
        return {"status": "error", "error": f"timeout_after_{GOV_COLLECTOR_TIMEOUT_SEC}s"}
    except Exception as e:
        print(f"[GOV] Collector failed: {e}")
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def render_table(headers, rows):
    head = "".join(f"<th>{html_escape(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html_escape(v)}</td>" for v in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"

def css():
    return """
    <style>
    body{font-family:Segoe UI,Arial,sans-serif;background:#091225;color:#f5f8ff;margin:0;padding:24px}
    h1{font-size:28px;margin:0 0 6px 0}
    .sub{opacity:.82;margin-bottom:18px}
    .grid{display:grid;grid-template-columns:repeat(4,minmax(180px,1fr));gap:14px;margin-bottom:18px}
    .card{background:#0f1d3a;border:1px solid #223d72;border-radius:14px;padding:16px;box-shadow:0 10px 30px rgba(0,0,0,.20)}
    .label{font-size:12px;text-transform:uppercase;opacity:.78;margin-bottom:8px}
    .value{font-size:22px;font-weight:700}
    .small{font-size:12px;opacity:.85;margin-top:6px}
    table{width:100%;border-collapse:collapse;background:#0f1d3a;border:1px solid #223d72;border-radius:12px;overflow:hidden}
    th,td{padding:10px 8px;border-bottom:1px solid #1d3563;font-size:13px;text-align:left}
    th{background:#12254a}
    .section{margin-top:18px}
    .pill{display:inline-block;padding:2px 8px;border-radius:999px;background:#1c3768}
    .ok{color:#8ff0a4}
    .warn{color:#ffd479}
    .mono{font-family:Consolas,monospace}
    </style>
    """

def build_paper_dashboard(p):
    html = f"""
    <html><head><meta charset='utf-8'><title>LumenCore Paper Dashboard</title>{css()}</head><body>
    <h1>LumenCore — Alpaca Paper Live Dashboard</h1>
    <div class='sub'>Continuous paper-trading proof loop with ledger, state snapshots, and chain-of-custody hashes.</div>
    <div class='grid'>
      <div class='card'><div class='label'>Starting capital</div><div class='value'>${p['starting_capital']:,.2f}</div></div>
      <div class='card'><div class='label'>Current equity</div><div class='value'>${p['current_equity']:,.2f}</div></div>
      <div class='card'><div class='label'>Paper profit</div><div class='value'>${p['paper_profit']:,.2f}</div></div>
      <div class='card'><div class='label'>Trades</div><div class='value'>{p['trades']}</div></div>
      <div class='card'><div class='label'>Wins</div><div class='value'>{p['wins']}</div></div>
      <div class='card'><div class='label'>Losses</div><div class='value'>{p['losses']}</div></div>
      <div class='card'><div class='label'>Paper Sharpe</div><div class='value'>{p['paper_sharpe']}</div></div>
      <div class='card'><div class='label'>Paper Max Drawdown</div><div class='value'>{p['paper_max_drawdown_pct']}%</div></div>
      <div class='card'><div class='label'>Paper Win Rate</div><div class='value'>{p['win_rate_pct']}%</div></div>
      <div class='card'><div class='label'>Last symbol</div><div class='value'>{html_escape(p['last_symbol'])}</div></div>
      <div class='card'><div class='label'>Last side</div><div class='value'>{html_escape(p['last_side'])}</div></div>
      <div class='card'><div class='label'>Value basis</div><div class='value'>{html_escape(p['value_basis'])}</div></div>
    </div>
    <div class='card'><div class='small'>Generated UTC: {html_escape(p['generated_utc'])}</div>
    <div class='small'>Ledger rows scanned: {p['ledger_rows_scanned']} | Equity curve points: {p['equity_curve_points']}</div>
    <div class='small'>Proof files: rolling_performance.json, unified_dashboard_chain_of_custody_sha256.json</div></div>
    </body></html>
    """
    PAPER_DASH_PATH.write_text(html, encoding="utf-8")

def build_infra_dashboard(m, p):
    try:
        matrix_rows = []
        for r in m.get("sector_value_matrix", []):
            matrix_rows.append([
                r.get("sector", "n/a"),
                r.get("live_sources", 0),
                r.get("failure_count", 0),
                r.get("rows", 0),
                f"${safe_float(r.get('hour', 0.0)):,.2f}",
                f"${safe_float(r.get('annual_exposure_usd', 0.0)):,.2f}",
                f"${safe_float(r.get('exposure_20y_usd', 0.0)):,.2f}",
                f"${safe_float(r.get('modeled_annual_upside_usd', 0.0)):,.2f}",
                r.get("basis", "ESTIMATED"),
            ])

        failure_rows = []
        for r in m.get("high_priority_failures", []):
            failure_rows.append([
                r.get("source", "n/a"),
                r.get("sector", "n/a"),
                r.get("status", "UNKNOWN"),
                r.get("failure_reason", "UNKNOWN"),
                r.get("rows", 0),
                f"${safe_float(r.get('estimated_hour_value', 0.0)):,.2f}",
                f"${safe_float(r.get('annual_exposure_usd', 0.0)):,.2f}",
                f"${safe_float(r.get('exposure_20y_usd', 0.0)):,.2f}",
                f"${safe_float(r.get('modeled_annual_upside_usd', 0.0)):,.2f}",
                f"{safe_float(r.get('modeled_capture_pct', 0.0)):.2f}%",
                r.get("last_probe_utc", ""),
            ])

        live_rows = []
        for r in m.get("live_measured_source_table", []):
            live_rows.append([
                r.get("source", "n/a"),
                r.get("sector", "n/a"),
                r.get("rows", 0),
                f"${safe_float(r.get('estimated_hour_value', 0.0)):,.2f}",
                f"${safe_float(r.get('annual_exposure_usd', 0.0)):,.2f}",
                r.get("last_probe_utc", ""),
            ])

        html = f"""
        <html><head><meta charset='utf-8'><title>LumenCore Institutional Infrastructure Live Dashboard</title>{css()}</head><body>
        <h1>LumenCore — Institutional Infrastructure Live Dashboard</h1>
        <div class='sub'>Production truth only: live-measured source coverage, failed-source exposure, and sector-level 20-year cost attribution.</div>

        <div class='grid'>
                <div class='card'><div class='label'>Enabled sources</div><div class='value'>{m['enabled_sources']}</div></div>
                <div class='card'><div class='label'>Live key sources</div><div class='value'>{m['live_key_sources']}</div></div>
                <div class='card'><div class='label'>Live measured sources</div><div class='value'>{m['live_measured_sources']}</div></div>
                <div class='card'><div class='label'>Failing enabled sources</div><div class='value'>{m['failing_enabled_sources']}</div></div>

                <div class='card'><div class='label'>Hourly value (all enabled)</div><div class='value'>${m['estimated_hourly_preserved_value']:,.2f}</div></div>
                <div class='card'><div class='label'>Annual exposure</div><div class='value'>${m['annual_exposure_usd']:,.2f}</div></div>
                <div class='card'><div class='label'>20-year exposure</div><div class='value'>${m['exposure_20y_usd']:,.2f}</div></div>
                <div class='card'><div class='label'>Modeled annual upside</div><div class='value'>${m['modeled_annual_upside_usd']:,.2f}</div></div>

                <div class='card'><div class='label'>Paper Sharpe</div><div class='value'>{p['paper_sharpe']}</div></div>
                <div class='card'><div class='label'>Paper Max Drawdown</div><div class='value'>{p['paper_max_drawdown_pct']}%</div></div>
                <div class='card'><div class='label'>Paper Win Rate</div><div class='value'>{p['win_rate_pct']}%</div></div>
                <div class='card'><div class='label'>Paper PnL</div><div class='value'>${p['paper_profit']:,.2f}</div></div>
        </div>

        <div class='section card'>
                <h3>Sector Priority Matrix</h3>
                {render_table(
                        ["Sector","Live Measured Sources","Failing Sources","Rows","Hourly","Annual Exposure","20Y Exposure","Modeled Annual Upside","Basis"],
                        matrix_rows
                )}
        </div>

        <div class='section card'>
            <h3>High-Priority Failed Sources (Production Fix Queue)</h3>
            {render_table(
                ["Source","Sector","Status","Failure Reason","Rows","Est $/hr","Annual Exposure","20Y Exposure","Modeled Annual Upside","Modeled Capture %","Last Probe UTC"],
                failure_rows
            )}
        </div>

        <div class='section card'>
            <h3>Live-Measured Production Sources</h3>
            {render_table(
                ["Source","Sector","Rows","Est $/hr","Annual Exposure","Last Probe UTC"],
                live_rows
            )}
        </div>

        <div class='section card'>
            <h3>Investor / reviewer readout</h3>
            <p><b>What this proves</b>: only sources with live key + measured rows are counted as production evidence.</p>
            <p><b>Failure attribution</b>: each failed source shows the failure mode plus annual and 20-year exposure if left unresolved.</p>
            <p><b>Modeled upside</b>: annual upside uses a transparent sector capture-rate model (22%-35%) and is explicitly marked modeled.</p>
            <p class='mono'>Generated UTC: {html_escape(m['generated_utc'])}</p>
            <p class='mono'>Proof files: live_source_registry.json, live_sources.json, rolling_performance.json, sector_value_matrix.json, source_truth_table.json, unified_dashboard_chain_of_custody_sha256.json</p>
        </div>
        </body></html>
        """
        INFRA_DASH_PATH.write_text(html, encoding="utf-8")
    except Exception as e:
        # Always write a minimal dashboard file on error
        error_html = f"""
        <html><head><meta charset='utf-8'><title>Dashboard Error</title></head><body>
        <h1>Dashboard Generation Error</h1>
        <pre>{html_escape(str(e))}</pre>
        </body></html>
        """
        INFRA_DASH_PATH.write_text(error_html, encoding="utf-8")

def refresh_once():
    try:
        p = build_paper_metrics()
        m = build_infra_metrics()
        build_paper_dashboard(p)
        build_infra_dashboard(m, p)
        build_external_dashboards()
        run_canonical_gov_collector_throttled()
        build_advanced_validation_dashboard()
        build_master_unified_dashboard()
        iis_publish = publish_master_dashboard_to_iis()
        build_lane_audit_dashboard()
        build_chain()
        if isinstance(iis_publish, dict) and iis_publish.get("status") != "ok":
            print(f"[{now_iso()}] iis publish: {iis_publish}")
        print(f"[{now_iso()}] unified dashboards refreshed")
    except Exception as e:
        print(f"[{now_iso()}] refresh error: {e}")
        traceback.print_exc()


def loop():
    while True:
        refresh_once()
        time.sleep(60)


def pid_is_running(pid) -> bool:
    try:
        pid = int(pid)
    except Exception:
        return False

    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def acquire_loop_lock() -> bool:
    """Prevent duplicate loop workers from writing dashboards simultaneously."""
    try:
        LOOP_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(LOOP_LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        payload = {
            "pid": os.getpid(),
            "created_utc": now_iso(),
            "note": "singleton lock for dashboard_unified_refresh --loop",
        }
        os.write(fd, json.dumps(payload).encode("utf-8"))
        os.close(fd)
        return True
    except FileExistsError:
        # Recycle stale locks when the owner PID is gone or the file is too old.
        try:
            payload = read_json(LOOP_LOCK_PATH, {})
            owner_pid = payload.get("pid") if isinstance(payload, dict) else None
            if owner_pid and not pid_is_running(owner_pid):
                LOOP_LOCK_PATH.unlink(missing_ok=True)
                return acquire_loop_lock()

            age_sec = time.time() - LOOP_LOCK_PATH.stat().st_mtime
            if age_sec > 21600:
                LOOP_LOCK_PATH.unlink(missing_ok=True)
                return acquire_loop_lock()
        except Exception:
            pass
        return False
    except Exception:
        return False


def release_loop_lock():
    try:
        LOOP_LOCK_PATH.unlink(missing_ok=True)
    except Exception:
        pass

if __name__ == "__main__":
    if "--loop" in sys.argv:
        if not acquire_loop_lock():
            print(f"[{now_iso()}] loop already running; exiting duplicate worker")
            raise SystemExit(0)
        try:
            loop()
        finally:
            release_loop_lock()
    else:
        refresh_once()
