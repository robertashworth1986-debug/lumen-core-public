# =============================================================================
# LumaTrader™ — LumenCore Universal Execution Orchestrator
# Production-grade multi-exchange trading engine with harmonic intelligence
# =============================================================================

import sys
import os
import time
import json
import subprocess
import hashlib
import hmac
import base64
import urllib.parse
import signal
import threading
import uuid
import re
import traceback
import inspect
import glob
import logging
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import requests

# Ensure local code paths are on sys.path before local imports
_BOOTSTRAP_PATHS = [
    r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code',
    r'C:\LumaTrader\INSTITUTIONAL_STACK_V2\code\execution',
]
for _bootstrap_path in _BOOTSTRAP_PATHS:
    if _bootstrap_path not in sys.path:
        sys.path[:0] = [_bootstrap_path]

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from signal_gate import EvolutionarySignalGate, GateInput
import signal_gate
from portfolio_brain import PortfolioBrain, Position
from liquidity_guard import LiquidityGuard, LiquiditySnapshot
from risk_kernel import RiskKernel, RiskState
from rl_policy import RLPolicy
from sector_rotation import SectorRotation
from runtime_live_lock import runtime_writer_hint

try:
    from execution.harmonic_signal_connector import HarmonicSignalConnector
    from execution.live_runtime_guard import LiveRuntimeGuard
    from execution.audit_chain import AuditChain
except Exception:
    from harmonic_signal_connector import HarmonicSignalConnector
    from live_runtime_guard import LiveRuntimeGuard
    from audit_chain import AuditChain

try:
    from arch.univariate import arch_model
    ARCH_AVAILABLE = True
except Exception:
    arch_model = None
    ARCH_AVAILABLE = False

RiverMean = None
RiverVar = None
RIVER_AVAILABLE = False

# === Configuration paths ===
ROOT = Path(r'C:\LumaTrader\INSTITUTIONAL_STACK_V2')
OUT = ROOT / 'out' / 'execution'
CONFIG = ROOT / 'config'
ENV_FILE = CONFIG / 'luma_live_keys.env'
RUNTIME_FILE = CONFIG / 'runtime_control.json'
RUNTIME_PROFILE_LOCK_FILE = CONFIG / 'runtime_profile_lock.json'
AUDIT_CHAIN_FILE = OUT / 'execution_audit_chain.jsonl'
ADAPTIVE_PROFILE_FILE = OUT / 'adaptive_profile_state.json'
PAYOUT_INTENTS_FILE = OUT / 'payout_intents.json'
WALLET_TRANSFER_REQUESTS_FILE = OUT / 'wallet_transfer_requests.json'
LIVE_BALANCE_SNAPSHOT_FILE = OUT / 'live_balance_snapshot.json'
X1000_CONTROL_PLANE_FILE = ROOT / 'code' / 'x1000_control_plane.py'
LIVE_MARKET_STREAM_STATUS_FILE = OUT / 'live_market_stream_status.json'
LIVE_RESELECTION_STATUS_FILE = OUT / 'live_reselection_status.json'
LIVE_ENGINE_HEARTBEAT_FILE = OUT / 'live_engine_heartbeat.json'
RUNTIME_DRIFT_ALERT_FILE = OUT / 'runtime_drift_alert.json'
RUNTIME_DRIFT_OPERATOR_ALERT_FILE = OUT / 'runtime_drift_operator_alert.json'
EXECUTION_LOCK_FILE = OUT / '.execution_lock'
MAX_FALLBACK_BUYING_POWER_USD = 1_000_000_000.0

KNOWN_RUNTIME_WRITER_PATHS = [
    'code/FULL_TRUTH_ORCHESTRATOR.py',
    'code/DISCOVER_AND_ROUTE_ALL_LIVE_KEYS.py',
    'code/REBUILD_FULL_ADAPTIVE_LIVE_STACK.py',
    'code/BUILD_ADAPTIVE_UNIVERSE_FROM_LIVE_KEYS.py',
]

# Rolling capital paths
ROLLING_CAPITAL_BEST_MULTI_PATH = Path(r"C:/LumaTrader/rolling_capital/rolling_capital_best_multi.json")
ROLLING_CAPITAL_HEATMAP_PATH = Path(r"C:/LumaTrader/rolling_capital/rolling_capital_heatmap.json")
ROLLING_CAPITAL_BEST_PATH = Path(r"C:/LumaTrader/rolling_capital/rolling_capital_best.json")


def get_rolling_capital_best_multi() -> tuple[Optional[str], Optional[str], Dict[str, Any]]:
    if not ROLLING_CAPITAL_BEST_MULTI_PATH.exists():
        return None, None, {}
    try:
        payload = json.loads(ROLLING_CAPITAL_BEST_MULTI_PATH.read_text(encoding='utf-8'))
    except Exception:
        return None, None, {}
    if not isinstance(payload, dict):
        return None, None, {}
    symbol = payload.get('symbol')
    family = payload.get('family')
    metrics = payload.get('metrics')
    return (
        str(symbol).strip() if symbol else None,
        str(family).strip() if family else None,
        metrics if isinstance(metrics, dict) else {},
    )


def _normalize_best_multi_payload(value: Any) -> tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """Normalize legacy/new rolling-capital payload shapes into a stable 3-tuple."""
    symbol: Optional[str] = None
    family: Optional[str] = None
    metrics: Dict[str, Any] = {}

    if isinstance(value, dict):
        symbol = value.get('symbol')
        family = value.get('family')
        raw_metrics = value.get('metrics')
        if isinstance(raw_metrics, dict):
            metrics = raw_metrics
    elif isinstance(value, (tuple, list)):
        if len(value) >= 1:
            symbol = value[0]
        if len(value) >= 2:
            family = value[1]
        if len(value) >= 3 and isinstance(value[2], dict):
            metrics = value[2]

    out_symbol = str(symbol).strip() if symbol else None
    out_family = str(family).strip() if family else None
    return out_symbol, out_family, metrics


def get_rolling_capital_heatmap() -> List[Dict[str, Any]]:
    if not ROLLING_CAPITAL_HEATMAP_PATH.exists():
        return []
    try:
        payload = json.loads(ROLLING_CAPITAL_HEATMAP_PATH.read_text(encoding='utf-8'))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]

OUT.mkdir(parents=True, exist_ok=True)

# === Control flow variables (initialized once at module load) ===
auto_stop_triggered = False
auto_boost_active = False
auto_stop_reason = None
auto_boost_reason = None
current_drawdown = None
risk_reasons = []
win_streak = None

print("\u001b[36m\u2728 LUMENCORE UNIVERSAL EXECUTION ORCHESTRATOR\u001b[0m")
print("=" * 70)
print("Signal Engine \u2192 Full Symbol Range \u2192 Multi-Exchange Routing")
print("=" * 70)

# Load API keys
def load_api_keys():
    keys = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.strip() and '=' in line:
                    k, v = line.strip().split('=', 1)
                    keys[k] = v
    return keys


def _atomic_write_json(path: Path, payload: Any, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=indent)
    os.replace(tmp_path, path)


def _append_startup_fatal(reason: str, context: Optional[Dict[str, Any]] = None, exc_info: Optional[Any] = None) -> None:
    payload = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'reason': str(reason or 'unknown_startup_failure'),
        'pid': int(os.getpid()),
        'context': dict(context or {}),
    }
    try:
        _atomic_write_json(OUT / 'startup_failure.json', payload, indent=2)
    except Exception:
        pass

    try:
        with open(OUT / 'startup_fatal.log', 'a', encoding='utf-8') as log_file:
            log_file.write(json.dumps(payload, ensure_ascii=False) + '\n')
    except Exception:
        pass

    if exc_info and isinstance(exc_info, tuple) and len(exc_info) == 3:
        try:
            with open(OUT / 'startup_fatal.log', 'a', encoding='utf-8') as log_file:
                traceback.print_exception(exc_info[0], exc_info[1], exc_info[2], file=log_file)
        except Exception:
            pass


def _unhandled_exception_hook(exc_type, exc_value, exc_tb):
    if exc_type is KeyboardInterrupt:
        return
    _append_startup_fatal(
        'unhandled_exception',
        context={
            'exc_type': str(getattr(exc_type, '__name__', exc_type)),
            'exc_message': str(exc_value),
        },
        exc_info=(exc_type, exc_value, exc_tb),
    )
    try:
        traceback.print_exception(exc_type, exc_value, exc_tb, file=sys.stderr)
    except Exception:
        pass


sys.excepthook = _unhandled_exception_hook


def _load_live_market_stream_status() -> Dict[str, Any]:
    if not LIVE_MARKET_STREAM_STATUS_FILE.exists():
        return {}
    try:
        payload = json.loads(LIVE_MARKET_STREAM_STATUS_FILE.read_text(encoding='utf-8'))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _load_live_reselection_status() -> Dict[str, Any]:
    if not LIVE_RESELECTION_STATUS_FILE.exists():
        return {}
    try:
        payload = json.loads(LIVE_RESELECTION_STATUS_FILE.read_text(encoding='utf-8'))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _format_live_market_stream_brief(status: Optional[Dict[str, Any]]) -> str:
    status = status if isinstance(status, dict) else {}
    state = str(status.get('status', 'unknown') or 'unknown').strip().lower()
    pair = str(status.get('pair', '') or '').strip()
    channel = str(status.get('channel', '') or '').strip()
    reason = str(status.get('reason', '') or '').strip()
    error = str(status.get('error', '') or '').strip()

    parts: List[str] = []
    if state:
        parts.append(state)
    if channel:
        parts.append(channel)
    if pair:
        parts.append(pair)
    elif reason:
        parts.append(reason)
    elif error:
        parts.append(error[:48])
    return ' | '.join(parts) if parts else 'unknown'


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def _read_execution_lock_metadata() -> Dict[str, Any]:
    if not EXECUTION_LOCK_FILE.exists():
        return {
            'file_exists': False,
            'owner_pid': None,
            'owner_token': '',
            'owner_alive': False,
            'age_seconds': None,
            'created_utc': '',
        }

    raw = ''
    try:
        raw = EXECUTION_LOCK_FILE.read_text(encoding='utf-8')
    except Exception:
        pass

    parsed: Dict[str, str] = {}
    for line in str(raw or '').splitlines():
        txt = str(line or '').strip()
        if not txt or '=' not in txt:
            continue
        key, value = txt.split('=', 1)
        parsed[str(key).strip()] = str(value).strip()

    owner_pid = None
    for pid_key in ['owner_pid', 'pid']:
        if pid_key in parsed:
            try:
                owner_pid = int(parsed.get(pid_key, '').strip())
                break
            except Exception:
                owner_pid = None

    created_utc = str(parsed.get('created_utc', '') or parsed.get('time', '') or '').strip()
    age_seconds = None
    if created_utc:
        try:
            created_dt = datetime.fromisoformat(created_utc.replace('Z', '+00:00'))
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            age_seconds = max(0.0, (datetime.now(timezone.utc) - created_dt).total_seconds())
        except Exception:
            age_seconds = None

    owner_alive = _is_pid_alive(owner_pid) if owner_pid is not None else False
    return {
        'file_exists': True,
        'owner_pid': owner_pid,
        'owner_token': str(parsed.get('owner_token', '') or ''),
        'owner_alive': bool(owner_alive),
        'age_seconds': None if age_seconds is None else float(age_seconds),
        'created_utc': created_utc,
    }


def _persist_live_engine_heartbeat(
    loop_count: int,
    runtime_cfg: Dict[str, Any],
    portfolio,
    active_profile: str,
    status: str,
    reason: str,
    symbol: Optional[str] = None,
    engine_decision: Optional[Dict[str, Any]] = None,
    selection_meta: Optional[Dict[str, Any]] = None,
    gate_decision: Any = None,
    ticker: Optional[Dict[str, Any]] = None,
    usd_balance: Optional[float] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    stream_status = _load_live_market_stream_status()
    reselection_status = _load_live_reselection_status()
    execution_lock = _read_execution_lock_metadata()
    decision = dict(engine_decision or {})
    selection = dict(selection_meta or {})
    tick = dict(ticker or {})
    gate_score = None
    gate_armed = None
    gate_reasons: List[str] = []
    if gate_decision is not None:
        try:
            gate_score = float(getattr(gate_decision, 'composite_score', 0.0) or 0.0)
        except Exception:
            gate_score = None
        try:
            gate_armed = bool(getattr(gate_decision, 'armed', False))
        except Exception:
            gate_armed = None
        try:
            gate_reasons = list(getattr(gate_decision, 'reason_codes', []) or [])
        except Exception:
            gate_reasons = []

    heartbeat = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'loop': int(loop_count),
        'status': str(status or 'unknown'),
        'reason': str(reason or ''),
        'active_profile': str(active_profile or ''),
        'runtime_mode': str(runtime_cfg.get('mode', 'paper')).upper(),
        'live_orders_armed': bool(runtime_cfg.get('allow_live_orders', False)),
        'paper_enabled': bool(runtime_cfg.get('paper_enabled', True)),
        'symbol': str(symbol or decision.get('symbol', '') or ''),
        'selection_mode': str(selection.get('selection_mode', '') or ''),
        'market_data_mode': str(decision.get('market_data_mode', '') or ''),
        'signal_source': str(decision.get('source', '') or ''),
        'regime': str(decision.get('regime', '') or ''),
        'direction': str(decision.get('direction', '') or ''),
        'confidence': None if decision.get('confidence') is None else float(decision.get('confidence', 0.0) or 0.0),
        'edge_bps': None if decision.get('edge_bps') is None else float(decision.get('edge_bps', 0.0) or 0.0),
        'ranking_score': None if decision.get('ranking_score') is None else float(decision.get('ranking_score', 0.0) or 0.0),
        'affordability_ratio': None if decision.get('affordability_ratio') is None else float(decision.get('affordability_ratio', 0.0) or 0.0),
        'gate_score': gate_score,
        'gate_armed': gate_armed,
        'gate_reasons': gate_reasons,
        'ticker': {
            'pair': str(tick.get('pair', '') or ''),
            'last': None if tick.get('last') is None else float(tick.get('last', 0.0) or 0.0),
            'bid': None if tick.get('bid') is None else float(tick.get('bid', 0.0) or 0.0),
            'ask': None if tick.get('ask') is None else float(tick.get('ask', 0.0) or 0.0),
        },
        'usd_balance': None if usd_balance is None else float(usd_balance),
        'portfolio_equity_usd': float(getattr(portfolio, 'current_equity', 0.0) or 0.0),
        'portfolio_realized_pnl_usd': float(getattr(portfolio, 'realized_pnl_total', 0.0) or 0.0),
        'stream_status': stream_status,
        'stream_brief': _format_live_market_stream_brief(stream_status),
        'reselection_status': reselection_status,
        'execution_lock': execution_lock,
    }
    if extra:
        heartbeat['extra'] = dict(extra)
    _atomic_write_json(LIVE_ENGINE_HEARTBEAT_FILE, heartbeat, indent=2)


def _persist_runtime_drift_alert(
    loop_count: int,
    runtime_cfg: Dict[str, Any],
    changed_runtime: Dict[str, Any],
    runtime_profile_sync_events_window: deque,
    now_sync_ts: float,
    runtime_writer_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    window_seconds = float(runtime_cfg.get('runtime_drift_alert_window_sec', 900.0) or 900.0)
    window_seconds = max(60.0, min(3600.0, window_seconds))
    threshold = int(runtime_cfg.get('runtime_drift_alert_threshold', 6) or 6)
    threshold = max(1, min(200, threshold))

    writer_meta = dict(runtime_writer_meta or {})
    likely_culprit_writer = str(
        writer_meta.get('last_runtime_writer', runtime_cfg.get('_last_runtime_writer', '')) or ''
    ).strip()
    last_runtime_write_utc = str(
        writer_meta.get('last_runtime_write_utc', runtime_cfg.get('_last_runtime_write_utc', '')) or ''
    ).strip()
    last_runtime_write_reason = str(
        writer_meta.get('last_runtime_write_reason', runtime_cfg.get('_last_runtime_write_reason', '')) or ''
    ).strip()
    strict_live_locked_at_write = bool(
        writer_meta.get('strict_live_locked_at_write', runtime_cfg.get('_strict_live_locked_at_write', False))
    )

    while runtime_profile_sync_events_window and (now_sync_ts - float(runtime_profile_sync_events_window[0])) > window_seconds:
        runtime_profile_sync_events_window.popleft()

    previous_total = 0
    try:
        if RUNTIME_DRIFT_ALERT_FILE.exists():
            previous = json.loads(RUNTIME_DRIFT_ALERT_FILE.read_text(encoding='utf-8'))
            if isinstance(previous, dict):
                previous_total = int(previous.get('total_events', 0) or 0)
    except Exception:
        previous_total = 0

    payload = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'loop': int(loop_count),
        'window_seconds': float(window_seconds),
        'window_events': int(len(runtime_profile_sync_events_window)),
        'threshold': int(threshold),
        'excessive': bool(len(runtime_profile_sync_events_window) >= threshold),
        'total_events': int(previous_total + 1),
        'runtime_mode': str(runtime_cfg.get('mode', 'paper')).lower(),
        'live_orders_armed': bool(runtime_cfg.get('allow_live_orders', False)),
        'paper_enabled': bool(runtime_cfg.get('paper_enabled', True)),
        'changed_runtime': dict(changed_runtime or {}),
        'likely_culprit_writer': likely_culprit_writer,
        'last_runtime_write_utc': last_runtime_write_utc,
        'last_runtime_write_reason': last_runtime_write_reason,
        'strict_live_locked_at_write': strict_live_locked_at_write,
        'culprit_candidates': list(KNOWN_RUNTIME_WRITER_PATHS),
    }
    _atomic_write_json(RUNTIME_DRIFT_ALERT_FILE, payload, indent=2)
    return payload


def _persist_runtime_drift_operator_alert(loop_count: int, drift_alert: Dict[str, Any]) -> Dict[str, Any]:
    likely_culprit_writer = str(drift_alert.get('likely_culprit_writer', '') or '').strip()
    if not likely_culprit_writer:
        likely_culprit_writer = KNOWN_RUNTIME_WRITER_PATHS[0]

    payload = {
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'loop': int(loop_count),
        'severity': 'high',
        'alert_type': 'runtime_live_profile_drift_excessive',
        'window_events': int(drift_alert.get('window_events', 0) or 0),
        'window_seconds': float(drift_alert.get('window_seconds', 0.0) or 0.0),
        'threshold': int(drift_alert.get('threshold', 0) or 0),
        'likely_culprit_writer': likely_culprit_writer,
        'last_runtime_write_utc': str(drift_alert.get('last_runtime_write_utc', '') or ''),
        'last_runtime_write_reason': str(drift_alert.get('last_runtime_write_reason', '') or ''),
        'strict_live_locked_at_write': bool(drift_alert.get('strict_live_locked_at_write', False)),
        'changed_runtime': dict(drift_alert.get('changed_runtime', {}) or {}),
        'recommended_actions': [
            'inspect likely_culprit_writer and disable paper-mode overrides',
            'verify config/runtime_control.json remains {mode: live, allow_live_orders: true, paper_enabled: false}',
            'check out/execution/execution_events.jsonl for runtime_live_profile_forced frequency',
        ],
    }

    write_ok = False
    try:
        _atomic_write_json(RUNTIME_DRIFT_OPERATOR_ALERT_FILE, payload, indent=2)
        write_ok = True
    except Exception as exc:
        payload['write_error'] = str(exc)[:180]

    # Last-resort fallback so operator visibility never depends on one write path.
    if not write_ok:
        try:
            RUNTIME_DRIFT_OPERATOR_ALERT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(RUNTIME_DRIFT_OPERATOR_ALERT_FILE, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)
            write_ok = True
        except Exception as exc:
            payload['fallback_write_error'] = str(exc)[:180]

    payload['file_exists'] = bool(RUNTIME_DRIFT_OPERATOR_ALERT_FILE.exists())
    payload['write_ok'] = bool(write_ok)
    return payload


def _load_payout_intents() -> List[Dict[str, Any]]:
    if not PAYOUT_INTENTS_FILE.exists():
        return []
    try:
        with open(PAYOUT_INTENTS_FILE, 'r', encoding='utf-8') as f:
            parsed = json.load(f)
            if isinstance(parsed, list):
                return parsed
    except Exception:
        return []
    return []


def _persist_engine_checkpoint(
    portfolio,
    runtime_cfg: Dict[str, Any],
    loop_count: int,
) -> None:
    """
    Save critical engine state to checkpoint file.
    Used on restart to prevent 'relearning' — preserves:
    - Open positions and their entry prices
    - Portfolio equity, realized P&L
    - Current symbol blacklist
    - Active profile and risk state
    
    Called every ~50 loops (every 100s on 2s loop) to avoid excessive I/O.
    """
    try:
        checkpoint = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'loop_count': int(loop_count),
            'version': 1,
            'portfolio': {
                'current_equity_usd': float(getattr(portfolio, 'current_equity', 0.0) or 0.0),
                'realized_pnl_total_usd': float(getattr(portfolio, 'realized_pnl_total', 0.0) or 0.0),
                'unrealized_pnl_total_usd': float(getattr(portfolio, 'unrealized_pnl_total', 0.0) or 0.0),
                'total_notional_usd': float(getattr(portfolio, 'total_notional', 0.0) or 0.0),
                'open_position_count': len(list(getattr(portfolio, 'open_positions', {}).values())),
                'open_positions': [
                    {
                        'symbol': str(pos.symbol or ''),
                        'entry_price_usd': float(pos.entry_price or 0.0),
                        'quantity': float(pos.quantity or 0.0),
                        'size_usd': float(pos.size_usd or 0.0),
                        'entry_time_utc': str(pos.entry_time_utc or ''),
                        'unrealized_pnl_usd': float(pos.unrealized_pnl or 0.0),
                        'stop_loss_price': None if pos.stop_loss_price is None else float(pos.stop_loss_price),
                        'take_profit_price': None if pos.take_profit_price is None else float(pos.take_profit_price),
                    }
                    for pos in getattr(portfolio, 'open_positions', {}).values()
                ] if hasattr(portfolio, 'open_positions') else [],
            },
            'runtime_config': {
                'mode': str(runtime_cfg.get('mode', 'paper')),
                'allow_live_orders': bool(runtime_cfg.get('allow_live_orders', False)),
                'max_open_positions': int(runtime_cfg.get('max_open_positions', 3)),
                'max_position_usd': float(runtime_cfg.get('max_position_usd', 45.0)),
                'min_position_usd': float(runtime_cfg.get('min_position_usd', 20.0)),
                'capital_aware_ranking_enabled': bool(runtime_cfg.get('capital_aware_ranking_enabled', True)),
                'selection_min_edge_bps': float(runtime_cfg.get('selection_min_edge_bps', 18.0)),
                'min_expected_net_edge_bps': float(runtime_cfg.get('min_expected_net_edge_bps', 55.0)),
                'symbol_blacklist': list(runtime_cfg.get('symbol_blacklist', [])),
            },
            'status': {
                'engine_healthy': True,
                'last_trade_timestamp_utc': None,
                'restart_recovery_ready': True,
            },
        }
        
        CHECKPOINT_FILE = OUT / 'engine_checkpoint.json'
        _atomic_write_json(CHECKPOINT_FILE, checkpoint, indent=2)
        
    except Exception as e:
        # Checkpoint failure is non-fatal; don't crash the engine
        pass


def _append_payout_intent(intent: Dict[str, Any]) -> None:
    intents = _load_payout_intents()
    intents.append(intent)
    _atomic_write_json(PAYOUT_INTENTS_FILE, intents, indent=2)


def _update_payout_intent(intent_id: str, updates: Dict[str, Any]) -> bool:
    intents = _load_payout_intents()
    found = False
    for item in intents:
        if str(item.get('intent_id', '')) == str(intent_id):
            item.update(dict(updates or {}))
            found = True
            break
    if found:
        _atomic_write_json(PAYOUT_INTENTS_FILE, intents, indent=2)
    return found


def _is_valid_webhook_url(value: str) -> bool:
    txt = str(value or '').strip()
    if not txt:
        return False
    if ' ' in txt:
        return False
    return txt.startswith('https://') or txt.startswith('http://')


def _resolve_payout_runtime_credentials(runtime_cfg: Dict[str, Any]) -> Dict[str, str]:
    cfg_url = str(runtime_cfg.get('payout_webhook_url', '') or '').strip()
    cfg_token = str(runtime_cfg.get('payout_webhook_auth_bearer', '') or '').strip()

    env_url_keys = [
        'LUMA_PAYOUT_WEBHOOK',
        'PAYOUT_WEBHOOK_URL',
        'CHIME_PAYOUT_WEBHOOK_URL',
        'CHIME_WEBHOOK_URL',
        'PAYOUT_WEBHOOK',
    ]
    env_token_keys = [
        'LUMA_PAYOUT_TOKEN',
        'PAYOUT_WEBHOOK_AUTH_BEARER',
        'CHIME_PAYOUT_BEARER_TOKEN',
        'CHIME_WEBHOOK_BEARER',
        'WEBHOOK_SHARED_SECRET',
    ]

    file_env_keys = globals().get('api_keys', {}) if isinstance(globals().get('api_keys', {}), dict) else {}

    resolved_url = cfg_url if _is_valid_webhook_url(cfg_url) else ''
    if not resolved_url:
        for key in env_url_keys:
            candidate = str(os.environ.get(key, '') or file_env_keys.get(key, '') or '').strip()
            if _is_valid_webhook_url(candidate):
                resolved_url = candidate
                break

    resolved_token = cfg_token
    if not resolved_token:
        for key in env_token_keys:
            candidate = str(os.environ.get(key, '') or file_env_keys.get(key, '') or '').strip()
            if candidate:
                resolved_token = candidate
                break

    return {
        'payout_webhook_url': resolved_url,
        'payout_webhook_auth_bearer': resolved_token,
    }


