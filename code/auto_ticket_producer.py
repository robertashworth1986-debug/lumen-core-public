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
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE_FILE = ROOT / "execution_approval_queue.json"
SPIKE_LATEST = ROOT / "out" / "spike_hunter" / "spike_hunter_latest.json"
ALPHA_MAP_LATEST_JSON = ROOT / "out" / "ops" / "kraken_multi_tf_alpha_map_latest.json"
ALPHA_MAP_LATEST_CSV = ROOT / "out" / "ops" / "kraken_multi_tf_alpha_map_latest.csv"
SPIKE_HISTORY_DIR = ROOT / "out" / "spike_hunter" / "history"
SPIKE_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
PRODUCER_LOG = ROOT / "out" / "execution" / "auto_ticket_producer.jsonl"
PRODUCER_LOG.parent.mkdir(parents=True, exist_ok=True)
AUTO_FIRE_CONFIG = ROOT / "run" / "auto_fire_config.json"
AUTO_FIRE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
DAEMON_PID_FILE = ROOT / "run" / "auto_ticket_producer.pid"


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
                "max_auto_fires_per_cycle": cfg.get("max_auto_fires_per_cycle"),
                "alpha_gate_min_edge": cfg.get("alpha_gate_min_edge"),
                "alpha_gate_max_spread_bps": cfg.get("alpha_gate_max_spread_bps"),
                "alpha_gate_min_turnover_usd": cfg.get("alpha_gate_min_turnover_usd"),
                "alpha_gate_allow_watch_strategy": cfg.get("alpha_gate_allow_watch_strategy"),
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
        "max_auto_fires_per_cycle": None,
        "alpha_gate_min_edge": None,
        "alpha_gate_max_spread_bps": None,
        "alpha_gate_min_turnover_usd": None,
        "alpha_gate_allow_watch_strategy": None,
        "strategy_mode": None,
        "max_notional_usd": None,
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
# Fail-closed only in LIVE mode. In DRY-RUN mode we keep discovery running.
ALPHA_GATE_REQUIRE_MATCH_LIVE = True
COOLDOWN_PAIRS_STATES = {"PENDING_HUMAN_APPROVAL", "EXECUTED_OPEN"}
INTERVAL_MIN_DEFAULT = 15
BANKROLL_DEFAULT     = 150.0
TOP_N_DEFAULT        = 20

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
                    "spread_bps": float(row.get("spread_bps") or 0.0),
                    "turnover_24h_usd": float(row.get("turnover_24h_usd") or 0.0),
                    "r_1h_pct": float(row.get("r_1h_pct") or 0.0),
                    "r_24h_pct": float(row.get("r_24h_pct") or 0.0),
                    "best_buy_hour_utc": int(float(row.get("best_buy_hour_utc") or -1)),
                }
    except Exception:
        return context

    context["available"] = bool(lookup)
    context["lookup"] = lookup
    if context["pairs_analyzed"] <= 0:
        context["pairs_analyzed"] = len(lookup)
    return context


def _alpha_gate_required(validate: bool) -> bool:
    return (not validate) and ALPHA_GATE_REQUIRE_MATCH_LIVE


def _resolve_alpha_gate(runtime_cfg: dict | None) -> dict[str, float]:
    cfg = runtime_cfg or {}
    return {
        "min_edge": max(0.0, _safe_float(cfg.get("alpha_gate_min_edge"), ALPHA_GATE_MIN_EDGE)),
        "max_spread_bps": max(0.0, _safe_float(cfg.get("alpha_gate_max_spread_bps"), ALPHA_GATE_MAX_SPREAD_BPS)),
        "min_turnover_usd": max(0.0, _safe_float(cfg.get("alpha_gate_min_turnover_usd"), ALPHA_GATE_MIN_TURNOVER_USD)),
        "allow_watch_strategy": bool(cfg.get("alpha_gate_allow_watch_strategy", False)),
    }


def _alpha_gate(row: dict, alpha_ctx: dict, validate: bool, gate_cfg: dict[str, float]) -> tuple[bool, str, dict | None]:
    required = _alpha_gate_required(validate)
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

    mode = str(alpha.get("strategy_mode") or "watch").strip().lower()
    edge = float(alpha.get("alpha_edge_score") or 0.0)
    spread = float(alpha.get("spread_bps") or 0.0)
    turnover = float(alpha.get("turnover_24h_usd") or 0.0)
    min_edge = float(gate_cfg.get("min_edge", ALPHA_GATE_MIN_EDGE))
    max_spread = float(gate_cfg.get("max_spread_bps", ALPHA_GATE_MAX_SPREAD_BPS))
    min_turnover = float(gate_cfg.get("min_turnover_usd", ALPHA_GATE_MIN_TURNOVER_USD))

    if mode not in ALPHA_GATE_ALLOWED_STRATEGIES:
        if not (mode == "watch" and bool(gate_cfg.get("allow_watch_strategy", False))):
            return False, "alpha_strategy_not_actionable", alpha
    
    if edge < min_edge:
        return False, f"alpha_edge<{min_edge}", alpha
    if spread > max_spread:
        return False, f"alpha_spread>{max_spread}", alpha
    if turnover < min_turnover:
        return False, f"alpha_turnover<{min_turnover}", alpha

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


