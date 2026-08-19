import os, sys, json, csv, time, math, subprocess, traceback, re
from pathlib import Path
from datetime import datetime, timezone
import urllib.request
import pandas as pd
import numpy as np
from runtime_live_lock import is_strict_live_locked, stamp_runtime_writer
from execution.live_action_authority import validate_live_action_authority
try:
    import yaml
except ImportError:
    yaml = None
from modular_hypercompounder_filter import HyperCompounderFilter, momentum_breakout_score
from external_data_sources import fetch_coingecko_market_data, fetch_binance_ohlc, fetch_kraken_ohlc, get_all_binance_symbols, get_all_kraken_symbols
from hybrid_harmonic_algorithms import ALGO_WRAPPERS
from hybrid_harmonic_strategies import strat_harmonic_consensus

ROOT = Path(os.getenv("LUMA_ROOT", str(Path(__file__).resolve().parents[1]))).resolve()
WORKSPACE_ROOT = ROOT.parent
CODE = ROOT / "code"
CONF = ROOT / "config"
OUT  = ROOT / "out"
DASH = WORKSPACE_ROOT / "dashboard"

DATA_ROOTS = [
    ROOT / "data",
    WORKSPACE_ROOT / "data",
    Path.home() / "iCloudDrive" / "Data sets",
    Path.home() / "iCloudDrive" / "Data_sets",
    Path.home() / "iCloudDrive" / "Documents" / "Data sets",
]

for _extra in [s.strip() for s in os.getenv("LUMA_EXTRA_DATA_ROOTS", "").split(";") if s.strip()]:
    DATA_ROOTS.append(Path(_extra))

LIVE_SOURCES_PATH          = CONF / "live_sources.json"
LIVE_SOURCE_REGISTRY_PATH  = CONF / "live_source_registry.json"
RUNTIME_CONTROL_PATH       = CONF / "runtime_control.json"
PAPER_RUNTIME_PATH         = CONF / "paper_trader_runtime.json"
INFRA_RUNTIME_PATH         = CONF / "infra_live_runtime.json"

DATASET_CATALOG_CSV        = OUT / "dataset_catalog_live.csv"
DATASET_SCAN_SUMMARY_CSV   = OUT / "data_scan_summary_live.csv"
DATA_INGEST_PROOF_JSON     = OUT / "data_ingest_proof_live.json"
SOURCE_TRUTH_TABLE_JSON    = OUT / "source_truth_table.json"
TRUTH_STATUS_JSON          = OUT / "truth_orchestrator_status.json"

LUMASCOUT_API_REGISTRY     = ROOT / "LamaScout" / "config" / "api_registry.yaml"
LUMASCOUT_TRUTH_SUMMARY    = ROOT / "LamaScout" / "out" / "truth_engine_summary.json"
LUMASCOUT_RUN_PROOF        = ROOT / "LamaScout" / "reports" / "artist_scout_run_proof.json"
LUMASCOUT_DELTA_HISTORY    = ROOT / "LamaScout" / "reports" / "delta_history.json"
LUMASCOUT_SUMMARY_EXPORT   = OUT / "lumascout_summary.json"

PAPER_STATE_JSON           = OUT / "paper_trade_state.json"
PAPER_LEDGER_JSONL         = OUT / "paper_trade_ledger.jsonl"
EXECUTION_RUNTIME_JSON     = OUT / "execution_runtime.json"
EXECUTION_STATUS_JSON      = OUT / "execution_status.json"
APPROVAL_QUEUE_JSON        = OUT / "execution_approval_queue.json"
LIVE_ACTION_RECEIPT_PATH   = OUT / "execution" / "live_action_time_approval_receipt_latest.json"
OPS_OUT_DIR                = OUT / "ops"

SECTOR_PIPELINE_WRAPPER            = CODE / "ops" / "RUN_SECTOR_ENERGY_EVIDENCE_PIPELINE.ps1"
SECTOR_PIPELINE_LATEST_JSON        = OPS_OUT_DIR / "sector_energy_evidence_pipeline_latest.json"
SECTOR_PIPELINE_ORCH_STATUS_JSON   = OPS_OUT_DIR / "sector_energy_pipeline_orchestrator_status.json"
UNIVERSAL_ORCH_SCRIPT_NAME         = "run_universal_meta_orchestrator.py"
UNIVERSAL_ORCH_CADENCE_STATE_JSON  = OUT / "execution" / "universal_orch_cadence_state.json"