def _load_runtime_profile_lock_overrides() -> Dict[str, Any]:
    if not RUNTIME_PROFILE_LOCK_FILE.exists():
        return {}
    try:
        payload = json.loads(RUNTIME_PROFILE_LOCK_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    if not bool(payload.get('enabled', False)):
        return {}
    locked = payload.get('locked', {})
    return dict(locked) if isinstance(locked, dict) else {}


def _dispatch_payout_intent(runtime_cfg: Dict[str, Any], intent: Dict[str, Any]) -> Dict[str, Any]:
    auto_enabled = bool(runtime_cfg.get('payout_auto_dispatch_enabled', False))
    if not auto_enabled:
        return {'attempted': False, 'ok': False, 'reason': 'auto_dispatch_disabled'}

    dispatch_mode = str(runtime_cfg.get('payout_dispatch_mode', 'webhook') or 'webhook').strip().lower()
    if dispatch_mode == 'wallet_file':
        def _looks_like_card_number(value: str) -> bool:
            digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
            if not (12 <= len(digits) <= 19):
                return False
            try:
                checksum = 0
                parity = len(digits) % 2
                for idx, ch in enumerate(digits):
                    num = int(ch)
                    if idx % 2 == parity:
                        num *= 2
                        if num > 9:
                            num -= 9
                    checksum += num
                return checksum % 10 == 0
            except Exception:
                return False

        def _is_valid_wallet_address(address: str, network: str) -> bool:
            addr = str(address or '').strip()
            net = str(network or '').strip().upper()
            if not addr:
                return False
            if _looks_like_card_number(addr):
                return False
            if net == 'TRC20':
                return bool(re.match(r'^T[1-9A-HJ-NP-Za-km-z]{33}$', addr))
            if net in ('ERC20', 'BEP20'):
                return bool(re.match(r'^0x[a-fA-F0-9]{40}$', addr))
            if net in ('BTC', 'BITCOIN'):
                return bool(re.match(r'^(bc1[ac-hj-np-z02-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$', addr))
            return len(addr) >= 20

        wallet_address = str(runtime_cfg.get('payout_wallet_address', '') or '').strip()
        wallet_network = str(runtime_cfg.get('payout_wallet_network', 'TRC20') or 'TRC20').strip().upper()
        wallet_asset = str(runtime_cfg.get('payout_wallet_asset', 'USDT') or 'USDT').strip().upper()
        wallet_label = str(runtime_cfg.get('payout_wallet_label', 'self_custody_wallet') or 'self_custody_wallet').strip()
        if not wallet_address:
            return {'attempted': False, 'ok': False, 'reason': 'missing_payout_wallet_address'}
        if _looks_like_card_number(wallet_address):
            return {'attempted': False, 'ok': False, 'reason': 'wallet_address_looks_like_card_number'}
        if not _is_valid_wallet_address(wallet_address, wallet_network):
            return {'attempted': False, 'ok': False, 'reason': f'invalid_payout_wallet_address_for_network:{wallet_network}'}

        existing_requests: List[Dict[str, Any]] = []
        if WALLET_TRANSFER_REQUESTS_FILE.exists():
            try:
                with open(WALLET_TRANSFER_REQUESTS_FILE, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if isinstance(payload, list):
                    existing_requests = payload
            except Exception:
                existing_requests = []

        transfer_request = {
            'request_id': f"wallet-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}",
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'source': 'execution_orchestrator',
            'intent_id': str(intent.get('intent_id', '') or ''),
            'destination_type': 'wallet',
            'wallet_label': wallet_label,
            'asset': wallet_asset,
            'network': wallet_network,
            'address': wallet_address,
            'amount_usd': float(intent.get('amount_usd', 0.0) or 0.0),
            'destination': str(intent.get('destination', '') or ''),
            'destination_label': str(intent.get('destination_label', '') or ''),
            'account_hint': str(intent.get('account_hint', '') or ''),
            'status': 'REQUESTED',
            'notes': 'Manual or external executor should submit this withdrawal/deposit transfer.',
        }
        existing_requests.append(transfer_request)
        _atomic_write_json(WALLET_TRANSFER_REQUESTS_FILE, existing_requests, indent=2)
        return {
            'attempted': True,
            'ok': True,
            'reason': 'wallet_transfer_requested',
            'mode': 'wallet_file',
            'request_id': transfer_request['request_id'],
            'request_file': str(WALLET_TRANSFER_REQUESTS_FILE),
        }

    if dispatch_mode != 'webhook':
        return {'attempted': False, 'ok': False, 'reason': f'unsupported_dispatch_mode:{dispatch_mode}'}

    resolved = _resolve_payout_runtime_credentials(runtime_cfg)
    webhook_url = str(resolved.get('payout_webhook_url', '') or '').strip()
    if not _is_valid_webhook_url(webhook_url):
        return {'attempted': False, 'ok': False, 'reason': 'missing_payout_webhook_url'}

    timeout_sec = float(runtime_cfg.get('payout_webhook_timeout_sec', 10.0) or 10.0)
    auth_bearer = str(resolved.get('payout_webhook_auth_bearer', '') or '').strip()
    headers = {'Content-Type': 'application/json'}
    if auth_bearer:
        headers['Authorization'] = f'Bearer {auth_bearer}'

    started = time.time()
    try:
        response = requests.post(
            webhook_url,
            json=intent,
            headers=headers,
            timeout=max(1.0, timeout_sec),
        )
        latency_ms = (time.time() - started) * 1000.0
        ok = 200 <= int(response.status_code) < 300
        return {
            'attempted': True,
            'ok': bool(ok),
            'reason': 'ok' if ok else f'http_{int(response.status_code)}',
            'status_code': int(response.status_code),
            'latency_ms': float(round(latency_ms, 2)),
            'response_excerpt': (response.text or '')[:240],
        }
    except Exception as exc:
        latency_ms = (time.time() - started) * 1000.0
        return {
            'attempted': True,
            'ok': False,
            'reason': f'exception:{type(exc).__name__}',
            'latency_ms': float(round(latency_ms, 2)),
            'response_excerpt': str(exc)[:240],
        }


def _validate_runtime_cfg(raw_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    cfg = dict(raw_cfg or {})
    issues: List[str] = []

    profile_locked_values = _load_runtime_profile_lock_overrides()
    if profile_locked_values:
        cfg.update(profile_locked_values)
        issues.append(f"profile_lock_applied({len(profile_locked_values)})")

    def _as_bool(key: str, default: bool) -> bool:
        value = cfg.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            txt = value.strip().lower()
            if txt in ('1', 'true', 'yes', 'y', 'on'):
                return True
            if txt in ('0', 'false', 'no', 'n', 'off'):
                return False
        issues.append(f"{key}=invalid_bool({value})")
        return default

    def _as_float(key: str, default: float, min_v: Optional[float] = None, max_v: Optional[float] = None) -> float:
        value = cfg.get(key, default)
        try:
            out = float(value)
        except (TypeError, ValueError):
            issues.append(f"{key}=invalid_float({value})")
            out = default
        if min_v is not None and out < min_v:
            issues.append(f"{key}=below_min({out}<{min_v})")
            out = min_v
        if max_v is not None and out > max_v:
            issues.append(f"{key}=above_max({out}>{max_v})")
            out = max_v
        return out

    def _as_int(key: str, default: int, min_v: Optional[int] = None, max_v: Optional[int] = None) -> int:
        value = cfg.get(key, default)
        try:
            out = int(value)
        except (TypeError, ValueError):
            issues.append(f"{key}=invalid_int({value})")
            out = default
        if min_v is not None and out < min_v:
            issues.append(f"{key}=below_min({out}<{min_v})")
            out = min_v
        if max_v is not None and out > max_v:
            issues.append(f"{key}=above_max({out}>{max_v})")
            out = max_v
        return out

    mode = str(cfg.get('mode', 'paper')).strip().lower()
    if mode not in ('paper', 'live'):
        issues.append(f"mode=invalid({mode})")
        mode = 'paper'
    cfg['mode'] = mode

    cfg['allow_live_orders'] = _as_bool('allow_live_orders', False)
    cfg['kill_switch'] = _as_bool('kill_switch', False)
    cfg['paper_enabled'] = _as_bool('paper_enabled', True)
    cfg['strict_live_only'] = _as_bool('strict_live_only', False)
    cfg['futures_mode'] = _as_bool('futures_mode', False)
    cfg['capital_aware_ranking_enabled'] = _as_bool('capital_aware_ranking_enabled', True)
    cfg['x1000_auto_enabled'] = _as_bool('x1000_auto_enabled', False)
    cfg['x1000_auto_apply'] = _as_bool('x1000_auto_apply', False)
    cfg['force_live_mode'] = _as_bool('force_live_mode', False)
    cfg['shadow_intelligence_enabled'] = _as_bool('shadow_intelligence_enabled', True)
    cfg['shadow_river_enabled'] = _as_bool('shadow_river_enabled', True)
    cfg['shadow_arch_enabled'] = _as_bool('shadow_arch_enabled', True)

    cfg['loop_seconds'] = _as_float('loop_seconds', 1.0, 0.1, 60.0)
    cfg['max_drawdown_pct'] = _as_float('max_drawdown_pct', 10.0, 0.0, 100.0)
    cfg['max_daily_loss_usd'] = _as_float('max_daily_loss_usd', 200.0, 0.0, 1_000_000.0)
    cfg['max_portfolio_heat'] = _as_float('max_portfolio_heat', 0.4, 0.0, 1.0)
    cfg['max_position_usd'] = _as_float('max_position_usd', 50.0, 0.1, 10_000_000.0)
    cfg['min_position_usd'] = _as_float('min_position_usd', 5.0, 0.01, 10_000_000.0)
    cfg['reserve_usd'] = _as_float('reserve_usd', 15.0, 0.0, 10_000_000.0)
    cfg['fallback_buying_power_usd'] = _as_float('fallback_buying_power_usd', 0.0, 0.0, MAX_FALLBACK_BUYING_POWER_USD)
    cfg['base_risk_fraction'] = _as_float('base_risk_fraction', 0.20, 0.01, 1.0)
    cfg['leverage_multiplier'] = _as_float('leverage_multiplier', 1.0, 1.0, 5.0)
    cfg['micro_balance_threshold_usd'] = _as_float('micro_balance_threshold_usd', 25.0, 0.0, 10000.0)
    cfg['position_hold_seconds'] = _as_float('position_hold_seconds', 5.0, 0.1, 120.0)
    cfg['position_max_hold_seconds'] = _as_float('position_max_hold_seconds', 30.0, 1.0, 600.0)
    cfg['position_hard_max_hold_seconds'] = _as_float('position_hard_max_hold_seconds', 240.0, 5.0, 3600.0)
    cfg['position_poll_seconds'] = _as_float('position_poll_seconds', 1.0, 0.1, 5.0)
    cfg['position_min_hold_seconds'] = _as_float('position_min_hold_seconds', 5.0, 0.0, 300.0)
    cfg['position_stop_loss_min_hold_seconds'] = _as_float('position_stop_loss_min_hold_seconds', 8.0, 0.0, 300.0)
    cfg['position_tp_net_bps'] = _as_float('position_tp_net_bps', 18.0, 1.0, 1000.0)
    cfg['position_sl_net_bps'] = _as_float('position_sl_net_bps', 40.0, 1.0, 2000.0)
    cfg['position_tp_volatility_multiplier'] = _as_float('position_tp_volatility_multiplier', 0.9, 0.1, 10.0)
    cfg['position_sl_volatility_multiplier'] = _as_float('position_sl_volatility_multiplier', 2.2, 0.5, 20.0)
    cfg['position_volatility_bps_floor'] = _as_float('position_volatility_bps_floor', 6.0, 0.0, 1000.0)
    cfg['position_volatility_bps_cap'] = _as_float('position_volatility_bps_cap', 80.0, 1.0, 5000.0)
    cfg['position_timeout_grace_net_bps'] = _as_float('position_timeout_grace_net_bps', -8.0, -1000.0, 500.0)
    cfg['position_timeout_exit_enabled'] = _as_bool('position_timeout_exit_enabled', True)
    cfg['reconciliation_auto_cancel_orphans'] = _as_bool('reconciliation_auto_cancel_orphans', True)
    cfg['min_expected_net_edge_bps'] = _as_float('min_expected_net_edge_bps', 65.0, 1.0, 2000.0)
    cfg['edge_fee_coverage_multiplier'] = _as_float('edge_fee_coverage_multiplier', 1.15, 0.1, 5.0)
    cfg['maker_first_enabled'] = _as_bool('maker_first_enabled', True)
    cfg['kraken_maker_fee_pct'] = _as_float('kraken_maker_fee_pct', 0.0016, 0.0, 0.05)
    cfg['adaptive_entry_gate_enabled'] = _as_bool('adaptive_entry_gate_enabled', True)
    cfg['adaptive_entry_gate_min_bps'] = _as_float('adaptive_entry_gate_min_bps', 42.0, 1.0, 2000.0)
    cfg['adaptive_entry_gate_max_bps'] = _as_float('adaptive_entry_gate_max_bps', 120.0, 1.0, 2000.0)
    cfg['adaptive_entry_gate_relax_step_bps'] = _as_float('adaptive_entry_gate_relax_step_bps', 1.5, 0.1, 200.0)
    cfg['adaptive_entry_gate_tighten_step_bps'] = _as_float('adaptive_entry_gate_tighten_step_bps', 3.0, 0.1, 200.0)
    cfg['adaptive_entry_gate_starvation_sec'] = _as_float('adaptive_entry_gate_starvation_sec', 45.0, 5.0, 3600.0)
    cfg['adaptive_entry_gate_adjust_cooldown_sec'] = _as_float('adaptive_entry_gate_adjust_cooldown_sec', 20.0, 1.0, 3600.0)
    cfg['adaptive_entry_gate_recent_trades'] = _as_int('adaptive_entry_gate_recent_trades', 8, 2, 120)
    cfg['adaptive_entry_gate_min_win_rate_pct'] = _as_float('adaptive_entry_gate_min_win_rate_pct', 35.0, 0.0, 100.0)
    cfg['adaptive_entry_gate_min_avg_net_pnl_usd'] = _as_float('adaptive_entry_gate_min_avg_net_pnl_usd', 0.0, -1000000.0, 1000000.0)
    cfg['selection_min_edge_bps'] = _as_float('selection_min_edge_bps', 6.0, 1.0, 2000.0)
    cfg['min_gate_score_for_entry'] = _as_float('min_gate_score_for_entry', 0.90, 0.0, 1.0)
    cfg['micro_max_min_notional_usd'] = _as_float('micro_max_min_notional_usd', 25.0, 1.0, 10000.0)
    cfg['micro_priority_bonus'] = _as_float('micro_priority_bonus', 15.0, 0.0, 1000.0)
    cfg['pair_fill_guard_enabled'] = _as_bool('pair_fill_guard_enabled', True)
    cfg['min_order_fee_cushion_pct'] = _as_float('min_order_fee_cushion_pct', 0.015, 0.0, 0.50)
    cfg['min_order_slippage_cushion_pct'] = _as_float('min_order_slippage_cushion_pct', 0.010, 0.0, 0.50)
    cfg['min_notional_floor_usd'] = _as_float('min_notional_floor_usd', 1.0, 0.0, 10000.0)
    cfg['auto_convert_collateral'] = _as_bool('auto_convert_collateral', True)
    cfg['collateral_sell_fraction'] = _as_float('collateral_sell_fraction', 0.20, 0.01, 1.0)
    cfg['collateral_convert_cooldown_sec'] = _as_float('collateral_convert_cooldown_sec', 12.0, 0.0, 3600.0)
    cfg['auto_sweep_to_usd_enabled'] = _as_bool('auto_sweep_to_usd_enabled', True)
    cfg['auto_sweep_full_balance'] = _as_bool('auto_sweep_full_balance', True)
    cfg['auto_sweep_require_no_open_positions'] = _as_bool('auto_sweep_require_no_open_positions', True)
    cfg['auto_sweep_min_notional_usd'] = _as_float('auto_sweep_min_notional_usd', 2.0, 0.0, 1000000.0)
    cfg['auto_sweep_reserve_asset_qty'] = _as_float('auto_sweep_reserve_asset_qty', 0.0, 0.0, 1000000000.0)
    cfg['auto_sweep_max_assets_per_loop'] = _as_int('auto_sweep_max_assets_per_loop', 2, 1, 25)
    cfg['post_conversion_settle_sec'] = _as_float('post_conversion_settle_sec', 1.2, 0.0, 15.0)
    cfg['post_conversion_balance_retries'] = _as_int('post_conversion_balance_retries', 2, 1, 8)
    cfg['micro_reentry_governor_enabled'] = _as_bool('micro_reentry_governor_enabled', True)
    cfg['micro_reentry_scope_threshold_usd'] = _as_float('micro_reentry_scope_threshold_usd', 50.0, 0.0, 100000.0)
    cfg['micro_reentry_cooldown_sec'] = _as_float('micro_reentry_cooldown_sec', 45.0, 0.0, 3600.0)
    cfg['micro_reentry_max_per_hour'] = _as_int('micro_reentry_max_per_hour', 6, 1, 1000)
    cfg['profit_lock_enabled'] = _as_bool('profit_lock_enabled', True)
    cfg['profit_lock_trigger_usd'] = _as_float('profit_lock_trigger_usd', 25.0, 0.0, 1000000000.0)
    cfg['profit_lock_drawdown_frac'] = _as_float('profit_lock_drawdown_frac', 0.35, 0.01, 1.0)
    cfg['profit_lock_risk_floor'] = _as_float('profit_lock_risk_floor', 0.35, 0.05, 1.0)
    cfg['runway_goal_usd'] = _as_float('runway_goal_usd', 1000000.0, 1.0, 1000000000.0)
    cfg['runway_goal_horizon_days'] = _as_float('runway_goal_horizon_days', 3650.0, 1.0, 36500.0)
    cfg['payout_milestones_enabled'] = _as_bool('payout_milestones_enabled', True)
    cfg['payout_fraction'] = _as_float('payout_fraction', 0.50, 0.01, 1.0)
    cfg['payout_min_amount_usd'] = _as_float('payout_min_amount_usd', 10.0, 0.0, 1000000000.0)
    cfg['payout_destination'] = str(cfg.get('payout_destination', 'chime')).strip().lower() or 'chime'
    cfg['payout_destination_label'] = str(cfg.get('payout_destination_label', 'Chime')).strip() or 'Chime'
    cfg['payout_account_hint'] = str(cfg.get('payout_account_hint', 'primary')).strip() or 'primary'
    cfg['payout_auto_dispatch_enabled'] = _as_bool('payout_auto_dispatch_enabled', False)
    cfg['payout_dispatch_mode'] = str(cfg.get('payout_dispatch_mode', 'webhook')).strip().lower() or 'webhook'
    cfg['payout_webhook_url'] = str(cfg.get('payout_webhook_url', '')).strip()
    cfg['payout_webhook_auth_bearer'] = str(cfg.get('payout_webhook_auth_bearer', '')).strip()
    cfg['payout_webhook_timeout_sec'] = _as_float('payout_webhook_timeout_sec', 10.0, 1.0, 60.0)
    cfg['payout_wallet_address'] = str(cfg.get('payout_wallet_address', '') or '').strip()
    cfg['payout_wallet_network'] = str(cfg.get('payout_wallet_network', 'TRC20') or 'TRC20').strip().upper() or 'TRC20'
    cfg['payout_wallet_asset'] = str(cfg.get('payout_wallet_asset', 'USDT') or 'USDT').strip().upper() or 'USDT'
    cfg['payout_wallet_label'] = str(cfg.get('payout_wallet_label', 'self_custody_wallet') or 'self_custody_wallet').strip() or 'self_custody_wallet'

    resolved_payout = _resolve_payout_runtime_credentials(cfg)
    cfg['payout_webhook_url'] = str(resolved_payout.get('payout_webhook_url', '') or '').strip()
    cfg['payout_webhook_auth_bearer'] = str(resolved_payout.get('payout_webhook_auth_bearer', '') or '').strip()

    cfg['max_open_positions'] = _as_int('max_open_positions', 5, 1, 100)
    cfg['max_consecutive_order_failures'] = _as_int('max_consecutive_order_failures', 8, 1, 100)
    # PATCH: Always use all available symbols for scan size
    cfg['capital_aware_scan_size'] = len([s for s in SYMBOL_REGISTRY.keys() if isinstance(s, str)])
    cfg['micro_scan_size'] = len([s for s in SYMBOL_REGISTRY.keys() if isinstance(s, str)])
    print(f"[PATCHED-SCAN-SIZE] capital_aware_scan_size={cfg['capital_aware_scan_size']} micro_scan_size={cfg['micro_scan_size']} total_symbols={len(SYMBOL_REGISTRY)}")
    cfg['capital_aware_rank_cache_sec'] = _as_float('capital_aware_rank_cache_sec', 15.0, 0.0, 300.0)
    cfg['capital_aware_selection_timeout_sec'] = _as_float('capital_aware_selection_timeout_sec', 4.0, 0.25, 60.0)
    cfg['x1000_interval_loops'] = _as_int('x1000_interval_loops', 60, 1, 100000)
    cfg['x1000_passes'] = _as_int('x1000_passes', 2, 1, 2)
    cfg['x1000_timeout_sec'] = _as_int('x1000_timeout_sec', 120, 10, 3600)
    cfg['shadow_arch_every_loops'] = _as_int('shadow_arch_every_loops', 25, 1, 5000)
    cfg['shadow_arch_min_points'] = _as_int('shadow_arch_min_points', 180, 60, 5000)
    cfg['shadow_arch_high_vol_pct'] = _as_float('shadow_arch_high_vol_pct', 1.2, 0.01, 50.0)
    cfg['adaptive_selection_tuner_enabled'] = _as_bool('adaptive_selection_tuner_enabled', True)
    cfg['adaptive_selection_tuner_interval_loops'] = _as_int('adaptive_selection_tuner_interval_loops', 30, 1, 5000)
    cfg['adaptive_selection_tuner_starvation_sec'] = _as_float('adaptive_selection_tuner_starvation_sec', 60.0, 5.0, 3600.0)
    cfg['adaptive_selection_tuner_step_edge_bps'] = _as_float('adaptive_selection_tuner_step_edge_bps', 0.5, 0.05, 10.0)
    cfg['adaptive_selection_tuner_step_gate_score'] = _as_float('adaptive_selection_tuner_step_gate_score', 0.01, 0.001, 0.20)
    cfg['adaptive_selection_tuner_min_edge_bps'] = _as_float('adaptive_selection_tuner_min_edge_bps', 3.0, 1.0, 2000.0)
    cfg['adaptive_selection_tuner_max_edge_bps'] = _as_float('adaptive_selection_tuner_max_edge_bps', 20.0, 1.0, 2000.0)
    cfg['adaptive_selection_tuner_min_gate_score'] = _as_float('adaptive_selection_tuner_min_gate_score', 0.55, 0.0, 1.0)
    cfg['adaptive_selection_tuner_max_gate_score'] = _as_float('adaptive_selection_tuner_max_gate_score', 0.95, 0.0, 1.0)
    cfg['adaptive_selection_tuner_recent_closed'] = _as_int('adaptive_selection_tuner_recent_closed', 10, 3, 200)
    cfg['adaptive_selection_tuner_min_win_rate_pct'] = _as_float('adaptive_selection_tuner_min_win_rate_pct', 35.0, 0.0, 100.0)
    cfg['adaptive_selection_tuner_min_avg_net_pnl_usd'] = _as_float('adaptive_selection_tuner_min_avg_net_pnl_usd', 0.0, -1000000.0, 1000000.0)
    cfg['profit_protect_dynamic_enabled'] = _as_bool('profit_protect_dynamic_enabled', True)
    cfg['profit_protect_loss_streak_trigger'] = _as_int('profit_protect_loss_streak_trigger', 2, 1, 20)
    cfg['profit_protect_loss_streak_floor'] = _as_float('profit_protect_loss_streak_floor', 0.35, 0.05, 1.0)
    cfg['profit_protect_drawdown_floor'] = _as_float('profit_protect_drawdown_floor', 0.45, 0.05, 1.0)
    cfg['profit_protect_win_streak_cap'] = _as_float('profit_protect_win_streak_cap', 1.35, 1.0, 3.0)
    cfg['symbol_skip_cooldown_sec'] = _as_float('symbol_skip_cooldown_sec', 45.0, 0.0, 3600.0)
    cfg['symbol_permission_cooldown_sec'] = _as_float('symbol_permission_cooldown_sec', 14400.0, 60.0, 604800.0)
    cfg['ticker_fail_cooldown_sec'] = _as_float('ticker_fail_cooldown_sec', 5.0, 0.1, 600.0)
    cfg['min_order_cooldown_sec'] = _as_float('min_order_cooldown_sec', 60.0, 0.1, 3600.0)
    cfg['live_ohlc_cache_enabled'] = _as_bool('live_ohlc_cache_enabled', True)
    cfg['live_ohlc_cache_ttl_sec'] = _as_float('live_ohlc_cache_ttl_sec', 8.0, 0.0, 300.0)
    cfg['live_ohlc_cache_max_points'] = _as_int('live_ohlc_cache_max_points', 400, 60, 5000)
    cfg['live_websocket_enabled'] = _as_bool('live_websocket_enabled', True)
    cfg['live_websocket_seed_rest'] = _as_bool('live_websocket_seed_rest', True)
    cfg['live_websocket_reconnect_sec'] = _as_float('live_websocket_reconnect_sec', 8.0, 1.0, 300.0)
    cfg['live_websocket_stale_after_sec'] = _as_float('live_websocket_stale_after_sec', 20.0, 5.0, 600.0)
    cfg['live_websocket_ping_interval_sec'] = _as_float('live_websocket_ping_interval_sec', 20.0, 5.0, 120.0)
    cfg['live_selection_refresh_every'] = _as_int('live_selection_refresh_every', 15, 1, 10000)
    cfg['live_reselection_enabled'] = _as_bool('live_reselection_enabled', False)
    cfg['live_reselection_interval_sec'] = _as_float('live_reselection_interval_sec', 1800.0, 60.0, 86400.0)
    cfg['live_reselection_min_files'] = _as_int('live_reselection_min_files', 1, 1, 100)

    raw_symbol_blacklist = cfg.get('symbol_blacklist', [])
    parsed_blacklist: List[str] = []
    if isinstance(raw_symbol_blacklist, str):
        parsed_blacklist = [s.strip().upper() for s in raw_symbol_blacklist.replace(';', ',').split(',') if s.strip()]
    elif isinstance(raw_symbol_blacklist, list):
        parsed_blacklist = [str(s).strip().upper() for s in raw_symbol_blacklist if str(s).strip()]
    cfg['symbol_blacklist'] = sorted(list({s for s in parsed_blacklist}))

    raw_hard_symbol_blacklist = cfg.get('hard_symbol_blacklist', ['AUD', 'EUR', 'GBP'])
    parsed_hard_blacklist: List[str] = []
    if isinstance(raw_hard_symbol_blacklist, str):
        parsed_hard_blacklist = [s.strip().upper() for s in raw_hard_symbol_blacklist.replace(';', ',').split(',') if s.strip()]
    elif isinstance(raw_hard_symbol_blacklist, list):
        parsed_hard_blacklist = [str(s).strip().upper() for s in raw_hard_symbol_blacklist if str(s).strip()]
    cfg['hard_symbol_blacklist'] = sorted(list({s for s in parsed_hard_blacklist}))

    default_withdraw_levels = [3, 5, 7, 9]
    raw_levels = cfg.get('payout_milestone_levels', default_withdraw_levels)
    parsed_levels: List[int] = []
    if isinstance(raw_levels, str):
        parsed_levels = [int(s.strip()) for s in raw_levels.replace(';', ',').split(',') if s.strip().isdigit()]
    elif isinstance(raw_levels, list):
        for level in raw_levels:
            try:
                parsed_levels.append(int(level))
            except Exception:
                continue
    parsed_levels = sorted({lv for lv in parsed_levels if lv >= 1})
    cfg['payout_milestone_levels'] = parsed_levels or default_withdraw_levels


    # Use all available symbols from the registry, excluding blacklists
    all_symbols = [s for s in SYMBOL_REGISTRY.keys() if isinstance(s, str)]
    symbol_blacklist = set(cfg.get('symbol_blacklist', []))
    hard_symbol_blacklist = set(cfg.get('hard_symbol_blacklist', []))
    filtered_symbols = [s for s in all_symbols if s not in symbol_blacklist and s not in hard_symbol_blacklist]
    cfg['micro_low_min_order_symbols'] = filtered_symbols
    print(f"[DEBUG-FULL-SYMBOLS] scan_size={len(filtered_symbols)} symbols={filtered_symbols[:20]} ... total={len(filtered_symbols)}")

    if cfg['kill_switch']:
        cfg['allow_live_orders'] = False
    if cfg['mode'] != 'live':
        cfg['allow_live_orders'] = False

    if cfg['adaptive_entry_gate_max_bps'] < cfg['adaptive_entry_gate_min_bps']:
        cfg['adaptive_entry_gate_max_bps'] = cfg['adaptive_entry_gate_min_bps']

    if issues:
        print(f"  ⚠ Runtime config normalized ({len(issues)} issue(s)): {'; '.join(issues[:8])}")

    return cfg


def _force_live_mode(raw_cfg: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Optionally force live mode when explicitly armed by config.

    By default this function preserves operator/runtime mode and only enforces
    safety rails (kill switch disarms live orders).
    """
    cfg = dict(raw_cfg or {})
    force_live = bool(cfg.get('force_live_mode', False))
    kill_switch = bool(cfg.get('kill_switch', False))

    if not force_live:
        mode = str(cfg.get('mode', 'paper') or 'paper').strip().lower()
        cfg['mode'] = mode if mode in ('paper', 'live') else 'paper'
        if cfg['mode'] != 'live':
            cfg['allow_live_orders'] = False
            cfg['paper_enabled'] = bool(cfg.get('paper_enabled', True))
        if kill_switch:
            cfg['allow_live_orders'] = False
        return cfg

    cfg['mode'] = 'live'
    cfg['paper_enabled'] = False

    cfg['allow_live_orders'] = False if kill_switch else True

    alpaca_mode = str(cfg.get('alpaca_authorized_mode', 'paper') or 'paper').strip().lower()
    if alpaca_mode != 'live':
        cfg['alpaca_live_trading_enabled'] = False

    return cfg


# Structured Event Logging System
class StructuredEventLogger:
    """Emit structured JSON events for full operational visibility + audit trail."""

    def __init__(self, events_file: Path):
        self.events_file = Path(events_file)
        self.events_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._event_counts: Dict[str, int] = {}
        self._loop_latencies: List[float] = []
        self._error_rate_window: deque = deque(maxlen=100)

    def emit(self, event_type: str, loop_count: int, symbol: Optional[str] = None, 
             reason_code: Optional[str] = None, latency_ms: float = 0.0, txid: Optional[str] = None,
             context: Optional[Dict[str, Any]] = None) -> str:
        """Emit a structured event with full context."""
        event_id = str(uuid.uuid4())[:8]
        timestamp_utc = datetime.now(timezone.utc).isoformat()
        
        payload = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp_utc": timestamp_utc,
            "loop": loop_count,
            "symbol": symbol,
            "reason_code": reason_code,
            "latency_ms": round(latency_ms, 2),
            "txid": txid,
        }
        if context:
            payload.update(context)
        
        self._event_counts[event_type] = self._event_counts.get(event_type, 0) + 1
        if latency_ms > 0:
            self._loop_latencies.append(latency_ms)
        if reason_code and reason_code.startswith("error_"):
            self._error_rate_window.append(1)
        
        with self._lock:
            with self.events_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, separators=(",", ":")) + "\n")
        
        return event_id

    def get_health_snapshot(self) -> Dict[str, Any]:
        """Return operational health metrics for health_metrics.json."""
        total_events = sum(self._event_counts.values())
        error_count = self._error_rate_window.count(1)
        error_rate = (error_count / len(self._error_rate_window) * 100.0) if self._error_rate_window else 0.0
        
        latencies = sorted(self._loop_latencies[-1000:]) if self._loop_latencies else []
        p50_lat = latencies[len(latencies) // 2] if latencies else 0.0
        p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
        p99_lat = latencies[int(len(latencies) * 0.99)] if latencies else 0.0
        
        return {
            "total_events": total_events,
            "event_type_counts": dict(self._event_counts),
            "error_rate_pct": round(error_rate, 2),
            "latency_p50_ms": round(p50_lat, 2),
            "latency_p95_ms": round(p95_lat, 2),
            "latency_p99_ms": round(p99_lat, 2),
            "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        }


class ShadowIntelligence:
    """Phase-1 shadow intelligence (log-only). Never affects order decisions."""

    def __init__(self) -> None:
        self._edge_mean = RiverMean() if RIVER_AVAILABLE else None
        self._edge_var = RiverVar() if RIVER_AVAILABLE else None
        self._conf_mean = RiverMean() if RIVER_AVAILABLE else None
        self._conf_var = RiverVar() if RIVER_AVAILABLE else None
        self._last_snapshot: Dict[str, Any] = {
            'enabled': False,
            'reason': 'not_initialized',
        }

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _zscore(value: float, mean_obj: Any, var_obj: Any) -> float:
        if mean_obj is None or var_obj is None:
            return 0.0
        try:
            mean_v = float(getattr(mean_obj, 'get')())
            var_v = float(getattr(var_obj, 'get')())
            if var_v <= 1e-12:
                return 0.0
            return float((value - mean_v) / max(var_v ** 0.5, 1e-9))
        except Exception:
            return 0.0

    def evaluate(self, loop_count: int, symbol: str, engine_decision: Dict[str, Any], runtime_cfg: Dict[str, Any]) -> Dict[str, Any]:
        if not bool(runtime_cfg.get('shadow_intelligence_enabled', True)):
            self._last_snapshot = {'enabled': False, 'reason': 'shadow_disabled'}
            return dict(self._last_snapshot)

        edge_bps = self._safe_float(engine_decision.get('edge_bps', 0.0), 0.0)
        confidence = self._safe_float(engine_decision.get('confidence', 0.0), 0.0)
        recent_closes = engine_decision.get('recent_closes', [])

        snapshot: Dict[str, Any] = {
            'enabled': True,
            'symbol': str(symbol or ''),
            'river_available': bool(RIVER_AVAILABLE),
            'arch_available': bool(ARCH_AVAILABLE),
            'edge_bps': float(round(edge_bps, 4)),
            'confidence': float(round(confidence, 6)),
        }

        if bool(runtime_cfg.get('shadow_river_enabled', True)) and RIVER_AVAILABLE:
            try:
                self._edge_mean.update(edge_bps)
                self._edge_var.update(edge_bps)
                self._conf_mean.update(confidence)
                self._conf_var.update(confidence)
                snapshot['river_edge_mean_bps'] = float(round(self._safe_float(self._edge_mean.get(), 0.0), 4))
                snapshot['river_edge_zscore'] = float(round(self._zscore(edge_bps, self._edge_mean, self._edge_var), 4))
                snapshot['river_conf_mean'] = float(round(self._safe_float(self._conf_mean.get(), 0.0), 6))
                snapshot['river_conf_zscore'] = float(round(self._zscore(confidence, self._conf_mean, self._conf_var), 4))
            except Exception as exc:
                snapshot['river_error'] = str(exc)[:120]

        arch_enabled = bool(runtime_cfg.get('shadow_arch_enabled', True)) and ARCH_AVAILABLE
        arch_every_loops = int(runtime_cfg.get('shadow_arch_every_loops', 25) or 25)
        arch_min_points = int(runtime_cfg.get('shadow_arch_min_points', 180) or 180)
        high_vol_pct = float(runtime_cfg.get('shadow_arch_high_vol_pct', 1.2) or 1.2)

        if arch_enabled:
            run_arch_now = (loop_count % max(1, arch_every_loops)) == 0
            if run_arch_now and isinstance(recent_closes, list) and len(recent_closes) >= arch_min_points:
                try:
                    closes = np.asarray(recent_closes, dtype=float)
                    closes = closes[np.isfinite(closes)]
                    if closes.size >= arch_min_points and np.all(closes > 0):
                        rets = np.diff(np.log(closes)) * 100.0
                        if rets.size >= 30:
                            model = arch_model(rets, mean='Zero', vol='Garch', p=1, q=1, dist='normal')
                            fit = model.fit(disp='off')
                            fcast = fit.forecast(horizon=1)
                            next_var = float(fcast.variance.values[-1, 0])
                            next_vol_pct = max(0.0, next_var) ** 0.5
                            snapshot['arch_next_vol_pct'] = float(round(next_vol_pct, 6))
                            snapshot['arch_regime'] = 'high_vol' if next_vol_pct >= high_vol_pct else 'normal'
                except Exception as exc:
                    snapshot['arch_error'] = str(exc)[:120]

        self._last_snapshot = dict(snapshot)
        return dict(snapshot)

    def last_snapshot(self) -> Dict[str, Any]:
        return dict(self._last_snapshot)


api_keys = load_api_keys()
try:
    import importlib.util

    registry_path = ROOT / 'symbol_registry_auto.py'
    spec = importlib.util.spec_from_file_location('symbol_registry_auto', registry_path)
    if spec and spec.loader and registry_path.exists():
        symbol_registry_auto = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(symbol_registry_auto)
        SYMBOL_REGISTRY = getattr(symbol_registry_auto, 'SYMBOL_REGISTRY', {})
    else:
        SYMBOL_REGISTRY = {}
except Exception:
    SYMBOL_REGISTRY = {}
class UniversalExchangeRouter:
    """Routes orders to correct exchange based on symbol"""
    ALPACA_SUPPORTED_SYMBOLS = {'BTC', 'ETH', 'SOL', 'XRP', 'DOGE'}
    
    def __init__(self, api_keys: Dict):
        self.api_keys = api_keys
        self.kraken_api_key = api_keys.get('KRAKEN_API_KEY')
        self.kraken_api_secret = api_keys.get('KRAKEN_API_SECRET')
        self.session = requests.Session()
        self.alpaca_api_key = (
            api_keys.get('ALPACA_API_KEY')
            or api_keys.get('APCA_API_KEY_ID')
            or os.environ.get('ALPACA_API_KEY')
            or os.environ.get('APCA_API_KEY_ID')
            or ''
        )
        self.alpaca_api_secret = (
            api_keys.get('ALPACA_API_SECRET')
            or api_keys.get('APCA_API_SECRET_KEY')
            or os.environ.get('ALPACA_API_SECRET')
            or os.environ.get('APCA_API_SECRET_KEY')
            or ''
        )
        self.alpaca_trading_base = str(
            api_keys.get('ALPACA_BASE_URL')
            or api_keys.get('ALPACA_TRADING_BASE_URL')
            or os.environ.get('ALPACA_BASE_URL')
            or os.environ.get('ALPACA_TRADING_BASE_URL')
            or 'https://api.alpaca.markets'
        ).strip().rstrip('/')
        self.alpaca_session = requests.Session()
        if self.alpaca_api_key and self.alpaca_api_secret:
            self.alpaca_session.headers.update(
                {
                    'APCA-API-KEY-ID': self.alpaca_api_key,
                    'APCA-API-SECRET-KEY': self.alpaca_api_secret,
                }
            )
        self._route_pref_cache: Dict[str, Any] = {}
        self._route_pref_cache_ts = 0.0
        # Use ns-scale nonce to stay above any previously used ms/non-ms nonce values.
        self._nonce_counter = int(time.time_ns())

    def _alpaca_is_configured(self) -> bool:
        return bool(self.alpaca_api_key and self.alpaca_api_secret)

    def _load_route_preferences(self) -> Dict[str, Any]:
        now_ts = time.time()
        if (now_ts - self._route_pref_cache_ts) < 1.0 and self._route_pref_cache:
            return dict(self._route_pref_cache)

        prefs = {
            'mode': 'paper',
            'allow_live_orders': False,
            'paper_enabled': True,
            'preferred_live_exchange': 'alpaca',
            'alpaca_live_trading_enabled': True,
        }
        try:
            if RUNTIME_FILE.exists():
                payload = json.loads(RUNTIME_FILE.read_text(encoding='utf-8'))
                if isinstance(payload, dict):
                    prefs['mode'] = str(payload.get('mode', prefs['mode']) or prefs['mode']).strip().lower()
                    prefs['allow_live_orders'] = bool(payload.get('allow_live_orders', prefs['allow_live_orders']))
                    prefs['paper_enabled'] = bool(payload.get('paper_enabled', prefs['paper_enabled']))
                    prefs['preferred_live_exchange'] = str(
                        payload.get('preferred_live_exchange', prefs['preferred_live_exchange']) or prefs['preferred_live_exchange']
                    ).strip().lower()
                    prefs['alpaca_live_trading_enabled'] = bool(
                        payload.get('alpaca_live_trading_enabled', prefs['alpaca_live_trading_enabled'])
                    )
        except Exception:
            pass

        self._route_pref_cache = dict(prefs)
        self._route_pref_cache_ts = now_ts
        return prefs

    def get_route_exchange(self, symbol: str, preferred_exchange: Optional[str] = None) -> str:
        config = self.get_symbol_config(symbol) or {}
        default_exchange = str(config.get('exchange', 'kraken') or 'kraken').strip().lower()
        override = str(preferred_exchange or '').strip().lower()
        if override in {'kraken', 'alpaca', 'binance_fallback'}:
            return override

        prefs = self._load_route_preferences()
        if (
            self._alpaca_is_configured()
            and prefs.get('alpaca_live_trading_enabled', True)
            and prefs.get('mode') == 'live'
            and prefs.get('allow_live_orders', False)
            and not prefs.get('paper_enabled', True)
            and str(prefs.get('preferred_live_exchange', 'alpaca')).lower() in {'alpaca', 'auto'}
            and str(symbol or '').upper() in self.ALPACA_SUPPORTED_SYMBOLS
        ):
            return 'alpaca'
        return default_exchange

    @staticmethod
    def _alpaca_symbol(symbol: str) -> str:
        return f"{str(symbol or '').upper()}USD"

    @staticmethod
    def _normalize_alpaca_position_symbol(value: str) -> str:
        txt = str(value or '').upper().replace('/', '').replace('-', '')
        if txt.endswith('USD') and len(txt) > 3:
            txt = txt[:-3]
        return txt

    def _alpaca_get_account(self) -> Dict[str, Any]:
        if not self._alpaca_is_configured():
            return {}
        try:
            response = self.alpaca_session.get(f"{self.alpaca_trading_base}/v2/account", timeout=15)
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {}
        except (requests.RequestException, ValueError, TypeError):
            return {}

    def _alpaca_list_positions(self) -> List[Dict[str, Any]]:
        if not self._alpaca_is_configured():
            return []
        try:
            response = self.alpaca_session.get(f"{self.alpaca_trading_base}/v2/positions", timeout=15)
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, list) else []
        except (requests.RequestException, ValueError, TypeError):
            return []

    def _build_alpaca_balance_map(self) -> Dict[str, Any]:
        balances: Dict[str, Any] = {}
        account = self._alpaca_get_account()
        if account:
            try:
                cash = float(account.get('cash', 0.0) or 0.0)
            except Exception:
                cash = 0.0
            try:
                buying_power = float(account.get('buying_power', cash) or cash)
            except Exception:
                buying_power = cash
            try:
                equity = float(account.get('equity', cash) or cash)
            except Exception:
                equity = cash
            balances.update(
                {
                    'USD': cash,
                    'ZUSD': cash,
                    'USD.ALPACA': cash,
                    'BUYING_POWER': buying_power,
                    'EQUITY': equity,
                }
            )

        for position in self._alpaca_list_positions():
            symbol = self._normalize_alpaca_position_symbol(position.get('symbol', ''))
            if not symbol:
                continue
            try:
                qty = float(position.get('qty_available', position.get('qty', 0.0)) or 0.0)
            except Exception:
                qty = 0.0
            if qty <= 0:
                continue
            balances[symbol] = float(balances.get(symbol, 0.0) or 0.0) + qty

        return balances

    def _kraken_private_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        max_nonce_attempts = 3
        for attempt in range(max_nonce_attempts):
            payload_params = dict(params or {})
            now_nonce = int(time.time_ns())
            self._nonce_counter = max(self._nonce_counter + 1, now_nonce)
            nonce = str(self._nonce_counter)
            payload_params['nonce'] = nonce

            postdata = urllib.parse.urlencode(payload_params)
            encoded = (nonce + postdata).encode('utf-8')
            message = endpoint.encode('utf-8') + hashlib.sha256(encoded).digest()

            secret = self.kraken_api_secret or ""
            signature = hmac.new(
                base64.b64decode(secret),
                message,
                hashlib.sha512
            ).digest()

            headers = {
                'API-Key': self.kraken_api_key or "",
                'API-Sign': base64.b64encode(signature).decode('utf-8')
            }

            try:
                response = self.session.post(
                    "https://api.kraken.com" + endpoint,
                    data=postdata,
                    headers=headers,
                    timeout=15
                )
                payload = response.json()
            except requests.RequestException as exc:
                if attempt < max_nonce_attempts - 1:
                    time.sleep(0.15 * (attempt + 1))
                    continue
                return {'error': [f'network_error:{exc}'], 'result': {}}

            errors = payload.get('error') or []
            nonce_err = any('Invalid nonce' in str(err) for err in errors)
            if nonce_err and attempt < max_nonce_attempts - 1:
                self._nonce_counter = max(self._nonce_counter + 1000, int(time.time_ns()))
                time.sleep(0.12 * (attempt + 1))
                continue
            return payload

        return {'error': ['EAPI:Invalid nonce'], 'result': {}}
    
    def get_symbol_config(self, symbol: str) -> Optional[Dict]:
        """Get exchange routing for symbol"""
        return SYMBOL_REGISTRY.get(symbol.upper())
    
    def place_order(self, symbol: str, side: str, size: float, limit_price: Optional[float] = None,
                    leverage: float = 1.0, preferred_exchange: Optional[str] = None,
                    maker_first: bool = False, bid: Optional[float] = None, ask: Optional[float] = None,
                    max_slippage_pct: float = 1.0, max_retries: int = 3, retry_delay: float = 0.25,
                    guard_context: Optional[Dict[str, Any]] = None) -> Dict:
        """
        Enhanced: step size enforcement, slippage protection, dynamic sizing, multi-asset balance, partial fill retry, order throttling, logging, graceful degradation.
        """
        import math
        context = guard_context if isinstance(guard_context, dict) else {}
        context_runtime = context.get('runtime') if isinstance(context.get('runtime'), dict) else {}
        if context.get('preflight_authorized') is not True or not context_runtime:
            return {'error': 'live_order_authority_blocked:human_action_time_authority_context_required', 'result': None}
        route_guard = LiveRuntimeGuard(ROOT)
        route_allowed, route_reason = route_guard.can_place_live_order(
            context_runtime,
            realized_pnl_total=float(context.get('realized_pnl_total', 0.0) or 0.0),
            portfolio_heat=float(context.get('portfolio_heat', 0.0) or 0.0),
            open_positions=int(context.get('open_positions', 0) or 0),
        )
        if not route_allowed:
            return {'error': f'live_order_authority_blocked:{route_reason}', 'result': None}
        config = self.get_symbol_config(symbol)
        if not config:
            return {'error': f'Symbol {symbol} not in registry'}

        exchange = self.get_route_exchange(symbol, preferred_exchange=preferred_exchange)
        min_order = float(config.get('min_order', 0.0) or 0.0)
        max_order = float(config.get('max_order', 0.0) or 0.0)
        step_size = float(config.get('step_size', 0.0) or 0.0)
        # Fetch latest price for notional calculation
        ticker = self.get_ticker(symbol)
        price = ticker['last'] if ticker and 'last' in ticker else (limit_price or 1.0)
        bid = ticker['bid'] if ticker and 'bid' in ticker else bid
        ask = ticker['ask'] if ticker and 'ask' in ticker else ask
        # SPOT-ONLY PATCH: Use only spot balances for order sizing
        balances = self.get_balance()
        quote_assets = ['USD', 'USDT', 'ZUSD']
        available = max(float(balances.get(asset, 0.0) or 0.0) for asset in quote_assets)
        base_asset = symbol.split('/')[0] if '/' in symbol else symbol
        base_available = float(balances.get(base_asset, 0.0) or 0.0)
        # Calculate max affordable size (spot only)
        max_affordable = available / price if price > 0 else size
        working_size = min(size, max_affordable)
        if max_order > 0:
            working_size = min(working_size, max_order)
        # Step size enforcement
        if step_size > 0:
            working_size = math.floor(working_size / step_size) * step_size
        if working_size < min_order:
            if max_affordable >= min_order:
                working_size = math.floor(min_order / step_size) * step_size if step_size > 0 else min_order
            else:
                print(f"[ORDER-SKIP] {symbol} insufficient spot funds for min order: min={min_order} available={available}")
                return {'error': f'Insufficient spot funds for min order: {symbol} min={min_order} available={available}'}
        if abs(working_size - size) > 1e-8:
            print(f"[AUTO-ADJUST] {symbol} spot order size adjusted from {size} to {working_size} (min={min_order}, max={max_order}, available={available}, price={price}, step={step_size})")
        # Disable margin/futures logic in spot mode
        leverage = 1.0
        # Log spot mode
        print(f"[SPOT-ONLY MODE] Trading spot only. Margin/futures disabled. Available spot balance: {available}")

        # Slippage protection
        if limit_price is not None and price > 0:
            slippage = abs(limit_price - price) / price * 100.0
            if slippage > max_slippage_pct:
                print(f"[ORDER-SKIP] {symbol} slippage {slippage:.2f}% exceeds max {max_slippage_pct}% (limit={limit_price}, last={price})")
                return {'error': f'Slippage {slippage:.2f}% exceeds max {max_slippage_pct}%'}

        # Throttling (simple sleep, could be replaced with token bucket)
        import time
        time.sleep(0.1)

        # Continue with normal routing logic
        if exchange == 'alpaca':
            result = self._place_alpaca_order(symbol, side, working_size, limit_price)
            if result.get('error') and 'Insufficient' in str(result['error']):
                print(f"[ORDER-RETRY] Alpaca insufficient funds, retrying with reduced size.")
                working_size = max(working_size * 0.90, min_order)
                if working_size >= min_order:
                    return self._place_alpaca_order(symbol, side, working_size, limit_price)
            return result
        if exchange != 'kraken':
            print(f"[ORDER-ROUTE] {symbol} exchange {exchange} not implemented, skipping.")
            return {'error': f'Exchange {exchange} not implemented', 'result': None}

        last_error = 'unknown_order_error'
        side_lower = str(side or '').lower()
        partial_filled = 0.0
        for attempt in range(max_retries):
            # --- MAKER-FIRST PATH ---
            if maker_first and bid and ask and float(bid) > 0 and float(ask) > 0:
                maker_price = float(bid) if side_lower == 'buy' else float(ask)
                maker_result = self._place_kraken_order(config['pair'], side, working_size, maker_price, leverage, post_only=True)
                if not maker_result.get('error'):
                    maker_result['execution_mode'] = 'maker'
                    maker_result['maker_price'] = float(maker_price)
                    return maker_result
                maker_err = str(maker_result.get('error', ''))
                if 'Post order' not in maker_err and 'post' not in maker_err.lower():
                    last_error = maker_err

            # --- TAKER / LIMIT FALLBACK ---
            result = self._place_kraken_order(config['pair'], side, working_size, limit_price, leverage)
            if not result.get('error'):
                result['execution_mode'] = 'taker'
                return result

            err_text = str(result.get('error'))
            last_error = err_text

            # Market fallback for maximum fill probability when limit is also rejected.
            if limit_price is not None:
                market_result = self._place_kraken_order(config['pair'], side, working_size, None, leverage)
                if not market_result.get('error'):
                    market_result['execution_fallback'] = 'limit_to_market'
                    market_result['execution_mode'] = 'taker'
                    return market_result
                last_error = str(market_result.get('error'))

            # Shrink size on funds errors to salvage a smaller valid execution.
            if 'Insufficient funds' in err_text:
                working_size = max(working_size * 0.90, min_order)
                if working_size < min_order:
                    print(f"[AUTO-ADJUST] {symbol} order size dropped below min after shrink; aborting.")
                    return {'error': f'Order size below min after shrink: {symbol} min={min_order} available={available}'}

            # Partial fill retry (simulate, as most APIs return fill status async)
            if 'partial fill' in err_text.lower() and partial_filled < working_size:
                partial_filled += working_size * 0.5
                working_size = max(working_size * 0.5, min_order)
                print(f"[ORDER-RETRY] {symbol} partial fill, retrying with reduced size {working_size}")
                continue

            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        # Graceful degradation: fallback to Binance if enabled
        if 'binance' in config.get('fallbacks', []):
            print(f"[ORDER-FALLBACK] {symbol} routing to Binance fallback.")
            return self._place_binance_order_fallback(symbol, side, working_size, limit_price)

        print(f"[ORDER-FAIL] {symbol} placement failed after {max_retries} retries: {last_error}")
        return {'error': f'Order placement failed on {exchange} after {max_retries} retries: {last_error}', 'result': None}
        """
        Auto-adjusts order size to available balance and exchange minimums, retries with best effort, and logs adjustments instead of blocking.
        """
        config = self.get_symbol_config(symbol)
        if not config:
            return {'error': f'Symbol {symbol} not in registry'}

        exchange = self.get_route_exchange(symbol, preferred_exchange=preferred_exchange)
        min_order = float(config.get('min_order', 0.0) or 0.0)
        max_order = float(config.get('max_order', 0.0) or 0.0)
        # Fetch latest price for notional calculation
        ticker = self.get_ticker(symbol)
        price = ticker['last'] if ticker and 'last' in ticker else (limit_price or 1.0)
        # Check available balance for base/quote asset
        balances = self.get_balance()
        quote_asset = 'USD' if 'USD' in symbol else 'USDT'
        available = float(balances.get(quote_asset, 0.0) or 0.0)
        # Calculate max affordable size
        max_affordable = available / price if price > 0 else size
        working_size = min(size, max_affordable)
        if max_order > 0:
            working_size = min(working_size, max_order)
        if working_size < min_order:
            # Try to auto-adjust up to min_order if possible
            if max_affordable >= min_order:
                working_size = min_order
            else:
                return {'error': f'Insufficient funds for min order: {symbol} min={min_order} available={available}'}
        # Log adjustment if size changed
        if abs(working_size - size) > 1e-8:
            print(f"[AUTO-ADJUST] {symbol} order size adjusted from {size} to {working_size} (min={min_order}, max={max_order}, available={available}, price={price})")

        # Continue with normal routing logic
        if exchange == 'alpaca':
            return self._place_alpaca_order(symbol, side, working_size, limit_price)
        if exchange != 'kraken':
            return {'error': f'Exchange {exchange} not implemented', 'result': None}

        max_retries = 3
        retry_delay = 0.25
        last_error = 'unknown_order_error'
        side_lower = str(side or '').lower()

        for attempt in range(max_retries):
            # --- MAKER-FIRST PATH ---
            if maker_first and bid and ask and float(bid) > 0 and float(ask) > 0:
                maker_price = float(bid) if side_lower == 'buy' else float(ask)
                maker_result = self._place_kraken_order(config['pair'], side, working_size, maker_price, leverage, post_only=True)
                if not maker_result.get('error'):
                    maker_result['execution_mode'] = 'maker'
                    maker_result['maker_price'] = float(maker_price)
                    return maker_result
                maker_err = str(maker_result.get('error', ''))
                if 'Post order' not in maker_err and 'post' not in maker_err.lower():
                    last_error = maker_err

            # --- TAKER / LIMIT FALLBACK ---
            result = self._place_kraken_order(config['pair'], side, working_size, limit_price, leverage)
            if not result.get('error'):
                result['execution_mode'] = 'taker'
                return result

            err_text = str(result.get('error'))
            last_error = err_text

            # Market fallback for maximum fill probability when limit is also rejected.
            if limit_price is not None:
                market_result = self._place_kraken_order(config['pair'], side, working_size, None, leverage)
                if not market_result.get('error'):
                    market_result['execution_fallback'] = 'limit_to_market'
                    market_result['execution_mode'] = 'taker'
                    return market_result
                last_error = str(market_result.get('error'))

            # Shrink size on funds errors to salvage a smaller valid execution.
            if 'Insufficient funds' in err_text:
                working_size = max(working_size * 0.90, min_order)
                if working_size < min_order:
                    print(f"[AUTO-ADJUST] {symbol} order size dropped below min after shrink; aborting.")
                    return {'error': f'Order size below min after shrink: {symbol} min={min_order} available={available}'}

            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        return {'error': f'Order placement failed on {exchange} after {max_retries} retries: {last_error}', 'result': None}
        """Place order with maker-first post-only attempt, taker fallback, and graceful size backoff.
        
        maker_first=True: tries a post-only limit at bid (buy) or ask (sell) for maker fee.
        Falls back to taker (market/limit) automatically if post-only is rejected by Kraken.
        """
        config = self.get_symbol_config(symbol)
        
        if not config:
            return {'error': f'Symbol {symbol} not in registry'}
        
        exchange = self.get_route_exchange(symbol, preferred_exchange=preferred_exchange)
        if exchange == 'alpaca':
            return self._place_alpaca_order(symbol, side, size, limit_price)
        if exchange != 'kraken':
            return {'error': f'Exchange {exchange} not implemented', 'result': None}

        max_retries = 3
        retry_delay = 0.25
        working_size = float(size)
        last_error = 'unknown_order_error'
        side_lower = str(side or '').lower()

        for attempt in range(max_retries):
            # --- MAKER-FIRST PATH ---
            # Price at bid for buy (queue at best bid, wait for seller to come down),
            # price at ask for sell (queue at best ask, wait for buyer to come up).
            # This earns maker rebate (~0.16%) instead of paying taker fee (~0.26%).
            if maker_first and bid and ask and float(bid) > 0 and float(ask) > 0:
                if side_lower == 'buy':
                    maker_price = float(bid)
                else:
                    maker_price = float(ask)
                maker_result = self._place_kraken_order(config['pair'], side, working_size, maker_price, leverage, post_only=True)
                if not maker_result.get('error'):
                    maker_result['execution_mode'] = 'maker'
                    maker_result['maker_price'] = float(maker_price)
                    return maker_result
                # EOrder:Post order = would have crossed book; expected, fall through to taker
                maker_err = str(maker_result.get('error', ''))
                if 'Post order' not in maker_err and 'post' not in maker_err.lower():
                    # Unexpected error — log it but still fall through
                    last_error = maker_err

            # --- TAKER / LIMIT FALLBACK ---
            result = self._place_kraken_order(config['pair'], side, working_size, limit_price, leverage)
            if not result.get('error'):
                result['execution_mode'] = 'taker'
                return result

            err_text = str(result.get('error'))
            last_error = err_text

            # Market fallback for maximum fill probability when limit is also rejected.
            if limit_price is not None:
                market_result = self._place_kraken_order(config['pair'], side, working_size, None, leverage)
                if not market_result.get('error'):
                    market_result['execution_fallback'] = 'limit_to_market'
                    market_result['execution_mode'] = 'taker'
                    return market_result
                last_error = str(market_result.get('error'))

            # Shrink size on funds errors to salvage a smaller valid execution.
            if 'Insufficient funds' in err_text:
                working_size = max(working_size * 0.90, float(config.get('min_order', 0.0) or 0.0))

            if attempt < max_retries - 1:
                time.sleep(retry_delay)

        return {'error': f'Order placement failed on {exchange} after {max_retries} retries: {last_error}', 'result': None}

    def _place_alpaca_order(self, symbol: str, side: str, volume: float, price: Optional[float]) -> Dict:
        """Place order on Alpaca live trading API."""
        if not self._alpaca_is_configured():
            return {'error': 'Alpaca credentials not configured', 'result': None}

        payload: Dict[str, Any] = {
            'symbol': self._alpaca_symbol(symbol),
            'side': str(side or '').lower(),
            'qty': str(round(float(volume), 8)),
            'type': 'limit' if price else 'market',
            'time_in_force': 'gtc',
        }
        if price is not None:
            payload['limit_price'] = str(round(float(price), 8))

        try:
            response = self.alpaca_session.post(f"{self.alpaca_trading_base}/v2/orders", json=payload, timeout=20)
            response.raise_for_status()
            result = response.json()
            return {
                'txid': str(result.get('id', 'unknown')),
                'order_id': str(result.get('client_order_id', result.get('id', 'unknown'))),
                'pair': self._alpaca_symbol(symbol),
                'side': side,
                'volume': float(volume),
                'price': price,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': str(result.get('status', 'accepted')).upper(),
                'exchange': 'alpaca',
                'result': result,
            }
        except requests.HTTPError as exc:
            response = getattr(exc, 'response', None)
            detail = ''
            if response is not None:
                try:
                    payload = response.json()
                    detail = str(payload.get('message') or payload.get('code') or payload)
                except Exception:
                    detail = str(response.text or '').strip()
            return {'error': f'Alpaca order failed: {detail or exc}', 'result': None, 'exchange': 'alpaca'}
        except (requests.RequestException, ValueError, TypeError) as exc:
            return {'error': f'Alpaca order failed: {exc}', 'result': None, 'exchange': 'alpaca'}
    
    def _place_kraken_order(self, pair: str, side: str, volume: float, price: Optional[float], leverage: float = 1.0, post_only: bool = False) -> Dict:
        """Place order on Kraken. post_only=True uses oflags=post for maker (lower fee) execution."""
        try:
            endpoint = "/0/private/AddOrder"
            params = {
                'pair': pair,
                'type': side,
                'ordertype': 'limit' if price else 'market',
                'volume': str(volume)
            }

            if leverage and float(leverage) > 1.0:
                lev = max(2.0, min(5.0, float(leverage)))
                params['leverage'] = f"{int(round(lev))}:1"
            
            if price:
                params['price'] = str(price)

            # Maker post-only flag: prevents Kraken from matching as taker.
            # If it would cross the book, Kraken rejects with EOrder:Post order.
            if post_only and price:
                params['oflags'] = 'post'

            result = self._kraken_private_request(endpoint, params)
            
            if result.get('error'):
                return {'error': result['error'], 'result': None}
            
            txid = result.get('result', {}).get('txid', ['unknown'])[0]
            order_info = result.get('result', {}).get('order_id', 'unknown')
            
            return {
                'txid': txid,
                'order_id': order_info,
                'pair': pair,
                'side': side,
                'volume': volume,
                'price': price,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'PLACED',
                'result': result.get('result')
            }
        
        except Exception as e:
            return {'error': str(e), 'result': None}

    def cancel_order(self, txid: str, preferred_exchange: Optional[str] = None) -> Dict:
        exchange = str(preferred_exchange or 'kraken').strip().lower()
        if exchange == 'alpaca':
            if not self._alpaca_is_configured():
                return {'ok': False, 'error': 'Alpaca credentials not configured', 'exchange': 'alpaca'}
            try:
                response = self.alpaca_session.delete(
                    f"{self.alpaca_trading_base}/v2/orders/{str(txid)}",
                    timeout=20,
                )
                if response.status_code in (200, 204):
                    return {'ok': True, 'txid': str(txid), 'exchange': 'alpaca'}
                try:
                    payload = response.json()
                    detail = str(payload.get('message') or payload)
                except Exception:
                    detail = str(response.text or '').strip()
                return {'ok': False, 'error': detail or f'HTTP {response.status_code}', 'exchange': 'alpaca'}
            except Exception as exc:
                return {'ok': False, 'error': str(exc), 'exchange': 'alpaca'}

        try:
            result = self._kraken_private_request('/0/private/CancelOrder', {'txid': str(txid)})
            errors = result.get('error') or []
            if errors:
                return {'ok': False, 'error': ' | '.join(str(e) for e in errors), 'exchange': 'kraken'}
            return {
                'ok': True,
                'txid': str(txid),
                'exchange': 'kraken',
                'result': result.get('result', {}),
            }
        except Exception as exc:
            return {'ok': False, 'error': str(exc), 'exchange': 'kraken'}
    
    def _place_binance_order_fallback(self, symbol: str, side: str, volume: float, price: Optional[float]) -> Dict:
        """FALLBACK: Place order on Binance if Kraken fails (emergency liquidity)"""
        try:
            # Map Luma symbols to Binance format (BTC -> BTCUSDT, etc.)
            binance_symbol = f"{symbol}USDT" if symbol != "DOGE" else "DOGEUSDT"
            
            # Construct Binance market order
            order_type = 'LIMIT' if price else 'MARKET'
            order_side = 'BUY' if side == 'long' else 'SELL'
            
            endpoint = "https://api.binance.com/api/v3/order"
            headers = {'X-MBX-APIKEY': self.api_keys.get('BINANCE_API_KEY', '')}
            
            params = {
                'symbol': binance_symbol,
                'side': order_side,
                'type': order_type,
                'quantity': volume,
                'timestamp': int(time.time() * 1000)
            }
            
            if price and order_type == 'LIMIT':
                params['price'] = price
                params['timeInForce'] = 'GTC'
            
            response = self.session.post(endpoint, params=params, headers=headers, timeout=5)
            result = response.json()
            
            if 'orderId' in result:
                return {
                    'txid': str(result.get('orderId')),
                    'exchange': 'binance_fallback',
                    'symbol': symbol,
                    'side': side,
                    'volume': volume,
                    'price': price,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'status': 'PLACED'
                }
            else:
                return {'error': result.get('msg', 'Binance order failed')}
        
        except Exception as e:
            return {'error': f'Binance fallback error: {str(e)}'}

    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get current price for symbol. Debugs symbol, pair, and raw Kraken response if missing."""
        config = self.get_symbol_config(symbol)
        if not config:
            print(f"[TICKER-DEBUG] Symbol not in registry: {symbol}")
            return None
        try:
            print(f"[TICKER-DEBUG] Requesting ticker for symbol={symbol} pair={config['pair']}")
            response = self.session.get(
                "https://api.kraken.com/0/public/Ticker",
                params={'pair': config['pair']},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            if data.get('result'):
                result_map = data['result']
                ticker = next(iter(result_map.values()))
                return {
                    'symbol': symbol,
                    'pair': config['pair'],
                    'bid': float(ticker['b'][0]),
                    'ask': float(ticker['a'][0]),
                    'last': float(ticker['c'][0]),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            else:
                print(f"[TICKER-DEBUG] No result for symbol={symbol} pair={config['pair']} raw={data}")
        except Exception as e:
            print(f"[TICKER-DEBUG] Exception for symbol={symbol} pair={config['pair']}: {e}")
        return None
    
    def get_balance(self, asset: str = None) -> Dict:
        """Get balance for specific asset or all"""
        balances: Dict[str, Any] = {}
        try:
            result = self._kraken_private_request("/0/private/Balance", {})

            errors = result.get('error') or []
            if errors:
                err_text = ' '.join(str(e) for e in errors)
                # Retry once on transient private API failures.
                if ('Rate limit' in err_text) or ('Invalid nonce' in err_text):
                    time.sleep(0.5)
                    result = self._kraken_private_request("/0/private/Balance", {})
                    errors = result.get('error') or []
                if not errors:
                    balances.update(result.get('result', {}))
            else:
                balances.update(result.get('result', {}))

        except (requests.RequestException, ValueError, TypeError, KeyError):
            balances = {}

        if self.get_route_exchange('BTC') == 'alpaca':
            alpaca_balances = self._build_alpaca_balance_map()
            for key, value in alpaca_balances.items():
                if key in {'USD', 'ZUSD', 'USD.ALPACA', 'BUYING_POWER', 'EQUITY'}:
                    balances[key] = value
                else:
                    balances[key] = max(float(balances.get(key, 0.0) or 0.0), float(value or 0.0))

        if asset:
            return {asset: balances.get(asset, 0)}

        return balances

    def get_trade_balance(self, asset: str = 'ZUSD') -> Dict:
        """Get margin/equity values for futures-like sizing."""
        if self.get_route_exchange('BTC') == 'alpaca':
            account = self._alpaca_get_account()
            if account:
                try:
                    equity = float(account.get('equity', 0.0) or 0.0)
                except Exception:
                    equity = 0.0
                try:
                    buying_power = float(account.get('buying_power', account.get('cash', 0.0)) or 0.0)
                except Exception:
                    buying_power = 0.0
                try:
                    cash = float(account.get('cash', 0.0) or 0.0)
                except Exception:
                    cash = 0.0
                return {'eb': equity, 'mf': buying_power, 'tb': cash, 'exchange': 'alpaca'}

        try:
            result = self._kraken_private_request("/0/private/TradeBalance", {"asset": asset})

            errors = result.get('error') or []
            if errors:
                err_text = ' '.join(str(e) for e in errors)
                if ('Rate limit' in err_text) or ('Invalid nonce' in err_text):
                    time.sleep(0.5)
                    result = self._kraken_private_request("/0/private/TradeBalance", {"asset": asset})
                    errors = result.get('error') or []
                if errors:
                    return {}

            return result.get('result', {}) or {}
        except (requests.RequestException, ValueError, TypeError, KeyError):
            return {}




# === INIT: Cross-Exchange Capital Rolling & Arbitrage + RL Policy ===
print("\n[INIT] Loading components...")
signal_gate = EvolutionarySignalGate()
liquidity_guard = LiquidityGuard()
risk_kernel = RiskKernel()
router = UniversalExchangeRouter(api_keys)
runtime_guard = LiveRuntimeGuard(ROOT)

runtime_cfg = _validate_runtime_cfg(runtime_guard.load())
runtime_cfg = _force_live_mode(runtime_cfg)
print(f"[FORCE] Runtime Mode: {runtime_cfg['mode'].upper()}")
print(f"[FORCE] Live Orders Armed: {runtime_cfg['allow_live_orders']}")
print(f"[DEBUG-REGISTRY-ORCH] SYMBOL_REGISTRY count: {len(SYMBOL_REGISTRY)}")
print(f"[DEBUG-REGISTRY-ORCH] SYMBOL_REGISTRY keys: {list(SYMBOL_REGISTRY.keys())[:50]} ... (truncated)")
sys.stderr.flush()
sys.stdout.flush()
harmonic_connector = HarmonicSignalConnector(SYMBOL_REGISTRY, runtime_cfg=runtime_cfg)
audit_chain = AuditChain(AUDIT_CHAIN_FILE)
event_logger = StructuredEventLogger(OUT / 'execution_events.jsonl')
lock_file = EXECUTION_LOCK_FILE
shutdown_event = threading.Event()
PROCESS_INSTANCE_TOKEN = uuid.uuid4().hex


# RL Policy and Sector Rotation
rl_policy = RLPolicy()
sector_rotation = SectorRotation()

# === AUTO-DETECT AND WIRE ALL ENGINES FOR META ENGINE ===
import importlib
from bounded_infinity import MetaEngine

def discover_engines():
    engines: Dict[str, Any] = {}

    # Wire known in-memory engines only. Wildcard importing *engine.py modules is
    # unsafe here because several files are script-style and execute side effects
    # at import time (including process launches).
    base_engines = {
        'signal_gate': signal_gate,
        'liquidity_guard': liquidity_guard,
        'risk_kernel': risk_kernel,
        'rl_policy': rl_policy,
        'sector_rotation': sector_rotation,
        'harmonic_connector': harmonic_connector,
    }
    for engine_name, engine_obj in base_engines.items():
        if engine_obj is not None:
            engines[engine_name] = engine_obj

    # Optional dynamic imports are explicit-only and disabled by default.
    if not bool(runtime_cfg.get('meta_engine_enable_dynamic_imports', False)):
        return engines

    dynamic_modules = runtime_cfg.get('meta_engine_modules', [])
    if not isinstance(dynamic_modules, list):
        return engines

    for module_name_raw in dynamic_modules:
        module_name = str(module_name_raw or '').strip()
        if not module_name or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', module_name):
            continue
        try:
            mod = importlib.import_module(module_name)
        except Exception:
            continue
        for attr in dir(mod):
            if not attr.lower().endswith('engine'):
                continue
            candidate = getattr(mod, attr, None)
            if candidate is None:
                continue
            if inspect.isclass(candidate):
                try:
                    candidate = candidate()
                except Exception:
                    continue
            engines[f'{module_name}.{attr.lower()}'] = candidate

    return engines

# Instantiate MetaEngine with all discovered engines
all_engines = discover_engines()
meta_engine = MetaEngine(all_engines)

# --- Cross-Exchange Capital Rolling Logic ---
def cross_exchange_capital_rolling(router, runtime_cfg):
    try:
        balances = {
            'kraken': router.get_balance(),
            'alpaca': router._build_alpaca_balance_map() if router._alpaca_is_configured() else {},
        }
        threshold = float(runtime_cfg.get('cross_exchange_roll_threshold_usd', 100.0))
        best_multi = get_rolling_capital_best_multi()
        best_symbol, best_family, best_metrics = _normalize_best_multi_payload(best_multi)
        best_exchange = None
        if best_symbol:
            best_exchange = router.get_route_exchange(best_symbol)
        for exch, bal in balances.items():
            usd = float(bal.get('USD', 0.0) or bal.get('ZUSD', 0.0) or 0.0)
            if exch != best_exchange and usd > threshold and best_exchange:
                intent = {
                    'intent_id': f'roll-{exch}-to-{best_exchange}-{int(time.time())}',
                    'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                    'from_exchange': exch,
                    'to_exchange': best_exchange,
                    'amount_usd': usd,
                    'reason': 'cross_exchange_roll',
                    'status': 'REQUESTED',
                }
                print(f"[CROSS-EXCHANGE] Rolling ${usd:.2f} from {exch} to {best_exchange} (best edge: {best_symbol} {best_family})")
                _append_payout_intent(intent)
    except Exception as e:
        print(f"[CROSS-EXCHANGE] Error in capital rolling: {e}")

cross_exchange_capital_rolling(router, runtime_cfg)

# --- RL Policy Integration Example (call in main loop or trade decision logic) ---
# Example usage:
#   action = rl_policy.select_action(symbol, family, sharpe, win_rate, drawdown, regime)
#   risk_fraction, sizing_multiplier = action
#   ... use these for position sizing and risk ...
#   ... after trade outcome ...
#   rl_policy.update(symbol, family, sharpe, win_rate, drawdown, regime, action, reward)

def graceful_shutdown(signum=None, frame=None):
    """Clean shutdown: flush audit chain + lock file on SIGTERM only."""
    print("\n\n[SHUTDOWN] Graceful shutdown initiated...")
    shutdown_event.set()
    time.sleep(0.5)
    _release_execution_lock()
    print("[SHUTDOWN] Lock file released | Audit chain flushed | Process safe to exit")
    sys.exit(0)

# Ignore SIGINT (Ctrl+C from parent console group on Windows) — only SIGTERM triggers clean shutdown
signal.signal(signal.SIGINT, signal.SIG_IGN)
signal.signal(signal.SIGTERM, graceful_shutdown)


def _acquire_execution_lock() -> bool:
    """Prevent concurrent execution runs."""
    try:
        existing = _read_execution_lock_metadata()
        if bool(existing.get('file_exists', False)):
            locked_pid = existing.get('owner_pid', None)
            locked_token = str(existing.get('owner_token', '') or '')
            lock_is_stale = (locked_pid is None) or (not bool(existing.get('owner_alive', False)))

            if lock_is_stale:
                try:
                    lock_file.unlink()
                except Exception:
                    return False
            else:
                if int(locked_pid) == int(os.getpid()) and locked_token == PROCESS_INSTANCE_TOKEN:
                    return True
                return False

        payload = (
            f"owner_pid={os.getpid()}\n"
            f"owner_token={PROCESS_INSTANCE_TOKEN}\n"
            f"created_utc={datetime.now(timezone.utc).isoformat()}\n"
            f"script=execution_orchestrator.py\n"
        )
        lock_file.write_text(payload, encoding='utf-8')
        return True
    except Exception:
        return False


def _release_execution_lock():
    """Release execution lock on shutdown."""
    try:
        if lock_file.exists():
            existing = _read_execution_lock_metadata()
            owner_pid = existing.get('owner_pid', None)
            owner_token = str(existing.get('owner_token', '') or '')
            owner_pid_int = None
            try:
                owner_pid_int = int(owner_pid)
            except Exception:
                owner_pid_int = None
            if owner_pid_int is not None and owner_pid_int == int(os.getpid()) and owner_token == PROCESS_INSTANCE_TOKEN:
                lock_file.unlink()
    except Exception:
        pass


if not _acquire_execution_lock():
    existing = _read_execution_lock_metadata()
    owner_pid = existing.get('owner_pid', None)
    owner_alive = bool(existing.get('owner_alive', False))
    age_seconds = existing.get('age_seconds', None)
    age_text = f"{float(age_seconds):.1f}s" if age_seconds is not None else "?"
    _append_startup_fatal(
        'execution_lock_active',
        context={
            'owner_pid': owner_pid,
            'owner_alive': bool(owner_alive),
            'age_seconds': age_seconds,
        },
    )
    print(f"[ERROR] Active execution lock held (owner_pid={owner_pid}, alive={owner_alive}, age={age_text}). Exiting.")
    sys.exit(1)


def _resolve_starting_capital_usd(runtime_cfg: Dict, router: UniversalExchangeRouter) -> float:
    configured = float(runtime_cfg.get('initial_capital_usd', 0.0) or 0.0)
    if configured > 0:
        return configured

    usd_balance = 0.0
    try:
        balances = router.get_balance() or {}
        for key in ['ZUSD', 'USD', 'USDT', 'USDC', 'ZUSD.F', 'USD.F']:
            if key in balances:
                try:
                    value = float(balances.get(key, 0) or 0)
                    if value > usd_balance:
                        usd_balance = value
                except Exception:
                    continue
    except Exception:
        pass

    if usd_balance > 0:
        return usd_balance

    fallback = _sanitize_fallback_buying_power_usd(runtime_cfg.get('fallback_buying_power_usd', 0.0))
    if fallback > 0:
        return fallback
    return 219.0


def _sanitize_fallback_buying_power_usd(raw_value: Any) -> float:
    """Normalize operator fallback buying power to a finite, bounded non-negative float."""
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return 0.0
    if not np.isfinite(value):
        return 0.0
    if value <= 0:
        return 0.0
    return min(value, MAX_FALLBACK_BUYING_POWER_USD)


def _reconcile_exchange_state(router: UniversalExchangeRouter, trade_log_path: Path, runtime_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Startup reconciliation: fetch live exchange state and compare with trade log."""
    runtime_cfg = dict(runtime_cfg or {})
    auto_cancel_orphans = bool(runtime_cfg.get('reconciliation_auto_cancel_orphans', True))
    reconciliation_report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "orphaned_open_orders": [],
        "orphan_cancellations": [],
        "balance_drift": {},
        "warnings": [],
    }
    
    try:
        # Fetch all open orders from Kraken
        open_orders_result = router._kraken_private_request("/0/private/OpenOrders", {})
        open_orders_live = open_orders_result.get('result', {}).get('open', {})
        
        # Load trade log for cross-check
        trade_log_data = []
        if trade_log_path.exists():
            try:
                with open(trade_log_path, 'r') as f:
                    trade_log_data = json.load(f)
            except Exception as e:
                reconciliation_report["warnings"].append(f"trade_log parse error: {str(e)}")
        
        logged_txids = set(str(t.get('txid', '')) for t in trade_log_data)
        
        # Identify orphaned orders (live on exchange but not in log)
        for txid, order_info in open_orders_live.items():
            if txid not in logged_txids:
                reconciliation_report["orphaned_open_orders"].append({
                    "txid": txid,
                    "pair": order_info.get('info', {}).get('pair', 'unknown'),
                    "type": order_info.get('info', {}).get('type', 'unknown'),
                    "volume": order_info.get('info', {}).get('vol', 0),
                })
                reconciliation_report["warnings"].append(f"Orphaned order found: {txid}")

                if auto_cancel_orphans:
                    cancel_out = router.cancel_order(txid, preferred_exchange='kraken')
                    reconciliation_report["orphan_cancellations"].append({
                        "txid": txid,
                        "ok": bool(cancel_out.get('ok', False)),
                        "exchange": str(cancel_out.get('exchange', 'kraken')),
                        "error": str(cancel_out.get('error', ''))[:240],
                    })
                    if bool(cancel_out.get('ok', False)):
                        reconciliation_report["warnings"].append(f"Auto-cancelled orphaned order: {txid}")
                    else:
                        reconciliation_report["warnings"].append(
                            f"Failed to auto-cancel orphaned order {txid}: {str(cancel_out.get('error', 'unknown'))[:160]}"
                        )
        
        # Check balance consistency
        balances_live = router.get_balance() or {}
        reconciliation_report["balance_drift"]["live_balances"] = {k: float(v or 0) for k, v in balances_live.items()}
        
        if reconciliation_report["warnings"]:
            print(f"  ⚠ Reconciliation found {len(reconciliation_report['warnings'])} issue(s)")
            for w in reconciliation_report["warnings"]:
                print(f"    - {w}")
    except Exception as e:
        reconciliation_report["warnings"].append(f"reconciliation failed: {str(e)}")
    
    _atomic_write_json(OUT / 'reconciliation_report.json', reconciliation_report)
    return reconciliation_report


def _persist_operational_health(
    event_logger: StructuredEventLogger,
    portfolio: 'PortfolioBrain',
    loop_count: int,
    rolling_pnl_pct: deque,
    rolling_order_outcomes: deque,
    runtime_cfg: Dict[str, Any],
    runway_start_ts: float,
    realized_pnl_samples: deque,
    entry_timestamps: deque,
    shadow_snapshot: Optional[Dict[str, Any]] = None,
) -> None:
    """Emit operational health metrics to health_metrics.json every iteration."""
    rolling_series = list(rolling_pnl_pct)
    rolling_sharpe = _rolling_sharpe_from_pnl_pct(rolling_series)
    # PATCH: Never fallback to trade log for Sharpe—always use live rolling data only.
    fail_rate = _failure_rate(list(rolling_order_outcomes))
    now_ts = time.time()
    runway_metrics = _compute_runway_metrics(
        runtime_cfg,
        float(runway_start_ts),
        float(now_ts),
        float(portfolio.current_equity),
        list(realized_pnl_samples),
        list(entry_timestamps),
    )
    
    health = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "loop": loop_count,
        "runtime_uptime_minutes": round(loop_count * float(runtime_cfg.get('loop_seconds', 1.0) or 1.0) / 60.0, 2),
        "portfolio_equity_usd": round(portfolio.current_equity, 2),
        "portfolio_pnl_usd": round(float(getattr(portfolio, 'realized_pnl_total', 0.0)), 2),
        "portfolio_pnl_pct": round(((float(getattr(portfolio, 'realized_pnl_total', 0.0)) / max(float(getattr(portfolio, 'initial_capital', 0.0)), 1e-9)) * 100.0), 2),
        "rolling_sharpe": round(rolling_sharpe, 3),
        "win_rate_pct": round(portfolio.win_rate() if portfolio.total_trades >= 1 else 0.0, 2),
        "order_success_rate_pct": round((1.0 - fail_rate) * 100.0, 2),
        "total_trades": portfolio.total_trades,
        "open_positions": len(portfolio.get_open_positions()),
        **runway_metrics,
        **event_logger.get_health_snapshot(),
    }
    if isinstance(shadow_snapshot, dict) and shadow_snapshot:
        health['shadow_intelligence'] = dict(shadow_snapshot)
    _atomic_write_json(OUT / 'health_metrics.json', health)

    kpi_summary = {
        'timestamp_utc': health['timestamp_utc'],
        'loop': int(loop_count),
        'equity_usd': float(round(portfolio.current_equity, 4)),
        'realized_pnl_usd': float(round(float(getattr(portfolio, 'realized_pnl_total', 0.0)), 4)),
        'win_rate_pct': float(health.get('win_rate_pct', 0.0) or 0.0),
        'order_success_rate_pct': float(health.get('order_success_rate_pct', 0.0) or 0.0),
        'total_trades': int(portfolio.total_trades),
        'open_positions': int(len(portfolio.get_open_positions())),
        'rolling_sharpe': float(health.get('rolling_sharpe', 0.0) or 0.0),
        'drawdown_pct': float(abs(float(getattr(portfolio, 'max_drawdown', 0.0) or 0.0)) * 100.0),
        'selection_min_edge_bps': float(runtime_cfg.get('selection_min_edge_bps', 0.0) or 0.0),
        'min_expected_net_edge_bps': float(runtime_cfg.get('min_expected_net_edge_bps', 0.0) or 0.0),
        'min_gate_score_for_entry': float(runtime_cfg.get('min_gate_score_for_entry', 0.0) or 0.0),
        'edge_fee_coverage_multiplier': float(runtime_cfg.get('edge_fee_coverage_multiplier', 0.0) or 0.0),
    }
    if isinstance(shadow_snapshot, dict) and shadow_snapshot:
        kpi_summary['shadow_reason'] = str(shadow_snapshot.get('reason', '') or '')
        kpi_summary['selection_mode'] = str(shadow_snapshot.get('selection_mode', '') or '')
    _atomic_write_json(OUT / 'kpi_summary.json', kpi_summary, indent=2)


def _persist_runtime_tuner_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(updates, dict) or not updates:
        return {}
    try:
        payload: Dict[str, Any] = {}
        if RUNTIME_FILE.exists():
            loaded = json.loads(RUNTIME_FILE.read_text(encoding='utf-8'))
            if isinstance(loaded, dict):
                payload = dict(loaded)
        changed: Dict[str, Any] = {}
        for key, value in updates.items():
            if payload.get(key) != value:
                changed[key] = value
        if not changed:
            return {}
        payload.update(changed)
        _atomic_write_json(RUNTIME_FILE, payload, indent=2)
        return changed
    except Exception:
        return {}


def _maybe_run_adaptive_selection_tuner(
    runtime_cfg: Dict[str, Any],
    trade_log: List[Dict[str, Any]],
    loop_count: int,
    last_successful_order_ts: float,
    event_logger: StructuredEventLogger,
) -> Dict[str, Any]:
    if not bool(runtime_cfg.get('adaptive_selection_tuner_enabled', True)):
        return runtime_cfg
    interval_loops = int(runtime_cfg.get('adaptive_selection_tuner_interval_loops', 30) or 30)
    if interval_loops <= 0 or (loop_count % interval_loops) != 0:
        return runtime_cfg
    if _load_runtime_profile_lock_overrides():
        return runtime_cfg

    edge_bps = float(runtime_cfg.get('selection_min_edge_bps', 6.0) or 6.0)
    gate_score = float(runtime_cfg.get('min_gate_score_for_entry', 0.90) or 0.90)
    step_edge = float(runtime_cfg.get('adaptive_selection_tuner_step_edge_bps', 0.5) or 0.5)
    step_gate = float(runtime_cfg.get('adaptive_selection_tuner_step_gate_score', 0.01) or 0.01)
    min_edge = float(runtime_cfg.get('adaptive_selection_tuner_min_edge_bps', 3.0) or 3.0)
    max_edge = float(runtime_cfg.get('adaptive_selection_tuner_max_edge_bps', 24.0) or 24.0)
    min_gate = float(runtime_cfg.get('adaptive_selection_tuner_min_gate_score', 0.55) or 0.55)
    max_gate = float(runtime_cfg.get('adaptive_selection_tuner_max_gate_score', 0.98) or 0.98)
    starvation_sec = float(runtime_cfg.get('adaptive_selection_tuner_starvation_sec', 60.0) or 60.0)
    recent_closed_n = int(runtime_cfg.get('adaptive_selection_tuner_recent_closed', 10) or 10)
    min_win_rate_pct = float(runtime_cfg.get('adaptive_selection_tuner_min_win_rate_pct', 35.0) or 35.0)
    min_avg_net = float(runtime_cfg.get('adaptive_selection_tuner_min_avg_net_pnl_usd', 0.0) or 0.0)

    now_ts = time.time()
    seconds_since_fill = max(0.0, float(now_ts - last_successful_order_ts))
    new_edge = edge_bps
    new_gate = gate_score
    reason_code = None

    # Sharpe-aware tuning: if rolling_sharpe is present in runtime_cfg, use it to adjust risk/entry
    rolling_sharpe = runtime_cfg.get('rolling_sharpe', None)
    if rolling_sharpe is not None:
        try:
            rolling_sharpe = float(rolling_sharpe)
            if rolling_sharpe < -1.0:
                # Deep negative Sharpe: force very strict entry, recovery mode
                new_edge = min(max_edge, 22.0)
                new_gate = min(max_gate, 0.80)
                reason_code = 'sharpe_recovery_mode'
            elif rolling_sharpe < 0.0:
                # Negative Sharpe: tighten entry
                new_edge = min(max_edge, edge_bps + 2.0)
                new_gate = min(max_gate, gate_score + 0.04)
                reason_code = 'sharpe_tighten'
            elif rolling_sharpe > 1.5:
                # Strong Sharpe: relax entry
                new_edge = max(min_edge, edge_bps - 1.0)
                new_gate = max(min_gate, gate_score - 0.03)
                reason_code = 'sharpe_relax'
        except Exception:
            pass

    if seconds_since_fill >= starvation_sec:
        new_edge = max(min_edge, new_edge - step_edge)
        new_gate = max(min_gate, new_gate - step_gate)
        reason_code = reason_code or 'starvation_relax'

    closed_rows: List[Dict[str, Any]] = []
    for row in reversed(trade_log):
        if str(row.get('status', '')).upper() != 'CLOSED':
            continue
        closed_rows.append(row)
        if len(closed_rows) >= recent_closed_n:
            break

    if len(closed_rows) >= max(3, int(recent_closed_n * 0.6)):
        net_samples = [float(r.get('net_pnl', 0.0) or 0.0) for r in closed_rows]
        avg_net = sum(net_samples) / max(1, len(net_samples))
        win_rate_pct = (sum(1 for v in net_samples if v > 0.0) / max(1, len(net_samples))) * 100.0
        if (avg_net < min_avg_net) or (win_rate_pct < min_win_rate_pct):
            new_edge = min(max_edge, new_edge + step_edge)
            new_gate = min(max_gate, new_gate + step_gate)
            reason_code = reason_code or 'underperform_tighten'
        elif (avg_net > min_avg_net) and (win_rate_pct >= (min_win_rate_pct + 8.0)):
            new_edge = max(min_edge, new_edge - step_edge)
            new_gate = max(min_gate, new_gate - step_gate)
            reason_code = reason_code or 'healthy_relax'

    updates = {
        'selection_min_edge_bps': round(float(new_edge), 4),
        'min_gate_score_for_entry': round(float(new_gate), 6),
    }
    changed = _persist_runtime_tuner_updates(updates)
    if not changed:
        return runtime_cfg

    runtime_cfg.update(changed)
    event_logger.emit(
        'adaptive_selection_tuner_applied',
        loop_count,
        reason_code=str(reason_code or 'periodic_tune'),
        context={
            'changed': dict(changed),
            'seconds_since_last_fill': float(round(seconds_since_fill, 3)),
            'interval_loops': int(interval_loops),
            'rolling_sharpe': rolling_sharpe,
        },
    )
    if rolling_sharpe is not None and rolling_sharpe < -1.0:
        print(f"  ⚠ WARNING: Sharpe ratio is deeply negative ({rolling_sharpe:.2f}). Entering recovery mode.")
    print(
        f"  ⚙ Selection tuner: edge={float(runtime_cfg.get('selection_min_edge_bps', 0.0)):.2f}bps "
        f"gate={float(runtime_cfg.get('min_gate_score_for_entry', 0.0)):.3f} "
        f"reason={str(reason_code or 'periodic_tune')}"
    )
    return runtime_cfg


def _run_x1000_control_plane(runtime_cfg: Dict[str, Any], loop_count: int) -> Dict[str, Any]:
    if not X1000_CONTROL_PLANE_FILE.exists():
        return {
            'ok': False,
            'status': 'missing_script',
            'reason': f'{X1000_CONTROL_PLANE_FILE} not found',
            'loop': loop_count,
        }

    cmd = [sys.executable, str(X1000_CONTROL_PLANE_FILE), '--passes', str(int(runtime_cfg.get('x1000_passes', 2) or 2))]
    if bool(runtime_cfg.get('x1000_auto_apply', False)):
        cmd.append('--apply')

    timeout_sec = int(runtime_cfg.get('x1000_timeout_sec', 120) or 120)
    started = time.time()
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        elapsed_ms = (time.time() - started) * 1000.0
        stdout_tail = (completed.stdout or '').strip()[-1200:]
        stderr_tail = (completed.stderr or '').strip()[-1200:]
        return {
            'ok': completed.returncode == 0,
            'status': 'ok' if completed.returncode == 0 else 'failed',
            'returncode': int(completed.returncode),
            'elapsed_ms': float(round(elapsed_ms, 2)),
            'stdout_tail': stdout_tail,
            'stderr_tail': stderr_tail,
            'loop': loop_count,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = (time.time() - started) * 1000.0
        return {
            'ok': False,
            'status': 'timeout',
            'reason': f'x1000 control-plane timeout after {timeout_sec}s',
            'elapsed_ms': float(round(elapsed_ms, 2)),
            'stdout_tail': str(exc.stdout or '')[-1200:],
            'stderr_tail': str(exc.stderr or '')[-1200:],
            'loop': loop_count,
        }
    except Exception as exc:
        elapsed_ms = (time.time() - started) * 1000.0
        return {
            'ok': False,
            'status': 'exception',
            'reason': str(exc),
            'elapsed_ms': float(round(elapsed_ms, 2)),
            'loop': loop_count,
        }


initial_capital_usd = _resolve_starting_capital_usd(runtime_cfg, router)
portfolio = PortfolioBrain(initial_capital=initial_capital_usd)
if hasattr(meta_engine, 'engines') and isinstance(meta_engine.engines, dict):
    meta_engine.engines['portfolio_brain'] = portfolio

print("✓ Signal Gate (Monte Carlo)")
print("✓ Portfolio Brain (P&L Tracking)")
print("✓ Liquidity Guard (6-Factor)")
print("✓ Risk Kernel (10-Layer)")
print("✓ Exchange Router (Universal)")
print("✓ Harmonic Signal Connector (Live Suite)")
print("✓ Runtime Guard (Institutional)")
print("✓ Audit Chain (Tamper-Evident)")
print("✓ Structured Event Logger (JSON Streaming)")
print("✓ Graceful Shutdown Handlers (SIGINT/SIGTERM)")
print("✓ Execution Lock & State Reconciliation")

print("\n[INIT] Performing startup reconciliation...")
reconciliation = _reconcile_exchange_state(router, OUT / 'trade_log.json', runtime_cfg=runtime_cfg)
if not reconciliation.get("warnings"):
    print("  ✓ Exchange state clean (no orphaned orders)")

# Trade log and pyramid tracking
trade_log: List[Dict] = []
trade_log_path = OUT / 'trade_log.json'
if trade_log_path.exists():
    try:
        loaded_trade_log = json.loads(trade_log_path.read_text(encoding='utf-8'))
        if isinstance(loaded_trade_log, list):
            trade_log = [row for row in loaded_trade_log if isinstance(row, dict)]
            if len(trade_log) > 0:
                print(f"  ↺ Restored trade history: {len(trade_log)} rows")
    except Exception as e:
        print(f"  ⚠ Could not restore historical trade_log.json ({str(e)[:120]})")
pyramid_level = 1
consecutive_losses = 0
consecutive_wins = 0
consecutive_order_failures = 0
last_positive_usd_balance = 0.0
last_balance_snapshot: Dict = {}
last_balance_fetch_ts = 0.0
balance_poll_interval_sec = 12.0
last_trade_balance_snapshot: Dict = {}
last_trade_balance_fetch_ts = 0.0
trade_balance_poll_interval_sec = 20.0
last_collateral_convert_ts = 0.0
rolling_pnl_pct = deque(maxlen=60)
rolling_order_outcomes = deque(maxlen=120)  # 1=success, 0=failure
active_profile = "micro"
last_profile_switch_loop = 0
futures_leverage_supported = True
symbol_cooldown_until: Dict[str, float] = {}
symbol_entry_history: Dict[str, List[float]] = {}
entry_timestamps = deque(maxlen=360)
realized_pnl_samples = deque(maxlen=720)
realized_pnl_peak = 0.0
insufficient_funds_size_scale = 1.0
shadow_intelligence = ShadowIntelligence()
shadow_snapshot: Dict[str, Any] = {}

if trade_log:
    closed_samples = 0
    for row in trade_log[-240:]:
        if str(row.get('status', '')).upper() != 'CLOSED':
            continue
        try:
            rolling_pnl_pct.append(float(row.get('net_pnl_pct', row.get('pnl_pct', 0.0)) or 0.0))
            closed_samples += 1
        except Exception:
            continue
    if closed_samples > 0:
        print(f"  ↺ Seeded rolling P&L samples from history: {closed_samples}")

# ============================================================================
# FEE TRACKING & RESERVE CALCULATION
# ============================================================================
KRAKEN_TAKER_FEE_PCT = 0.0026  # 0.26% taker fee per side (entry + exit = 0.52% round-trip)
KRAKEN_ENTRY_FEE_PCT = KRAKEN_TAKER_FEE_PCT
KRAKEN_EXIT_FEE_PCT = KRAKEN_TAKER_FEE_PCT
KRAKEN_ROUND_TRIP_FEE_PCT = KRAKEN_ENTRY_FEE_PCT + KRAKEN_EXIT_FEE_PCT
total_fees_paid_usd = 0.0  # Cumulative taker fees paid this session
total_fees_reserved_usd = 0.0  # Exit-side fees reserved (expected) but not yet charged
fee_tracking_by_symbol: Dict[str, Dict[str, float]] = {}  # symbol -> {entry_fees, exit_fees, count}
runway_start_ts = time.time()
realized_pnl_samples.append({'ts': runway_start_ts, 'pnl': 0.0})
last_x1000_trigger_loop = 0
adaptive_min_expected_edge_bps = float(runtime_cfg.get('min_expected_net_edge_bps', 65.0) or 65.0)
adaptive_gate_last_update_ts = time.time()
last_successful_order_ts = time.time()
adaptive_last_seen_closed_count = len([row for row in trade_log if str(row.get('status', '')).upper() == 'CLOSED'])

PROFILE_PRESETS = {
    "micro": {
        "loop_seconds": 0.5,
        "base_risk_fraction": 0.95,
        "max_position_usd": 10.0,
        "reserve_usd": 0.20,
        "max_open_positions": 4,
        "gate_override_min_confidence": 0.55,
        "gate_override_min_edge_bps": 8.0,
    },
    "safe": {
        "loop_seconds": 2.0,
        "base_risk_fraction": 0.12,
        "max_position_usd": 40.0,
        "reserve_usd": 25.0,
        "max_open_positions": 6,
        "gate_override_min_confidence": 0.72,
        "gate_override_min_edge_bps": 16.0,
    },
    "balanced": {
        "loop_seconds": 1.0,
        "base_risk_fraction": 0.22,
        "max_position_usd": 90.0,
        "reserve_usd": 15.0,
        "max_open_positions": 10,
        "gate_override_min_confidence": 0.64,
        "gate_override_min_edge_bps": 12.0,
    },
    "aggressive": {
        "loop_seconds": 0.75,
        "base_risk_fraction": 0.35,
        "max_position_usd": 150.0,
        "reserve_usd": 8.0,
        "max_open_positions": 15,
        "gate_override_min_confidence": 0.58,
        "gate_override_min_edge_bps": 9.0,
    },
    "recovery": {
        "loop_seconds": 2.5,
        "base_risk_fraction": 0.06,
        "max_position_usd": 8.0,
        "reserve_usd": 30.0,
        "max_open_positions": 2,
        "gate_override_min_confidence": 0.80,
        "gate_override_min_edge_bps": 22.0,
    },
}

ASSET_KEY_TO_SYMBOL = {
    'BTC': 'BTC',
    'XXBT': 'BTC',
    'XBT': 'BTC',
    'ETH': 'ETH',
    'XETH': 'ETH',
    'SOL': 'SOL',
    'XSOL': 'SOL',
    'ADA': 'ADA',
    'XADA': 'ADA',
    'XRP': 'XRP',
    'XXRP': 'XRP',
    'DOGE': 'DOGE',
    'XDG': 'DOGE',
    'XXDG': 'DOGE',
    'DOT': 'DOT',
    'LINK': 'LINK',
    'MATIC': 'MATIC',
    'LTC': 'LTC',
    'XLTC': 'LTC',
}


def _infer_symbol_from_asset_key(asset_key: str) -> Optional[str]:
    key = str(asset_key or '').strip().upper().split('.', 1)[0]
    if not key:
        return None

    if 'USD' in key or key in ('USDT', 'USDC', 'ZUSD', 'USD'):
        return None

    if key in ASSET_KEY_TO_SYMBOL:
        return ASSET_KEY_TO_SYMBOL[key]
    if key in SYMBOL_REGISTRY:
        return key

    for prefix in ('X', 'Z'):
        if key.startswith(prefix) and key[1:] in SYMBOL_REGISTRY:
            return key[1:]
    for prefix in ('XX', 'ZZ'):
        if key.startswith(prefix) and key[2:] in SYMBOL_REGISTRY:
            return key[2:]

    return None


def _resolve_usd_buckets_from_balances(balances: Dict[str, Any]) -> Dict[str, Any]:
    usd_candidates = ['ZUSD', 'USD', 'USDT', 'USDC', 'ZUSD.F', 'USD.F']
    usd_buckets: Dict[str, float] = {}
    max_usd = 0.0

    for k in usd_candidates:
        if k in balances:
            try:
                value = float(balances.get(k, 0) or 0)
                usd_buckets[k] = value
                if value > max_usd:
                    max_usd = value
            except Exception:
                continue

    for k, raw_v in balances.items():
        key = str(k).upper()
        if ('USD' in key or key.endswith('ZUSD')) and 'HOLD' not in key:
            try:
                value = float(raw_v or 0)
            except Exception:
                continue
            if key not in usd_buckets:
                usd_buckets[key] = value
            if value > max_usd:
                max_usd = value

    return {
        'max_usd': float(max_usd),
        'usd_buckets': usd_buckets,
    }


def _build_core_crypto_balance_snapshot(router: UniversalExchangeRouter, balances: Dict[str, Any]) -> Dict[str, Any]:
    core_symbols = ['BTC', 'ETH', 'SOL', 'ADA', 'XRP', 'DOGE']
    symbol_qty: Dict[str, float] = {symbol: 0.0 for symbol in core_symbols}
    raw_asset_rows: List[Dict[str, Any]] = []

    for asset_key, raw_qty in (balances or {}).items():
        try:
            qty = float(raw_qty or 0.0)
        except Exception:
            continue
        if qty <= 0:
            continue

        inferred = _infer_symbol_from_asset_key(str(asset_key))
        if inferred in symbol_qty:
            symbol_qty[inferred] += qty

        raw_asset_rows.append(
            {
                'asset_key': str(asset_key),
                'qty': float(qty),
                'inferred_symbol': inferred,
            }
        )

    core_assets: List[Dict[str, Any]] = []
    priced_total_usd = 0.0
    unpriced_symbols: List[str] = []

    for symbol in core_symbols:
        qty = float(symbol_qty.get(symbol, 0.0) or 0.0)
        price = None
        est_usd = 0.0

        if qty > 0:
            ticker = router.get_ticker(symbol)
            if ticker:
                try:
                    price = float(ticker.get('last', 0.0) or 0.0)
                except Exception:
                    price = None

            if price and price > 0:
                est_usd = qty * price
                priced_total_usd += est_usd
            else:
                unpriced_symbols.append(symbol)

        core_assets.append(
            {
                'symbol': symbol,
                'qty': float(qty),
                'last': None if price is None else float(price),
                'est_usd': float(est_usd),
                'has_price': bool(price is not None and price > 0),
            }
        )

    return {
        'core_symbols': core_symbols,
        'core_assets': core_assets,
        'core_crypto_est_usd': float(priced_total_usd),
        'unpriced_symbols': unpriced_symbols,
        'raw_assets_positive_count': int(len(raw_asset_rows)),
        'raw_assets': raw_asset_rows,
    }


def _rolling_sharpe_from_pnl_pct(pnl_pct_values: List[float]) -> float:
    if len(pnl_pct_values) < 2:
        return 0.0
    arr = np.array(pnl_pct_values, dtype=float) / 100.0
    std = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    mean_ret = float(arr.mean()) if len(arr) else 0.0
    if std <= 1e-9:
        if abs(mean_ret) <= 1e-9:
            return 0.0
        proxy = (mean_ret / 0.0005) * float(np.sqrt(252.0))
        return float(np.clip(proxy, -10.0, 10.0))
    sharpe = (mean_ret / std) * float(np.sqrt(252.0))
    return float(np.clip(sharpe, -10.0, 10.0))


def _failure_rate(order_outcomes: List[int]) -> float:
    if not order_outcomes:
        return 0.0
    success_ratio = float(sum(order_outcomes)) / float(len(order_outcomes))
    return 1.0 - success_ratio


def _select_adaptive_profile(
    rolling_sharpe: float,
    fail_rate: float,
    drawdown_pct: float,
    usd_balance: float,
    micro_balance_threshold_usd: float = 25.0,
) -> str:
    # Micro-balance mode: prioritize deployment when capital is tiny.
    if usd_balance < float(micro_balance_threshold_usd):
        return "micro"
    # Sharpe recovery mode: if Sharpe is deeply negative, enter recovery.
    if rolling_sharpe < -1.0:
        return "recovery"
    # Conservative downgrade first when instability appears.
    if fail_rate >= 0.55 or drawdown_pct >= 6.0 or rolling_sharpe < -0.20:
        return "safe"
    # Promote to aggressive only on stable quality.
    if fail_rate <= 0.30 and drawdown_pct <= 3.0 and rolling_sharpe >= 1.75:
        return "aggressive"
    return "balanced"


def _apply_profile(runtime_cfg: Dict, profile_name: str) -> Dict:
    out = dict(runtime_cfg)
    out.update(PROFILE_PRESETS.get(profile_name, PROFILE_PRESETS["balanced"]))
    return out

# ── Symbol Watcher Fleet integration ─────────────────────────────────────────
# Import helpers at call time to avoid circular imports.
# The fleet runs as a separate daemon process writing JSON files.
# We read those files here — zero coupling, zero blocking.
def _get_fleet_priority_symbols(excluded: set, n: int = 30) -> List[Dict[str, Any]]:
    """
    Read the watcher fleet summary and return pre-ranked signal candidates.
    Returns list of dicts with keys: symbol, spike_score, spike_real,
    spike_direction, spike_z_score, last_price, peak_high, peak_low.
    Falls back to empty list if fleet is not running.
    """
    try:
        fleet_file = ROOT / "out" / "symbol_states" / "_fleet_summary.json"
        if not fleet_file.exists():
            return []
        age = time.time() - fleet_file.stat().st_mtime
        if age > 60.0:
            # Fleet summary is stale — don't use it
            return []
        payload = json.loads(fleet_file.read_text(encoding="utf-8"))
        top = payload.get("top_signals", [])
        return [
            s for s in top
            if str(s.get("symbol", "")).upper() not in excluded
            and s.get("last_price") is not None
        ][:n]
    except Exception:
        return []


def _fleet_signal_to_decision(sig: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a fleet watcher signal dict into an orchestrator decision dict."""
    symbol    = str(sig.get("symbol", "")).upper()
    direction = str(sig.get("spike_direction", "up") or "up")
    # Map fleet direction to orchestrator convention
    orch_dir  = "long" if direction == "up" else "short"
    z         = float(sig.get("spike_z_score", 0.0) or 0.0)
    score     = float(sig.get("spike_score", 0.0) or 0.0)
    # Derive synthetic confidence and edge from spike stats
    confidence = min(0.99, max(0.50, 0.50 + (score / 10.0)))
    edge_bps   = max(8.0, score * 12.0)
    return {
        "symbol":         symbol,
        "direction":      orch_dir,
        "confidence":     round(confidence, 4),
        "edge_bps":       round(edge_bps, 2),
        "regime":         "spike_detected",
        "signal":         f"z={z:.2f}_real={sig.get('spike_real', False)}",
        "source":         "symbol_watcher_fleet",
        "spike_real":     bool(sig.get("spike_real", False)),
        "spike_score":    round(score, 4),
        "spike_z_score":  round(z, 4),
        "peak_high":      sig.get("peak_high"),
        "peak_low":       sig.get("peak_low"),
        "peak_high_ts":   sig.get("peak_high_ts"),
        "peak_low_ts":    sig.get("peak_low_ts"),
        "last_price":     sig.get("last_price"),
        "spread_bps":     sig.get("spread_bps"),
        "market_data_mode": "watcher_fleet",
    }


# Live harmonic decision engine
def get_next_symbol_decision(excluded_symbols: Optional[set] = None, max_attempts: int = 24) -> Dict:
    """
    Live harmonic signal engine — replaces random stub.
    Rotates through SYMBOL_REGISTRY, fetches Kraken OHLC, and runs
    the best (flow × strategy × algo) from institutional_live_selection.json.

    FLEET INTEGRATION: If the symbol_watcher_fleet daemon is running and its
    summary file is fresh (< 60s old), this function FIRST checks for confirmed
    real-spike candidates from the fleet.  Real spikes are returned immediately
    — no brute-force scan needed.  This gives the orchestrator first-mover
    advantage on every spike across all 1,693 symbols.

    Returns: {symbol, direction, confidence, edge_bps, regime, signal, source}
    """
    excluded = {str(s).strip().upper() for s in (excluded_symbols or set()) if str(s).strip()}
    last_decision = None
    attempts = max(1, int(max_attempts or 1))

    # === SYMBOL WATCHER FLEET — first-mover spike detection ==================
    # If the fleet daemon is running, real spikes are pre-detected across ALL
    # symbols every few seconds.  Grab the best confirmed real-spike first.
    # This fires BEFORE the brute-force scan so we never miss a spike window.
    fleet_candidates = _get_fleet_priority_symbols(excluded, n=30)
    if fleet_candidates:
        # Prefer confirmed real spikes first, then any high-score signal
        real_spikes = [s for s in fleet_candidates if s.get("spike_real")]
        best_fleet  = (real_spikes or fleet_candidates)[0]
        sym_upper   = str(best_fleet.get("symbol", "")).upper()
        if sym_upper and sym_upper not in excluded and sym_upper in SYMBOL_REGISTRY:
            decision = _fleet_signal_to_decision(best_fleet)
            real_tag = "REAL-SPIKE" if best_fleet.get("spike_real") else "signal"
            print(
                f"[FLEET-HIT] {sym_upper} {real_tag} "
                f"z={best_fleet.get('spike_z_score', 0.0):.2f} "
                f"score={best_fleet.get('spike_score', 0.0):.3f} "
                f"dir={best_fleet.get('spike_direction', '?')} "
                f"price={best_fleet.get('last_price')}"
            )
            return decision
    # =========================================================================

    # Use multi-asset rolling capital engine for dynamic symbol/pair selection and adaptive sizing

    # === LIVE OPPORTUNITY HEATMAP & LOGGING ===
    heatmap = get_rolling_capital_heatmap() or []
    if heatmap:
        # Log top 5 opportunities to a live feed
        top_opps = sorted(heatmap, key=lambda x: float(x.get('sharpe', 0.0)), reverse=True)[:5]
        with open(OUT / 'live_opportunity_feed.json', 'w', encoding='utf-8') as f:
            json.dump(top_opps, f, indent=2)
        # Print top opportunity for alerting
        if top_opps:
            print(f"[HEATMAP] Top live opportunity: {top_opps[0].get('symbol','?')} Sharpe={top_opps[0].get('sharpe',0.0):.3f} Edge={top_opps[0].get('edge_bps',0.0):.2f}bps")

    # === AGGRESSIVE COMPOUNDING MODE (profile/risk logic) ===
    # If runtime_cfg or profile is set to 'aggressive', boost risk fraction and max position
    global runtime_cfg, active_profile
    if str(runtime_cfg.get('mode','')).lower() == 'live' and (active_profile == 'aggressive' or runtime_cfg.get('aggressive_compounding', False)):
        runtime_cfg['base_risk_fraction'] = 0.45
        runtime_cfg['max_position_usd'] = max(150.0, float(runtime_cfg.get('max_position_usd', 0.0)))
        runtime_cfg['reserve_usd'] = min(8.0, float(runtime_cfg.get('reserve_usd', 8.0)))
        print("[PROFILE] Aggressive compounding mode ENABLED")

    # === DYNAMIC SYMBOL/PAIR SELECTION & ADAPTIVE SIZING ===
    best_symbol, best_family, best_metrics = _normalize_best_multi_payload(get_rolling_capital_best_multi())
    if best_symbol and best_family:
        print(f"[ORCH] Using rolling capital best: {best_symbol} {best_family} Sharpe: {best_metrics.get('sharpe', 0.0):.3f}")
        best_direction = str(best_metrics.get('direction', 'long') or 'long').strip().lower()
        if best_direction not in ('long', 'short'):
            best_direction = 'long'
        # Build decision dict for orchestrator
        decision = {
            'symbol': best_symbol,
            'family': best_family,
            'direction': best_direction,
            'confidence': float(best_metrics.get('win_rate', 0.0)),
            'edge_bps': float(best_metrics.get('sharpe', 0.0)) * 100,
            'regime': 'rolling_capital',
            'signal': 'multi_family',
            'source': 'rolling_capital_engine_multi',
            'rolling_capital_metrics': best_metrics,
        }
        # Adaptive sizing: scale position size by Sharpe/volatility/edge/confidence
        edge = abs(float(best_metrics.get('sharpe', 0.0)))
        conf = float(best_metrics.get('win_rate', 0.0))
        # Sizing factor: higher of edge or confidence, capped
        adaptive_size_factor = max(0.1, min(2.5, max(edge, conf)))
        decision['adaptive_size_factor'] = adaptive_size_factor
        # Log adaptive sizing
        print(f"[SIZING] Adaptive size factor: {adaptive_size_factor:.3f} (edge={edge:.3f}, conf={conf:.3f})")
        if best_symbol.upper() not in (excluded or set()):
            return decision

    # Fallback to normal logic
    for _ in range(attempts):
        decision = harmonic_connector.get_decision()
        if not isinstance(decision, dict):
            continue
        last_decision = decision
        symbol = str(decision.get('symbol', '')).upper().strip()
        if symbol and symbol not in excluded:
            return decision

    return last_decision or harmonic_connector.get_decision()


def _estimate_max_feasible_notional(runtime_cfg: Dict, usd_balance: float, effective_usd_balance: float, futures_mode: bool) -> float:
    leverage_preview = float(runtime_cfg.get('leverage_multiplier', 1.0) or 1.0)
    leverage_preview = max(1.0, min(5.0, leverage_preview))
    leverage_notional_preview = leverage_preview if futures_mode else 1.0
    reserve_preview = float(runtime_cfg.get('reserve_usd', 15.0) or 15.0)
    min_position_preview = float(runtime_cfg.get('min_position_usd', 5.0) or 5.0)
    if usd_balance <= (reserve_preview + min_position_preview):
        reserve_preview = 0.0
    allocatable_preview = max(0.0, effective_usd_balance - reserve_preview)
    return allocatable_preview * 0.92 * leverage_notional_preview


def _resolve_pair_fillability_bounds(runtime_cfg: Dict, config: Dict, current_price: float) -> Dict[str, float]:
    base_min_notional = float(config.get('min_order', 0.0) or 0.0) * max(float(current_price), 1e-9)
    # KRAKEN FEE HARDENING: Use actual 2% taker fee, not a vague "cushion"
    # We must reserve for: entry fee (2%) + slippage (1%) + exit fee (2%) = 5% minimum guard
    kraken_taker_fee_pct = float(runtime_cfg.get('kraken_taker_fee_pct', 0.0026) or 0.0026)
    slip_cushion_pct = float(runtime_cfg.get('min_order_slippage_cushion_pct', 0.010) or 0.010)
    # Total guard multiplier now accounts for entry fee + slippage + exit fee
    guard_enabled = bool(runtime_cfg.get('pair_fill_guard_enabled', True))

    guard_multiplier = (1.0 + kraken_taker_fee_pct + slip_cushion_pct + kraken_taker_fee_pct) if guard_enabled else 1.0
    required_notional = max(base_min_notional * guard_multiplier, float(runtime_cfg.get('min_notional_floor_usd', 1.0) or 1.0))
    required_qty = required_notional / max(float(current_price), 1e-9)



    return {
        'min_qty': required_qty,
        'min_notional': required_notional,
        'guard_multiplier': guard_multiplier,
    }


def _profit_lock_risk_scalar(runtime_cfg: Dict, realized_pnl_total: float, realized_pnl_peak: float) -> Dict[str, Any]:
    if not bool(runtime_cfg.get('profit_lock_enabled', True)):
        return {
            'risk_scalar': 1.0,
            'drawdown_frac': 0.0,
            'reason': 'profit_lock_disabled',
        }

    trigger_usd = float(runtime_cfg.get('profit_lock_trigger_usd', 25.0) or 25.0)
    drawdown_limit = float(runtime_cfg.get('profit_lock_drawdown_frac', 0.35) or 0.35)
    risk_floor = float(runtime_cfg.get('profit_lock_risk_floor', 0.35) or 0.35)

    if realized_pnl_peak < trigger_usd:
        return {
            'risk_scalar': 1.0,
            'drawdown_frac': 0.0,
            'reason': 'profit_lock_not_armed',
        }

    base_peak = max(realized_pnl_peak, 1e-9)
    drawdown_frac = max(0.0, (realized_pnl_peak - realized_pnl_total) / base_peak)
    if drawdown_frac <= 0.0:
        return {
            'risk_scalar': 1.0,
            'drawdown_frac': 0.0,
            'reason': 'profit_lock_no_drawdown',
        }

    normalized = min(1.0, drawdown_frac / max(drawdown_limit, 1e-9))
    risk_scalar = max(risk_floor, 1.0 - (1.0 - risk_floor) * normalized)
    return {
        'risk_scalar': float(risk_scalar),
        'drawdown_frac': float(drawdown_frac),
        'reason': 'profit_lock_throttled' if risk_scalar < 0.999 else 'profit_lock_no_throttle',
    }


def _compute_runway_metrics(
    runtime_cfg: Dict,
    start_ts: float,
    now_ts: float,
    portfolio_equity_usd: float,
    realized_pnl_samples: List[Dict[str, Any]],
    entry_timestamps: List[float],
) -> Dict[str, Any]:
    elapsed_hours = max(0.0, (now_ts - start_ts) / 3600.0)
    goal_usd = float(runtime_cfg.get('runway_goal_usd', 1000000.0) or 1000000.0)
    horizon_days = float(runtime_cfg.get('runway_goal_horizon_days', 3650.0) or 3650.0)

    progress_pct = min(100.0, max(0.0, (portfolio_equity_usd / max(goal_usd, 1e-9)) * 100.0))

    pnl_velocity_usd_per_hour = 0.0
    samples = [s for s in realized_pnl_samples if now_ts - float(s.get('ts', 0.0)) <= 24.0 * 3600.0]
    if len(samples) >= 2:
        samples.sort(key=lambda x: float(x.get('ts', 0.0)))
        first = samples[0]
        last = samples[-1]
        dt_hours = max(1e-9, (float(last.get('ts', 0.0)) - float(first.get('ts', 0.0))) / 3600.0)
        pnl_velocity_usd_per_hour = (float(last.get('pnl', 0.0)) - float(first.get('pnl', 0.0))) / dt_hours

    entries_last_hour = len([ts for ts in entry_timestamps if (now_ts - float(ts)) <= 3600.0])

    remaining_usd = max(0.0, goal_usd - portfolio_equity_usd)
    projected_days_to_goal = None
    if pnl_velocity_usd_per_hour > 1e-9:
        projected_days_to_goal = remaining_usd / (pnl_velocity_usd_per_hour * 24.0)

    expected_progress_pct = min(100.0, max(0.0, (elapsed_hours / 24.0) / max(horizon_days, 1e-9) * 100.0))

    return {
        'runway_goal_usd': float(goal_usd),
        'runway_progress_pct': float(round(progress_pct, 3)),
        'runway_expected_progress_pct': float(round(expected_progress_pct, 3)),
        'runway_gap_pct': float(round(progress_pct - expected_progress_pct, 3)),
        'runway_elapsed_hours': float(round(elapsed_hours, 3)),
        'runway_entries_last_hour': int(entries_last_hour),
        'runway_entries_per_hour': float(round(float(entries_last_hour), 3)),
        'runway_pnl_velocity_usd_per_hour': float(round(pnl_velocity_usd_per_hour, 6)),
        'runway_projected_days_to_goal': None if projected_days_to_goal is None else float(round(projected_days_to_goal, 3)),
        'runway_on_track': bool(progress_pct >= expected_progress_pct),
    }


_RANKED_CANDIDATES_CACHE: Dict[str, Any] = {
    'timestamp': 0.0,
    'scan_size': 0,
    'candidates': [],
}


def _select_capital_aware_candidate(runtime_cfg: Dict, usd_balance: float, effective_usd_balance: float, futures_mode: bool):
    import sys
    print("[DEBUG-SELECT] Entered _select_capital_aware_candidate", file=sys.stderr, flush=True)
    global _RANKED_CANDIDATES_CACHE

    symbol_blacklist = {
        str(s).strip().upper()
        for s in (runtime_cfg.get('symbol_blacklist', []) or [])
        if str(s).strip()
    }

    if not bool(runtime_cfg.get('capital_aware_ranking_enabled', True)):
        print("[DEBUG-SELECT] Early return: capital_aware_ranking_enabled is False", file=sys.stderr, flush=True)
        return get_next_symbol_decision(excluded_symbols=symbol_blacklist), None, {'selection_mode': 'legacy'}

    micro_balance_threshold_usd = float(runtime_cfg.get('micro_balance_threshold_usd', 25.0) or 25.0)
    micro_mode = usd_balance > 0 and usd_balance <= micro_balance_threshold_usd

    scan_size = int(runtime_cfg.get('capital_aware_scan_size', 6) or 6)
    if micro_mode:
        scan_size = max(scan_size, int(runtime_cfg.get('micro_scan_size', 12) or 12))

    # DEBUG PATCH: Print scan_size and all available symbols
    all_symbols = list(SYMBOL_REGISTRY.keys())
    print(f"[DEBUG-FIX] capital_aware_scan_size={scan_size} | SYMBOL_REGISTRY count={len(all_symbols)}", file=sys.stderr, flush=True)
    print(f"[DEBUG-FIX] First 20 symbols: {all_symbols[:20]}", file=sys.stderr, flush=True)

    micro_low_min_order_symbols = {
        str(s).upper()
        for s in (runtime_cfg.get('micro_low_min_order_symbols', ['ADA', 'XRP', 'DOGE', 'SOL', 'BTC', 'ETH']) or [])
    }
    micro_max_min_notional_usd = float(runtime_cfg.get('micro_max_min_notional_usd', 25.0) or 25.0)
    micro_priority_bonus = float(runtime_cfg.get('micro_priority_bonus', 15.0) or 15.0)

    rank_cache_sec = float(runtime_cfg.get('capital_aware_rank_cache_sec', 15.0) or 15.0)
    rank_cache_sec = max(0.0, rank_cache_sec)
    selection_timeout_sec = max(0.25, float(runtime_cfg.get('capital_aware_selection_timeout_sec', 4.0) or 4.0))
    cache_ts = float(_RANKED_CANDIDATES_CACHE.get('timestamp', 0.0) or 0.0)
    cache_scan_size = int(_RANKED_CANDIDATES_CACHE.get('scan_size', 0) or 0)
    cache_candidates = _RANKED_CANDIDATES_CACHE.get('candidates', [])
    cache_age_sec = max(0.0, time.time() - cache_ts)
    selection_mode = 'capital_aware'

    import sys
    print(f"[DEBUG-CACHE] rank_cache_sec={rank_cache_sec} cache_scan_size={cache_scan_size} scan_size={scan_size} cache_age_sec={cache_age_sec} cache_candidates_len={len(cache_candidates)}", file=sys.stderr, flush=True)

    if (
        rank_cache_sec > 0.0
        and cache_scan_size >= scan_size
        and cache_age_sec <= rank_cache_sec
        and isinstance(cache_candidates, list)
        and len(cache_candidates) > 0
    ):
        print("[DEBUG-CACHE] Using cached candidates", file=sys.stderr, flush=True)
        ranked_candidates = [dict(c) for c in cache_candidates[:scan_size] if isinstance(c, dict)]
    else:
        print("[DEBUG-CACHE] Cache miss, starting ranking thread", file=sys.stderr, flush=True)
        # Fetch fresh rankings in a daemon thread — hard timeout to prevent blocking the main loop
        _rank_result: Dict[str, Any] = {'done': False, 'items': [], 'error': None}


        def _ranking_worker() -> None:
            import sys
            print("[DEBUG-THREAD] Ranking thread started", file=sys.stderr, flush=True)
            import traceback
            try:
                print("[DEBUG-THREAD] About to call get_ranked_decisions", file=sys.stderr, flush=True)
                _rank_result['items'] = harmonic_connector.get_ranked_decisions(scan_size=scan_size)
                print("[DEBUG-THREAD] get_ranked_decisions call returned", file=sys.stderr, flush=True)
            except Exception as _exc:
                tb = traceback.format_exc()
                print(f"[DEBUG-THREAD] Exception in ranking thread: {_exc}\n{tb}", file=sys.stderr, flush=True)
                _rank_result['error'] = tb
            finally:
                _rank_result['done'] = True

        print("[DEBUG-THREAD] About to start ranking thread", file=sys.stderr, flush=True)
        _t = threading.Thread(target=_ranking_worker, name='capital-aware-ranking', daemon=True)
        _t.start()
        _t.join(timeout=selection_timeout_sec)

        if not _rank_result.get('done'):
            # Timed out — use stale cache or fall back to legacy (no hang)
            if isinstance(cache_candidates, list) and len(cache_candidates) > 0:
                ranked_candidates = [dict(c) for c in cache_candidates[:scan_size] if isinstance(c, dict)]
                selection_mode = 'capital_aware_stale_cache_timeout'
            else:
                return get_next_symbol_decision(excluded_symbols=symbol_blacklist), None, {
                    'selection_mode': 'legacy_timeout_fallback',
                    'selection_timeout_sec': float(selection_timeout_sec),
                    'scan_size': int(scan_size),
                    'micro_mode': bool(micro_mode),
                }
        elif _rank_result.get('error'):
            if isinstance(cache_candidates, list) and len(cache_candidates) > 0:
                ranked_candidates = [dict(c) for c in cache_candidates[:scan_size] if isinstance(c, dict)]
                selection_mode = 'capital_aware_stale_cache_error'
            else:
                return get_next_symbol_decision(excluded_symbols=symbol_blacklist), None, {
                    'selection_mode': 'legacy_error_fallback',
                    'selection_error': str(_rank_result.get('error', ''))[:160],
                    'scan_size': int(scan_size),
                    'micro_mode': bool(micro_mode),
                }
        else:
            ranked_candidates = list(_rank_result.get('items') or [])
            _RANKED_CANDIDATES_CACHE.update({
                'timestamp': float(time.time()),
                'scan_size': int(scan_size),
                'candidates': [dict(c) for c in ranked_candidates if isinstance(c, dict)],
            })

    # === DEBUG PATCH: Print all candidate symbols and fallback status ===
    candidate_symbols = [str(c.get('symbol', '?')).upper() for c in ranked_candidates if isinstance(c, dict)]
    print(f"[DEBUG] Candidate symbols this loop: {candidate_symbols}")

    max_feasible_order_usd = _estimate_max_feasible_notional(runtime_cfg, usd_balance, effective_usd_balance, futures_mode)
    pounce_threshold = float(runtime_cfg.get('gate_override_min_edge_bps', 12.0) or 12.0) + float(runtime_cfg.get('pounce_edge_bps_bonus', 4.0) or 4.0)
    selection_min_edge_bps = float(runtime_cfg.get('selection_min_edge_bps', 20.0) or 20.0)

    best_executable = None
    best_fallback = None
    best_low_edge = None
    now_ts = time.time()

    # FORCE: Always pick the top ranked candidate and fire, bypassing all edge/affordability checks
    for candidate in ranked_candidates:
        raw_symbol = str(candidate.get('symbol', '')).upper()
        # Normalize symbol for ticker/registry lookup (strip /USD etc.)
        symbol = raw_symbol.split("/")[0] if "/" in raw_symbol else raw_symbol
        if not symbol or symbol in symbol_blacklist:
            continue
        ticker = router.get_ticker(symbol)
        print(f"[DEBUG-TICKER-LOOKUP] Symbol: {symbol}, get_ticker() returned: {ticker}")
        sys.stdout.flush(); sys.stderr.flush()
        if not ticker:
            print(f"[DEBUG-TICKER-MISS] No ticker for {symbol}, fallback to CSV/local data should trigger in connector.")
            sys.stdout.flush(); sys.stderr.flush()
            continue
        enriched = dict(candidate)
        return enriched, ticker, {
            'selection_mode': 'forced_always_fire',
            'scan_size': scan_size,
            'micro_mode': bool(micro_mode),
            'micro_threshold_usd': micro_balance_threshold_usd,
            'selection_timeout_sec': float(selection_timeout_sec),
        }
    # If no candidates, fallback as before
    print("[DEBUG-SELECT] End of function: returning forced_legacy_fallback", file=sys.stderr, flush=True)
    return get_next_symbol_decision(excluded_symbols=symbol_blacklist), None, {
        'selection_mode': 'forced_legacy_fallback',
        'scan_size': scan_size,
        'micro_mode': bool(micro_mode),
        'micro_threshold_usd': micro_balance_threshold_usd,
    }

print("\n[STATUS] Ready for execution")
print(f"  Initial Capital: ${initial_capital_usd:.2f}")
print(f"  Pyramid Level: {pyramid_level}")
print(f"  Symbols Available: {len(SYMBOL_REGISTRY)}")
print(f"  Runtime Mode: {str(runtime_cfg.get('mode', 'paper')).upper()}")
print(f"  Live Orders Armed: {bool(runtime_cfg.get('allow_live_orders', False))}")
print(
    "  Live Data Engine: "
    f"cache={'ON' if bool(runtime_cfg.get('live_ohlc_cache_enabled', True)) else 'OFF'}, "
    f"ttl={float(runtime_cfg.get('live_ohlc_cache_ttl_sec', 8.0) or 8.0):.1f}s, "
    f"ws={'ON' if bool(runtime_cfg.get('live_websocket_enabled', True)) else 'OFF'}, "
    f"reselection={'ON' if bool(runtime_cfg.get('live_reselection_enabled', False)) else 'OFF'}"
)
print(
    "  Entry Edge Gate: "
    f"min_expected_net_edge_bps={float(runtime_cfg.get('min_expected_net_edge_bps', 65.0) or 65.0):.2f}, "
    f"edge_fee_coverage_multiplier={float(runtime_cfg.get('edge_fee_coverage_multiplier', 1.15) or  1.15):.2f}, "
    f"min_gate_score_for_entry={float(runtime_cfg.get('min_gate_score_for_entry', 0.996) or 0.996):.3f}"
)
print(f"  Adaptive Profile: {active_profile.upper()}")
print("=" * 70)


# Ensure sys is imported everywhere needed (threaded/inner functions)
import sys

import traceback
import logging

# Setup persistent error log file
robust_log_path = OUT / 'orchestrator_exceptions.log'
logging.basicConfig(
    filename=str(robust_log_path),
    filemode='a',
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.ERROR
)

loop_count = 0
last_live_profile_sync_log_ts = 0.0
last_runtime_drift_alert_log_ts = 0.0
runtime_profile_sync_events_window: deque = deque(maxlen=512)
while True:
    try:
        loop_count += 1
        timestamp = datetime.now(timezone.utc)
        print(f"[DEBUG-MAIN-LOOP] Top of main loop, loop_count={loop_count}", file=sys.stderr, flush=True)
        sys.stdout.flush(); sys.stderr.flush()

        # === META ENGINE: Route capital and run all engines ===
        # You can pass live data/context as needed; here we pass portfolio and runtime_cfg
        meta_results = meta_engine.run(data=portfolio, context=runtime_cfg)
        print(f"[META ENGINE] Results: {meta_results}")

        loaded_runtime_cfg = _validate_runtime_cfg(runtime_guard.load())
        runtime_writer_meta = runtime_writer_hint(loaded_runtime_cfg)
        runtime_cfg = _force_live_mode(loaded_runtime_cfg)

        forced_runtime_updates = {
            'mode': str(runtime_cfg.get('mode', 'live')).lower(),
            'allow_live_orders': bool(runtime_cfg.get('allow_live_orders', True)),
            'paper_enabled': bool(runtime_cfg.get('paper_enabled', False)),
        }
        if (
            str(loaded_runtime_cfg.get('mode', 'paper')).lower() != 'live'
            or bool(loaded_runtime_cfg.get('allow_live_orders', False)) != forced_runtime_updates['allow_live_orders']
            or bool(loaded_runtime_cfg.get('paper_enabled', True)) != forced_runtime_updates['paper_enabled']
        ):
            changed_runtime = _persist_runtime_tuner_updates(forced_runtime_updates)
            if changed_runtime:
                now_sync_ts = time.time()
                runtime_profile_sync_events_window.append(now_sync_ts)
                if (now_sync_ts - last_live_profile_sync_log_ts) >= 30.0:
                    print(f"  🔁 Runtime profile re-synced to LIVE: {changed_runtime}")
                    last_live_profile_sync_log_ts = now_sync_ts
                event_logger.emit(
                    "runtime_live_profile_forced",
                    loop_count,
                    reason_code="runtime_profile_sync",
                    context={
                        "mode": changed_runtime.get('mode', forced_runtime_updates['mode']),
                        "allow_live_orders": bool(changed_runtime.get('allow_live_orders', forced_runtime_updates['allow_live_orders'])),
                        "paper_enabled": bool(changed_runtime.get('paper_enabled', forced_runtime_updates['paper_enabled'])),
                    },
                )
                drift_alert = _persist_runtime_drift_alert(
                    loop_count,
                    runtime_cfg,
                    changed_runtime,
                    runtime_profile_sync_events_window,
                    now_sync_ts,
                    runtime_writer_meta=runtime_writer_meta,
                )
                if bool(drift_alert.get('excessive', False)):
                    operator_alert = _persist_runtime_drift_operator_alert(loop_count, drift_alert)
                    if (now_sync_ts - last_runtime_drift_alert_log_ts) >= 30.0:
                        print(
                            "  [WARN] Runtime drift rate elevated: "
                            f"{int(drift_alert.get('window_events', 0))}/"
                            f"{int(drift_alert.get('window_seconds', 0))}s"
                        )
                        last_runtime_drift_alert_log_ts = now_sync_ts
                    event_logger.emit(
                        "runtime_live_profile_drift_excessive",
                        loop_count,
                        reason_code="runtime_profile_drift_rate",
                        context={
                            "window_events": int(drift_alert.get('window_events', 0) or 0),
                            "window_seconds": float(drift_alert.get('window_seconds', 0.0) or 0.0),
                            "threshold": int(drift_alert.get('threshold', 0) or 0),
                            "likely_culprit_writer": str(drift_alert.get('likely_culprit_writer', '') or ''),
                            "operator_alert_file": str(RUNTIME_DRIFT_OPERATOR_ALERT_FILE),
                            "operator_alert_severity": str(operator_alert.get('severity', 'high') or 'high'),
                            "operator_alert_write_ok": bool(operator_alert.get('write_ok', False)),
                            "operator_alert_file_exists": bool(operator_alert.get('file_exists', False)),
                            "operator_alert_write_error": str(operator_alert.get('write_error', '') or ''),
                            "operator_alert_fallback_write_error": str(operator_alert.get('fallback_write_error', '') or ''),
                        },
                    )

        harmonic_connector.update_runtime_config(runtime_cfg)

        strict_live_only = bool(runtime_cfg.get('strict_live_only', False))
        live_profile_armed = (
            str(runtime_cfg.get('mode', 'paper')).lower() == 'live'
            and bool(runtime_cfg.get('allow_live_orders', False))
            and not bool(runtime_cfg.get('paper_enabled', False))
            and not bool(runtime_cfg.get('kill_switch', False))
        )
        if strict_live_only and (not live_profile_armed):
            event_logger.emit(
                "strict_live_profile_blocked",
                loop_count,
                reason_code="profile_not_live_armed",
                context={
                    "mode": str(runtime_cfg.get('mode', 'paper')),
                    "allow_live_orders": bool(runtime_cfg.get('allow_live_orders', False)),
                    "paper_enabled": bool(runtime_cfg.get('paper_enabled', True)),
                    "kill_switch": bool(runtime_cfg.get('kill_switch', False)),
                },
            )
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='blocked',
                reason='strict_live_profile_not_armed',
            )
            print("  ⛔ Strict live-only profile not armed; blocking loop")
            time.sleep(max(0.5, float(runtime_cfg.get('loop_seconds', 1) or 1)))
            continue

        if bool(runtime_cfg.get('x1000_auto_enabled', True)):
            x1000_interval_loops = int(runtime_cfg.get('x1000_interval_loops', 60) or 60)
            if (loop_count - last_x1000_trigger_loop) >= x1000_interval_loops:
                x1000_result = _run_x1000_control_plane(runtime_cfg, loop_count)
                last_x1000_trigger_loop = loop_count
                status_txt = str(x1000_result.get('status', 'unknown'))
                print(f"  ⚡ X1000 control-plane cycle @ loop {loop_count}: {status_txt}")
                event_logger.emit(
                    "x1000_cycle",
                    loop_count,
                    reason_code=status_txt,
                    latency_ms=float(x1000_result.get('elapsed_ms', 0.0) or 0.0),
                    context={
                        "returncode": x1000_result.get('returncode'),
                        "x1000_passes": int(runtime_cfg.get('x1000_passes', 2) or 2),
                        "x1000_auto_apply": bool(runtime_cfg.get('x1000_auto_apply', False)),
                        "stdout_tail": x1000_result.get('stdout_tail', ''),
                        "stderr_tail": x1000_result.get('stderr_tail', ''),
                    },
                )
                audit_chain.append(
                    "x1000_cycle",
                    {
                        "loop": loop_count,
                        "status": status_txt,
                        "ok": bool(x1000_result.get('ok', False)),
                        "returncode": x1000_result.get('returncode'),
                        "elapsed_ms": float(x1000_result.get('elapsed_ms', 0.0) or 0.0),
                        "reason": x1000_result.get('reason'),
                    },
                    timestamp.isoformat(),
                )

        rolling_sharpe = _rolling_sharpe_from_pnl_pct(list(rolling_pnl_pct))
        fail_rate = _failure_rate(list(rolling_order_outcomes))
        drawdown_pct = abs(float(portfolio.max_drawdown)) * 100.0

        now_ts = time.time()
        balances_for_profile = {}
        if (now_ts - last_balance_fetch_ts) >= balance_poll_interval_sec:
            polled = router.get_balance()
            if polled:
                last_balance_snapshot = polled
                last_balance_fetch_ts = now_ts
                balances_for_profile = polled
            else:
                balances_for_profile = last_balance_snapshot
        else:
            balances_for_profile = last_balance_snapshot
        profile_balance = 0.0
        for _k in ['ZUSD', 'USD', 'USDT', 'USDC']:
            if _k in balances_for_profile:
                try:
                    profile_balance = float(balances_for_profile.get(_k, 0) or 0)
                    if profile_balance > 0:
                        break
                except Exception:
                    pass

        candidate_profile = _select_adaptive_profile(
            rolling_sharpe,
            fail_rate,
            drawdown_pct,
            profile_balance,
            float(runtime_cfg.get('micro_balance_threshold_usd', 25.0) or 25.0),
        )
        if candidate_profile != active_profile and (loop_count - last_profile_switch_loop) >= 8:
            prev_profile = active_profile
            active_profile = candidate_profile
            last_profile_switch_loop = loop_count
            print(
                f"  🔁 Adaptive profile switch: {prev_profile.upper()} -> {active_profile.upper()} "
                f"| Sharpe={rolling_sharpe:.2f} Fail={fail_rate:.2%} DD={drawdown_pct:.2f}%"
            )
            audit_chain.append(
                "adaptive_profile_switch",
                {
                    "loop": loop_count,
                    "from": prev_profile,
                    "to": active_profile,
                    "rolling_sharpe": float(rolling_sharpe),
                    "failure_rate": float(fail_rate),
                    "drawdown_pct": float(drawdown_pct),
                },
                timestamp.isoformat(),
            )

        runtime_cfg = _apply_profile(runtime_cfg, active_profile)
        profile_locked_values = _load_runtime_profile_lock_overrides()
        if profile_locked_values:
            runtime_cfg.update(profile_locked_values)
        runtime_cfg = _maybe_run_adaptive_selection_tuner(
            runtime_cfg,
            trade_log,
            loop_count,
            last_successful_order_ts,
            event_logger,
        )
        _atomic_write_json(
            ADAPTIVE_PROFILE_FILE,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_profile": active_profile,
                "rolling_sharpe": float(rolling_sharpe),
                "rolling_failure_rate": float(fail_rate),
                "drawdown_pct": float(drawdown_pct),
                "micro_balance_threshold_usd": float(runtime_cfg.get('micro_balance_threshold_usd', 25.0) or 25.0),
                "sampled_trades": len(rolling_pnl_pct),
                "sampled_orders": len(rolling_order_outcomes),
                "profile_presets": PROFILE_PRESETS,
            },
            indent=2,
        )

        selection_usd_balance = profile_balance
        selection_effective_usd_balance = selection_usd_balance
        selection_futures_mode = bool(runtime_cfg.get('futures_mode', False)) and futures_leverage_supported
        if selection_futures_mode:
            tb = last_trade_balance_snapshot or {}
            try:
                selection_margin_free = float(tb.get('mf', 0) or 0)
                if selection_margin_free > selection_effective_usd_balance:
                    selection_effective_usd_balance = selection_margin_free
            except Exception:
                pass
            manual_bp = _sanitize_fallback_buying_power_usd(runtime_cfg.get('fallback_buying_power_usd', 0.0))
            if selection_effective_usd_balance <= 0 and manual_bp > 0:
                selection_effective_usd_balance = manual_bp

        _persist_live_engine_heartbeat(
            loop_count,
            runtime_cfg,
            portfolio,
            active_profile,
            status='selecting',
            reason='capital_aware_ranking',
            usd_balance=selection_usd_balance,
            extra={
                'effective_usd_balance': float(selection_effective_usd_balance),
                'capital_aware_rank_cache_sec': float(runtime_cfg.get('capital_aware_rank_cache_sec', 15.0) or 15.0),
            },
        )

        # Get decision from engine
        selection_result = _select_capital_aware_candidate(
            runtime_cfg,
            usd_balance=selection_usd_balance,
            effective_usd_balance=selection_effective_usd_balance,
            futures_mode=selection_futures_mode,
        )
        if isinstance(selection_result, tuple):
            if len(selection_result) >= 3:
                engine_decision, preloaded_ticker, selection_meta = selection_result[0], selection_result[1], selection_result[2]
            elif len(selection_result) == 2:
                engine_decision, preloaded_ticker = selection_result
                selection_meta = {'selection_mode': 'legacy_two_tuple_coerced'}
            elif len(selection_result) == 1:
                engine_decision = selection_result[0]
                preloaded_ticker = None
                selection_meta = {'selection_mode': 'legacy_single_value_coerced'}
            else:
                engine_decision = None
                preloaded_ticker = None
                selection_meta = {'selection_mode': 'empty_selection_result'}
        else:
            engine_decision = selection_result
            preloaded_ticker = None
            selection_meta = {'selection_mode': 'non_tuple_selection_result'}
        if not isinstance(selection_meta, dict):
            selection_meta = {'selection_mode': 'selection_meta_coerced'}
        live_market_stream_status = _load_live_market_stream_status()
        live_market_stream_brief = _format_live_market_stream_brief(live_market_stream_status)
        if engine_decision is None:
            shadow_snapshot = {
                'enabled': bool(runtime_cfg.get('shadow_intelligence_enabled', True)),
                'reason': 'no_executable_candidate',
                'selection_mode': str(selection_meta.get('selection_mode', 'capital_aware_wait')),
                'best_symbol': str(selection_meta.get('best_symbol', '') or ''),
                'best_affordability_ratio': float(selection_meta.get('best_affordability_ratio', 0.0) or 0.0),
            }
            event_logger.emit(
                "shadow_intelligence",
                loop_count,
                symbol=str(selection_meta.get('best_symbol', '') or None),
                reason_code="shadow_wait_state",
                context={
                    'shadow_reason': str(shadow_snapshot.get('reason', '')),
                    'selection_mode': str(shadow_snapshot.get('selection_mode', '')),
                    'best_affordability_ratio': float(shadow_snapshot.get('best_affordability_ratio', 0.0) or 0.0),
                },
            )
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='waiting',
                reason=str(selection_meta.get('selection_mode', 'capital_aware_wait')),
                selection_meta=selection_meta,
                extra={
                    'best_symbol': str(selection_meta.get('best_symbol', '')),
                    'best_affordability_ratio': float(selection_meta.get('best_affordability_ratio', 0.0) or 0.0),
                    'shadow_intelligence': dict(shadow_snapshot),
                },
            )
            print(
                f"\n[{loop_count}] {timestamp.strftime('%H:%M:%S')} | No executable candidate "
                f"| Selection: {selection_meta.get('selection_mode', 'capital_aware_wait')} "
                f"| Best: {selection_meta.get('best_symbol', 'N/A')} "
                f"({float(selection_meta.get('best_affordability_ratio', 0.0) or 0.0):.2f}x) "
                f"| Stream: {live_market_stream_brief}"
            )
            _persist_operational_health(
                event_logger,
                portfolio,
                loop_count,
                rolling_pnl_pct,
                rolling_order_outcomes,
                runtime_cfg,
                runway_start_ts,
                realized_pnl_samples,
                entry_timestamps,
                shadow_snapshot,
            )
            time.sleep(0.25)
            continue
        symbol = engine_decision['symbol']
        now_loop_ts = time.time()
        if now_loop_ts < symbol_cooldown_until.get(symbol.upper(), 0.0):
            remaining = symbol_cooldown_until[symbol.upper()] - now_loop_ts
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='cooldown',
                reason='symbol_cooldown_active',
                symbol=symbol,
                engine_decision=engine_decision,
                selection_meta=selection_meta,
                extra={'cooldown_remaining_sec': float(remaining)},
            )
            print(f"\n[{loop_count}] {timestamp.strftime('%H:%M:%S')} | Symbol: {symbol.upper()} | cooling down {remaining:.1f}s")
            time.sleep(0.1)
            continue
        audit_chain.append(
            "engine_decision",
            {
                "loop": loop_count,
                "symbol": symbol,
                "direction": engine_decision.get('direction'),
                "confidence": float(engine_decision.get('confidence', 0.0) or 0.0),
                "edge_bps": float(engine_decision.get('edge_bps', 0.0) or 0.0),
                "regime": engine_decision.get('regime'),
                "source": engine_decision.get('source', 'unknown'),
                "market_data_mode": str(engine_decision.get('market_data_mode', 'unknown') or 'unknown'),
                "live_market_stream_status": live_market_stream_status,
                "selection_mode": selection_meta.get('selection_mode', 'legacy'),
                "ranking_score": float(engine_decision.get('ranking_score', 0.0) or 0.0),
                "affordability_ratio": float(engine_decision.get('affordability_ratio', 0.0) or 0.0)
            },
            timestamp.isoformat()
        )

        print(
            f"\n[{loop_count}] {timestamp.strftime('%H:%M:%S')} | Symbol: {symbol.upper()} "
            f"| Data: {str(engine_decision.get('market_data_mode', 'unknown') or 'unknown').upper()} "
            f"| Stream: {live_market_stream_brief}"
        )
        _persist_live_engine_heartbeat(
            loop_count,
            runtime_cfg,
            portfolio,
            active_profile,
            status='candidate_selected',
            reason='engine_decision_ready',
            symbol=symbol,
            engine_decision=engine_decision,
            selection_meta=selection_meta,
        )

        symbol_blacklist = {str(s).strip().upper() for s in list(runtime_cfg.get('symbol_blacklist', []) or [])}
        hard_symbol_blacklist = {str(s).strip().upper() for s in list(runtime_cfg.get('hard_symbol_blacklist', []) or [])}
        blocked_symbols = symbol_blacklist.union(hard_symbol_blacklist)
        if symbol.upper() in blocked_symbols:
            event_logger.emit(
                "symbol_blacklisted_skip",
                loop_count,
                symbol=symbol,
                reason_code="blacklisted_symbol",
                context={
                    "blocked_by": "hard_symbol_blacklist" if symbol.upper() in hard_symbol_blacklist else "symbol_blacklist",
                },
            )
            print(
                f"  ⛔ Blocked symbol policy skip: {symbol.upper()} "
                f"({ 'hard' if symbol.upper() in hard_symbol_blacklist else 'runtime' } blacklist)"
            )
            symbol_cooldown_until[symbol.upper()] = time.time() + 60.0
            time.sleep(0.1)
            continue

        if engine_decision.get('ranking_score') is not None:
            print(
                f"  Rank Score: {float(engine_decision.get('ranking_score', 0.0) or 0.0):.2f} "
                f"| Affordability: {float(engine_decision.get('affordability_ratio', 0.0) or 0.0):.2f}x "
                f"| Selection: {selection_meta.get('selection_mode', 'legacy')}"
            )

        # Get ticker
        ticker_start = time.time()
        ticker = preloaded_ticker or router.get_ticker(symbol)
        ticker_latency_ms = (time.time() - ticker_start) * 1000.0

        if not ticker:
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='blocked',
                reason='ticker_fetch_failed',
                symbol=symbol,
                engine_decision=engine_decision,
                selection_meta=selection_meta,
            )
            print(f"  ⚠ Could not get ticker")
            event_logger.emit("ticker_fetch_failed", loop_count, symbol=symbol,
                            latency_ms=ticker_latency_ms, reason_code="api_error")
            ticker_cd = float(runtime_cfg.get('ticker_fail_cooldown_sec', 5) or 5)
            symbol_cooldown_until[symbol.upper()] = time.time() + ticker_cd
            time.sleep(0.5)
            continue

        event_logger.emit("ticker_fetched", loop_count, symbol=symbol, latency_ms=ticker_latency_ms)

        current_price = ticker['last']
        bid = ticker['bid']
        ask = ticker['ask']
        pair = ticker['pair']

        config = SYMBOL_REGISTRY[symbol.upper()]

        print(f"  Price: ${current_price:.4f} | Bid: ${bid:.4f} | Ask: ${ask:.4f}")

        # Get balance
        now_ts = time.time()
        if (now_ts - last_balance_fetch_ts) >= balance_poll_interval_sec:
            polled = router.get_balance()
            if polled:
                last_balance_snapshot = polled
                last_balance_fetch_ts = now_ts
                balances = polled
            else:
                balances = last_balance_snapshot
        else:
            balances = last_balance_snapshot
        usd_scan = _resolve_usd_buckets_from_balances(balances)
        usd_balance = float(usd_scan.get('max_usd', 0.0) or 0.0)

        core_snapshot = _build_core_crypto_balance_snapshot(router, balances)
        live_balance_snapshot = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(),
            'loop': int(loop_count),
            'usd_balance_max': float(usd_balance),
            'usd_buckets': dict(usd_scan.get('usd_buckets', {}) or {}),
            'core_crypto_est_usd': float(core_snapshot.get('core_crypto_est_usd', 0.0) or 0.0),
            'portfolio_est_total_usd': float(usd_balance + float(core_snapshot.get('core_crypto_est_usd', 0.0) or 0.0)),
            'core_assets': list(core_snapshot.get('core_assets', []) or []),
            'unpriced_symbols': list(core_snapshot.get('unpriced_symbols', []) or []),
            'raw_assets_positive_count': int(core_snapshot.get('raw_assets_positive_count', 0) or 0),
        }
        _atomic_write_json(LIVE_BALANCE_SNAPSHOT_FILE, live_balance_snapshot, indent=2)
        if usd_balance > 0:
            last_positive_usd_balance = usd_balance
        elif last_positive_usd_balance > 0:
            # Transient empty balance payloads are common; keep last seen positive value.
            usd_balance = last_positive_usd_balance

        futures_mode = bool(runtime_cfg.get('futures_mode', False)) and futures_leverage_supported
        effective_usd_balance = usd_balance
        account_equity_usd = 0.0
        if futures_mode:
            now_tb = time.time()
            if (now_tb - last_trade_balance_fetch_ts) >= trade_balance_poll_interval_sec:
                tb_polled = router.get_trade_balance('ZUSD')
                if tb_polled:
                    last_trade_balance_snapshot = tb_polled
                    last_trade_balance_fetch_ts = now_tb

            tb = last_trade_balance_snapshot or {}
            try:
                account_equity_usd = float(tb.get('eb', 0) or 0)
                margin_free = float(tb.get('mf', 0) or 0)
                if margin_free > effective_usd_balance:
                    effective_usd_balance = margin_free
            except Exception:
                pass

            # Emergency fallback: use operator-provided buying power when APIs are stale.
            manual_bp = _sanitize_fallback_buying_power_usd(runtime_cfg.get('fallback_buying_power_usd', 0.0))
            if effective_usd_balance <= 0 and manual_bp > 0:
                effective_usd_balance = manual_bp

        portfolio_value = usd_balance

        print(f"  Free USD Cash: ${usd_balance:.2f}")
        core_assets = list(core_snapshot.get('core_assets', []) or [])
        core_summary = " | ".join(
            [f"{str(a.get('symbol','?'))}:{float(a.get('qty',0.0) or 0.0):.6f}" for a in core_assets]
        )
        print(
            f"  Core Crypto (BTC/ETH/SOL/ADA/XRP/DOGE) Est: "
            f"${float(core_snapshot.get('core_crypto_est_usd', 0.0) or 0.0):.2f} "
            f"| {core_summary}"
        )
        if core_snapshot.get('unpriced_symbols'):
            print(f"  ⚠ Unpriced core symbols: {', '.join(core_snapshot.get('unpriced_symbols', []))}")
        if account_equity_usd > 0:
            print(f"  Account Equity (eb): ${account_equity_usd:.2f}")
        if futures_mode and effective_usd_balance > usd_balance:
            print(f"  Account Buying Power (mf): ${effective_usd_balance:.2f}")

        # Auto-convert/sweep non-USD collateral to USD so capital recycles into the engine.
        min_position_for_conversion = float(runtime_cfg.get('min_position_usd', 5.0) or 5.0)
        convert_enabled = bool(runtime_cfg.get('auto_convert_collateral', True))
        convert_fraction = float(runtime_cfg.get('collateral_sell_fraction', 0.20) or 0.20)
        convert_cooldown = float(runtime_cfg.get('collateral_convert_cooldown_sec', 12.0) or 12.0)
        proactive_sweep_enabled = bool(runtime_cfg.get('auto_sweep_to_usd_enabled', True))
        sweep_full_balance = bool(runtime_cfg.get('auto_sweep_full_balance', True))
        sweep_require_no_open_positions = bool(runtime_cfg.get('auto_sweep_require_no_open_positions', True))
        sweep_min_notional_usd = float(runtime_cfg.get('auto_sweep_min_notional_usd', 2.0) or 2.0)
        sweep_reserve_asset_qty = float(runtime_cfg.get('auto_sweep_reserve_asset_qty', 0.0) or 0.0)
        sweep_max_assets_per_loop = int(runtime_cfg.get('auto_sweep_max_assets_per_loop', 2) or 2)

        loop_open_positions = len(portfolio.get_open_positions())
        cash_starved = usd_balance < min_position_for_conversion
        no_open_position_gate = (not sweep_require_no_open_positions) or (loop_open_positions == 0)
        cooldown_ready = (time.time() - last_collateral_convert_ts) >= convert_cooldown
        should_attempt_conversion = convert_enabled and cooldown_ready and (cash_starved or (proactive_sweep_enabled and no_open_position_gate))


        if should_attempt_conversion:
            conversion_portfolio_heat = portfolio.exposure() / max(portfolio.current_equity, 1.0)
            live_convert_allowed, live_convert_guard_reason = runtime_guard.can_place_live_order(
                runtime_cfg,
                realized_pnl_total=float(portfolio.realized_pnl_total),
                portfolio_heat=float(conversion_portfolio_heat),
                open_positions=int(loop_open_positions),
            )
            strict_live_only = bool(runtime_cfg.get('strict_live_only', False))
            if strict_live_only and not live_convert_allowed:
                event_logger.emit(
                    "collateral_conversion_skipped",
                    loop_count,
                    reason_code="strict_live_convert_block",
                )
                print("  ⛔ Strict live-only: collateral conversion skipped (live convert not allowed)")
                should_attempt_conversion = False

            sweep_candidates: List[Dict[str, Any]] = []
            for asset_key, raw_qty in (balances or {}).items():
                try:
                    asset_qty = float(raw_qty or 0.0)
                except Exception:
                    continue
                if asset_qty <= 0:
                    continue

                symbol_key = _infer_symbol_from_asset_key(str(asset_key))
                if not symbol_key or symbol_key not in SYMBOL_REGISTRY:
                    continue

                ticker_conv = router.get_ticker(symbol_key)
                if not ticker_conv:
                    continue
                bid_px = float(ticker_conv.get('bid', 0.0) or 0.0)
                if bid_px <= 0:
                    continue

                notional_usd = asset_qty * bid_px
                if notional_usd < sweep_min_notional_usd:
                    continue

                sweep_candidates.append(
                    {
                        'asset_key': str(asset_key),
                        'symbol': str(symbol_key),
                        'asset_qty': float(asset_qty),
                        'bid': float(bid_px),
                        'notional_usd': float(notional_usd),
                    }
                )

            sweep_candidates.sort(key=lambda item: float(item.get('notional_usd', 0.0) or 0.0), reverse=True)
            converted_count = 0

            for candidate in sweep_candidates[:max(1, sweep_max_assets_per_loop)]:
                symbol_key = str(candidate.get('symbol', '') or '')
                cfg_conv = SYMBOL_REGISTRY.get(symbol_key)
                if not cfg_conv:
                    continue

                asset_qty = float(candidate.get('asset_qty', 0.0) or 0.0)
                bid_px = float(candidate.get('bid', 0.0) or 0.0)
                min_order_qty = float(cfg_conv.get('min_order', 0.0) or 0.0)

                if sweep_full_balance:
                    sell_qty = max(0.0, asset_qty - sweep_reserve_asset_qty)
                else:
                    sell_qty = asset_qty * convert_fraction
                    sell_qty = min(sell_qty, max(0.0, asset_qty - sweep_reserve_asset_qty))

                if sell_qty < min_order_qty:
                    continue
                if (sell_qty * bid_px) < sweep_min_notional_usd:
                    continue

                print(f"  💱 Auto-sweeping collateral: {candidate.get('asset_key')} -> USD | Qty: {sell_qty:.8f}")

                if strict_live_only and (not live_convert_allowed):
                    event_logger.emit(
                        "collateral_conversion_skipped",
                        loop_count,
                        symbol=symbol_key,
                        reason_code="strict_live_convert_block",
                        context={"asset_key": str(candidate.get('asset_key'))},
                    )
                    continue

                if live_convert_allowed:
                    conv_order = router.place_order(
                        symbol=symbol_key,
                        side='sell',
                        size=sell_qty,
                        limit_price=bid_px,
                        leverage=1.0,
                        preferred_exchange='kraken',
                        guard_context={
                            'preflight_authorized': bool(live_convert_allowed),
                            'runtime': runtime_cfg,
                            'realized_pnl_total': float(portfolio.realized_pnl_total),
                            'portfolio_heat': float(conversion_portfolio_heat),
                            'open_positions': int(loop_open_positions),
                        },
                    )
                    conv_mode = 'LIVE'
                else:
                    conv_order = {
                        'txid': f"PAPER-CONVERT-{int(time.time() * 1000)}",
                        'status': 'PAPER_CONVERTED',
                    }
                    conv_mode = 'PAPER'

                if strict_live_only and conv_mode == 'PAPER':
                    event_logger.emit(
                        "paper_mode_violation",
                        loop_count,
                        symbol=symbol_key,
                        reason_code="strict_live_conversion_paper_fallback",
                        context={"asset_key": str(candidate.get('asset_key'))},
                    )
                    audit_chain.append(
                        "paper_mode_violation",
                        {
                            "loop": loop_count,
                            "symbol": symbol_key,
                            "scope": "collateral_conversion",
                            "asset_key": str(candidate.get('asset_key')),
                        },
                        timestamp.isoformat(),
                    )
                    print("  ⛔ Strict live-only violation detected (conversion paper fallback). Blocking loop")
                    time.sleep(0.2)
                    continue

                if conv_order.get('error'):
                    print(f"  ⚠ Collateral conversion failed for {candidate.get('asset_key')}: {conv_order.get('error')}")
                    event_logger.emit(
                        "collateral_conversion_failed",
                        loop_count,
                        symbol=symbol_key,
                        reason_code="convert_failed",
                        context={"asset_key": str(candidate.get('asset_key')), "error": str(conv_order.get('error'))[:160]},
                    )
                    continue

                est_usd = float(sell_qty) * float(bid_px) * 0.99
                usd_balance += est_usd
                last_positive_usd_balance = max(last_positive_usd_balance, usd_balance)
                converted_count += 1

                print(f"  ✅ Collateral converted ({conv_mode}) | Est. USD added: ${est_usd:.2f}")
                event_logger.emit(
                    "collateral_converted",
                    loop_count,
                    symbol=symbol_key,
                    reason_code=f"mode_{conv_mode.lower()}",
                    txid=str(conv_order.get('txid', 'unknown')),
                    context={
                        "asset_key": str(candidate.get('asset_key')),
                        "qty": float(sell_qty),
                        "est_usd": float(est_usd),
                    },
                )
                audit_chain.append(
                    "collateral_converted",
                    {
                        "loop": loop_count,
                        "asset_key": str(candidate.get('asset_key')),
                        "symbol": symbol_key,
                        "qty": float(sell_qty),
                        "est_usd": float(est_usd),
                        "mode": conv_mode,
                        "txid": str(conv_order.get('txid', 'unknown')),
                    },
                    timestamp.isoformat(),
                )

            if converted_count > 0:
                last_collateral_convert_ts = time.time()
                print(f"  💵 Updated USD Balance (estimated): ${usd_balance:.2f}")
                effective_usd_balance = max(effective_usd_balance, usd_balance)

                settle_sec = float(runtime_cfg.get('post_conversion_settle_sec', 1.2) or 1.2)
                settle_retries = int(runtime_cfg.get('post_conversion_balance_retries', 2) or 2)
                refreshed_balance = None

                for _ in range(max(1, settle_retries)):
                    if settle_sec > 0:
                        time.sleep(settle_sec)
                    polled_after_convert = router.get_balance()
                    if polled_after_convert:
                        refreshed_balance = polled_after_convert
                        break

                if refreshed_balance:
                    last_balance_snapshot = refreshed_balance
                    last_balance_fetch_ts = time.time()
                    balances = refreshed_balance
                    refreshed_scan = _resolve_usd_buckets_from_balances(refreshed_balance)
                    refreshed_usd = float(refreshed_scan.get('max_usd', 0.0) or 0.0)
                    if refreshed_usd > 0:
                        usd_balance = refreshed_usd
                        last_positive_usd_balance = refreshed_usd
                    effective_usd_balance = max(effective_usd_balance, usd_balance)
                    print(f"  🔄 Post-conversion cash refresh: ${usd_balance:.2f}")

        # Skip symbols that are not executable with current buying power.
        max_feasible_order_usd = _estimate_max_feasible_notional(runtime_cfg, usd_balance, effective_usd_balance, futures_mode)
        fill_guard = _resolve_pair_fillability_bounds(runtime_cfg, config, float(current_price))
        min_notional_required_usd = float(fill_guard.get('required_min_notional_usd', 0.0) or 0.0)
        if max_feasible_order_usd < min_notional_required_usd:
            print(
                f"  ⚠ Unfillable now: needs >= ${min_notional_required_usd:.2f} notional "
                f"(max feasible ${max_feasible_order_usd:.2f})"
            )
            min_cd = float(runtime_cfg.get('min_order_cooldown_sec', 60) or 60)
            symbol_cooldown_until[symbol.upper()] = time.time() + min_cd
            time.sleep(0.1)
            continue
        
        # Create gate input from engine decision
        spread_bps = ((ask - bid) / max(current_price, 1e-9)) * 10000.0
        engine_conf = float(engine_decision.get('confidence', 0.0) or 0.0)
        engine_edge = float(engine_decision.get('edge_bps', 0.0) or 0.0)
        engine_direction = str(engine_decision.get('direction', 'long') or 'long').strip().lower()
        if engine_direction not in ('long', 'short'):
            engine_direction = 'long'
        edge_norm = min(max(engine_edge / 25.0, 0.0), 1.0)
        alignment_score = min(max(0.35 + 0.55 * engine_conf + 0.10 * edge_norm, 0.0), 1.0)
        cross_confirm_score = min(max(0.30 + 0.50 * engine_conf + 0.20 * edge_norm, 0.0), 1.0)

        gate_input = GateInput(
            regime=engine_decision['regime'],
            regime_confidence=engine_conf,
            alignment_score=alignment_score,
            liquidity_score=max(0.30, 1.0 - min(spread_bps / 40.0, 0.60)),
            signal_decay_score=min(0.45, max(0.05, spread_bps / 100.0)),
            cross_confirm_score=cross_confirm_score,
            expected_edge_bps=engine_edge,
            direction_hint=1.0 if engine_direction == 'long' else 0.0,
            volatility_pct=max(0.05, min(abs((ask - bid) / max(current_price, 1e-9)) * 100.0, 8.0)),
            correlation_to_portfolio=min(portfolio.exposure() / max(portfolio.current_equity, 1.0), 1.0),
            market_regime="normal",
            sector_heat=min(len(portfolio.get_open_positions()) / max(float(runtime_cfg.get('max_open_positions', 5) or 5), 1.0), 1.0),
            historical_win_rate=(portfolio.win_rate() / 100.0) if portfolio.total_trades >= 20 else 0.5,
            monte_carlo_edge=0.0,
            live_data_freshness=0.95,
            # --- Orderbook features ---
            orderbook_spread_bps=spread_bps,
            orderbook_depth_usd=float(engine_decision.get('orderbook_depth_usd', 0.0)),
            orderbook_imbalance=float(engine_decision.get('orderbook_imbalance', 0.0)),
            # --- On-chain features ---
            onchain_tx_volume_usd=float(engine_decision.get('onchain_tx_volume_usd', 0.0)),
            onchain_gas_fee_usd=float(engine_decision.get('onchain_gas_fee_usd', 0.0)),
            onchain_whale_tx_count=int(engine_decision.get('onchain_whale_tx_count', 0)),
            onchain_block_height=int(engine_decision.get('onchain_block_height', 0)),
            onchain_data_freshness=float(engine_decision.get('onchain_data_freshness', 1.0)),
        )

        shadow_snapshot = shadow_intelligence.evaluate(loop_count, symbol, engine_decision, runtime_cfg)
        if bool(shadow_snapshot.get('enabled', False)):
            event_logger.emit(
                "shadow_intelligence",
                loop_count,
                symbol=symbol,
                reason_code="shadow_signal",
                context={
                    "shadow_edge_bps": float(shadow_snapshot.get('edge_bps', 0.0) or 0.0),
                    "shadow_confidence": float(shadow_snapshot.get('confidence', 0.0) or 0.0),
                    "shadow_arch_regime": str(shadow_snapshot.get('arch_regime', '') or ''),
                    "shadow_river_edge_zscore": float(shadow_snapshot.get('river_edge_zscore', 0.0) or 0.0),
                },
            )
        
        # Get signal gate decision
        gate_start = time.time()
        recent_closes = engine_decision.get('recent_closes', [])
        mc_series = pd.Series(recent_closes) if isinstance(recent_closes, list) and len(recent_closes) >= 100 else None
        gate_decision = signal_gate.decide(gate_input, price_series=mc_series)
        gate_latency_ms = (time.time() - gate_start) * 1000.0
        
        print(f"  Gate Score: {gate_decision.composite_score:.3f} | Armed: {gate_decision.armed} | Latency: {gate_latency_ms:.1f}ms")
        _persist_live_engine_heartbeat(
            loop_count,
            runtime_cfg,
            portfolio,
            active_profile,
            status='gated',
            reason='gate_evaluated',
            symbol=symbol,
            engine_decision=engine_decision,
            selection_meta=selection_meta,
            gate_decision=gate_decision,
            ticker=ticker,
            usd_balance=usd_balance,
            extra={'shadow_intelligence': dict(shadow_snapshot)},
        )

        gate_override_enabled = bool(runtime_cfg.get('gate_override_enabled', True))
        should_override = False
        if not gate_decision.armed:
            reasons = list(gate_decision.reason_codes or [])
            soft_blocks = {
                'alignment_too_low',
                'regime_conf_too_low',
                'edge_too_small',
                'monte_carlo_edge_insufficient',
            }
            reason_set = set(reasons)
            if (
                gate_override_enabled
                and len(reason_set) > 0
                and reason_set.issubset(soft_blocks)
                and float(engine_decision.get('confidence', 0.0) or 0.0) >= float(runtime_cfg.get('gate_override_min_confidence', 0.60) or 0.60)
                and float(engine_decision.get('edge_bps', 0.0) or 0.0) >= float(runtime_cfg.get('gate_override_min_edge_bps', 12.0) or 12.0)
            ):
                should_override = True
                print(f"  ⚠ Gate override active for soft blocks: {','.join(reasons)}")
                audit_chain.append(
                    "gate_override",
                    {
                        "loop": loop_count,
                        "symbol": symbol,
                        "reasons": reasons,
                        "score": float(gate_decision.composite_score),
                        "engine_confidence": float(engine_decision.get('confidence', 0.0) or 0.0),
                        "engine_edge_bps": float(engine_decision.get('edge_bps', 0.0) or 0.0),
                    },
                    timestamp.isoformat()
                )

        if not gate_decision.armed and not should_override:
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='blocked',
                reason=str(gate_decision.reason_codes[0] if gate_decision.reason_codes else 'gate_blocked'),
                symbol=symbol,
                engine_decision=engine_decision,
                selection_meta=selection_meta,
                gate_decision=gate_decision,
                ticker=ticker,
                usd_balance=usd_balance,
            )
            print(f"  ✗ Blocked: {gate_decision.reason_codes[0]}")
            audit_chain.append(
                "gate_blocked",
                {
                    "loop": loop_count,
                    "symbol": symbol,
                    "reason": gate_decision.reason_codes[0],
                    "score": float(gate_decision.composite_score)
                },
                timestamp.isoformat()
            )
            time.sleep(0.5)
            continue

        min_gate_score_for_entry = float(runtime_cfg.get('min_gate_score_for_entry', 0.90) or 0.90)
        if float(gate_decision.composite_score) < min_gate_score_for_entry:
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='blocked',
                reason='gate_score_below_minimum',
                symbol=symbol,
                engine_decision=engine_decision,
                selection_meta=selection_meta,
                gate_decision=gate_decision,
                ticker=ticker,
                usd_balance=usd_balance,
                extra={'min_gate_score_for_entry': float(min_gate_score_for_entry)},
            )
            event_logger.emit(
                "gate_score_blocked",
                loop_count,
                symbol=symbol,
                reason_code="gate_score_below_minimum",
                context={
                    "gate_score": float(gate_decision.composite_score),
                    "min_gate_score_for_entry": float(min_gate_score_for_entry),
                },
            )
            print(
                f"  ✗ Gate score block: score={float(gate_decision.composite_score):.3f} "
                f"< min={float(min_gate_score_for_entry):.3f}"
            )
            time.sleep(0.2)
            continue

        _taker_fee_pct = float(runtime_cfg.get('kraken_taker_fee_pct', 0.0026) or 0.0026)
        _maker_fee_pct = float(runtime_cfg.get('kraken_maker_fee_pct', 0.0016) or 0.0016)
        _maker_first_gate = bool(runtime_cfg.get('maker_first_enabled', True))
        # When maker-first is on, best-case entry = maker fee; exit still taker (market exit)
        # fee_bps_round_trip is used for gate calculation (be conservative = maker entry + taker exit)
        _entry_fee_pct_gate = _maker_fee_pct if _maker_first_gate else _taker_fee_pct
        fee_bps_round_trip = (_entry_fee_pct_gate + _taker_fee_pct) * 10000.0
        fee_coverage_multiplier = float(runtime_cfg.get('edge_fee_coverage_multiplier', 1.15) or 1.15)
        minimum_expected_net_edge_bps = float(runtime_cfg.get('min_expected_net_edge_bps', 65.0) or 65.0)

        adaptive_enabled = bool(runtime_cfg.get('adaptive_entry_gate_enabled', True))
        adaptive_gate_min_bps = float(runtime_cfg.get('adaptive_entry_gate_min_bps', 42.0) or 42.0)
        adaptive_gate_max_bps = float(runtime_cfg.get('adaptive_entry_gate_max_bps', 120.0) or 120.0)
        adaptive_relax_step_bps = float(runtime_cfg.get('adaptive_entry_gate_relax_step_bps', 1.5) or 1.5)
        adaptive_tighten_step_bps = float(runtime_cfg.get('adaptive_entry_gate_tighten_step_bps', 3.0) or 3.0)
        adaptive_starvation_sec = float(runtime_cfg.get('adaptive_entry_gate_starvation_sec', 45.0) or 45.0)
        adaptive_adjust_cooldown_sec = float(runtime_cfg.get('adaptive_entry_gate_adjust_cooldown_sec', 20.0) or 20.0)
        adaptive_recent_trades = int(runtime_cfg.get('adaptive_entry_gate_recent_trades', 8) or 8)
        adaptive_min_win_rate_pct = float(runtime_cfg.get('adaptive_entry_gate_min_win_rate_pct', 35.0) or 35.0)
        adaptive_min_avg_net_pnl_usd = float(runtime_cfg.get('adaptive_entry_gate_min_avg_net_pnl_usd', 0.0) or 0.0)

        if adaptive_enabled:
            adaptive_gate_max_bps = max(adaptive_gate_min_bps, adaptive_gate_max_bps)
            adaptive_min_expected_edge_bps = max(adaptive_gate_min_bps, min(adaptive_gate_max_bps, adaptive_min_expected_edge_bps))

            recent_closed_rows: List[Dict[str, Any]] = []
            for row in reversed(trade_log):
                if str(row.get('status', '')).upper() != 'CLOSED':
                    continue
                recent_closed_rows.append(row)
                if len(recent_closed_rows) >= adaptive_recent_trades:
                    break

            now_gate_ts = time.time()
            can_adjust_now = (now_gate_ts - adaptive_gate_last_update_ts) >= adaptive_adjust_cooldown_sec
            if can_adjust_now:
                new_adaptive_edge = float(adaptive_min_expected_edge_bps)
                current_closed_count = len([r for r in trade_log if str(r.get('status', '')).upper() == 'CLOSED'])
                saw_new_closed_outcome = current_closed_count > adaptive_last_seen_closed_count

                if saw_new_closed_outcome and len(recent_closed_rows) >= max(3, int(adaptive_recent_trades * 0.5)):
                    net_samples = [float(r.get('net_pnl', 0.0) or 0.0) for r in recent_closed_rows]
                    avg_net = sum(net_samples) / max(1, len(net_samples))
                    win_rate_pct = (sum(1 for v in net_samples if v > 0) / max(1, len(net_samples))) * 100.0
                    if (avg_net < adaptive_min_avg_net_pnl_usd) or (win_rate_pct < adaptive_min_win_rate_pct):
                        new_adaptive_edge = min(adaptive_gate_max_bps, new_adaptive_edge + adaptive_tighten_step_bps)
                    elif (avg_net > adaptive_min_avg_net_pnl_usd) and (win_rate_pct >= (adaptive_min_win_rate_pct + 10.0)):
                        new_adaptive_edge = max(adaptive_gate_min_bps, new_adaptive_edge - adaptive_relax_step_bps)

                if (now_gate_ts - last_successful_order_ts) >= adaptive_starvation_sec:
                    new_adaptive_edge = max(adaptive_gate_min_bps, new_adaptive_edge - adaptive_relax_step_bps)

                if abs(new_adaptive_edge - adaptive_min_expected_edge_bps) >= 0.01:
                    adaptive_min_expected_edge_bps = float(new_adaptive_edge)
                    adaptive_gate_last_update_ts = now_gate_ts
                    event_logger.emit(
                        "adaptive_edge_gate_adjusted",
                        loop_count,
                        symbol=symbol,
                        reason_code="adaptive_gate_update",
                        context={
                            "adaptive_min_expected_edge_bps": float(round(adaptive_min_expected_edge_bps, 4)),
                            "adaptive_gate_min_bps": float(adaptive_gate_min_bps),
                            "adaptive_gate_max_bps": float(adaptive_gate_max_bps),
                            "seconds_since_last_fill": float(round(now_gate_ts - last_successful_order_ts, 3)),
                            "base_min_expected_net_edge_bps": float(minimum_expected_net_edge_bps),
                            "saw_new_closed_outcome": bool(saw_new_closed_outcome),
                        },
                    )
                    print(f"  ⚙ Adaptive edge gate adjusted: {adaptive_min_expected_edge_bps:.2f}bps")

                adaptive_last_seen_closed_count = current_closed_count

            minimum_expected_net_edge_bps = float(adaptive_min_expected_edge_bps)
        required_edge_bps = max(minimum_expected_net_edge_bps, fee_bps_round_trip * fee_coverage_multiplier)
        if float(engine_edge) < float(required_edge_bps):
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='blocked',
                reason='expected_edge_below_fee_gate',
                symbol=symbol,
                engine_decision=engine_decision,
                selection_meta=selection_meta,
                gate_decision=gate_decision,
                ticker=ticker,
                usd_balance=usd_balance,
                extra={
                    'required_edge_bps': float(round(required_edge_bps, 3)),
                    'fee_bps_round_trip': float(round(fee_bps_round_trip, 3)),
                },
            )
            event_logger.emit(
                "edge_fee_blocked",
                loop_count,
                symbol=symbol,
                reason_code="expected_edge_below_fee_gate",
                context={
                    "engine_edge_bps": float(engine_edge),
                    "required_edge_bps": float(round(required_edge_bps, 3)),
                    "fee_bps_round_trip": float(round(fee_bps_round_trip, 3)),
                    "fee_coverage_multiplier": float(fee_coverage_multiplier),
                },
            )
            print(
                f"  ✗ Edge/Fee block: edge={float(engine_edge):.2f}bps < "
                f"required={float(required_edge_bps):.2f}bps (fees≈{float(fee_bps_round_trip):.2f}bps)"
            )
            symbol_cooldown_until[symbol.upper()] = time.time() + 5.0
            time.sleep(0.2)
            continue
        
        # Check liquidity
        liq_start = time.time()
        liq_decision = liquidity_guard.assess(
            LiquiditySnapshot(
                bid=bid,
                ask=ask,
                bid_size=1.0,
                ask_size=1.0,
                est_sweep_cost_bps=5.0,
                quote_update_rate=2.0
            )
        )
        liq_latency_ms = (time.time() - liq_start) * 1000.0
        
        if not liq_decision.pass_trade:
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='blocked',
                reason='liquidity_blocked',
                symbol=symbol,
                engine_decision=engine_decision,
                selection_meta=selection_meta,
                gate_decision=gate_decision,
                ticker=ticker,
                usd_balance=usd_balance,
                extra={'liquidity_reasons': list(liq_decision.reasons or [])},
            )
            event_logger.emit("liquidity_blocked", loop_count, symbol=symbol, 
                            reason_code="liquidity", latency_ms=liq_latency_ms)
            print(f"  ✗ Liquidity blocked: {','.join(liq_decision.reasons) if liq_decision.reasons else 'low_score'}")
            time.sleep(0.5)
            continue
        
        event_logger.emit("liquidity_passed", loop_count, symbol=symbol, latency_ms=liq_latency_ms)
        
        # Check risk
        risk_start = time.time()
        risk_allowed, risk_reasons = risk_kernel.allow(
            RiskState(
                day_pnl_usd=portfolio.realized_pnl_total,
                open_risk_usd=portfolio.exposure(),
                portfolio_heat=portfolio.exposure() / max(portfolio.current_equity, 1),
                symbol_cooldown_active=False,
                open_positions=len(portfolio.get_open_positions()),
                max_open_positions=int(runtime_cfg.get('max_open_positions', 5) or 5),
                live_mode=str(runtime_cfg.get('mode', 'paper')).lower() == 'live',
                kill_switch=bool(runtime_cfg.get('kill_switch', False))
            )
        )
        risk_latency_ms = (time.time() - risk_start) * 1000.0
        
        if not risk_allowed:
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='blocked',
                reason='risk_violation',
                symbol=symbol,
                engine_decision=engine_decision,
                selection_meta=selection_meta,
                gate_decision=gate_decision,
                ticker=ticker,
                usd_balance=usd_balance,
                extra={'risk_reasons': list(risk_reasons or [])},
            )
            event_logger.emit("risk_blocked", loop_count, symbol=symbol, 
                            reason_code="risk_violation", latency_ms=risk_latency_ms)
            print(f"  🛑 Risk blocked")
            audit_chain.append(
                "risk_blocked",
                {
                    "loop": loop_count,
                    "symbol": symbol,
                    "reason_codes": list(risk_reasons or []),
                    "mode": str(runtime_cfg.get('mode', 'paper')),
                    "kill_switch": bool(runtime_cfg.get('kill_switch', False))
                },
                timestamp.isoformat()
            )
            time.sleep(0.5)
            continue
        
        # Calculate position size using reserve, risk fraction, and streak-based compounding.
        pyramid_targets = [100, 100, 200, 400, 800, 1600, 3200, 6400, 12800]
        target_capital = pyramid_targets[min(pyramid_level - 1, len(pyramid_targets) - 1)]
        
        max_position_usd = float(runtime_cfg.get('max_position_usd', 50.0) or 50.0)
        min_position_usd = float(runtime_cfg.get('min_position_usd', 5.0) or 5.0)
        reserve_usd = float(runtime_cfg.get('reserve_usd', 15.0) or 15.0)
        base_risk_fraction = float(runtime_cfg.get('base_risk_fraction', 0.20) or 0.20)
        profit_lock_state = _profit_lock_risk_scalar(runtime_cfg, float(portfolio.realized_pnl_total), float(realized_pnl_peak))
        risk_scalar = float(profit_lock_state.get('risk_scalar', 1.0) or 1.0)
        base_risk_fraction *= risk_scalar
        reinvestment_multiplier = float(runtime_cfg.get('pyramid_reinvestment_multiplier', 1.15) or 1.15)
        futures_mode = bool(runtime_cfg.get('futures_mode', False)) and futures_leverage_supported
        leverage_multiplier = float(runtime_cfg.get('leverage_multiplier', 1.0) or 1.0)
        leverage_multiplier = max(1.0, min(5.0, leverage_multiplier))

        if risk_scalar < 0.999:
            print(
                f"  🧷 Profit-lock active: risk x{risk_scalar:.3f} "
                f"(drawdown={float(profit_lock_state.get('drawdown_frac', 0.0) or 0.0) * 100.0:.2f}%)"
            )

        # Auto-release reserve when capital is tiny so engine can keep compounding.
        if usd_balance <= (reserve_usd + min_position_usd):
            reserve_usd = 0.0

        # KRAKEN FEE HARDENING: Reserve adequate collateral for entry (2%) + exit (2%) + slippage (1%) = 5% minimum
        allocatable_usd = max(0.0, effective_usd_balance - reserve_usd)
        kraken_fee_pct = float(runtime_cfg.get('kraken_taker_fee_pct', 0.0026) or 0.0026)
        round_trip_fee_reserve = (kraken_fee_pct * 2.0) + 0.01  # 2% entry + 2% exit + 1% slippage = 5%
        fee_reserved = allocatable_usd * round_trip_fee_reserve
        fee_cushion_allocatable = allocatable_usd - fee_reserved  # Allocate only what remains after fee reserve
        win_streak_cap = float(runtime_cfg.get('profit_protect_win_streak_cap', 1.35) or 1.35)
        win_boost = min(1.0 + (0.06 * consecutive_wins), max(1.0, win_streak_cap))
        if bool(runtime_cfg.get('profit_protect_dynamic_enabled', True)):
            loss_trigger = int(runtime_cfg.get('profit_protect_loss_streak_trigger', 2) or 2)
            loss_floor = float(runtime_cfg.get('profit_protect_loss_streak_floor', 0.35) or 0.35)
            dd_floor = float(runtime_cfg.get('profit_protect_drawdown_floor', 0.45) or 0.45)
            if consecutive_losses < loss_trigger:
                loss_streak_scale = 1.0
            else:
                loss_streak_scale = max(loss_floor, 1.0 - (0.18 * float(consecutive_losses - loss_trigger + 1)))
            drawdown_frac = abs(float(portfolio.max_drawdown or 0.0))
            drawdown_scale = max(dd_floor, 1.0 - min(0.55, drawdown_frac * 2.5))
            loss_throttle = max(0.15, min(loss_streak_scale, drawdown_scale))
        else:
            loss_throttle = 0.50 if consecutive_losses >= 3 else 1.00
        leverage_notional = leverage_multiplier if futures_mode else 1.0
        target_size = fee_cushion_allocatable * base_risk_fraction * reinvestment_multiplier * win_boost * loss_throttle * leverage_notional
        position_size_usd = min(target_size, max_position_usd * leverage_notional, fee_cushion_allocatable * leverage_notional)
        position_size_usd *= max(0.25, min(1.0, float(insufficient_funds_size_scale)))
        position_size_usd = min(position_size_usd, max_feasible_order_usd)

        size_adjusted_for_fillability = False
        if position_size_usd < min_notional_required_usd <= max_feasible_order_usd:
            position_size_usd = min_notional_required_usd
            size_adjusted_for_fillability = True
        
        if position_size_usd < min_position_usd:
            print(f"  ⚠ Position size too small (${position_size_usd:.2f}); min required ${min_position_usd:.2f}")
            time.sleep(0.2)
            continue
        
        # KRAKEN FEE HARDENING: Track fees before order placement
        entry_fee_usd = position_size_usd * kraken_fee_pct
        exit_fee_usd = position_size_usd * kraken_fee_pct
        round_trip_fee_usd = entry_fee_usd + exit_fee_usd
        net_proceeds_after_fees = position_size_usd - round_trip_fee_usd
        
        # Convert to asset quantity
        qty = position_size_usd / current_price
        
        required_min_qty = float(fill_guard.get('required_min_qty', 0.0) or 0.0)
        if qty < required_min_qty:
            print(f"  ⚠ Below guarded minimum order ({qty:.8f} < {required_min_qty:.8f})")
            min_cd = float(runtime_cfg.get('min_order_cooldown_sec', 60) or 60)
            symbol_cooldown_until[symbol.upper()] = time.time() + min_cd
            time.sleep(0.1)
            continue
        
        # Place order
        trade_direction = gate_decision.direction if gate_decision.direction in ('long', 'short') else str(engine_decision.get('direction', 'long'))
        side = 'buy' if trade_direction == 'long' else 'sell'

        available_symbol_qty = 0.0
        for asset_key, raw_qty in (balances or {}).items():
            inferred_symbol = _infer_symbol_from_asset_key(str(asset_key))
            if inferred_symbol != symbol.upper():
                continue
            try:
                available_symbol_qty += float(raw_qty or 0.0)
            except Exception:
                continue

        if not futures_mode and side == 'sell':
            if available_symbol_qty <= 0:
                print(
                    f"  ↪ Spot cash account has no {symbol.upper()} inventory; "
                    f"coercing short signal to BUY so we stop sending unsupported sells"
                )
                event_logger.emit(
                    "spot_short_coerced_to_buy",
                    loop_count,
                    symbol=symbol,
                    reason_code="no_inventory_for_spot_sell",
                    context={
                        "requested_direction": str(trade_direction),
                        "available_symbol_qty": float(available_symbol_qty),
                    },
                )
                trade_direction = 'long'
                side = 'buy'
            elif qty > available_symbol_qty:
                capped_qty = max(0.0, float(available_symbol_qty))
                print(
                    f"  ↪ Spot sell capped by inventory: requested {qty:.8f} {symbol.upper()} "
                    f"but only {available_symbol_qty:.8f} available"
                )
                event_logger.emit(
                    "spot_sell_qty_capped",
                    loop_count,
                    symbol=symbol,
                    reason_code="inventory_cap",
                    context={
                        "requested_qty": float(qty),
                        "available_symbol_qty": float(available_symbol_qty),
                    },
                )
                qty = capped_qty
                position_size_usd = qty * current_price
                entry_fee_usd = position_size_usd * kraken_fee_pct
                exit_fee_usd = position_size_usd * kraken_fee_pct
                round_trip_fee_usd = entry_fee_usd + exit_fee_usd
                net_proceeds_after_fees = position_size_usd - round_trip_fee_usd
                if qty < required_min_qty or qty <= 0:
                    print(f"  ⚠ Inventory-capped sell is now below minimum tradable size for {symbol.upper()}")
                    min_cd = float(runtime_cfg.get('min_order_cooldown_sec', 60) or 60)
                    symbol_cooldown_until[symbol.upper()] = time.time() + min_cd
                    time.sleep(0.1)
                    continue

        reentry_guard = _micro_reentry_guard(runtime_cfg, symbol.upper(), usd_balance, time.time(), symbol_entry_history)
        if not bool(reentry_guard.get('allowed', False)):
            reason = str(reentry_guard.get('reason', 'micro_reentry_blocked'))
            remaining = float(reentry_guard.get('cooldown_remaining_sec', 0.0) or 0.0)
            print(
                f"  ⚠ Re-entry governor blocked: {reason} "
                f"| cooldown={remaining:.1f}s "
                f"| entries_last_hour={int(reentry_guard.get('entries_last_hour', 0) or 0)}"
            )
            event_logger.emit(
                "micro_reentry_blocked",
                loop_count,
                symbol=symbol,
                reason_code=reason,
                latency_ms=0.0,
                context={
                    "cooldown_remaining_sec": float(remaining),
                    "entries_last_hour": int(reentry_guard.get('entries_last_hour', 0) or 0),
                    "max_per_hour": int(reentry_guard.get('max_per_hour', 0) or 0),
                    "micro_scope": bool(reentry_guard.get('micro_scope', False)),
                },
            )
            symbol_cooldown_until[symbol.upper()] = time.time() + max(0.25, min(remaining, 5.0))
            time.sleep(0.1)
            continue
        
        print(f"\n  🎯 PLACING ORDER:")
        print(f"     Symbol: {symbol.upper()}")
        print(f"     Side: {side.upper()}")
        print(f"     Qty: {qty:.8f}")
        print(f"     Price: ${current_price:.4f}")
        print(f"     Size: ${position_size_usd:.2f}")
        print(
            f"     💰 Kraken Fees: Entry ${entry_fee_usd:.4f} + Exit ${exit_fee_usd:.4f} = "
            f"${round_trip_fee_usd:.4f} ({(kraken_fee_pct * 2.0) * 100.0:.2f}% round-trip)"
        )
        print(f"     📊 Net Proceeds After Fees: ${net_proceeds_after_fees:.4f}")
        if size_adjusted_for_fillability:
            print(f"     Fill Guard: raised to ${min_notional_required_usd:.2f} min notional")
        if futures_mode and leverage_multiplier > 1.0:
            est_margin = position_size_usd / leverage_multiplier
            print(f"     Leverage: {leverage_multiplier:.1f}x | Est. Margin: ${est_margin:.2f}")

        portfolio_heat = portfolio.exposure() / max(portfolio.current_equity, 1.0)
        strict_live_only = bool(runtime_cfg.get('strict_live_only', False))
        live_mode_enabled = str(runtime_cfg.get('mode', 'paper')).lower() == 'live'
        can_live, guard_reason = runtime_guard.can_place_live_order(
            runtime_cfg,
            realized_pnl_total=float(portfolio.realized_pnl_total),
            portfolio_heat=float(portfolio_heat),
            open_positions=len(portfolio.get_open_positions())
        )

        if strict_live_only and live_mode_enabled and not can_live:
            event_logger.emit(
                "live_order_blocked",
                loop_count,
                symbol=symbol,
                reason_code="strict_live_guard_block",
                context={"guard_reason": str(guard_reason or '')[:160]},
            )
            print(f"  ⛔ Live-only mode blocked order (reason: {guard_reason})")
            time.sleep(0.1)
            continue

        # KRAKEN FEE HARDENING: Track fees before order placement
        if symbol not in fee_tracking_by_symbol:
            fee_tracking_by_symbol[symbol] = {'entry_fees': 0.0, 'exit_fees': 0.0, 'count': 0}
        route_exchange = router.get_route_exchange(symbol)
        _maker_first_enabled_disp = bool(runtime_cfg.get('maker_first_enabled', True))
        _kraken_maker_fee_disp = float(runtime_cfg.get('kraken_maker_fee_pct', 0.0016) or 0.0016)
        print(f"     Route: {route_exchange.upper()} | Maker-First: {'ON' if _maker_first_enabled_disp else 'OFF'} (maker={_kraken_maker_fee_disp*100:.2f}% vs taker={kraken_fee_pct*100:.2f}%)")
        
        order_start = time.time()
        _maker_first_enabled = bool(runtime_cfg.get('maker_first_enabled', True))
        _kraken_maker_fee_pct = float(runtime_cfg.get('kraken_maker_fee_pct', 0.0016) or 0.0016)
        if can_live:
            order = router.place_order(
                symbol=symbol,
                side=side,
                size=qty,
                limit_price=current_price,
                leverage=leverage_multiplier if futures_mode else 1.0,
                preferred_exchange=route_exchange,
                maker_first=_maker_first_enabled,
                bid=float(bid) if bid else None,
                ask=float(ask) if ask else None,
                guard_context={
                    'preflight_authorized': bool(can_live),
                    'runtime': runtime_cfg,
                    'realized_pnl_total': float(portfolio.realized_pnl_total),
                    'portfolio_heat': float(portfolio_heat),
                    'open_positions': len(portfolio.get_open_positions()),
                },
            )
            order_mode = 'LIVE'
        else:
            order = {
                'txid': f"PAPER-{int(time.time() * 1000)}",
                'order_id': 'paper-sim',
                'pair': pair,
                'side': side,
                'volume': qty,
                'price': current_price,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': 'PAPER_PLACED',
            }
            order_mode = 'PAPER'
            print(f"  ℹ Paper mode order (reason: {guard_reason})")

        if strict_live_only and order_mode == 'PAPER':
            event_logger.emit(
                "paper_mode_violation",
                loop_count,
                symbol=symbol,
                reason_code="strict_live_order_paper_fallback",
                context={"guard_reason": str(guard_reason or '')[:160]},
            )
            audit_chain.append(
                "paper_mode_violation",
                {
                    "loop": loop_count,
                    "symbol": symbol,
                    "scope": "order_placement",
                    "guard_reason": str(guard_reason or '')[:160],
                },
                timestamp.isoformat(),
            )
            print("  ⛔ Strict live-only violation detected (order paper fallback). Blocking loop")
            time.sleep(0.2)
            continue
        
        order_latency_ms = (time.time() - order_start) * 1000.0
        
        if order.get('error'):
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='blocked',
                reason='order_failed',
                symbol=symbol,
                engine_decision=engine_decision,
                selection_meta=selection_meta,
                gate_decision=gate_decision,
                ticker=ticker,
                usd_balance=usd_balance,
                extra={'order_error': str(order.get('error'))[:200]},
            )
            event_logger.emit("order_placement_failed", loop_count, symbol=symbol, 
                            reason_code="order_error", latency_ms=order_latency_ms, 
                            context={"error": str(order.get('error'))[:100]})
            print(f"  ❌ ORDER FAILED: {order['error']}")
            err_text = str(order.get('error'))
            if ("Reduce only:Non-ECP" in err_text) or ("Non-ECP" in err_text):
                futures_leverage_supported = False
                print("  ⚙ Account rejected leverage mode; auto-downgrading to spot compounding mode")
                audit_chain.append(
                    "futures_downgrade",
                    {
                        "loop": loop_count,
                        "reason": err_text,
                        "futures_leverage_supported": False,
                    },
                    timestamp.isoformat(),
                )
            if ("volume minimum not met" in err_text) or ("Invalid arguments:volume" in err_text):
                learned_min = max(float(config.get('min_order', 0.0) or 0.0), float(qty) * 1.10)
                config['min_order'] = learned_min
                print(f"  📏 Learned higher min order for {symbol.upper()}: {learned_min:.8f}")
                min_cd = float(runtime_cfg.get('min_order_cooldown_sec', 60) or 60)
                symbol_cooldown_until[symbol.upper()] = time.time() + min_cd
            elif ("Invalid permissions" in err_text) or ("EAccount:Invalid permissions" in err_text):
                permission_cd = float(runtime_cfg.get('symbol_permission_cooldown_sec', 14400) or 14400)
                symbol_cooldown_until[symbol.upper()] = time.time() + permission_cd
                print(f"  🚫 Symbol permission block for {symbol.upper()} ({permission_cd:.0f}s cooldown)")
                persisted_runtime = dict(runtime_guard.load() or {})
                live_blacklist = {str(s).strip().upper() for s in list(persisted_runtime.get('symbol_blacklist', []) or [])}
                if symbol.upper() not in live_blacklist:
                    live_blacklist.add(symbol.upper())
                    persisted_runtime['symbol_blacklist'] = sorted(list(live_blacklist))
                    try:
                        _atomic_write_json(RUNTIME_FILE, persisted_runtime, indent=2)
                        print(f"  🧱 Persisted blacklist add: {symbol.upper()}")
                    except Exception:
                        pass
                audit_chain.append(
                    "symbol_permission_blocked",
                    {
                        "loop": loop_count,
                        "symbol": symbol,
                        "cooldown_sec": float(permission_cd),
                        "reason": str(err_text)[:180],
                    },
                    timestamp.isoformat(),
                )
            elif ("Insufficient funds" in err_text) or ("Invalid nonce" in err_text):
                generic_cd = float(runtime_cfg.get('symbol_skip_cooldown_sec', 45) or 45)
                symbol_cooldown_until[symbol.upper()] = time.time() + generic_cd
                if "Insufficient funds" in err_text:
                    previous_scale = float(insufficient_funds_size_scale)
                    insufficient_funds_size_scale = max(0.25, float(insufficient_funds_size_scale) * 0.80)
                    print(
                        f"  💧 Funds backoff scale adjusted: {previous_scale:.2f} -> {insufficient_funds_size_scale:.2f}"
                    )
                    event_logger.emit(
                        "insufficient_funds_backoff",
                        loop_count,
                        symbol=symbol,
                        reason_code="insufficient_funds",
                        context={
                            "previous_scale": float(round(previous_scale, 4)),
                            "new_scale": float(round(insufficient_funds_size_scale, 4)),
                        },
                    )
                    refreshed = router.get_balance()
                    if refreshed:
                        last_balance_snapshot = refreshed
                        last_balance_fetch_ts = time.time()
            consecutive_order_failures += 1
            rolling_order_outcomes.append(0)
            audit_chain.append(
                "order_failed",
                {
                    "loop": loop_count,
                    "symbol": symbol,
                    "side": side,
                    "qty": float(qty),
                    "price": float(current_price),
                    "error": str(order.get('error'))
                },
                timestamp.isoformat()
            )

            if consecutive_order_failures >= int(runtime_cfg.get('max_consecutive_order_failures', 8) or 8):
                cooldown = float(runtime_cfg.get('order_failure_cooldown_sec', 30) or 30)
                print(f"  🧊 Failure circuit breaker engaged: sleeping {cooldown:.1f}s")
                audit_chain.append(
                    "failure_circuit_breaker",
                    {
                        "loop": loop_count,
                        "symbol": symbol,
                        "consecutive_order_failures": int(consecutive_order_failures),
                        "cooldown_sec": float(cooldown)
                    },
                    timestamp.isoformat()
                )
                time.sleep(cooldown)
                consecutive_order_failures = 0

            time.sleep(0.5)
            continue
        
        consecutive_order_failures = 0
        rolling_order_outcomes.append(1)
        # On successful order, reset scale to 1.0 immediately (no need to crawl back)
        if insufficient_funds_size_scale < 1.0:
            old_scale = insufficient_funds_size_scale
            insufficient_funds_size_scale = 1.0
            print(f"  ✨ Funds scale RESET: {old_scale:.2f} -> 1.0 (recovery on success)")
        txid = order['txid']
        _exec_mode = str(order.get('execution_mode', 'taker'))
        _maker_price_filled = order.get('maker_price')
        last_successful_order_ts = time.time()
        print(f"  ✅ ORDER PLACED!")
        print(f"     Exchange: {str(order.get('exchange', route_exchange)).upper()}")
        print(f"     TXID: {txid}")
        print(f"     ⚡ Execution: {_exec_mode.upper()}{f' @ ${_maker_price_filled:.6f} (maker bid/ask)' if _maker_price_filled else ''}")
        
        # KRAKEN FEE HARDENING: Track actual fees charged on successful order placement
        total_fees_paid_usd += entry_fee_usd
        fee_tracking_by_symbol[symbol]['entry_fees'] += entry_fee_usd
        fee_tracking_by_symbol[symbol]['count'] += 1
        print(f"  💵 Entry fee charged: ${entry_fee_usd:.4f} | Paid total: ${total_fees_paid_usd:.2f}")
        event_logger.emit(
            "kraken_entry_fee_charged",
            loop_count,
            symbol=symbol,
            reason_code="order_filled",
            context={
                "entry_fee_usd": float(entry_fee_usd),
                "position_size_usd": float(position_size_usd),
                "fee_pct": float(kraken_fee_pct * 100),
                "txid": str(txid)[:50],
                "session_total_paid_fees_usd": float(total_fees_paid_usd),
            },
        )
        
        # KRAKEN FEE HARDENING: Reserve exit fee for position closeout
        total_fees_reserved_usd += exit_fee_usd
        fee_tracking_by_symbol[symbol]['exit_fees'] += exit_fee_usd
        print(
            f"  💵 Exit fee reserved: ${exit_fee_usd:.4f} | "
            f"Reserved total: ${total_fees_reserved_usd:.2f} | Position round-trip cost: ${round_trip_fee_usd:.4f}"
        )
        event_logger.emit(
            "kraken_exit_fee_reserved",
            loop_count,
            symbol=symbol,
            reason_code="position_close_expected",
            context={
                "exit_fee_usd": float(exit_fee_usd),
                "position_size_usd": float(position_size_usd),
                "round_trip_fee_usd": float(round_trip_fee_usd),
                "fee_pct": float(kraken_fee_pct * 100),
                "net_proceeds": float(net_proceeds_after_fees),
                "session_total_paid_fees_usd": float(total_fees_paid_usd),
                "session_total_reserved_fees_usd": float(total_fees_reserved_usd),
            },
        )
        audit_chain.append(
            "order_placed",
            {
                "loop": loop_count,
                "symbol": symbol,
                "mode": order_mode,
                "exchange": str(order.get('exchange', route_exchange or 'kraken')),
                "guard_reason": guard_reason,
                "txid": txid,
                "side": side,
                "qty": float(qty),
                "price": float(current_price),
                "size_usd": float(position_size_usd),
                "execution_mode": str(order.get('execution_mode', 'taker')),
                "maker_price": float(order.get('maker_price') or current_price),
                "fill_guard": {
                    "required_min_notional_usd": float(min_notional_required_usd),
                    "required_min_qty": float(required_min_qty),
                    "base_min_notional_usd": float(fill_guard.get('base_min_notional_usd', 0.0) or 0.0),
                    "size_adjusted_for_fillability": bool(size_adjusted_for_fillability),
                },
                "micro_reentry_guard": {
                    "reason": str(reentry_guard.get('reason', 'n/a')),
                    "entries_last_hour": int(reentry_guard.get('entries_last_hour', 0) or 0),
                    "max_per_hour": int(reentry_guard.get('max_per_hour', 0) or 0),
                    "micro_scope": bool(reentry_guard.get('micro_scope', False)),
                },
                "profit_lock": {
                    "reason": str(profit_lock_state.get('reason', 'n/a')),
                    "risk_scalar": float(profit_lock_state.get('risk_scalar', 1.0) or 1.0),
                    "drawdown_frac": float(profit_lock_state.get('drawdown_frac', 0.0) or 0.0),
                },
            },
            timestamp.isoformat()
        )

        symbol_entry_history[symbol.upper()] = _prune_entry_history(
            symbol_entry_history.get(symbol.upper(), []) + [time.time()],
            time.time(),
            3600.0,
        )
        entry_timestamps.append(time.time())
        
        event_logger.emit("order_placed_success", loop_count, symbol=symbol, 
                        latency_ms=order_latency_ms, txid=txid,
                        context={"mode": order_mode, "exchange": str(order.get('exchange', route_exchange or 'kraken')), "qty": round(qty, 8), "price": round(current_price, 4)})
        
        # Record position
        position = Position(
            symbol=f"{symbol.upper()}/USD",
            side=trade_direction,
            entry_price=current_price,
            current_price=current_price,
            qty=qty,
            entry_time_utc=timestamp.isoformat(),
            flowform="fibonacci",
            algo="echo_stack",
            strategy="harmonic_blend",
            order_id=txid,
            status="OPEN"
        )
        
        portfolio.add_position(position)
        
        # Log trade
        trade_entry = {
            'timestamp': timestamp.isoformat(),
            'txid': txid,
            'exchange': str(order.get('exchange', route_exchange or 'kraken')),
            'symbol': symbol.upper(),
            'pair': pair,
            'direction': trade_direction,
            'side': side,
            'entry_price': current_price,
            'qty': qty,
            'size_usd': position_size_usd,
            'fill_guard_required_notional_usd': float(min_notional_required_usd),
            'fill_guard_required_qty': float(required_min_qty),
            'fill_guard_size_adjusted': bool(size_adjusted_for_fillability),
            'gate_score': gate_decision.composite_score,
            'urgency': gate_decision.urgency,
            'status': 'PLACED',
            'pyramid_level': pyramid_level
        }
        
        trade_log.append(trade_entry)
        
        base_hold_seconds = float(runtime_cfg.get('position_hold_seconds', 5.0) or 5.0)
        max_hold_seconds = float(runtime_cfg.get('position_max_hold_seconds', 30.0) or 30.0)
        hard_max_hold_seconds = float(runtime_cfg.get('position_hard_max_hold_seconds', 240.0) or 240.0)
        poll_seconds = float(runtime_cfg.get('position_poll_seconds', 1.0) or 1.0)
        min_hold_seconds = float(runtime_cfg.get('position_min_hold_seconds', base_hold_seconds) or base_hold_seconds)
        stop_loss_min_hold_seconds = float(runtime_cfg.get('position_stop_loss_min_hold_seconds', max(min_hold_seconds, 8.0)) or max(min_hold_seconds, 8.0))
        timeout_exit_enabled = bool(runtime_cfg.get('position_timeout_exit_enabled', True))
        timeout_grace_net_bps = float(runtime_cfg.get('position_timeout_grace_net_bps', -8.0) or -8.0)
        base_hold_seconds = max(0.1, min(120.0, base_hold_seconds))
        max_hold_seconds = max(base_hold_seconds, min(600.0, max_hold_seconds))
        hard_max_hold_seconds = max(max_hold_seconds, min(3600.0, hard_max_hold_seconds))
        poll_seconds = max(0.1, min(5.0, poll_seconds))
        min_hold_seconds = max(0.0, min(max_hold_seconds, min_hold_seconds))
        stop_loss_min_hold_seconds = max(min_hold_seconds, min(max_hold_seconds, stop_loss_min_hold_seconds))
        tp_net_bps_cfg = float(runtime_cfg.get('position_tp_net_bps', 18.0) or 18.0)
        sl_net_bps_cfg = float(runtime_cfg.get('position_sl_net_bps', 40.0) or 40.0)
        tp_volatility_multiplier = float(runtime_cfg.get('position_tp_volatility_multiplier', 0.9) or 0.9)
        sl_volatility_multiplier = float(runtime_cfg.get('position_sl_volatility_multiplier', 2.2) or 2.2)
        volatility_bps_floor = float(runtime_cfg.get('position_volatility_bps_floor', 6.0) or 6.0)
        volatility_bps_cap = float(runtime_cfg.get('position_volatility_bps_cap', 80.0) or 80.0)
        volatility_bps_cap = max(volatility_bps_floor, volatility_bps_cap)

        entry_bid = float(bid or current_price)
        entry_ask = float(ask or current_price)
        entry_mid = (entry_bid + entry_ask) / 2.0 if (entry_bid > 0 and entry_ask > 0) else float(current_price)
        entry_spread_bps = 0.0
        if entry_mid > 0:
            entry_spread_bps = abs(entry_ask - entry_bid) / entry_mid * 10000.0

        observed_volatility_bps = max(volatility_bps_floor, min(volatility_bps_cap, entry_spread_bps))
        edge_scaled_tp_bps = max(tp_net_bps_cfg, min(float(engine_edge) * 0.35, 120.0))
        dynamic_tp_net_bps = max(edge_scaled_tp_bps, min(observed_volatility_bps * tp_volatility_multiplier, 160.0))
        dynamic_sl_net_bps = max(sl_net_bps_cfg, min(observed_volatility_bps * sl_volatility_multiplier, 280.0))

        opened_at = time.time()
        close_reason = 'timeout'
        latest_ticker = None
        latest_net_pnl_pct = None

        while True:
            elapsed = time.time() - opened_at
            if elapsed < min_hold_seconds:
                time.sleep(min(poll_seconds, max(0.05, min_hold_seconds - elapsed)))
                continue

            latest_ticker = router.get_ticker(symbol)
            if latest_ticker:
                probe_price = float(latest_ticker.get('last', current_price) or current_price)
                if trade_direction == "long":
                    probe_pnl = (probe_price - current_price) * qty
                else:
                    probe_pnl = (current_price - probe_price) * qty
                # Unrealized P&L: entry fee already paid — only deduct exit fee for probe
                probe_net_pnl = float(probe_pnl) - float(exit_fee_usd)
                probe_net_pnl_pct = (probe_net_pnl / position_size_usd) * 100 if position_size_usd > 0 else 0.0
                latest_net_pnl_pct = float(probe_net_pnl_pct)
                probe_net_bps = float(probe_net_pnl_pct) * 100.0

                if current_price > 0:
                    drift_bps = abs((probe_price - current_price) / current_price) * 10000.0
                    observed_volatility_bps = max(observed_volatility_bps, min(volatility_bps_cap, drift_bps))
                    dynamic_tp_net_bps = max(edge_scaled_tp_bps, min(observed_volatility_bps * tp_volatility_multiplier, 160.0))
                    dynamic_sl_net_bps = max(sl_net_bps_cfg, min(observed_volatility_bps * sl_volatility_multiplier, 280.0))

                if probe_net_bps >= dynamic_tp_net_bps:
                    close_reason = 'take_profit'
                    break
                if probe_net_bps <= (-1.0 * dynamic_sl_net_bps):
                    if elapsed >= stop_loss_min_hold_seconds:
                        close_reason = 'stop_loss'
                        break
                    if probe_net_bps <= (-2.0 * dynamic_sl_net_bps):
                        close_reason = 'stop_loss_emergency'
                        break

            if timeout_exit_enabled and elapsed >= max_hold_seconds:
                if latest_net_pnl_pct is not None:
                    latest_net_bps = float(latest_net_pnl_pct) * 100.0
                    if latest_net_bps >= float(timeout_grace_net_bps):
                        close_reason = 'timeout_soft'
                        break
                if elapsed >= hard_max_hold_seconds:
                    close_reason = 'timeout_hard'
                    break
                time.sleep(poll_seconds)
                continue

            if (not timeout_exit_enabled) and elapsed >= max_hold_seconds:
                close_reason = 'max_hold_guard'
                break

            if elapsed >= hard_max_hold_seconds:
                close_reason = 'hard_hold_guard'
                break

            time.sleep(poll_seconds)

        new_ticker = latest_ticker or router.get_ticker(symbol)
        
        if new_ticker:
            new_price = new_ticker['last']
            
            # Calculate P&L
            if trade_direction == "long":
                pnl = (new_price - current_price) * qty
            else:
                pnl = (current_price - new_price) * qty

            net_pnl = float(pnl) - float(round_trip_fee_usd)
            pnl_pct = (pnl / position_size_usd) * 100 if position_size_usd > 0 else 0
            net_pnl_pct = (net_pnl / position_size_usd) * 100 if position_size_usd > 0 else 0
            
            print(f"\n  📊 POSITION CLOSED:")
            print(f"     Exit Price: ${new_price:.4f}")
            print(f"     P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
            print(f"     Net P&L After Fees: ${net_pnl:.2f} ({net_pnl_pct:.2f}%)")
            print(
                f"     Close Reason: {close_reason} | Held: {time.time() - opened_at:.1f}s | "
                f"TP/SL Net: +{dynamic_tp_net_bps:.1f}bps / -{dynamic_sl_net_bps:.1f}bps"
            )
            
            # Update portfolio
            portfolio.close_position(f"{symbol.upper()}/USD", new_price, datetime.now(timezone.utc).isoformat())
            
            # Update trade log
            trade_log[-1]['status'] = 'CLOSED'
            trade_log[-1]['exit_price'] = new_price
            trade_log[-1]['pnl'] = pnl
            trade_log[-1]['pnl_pct'] = pnl_pct
            trade_log[-1]['net_pnl'] = net_pnl
            trade_log[-1]['net_pnl_pct'] = net_pnl_pct
            trade_log[-1]['round_trip_fee_usd'] = float(round_trip_fee_usd)
            trade_log[-1]['close_reason'] = str(close_reason)
            trade_log[-1]['hold_seconds_actual'] = float(round(time.time() - opened_at, 3))
            trade_log[-1]['tp_net_bps'] = float(round(dynamic_tp_net_bps, 4))
            trade_log[-1]['sl_net_bps'] = float(round(dynamic_sl_net_bps, 4))
            trade_log[-1]['observed_volatility_bps'] = float(round(observed_volatility_bps, 4))
            trade_log[-1]['stop_loss_min_hold_seconds'] = float(round(stop_loss_min_hold_seconds, 4))
            trade_log[-1]['execution_mode'] = order_mode
            rolling_pnl_pct.append(float(net_pnl_pct))
            realized_pnl_peak = max(float(realized_pnl_peak), float(portfolio.realized_pnl_total))
            realized_pnl_samples.append({
                'ts': time.time(),
                'pnl': float(portfolio.realized_pnl_total),
            })
            
            # Check pyramid level
            if portfolio.realized_pnl_total >= target_capital:
                print(f"\n  🎉 PYRAMID LEVEL {pyramid_level} COMPLETE!")
                print(f"     Target: ${target_capital:.2f}")
                print(f"     Actual: ${portfolio.realized_pnl_total:.2f}")
                pyramid_level += 1
                
                # Milestone withdrawal
                payout_levels = set(runtime_cfg.get('payout_milestone_levels', [3, 5, 7, 9]) or [3, 5, 7, 9])
                payout_enabled = bool(runtime_cfg.get('payout_milestones_enabled', True))
                payout_fraction = float(runtime_cfg.get('payout_fraction', 0.5) or 0.5)
                payout_min_amount_usd = float(runtime_cfg.get('payout_min_amount_usd', 10.0) or 10.0)
                payout_destination = str(runtime_cfg.get('payout_destination', 'chime') or 'chime').strip().lower()
                payout_destination_label = str(runtime_cfg.get('payout_destination_label', 'Chime') or 'Chime').strip()
                payout_account_hint = str(runtime_cfg.get('payout_account_hint', 'primary') or 'primary').strip()

                if payout_enabled and pyramid_level in payout_levels:
                    withdrawal = max(0.0, float(portfolio.realized_pnl_total) * payout_fraction)
                    if withdrawal >= payout_min_amount_usd:
                        payout_intent = {
                            "intent_id": f"payout-{int(time.time() * 1000)}",
                            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                            "status": "PENDING",
                            "destination": payout_destination,
                            "destination_label": payout_destination_label,
                            "account_hint": payout_account_hint,
                            "amount_usd": float(round(withdrawal, 2)),
                            "trigger": {
                                "type": "pyramid_milestone",
                                "pyramid_level": int(pyramid_level),
                                "payout_fraction": float(payout_fraction),
                                "realized_pnl_total_usd": float(portfolio.realized_pnl_total),
                            },
                            "execution_note": "Queue this amount for transfer in destination app/bank rail.",
                        }
                        _append_payout_intent(payout_intent)
                        print(f"  💸 WITHDRAWAL MILESTONE: ${withdrawal:.2f} queued for {payout_destination_label}")
                        event_logger.emit(
                            "withdrawal_milestone_queued",
                            loop_count,
                            reason_code="milestone_trigger",
                            context={
                                "amount_usd": float(round(withdrawal, 2)),
                                "destination": payout_destination,
                                "account_hint": payout_account_hint,
                                "pyramid_level": int(pyramid_level),
                            },
                        )
                        audit_chain.append(
                            "withdrawal_milestone_queued",
                            {
                                "loop": loop_count,
                                "pyramid_level": int(pyramid_level),
                                "amount_usd": float(round(withdrawal, 2)),
                                "destination": payout_destination,
                                "destination_label": payout_destination_label,
                                "account_hint": payout_account_hint,
                            },
                            datetime.now(timezone.utc).isoformat(),
                        )

                        dispatch = _dispatch_payout_intent(runtime_cfg, payout_intent)
                        if bool(dispatch.get('attempted', False)):
                            status_value = 'DISPATCHED' if bool(dispatch.get('ok', False)) else 'DISPATCH_FAILED'
                            _update_payout_intent(
                                str(payout_intent.get('intent_id', '')),
                                {
                                    'status': status_value,
                                    'dispatch': {
                                        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                                        'mode': str(runtime_cfg.get('payout_dispatch_mode', 'webhook') or 'webhook'),
                                        'result': dispatch,
                                    },
                                },
                            )
                            event_logger.emit(
                                "withdrawal_dispatch_result",
                                loop_count,
                                reason_code=str(dispatch.get('reason', 'unknown')),
                                context={
                                    "intent_id": str(payout_intent.get('intent_id', '')),
                                    "ok": bool(dispatch.get('ok', False)),
                                    "destination": payout_destination,
                                    "status_code": int(dispatch.get('status_code', 0) or 0),
                                    "latency_ms": float(dispatch.get('latency_ms', 0.0) or 0.0),
                                },
                            )
                            audit_chain.append(
                                "withdrawal_dispatch_result",
                                {
                                    "loop": loop_count,
                                    "intent_id": str(payout_intent.get('intent_id', '')),
                                    "ok": bool(dispatch.get('ok', False)),
                                    "reason": str(dispatch.get('reason', 'unknown')),
                                    "destination": payout_destination,
                                    "status_code": int(dispatch.get('status_code', 0) or 0),
                                },
                                datetime.now(timezone.utc).isoformat(),
                            )
            
            # Track losses
            if pnl < 0:
                consecutive_losses += 1
                consecutive_wins = 0
            else:
                consecutive_wins += 1
                consecutive_losses = 0
            
            # Save state (atomic writes)
            _atomic_write_json(OUT / 'trade_log.json', trade_log, indent=2)
            _atomic_write_json(OUT / 'portfolio_summary.json', portfolio.get_summary(), indent=2)
            _atomic_write_json(
                ADAPTIVE_PROFILE_FILE,
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "active_profile": active_profile,
                    "rolling_sharpe": _rolling_sharpe_from_pnl_pct(list(rolling_pnl_pct)),
                    "rolling_failure_rate": _failure_rate(list(rolling_order_outcomes)),
                    "drawdown_pct": abs(float(portfolio.max_drawdown)) * 100.0,
                    "sampled_trades": len(rolling_pnl_pct),
                    "sampled_orders": len(rolling_order_outcomes),
                    "profile_presets": PROFILE_PRESETS,
                },
                indent=2,
            )
            
            print(f"  Portfolio: ${portfolio.current_equity:.2f} | Realized P&L: ${portfolio.realized_pnl_total:.2f}")
            _persist_live_engine_heartbeat(
                loop_count,
                runtime_cfg,
                portfolio,
                active_profile,
                status='position_closed',
                reason=str(close_reason),
                symbol=symbol,
                engine_decision=engine_decision,
                selection_meta=selection_meta,
                gate_decision=gate_decision,
                ticker=new_ticker,
                usd_balance=usd_balance,
                extra={
                    'net_pnl': float(net_pnl),
                    'net_pnl_pct': float(net_pnl_pct),
                    'txid': str(txid),
                },
            )
            audit_chain.append(
                "position_closed",
                {
                    "loop": loop_count,
                    "symbol": symbol,
                    "txid": txid,
                    "execution_mode": order_mode,
                    "entry_price": float(current_price),
                    "exit_price": float(new_price),
                    "qty": float(qty),
                    "pnl": float(pnl),
                    "pnl_pct": float(pnl_pct),
                    "realized_pnl_total": float(portfolio.realized_pnl_total)
                },
                datetime.now(timezone.utc).isoformat()
            )
        
        # Emit operational health metrics every loop
        _persist_operational_health(
            event_logger,
            portfolio,
            loop_count,
            rolling_pnl_pct,
            rolling_order_outcomes,
            runtime_cfg,
            runway_start_ts,
            realized_pnl_samples,
            entry_timestamps,
            shadow_snapshot,
        )
        
        if shutdown_event.is_set():
            break
        
        # Persist checkpoint every 50 loops (~100s at 2s loop_seconds)
        # Used on restart to prevent engine 'relearning' from scratch
        if loop_count % 50 == 0:
            _persist_engine_checkpoint(portfolio, runtime_cfg, loop_count)
        
        time.sleep(runtime_cfg.get('loop_seconds', 1))  # Use configured loop speed
    
    except KeyboardInterrupt:
        print("\n\n✅ EXECUTION STOPPING (graceful shutdown)...")
        event_logger.emit("shutdown", loop_count, reason_code="user_interrupt")
        shutdown_event.set()
        break
    except Exception as e:
        tb_text = traceback.format_exc()
        tb_tail = str(tb_text or '')[-2000:]
        try:
            logging.error(
                "Exception in main loop (iteration %s): %s\n%s",
                loop_count,
                str(e),
                tb_text,
            )
        except Exception:
            pass
        event_logger.emit(
            "execution_error",
            loop_count,
            reason_code=f"error_{type(e).__name__}",
            context={
                "error": str(e)[:200],
                "exception_type": type(e).__name__,
                "traceback_tail": tb_tail,
            },
        )
        print(f"\n⚠ Error: {e}")
        time.sleep(0.5)
        if shutdown_event.is_set():
            break
        continue

print("\n" + "=" * 70)
print("🏁 EXECUTION COMPLETE")
print(f"Total Trades: {len(trade_log)}")
print(f"Pyramid Level: {pyramid_level}")
print(f"Portfolio Value: ${portfolio.current_equity:.2f}")
print(f"Realized P&L: ${portfolio.realized_pnl_total:.2f}")
print(f"Total Events Logged: {sum(event_logger._event_counts.values())}")
print("=" * 70)

_release_execution_lock()