def _resolve_strategy_runtime(runtime_cfg: dict | None, bankroll: float, validate: bool) -> dict:
    cfg = runtime_cfg or {}
    strategy_mode = str(cfg.get("strategy_mode") or STRATEGY_MODE_HYBRID).strip().lower()
    if strategy_mode not in STRATEGY_MODES:
        strategy_mode = STRATEGY_MODE_HYBRID

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
        max(bankroll * moonshot_bankroll_frac, MIN_NOTIONAL_USD),
        MIN_NOTIONAL_USD,
        max_notional_usd,
    )
    quickhit_target_notional_usd = _clamp(
        _safe_float(cfg.get("quickhit_target_notional_usd"), 12.0),
        MIN_NOTIONAL_USD,
        max_notional_usd,
    )
    swing_target_notional_usd = _clamp(
        _safe_float(cfg.get("swing_target_notional_usd"), 16.0),
        MIN_NOTIONAL_USD,
        max_notional_usd,
    )

    return {
        "strategy_mode": strategy_mode,
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
        "swing_target_notional_usd": swing_target_notional_usd,
        "swing_max_per_cycle": max(0, _safe_int(cfg.get("swing_max_per_cycle"), 2)),
        "swing_min_edge": _safe_float(cfg.get("swing_min_edge"), 4.5),
        "swing_min_r1h_pct": _safe_float(cfg.get("swing_min_r1h_pct"), 0.12),
        "swing_min_m4h_pct": _safe_float(cfg.get("swing_min_m4h_pct"), -3.0),
        "swing_max_spread_bps": _safe_float(cfg.get("swing_max_spread_bps"), 30.0),
        "swing_min_turnover_usd": _safe_float(cfg.get("swing_min_turnover_usd"), 150000.0),
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

    edge = _safe_float(alpha.get("alpha_edge_score"), 0.0)
    spread = _safe_float(alpha.get("spread_bps"), 0.0)
    turnover = _safe_float(alpha.get("turnover_24h_usd"), 0.0)
    trend_score = _safe_float(alpha.get("trend_score"), 0.0)

    r_1m = _safe_float(alpha.get("r_1m_pct"), 0.0)
    r_5m = _safe_float(alpha.get("r_5m_pct"), 0.0)
    r_30m = _safe_float(alpha.get("r_30m_pct"), 0.0)
    r_1h = _safe_float(alpha.get("r_1h_pct"), 0.0)
    r_15m = 0.65 * r_5m + 0.35 * r_30m
    m4h = _safe_float(row.get("m4h"), r_1h * 4.0)

    dip_pct = _safe_float(row.get("dip_from_high_pct"), 0.0)
    rsi = _safe_float(row.get("rsi"), 50.0)
    vol_surge = _safe_float(row.get("vol_surge"), 0.0)
    score = _safe_float(row.get("score"), 0.0)
    alpha_mode = str(alpha.get("strategy_mode") or "watch").strip().lower()
    signals = {str(x).upper() for x in (row.get("signals") or [])}

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


def _resolve_lane_notional_usd(row: dict, lane: str, strategy_cfg: dict) -> float:
    suggested_usd = float(row.get("size_usd", 0)) or float(row.get("size_pct", 0)) * BANKROLL_DEFAULT / 100
    if lane == LANE_MOONSHOT:
        target = max(suggested_usd, _safe_float(strategy_cfg.get("moonshot_target_notional_usd"), MAX_NOTIONAL_USD))
    elif lane == LANE_QUICKHIT:
        target = _safe_float(strategy_cfg.get("quickhit_target_notional_usd"), min(12.0, MAX_NOTIONAL_USD))
    elif lane == LANE_SWING:
        target = max(suggested_usd * 0.8, _safe_float(strategy_cfg.get("swing_target_notional_usd"), min(16.0, MAX_NOTIONAL_USD)))
    else:
        target = suggested_usd or MAX_NOTIONAL_USD

    max_notional = _safe_float(strategy_cfg.get("max_notional_usd"), MAX_NOTIONAL_USD)
    return _clamp(target, MIN_NOTIONAL_USD, max_notional)


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


def _eligible(row: dict, alpha_ctx: dict, validate: bool, gate_cfg: dict[str, float]) -> tuple[bool, str, dict | None]:
    score = float(row.get("score", 0))
    signals = row.get("signals") or []
    vol_24h = float(row.get("vol_24h_usd", 0))
    price   = float(row.get("price", 0))

    if signals == ["WATCH"]:
        return False, "watch_only", None
    if score < MIN_SCORE:
        return False, f"score<{MIN_SCORE}", None
    if vol_24h < MIN_24H_VOL_USD:
        return False, f"vol_24h<{MIN_24H_VOL_USD}", None
    if price <= 0:
        return False, "zero_price", None

    alpha_ok, alpha_reason, alpha_row = _alpha_gate(row, alpha_ctx, validate, gate_cfg)
    if not alpha_ok:
        return False, alpha_reason, alpha_row

    return True, "ok", alpha_row


def _compute_throughput_targets(
    leaderboard: list[dict],
    alpha_ctx: dict,
    validate: bool,
    pending_count: int,
    gate_cfg: dict[str, float],
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
        ok, _why, alpha_row = _eligible(row, alpha_ctx=alpha_ctx, validate=validate, gate_cfg=gate_cfg)
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
    strategy_lane: str | None = None,
    strategy_meta: dict | None = None,
    strategy_cfg: dict | None = None,
) -> dict | None:
    pair = _normalize_pair_for_kraken(row.get("pair", ""), row.get("wsname", ""))
    if not pair:
        return None
    price = float(row["price"])
    strat_cfg = strategy_cfg if isinstance(strategy_cfg, dict) else {}
    if strategy_lane:
        notional = _resolve_lane_notional_usd(row=row, lane=strategy_lane, strategy_cfg=strat_cfg)
    else:
        # Fallback for legacy callsites.
        suggested_usd = float(row.get("size_usd", 0)) or float(row.get("size_pct", 0)) * BANKROLL_DEFAULT / 100
        max_notional = _safe_float(strat_cfg.get("max_notional_usd"), MAX_NOTIONAL_USD)
        notional = max(MIN_NOTIONAL_USD, min(max_notional, suggested_usd or max_notional))
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
            "strategy": strategy_meta or {},
            "alpha_gate": {
                "enabled": True,
                "strategy_mode": (alpha_row or {}).get("strategy_mode"),
                "alpha_edge_score": (alpha_row or {}).get("alpha_edge_score"),
                "spread_bps": (alpha_row or {}).get("spread_bps"),
                "turnover_24h_usd": (alpha_row or {}).get("turnover_24h_usd"),
                "r_1h_pct": (alpha_row or {}).get("r_1h_pct"),
                "r_24h_pct": (alpha_row or {}).get("r_24h_pct"),
                "best_buy_hour_utc": (alpha_row or {}).get("best_buy_hour_utc"),
            },
        },
    }