_SCRIPT_LAST_RUN_TS: dict[str, float] = {}

REQUIRED_PAPER_SYMBOLS = [
    "SPY","QQQ","IWM","DIA",
    "NVDA","MSFT","AAPL","AMD","META","AMZN","TSLA",
    "GOOGL","AVGO","SMCI","PLTR","NFLX"
]

SOURCE_SECTOR_MAP = {
    "eia":"energy",
    "fred":"rates",
    "bea":"macro",
    "census":"demographic",
    "noaa":"weather",
    "nasa":"space",
    "bls":"labor",
    "nrel":"energy_lab",
    "usgs":"water",
    "alpaca":"broker",
    "twelve_data":"market_data",
    "polygon":"market_data",
    "finnhub":"market_data",
    "kraken":"crypto_exec",
    "epa_aqs":"air_quality",
    "massive":"market_data",
    "webhook":"internal",
}

def now_utc():
    return datetime.now(timezone.utc)

def iso_now():
    return now_utc().isoformat()

def load_json(path, default):
    try:
        if Path(path).exists():
            return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def load_lumascout_active_source_count():
    if not LUMASCOUT_API_REGISTRY.exists():
        return 0
    try:
        text = LUMASCOUT_API_REGISTRY.read_text(encoding="utf-8")
        if yaml is not None:
            data = yaml.safe_load(text)
            sources = data.get("sources", []) if isinstance(data, dict) else []
            return sum(1 for src in sources if isinstance(src, dict) and bool(src.get("active")))
        return len([line for line in text.splitlines() if re.match(r"^\s*active:\s*(true|yes)\s*$", line, flags=re.IGNORECASE)])
    except Exception:
        return 0


def load_lumascout_summary():
    summary = load_json(LUMASCOUT_TRUTH_SUMMARY, None)
    if summary is None:
        return {
            "generated_utc": iso_now(),
            "total_artists": 0,
            "live_artists": 0,
            "champions": 0,
            "watchlist": 0,
            "portfolio_size": 0,
            "hot_radar_count": 0,
            "top_prospect_count": 0,
            "top_artist": "n/a",
            "top_live_artist": "n/a",
            "status": "missing",
        }
    return summary


def load_lumascout_delta_status():
    delta = load_json(LUMASCOUT_DELTA_HISTORY, None)
    if not isinstance(delta, list):
        return {
            "delta_runs": 0,
            "last_checksum": None,
            "previous_checksum": None,
        }
    return {
        "delta_runs": len(delta),
        "last_checksum": delta[-1].get("checksum") if delta else None,
        "previous_checksum": delta[-1].get("previous_checksum") if delta else None,
    }


def export_lumascout_summary():
    summary = load_lumascout_summary()
    delta_status = load_lumascout_delta_status()
    export = {
        "generated_utc": iso_now(),
        "active_sources": load_lumascout_active_source_count(),
        "champions": int(summary.get("champions", 0)),
        "watchlist": int(summary.get("watchlist", 0)),
        "hot_radar_count": int(summary.get("hot_radar_count", 0)),
        "top_prospect_count": int(summary.get("top_prospect_count", 0)),
        "top_artist": summary.get("top_artist", "n/a"),
        "top_live_artist": summary.get("top_live_artist", "n/a"),
        "delta_runs": delta_status["delta_runs"],
        "last_checksum": delta_status["last_checksum"],
        "previous_checksum": delta_status["previous_checksum"],
        "truth_summary_path": str(LUMASCOUT_TRUTH_SUMMARY),
        "delta_history_path": str(LUMASCOUT_DELTA_HISTORY),
    }
    save_json(LUMASCOUT_SUMMARY_EXPORT, export)
    return export


def env_present(name):
    v = os.environ.get(name)
    return bool(v and str(v).strip())

def safe_int(x, default=0):
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return default


