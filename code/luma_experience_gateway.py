from __future__ import annotations

import base64
import atexit
import asyncio
import copy
import csv
import io
import json
import logging
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

log = logging.getLogger("luma_experience_gateway")


def _resolve_stack_root() -> Path:
    env_root = (os.getenv("LUMA_STACK_ROOT") or os.getenv("LUMA_ROOT") or "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()

    # Most portable default: parent of this file (..../INSTITUTIONAL_STACK_V2/code -> root)
    inferred = Path(__file__).resolve().parent.parent
    if (inferred / "dashboard").exists() or (inferred / "code").exists():
        return inferred

    win_default = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
    if win_default.exists():
        return win_default

    return inferred


def _resolve_dashboard_dir(root: Path) -> Path:
    env_dash = os.getenv("LUMA_DASHBOARD_DIR", "").strip()
    if env_dash:
        return Path(env_dash).expanduser().resolve()

    candidates = [
        root.parent / "dashboard",
        root / "dashboard",
        Path(r"C:\LumaTrader\dashboard"),
        Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2\dashboard"),
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return root / "dashboard"

try:
    from prometheus_fastapi_instrumentator import Instrumentator as _PrometheusInstrumentator
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False

try:
    import edge_tts

    _EDGE_TTS_AVAILABLE = True
except ImportError:
    edge_tts = None
    _EDGE_TTS_AVAILABLE = False

try:
    from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, Counter, Gauge, generate_latest

    def _metric_once(metric_type: str, name: str, doc: str):
        existing = REGISTRY._names_to_collectors.get(name)
        if existing is not None:
            return existing
        if metric_type == "gauge":
            return Gauge(name, doc)
        return Counter(name, doc)

    _WS_CONNECTIONS = _metric_once("gauge", "luma_ws_connections", "Active WebSocket connections")
    _SNAPSHOT_REQUESTS = _metric_once("counter", "luma_snapshot_requests_total", "Snapshot API calls")
    _ML_RUNS = _metric_once("counter", "luma_ml_signal_runs_total", "ML signal generation runs")
    _PROM_CLIENT_AVAILABLE = True
except ImportError:
    _PROM_CLIENT_AVAILABLE = False

ROOT = _resolve_stack_root()
CODE = ROOT / "code"
DASH = _resolve_dashboard_dir(ROOT)

# ── Singleton lock — prevent duplicate gateway processes ─────────────────────
_GATEWAY_LOCK = ROOT / "run" / "luma_experience_gateway.lock"
_GATEWAY_LOCK.parent.mkdir(parents=True, exist_ok=True)
if _GATEWAY_LOCK.exists():
    try:
        _existing_pid = int(_GATEWAY_LOCK.read_text().strip())
        if _existing_pid != os.getpid():
            os.kill(_existing_pid, 0)  # raises OSError if the process is gone
            print(f"[singleton] luma_experience_gateway already running as PID {_existing_pid} — exiting.", flush=True)
            raise SystemExit(0)
    except (ValueError, OSError, SystemError):
        pass  # stale lock
_GATEWAY_LOCK.write_text(str(os.getpid()))
atexit.register(lambda: _GATEWAY_LOCK.unlink(missing_ok=True))
# ─────────────────────────────────────────────────────────────────────────────

OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
LAMASCOUT_REPORTS = ROOT / "LamaScout" / "reports"
TWIN_SEED_PATH = Path(
    os.getenv(
        "LUMA_TWIN_SEED_PATH",
        r"C:\Users\Novac\iCloudDrive\Downloads 2\Copy of twin_seed.json",
    )
)

SCORECARD_FILE = EXEC_OUT / "investor_proof_scorecard.json"
SUPERVISOR_HEALTH_FILE = EXEC_OUT / "supervisor_health.json"
SUPERVISOR_HEALTH_FILES = [
    SUPERVISOR_HEALTH_FILE,
    CODE / "out" / "execution" / "supervisor_health.json",
    ROOT / "data" / "out" / "execution" / "supervisor_health.json",
]
SECTOR_FILE = OUT / "sector_value_matrix.json"
SCOUT_FILE = LAMASCOUT_REPORTS / "artist_scout_summary.json"
SESSION_MEMORY_FILE = EXEC_OUT / "luma_session_memory.json"
AWARENESS_FILE = EXEC_OUT / "symbol_watchdog_hierarchy.json"
HARMONIC_RANKED_FILE = OUT / "universal_edge" / "_cross_domain_ranked.json"
HARMONIC_SPORTS_FILE = OUT / "universal_edge" / "_sports_ranked.json"
HARMONIC_CRYPTO_FILE = OUT / "universal_edge" / "_crypto_ranked.json"
HARMONIC_INFRA_FILE  = OUT / "universal_edge" / "_infra_ranked.json"
EXECUTION_EVENTS_FILE = ROOT / "execution_events.jsonl"
EXECUTION_EVENT_FILES = [
    ROOT / "execution_events.jsonl",
    OUT / "execution_events.jsonl",
    ROOT / "data" / "out" / "execution_events.jsonl",
    EXEC_OUT / "execution_events.jsonl",
]
LEADERBOARD_CSV = ROOT / "institutional_leaderboard.csv"
ROLLING_PERF_FILE = OUT / "rolling_performance.json"
SECTOR_HISTORY_FILE = EXEC_OUT / "institutional_sector_opportunity_history.jsonl"
ML_SIGNAL_FILE   = OUT / "ml_signals" / "ensemble_signal.json"
ML_SHAP_FILE     = OUT / "ml_signals" / "shap_summary.json"
ML_TEARSHEET_FILE = OUT / "ml_signals" / "tearsheet_data.json"
ALPACA_STATUS_FILE = EXEC_OUT / "alpaca_paper_status.json"
CRYPTO_STATUS_FILE = EXEC_OUT / "multi_exchange_paper_ticker_status.json"
SPORTS_ROUTER_FILE = OUT / "sports_intelligence" / "_adaptive_router.json"
LIVE_TRUTH_FILE = OUT / "live_truth_fabric" / "live_truth_router.json"
LIVE_TRUTH_MANIFEST_FILE = OUT / "live_truth_fabric" / "live_truth_manifest.json"
LIVE_TRUTH_HEARTBEAT_FILE = EXEC_OUT / "live_truth_fabric_heartbeat.json"
KRAKEN_POSITIVE_PROOF_FILE = EXEC_OUT / "kraken_positive_proof.json"
KRAKEN_ALPHA_MAP_FILE = OUT / "ops" / "kraken_multi_tf_alpha_map_latest.json"
KRAKEN_ALPHA_MAP_FILE_STACK_FALLBACK = ROOT / "INSTITUTIONAL_STACK_V2" / "out" / "ops" / "kraken_multi_tf_alpha_map_latest.json"
PACKAGE_LEVERAGE_FILE = EXEC_OUT / "package_leverage_audit.json"
FUNDING_QUEUE_FILE = OUT / "funding" / "funding_approval_queue.json"
METRICS_SCORECARD_FILE = EXEC_OUT / "institutional_metrics_scorecard.json"
EDGE_TRUTH_FILE = EXEC_OUT / "edge_truth_report.json"
CONTROL_FLAGS_FILE = ROOT / "control_flags.json"
RUNTIME_CONTROL_FILE = ROOT / "config" / "runtime_control.json"
LIVE_EXECUTOR_HEARTBEAT_FILE = EXEC_OUT / "live_executor_heartbeat.json"
EXECUTION_STATUS_FILE = ROOT / "execution_status.json"
SYSTEM_OVERLORD_FILE = EXEC_OUT / "system_overlord_20s.json"
API_KEY_REGISTRY_FILE = EXEC_OUT / "api_key_registry_report.json"
LANE_INTEGRITY_FILE = EXEC_OUT / "lane_integrity_report.json"
BENCHMARK_BEATER_FILE = EXEC_OUT / "benchmark_beater.json"
SECTOR_CLOCK_FILE = EXEC_OUT / "sector_clock_beater.json"
PUBLIC_DASHBOARD_URL_FILE = EXEC_OUT / "public_dashboard_url.txt"
PUBLIC_DASHBOARD_TUNNEL_STATUS_FILE = EXEC_OUT / "public_dashboard_tunnel_status.json"
INNOVATION_AUTOPILOT_HEARTBEAT_FILE = EXEC_OUT / "innovation_autopilot_heartbeat.json"
BEEFY_SIMS_FILE = EXEC_OUT / "broader_beefier_sims.json"
DASH_EVIDENCE_RUNS_DIR = ROOT / "dashboard" / "evidence" / "runs"
DASH_GRID_VALUE_FILE = ROOT / "dashboard" / "grid_value_live.json"
DASH_INFRA_LIVE_DASHBOARD_FILE = ROOT / "dashboard" / "infra_live_dashboard.json"
HARMONIC_PROOFPACK_RUNS_DIR = EXEC_OUT / "harmonic_backprop_proofpack"
HARMONIC_PROOFPACK_LATEST_FILE = HARMONIC_PROOFPACK_RUNS_DIR / "latest.json"
FROZEN_DELTA_LEDGER_FILE = OUT / "frozen_delta_ledger.jsonl"
RUNTIME_DRIFT_ALERT_FILE = EXEC_OUT / "runtime_drift_alert.json"
RUNTIME_DRIFT_OPERATOR_ALERT_FILE = EXEC_OUT / "runtime_drift_operator_alert.json"
SCENE_VISUAL_PROFILE_FILE = ROOT / "config" / "scene_visual_profiles.json"
SCENE_SIMULATION_SCENARIO_FILE = ROOT / "config" / "scene_simulation_scenarios.json"
SCENE_SIMULATION_RUNS_FILE = EXEC_OUT / "scene_simulation_runs.jsonl"
STALENESS_REPORT_FILE = OUT / "ops" / "staleness_report.json"
LUMAQ_BRAIN_REPORT_FILE = OUT / "ops" / "lumaq_brain_report.json"
LUMAQ_TOP10_REGISTRY_FILE = OUT / "ops" / "lumaq_top10_alpha_registry.json"
UNIVERSE_MAP_DIR = EXEC_OUT / "universe_map"
UNIVERSE_MAP_FILE = UNIVERSE_MAP_DIR / "lumencore_universe_map.json"
NOBEL_ENGINE_CATALOG_FILE = UNIVERSE_MAP_DIR / "lumencore_nobel_engine_catalog.json"
BOOTH_EXPLAINER_BRIEF_FILE = UNIVERSE_MAP_DIR / "booth_explainer_brief.json"
PREMIUM_MIRROR_LATEST_FILE = ROOT.parent / "premium_packages_mirror" / "premium_package_mirror_latest.json"
LIVE_TRADE_LEDGER_FILE = EXEC_OUT / "live_trade_ledger.jsonl"

_EVIDENCE_CACHE_TTL_SEC = 30.0
_EVIDENCE_CACHE: dict[str, Any] = {
    "loaded_monotonic": 0.0,
    "payload": None,
}
_RUNTIME_DRIFT_CACHE_TTL_SEC = 10.0
_RUNTIME_DRIFT_CACHE: dict[str, Any] = {
    "loaded_monotonic": 0.0,
    "payload": None,
}
EVIDENCE_AUTO_REPAIR = str(os.getenv("LUMA_EVIDENCE_AUTO_REPAIR", "1")).strip().lower() not in {
    "0",
    "false",
    "off",
    "no",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def load_supervisor_health(default: Any) -> Any:
    for cand in SUPERVISOR_HEALTH_FILES:
        data = load_json(cand, None)
        if data is not None:
            return data
    return default


def _scan_latest_runtime_drift_excessive_event() -> dict[str, Any]:
    target_type = "runtime_live_profile_drift_excessive"
    max_tail_bytes = 256 * 1024

    for cand in EXECUTION_EVENT_FILES:
        try:
            if not cand.exists() or cand.stat().st_size <= 0:
                continue
            size = cand.stat().st_size
            with cand.open("rb") as fh:
                if size > max_tail_bytes:
                    fh.seek(size - max_tail_bytes)
                    fh.readline()  # discard partial line
                lines = fh.read().decode("utf-8", errors="replace").splitlines()
        except Exception:
            continue

        for raw in reversed(lines):
            raw = raw.strip()
            if not raw:
                continue
            try:
                event = json.loads(raw)
            except Exception:
                continue

            event_type = str(event.get("event_type") or event.get("event") or event.get("type") or "").strip().lower()
            if event_type != target_type:
                continue

            return {
                "source_file": str(cand),
                "timestamp_utc": event.get("timestamp_utc") or event.get("timestamp") or event.get("generated_utc"),
                "loop": int(event.get("loop", 0) or 0),
                "window_events": int(event.get("window_events", 0) or 0),
                "threshold": int(event.get("threshold", 0) or 0),
                "operator_alert_write_ok": bool(event.get("operator_alert_write_ok", False)),
                "operator_alert_file_exists": bool(event.get("operator_alert_file_exists", False)),
                "operator_alert_write_error": str(event.get("operator_alert_write_error", "") or ""),
                "operator_alert_fallback_write_error": str(event.get("operator_alert_fallback_write_error", "") or ""),
            }

    return {}


def load_runtime_drift_operator_status(force: bool = False) -> dict[str, Any]:
    now_ts = time.time()
    if not force:
        cached_payload = _RUNTIME_DRIFT_CACHE.get("payload")
        cached_loaded = float(_RUNTIME_DRIFT_CACHE.get("loaded_monotonic", 0.0) or 0.0)
        if isinstance(cached_payload, dict) and (now_ts - cached_loaded) < _RUNTIME_DRIFT_CACHE_TTL_SEC:
            return dict(cached_payload)

    drift_alert = load_json(RUNTIME_DRIFT_ALERT_FILE, {})
    operator_alert = load_json(RUNTIME_DRIFT_OPERATOR_ALERT_FILE, {})
    latest_event = _scan_latest_runtime_drift_excessive_event()

    operator_alert_file_exists = bool(
        latest_event.get("operator_alert_file_exists", False)
        if latest_event
        else RUNTIME_DRIFT_OPERATOR_ALERT_FILE.exists()
    )
    payload = {
        "event_found": bool(latest_event),
        "last_excessive_event_utc": latest_event.get("timestamp_utc") if latest_event else None,
        "operator_alert_write_ok": bool(latest_event.get("operator_alert_write_ok", False)) if latest_event else operator_alert_file_exists,
        "operator_alert_file_exists": operator_alert_file_exists,
        "operator_alert_write_error": str(latest_event.get("operator_alert_write_error", "") or "") if latest_event else "",
        "operator_alert_fallback_write_error": str(latest_event.get("operator_alert_fallback_write_error", "") or "") if latest_event else "",
        "operator_alert_path": str(RUNTIME_DRIFT_OPERATOR_ALERT_FILE),
        "operator_alert_generated_utc": operator_alert.get("timestamp_utc") if isinstance(operator_alert, dict) else None,
        "window_events": int((drift_alert.get("window_events", 0) if isinstance(drift_alert, dict) else 0) or 0),
        "threshold": int((drift_alert.get("threshold", 0) if isinstance(drift_alert, dict) else 0) or 0),
        "excessive": bool((drift_alert.get("excessive", False) if isinstance(drift_alert, dict) else False)),
        "likely_culprit_writer": str(
            (operator_alert.get("likely_culprit_writer") if isinstance(operator_alert, dict) else None)
            or (drift_alert.get("likely_culprit_writer") if isinstance(drift_alert, dict) else "")
            or ""
        ),
    }

    _RUNTIME_DRIFT_CACHE["loaded_monotonic"] = now_ts
    _RUNTIME_DRIFT_CACHE["payload"] = dict(payload)
    return payload


def fmt_usd(value: Any) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    if abs(amount) >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f}B"
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:.2f}"


def load_session_memory() -> dict[str, Any]:
    base = {
        "schema": "luma_session_memory_v1",
        "updated_utc": now_utc(),
        "events": [],
        "guide_history": [],
    }
    data = load_json(SESSION_MEMORY_FILE, base)
    if not isinstance(data, dict):
        return base
    data.setdefault("schema", "luma_session_memory_v1")
    data.setdefault("updated_utc", now_utc())
    data.setdefault("events", [])
    data.setdefault("guide_history", [])
    return data


def save_session_memory(memory: dict[str, Any]) -> None:
    memory["updated_utc"] = now_utc()
    SESSION_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_MEMORY_FILE.write_text(json.dumps(memory, indent=2), encoding="utf-8")


def load_harmonic_edge() -> dict[str, Any]:
    ranked = load_json(HARMONIC_RANKED_FILE, {})
    signals = ranked.get("top_signals", [])[:10] if isinstance(ranked, dict) else []
    summary = ranked.get("summary", {}) if isinstance(ranked, dict) else {}
    top = signals[0] if signals else {}
    return {
        "generated_utc":   ranked.get("generated_utc") if isinstance(ranked, dict) else None,
        "total_signals":   ranked.get("total", 0) if isinstance(ranked, dict) else 0,
        "by_domain":       summary,
        "top_score":       round(float(top.get("flowform", {}).get("hybrid_harmonic_score", 0.0) or 0.0), 4),
        "top_domain":      top.get("domain", "n/a"),
        "top_asset":       top.get("asset", "n/a"),
        "top_signal_type": top.get("signal_type", "n/a"),
        "top_edge_pct":    round(float(top.get("edge_pct", 0.0) or 0.0), 4),
        "top_signals":     signals,
    }


def _safe_num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _probe_json_file_health(path: Path) -> dict[str, Any]:
    details: dict[str, Any] = {
        "path": str(path),
        "exists": bool(path.exists()),
        "size_bytes": 0,
        "binary_like": False,
        "null_byte_ratio": 0.0,
        "json_parse_ok": False,
    }
    if not path.exists():
        return details

    try:
        size_bytes = int(path.stat().st_size or 0)
        details["size_bytes"] = size_bytes

        sample = b""
        if size_bytes > 0:
            sample_size = min(size_bytes, 8192)
            with path.open("rb") as fh:
                sample = fh.read(sample_size)

        if sample:
            null_ratio = sample.count(b"\x00") / float(len(sample))
            details["null_byte_ratio"] = round(null_ratio, 4)
            details["binary_like"] = bool(null_ratio >= 0.15)

        if not bool(details["binary_like"]):
            try:
                json.loads(path.read_text(encoding="utf-8"))
                details["json_parse_ok"] = True
            except Exception as exc:
                details["json_error"] = str(exc)[:180]
    except Exception as exc:
        details["json_error"] = str(exc)[:180]

    return details


def _dashboard_integrity_warnings(grid_health: dict[str, Any], infra_health: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for label, health in (("grid_value_live", grid_health), ("infra_live_dashboard", infra_health)):
        exists = bool(health.get("exists", False))
        if not exists:
            warnings.append(f"{label} is missing (expected JSON text)")
            continue
        if bool(health.get("binary_like", False)):
            warnings.append(f"{label} appears null-padded/binary-like (expected JSON text)")
            continue
        if not bool(health.get("json_parse_ok", False)):
            warnings.append(f"{label} exists but failed JSON parsing")
    return warnings


def _atomic_write_json_text(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _build_grid_value_repair_payload(evidence_hint: dict[str, Any]) -> dict[str, Any]:
    now_ts = now_utc()
    derived = evidence_hint.get("derived", {}) if isinstance(evidence_hint, dict) else {}
    delta_pct = _safe_num((derived or {}).get("stacker_router_delta_pct", 0.0), 0.0)
    if abs(delta_pct) > 1000.0:
        delta_pct = 0.0

    return {
        "timestamp": now_ts,
        "delta_percent": round(delta_pct, 6),
        "system_scale_usd": 0.0,
        "value_this_tick_usd": 0.0,
        "cumulative_value_usd": 0.0,
        "ticks": 0,
        "source": "gateway_evidence_auto_repair",
        "evidence_run_utc": str(evidence_hint.get("run_utc", "") or ""),
        "repair_note": "Regenerated as valid JSON after binary/invalid dashboard artifact was detected.",
    }


def _build_infra_live_repair_payload(evidence_hint: dict[str, Any]) -> dict[str, Any]:
    now_ts = now_utc()
    derived = evidence_hint.get("derived", {}) if isinstance(evidence_hint, dict) else {}
    regime_break_rate_pct = _safe_num((derived or {}).get("regime_break_rate_pct", 0.0), 0.0)
    router_win_rate_pct = _safe_num((derived or {}).get("router_win_rate_pct", 0.0), 0.0)
    stacker_router_win_rate_pct = _safe_num((derived or {}).get("stacker_router_win_rate_pct", 0.0), 0.0)

    return {
        "timestamp": now_ts,
        "baseline": 0.0,
        "drift": round(regime_break_rate_pct / 100.0, 6),
        "gain_percent": round(stacker_router_win_rate_pct - router_win_rate_pct, 6),
        "loss_per_hour": 0.0,
        "recovered_per_hour": 0.0,
        "cumulative_value": 0.0,
        "ticks": 0,
        "source": "gateway_evidence_auto_repair",
        "evidence_run_utc": str(evidence_hint.get("run_utc", "") or ""),
        "repair_note": "Regenerated as valid JSON after binary/invalid dashboard artifact was detected.",
    }


def _repair_dashboard_live_feeds_if_needed(
    grid_health: dict[str, Any],
    infra_health: dict[str, Any],
    evidence_hint: dict[str, Any],
) -> list[dict[str, Any]]:
    if not EVIDENCE_AUTO_REPAIR:
        return []

    repairs: list[dict[str, Any]] = []

    def _needs_repair(health: dict[str, Any]) -> bool:
        exists = bool(health.get("exists", False))
        if not exists:
            return True
        if bool(health.get("binary_like", False)):
            return True
        return not bool(health.get("json_parse_ok", False))

    if _needs_repair(grid_health):
        item = {
            "file": "grid_value_live",
            "path": str(DASH_GRID_VALUE_FILE),
            "attempted": True,
            "ok": False,
        }
        try:
            _atomic_write_json_text(DASH_GRID_VALUE_FILE, _build_grid_value_repair_payload(evidence_hint))
            item["ok"] = True
        except Exception as exc:
            item["error"] = str(exc)[:180]
        repairs.append(item)

    if _needs_repair(infra_health):
        item = {
            "file": "infra_live_dashboard",
            "path": str(DASH_INFRA_LIVE_DASHBOARD_FILE),
            "attempted": True,
            "ok": False,
        }
        try:
            _atomic_write_json_text(DASH_INFRA_LIVE_DASHBOARD_FILE, _build_infra_live_repair_payload(evidence_hint))
            item["ok"] = True
        except Exception as exc:
            item["error"] = str(exc)[:180]
        repairs.append(item)

    return repairs


def _latest_dashboard_evidence_run_dir() -> Path | None:
    if not DASH_EVIDENCE_RUNS_DIR.exists():
        return None
    runs = [
        p for p in DASH_EVIDENCE_RUNS_DIR.iterdir()
        if p.is_dir() and (p / "summary.json").exists()
    ]
    if not runs:
        return None
    runs.sort(key=lambda p: p.name)
    return runs[-1]


def _harmonic_proofpack_run_dirs() -> list[Path]:
    if not HARMONIC_PROOFPACK_RUNS_DIR.exists():
        return []
    runs = [
        p
        for p in HARMONIC_PROOFPACK_RUNS_DIR.iterdir()
        if p.is_dir() and (p / "summary.json").exists()
    ]
    runs.sort(key=lambda p: p.name, reverse=True)
    return runs


def _harmonic_proofpack_artifact_url(run_id: str, artifact_name: str) -> str | None:
    path = HARMONIC_PROOFPACK_RUNS_DIR / run_id / artifact_name
    if not path.exists():
        return None
    return f"/out/execution/harmonic_backprop_proofpack/{run_id}/{artifact_name}"


def _harmonic_proofpack_ledger_entry(run_id: str) -> dict[str, Any] | None:
    if not FROZEN_DELTA_LEDGER_FILE.exists():
        return None
    try:
        lines = FROZEN_DELTA_LEDGER_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return None
    for line in reversed(lines[-800:]):
        row_text = line.strip()
        if not row_text:
            continue
        try:
            row = json.loads(row_text)
        except Exception:
            continue
        test_name = str(row.get("test_name", "") or "").strip().lower()
        if test_name != "harmonic_backprop_proofpack":
            continue
        row_run_id = str(row.get("run_id", "") or "").strip()
        if row_run_id != run_id:
            continue
        return row
    return None


def _harmonic_proofpack_run_payload(run_dir: Path) -> dict[str, Any]:
    summary = load_json(run_dir / "summary.json", {})
    manifest = load_json(run_dir / "manifest.sha256.json", {})
    run_id = run_dir.name

    winner = summary.get("winner", {}) if isinstance(summary, dict) else {}
    input_payload = summary.get("input", {}) if isinstance(summary, dict) else {}
    split_payload = summary.get("split", {}) if isinstance(summary, dict) else {}
    ranked_raw = summary.get("ranked_models", []) if isinstance(summary, dict) else []
    findings_raw = summary.get("findings", []) if isinstance(summary, dict) else []

    ranked_models: list[dict[str, Any]] = []
    for row in ranked_raw[:12] if isinstance(ranked_raw, list) else []:
        if not isinstance(row, dict):
            continue
        ranked_models.append(
            {
                "model": str(row.get("model", "") or ""),
                "rmse": round(_safe_num(row.get("rmse", 0.0), 0.0), 6),
                "mae": round(_safe_num(row.get("mae", 0.0), 0.0), 6),
                "mape_pct": round(_safe_num(row.get("mape_pct", 0.0), 0.0), 6),
            }
        )

    findings = [str(item) for item in findings_raw if str(item).strip()] if isinstance(findings_raw, list) else []
    manifest_files = manifest.get("files", {}) if isinstance(manifest, dict) else {}
    if not isinstance(manifest_files, dict):
        manifest_files = {}

    artifacts = {
        "summary_json": _harmonic_proofpack_artifact_url(run_id, "summary.json"),
        "manifest_json": _harmonic_proofpack_artifact_url(run_id, "manifest.sha256.json"),
        "metrics_csv": _harmonic_proofpack_artifact_url(run_id, "metrics.csv"),
        "metrics_pivot_csv": _harmonic_proofpack_artifact_url(run_id, "metrics_pivot.csv"),
        "holdout_predictions_csv": _harmonic_proofpack_artifact_url(run_id, "holdout_predictions.csv"),
        "holdout_predictions_png": _harmonic_proofpack_artifact_url(run_id, "holdout_predictions.png"),
        "rmse_rank_png": _harmonic_proofpack_artifact_url(run_id, "rmse_rank.png"),
        "report_pdf": _harmonic_proofpack_artifact_url(run_id, "report.pdf"),
    }

    ledger_entry = _harmonic_proofpack_ledger_entry(run_id)

    return {
        "run_id": run_id,
        "generated_utc": str(summary.get("generated_utc", "") if isinstance(summary, dict) else ""),
        "run_dir": str(run_dir),
        "input": {
            "path": str(input_payload.get("path", "") or "") if isinstance(input_payload, dict) else "",
            "sha256": str(input_payload.get("sha256", "") or "") if isinstance(input_payload, dict) else "",
            "value_col": str(input_payload.get("value_col", "") or "") if isinstance(input_payload, dict) else "",
            "date_col": str(input_payload.get("date_col", "") or "") if isinstance(input_payload, dict) else "",
            "rows_total": int((input_payload.get("rows_total", 0) if isinstance(input_payload, dict) else 0) or 0),
            "rows_valid": int((input_payload.get("rows_valid", 0) if isinstance(input_payload, dict) else 0) or 0),
        },
        "split": {
            "n_train": int((split_payload.get("n_train", 0) if isinstance(split_payload, dict) else 0) or 0),
            "n_test": int((split_payload.get("n_test", 0) if isinstance(split_payload, dict) else 0) or 0),
            "test_frac": round(_safe_num((split_payload.get("test_frac", 0.0) if isinstance(split_payload, dict) else 0.0), 0.0), 6),
        },
        "winner": {
            "model": str(winner.get("model", "") if isinstance(winner, dict) else ""),
            "rmse": round(_safe_num((winner.get("rmse", 0.0) if isinstance(winner, dict) else 0.0), 0.0), 6),
            "mae": round(_safe_num((winner.get("mae", 0.0) if isinstance(winner, dict) else 0.0), 0.0), 6),
            "mape_pct": round(_safe_num((winner.get("mape_pct", 0.0) if isinstance(winner, dict) else 0.0), 0.0), 6),
        },
        "ranked_models": ranked_models,
        "findings": findings,
        "manifest": {
            "generated_utc": str(manifest.get("generated_utc", "") if isinstance(manifest, dict) else ""),
            "files_count": len(manifest_files),
            "files": manifest_files,
        },
        "ledger_entry": {
            "run_utc": str((ledger_entry or {}).get("run_utc", "") or ""),
            "entry_sha256": str((ledger_entry or {}).get("entry_sha256", "") or ""),
            "prev_entry_sha256": str((ledger_entry or {}).get("prev_entry_sha256", "") or ""),
            "manifest_sha256": str((ledger_entry or {}).get("manifest_sha256", "") or ""),
            "summary_sha256": str((ledger_entry or {}).get("summary_sha256", "") or ""),
        },
        "artifacts": artifacts,
    }


def _build_dashboard_evidence_payload() -> dict[str, Any]:
    grid_health = _probe_json_file_health(DASH_GRID_VALUE_FILE)
    infra_health = _probe_json_file_health(DASH_INFRA_LIVE_DASHBOARD_FILE)

    run_dir = _latest_dashboard_evidence_run_dir()
    if run_dir is None:
        evidence_hint = {
            "run_utc": None,
            "derived": {
                "router_win_rate_pct": 0.0,
                "stacker_router_win_rate_pct": 0.0,
                "stacker_router_delta_pct": 0.0,
                "regime_break_rate_pct": 0.0,
            },
        }
        repairs = _repair_dashboard_live_feeds_if_needed(grid_health, infra_health, evidence_hint)
        if any(bool(r.get("ok", False)) for r in repairs):
            grid_health = _probe_json_file_health(DASH_GRID_VALUE_FILE)
            infra_health = _probe_json_file_health(DASH_INFRA_LIVE_DASHBOARD_FILE)
        warnings = _dashboard_integrity_warnings(grid_health, infra_health)

        return {
            "generated_utc": now_utc(),
            "available": False,
            "status": "not_found",
            "run_utc": None,
            "source_dir": None,
            "integrity": {
                "grid_value_live": grid_health,
                "infra_live_dashboard": infra_health,
            },
            "warnings": warnings + ["no completed dashboard evidence run found"],
            "repairs": repairs,
            "derived": {
                "router_win_rate_pct": 0.0,
                "stacker_router_win_rate_pct": 0.0,
                "stacker_router_delta_pct": 0.0,
                "regime_break_rate_pct": 0.0,
            },
        }

    run_summary = load_json(run_dir / "summary.json", {})
    router_eval = load_json(run_dir / "router" / "eval.json", {})
    stacker_eval = load_json(run_dir / "stacker" / "eval.json", {})
    regime_summary = load_json(run_dir / "regime" / "summary.json", {})

    router_summary = router_eval.get("summary", {}) if isinstance(router_eval, dict) else {}
    stacker_summary = stacker_eval.get("summary", {}) if isinstance(stacker_eval, dict) else {}

    router_win_rate_pct = 100.0 * _safe_num((router_summary.get("win_rates", {}) or {}).get("router", 0.0), 0.0)
    stacker_router_win_rate_pct = 100.0 * _safe_num((stacker_summary.get("win_rates", {}) or {}).get("router", 0.0), 0.0)
    stacker_router_delta_pct = stacker_router_win_rate_pct - router_win_rate_pct

    regime_n = int(regime_summary.get("n_datasets", 0) or 0)
    regime_recent = int(regime_summary.get("n_with_recent_break_within_12", 0) or 0)
    regime_break_rate_pct = 100.0 * _safe_num(regime_summary.get("frac_with_any_mean_break", 0.0), 0.0)
    regime_recent_break_rate_pct = (float(regime_recent) / max(float(regime_n), 1.0)) * 100.0

    v2_n_datasets = int(
        run_summary.get(
            "n_datasets_succeeded",
            stacker_summary.get("n_datasets", regime_n),
        )
        or 0
    )
    v2_n_universe = int(run_summary.get("n_datasets_in_universe", v2_n_datasets) or v2_n_datasets)
    harmonic_win_rate_pct = 100.0 * _safe_num(run_summary.get("harmonic_win_rate", 0.0), 0.0)

    manifest_state = {
        "router": bool((run_dir / "router" / "manifest.sha256.json").exists()),
        "stacker": bool((run_dir / "stacker" / "manifest.sha256.json").exists()),
        "regime": bool((run_dir / "regime" / "manifest.sha256.json").exists()),
    }

    evidence_hint = {
        "run_utc": run_dir.name,
        "derived": {
            "router_win_rate_pct": round(router_win_rate_pct, 2),
            "stacker_router_win_rate_pct": round(stacker_router_win_rate_pct, 2),
            "stacker_router_delta_pct": round(stacker_router_delta_pct, 2),
            "regime_break_rate_pct": round(regime_break_rate_pct, 2),
        },
    }
    repairs = _repair_dashboard_live_feeds_if_needed(grid_health, infra_health, evidence_hint)
    if any(bool(r.get("ok", False)) for r in repairs):
        grid_health = _probe_json_file_health(DASH_GRID_VALUE_FILE)
        infra_health = _probe_json_file_health(DASH_INFRA_LIVE_DASHBOARD_FILE)

    warnings = _dashboard_integrity_warnings(grid_health, infra_health)
    if not all(manifest_state.values()):
        warnings.append("one or more evidence manifests are missing")

    return {
        "generated_utc": now_utc(),
        "available": True,
        "status": "ok",
        "run_utc": run_dir.name,
        "source_dir": str(run_dir),
        "v2": {
            "n_datasets_in_universe": v2_n_universe,
            "n_datasets_succeeded": v2_n_datasets,
            "harmonic_win_rate_pct": round(harmonic_win_rate_pct, 2),
            "elapsed_s": round(_safe_num(run_summary.get("elapsed_s", 0.0), 0.0), 2),
            "test_name": str(run_summary.get("test_name", "") or ""),
            "scale": str(run_summary.get("scale", "") or ""),
        },
        "router": {
            "wins": int((router_summary.get("win_counts", {}) or {}).get("router", 0) or 0),
            "router_win_rate_pct": round(router_win_rate_pct, 2),
            "router_chose_correctly_pct": round(_safe_num(router_summary.get("router_chose_correctly_pct", 0.0), 0.0), 2),
            "classifier": str(router_summary.get("classifier", "") or ""),
            "cv_folds": int(router_summary.get("cv_folds", 0) or 0),
        },
        "stacker": {
            "router_wins": int((stacker_summary.get("win_counts", {}) or {}).get("router", 0) or 0),
            "router_win_rate_pct": round(stacker_router_win_rate_pct, 2),
            "beats_v2_oracle": int((stacker_summary.get("beats_v2_oracle", {}) or {}).get("router", 0) or 0),
        },
        "regime": {
            "n_datasets": regime_n,
            "n_with_any_mean_break": int(regime_summary.get("n_with_any_mean_break", 0) or 0),
            "break_rate_pct": round(regime_break_rate_pct, 2),
            "n_with_recent_break_within_12": regime_recent,
            "recent_break_rate_pct": round(regime_recent_break_rate_pct, 2),
            "n_with_variance_regime_break": int(regime_summary.get("n_with_variance_regime_break", 0) or 0),
            "total_mean_breaks": int(regime_summary.get("total_mean_breaks", 0) or 0),
        },
        "manifests": manifest_state,
        "integrity": {
            "grid_value_live": grid_health,
            "infra_live_dashboard": infra_health,
        },
        "derived": {
            "router_win_rate_pct": round(router_win_rate_pct, 2),
            "stacker_router_win_rate_pct": round(stacker_router_win_rate_pct, 2),
            "stacker_router_delta_pct": round(stacker_router_delta_pct, 2),
            "regime_break_rate_pct": round(regime_break_rate_pct, 2),
        },
        "warnings": warnings,
        "repairs": repairs,
    }


def load_latest_dashboard_evidence(force: bool = False) -> dict[str, Any]:
    now_ts = time.time()
    if not force:
        cached_payload = _EVIDENCE_CACHE.get("payload")
        cached_loaded = float(_EVIDENCE_CACHE.get("loaded_monotonic", 0.0) or 0.0)
        if isinstance(cached_payload, dict) and (now_ts - cached_loaded) < _EVIDENCE_CACHE_TTL_SEC:
            return dict(cached_payload)

    payload = _build_dashboard_evidence_payload()
    _EVIDENCE_CACHE["loaded_monotonic"] = now_ts
    _EVIDENCE_CACHE["payload"] = dict(payload)
    return payload


def _build_execution_snapshot() -> dict[str, Any]:
    heartbeat = load_json(LIVE_EXECUTOR_HEARTBEAT_FILE, {})
    runtime = load_json(RUNTIME_CONTROL_FILE, {})
    if not isinstance(heartbeat, dict):
        heartbeat = {}
    if not isinstance(runtime, dict):
        runtime = {}

    def runtime_float(key: str, default: float) -> float:
        try:
            return float(runtime.get(key, default) or default)
        except Exception:
            return float(default)

    return {
        "status": str(heartbeat.get("status", "unknown") or "unknown").lower(),
        "reason": str(heartbeat.get("reason", "") or ""),
        "symbol": heartbeat.get("symbol"),
        "updated_utc": heartbeat.get("ts") or heartbeat.get("generated_utc") or heartbeat.get("updated_utc"),
        "balance_confirmed_live": bool(heartbeat.get("balance_confirmed_live", False)),
        "balance_source": heartbeat.get("balance_source"),
        "guardrails": {
            "deliberate_mode_enabled": bool(runtime.get("deliberate_mode_enabled", False)),
            "global_entries_window_sec": runtime_float("global_entries_window_sec", 3600.0),
            "global_entry_cooldown_sec": runtime_float("global_entry_cooldown_sec", 0.0),
            "max_entries_per_hour": int(runtime_float("max_entries_per_hour", 0.0)),
            "per_symbol_entry_cooldown_sec": runtime_float("per_symbol_entry_cooldown_sec", 0.0),
            "per_symbol_entries_window_sec": runtime_float("per_symbol_entries_window_sec", 3600.0),
            "max_entries_per_symbol_window": int(runtime_float("max_entries_per_symbol_window", 0.0)),
            "max_consecutive_same_symbol_entries": int(runtime_float("max_consecutive_same_symbol_entries", 0.0)),
            "same_symbol_streak_window_sec": runtime_float("same_symbol_streak_window_sec", 3600.0),
        },
        "signals": {
            "entries_in_global_window": heartbeat.get("entries_in_global_window"),
            "max_entries_per_hour": heartbeat.get("max_entries_per_hour"),
            "symbol_entries_window": heartbeat.get("symbol_entries_window"),
            "max_entries_per_symbol_window": heartbeat.get("max_entries_per_symbol_window"),
            "same_symbol_streak_count": heartbeat.get("same_symbol_streak_count"),
            "elapsed_global_sec": heartbeat.get("elapsed_global_sec"),
            "elapsed_symbol_sec": heartbeat.get("elapsed_symbol_sec"),
        },
    }


def build_snapshot() -> dict[str, Any]:
    scorecard = load_json(SCORECARD_FILE, {})
    metrics = load_json(METRICS_SCORECARD_FILE, {})
    package_leverage = load_json(PACKAGE_LEVERAGE_FILE, {})
    edge_truth = load_json(EDGE_TRUTH_FILE, {})
    sector = load_json(SECTOR_FILE, {})
    scout = load_json(SCOUT_FILE, {})
    twin_seed = load_json(TWIN_SEED_PATH, {})
    awareness = load_json(AWARENESS_FILE, {})
    evidence = load_latest_dashboard_evidence()
    runtime_drift = load_runtime_drift_operator_status()

    lev_used = int(package_leverage.get("used_package_count", 0) or 0) if isinstance(package_leverage, dict) else 0
    lev_active = int(package_leverage.get("active_package_count", lev_used) or 0) if isinstance(package_leverage, dict) else lev_used
    lev_installed = int(package_leverage.get("installed_package_count", 0) or 0) if isinstance(package_leverage, dict) else 0
    lev_unused = int(package_leverage.get("unused_package_count", 0) or 0) if isinstance(package_leverage, dict) else 0
    lev_pct = (float(lev_active) / max(float(lev_installed), 1.0)) * 100.0
    top_test_sharpe = float((metrics.get("research_kpis", {}) or {}).get("top_test_sharpe", 0.0) or 0.0)
    top_wf_sharpe = float((metrics.get("research_kpis", {}) or {}).get("top_walkforward_sharpe_mean", 0.0) or 0.0)
    top_wf_stability = float((metrics.get("research_kpis", {}) or {}).get("top_walkforward_stability", 0.0) or 0.0)
    edge_verdict = str(
        (metrics.get("research_kpis", {}) or {}).get("edge_truth_verdict")
        or edge_truth.get("verdict")
        or "UNKNOWN"
    ).upper()
    edge_score = float(
        (metrics.get("research_kpis", {}) or {}).get("edge_truth_score")
        or edge_truth.get("edge_quality_score")
        or 0.0
    )
    if edge_verdict == "UNKNOWN":
        if top_test_sharpe >= 1.0 and top_wf_sharpe >= 1.0 and top_wf_stability >= 0.35:
            edge_verdict = "PASS"
            edge_score = max(edge_score, 70.0)
        elif top_test_sharpe > 0.0:
            edge_verdict = "WATCH"
            edge_score = max(edge_score, 45.0)
        else:
            edge_verdict = "FAIL"
            edge_score = max(edge_score, 20.0)

    return {
        "generated_utc": now_utc(),
        "paper": {
            "equity": scorecard.get("current_equity_usd", 0.0),
            "equity_text": fmt_usd(scorecard.get("current_equity_usd", 0.0)),
            "net_pnl": scorecard.get("net_pnl_usd", 0.0),
            "net_pnl_text": fmt_usd(scorecard.get("net_pnl_usd", 0.0)),
            "closed_trades": int(scorecard.get("closed_trades", 0) or 0),
            "win_rate_pct": float(scorecard.get("win_rate_pct", 0.0) or 0.0),
            "profit_factor": float(scorecard.get("profit_factor", 0.0) or 0.0),
        },
        "infra": {
            "active_surface": sector.get("yearly_translated_value", 0.0),
            "active_surface_text": fmt_usd(sector.get("yearly_translated_value", 0.0)),
            "top_lane": sector.get("top_current_optimization_lane", "n/a"),
        },
        "scout": {
            "top_artist": scout.get("top_production_artist") or scout.get("top_live_artist") or scout.get("top_artist") or "n/a",
            "candidates": int(scout.get("production_candidate_count", 0) or 0),
            "artists": int(scout.get("total_artists", 0) or 0),
        },
        "luma": {
            "version": twin_seed.get("twin_version", "LumaTwin v1.0"),
            "origin": twin_seed.get("origin_node", "Robert BabyRay Ashworth"),
            "traits": twin_seed.get("core_traits", {}),
        },
        "awareness": {
            "generated_utc": awareness.get("generated_utc"),
            "watchdog_count": int(awareness.get("watchdog_count", 0) or 0),
            "evaluated_count": int(awareness.get("evaluated_count", 0) or 0),
            "top_watchdog": (awareness.get("summary", {}) or {}).get("top_watchdog"),
            "top_entry": (awareness.get("summary", {}) or {}).get("top_entry"),
            "top_exit": (awareness.get("summary", {}) or {}).get("top_exit"),
            "top_eval": (awareness.get("summary", {}) or {}).get("top_eval"),
        },
        "runtime": {
            "drift_operator_alert": runtime_drift,
        },
        "edge": {
            "verdict": edge_verdict,
            "score": edge_score,
            "top_test_sharpe": top_test_sharpe,
            "top_walkforward_sharpe_mean": top_wf_sharpe,
            "top_walkforward_stability": top_wf_stability,
        },
        "packages": {
            "installed_count": lev_installed,
            "used_count": lev_used,
            "active_count": lev_active,
            "unused_count": lev_unused,
            "usage_pct": round(lev_pct, 2),
            "probes": (package_leverage.get("leverage_probes", {}) or {}),
        },
        "harmonic": load_harmonic_edge(),
        "execution": _build_execution_snapshot(),
        "evidence": evidence,
    }


class GuideRequest(BaseModel):
    prompt: str
    mode: str = "concierge"


class VoiceSynthesizeRequest(BaseModel):
    text: str
    profile: str = "luma_pitch"
    rate: float = 1.0
    pitch: float = 1.0


class SessionEvent(BaseModel):
    event: str
    source: str = "web"
    detail: dict[str, Any] = {}


class CueRequest(BaseModel):
    scene: str = "core"
    cue: str
    intensity: float = 0.5
    detail: dict[str, Any] = {}


class CueSimulationRequest(BaseModel):
    scene: str = "core"
    cue: str = "idle_breathe"
    start_intensity: float = 0.2
    end_intensity: float = 0.9
    steps: int = 5
    interval_ms: int = 220
    include_reverse: bool = False
    hint: str = ""
    detail: dict[str, Any] = {}


class CueScenarioRunRequest(BaseModel):
    scenario: str = "institutional_open"
    interval_scale: float = 1.0
    repeat: int = 1
    hint: str = ""
    detail: dict[str, Any] = {}


VOICE_PROFILE_PRESETS: dict[str, dict[str, str]] = {
    "luma_pitch": {
        "voice": "en-US-JennyNeural",
        "description": "Warm premium pitch voice",
    },
    "luma_operator": {
        "voice": "en-US-GuyNeural",
        "description": "Crisp operator brief voice",
    },
    "luma_analyst": {
        "voice": "en-US-AriaNeural",
        "description": "Measured analyst voice",
    },
}


def _clean_tts_text(raw: str) -> str:
    text = " ".join(str(raw or "").strip().split())
    max_chars_raw = os.getenv("LUMA_TTS_MAX_CHARS", "3200")
    try:
        max_chars = max(200, min(10000, int(max_chars_raw)))
    except Exception:
        max_chars = 3200
    return text[:max_chars]


def _edge_rate_from_multiplier(rate: float) -> str:
    try:
        mult = float(rate)
    except Exception:
        mult = 1.0
    mult = max(0.5, min(1.8, mult))
    pct = int(round((mult - 1.0) * 100.0))
    return f"{pct:+d}%"


def _edge_pitch_from_multiplier(pitch: float) -> str:
    try:
        mult = float(pitch)
    except Exception:
        mult = 1.0
    mult = max(0.7, min(1.4, mult))
    hz = int(round((mult - 1.0) * 24.0))
    return f"{hz:+d}Hz"


async def _synthesize_edge_tts_bytes(*, text: str, voice: str, rate: str, pitch: str) -> bytes:
    if not _EDGE_TTS_AVAILABLE or edge_tts is None:
        return b""
    communicator = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume="+0%",
        pitch=pitch,
    )
    chunks: list[bytes] = []
    async for chunk in communicator.stream():
        if chunk.get("type") != "audio":
            continue
        data = chunk.get("data")
        if isinstance(data, (bytes, bytearray)) and data:
            chunks.append(bytes(data))
    return b"".join(chunks)


DEFAULT_SCENE_VISUAL_PROFILES: dict[str, Any] = {
    "schema": "luma_scene_visual_profile_v1",
    "version": "2026-05-08",
    "defaults": {
        "render_pipeline": "urp",
        "palette": "luma_core",
        "postfx": {
            "bloom": 0.42,
            "vignette": 0.20,
            "chromatic_aberration": 0.05,
            "film_grain": 0.10,
        },
        "camera": {
            "shake": 0.08,
            "orbit_speed": 0.35,
            "fov_boost": 2.0,
        },
        "particles": {
            "density": 0.45,
            "turbulence": 0.35,
            "trail_length": 0.50,
        },
        "audio": {
            "layer": "ambient_core",
            "ducking": 0.12,
        },
        "haptics": {
            "pulse": 0.15,
            "duration_ms": 120,
        },
    },
    "cues": {
        "idle_breathe": {
            "mood": "stable",
            "bands": {
                "low": {
                    "postfx": {"bloom": 0.25},
                    "camera": {"shake": 0.02},
                    "particles": {"density": 0.20},
                },
                "medium": {
                    "postfx": {"bloom": 0.35},
                    "camera": {"shake": 0.04},
                    "particles": {"density": 0.30},
                },
                "high": {
                    "postfx": {"bloom": 0.45},
                    "camera": {"shake": 0.06},
                    "particles": {"density": 0.40},
                },
                "extreme": {
                    "postfx": {"bloom": 0.52},
                    "camera": {"shake": 0.09},
                    "particles": {"density": 0.50},
                },
            },
        },
        "success_pulse": {
            "mood": "positive",
            "palette": "profit_green",
            "bands": {
                "low": {"camera": {"fov_boost": 2.0}, "particles": {"density": 0.40}},
                "medium": {"camera": {"fov_boost": 3.0}, "particles": {"density": 0.55}},
                "high": {"camera": {"fov_boost": 4.0}, "particles": {"density": 0.70}},
                "extreme": {"camera": {"fov_boost": 5.0}, "particles": {"density": 0.82}},
            },
        },
        "warning_pulse": {
            "mood": "caution",
            "palette": "amber_warning",
            "bands": {
                "low": {"camera": {"shake": 0.10}, "audio": {"layer": "warning_soft"}},
                "medium": {"camera": {"shake": 0.16}, "audio": {"layer": "warning_soft"}},
                "high": {"camera": {"shake": 0.22}, "audio": {"layer": "warning_dense"}},
                "extreme": {"camera": {"shake": 0.30}, "audio": {"layer": "warning_dense"}},
            },
        },
        "critical_warning": {
            "mood": "critical",
            "palette": "critical_red",
            "bands": {
                "low": {"postfx": {"vignette": 0.35}, "haptics": {"pulse": 0.35}},
                "medium": {"postfx": {"vignette": 0.45}, "haptics": {"pulse": 0.50}},
                "high": {"postfx": {"vignette": 0.58}, "haptics": {"pulse": 0.70}},
                "extreme": {"postfx": {"vignette": 0.70}, "haptics": {"pulse": 0.88}},
            },
        },
        "institutional_signal": {
            "mood": "precision",
            "palette": "institutional_blue",
            "bands": {
                "low": {"camera": {"orbit_speed": 0.22}, "audio": {"layer": "institutional_soft"}},
                "medium": {"camera": {"orbit_speed": 0.28}, "audio": {"layer": "institutional_drive"}},
                "high": {"camera": {"orbit_speed": 0.33}, "audio": {"layer": "institutional_drive"}},
                "extreme": {"camera": {"orbit_speed": 0.38}, "audio": {"layer": "institutional_drive"}},
            },
        },
        "harmonic_peak": {
            "mood": "harmonic",
            "palette": "harmonic_cyan",
            "bands": {
                "low": {"particles": {"trail_length": 0.70}},
                "medium": {"particles": {"trail_length": 0.95}},
                "high": {"particles": {"trail_length": 1.20}},
                "extreme": {"particles": {"trail_length": 1.45}},
            },
        },
        "service_degraded": {
            "mood": "degraded",
            "palette": "service_orange",
            "bands": {
                "low": {"audio": {"layer": "degraded_soft"}},
                "medium": {"audio": {"layer": "degraded_soft"}, "camera": {"shake": 0.12}},
                "high": {"audio": {"layer": "degraded_hard"}, "camera": {"shake": 0.20}},
                "extreme": {"audio": {"layer": "degraded_hard"}, "camera": {"shake": 0.28}},
            },
        },
        "haptic_tick": {
            "mood": "control",
            "bands": {
                "low": {"haptics": {"pulse": 0.20, "duration_ms": 80}},
                "medium": {"haptics": {"pulse": 0.40, "duration_ms": 110}},
                "high": {"haptics": {"pulse": 0.60, "duration_ms": 140}},
                "extreme": {"haptics": {"pulse": 0.80, "duration_ms": 170}},
            },
        },
    },
    "scene_overrides": {
        "core": {
            "default": {
                "camera": {"orbit_speed": 0.30},
            }
        },
        "harmonic": {
            "default": {
                "palette": "harmonic_cyan",
                "particles": {"turbulence": 0.55},
            },
            "bands": {
                "high": {"postfx": {"bloom": 0.58}},
                "extreme": {"postfx": {"bloom": 0.68}},
            },
        },
        "alert": {
            "default": {
                "palette": "critical_red",
                "postfx": {"vignette": 0.55},
            },
            "bands": {
                "high": {"camera": {"shake": 0.24}},
                "extreme": {"camera": {"shake": 0.35}},
            },
        },
    },
    "hints": {
        "cinematic": {
            "postfx": {"film_grain": 0.18},
            "camera": {"fov_boost": 4.0},
        },
        "investor": {
            "camera": {"orbit_speed": 0.24},
            "audio": {"layer": "institutional_drive"},
        },
        "sports": {
            "palette": "sports_neon",
            "particles": {"turbulence": 0.65},
        },
    },
}


DEFAULT_SCENE_SIMULATION_SCENARIOS: dict[str, Any] = {
    "schema": "luma_scene_simulation_scenarios_v1",
    "version": "2026-05-09",
    "scenarios": {
        "institutional_open": {
            "label": "Institutional Open",
            "description": "Warm-up into conviction with rising institutional pressure.",
            "scene": "core",
            "hint": "investor",
            "detail": {
                "source": "scenario_institutional_open",
            },
            "steps": [
                {"cue": "idle_breathe", "intensity": 0.28, "wait_ms": 180},
                {"scene": "harmonic", "cue": "institutional_signal", "intensity": 0.62, "wait_ms": 230},
                {"scene": "harmonic", "cue": "success_pulse", "intensity": 0.76, "wait_ms": 240},
                {"scene": "harmonic", "cue": "institutional_signal", "intensity": 0.88, "wait_ms": 270},
            ],
        },
        "harmonic_breakout": {
            "label": "Harmonic Breakout",
            "description": "Cross-domain harmonic acceleration and breakout confirmation.",
            "scene": "harmonic",
            "hint": "cinematic",
            "detail": {
                "source": "scenario_harmonic_breakout",
            },
            "steps": [
                {"cue": "harmonic_peak", "intensity": 0.52, "wait_ms": 150},
                {"cue": "harmonic_peak", "intensity": 0.72, "wait_ms": 170},
                {"cue": "institutional_signal", "hint": "investor", "intensity": 0.79, "wait_ms": 180},
                {"cue": "success_pulse", "hint": "investor", "intensity": 0.86, "wait_ms": 240},
            ],
        },
        "risk_off_recovery": {
            "label": "Risk-Off Recovery",
            "description": "Handles drawdown shock then stabilizes into controlled recovery.",
            "scene": "alert",
            "hint": "cinematic",
            "detail": {
                "source": "scenario_risk_off_recovery",
            },
            "steps": [
                {"cue": "warning_pulse", "intensity": 0.74, "wait_ms": 170},
                {"cue": "service_degraded", "intensity": 0.82, "wait_ms": 190},
                {"cue": "critical_warning", "intensity": 0.94, "wait_ms": 230},
                {"scene": "core", "cue": "warning_pulse", "intensity": 0.58, "wait_ms": 230},
                {"scene": "core", "cue": "idle_breathe", "hint": "investor", "intensity": 0.35, "wait_ms": 260},
            ],
        },
    },
}


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _deep_merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], val)
        else:
            merged[key] = copy.deepcopy(val)
    return merged


