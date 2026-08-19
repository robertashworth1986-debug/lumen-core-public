"""
LUMA AUTO-TICKET PRODUCER
─────────────────────────
Runs the spike hunter scanner and emits high-conviction setups
as PENDING_HUMAN_APPROVAL tickets into execution_approval_queue.json.

Robert (or any allowlisted controller) still has to click Approve & Fire
in the v3 dashboard. This module just keeps the queue full of the BEST
opportunities the scanner can find.

USAGE
─────
  Single shot (rescan + emit, then exit):
    python code/auto_ticket_producer.py

  Daemon (loops every INTERVAL_MIN minutes):
    python code/auto_ticket_producer.py --daemon

  Use cached spike_hunter_latest.json without rescanning:
    python code/auto_ticket_producer.py --cached

SAFETY
──────
* Defaults to `validate=true` (Kraken DRY-RUN). Pass --live to flip to real.
* Hard caps: notional <= MAX_NOTIONAL_USD ($20, under the gateway's $25 cap).
* Adaptive queue caps: base MAX_PENDING_TICKETS with hard ceilings per mode.
* Per-pair cooldown: never emit a duplicate while one is PENDING/OPEN.
* Skips signals == ['WATCH']. Requires score >= MIN_SCORE.
* Skips pairs with 24h USD volume below MIN_24H_VOL_USD (illiquid).
"""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

try:
    from execution.live_action_authority import (
        DEFAULT_AUTHORITY_TTL_SEC,
        validate_live_action_authority,
    )
except ImportError:
    _authority_path = Path(__file__).resolve().parent / "execution" / "live_action_authority.py"
    _authority_spec = importlib.util.spec_from_file_location(
        "auto_ticket_live_action_authority",
        _authority_path,
    )
    if _authority_spec is None or _authority_spec.loader is None:
        raise RuntimeError("live action authority validator is unavailable")
    _authority_module = importlib.util.module_from_spec(_authority_spec)
    _authority_spec.loader.exec_module(_authority_module)
    DEFAULT_AUTHORITY_TTL_SEC = _authority_module.DEFAULT_AUTHORITY_TTL_SEC
    validate_live_action_authority = _authority_module.validate_live_action_authority

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "execution_approval_queue.json"
SPIKE_LATEST = ROOT / "out" / "spike_hunter" / "spike_hunter_latest.json"
ALPHA_MAP_LATEST_JSON = ROOT / "out" / "ops" / "kraken_multi_tf_alpha_map_latest.json"
ALPHA_MAP_LATEST_CSV = ROOT / "out" / "ops" / "kraken_multi_tf_alpha_map_latest.csv"
CLUSTER_LATEST_JSON = ROOT / "out" / "ops" / "kraken_6m_move_clusters_latest.json"
SPIKE_HISTORY_DIR = ROOT / "out" / "spike_hunter" / "history"
SPIKE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
PRODUCER_LOG = ROOT / "out" / "execution" / "auto_ticket_producer.jsonl"
PRODUCER_LOG.parent.mkdir(parents=True, exist_ok=True)
AUTO_FIRE_CONFIG = ROOT / "run" / "auto_fire_config.json"
AUTO_FIRE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
DAEMON_PID_FILE = ROOT / "run" / "auto_ticket_producer.pid"
RUNTIME_CONTROL_FILE = ROOT / "config" / "runtime_control.json"
LIVE_ACTION_RECEIPT_FILE = ROOT / "out" / "execution" / "live_action_time_approval_receipt_latest.json"


def _live_authority_state(validate: bool, controller: str) -> dict:
    if validate:
        return {
            "authorized": False,
            "required": False,
            "reasons": ["validate_only_ticket"],
        }
    state = validate_live_action_authority(
        runtime_path=RUNTIME_CONTROL_FILE,
        receipt_path=LIVE_ACTION_RECEIPT_FILE,
        controller=controller,
        ttl_seconds=DEFAULT_AUTHORITY_TTL_SEC,
    )
    return {**state, "required": True}


def _require_live_authority(validate: bool, controller: str, action: str) -> dict:
    state = _live_authority_state(validate=validate, controller=controller)
    if validate or state.get("authorized") is True:
        return state
    reasons = ",".join(str(reason) for reason in state.get("reasons", [])) or "not_authorized"
    raise RuntimeError(f"{action} blocked: fresh hash-bound human action-time authority required ({reasons})")


def _read_runtime_config(default_threshold: float | None,
                         default_enabled: bool) -> dict:
    """Read live config from disk; returns producer runtime controls."""
    if AUTO_FIRE_CONFIG.exists():
        try:
            cfg = json.loads(AUTO_FIRE_CONFIG.read_text(encoding="utf-8"))
            return {
                "enabled": bool(cfg.get("enabled", default_enabled)),
                "auto_fire_score": cfg.get("auto_fire_score", default_threshold),
                "max_pending_tickets": cfg.get("max_pending_tickets"),
                "max_cycle_emits": cfg.get("max_cycle_emits"),
                "adaptive_queue": cfg.get("adaptive_queue", True),
                "scan_max_age_sec": cfg.get("scan_max_age_sec"),
                "top_n": cfg.get("top_n"),
                "pending_ticket_max_age_sec": cfg.get("pending_ticket_max_age_sec"),
                "pending_profit_lock_max_age_sec": cfg.get("pending_profit_lock_max_age_sec"),
                "pending_dedupe_by_pair_side": cfg.get("pending_dedupe_by_pair_side"),
                "pending_keep_per_pair_side": cfg.get("pending_keep_per_pair_side"),
                "max_auto_fires_per_cycle": cfg.get("max_auto_fires_per_cycle"),
                "auto_fire_score_moonshot": cfg.get("auto_fire_score_moonshot"),
                "auto_fire_score_quickhit": cfg.get("auto_fire_score_quickhit"),
                "auto_fire_score_swing": cfg.get("auto_fire_score_swing"),
                "max_auto_fires_per_cycle_moonshot": cfg.get("max_auto_fires_per_cycle_moonshot"),
                "max_auto_fires_per_cycle_quickhit": cfg.get("max_auto_fires_per_cycle_quickhit"),
                "max_auto_fires_per_cycle_swing": cfg.get("max_auto_fires_per_cycle_swing"),
                "alpha_gate_min_edge": cfg.get("alpha_gate_min_edge"),
                "alpha_gate_max_spread_bps": cfg.get("alpha_gate_max_spread_bps"),
                "alpha_gate_min_turnover_usd": cfg.get("alpha_gate_min_turnover_usd"),
                "alpha_gate_allow_watch_strategy": cfg.get("alpha_gate_allow_watch_strategy"),
                "alpha_gate_require_match_live": cfg.get("alpha_gate_require_match_live"),
                "cluster_gate_enabled": cfg.get("cluster_gate_enabled"),
                "cluster_enforce_time_alignment": cfg.get("cluster_enforce_time_alignment"),
                "cluster_min_pair_score": cfg.get("cluster_min_pair_score"),
                "cluster_hour_tolerance": cfg.get("cluster_hour_tolerance"),
                "cluster_weekday_tolerance": cfg.get("cluster_weekday_tolerance"),
                "cluster_require_alignment_live": cfg.get("cluster_require_alignment_live"),
                "strategy_mode": cfg.get("strategy_mode"),
                "bankroll_usd": cfg.get("bankroll_usd"),
                "max_notional_usd": cfg.get("max_notional_usd"),
                "compounding_enabled": cfg.get("compounding_enabled"),
                "compounding_reference_bankroll_usd": cfg.get("compounding_reference_bankroll_usd"),
                "compounding_growth_sensitivity": cfg.get("compounding_growth_sensitivity"),
                "compounding_min_bankroll_mult": cfg.get("compounding_min_bankroll_mult"),
                "compounding_max_bankroll_mult": cfg.get("compounding_max_bankroll_mult"),
                "compounding_equity_source_path": cfg.get("compounding_equity_source_path"),
                "compounding_equity_max_age_sec": cfg.get("compounding_equity_max_age_sec"),
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
                "profitability_min_net_edge_pct": cfg.get("profitability_min_net_edge_pct"),
                "profitability_fee_roundtrip_bps": cfg.get("profitability_fee_roundtrip_bps"),
                "profitability_slippage_floor_bps": cfg.get("profitability_slippage_floor_bps"),
                "profitability_spread_slippage_mult": cfg.get("profitability_spread_slippage_mult"),
                "profitability_min_execution_quality_score": cfg.get("profitability_min_execution_quality_score"),
                "profitability_notional_edge_scale_pct": cfg.get("profitability_notional_edge_scale_pct"),
                "profitability_notional_floor_mult": cfg.get("profitability_notional_floor_mult"),
                "profitability_notional_cap_mult": cfg.get("profitability_notional_cap_mult"),
            }
        except Exception:
            pass
    return {
        "enabled": default_enabled,
        "auto_fire_score": default_threshold,
        "max_pending_tickets": None,
        "max_cycle_emits": None,
        "adaptive_queue": True,
        "scan_max_age_sec": None,
        "top_n": None,
        "pending_ticket_max_age_sec": None,
        "pending_profit_lock_max_age_sec": None,
        "pending_dedupe_by_pair_side": None,
        "pending_keep_per_pair_side": None,
        "max_auto_fires_per_cycle": None,
        "auto_fire_score_moonshot": None,
        "auto_fire_score_quickhit": None,
        "auto_fire_score_swing": None,
        "max_auto_fires_per_cycle_moonshot": None,
        "max_auto_fires_per_cycle_quickhit": None,
        "max_auto_fires_per_cycle_swing": None,
        "alpha_gate_min_edge": None,
        "alpha_gate_max_spread_bps": None,
        "alpha_gate_min_turnover_usd": None,
        "alpha_gate_allow_watch_strategy": None,
        "alpha_gate_require_match_live": None,
        "cluster_gate_enabled": None,
        "cluster_enforce_time_alignment": None,
        "cluster_min_pair_score": None,
        "cluster_hour_tolerance": None,
        "cluster_weekday_tolerance": None,
        "cluster_require_alignment_live": None,
        "strategy_mode": None,
        "bankroll_usd": None,
        "max_notional_usd": None,
        "compounding_enabled": None,
        "compounding_reference_bankroll_usd": None,
        "compounding_growth_sensitivity": None,
        "compounding_min_bankroll_mult": None,
        "compounding_max_bankroll_mult": None,
        "compounding_equity_source_path": None,
        "compounding_equity_max_age_sec": None,
        "moonshot_bankroll_frac": None,
        "moonshot_max_per_cycle": None,
        "moonshot_min_edge": None,
        "moonshot_min_dip_pct": None,
        "moonshot_max_rsi": None,
        "moonshot_min_rebound_15m_pct": None,
        "moonshot_max_spread_bps": None,
        "moonshot_min_turnover_usd": None,
        "quickhit_target_notional_usd": None,
        "quickhit_max_per_cycle": None,
        "quickhit_min_edge": None,
        "quickhit_min_r1m_pct": None,
        "quickhit_min_r15m_pct": None,
        "quickhit_min_m4h_pct": None,
        "quickhit_max_spread_bps": None,
        "quickhit_min_turnover_usd": None,
        "swing_target_notional_usd": None,
        "swing_max_per_cycle": None,
        "swing_min_edge": None,
        "swing_min_r1h_pct": None,
        "swing_min_m4h_pct": None,
        "swing_max_spread_bps": None,
        "swing_min_turnover_usd": None,
        "profitability_min_net_edge_pct": None,
        "profitability_fee_roundtrip_bps": None,
        "profitability_slippage_floor_bps": None,
        "profitability_spread_slippage_mult": None,
        "profitability_min_execution_quality_score": None,
        "profitability_notional_edge_scale_pct": None,
        "profitability_notional_floor_mult": None,
        "profitability_notional_cap_mult": None,
    }