def env_truthy(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    txt = str(raw).strip().lower()
    if not txt:
        return bool(default)
    return txt in {"1", "true", "yes", "on"}


def parse_utc_maybe(value):
    if not value:
        return None
    try:
        txt = str(value).strip()
        if txt.endswith("Z"):
            txt = txt[:-1] + "+00:00"
        dt = datetime.fromisoformat(txt)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _load_script_cadence_state() -> dict[str, float]:
    payload = load_json(UNIVERSAL_ORCH_CADENCE_STATE_JSON, {})
    raw = payload.get("script_last_run_ts") if isinstance(payload, dict) else {}
    if not isinstance(raw, dict):
        return {}

    out: dict[str, float] = {}
    for key, value in raw.items():
        try:
            out[str(key)] = float(value)
        except Exception:
            continue
    return out


def _persist_script_last_run_ts(script_name: str, ts_value: float) -> None:
    _SCRIPT_LAST_RUN_TS[str(script_name)] = float(ts_value)
    payload = {
        "generated_utc": iso_now(),
        "script_last_run_ts": {
            str(k): float(v)
            for k, v in _SCRIPT_LAST_RUN_TS.items()
        },
    }
    try:
        save_json(UNIVERSAL_ORCH_CADENCE_STATE_JSON, payload)
    except Exception:
        pass


_SCRIPT_LAST_RUN_TS.update(_load_script_cadence_state())

def scan_csv_meta(path: Path):
    meta = {
        "file": path.name,
        "source_path": str(path),
        "rows": 0,
        "cols": 0,
        "value_col": None,
        "time_col": None,
        "status": "skipped",
        "reason": "unknown",
        "quality_score": 0.0,
    }
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)
        if not rows:
            meta["reason"] = "empty_file"
            return meta
        header = rows[0]
        data = rows[1:] if len(rows) > 1 else []
        meta["rows"] = len(data)
        meta["cols"] = len(header)

        if len(header) == 0:
            meta["reason"] = "no_header"
            return meta

        header_lower = [str(h).strip().lower() for h in header]

        time_candidates = [
            "timestamp","time","date","datetime","period",
            "interval_start","interval_end","trading_day"
        ]
        value_candidates = [
            "close","price","value","volume","open","high","low","adj_close",
            "demand forecast (mwh)","load","generation","mw","mwh"
        ]

        time_col = None
        for c in time_candidates:
            if c in header_lower:
                time_col = header[header_lower.index(c)]
                break

        value_col = None
        for c in value_candidates:
            if c in header_lower:
                value_col = header[header_lower.index(c)]
                break

        if value_col is None:
            numeric_counts = {}
            for idx, col in enumerate(header):
                count = 0
                for r in data[:250]:
                    if idx < len(r):
                        try:
                            float(str(r[idx]).replace(",",""))
                            count += 1
                        except Exception:
                            pass
                numeric_counts[col] = count
            if numeric_counts:
                value_col = max(numeric_counts, key=numeric_counts.get)

        usable = (meta["rows"] > 25 and meta["cols"] >= 2 and value_col is not None)
        meta["value_col"] = value_col
        meta["time_col"] = time_col
        meta["status"] = "usable" if usable else "skipped"
        meta["reason"] = "ok" if usable else "insufficient_rows_or_no_value_col"

        score = 0.0
        if meta["rows"] >= 25: score += 20
        if meta["rows"] >= 100: score += 20
        if meta["rows"] >= 500: score += 20
        if meta["cols"] >= 2: score += 10
        if value_col: score += 20
        if time_col: score += 10
        meta["quality_score"] = round(score, 2)
        return meta
    except Exception as e:
        meta["reason"] = f"error:{type(e).__name__}"
        return meta

def discover_csvs():
    found = []
    seen = set()
    for root in DATA_ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*.csv"):
            key = str(p).lower()
            if key not in seen:
                seen.add(key)
                found.append(p)
    return found

def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

def build_dataset_truth():
    csvs = discover_csvs()
    metas = [scan_csv_meta(p) for p in csvs]
    usable = [m for m in metas if m["status"] == "usable"]

    write_csv(
        DATASET_CATALOG_CSV,
        metas,
        ["file","source_path","rows","cols","value_col","time_col","status","reason","quality_score"]
    )
    write_csv(
        DATASET_SCAN_SUMMARY_CSV,
        usable,
        ["file","source_path","rows","cols","value_col","time_col","status","reason","quality_score"]
    )

    proof = {
        "generated_utc": iso_now(),
        "roots_scanned": [str(r) for r in DATA_ROOTS if r.exists()],
        "files_scanned": len(metas),
        "usable_files": len(usable),
        "top_clean_files": sorted(usable, key=lambda x: (-x["quality_score"], -x["rows"]))[:50]
    }
    save_json(DATA_INGEST_PROOF_JSON, proof)
    return metas, usable