def emit_tickets(use_cached: bool, validate: bool, controller: str,
                 bankroll: float, top_n: int,
                 auto_fire_score: float | None = None,
                 gateway_url: str = "http://127.0.0.1:8787",
                 scan_max_age_sec: float = SCAN_MAX_AGE_SEC_DEFAULT,
                 runtime_cfg: dict | None = None) -> dict:
    rt_cfg = runtime_cfg if isinstance(runtime_cfg, dict) else _read_runtime_config(
        default_threshold=auto_fire_score,
        default_enabled=True,
    )

    scan_source = "fresh_scan"
    scan = _load_cached_scan() if use_cached else _load_cached_scan_if_fresh(scan_max_age_sec)
    if scan is not None:
        scan_source = "cached_forced" if use_cached else "cached_fresh"
    if scan is None:
        scan = _refresh_scan(bankroll=bankroll, top_n=top_n)
        # Archive every fresh scan for later backtesting.
        _archive_scan(scan)

    leaderboard = scan.get("leaderboard") or []
    alpha_ctx = _load_alpha_map_context()
    gate_cfg = _resolve_alpha_gate(rt_cfg)
    strategy_cfg = _resolve_strategy_runtime(runtime_cfg=rt_cfg, bankroll=bankroll, validate=validate)
    rows = _load_queue()

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
        validate=validate,
        pending_count=pending_count,
        gate_cfg=gate_cfg,
        runtime_cfg=rt_cfg,
    )
    slots = int(throughput["cycle_emit_budget"])

    emitted = []
    skipped = []
    alpha_gate_pass_count = 0
    alpha_gate_fail_count = 0
    lane_emitted_counts = {lane: 0 for lane in LANES}
    lane_skip_counts = {lane: 0 for lane in LANES}

    for row in leaderboard:
        if slots <= 0:
            break
        pair = _normalize_pair_for_kraken(row.get("pair", ""), row.get("wsname", ""))
        if pair in blocked_pairs:
            skipped.append({"pair": pair, "reason": "in_queue"})
            continue
        ok, why, alpha_row = _eligible(row, alpha_ctx=alpha_ctx, validate=validate, gate_cfg=gate_cfg)
        if not ok:
            skipped.append({"pair": pair, "reason": why})
            if str(why).startswith("alpha_"):
                alpha_gate_fail_count += 1
            continue
        if alpha_row:
            alpha_gate_pass_count += 1

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
                f"r1m={strat.get('tf', {}).get('r_1m_pct')} "
                f"r15m={strat.get('tf', {}).get('r_15m_pct')} "
                f"r1h={strat.get('tf', {}).get('r_1h_pct')} "
                f"r4h={strat.get('tf', {}).get('r_4h_pct')}"
            ),
            alpha_row=alpha_row,
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
            "notional_usd": ticket["notional_usd"],
            "validate": ticket["payload"]["validate"],
        })
        slots -= 1

    if emitted:
        _save_queue(rows)

    # ── Optional auto-fire ─────────────────────────────────────────────
    auto_fired = []
    max_auto_fires_per_cycle = max(0, _safe_int((rt_cfg or {}).get("max_auto_fires_per_cycle"), MAX_AUTO_FIRES_PER_CYCLE))
    if auto_fire_score is not None and emitted:
        for e in emitted:
            if max_auto_fires_per_cycle and len(auto_fired) >= max_auto_fires_per_cycle:
                break
            score = e.get("score") or 0.0
            if score < auto_fire_score:
                continue
            if e.get("validate"):
                # never auto-fire DRY-RUN; pointless
                continue
            tid = e["ticket_id"]
            body = json.dumps({
                "ticket_id": tid,
                "decision": "approve",
                "controller": controller,
                "reason": f"auto-fire: score {score} >= {auto_fire_score}",
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
                    "score": score,
                    "status": res.get("status"),
                    "txid": res.get("txid"),
                    "reason": res.get("reason"),
                })
            except urllib.error.HTTPError as he:
                auto_fired.append({"ticket_id": tid, "pair": e["pair"], "status": "http_error",
                                   "code": he.code, "body": he.read().decode("utf-8", "ignore")[:200]})
            except Exception as exc:  # noqa: BLE001
                auto_fired.append({"ticket_id": tid, "pair": e["pair"], "status": "error", "error": str(exc)})

    summary = {
        "scan_generated_utc": scan.get("generated_utc"),
        "scan_source": scan_source,
        "scan_max_age_sec": round(float(scan_max_age_sec), 3),
        "pairs_scanned": scan.get("pairs_scanned"),
        "leaderboard_size": len(leaderboard),
        "alpha_map_available": bool(alpha_ctx.get("available")),
        "alpha_map_generated_utc": alpha_ctx.get("generated_utc"),
        "alpha_map_pairs_analyzed": alpha_ctx.get("pairs_analyzed"),
        "alpha_gate_required": _alpha_gate_required(validate),
        "alpha_gate_pass_count": alpha_gate_pass_count,
        "alpha_gate_fail_count": alpha_gate_fail_count,
        "alpha_gate_min_edge": float(gate_cfg.get("min_edge", ALPHA_GATE_MIN_EDGE)),
        "alpha_gate_max_spread_bps": float(gate_cfg.get("max_spread_bps", ALPHA_GATE_MAX_SPREAD_BPS)),
        "alpha_gate_min_turnover_usd": float(gate_cfg.get("min_turnover_usd", ALPHA_GATE_MIN_TURNOVER_USD)),
        "strategy_mode": strategy_cfg.get("strategy_mode"),
        "max_notional_usd": strategy_cfg.get("max_notional_usd"),
        "strategy_lane_caps": {
            LANE_MOONSHOT: _lane_cycle_cap(LANE_MOONSHOT, strategy_cfg),
            LANE_QUICKHIT: _lane_cycle_cap(LANE_QUICKHIT, strategy_cfg),
            LANE_SWING: _lane_cycle_cap(LANE_SWING, strategy_cfg),
        },
        "strategy_lane_emitted": lane_emitted_counts,
        "strategy_lane_skipped_budget": lane_skip_counts,
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
        "auto_fire_score": auto_fire_score,
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
            "max_auto_fires_per_cycle": MAX_AUTO_FIRES_PER_CYCLE,
            "alpha_gate_min_edge": ALPHA_GATE_MIN_EDGE,
            "alpha_gate_max_spread_bps": ALPHA_GATE_MAX_SPREAD_BPS,
            "alpha_gate_min_turnover_usd": ALPHA_GATE_MIN_TURNOVER_USD,
            "alpha_gate_allow_watch_strategy": False,
            "strategy_mode": STRATEGY_MODE_HYBRID,
            "max_notional_usd": MAX_NOTIONAL_USD,
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