def _clamp_intensity(value: Any) -> float:
    try:
        n = float(value)
    except Exception:
        return 0.5
    return max(0.0, min(1.0, n))


def _clamp_int_range(value: Any, fallback: int, min_value: int, max_value: int) -> int:
    try:
        n = int(float(value))
    except Exception:
        return fallback
    return max(min_value, min(max_value, n))


def _build_simulation_intensity_sequence(
    start_intensity: Any,
    end_intensity: Any,
    steps: int,
    include_reverse: bool,
) -> list[float]:
    start = _clamp_intensity(start_intensity)
    end = _clamp_intensity(end_intensity)
    bounded_steps = max(1, min(int(steps or 1), 30))

    if bounded_steps == 1:
        sequence = [end]
    else:
        span = end - start
        sequence = [round(start + span * (i / (bounded_steps - 1)), 4) for i in range(bounded_steps)]

    if include_reverse and len(sequence) > 1:
        sequence.extend(reversed(sequence[:-1]))
    return sequence


def _intensity_band(intensity: float) -> str:
    if intensity >= 0.85:
        return "extreme"
    if intensity >= 0.65:
        return "high"
    if intensity >= 0.35:
        return "medium"
    return "low"


def _load_scene_visual_profile_config() -> dict[str, Any]:
    loaded = load_json(SCENE_VISUAL_PROFILE_FILE, {})
    if not isinstance(loaded, dict):
        return copy.deepcopy(DEFAULT_SCENE_VISUAL_PROFILES)
    return _deep_merge_dicts(DEFAULT_SCENE_VISUAL_PROFILES, loaded)


def _load_scene_simulation_scenario_config() -> dict[str, Any]:
    loaded = load_json(SCENE_SIMULATION_SCENARIO_FILE, {})
    if not isinstance(loaded, dict):
        return copy.deepcopy(DEFAULT_SCENE_SIMULATION_SCENARIOS)
    return _deep_merge_dicts(DEFAULT_SCENE_SIMULATION_SCENARIOS, loaded)


def _extract_scene_simulation_steps(raw_steps: Any, fallback_scene: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not isinstance(raw_steps, list):
        return steps

    for raw in raw_steps:
        if not isinstance(raw, dict):
            continue
        cue = str(raw.get("cue", "") or "").strip()
        if not cue:
            continue

        steps.append(
            {
                "scene": str(raw.get("scene") or fallback_scene or "core"),
                "cue": cue,
                "intensity": _clamp_intensity(raw.get("intensity", 0.5)),
                "wait_ms": _clamp_int_range(raw.get("wait_ms", 200), 200, 40, 8000),
                "hint": str(raw.get("hint", "") or "").strip().lower(),
                "detail": _safe_dict(raw.get("detail")),
            }
        )

    return steps


def _resolve_scene_visual_profile(
    scene: str,
    cue: str,
    intensity: float,
    detail: dict[str, Any],
) -> dict[str, Any]:
    cfg = _load_scene_visual_profile_config()
    cues = _safe_dict(cfg.get("cues"))
    scene_overrides = _safe_dict(cfg.get("scene_overrides"))
    hints = _safe_dict(cfg.get("hints"))

    cue_cfg = _safe_dict(cues.get(cue))
    scene_cfg = _safe_dict(scene_overrides.get(scene))
    hint_name = str(detail.get("visual_profile_hint", "") or "").strip().lower()
    if not hint_name:
        src = str(detail.get("source", "") or "").strip().lower()
        if "investor" in src or cue == "institutional_signal":
            hint_name = "investor"
        elif "harmonic" in src or cue == "harmonic_peak":
            hint_name = "cinematic"
        elif "sports" in src:
            hint_name = "sports"

    band = str(detail.get("profile_band", "") or "").strip().lower()
    if band not in {"low", "medium", "high", "extreme"}:
        band = _intensity_band(intensity)

    profile = _safe_dict(cfg.get("defaults"))

    cue_base = {k: v for k, v in cue_cfg.items() if k != "bands"}
    if cue_base:
        profile = _deep_merge_dicts(profile, cue_base)
    cue_bands = _safe_dict(cue_cfg.get("bands"))
    cue_band_cfg = _safe_dict(cue_bands.get(band))
    if cue_band_cfg:
        profile = _deep_merge_dicts(profile, cue_band_cfg)

    scene_default = _safe_dict(scene_cfg.get("default"))
    if scene_default:
        profile = _deep_merge_dicts(profile, scene_default)
    scene_bands = _safe_dict(scene_cfg.get("bands"))
    scene_band_cfg = _safe_dict(scene_bands.get(band))
    if scene_band_cfg:
        profile = _deep_merge_dicts(profile, scene_band_cfg)

    if hint_name:
        hint_cfg = _safe_dict(hints.get(hint_name))
        if hint_cfg:
            profile = _deep_merge_dicts(profile, hint_cfg)

    profile["schema"] = "luma_scene_visual_profile_applied_v1"
    profile["config_schema"] = str(cfg.get("schema", "luma_scene_visual_profile_v1"))
    profile["config_version"] = str(cfg.get("version", "unknown"))
    profile["scene"] = scene
    profile["cue"] = cue
    profile["band"] = band
    profile["intensity"] = intensity
    profile["applied_utc"] = now_utc()
    return profile


def _build_scene_cue_packet(
    scene: Any,
    cue: Any,
    intensity: Any,
    detail: Any,
    source: str,
) -> dict[str, Any]:
    safe_scene = str(scene or "core")
    safe_cue = str(cue or "pulse")
    safe_intensity = _clamp_intensity(intensity)
    safe_detail = _safe_dict(detail)

    visual_profile = _resolve_scene_visual_profile(safe_scene, safe_cue, safe_intensity, safe_detail)
    enriched_detail = dict(safe_detail)
    enriched_detail.setdefault("profile_band", visual_profile.get("band"))
    enriched_detail.setdefault("profile_source", "gateway_scene_visual_profiles")
    enriched_detail["visual_profile"] = visual_profile

    return {
        "type": "scene_cue",
        "data": {
            "ts": now_utc(),
            "scene": safe_scene,
            "cue": safe_cue,
            "intensity": safe_intensity,
            "detail": enriched_detail,
            "source": source,
        },
    }


class RemediationTriggerRequest(BaseModel):
    engine: str
    execute: bool = False
    force: bool = False


def _last_verified_txid(events: list[dict[str, Any]]) -> str:
    for event in reversed(events):
        validation = event.get("validation_result", {}) or {}
        txid = validation.get("txid") or event.get("txid") or event.get("order_id")
        if isinstance(txid, list):
            txid = txid[0] if txid else None
        if txid:
            return str(txid)
    return "n/a"


def _top_strategy_summary(brief: dict[str, Any]) -> str:
    rows = brief.get("strategy_leaderboard", []) or []
    if not rows:
        return "Top strategy leaderboard is not ready yet."
    top = rows[0]
    return (
        f"Top strategy is {top.get('strategy', 'n/a')} with algo {top.get('algo', 'n/a')}, "
        f"test Sharpe {float(top.get('test_sharpe', 0.0) or 0.0):.3f}, "
        f"win rate {float(top.get('test_win_rate', 0.0) or 0.0):.2f}, "
        f"and institutional score {float(top.get('inst_score', 0.0) or 0.0):.2f}."
    )


def _guide_response(req: GuideRequest, snapshot: dict[str, Any], brief: dict[str, Any]) -> str:
    prompt = (req.prompt or "").strip()
    q = prompt.lower()
    headline = brief.get("headline", {}) or {}
    scout = snapshot.get("scout", {}) or {}
    infra = snapshot.get("infra", {}) or {}
    harmonic = snapshot.get("harmonic", {}) or {}
    proof = brief.get("execution_proof", []) or []
    services = headline.get("services_up", "n/a")
    services_text = "health pending"
    if isinstance(services, str) and "/" in services:
        left, _, right = services.partition("/")
        if (left.isdigit() and right.isdigit()):
            services_text = f"{services} up" if int(right) > 0 else "health pending"
    elif services not in {None, "", "n/a"}:
        services_text = str(services)
    txid = _last_verified_txid(proof)

    pitch = (
        "LumaCore is a single operating surface for execution proof, cross-sector intelligence, and production artist discovery. "
        f"Current paper equity is {headline.get('equity_text', 'n/a')} with PnL {headline.get('net_pnl_text', 'n/a')}, "
        f"services are {services_text}, infra top lane is {headline.get('infra_top_lane', infra.get('top_lane', 'n/a'))}, "
        f"edge verdict is {headline.get('edge_verdict', snapshot.get('edge', {}).get('verdict', 'UNKNOWN'))}, "
        f"package leverage is {float(headline.get('package_usage_pct', snapshot.get('packages', {}).get('usage_pct', 0.0)) or 0.0):.1f}%, "
        f"and the latest verified execution proof points to TXID {txid}."
    )

    analyst = (
        f"Execution: {headline.get('closed_trades', 0)} closed trades, win rate {float(headline.get('win_rate_pct', 0.0) or 0.0):.1f}%, "
        f"profit factor {float(headline.get('profit_factor', 0.0) or 0.0):.2f}, rolling Sharpe {float(headline.get('sharpe', 0.0) or 0.0):.3f}. "
        f"Edge trust is {headline.get('edge_verdict', snapshot.get('edge', {}).get('verdict', 'UNKNOWN'))} "
        f"with score {float(headline.get('edge_score', snapshot.get('edge', {}).get('score', 0.0)) or 0.0):.1f}. "
        f"Harmonic top asset is {headline.get('harmonic_top_asset', harmonic.get('top_asset', 'n/a'))} with score {float(headline.get('harmonic_top_score', harmonic.get('top_score', 0.0)) or 0.0):.3f}. "
        + _top_strategy_summary(brief)
    )

    scout_msg = (
        f"LumaScout is tracking {scout.get('artists', 0)} artists with {scout.get('candidates', 0)} production candidates. "
        f"Top production-grade artist is {scout.get('top_artist', 'n/a')}. "
        "Production outputs are filtered for live, unsigned, non-suspicious rows with institutional quality gates."
    )

    infra_msg = (
        f"Cross-sector intelligence currently prioritizes {infra.get('top_lane', 'n/a')} with translated active surface {infra.get('active_surface_text', 'n/a')}. "
        f"Services health is {services_text}, and the gateway is aggregating live provider evidence into the investor brief."
    )

    proof_msg = (
        f"The latest execution proof chain includes verified event records and most recent TXID {txid}. "
        f"Closed trades snapshot is {headline.get('closed_trades', 0)} and current equity is {headline.get('equity_text', 'n/a')}."
    )

    if req.mode == "pitch":
        return pitch + (" " + scout_msg if any(k in q for k in ["artist", "scout", "music", "talent"]) else "")

    if any(k in q for k in ["artist", "scout", "music", "unsigned", "talent", "production"]):
        return scout_msg
    if any(k in q for k in ["proof", "txid", "trade", "execution", "order", "live"]):
        return proof_msg
    if any(k in q for k in ["sector", "infra", "api", "provider", "macro", "cross-sector", "energy", "fred", "eia"]):
        return infra_msg
    if any(k in q for k in ["sharpe", "alpha", "strategy", "signal", "model", "harmonic"]):
        return analyst
    if req.mode == "analyst":
        return analyst
    return "Concierge mode. " + pitch + " " + analyst


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        stale: list[WebSocket] = []
        text = json.dumps(payload)
        # Iterate over a stable snapshot because websocket handlers can disconnect
        # concurrently and mutate the underlying set during broadcast.
        for ws in tuple(self.connections):
            try:
                await ws.send_text(text)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws)