def infer_sector_from_name(name: str):
    n = name.lower()
    if "kraken" in n or "crypto" in n or "xbt" in n or "btc" in n:
        return "crypto_exec"
    if "fred" in n:
        if "dgs" in n or "rate" in n or "yield" in n:
            return "rates"
        return "macro"
    if "eia" in n or "generation" in n or "nuclear" in n or "mer_" in n or "930-data" in n:
        return "energy"
    if "alpaca" in n or "equity" in n or "stock" in n:
        return "broker"
    return "unknown"

def sync_live_sources(usable_files):
    live_sources = load_json(LIVE_SOURCES_PATH, {})
    if not isinstance(live_sources, dict):
        live_sources = {}

    for name, cfg in list(live_sources.items()):
        if not isinstance(cfg, dict):
            cfg = {}
            live_sources[name] = cfg
        env_name = cfg.get("api_key_env")
        present = env_present(env_name) if env_name else False
        cfg["enabled"] = bool(present)
        cfg["last_truth_sync_utc"] = iso_now()

    save_json(LIVE_SOURCES_PATH, live_sources)

    registry_rows = []
    usable_by_sector = {}
    for m in usable_files:
        sec = infer_sector_from_name(m["file"])
        usable_by_sector[sec] = usable_by_sector.get(sec, 0) + 1

    for name, cfg in live_sources.items():
        env_name = cfg.get("api_key_env")
        present = env_present(env_name) if env_name else False
        sector = SOURCE_SECTOR_MAP.get(name.lower(), "unknown")
        measured_rows = usable_by_sector.get(sector, 0)
        row = {
            "source": name.upper(),
            "sector": sector,
            "status": "LIVE_KEY_PRESENT" if present else "MISSING",
            "rows": measured_rows,
            "evidence_basis": "MEASURED_FILE_MATCH" if measured_rows > 0 else "KEY_ONLY",
            "dollar_basis": "MEASURED" if measured_rows > 0 else "UNMEASURED",
            "last_probe_utc": iso_now(),
            "env": env_name,
            "enabled": bool(cfg.get("enabled", False)),
        }
        registry_rows.append(row)

    payload = {
        "generated_utc": iso_now(),
        "paper_live_linked": True,
        "rows": registry_rows
    }
    save_json(LIVE_SOURCE_REGISTRY_PATH, payload)
    save_json(SOURCE_TRUTH_TABLE_JSON, payload)
    return live_sources, payload

