from __future__ import annotations

import atexit
import asyncio
import csv
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from prometheus_fastapi_instrumentator import Instrumentator as _PrometheusInstrumentator
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Gauge
    _WS_CONNECTIONS = Gauge("luma_ws_connections", "Active WebSocket connections")
    _SNAPSHOT_REQUESTS = Counter("luma_snapshot_requests_total", "Snapshot API calls")
    _ML_RUNS = Counter("luma_ml_signal_runs_total", "ML signal generation runs")
    _PROM_CLIENT_AVAILABLE = True
except ImportError:
    _PROM_CLIENT_AVAILABLE = False

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CODE = ROOT / "code"
DASH = Path(r"C:\LumaTrader\dashboard")

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
    except (ValueError, OSError):
        pass  # stale lock
_GATEWAY_LOCK.write_text(str(os.getpid()))
atexit.register(lambda: _GATEWAY_LOCK.unlink(missing_ok=True))
# ─────────────────────────────────────────────────────────────────────────────

OUT = ROOT / "out"
EXEC_OUT = OUT / "execution"
LAMASCOUT_REPORTS = ROOT / "LamaScout" / "reports"
TWIN_SEED_PATH = Path(r"C:\Users\Novac\iCloudDrive\Downloads 2\Copy of twin_seed.json")

SCORECARD_FILE = EXEC_OUT / "investor_proof_scorecard.json"
SUPERVISOR_HEALTH_FILE = EXEC_OUT / "supervisor_health.json"
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


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


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


def build_snapshot() -> dict[str, Any]:
    scorecard = load_json(SCORECARD_FILE, {})
    sector = load_json(SECTOR_FILE, {})
    scout = load_json(SCOUT_FILE, {})
    twin_seed = load_json(TWIN_SEED_PATH, {})
    awareness = load_json(AWARENESS_FILE, {})

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
        "harmonic": load_harmonic_edge(),
    }


class GuideRequest(BaseModel):
    prompt: str
    mode: str = "concierge"


class SessionEvent(BaseModel):
    event: str
    source: str = "web"
    detail: dict[str, Any] = {}


class CueRequest(BaseModel):
    scene: str = "core"
    cue: str
    intensity: float = 0.5
    detail: dict[str, Any] = {}


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
        f"and the latest verified execution proof points to TXID {txid}."
    )

    analyst = (
        f"Execution: {headline.get('closed_trades', 0)} closed trades, win rate {float(headline.get('win_rate_pct', 0.0) or 0.0):.1f}%, "
        f"profit factor {float(headline.get('profit_factor', 0.0) or 0.0):.2f}, rolling Sharpe {float(headline.get('sharpe', 0.0) or 0.0):.3f}. "
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
        for ws in self.connections:
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

manager = ConnectionManager()


@app.on_event("startup")
async def startup_event() -> None:
    DASH.mkdir(parents=True, exist_ok=True)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/luma_experience.html", status_code=307)


@app.get("/health")
def health() -> dict[str, Any]:
    supervisor = load_json(SUPERVISOR_HEALTH_FILE, None)
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


@app.get("/api/harmonic/top")
def harmonic_top() -> dict[str, Any]:
    """Live harmonic edge signals across all domains — sports, crypto, infra."""
    ranked = load_json(HARMONIC_RANKED_FILE, {})
    return {
        "generated_utc": now_utc(),
        "source_utc":    ranked.get("generated_utc") if isinstance(ranked, dict) else None,
        "total_signals": ranked.get("total", 0) if isinstance(ranked, dict) else 0,
        "summary":       ranked.get("summary", {}) if isinstance(ranked, dict) else {},
        "top_signals":   (ranked.get("top_signals", []) if isinstance(ranked, dict) else [])[:20],
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
    payload = {
        "type": "scene_cue",
        "data": {
            "ts": now_utc(),
            "scene": req.scene,
            "cue": req.cue,
            "intensity": req.intensity,
            "detail": req.detail,
        },
    }
    await manager.broadcast(payload)
    return {"status": "ok", "sent": True, "cue": req.cue}


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
    supervisor  = load_json(SUPERVISOR_HEALTH_FILE, {})
    sector      = load_json(SECTOR_FILE, {})
    harmonic    = load_harmonic_edge()

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
            "closed_trades":    int(scorecard.get("closed_trades", 0) or 0),
            "win_rate_pct":     float(scorecard.get("win_rate_pct", 0.0) or 0.0),
            "profit_factor":    float(scorecard.get("profit_factor", 0.0) or 0.0),
            "sharpe":           float(rolling.get("sharpe", 0.0) or 0.0),
            "services_up":      f"{svc_up}/{svc_total}",
            "supervisor_tick":  supervisor.get("tick", 0),
            "infra_top_lane":   sector.get("top_current_optimization_lane", "n/a"),
            "harmonic_top_asset":   harmonic.get("top_asset", "n/a"),
            "harmonic_top_score":   harmonic.get("top_score", 0.0),
        },
        "strategy_leaderboard": top10,
        "execution_proof":      proof_events,
        "rolling_performance":  rolling,
        "harmonic":             harmonic,
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
    supervisor = load_json(SUPERVISOR_HEALTH_FILE, {})
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
                    {
                        "type": "scene_cue",
                        "data": {
                            "ts": now_utc(),
                            "scene": message.get("scene", "core"),
                            "cue": message.get("cue", "pulse"),
                            "intensity": float(message.get("intensity", 0.5) or 0.5),
                            "detail": message.get("detail", {}),
                        },
                    }
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        return
    except Exception:
        manager.disconnect(websocket)
        return


async def broadcaster() -> None:
    while True:
        payload = {"type": "snapshot", "data": build_snapshot()}
        await manager.broadcast(payload)
        await asyncio.sleep(2.0)


@app.on_event("startup")
async def start_broadcaster() -> None:
    asyncio.create_task(broadcaster())


if DASH.exists():
    app.mount("/", StaticFiles(directory=str(DASH), html=True), name="dashboard")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "luma_experience_gateway:app",
        host="0.0.0.0",
        port=8787,
        reload=False,
        log_level="info",
    )