app = FastAPI(title="Luma Experience Gateway", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if _PROMETHEUS_AVAILABLE:
    _PrometheusInstrumentator().instrument(app).expose(app, endpoint="/metrics")

# LinkedIn auth router (no-ops gracefully when LINKEDIN_CLIENT_ID is missing)
try:
    from linkedin_router import router as _linkedin_router  # type: ignore
    app.include_router(_linkedin_router)
except Exception as _li_err:  # pragma: no cover
    log.warning("linkedin_router not mounted: %s", _li_err)

# Forecast API (innovation #3) — serves router-chosen forecasts with CI bands
try:
    from forecast_api import router as _forecast_router  # type: ignore
    app.include_router(_forecast_router)
except Exception as _fc_err:  # pragma: no cover
    log.warning("forecast_api not mounted: %s", _fc_err)

# Grants API (innovation #15) — grant application factory
try:
    from grants_api import router as _grants_router  # type: ignore
    app.include_router(_grants_router)
except Exception as _gr_err:  # pragma: no cover
    log.warning("grants_api not mounted: %s", _gr_err)

# Opportunities API — federal grant/contract harvester + filler bot
try:
    from opportunities_api import router as _opps_router  # type: ignore
    app.include_router(_opps_router)
except Exception as _op_err:  # pragma: no cover
    log.warning("opportunities_api not mounted: %s", _op_err)

# Autonomous Agent Manifest — unified human-in-the-loop approval queue
try:
    from autonomous_agent_manifest import router as _agents_router  # type: ignore
    app.include_router(_agents_router)
except Exception as _ag_err:  # pragma: no cover
    log.warning("autonomous_agent_manifest not mounted: %s", _ag_err)

manager = ConnectionManager()


# Wire grants_api -> WebSocket so Node-RED / Unity / Mission Control get
# push events on approve / submitted.
try:
    import asyncio as _asyncio
    from grants_api import set_event_sink as _grants_set_sink  # type: ignore

    def _grants_event_sink(payload: dict) -> None:
        try:
            loop = _asyncio.get_event_loop()
            if loop.is_running():
                _asyncio.create_task(manager.broadcast(payload))
        except Exception:
            pass

    _grants_set_sink(_grants_event_sink)
except Exception as _gs_err:  # pragma: no cover
    log.warning("grants websocket sink not wired: %s", _gs_err)


@app.on_event("startup")
async def startup_event() -> None:
    DASH.mkdir(parents=True, exist_ok=True)


@app.get("/")
def root() -> RedirectResponse:
    # Unified Luma Quant Lab cockpit — every module mounted as a pane.
    return RedirectResponse(url="/quant_lab.html", status_code=307)


@app.get("/health")
def health() -> dict[str, Any]:
    supervisor = load_supervisor_health(None)
    if supervisor is None:
        svc_status = {"supervisor": "not_running"}
    else:
        svc_status = {
            "supervisor_pid": supervisor.get("supervisor_pid"),
            "all_healthy": supervisor.get("all_healthy"),
            "supervisor_tick": supervisor.get("tick"),
            "supervisor_updated_utc": supervisor.get("timestamp_utc"),
            "services": {
                s["name"]: {"running": s["running"], "pid": s["pid"], "restarts": s["restart_count"]}
                for s in supervisor.get("services", [])
            },
        }
    return {"status": "ok", "generated_utc": now_utc(), **svc_status}


@app.get("/api/snapshot")
def snapshot() -> dict[str, Any]:
    return build_snapshot()


@app.get("/api/evidence/latest")
def evidence_latest(force: bool = False) -> dict[str, Any]:
    return load_latest_dashboard_evidence(force=bool(force))


@app.get("/api/proofpack/harmonic/runs")
def harmonic_proofpack_runs(limit: int = 8) -> dict[str, Any]:
    capped = max(1, min(int(limit or 8), 40))
    run_dirs = _harmonic_proofpack_run_dirs()
    payloads = [_harmonic_proofpack_run_payload(run_dir) for run_dir in run_dirs[:capped]]
    latest_pointer = load_json(HARMONIC_PROOFPACK_LATEST_FILE, {})
    if not isinstance(latest_pointer, dict):
        latest_pointer = {}
    return {
        "generated_utc": now_utc(),
        "status": "ok" if payloads else "not_found",
        "count": len(payloads),
        "total_runs": len(run_dirs),
        "latest_pointer": latest_pointer,
        "runs": payloads,
    }


@app.get("/api/proofpack/harmonic/latest")
def harmonic_proofpack_latest() -> dict[str, Any]:
    run_dirs = _harmonic_proofpack_run_dirs()
    latest_pointer = load_json(HARMONIC_PROOFPACK_LATEST_FILE, {})
    if not isinstance(latest_pointer, dict):
        latest_pointer = {}

    if not run_dirs:
        return {
            "generated_utc": now_utc(),
            "status": "not_found",
            "available": False,
            "message": "No harmonic_backprop_proofpack runs found. Execute harmonic_backprop_proofpack.py first.",
            "latest_pointer": latest_pointer,
        }

    payload = _harmonic_proofpack_run_payload(run_dirs[0])
    return {
        "generated_utc": now_utc(),
        "status": "ok",
        "available": True,
        "latest_pointer": latest_pointer,
        **payload,
    }


@app.get("/api/proofpack/harmonic/run/{run_id}")
def harmonic_proofpack_run(run_id: str) -> dict[str, Any]:
    safe_run_id = str(run_id or "").strip()
    if not safe_run_id:
        return {
            "generated_utc": now_utc(),
            "status": "error",
            "message": "run_id is required",
        }

    target_dir = HARMONIC_PROOFPACK_RUNS_DIR / safe_run_id
    if not target_dir.exists() or not target_dir.is_dir() or not (target_dir / "summary.json").exists():
        return {
            "generated_utc": now_utc(),
            "status": "not_found",
            "available": False,
            "run_id": safe_run_id,
            "message": f"Run '{safe_run_id}' not found under harmonic_backprop_proofpack outputs.",
        }

    payload = _harmonic_proofpack_run_payload(target_dir)
    return {
        "generated_utc": now_utc(),
        "status": "ok",
        "available": True,
        **payload,
    }


@app.get("/api/ops/staleness")
def ops_staleness() -> dict[str, Any]:
    payload = load_json(STALENESS_REPORT_FILE, {})
    if not isinstance(payload, dict) or not payload:
        return {
            "generated_utc": now_utc(),
            "status": "not_found",
            "available": False,
            "message": "No staleness report found. Run code/deploy/end_to_end_staleness_finder.py first.",
            "report_path": str(STALENESS_REPORT_FILE),
        }
    return payload


@app.get("/api/ops/lumaq")
def ops_lumaq() -> dict[str, Any]:
    payload = load_json(LUMAQ_BRAIN_REPORT_FILE, {})
    if not isinstance(payload, dict) or not payload:
        return {
            "generated_utc": now_utc(),
            "status": "not_found",
            "available": False,
            "message": "No LumaQ brain report found. Run code/deploy/lumaq_brain_builder.py first.",
            "report_path": str(LUMAQ_BRAIN_REPORT_FILE),
        }
    return payload


@app.get("/api/ops/lumaq/top10")
def ops_lumaq_top10() -> dict[str, Any]:
    payload = load_json(LUMAQ_TOP10_REGISTRY_FILE, {})
    if not isinstance(payload, dict) or not payload:
        return {
            "generated_utc": now_utc(),
            "status": "not_found",
            "available": False,
            "message": "No LumaQ top-10 registry found. Run code/deploy/build_lumaq_execution_pack.py first.",
            "report_path": str(LUMAQ_TOP10_REGISTRY_FILE),
        }
    return payload


@app.get("/api/harmonic/top")
def harmonic_top() -> dict[str, Any]:
    """Live harmonic edge signals across all domains — sports, crypto, infra."""
    ranked = load_json(HARMONIC_RANKED_FILE, {})
    if not isinstance(ranked, dict):
        ranked = {}
    summary: dict = ranked.get("summary", {}) or {}
    top_signals: list = (ranked.get("top_signals", []) or [])[:20]

    # Derive root-level fields the dashboard panels expect
    top_signal = top_signals[0] if top_signals else {}
    ff = top_signal.get("flowform", {}) or {}
    top_score = float(ff.get("hybrid_harmonic_score", 0.0) or 0.0)
    # Fall back to summary max if flowform missing
    if top_score == 0.0 and summary:
        top_score = max((v.get("top_score", 0) if isinstance(v, dict) else 0) for v in summary.values())
    top_asset = str(top_signal.get("asset", "")) or ""
    domain_count = len([d for d, v in summary.items() if (v.get("count", 0) if isinstance(v, dict) else 0) > 0])

    return {
        "generated_utc":   now_utc(),
        "source_utc":      ranked.get("generated_utc"),
        "total_signals":   ranked.get("total", len(top_signals)),
        "top_asset":       top_asset,
        "top_score":       round(top_score, 4),
        "domain_count":    domain_count,
        "domain_breakdown": summary,
        "summary":         summary,
        "top_signals":     top_signals,
    }


@app.get("/api/harmonic/domain/{domain}")
def harmonic_domain(domain: str) -> dict[str, Any]:
    """Per-domain harmonic signals: sports | crypto | infra | digital_scout."""
    file_map = {
        "sports":        HARMONIC_SPORTS_FILE,
        "crypto":        HARMONIC_CRYPTO_FILE,
        "infra":         HARMONIC_INFRA_FILE,
    }
    path = file_map.get(domain.lower())
    if path is None:
        return {"error": f"unknown domain '{domain}'", "valid": list(file_map.keys())}
    data = load_json(path, {})
    return data if isinstance(data, dict) else {"error": "data unavailable"}


@app.get("/api/unity/edge")
def unity_edge() -> dict[str, Any]:
    """
    Flat, Unity-friendly JSON payload for XR/3D scene integration.
    Each signal becomes a node in Unity's 3D harmonic field visualization.
    All floats guaranteed — no nulls.
    """
    ranked = load_json(HARMONIC_RANKED_FILE, {})
    signals = ranked.get("top_signals", [])[:50] if isinstance(ranked, dict) else []
    nodes = []
    for i, sig in enumerate(signals):
        ff = sig.get("flowform", {}) or {}
        nodes.append({
            "id":               i,
            "asset":            str(sig.get("asset", "")),
            "domain":           str(sig.get("domain", "")),
            "signal_type":      str(sig.get("signal_type", "")),
            "edge_pct":         round(float(sig.get("edge_pct", 0.0) or 0.0), 4),
            "harmonic_score":   round(float(ff.get("hybrid_harmonic_score", 0.0) or 0.0), 4),
            "curvature":        round(float(ff.get("curvature_score", 0.0) or 0.0), 4),
            "resonance":        round(float(ff.get("resonance_score", 0.0) or 0.0), 4),
            "persistence":      round(float(ff.get("persistence_score", 0.0) or 0.0), 4),
            "phi_bonus":        round(float(ff.get("phi_resonance_bonus", 0.0) or 0.0), 4),
        })
    return {
        "generated_utc": now_utc(),
        "node_count":    len(nodes),
        "phi":           1.6180339887,
        "nodes":         nodes,
    }


@app.get("/api/unity/unified-edge")
def unity_unified_edge() -> dict[str, Any]:
    """
    Unified Unity feed: harmonic intelligence + unified trading execution state.
    Keeps the same flat node contract so existing Unity/Node-RED mappers continue to work.
    """
    harmonic = unity_edge()
    harmonic_nodes = list(harmonic.get("nodes", [])) if isinstance(harmonic, dict) else []

    alpha_signals_path = OUT / "unified_alpha" / "unified_alpha_signals.json"
    trade_state_path = OUT / "unified_trade" / "unified_trade_state.json"
    trade_perf_path = OUT / "unified_trade" / "unified_trade_performance.json"

    alpha_payload = load_json(alpha_signals_path, {})
    state = load_json(trade_state_path, {})
    perf = load_json(trade_perf_path, {})

    signals = alpha_payload.get("signals", []) if isinstance(alpha_payload, dict) else []
    open_positions = state.get("open_positions", []) if isinstance(state, dict) else []

    trading_nodes: list[dict[str, Any]] = []
    base_id = len(harmonic_nodes)

    for i, sig in enumerate(signals[:40]):
        sym = str(sig.get("symbol", ""))
        confidence = float(sig.get("confidence_pct", 0.0) or 0.0)
        ev = float(sig.get("expected_value_pct", 0.0) or 0.0)
        payoff = float(sig.get("payoff_multiple", 0.0) or 0.0)
        direction = str(sig.get("direction", ""))
        open_match = next((p for p in open_positions if str(p.get("symbol", "")) == sym), None)
        pnl = float((open_match or {}).get("current_pnl", 0.0) or 0.0)

        trading_nodes.append(
            {
                "id": base_id + i,
                "asset": sym,
                "domain": "trading",
                "signal_type": str(sig.get("signal_type", "alpha")),
                "edge_pct": round(ev, 4),
                "harmonic_score": round(confidence, 4),
                "curvature": round(abs(payoff) * 100.0, 4),
                "resonance": round(float(sig.get("historical_win_rate", 0.0) or 0.0), 4),
                "persistence": round(float(sig.get("lookback_days", 0.0) or 0.0), 4),
                "phi_bonus": 1.0 if bool(sig.get("is_moonshot", False)) else 0.0,
                "direction": direction,
                "open_position": bool(open_match),
                "open_pnl": round(pnl, 4),
            }
        )

    # ── Symbol Watcher Mesh nodes (live spike detections across 1693 symbols) ──
    mesh_nodes: list[dict[str, Any]] = []
    if SYMBOL_MESH_SUMMARY_FILE.exists():
        mesh_age = time.time() - SYMBOL_MESH_SUMMARY_FILE.stat().st_mtime
        if mesh_age <= 30.0:
            mesh_summary = load_json(SYMBOL_MESH_SUMMARY_FILE, {})
            mesh_top = mesh_summary.get("top_signals", []) if isinstance(mesh_summary, dict) else []
            mesh_base_id = len(harmonic_nodes) + len(trading_nodes)
            for j, sig in enumerate(mesh_top[:20]):
                if not isinstance(sig, dict):
                    continue
                z = float(sig.get("spike_z_score", 0.0) or 0.0)
                score = float(sig.get("spike_score", 0.0) or 0.0)
                is_real = bool(sig.get("spike_real", False))
                mesh_nodes.append({
                    "id": mesh_base_id + j,
                    "asset": str(sig.get("symbol", "")),
                    "domain": "mesh",
                    "signal_type": "real_spike" if is_real else "spike_candidate",
                    "edge_pct": round(abs(z) * 0.5, 4),
                    "harmonic_score": round(min(score * 20.0, 100.0), 4),
                    "curvature": round(abs(z), 4),
                    "resonance": round(float(sig.get("spread_bps", 0.0) or 0.0), 4),
                    "persistence": round(float(sig.get("age_sec", 0.0) or 0.0), 4),
                    "phi_bonus": 1.0 if is_real else 0.0,
                    "direction": str(sig.get("spike_direction", "") or ""),
                    "spike_real": is_real,
                    "spike_z_score": round(z, 4),
                    "last_price": sig.get("last_price"),
                })

    merged = harmonic_nodes + trading_nodes + mesh_nodes
    return {
        "generated_utc": now_utc(),
        "node_count": len(merged),
        "phi": 1.6180339887,
        "schema": "luma_unified_edge_v2",
        "domains": {
            "harmonic_nodes": len(harmonic_nodes),
            "trading_nodes": len(trading_nodes),
            "mesh_nodes": len(mesh_nodes),
            "open_positions": len(open_positions),
            "total_trades": int(float(perf.get("total_trades", 0) or 0)),
        },
        "nodes": merged,
    }


@app.post("/api/nodered/ingest")
async def nodered_ingest(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Node-RED can POST signal batches here.
    Gateway broadcasts them live to all WebSocket clients (Luma dashboard + Unity).
    """
    await manager.broadcast({"type": "nodered_signal", "data": payload, "ts": now_utc()})
    return {"status": "broadcast", "ts": now_utc(), "nodes": len(manager.connections)}


@app.get("/api/session/memory")
def session_memory() -> dict[str, Any]:
    return load_session_memory()


@app.get("/api/scene/profile-config")
def scene_profile_config() -> dict[str, Any]:
    payload = _load_scene_visual_profile_config()
    payload["generated_utc"] = now_utc()
    payload["source"] = str(SCENE_VISUAL_PROFILE_FILE)
    return payload


@app.get("/api/scene/profile")
def scene_profile(
    scene: str = "core",
    cue: str = "idle_breathe",
    intensity: float = 0.5,
    hint: str = "",
) -> dict[str, Any]:
    detail: dict[str, Any] = {}
    if hint.strip():
        detail["visual_profile_hint"] = hint.strip()
    profile = _resolve_scene_visual_profile(
        scene=str(scene or "core"),
        cue=str(cue or "idle_breathe"),
        intensity=_clamp_intensity(intensity),
        detail=detail,
    )
    return {
        "generated_utc": now_utc(),
        "scene": scene,
        "cue": cue,
        "intensity": _clamp_intensity(intensity),
        "profile": profile,
    }


@app.get("/api/scene/scenarios")
def scene_scenarios() -> dict[str, Any]:
    cfg = _load_scene_simulation_scenario_config()
    scenarios = _safe_dict(cfg.get("scenarios"))
    rows: list[dict[str, Any]] = []

    for name in sorted(scenarios.keys()):
        raw = _safe_dict(scenarios.get(name))
        fallback_scene = str(raw.get("scene", "core") or "core")
        steps = _extract_scene_simulation_steps(raw.get("steps"), fallback_scene=fallback_scene)
        if not steps:
            continue

        cues = list(dict.fromkeys(str(step.get("cue", "")) for step in steps if step.get("cue")))
        rows.append(
            {
                "name": str(name),
                "label": str(raw.get("label", name)),
                "description": str(raw.get("description", "") or ""),
                "scene": fallback_scene,
                "hint": str(raw.get("hint", "") or "").strip().lower(),
                "step_count": len(steps),
                "cues": cues,
                "steps": steps,
            }
        )

    return {
        "generated_utc": now_utc(),
        "schema": str(cfg.get("schema", "luma_scene_simulation_scenarios_v1")),
        "version": str(cfg.get("version", "unknown")),
        "source": str(SCENE_SIMULATION_SCENARIO_FILE),
        "scenarios": rows,
    }


@app.get("/api/scene/runs")
def scene_runs(limit: int = 20, run_type: str = "all") -> dict[str, Any]:
    bounded_limit = _clamp_int_range(limit, 20, 1, 300)
    run_type_key = str(run_type or "all").strip().lower()
    rows = _tail_jsonl(SCENE_SIMULATION_RUNS_FILE, max(60, bounded_limit * 4))

    if run_type_key in {"simulate", "scenario", "cue"}:
        rows = [
            row for row in rows
            if str(row.get("run_type", "") or "").strip().lower() == run_type_key
        ]
    else:
        run_type_key = "all"

    rows = rows[-bounded_limit:]
    summary = {
        "cue_runs": sum(
            1 for row in rows
            if str(row.get("run_type", "") or "").strip().lower() == "cue"
        ),
        "simulate_runs": sum(
            1 for row in rows
            if str(row.get("run_type", "") or "").strip().lower() == "simulate"
        ),
        "scenario_runs": sum(
            1 for row in rows
            if str(row.get("run_type", "") or "").strip().lower() == "scenario"
        ),
    }

    return {
        "generated_utc": now_utc(),
        "source": str(SCENE_SIMULATION_RUNS_FILE),
        "run_type": run_type_key,
        "count": len(rows),
        "summary": summary,
        "runs": rows,
    }


@app.post("/api/scene/scenario/run")
async def scene_scenario_run(req: CueScenarioRunRequest) -> dict[str, Any]:
    cfg = _load_scene_simulation_scenario_config()
    scenarios = _safe_dict(cfg.get("scenarios"))

    scenario_name = str(req.scenario or "").strip()
    raw = _safe_dict(scenarios.get(scenario_name))
    if not raw:
        return {
            "status": "error",
            "reason": "scenario_not_found",
            "scenario": scenario_name,
            "available_scenarios": sorted(str(name) for name in scenarios.keys()),
            "generated_utc": now_utc(),
        }

    fallback_scene = str(raw.get("scene", "core") or "core")
    steps = _extract_scene_simulation_steps(raw.get("steps"), fallback_scene=fallback_scene)
    if not steps:
        return {
            "status": "error",
            "reason": "scenario_empty",
            "scenario": scenario_name,
            "generated_utc": now_utc(),
        }

    try:
        interval_scale = float(req.interval_scale)
    except Exception:
        interval_scale = 1.0
    interval_scale = max(0.25, min(4.0, interval_scale))
    repeat = _clamp_int_range(req.repeat, 1, 1, 6)

    scenario_label = str(raw.get("label", scenario_name))
    scenario_hint = str(req.hint or raw.get("hint", "") or "").strip().lower()
    scenario_detail = _safe_dict(raw.get("detail"))
    request_detail = _safe_dict(req.detail)

    total_steps = len(steps) * repeat
    sent = 0
    events: list[dict[str, Any]] = []

    for cycle_idx in range(repeat):
        for step in steps:
            sent += 1
            step_detail = _safe_dict(step.get("detail"))
            step_hint = str(step.get("hint", "") or "").strip().lower()

            detail = dict(scenario_detail)
            detail.update(step_detail)
            detail.update(request_detail)
            if scenario_hint:
                detail.setdefault("visual_profile_hint", scenario_hint)
            if step_hint:
                detail["visual_profile_hint"] = step_hint
            detail.setdefault("source", f"scenario:{scenario_name}")
            detail["scenario"] = scenario_name
            detail["scenario_label"] = scenario_label
            detail["scenario_cycle"] = cycle_idx + 1
            detail["scenario_repeat"] = repeat
            detail["scenario_step"] = sent
            detail["scenario_total_steps"] = total_steps

            payload = _build_scene_cue_packet(
                scene=step.get("scene", fallback_scene),
                cue=step.get("cue", "idle_breathe"),
                intensity=step.get("intensity", 0.5),
                detail=detail,
                source="scenario_api",
            )
            await manager.broadcast(payload)

            visual_profile = (
                _safe_dict(_safe_dict(payload.get("data")).get("detail")).get("visual_profile", {})
            )
            wait_ms = _clamp_int_range(step.get("wait_ms", 200), 200, 40, 8000)
            scaled_wait_sec = max(0.04, min(8.0, float(wait_ms) * interval_scale / 1000.0))

            events.append(
                {
                    "step": sent,
                    "cycle": cycle_idx + 1,
                    "scene": str(step.get("scene", fallback_scene)),
                    "cue": str(step.get("cue", "idle_breathe")),
                    "intensity": round(float(step.get("intensity", 0.5) or 0.5), 4),
                    "band": visual_profile.get("band", "medium"),
                    "wait_ms": int(round(scaled_wait_sec * 1000.0)),
                }
            )

            if sent < total_steps:
                await asyncio.sleep(scaled_wait_sec)

    run_id = _record_scene_simulation_run(
        run_type="scenario",
        scene=fallback_scene,
        cue="scenario",
        events=events,
        detail=request_detail,
        scenario=scenario_name,
        label=scenario_label,
        hint=scenario_hint,
        repeat=repeat,
        interval_scale=interval_scale,
        source="scenario_api",
        config_version=str(cfg.get("version", "unknown")),
    )

    return {
        "status": "ok",
        "scenario": scenario_name,
        "label": scenario_label,
        "steps_sent": len(events),
        "repeat": repeat,
        "interval_scale": round(interval_scale, 3),
        "run_id": run_id,
        "events": events,
        "config_version": str(cfg.get("version", "unknown")),
        "generated_utc": now_utc(),
    }


@app.post("/api/session/event")
def session_event(req: SessionEvent) -> dict[str, Any]:
    memory = load_session_memory()
    events = list(memory.get("events", []))
    events.append(
        {
            "ts": now_utc(),
            "event": req.event,
            "source": req.source,
            "detail": req.detail,
        }
    )
    if len(events) > 500:
        events = events[-500:]
    memory["events"] = events
    save_session_memory(memory)
    return {"status": "ok", "events": len(events), "updated_utc": memory["updated_utc"]}


@app.post("/api/scene/cue")
async def scene_cue(req: CueRequest) -> dict[str, Any]:
    payload = _build_scene_cue_packet(
        scene=req.scene,
        cue=req.cue,
        intensity=req.intensity,
        detail=req.detail,
        source="api",
    )
    await manager.broadcast(payload)
    visual_profile = (
        _safe_dict(_safe_dict(payload.get("data")).get("detail")).get("visual_profile", {})
    )
    run_id = _record_scene_simulation_run(
        run_type="cue",
        scene=str(req.scene or "core"),
        cue=str(req.cue or "pulse"),
        events=[
            {
                "step": 1,
                "scene": str(req.scene or "core"),
                "cue": str(req.cue or "pulse"),
                "intensity": _clamp_intensity(req.intensity),
                "band": visual_profile.get("band", "medium"),
                "wait_ms": 0,
            }
        ],
        detail=_safe_dict(req.detail),
        scenario="",
        label="Single Cue",
        hint=str(_safe_dict(req.detail).get("visual_profile_hint", "") or ""),
        repeat=1,
        interval_scale=1.0,
        source="api",
        config_version=str(visual_profile.get("config_version", "unknown") or "unknown"),
    )
    return {
        "status": "ok",
        "sent": True,
        "cue": req.cue,
        "profile_band": visual_profile.get("band", "medium"),
        "profile_version": visual_profile.get("config_version", "unknown"),
        "run_id": run_id,
    }


@app.post("/api/scene/simulate")
async def scene_simulate(req: CueSimulationRequest) -> dict[str, Any]:
    sequence = _build_simulation_intensity_sequence(
        start_intensity=req.start_intensity,
        end_intensity=req.end_intensity,
        steps=req.steps,
        include_reverse=req.include_reverse,
    )
    interval_sec = max(0.05, min(3.0, float(req.interval_ms or 0) / 1000.0))
    safe_scene = str(req.scene or "core")
    safe_cue = str(req.cue or "idle_breathe")
    base_detail = _safe_dict(req.detail)
    if req.hint.strip():
        base_detail.setdefault("visual_profile_hint", req.hint.strip())
    base_detail.setdefault("source", "scene_simulator")

    events: list[dict[str, Any]] = []
    for idx, level in enumerate(sequence):
        detail = dict(base_detail)
        detail["sim_step"] = idx + 1
        detail["sim_total_steps"] = len(sequence)

        payload = _build_scene_cue_packet(
            scene=safe_scene,
            cue=safe_cue,
            intensity=level,
            detail=detail,
            source="simulator_api",
        )
        await manager.broadcast(payload)

        visual_profile = (
            _safe_dict(_safe_dict(payload.get("data")).get("detail")).get("visual_profile", {})
        )
        events.append(
            {
                "step": idx + 1,
                "intensity": round(level, 4),
                "band": visual_profile.get("band", "medium"),
            }
        )
        if idx < len(sequence) - 1:
            await asyncio.sleep(interval_sec)

    run_id = _record_scene_simulation_run(
        run_type="simulate",
        scene=safe_scene,
        cue=safe_cue,
        events=events,
        detail=base_detail,
        scenario="",
        label="Pulse Sweep",
        hint=str(req.hint or ""),
        repeat=1,
        interval_scale=1.0,
        source="simulator_api",
        config_version="unknown",
    )

    return {
        "status": "ok",
        "scene": safe_scene,
        "cue": safe_cue,
        "steps_sent": len(events),
        "interval_ms": int(round(interval_sec * 1000.0)),
        "run_id": run_id,
        "events": events,
        "generated_utc": now_utc(),
    }


@app.post("/api/guide/respond")
def guide_respond(req: GuideRequest) -> dict[str, Any]:
    data = build_snapshot()
    brief = investor_brief()
    message = _guide_response(req, data, brief)
    memory = load_session_memory()
    history = list(memory.get("guide_history", []))
    history.append(
        {
            "ts": now_utc(),
            "mode": req.mode,
            "prompt": req.prompt,
            "response": message,
        }
    )
    if len(history) > 300:
        history = history[-300:]
    memory["guide_history"] = history
    save_session_memory(memory)
    return {"generated_utc": now_utc(), "mode": req.mode, "response": message, "history_size": len(history)}


@app.post("/api/voice/synthesize")
async def voice_synthesize(req: VoiceSynthesizeRequest) -> dict[str, Any]:
    text = _clean_tts_text(req.text)
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    profile_key = str(req.profile or "luma_pitch").strip().lower()
    profile = VOICE_PROFILE_PRESETS.get(profile_key) or VOICE_PROFILE_PRESETS["luma_pitch"]

    if not _EDGE_TTS_AVAILABLE:
        return {
            "status": "not_ready",
            "provider": "edge-tts",
            "error": "edge-tts package not installed",
            "hint": "Install edge-tts in the active Python environment to enable neural narration.",
            "generated_utc": now_utc(),
        }

    rate = _edge_rate_from_multiplier(req.rate)
    pitch = _edge_pitch_from_multiplier(req.pitch)
    voice_name = str(profile.get("voice") or "en-US-JennyNeural")

    try:
        audio_bytes = await _synthesize_edge_tts_bytes(
            text=text,
            voice=voice_name,
            rate=rate,
            pitch=pitch,
        )
        if not audio_bytes:
            raise RuntimeError("empty audio output")
    except Exception as exc:
        return {
            "status": "error",
            "provider": "edge-tts",
            "error": f"tts_synthesis_failed: {exc}",
            "generated_utc": now_utc(),
        }

    return {
        "status": "ok",
        "provider": "edge-tts",
        "profile": profile_key,
        "voice": voice_name,
        "description": profile.get("description", ""),
        "mime_type": "audio/mpeg",
        "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
        "char_count": len(text),
        "generated_utc": now_utc(),
    }


# ── Investor Command-Room endpoints ──────────────────────────────────────────

def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        return [dict(r) for r in reader]
    except Exception:
        return []


def _tail_jsonl(path: Path, n: int = 50) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in lines[-n:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    return out


def _tail_jsonl_candidates(paths: list[Path], n: int = 200) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in paths:
        for row in _tail_jsonl(p, n):
            try:
                key = json.dumps(row, sort_keys=True)
            except Exception:
                key = str(row)
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
    merged.sort(key=lambda x: str(x.get("timestamp", x.get("generated_utc", ""))))
    return merged[-n:]


def _build_booth_explainer_brief_payload() -> dict[str, Any]:
    universe_map = load_json(UNIVERSE_MAP_FILE, {})
    catalog = load_json(NOBEL_ENGINE_CATALOG_FILE, {})
    heartbeat = load_json(LIVE_EXECUTOR_HEARTBEAT_FILE, {})
    mirror = load_json(PREMIUM_MIRROR_LATEST_FILE, {})
    trades = _tail_jsonl(LIVE_TRADE_LEDGER_FILE, 120)

    default_founder_profile = {
        "founder": "Robert BabyRay Ashworth",
        "company_system": "LumenCore / NovaCore / LumaCore",
        "uei": "SQY2XW71ZM51",
        "cage": "14TM8",
        "ein": "39-3507463",
        "uspto_non_provisional_application": "19/281,546",
        "patent_title": "LumenCore: A Modular AI Node Framework for Conscious Systems Integration",
    }

    founder_profile = default_founder_profile
    if isinstance(universe_map, dict):
        candidate = universe_map.get("founder_profile")
        if isinstance(candidate, dict) and candidate:
            founder_profile = candidate

    scan = universe_map.get("scan", {}) if isinstance(universe_map, dict) else {}
    roots = universe_map.get("roots", []) if isinstance(universe_map, dict) else []
    engine_counts = scan.get("engine_counts", {}) if isinstance(scan, dict) else {}

    roots_present = sum(1 for root in roots if isinstance(root, dict) and bool(root.get("exists")))
    roots_total = len([root for root in roots if isinstance(root, dict)])

    engine_rows = catalog.get("engines", []) if isinstance(catalog, dict) else []
    if not isinstance(engine_rows, list):
        engine_rows = []

    catalog_by_id: dict[str, dict[str, Any]] = {}
    for row in engine_rows:
        if not isinstance(row, dict):
            continue
        engine_id = str(row.get("engine_id", "") or "")
        if not engine_id:
            continue
        catalog_by_id[engine_id] = row

    ranked_engine_hits: list[tuple[str, int]] = []
    if isinstance(engine_counts, dict):
        for engine_id, hits in engine_counts.items():
            ranked_engine_hits.append((str(engine_id), int(_safe_num(hits, 0))))
    ranked_engine_hits.sort(key=lambda item: item[1], reverse=True)

    top_engines: list[dict[str, Any]] = []
    for engine_id, hits in ranked_engine_hits[:15]:
        info = catalog_by_id.get(engine_id, {})
        one_pager = info.get("one_pager", {}) if isinstance(info, dict) else {}
        if not isinstance(one_pager, dict):
            one_pager = {}
        top_engines.append(
            {
                "engine_id": engine_id,
                "name": str(info.get("name", engine_id)),
                "asset_hits": int(hits),
                "readiness_score_0_100": round(_safe_num(info.get("readiness_score_0_100", 0.0), 0.0), 2),
                "what_it_does": str(one_pager.get("what_it_does", "")),
                "who_buys_it": str(one_pager.get("who_buys_it", "")),
            }
        )

    latest_trade = trades[-1] if trades else {}
    if not isinstance(latest_trade, dict):
        latest_trade = {}

    recent_trades: list[dict[str, Any]] = []
    for row in trades[-10:]:
        if not isinstance(row, dict):
            continue
        recent_trades.append(
            {
                "timestamp": str(row.get("timestamp", "") or ""),
                "txid": str(row.get("txid", "") or ""),
                "symbol": str(row.get("symbol", "") or ""),
                "pair": str(row.get("pair", "") or ""),
                "side": str(row.get("side", "") or ""),
                "status": str(row.get("status", "") or ""),
                "size_usd": round(_safe_num(row.get("size_usd", 0.0), 0.0), 6),
            }
        )

    return {
        "generated_utc": now_utc(),
        "schema": "luma_booth_explainer_brief_v1",
        "founder_profile": founder_profile,
        "indexing": {
            "files_indexed": int(_safe_num((scan or {}).get("files_scanned", 0), 0)),
            "total_size_bytes": int(_safe_num((scan or {}).get("total_size_bytes", 0), 0)),
            "roots_present": int(roots_present),
            "roots_total": int(roots_total),
            "scan_capped": bool((scan or {}).get("scan_capped", False)),
        },
        "catalog": {
            "engine_count": len(engine_rows),
            "assets_source_rows": int(_safe_num(catalog.get("assets_source_rows", 0), 0)) if isinstance(catalog, dict) else 0,
            "top_engines": top_engines,
        },
        "live_execution": {
            "heartbeat": {
                "status": str((heartbeat or {}).get("status", "unknown")),
                "reason": str((heartbeat or {}).get("reason", "")),
                "symbol": str((heartbeat or {}).get("selected_symbol") or (heartbeat or {}).get("symbol") or ""),
                "universe_candidate_count": int(_safe_num((heartbeat or {}).get("universe_candidate_count", 0), 0)),
                "timestamp_utc": str((heartbeat or {}).get("timestamp_utc", "")),
            },
            "latest_trade": {
                "timestamp": str(latest_trade.get("timestamp", "") or ""),
                "txid": str(latest_trade.get("txid", "") or ""),
                "symbol": str(latest_trade.get("symbol", "") or ""),
                "pair": str(latest_trade.get("pair", "") or ""),
                "side": str(latest_trade.get("side", "") or ""),
                "status": str(latest_trade.get("status", "") or ""),
                "size_usd": round(_safe_num(latest_trade.get("size_usd", 0.0), 0.0), 6),
            },
            "recent_trade_count": len(recent_trades),
            "recent_trades": recent_trades,
        },
        "premium_mirror": {
            "generated_utc": str((mirror or {}).get("generated_utc", "")),
            "destination_root": str((mirror or {}).get("destination_root", "")),
            "total_sources": int(_safe_num((mirror or {}).get("total_sources", 0), 0)),
            "total_files_seen": int(_safe_num((mirror or {}).get("total_files_seen", 0), 0)),
            "total_files_copied": int(_safe_num((mirror or {}).get("total_files_copied", 0), 0)),
            "total_bytes_seen": int(_safe_num((mirror or {}).get("total_bytes_seen", 0), 0)),
            "chain_of_custody_sha256": str((mirror or {}).get("chain_of_custody_sha256", "")),
        },
        "artifact_paths": {
            "universe_map_json": str(UNIVERSE_MAP_FILE),
            "nobel_engine_catalog_json": str(NOBEL_ENGINE_CATALOG_FILE),
            "live_trade_ledger_jsonl": str(LIVE_TRADE_LEDGER_FILE),
            "live_executor_heartbeat_json": str(LIVE_EXECUTOR_HEARTBEAT_FILE),
            "premium_mirror_latest_json": str(PREMIUM_MIRROR_LATEST_FILE),
        },
    }


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")
    except Exception:
        pass


@app.get("/api/master/booth-brief")
def master_booth_brief() -> dict[str, Any]:
    payload = load_json(BOOTH_EXPLAINER_BRIEF_FILE, {})
    if isinstance(payload, dict) and payload:
        out = dict(payload)
        out["source"] = "prebuilt"
        out["served_utc"] = now_utc()
        return out

    out = _build_booth_explainer_brief_payload()
    out["source"] = "live_fallback"
    out["served_utc"] = now_utc()
    return out


def _scene_run_band_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        band = str(event.get("band", "") or "").strip().lower()
        if not band:
            continue
        counts[band] = int(counts.get(band, 0) or 0) + 1
    return counts


def _record_scene_simulation_run(
    run_type: str,
    scene: str,
    cue: str,
    events: list[dict[str, Any]],
    detail: dict[str, Any] | None,
    scenario: str,
    label: str,
    hint: str,
    repeat: int,
    interval_scale: float,
    source: str,
    config_version: str,
) -> str:
    run_id = f"{run_type}_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    safe_events = [dict(e) for e in events if isinstance(e, dict)]
    band_counts = _scene_run_band_counts(safe_events)
    first_event = safe_events[0] if safe_events else {}
    last_event = safe_events[-1] if safe_events else {}

    row = {
        "ts": now_utc(),
        "run_id": run_id,
        "run_type": str(run_type or "simulate"),
        "scenario": str(scenario or ""),
        "label": str(label or ""),
        "scene": str(scene or "core"),
        "cue": str(cue or "pulse"),
        "steps_sent": len(safe_events),
        "repeat": int(repeat or 1),
        "interval_scale": round(float(interval_scale or 1.0), 4),
        "hint": str(hint or ""),
        "band_counts": band_counts,
        "first_event": first_event,
        "last_event": last_event,
        "source": str(source or ""),
        "config_version": str(config_version or "unknown"),
        "detail": _safe_dict(detail),
    }
    _append_jsonl(SCENE_SIMULATION_RUNS_FILE, row)

    try:
        memory = load_session_memory()
        memory_events = list(memory.get("events", []))
        memory_events.append(
            {
                "ts": row.get("ts"),
                "event": "scene_simulation_run",
                "source": "gateway_scene",
                "detail": {
                    "run_id": run_id,
                    "run_type": row.get("run_type"),
                    "scenario": row.get("scenario"),
                    "scene": row.get("scene"),
                    "cue": row.get("cue"),
                    "steps_sent": row.get("steps_sent"),
                    "band_counts": row.get("band_counts"),
                },
            }
        )
        if len(memory_events) > 500:
            memory_events = memory_events[-500:]
        memory["events"] = memory_events
        save_session_memory(memory)
    except Exception:
        pass

    return run_id


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _remediation_action_map() -> dict[str, dict[str, Any]]:
    py = str(ROOT / ".venv" / "Scripts" / "python.exe")
    return {
        "spike_engine": {
            "argv": [py, "code/execution/spike_trade_engine.py"],
            "cooldown_sec": 90,
        },
        "fleet_coherence": {
            "argv": [py, "code/execution/fleet_coherence_monitor.py"],
            "cooldown_sec": 90,
        },
        "harmonic_resonance": {
            "argv": [py, "code/execution/harmonic_resonance_detector.py"],
            "cooldown_sec": 90,
        },
        "symbol_mesh": {
            "argv": [py, "code/execution/symbol_watcher_fleet.py"],
            "cooldown_sec": 90,
        },
        "unified_alpha": {
            "argv": [py, "code/unified_alpha_engine.py", "--daemon"],
            "cooldown_sec": 180,
        },
        "unified_trade": {
            "argv": [py, "code/unified_trade_executor.py", "--daemon"],
            "cooldown_sec": 180,
        },
        "innovation_autopilot": {
            "argv": [py, "code/execution/innovation_autopilot.py"],
            "cooldown_sec": 180,
        },
        "benchmark_beater": {
            "argv": [py, "code/execution/benchmark_beater.py", "--loop"],
            "cooldown_sec": 180,
        },
        "sector_clock": {
            "argv": [py, "code/execution/sector_clock_beater.py", "--loop"],
            "cooldown_sec": 180,
        },
        "system_overlord": {
            "argv": [py, "code/execution/system_overlord_20s.py", "--loop"],
            "cooldown_sec": 180,
        },
        "supervisor_health": {
            "argv": [py, "code/luma_supervisor.py"],
            "cooldown_sec": 240,
        },
    }


@app.get("/api/investor/brief")
def investor_brief() -> dict[str, Any]:
    """
    Single-endpoint full investor brief:
    - Strategy leaderboard top-10 (Sharpe, CAGR, win-rate, profit-factor)
    - Live paper performance scorecard
    - Sector opportunity gain headline
    - Harmonic edge headline
    - Supervisor health summary
    - Recent execution events (TXIDs, orders)
    - Rolling performance
    """
    scorecard   = load_json(SCORECARD_FILE, {})
    rolling     = load_json(ROLLING_PERF_FILE, {})
    supervisor  = load_supervisor_health({})
    sector      = load_json(SECTOR_FILE, {})
    harmonic    = load_harmonic_edge()
    snapshot_data = build_snapshot()
    snapshot_edge = snapshot_data.get("edge", {}) if isinstance(snapshot_data, dict) else {}
    snapshot_packages = snapshot_data.get("packages", {}) if isinstance(snapshot_data, dict) else {}
    snapshot_evidence = snapshot_data.get("evidence", {}) if isinstance(snapshot_data, dict) else {}
    evidence_derived = snapshot_evidence.get("derived", {}) if isinstance(snapshot_evidence, dict) else {}
    alpha_map_raw: dict[str, Any] = {}
    alpha_map_source = ""
    for cand in (KRAKEN_ALPHA_MAP_FILE, KRAKEN_ALPHA_MAP_FILE_STACK_FALLBACK):
        payload = load_json(cand, None)
        if isinstance(payload, dict) and payload:
            alpha_map_raw = payload
            alpha_map_source = str(cand)
            break
    alpha_leaderboard = alpha_map_raw.get("alpha_leaderboard") if isinstance(alpha_map_raw.get("alpha_leaderboard"), list) else []
    alpha_top = alpha_leaderboard[0] if alpha_leaderboard else {}
    if not isinstance(alpha_top, dict):
        alpha_top = {}

    try:
        alpha_pairs_analyzed = int(float(alpha_map_raw.get("pairs_analyzed", 0) or 0))
    except Exception:
        alpha_pairs_analyzed = 0
    try:
        alpha_pair_errors = int(float(alpha_map_raw.get("pair_errors", 0) or 0))
    except Exception:
        alpha_pair_errors = 0

    alpha_map_summary = {
        "generated_utc": alpha_map_raw.get("generated_utc"),
        "pairs_analyzed": alpha_pairs_analyzed,
        "pair_errors": alpha_pair_errors,
        "source_path": alpha_map_source,
        "controls": alpha_map_raw.get("controls", {}),
        "alpha_leaderboard": alpha_leaderboard[:20],
    }
    try:
        perf = api_perf_session()
    except Exception:
        perf = {}
    perf_24h = perf.get("last_24h", {}) if isinstance(perf, dict) else {}
    perf_24h_realized_net = float(perf_24h.get("realized_pnl_net_usd", 0.0) or 0.0)
    perf_24h_sells = int(perf_24h.get("sells_count", 0) or 0)

    # Leaderboard top 10
    rows = _load_csv_rows(LEADERBOARD_CSV)
    top10: list[dict[str, Any]] = []
    for r in rows[:10]:
        def _f(k: str) -> float:
            try: return round(float(r.get(k, 0) or 0), 4)
            except Exception: return 0.0
        top10.append({
            "flow":           r.get("flow", ""),
            "strategy":       r.get("strategy", ""),
            "algo":           r.get("algo", ""),
            "train_sharpe":   _f("train_sharpe"),
            "test_sharpe":    _f("test_sharpe"),
            "test_sortino":   _f("test_sortino"),
            "test_cagr":      _f("test_cagr"),
            "test_win_rate":  _f("test_win_rate"),
            "profit_factor":  _f("test_profit_factor"),
            "max_drawdown":   _f("test_max_dd"),
            "inst_score":     _f("institutional_score"),
        })

    # Execution proof — last 20 meaningful events
    events = _tail_jsonl_candidates(EXECUTION_EVENT_FILES, 300)
    proof_events = [
        e for e in events
        if e.get("event") in {
            "submit_order", "submit_order_validate_only", "order_filled",
            "approval_ticket_created", "deadman_armed",
        }
    ][-20:]

    # Services health
    svc_up = sum(1 for s in supervisor.get("services", []) if s.get("running"))
    svc_total = len(supervisor.get("services", []))

    return {
        "generated_utc": now_utc(),
        "headline": {
            "equity_usd":       scorecard.get("current_equity_usd", 0.0),
            "equity_text":      fmt_usd(scorecard.get("current_equity_usd", 0.0)),
            "net_pnl_usd":      scorecard.get("net_pnl_usd", 0.0),
            "net_pnl_text":     fmt_usd(scorecard.get("net_pnl_usd", 0.0)),
            "realized_24h_net_usd": perf_24h_realized_net,
            "realized_24h_sells": perf_24h_sells,
            "closed_trades":    int(scorecard.get("closed_trades", 0) or 0),
            "win_rate_pct":     float(scorecard.get("win_rate_pct", 0.0) or 0.0),
            "profit_factor":    float(scorecard.get("profit_factor", 0.0) or 0.0),
            "sharpe":           float(rolling.get("sharpe", 0.0) or 0.0),
            "services_up":      f"{svc_up}/{svc_total}",
            "supervisor_tick":  supervisor.get("tick", 0),
            "infra_top_lane":   sector.get("top_current_optimization_lane", "n/a"),
            "harmonic_top_asset":   harmonic.get("top_asset", "n/a"),
            "harmonic_top_score":   harmonic.get("top_score", 0.0),
            "edge_verdict":     snapshot_edge.get("verdict", "UNKNOWN"),
            "edge_score":       float(snapshot_edge.get("score", 0.0) or 0.0),
            "package_usage_pct": float(snapshot_packages.get("usage_pct", 0.0) or 0.0),
            "evidence_run_utc": snapshot_evidence.get("run_utc", "n/a"),
            "router_win_rate_pct": float(evidence_derived.get("router_win_rate_pct", 0.0) or 0.0),
            "stacker_router_win_rate_pct": float(evidence_derived.get("stacker_router_win_rate_pct", 0.0) or 0.0),
            "regime_break_rate_pct": float(evidence_derived.get("regime_break_rate_pct", 0.0) or 0.0),
            "alpha_pairs_analyzed": alpha_pairs_analyzed,
            "alpha_top_pair": str(alpha_top.get("pair", "") or ""),
            "alpha_top_edge_score": float(alpha_top.get("alpha_edge_score", 0.0) or 0.0),
            "alpha_top_strategy_mode": str(alpha_top.get("strategy_mode", "") or ""),
            "alpha_generated_utc": alpha_map_summary.get("generated_utc"),
        },
        "strategy_leaderboard": top10,
        "execution_proof":      proof_events,
        "rolling_performance":  rolling,
        "harmonic":             harmonic,
        "evidence":             snapshot_evidence,
        "alpha_map":            alpha_map_summary,
        "supervisor": {
            "pid":         supervisor.get("supervisor_pid"),
            "tick":        supervisor.get("tick"),
            "all_healthy": supervisor.get("all_healthy"),
            "services": {
                s["name"]: {"running": s["running"], "pid": s["pid"], "restarts": s["restart_count"]}
                for s in supervisor.get("services", [])
            },
        },
    }


@app.get("/api/investor/leaderboard")
def investor_leaderboard(limit: int = 50) -> dict[str, Any]:
    """Full strategy leaderboard for detailed investor analysis."""
    rows = _load_csv_rows(LEADERBOARD_CSV)
    out: list[dict[str, Any]] = []
    for r in rows[:limit]:
        def _f(k: str) -> float:
            try: return round(float(r.get(k, 0) or 0), 4)
            except Exception: return 0.0
        out.append({
            "flow":          r.get("flow", ""),
            "strategy":      r.get("strategy", ""),
            "algo":          r.get("algo", ""),
            "train_sharpe":  _f("train_sharpe"),
            "test_sharpe":   _f("test_sharpe"),
            "test_sortino":  _f("test_sortino"),
            "test_cagr":     _f("test_cagr"),
            "test_win_rate": _f("test_win_rate"),
            "profit_factor": _f("test_profit_factor"),
            "max_drawdown":  _f("test_max_dd"),
            "stability":     _f("stability"),
            "inst_score":    _f("institutional_score"),
            "is_live_tradable": r.get("is_live_tradable", "False") == "True",
        })
    return {"generated_utc": now_utc(), "count": len(out), "strategies": out}


@app.get("/api/investor/execution-proof")
def execution_proof(limit: int = 100) -> dict[str, Any]:
    """Auditable execution event chain — TXIDs, orders, deadman records."""
    events = _tail_jsonl_candidates(EXECUTION_EVENT_FILES, limit * 6)
    proof = [
        e for e in events
        if e.get("event") in {
            "submit_order", "submit_order_validate_only", "order_filled",
            "approval_ticket_created", "deadman_armed", "verify_env_only",
        }
    ][-limit:]
    txids = [
        e.get("validation_result", {}).get("txid", [])
        for e in proof
        if e.get("validation_result", {}).get("txid")
    ]
    flat_txids = [t for sub in txids for t in (sub if isinstance(sub, list) else [sub])]
    return {
        "generated_utc":  now_utc(),
        "event_count":    len(proof),
        "txid_count":     len(flat_txids),
        "verified_txids": flat_txids,
        "events":         proof,
    }


@app.get("/api/investor/kraken-positive-proof")
def kraken_positive_proof() -> dict[str, Any]:
    """Positive institutional proof pack focused on controls, edge quality, and chain-of-custody integrity."""
    proof = load_json(KRAKEN_POSITIVE_PROOF_FILE, {})
    if not isinstance(proof, dict) or not proof:
        return {
            "generated_utc": now_utc(),
            "status": "missing",
            "message": "kraken_positive_proof.json not found. Run code/build_kraken_positive_proof.py",
        }
    return proof


@app.get("/api/investor/package-leverage")
def investor_package_leverage() -> dict[str, Any]:
    """Package utilization and live leverage probe results for innovation readiness."""
    payload = load_json(PACKAGE_LEVERAGE_FILE, {})
    if not isinstance(payload, dict) or not payload:
        return {
            "generated_utc": now_utc(),
            "status": "missing",
            "message": "package_leverage_audit.json not found. Run code/audit_and_leverage_packages.py",
        }
    return payload


@app.get("/api/investor/sector-heat")
def sector_heat() -> dict[str, Any]:
    """Sector opportunity gain heat map data + recent history ticks."""
    sector  = load_json(SECTOR_FILE, {})
    history = _tail_jsonl(SECTOR_HISTORY_FILE, 120)
    return {
        "generated_utc":         now_utc(),
        "top_lane":              sector.get("top_current_optimization_lane", "n/a"),
        "yearly_value_usd":      sector.get("yearly_translated_value", 0.0),
        "yearly_value_text":     fmt_usd(sector.get("yearly_translated_value", 0.0)),
        "sector_breakdown":      sector.get("sector_breakdown", {}),
        "history_ticks":         history[-60:],
    }


@app.get("/investor")
def investor_dashboard_redirect() -> RedirectResponse:
    return RedirectResponse(url="/investor_command_room.html", status_code=307)


# ── ML Signal + SHAP endpoints ───────────────────────────────────────────────

@app.get("/api/ml/signal")
def ml_signal() -> dict[str, Any]:
    """
    Latest LightGBM+XGBoost ensemble signal over all strategies.
    Returns top-10 ensemble-ranked strategies + model agreement score.
    """
    data = load_json(ML_SIGNAL_FILE, None)
    if data is None:
        return {"status": "not_ready", "hint": "Run luma_ml_signals.py to generate"}
    return data


@app.get("/api/ml/shap")
def ml_shap() -> dict[str, Any]:
    """SHAP feature importances — which strategy features drive institutional score."""
    data = load_json(ML_SHAP_FILE, None)
    if data is None:
        return {"status": "not_ready", "hint": "Run luma_ml_signals.py to generate"}
    return data


@app.get("/api/ml/tearsheet")
def ml_tearsheet() -> dict[str, Any]:
    """Aggregate portfolio tearsheet metrics across all strategies."""
    data = load_json(ML_TEARSHEET_FILE, None)
    if data is None:
        return {"status": "not_ready"}
    return {"generated_utc": now_utc(), **data}


@app.post("/api/ml/trigger")
async def ml_trigger() -> dict[str, Any]:
    """
    Kick off an async ML signal regeneration without blocking the response.
    The new signal will be available at /api/ml/signal within ~5s.
    """
    import asyncio, subprocess, sys
    script = str(CODE / "luma_ml_signals.py") if (CODE / "luma_ml_signals.py").exists() else None
    if script is None:
        return {"status": "error", "detail": "luma_ml_signals.py not found"}
    try:
        subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(CODE),
        )
        return {"status": "triggered", "ts": now_utc()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ── Prometheus raw metrics passthrough (if prometheus_client available) ──────

@app.get("/api/system/metrics-summary")
def metrics_summary() -> dict[str, Any]:
    """JSON summary of key system health metrics for non-Prometheus consumers."""
    supervisor = load_supervisor_health({})
    services   = supervisor.get("services", [])
    up   = sum(1 for s in services if s.get("running"))
    total = len(services)
    restarts = sum(s.get("restart_count", 0) for s in services)
    return {
        "generated_utc":  now_utc(),
        "services_up":    up,
        "services_total": total,
        "total_restarts": restarts,
        "supervisor_tick": supervisor.get("tick", 0),
        "all_healthy":    supervisor.get("all_healthy", False),
        "prometheus_endpoint": "/metrics" if _PROMETHEUS_AVAILABLE else "not_installed",
    }


@app.get("/api/system/adaptive-router")
def adaptive_router_summary() -> dict[str, Any]:
    equity = load_json(ALPACA_STATUS_FILE, {})
    crypto = load_json(CRYPTO_STATUS_FILE, {})
    sports = load_json(SPORTS_ROUTER_FILE, {})
    equity_candidate = equity.get("candidate", {}) if isinstance(equity, dict) else {}
    crypto_regime = crypto.get("regime_controller", {}) if isinstance(crypto, dict) else {}
    return {
        "generated_utc": now_utc(),
        "equity": {
            "signal_family": equity_candidate.get("signal_family", "n/a"),
            "regime_state": equity_candidate.get("regime_state", "n/a"),
            "family_confidence": equity_candidate.get("family_confidence", 0.0),
            "symbol": equity_candidate.get("symbol", ""),
        },
        "crypto": {
            "regime": crypto_regime.get("regime", "n/a"),
            "preferred_family": crypto_regime.get("preferred_family", "n/a"),
            "family_confidence": crypto_regime.get("family_confidence", 0.0),
            "router_votes": crypto_regime.get("router_votes", {}),
        },
        "sports": sports if isinstance(sports, dict) else {},
    }


@app.get("/api/system/overlord-20s")
def system_overlord_20s() -> dict[str, Any]:
    """20-second economics snapshot: live kW, $/hour, downtime loss, and gain potential."""
    payload = load_json(SYSTEM_OVERLORD_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/execution/system_overlord_20s.py --loop",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/system/api-key-registry")
def api_key_registry() -> dict[str, Any]:
    """Non-secret key registry: purpose mapping + presence for route ownership."""
    payload = load_json(API_KEY_REGISTRY_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/execution/api_key_purpose_registry.py",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/system/lane-integrity")
def lane_integrity() -> dict[str, Any]:
    """Lane integrity report to prevent crossed roots between execution/data/audit lanes."""
    payload = load_json(LANE_INTEGRITY_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/execution/lane_integrity_guard.py",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/system/benchmark-beater")
def benchmark_beater() -> dict[str, Any]:
    """Phase-locked flowform champion vs benchmark — live rolling clock + beat %."""
    payload = load_json(BENCHMARK_BEATER_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/execution/benchmark_beater.py --loop",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/system/sector-clock")
def sector_clock() -> dict[str, Any]:
    """All-sector rolling clock — energy, infra, macro vs baseline. LumenCore proof."""
    payload = load_json(SECTOR_CLOCK_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/execution/sector_clock_beater.py --loop",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/funding/approval-queue")
def funding_approval_queue() -> dict[str, Any]:
    """Funding opportunities awaiting approval and submission packaging."""
    queue = load_json(FUNDING_QUEUE_FILE, [])
    if not isinstance(queue, list):
        queue = []
    pending = [q for q in queue if str(q.get("approval_state", "")).upper() == "PENDING_HUMAN_APPROVAL"]
    approved = [q for q in queue if str(q.get("approval_state", "")).upper() == "APPROVED"]
    shipped = [q for q in queue if str(q.get("approval_state", "")).upper() == "SHIPPED"]
    return {
        "generated_utc": now_utc(),
        "queue_count": len(queue),
        "pending_count": len(pending),
        "approved_count": len(approved),
        "shipped_count": len(shipped),
        "items": queue[:80],
    }


@app.get("/api/system/share-links")
def system_share_links() -> dict[str, Any]:
    """Where to view/share the live system while running."""
    tunnel_status = load_json(PUBLIC_DASHBOARD_TUNNEL_STATUS_FILE, {})
    public_url = ""
    if PUBLIC_DASHBOARD_URL_FILE.exists():
        try:
            public_url = PUBLIC_DASHBOARD_URL_FILE.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception:
            public_url = ""
    return {
        "generated_utc": now_utc(),
        "local": {
            "dashboard": "http://127.0.0.1:8787/",
            "investor": "http://127.0.0.1:8787/investor",
            "sector_clock_api": "http://127.0.0.1:8787/api/system/sector-clock",
            "package_leverage_api": "http://127.0.0.1:8787/api/investor/package-leverage",
            "funding_queue_api": "http://127.0.0.1:8787/api/funding/approval-queue",
        },
        "public": {
            "dashboard_url": public_url,
            "tunnel_state": tunnel_status.get("state", "unknown"),
            "tunnel_message": tunnel_status.get("message", ""),
        },
        "sharing_guidance": [
            "Use live URL links for demos; screenshots are only backup evidence.",
            "If public tunnel is down, restart RUN_PUBLIC_DASHBOARD_TUNNEL.ps1 and share new URL.",
            "Do not present stale metrics as live truth.",
        ],
    }


@app.get("/api/system/innovation-autopilot")
def innovation_autopilot_status() -> dict[str, Any]:
    """Self-healing automation status for live freshness and tunnel availability."""
    payload = load_json(INNOVATION_AUTOPILOT_HEARTBEAT_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/execution/innovation_autopilot.py",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/system/beefy-sims")
def beefy_sims_status() -> dict[str, Any]:
    """Broader/beefier multi-core simulation status and summary."""
    payload = load_json(BEEFY_SIMS_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/execution/broader_beefier_sims.py --loop",
            "generated_utc": now_utc(),
        }
    return payload


# ── Unified Trading System endpoints ─────────────────────────────────────────

UNIFIED_ALPHA_SIGNALS_FILE = OUT / "unified_alpha" / "unified_alpha_signals.json"
UNIFIED_ALPHA_HEARTBEAT_FILE = OUT / "unified_alpha" / "unified_alpha_heartbeat.json"
UNIFIED_ALPHA_PERFORMANCE_FILE = OUT / "unified_alpha" / "unified_alpha_performance.json"
UNIFIED_TRADE_STATE_FILE = OUT / "unified_trade" / "unified_trade_state.json"
UNIFIED_TRADE_HEARTBEAT_FILE = OUT / "unified_trade" / "unified_trade_heartbeat.json"
UNIFIED_TRADE_PERFORMANCE_FILE = OUT / "unified_trade" / "unified_trade_performance.json"
UNIFIED_TRADE_LEDGER_FILE = OUT / "unified_trade" / "unified_trade_ledger.jsonl"
SYMBOL_MESH_SUMMARY_FILE = OUT / "symbol_states" / "_fleet_summary.json"
SYMBOL_MESH_ALERTS_FILE = OUT / "symbol_states" / "_real_spike_alerts.json"
SPIKE_ENGINE_HEARTBEAT_FILE = OUT / "spike_trade" / "spike_engine_heartbeat.json"
SPIKE_ENGINE_STATE_FILE    = OUT / "spike_trade" / "spike_engine_state.json"
COHERENCE_LATEST_FILE      = OUT / "coherence" / "fleet_coherence_latest.json"
COHERENCE_HEARTBEAT_FILE   = OUT / "coherence" / "coherence_heartbeat.json"
COHERENCE_HISTORY_FILE     = OUT / "coherence" / "fleet_coherence_history.jsonl"
HARMONIC_LATEST_FILE       = OUT / "harmonic"  / "resonance_latest.json"
HARMONIC_HEARTBEAT_FILE    = OUT / "harmonic"  / "resonance_heartbeat.json"
HARMONIC_HISTORY_FILE      = OUT / "harmonic"  / "resonance_history.jsonl"


@app.get("/api/trading/alpha-signals")
def trading_alpha_signals() -> dict[str, Any]:
    """Current unified alpha signals ranked by Kelly value — arbitrage, momentum, volatility."""
    payload = load_json(UNIFIED_ALPHA_SIGNALS_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/unified_alpha_engine.py to generate signals",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/trading/alpha-performance")
def trading_alpha_performance() -> dict[str, Any]:
    """Alpha signal performance scorecard — moonshots, win rate, expected value."""
    payload = load_json(UNIFIED_ALPHA_PERFORMANCE_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/unified_alpha_engine.py --daemon",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/trading/positions")
def trading_positions() -> dict[str, Any]:
    """Current open positions and historical closed trades."""
    state = load_json(UNIFIED_TRADE_STATE_FILE, {})
    open_positions = state.get("open_positions", [])
    closed_trades = state.get("closed_trades", [])
    
    bankroll = state.get("bankroll", 100000.0)
    open_pnl = sum(p.get("current_pnl", 0) for p in open_positions)
    realized_pnl = sum(t.get("realized_pnl", 0) for t in closed_trades)
    total_pnl = open_pnl + realized_pnl
    
    return {
        "generated_utc": now_utc(),
        "mode": os.environ.get("UNIFIED_EXECUTOR_MODE", "paper"),
        "bankroll": round(bankroll, 2),
        "open_pnl": round(open_pnl, 2),
        "realized_pnl": round(realized_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "open_position_count": len(open_positions),
        "closed_trade_count": len(closed_trades),
        "open_positions": open_positions[:20],  # Latest 20
        "recent_closed": closed_trades[-20:],   # Latest 20
    }


@app.get("/api/trading/performance")
def trading_performance() -> dict[str, Any]:
    """Real-time trading performance metrics — win rate, Sharpe, drawdown, P&L."""
    payload = load_json(UNIFIED_TRADE_PERFORMANCE_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/unified_trade_executor.py --daemon",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/trading/heartbeat")
def trading_heartbeat() -> dict[str, Any]:
    """Executor heartbeat — active, cycle duration, positions opened/closed."""
    payload = load_json(UNIFIED_TRADE_HEARTBEAT_FILE, None)
    if not isinstance(payload, dict):
        return {
            "status": "not_ready",
            "hint": "Run code/unified_trade_executor.py --daemon",
            "generated_utc": now_utc(),
        }
    return payload


@app.get("/api/trading/summary")
def trading_summary() -> dict[str, Any]:
    """Unified trading system summary — everything you need for a live dashboard card."""
    alpha_perf = load_json(UNIFIED_ALPHA_PERFORMANCE_FILE, {})
    trade_perf = load_json(UNIFIED_TRADE_PERFORMANCE_FILE, {})
    trade_hb = load_json(UNIFIED_TRADE_HEARTBEAT_FILE, {})
    state = load_json(UNIFIED_TRADE_STATE_FILE, {})
    
    bankroll = state.get("bankroll", 100000.0)
    
    return {
        "generated_utc": now_utc(),
        "mode": os.environ.get("UNIFIED_EXECUTOR_MODE", "paper"),
        "status": "running" if trade_hb.get("generated_utc") else "not_running",
        "alpha": {
            "signals_generated": alpha_perf.get("total_signals", 0),
            "moonshots": alpha_perf.get("moonshot_count", 0),
            "avg_expected_value_pct": alpha_perf.get("avg_expected_value_pct", 0),
        },
        "execution": {
            "current_bankroll": round(bankroll, 2),
            "total_return_pct": trade_perf.get("total_realized_return_pct", 0.0),
            "open_positions": trade_perf.get("open_positions", 0),
            "total_trades": trade_perf.get("total_trades", 0),
            "win_rate_pct": trade_perf.get("win_rate_pct", 0.0),
            "profit_factor": trade_perf.get("profit_factor", 0.0),
        },
        "heartbeat": {
            "cycle_duration_sec": trade_hb.get("cycle_duration_sec"),
            "last_update_utc": trade_hb.get("generated_utc"),
        }
    }


@app.get("/api/trading/symbol-mesh")
def trading_symbol_mesh() -> dict[str, Any]:
    """Per-symbol watcher fleet health and top signal payload for dashboards/Node-RED/Unity."""
    if not SYMBOL_MESH_SUMMARY_FILE.exists():
        return {
            "status": "not_ready",
            "hint": "Run code/execution/symbol_watcher_fleet.py",
            "generated_utc": now_utc(),
        }

    summary = load_json(SYMBOL_MESH_SUMMARY_FILE, {})
    if not isinstance(summary, dict):
        return {
            "status": "error",
            "hint": "Invalid symbol mesh summary payload",
            "generated_utc": now_utc(),
        }

    age_sec = max(0.0, time.time() - SYMBOL_MESH_SUMMARY_FILE.stat().st_mtime)
    alerts = load_json(SYMBOL_MESH_ALERTS_FILE, []) if SYMBOL_MESH_ALERTS_FILE.exists() else []
    if not isinstance(alerts, list):
        alerts = []

    top_signals = summary.get("top_signals", [])
    if not isinstance(top_signals, list):
        top_signals = []

    return {
        "generated_utc": now_utc(),
        "status": "running" if age_sec <= 30.0 else "stale",
        "freshness_sec": round(age_sec, 2),
        "summary": {
            "updated_utc": summary.get("updated_utc"),
            "total_watched": int(summary.get("total_watched", 0) or 0),
            "symbols_with_data": int(summary.get("symbols_with_data", 0) or 0),
            "active_spikes": int(summary.get("active_spikes", 0) or 0),
            "real_spikes": int(summary.get("real_spikes", 0) or 0),
        },
        "top_signals": top_signals[:25],
        "real_spike_alerts": alerts[:25],
    }


@app.get("/api/trading/spike-engine")
def trading_spike_engine() -> dict[str, Any]:
    """Spike Trade Engine status — real-time P&L, positions opened from live spike detections."""
    hb = load_json(SPIKE_ENGINE_HEARTBEAT_FILE, None)
    state = load_json(SPIKE_ENGINE_STATE_FILE, None)

    if not isinstance(hb, dict):
        return {
            "status": "not_running",
            "hint": "Run: python code/execution/spike_trade_engine.py",
            "generated_utc": now_utc(),
        }

    age_sec = 0.0
    if SPIKE_ENGINE_HEARTBEAT_FILE.exists():
        age_sec = max(0.0, time.time() - SPIKE_ENGINE_HEARTBEAT_FILE.stat().st_mtime)

    open_positions = []
    recent_closed = []
    if isinstance(state, dict):
        open_positions = state.get("open_positions", [])[:10]
        recent_closed  = state.get("recent_closed", [])[-10:]

    return {
        "generated_utc": now_utc(),
        "status": "running" if age_sec <= 15.0 else "stale",
        "freshness_sec": round(age_sec, 2),
        "mode": hb.get("mode", "paper"),
        "bankroll": hb.get("bankroll", 0.0),
        "open_positions": hb.get("open_positions", 0),
        "open_pnl": hb.get("open_pnl", 0.0),
        "total_trades": hb.get("total_trades", 0),
        "wins": hb.get("wins", 0),
        "losses": hb.get("losses", 0),
        "win_rate_pct": hb.get("win_rate_pct", 0.0),
        "total_realized_pnl": hb.get("total_realized_pnl", 0.0),
        "ws_connected": hb.get("ws_connected", False),
        "last_spike_alert_utc": hb.get("last_spike_alert_utc"),
        "positions": open_positions,
        "recent_closed": recent_closed,
    }


@app.get("/api/system/fleet-coherence")
def system_fleet_coherence(history: int = 0) -> dict[str, Any]:
    """
    V8 Perturbation Suite — Live Coherence Snapshot.

    Returns current Ω/C/S/E metrics + all 8 perturbation class verdicts.
    Pass history=N (1–200) to also return the last N historical snapshots.
    """
    hb = load_json(COHERENCE_HEARTBEAT_FILE, None)
    latest = load_json(COHERENCE_LATEST_FILE, None)

    if not isinstance(hb, dict) or not isinstance(latest, dict):
        return {
            "status": "not_running",
            "hint": "Run: python code/execution/fleet_coherence_monitor.py",
            "generated_utc": now_utc(),
        }

    age_sec = 0.0
    if COHERENCE_HEARTBEAT_FILE.exists():
        age_sec = max(0.0, time.time() - COHERENCE_HEARTBEAT_FILE.stat().st_mtime)

    # Optionally include recent history
    hist_records: list[Any] = []
    if history > 0 and COHERENCE_HISTORY_FILE.exists():
        try:
            lines = COHERENCE_HISTORY_FILE.read_text(encoding="utf-8").splitlines()
            for raw in lines[-min(history, 200):]:
                try:
                    hist_records.append(json.loads(raw))
                except Exception:
                    pass
        except Exception:
            pass

    return {
        "generated_utc": now_utc(),
        "status": "running" if age_sec <= 12.0 else "stale",
        "freshness_sec": round(age_sec, 2),
        "scan_count": hb.get("scan_count", 0),
        "grade": hb.get("grade", "?"),
        "pass": latest.get("overall_pass", False),
        "metrics": {
            "omega": latest.get("omega", 0.0),
            "C": latest.get("C", 0.0),
            "S": latest.get("S", 0.0),
            "E": latest.get("E", 0.0),
            "mean_z": latest.get("mean_z", 0.0),
            "freshness_sec": latest.get("freshness_sec", 0.0),
        },
        "fleet": {
            "total_watched": latest.get("total_watched", 0),
            "symbols_with_data": latest.get("symbols_with_data", 0),
            "active_spikes": latest.get("active_spikes", 0),
            "real_spikes": latest.get("real_spikes", 0),
        },
        "perturbations": latest.get("perturbations", []),
        "history": hist_records,
    }


@app.get("/api/system/risk-regime")
def system_risk_regime() -> dict[str, Any]:
    """
    Current V8-derived risk regime controlling the Spike Trade Engine.

    Regime ladder: NORMAL → ELEVATED → GUARDED → CRISIS → LOCKOUT
    Shows effective thresholds, reason, and which P-classes drove the decision.
    """
    REGIME_FILE = OUT / "spike_trade" / "risk_regime.json"
    regime = load_json(REGIME_FILE, None)

    if not isinstance(regime, dict):
        return {
            "status": "not_available",
            "hint": "Spike Trade Engine not running or no V8 coherence data yet",
            "generated_utc": now_utc(),
        }

    age_sec = 0.0
    if REGIME_FILE.exists():
        age_sec = max(0.0, time.time() - REGIME_FILE.stat().st_mtime)

    # Regime colour for dashboard
    REGIME_COLORS = {
        "NORMAL":   "#34d399",
        "ELEVATED": "#fbbf24",
        "GUARDED":  "#f97316",
        "CRISIS":   "#f87171",
        "LOCKOUT":  "#dc2626",
    }
    regime_name = regime.get("regime", "?")

    return {
        "generated_utc": now_utc(),
        "freshness_sec": round(age_sec, 2),
        "regime": regime_name,
        "color": REGIME_COLORS.get(regime_name, "#94a3b8"),
        "allow_new": regime.get("allow_new", True),
        "reason": regime.get("reason", ""),
        "active_p_classes": regime.get("active_p_classes", []),
        "effective": regime.get("effective", {}),
        "v8": regime.get("v8", {}),
        "ts": regime.get("ts"),
    }


@app.get("/api/system/harmonic-resonance")
def system_harmonic_resonance(history: int = 0) -> dict[str, Any]:
    """
    EchoLock™ Harmonic Resonance — live phase-lock detection.

    Grade ladder: NOISE → WEAK → MODERATE → STRONG → LOCK
    confidence_mult ≥ 1.0 (up to 2.0 at full LOCK) fed to Spike Engine position sizing.
    Optional ?history=N returns last N scan rows from resonance_history.jsonl.
    """
    latest = load_json(HARMONIC_LATEST_FILE, None)
    heartbeat = load_json(HARMONIC_HEARTBEAT_FILE, {})

    if not isinstance(latest, dict):
        return {
            "status": "not_available",
            "hint": "Start harmonic_resonance_detector.py to enable EchoLock detection",
            "generated_utc": now_utc(),
        }

    age_sec = 0.0
    if HARMONIC_LATEST_FILE.exists():
        age_sec = max(0.0, time.time() - HARMONIC_LATEST_FILE.stat().st_mtime)

    GRADE_COLORS = {
        "NOISE":    "#64748b",
        "WEAK":     "#94a3b8",
        "MODERATE": "#fbbf24",
        "STRONG":   "#34d399",
        "LOCK":     "#a78bfa",
    }
    grade = latest.get("grade", "NOISE")

    hist_records: list[Any] = []
    if history > 0 and HARMONIC_HISTORY_FILE.exists():
        lines = HARMONIC_HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        for raw in lines[-min(history, 500):]:
            try:
                hist_records.append(json.loads(raw))
            except Exception:
                pass

    return {
        "generated_utc":      now_utc(),
        "freshness_sec":      round(age_sec, 2),
        "grade":              grade,
        "color":              GRADE_COLORS.get(grade, "#64748b"),
        "score":              latest.get("score", 0.0),
        "confidence_mult":    latest.get("confidence_mult", 1.0),
        "dominant_period_sec": latest.get("dominant_period_sec", 0.0),
        "phi_deg":            latest.get("phi_deg", 0.0),
        "cv":                 latest.get("cv", 1.0),
        "harmonic_depth":     latest.get("harmonic_depth", 0),
        "event_window_size":  latest.get("event_window_size", 0),
        "last_spike_age_sec": latest.get("last_spike_age_sec", 9999.0),
        "v8_grade":           latest.get("v8_grade", "?"),
        "v8_omega":           latest.get("v8_omega", 0.0),
        "note":               latest.get("note", ""),
        "ts":                 latest.get("ts"),
        "daemon":             heartbeat,
        "history":            hist_records,
    }


@app.get("/api/live-truth/fabric")
def live_truth_fabric() -> dict[str, Any]:
    data = load_json(LIVE_TRUTH_FILE, None)
    if not isinstance(data, dict):
        return {
            "status": "not_ready",
            "hint": "Start live_truth_fabric_daemon.py to generate fused cross-sector + digital-scout truth",
            "generated_utc": now_utc(),
        }
    return data


@app.get("/api/live-truth/manifest")
def live_truth_manifest() -> dict[str, Any]:
    manifest = load_json(LIVE_TRUTH_MANIFEST_FILE, {})
    heartbeat = load_json(LIVE_TRUTH_HEARTBEAT_FILE, {})
    return {
        "generated_utc": now_utc(),
        "heartbeat": heartbeat,
        "manifest": manifest,
    }


@app.get("/api/live-truth/integration-pack")
def live_truth_integration_pack() -> dict[str, Any]:
    return {
        "generated_utc": now_utc(),
        "node_red": {
            "poll_endpoint": "/api/live-truth/fabric",
            "poll_interval_sec": 5,
            "routing_hint": "Emit cues when lattice_score rises and mode enters targeted_expansion/aggressive_expansion",
        },
        "unity": {
            "poll_endpoint": "/api/live-truth/fabric",
            "routing_hint": "Map geometry.curvature to pulse intensity and geometry.resonance to emission color band",
        },
        "vps": {
            "replicate_paths": [
                "out/live_truth_fabric/live_truth_router.json",
                "out/live_truth_fabric/live_truth_manifest.json",
                "out/execution/live_truth_fabric_heartbeat.json",
            ],
            "serve_hint": "Host as immutable snapshots + API cache for remote consumers",
        },
        "lumen_core_ai": {
            "consume_endpoint": "/api/live-truth/fabric",
            "verification_endpoint": "/api/live-truth/manifest",
            "trust_model": "payload sha256 + source artifact hashes",
        },
    }


# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps({"type": "snapshot", "data": build_snapshot()}))
        while True:
            try:
                msg_text = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except TimeoutError:
                await websocket.send_text(json.dumps({"type": "keepalive", "ts": now_utc()}))
                continue

            if not msg_text.strip() or msg_text.strip().lower() in {"ping", "hello"}:
                continue

            try:
                message = json.loads(msg_text)
            except Exception:
                continue

            msg_type = str(message.get("type", "")).lower()
            if msg_type == "session_event":
                memory = load_session_memory()
                events = list(memory.get("events", []))
                events.append(
                    {
                        "ts": now_utc(),
                        "event": message.get("event", "ws_event"),
                        "source": message.get("source", "ws"),
                        "detail": message.get("detail", {}),
                    }
                )
                if len(events) > 500:
                    events = events[-500:]
                memory["events"] = events
                save_session_memory(memory)
            elif msg_type == "scene_cue":
                await manager.broadcast(
                    _build_scene_cue_packet(
                        scene=message.get("scene", "core"),
                        cue=message.get("cue", "pulse"),
                        intensity=message.get("intensity", 0.5),
                        detail=message.get("detail", {}),
                        source="ws",
                    )
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        return
    except Exception:
        manager.disconnect(websocket)
        return


@app.websocket("/ws")
async def ws_live_legacy(websocket: WebSocket) -> None:
    # Backward-compatible alias for older dashboard clients.
    await ws_live(websocket)


async def broadcaster() -> None:
    while True:
        try:
            payload = {"type": "snapshot", "data": build_snapshot()}
            await manager.broadcast(payload)
        except Exception:
            pass
        await asyncio.sleep(2.0)


async def spike_broadcaster() -> None:
    """
    Background loop: polls _fleet_summary.json every 3s.
    When new real spikes are detected, broadcasts a spike_alert event to all
    WebSocket clients so dashboards, Unity and Node-RED get instant push.
    """
    last_spike_set: set = set()
    while True:
        try:
            if SYMBOL_MESH_SUMMARY_FILE.exists():
                age = time.time() - SYMBOL_MESH_SUMMARY_FILE.stat().st_mtime
                if age <= 30.0:
                    summary = load_json(SYMBOL_MESH_SUMMARY_FILE, {})
                    top = summary.get("top_signals", []) if isinstance(summary, dict) else []
                    real_spikes = [
                        s for s in top
                        if isinstance(s, dict) and bool(s.get("spike_real"))
                    ]
                    current_set = {
                        (str(s.get("symbol", "")), str(s.get("spike_start_ts", "")))
                        for s in real_spikes
                    }
                    new_spikes = [
                        s for s in real_spikes
                        if (str(s.get("symbol", "")), str(s.get("spike_start_ts", ""))) not in last_spike_set
                    ]
                    if new_spikes:
                        await manager.broadcast({
                            "type": "spike_alert",
                            "ts": now_utc(),
                            "count": len(new_spikes),
                            "spikes": [
                                {
                                    "symbol": s.get("symbol"),
                                    "direction": s.get("spike_direction"),
                                    "z_score": round(float(s.get("spike_z_score", 0.0) or 0.0), 3),
                                    "score": round(float(s.get("spike_score", 0.0) or 0.0), 4),
                                    "last_price": s.get("last_price"),
                                    "peak_high": s.get("peak_high"),
                                    "peak_low": s.get("peak_low"),
                                    "spike_start_ts": s.get("spike_start_ts"),
                                }
                                for s in new_spikes
                            ],
                        })
                    last_spike_set = current_set
        except Exception:
            pass
        await asyncio.sleep(3.0)


@app.on_event("startup")
async def start_broadcaster() -> None:
    asyncio.create_task(broadcaster())
    asyncio.create_task(spike_broadcaster())
    asyncio.create_task(_kraken_equity_sampler())
    asyncio.create_task(_profit_lock_watcher())
    asyncio.create_task(_autobuy_watcher())
    asyncio.create_task(_smart_scanner_watcher())


async def _kraken_equity_sampler() -> None:
    """Background loop: snapshot real Kraken USD equity every 60s so the equity
    curve on /live_positions.html grows even when nobody is on the page.
    If `_KRAKEN_SAMPLER_STATE['fast_until_ts']` is in the future, polls every 5s
    instead — used for live demos."""
    _KRAKEN_SAMPLER_STATE["started_utc"] = now_utc()
    await asyncio.sleep(5)
    while True:
        snap_ok = False
        try:
            snap = await asyncio.to_thread(_build_kraken_equity_snapshot)
            snap_ok = bool(snap and snap.get("ok"))
        except Exception:
            pass
        _KRAKEN_SAMPLER_STATE["last_sample_utc"] = now_utc()
        _KRAKEN_SAMPLER_STATE["last_ok"] = snap_ok
        _KRAKEN_SAMPLER_STATE["samples_taken"] = int(_KRAKEN_SAMPLER_STATE.get("samples_taken") or 0) + 1
        sleep_s = 5 if time.time() < float(_KRAKEN_SAMPLER_STATE.get("fast_until_ts") or 0) else int(_KRAKEN_SAMPLER_STATE.get("interval_s") or 60)
        await asyncio.sleep(sleep_s)


@app.get("/api/execution/edge-gate")
def execution_edge_gate() -> dict[str, Any]:
    """
    Smart execution gate: evaluates edge verdict, walk-forward Sharpe, VIX regime,
    and supervisor health to produce a GO / CAUTION / BLOCK decision.
    Consumed by orchestrators before arming live orders.
    """
    edge_report  = load_json(EDGE_TRUTH_FILE, {})
    supervisor   = load_supervisor_health({})
    scorecard    = load_json(SCORECARD_FILE, {})
    macro_file   = ROOT / "out" / "sports_intelligence" / "_dk_alpha_board.json"
    macro        = {}
    try:
        raw = macro_file.read_text(encoding="utf-8").replace(": NaN", ": null")
        macro = json.loads(raw).get("macro", {})
    except Exception:
        pass

    edge_verdict = edge_report.get("edge_verdict")
    if edge_verdict is None:
        edge_verdict = edge_report.get("verdict")
    verdict = str(edge_verdict or "UNKNOWN").upper()

    score = float(edge_report.get("edge_quality_score") or scorecard.get("edge_quality_score") or 0.0)

    wf_sharpe_source = "none"
    wf_sharpe_raw: Any = edge_report.get("walk_forward_sharpe")
    if wf_sharpe_raw is not None:
        wf_sharpe_source = "edge_report.walk_forward_sharpe"
    if wf_sharpe_raw is None and isinstance(edge_report.get("champion"), dict):
        candidate = edge_report.get("champion", {}).get("test_sharpe")
        if candidate is not None:
            wf_sharpe_raw = candidate
            wf_sharpe_source = "edge_report.champion.test_sharpe"
    if wf_sharpe_raw is None:
        closed_trades = int(_safe_num(scorecard.get("closed_trades", 0), 0))
        candidate = scorecard.get("sharpe")
        if candidate is not None and closed_trades > 0:
            wf_sharpe_raw = candidate
            wf_sharpe_source = "scorecard.sharpe"

    has_wf_sharpe = wf_sharpe_raw is not None
    wf_sharpe = float(_safe_num(wf_sharpe_raw, 0.0))
    all_healthy  = bool(supervisor.get("all_healthy", False))
    vix          = float(macro.get("vix", 0.0) or 0.0)
    regime       = str(macro.get("regime", "unknown")).lower()

    # ── Gate rules ─────────────────────────────────────────────────────────
    blocks  : list[str] = []
    cautions: list[str] = []

    if verdict == "FAIL":
        blocks.append(f"Edge verdict is FAIL (score={score:.1f})")
    if has_wf_sharpe:
        if wf_sharpe < 0.5:
            blocks.append(f"Walk-forward Sharpe too low ({wf_sharpe:.2f} < 0.5)")
    else:
        cautions.append("Walk-forward Sharpe unavailable")
    if not all_healthy:
        cautions.append("Not all supervisor services healthy")
    if vix > 35:
        blocks.append(f"VIX elevated: {vix:.1f} > 35")
    elif vix > 25:
        cautions.append(f"VIX elevated: {vix:.1f} > 25")
    if regime in ("crisis", "stress"):
        blocks.append(f"Macro regime is {regime}")
    elif regime in ("high_vol",):
        cautions.append(f"Macro regime is {regime}")

    if blocks:
        gate = "BLOCK"
    elif cautions:
        gate = "CAUTION"
    else:
        gate = "GO"

    return {
        "generated_utc":    now_utc(),
        "gate":             gate,
        "edge_verdict":     verdict,
        "edge_score":       round(score, 2),
        "walk_forward_sharpe": round(wf_sharpe, 3),
        "walk_forward_sharpe_source": wf_sharpe_source,
        "vix":              vix,
        "regime":           regime,
        "supervisor_healthy": all_healthy,
        "blocks":           blocks,
        "cautions":         cautions,
        "summary":          f"{gate}: {'; '.join(blocks + cautions) or 'All systems nominal'}",
    }


@app.get("/api/investor/readiness")
def investor_readiness() -> dict[str, Any]:
    """Investor-facing readiness summary with explicit blockers and cautions."""
    gate = execution_edge_gate()
    control_flags = load_json(CONTROL_FLAGS_FILE, {})
    execution_status = load_json(EXECUTION_STATUS_FILE, {})
    package_leverage = load_json(PACKAGE_LEVERAGE_FILE, {})

    blockers: list[str] = list(gate.get("blocks", []) or [])
    cautions: list[str] = list(gate.get("cautions", []) or [])

    mode = str(execution_status.get("execution_mode", "unknown")).lower()
    live_arm = str(execution_status.get("live_arm", "unknown")).upper()
    kill_switch = bool(control_flags.get("kill_switch", False))
    live_enabled = bool(control_flags.get("live_enabled", False))
    note = str(execution_status.get("note", "")).lower()

    if mode in {"paper", "sim", "simulation"}:
        blockers.append(f"Execution mode is {mode}")
    if live_arm in {"OFF", "FALSE", "0", "NO"}:
        blockers.append("Live arm is OFF")
    if kill_switch:
        blockers.append("Kill switch is active")
    if not live_enabled:
        blockers.append("control_flags.live_enabled is false")
    if "no autonomous live order" in note:
        blockers.append("Execution status note indicates autonomous live orders are disabled")

    used = int(package_leverage.get("used_package_count", 0) or 0) if isinstance(package_leverage, dict) else 0
    installed = int(package_leverage.get("installed_package_count", 0) or 0) if isinstance(package_leverage, dict) else 0
    util_pct = round((used / installed * 100.0), 2) if installed > 0 else 0.0
    if installed == 0:
        cautions.append("Package leverage audit missing or empty")
    elif util_pct < 10.0:
        cautions.append(f"Package utilization is low ({util_pct:.2f}%)")

    blockers = sorted(set(blockers))
    cautions = sorted(set(cautions))
    readiness = "ready" if not blockers else "blocked"

    return {
        "generated_utc": now_utc(),
        "readiness": readiness,
        "gate": gate.get("gate", "UNKNOWN"),
        "blocker_count": len(blockers),
        "caution_count": len(cautions),
        "blockers": blockers,
        "cautions": cautions,
        "execution": {
            "mode": mode,
            "live_arm": live_arm,
            "live_enabled": live_enabled,
            "kill_switch": kill_switch,
        },
        "package_utilization_pct": util_pct,
        "summary": (
            "READY: no blockers detected" if not blockers else
            f"BLOCKED: {len(blockers)} blocker(s), {len(cautions)} caution(s)"
        ),
    }


@app.get("/api/master/snapshot-v3")
def master_snapshot_v3() -> dict[str, Any]:
    """
    Unified master payload for premium dashboards.

    This endpoint intentionally aggregates legacy + new engine feeds so the
    UI can load from one source and still drill down to raw endpoints when needed.
    """
    top = build_snapshot()
    brief = investor_brief()
    pkg = investor_package_leverage()
    sector = sector_heat()
    spike = trading_spike_engine()
    mesh = trading_symbol_mesh()
    v8 = system_fleet_coherence(history=24)
    regime = system_risk_regime()
    harmonic = system_harmonic_resonance(history=24)
    readiness = investor_readiness()
    proof = execution_proof(limit=80)
    harmonic_proofpack = harmonic_proofpack_latest()
    metrics = metrics_summary()
    benchmark = benchmark_beater()
    clock = sector_clock()
    alpha = trading_alpha_signals()
    performance = trading_performance()
    evidence = load_latest_dashboard_evidence()
    evidence_derived = evidence.get("derived", {}) if isinstance(evidence, dict) else {}
    booth = master_booth_brief()

    strategies = []
    if isinstance(brief, dict):
        strategies = list(brief.get("strategy_leaderboard", []) or [])
    if not strategies:
        fallback = investor_leaderboard(limit=25)
        strategies = list(fallback.get("strategies", []) or []) if isinstance(fallback, dict) else []

    pkg_used = 0
    pkg_installed = 0
    if isinstance(pkg, dict):
        pkg_used = int(pkg.get("used_package_count", 0) or 0)
        pkg_installed = int(pkg.get("installed_package_count", 0) or 0)
    pkg_ratio = round((pkg_used / pkg_installed * 100.0), 2) if pkg_installed > 0 else 0.0

    return {
        "generated_utc": now_utc(),
        "schema": "luma_master_snapshot_v3",
        "topline": top,
        "brief": brief,
        "booth_brief": booth,
        "evidence": evidence,
        "package_leverage": pkg,
        "sector_heat": sector,
        "trading": {
            "spike_engine": spike,
            "symbol_mesh": mesh,
            "alpha_signals": alpha,
            "performance": performance,
        },
        "system": {
            "fleet_coherence": v8,
            "risk_regime": regime,
            "harmonic_resonance": harmonic,
            "metrics_summary": metrics,
            "benchmark_beater": benchmark,
            "sector_clock": clock,
        },
        "investor": {
            "readiness": readiness,
            "execution_proof": proof,
            "leaderboard": {
                "count": len(strategies),
                "strategies": strategies,
            },
        },
        "proofpacks": {
            "harmonic_backprop": harmonic_proofpack,
        },
        "derived": {
            "package_usage_pct": pkg_ratio,
            "txid_count": int(proof.get("txid_count", 0) or 0) if isinstance(proof, dict) else 0,
            "watch_symbols": int((mesh.get("summary", {}) or {}).get("total_watched", 0) or 0) if isinstance(mesh, dict) else 0,
            "coherence_grade": str((v8 or {}).get("grade", "?")),
            "regime": str((regime or {}).get("regime", "?")),
            "harmonic_grade": str((harmonic or {}).get("grade", "NOISE")),
            "harmonic_proofpack_status": str((harmonic_proofpack or {}).get("status", "unknown")),
            "harmonic_proofpack_winner": str(((harmonic_proofpack or {}).get("winner", {}) or {}).get("model", "")),
            "harmonic_proofpack_rmse": float((((harmonic_proofpack or {}).get("winner", {}) or {}).get("rmse", 0.0) or 0.0)),
            "evidence_run_utc": str((evidence or {}).get("run_utc", "")),
            "router_win_rate_pct": float(evidence_derived.get("router_win_rate_pct", 0.0) or 0.0),
            "stacker_router_win_rate_pct": float(evidence_derived.get("stacker_router_win_rate_pct", 0.0) or 0.0),
            "regime_break_rate_pct": float(evidence_derived.get("regime_break_rate_pct", 0.0) or 0.0),
        },
        "raw_endpoints": {
            "brief": "/api/investor/brief",
            "booth_brief": "/api/master/booth-brief",
            "evidence_latest": "/api/evidence/latest",
            "package_leverage": "/api/investor/package-leverage",
            "sector_heat": "/api/investor/sector-heat",
            "spike_engine": "/api/trading/spike-engine",
            "symbol_mesh": "/api/trading/symbol-mesh",
            "fleet_coherence": "/api/system/fleet-coherence",
            "risk_regime": "/api/system/risk-regime",
            "harmonic_resonance": "/api/system/harmonic-resonance",
            "readiness": "/api/investor/readiness",
            "execution_proof": "/api/investor/execution-proof",
            "harmonic_proofpack_latest": "/api/proofpack/harmonic/latest",
            "ops_staleness": "/api/ops/staleness",
            "ops_lumaq": "/api/ops/lumaq",
            "ops_lumaq_top10": "/api/ops/lumaq/top10",
        },
    }


@app.get("/api/master/engine-catalog")
def master_engine_catalog(limit: int = 500) -> dict[str, Any]:
    """Catalog engine/orchestrator/executor modules across legacy and modular lanes."""
    roots = [CODE, CODE / "execution"]
    keywords = (
        "engine",
        "orchestrator",
        "executor",
        "builder",
        "strategy",
        "algo",
        "router",
        "monitor",
    )

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        try:
            for py in root.rglob("*.py"):
                rel = py.relative_to(ROOT).as_posix()
                if rel in seen:
                    continue
                seen.add(rel)
                rel_lower = rel.lower()
                if "/.venv/" in rel_lower or "/site-packages/" in rel_lower or rel_lower.startswith("code/.venv/"):
                    continue
                name = py.name.lower()
                if not any(k in name for k in keywords):
                    continue
                try:
                    stat = py.stat()
                    size = int(stat.st_size)
                    mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
                    line_count = 0
                    try:
                        with py.open("r", encoding="utf-8", errors="ignore") as fh:
                            for _ in fh:
                                line_count += 1
                    except Exception:
                        line_count = 0
                    rows.append(
                        {
                            "path": rel,
                            "name": py.name,
                            "size_bytes": size,
                            "line_count": line_count,
                            "mtime_utc": mtime,
                            "lane": "execution" if "execution/" in rel else "core",
                        }
                    )
                except Exception:
                    continue
        except Exception:
            continue

    rows.sort(key=lambda x: x.get("line_count", 0), reverse=True)
    trimmed = rows[: max(1, min(limit, 2000))]
    return {
        "generated_utc": now_utc(),
        "schema": "luma_engine_catalog_v1",
        "count": len(trimmed),
        "total_scanned": len(rows),
        "largest_modules": trimmed[:25],
        "modules": trimmed,
    }


@app.get("/api/master/engine-adapters")
def master_engine_adapters(limit: int = 180) -> dict[str, Any]:
    """Live adapter matrix for legacy/new engines based on heartbeat/status artifacts."""

    watch_files: list[tuple[str, Path, float]] = [
        ("spike_engine", SPIKE_ENGINE_HEARTBEAT_FILE, 20.0),
        ("fleet_coherence", COHERENCE_HEARTBEAT_FILE, 20.0),
        ("harmonic_resonance", HARMONIC_HEARTBEAT_FILE, 20.0),
        ("symbol_mesh", SYMBOL_MESH_SUMMARY_FILE, 35.0),
        ("unified_alpha", UNIFIED_ALPHA_HEARTBEAT_FILE, 45.0),
        ("unified_trade", UNIFIED_TRADE_HEARTBEAT_FILE, 45.0),
        ("innovation_autopilot", INNOVATION_AUTOPILOT_HEARTBEAT_FILE, 120.0),
        ("system_overlord", SYSTEM_OVERLORD_FILE, 120.0),
        ("benchmark_beater", BENCHMARK_BEATER_FILE, 120.0),
        ("sector_clock", SECTOR_CLOCK_FILE, 120.0),
        ("supervisor_health", SUPERVISOR_HEALTH_FILE, 120.0),
        ("metrics_scorecard", METRICS_SCORECARD_FILE, 300.0),
        ("edge_truth", EDGE_TRUTH_FILE, 300.0),
        ("lane_integrity", LANE_INTEGRITY_FILE, 300.0),
        ("api_key_registry", API_KEY_REGISTRY_FILE, 300.0),
    ]

    adapter_rows: list[dict[str, Any]] = []
    for name, path, stale_after in watch_files:
        exists = path.exists()
        freshness_sec = None
        updated_utc = None
        payload_status = "unknown"
        if exists:
            try:
                stat = path.stat()
                freshness_sec = max(0.0, time.time() - stat.st_mtime)
                updated_utc = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
            except Exception:
                freshness_sec = None

            payload = load_json(path, {})
            if isinstance(payload, dict):
                payload_status = str(payload.get("status", payload.get("grade", "running")))

        if not exists:
            adapter_state = "missing"
        elif freshness_sec is None:
            adapter_state = "unknown"
        elif freshness_sec <= stale_after:
            adapter_state = "fresh"
        elif freshness_sec <= stale_after * 4:
            adapter_state = "stale"
        else:
            adapter_state = "cold"

        # Higher score = higher upgrade/repair urgency
        if adapter_state == "missing":
            priority_score = 100.0
        elif adapter_state == "cold":
            priority_score = 80.0
        elif adapter_state == "stale":
            priority_score = 55.0
        elif adapter_state == "unknown":
            priority_score = 45.0
        else:
            priority_score = 15.0

        adapter_rows.append(
            {
                "engine": name,
                "path": path.relative_to(ROOT).as_posix() if str(path).startswith(str(ROOT)) else str(path),
                "exists": exists,
                "state": adapter_state,
                "payload_status": payload_status,
                "freshness_sec": round(float(freshness_sec), 2) if freshness_sec is not None else None,
                "updated_utc": updated_utc,
                "stale_after_sec": stale_after,
                "priority_score": round(priority_score, 2),
            }
        )

    # Also discover additional heartbeat files for innovation visibility.
    extra_rows: list[dict[str, Any]] = []
    try:
        for hb in OUT.rglob("*heartbeat*.json"):
            rel = hb.relative_to(ROOT).as_posix()
            if any(r.get("path") == rel for r in adapter_rows):
                continue
            age = max(0.0, time.time() - hb.stat().st_mtime)
            state = "fresh" if age <= 90.0 else "stale"
            extra_rows.append(
                {
                    "engine": hb.stem,
                    "path": rel,
                    "exists": True,
                    "state": state,
                    "payload_status": "discovered",
                    "freshness_sec": round(age, 2),
                    "updated_utc": datetime.fromtimestamp(hb.stat().st_mtime, timezone.utc).isoformat(),
                    "stale_after_sec": 90.0,
                    "priority_score": 35.0 if state == "fresh" else 65.0,
                }
            )
    except Exception:
        pass

    merged = adapter_rows + extra_rows
    merged.sort(key=lambda x: float(x.get("priority_score", 0.0)), reverse=True)
    merged = merged[: max(1, min(limit, 1000))]

    counts = {
        "fresh": sum(1 for r in merged if r.get("state") == "fresh"),
        "stale": sum(1 for r in merged if r.get("state") == "stale"),
        "cold": sum(1 for r in merged if r.get("state") == "cold"),
        "missing": sum(1 for r in merged if r.get("state") == "missing"),
        "unknown": sum(1 for r in merged if r.get("state") == "unknown"),
    }

    return {
        "generated_utc": now_utc(),
        "schema": "luma_engine_adapters_v1",
        "count": len(merged),
        "state_counts": counts,
        "top_priority": merged[:15],
        "adapters": merged,
    }


@app.get("/api/master/remediation-playbook")
def master_remediation_playbook(limit: int = 20) -> dict[str, Any]:
    """Actionable remediation queue derived from engine adapter health."""
    adapters_payload = master_engine_adapters(limit=300)
    adapters = adapters_payload.get("adapters", []) if isinstance(adapters_payload, dict) else []
    if not isinstance(adapters, list):
        adapters = []

    action_map = _remediation_action_map()

    queue: list[dict[str, Any]] = []
    for row in adapters:
        if not isinstance(row, dict):
            continue
        state = str(row.get("state", "unknown"))
        if state == "fresh":
            continue
        engine = str(row.get("engine", "unknown"))
        severity = "P0" if state in {"missing", "cold"} else ("P1" if state == "stale" else "P2")
        action = action_map.get(engine, {})
        argv = action.get("argv", []) if isinstance(action, dict) else []
        command = " ".join(str(x) for x in argv) if argv else "Review engine owner and restart command for this module"
        queue.append(
            {
                "engine": engine,
                "state": state,
                "priority": severity,
                "priority_score": float(row.get("priority_score", 0.0) or 0.0),
                "path": row.get("path"),
                "freshness_sec": row.get("freshness_sec"),
                "payload_status": row.get("payload_status"),
                "recommended_command": command,
                "trigger_endpoint": "/api/master/remediation/trigger",
                "reason": f"Engine state={state}, payload_status={row.get('payload_status', 'unknown')}",
            }
        )

    queue.sort(key=lambda x: (x.get("priority", "P9"), -float(x.get("priority_score", 0.0) or 0.0)))
    queue = queue[: max(1, min(limit, 100))]

    return {
        "generated_utc": now_utc(),
        "schema": "luma_remediation_playbook_v1",
        "count": len(queue),
        "items": queue,
    }


@app.get("/api/master/dependency-graph")
def master_dependency_graph() -> dict[str, Any]:
    """Cross-engine dependency graph with live status coloring hints."""
    adapters_payload = master_engine_adapters(limit=300)
    adapters = adapters_payload.get("adapters", []) if isinstance(adapters_payload, dict) else []
    status_map: dict[str, str] = {}
    if isinstance(adapters, list):
        for row in adapters:
            if isinstance(row, dict):
                status_map[str(row.get("engine", ""))] = str(row.get("state", "unknown"))

    node_list = [
        "gateway",
        "supervisor_health",
        "symbol_mesh",
        "fleet_coherence",
        "harmonic_resonance",
        "spike_engine",
        "unified_alpha",
        "unified_trade",
        "benchmark_beater",
        "sector_clock",
        "investor_readiness",
    ]

    edges = [
        {"from": "symbol_mesh", "to": "fleet_coherence", "kind": "signal_feed"},
        {"from": "fleet_coherence", "to": "harmonic_resonance", "kind": "stability_gate"},
        {"from": "fleet_coherence", "to": "spike_engine", "kind": "risk_gate"},
        {"from": "harmonic_resonance", "to": "spike_engine", "kind": "size_multiplier"},
        {"from": "unified_alpha", "to": "unified_trade", "kind": "alpha_execution"},
        {"from": "spike_engine", "to": "investor_readiness", "kind": "execution_proof"},
        {"from": "benchmark_beater", "to": "investor_readiness", "kind": "performance_signal"},
        {"from": "sector_clock", "to": "investor_readiness", "kind": "sector_signal"},
        {"from": "supervisor_health", "to": "gateway", "kind": "orchestration_health"},
        {"from": "gateway", "to": "investor_readiness", "kind": "aggregation"},
    ]

    nodes = [
        {
            "id": name,
            "status": status_map.get(name, "derived" if name in {"gateway", "investor_readiness"} else "unknown"),
        }
        for name in node_list
    ]

    return {
        "generated_utc": now_utc(),
        "schema": "luma_dependency_graph_v1",
        "nodes": nodes,
        "edges": edges,
    }


@app.get("/api/master/dependency-impact")
def master_dependency_impact() -> dict[str, Any]:
    """Rank engines by downstream dependency impact and current health state."""
    graph = master_dependency_graph()
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    edges = graph.get("edges", []) if isinstance(graph, dict) else []

    in_deg: dict[str, int] = {}
    out_deg: dict[str, int] = {}
    state_map: dict[str, str] = {}
    for n in nodes if isinstance(nodes, list) else []:
        if not isinstance(n, dict):
            continue
        node_id = str(n.get("id", ""))
        state_map[node_id] = str(n.get("status", "unknown"))
        in_deg.setdefault(node_id, 0)
        out_deg.setdefault(node_id, 0)

    for e in edges if isinstance(edges, list) else []:
        if not isinstance(e, dict):
            continue
        src = str(e.get("from", ""))
        dst = str(e.get("to", ""))
        out_deg[src] = out_deg.get(src, 0) + 1
        in_deg[dst] = in_deg.get(dst, 0) + 1

    impact_rows: list[dict[str, Any]] = []
    for node_id in set(list(in_deg.keys()) + list(out_deg.keys())):
        state = state_map.get(node_id, "unknown")
        risk_mult = 1.0
        if state in {"missing", "cold", "fail", "blocked"}:
            risk_mult = 2.0
        elif state in {"stale", "warn"}:
            risk_mult = 1.4
        elif state in {"fresh", "pass", "ready"}:
            risk_mult = 0.8
        score = (out_deg.get(node_id, 0) * 3.0 + in_deg.get(node_id, 0) * 1.2) * risk_mult
        impact_rows.append(
            {
                "node": node_id,
                "state": state,
                "in_degree": in_deg.get(node_id, 0),
                "out_degree": out_deg.get(node_id, 0),
                "impact_score": round(score, 3),
            }
        )

    impact_rows.sort(key=lambda x: float(x.get("impact_score", 0.0)), reverse=True)
    return {
        "generated_utc": now_utc(),
        "schema": "luma_dependency_impact_v1",
        "count": len(impact_rows),
        "top_critical": impact_rows[:20],
        "nodes": impact_rows,
    }


@app.post("/api/master/remediation/trigger")
def master_remediation_trigger(req: RemediationTriggerRequest) -> dict[str, Any]:
    """Guarded remediation runner. Defaults to preview unless execute=true is provided."""
    engine = str(req.engine or "").strip()
    actions = _remediation_action_map()
    action = actions.get(engine)
    log_file = EXEC_OUT / "remediation_actions.jsonl"

    if action is None:
        payload = {
            "generated_utc": now_utc(),
            "status": "rejected",
            "reason": f"Engine '{engine}' is not in allowlist",
            "allowed": sorted(actions.keys()),
        }
        _append_jsonl(
            log_file,
            {
                "ts": payload["generated_utc"],
                "event": "remediation_rejected",
                "engine": engine,
                "reason": payload["reason"],
            },
        )
        return payload

    argv = [str(x) for x in action.get("argv", [])]
    cooldown = int(action.get("cooldown_sec", 120) or 120)
    lock_dir = ROOT / "run" / "remediation"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_file = lock_dir / f"{engine}.json"

    now_ts = time.time()
    lock = load_json(lock_file, {})
    prev_pid = int(lock.get("pid", 0) or 0) if isinstance(lock, dict) else 0
    prev_ts = float(lock.get("ts", 0.0) or 0.0) if isinstance(lock, dict) else 0.0
    age = max(0.0, now_ts - prev_ts)

    if _pid_alive(prev_pid) and not req.force:
        payload = {
            "generated_utc": now_utc(),
            "status": "already_running",
            "engine": engine,
            "pid": prev_pid,
            "age_sec": round(age, 2),
            "command": " ".join(argv),
        }
        _append_jsonl(
            log_file,
            {
                "ts": payload["generated_utc"],
                "event": "remediation_already_running",
                "engine": engine,
                "pid": prev_pid,
                "age_sec": payload["age_sec"],
                "command": argv,
            },
        )
        return payload

    if age < cooldown and not req.force:
        payload = {
            "generated_utc": now_utc(),
            "status": "cooldown",
            "engine": engine,
            "cooldown_sec": cooldown,
            "remaining_sec": round(max(cooldown - age, 0.0), 2),
            "command": " ".join(argv),
        }
        _append_jsonl(
            log_file,
            {
                "ts": payload["generated_utc"],
                "event": "remediation_cooldown",
                "engine": engine,
                "remaining_sec": payload["remaining_sec"],
                "command": argv,
            },
        )
        return payload

    if not req.execute:
        payload = {
            "generated_utc": now_utc(),
            "status": "preview",
            "engine": engine,
            "command": " ".join(argv),
            "cooldown_sec": cooldown,
        }
        _append_jsonl(
            log_file,
            {
                "ts": payload["generated_utc"],
                "event": "remediation_preview",
                "engine": engine,
                "command": argv,
                "cooldown_sec": cooldown,
            },
        )
        return payload

    try:
        proc = subprocess.Popen(
            argv,
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        lock_payload = {
            "engine": engine,
            "pid": int(proc.pid),
            "ts": now_ts,
            "command": argv,
        }
        lock_file.write_text(json.dumps(lock_payload, indent=2), encoding="utf-8")
        _append_jsonl(
            log_file,
            {
                "ts": now_utc(),
                "event": "remediation_triggered",
                "engine": engine,
                "pid": int(proc.pid),
                "command": argv,
                "force": bool(req.force),
            },
        )
        return {
            "generated_utc": now_utc(),
            "status": "started",
            "engine": engine,
            "pid": int(proc.pid),
            "command": " ".join(argv),
        }
    except Exception as exc:
        _append_jsonl(
            log_file,
            {
                "ts": now_utc(),
                "event": "remediation_error",
                "engine": engine,
                "error": str(exc),
            },
        )
        return {
            "generated_utc": now_utc(),
            "status": "error",
            "engine": engine,
            "error": str(exc),
            "command": " ".join(argv),
        }


@app.get("/api/master/remediation/history")
def master_remediation_history(limit: int = 120) -> dict[str, Any]:
    """Recent remediation trigger audit events."""
    log_file = EXEC_OUT / "remediation_actions.jsonl"
    rows = _tail_jsonl(log_file, max(1, min(limit, 1000)))
    return {
        "generated_utc": now_utc(),
        "schema": "luma_remediation_history_v1",
        "count": len(rows),
        "events": rows,
    }


# ──────────────────────────────────────────────────────────────────────────
# APPROVAL QUEUE  — Human-in-the-loop live order gating
# Reads execution_approval_queue.json (PENDING_HUMAN_APPROVAL tickets),
# evaluates ALL guard rails server-side on every request,
# and only fires Kraken /0/private/AddOrder after approve + guards pass.
# ──────────────────────────────────────────────────────────────────────────

import hmac as _hmac_appr
import hashlib as _hashlib_appr
import base64 as _base64_appr
from urllib.parse import urlencode as _urlencode_appr
import requests as _requests_appr

APPROVAL_QUEUE_FILE = ROOT / "execution_approval_queue.json"
APPROVAL_QUEUE_FILE_OUT = OUT / "execution_approval_queue.json"
APPROVAL_AUDIT_FILE = EXEC_OUT / "approval_decisions.jsonl"
LIVE_KEYS_FILE = ROOT / "config" / "luma_live_keys.env"
APPROVAL_TICKET_TTL_HOURS = 24.0
APPROVAL_MIN_OPEN_POSITIONS_FLOOR = 10


def _load_control_flags() -> dict[str, Any]:
    return load_json(CONTROL_FLAGS_FILE, {}) or {}


def _load_approval_queue() -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for queue_file in (APPROVAL_QUEUE_FILE, APPROVAL_QUEUE_FILE_OUT):
        data = load_json(queue_file, [])
        if not isinstance(data, list):
            continue
        for idx, row in enumerate(data):
            if not isinstance(row, dict):
                continue
            ticket_id = str(row.get("ticket_id", "")).strip()
            if not ticket_id:
                ticket_id = f"__anon__::{queue_file.name}::{idx}::{row.get('timestamp', '')}"
            merged[ticket_id] = row
    rows = list(merged.values())
    rows.sort(key=lambda row: str(row.get("timestamp", "")), reverse=True)
    return rows


def _save_approval_queue(rows: list[dict[str, Any]]) -> None:
    payload = json.dumps(rows, indent=2)
    for queue_file in (APPROVAL_QUEUE_FILE, APPROVAL_QUEUE_FILE_OUT):
        queue_file.parent.mkdir(parents=True, exist_ok=True)
        queue_file.write_text(payload, encoding="utf-8")


def _load_kraken_keys() -> tuple[str, str]:
    if not LIVE_KEYS_FILE.exists():
        return "", ""
    key = ""
    secret = ""
    for line in LIVE_KEYS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip(); v = v.strip()
        if k in ("KRAKEN_API_KEY", "LUMA_KRAKEN_API_KEY"):
            key = v
        elif k in ("KRAKEN_API_SECRET", "LUMA_KRAKEN_API_SECRET"):
            secret = v
    return key, secret


def _ticket_age_hours(ticket: dict[str, Any]) -> float:
    ts = ticket.get("timestamp")
    if not ts:
        return float("inf")
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    except Exception:
        return float("inf")


def _count_open_positions(queue: list[dict[str, Any]]) -> int:
    # Count tickets we've executed-and-not-closed in this queue file.
    return sum(1 for t in queue if str(t.get("approval_state", "")).upper() == "EXECUTED_OPEN")


def _evaluate_guards(
    ticket: dict[str, Any],
    flags: dict[str, Any],
    open_positions: int,
) -> dict[str, Any]:
    """Pure server-side guard evaluation. Returns {guards: [...], pass_all: bool}."""
    guards: list[dict[str, Any]] = []

    def add(name: str, ok: bool, detail: str) -> None:
        guards.append({"name": name, "pass": bool(ok), "detail": detail})

    kill = bool(flags.get("kill_switch", True))
    add("kill_switch_off", not kill, "kill_switch=ON" if kill else "kill_switch=OFF")

    live_enabled = bool(flags.get("live_enabled", False))
    add("live_enabled", live_enabled, "live_enabled=" + str(live_enabled))

    controller = str(ticket.get("controller", "")).strip()
    allowed = list(flags.get("allowed_controllers", []) or [])
    add(
        "controller_allowlisted",
        bool(controller) and controller in allowed,
        f"controller='{controller}' allowed={allowed}",
    )

    notional = float(ticket.get("notional_usd", 0.0) or 0.0)
    cap = float(flags.get("max_notional_per_trade_usd", 0.0) or 0.0)
    add(
        "notional_under_cap",
        notional > 0 and (cap <= 0 or notional <= cap),
        f"notional={notional} cap={cap}",
    )

    try:
        raw_max_open = int(float(flags.get("max_open_positions", 0) or 0))
    except Exception:
        raw_max_open = 0
    max_open = 0 if raw_max_open <= 0 else max(raw_max_open, APPROVAL_MIN_OPEN_POSITIONS_FLOOR)
    ticket_side = str(ticket.get("side", "")).strip().lower()
    max_open_ok = (max_open <= 0 or open_positions < max_open) if ticket_side == "buy" else True
    add(
        "open_positions_under_max",
        max_open_ok,
        f"open={open_positions} max={max_open} side={ticket_side or 'unknown'}",
    )

    age_h = _ticket_age_hours(ticket)
    add(
        "ticket_fresh",
        age_h < APPROVAL_TICKET_TTL_HOURS,
        f"age_hours={age_h:.2f} ttl={APPROVAL_TICKET_TTL_HOURS}",
    )

    payload = ticket.get("payload") or {}
    pair = str(payload.get("pair", "")).strip()
    side = str(payload.get("type", "")).strip().lower()
    volume = str(payload.get("volume", "")).strip()
    add(
        "payload_complete",
        bool(pair) and side in ("buy", "sell") and bool(volume),
        f"pair='{pair}' side='{side}' volume='{volume}'",
    )

    state = str(ticket.get("approval_state", "")).upper()
    add(
        "ticket_pending",
        state == "PENDING_HUMAN_APPROVAL",
        f"approval_state={state}",
    )

    return {"guards": guards, "pass_all": all(g["pass"] for g in guards)}


def _norm_symbol(raw: Any) -> str:
    s = str(raw or "").strip().upper().replace("/", "").replace("-", "")
    if s.endswith(".HOLD"):
        s = s[:-5]
    return s


def _pair_base_candidates(pair: str) -> set[str]:
    p = _norm_symbol(pair)
    if not p:
        return set()
    out: set[str] = {p}
    for quote in ("ZUSD", "USD"):
        if p.endswith(quote) and len(p) > len(quote):
            base = p[: -len(quote)]
            out.add(base)
            if len(base) > 3 and base[0] in ("X", "Z"):
                out.add(base[1:])
    return {x for x in out if x}


def _sell_balance_precheck(
    pair: str,
    volume: Any,
    balance_snapshot: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    pair_clean = str(pair or "").strip().upper()
    try:
        required = abs(float(volume))
    except Exception:
        return {
            "ok": False,
            "enforced": True,
            "reason": "invalid_volume",
            "pair": pair_clean,
            "required": 0.0,
            "available": 0.0,
            "matched_assets": [],
        }

    if required <= 0:
        return {
            "ok": False,
            "enforced": True,
            "reason": "non_positive_volume",
            "pair": pair_clean,
            "required": required,
            "available": 0.0,
            "matched_assets": [],
        }

    snap = balance_snapshot if isinstance(balance_snapshot, dict) else api_kraken_balance(force=0)
    if not isinstance(snap, dict) or not bool(snap.get("ok")):
        # Fail open if balance endpoint is unavailable.
        return {
            "ok": True,
            "enforced": False,
            "reason": "balance_unavailable",
            "pair": pair_clean,
            "required": required,
            "available": None,
            "matched_assets": [],
        }

    pair_norm = _norm_symbol(pair_clean)
    base_candidates = _pair_base_candidates(pair_clean)
    matched_assets: list[str] = []
    available = 0.0

    for row in (snap.get("breakdown") or []):
        if not isinstance(row, dict):
            continue
        asset = str(row.get("asset") or "").strip().upper()
        if not asset:
            continue
        qty = to_float(row.get("qty"), 0.0)
        if qty <= 0:
            continue

        asset_norm = _norm_symbol(asset)
        asset_base = asset_norm[1:] if len(asset_norm) > 3 and asset_norm[0] in ("X", "Z") else asset_norm
        guessed_pair_norm = _norm_symbol(_asset_to_usd_pair(asset) or "")

        match = False
        if guessed_pair_norm and guessed_pair_norm == pair_norm:
            match = True
        if not match and (asset_norm in base_candidates or asset_base in base_candidates):
            match = True

        if match:
            available += qty
            matched_assets.append(asset)

    epsilon = max(1e-8, required * 0.0005)
    return {
        "ok": (available + epsilon) >= required,
        "enforced": True,
        "reason": "ok" if (available + epsilon) >= required else "insufficient_base_balance",
        "pair": pair_clean,
        "required": required,
        "available": available,
        "matched_assets": sorted(set(matched_assets)),
    }


def _auto_stale_queue(queue: list[dict[str, Any]]) -> int:
    """Mark any PENDING ticket older than TTL as STALE_AUTOEXPIRED. Returns count changed."""
    changed = 0
    for t in queue:
        if str(t.get("approval_state", "")).upper() != "PENDING_HUMAN_APPROVAL":
            continue
        if _ticket_age_hours(t) >= APPROVAL_TICKET_TTL_HOURS:
            t["approval_state"] = "STALE_AUTOEXPIRED"
            t["staled_at_utc"] = now_utc()
            changed += 1
    return changed


def _kraken_sign(secret: str, urlpath: str, data: dict[str, Any]) -> str:
    nonce = data["nonce"]
    postdata = _urlencode_appr(data)
    encoded = (str(nonce) + postdata).encode()
    message = urlpath.encode() + _hashlib_appr.sha256(encoded).digest()
    mac = _hmac_appr.new(_base64_appr.b64decode(secret), message, _hashlib_appr.sha512)
    return _base64_appr.b64encode(mac.digest()).decode()


def _kraken_add_order(payload: dict[str, Any]) -> dict[str, Any]:
    """Submit signed order to Kraken. Honors payload['validate'] flag for dry-run."""
    api_key, api_secret = _load_kraken_keys()
    if not api_key or not api_secret:
        return {"error": ["EAPI:Missing credentials in luma_live_keys.env"]}

    data = dict(payload or {})
    # Use nanosecond nonce — Kraken requires strict monotonic increase per API key.
    # Other clients on this key may already be using high-resolution nonces, so we
    # use time.time_ns() to guarantee we never fall below their last value.
    data["nonce"] = str(time.time_ns())
    # Normalize validate to Kraken's expected literal
    if "validate" in data:
        data["validate"] = "true" if str(data["validate"]).lower() in ("true", "1", "yes") else "false"

    urlpath = "/0/private/AddOrder"
    headers = {
        "API-Key": api_key,
        "API-Sign": _kraken_sign(api_secret, urlpath, data),
    }
    try:
        r = _requests_appr.post("https://api.kraken.com" + urlpath, data=data, headers=headers, timeout=20)
        r.raise_for_status()
        body = r.json()
        return body
    except Exception as exc:
        return {"error": [f"transport:{exc}"]}


@app.get("/api/master/approval-queue")
def master_approval_queue() -> dict[str, Any]:
    """Live approval queue with per-ticket guard evaluation. Auto-stales >24h tickets."""
    flags = _load_control_flags()
    queue = _load_approval_queue()
    changed = _auto_stale_queue(queue)
    if changed:
        _save_approval_queue(queue)

    open_pos = _count_open_positions(queue)
    enriched = []
    for t in queue:
        guards = _evaluate_guards(t, flags, open_pos)
        enriched.append({
            "ticket_id": t.get("ticket_id"),
            "timestamp": t.get("timestamp"),
            "controller": t.get("controller"),
            "pair": t.get("pair"),
            "side": t.get("side"),
            "notional_usd": t.get("notional_usd"),
            "volume_base": t.get("volume_base"),
            "approval_state": t.get("approval_state"),
            "note": t.get("note"),
            "validate": str((t.get("payload") or {}).get("validate", "true")).lower() in ("true", "1", "yes"),
            "age_hours": round(_ticket_age_hours(t), 3),
            "guards": guards["guards"],
            "guards_pass_all": guards["pass_all"],
            "txid": t.get("txid"),
            "decided_at_utc": t.get("decided_at_utc"),
            "decided_by": t.get("decided_by"),
            "decision_reason": t.get("decision_reason"),
            "scanner_meta": t.get("scanner_meta") or {},
        })

    return {
        "generated_utc": now_utc(),
        "schema": "luma_approval_queue_v1",
        "count": len(enriched),
        "open_positions": open_pos,
        "control_flags": {
            "kill_switch": bool(flags.get("kill_switch", True)),
            "live_enabled": bool(flags.get("live_enabled", False)),
            "max_notional_per_trade_usd": float(flags.get("max_notional_per_trade_usd", 0.0) or 0.0),
            "max_open_positions": int(flags.get("max_open_positions", 0) or 0),
            "max_daily_loss_usd": float(flags.get("max_daily_loss_usd", 0.0) or 0.0),
            "allowed_controllers": list(flags.get("allowed_controllers", []) or []),
            "deadman_timeout_seconds": int(flags.get("deadman_timeout_seconds", 0) or 0),
        },
        "tickets": enriched,
    }


class ApprovalDecideRequest(BaseModel):
    ticket_id: str
    decision: str  # "approve" | "reject"
    controller: str
    reason: str = ""
    confirm_phrase: str = ""  # must equal "FIRE {ticket_id}" for approve


@app.post("/api/master/approval/decide")
def master_approval_decide(req: ApprovalDecideRequest) -> dict[str, Any]:
    """
    Approve or reject a pending ticket.
    Approve path re-evaluates ALL guards, requires confirm_phrase == 'FIRE <ticket_id>',
    and only then submits the signed Kraken order. Honors ticket payload's validate flag.
    """
    decision = (req.decision or "").lower().strip()
    if decision not in ("approve", "reject"):
        return {"status": "error", "message": "decision must be 'approve' or 'reject'"}

    flags = _load_control_flags()
    queue = _load_approval_queue()
    _auto_stale_queue(queue)

    ticket = next((t for t in queue if str(t.get("ticket_id")) == str(req.ticket_id)), None)
    if ticket is None:
        return {"status": "error", "message": f"ticket {req.ticket_id} not found"}

    state = str(ticket.get("approval_state", "")).upper()
    if state != "PENDING_HUMAN_APPROVAL":
        _append_jsonl(APPROVAL_AUDIT_FILE, {
            "ts": now_utc(),
            "event": "decision_rejected_state",
            "ticket_id": req.ticket_id,
            "current_state": state,
            "controller": req.controller,
        })
        return {"status": "rejected", "reason": f"ticket state is {state}, not PENDING_HUMAN_APPROVAL"}

    if decision == "reject":
        ticket["approval_state"] = "REJECTED_BY_HUMAN"
        ticket["decided_at_utc"] = now_utc()
        ticket["decided_by"] = req.controller
        ticket["decision_reason"] = req.reason or "(no reason)"
        _save_approval_queue(queue)
        _append_jsonl(APPROVAL_AUDIT_FILE, {
            "ts": now_utc(),
            "event": "ticket_rejected",
            "ticket_id": req.ticket_id,
            "controller": req.controller,
            "reason": ticket["decision_reason"],
        })
        return {"status": "rejected", "ticket_id": req.ticket_id}

    # ── APPROVE path ────────────────────────────────────────────────
    expected_phrase = f"FIRE {ticket.get('ticket_id')}"
    if (req.confirm_phrase or "").strip() != expected_phrase:
        _append_jsonl(APPROVAL_AUDIT_FILE, {
            "ts": now_utc(),
            "event": "approve_blocked_confirm_phrase",
            "ticket_id": req.ticket_id,
            "controller": req.controller,
            "expected": expected_phrase,
            "received": req.confirm_phrase,
        })
        return {"status": "blocked", "reason": f"confirm_phrase must equal '{expected_phrase}'"}

    if (req.controller or "").strip() != str(ticket.get("controller", "")).strip():
        _append_jsonl(APPROVAL_AUDIT_FILE, {
            "ts": now_utc(),
            "event": "approve_blocked_controller_mismatch",
            "ticket_id": req.ticket_id,
            "controller": req.controller,
            "ticket_controller": ticket.get("controller"),
        })
        return {"status": "blocked", "reason": "controller does not match ticket controller"}

    open_pos = _count_open_positions(queue)
    eval_res = _evaluate_guards(ticket, flags, open_pos)
    if not eval_res["pass_all"]:
        ticket["approval_state"] = "REJECTED_BY_GUARD"
        ticket["decided_at_utc"] = now_utc()
        ticket["decided_by"] = req.controller
        ticket["decision_reason"] = "guard rail failure"
        ticket["guard_failures"] = [g for g in eval_res["guards"] if not g["pass"]]
        _save_approval_queue(queue)
        _append_jsonl(APPROVAL_AUDIT_FILE, {
            "ts": now_utc(),
            "event": "approve_blocked_by_guards",
            "ticket_id": req.ticket_id,
            "controller": req.controller,
            "failed_guards": ticket["guard_failures"],
        })
        return {"status": "blocked", "reason": "guard_failure", "failed_guards": ticket["guard_failures"]}

    # All guards pass — submit signed order to Kraken.
    payload = dict(ticket.get("payload") or {})
    is_validate = str(payload.get("validate", "true")).lower() in ("true", "1", "yes")

    payload_pair = str(payload.get("pair") or "").strip().upper()
    payload_side = str(payload.get("type") or "").strip().lower()
    payload_volume = payload.get("volume")

    if payload_side == "sell" and not is_validate:
        sell_check = _sell_balance_precheck(payload_pair, payload_volume)
        if not bool(sell_check.get("ok", True)):
            failure = {
                "name": "sell_volume_available",
                "pass": False,
                "detail": (
                    f"pair='{payload_pair}' required={to_float(sell_check.get('required'), 0.0):.8f} "
                    f"available={to_float(sell_check.get('available'), 0.0):.8f} "
                    f"assets={sell_check.get('matched_assets') or []}"
                ),
            }
            ticket["approval_state"] = "REJECTED_BY_GUARD"
            ticket["decided_at_utc"] = now_utc()
            ticket["decided_by"] = req.controller
            ticket["decision_reason"] = "guard rail failure"
            ticket["guard_failures"] = [failure]
            _save_approval_queue(queue)
            _append_jsonl(
                APPROVAL_AUDIT_FILE,
                {
                    "ts": now_utc(),
                    "event": "approve_blocked_sell_balance_precheck",
                    "ticket_id": req.ticket_id,
                    "controller": req.controller,
                    "balance_check": sell_check,
                    "failed_guards": [failure],
                },
            )
            return {
                "status": "blocked",
                "reason": "guard_failure",
                "failed_guards": [failure],
            }

    _append_jsonl(APPROVAL_AUDIT_FILE, {
        "ts": now_utc(),
        "event": "approve_submitting_to_kraken",
        "ticket_id": req.ticket_id,
        "controller": req.controller,
        "validate": is_validate,
        "pair": payload_pair,
        "side": payload_side,
        "volume": payload_volume,
    })

    result = _kraken_add_order(payload)
    err = result.get("error") or []
    if err:
        ticket["approval_state"] = "EXECUTION_ERROR"
        ticket["decided_at_utc"] = now_utc()
        ticket["decided_by"] = req.controller
        ticket["decision_reason"] = req.reason or "(approved)"
        ticket["kraken_error"] = err
        _save_approval_queue(queue)
        _append_jsonl(APPROVAL_AUDIT_FILE, {
            "ts": now_utc(),
            "event": "kraken_error",
            "ticket_id": req.ticket_id,
            "error": err,
        })
        return {"status": "error", "ticket_id": req.ticket_id, "kraken_error": err}

    kraken_result = result.get("result", {}) if isinstance(result, dict) else {}
    txids = kraken_result.get("txid") or []
    descr = kraken_result.get("descr") or {}

    ticket["approval_state"] = "EXECUTED_VALIDATE" if is_validate else "EXECUTED_OPEN"
    ticket["decided_at_utc"] = now_utc()
    ticket["decided_by"] = req.controller
    ticket["decision_reason"] = req.reason or "(approved)"
    ticket["txid"] = txids
    ticket["kraken_descr"] = descr
    _save_approval_queue(queue)

    # Append to canonical execution events log + approval audit
    event_row = {
        "ts": now_utc(),
        "event": "submit_order",
        "ticket_id": req.ticket_id,
        "controller": req.controller,
        "validate": is_validate,
        "pair": payload.get("pair"),
        "side": payload.get("type"),
        "volume": payload.get("volume"),
        "txid": txids,
        "descr": descr,
        "source": "approval_dashboard",
    }
    _append_jsonl(EXECUTION_EVENTS_FILE, event_row)
    _append_jsonl(APPROVAL_AUDIT_FILE, event_row)

    return {
        "status": "executed",
        "ticket_id": req.ticket_id,
        "validate": is_validate,
        "txid": txids,
        "descr": descr,
    }


# ───────────────────────────────────────────────────────────────────────
# AUTO-TICKET PRODUCER bridge — one-click "Scan & Refill" from dashboard
# ───────────────────────────────────────────────────────────────────────
@app.post("/api/master/approval/scan-refill")
def master_scan_refill(req: dict | None = None) -> dict[str, Any]:
    """Emit fresh PENDING tickets from the latest spike-hunter cache.

    Body (all optional):
      {
        "use_cached": true,        # use spike_hunter_latest.json (default true, instant)
        "validate":   true,        # true=DRY-RUN, false=LIVE (default true)
                "controller": "Robert",    # default Robert
                "top_n": 160,               # optional override
                "scan_max_age_sec": 60      # optional override
      }
    """
    body = req or {}
    use_cached = bool(body.get("use_cached", True))
    validate = bool(body.get("validate", True))
    controller = str(body.get("controller") or "Robert")

    try:
        import sys as _sys_atp, importlib as _imp_atp
        _code_dir = str(ROOT / "code")
        if _code_dir not in _sys_atp.path:
            _sys_atp.path.insert(0, _code_dir)
        if "auto_ticket_producer" in _sys_atp.modules:
            atp = _imp_atp.reload(_sys_atp.modules["auto_ticket_producer"])
        else:
            atp = _imp_atp.import_module("auto_ticket_producer")

        runtime_cfg = atp._read_runtime_config(default_threshold=None, default_enabled=True)
        runtime_top_n = max(1, atp._safe_int(body.get("top_n"), atp._safe_int(runtime_cfg.get("top_n"), atp.TOP_N_DEFAULT)))
        runtime_scan_max_age = max(
            0.0,
            atp._safe_float(
                body.get("scan_max_age_sec"),
                atp._safe_float(runtime_cfg.get("scan_max_age_sec"), atp.SCAN_MAX_AGE_SEC_DEFAULT),
            ),
        )

        summary = atp.emit_tickets(
            use_cached=use_cached,
            validate=validate,
            controller=controller,
            bankroll=atp.BANKROLL_DEFAULT,
            top_n=runtime_top_n,
            scan_max_age_sec=runtime_scan_max_age,
            runtime_cfg=runtime_cfg,
        )
        return {"status": "ok", **summary}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}


@app.get("/api/master/auto-fire/status")
def master_autofire_status() -> dict[str, Any]:
    """Read live config + daemon liveness for the auto-ticket producer."""
    cfg_path = ROOT / "run" / "auto_fire_config.json"
    pid_path = ROOT / "run" / "auto_ticket_producer.pid"
    cfg = {"enabled": False, "auto_fire_score": None}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    pid = None
    alive = False
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip())
        except Exception:
            pid = None
    if pid is not None:
        # Cross-platform liveness probe. Windows os.kill(pid,0) raises
        # OSError(87) for live processes, so prefer psutil when available.
        try:
            import psutil  # type: ignore
            alive = psutil.pid_exists(pid)
        except Exception:
            try:
                import ctypes
                PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                h = ctypes.windll.kernel32.OpenProcess(
                    PROCESS_QUERY_LIMITED_INFORMATION, False, pid
                )
                if h:
                    ctypes.windll.kernel32.CloseHandle(h)
                    alive = True
                else:
                    alive = False
            except Exception:
                alive = False
    return {
        "status": "ok",
        "enabled": bool(cfg.get("enabled")),
        "auto_fire_score": cfg.get("auto_fire_score"),
        "max_pending_tickets": cfg.get("max_pending_tickets"),
        "max_cycle_emits": cfg.get("max_cycle_emits"),
        "adaptive_queue": cfg.get("adaptive_queue", True),
        "scan_max_age_sec": cfg.get("scan_max_age_sec"),
        "top_n": cfg.get("top_n"),
        "max_auto_fires_per_cycle": cfg.get("max_auto_fires_per_cycle"),
        "alpha_gate_min_edge": cfg.get("alpha_gate_min_edge"),
        "alpha_gate_max_spread_bps": cfg.get("alpha_gate_max_spread_bps"),
        "alpha_gate_min_turnover_usd": cfg.get("alpha_gate_min_turnover_usd"),
        "alpha_gate_allow_watch_strategy": cfg.get("alpha_gate_allow_watch_strategy"),
        "alpha_gate_require_match_live": cfg.get("alpha_gate_require_match_live"),
        "strategy_mode": cfg.get("strategy_mode"),
        "max_notional_usd": cfg.get("max_notional_usd"),
        "moonshot_bankroll_frac": cfg.get("moonshot_bankroll_frac"),
        "moonshot_max_per_cycle": cfg.get("moonshot_max_per_cycle"),
        "moonshot_min_edge": cfg.get("moonshot_min_edge"),
        "moonshot_min_dip_pct": cfg.get("moonshot_min_dip_pct"),
        "moonshot_max_rsi": cfg.get("moonshot_max_rsi"),
        "moonshot_min_rebound_15m_pct": cfg.get("moonshot_min_rebound_15m_pct"),
        "moonshot_max_spread_bps": cfg.get("moonshot_max_spread_bps"),
        "moonshot_min_turnover_usd": cfg.get("moonshot_min_turnover_usd"),
        "quickhit_target_notional_usd": cfg.get("quickhit_target_notional_usd"),
        "quickhit_max_per_cycle": cfg.get("quickhit_max_per_cycle"),
        "quickhit_min_edge": cfg.get("quickhit_min_edge"),
        "quickhit_min_r1m_pct": cfg.get("quickhit_min_r1m_pct"),
        "quickhit_min_r15m_pct": cfg.get("quickhit_min_r15m_pct"),
        "quickhit_min_m4h_pct": cfg.get("quickhit_min_m4h_pct"),
        "quickhit_max_spread_bps": cfg.get("quickhit_max_spread_bps"),
        "quickhit_min_turnover_usd": cfg.get("quickhit_min_turnover_usd"),
        "swing_target_notional_usd": cfg.get("swing_target_notional_usd"),
        "swing_max_per_cycle": cfg.get("swing_max_per_cycle"),
        "swing_min_edge": cfg.get("swing_min_edge"),
        "swing_min_r1h_pct": cfg.get("swing_min_r1h_pct"),
        "swing_min_m4h_pct": cfg.get("swing_min_m4h_pct"),
        "swing_max_spread_bps": cfg.get("swing_max_spread_bps"),
        "swing_min_turnover_usd": cfg.get("swing_min_turnover_usd"),
        "daemon_pid": pid,
        "daemon_alive": alive,
    }


@app.post("/api/master/auto-fire/control")
def master_autofire_control(req: dict | None = None) -> dict[str, Any]:
    """Update live auto-fire config without restarting the daemon.

    Body (all optional):
      {
        "enabled":          true|false,   # pause/resume auto-fire
                "auto_fire_score":  70.0,         # null disables auto-fire
                "max_pending_tickets": 10,
                "max_cycle_emits": 6,
                "adaptive_queue": true,
                "scan_max_age_sec": 120,
                "top_n": 60,
                                "max_auto_fires_per_cycle": 3,
                                "alpha_gate_min_edge": 4.0,
                                "alpha_gate_max_spread_bps": 35.0,
                                "alpha_gate_min_turnover_usd": 250000.0,
                                                                "alpha_gate_allow_watch_strategy": false,
                                "alpha_gate_require_match_live": true,
                                                                "strategy_mode": "hybrid",   # hybrid|moonshot|quickhit|swing
                                                                "max_notional_usd": 20.0
      }
    """
    body = req or {}
    cfg_path = ROOT / "run" / "auto_fire_config.json"
    cur = {
        "enabled": True,
        "auto_fire_score": None,
        "max_pending_tickets": 6,
        "max_cycle_emits": 6,
        "adaptive_queue": True,
        "scan_max_age_sec": 120.0,
        "top_n": 20,
        "max_auto_fires_per_cycle": 3,
        "alpha_gate_min_edge": 4.0,
        "alpha_gate_max_spread_bps": 35.0,
        "alpha_gate_min_turnover_usd": 250000.0,
        "alpha_gate_allow_watch_strategy": False,
        "alpha_gate_require_match_live": True,
        "strategy_mode": "hybrid",
        "max_notional_usd": 20.0,
        "moonshot_bankroll_frac": 0.18,
        "moonshot_max_per_cycle": 1,
        "moonshot_min_edge": 5.5,
        "moonshot_min_dip_pct": 18.0,
        "moonshot_max_rsi": 24.0,
        "moonshot_min_rebound_15m_pct": 0.08,
        "moonshot_max_spread_bps": 22.0,
        "moonshot_min_turnover_usd": 200000.0,
        "quickhit_target_notional_usd": 12.0,
        "quickhit_max_per_cycle": 4,
        "quickhit_min_edge": 4.0,
        "quickhit_min_r1m_pct": 0.05,
        "quickhit_min_r15m_pct": 0.15,
        "quickhit_min_m4h_pct": -8.0,
        "quickhit_max_spread_bps": 24.0,
        "quickhit_min_turnover_usd": 180000.0,
        "swing_target_notional_usd": 16.0,
        "swing_max_per_cycle": 2,
        "swing_min_edge": 4.5,
        "swing_min_r1h_pct": 0.12,
        "swing_min_m4h_pct": -3.0,
        "swing_max_spread_bps": 30.0,
        "swing_min_turnover_usd": 150000.0,
    }
    if cfg_path.exists():
        try:
            cur = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    if "enabled" in body:
        cur["enabled"] = bool(body["enabled"])
    if "auto_fire_score" in body:
        v = body["auto_fire_score"]
        if v is None:
            cur["auto_fire_score"] = None
        else:
            try:
                cur["auto_fire_score"] = float(v)
            except Exception:
                return {"status": "error", "error": "auto_fire_score must be a number or null"}
    if "max_pending_tickets" in body:
        try:
            cur["max_pending_tickets"] = max(1, int(float(body["max_pending_tickets"])))
        except Exception:
            return {"status": "error", "error": "max_pending_tickets must be a positive integer"}
    if "max_cycle_emits" in body:
        try:
            cur["max_cycle_emits"] = max(1, int(float(body["max_cycle_emits"])))
        except Exception:
            return {"status": "error", "error": "max_cycle_emits must be a positive integer"}
    if "adaptive_queue" in body:
        cur["adaptive_queue"] = bool(body["adaptive_queue"])
    if "scan_max_age_sec" in body:
        try:
            cur["scan_max_age_sec"] = max(0.0, float(body["scan_max_age_sec"]))
        except Exception:
            return {"status": "error", "error": "scan_max_age_sec must be a non-negative number"}
    if "top_n" in body:
        try:
            cur["top_n"] = max(1, int(float(body["top_n"])))
        except Exception:
            return {"status": "error", "error": "top_n must be a positive integer"}
    if "max_auto_fires_per_cycle" in body:
        try:
            cur["max_auto_fires_per_cycle"] = max(0, int(float(body["max_auto_fires_per_cycle"])))
        except Exception:
            return {"status": "error", "error": "max_auto_fires_per_cycle must be a non-negative integer"}
    if "alpha_gate_min_edge" in body:
        try:
            cur["alpha_gate_min_edge"] = max(0.0, float(body["alpha_gate_min_edge"]))
        except Exception:
            return {"status": "error", "error": "alpha_gate_min_edge must be a non-negative number"}
    if "alpha_gate_max_spread_bps" in body:
        try:
            cur["alpha_gate_max_spread_bps"] = max(0.0, float(body["alpha_gate_max_spread_bps"]))
        except Exception:
            return {"status": "error", "error": "alpha_gate_max_spread_bps must be a non-negative number"}
    if "alpha_gate_min_turnover_usd" in body:
        try:
            cur["alpha_gate_min_turnover_usd"] = max(0.0, float(body["alpha_gate_min_turnover_usd"]))
        except Exception:
            return {"status": "error", "error": "alpha_gate_min_turnover_usd must be a non-negative number"}
    if "alpha_gate_allow_watch_strategy" in body:
        cur["alpha_gate_allow_watch_strategy"] = bool(body["alpha_gate_allow_watch_strategy"])
    if "alpha_gate_require_match_live" in body:
        cur["alpha_gate_require_match_live"] = bool(body["alpha_gate_require_match_live"])
    if "strategy_mode" in body:
        mode = str(body.get("strategy_mode") or "").strip().lower()
        if mode not in {"hybrid", "moonshot", "quickhit", "swing"}:
            return {"status": "error", "error": "strategy_mode must be one of hybrid|moonshot|quickhit|swing"}
        cur["strategy_mode"] = mode
    if "max_notional_usd" in body:
        try:
            cur["max_notional_usd"] = max(5.0, float(body["max_notional_usd"]))
        except Exception:
            return {"status": "error", "error": "max_notional_usd must be a number >= 5"}

    if "moonshot_bankroll_frac" in body:
        try:
            cur["moonshot_bankroll_frac"] = min(0.60, max(0.02, float(body["moonshot_bankroll_frac"])))
        except Exception:
            return {"status": "error", "error": "moonshot_bankroll_frac must be a number"}
    if "moonshot_max_per_cycle" in body:
        try:
            cur["moonshot_max_per_cycle"] = max(0, int(float(body["moonshot_max_per_cycle"])))
        except Exception:
            return {"status": "error", "error": "moonshot_max_per_cycle must be a non-negative integer"}
    if "moonshot_min_edge" in body:
        try:
            cur["moonshot_min_edge"] = max(0.0, float(body["moonshot_min_edge"]))
        except Exception:
            return {"status": "error", "error": "moonshot_min_edge must be a non-negative number"}
    if "moonshot_min_dip_pct" in body:
        try:
            cur["moonshot_min_dip_pct"] = max(0.0, float(body["moonshot_min_dip_pct"]))
        except Exception:
            return {"status": "error", "error": "moonshot_min_dip_pct must be a non-negative number"}
    if "moonshot_max_rsi" in body:
        try:
            cur["moonshot_max_rsi"] = min(100.0, max(0.0, float(body["moonshot_max_rsi"])))
        except Exception:
            return {"status": "error", "error": "moonshot_max_rsi must be a number between 0 and 100"}
    if "moonshot_min_rebound_15m_pct" in body:
        try:
            cur["moonshot_min_rebound_15m_pct"] = float(body["moonshot_min_rebound_15m_pct"])
        except Exception:
            return {"status": "error", "error": "moonshot_min_rebound_15m_pct must be a number"}
    if "moonshot_max_spread_bps" in body:
        try:
            cur["moonshot_max_spread_bps"] = max(0.0, float(body["moonshot_max_spread_bps"]))
        except Exception:
            return {"status": "error", "error": "moonshot_max_spread_bps must be a non-negative number"}
    if "moonshot_min_turnover_usd" in body:
        try:
            cur["moonshot_min_turnover_usd"] = max(0.0, float(body["moonshot_min_turnover_usd"]))
        except Exception:
            return {"status": "error", "error": "moonshot_min_turnover_usd must be a non-negative number"}

    if "quickhit_target_notional_usd" in body:
        try:
            cur["quickhit_target_notional_usd"] = max(5.0, float(body["quickhit_target_notional_usd"]))
        except Exception:
            return {"status": "error", "error": "quickhit_target_notional_usd must be a number >= 5"}
    if "quickhit_max_per_cycle" in body:
        try:
            cur["quickhit_max_per_cycle"] = max(0, int(float(body["quickhit_max_per_cycle"])))
        except Exception:
            return {"status": "error", "error": "quickhit_max_per_cycle must be a non-negative integer"}
    if "quickhit_min_edge" in body:
        try:
            cur["quickhit_min_edge"] = max(0.0, float(body["quickhit_min_edge"]))
        except Exception:
            return {"status": "error", "error": "quickhit_min_edge must be a non-negative number"}
    if "quickhit_min_r1m_pct" in body:
        try:
            cur["quickhit_min_r1m_pct"] = float(body["quickhit_min_r1m_pct"])
        except Exception:
            return {"status": "error", "error": "quickhit_min_r1m_pct must be a number"}
    if "quickhit_min_r15m_pct" in body:
        try:
            cur["quickhit_min_r15m_pct"] = float(body["quickhit_min_r15m_pct"])
        except Exception:
            return {"status": "error", "error": "quickhit_min_r15m_pct must be a number"}
    if "quickhit_min_m4h_pct" in body:
        try:
            cur["quickhit_min_m4h_pct"] = float(body["quickhit_min_m4h_pct"])
        except Exception:
            return {"status": "error", "error": "quickhit_min_m4h_pct must be a number"}
    if "quickhit_max_spread_bps" in body:
        try:
            cur["quickhit_max_spread_bps"] = max(0.0, float(body["quickhit_max_spread_bps"]))
        except Exception:
            return {"status": "error", "error": "quickhit_max_spread_bps must be a non-negative number"}
    if "quickhit_min_turnover_usd" in body:
        try:
            cur["quickhit_min_turnover_usd"] = max(0.0, float(body["quickhit_min_turnover_usd"]))
        except Exception:
            return {"status": "error", "error": "quickhit_min_turnover_usd must be a non-negative number"}

    if "swing_target_notional_usd" in body:
        try:
            cur["swing_target_notional_usd"] = max(5.0, float(body["swing_target_notional_usd"]))
        except Exception:
            return {"status": "error", "error": "swing_target_notional_usd must be a number >= 5"}
    if "swing_max_per_cycle" in body:
        try:
            cur["swing_max_per_cycle"] = max(0, int(float(body["swing_max_per_cycle"])))
        except Exception:
            return {"status": "error", "error": "swing_max_per_cycle must be a non-negative integer"}
    if "swing_min_edge" in body:
        try:
            cur["swing_min_edge"] = max(0.0, float(body["swing_min_edge"]))
        except Exception:
            return {"status": "error", "error": "swing_min_edge must be a non-negative number"}
    if "swing_min_r1h_pct" in body:
        try:
            cur["swing_min_r1h_pct"] = float(body["swing_min_r1h_pct"])
        except Exception:
            return {"status": "error", "error": "swing_min_r1h_pct must be a number"}
    if "swing_min_m4h_pct" in body:
        try:
            cur["swing_min_m4h_pct"] = float(body["swing_min_m4h_pct"])
        except Exception:
            return {"status": "error", "error": "swing_min_m4h_pct must be a number"}
    if "swing_max_spread_bps" in body:
        try:
            cur["swing_max_spread_bps"] = max(0.0, float(body["swing_max_spread_bps"]))
        except Exception:
            return {"status": "error", "error": "swing_max_spread_bps must be a non-negative number"}
    if "swing_min_turnover_usd" in body:
        try:
            cur["swing_min_turnover_usd"] = max(0.0, float(body["swing_min_turnover_usd"]))
        except Exception:
            return {"status": "error", "error": "swing_min_turnover_usd must be a non-negative number"}

    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cur, indent=2), encoding="utf-8")
    return {"status": "ok", **cur}


if DASH.exists():
    # ──────────────────────────────────────────────────────────────
    # SPIKE HUNTER  — Live Kraken opportunity scanner
    # ──────────────────────────────────────────────────────────────
    _SPIKE_HUNTER_OUT  = ROOT / "out" / "spike_hunter"
    _SPIKE_HUNTER_FILE = _SPIKE_HUNTER_OUT / "spike_hunter_latest.json"
    _SPIKE_SCAN_LOCK   = ROOT / "run" / "spike_hunter_running.lock"


    @app.get("/api/spike-hunter/latest")
    def spike_hunter_latest() -> dict[str, Any]:
        """Return the most recently completed spike scan results."""
        if _SPIKE_HUNTER_FILE.exists():
            try:
                data = json.loads(_SPIKE_HUNTER_FILE.read_text())
                data["from_cache"] = True
                return data
            except Exception:
                pass
        return {
            "schema": "luma_spike_hunter_v1",
            "generated_utc": now_utc(),
            "from_cache": False,
            "pairs_scanned": 0,
            "leaderboard": [],
            "message": "No scan results yet — call POST /api/spike-hunter/scan to run.",
        }


    class SpikeHunterScanRequest(BaseModel):
        bankroll: float = 150.0
        top_n: int = 15


    @app.post("/api/spike-hunter/scan")
    def spike_hunter_scan(req: SpikeHunterScanRequest) -> dict[str, Any]:
        """
        Kick off a background spike scan on all Kraken USD pairs.
        Returns immediately with status; poll /api/spike-hunter/latest for results.
        """
        if _SPIKE_SCAN_LOCK.exists():
            try:
                age = time.time() - _SPIKE_SCAN_LOCK.stat().st_mtime
                if age < 300:  # scan already running (within last 5 min)
                    return {"status": "already_running", "lock_age_seconds": round(age, 0)}
            except Exception:
                pass
            _SPIKE_SCAN_LOCK.unlink(missing_ok=True)

        _SPIKE_SCAN_LOCK.parent.mkdir(parents=True, exist_ok=True)
        _SPIKE_SCAN_LOCK.touch()

        script = CODE / "kraken_spike_hunter_live.py"
        if not script.exists():
            _SPIKE_SCAN_LOCK.unlink(missing_ok=True)
            return {"status": "error", "message": "spike hunter script not found"}

        try:
            python = sys.executable
            proc = subprocess.Popen(
                [python, str(script), str(req.bankroll)],
                cwd=str(ROOT),
                stdout=subprocess.DEVNULL,
                stderr=open(str(ROOT / "run" / "spike_hunter_stderr.log"), "w"),
            )
            _append_jsonl(EXEC_OUT / "remediation_actions.jsonl", {
                "ts": now_utc(),
                "event": "spike_scan_started",
                "pid": proc.pid,
                "bankroll": req.bankroll,
            })
            return {"status": "started", "pid": proc.pid, "bankroll": req.bankroll,
                    "message": "Scan running in background. Poll /api/spike-hunter/latest for results."}
        except Exception as exc:
            _SPIKE_SCAN_LOCK.unlink(missing_ok=True)
            return {"status": "error", "message": str(exc)}


# Mount static dashboard last so all API routes take priority.
@app.get("/api/events/recent")
def api_events_recent(limit: int = 24):
    """Tail the execution_events.jsonl ledger for the cockpit ticker.
    Returns the last `limit` events with normalized shape."""
    src = None
    for cand in (ROOT / "execution_events.jsonl",
                 OUT / "execution_events.jsonl",
                 ROOT / "data" / "out" / "execution_events.jsonl",
                 EXEC_OUT / "execution_events.jsonl"):
        try:
            if cand.exists() and cand.stat().st_size > 0:
                src = cand
                break
        except Exception:
            continue
    if src is None:
        return {"events": [], "source": None, "count": 0}
    try:
        # Read last ~64KB to bound IO; filter and tail.
        try:
            sz = src.stat().st_size
            with src.open("rb") as fh:
                if sz > 65536:
                    fh.seek(sz - 65536)
                    fh.readline()  # discard partial
                tail = fh.read().decode("utf-8", errors="replace").splitlines()
        except Exception:
            tail = src.read_text(encoding="utf-8", errors="replace").splitlines()
        rows = []
        for line in tail[-max(1, min(limit, 200)):]:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            txid = ev.get("txid")
            if isinstance(txid, list) and txid:
                txid = txid[0]
            rows.append({
                "ts": ev.get("ts") or ev.get("timestamp"),
                "event": ev.get("event") or ev.get("type") or "event",
                "pair": ev.get("pair") or ev.get("symbol"),
                "side": ev.get("side"),
                "volume": ev.get("volume"),
                "txid": txid,
                "controller": ev.get("controller"),
                "source": ev.get("source"),
            })
        return {"events": rows, "source": str(src), "count": len(rows)}
    except Exception as exc:
        return {"events": [], "source": str(src), "error": str(exc)}


@app.get("/api/positions/live")
def api_positions_live():
    """Reduce execution_events.jsonl into an honest open-position view.

    Surfaces ONLY what's in the real Kraken ledger:
      - real opens (events with txid + side + pair),
      - any closes/sells (matched against opens by pair, FIFO),
      - resulting open lots (still on the books),
      - per-event-type counts so investors can see the full audit shape.

    No paper-engine numbers are mixed in. This is the live truth.
    """
    src = None
    for cand in (ROOT / "execution_events.jsonl",
                 OUT / "execution_events.jsonl",
                 ROOT / "data" / "out" / "execution_events.jsonl",
                 EXEC_OUT / "execution_events.jsonl"):
        try:
            if cand.exists() and cand.stat().st_size > 0:
                src = cand
                break
        except Exception:
            continue
    if src is None:
        return {"source": None, "lots_open": [], "closed": [], "totals": {}, "event_counts": {}}
    try:
        lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as exc:
        return {"source": str(src), "error": str(exc)}

    event_counts: dict[str, int] = {}
    side_counts: dict[str, int] = {"buy": 0, "sell": 0, "other": 0}
    pair_counts: dict[str, int] = {}
    opens: list[dict[str, Any]] = []
    closes: list[dict[str, Any]] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        et = (ev.get("event") or ev.get("type") or "event")
        event_counts[et] = event_counts.get(et, 0) + 1
        side = (ev.get("side") or "").lower()
        if side == "buy":
            side_counts["buy"] += 1
        elif side == "sell":
            side_counts["sell"] += 1
        elif side:
            side_counts["other"] += 1
        pair = ev.get("pair") or ev.get("symbol")
        if pair:
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

        # A "real fill" is a submit_order with a Kraken txid (OXXXXX-XXXXX-XXXXXX shape).
        txid = ev.get("txid")
        if isinstance(txid, list) and txid:
            txid = txid[0]
        is_real_fill = (
            et == "submit_order"
            and isinstance(txid, str)
            and len(txid) >= 15
            and txid.count("-") >= 2
        )
        if not is_real_fill:
            continue
        try:
            vol = float(ev.get("volume") or 0)
        except Exception:
            vol = 0.0
        try:
            px = float(ev.get("price") or ev.get("limit_price") or 0) or None
        except Exception:
            px = None
        rec = {
            "ts": ev.get("ts") or ev.get("timestamp"),
            "pair": pair,
            "side": side,
            "volume": vol,
            "remaining": vol,
            "price": px,
            "txid": txid,
            "controller": ev.get("controller"),
        }
        if side == "buy":
            opens.append(rec)
        elif side == "sell":
            # FIFO match against any open buys on same pair
            qty = vol
            for op in opens:
                if op["pair"] != pair or op["remaining"] <= 0:
                    continue
                take = min(op["remaining"], qty)
                op["remaining"] -= take
                qty -= take
                closes.append({
                    "open_txid": op["txid"], "close_txid": txid,
                    "pair": pair, "qty": take,
                    "open_ts": op["ts"], "close_ts": rec["ts"],
                    "open_price": op["price"], "close_price": rec["price"],
                })
                if qty <= 1e-12:
                    break
            if qty > 1e-12:
                # naked short / unmatched sell
                closes.append({
                    "open_txid": None, "close_txid": txid,
                    "pair": pair, "qty": qty,
                    "open_ts": None, "close_ts": rec["ts"],
                    "open_price": None, "close_price": rec["price"],
                    "naked_sell": True,
                })

    lots_open = [
        {k: v for k, v in op.items() if k != "remaining"} | {"remaining": op["remaining"]}
        for op in opens if op["remaining"] > 1e-12
    ]
    totals = {
        "events_total": sum(event_counts.values()),
        "real_fills": len([1 for o in opens]) + len([1 for c in closes if c.get("close_txid")]),
        "real_buys":  sum(1 for o in opens),
        "real_sells": sum(1 for c in closes if c.get("close_txid")),
        "open_lot_count": len(lots_open),
        "closed_round_trips": sum(1 for c in closes if c.get("open_txid") and c.get("close_txid")),
        "naked_sells": sum(1 for c in closes if c.get("naked_sell")),
    }
    return {
        "source": str(src),
        "totals": totals,
        "event_counts": event_counts,
        "side_counts": side_counts,
        "pair_counts": pair_counts,
        "lots_open": lots_open,
        "closed": closes,
    }


# ---------------------------------------------------------------------------
# REAL KRAKEN BALANCE (private/Balance) + USD equity + history sparkline
# ---------------------------------------------------------------------------
KRAKEN_EQUITY_HISTORY_FILE = ROOT / "kraken_equity_history.jsonl"
_KRAKEN_BAL_CACHE: dict[str, Any] = {"ts": 0.0, "data": None}
_KRAKEN_BAL_TTL_S = 25.0  # respect Kraken rate limits — refresh at most every 25s

# Kraken returns asset codes like "ZUSD", "XXBT", "API3"; map to USD ticker pair.
_KRAKEN_ASSET_TO_PAIR = {
    "ZUSD": None, "USD": None, "ZUSD.HOLD": None,
    "XXBT": "XBTUSD", "XBT": "XBTUSD",
    "XETH": "ETHUSD", "ETH": "ETHUSD",
    "XLTC": "LTCUSD", "LTC": "LTCUSD",
    "XXRP": "XRPUSD", "XRP": "XRPUSD",
    "XXDG": "XDGUSD", "XDG": "XDGUSD", "DOGE": "XDGUSD",
}


def _asset_to_usd_pair(asset: str) -> str | None:
    if asset in _KRAKEN_ASSET_TO_PAIR:
        return _KRAKEN_ASSET_TO_PAIR[asset]
    # Default: assume e.g. "API3" → "API3USD", "BABY" → "BABYUSD"
    base = asset.lstrip("X").lstrip("Z") if asset.startswith(("X", "Z")) and len(asset) > 3 else asset
    return f"{base}USD"


def _kraken_public_tickers(pairs: list[str]) -> dict[str, float]:
    if not pairs:
        return {}
    try:
        url = "https://api.kraken.com/0/public/Ticker?pair=" + ",".join(pairs)
        r = _requests_appr.get(url, timeout=8)
        obj = r.json()
        out: dict[str, float] = {}
        for k, v in (obj.get("result") or {}).items():
            try:
                # Kraken ticker: c[0] = last trade close price
                out[k] = float(v["c"][0])
            except Exception:
                continue
        return out
    except Exception:
        return {}


def _kraken_private_balance() -> dict[str, Any]:
    api_key, api_secret = _load_kraken_keys()
    if not api_key or not api_secret:
        return {"error": ["EAPI:Missing credentials in luma_live_keys.env"]}
    urlpath = "/0/private/Balance"
    data = {"nonce": str(time.time_ns())}
    headers = {
        "API-Key": api_key,
        "API-Sign": _kraken_sign(api_secret, urlpath, data),
    }
    try:
        r = _requests_appr.post("https://api.kraken.com" + urlpath, data=data, headers=headers, timeout=12)
        return r.json()
    except Exception as e:
        return {"error": [f"EAPI:Network:{e}"]}


def _build_kraken_equity_snapshot() -> dict[str, Any]:
    raw = _kraken_private_balance()
    if raw.get("error"):
        return {"ok": False, "error": raw.get("error"), "ts": now_utc()}
    bal = raw.get("result") or {}
    # Convert string balances → float, drop dust (< 1e-10)
    holdings: dict[str, float] = {}
    for k, v in bal.items():
        try:
            f = float(v)
        except Exception:
            continue
        if abs(f) > 1e-10:
            holdings[k] = f

    # Resolve USD equivalent
    pair_map: dict[str, str] = {}
    for asset in holdings:
        pr = _asset_to_usd_pair(asset)
        if pr:
            pair_map[asset] = pr
    tickers = _kraken_public_tickers(sorted(set(pair_map.values()))) if pair_map else {}

    breakdown: list[dict[str, Any]] = []
    usd_equity = 0.0
    for asset, qty in holdings.items():
        if asset in ("ZUSD", "USD"):
            usd_value = qty
            price = 1.0
            pair = "USD"
        else:
            pair = pair_map.get(asset)
            # Kraken often returns ticker keyed by its own pair name; try a couple variants
            price = 0.0
            if pair:
                for cand in (pair, "X" + pair, pair.replace("XBT", "XXBT"), pair.replace("USD", "ZUSD")):
                    if cand in tickers:
                        price = tickers[cand]; break
                # Some pairs key as base symbol concat e.g. API3USD, BABYUSD — already covered
                if not price:
                    for tk_key, tk_px in tickers.items():
                        if tk_key.endswith("USD") and pair and tk_key.replace("X", "").replace("Z", "") == pair.replace("X", "").replace("Z", ""):
                            price = tk_px; break
            usd_value = qty * price if price else 0.0
        usd_equity += usd_value
        breakdown.append({
            "asset": asset,
            "qty": qty,
            "pair": pair,
            "price_usd": price,
            "value_usd": usd_value,
            "priced": price > 0 or asset in ("ZUSD", "USD"),
        })
    breakdown.sort(key=lambda r: -r["value_usd"])

    snap = {
        "ok": True,
        "ts": now_utc(),
        "usd_equity": round(usd_equity, 4),
        "asset_count": len(holdings),
        "breakdown": breakdown,
    }
    # Append to history
    try:
        with KRAKEN_EQUITY_HISTORY_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": snap["ts"], "usd_equity": snap["usd_equity"], "asset_count": snap["asset_count"]}) + "\n")
    except Exception:
        pass
    return snap


@app.get("/api/kraken/balance")
def api_kraken_balance(force: int = 0):
    now = time.time()
    cached = _KRAKEN_BAL_CACHE.get("data")
    if not force and cached and (now - _KRAKEN_BAL_CACHE.get("ts", 0.0)) < _KRAKEN_BAL_TTL_S:
        return {**cached, "cached": True, "cache_age_s": round(now - _KRAKEN_BAL_CACHE["ts"], 1)}
    snap = _build_kraken_equity_snapshot()
    if snap.get("ok"):
        _KRAKEN_BAL_CACHE["ts"] = now
        _KRAKEN_BAL_CACHE["data"] = snap
    return {**snap, "cached": False}


@app.get("/api/kraken/equity_history")
def api_kraken_equity_history(limit: int = 240):
    """Return last N equity snapshots for the cockpit sparkline."""
    out: list[dict[str, Any]] = []
    if not KRAKEN_EQUITY_HISTORY_FILE.exists():
        return {"points": [], "count": 0, "source": str(KRAKEN_EQUITY_HISTORY_FILE)}
    try:
        with KRAKEN_EQUITY_HISTORY_FILE.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass
    if limit and len(out) > limit:
        out = out[-limit:]
    first_eq = out[0]["usd_equity"] if out else 0.0
    last_eq  = out[-1]["usd_equity"] if out else 0.0
    return {
        "points": out,
        "count": len(out),
        "first_usd": first_eq,
        "last_usd": last_eq,
        "delta_usd": round(last_eq - first_eq, 4),
        "delta_pct": round(((last_eq - first_eq) / first_eq * 100.0), 4) if first_eq else 0.0,
        "source": str(KRAKEN_EQUITY_HISTORY_FILE),
    }


@app.get("/api/kraken/unrealized")
def api_kraken_unrealized() -> dict[str, Any]:
    """For each open lot in the live ledger, compute unrealized P&L by comparing
    fill price vs current Kraken last-trade price. This is the honest 'are we up
    or down on this real money?' answer."""
    pos = api_positions_live()  # reuse the FIFO logic
    lots = pos.get("lots_open") or []
    if not lots:
        return {"ok": True, "ts": now_utc(), "lots": [], "totals": {"cost_usd": 0, "value_usd": 0, "upnl_usd": 0, "upnl_pct": 0}}
    pairs = sorted({l.get("pair") for l in lots if l.get("pair")})
    tickers = _kraken_public_tickers(pairs)
    # Enrich missing fill prices via QueryOrders (cached on disk)
    fill_prices = _resolve_fill_prices([l.get("txid") for l in lots if l.get("txid")])
    enriched: list[dict[str, Any]] = []
    cost_total = 0.0
    value_total = 0.0
    for l in lots:
        pair = l.get("pair") or ""
        qty  = float(l.get("remaining") or 0.0)
        fill = float(l.get("price") or 0.0)
        if not fill and l.get("txid") in fill_prices:
            fill = float(fill_prices[l["txid"]] or 0.0)
        # Try direct + fuzzy match for ticker keys
        cur = 0.0
        if pair in tickers:
            cur = tickers[pair]
        else:
            for k, v in tickers.items():
                if k.replace("X", "").replace("Z", "").upper() == pair.replace("X", "").replace("Z", "").upper():
                    cur = v; break
        cost = qty * fill if fill else 0.0
        val  = qty * cur if cur else 0.0
        upnl = (val - cost) if (cost and val) else 0.0
        upnl_pct = ((cur - fill) / fill * 100.0) if fill and cur else 0.0
        cost_total  += cost
        value_total += val
        enriched.append({
            "pair": pair,
            "qty": qty,
            "fill_price": fill,
            "current_price": cur,
            "cost_usd":  round(cost, 4),
            "value_usd": round(val, 4),
            "upnl_usd":  round(upnl, 4),
            "upnl_pct":  round(upnl_pct, 4),
            "txid": l.get("txid"),
            "controller": l.get("controller"),
            "ts": l.get("ts"),
            "fill_price_source": "kraken_query_orders" if (fill_prices.get(l.get("txid")) and not l.get("price")) else "ledger",
        })
    enriched.sort(key=lambda r: -r["value_usd"])
    upnl_total = value_total - cost_total
    return {
        "ok": True,
        "ts": now_utc(),
        "lots": enriched,
        "totals": {
            "cost_usd": round(cost_total, 4),
            "value_usd": round(value_total, 4),
            "upnl_usd":  round(upnl_total, 4),
            "upnl_pct":  round((upnl_total / cost_total * 100.0) if cost_total else 0.0, 4),
        },
    }


# Cached fill-price store: txid -> {"price": float, "ts": iso, "vol_exec": float}
_KRAKEN_FILL_CACHE_FILE = ROOT / "kraken_fill_prices.json"
_KRAKEN_FILL_CACHE: dict[str, dict[str, Any]] | None = None


def _load_fill_cache() -> dict[str, dict[str, Any]]:
    global _KRAKEN_FILL_CACHE
    if _KRAKEN_FILL_CACHE is not None:
        return _KRAKEN_FILL_CACHE
    if _KRAKEN_FILL_CACHE_FILE.exists():
        try:
            _KRAKEN_FILL_CACHE = json.loads(_KRAKEN_FILL_CACHE_FILE.read_text(encoding="utf-8"))
            if not isinstance(_KRAKEN_FILL_CACHE, dict):
                _KRAKEN_FILL_CACHE = {}
        except Exception:
            _KRAKEN_FILL_CACHE = {}
    else:
        _KRAKEN_FILL_CACHE = {}
    return _KRAKEN_FILL_CACHE


def _save_fill_cache() -> None:
    cache = _load_fill_cache()
    try:
        _KRAKEN_FILL_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass


def _kraken_query_orders(txids: list[str]) -> dict[str, Any]:
    api_key, api_secret = _load_kraken_keys()
    if not api_key or not api_secret or not txids:
        return {}
    urlpath = "/0/private/QueryOrders"
    data = {
        "nonce": str(time.time_ns()),
        "txid": ",".join(txids[:20]),  # Kraken accepts up to 20
    }
    headers = {
        "API-Key": api_key,
        "API-Sign": _kraken_sign(api_secret, urlpath, data),
    }
    try:
        r = _requests_appr.post("https://api.kraken.com" + urlpath, data=data, headers=headers, timeout=12)
        return r.json()
    except Exception:
        return {}


def _resolve_fill_prices(txids: list[str]) -> dict[str, float]:
    """Return {txid: fill_price}. Uses on-disk cache first; falls back to
    Kraken /0/private/QueryOrders for any missing TXIDs and persists results."""
    cache = _load_fill_cache()
    out: dict[str, float] = {}
    missing: list[str] = []
    for tx in txids:
        if not tx:
            continue
        c = cache.get(tx)
        if c and c.get("price"):
            out[tx] = float(c["price"])
        else:
            missing.append(tx)
    if missing:
        resp = _kraken_query_orders(missing)
        result = (resp or {}).get("result") or {}
        for tx, info in result.items():
            try:
                # Kraken returns 'price' (avg fill px) and 'vol_exec'
                px = float(info.get("price") or info.get("avg_price") or 0.0)
                if not px:
                    # market order: use 'cost' / 'vol_exec'
                    cost = float(info.get("cost") or 0.0)
                    vol  = float(info.get("vol_exec") or 0.0)
                    px = (cost / vol) if vol else 0.0
                if px:
                    cache[tx] = {
                        "price": px,
                        "vol_exec": float(info.get("vol_exec") or 0.0),
                        "cost": float(info.get("cost") or 0.0),
                        "fee":  float(info.get("fee") or 0.0),
                        "status": info.get("status"),
                        "resolved_utc": now_utc(),
                    }
                    out[tx] = px
            except Exception:
                continue
        _save_fill_cache()
    return out


# Track sampler heartbeat for the UI ("samples · 1/min · last @ HH:MM:SSZ")
_KRAKEN_SAMPLER_STATE: dict[str, Any] = {
    "interval_s": 60,
    "started_utc": None,
    "last_sample_utc": None,
    "last_ok": None,
    "samples_taken": 0,
    "fast_until_ts": 0.0,   # epoch seconds; while now < this, sampler runs every 5s
}


@app.get("/api/kraken/sampler/status")
def api_kraken_sampler_status() -> dict[str, Any]:
    s = dict(_KRAKEN_SAMPLER_STATE)
    s["fast_mode_active"] = time.time() < float(s.get("fast_until_ts") or 0)
    s["effective_interval_s"] = 5 if s["fast_mode_active"] else s.get("interval_s", 60)
    return s


@app.post("/api/kraken/sampler/fast")
def api_kraken_sampler_fast(seconds: int = 120) -> dict[str, Any]:
    """Switch the equity sampler into 5s mode for `seconds` seconds (default 2 min)
    so the curve grows visibly during a demo or after a fresh order."""
    seconds = max(10, min(seconds, 1800))  # clamp 10s..30min
    _KRAKEN_SAMPLER_STATE["fast_until_ts"] = time.time() + seconds
    return {"ok": True, "fast_until_ts": _KRAKEN_SAMPLER_STATE["fast_until_ts"], "duration_s": seconds}


# =============================================================================
# PROFIT LOCK — auto-sell-ticket creator for the small-wins-compound game.
# Pure crypto reality: a +20% open lot is meaningless until you sell. This
# module watches /api/kraken/unrealized and creates SELL approval tickets when
# (a) a lot crosses a per-tier take-profit threshold, OR
# (b) a trailing stop fires after a peak gain has been registered.
# Backtest finding (out/backtest/score_buckets.csv) — score 0-20 has the best
# 24h win rate (54.27%) — so we lean LIGHT on size and FAST on profit-taking
# instead of waiting for fat tails that rarely appear.
# =============================================================================

PROFIT_LOCK_FILE = ROOT / "config" / "profit_lock.json"
PROFIT_LOCK_PEAKS_FILE = ROOT / "profit_lock_peaks.json"

PROFIT_LOCK_DEFAULT = {
    "enabled": False,                # auto-create OFF until user opts in
    "min_notional_usd": 5.0,         # don't bother below $5 lots
    # Take-profit ladder. First match wins; sells the whole lot.
    # Honest small-win economics: +1.5% covers Kraken round-trip fee (~0.52% taker x2 = ~1.04%) + slippage with margin.
    "tp_ladder_pct": [1.5, 3.0, 6.0, 12.0],
    # Default: lock in profit at the first ladder rung that triggers.
    "default_tp_pct": 1.5,
    # Trailing stop: arm once gain exceeds arm_pct, exit if drops by give_back_pct from peak.
    "trail_arm_pct": 4.0,
    "trail_give_back_pct": 1.5,
    # Hard stop: emergency exit if a lot drops more than this from entry.
    "hard_stop_pct": -8.0,
    # Per-pair cooldown so we don't spam tickets for the same lot.
    "ticket_cooldown_s": 600,
    # Watcher cadence
    "scan_interval_s": 30,
}


def _load_profit_lock_cfg() -> dict[str, Any]:
    cfg = dict(PROFIT_LOCK_DEFAULT)
    try:
        if PROFIT_LOCK_FILE.exists():
            user = json.loads(PROFIT_LOCK_FILE.read_text(encoding="utf-8"))
            if isinstance(user, dict):
                cfg.update(user)
    except Exception:
        pass
    return cfg


def _save_profit_lock_cfg(cfg: dict[str, Any]) -> None:
    PROFIT_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFIT_LOCK_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _load_peaks() -> dict[str, dict[str, Any]]:
    try:
        if PROFIT_LOCK_PEAKS_FILE.exists():
            d = json.loads(PROFIT_LOCK_PEAKS_FILE.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
    except Exception:
        pass
    return {}


def _save_peaks(peaks: dict[str, dict[str, Any]]) -> None:
    try:
        PROFIT_LOCK_PEAKS_FILE.write_text(json.dumps(peaks, indent=2), encoding="utf-8")
    except Exception:
        pass


def _evaluate_lot_exit(lot: dict[str, Any], cfg: dict[str, Any], peak: dict[str, Any]) -> dict[str, Any]:
    """Return {action: 'hold'|'lock_in'|'trail_stop'|'hard_stop', reason, target_pct}."""
    upnl_pct = float(lot.get("upnl_pct") or 0.0)
    cost = float(lot.get("cost_usd") or 0.0)
    if cost < float(cfg.get("min_notional_usd") or 0):
        return {"action": "skip", "reason": f"notional ${cost:.2f} below floor", "tier": None}

    # Track running peak
    peak_pct = max(float(peak.get("peak_pct") or 0.0), upnl_pct)

    # Hard stop
    hs = float(cfg.get("hard_stop_pct") or -8.0)
    if upnl_pct <= hs:
        return {"action": "hard_stop", "reason": f"uPnL {upnl_pct:.2f}% <= hard_stop {hs}%", "tier": "HARD", "peak_pct": peak_pct}

    # Trailing stop (only if armed by peak)
    arm = float(cfg.get("trail_arm_pct") or 4.0)
    give = float(cfg.get("trail_give_back_pct") or 1.5)
    if peak_pct >= arm and (peak_pct - upnl_pct) >= give:
        return {"action": "trail_stop", "reason": f"peaked {peak_pct:.2f}%, now {upnl_pct:.2f}% (gave back {peak_pct-upnl_pct:.2f}%)", "tier": "TRAIL", "peak_pct": peak_pct}

    # Take-profit ladder — pick the highest rung crossed
    ladder = sorted([float(x) for x in (cfg.get("tp_ladder_pct") or []) if float(x) > 0])
    crossed = [r for r in ladder if upnl_pct >= r]
    if crossed:
        rung = crossed[-1]
        return {"action": "lock_in", "reason": f"uPnL {upnl_pct:.2f}% >= TP rung {rung}%", "tier": f"TP{rung}", "target_pct": rung, "peak_pct": peak_pct}

    return {"action": "hold", "reason": f"uPnL {upnl_pct:.2f}% — waiting", "tier": None, "peak_pct": peak_pct}


def _build_sell_ticket(lot: dict[str, Any], decision: dict[str, Any], note_prefix: str = "profit_lock") -> dict[str, Any]:
    pair = str(lot.get("pair") or "")
    qty = float(lot.get("qty") or 0.0)
    fill = float(lot.get("fill_price") or 0.0)
    cur = float(lot.get("current_price") or 0.0)
    upnl = float(lot.get("upnl_usd") or 0.0)
    upnl_pct = float(lot.get("upnl_pct") or 0.0)
    notional = qty * cur if cur else qty * fill
    # Kraken volume precision varies by pair; round to 8 decimals.
    vol_str = f"{qty:.8f}".rstrip("0").rstrip(".")
    if not vol_str:
        vol_str = "0"
    # Include a short suffix from the source lot txid to guarantee uniqueness when
    # multiple sell tickets are minted in the same millisecond (e.g. lock_in {all:true}).
    src_tx = str(lot.get("txid") or "")
    suffix = src_tx.replace("-", "")[-6:].upper() if src_tx else f"{random.randint(0, 0xFFFF):04X}"
    ticket_id = f"TICKET-SELL-{int(time.time()*1000)}-{suffix}"
    return {
        "ticket_id": ticket_id,
        "timestamp": now_utc(),
        "controller": "Robert",
        "pair": pair,
        "side": "sell",
        "notional_usd": round(notional, 4),
        "volume_base": qty,
        "payload": {
            "pair": pair,
            "type": "sell",
            "ordertype": "market",
            "volume": vol_str,
            "validate": "false",
            "userref": int(time.time()),
        },
        "approval_state": "PENDING_HUMAN_APPROVAL",
        "note": f"{note_prefix} :: {decision.get('tier','?')} :: src_txid={lot.get('txid')} fill={fill:.6f} cur={cur:.6f} uPnL=${upnl:.2f} ({upnl_pct:.2f}%) — {decision.get('reason','')}",
        "source_txid": lot.get("txid"),
        "exit_reason": decision.get("tier"),
        "expected_realized_usd": round(upnl, 4),
        "origin": "profit_lock",
    }


@app.get("/api/sells/config")
def api_sells_config() -> dict[str, Any]:
    return {"ok": True, "config": _load_profit_lock_cfg(), "path": str(PROFIT_LOCK_FILE)}


@app.post("/api/sells/config")
async def api_sells_config_set(request: Request) -> dict[str, Any]:
    body = await request.json()
    if not isinstance(body, dict):
        return {"ok": False, "error": "body must be object"}
    cfg = _load_profit_lock_cfg()
    # Whitelist update
    for k in PROFIT_LOCK_DEFAULT.keys():
        if k in body:
            cfg[k] = body[k]
    _save_profit_lock_cfg(cfg)
    return {"ok": True, "config": cfg}


@app.get("/api/sells/candidates")
def api_sells_candidates() -> dict[str, Any]:
    """Preview profit-lock decisions for every open lot. No tickets created."""
    cfg = _load_profit_lock_cfg()
    upnl = api_kraken_unrealized()
    peaks = _load_peaks()
    rows = []
    actionable = 0
    for lot in upnl.get("lots") or []:
        tx = str(lot.get("txid") or "")
        peak = peaks.get(tx, {})
        decision = _evaluate_lot_exit(lot, cfg, peak)
        # Persist new peak
        new_peak = max(float(peak.get("peak_pct") or 0.0), float(lot.get("upnl_pct") or 0.0))
        peaks[tx] = {"peak_pct": new_peak, "last_seen_utc": now_utc()}
        rows.append({
            "txid": tx,
            "pair": lot.get("pair"),
            "qty": lot.get("qty"),
            "fill_price": lot.get("fill_price"),
            "current_price": lot.get("current_price"),
            "cost_usd": lot.get("cost_usd"),
            "value_usd": lot.get("value_usd"),
            "upnl_usd": lot.get("upnl_usd"),
            "upnl_pct": lot.get("upnl_pct"),
            "peak_pct": round(new_peak, 4),
            "action": decision.get("action"),
            "tier": decision.get("tier"),
            "reason": decision.get("reason"),
            "actionable": decision.get("action") in ("lock_in", "trail_stop", "hard_stop"),
        })
        if decision.get("action") in ("lock_in", "trail_stop", "hard_stop"):
            actionable += 1
    _save_peaks(peaks)
    rows.sort(key=lambda r: (-1 if r["actionable"] else 0, -float(r.get("upnl_pct") or 0)))
    return {
        "ok": True,
        "ts": now_utc(),
        "config": cfg,
        "actionable_count": actionable,
        "candidates": rows,
        "totals": upnl.get("totals"),
    }


@app.post("/api/sells/lock_in")
async def api_sells_lock_in(request: Request) -> dict[str, Any]:
    """Create a SELL approval ticket for a specific lot (by txid) or for ALL
    actionable lots (if body={'all': true})."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    target_txid = str(body.get("txid") or "").strip()
    do_all = bool(body.get("all"))
    force = bool(body.get("force"))   # bypass cooldown / action gate (manual click)

    cfg = _load_profit_lock_cfg()
    cooldown = int(cfg.get("ticket_cooldown_s") or 600)
    upnl = api_kraken_unrealized()
    peaks = _load_peaks()
    queue = _load_approval_queue()

    # Build set of source_txids that already have a fresh PENDING/EXECUTED sell.
    now_ts = time.time()
    recent_by_src: dict[str, float] = {}
    for t in queue:
        if str(t.get("side", "")).lower() != "sell":
            continue
        # Count guard/human rejections toward cooldown to avoid rapid
        # re-emission loops for lots that are not currently executable.
        state = str(t.get("approval_state") or "").upper()
        if state in ("CANCELLED", "EXPIRED"):
            continue
        src = str(t.get("source_txid") or "")
        if not src:
            continue
        try:
            dt = datetime.fromisoformat(str(t.get("timestamp", "")).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age_s = (datetime.now(timezone.utc) - dt).total_seconds()
        except Exception:
            age_s = 1e9
        recent_by_src[src] = min(recent_by_src.get(src, 1e9), age_s)

    balance_snap = api_kraken_balance(force=0)

    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for lot in upnl.get("lots") or []:
        tx = str(lot.get("txid") or "")
        if not do_all and target_txid and tx != target_txid:
            continue
        peak = peaks.get(tx, {})
        decision = _evaluate_lot_exit(lot, cfg, peak)
        if not force and decision.get("action") not in ("lock_in", "trail_stop", "hard_stop"):
            skipped.append({"txid": tx, "reason": f"no-trigger ({decision.get('action')})"})
            continue
        if not force and recent_by_src.get(tx, 1e9) < cooldown:
            skipped.append({"txid": tx, "reason": f"cooldown ({recent_by_src[tx]:.0f}s < {cooldown}s)"})
            continue

        # Skip creating SELL tickets that cannot pass live balance precheck.
        if not force:
            sell_check = _sell_balance_precheck(
                str(lot.get("pair") or ""),
                lot.get("qty"),
                balance_snapshot=balance_snap,
            )
            if not bool(sell_check.get("ok", True)):
                skipped.append(
                    {
                        "txid": tx,
                        "reason": (
                            f"insufficient_base_balance "
                            f"(required={to_float(sell_check.get('required'), 0.0):.8f} "
                            f"available={to_float(sell_check.get('available'), 0.0):.8f})"
                        ),
                    }
                )
                continue

        ticket = _build_sell_ticket(lot, decision, note_prefix="profit_lock_manual" if force else "profit_lock")
        queue.append(ticket)
        created.append(ticket)
        if not do_all and target_txid:
            break

    if created:
        _save_approval_queue(queue)
    return {
        "ok": True,
        "ts": now_utc(),
        "created": created,
        "skipped": skipped,
        "created_count": len(created),
    }


# Background watcher — auto-creates SELL tickets when cfg.enabled is true.
_PROFIT_LOCK_STATE: dict[str, Any] = {
    "started_utc": None,
    "last_scan_utc": None,
    "last_scan_actionable": 0,
    "tickets_created_total": 0,
    "last_decision": None,
}


@app.get("/api/sells/watcher/status")
def api_sells_watcher_status() -> dict[str, Any]:
    s = dict(_PROFIT_LOCK_STATE)
    s["config"] = _load_profit_lock_cfg()
    return s


async def _profit_lock_watcher() -> None:
    _PROFIT_LOCK_STATE["started_utc"] = now_utc()
    while True:
        try:
            cfg = _load_profit_lock_cfg()
            interval = int(cfg.get("scan_interval_s") or 30)
            if not bool(cfg.get("enabled")):
                _PROFIT_LOCK_STATE["last_scan_utc"] = now_utc()
                _PROFIT_LOCK_STATE["last_scan_actionable"] = 0
                await asyncio.sleep(interval)
                continue
            # Scan
            preview = api_sells_candidates()
            actionable = int(preview.get("actionable_count") or 0)
            _PROFIT_LOCK_STATE["last_scan_utc"] = now_utc()
            _PROFIT_LOCK_STATE["last_scan_actionable"] = actionable
            if actionable > 0:
                # Re-use the lock_in path for {'all': true}
                upnl = api_kraken_unrealized()
                peaks = _load_peaks()
                queue = _load_approval_queue()
                balance_snap = api_kraken_balance(force=0)
                cooldown = int(cfg.get("ticket_cooldown_s") or 600)
                recent_by_src: dict[str, float] = {}
                for t in queue:
                    if str(t.get("side", "")).lower() != "sell":
                        continue
                    state = str(t.get("approval_state") or "").upper()
                    if state in ("CANCELLED", "EXPIRED"):
                        continue
                    src = str(t.get("source_txid") or "")
                    if not src:
                        continue
                    try:
                        dt = datetime.fromisoformat(str(t.get("timestamp", "")).replace("Z", "+00:00"))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        age_s = (datetime.now(timezone.utc) - dt).total_seconds()
                    except Exception:
                        age_s = 1e9
                    recent_by_src[src] = min(recent_by_src.get(src, 1e9), age_s)
                created = 0
                for lot in upnl.get("lots") or []:
                    tx = str(lot.get("txid") or "")
                    decision = _evaluate_lot_exit(lot, cfg, peaks.get(tx, {}))
                    if decision.get("action") not in ("lock_in", "trail_stop", "hard_stop"):
                        continue
                    if recent_by_src.get(tx, 1e9) < cooldown:
                        continue

                    sell_check = _sell_balance_precheck(
                        str(lot.get("pair") or ""),
                        lot.get("qty"),
                        balance_snapshot=balance_snap,
                    )
                    if not bool(sell_check.get("ok", True)):
                        continue

                    queue.append(_build_sell_ticket(lot, decision, note_prefix="profit_lock_auto"))
                    created += 1
                    _PROFIT_LOCK_STATE["last_decision"] = {
                        "ts": now_utc(),
                        "txid": tx,
                        "pair": lot.get("pair"),
                        "tier": decision.get("tier"),
                        "reason": decision.get("reason"),
                    }
                if created:
                    _save_approval_queue(queue)
                    _PROFIT_LOCK_STATE["tickets_created_total"] = int(_PROFIT_LOCK_STATE.get("tickets_created_total") or 0) + created
        except Exception as exc:
            _PROFIT_LOCK_STATE["last_error"] = f"{type(exc).__name__}: {exc}"
        await asyncio.sleep(int((_load_profit_lock_cfg().get("scan_interval_s") or 30)))


# =============================================================================
# BEST BUYS NOW — backtest-grounded candidate ranker.
# Reads spike_hunter_latest.json + score_buckets.csv and returns picks tilted
# toward the bucket with the highest verified win rate (score 0-20 = 54.27% @ 24h).
# =============================================================================

SPIKE_HUNTER_LATEST = ROOT / "out" / "spike_hunter" / "spike_hunter_latest.json"
SCORE_BUCKETS_CSV = ROOT / "out" / "backtest" / "score_buckets.csv"

_SCORE_BUCKETS_CACHE: list[dict[str, Any]] | None = None


def _load_score_buckets() -> list[dict[str, Any]]:
    global _SCORE_BUCKETS_CACHE
    if _SCORE_BUCKETS_CACHE is not None:
        return _SCORE_BUCKETS_CACHE
    rows: list[dict[str, Any]] = []
    try:
        if SCORE_BUCKETS_CSV.exists():
            import csv as _csv
            with SCORE_BUCKETS_CSV.open("r", encoding="utf-8") as fh:
                rd = _csv.DictReader(fh)
                for r in rd:
                    try:
                        rows.append({
                            "horizon_h": int(r["horizon_h"]),
                            "score_lo": float(r["score_lo"]),
                            "score_hi": float(r["score_hi"]),
                            "n": int(r["n"]),
                            "mean_pct": float(r["mean_pct"]),
                            "win_rate_pct": float(r["win_rate_pct"]),
                            "sharpe": float(r["sharpe"]),
                        })
                    except Exception:
                        continue
    except Exception:
        pass
    _SCORE_BUCKETS_CACHE = rows
    return rows


def _bucket_for_score(score: float, horizon_h: int = 24) -> dict[str, Any]:
    for b in _load_score_buckets():
        if b["horizon_h"] != horizon_h:
            continue
        if b["score_lo"] <= score < b["score_hi"]:
            return b
    return {"horizon_h": horizon_h, "score_lo": 0, "score_hi": 0, "n": 0, "mean_pct": 0, "win_rate_pct": 0, "sharpe": 0}


@app.get("/api/buys/best")
def api_buys_best(limit: int = 10, horizon_h: int = 24) -> dict[str, Any]:
    """Rank current spike_hunter candidates by their backtested win-probability bucket.
    Surfaces the score bucket each pick falls into so user can SEE which picks
    are statistically supported vs. noise."""
    if not SPIKE_HUNTER_LATEST.exists():
        return {"ok": False, "ts": now_utc(), "error": "no spike_hunter_latest.json", "picks": []}
    try:
        data = json.loads(SPIKE_HUNTER_LATEST.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "error": f"parse: {exc}", "picks": []}
    sigs = data.get("signals") or data.get("results") or data.get("leaderboard") or []
    if not isinstance(sigs, list):
        sigs = []
    picks = []
    for s in sigs:
        # composite/score from various spike_hunter schema versions
        score = float(
            s.get("score")
            or s.get("composite_score")
            or s.get("spike_score")
            or s.get("opportunity_score")
            or 0.0
        )
        bucket = _bucket_for_score(score, horizon_h)
        # Edge score = win_rate * mean_pct * log10(sample_size+1)
        import math as _m
        edge = bucket["win_rate_pct"] / 100.0 * bucket["mean_pct"] * _m.log10(bucket["n"] + 1)
        picks.append({
            "pair": s.get("pair") or s.get("symbol") or s.get("wsname"),
            "score": round(score, 2),
            "classification": s.get("classification") or (",".join(s.get("signals", [])) if isinstance(s.get("signals"), list) else None),
            "current_price": s.get("current_price") or s.get("price"),
            "rsi": s.get("rsi"),
            "vol_surge": s.get("vol_surge") or s.get("volume_surge"),
            "expected_pct": s.get(f"expected_{horizon_h}h_pct") or s.get("expected_24h_pct"),
            "bucket_lo": bucket["score_lo"],
            "bucket_hi": bucket["score_hi"],
            "bucket_n": bucket["n"],
            "bucket_win_rate_pct": bucket["win_rate_pct"],
            "bucket_mean_pct": bucket["mean_pct"],
            "bucket_sharpe": bucket["sharpe"],
            "edge_score": round(edge, 6),
        })
    # Sort by edge_score desc; ties broken by win-rate
    picks.sort(key=lambda p: (-(p["edge_score"] or 0), -(p["bucket_win_rate_pct"] or 0)))
    return {
        "ok": True,
        "ts": now_utc(),
        "horizon_h": horizon_h,
        "spike_hunter_generated_utc": data.get("generated_utc"),
        "spike_hunter_count": len(sigs),
        "picks": picks[:max(1, int(limit))],
        "score_buckets": [b for b in _load_score_buckets() if b["horizon_h"] == horizon_h],
    }


# =============================================================================
# AUTO-BUY watcher — buy-side mirror of Profit Lock.
# Pulls top edge picks from /api/buys/best, sizes by edge_score, and creates
# PENDING_HUMAN_APPROVAL tickets respecting controller caps + a "no rebuy after
# recent loss" guard. OFF by default; user opts in via /api/buys/autobuy/config.
# =============================================================================

AUTOBUY_FILE = ROOT / "config" / "autobuy.json"

AUTOBUY_DEFAULT = {
    "enabled": False,                 # OFF until user opts in
    "max_open_target": 10,            # auto-buy stops once we hit this many open lots
    "max_pending": 4,                 # don't queue more than N pending buy tickets at once
    "min_edge_score": 0.5,            # require edge_score >= this from /api/buys/best
    "min_bucket_n": 5,                # require backtest sample size >= this in bucket
    "min_win_rate_pct": 50.0,         # require bucket win rate >= this
    "base_notional_usd": 12.0,        # baseline bet size
    "edge_size_boost": True,          # tilt size up by edge_score (Kelly-lite, capped)
    "max_notional_usd": 25.0,         # never exceed this per ticket
    "horizon_h": 24,                  # backtest horizon to use
    "loss_cooldown_hours": 2.0,       # don't rebuy a pair we hard-stopped within last N hrs
    "controller": "Robert",
    "scan_interval_s": 60,            # cadence; wider than profit lock so we don't spam
    # ---- god-tier safety + freshness ----
    "daily_loss_floor_usd": -10.0,    # if today's net realized falls below this, AutoBuy auto-disables
    "spike_max_age_minutes": 20,      # if cache older than this, AutoBuy triggers a fresh scan before deciding
}


def _load_autobuy_cfg() -> dict[str, Any]:
    cfg = dict(AUTOBUY_DEFAULT)
    try:
        if AUTOBUY_FILE.exists():
            user = json.loads(AUTOBUY_FILE.read_text(encoding="utf-8"))
            if isinstance(user, dict):
                cfg.update(user)
    except Exception:
        pass
    return cfg


def _save_autobuy_cfg(cfg: dict[str, Any]) -> None:
    AUTOBUY_FILE.parent.mkdir(parents=True, exist_ok=True)
    AUTOBUY_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


_AUTOBUY_STATE: dict[str, Any] = {
    "started_utc": None,
    "last_scan_utc": None,
    "last_scan_eligible": 0,
    "tickets_created_total": 0,
    "last_decision": None,
    "circuit_breaker_tripped": False,    # true when daily loss floor pierced
    "circuit_breaker_reason": None,
    "circuit_breaker_ts": None,
    "spike_refresh_count": 0,            # auto-refreshes triggered by stale-cache gate
    "last_spike_refresh_utc": None,
}


def _recently_stopped_pairs(window_hours: float) -> dict[str, str]:
    """Return {pair: reason} for pairs whose most recent EXECUTED sell was a
    hard_stop within the last `window_hours`. We don't want to immediately
    rebuy a falling knife."""
    out: dict[str, str] = {}
    try:
        queue = _load_approval_queue()
    except Exception:
        return out
    cutoff = datetime.now(timezone.utc).timestamp() - window_hours * 3600.0
    for t in queue:
        if str(t.get("side", "")).lower() != "sell":
            continue
        if str(t.get("approval_state", "")).upper() != "EXECUTED_OPEN":
            continue
        note = str(t.get("note") or "")
        # _build_sell_ticket bakes the tier/reason into the note (e.g. "profit_lock HARD: ...")
        if "HARD" not in note.upper() and "hard_stop" not in note:
            continue
        try:
            dt = datetime.fromisoformat(str(t.get("timestamp", "")).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ts = dt.timestamp()
        except Exception:
            continue
        if ts < cutoff:
            continue
        pair = str(t.get("pair") or "")
        if pair:
            out[pair] = note[:80]
    return out


def _build_buy_ticket(pick: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any] | None:
    pair = str(pick.get("pair") or "")
    price = float(pick.get("current_price") or 0.0)
    if not pair or price <= 0:
        return None
    base = float(cfg.get("base_notional_usd") or 12.0)
    notional = base
    if bool(cfg.get("edge_size_boost", True)):
        edge = max(0.0, float(pick.get("edge_score") or 0.0))
        # Kelly-lite multiplier: 1.0..2.0 over edge range 0..2
        mult = 1.0 + min(1.0, edge / 2.0)
        notional = base * mult
    notional = min(float(cfg.get("max_notional_usd") or 25.0), max(5.0, notional))
    volume_base = notional / price
    if volume_base <= 0:
        return None
    vol_str = f"{volume_base:.8f}".rstrip("0").rstrip(".") or "0"
    suffix = pair.replace("/", "")[-6:].upper() or f"{random.randint(0, 0xFFFF):04X}"
    ticket_id = f"TICKET-AUTOBUY-{int(time.time()*1000)}-{suffix}"
    note = (
        f"autobuy: edge={pick.get('edge_score')} wr={pick.get('bucket_win_rate_pct')}% "
        f"mean={pick.get('bucket_mean_pct')}% n={pick.get('bucket_n')} score={pick.get('score')}"
    )
    return {
        "ticket_id": ticket_id,
        "timestamp": now_utc(),
        "controller": str(cfg.get("controller") or "Robert"),
        "pair": pair,
        "side": "buy",
        "notional_usd": round(notional, 4),
        "volume_base": volume_base,
        "payload": {
            "pair": pair,
            "type": "buy",
            "ordertype": "market",
            "volume": vol_str,
            "validate": "false",
            "userref": int(time.time()),
        },
        "approval_state": "PENDING_HUMAN_APPROVAL",
        "note": note,
        "scanner_meta": {
            "source": "autobuy_v1",
            "edge_score": pick.get("edge_score"),
            "bucket_win_rate_pct": pick.get("bucket_win_rate_pct"),
            "bucket_mean_pct": pick.get("bucket_mean_pct"),
            "bucket_n": pick.get("bucket_n"),
            "score": pick.get("score"),
            "rsi": pick.get("rsi"),
            "vol_surge": pick.get("vol_surge"),
        },
    }


def _autobuy_eligible_picks(cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter /api/buys/best picks against config thresholds. Returns (eligible, skipped)."""
    horizon_h = int(cfg.get("horizon_h") or 24)
    best = api_buys_best(limit=20, horizon_h=horizon_h)
    picks = best.get("picks") or []
    min_edge = float(cfg.get("min_edge_score") or 0.0)
    min_n = int(cfg.get("min_bucket_n") or 0)
    min_wr = float(cfg.get("min_win_rate_pct") or 0.0)
    eligible: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for p in picks:
        edge = float(p.get("edge_score") or 0.0)
        n = int(p.get("bucket_n") or 0)
        wr = float(p.get("bucket_win_rate_pct") or 0.0)
        why = None
        if edge < min_edge:
            why = f"edge {edge:.3f} < {min_edge}"
        elif n < min_n:
            why = f"n={n} < {min_n}"
        elif wr < min_wr:
            why = f"wr {wr:.1f}% < {min_wr}%"
        if why:
            skipped.append({"pair": p.get("pair"), "reason": why})
        else:
            eligible.append(p)
    return eligible, skipped


def _maybe_refresh_spike_cache(max_age_minutes: float) -> dict[str, Any]:
    """If spike_hunter_latest.json is older than `max_age_minutes`, kick a
    background scan (no-op if scan is already running). Returns status dict."""
    info: dict[str, Any] = {"refreshed": False, "age_minutes": None, "running": False}
    try:
        if SPIKE_HUNTER_LATEST.exists():
            age_s = time.time() - SPIKE_HUNTER_LATEST.stat().st_mtime
            info["age_minutes"] = round(age_s / 60.0, 2)
            if age_s / 60.0 < max(1.0, float(max_age_minutes)):
                return info
        # Stale or missing — try to launch refresh
        lock = ROOT / "run" / "spike_hunter_running.lock"
        if lock.exists():
            try:
                if (time.time() - lock.stat().st_mtime) < 300:
                    info["running"] = True
                    return info
            except Exception:
                pass
            lock.unlink(missing_ok=True)
        script = CODE / "kraken_spike_hunter_live.py"
        if not script.exists():
            info["error"] = "spike script missing"
            return info
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.touch()
        stderr_log = open(str(ROOT / "run" / "spike_hunter_stderr.log"), "w")
        subprocess.Popen(
            [sys.executable, str(script), "150"],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=stderr_log,
        )
        info["refreshed"] = True
        _AUTOBUY_STATE["spike_refresh_count"] = int(_AUTOBUY_STATE.get("spike_refresh_count") or 0) + 1
        _AUTOBUY_STATE["last_spike_refresh_utc"] = now_utc()
    except Exception as exc:
        info["error"] = str(exc)[:200]
    return info


# =============================================================================
# SMART SCANNER SERVICE — dedicated background scanner that continuously
# refreshes scan intelligence while execution workers are running.
# =============================================================================

SMART_SCANNER_FILE = ROOT / "config" / "smart_scanner.json"
SMART_SCANNER_ALPHA_LOG = ROOT / "run" / "smart_scanner_alpha.log"

SMART_SCANNER_DEFAULT = {
    "enabled": True,
    "scan_interval_s": 30,
    "spike_enabled": True,
    "spike_max_age_minutes": 8.0,
    "alpha_enabled": True,
    "alpha_max_age_minutes": 30.0,
    "alpha_quotes": "ZUSD,USDT",
    "alpha_top_liquid": 711,
    "alpha_limit": 711,
    "alpha_min_turnover_usd": 0.0,
    "alpha_max_spread_bps": 10000.0,
    "alpha_spike_threshold_pct": 3.0,
}

_SMART_SCANNER_STATE: dict[str, Any] = {
    "started_utc": None,
    "last_tick_utc": None,
    "last_error": None,
    "last_spike_scan_utc": None,
    "last_spike_status": None,
    "last_alpha_scan_utc": None,
    "last_alpha_status": None,
    "last_alpha_completed_utc": None,
    "last_alpha_success_utc": None,
    "last_alpha_exit_code": None,
    "spike_refresh_count": 0,
    "alpha_refresh_count": 0,
    "alpha_running": False,
}

_SMART_SCANNER_ALPHA_PROC: Any = None
_SMART_SCANNER_ALPHA_LOG_FH: Any = None


def _load_smart_scanner_cfg() -> dict[str, Any]:
    cfg = dict(SMART_SCANNER_DEFAULT)
    try:
        if SMART_SCANNER_FILE.exists():
            user = json.loads(SMART_SCANNER_FILE.read_text(encoding="utf-8"))
            if isinstance(user, dict):
                cfg.update(user)
    except Exception:
        pass
    return cfg


def _save_smart_scanner_cfg(cfg: dict[str, Any]) -> None:
    SMART_SCANNER_FILE.parent.mkdir(parents=True, exist_ok=True)
    SMART_SCANNER_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _latest_alpha_map_path() -> Path | None:
    candidates = [
        KRAKEN_ALPHA_MAP_FILE,
        KRAKEN_ALPHA_MAP_FILE_STACK_FALLBACK,
    ]
    existing: list[Path] = []
    for cand in candidates:
        try:
            if cand.exists():
                existing.append(cand)
        except Exception:
            continue
    if not existing:
        return None
    try:
        return max(existing, key=lambda p: p.stat().st_mtime)
    except Exception:
        return existing[0]


def _latest_alpha_map_age_minutes() -> float | None:
    path = _latest_alpha_map_path()
    if path is None:
        return None
    try:
        age_s = max(0.0, time.time() - path.stat().st_mtime)
        return round(age_s / 60.0, 3)
    except Exception:
        return None


def _read_latest_alpha_map_summary() -> dict[str, Any]:
    path = _latest_alpha_map_path()
    if path is None:
        return {"available": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "available": True,
            "path": str(path),
            "generated_utc": payload.get("generated_utc"),
            "pairs_discovered": payload.get("pairs_discovered"),
            "pairs_after_liquidity_filter": payload.get("pairs_after_liquidity_filter"),
            "pairs_analyzed": payload.get("pairs_analyzed"),
            "pair_errors": payload.get("pair_errors"),
            "age_minutes": _latest_alpha_map_age_minutes(),
        }
    except Exception as exc:
        return {
            "available": False,
            "path": str(path),
            "error": str(exc)[:200],
            "age_minutes": _latest_alpha_map_age_minutes(),
        }


def _poll_alpha_scan_process() -> None:
    global _SMART_SCANNER_ALPHA_PROC
    global _SMART_SCANNER_ALPHA_LOG_FH
    proc = _SMART_SCANNER_ALPHA_PROC
    if proc is None:
        _SMART_SCANNER_STATE["alpha_running"] = False
        return

    try:
        rc = proc.poll()
    except Exception as exc:
        _SMART_SCANNER_STATE["alpha_running"] = False
        _SMART_SCANNER_STATE["last_error"] = f"alpha_poll_error: {str(exc)[:200]}"
        _SMART_SCANNER_ALPHA_PROC = None
        return

    if rc is None:
        _SMART_SCANNER_STATE["alpha_running"] = True
        return

    _SMART_SCANNER_STATE["alpha_running"] = False
    _SMART_SCANNER_STATE["last_alpha_completed_utc"] = now_utc()
    _SMART_SCANNER_STATE["last_alpha_exit_code"] = int(rc)
    if int(rc) == 0:
        _SMART_SCANNER_STATE["last_alpha_success_utc"] = now_utc()
        _SMART_SCANNER_STATE["last_alpha_status"] = {
            "state": "completed",
            "exit_code": int(rc),
            "summary": _read_latest_alpha_map_summary(),
        }
    else:
        _SMART_SCANNER_STATE["last_error"] = f"alpha_scan_exit_code={int(rc)}"
        _SMART_SCANNER_STATE["last_alpha_status"] = {
            "state": "failed",
            "exit_code": int(rc),
        }
    _SMART_SCANNER_ALPHA_PROC = None
    try:
        if _SMART_SCANNER_ALPHA_LOG_FH is not None:
            _SMART_SCANNER_ALPHA_LOG_FH.close()
    except Exception:
        pass
    _SMART_SCANNER_ALPHA_LOG_FH = None


def _start_alpha_scan(cfg: dict[str, Any], reason: str) -> dict[str, Any]:
    global _SMART_SCANNER_ALPHA_PROC
    global _SMART_SCANNER_ALPHA_LOG_FH
    _poll_alpha_scan_process()
    if _SMART_SCANNER_ALPHA_PROC is not None:
        return {"started": False, "running": True, "reason": "already_running"}

    script = CODE / "ops" / "build_kraken_multi_tf_alpha_map.py"
    if not script.exists():
        return {"started": False, "running": False, "reason": "script_missing", "path": str(script)}

    top_liquid = max(1, int(to_float(cfg.get("alpha_top_liquid"), 711)))
    limit = max(1, int(to_float(cfg.get("alpha_limit"), 711)))
    min_turnover = float(to_float(cfg.get("alpha_min_turnover_usd"), 0.0))
    max_spread = float(to_float(cfg.get("alpha_max_spread_bps"), 10000.0))
    spike_threshold = float(to_float(cfg.get("alpha_spike_threshold_pct"), 3.0))
    quotes = str(cfg.get("alpha_quotes") or "ZUSD,USDT").strip() or "ZUSD,USDT"

    SMART_SCANNER_ALPHA_LOG.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(script),
        "--stack-root",
        str(ROOT),
        "--quotes",
        quotes,
        "--top-liquid",
        str(top_liquid),
        "--limit",
        str(limit),
        "--min-turnover-usd",
        str(min_turnover),
        "--max-spread-bps",
        str(max_spread),
        "--spike-threshold-pct",
        str(spike_threshold),
    ]

    try:
        try:
            if _SMART_SCANNER_ALPHA_LOG_FH is not None:
                _SMART_SCANNER_ALPHA_LOG_FH.close()
        except Exception:
            pass
        _SMART_SCANNER_ALPHA_LOG_FH = open(str(SMART_SCANNER_ALPHA_LOG), "a", encoding="utf-8")
        _SMART_SCANNER_ALPHA_PROC = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=_SMART_SCANNER_ALPHA_LOG_FH,
            stderr=_SMART_SCANNER_ALPHA_LOG_FH,
        )
        _SMART_SCANNER_STATE["alpha_running"] = True
        _SMART_SCANNER_STATE["last_alpha_scan_utc"] = now_utc()
        _SMART_SCANNER_STATE["alpha_refresh_count"] = int(_SMART_SCANNER_STATE.get("alpha_refresh_count") or 0) + 1
        _SMART_SCANNER_STATE["last_alpha_status"] = {
            "state": "started",
            "reason": reason,
            "cmd": cmd,
        }
        return {
            "started": True,
            "running": True,
            "reason": reason,
            "cmd": cmd,
        }
    except Exception as exc:
        _SMART_SCANNER_STATE["alpha_running"] = False
        _SMART_SCANNER_STATE["last_error"] = f"alpha_start_error: {str(exc)[:200]}"
        return {
            "started": False,
            "running": False,
            "reason": "start_failed",
            "error": str(exc)[:200],
        }


def _smart_scanner_tick(force: bool = False, run_spike: bool = True, run_alpha: bool = True) -> dict[str, Any]:
    cfg = _load_smart_scanner_cfg()
    _poll_alpha_scan_process()
    interval = max(10, int(to_float(cfg.get("scan_interval_s"), 30)))
    _SMART_SCANNER_STATE["last_tick_utc"] = now_utc()

    if not bool(cfg.get("enabled", True)) and not force:
        return {
            "ok": True,
            "enabled": False,
            "effective_interval_s": interval,
            "spike": {"skipped": "disabled"},
            "alpha": {"skipped": "disabled"},
        }

    spike_status: dict[str, Any] = {"skipped": "not_requested"}
    alpha_status: dict[str, Any] = {"skipped": "not_requested"}

    if run_spike and bool(cfg.get("spike_enabled", True)):
        spike_status = _maybe_refresh_spike_cache(float(to_float(cfg.get("spike_max_age_minutes"), 8.0)))
        if bool(spike_status.get("refreshed")):
            _SMART_SCANNER_STATE["spike_refresh_count"] = int(_SMART_SCANNER_STATE.get("spike_refresh_count") or 0) + 1
            _SMART_SCANNER_STATE["last_spike_scan_utc"] = now_utc()
        _SMART_SCANNER_STATE["last_spike_status"] = spike_status

    if run_alpha and bool(cfg.get("alpha_enabled", True)):
        alpha_age_minutes = _latest_alpha_map_age_minutes()
        max_age_minutes = float(to_float(cfg.get("alpha_max_age_minutes"), 30.0))
        due = force or (alpha_age_minutes is None) or (alpha_age_minutes >= max_age_minutes)
        if due:
            alpha_status = _start_alpha_scan(cfg, reason="force" if force else "stale_or_missing")
        else:
            alpha_status = {
                "started": False,
                "running": bool(_SMART_SCANNER_STATE.get("alpha_running")),
                "reason": "fresh_cache",
                "age_minutes": alpha_age_minutes,
                "max_age_minutes": max_age_minutes,
            }
        _SMART_SCANNER_STATE["last_alpha_status"] = alpha_status

    return {
        "ok": True,
        "enabled": bool(cfg.get("enabled", True)),
        "effective_interval_s": interval,
        "spike": spike_status,
        "alpha": alpha_status,
    }


@app.get("/api/scanner/smart/config")
def api_smart_scanner_get_config() -> dict[str, Any]:
    return {
        "ok": True,
        "config": _load_smart_scanner_cfg(),
        "path": str(SMART_SCANNER_FILE),
    }


@app.post("/api/scanner/smart/config")
async def api_smart_scanner_set_config(req: Request) -> dict[str, Any]:
    body = await req.json()
    if not isinstance(body, dict):
        return {"ok": False, "error": "expected JSON object"}
    cfg = _load_smart_scanner_cfg()
    for key in SMART_SCANNER_DEFAULT.keys():
        if key in body:
            cfg[key] = body[key]
    _save_smart_scanner_cfg(cfg)
    return {"ok": True, "config": cfg}


@app.post("/api/scanner/smart/run")
async def api_smart_scanner_run(req: Request) -> dict[str, Any]:
    body: dict[str, Any] = {}
    try:
        body = await req.json()
    except Exception:
        body = {}
    force = bool(body.get("force", True))
    run_spike = bool(body.get("run_spike", True))
    run_alpha = bool(body.get("run_alpha", True))
    return {
        "ok": True,
        "ts": now_utc(),
        "result": _smart_scanner_tick(force=force, run_spike=run_spike, run_alpha=run_alpha),
    }


@app.get("/api/scanner/smart/status")
def api_smart_scanner_status() -> dict[str, Any]:
    _poll_alpha_scan_process()
    cfg = _load_smart_scanner_cfg()
    alpha_summary = _read_latest_alpha_map_summary()
    return {
        "ok": True,
        "ts": now_utc(),
        "config": cfg,
        "state": dict(_SMART_SCANNER_STATE),
        "alpha_latest": alpha_summary,
        "spike_latest": {
            "path": str(SPIKE_HUNTER_LATEST),
            "exists": bool(SPIKE_HUNTER_LATEST.exists()),
            "age_minutes": (
                round((time.time() - SPIKE_HUNTER_LATEST.stat().st_mtime) / 60.0, 3)
                if SPIKE_HUNTER_LATEST.exists()
                else None
            ),
        },
    }


async def _smart_scanner_watcher() -> None:
    _SMART_SCANNER_STATE["started_utc"] = now_utc()
    await asyncio.sleep(6.0)
    while True:
        sleep_s = 30
        try:
            tick = _smart_scanner_tick(force=False, run_spike=True, run_alpha=True)
            sleep_s = max(10, int(tick.get("effective_interval_s") or 30))
        except Exception as exc:
            _SMART_SCANNER_STATE["last_error"] = f"watcher_error: {str(exc)[:200]}"
        await asyncio.sleep(sleep_s)


def _check_circuit_breaker(cfg: dict[str, Any]) -> dict[str, Any]:
    """Disable AutoBuy if today's net realized falls below the configured floor.
    Returns the status dict; mutates _AUTOBUY_STATE on trip."""
    floor = cfg.get("daily_loss_floor_usd")
    if floor is None:
        return {"tripped": False, "reason": "no floor configured"}
    try:
        floor = float(floor)
    except Exception:
        return {"tripped": False, "reason": "invalid floor"}
    try:
        perf = api_perf_session()
        # Prefer rolling 24h if today UTC is empty (post-midnight)
        s = perf.get("session", {}) or {}
        net = s.get("realized_pnl_net_usd")
        scope = "today_utc"
        if (s.get("sells_count") or 0) == 0:
            net = (perf.get("last_24h", {}) or {}).get("realized_pnl_net_usd")
            scope = "last_24h"
        if net is None:
            return {"tripped": False, "reason": "no perf data"}
        if float(net) <= floor:
            cfg2 = _load_autobuy_cfg()
            if cfg2.get("enabled"):
                cfg2["enabled"] = False
                _save_autobuy_cfg(cfg2)
            _AUTOBUY_STATE["circuit_breaker_tripped"] = True
            _AUTOBUY_STATE["circuit_breaker_reason"] = f"{scope} net ${net:.2f} <= floor ${floor:.2f}"
            _AUTOBUY_STATE["circuit_breaker_ts"] = now_utc()
            return {"tripped": True, "scope": scope, "net_usd": float(net), "floor_usd": floor}
        else:
            # If we previously tripped but conditions recovered, surface the cleared state
            if _AUTOBUY_STATE.get("circuit_breaker_tripped"):
                _AUTOBUY_STATE["circuit_breaker_reason"] = (
                    f"cleared @ {now_utc()}; was: {_AUTOBUY_STATE.get('circuit_breaker_reason')}"
                )
            return {"tripped": False, "scope": scope, "net_usd": float(net), "floor_usd": floor}
    except Exception as exc:
        return {"tripped": False, "error": str(exc)[:200]}


def _autobuy_scan_once(force: bool = False) -> dict[str, Any]:
    """Single auto-buy pass. Honors caps, dedupes, respects loss cooldown.

    Now also: (1) refreshes spike cache if stale, (2) checks the equity-floor
    circuit breaker BEFORE creating any tickets."""
    cfg = _load_autobuy_cfg()
    if not force and not bool(cfg.get("enabled", False)):
        return {"ok": True, "skipped_all": "disabled", "created": [], "skipped": []}

    # --- Equity-floor circuit breaker (god-tier safety) ---
    breaker = _check_circuit_breaker(cfg)
    if breaker.get("tripped") and not force:
        return {
            "ok": True,
            "ts": now_utc(),
            "skipped_all": "circuit_breaker_tripped",
            "circuit_breaker": breaker,
            "created": [],
            "skipped": [],
        }

    # --- Spike cache freshness gate ---
    spike_status = _maybe_refresh_spike_cache(float(cfg.get("spike_max_age_minutes") or 20))
    if spike_status.get("refreshed") or spike_status.get("running"):
        # Don't make a decision on stale data this tick — let the next scan use fresh signals
        _AUTOBUY_STATE["last_scan_utc"] = now_utc()
        _AUTOBUY_STATE["last_scan_eligible"] = 0
        return {
            "ok": True,
            "ts": now_utc(),
            "skipped_all": "spike_cache_refreshing",
            "spike_cache": spike_status,
            "circuit_breaker": breaker,
            "created": [],
            "skipped": [],
        }

    # Slot accounting
    queue = _load_approval_queue()
    pending_buys = [t for t in queue if str(t.get("side", "")).lower() == "buy"
                    and str(t.get("approval_state", "")).upper() == "PENDING_HUMAN_APPROVAL"]
    open_lots: list[dict[str, Any]] = []
    try:
        upnl = api_kraken_unrealized()
        open_lots = upnl.get("lots") or []
    except Exception:
        pass
    held_pairs = {str(l.get("pair") or "") for l in open_lots}
    pending_pairs = {str(t.get("pair") or "") for t in pending_buys}

    max_pending = int(cfg.get("max_pending") or 4)
    max_open_target = int(cfg.get("max_open_target") or 10)
    pending_slots = max(0, max_pending - len(pending_buys))
    open_slots = max(0, max_open_target - len(open_lots))
    slots = min(pending_slots, open_slots)

    # Loss cooldown
    cooldown_pairs = _recently_stopped_pairs(float(cfg.get("loss_cooldown_hours") or 2.0))

    eligible, edge_skipped = _autobuy_eligible_picks(cfg)
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = list(edge_skipped)

    for p in eligible:
        if slots <= 0:
            skipped.append({"pair": p.get("pair"), "reason": "slots_full"})
            continue
        pair = str(p.get("pair") or "")
        if pair in held_pairs:
            skipped.append({"pair": pair, "reason": "already_held"})
            continue
        if pair in pending_pairs:
            skipped.append({"pair": pair, "reason": "already_pending"})
            continue
        if pair in cooldown_pairs:
            skipped.append({"pair": pair, "reason": f"loss_cooldown ({cooldown_pairs[pair][:40]})"})
            continue
        ticket = _build_buy_ticket(p, cfg)
        if not ticket:
            skipped.append({"pair": pair, "reason": "build_failed"})
            continue
        queue.append(ticket)
        created.append(ticket)
        pending_pairs.add(pair)
        slots -= 1

    if created:
        _save_approval_queue(queue)
        _AUTOBUY_STATE["tickets_created_total"] = int(_AUTOBUY_STATE.get("tickets_created_total") or 0) + len(created)
        _AUTOBUY_STATE["last_decision"] = {
            "ts": now_utc(),
            "pairs": [t["pair"] for t in created],
            "count": len(created),
        }

    _AUTOBUY_STATE["last_scan_utc"] = now_utc()
    _AUTOBUY_STATE["last_scan_eligible"] = len(eligible)

    return {
        "ok": True,
        "ts": now_utc(),
        "enabled": bool(cfg.get("enabled", False)),
        "open_lots": len(open_lots),
        "pending_buys": len(pending_buys) + len(created),
        "slots_used": len(created),
        "slots_remaining": max(0, slots),
        "created": [
            {
                "ticket_id": t["ticket_id"],
                "pair": t["pair"],
                "notional_usd": t["notional_usd"],
                "edge": t["scanner_meta"].get("edge_score"),
            } for t in created
        ],
        "skipped": skipped[:30],
        "loss_cooldown_pairs": list(cooldown_pairs.keys()),
    }


@app.get("/api/buys/autobuy/config")
def api_autobuy_get_config() -> dict[str, Any]:
    return {"ok": True, "config": _load_autobuy_cfg(), "path": str(AUTOBUY_FILE)}


@app.post("/api/buys/autobuy/config")
async def api_autobuy_set_config(req: Request) -> dict[str, Any]:
    body = await req.json()
    if not isinstance(body, dict):
        return {"ok": False, "error": "expected JSON object"}
    cfg = _load_autobuy_cfg()
    for k in AUTOBUY_DEFAULT.keys():
        if k in body:
            cfg[k] = body[k]
    _save_autobuy_cfg(cfg)
    return {"ok": True, "config": cfg}


@app.post("/api/buys/autobuy/run")
async def api_autobuy_run(req: Request) -> dict[str, Any]:
    """Manual one-shot auto-buy scan. Honors `force=true` to ignore the enabled flag."""
    body: dict[str, Any] = {}
    try:
        body = await req.json()
    except Exception:
        body = {}
    return _autobuy_scan_once(force=bool(body.get("force", False)))


@app.get("/api/buys/autobuy/status")
def api_autobuy_status() -> dict[str, Any]:
    cfg = _load_autobuy_cfg()
    # Compute "best available edge" snapshot vs. thresholds — tells the user
    # at a glance why AutoBuy isn't firing.
    best_summary: dict[str, Any] = {}
    try:
        best = api_buys_best(limit=20, horizon_h=int(cfg.get("horizon_h") or 24))
        picks = best.get("picks") or []
        if picks:
            min_edge = float(cfg.get("min_edge_score") or 0.0)
            min_n = int(cfg.get("min_bucket_n") or 0)
            min_wr = float(cfg.get("min_win_rate_pct") or 0.0)
            top = picks[0]
            top_edge = float(top.get("edge_score") or 0.0)
            top_wr = float(top.get("bucket_win_rate_pct") or 0.0)
            top_n = int(top.get("bucket_n") or 0)
            blockers = []
            if top_edge < min_edge:
                blockers.append(f"top edge {top_edge:.3f} < {min_edge}")
            if top_n < min_n:
                blockers.append(f"top n={top_n} < {min_n}")
            if top_wr < min_wr:
                blockers.append(f"top wr {top_wr:.1f}% < {min_wr}%")
            best_summary = {
                "spike_hunter_count": int(best.get("spike_hunter_count") or 0),
                "spike_hunter_generated_utc": best.get("spike_hunter_generated_utc"),
                "top_pair": top.get("pair"),
                "top_edge_score": top_edge,
                "top_win_rate_pct": top_wr,
                "top_bucket_n": top_n,
                "edge_gap": round(min_edge - top_edge, 4) if top_edge < min_edge else 0.0,
                "blockers": blockers,
                "all_clear": not blockers,
            }
        else:
            best_summary = {"spike_hunter_count": int(best.get("spike_hunter_count") or 0), "blockers": ["no picks available"], "all_clear": False}
    except Exception as exc:
        best_summary = {"error": str(exc)[:200]}
    return {
        "ok": True,
        "ts": now_utc(),
        "config": cfg,
        "started_utc": _AUTOBUY_STATE.get("started_utc"),
        "last_scan_utc": _AUTOBUY_STATE.get("last_scan_utc"),
        "last_scan_eligible": _AUTOBUY_STATE.get("last_scan_eligible"),
        "tickets_created_total": _AUTOBUY_STATE.get("tickets_created_total"),
        "last_decision": _AUTOBUY_STATE.get("last_decision"),
        "best_available": best_summary,
        "circuit_breaker": {
            "tripped": bool(_AUTOBUY_STATE.get("circuit_breaker_tripped")),
            "reason": _AUTOBUY_STATE.get("circuit_breaker_reason"),
            "ts": _AUTOBUY_STATE.get("circuit_breaker_ts"),
            "floor_usd": cfg.get("daily_loss_floor_usd"),
        },
        "spike_cache": {
            "refresh_count": _AUTOBUY_STATE.get("spike_refresh_count"),
            "last_refresh_utc": _AUTOBUY_STATE.get("last_spike_refresh_utc"),
            "max_age_minutes": cfg.get("spike_max_age_minutes"),
        },
    }


async def _autobuy_watcher() -> None:
    _AUTOBUY_STATE["started_utc"] = now_utc()
    await asyncio.sleep(8.0)  # let other watchers settle first
    while True:
        try:
            cfg = _load_autobuy_cfg()
            interval = max(20, int(cfg.get("scan_interval_s") or 60))
            if bool(cfg.get("enabled", False)):
                try:
                    _autobuy_scan_once(force=False)
                except Exception as exc:
                    _AUTOBUY_STATE["last_decision"] = {"ts": now_utc(), "error": str(exc)[:200]}
            else:
                _AUTOBUY_STATE["last_scan_utc"] = now_utc()
                _AUTOBUY_STATE["last_scan_eligible"] = 0
        except Exception:
            interval = 60
        await asyncio.sleep(interval)


# =============================================================================
# SESSION PERFORMANCE — today's realized P&L from executed sells, matched
# against the original buy notional via source_txid. Powers the "small wins
# adding up" header card on /live_positions.html.
# =============================================================================

@app.get("/api/perf/session")
def api_perf_session() -> dict[str, Any]:
    """Today's realized P&L tally + wins/losses/win-rate.

    Returns BOTH gross P&L (sell-proceeds - buy-cost) and net P&L after Kraken
    fees (taker fee charged on both legs). Default fee = 0.40% per leg = 0.80%
    round-trip; override via control_flags.json -> "kraken_taker_fee_pct"."""
    queue = _load_approval_queue()
    # Fee rate per leg (taker default 0.40%)
    try:
        flags = _load_control_flags() if "_load_control_flags" in globals() else {}
        fee_pct_per_leg = float(flags.get("kraken_taker_fee_pct") or 0.40)
    except Exception:
        fee_pct_per_leg = 0.40
    fee_rate = fee_pct_per_leg / 100.0
    # Build buy-txid -> buy_notional lookup from EXECUTED buys
    buy_cost_by_txid: dict[str, float] = {}
    for t in queue:
        if str(t.get("side", "")).lower() != "buy":
            continue
        if str(t.get("approval_state", "")).upper() != "EXECUTED_OPEN":
            continue
        for tx in (t.get("txid") or []):
            try:
                buy_cost_by_txid[str(tx)] = float(t.get("notional_usd") or 0.0)
            except Exception:
                pass

    # UTC midnight cutoff for "today"
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_ts = today_start.timestamp()

    wins: list[dict[str, Any]] = []
    losses: list[dict[str, Any]] = []
    flat: list[dict[str, Any]] = []
    realized_today_usd = 0.0
    realized_today_net_usd = 0.0
    realized_all_usd = 0.0
    realized_all_net_usd = 0.0
    fees_today_usd = 0.0
    sells_today = 0
    sells_all = 0
    # Rolling 24h window — bridges UTC-midnight rollovers so the dashboard
    # tile stays informative right after a fresh UTC day starts.
    last_24h_cutoff = (now - timedelta(hours=24)).timestamp()
    realized_24h_usd = 0.0
    realized_24h_net_usd = 0.0
    fees_24h_usd = 0.0
    wins_24h = 0
    losses_24h = 0
    sells_24h = 0
    records_24h: list[dict[str, Any]] = []

    for t in queue:
        if str(t.get("side", "")).lower() != "sell":
            continue
        if str(t.get("approval_state", "")).upper() != "EXECUTED_OPEN":
            continue
        try:
            dt = datetime.fromisoformat(str(t.get("timestamp", "")).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ts = dt.timestamp()
        except Exception:
            ts = 0.0
        src = str(t.get("source_txid") or "")
        sell_proceeds = float(t.get("notional_usd") or 0.0)
        buy_cost = buy_cost_by_txid.get(src, 0.0)
        # If we couldn't match the buy, skip — we only count audited matched pairs.
        if buy_cost <= 0 or sell_proceeds <= 0:
            continue
        pnl = sell_proceeds - buy_cost
        pnl_pct = (pnl / buy_cost) * 100.0 if buy_cost else 0.0
        # Fee-aware net: subtract taker fees on BOTH legs
        leg_fees = (buy_cost + sell_proceeds) * fee_rate
        pnl_net = pnl - leg_fees
        pnl_net_pct = (pnl_net / buy_cost) * 100.0 if buy_cost else 0.0
        rec = {
            "ticket_id": t.get("ticket_id"),
            "pair": t.get("pair"),
            "ts": t.get("timestamp"),
            "buy_cost_usd": round(buy_cost, 4),
            "sell_proceeds_usd": round(sell_proceeds, 4),
            "fees_usd": round(leg_fees, 4),
            "pnl_usd": round(pnl, 4),
            "pnl_pct": round(pnl_pct, 4),
            "pnl_net_usd": round(pnl_net, 4),
            "pnl_net_pct": round(pnl_net_pct, 4),
            "note": t.get("note"),
        }
        sells_all += 1
        realized_all_usd += pnl
        realized_all_net_usd += pnl_net
        if ts >= last_24h_cutoff:
            sells_24h += 1
            realized_24h_usd += pnl
            realized_24h_net_usd += pnl_net
            fees_24h_usd += leg_fees
            if pnl_net > 0:
                wins_24h += 1
            elif pnl_net < 0:
                losses_24h += 1
            records_24h.append(rec)
        if ts >= today_ts:
            sells_today += 1
            realized_today_usd += pnl
            realized_today_net_usd += pnl_net
            fees_today_usd += leg_fees
            # Win/loss classification uses NET P&L (post-fees) — what actually hits the wallet
            if pnl_net > 0:
                wins.append(rec)
            elif pnl_net < 0:
                losses.append(rec)
            else:
                flat.append(rec)

    win_count = len(wins)
    loss_count = len(losses)
    decided = win_count + loss_count
    win_rate_pct = (win_count / decided * 100.0) if decided else 0.0
    biggest_win = max(wins, key=lambda r: r["pnl_net_usd"]) if wins else None
    worst_loss = min(losses, key=lambda r: r["pnl_net_usd"]) if losses else None
    avg_win = (sum(r["pnl_net_usd"] for r in wins) / win_count) if win_count else 0.0
    avg_loss = (sum(r["pnl_net_usd"] for r in losses) / loss_count) if loss_count else 0.0
    payoff = (avg_win / abs(avg_loss)) if avg_loss else None

    # Sort recent first
    today_records = sorted(wins + losses + flat, key=lambda r: r.get("ts") or "", reverse=True)
    records_24h_sorted = sorted(records_24h, key=lambda r: r.get("ts") or "", reverse=True)

    decided_24h = wins_24h + losses_24h
    win_rate_24h = (wins_24h / decided_24h * 100.0) if decided_24h else 0.0

    result = {
        "ok": True,
        "ts": now_utc(),
        "today_utc_start": today_start.isoformat(),
        "fee_pct_per_leg": fee_pct_per_leg,
        "session": {
            "realized_pnl_usd": round(realized_today_usd, 4),
            "realized_pnl_net_usd": round(realized_today_net_usd, 4),
            "fees_usd": round(fees_today_usd, 4),
            "sells_count": sells_today,
            "wins": win_count,
            "losses": loss_count,
            "flat": len(flat),
            "win_rate_pct": round(win_rate_pct, 2),
            "avg_win_usd": round(avg_win, 4),
            "avg_loss_usd": round(avg_loss, 4),
            "payoff_ratio": round(payoff, 3) if payoff is not None else None,
            "biggest_win": biggest_win,
            "worst_loss": worst_loss,
        },
        "last_24h": {
            "realized_pnl_usd": round(realized_24h_usd, 4),
            "realized_pnl_net_usd": round(realized_24h_net_usd, 4),
            "fees_usd": round(fees_24h_usd, 4),
            "sells_count": sells_24h,
            "wins": wins_24h,
            "losses": losses_24h,
            "win_rate_pct": round(win_rate_24h, 2),
            "trades": records_24h_sorted,
        },
        "all_time": {
            "realized_pnl_usd": round(realized_all_usd, 4),
            "realized_pnl_net_usd": round(realized_all_net_usd, 4),
            "matched_sells": sells_all,
        },
        "trades_today": today_records,
    }
    # Persist today's snapshot for the history endpoint / dashboard sparkline.
    try:
        _persist_daily_snapshot(result)
    except Exception:
        pass
    return result


# Helper for the legacy `return {...}` pattern above — assign result name.
_PERF_SESSION_PATCHED = True


# =============================================================================
# DAILY PERF SNAPSHOTS — last-write-wins per UTC day. Enables history endpoint
# and the dashboard 7-day equity sparkline.
# =============================================================================

PERF_DAILY_DIR = ROOT / "out" / "perf"


def _persist_daily_snapshot(perf: dict[str, Any]) -> None:
    """Write today's snapshot to out/perf/daily_<YYYY-MM-DD>.json (atomic).

    Also backfills prior-day snapshots from the full matched-trade history so
    the 7-day chart has data even for days the gateway wasn't running."""
    try:
        ts_iso = perf.get("today_utc_start") or now_utc()
        day = str(ts_iso)[:10]
        PERF_DAILY_DIR.mkdir(parents=True, exist_ok=True)
        snap = {
            "date_utc": day,
            "ts": now_utc(),
            "fee_pct_per_leg": perf.get("fee_pct_per_leg"),
            "session": perf.get("session", {}),
            "all_time": perf.get("all_time", {}),
            "trade_count": len(perf.get("trades_today") or []),
        }
        target = PERF_DAILY_DIR / f"daily_{day}.json"
        tmp = target.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(snap, indent=2), encoding="utf-8")
        tmp.replace(target)
    except Exception:
        # Persistence is best-effort; never block the API on disk errors.
        pass
    # Backfill: scan all matched sells, group by UTC date, write any missing
    # day snapshots. Cheap (iterates the queue once) and idempotent.
    try:
        _backfill_daily_snapshots(perf.get("fee_pct_per_leg") or 0.40)
    except Exception:
        pass


def _backfill_daily_snapshots(fee_pct_per_leg: float) -> None:
    """Reconstruct per-UTC-day net P&L from the full approval queue and write
    snapshots for any historical day not already persisted."""
    queue = _load_approval_queue()
    fee_rate = float(fee_pct_per_leg) / 100.0
    # Map buy txid -> notional
    buy_cost: dict[str, float] = {}
    for t in queue:
        if str(t.get("side", "")).lower() != "buy":
            continue
        if str(t.get("approval_state", "")).upper() != "EXECUTED_OPEN":
            continue
        for tx in (t.get("txid") or []):
            try:
                buy_cost[str(tx)] = float(t.get("notional_usd") or 0.0)
            except Exception:
                pass
    # Group sells by UTC date
    by_day: dict[str, dict[str, Any]] = {}
    for t in queue:
        if str(t.get("side", "")).lower() != "sell":
            continue
        if str(t.get("approval_state", "")).upper() != "EXECUTED_OPEN":
            continue
        try:
            dt = datetime.fromisoformat(str(t.get("timestamp", "")).replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        day = dt.astimezone(timezone.utc).date().isoformat()
        src = str(t.get("source_txid") or "")
        sell_proc = float(t.get("notional_usd") or 0.0)
        b = buy_cost.get(src, 0.0)
        if b <= 0 or sell_proc <= 0:
            continue
        gross = sell_proc - b
        fees = (b + sell_proc) * fee_rate
        net = gross - fees
        agg = by_day.setdefault(day, {
            "realized_pnl_usd": 0.0, "realized_pnl_net_usd": 0.0,
            "fees_usd": 0.0, "wins": 0, "losses": 0, "sells_count": 0,
        })
        agg["realized_pnl_usd"] += gross
        agg["realized_pnl_net_usd"] += net
        agg["fees_usd"] += fees
        agg["sells_count"] += 1
        if net > 0:
            agg["wins"] += 1
        elif net < 0:
            agg["losses"] += 1

    today_str = datetime.now(timezone.utc).date().isoformat()
    for day, agg in by_day.items():
        target = PERF_DAILY_DIR / f"daily_{day}.json"
        # For TODAY we always overwrite (the live api_perf_session writes the canonical snapshot).
        # For prior days we write only if missing OR if our reconstructed net differs materially.
        if day == today_str and target.exists():
            continue
        try:
            if target.exists():
                existing = json.loads(target.read_text(encoding="utf-8"))
                ex_net = float((existing.get("session") or {}).get("realized_pnl_net_usd") or 0.0)
                if abs(ex_net - agg["realized_pnl_net_usd"]) < 0.005:
                    continue  # already correct
        except Exception:
            pass
        decided = agg["wins"] + agg["losses"]
        wr = (agg["wins"] / decided * 100.0) if decided else 0.0
        snap = {
            "date_utc": day,
            "ts": now_utc(),
            "fee_pct_per_leg": fee_pct_per_leg,
            "session": {
                "realized_pnl_usd": round(agg["realized_pnl_usd"], 4),
                "realized_pnl_net_usd": round(agg["realized_pnl_net_usd"], 4),
                "fees_usd": round(agg["fees_usd"], 4),
                "sells_count": agg["sells_count"],
                "wins": agg["wins"],
                "losses": agg["losses"],
                "win_rate_pct": round(wr, 2),
            },
            "all_time": None,
            "trade_count": agg["sells_count"],
            "backfilled": True,
        }
        try:
            tmp = target.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(snap, indent=2), encoding="utf-8")
            tmp.replace(target)
        except Exception:
            pass


@app.get("/api/perf/history")
def api_perf_history(days: int = 14) -> dict[str, Any]:
    """Return last `days` daily perf snapshots, oldest-first, for sparkline / chart."""
    days = max(1, min(int(days or 14), 90))
    if not PERF_DAILY_DIR.exists():
        return {"ok": True, "ts": now_utc(), "days": [], "count": 0}
    rows: list[dict[str, Any]] = []
    today = datetime.now(timezone.utc).date()
    for back in range(days - 1, -1, -1):
        day = (today - timedelta(days=back)).isoformat()
        f = PERF_DAILY_DIR / f"daily_{day}.json"
        if not f.exists():
            rows.append({"date_utc": day, "session": None, "missing": True})
            continue
        try:
            snap = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            rows.append({"date_utc": day, "session": None, "error": "parse"})
            continue
        s = snap.get("session", {}) or {}
        rows.append({
            "date_utc": day,
            "realized_pnl_net_usd": s.get("realized_pnl_net_usd", 0.0),
            "realized_pnl_usd": s.get("realized_pnl_usd", 0.0),
            "fees_usd": s.get("fees_usd", 0.0),
            "wins": s.get("wins", 0),
            "losses": s.get("losses", 0),
            "win_rate_pct": s.get("win_rate_pct", 0.0),
            "sells_count": s.get("sells_count", 0),
            "missing": False,
        })
    # Cumulative net curve
    cum = 0.0
    for r in rows:
        if not r.get("missing"):
            cum += float(r.get("realized_pnl_net_usd") or 0.0)
        r["cum_net_usd"] = round(cum, 4)
    # Aggregates
    present = [r for r in rows if not r.get("missing")]
    total_net = round(sum(float(r.get("realized_pnl_net_usd") or 0.0) for r in present), 4)
    total_wins = sum(int(r.get("wins") or 0) for r in present)
    total_losses = sum(int(r.get("losses") or 0) for r in present)
    decided = total_wins + total_losses
    return {
        "ok": True,
        "ts": now_utc(),
        "window_days": days,
        "days": rows,
        "count": len(rows),
        "totals": {
            "net_usd": total_net,
            "wins": total_wins,
            "losses": total_losses,
            "win_rate_pct": round((total_wins / decided * 100.0) if decided else 0.0, 2),
            "trading_days": sum(1 for r in present if (r.get("sells_count") or 0) > 0),
        },
    }


# (api_perf_session calls _persist_daily_snapshot inline; see below.)


if DASH.exists():
    # Expose the workspace `out/` tree read-only so master_evidence.html
    # can resolve `../out/master_universe_v2/...` relative paths.
    _OUT_DIR = OUT
    _out_env = (os.getenv("LUMA_OUT_DIR") or "").strip()
    if _out_env:
        _OUT_DIR = Path(_out_env).expanduser().resolve()
    if _OUT_DIR.exists():
        app.mount("/out", StaticFiles(directory=str(_OUT_DIR)), name="out_tree")
    app.mount("/", StaticFiles(directory=str(DASH), html=True), name="dashboard")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8787,
        reload=False,
        log_level="info",
    )