def sync_runtime_files():
    rt = load_json(RUNTIME_CONTROL_PATH, {})

    strict_live_requested = is_strict_live_locked(rt)
    human_action_time_authority = {
        "authorized": False,
        "reasons": ["strict_live_lock_not_requested"],
        "receipt_present": LIVE_ACTION_RECEIPT_PATH.exists(),
        "receipt_age_sec": None,
    }
    if strict_live_requested:
        human_action_time_authority = validate_live_action_authority(
            runtime_path=RUNTIME_CONTROL_PATH,
            receipt_path=LIVE_ACTION_RECEIPT_PATH,
            ttl_seconds=300,
        )
    strict_live_locked = bool(
        strict_live_requested and human_action_time_authority.get("authorized")
    )

    canonical_runtime_rewritten = False
    if not strict_live_locked:
        rt["mode"] = "paper"
        rt["allow_live_orders"] = False
        rt["paper_enabled"] = True
        rt["kill_switch"] = True
        rt["symbol"] = "UNIVERSE"
        rt["loop_seconds"] = 5
        stamp_runtime_writer(
            rt,
            writer="code/FULL_TRUTH_ORCHESTRATOR.py",
            strict_live_lock=False,
            reason="full_truth_fail_closed_paper_sync",
        )
        save_json(RUNTIME_CONTROL_PATH, rt)
        canonical_runtime_rewritten = True

    paper = load_json(PAPER_RUNTIME_PATH, {})
    paper["starting_capital_usd"] = float(paper.get("starting_capital_usd", 100000.0))
    paper["loop_seconds"] = 5
    paper["symbols"] = REQUIRED_PAPER_SYMBOLS
    paper["paper_enabled"] = True
    paper["universe_mode"] = True
    save_json(PAPER_RUNTIME_PATH, paper)

    infra = load_json(INFRA_RUNTIME_PATH, {})
    infra["loop_seconds"] = 60
    infra["data_roots"] = [str(r) for r in DATA_ROOTS if r.exists()]
    infra["dataset_catalog_csv"] = str(DATASET_CATALOG_CSV)
    infra["dataset_scan_summary_csv"] = str(DATASET_SCAN_SUMMARY_CSV)
    infra["data_ingest_proof_json"] = str(DATA_INGEST_PROOF_JSON)
    infra["source_truth_table_json"] = str(SOURCE_TRUTH_TABLE_JSON)
    infra["live_source_registry_json"] = str(LIVE_SOURCE_REGISTRY_PATH)
    save_json(INFRA_RUNTIME_PATH, infra)

    ex_rt = load_json(EXECUTION_RUNTIME_JSON, {})
    ex_rt["timestamp"] = iso_now()
    ex_rt["live_enabled"] = bool(strict_live_locked)
    ex_rt["kill_switch"] = not strict_live_locked
    ex_rt["runtime_mode"] = "live" if strict_live_locked else "paper"
    ex_rt["position"] = ex_rt.get("position", "flat")
    ex_rt["symbol"] = None
    ex_rt["last_mode"] = "LIVE" if strict_live_locked else "PAPER"
    save_json(EXECUTION_RUNTIME_JSON, ex_rt)

    ex_status = load_json(EXECUTION_STATUS_JSON, {})
    ex_status["generated_utc"] = iso_now()
    ex_status["execution_mode"] = "live" if strict_live_locked else "paper"
    ex_status["kill_switch"] = not strict_live_locked
    ex_status["live_arm"] = "ON" if strict_live_locked else "OFF"
    ex_status["live_action_time_authority"] = {
        "authorized": bool(human_action_time_authority.get("authorized")),
        "reasons": list(human_action_time_authority.get("reasons") or []),
        "receipt_present": bool(human_action_time_authority.get("receipt_present")),
        "receipt_age_sec": human_action_time_authority.get("receipt_age_sec"),
    }
    ex_status["canonical_runtime_rewritten"] = canonical_runtime_rewritten
    ex_status["note"] = (
        "Strict live profile and fresh action-time authority verified; preserving live execution arming."
        if strict_live_locked
        else "Paper + universe truth sync only. Existing live flags are not preserved without fresh action-time authority."
    )
    save_json(EXECUTION_STATUS_JSON, ex_status)

    if not APPROVAL_QUEUE_JSON.exists():
        save_json(APPROVAL_QUEUE_JSON, [])