def _write_runtime_config(cfg: dict) -> None:
    AUTO_FIRE_CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def _archive_scan(scan: dict) -> None:
    """Save a timestamped snapshot for later backtesting."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = SPIKE_HISTORY_DIR / f"spike_{ts}.json"
    try:
        out.write_text(json.dumps(scan, indent=2), encoding="utf-8")
    except Exception:
        pass

# Tunables ─────────────────────────────────────────────────────────────────
DEFAULT_CONTROLLER = "Robert"
MAX_NOTIONAL_USD   = 20.0   # default; runtime can lower/raise within hard caps
MAX_NOTIONAL_USD_LIVE_HARD = 50.0
MAX_NOTIONAL_USD_VALIDATE_HARD = 75.0
MIN_NOTIONAL_USD   = 5.0    # Kraken minimums vary; $5 is generally safe
MAX_PENDING_TICKETS = 6     # never flood the queue
MAX_PENDING_TICKETS_LIVE_HARD = 14
MAX_PENDING_TICKETS_VALIDATE_HARD = 40
MAX_CYCLE_EMITS = 6
MAX_CYCLE_EMITS_LIVE_HARD = 8
MAX_CYCLE_EMITS_VALIDATE_HARD = 20
MAX_AUTO_FIRES_PER_CYCLE = 3
ADAPTIVE_QUEUE_DEFAULT = True
ADAPTIVE_STRONG_EDGE = 8.0
SCAN_MAX_AGE_SEC_DEFAULT = 120.0
MIN_SCORE          = 35.0   # 0-100 composite
MIN_24H_VOL_USD    = 25_000 # liquidity floor
ALPHA_GATE_MIN_EDGE = 4.0
ALPHA_GATE_MAX_SPREAD_BPS = 35.0
ALPHA_GATE_MIN_TURNOVER_USD = 250_000.0
ALPHA_GATE_ALLOWED_STRATEGIES = {
    "momentum_snipe",
    "mean_reversion_snapback",
    "trend_follow_swing",
}
PROFITABILITY_MIN_NET_EDGE_PCT = 1.0
PROFITABILITY_FEE_ROUNDTRIP_BPS = 40.0
PROFITABILITY_SLIPPAGE_FLOOR_BPS = 8.0
PROFITABILITY_SPREAD_SLIPPAGE_MULT = 1.25
PROFITABILITY_MIN_EXECUTION_QUALITY_SCORE = 10.0
PROFITABILITY_NOTIONAL_EDGE_SCALE_PCT = 8.0
PROFITABILITY_NOTIONAL_FLOOR_MULT = 0.7
PROFITABILITY_NOTIONAL_CAP_MULT = 1.4
CLUSTER_GATE_ENABLED_DEFAULT = True
CLUSTER_GATE_ENFORCE_TIME_ALIGNMENT_DEFAULT = True
CLUSTER_GATE_MIN_PAIR_SCORE = 8.0
CLUSTER_GATE_HOUR_TOLERANCE = 1
CLUSTER_GATE_WEEKDAY_TOLERANCE = 0
CLUSTER_GATE_REQUIRE_ALIGNMENT_LIVE = True
# Fail-closed only in LIVE mode. In DRY-RUN mode we keep discovery running.
ALPHA_GATE_REQUIRE_MATCH_LIVE = True
COOLDOWN_PAIRS_STATES = {"PENDING_HUMAN_APPROVAL", "EXECUTED_OPEN"}
INTERVAL_MIN_DEFAULT = 15
BANKROLL_DEFAULT     = 150.0
TOP_N_DEFAULT        = 20
PENDING_TICKET_MAX_AGE_SEC_DEFAULT = 1800.0
PENDING_PROFIT_LOCK_MAX_AGE_SEC_DEFAULT = 180.0
PENDING_DEDUPE_BY_PAIR_SIDE_DEFAULT = True
PENDING_KEEP_PER_PAIR_SIDE_DEFAULT = 1
COMPOUNDING_ENABLED_DEFAULT = True
COMPOUNDING_REFERENCE_BANKROLL_USD = BANKROLL_DEFAULT
COMPOUNDING_GROWTH_SENSITIVITY = 0.8
COMPOUNDING_MIN_BANKROLL_MULT = 0.75
COMPOUNDING_MAX_BANKROLL_MULT = 1.35
COMPOUNDING_EQUITY_MAX_AGE_SEC = 10_800.0
DEFAULT_COMPOUNDING_EQUITY_SOURCE = ROOT / "out" / "rolling_performance.json"

STRATEGY_MODE_HYBRID = "hybrid"
STRATEGY_MODE_MOONSHOT = "moonshot"
STRATEGY_MODE_QUICKHIT = "quickhit"
STRATEGY_MODE_SWING = "swing"
STRATEGY_MODES = {
    STRATEGY_MODE_HYBRID,
    STRATEGY_MODE_MOONSHOT,
    STRATEGY_MODE_QUICKHIT,
    STRATEGY_MODE_SWING,
}

LANE_MOONSHOT = "moonshot_reversal"
LANE_QUICKHIT = "quickhit_scalp"
LANE_SWING = "swing_trend"
LANES = (LANE_MOONSHOT, LANE_QUICKHIT, LANE_SWING)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_queue() -> list[dict]:
    if not QUEUE_FILE.exists():
        return []
    try:
        return json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_queue(rows: list[dict]) -> None:
    QUEUE_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _parse_utc_ts(raw: object) -> datetime | None:
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _compact_pending_queue(rows: list[dict], runtime_cfg: dict | None) -> tuple[list[dict], dict]:
    cfg = runtime_cfg or {}
    ttl_pending_sec = max(
        0.0,
        _safe_float(cfg.get("pending_ticket_max_age_sec"), PENDING_TICKET_MAX_AGE_SEC_DEFAULT),
    )
    ttl_profit_lock_sec = max(
        0.0,
        _safe_float(
            cfg.get("pending_profit_lock_max_age_sec"),
            PENDING_PROFIT_LOCK_MAX_AGE_SEC_DEFAULT,
        ),
    )
    dedupe_by_pair_side = bool(
        cfg.get("pending_dedupe_by_pair_side", PENDING_DEDUPE_BY_PAIR_SIDE_DEFAULT)
    )
    keep_per_pair_side = max(
        1,
        _safe_int(cfg.get("pending_keep_per_pair_side"), PENDING_KEEP_PER_PAIR_SIDE_DEFAULT),
    )

    pending_before = sum(
        1 for r in rows if str(r.get("approval_state") or "") == "PENDING_HUMAN_APPROVAL"
    )
    if not rows:
        return rows, {
            "changed": False,
            "pending_before": 0,
            "pending_after": 0,
            "dropped_stale": 0,
            "dropped_dedupe": 0,
            "dedupe_enabled": dedupe_by_pair_side,
        }

    now_utc = datetime.now(timezone.utc)
    keep_indices: set[int] = set()
    pending_buckets: dict[str, list[tuple[float, int]]] = {}
    dropped_stale = 0

    for idx, row in enumerate(rows):
        state = str(row.get("approval_state") or "")
        if state != "PENDING_HUMAN_APPROVAL":
            keep_indices.add(idx)
            continue

        ts = _parse_utc_ts(row.get("timestamp"))
        age_sec = max(0.0, (now_utc - ts).total_seconds()) if ts else None
        origin = str(row.get("origin") or "").strip().lower()
        ttl = ttl_profit_lock_sec if origin == "profit_lock" else ttl_pending_sec
        if ttl > 0 and age_sec is not None and age_sec > ttl:
            dropped_stale += 1
            continue

        pair = str(row.get("pair") or "")
        side = str(row.get("side") or "")
        if not dedupe_by_pair_side:
            keep_indices.add(idx)
            continue

        key = f"{pair}|{side}"
        epoch = ts.timestamp() if ts else -1.0
        pending_buckets.setdefault(key, []).append((epoch, idx))

    dropped_dedupe = 0
    if dedupe_by_pair_side:
        selected_pending: set[int] = set()
        for entries in pending_buckets.values():
            entries.sort(key=lambda x: (x[0], x[1]), reverse=True)
            for pos, (_, idx) in enumerate(entries):
                if pos < keep_per_pair_side:
                    selected_pending.add(idx)
                else:
                    dropped_dedupe += 1
        keep_indices.update(selected_pending)

    cleaned = [row for idx, row in enumerate(rows) if idx in keep_indices]
    pending_after = sum(
        1 for r in cleaned if str(r.get("approval_state") or "") == "PENDING_HUMAN_APPROVAL"
    )
    return cleaned, {
        "changed": len(cleaned) != len(rows),
        "pending_before": pending_before,
        "pending_after": pending_after,
        "dropped_stale": dropped_stale,
        "dropped_dedupe": dropped_dedupe,
        "dedupe_enabled": dedupe_by_pair_side,
    }


def _log_event(event: dict) -> None:
    event = {"ts": _utc_iso(), **event}
    with PRODUCER_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def _round_volume(vol: float) -> str:
    # Kraken accepts up to 8 decimals on most pairs.
    if vol >= 1:
        return f"{vol:.4f}"
    if vol >= 0.01:
        return f"{vol:.6f}"
    return f"{vol:.8f}"


def _normalize_pair_for_kraken(pair: str, wsname: str) -> str:
    # Kraken AddOrder happily takes either the altname (e.g. XBTUSD) or the
    # legacy code (e.g. XXBTZUSD). The altname is what the spike hunter stores
    # under "pair", so we use it directly. wsname like "XBT/USD" also works.
    return pair or wsname.replace("/", "")


def _pair_token(value: str) -> str:
    return "".join(ch for ch in str(value or "").upper() if ch.isalnum())


def _load_alpha_map_context() -> dict:
    context = {
        "available": False,
        "generated_utc": "",
        "pairs_analyzed": 0,
        "lookup": {},
    }

    if ALPHA_MAP_LATEST_JSON.exists():
        try:
            payload = json.loads(ALPHA_MAP_LATEST_JSON.read_text(encoding="utf-8"))
            context["generated_utc"] = str(payload.get("generated_utc") or "")
            context["pairs_analyzed"] = int(payload.get("pairs_analyzed") or 0)
        except Exception:
            pass

    if not ALPHA_MAP_LATEST_CSV.exists():
        return context

    lookup = {}
    try:
        with ALPHA_MAP_LATEST_CSV.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if not isinstance(row, dict):
                    continue
                pair = str(row.get("pair") or "")
                wsname = str(row.get("wsname") or "")
                key = _pair_token(pair or wsname)
                if not key:
                    continue
                lookup[key] = {
                    "pair": pair,
                    "wsname": wsname,
                    "strategy_mode": str(row.get("strategy_mode") or "watch").strip().lower(),
                    "alpha_edge_score": float(row.get("alpha_edge_score") or 0.0),
                    "momentum_score": float(row.get("momentum_score") or 0.0),
                    "trend_score": float(row.get("trend_score") or 0.0),
                    "reversion_score": float(row.get("reversion_score") or 0.0),
                    "liquidity_score": float(row.get("liquidity_score") or 0.0),
                    "volatility_score": float(row.get("volatility_score") or 0.0),
                    "execution_quality_score": float(row.get("execution_quality_score") or 0.0),
                    "spread_penalty": float(row.get("spread_penalty") or 0.0),
                    "spread_bps": float(row.get("spread_bps") or 0.0),
                    "turnover_24h_usd": float(row.get("turnover_24h_usd") or 0.0),
                    "r_1m_pct": float(row.get("r_1m_pct") or 0.0),
                    "r_5m_pct": float(row.get("r_5m_pct") or 0.0),
                    "r_30m_pct": float(row.get("r_30m_pct") or 0.0),
                    "r_1h_pct": float(row.get("r_1h_pct") or 0.0),
                    "r_24h_pct": float(row.get("r_24h_pct") or 0.0),
                    "hv_24h_pct": float(row.get("hv_24h_pct") or 0.0),
                    "best_buy_hour_utc": int(float(row.get("best_buy_hour_utc") or -1)),
                    "prefilter_score": float(row.get("prefilter_score") or 0.0),
                }
    except Exception:
        return context

    context["available"] = bool(lookup)
    context["lookup"] = lookup
    if context["pairs_analyzed"] <= 0:
        context["pairs_analyzed"] = len(lookup)
    return context


def _load_cluster_context() -> dict:
    context = {
        "available": False,
        "generated_utc": "",
        "pairs_analyzed": 0,
        "lookup": {},
    }
    if not CLUSTER_LATEST_JSON.exists():
        return context

    try:
        payload = json.loads(CLUSTER_LATEST_JSON.read_text(encoding="utf-8"))
    except Exception:
        return context

    rows = payload.get("pair_clusters") or []
    if not isinstance(rows, list):
        return context

    lookup = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        pair = str(row.get("pair") or "")
        wsname = str(row.get("wsname") or "")
        key = _pair_token(pair or wsname)
        if not key:
            continue
        lookup[key] = {
            "pair": pair,
            "wsname": wsname,
            "cluster_score": float(row.get("cluster_score") or 0.0),
            "best_hour_utc": int(float(row.get("best_hour_utc") or -1)),
            "best_weekday_utc": int(float(row.get("best_weekday_utc") or -1)),
            "best_weekday_name": str(row.get("best_weekday_name") or ""),
            "best_hour_score": float(row.get("best_hour_score") or 0.0),
            "best_weekday_score": float(row.get("best_weekday_score") or 0.0),
            "mean_abs_move_pct": float(row.get("mean_abs_move_pct") or 0.0),
            "burst_rate_pct": float(row.get("burst_rate_pct") or 0.0),
            "win_rate_pct": float(row.get("win_rate_pct") or 0.0),
            "turnover_24h_usd": float(row.get("turnover_24h_usd") or 0.0),
            "samples": int(float(row.get("samples") or 0)),
        }

    context["generated_utc"] = str(payload.get("generated_utc") or "")
    context["pairs_analyzed"] = int(payload.get("pairs_analyzed") or len(lookup) or 0)
    context["available"] = bool(lookup)
    context["lookup"] = lookup
    return context


def _alpha_gate_required(validate: bool, gate_cfg: dict[str, object] | None = None) -> bool:
    require_match_live = ALPHA_GATE_REQUIRE_MATCH_LIVE
    if isinstance(gate_cfg, dict) and "require_match_live" in gate_cfg:
        require_match_live = bool(gate_cfg.get("require_match_live"))
    return (not validate) and bool(require_match_live)


def _resolve_alpha_gate(runtime_cfg: dict | None) -> dict[str, object]:
    cfg = runtime_cfg or {}
    return {
        "min_edge": max(0.0, _safe_float(cfg.get("alpha_gate_min_edge"), ALPHA_GATE_MIN_EDGE)),
        "max_spread_bps": max(0.0, _safe_float(cfg.get("alpha_gate_max_spread_bps"), ALPHA_GATE_MAX_SPREAD_BPS)),
        "min_turnover_usd": max(0.0, _safe_float(cfg.get("alpha_gate_min_turnover_usd"), ALPHA_GATE_MIN_TURNOVER_USD)),
        "allow_watch_strategy": bool(cfg.get("alpha_gate_allow_watch_strategy", False)),
        "require_match_live": bool(cfg.get("alpha_gate_require_match_live", ALPHA_GATE_REQUIRE_MATCH_LIVE)),
    }


def _cluster_gate_required(validate: bool, cluster_cfg: dict[str, object] | None = None) -> bool:
    require_alignment_live = CLUSTER_GATE_REQUIRE_ALIGNMENT_LIVE
    if isinstance(cluster_cfg, dict) and "require_alignment_live" in cluster_cfg:
        require_alignment_live = bool(cluster_cfg.get("require_alignment_live"))
    return (not validate) and bool(require_alignment_live)


def _resolve_cluster_gate(runtime_cfg: dict | None) -> dict[str, object]:
    cfg = runtime_cfg or {}
    return {
        "enabled": bool(cfg.get("cluster_gate_enabled", CLUSTER_GATE_ENABLED_DEFAULT)),
        "enforce_time_alignment": bool(
            cfg.get("cluster_enforce_time_alignment", CLUSTER_GATE_ENFORCE_TIME_ALIGNMENT_DEFAULT)
        ),
        "min_pair_score": max(
            0.0,
            _safe_float(cfg.get("cluster_min_pair_score"), CLUSTER_GATE_MIN_PAIR_SCORE),
        ),
        "hour_tolerance": max(
            0,
            _safe_int(cfg.get("cluster_hour_tolerance"), CLUSTER_GATE_HOUR_TOLERANCE),
        ),
        "weekday_tolerance": max(
            0,
            _safe_int(cfg.get("cluster_weekday_tolerance"), CLUSTER_GATE_WEEKDAY_TOLERANCE),
        ),
        "require_alignment_live": bool(
            cfg.get("cluster_require_alignment_live", CLUSTER_GATE_REQUIRE_ALIGNMENT_LIVE)
        ),
    }


def _cyclic_distance(value: int, target: int, modulo: int) -> int:
    if modulo <= 0:
        return abs(value - target)
    raw = abs(value - target) % modulo
    return min(raw, modulo - raw)


def _cluster_gate(
    row: dict,
    cluster_ctx: dict,
    validate: bool,
    cluster_cfg: dict[str, object],
) -> tuple[bool, str, dict | None]:
    if not bool(cluster_cfg.get("enabled", CLUSTER_GATE_ENABLED_DEFAULT)):
        return True, "cluster_gate_disabled", None

    required = _cluster_gate_required(validate, cluster_cfg)
    lookup = cluster_ctx.get("lookup") if isinstance(cluster_ctx, dict) else {}
    if not isinstance(lookup, dict) or not lookup:
        if required:
            return False, "cluster_map_unavailable", None
        return True, "cluster_map_unavailable_validate_mode", None

    pair = _normalize_pair_for_kraken(row.get("pair", ""), row.get("wsname", ""))
    key = _pair_token(pair)
    cluster = lookup.get(key)

    if cluster is None:
        if required:
            return False, "cluster_pair_not_mapped", None
        return True, "cluster_pair_not_mapped_validate_mode", None

    score = float(cluster.get("cluster_score") or 0.0)
    min_pair_score = float(cluster_cfg.get("min_pair_score", CLUSTER_GATE_MIN_PAIR_SCORE))
    if score < min_pair_score:
        return False, f"cluster_score<{min_pair_score}", cluster

    if bool(cluster_cfg.get("enforce_time_alignment", CLUSTER_GATE_ENFORCE_TIME_ALIGNMENT_DEFAULT)):
        best_hour = int(cluster.get("best_hour_utc") or -1)
        best_weekday = int(cluster.get("best_weekday_utc") or -1)
        now_dt = datetime.now(timezone.utc)
        hour_tol = int(cluster_cfg.get("hour_tolerance", CLUSTER_GATE_HOUR_TOLERANCE))
        weekday_tol = int(cluster_cfg.get("weekday_tolerance", CLUSTER_GATE_WEEKDAY_TOLERANCE))

        if best_hour >= 0:
            hour_dist = _cyclic_distance(now_dt.hour, best_hour, 24)
            if hour_dist > hour_tol:
                return False, "cluster_hour_window_miss", cluster

        if best_weekday >= 0:
            weekday_dist = _cyclic_distance(now_dt.weekday(), best_weekday, 7)
            if weekday_dist > weekday_tol:
                return False, "cluster_weekday_window_miss", cluster

    return True, "cluster_gate_ok", cluster


def _resolve_profitability_cfg(runtime_cfg: dict | None) -> dict[str, float]:
    cfg = runtime_cfg or {}
    return {
        "min_net_edge_pct": max(
            0.0,
            _safe_float(cfg.get("profitability_min_net_edge_pct"), PROFITABILITY_MIN_NET_EDGE_PCT),
        ),
        "fee_roundtrip_bps": max(
            0.0,
            _safe_float(cfg.get("profitability_fee_roundtrip_bps"), PROFITABILITY_FEE_ROUNDTRIP_BPS),
        ),
        "slippage_floor_bps": max(
            0.0,
            _safe_float(cfg.get("profitability_slippage_floor_bps"), PROFITABILITY_SLIPPAGE_FLOOR_BPS),
        ),
        "spread_slippage_mult": max(
            0.0,
            _safe_float(cfg.get("profitability_spread_slippage_mult"), PROFITABILITY_SPREAD_SLIPPAGE_MULT),
        ),
        "min_execution_quality_score": max(
            0.0,
            _safe_float(
                cfg.get("profitability_min_execution_quality_score"),
                PROFITABILITY_MIN_EXECUTION_QUALITY_SCORE,
            ),
        ),
        "notional_edge_scale_pct": max(
            0.25,
            _safe_float(
                cfg.get("profitability_notional_edge_scale_pct"),
                PROFITABILITY_NOTIONAL_EDGE_SCALE_PCT,
            ),
        ),
        "notional_floor_mult": _clamp(
            _safe_float(cfg.get("profitability_notional_floor_mult"), PROFITABILITY_NOTIONAL_FLOOR_MULT),
            0.2,
            1.0,
        ),
        "notional_cap_mult": max(
            1.0,
            _safe_float(cfg.get("profitability_notional_cap_mult"), PROFITABILITY_NOTIONAL_CAP_MULT),
        ),
    }


def _annotate_profitability(alpha: dict, profit_cfg: dict[str, float]) -> dict:
    enriched = dict(alpha or {})

    gross_edge_pct = max(0.0, _safe_float(enriched.get("alpha_edge_score"), 0.0))
    spread_bps = max(0.0, _safe_float(enriched.get("spread_bps"), 0.0))
    execution_quality_score = max(0.0, _safe_float(enriched.get("execution_quality_score"), 0.0))
    liquidity_score = max(0.0, _safe_float(enriched.get("liquidity_score"), 0.0))

    quality_norm = _clamp((0.65 * execution_quality_score + 0.35 * liquidity_score) / 20.0, 0.0, 1.0)
    slippage_bps = max(
        profit_cfg["slippage_floor_bps"],
        spread_bps * profit_cfg["spread_slippage_mult"],
    )
    friction_bps = profit_cfg["fee_roundtrip_bps"] + slippage_bps
    net_edge_pct = gross_edge_pct - (friction_bps / 100.0)
    risk_adjusted_net_edge_pct = net_edge_pct * (0.65 + 0.35 * quality_norm)

    enriched.update(
        {
            "gross_edge_pct": round(gross_edge_pct, 6),
            "estimated_fee_bps": round(float(profit_cfg["fee_roundtrip_bps"]), 6),
            "estimated_slippage_bps": round(slippage_bps, 6),
            "estimated_friction_bps": round(friction_bps, 6),
            "net_edge_pct": round(net_edge_pct, 6),
            "risk_adjusted_net_edge_pct": round(risk_adjusted_net_edge_pct, 6),
            "quality_norm": round(quality_norm, 6),
            "execution_quality_score": round(execution_quality_score, 6),
            "liquidity_score": round(liquidity_score, 6),
        }
    )
    return enriched


def _alpha_gate(
    row: dict,
    alpha_ctx: dict,
    validate: bool,
    gate_cfg: dict[str, object],
    profit_cfg: dict[str, float],
) -> tuple[bool, str, dict | None]:
    required = _alpha_gate_required(validate, gate_cfg)
    lookup = alpha_ctx.get("lookup") if isinstance(alpha_ctx, dict) else {}
    if not isinstance(lookup, dict) or not lookup:
        if required:
            return False, "alpha_map_unavailable", None
        return True, "alpha_map_unavailable_validate_mode", None

    pair = _normalize_pair_for_kraken(row.get("pair", ""), row.get("wsname", ""))
    key = _pair_token(pair)
    alpha = lookup.get(key)

    if alpha is None:
        if required:
            return False, "alpha_pair_not_mapped", None
        return True, "alpha_pair_not_mapped_validate_mode", None

    alpha = _annotate_profitability(alpha=alpha, profit_cfg=profit_cfg)

    mode = str(alpha.get("strategy_mode") or "watch").strip().lower()
    edge = float(alpha.get("alpha_edge_score") or 0.0)
    spread = float(alpha.get("spread_bps") or 0.0)
    turnover = float(alpha.get("turnover_24h_usd") or 0.0)
    execution_quality_score = float(alpha.get("execution_quality_score") or 0.0)
    net_edge_pct = float(alpha.get("net_edge_pct") or 0.0)
    min_edge = float(gate_cfg.get("min_edge", ALPHA_GATE_MIN_EDGE))
    max_spread = float(gate_cfg.get("max_spread_bps", ALPHA_GATE_MAX_SPREAD_BPS))
    min_turnover = float(gate_cfg.get("min_turnover_usd", ALPHA_GATE_MIN_TURNOVER_USD))
    min_execution_quality_score = float(
        profit_cfg.get("min_execution_quality_score", PROFITABILITY_MIN_EXECUTION_QUALITY_SCORE)
    )
    min_net_edge_pct = float(profit_cfg.get("min_net_edge_pct", PROFITABILITY_MIN_NET_EDGE_PCT))

    if mode not in ALPHA_GATE_ALLOWED_STRATEGIES:
        if not (mode == "watch" and bool(gate_cfg.get("allow_watch_strategy", False))):
            return False, "alpha_strategy_not_actionable", alpha
    
    if edge < min_edge:
        return False, f"alpha_edge<{min_edge}", alpha
    if spread > max_spread:
        return False, f"alpha_spread>{max_spread}", alpha
    if turnover < min_turnover:
        return False, f"alpha_turnover<{min_turnover}", alpha
    if execution_quality_score < min_execution_quality_score:
        return False, f"alpha_exec_quality<{min_execution_quality_score}", alpha
    if net_edge_pct < min_net_edge_pct:
        return False, f"alpha_net_edge<{min_net_edge_pct}", alpha

    return True, "alpha_gate_ok", alpha


def _refresh_scan(bankroll: float, top_n: int) -> dict:
    """Re-run the live spike hunter scan."""
    sys.path.insert(0, str(ROOT / "code"))
    import kraken_spike_hunter_live as sh  # type: ignore
    return sh.run_scan(bankroll=bankroll, top_n=top_n)


def _load_cached_scan() -> dict | None:
    if not SPIKE_LATEST.exists():
        return None
    try:
        return json.loads(SPIKE_LATEST.read_text(encoding="utf-8"))
    except Exception:
        return None


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value: object, default: int) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _resolve_effective_bankroll(runtime_cfg: dict | None, fallback_bankroll: float) -> tuple[float, dict]:
    cfg = runtime_cfg or {}
    fallback = max(MIN_NOTIONAL_USD, _safe_float(fallback_bankroll, BANKROLL_DEFAULT))

    bankroll_override = _safe_float(cfg.get("bankroll_usd"), 0.0)
    if bankroll_override > 0:
        return bankroll_override, {
            "source": "runtime_cfg.bankroll_usd",
            "source_path": None,
            "source_age_sec": None,
            "source_fresh": True,
        }

    source_path_raw = str(cfg.get("compounding_equity_source_path") or "").strip()
    source_path = Path(source_path_raw) if source_path_raw else DEFAULT_COMPOUNDING_EQUITY_SOURCE
    if not source_path.is_absolute():
        source_path = ROOT / source_path
    max_age_sec = max(
        0.0,
        _safe_float(cfg.get("compounding_equity_max_age_sec"), COMPOUNDING_EQUITY_MAX_AGE_SEC),
    )
    source_label = str(source_path)
    try:
        source_label = str(source_path.relative_to(ROOT))
    except Exception:
        pass

    if source_path.exists():
        try:
            age_sec = max(0.0, time.time() - source_path.stat().st_mtime)
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            equity = _safe_float(payload.get("current_equity"), 0.0)
            if equity <= 0:
                equity = _safe_float(payload.get("current_equity_usd"), 0.0)
            if equity <= 0:
                equity = _safe_float(payload.get("equity_usd"), 0.0)
            source_fresh = (max_age_sec <= 0) or (age_sec <= max_age_sec)
            if equity > 0 and source_fresh:
                return max(MIN_NOTIONAL_USD, equity), {
                    "source": "compounding_equity_source",
                    "source_path": source_label,
                    "source_age_sec": round(float(age_sec), 3),
                    "source_fresh": True,
                }
            return fallback, {
                "source": "compounding_equity_source_stale_or_invalid",
                "source_path": source_label,
                "source_age_sec": round(float(age_sec), 3),
                "source_fresh": False,
            }
        except Exception:
            pass

    return fallback, {
        "source": "cli_fallback",
        "source_path": source_label,
        "source_age_sec": None,
        "source_fresh": False,
    }


def _resolve_strategy_runtime(runtime_cfg: dict | None, bankroll: float, validate: bool) -> dict:
    cfg = runtime_cfg or {}
    strategy_mode = str(cfg.get("strategy_mode") or STRATEGY_MODE_HYBRID).strip().lower()
    if strategy_mode not in STRATEGY_MODES:
        strategy_mode = STRATEGY_MODE_HYBRID

    effective_bankroll = max(MIN_NOTIONAL_USD, _safe_float(bankroll, BANKROLL_DEFAULT))
    compounding_enabled = bool(cfg.get("compounding_enabled", COMPOUNDING_ENABLED_DEFAULT))
    reference_bankroll_usd = max(
        MIN_NOTIONAL_USD,
        _safe_float(
            cfg.get("compounding_reference_bankroll_usd"),
            COMPOUNDING_REFERENCE_BANKROLL_USD,
        ),
    )
    compounding_growth_sensitivity = _clamp(
        _safe_float(
            cfg.get("compounding_growth_sensitivity"),
            COMPOUNDING_GROWTH_SENSITIVITY,
        ),
        0.1,
        2.5,
    )
    compounding_min_bankroll_mult = _clamp(
        _safe_float(
            cfg.get("compounding_min_bankroll_mult"),
            COMPOUNDING_MIN_BANKROLL_MULT,
        ),
        0.25,
        1.0,
    )
    compounding_max_bankroll_mult = max(
        1.0,
        _safe_float(
            cfg.get("compounding_max_bankroll_mult"),
            COMPOUNDING_MAX_BANKROLL_MULT,
        ),
    )
    bankroll_ratio = effective_bankroll / max(reference_bankroll_usd, MIN_NOTIONAL_USD)
    raw_bankroll_mult = bankroll_ratio ** compounding_growth_sensitivity if compounding_enabled else 1.0
    compounding_bankroll_mult = (
        _clamp(raw_bankroll_mult, compounding_min_bankroll_mult, compounding_max_bankroll_mult)
        if compounding_enabled
        else 1.0
    )

    hard_max_notional = MAX_NOTIONAL_USD_VALIDATE_HARD if validate else MAX_NOTIONAL_USD_LIVE_HARD
    max_notional_usd = _clamp(
        _safe_float(cfg.get("max_notional_usd"), MAX_NOTIONAL_USD),
        MIN_NOTIONAL_USD,
        hard_max_notional,
    )

    moonshot_bankroll_frac = _clamp(
        _safe_float(cfg.get("moonshot_bankroll_frac"), 0.18),
        0.02,
        0.60,
    )
    moonshot_target_notional_usd = _clamp(
        max(effective_bankroll * moonshot_bankroll_frac, MIN_NOTIONAL_USD),
        MIN_NOTIONAL_USD,
        max_notional_usd,
    )
    quickhit_base_target_notional_usd = _clamp(
        _safe_float(cfg.get("quickhit_target_notional_usd"), 12.0),
        MIN_NOTIONAL_USD,
        max_notional_usd,
    )
    quickhit_target_notional_usd = _clamp(
        quickhit_base_target_notional_usd * compounding_bankroll_mult,
        MIN_NOTIONAL_USD,
        max_notional_usd,
    )
    swing_base_target_notional_usd = _clamp(
        _safe_float(cfg.get("swing_target_notional_usd"), 16.0),
        MIN_NOTIONAL_USD,
        max_notional_usd,
    )
    swing_target_notional_usd = _clamp(
        swing_base_target_notional_usd * compounding_bankroll_mult,
        MIN_NOTIONAL_USD,
        max_notional_usd,
    )

    return {
        "strategy_mode": strategy_mode,
        "effective_bankroll_usd": effective_bankroll,
        "compounding_enabled": compounding_enabled,
        "compounding_reference_bankroll_usd": reference_bankroll_usd,
        "compounding_growth_sensitivity": compounding_growth_sensitivity,
        "compounding_min_bankroll_mult": compounding_min_bankroll_mult,
        "compounding_max_bankroll_mult": compounding_max_bankroll_mult,
        "compounding_bankroll_ratio": bankroll_ratio,
        "compounding_bankroll_mult": compounding_bankroll_mult,
        "max_notional_usd": max_notional_usd,
        "moonshot_target_notional_usd": moonshot_target_notional_usd,
        "moonshot_max_per_cycle": max(0, _safe_int(cfg.get("moonshot_max_per_cycle"), 1)),
        "moonshot_min_edge": _safe_float(cfg.get("moonshot_min_edge"), 5.5),
        "moonshot_min_dip_pct": _safe_float(cfg.get("moonshot_min_dip_pct"), 18.0),
        "moonshot_max_rsi": _safe_float(cfg.get("moonshot_max_rsi"), 24.0),
        "moonshot_min_rebound_15m_pct": _safe_float(cfg.get("moonshot_min_rebound_15m_pct"), 0.08),
        "moonshot_max_spread_bps": _safe_float(cfg.get("moonshot_max_spread_bps"), 22.0),
        "moonshot_min_turnover_usd": _safe_float(cfg.get("moonshot_min_turnover_usd"), 200000.0),
        "quickhit_target_notional_usd": quickhit_target_notional_usd,
        "quickhit_max_per_cycle": max(0, _safe_int(cfg.get("quickhit_max_per_cycle"), 4)),
        "quickhit_min_edge": _safe_float(cfg.get("quickhit_min_edge"), 4.0),
        "quickhit_min_r1m_pct": _safe_float(cfg.get("quickhit_min_r1m_pct"), 0.05),
        "quickhit_min_r15m_pct": _safe_float(cfg.get("quickhit_min_r15m_pct"), 0.15),
        "quickhit_min_m4h_pct": _safe_float(cfg.get("quickhit_min_m4h_pct"), -8.0),
        "quickhit_max_spread_bps": _safe_float(cfg.get("quickhit_max_spread_bps"), 24.0),
        "quickhit_min_turnover_usd": _safe_float(cfg.get("quickhit_min_turnover_usd"), 180000.0),
        "quickhit_base_target_notional_usd": quickhit_base_target_notional_usd,
        "swing_target_notional_usd": swing_target_notional_usd,
        "swing_max_per_cycle": max(0, _safe_int(cfg.get("swing_max_per_cycle"), 2)),
        "swing_min_edge": _safe_float(cfg.get("swing_min_edge"), 4.5),
        "swing_min_r1h_pct": _safe_float(cfg.get("swing_min_r1h_pct"), 0.12),
        "swing_min_m4h_pct": _safe_float(cfg.get("swing_min_m4h_pct"), -3.0),
        "swing_max_spread_bps": _safe_float(cfg.get("swing_max_spread_bps"), 30.0),
        "swing_min_turnover_usd": _safe_float(cfg.get("swing_min_turnover_usd"), 150000.0),
        "swing_base_target_notional_usd": swing_base_target_notional_usd,
    }


def _lane_allowed(strategy_mode: str, lane: str) -> bool:
    if strategy_mode == STRATEGY_MODE_HYBRID:
        return True
    if strategy_mode == STRATEGY_MODE_MOONSHOT:
        return lane == LANE_MOONSHOT
    if strategy_mode == STRATEGY_MODE_QUICKHIT:
        return lane == LANE_QUICKHIT
    if strategy_mode == STRATEGY_MODE_SWING:
        return lane == LANE_SWING
    return True


def _classify_strategy_lane(row: dict, alpha_row: dict | None, strategy_cfg: dict) -> dict:
    alpha = alpha_row or {}
    strategy_mode = str(strategy_cfg.get("strategy_mode") or STRATEGY_MODE_HYBRID)

    dip_pct = _safe_float(row.get("dip_from_high_pct"), 0.0)
    rsi = _safe_float(row.get("rsi"), 50.0)
    vol_surge = _safe_float(row.get("vol_surge"), 0.0)
    score = _safe_float(row.get("score"), 0.0)
    m4h = _safe_float(row.get("m4h"), 0.0)
    fallback_r_1h = m4h / 4.0 if m4h else 0.0
    fallback_r_5m = m4h / 48.0 if m4h else 0.0
    fallback_r_30m = m4h / 8.0 if m4h else 0.0
    fallback_r_1m = m4h / 240.0 if m4h else 0.0
    fallback_r_15m = 0.65 * fallback_r_5m + 0.35 * fallback_r_30m
    fallback_edge = max(0.0, score / 10.0)
    fallback_turnover = _safe_float(row.get("vol_24h_usd"), 0.0)
    fallback_spread = 18.0
    signals = {str(x).upper() for x in (row.get("signals") or [])}

    if not alpha:
        if "EXTREME_OVERSOLD" in signals or "DEEP_DIP" in signals:
            alpha_mode = "mean_reversion_snapback"
        elif fallback_r_1h > 0.0:
            alpha_mode = "trend_follow_swing"
        else:
            alpha_mode = "momentum_snipe"
    else:
        alpha_mode = str(alpha.get("strategy_mode") or "watch").strip().lower()

    raw_edge = _safe_float(alpha.get("alpha_edge_score"), fallback_edge)
    net_edge = _safe_float(alpha.get("net_edge_pct"), raw_edge)
    risk_adjusted_net_edge = _safe_float(alpha.get("risk_adjusted_net_edge_pct"), net_edge)
    edge = risk_adjusted_net_edge
    spread = _safe_float(alpha.get("spread_bps"), fallback_spread)
    turnover = _safe_float(alpha.get("turnover_24h_usd"), fallback_turnover)
    trend_score = _safe_float(alpha.get("trend_score"), 0.0)
    execution_quality_score = _safe_float(alpha.get("execution_quality_score"), 0.0)
    liquidity_score = _safe_float(alpha.get("liquidity_score"), 0.0)
    estimated_friction_bps = _safe_float(alpha.get("estimated_friction_bps"), spread)

    r_1m = _safe_float(alpha.get("r_1m_pct"), fallback_r_1m)
    r_5m = _safe_float(alpha.get("r_5m_pct"), fallback_r_5m)
    r_30m = _safe_float(alpha.get("r_30m_pct"), fallback_r_30m)
    r_1h = _safe_float(alpha.get("r_1h_pct"), fallback_r_1h)
    r_15m = 0.65 * r_5m + 0.35 * r_30m
    if not alpha:
        r_15m = fallback_r_15m

    candidates: list[tuple[str, float, str]] = []

    moonshot_ready = (
        _lane_allowed(strategy_mode, LANE_MOONSHOT)
        and edge >= _safe_float(strategy_cfg.get("moonshot_min_edge"), 5.5)
        and spread <= _safe_float(strategy_cfg.get("moonshot_max_spread_bps"), 22.0)
        and turnover >= _safe_float(strategy_cfg.get("moonshot_min_turnover_usd"), 200000.0)
        and (
            dip_pct >= _safe_float(strategy_cfg.get("moonshot_min_dip_pct"), 18.0)
            or rsi <= _safe_float(strategy_cfg.get("moonshot_max_rsi"), 24.0)
            or "EXTREME_OVERSOLD" in signals
            or "DEEP_DIP" in signals
        )
        and r_15m >= _safe_float(strategy_cfg.get("moonshot_min_rebound_15m_pct"), 0.08)
    )
    if moonshot_ready:
        mode_bonus = 4.0 if alpha_mode == "mean_reversion_snapback" else 0.0
        moonshot_score = (
            edge * 2.2
            + max(dip_pct, 0.0) * 0.45
            + max(25.0 - rsi, 0.0) * 0.55
            + max(r_15m, 0.0) * 5.5
            + max(vol_surge, 0.0) * 1.25
            + mode_bonus
        )
        candidates.append((LANE_MOONSHOT, moonshot_score, "deep dip + rebound + liquidity"))

    quickhit_ready = (
        _lane_allowed(strategy_mode, LANE_QUICKHIT)
        and edge >= _safe_float(strategy_cfg.get("quickhit_min_edge"), 4.0)
        and spread <= _safe_float(strategy_cfg.get("quickhit_max_spread_bps"), 24.0)
        and turnover >= _safe_float(strategy_cfg.get("quickhit_min_turnover_usd"), 180000.0)
        and r_1m >= _safe_float(strategy_cfg.get("quickhit_min_r1m_pct"), 0.05)
        and r_15m >= _safe_float(strategy_cfg.get("quickhit_min_r15m_pct"), 0.15)
        and m4h >= _safe_float(strategy_cfg.get("quickhit_min_m4h_pct"), -8.0)
    )
    if quickhit_ready:
        mode_bonus = 4.0 if alpha_mode == "momentum_snipe" else 0.0
        quickhit_score = (
            edge * 2.0
            + max(r_1m, 0.0) * 9.0
            + max(r_15m, 0.0) * 4.5
            + max(r_1h, 0.0) * 1.8
            + max(score, 0.0) * 0.15
            - spread * 0.04
            + mode_bonus
        )
        candidates.append((LANE_QUICKHIT, quickhit_score, "micro-momentum + execution quality"))

    swing_ready = (
        _lane_allowed(strategy_mode, LANE_SWING)
        and edge >= _safe_float(strategy_cfg.get("swing_min_edge"), 4.5)
        and spread <= _safe_float(strategy_cfg.get("swing_max_spread_bps"), 30.0)
        and turnover >= _safe_float(strategy_cfg.get("swing_min_turnover_usd"), 150000.0)
        and r_1h >= _safe_float(strategy_cfg.get("swing_min_r1h_pct"), 0.12)
        and m4h >= _safe_float(strategy_cfg.get("swing_min_m4h_pct"), -3.0)
    )
    if swing_ready:
        mode_bonus = 3.0 if alpha_mode == "trend_follow_swing" else 0.0
        swing_score = (
            edge * 1.8
            + max(r_1h, 0.0) * 3.8
            + max(m4h, 0.0) * 1.3
            + max(trend_score, 0.0) * 0.08
            + mode_bonus
        )
        candidates.append((LANE_SWING, swing_score, "trend continuation with healthy 1h/4h"))

    if not candidates:
        return {
            "lane": None,
            "lane_reason": "no_strategy_lane_match",
            "lane_score": 0.0,
            "alpha_mode": alpha_mode,
            "profitability": {
                "raw_edge_pct": round(raw_edge, 6),
                "net_edge_pct": round(net_edge, 6),
                "risk_adjusted_net_edge_pct": round(risk_adjusted_net_edge, 6),
                "estimated_friction_bps": round(estimated_friction_bps, 6),
                "execution_quality_score": round(execution_quality_score, 6),
                "liquidity_score": round(liquidity_score, 6),
            },
            "tf": {
                "r_1m_pct": round(r_1m, 6),
                "r_15m_pct": round(r_15m, 6),
                "r_1h_pct": round(r_1h, 6),
                "r_4h_pct": round(m4h, 6),
            },
        }

    lane, lane_score, lane_reason = max(candidates, key=lambda x: x[1])
    return {
        "lane": lane,
        "lane_reason": lane_reason,
        "lane_score": round(float(lane_score), 6),
        "alpha_mode": alpha_mode,
        "profitability": {
            "raw_edge_pct": round(raw_edge, 6),
            "net_edge_pct": round(net_edge, 6),
            "risk_adjusted_net_edge_pct": round(risk_adjusted_net_edge, 6),
            "estimated_friction_bps": round(estimated_friction_bps, 6),
            "execution_quality_score": round(execution_quality_score, 6),
            "liquidity_score": round(liquidity_score, 6),
        },
        "tf": {
            "r_1m_pct": round(r_1m, 6),
            "r_15m_pct": round(r_15m, 6),
            "r_1h_pct": round(r_1h, 6),
            "r_4h_pct": round(m4h, 6),
        },
    }


def _lane_cycle_cap(lane: str, strategy_cfg: dict) -> int:
    if lane == LANE_MOONSHOT:
        return max(0, _safe_int(strategy_cfg.get("moonshot_max_per_cycle"), 1))
    if lane == LANE_QUICKHIT:
        return max(0, _safe_int(strategy_cfg.get("quickhit_max_per_cycle"), 4))
    if lane == LANE_SWING:
        return max(0, _safe_int(strategy_cfg.get("swing_max_per_cycle"), 2))
    return 0


def _resolve_lane_notional_usd(
    row: dict,
    lane: str,
    strategy_cfg: dict,
    strategy_meta: dict | None = None,
) -> tuple[float, dict]:
    suggested_usd = float(row.get("size_usd", 0)) or float(row.get("size_pct", 0)) * BANKROLL_DEFAULT / 100
    if lane == LANE_MOONSHOT:
        target = max(suggested_usd, _safe_float(strategy_cfg.get("moonshot_target_notional_usd"), MAX_NOTIONAL_USD))
    elif lane == LANE_QUICKHIT:
        target = _safe_float(strategy_cfg.get("quickhit_target_notional_usd"), min(12.0, MAX_NOTIONAL_USD))
    elif lane == LANE_SWING:
        target = max(suggested_usd * 0.8, _safe_float(strategy_cfg.get("swing_target_notional_usd"), min(16.0, MAX_NOTIONAL_USD)))
    else:
        target = suggested_usd or MAX_NOTIONAL_USD

    sizing_meta = {
        "base_target_usd": round(float(target), 6),
        "conviction_mult": 1.0,
        "edge_for_sizing_pct": 0.0,
    }

    profit_meta = (strategy_meta or {}).get("profitability") if isinstance(strategy_meta, dict) else None
    edge_for_sizing = _safe_float(
        (profit_meta or {}).get("risk_adjusted_net_edge_pct"),
        _safe_float((profit_meta or {}).get("net_edge_pct"), 0.0),
    )
    if edge_for_sizing > 0:
        edge_scale = max(
            0.25,
            _safe_float(
                strategy_cfg.get("profitability_notional_edge_scale_pct"),
                PROFITABILITY_NOTIONAL_EDGE_SCALE_PCT,
            ),
        )
        floor_mult = _clamp(
            _safe_float(
                strategy_cfg.get("profitability_notional_floor_mult"),
                PROFITABILITY_NOTIONAL_FLOOR_MULT,
            ),
            0.2,
            1.0,
        )
        cap_mult = max(
            1.0,
            _safe_float(
                strategy_cfg.get("profitability_notional_cap_mult"),
                PROFITABILITY_NOTIONAL_CAP_MULT,
            ),
        )
        conviction_mult = _clamp(floor_mult + (edge_for_sizing / edge_scale), floor_mult, cap_mult)
        target *= conviction_mult
        sizing_meta = {
            "base_target_usd": sizing_meta["base_target_usd"],
            "conviction_mult": round(float(conviction_mult), 6),
            "edge_for_sizing_pct": round(float(edge_for_sizing), 6),
        }

    max_notional = _safe_float(strategy_cfg.get("max_notional_usd"), MAX_NOTIONAL_USD)
    return _clamp(target, MIN_NOTIONAL_USD, max_notional), sizing_meta


def _load_cached_scan_if_fresh(max_age_sec: float) -> dict | None:
    if max_age_sec <= 0:
        return None
    if not SPIKE_LATEST.exists():
        return None
    try:
        age_sec = time.time() - SPIKE_LATEST.stat().st_mtime
    except Exception:
        return None
    if age_sec > max_age_sec:
        return None
    return _load_cached_scan()


def _eligible(
    row: dict,
    alpha_ctx: dict,
    cluster_ctx: dict,
    validate: bool,
    gate_cfg: dict[str, object],
    profit_cfg: dict[str, float],
    cluster_cfg: dict[str, object],
) -> tuple[bool, str, dict | None, dict | None]:
    score = float(row.get("score", 0))
    signals = row.get("signals") or []
    vol_24h = float(row.get("vol_24h_usd", 0))
    price   = float(row.get("price", 0))
    allow_watch = bool((gate_cfg or {}).get("allow_watch_strategy", False))
    watch_only = len(signals) == 1 and str(signals[0]).upper() == "WATCH"

    if watch_only and not allow_watch:
        return False, "watch_only", None, None
    if score < MIN_SCORE:
        return False, f"score<{MIN_SCORE}", None, None
    if vol_24h < MIN_24H_VOL_USD:
        return False, f"vol_24h<{MIN_24H_VOL_USD}", None, None
    if price <= 0:
        return False, "zero_price", None, None

    alpha_ok, alpha_reason, alpha_row = _alpha_gate(row, alpha_ctx, validate, gate_cfg, profit_cfg)
    if not alpha_ok:
        return False, alpha_reason, alpha_row, None

    cluster_ok, cluster_reason, cluster_row = _cluster_gate(
        row=row,
        cluster_ctx=cluster_ctx,
        validate=validate,
        cluster_cfg=cluster_cfg,
    )
    if not cluster_ok:
        return False, cluster_reason, alpha_row, cluster_row

    return True, "ok", alpha_row, cluster_row


def _compute_throughput_targets(
    leaderboard: list[dict],
    alpha_ctx: dict,
    cluster_ctx: dict,
    validate: bool,
    pending_count: int,
    gate_cfg: dict[str, object],
    profit_cfg: dict[str, float],
    cluster_cfg: dict[str, object],
    runtime_cfg: dict | None,
) -> dict[str, int | bool]:
    cfg = runtime_cfg or {}

    base_pending = max(1, _safe_int(cfg.get("max_pending_tickets"), MAX_PENDING_TICKETS))
    hard_pending = MAX_PENDING_TICKETS_VALIDATE_HARD if validate else MAX_PENDING_TICKETS_LIVE_HARD
    target_pending = min(base_pending, hard_pending)

    base_cycle = max(1, _safe_int(cfg.get("max_cycle_emits"), MAX_CYCLE_EMITS))
    hard_cycle = MAX_CYCLE_EMITS_VALIDATE_HARD if validate else MAX_CYCLE_EMITS_LIVE_HARD
    target_cycle = min(base_cycle, hard_cycle)

    adaptive_queue = bool(cfg.get("adaptive_queue", ADAPTIVE_QUEUE_DEFAULT))
    actionable = 0
    strong = 0
    for row in leaderboard:
        ok, _why, alpha_row, _cluster_row = _eligible(
            row,
            alpha_ctx=alpha_ctx,
            cluster_ctx=cluster_ctx,
            validate=validate,
            gate_cfg=gate_cfg,
            profit_cfg=profit_cfg,
            cluster_cfg=cluster_cfg,
        )
        if not ok:
            continue
        actionable += 1
        if float((alpha_row or {}).get("alpha_edge_score") or 0.0) >= ADAPTIVE_STRONG_EDGE:
            strong += 1

    if adaptive_queue and actionable > 0:
        # Expand toward available high-confidence opportunities, capped by mode.
        dynamic_pending = pending_count + actionable + min(strong, 4)
        target_pending = min(hard_pending, max(target_pending, dynamic_pending))
        target_cycle = min(hard_cycle, max(target_cycle, min(actionable, hard_cycle)))

    slots_available = max(0, target_pending - pending_count)
    cycle_emit_budget = min(slots_available, target_cycle)
    return {
        "adaptive_queue": adaptive_queue,
        "target_pending": target_pending,
        "target_cycle": target_cycle,
        "slots_available": slots_available,
        "cycle_emit_budget": cycle_emit_budget,
        "actionable_candidates": actionable,
        "strong_candidates": strong,
    }


def _build_ticket(
    row: dict,
    controller: str,
    validate: bool,
    note: str,
    alpha_row: dict | None = None,
    cluster_row: dict | None = None,
    strategy_lane: str | None = None,
    strategy_meta: dict | None = None,
    strategy_cfg: dict | None = None,
) -> dict | None:
    pair = _normalize_pair_for_kraken(row.get("pair", ""), row.get("wsname", ""))
    if not pair:
        return None
    price = float(row["price"])
    strat_cfg = strategy_cfg if isinstance(strategy_cfg, dict) else {}
    strategy_payload = dict(strategy_meta or {})
    sizing_meta = {
        "base_target_usd": 0.0,
        "conviction_mult": 1.0,
        "edge_for_sizing_pct": 0.0,
    }
    if strategy_lane:
        notional, sizing_meta = _resolve_lane_notional_usd(
            row=row,
            lane=strategy_lane,
            strategy_cfg=strat_cfg,
            strategy_meta=strategy_payload,
        )
    else:
        # Fallback for legacy callsites.
        suggested_usd = float(row.get("size_usd", 0)) or float(row.get("size_pct", 0)) * BANKROLL_DEFAULT / 100
        max_notional = _safe_float(strat_cfg.get("max_notional_usd"), MAX_NOTIONAL_USD)
        notional = max(MIN_NOTIONAL_USD, min(max_notional, suggested_usd or max_notional))
        sizing_meta = {
            "base_target_usd": round(float(suggested_usd or max_notional), 6),
            "conviction_mult": 1.0,
            "edge_for_sizing_pct": 0.0,
        }
    strategy_payload["sizing"] = sizing_meta
    volume_base = notional / price
    if volume_base <= 0:
        return None

    userref = int(time.time())
    ticket_id = f"TICKET-{int(time.time()*1000)}-{pair}"
    return {
        "ticket_id":     ticket_id,
        "timestamp":     _utc_iso(),
        "controller":    controller,
        "pair":          pair,
        "side":          "buy",  # spot long-only setups
        "notional_usd":  round(notional, 2),
        "volume_base":   volume_base,
        "payload": {
            "pair":      pair,
            "type":      "buy",
            "ordertype": "market",
            "volume":    _round_volume(volume_base),
            "validate":  "true" if validate else "false",
            "userref":   userref,
        },
        "approval_state": "PENDING_HUMAN_APPROVAL",
        "note": note,
        "scanner_meta": {
            "score":      row.get("score"),
            "signals":    row.get("signals"),
            "rsi":        row.get("rsi"),
            "dip_pct":    row.get("dip_from_high_pct"),
            "vol_surge":  row.get("vol_surge"),
            "m4h":        row.get("m4h"),
            "m24h":       row.get("m24h"),
            "vol_24h_usd": row.get("vol_24h_usd"),
            "wsname":     row.get("wsname"),
            "source":     "spike_hunter_v1",
            "strategy_lane": strategy_lane,
            "strategy": strategy_payload,
            "alpha_gate": {
                "enabled": True,
                "strategy_mode": (alpha_row or {}).get("strategy_mode"),
                "alpha_edge_score": (alpha_row or {}).get("alpha_edge_score"),
                "spread_bps": (alpha_row or {}).get("spread_bps"),
                "turnover_24h_usd": (alpha_row or {}).get("turnover_24h_usd"),
                "execution_quality_score": (alpha_row or {}).get("execution_quality_score"),
                "liquidity_score": (alpha_row or {}).get("liquidity_score"),
                "estimated_friction_bps": (alpha_row or {}).get("estimated_friction_bps"),
                "gross_edge_pct": (alpha_row or {}).get("gross_edge_pct"),
                "net_edge_pct": (alpha_row or {}).get("net_edge_pct"),
                "risk_adjusted_net_edge_pct": (alpha_row or {}).get("risk_adjusted_net_edge_pct"),
                "r_1h_pct": (alpha_row or {}).get("r_1h_pct"),
                "r_24h_pct": (alpha_row or {}).get("r_24h_pct"),
                "best_buy_hour_utc": (alpha_row or {}).get("best_buy_hour_utc"),
            },
            "cluster_target": {
                "enabled": cluster_row is not None,
                "cluster_score": (cluster_row or {}).get("cluster_score"),
                "best_hour_utc": (cluster_row or {}).get("best_hour_utc"),
                "best_weekday_utc": (cluster_row or {}).get("best_weekday_utc"),
                "best_weekday_name": (cluster_row or {}).get("best_weekday_name"),
                "best_hour_score": (cluster_row or {}).get("best_hour_score"),
                "best_weekday_score": (cluster_row or {}).get("best_weekday_score"),
                "mean_abs_move_pct": (cluster_row or {}).get("mean_abs_move_pct"),
                "burst_rate_pct": (cluster_row or {}).get("burst_rate_pct"),
                "win_rate_pct": (cluster_row or {}).get("win_rate_pct"),
                "samples": (cluster_row or {}).get("samples"),
            },
        },
    }


def emit_tickets(use_cached: bool, validate: bool, controller: str,
                 bankroll: float, top_n: int,
                 auto_fire_score: float | None = None,
                 gateway_url: str = "http://127.0.0.1:8787",
                 scan_max_age_sec: float = SCAN_MAX_AGE_SEC_DEFAULT,
                 runtime_cfg: dict | None = None) -> dict:
    cycle_authority = _require_live_authority(
        validate=validate,
        controller=controller,
        action="live ticket cycle",
    )
    rt_cfg = runtime_cfg if isinstance(runtime_cfg, dict) else _read_runtime_config(
        default_threshold=auto_fire_score,
        default_enabled=True,
    )
    effective_bankroll, bankroll_meta = _resolve_effective_bankroll(rt_cfg, bankroll)

    scan_source = "fresh_scan"
    scan = _load_cached_scan() if use_cached else _load_cached_scan_if_fresh(scan_max_age_sec)
    if scan is not None:
        scan_source = "cached_forced" if use_cached else "cached_fresh"
    if scan is None:
        scan = _refresh_scan(bankroll=effective_bankroll, top_n=top_n)
        # Archive every fresh scan for later backtesting.
        _archive_scan(scan)

    leaderboard = scan.get("leaderboard") or []
    alpha_ctx = _load_alpha_map_context()
    cluster_ctx = _load_cluster_context()
    gate_cfg = _resolve_alpha_gate(rt_cfg)
    cluster_cfg = _resolve_cluster_gate(rt_cfg)
    profit_cfg = _resolve_profitability_cfg(rt_cfg)
    strategy_cfg = _resolve_strategy_runtime(runtime_cfg=rt_cfg, bankroll=effective_bankroll, validate=validate)
    strategy_cfg.update(
        {
            "profitability_notional_edge_scale_pct": profit_cfg.get(
                "notional_edge_scale_pct",
                PROFITABILITY_NOTIONAL_EDGE_SCALE_PCT,
            ),
            "profitability_notional_floor_mult": profit_cfg.get(
                "notional_floor_mult",
                PROFITABILITY_NOTIONAL_FLOOR_MULT,
            ),
            "profitability_notional_cap_mult": profit_cfg.get(
                "notional_cap_mult",
                PROFITABILITY_NOTIONAL_CAP_MULT,
            ),
        }
    )
    rows = _load_queue()
    rows, queue_cleanup = _compact_pending_queue(rows, rt_cfg)
    if queue_cleanup.get("changed"):
        _save_queue(rows)

    # Pairs already pending or in flight ─ skip duplicates
    blocked_pairs = {
        r.get("pair")
        for r in rows
        if r.get("approval_state") in COOLDOWN_PAIRS_STATES
    }
    pending_count = sum(
        1 for r in rows if r.get("approval_state") == "PENDING_HUMAN_APPROVAL"
    )
    throughput = _compute_throughput_targets(
        leaderboard=leaderboard,
        alpha_ctx=alpha_ctx,
        cluster_ctx=cluster_ctx,
        validate=validate,
        pending_count=pending_count,
        gate_cfg=gate_cfg,
        profit_cfg=profit_cfg,
        cluster_cfg=cluster_cfg,
        runtime_cfg=rt_cfg,
    )
    slots = int(throughput["cycle_emit_budget"])

    emitted = []
    skipped = []
    alpha_gate_pass_count = 0
    alpha_gate_fail_count = 0
    cluster_gate_pass_count = 0
    cluster_gate_fail_count = 0
    profitability_gate_fail_count = 0
    lane_emitted_counts = {lane: 0 for lane in LANES}
    lane_skip_counts = {lane: 0 for lane in LANES}

    for row in leaderboard:
        if slots <= 0:
            break
        pair = _normalize_pair_for_kraken(row.get("pair", ""), row.get("wsname", ""))
        if pair in blocked_pairs:
            skipped.append({"pair": pair, "reason": "in_queue"})
            continue
        ok, why, alpha_row, cluster_row = _eligible(
            row,
            alpha_ctx=alpha_ctx,
            cluster_ctx=cluster_ctx,
            validate=validate,
            gate_cfg=gate_cfg,
            profit_cfg=profit_cfg,
            cluster_cfg=cluster_cfg,
        )
        if not ok:
            skipped.append({"pair": pair, "reason": why})
            if str(why).startswith("alpha_"):
                alpha_gate_fail_count += 1
            if str(why).startswith("cluster_"):
                cluster_gate_fail_count += 1
            if str(why).startswith("alpha_net_edge") or str(why).startswith("alpha_exec_quality"):
                profitability_gate_fail_count += 1
            continue
        if alpha_row:
            alpha_gate_pass_count += 1
        if cluster_row:
            cluster_gate_pass_count += 1

        strat = _classify_strategy_lane(row=row, alpha_row=alpha_row, strategy_cfg=strategy_cfg)
        lane = str(strat.get("lane") or "")
        if not lane:
            skipped.append({"pair": pair, "reason": str(strat.get("lane_reason") or "no_strategy_lane_match")})
            continue

        lane_cap = _lane_cycle_cap(lane, strategy_cfg)
        if lane_emitted_counts.get(lane, 0) >= lane_cap:
            lane_skip_counts[lane] = lane_skip_counts.get(lane, 0) + 1
            skipped.append({"pair": pair, "reason": f"lane_budget_exhausted:{lane}"})
            continue

        ticket = _build_ticket(
            row,
            controller=controller,
            validate=validate,
            note=(
                f"auto_ticket_producer: score={row.get('score')} "
                f"signals={row.get('signals')} "
                f"lane={lane} "
                f"alpha_edge={(alpha_row or {}).get('alpha_edge_score', 'n/a')} "
                f"net_edge={(strat.get('profitability') or {}).get('risk_adjusted_net_edge_pct', 'n/a')} "
                f"friction_bps={(strat.get('profitability') or {}).get('estimated_friction_bps', 'n/a')} "
                f"r1m={strat.get('tf', {}).get('r_1m_pct')} "
                f"r15m={strat.get('tf', {}).get('r_15m_pct')} "
                f"r1h={strat.get('tf', {}).get('r_1h_pct')} "
                f"r4h={strat.get('tf', {}).get('r_4h_pct')}"
            ),
            alpha_row=alpha_row,
            cluster_row=cluster_row,
            strategy_lane=lane,
            strategy_meta=strat,
            strategy_cfg=strategy_cfg,
        )
        if not ticket:
            skipped.append({"pair": pair, "reason": "build_failed"})
            continue
        rows.append(ticket)
        blocked_pairs.add(pair)
        lane_emitted_counts[lane] = lane_emitted_counts.get(lane, 0) + 1
        emitted.append({
            "ticket_id": ticket["ticket_id"],
            "pair": pair,
            "score": row.get("score"),
            "signals": row.get("signals"),
            "strategy_lane": lane,
            "strategy_reason": strat.get("lane_reason"),
            "strategy_lane_score": strat.get("lane_score"),
            "tf": strat.get("tf"),
            "alpha_edge_score": (alpha_row or {}).get("alpha_edge_score"),
            "alpha_strategy_mode": (alpha_row or {}).get("strategy_mode"),
            "cluster_score": (cluster_row or {}).get("cluster_score"),
            "cluster_best_hour_utc": (cluster_row or {}).get("best_hour_utc"),
            "cluster_best_weekday_utc": (cluster_row or {}).get("best_weekday_utc"),
            "cluster_best_weekday_name": (cluster_row or {}).get("best_weekday_name"),
            "net_edge_pct": (strat.get("profitability") or {}).get("net_edge_pct"),
            "risk_adjusted_net_edge_pct": (strat.get("profitability") or {}).get("risk_adjusted_net_edge_pct"),
            "estimated_friction_bps": (strat.get("profitability") or {}).get("estimated_friction_bps"),
            "notional_usd": ticket["notional_usd"],
            "validate": ticket["payload"]["validate"],
        })
        slots -= 1

    if emitted:
        _save_queue(rows)

    # ── Optional auto-fire ─────────────────────────────────────────────
    auto_fired = []
    max_auto_fires_per_cycle = max(0, _safe_int((rt_cfg or {}).get("max_auto_fires_per_cycle"), MAX_AUTO_FIRES_PER_CYCLE))
    lane_threshold_keys = {
        LANE_MOONSHOT: "auto_fire_score_moonshot",
        LANE_QUICKHIT: "auto_fire_score_quickhit",
        LANE_SWING: "auto_fire_score_swing",
    }
    lane_cap_keys = {
        LANE_MOONSHOT: "max_auto_fires_per_cycle_moonshot",
        LANE_QUICKHIT: "max_auto_fires_per_cycle_quickhit",
        LANE_SWING: "max_auto_fires_per_cycle_swing",
    }
    default_auto_fire_threshold = (
        _safe_float(auto_fire_score, 0.0) if auto_fire_score is not None else None
    )
    lane_auto_fired_counts = {lane: 0 for lane in LANES}
    auto_fire_lane_thresholds = {}
    auto_fire_lane_caps = {}

    for lane in LANES:
        raw_threshold = (rt_cfg or {}).get(lane_threshold_keys.get(lane, ""))
        if raw_threshold is None:
            lane_threshold = default_auto_fire_threshold
        else:
            lane_threshold = _safe_float(
                raw_threshold,
                default_auto_fire_threshold if default_auto_fire_threshold is not None else 0.0,
            )
        auto_fire_lane_thresholds[lane] = lane_threshold
        auto_fire_lane_caps[lane] = max(
            0,
            _safe_int(
                (rt_cfg or {}).get(lane_cap_keys.get(lane, "")),
                max_auto_fires_per_cycle,
            ),
        )

    if default_auto_fire_threshold is not None and emitted:
        for e in emitted:
            if max_auto_fires_per_cycle and len(auto_fired) >= max_auto_fires_per_cycle:
                break

            lane = str(e.get("strategy_lane") or "")
            lane_cap = int(auto_fire_lane_caps.get(lane, max_auto_fires_per_cycle))
            if lane_cap and lane_auto_fired_counts.get(lane, 0) >= lane_cap:
                continue

            lane_threshold = auto_fire_lane_thresholds.get(lane, default_auto_fire_threshold)
            if lane_threshold is None:
                continue

            score = e.get("score") or 0.0
            if score < lane_threshold:
                continue
            if e.get("validate"):
                # never auto-fire DRY-RUN; pointless
                continue
            tid = e["ticket_id"]
            decision_authority = _require_live_authority(
                validate=False,
                controller=controller,
                action=f"automatic approval for {tid}",
            )
            body = json.dumps({
                "ticket_id": tid,
                "decision": "approve",
                "controller": controller,
                "reason": f"auto-fire[{lane}]: score {score} >= {lane_threshold}",
                "confirm_phrase": f"FIRE {tid}",
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{gateway_url}/api/master/approval/decide",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    res = json.loads(resp.read().decode("utf-8"))
                auto_fired.append({
                    "ticket_id": tid,
                    "pair": e["pair"],
                    "strategy_lane": lane,
                    "score_threshold": lane_threshold,
                    "score": score,
                    "status": res.get("status"),
                    "txid": res.get("txid"),
                    "reason": res.get("reason"),
                })
                lane_auto_fired_counts[lane] = lane_auto_fired_counts.get(lane, 0) + 1
            except urllib.error.HTTPError as he:
                auto_fired.append({
                    "ticket_id": tid,
                    "pair": e["pair"],
                    "strategy_lane": lane,
                    "score_threshold": lane_threshold,
                    "status": "http_error",
                    "code": he.code,
                    "body": he.read().decode("utf-8", "ignore")[:200],
                })
                lane_auto_fired_counts[lane] = lane_auto_fired_counts.get(lane, 0) + 1
            except Exception as exc:  # noqa: BLE001
                auto_fired.append({
                    "ticket_id": tid,
                    "pair": e["pair"],
                    "strategy_lane": lane,
                    "score_threshold": lane_threshold,
                    "status": "error",
                    "error": str(exc),
                })
                lane_auto_fired_counts[lane] = lane_auto_fired_counts.get(lane, 0) + 1

    summary = {
        "scan_generated_utc": scan.get("generated_utc"),
        "scan_source": scan_source,
        "scan_max_age_sec": round(float(scan_max_age_sec), 3),
        "pairs_scanned": scan.get("pairs_scanned"),
        "leaderboard_size": len(leaderboard),
        "bankroll_input_usd": float(bankroll),
        "effective_bankroll_usd": float(strategy_cfg.get("effective_bankroll_usd", effective_bankroll)),
        "bankroll_source": bankroll_meta.get("source"),
        "bankroll_source_path": bankroll_meta.get("source_path"),
        "bankroll_source_age_sec": bankroll_meta.get("source_age_sec"),
        "bankroll_source_fresh": bankroll_meta.get("source_fresh"),
        "compounding_enabled": bool(strategy_cfg.get("compounding_enabled", False)),
        "compounding_bankroll_mult": float(strategy_cfg.get("compounding_bankroll_mult", 1.0)),
        "compounding_reference_bankroll_usd": float(
            strategy_cfg.get("compounding_reference_bankroll_usd", BANKROLL_DEFAULT)
        ),
        "quickhit_base_target_notional_usd": float(
            strategy_cfg.get("quickhit_base_target_notional_usd", strategy_cfg.get("quickhit_target_notional_usd", 0.0))
        ),
        "quickhit_target_notional_usd": float(strategy_cfg.get("quickhit_target_notional_usd", 0.0)),
        "swing_base_target_notional_usd": float(
            strategy_cfg.get("swing_base_target_notional_usd", strategy_cfg.get("swing_target_notional_usd", 0.0))
        ),
        "swing_target_notional_usd": float(strategy_cfg.get("swing_target_notional_usd", 0.0)),
        "alpha_map_available": bool(alpha_ctx.get("available")),
        "alpha_map_generated_utc": alpha_ctx.get("generated_utc"),
        "alpha_map_pairs_analyzed": alpha_ctx.get("pairs_analyzed"),
        "cluster_map_available": bool(cluster_ctx.get("available")),
        "cluster_map_generated_utc": cluster_ctx.get("generated_utc"),
        "cluster_map_pairs_analyzed": cluster_ctx.get("pairs_analyzed"),
        "alpha_gate_required": _alpha_gate_required(validate, gate_cfg),
        "alpha_gate_pass_count": alpha_gate_pass_count,
        "alpha_gate_fail_count": alpha_gate_fail_count,
        "alpha_gate_min_edge": float(gate_cfg.get("min_edge", ALPHA_GATE_MIN_EDGE)),
        "alpha_gate_max_spread_bps": float(gate_cfg.get("max_spread_bps", ALPHA_GATE_MAX_SPREAD_BPS)),
        "alpha_gate_min_turnover_usd": float(gate_cfg.get("min_turnover_usd", ALPHA_GATE_MIN_TURNOVER_USD)),
        "cluster_gate_enabled": bool(cluster_cfg.get("enabled", CLUSTER_GATE_ENABLED_DEFAULT)),
        "cluster_gate_required": _cluster_gate_required(validate, cluster_cfg),
        "cluster_gate_enforce_time_alignment": bool(
            cluster_cfg.get("enforce_time_alignment", CLUSTER_GATE_ENFORCE_TIME_ALIGNMENT_DEFAULT)
        ),
        "cluster_gate_min_pair_score": float(
            cluster_cfg.get("min_pair_score", CLUSTER_GATE_MIN_PAIR_SCORE)
        ),
        "cluster_gate_hour_tolerance": int(
            cluster_cfg.get("hour_tolerance", CLUSTER_GATE_HOUR_TOLERANCE)
        ),
        "cluster_gate_weekday_tolerance": int(
            cluster_cfg.get("weekday_tolerance", CLUSTER_GATE_WEEKDAY_TOLERANCE)
        ),
        "cluster_gate_pass_count": cluster_gate_pass_count,
        "cluster_gate_fail_count": cluster_gate_fail_count,
        "profitability_min_net_edge_pct": float(
            profit_cfg.get("min_net_edge_pct", PROFITABILITY_MIN_NET_EDGE_PCT)
        ),
        "profitability_fee_roundtrip_bps": float(
            profit_cfg.get("fee_roundtrip_bps", PROFITABILITY_FEE_ROUNDTRIP_BPS)
        ),
        "profitability_slippage_floor_bps": float(
            profit_cfg.get("slippage_floor_bps", PROFITABILITY_SLIPPAGE_FLOOR_BPS)
        ),
        "profitability_spread_slippage_mult": float(
            profit_cfg.get("spread_slippage_mult", PROFITABILITY_SPREAD_SLIPPAGE_MULT)
        ),
        "profitability_min_execution_quality_score": float(
            profit_cfg.get(
                "min_execution_quality_score",
                PROFITABILITY_MIN_EXECUTION_QUALITY_SCORE,
            )
        ),
        "profitability_notional_edge_scale_pct": float(
            profit_cfg.get("notional_edge_scale_pct", PROFITABILITY_NOTIONAL_EDGE_SCALE_PCT)
        ),
        "profitability_notional_floor_mult": float(
            profit_cfg.get("notional_floor_mult", PROFITABILITY_NOTIONAL_FLOOR_MULT)
        ),
        "profitability_notional_cap_mult": float(
            profit_cfg.get("notional_cap_mult", PROFITABILITY_NOTIONAL_CAP_MULT)
        ),
        "profitability_gate_fail_count": profitability_gate_fail_count,
        "strategy_mode": strategy_cfg.get("strategy_mode"),
        "max_notional_usd": strategy_cfg.get("max_notional_usd"),
        "strategy_lane_caps": {
            LANE_MOONSHOT: _lane_cycle_cap(LANE_MOONSHOT, strategy_cfg),
            LANE_QUICKHIT: _lane_cycle_cap(LANE_QUICKHIT, strategy_cfg),
            LANE_SWING: _lane_cycle_cap(LANE_SWING, strategy_cfg),
        },
        "strategy_lane_emitted": lane_emitted_counts,
        "strategy_lane_skipped_budget": lane_skip_counts,
        "pending_cleanup_changed": bool(queue_cleanup.get("changed")),
        "pending_cleanup_before": int(queue_cleanup.get("pending_before", pending_count)),
        "pending_cleanup_after": int(queue_cleanup.get("pending_after", pending_count)),
        "pending_cleanup_dropped_stale": int(queue_cleanup.get("dropped_stale", 0)),
        "pending_cleanup_dropped_dedupe": int(queue_cleanup.get("dropped_dedupe", 0)),
        "pending_cleanup_dedupe_enabled": bool(queue_cleanup.get("dedupe_enabled", False)),
        "pending_before": pending_count,
        "adaptive_queue": bool(throughput["adaptive_queue"]),
        "target_pending_capacity": int(throughput["target_pending"]),
        "target_cycle_emits": int(throughput["target_cycle"]),
        "actionable_candidates": int(throughput["actionable_candidates"]),
        "strong_candidates": int(throughput["strong_candidates"]),
        "slots_available": int(throughput["slots_available"]),
        "emitted_count": len(emitted),
        "emitted": emitted,
        "skipped_count": len(skipped),
        "skipped_top10": skipped[:10],
        "validate_mode": validate,
        "controller": controller,
        "live_authority_required": bool(cycle_authority.get("required")),
        "live_authority_authorized": bool(cycle_authority.get("authorized")),
        "live_authority_reasons": list(cycle_authority.get("reasons", [])),
        "auto_fire_score": auto_fire_score,
        "auto_fire_lane_thresholds": auto_fire_lane_thresholds,
        "auto_fire_lane_caps": auto_fire_lane_caps,
        "auto_fire_lane_counts": lane_auto_fired_counts,
        "auto_fired": auto_fired,
        "auto_fired_count": len(auto_fired),
    }
    _log_event(summary)
    return summary


def main() -> int:
    # Force UTF-8 on stdout/stderr so unicode arrows etc don't crash the daemon
    # when output is redirected to a file on Windows (cp1252 default).
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daemon", action="store_true", help="loop forever")
    ap.add_argument("--interval-min", type=int, default=INTERVAL_MIN_DEFAULT)
    ap.add_argument("--cached", action="store_true",
                    help="use last spike_hunter_latest.json instead of rescanning")
    ap.add_argument("--live", action="store_true",
                    help="emit tickets with validate=false (REAL orders on approve)")
    ap.add_argument("--controller", default=DEFAULT_CONTROLLER)
    ap.add_argument("--bankroll", type=float, default=BANKROLL_DEFAULT)
    ap.add_argument("--top-n", type=int, default=TOP_N_DEFAULT)
    ap.add_argument("--scan-max-age-sec", type=float, default=SCAN_MAX_AGE_SEC_DEFAULT,
                    help="reuse cached spike scan if newer than this age (seconds) when not forcing --cached")
    ap.add_argument("--auto-fire-score", type=float, default=None,
                    help="Auto-approve+fire any LIVE ticket whose score >= this threshold "
                         "(0-100). Requires --live. Skipped for DRY-RUN tickets.")
    ap.add_argument("--gateway-url", default="http://127.0.0.1:8787")
    args = ap.parse_args()

    validate = not args.live
    try:
        _require_live_authority(
            validate=validate,
            controller=args.controller,
            action="live auto-ticket startup",
        )
    except RuntimeError as exc:
        print(f"[AUTO-TKT] {exc}", flush=True)
        return 2
    if args.auto_fire_score is not None and validate:
        print("[AUTO-TKT] WARNING: --auto-fire-score has no effect in DRY-RUN mode; "
              "pass --live to actually auto-fire.", flush=True)

    # Seed runtime config file with CLI defaults so the dashboard can edit live
    if not AUTO_FIRE_CONFIG.exists():
        _write_runtime_config({
            "enabled": True,
            "auto_fire_score": args.auto_fire_score,
            "max_pending_tickets": MAX_PENDING_TICKETS,
            "max_cycle_emits": MAX_CYCLE_EMITS,
            "adaptive_queue": ADAPTIVE_QUEUE_DEFAULT,
            "scan_max_age_sec": args.scan_max_age_sec,
            "top_n": args.top_n,
            "pending_ticket_max_age_sec": PENDING_TICKET_MAX_AGE_SEC_DEFAULT,
            "pending_profit_lock_max_age_sec": PENDING_PROFIT_LOCK_MAX_AGE_SEC_DEFAULT,
            "pending_dedupe_by_pair_side": PENDING_DEDUPE_BY_PAIR_SIDE_DEFAULT,
            "pending_keep_per_pair_side": PENDING_KEEP_PER_PAIR_SIDE_DEFAULT,
            "max_auto_fires_per_cycle": MAX_AUTO_FIRES_PER_CYCLE,
            "auto_fire_score_moonshot": 68.0,
            "auto_fire_score_quickhit": 72.0,
            "auto_fire_score_swing": 66.0,
            "max_auto_fires_per_cycle_moonshot": 1,
            "max_auto_fires_per_cycle_quickhit": 2,
            "max_auto_fires_per_cycle_swing": 1,
            "alpha_gate_min_edge": ALPHA_GATE_MIN_EDGE,
            "alpha_gate_max_spread_bps": ALPHA_GATE_MAX_SPREAD_BPS,
            "alpha_gate_min_turnover_usd": ALPHA_GATE_MIN_TURNOVER_USD,
            "alpha_gate_allow_watch_strategy": False,
            "alpha_gate_require_match_live": True,
            "cluster_gate_enabled": CLUSTER_GATE_ENABLED_DEFAULT,
            "cluster_enforce_time_alignment": CLUSTER_GATE_ENFORCE_TIME_ALIGNMENT_DEFAULT,
            "cluster_min_pair_score": CLUSTER_GATE_MIN_PAIR_SCORE,
            "cluster_hour_tolerance": CLUSTER_GATE_HOUR_TOLERANCE,
            "cluster_weekday_tolerance": CLUSTER_GATE_WEEKDAY_TOLERANCE,
            "cluster_require_alignment_live": CLUSTER_GATE_REQUIRE_ALIGNMENT_LIVE,
            "strategy_mode": STRATEGY_MODE_HYBRID,
            "bankroll_usd": args.bankroll,
            "max_notional_usd": MAX_NOTIONAL_USD,
            "compounding_enabled": COMPOUNDING_ENABLED_DEFAULT,
            "compounding_reference_bankroll_usd": COMPOUNDING_REFERENCE_BANKROLL_USD,
            "compounding_growth_sensitivity": COMPOUNDING_GROWTH_SENSITIVITY,
            "compounding_min_bankroll_mult": COMPOUNDING_MIN_BANKROLL_MULT,
            "compounding_max_bankroll_mult": COMPOUNDING_MAX_BANKROLL_MULT,
            "compounding_equity_source_path": "out/rolling_performance.json",
            "compounding_equity_max_age_sec": COMPOUNDING_EQUITY_MAX_AGE_SEC,
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
            "profitability_min_net_edge_pct": PROFITABILITY_MIN_NET_EDGE_PCT,
            "profitability_fee_roundtrip_bps": PROFITABILITY_FEE_ROUNDTRIP_BPS,
            "profitability_slippage_floor_bps": PROFITABILITY_SLIPPAGE_FLOOR_BPS,
            "profitability_spread_slippage_mult": PROFITABILITY_SPREAD_SLIPPAGE_MULT,
            "profitability_min_execution_quality_score": PROFITABILITY_MIN_EXECUTION_QUALITY_SCORE,
            "profitability_notional_edge_scale_pct": PROFITABILITY_NOTIONAL_EDGE_SCALE_PCT,
            "profitability_notional_floor_mult": PROFITABILITY_NOTIONAL_FLOOR_MULT,
            "profitability_notional_cap_mult": PROFITABILITY_NOTIONAL_CAP_MULT,
        })

    # Write PID for dashboard control
    try:
        DAEMON_PID_FILE.write_text(str(__import__("os").getpid()), encoding="utf-8")
    except Exception:
        pass

        boot_rt = _read_runtime_config(args.auto_fire_score, True)
        boot_strategy = _resolve_strategy_runtime(runtime_cfg=boot_rt, bankroll=args.bankroll, validate=validate)
        print(f"[AUTO-TKT] validate_mode={'DRY-RUN' if validate else 'LIVE'} "
            f"strategy_mode={boot_strategy['strategy_mode']} "
            f"max_notional=${boot_strategy['max_notional_usd']:.2f} "
            f"max_pending={MAX_PENDING_TICKETS} min_score={MIN_SCORE} "
            f"auto_fire_score={args.auto_fire_score} scan_max_age_sec={args.scan_max_age_sec}",
            flush=True)

    while True:
        # Re-read live config every cycle (dashboard can edit without restart)
        rt = _read_runtime_config(args.auto_fire_score, True)
        live_threshold = rt["auto_fire_score"] if rt["enabled"] else None
        runtime_top_n = max(1, _safe_int(rt.get("top_n"), args.top_n))
        runtime_scan_max_age = max(0.0, _safe_float(rt.get("scan_max_age_sec"), args.scan_max_age_sec))
        try:
            summary = emit_tickets(
                use_cached=args.cached,
                validate=validate,
                controller=args.controller,
                bankroll=args.bankroll,
            top_n=runtime_top_n,
                auto_fire_score=live_threshold,
                gateway_url=args.gateway_url,
            scan_max_age_sec=runtime_scan_max_age,
            runtime_cfg=rt,
            )
            print(f"[AUTO-TKT] cycle enabled={rt['enabled']} "
                  f"threshold={live_threshold} emitted={summary['emitted_count']} "
                  f"skipped={summary['skipped_count']} "
                  f"auto_fired={summary['auto_fired_count']} "
                  f"slots_left={summary['slots_available'] - summary['emitted_count']} "
                  f"scan={summary['scan_source']} top_n={runtime_top_n} "
                  f"lanes={summary.get('strategy_lane_emitted')}",
                  flush=True)
            for e in summary["emitted"]:
                print(f"  + {e['pair']:<12} score={e['score']:<5} "
                      f"lane={e.get('strategy_lane')} signals={e['signals']} ${e['notional_usd']} "
                      f"validate={e['validate']}", flush=True)
            for f in summary["auto_fired"]:
                print(f"  ⚡ AUTO-FIRED {f.get('pair','?'):<12} "
                      f"score={f.get('score','?')} status={f.get('status')} "
                      f"txid={f.get('txid')}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[AUTO-TKT] error: {exc}", flush=True)
            _log_event({"event": "error", "error": str(exc)})

        if not args.daemon:
            return 0
        sleep_s = max(60, args.interval_min * 60)
        print(f"[AUTO-TKT] sleeping {sleep_s}s...", flush=True)
        time.sleep(sleep_s)


if __name__ == "__main__":
    sys.exit(main())