def run_if_exists(path: Path, extra_args=None, timeout_sec=300):
    if not path.exists():
        return {"script": str(path), "ran": False, "ok": False, "reason": "missing"}

    script_name = path.name
    cadence_sec = 0
    if script_name == UNIVERSAL_ORCH_SCRIPT_NAME:
        cadence_sec = max(60, safe_int(os.getenv("LUMA_UNIVERSAL_ORCH_INTERVAL_SEC", "900"), 900))
    if cadence_sec > 0:
        last_ts = _SCRIPT_LAST_RUN_TS.get(script_name)
        if last_ts is not None:
            elapsed = max(0.0, time.time() - float(last_ts))
            if elapsed < cadence_sec:
                return {
                    "script": str(path),
                    "ran": False,
                    "ok": True,
                    "reason": "cadence_not_due",
                    "cadence_interval_sec": cadence_sec,
                    "cadence_due_in_sec": int(cadence_sec - elapsed),
                }

    suffix = path.suffix.lower()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    if suffix == ".py":
        cmd = [sys.executable, str(path)]
        if path.name == "run_universal_meta_orchestrator.py":
            cmd.append("--paper")
            env["PAPER_MODE"] = "true"
    elif suffix == ".ps1":
        cmd = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)]
    elif suffix in {".cmd", ".bat"}:
        cmd = [str(path)]
    else:
        return {
            "script": str(path),
            "ran": False,
            "ok": False,
            "reason": f"unsupported_script_type:{suffix}",
        }

    if extra_args:
        cmd.extend([str(a) for a in extra_args if str(a).strip()])

    effective_timeout = max(30, int(timeout_sec))
    if script_name == UNIVERSAL_ORCH_SCRIPT_NAME:
        effective_timeout = max(
            60,
            safe_int(os.getenv("LUMA_UNIVERSAL_ORCH_TIMEOUT_SEC", str(effective_timeout)), effective_timeout),
        )

    try:
        p = subprocess.run(
            cmd,
            cwd=str(path.parent),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=effective_timeout
        )
        _persist_script_last_run_ts(script_name, time.time())
        return {
            "script": str(path),
            "command": cmd,
            "ran": True,
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "timeout_sec": effective_timeout,
            "stdout_tail": (p.stdout or "")[-1200:],
            "stderr_tail": (p.stderr or "")[-1200:]
        }
    except Exception as e:
        _persist_script_last_run_ts(script_name, time.time())
        return {
            "script": str(path),
            "command": cmd,
            "ran": True,
            "ok": False,
            "timeout_sec": effective_timeout,
            "reason": repr(e),
        }


def maybe_run_sector_energy_pipeline():
    interval_sec = max(300, safe_int(os.getenv("LUMA_SECTOR_PIPELINE_INTERVAL_SEC", "900"), 900))
    step_timeout_sec = max(180, safe_int(os.getenv("LUMA_SECTOR_PIPELINE_STEP_TIMEOUT_SEC", "900"), 900))
    run_investor_sweep = env_truthy("LUMA_SECTOR_PIPELINE_RUN_INVESTOR_SWEEP", False)

    now = now_utc()
    prior = load_json(SECTOR_PIPELINE_ORCH_STATUS_JSON, {})
    prior_last_attempt = parse_utc_maybe(prior.get("last_attempt_utc"))
    due_in_sec = 0
    if prior_last_attempt is not None:
        elapsed = (now - prior_last_attempt).total_seconds()
        if elapsed < interval_sec:
            due_in_sec = int(interval_sec - elapsed)

    latest_payload = load_json(SECTOR_PIPELINE_LATEST_JSON, None)
    latest_generated_utc = latest_payload.get("generated_utc") if isinstance(latest_payload, dict) else None
    latest_status = latest_payload.get("status") if isinstance(latest_payload, dict) else None
    latest_run_dir = latest_payload.get("run_dir") if isinstance(latest_payload, dict) else None

    if due_in_sec > 0:
        return {
            "script": str(SECTOR_PIPELINE_WRAPPER),
            "ran": False,
            "ok": bool(prior.get("last_ok", True)),
            "reason": "cadence_not_due",
            "cadence_interval_sec": interval_sec,
            "cadence_due_in_sec": due_in_sec,
            "run_investor_sweep": run_investor_sweep,
            "latest_pipeline_generated_utc": latest_generated_utc,
            "latest_pipeline_status": latest_status,
            "latest_pipeline_run_dir": latest_run_dir,
            "last_success_utc": prior.get("last_success_utc"),
        }

    extra_args = ["-StepTimeoutSec", str(step_timeout_sec)]
    if run_investor_sweep:
        extra_args.append("-RunInvestorSweep")

    result = run_if_exists(
        SECTOR_PIPELINE_WRAPPER,
        extra_args=extra_args,
        timeout_sec=step_timeout_sec + 120,
    )

    latest_after = load_json(SECTOR_PIPELINE_LATEST_JSON, None)
    latest_after_generated_utc = latest_after.get("generated_utc") if isinstance(latest_after, dict) else latest_generated_utc
    latest_after_status = latest_after.get("status") if isinstance(latest_after, dict) else latest_status
    latest_after_run_dir = latest_after.get("run_dir") if isinstance(latest_after, dict) else latest_run_dir

    status_payload = {
        "generated_utc": iso_now(),
        "script": str(SECTOR_PIPELINE_WRAPPER),
        "cadence_interval_sec": interval_sec,
        "step_timeout_sec": step_timeout_sec,
        "run_investor_sweep": run_investor_sweep,
        "last_attempt_utc": iso_now(),
        "last_ok": bool(result.get("ok")),
        "last_returncode": result.get("returncode"),
        "last_reason": result.get("reason"),
        "latest_pipeline_generated_utc": latest_after_generated_utc,
        "latest_pipeline_status": latest_after_status,
        "latest_pipeline_run_dir": latest_after_run_dir,
    }
    if result.get("ok"):
        status_payload["last_success_utc"] = iso_now()
    else:
        status_payload["last_success_utc"] = prior.get("last_success_utc")
    save_json(SECTOR_PIPELINE_ORCH_STATUS_JSON, status_payload)

    return {
        **result,
        "cadence_interval_sec": interval_sec,
        "cadence_due_in_sec": 0,
        "run_investor_sweep": run_investor_sweep,
        "latest_pipeline_generated_utc": latest_after_generated_utc,
        "latest_pipeline_status": latest_after_status,
        "latest_pipeline_run_dir": latest_after_run_dir,
        "last_success_utc": status_payload.get("last_success_utc"),
    }

def find_script_candidates():
    names = [
        "auto_data_ingest.py",
        "full_beast_universe_runner.py",
        "adaptive_engine.py",
        "edge_truth_guard.py",
        "dashboard_unified_refresh.py",
        "alpaca_paper_loop_builder.py",
        "infra_live_loop_builder.py",
        "LAMASCOUT_INTEGRATION.py",
        "run_universal_meta_orchestrator.py",
    ]
    paths = [CODE / n for n in names]

    exec_dir = CODE / "execution"
    if exec_dir.exists():
        extra = []
        for p in sorted(exec_dir.glob("RUN_EXECUTION*"), key=lambda x: x.name.lower()):
            if p.suffix.lower() in {".py", ".ps1", ".cmd", ".bat"}:
                extra.append(p)
        paths.extend(extra[:5])
    return paths

def open_dashboards():
    candidates = [
        DASH / "alpaca_paper_live_dashboard.html",
        DASH / "infra_institutional_live_dashboard.html",
        DASH / "lumascout_dashboard.html",
        DASH / "karmuk_dashboard.html",
        DASH / "cold_case_dashboard.html",
        DASH / "seed_validation_readout.html",
        DASH / "hard_truth_live_measurement_audit.html",
        DASH / "infra_audit_dashboard.html",
        DASH / "live_audit_readout.html",
        DASH / "audit_derivation_pack.html",
        DASH / "live_source_registry.html",
        DASH / "nobel_tier_command_center.html",
    ]
    for c in candidates:
        if c.exists():
            try:
                os.startfile(str(c))
            except Exception:
                pass

    # Auto open LamaScout API UI if running
    api_url = "http://127.0.0.1:8000/ui"
    health_url = "http://127.0.0.1:8000/health"
    try:
        with urllib.request.urlopen(health_url, timeout=3) as resp:
            if resp.status == 200:
                try:
                    os.startfile(api_url)
                except Exception:
                    pass
    except Exception:
        pass

def cycle():
    metas, usable = build_dataset_truth()
    live_sources, registry = sync_live_sources(usable)
    sync_runtime_files()
    lumascout_export = export_lumascout_summary()
    sector_pipeline = maybe_run_sector_energy_pipeline()

    results = []
    for script in find_script_candidates():
        results.append(run_if_exists(script))

    runtime_now = load_json(RUNTIME_CONTROL_PATH, {})
    execution_now = load_json(EXECUTION_STATUS_JSON, {})
    runtime_mode_now = str(runtime_now.get("mode", "paper") or "paper").strip().lower()
    execution_mode_now = str(execution_now.get("execution_mode", runtime_mode_now) or runtime_mode_now).strip().lower()

    status = {
        "generated_utc": iso_now(),
        "data_roots_present": [str(r) for r in DATA_ROOTS if r.exists()],
        "files_scanned": len(metas),
        "usable_files": len(usable),
        "enabled_source_count": len([1 for _, v in live_sources.items() if isinstance(v, dict) and v.get("enabled")]),
        "registry_rows": len(registry.get("rows", [])),
        "runtime_mode": runtime_mode_now,
        "execution_mode": execution_mode_now,
        "lumascout_active_sources": int(lumascout_export.get("active_sources", 0)),
        "lumascout_champions": int(lumascout_export.get("champions", 0)),
        "lumascout_watchlist": int(lumascout_export.get("watchlist", 0)),
        "lumascout_hot_radar_count": int(lumascout_export.get("hot_radar_count", 0)),
        "lumascout_delta_runs": int(lumascout_export.get("delta_runs", 0)),
        "lumascout_last_checksum": lumascout_export.get("last_checksum"),
        "lumascout_previous_checksum": lumascout_export.get("previous_checksum"),
        "sector_energy_pipeline": sector_pipeline,
        "script_results": results
    }
    save_json(TRUTH_STATUS_JSON, status)
    return status

def main():
    open_dashboards()
    while True:
        try:
            s = cycle()
            sp = s.get("sector_energy_pipeline", {}) if isinstance(s, dict) else {}
            if sp.get("ran"):
                sp_state = "ok" if sp.get("ok") else "fail"
            elif sp.get("reason") == "cadence_not_due":
                sp_state = f"wait:{sp.get('cadence_due_in_sec', 0)}s"
            else:
                sp_state = "idle"
            print(f"[{iso_now()}] truth sync ok | files={s['files_scanned']} usable={s['usable_files']} enabled_sources={s['enabled_source_count']} sector_pipeline={sp_state}")
        except Exception:
            err = {
                "generated_utc": iso_now(),
                "error": traceback.format_exc()
            }
            save_json(TRUTH_STATUS_JSON, err)
            print(f"[{iso_now()}] truth sync error")
            print(err["error"])
        time.sleep(60)

if __name__ == "__main__":
    main()

# --- Hybrid Harmonic Metrics ---
def compute_hybrid_harmonic_metrics(df):
    metrics = {}
    for name, algo in ALGO_WRAPPERS.items():
        try:
            metrics[name] = df.groupby('symbol').apply(lambda x: algo(x['close'])).mean()
        except Exception as e:
            metrics[name] = f"ERR: {e}"
    # Example strategy
    try:
        metrics['harmonic_consensus'] = df.groupby('symbol').apply(lambda x: strat_harmonic_consensus(x['close'])).mean()
    except Exception as e:
        metrics['harmonic_consensus'] = f"ERR: {e}"
    return metrics

# --- Main Integration Example ---
def orchestrate_hypercompounder_pipeline():
    print("Auto-discovering all Binance symbols...")
    binance_syms = get_all_binance_symbols()
    print(f"Found {len(binance_syms)} Binance symbols.")
    print("Auto-discovering all Kraken symbols...")
    kraken_syms = get_all_kraken_symbols()
    print(f"Found {len(kraken_syms)} Kraken symbols.")
    print("Fetching Binance live data for top 3 symbols...")
    binance_data = fetch_live_data_for_symbols(binance_syms[:3], exchange="binance", days=90)
    print("Fetching Kraken live data for top 3 symbols...")
    kraken_data = fetch_live_data_for_symbols(kraken_syms[:3], exchange="kraken", days=90)
    data = pd.concat([binance_data, kraken_data], ignore_index=True)
    if data.empty:
        print("No live data fetched. Aborting.")
        return
    filter_mod = HyperCompounderFilter(momentum_breakout_score, {'window': 20}, threshold=0.98)
    print("Running Hyper-Compounder Backtest...")
    metrics, mc, filtered = run_backtest(data, filter_mod)
    print("Running Hyper-Compounder Live Monte Carlo...")
    metrics_live, mc_live, filtered_live = run_live_montecarlo(data, filter_mod)
    print("\n===== INSTITUTIONAL METRICS SUMMARY =====")
    print("Backtest Metrics:", metrics)
    print("Backtest Monte Carlo:", mc)
    print("Live Metrics:", metrics_live)
    print("Live Monte Carlo:", mc_live)
    print("Filtered symbols:", filtered['symbol'].unique())
    print("\n===== HYBRID HARMONIC METRICS =====")
    print("Backtest Hybrid Harmonic:", compute_hybrid_harmonic_metrics(filtered))
    print("Live Hybrid Harmonic:", compute_hybrid_harmonic_metrics(filtered_live))
