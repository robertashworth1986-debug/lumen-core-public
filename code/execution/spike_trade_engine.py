#!/usr/bin/env python3
"""
spike_trade_engine.py
─────────────────────
Real-time spike-driven trade execution daemon.

Closes the final loop:
  symbol_watcher_fleet  →  gateway spike_alert (WebSocket push)
  →  spike_trade_engine  →  unified_trade_executor pipeline  →  fills/P&L

How it works
────────────
1. Subscribes to the gateway WebSocket (/ws/live)
2. On every spike_alert event, evaluates each confirmed real spike
3. Converts spike metadata into a synthetic alpha signal
4. Size gate, cooldown, and max-concurrent position guards
5. Writes the signal to the unified alpha feed file so the standard
   executor can also pick it up, AND fires the position directly so
   there is zero latency waiting for the next executor scan

Outputs
───────
  out/spike_trade/spike_engine_heartbeat.json   — health / last event
  out/spike_trade/spike_trade_ledger.jsonl      — spike-driven fills
  out/spike_trade/spike_engine_state.json       — current spike positions

Configuration (env vars)
────────────────────────
  SPIKE_ENGINE_MODE          paper | live          (default: paper)
  SPIKE_ENGINE_BANKROLL      starting capital       (default: 50000.0)
  SPIKE_ENGINE_RISK_PCT      % bankroll per trade   (default: 1.5)
  SPIKE_ENGINE_MAX_POSITIONS max concurrent         (default: 8)
  SPIKE_ENGINE_COOLDOWN_SEC  same-symbol cooldown   (default: 60)
  SPIKE_ENGINE_MIN_Z         min z-score to trade   (default: 2.5)
  SPIKE_ENGINE_REAL_ONLY     require spike_real     (default: true)
  SPIKE_ENGINE_GW_URL        gateway ws url         (default: ws://127.0.0.1:8787/ws/live)

Usage
─────
  python code/execution/spike_trade_engine.py
  python code/execution/spike_trade_engine.py --mode live
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import websockets  # type: ignore
    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False

try:
    import requests as _requests  # for live price fetch
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
OUT  = ROOT / "out" / "spike_trade"
OUT.mkdir(parents=True, exist_ok=True)

HEARTBEAT_FILE  = OUT / "spike_engine_heartbeat.json"
LEDGER_FILE     = OUT / "spike_trade_ledger.jsonl"
STATE_FILE      = OUT / "spike_engine_state.json"

# Also write synthetic signals here so unified_trade_executor sees them
ALPHA_INJECT_FILE = ROOT / "out" / "unified_alpha" / "spike_injected_signals.json"
ALPHA_INJECT_FILE.parent.mkdir(parents=True, exist_ok=True)

# V8 Coherence integration
COHERENCE_LATEST_FILE  = ROOT / "out" / "coherence" / "fleet_coherence_latest.json"
RISK_REGIME_FILE       = OUT / "risk_regime.json"

# EchoLock Harmonic Resonance integration
HARMONIC_LATEST_FILE   = ROOT / "out" / "harmonic"  / "resonance_latest.json"

# ─── Config ───────────────────────────────────────────────────────────────────
MODE            = os.environ.get("SPIKE_ENGINE_MODE", "paper")
BANKROLL        = float(os.environ.get("SPIKE_ENGINE_BANKROLL", "50000.0"))
RISK_PCT        = float(os.environ.get("SPIKE_ENGINE_RISK_PCT", "1.5"))
MAX_POSITIONS   = int(os.environ.get("SPIKE_ENGINE_MAX_POSITIONS", "8"))
COOLDOWN_SEC    = float(os.environ.get("SPIKE_ENGINE_COOLDOWN_SEC", "60.0"))
MIN_Z           = float(os.environ.get("SPIKE_ENGINE_MIN_Z", "2.5"))
REAL_ONLY       = os.environ.get("SPIKE_ENGINE_REAL_ONLY", "true").lower() == "true"
GW_URL          = os.environ.get("SPIKE_ENGINE_GW_URL", "ws://127.0.0.1:8787/ws/live")
KRAKEN_TICKER   = "https://api.kraken.com/0/public/Ticker"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SPIKE-ENGINE] %(levelname)s: %(message)s",
)
log = logging.getLogger("spike_engine")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> float:
    return time.time()


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _fetch_price(symbol: str, pair: str) -> Optional[float]:
    """Fetch live price from Kraken ticker for a pair."""
    if not _REQUESTS_AVAILABLE:
        return None
    try:
        r = _requests.get(KRAKEN_TICKER, params={"pair": pair}, timeout=5)
        result = r.json().get("result", {})
        for v in result.values():
            return float(v["c"][0])
    except Exception:
        return None


# ─── Risk Regime (V8 Coherence-Aware) ────────────────────────────────────────

# Regime names, in order of increasing caution:
#   NORMAL   → baseline config
#   ELEVATED → P1/P2/P4/P5 detected (soft warning)
#   GUARDED  → P3/P6 detected (data quality / drift concern)
#   CRISIS   → P7/P8 detected (burst storm / resource pressure)
#   LOCKOUT  → multiple FAIL-severity perturbations (halt new entries)

_REGIME_OVERRIDE: Dict[str, Any] = {}   # filled by _compute_regime()

@dataclass
class RiskRegime:
    name: str           # NORMAL | ELEVATED | GUARDED | CRISIS | LOCKOUT
    min_z: float        # effective minimum z-score
    max_positions: int  # effective max concurrent positions
    risk_pct: float     # effective % bankroll per trade
    cooldown_sec: float # effective cooldown between same-symbol entries
    allow_new: bool     # whether new positions are allowed at all
    reason: str         # human-readable explanation
    active_p_classes: list  # which P-classes drove this regime
    v8_grade: str       # PASS | WARN | FAIL
    omega: float
    C: float
    S: float
    E: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": _now(),
            "regime": self.name,
            "allow_new": self.allow_new,
            "effective": {
                "min_z": self.min_z,
                "max_positions": self.max_positions,
                "risk_pct": self.risk_pct,
                "cooldown_sec": self.cooldown_sec,
            },
            "reason": self.reason,
            "active_p_classes": self.active_p_classes,
            "v8": {
                "grade": self.v8_grade,
                "omega": self.omega,
                "C": self.C,
                "S": self.S,
                "E": self.E,
            },
        }


def _compute_regime() -> RiskRegime:
    """
    Read the latest V8 coherence snapshot and derive the current risk regime.

    Regime ladder (highest severity wins):
      LOCKOUT  → grade=FAIL AND ≥2 FAIL-severity perturbations
      CRISIS   → P7 (burst) or P8 (resource) detected at any severity
      GUARDED  → P3 (dropout) or P6 (drift) detected
      ELEVATED → P1/P2/P4/P5 detected at warn+
      NORMAL   → no perturbations detected
    """
    snap = _load_json(COHERENCE_LATEST_FILE, None)

    # If coherence monitor isn't running, use baseline config
    if not isinstance(snap, dict):
        return RiskRegime(
            name="NORMAL", min_z=MIN_Z, max_positions=MAX_POSITIONS,
            risk_pct=RISK_PCT, cooldown_sec=COOLDOWN_SEC, allow_new=True,
            reason="No V8 coherence data (monitor not running — baseline defaults)",
            active_p_classes=[], v8_grade="?",
            omega=0.0, C=1.0, S=1.0, E=0.0,
        )

    # Check freshness — stale coherence data → ELEVATED caution
    coherence_age = max(0.0, _ts() - COHERENCE_LATEST_FILE.stat().st_mtime)
    if coherence_age > 30.0:
        return RiskRegime(
            name="ELEVATED", min_z=MIN_Z + 0.5, max_positions=max(1, MAX_POSITIONS - 2),
            risk_pct=RISK_PCT * 0.7, cooldown_sec=COOLDOWN_SEC * 1.5, allow_new=True,
            reason=f"V8 coherence data stale ({coherence_age:.0f}s) — elevated caution",
            active_p_classes=["stale"], v8_grade="?",
            omega=0.0, C=1.0, S=1.0, E=0.0,
        )

    grade     = snap.get("overall_grade", "PASS")
    omega     = float(snap.get("omega", 0.0))
    C         = float(snap.get("C", 1.0))
    S         = float(snap.get("S", 1.0))
    E         = float(snap.get("E", 0.0))
    perts     = snap.get("perturbations", [])

    detected  = {p["class_id"] for p in perts if p.get("detected")}
    fail_sev  = {p["class_id"] for p in perts if p.get("severity") == "fail"}

    # ── LOCKOUT: multiple FAIL-severity classes + overall FAIL ───────────────
    if grade == "FAIL" and len(fail_sev) >= 2:
        return RiskRegime(
            name="LOCKOUT",
            min_z=MIN_Z + 2.0,     # require very strong confirmation
            max_positions=0,        # no new positions
            risk_pct=0.0,
            cooldown_sec=COOLDOWN_SEC * 4,
            allow_new=False,
            reason=f"LOCKOUT: V8 FAIL with {len(fail_sev)} fail-severity classes ({','.join(sorted(fail_sev))})",
            active_p_classes=sorted(detected),
            v8_grade=grade, omega=omega, C=C, S=S, E=E,
        )

    # ── CRISIS: burst storm or resource overload ─────────────────────────────
    if "P7" in detected or "P8" in detected:
        crisis_classes = sorted(detected & {"P7", "P8"})
        return RiskRegime(
            name="CRISIS",
            min_z=MIN_Z + 1.0,     # only trade highest-conviction spikes
            max_positions=max(1, MAX_POSITIONS // 2),
            risk_pct=RISK_PCT * 0.5,
            cooldown_sec=COOLDOWN_SEC * 2.0,
            allow_new=True,
            reason=f"CRISIS: {','.join(crisis_classes)} active — spike storm/resource overload",
            active_p_classes=sorted(detected),
            v8_grade=grade, omega=omega, C=C, S=S, E=E,
        )

    # ── GUARDED: data dropout or adversarial drift ───────────────────────────
    if "P3" in detected or "P6" in detected:
        guarded_classes = sorted(detected & {"P3", "P6"})
        return RiskRegime(
            name="GUARDED",
            min_z=MIN_Z + 0.75,
            max_positions=max(2, int(MAX_POSITIONS * 0.7)),
            risk_pct=RISK_PCT * 0.65,
            cooldown_sec=COOLDOWN_SEC * 1.5,
            allow_new=True,
            reason=f"GUARDED: {','.join(guarded_classes)} — data quality/drift concern",
            active_p_classes=sorted(detected),
            v8_grade=grade, omega=omega, C=C, S=S, E=E,
        )

    # ── ELEVATED: noise/shock/latency/saturation ─────────────────────────────
    elevated_triggers = detected & {"P1", "P2", "P4", "P5"}
    if elevated_triggers:
        return RiskRegime(
            name="ELEVATED",
            min_z=MIN_Z + 0.4,
            max_positions=max(3, int(MAX_POSITIONS * 0.85)),
            risk_pct=RISK_PCT * 0.8,
            cooldown_sec=COOLDOWN_SEC * 1.2,
            allow_new=True,
            reason=f"ELEVATED: {','.join(sorted(elevated_triggers))} detected",
            active_p_classes=sorted(detected),
            v8_grade=grade, omega=omega, C=C, S=S, E=E,
        )

    # ── NORMAL ────────────────────────────────────────────────────────────────
    return RiskRegime(
        name="NORMAL",
        min_z=MIN_Z,
        max_positions=MAX_POSITIONS,
        risk_pct=RISK_PCT,
        cooldown_sec=COOLDOWN_SEC,
        allow_new=True,
        reason="All V8 perturbation classes clear",
        active_p_classes=[],
        v8_grade=grade, omega=omega, C=C, S=S, E=E,
    )

@dataclass
class SpikePosition:
    pos_id: str
    symbol: str
    pair: str
    direction: str          # "long" | "short"
    entry_price: float
    quantity: float
    position_size_usd: float
    entry_utc: str
    spike_z: float
    spike_score: float
    spike_real: bool
    current_price: float = 0.0
    current_pnl: float = 0.0
    current_pnl_pct: float = 0.0
    status: str = "OPEN"
    exit_price: Optional[float] = None
    exit_utc: Optional[str] = None
    realized_pnl: float = 0.0
    exit_reason: str = ""

    # Auto-exit thresholds (set at entry from z-score)
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0


class SpikeEngineState:
    def __init__(self) -> None:
        raw = _load_json(STATE_FILE, {})
        self.bankroll: float = float(raw.get("bankroll", BANKROLL))
        self.positions: Dict[str, SpikePosition] = {}
        self.total_trades: int = int(raw.get("total_trades", 0))
        self.wins: int = int(raw.get("wins", 0))
        self.losses: int = int(raw.get("losses", 0))
        self.total_realized_pnl: float = float(raw.get("total_realized_pnl", 0.0))
        # symbol → last entry timestamp (cooldown guard)
        self._symbol_last_entry: Dict[str, float] = {}

    # ── Guards ────────────────────────────────────────────────────────────────

    def is_on_cooldown(self, symbol: str, cooldown: float = COOLDOWN_SEC) -> bool:
        last = self._symbol_last_entry.get(symbol, 0.0)
        return (_ts() - last) < cooldown

    def has_position(self, symbol: str) -> bool:
        return any(
            p.symbol == symbol and p.status == "OPEN"
            for p in self.positions.values()
        )

    def open_count(self) -> int:
        return sum(1 for p in self.positions.values() if p.status == "OPEN")

    def can_open(self, symbol: str, regime: "RiskRegime") -> tuple[bool, str]:
        if self.open_count() >= regime.max_positions:
            return False, f"regime {regime.name} max_positions ({regime.max_positions}) reached"
        if self.has_position(symbol):
            return False, f"already have position in {symbol}"
        if self.is_on_cooldown(symbol, regime.cooldown_sec):
            return False, f"cooldown active for {symbol}"
        if self.bankroll <= 0:
            return False, "bankroll exhausted"
        return True, "ok"

    # ── Open ──────────────────────────────────────────────────────────────────

    def open_position(self, sp: SpikePosition) -> None:
        self.positions[sp.pos_id] = sp
        self._symbol_last_entry[sp.symbol] = _ts()
        self.bankroll -= sp.position_size_usd
        self.bankroll = round(self.bankroll, 2)
        self._save()

    # ── Close ─────────────────────────────────────────────────────────────────

    def close_position(self, pos_id: str, exit_price: float, reason: str) -> Optional[SpikePosition]:
        sp = self.positions.get(pos_id)
        if sp is None or sp.status != "OPEN":
            return None
        sp.exit_price = exit_price
        sp.exit_utc = _now()
        sp.status = "CLOSED"
        sp.exit_reason = reason

        qty = sp.quantity
        if sp.direction == "long":
            realized = (exit_price - sp.entry_price) * qty
        else:
            realized = (sp.entry_price - exit_price) * qty

        sp.realized_pnl = round(realized, 4)
        self.bankroll += sp.position_size_usd + realized
        self.bankroll = round(self.bankroll, 2)
        self.total_trades += 1
        self.total_realized_pnl = round(self.total_realized_pnl + realized, 4)
        if realized >= 0:
            self.wins += 1
        else:
            self.losses += 1
        self._save()
        return sp

    # ── Update mark-to-market ─────────────────────────────────────────────────

    def update_price(self, pos_id: str, price: float) -> None:
        sp = self.positions.get(pos_id)
        if sp is None or sp.status != "OPEN":
            return
        sp.current_price = price
        qty = sp.quantity
        if sp.direction == "long":
            pnl = (price - sp.entry_price) * qty
        else:
            pnl = (sp.entry_price - price) * qty
        sp.current_pnl = round(pnl, 4)
        sp.current_pnl_pct = round(pnl / max(sp.position_size_usd, 1e-9) * 100.0, 4)

    # ── Persist ───────────────────────────────────────────────────────────────

    def _save(self) -> None:
        _write_json(STATE_FILE, {
            "updated_utc": _now(),
            "mode": MODE,
            "bankroll": self.bankroll,
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate_pct": round(self.wins / max(self.total_trades, 1) * 100, 2),
            "total_realized_pnl": self.total_realized_pnl,
            "open_positions": [
                asdict(p) for p in self.positions.values() if p.status == "OPEN"
            ],
            "recent_closed": [
                asdict(p) for p in list(self.positions.values())[-20:]
                if p.status == "CLOSED"
            ],
        })

    def heartbeat(self, extra: Dict[str, Any] = {}) -> None:
        open_positions = [p for p in self.positions.values() if p.status == "OPEN"]
        open_pnl = sum(p.current_pnl for p in open_positions)
        _write_json(HEARTBEAT_FILE, {
            "updated_utc": _now(),
            "mode": MODE,
            "status": "running",
            "bankroll": self.bankroll,
            "open_positions": len(open_positions),
            "open_pnl": round(open_pnl, 4),
            "total_trades": self.total_trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate_pct": round(self.wins / max(self.total_trades, 1) * 100, 2),
            "total_realized_pnl": self.total_realized_pnl,
            **extra,
        })


# ─── Core logic ───────────────────────────────────────────────────────────────

def _build_position(spike: Dict[str, Any], state: SpikeEngineState, regime: RiskRegime) -> Optional[SpikePosition]:
    """Build a SpikePosition from a spike_alert spike dict."""
    symbol    = str(spike.get("symbol", "")).upper().strip()
    direction = str(spike.get("direction", "up"))
    z         = float(spike.get("z_score", spike.get("spike_z_score", 0.0)) or 0.0)
    score     = float(spike.get("score", spike.get("spike_score", 0.0)) or 0.0)
    is_real   = bool(spike.get("spike_real", spike.get("real", False)))
    last_price = float(spike.get("last_price", 0.0) or 0.0)

    if not symbol:
        return None

    # Resolve pair: try to look up from symbol_registry_auto, fall back to symbol/USD
    pair = f"{symbol}/USD"
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from symbol_registry_auto import SYMBOL_REGISTRY  # type: ignore
        reg = SYMBOL_REGISTRY.get(symbol, {})
        pair = reg.get("pair", pair)
    except Exception:
        pass

    # Fetch live price if not supplied or stale
    if last_price <= 0:
        fetched = _fetch_price(symbol, pair)
        if fetched:
            last_price = fetched
    if last_price <= 0:
        log.warning(f"[SKIP] {symbol}: no entry price available")
        return None

    # Size: regime-adjusted risk_pct of bankroll, scaled by z-score confidence
    # and EchoLock harmonic resonance confidence multiplier
    base_size = state.bankroll * (regime.risk_pct / 100.0)
    z_scalar  = min(2.0, max(0.5, abs(z) / 2.5))  # 1.0 at threshold, up to 2.0

    # EchoLock confidence multiplier (1.0 → 2.0)
    harmonic_mult = 1.0
    harmonic_grade = "NOISE"
    try:
        h = _load_json(HARMONIC_LATEST_FILE, None)
        if isinstance(h, dict):
            harmonic_mult  = float(h.get("confidence_mult", 1.0))
            harmonic_grade = str(h.get("grade", "NOISE"))
            age = time.time() - HARMONIC_LATEST_FILE.stat().st_mtime
            if age > 30:  # stale — don't apply boost
                harmonic_mult  = 1.0
                harmonic_grade = "STALE"
    except Exception:
        pass

    position_size = round(base_size * z_scalar * harmonic_mult, 2)
    if harmonic_mult > 1.0:
        log.debug(f"[ECHOLOCK] {symbol}: harmonic={harmonic_grade} mult=×{harmonic_mult:.2f} "
                  f"size=${position_size:.2f}")

    if position_size < 10.0:
        log.debug(f"[SKIP] {symbol}: position too small (${position_size:.2f})")
        return None

    qty = round(position_size / last_price, 6)
    trade_dir = "long" if direction in ("up", "long") else "short"

    # Stop-loss / take-profit: asymmetric — wider TP, tighter SL
    sl_pct = 0.025 + 0.005 * min(abs(z), 3.0)   # 2.5–4% stop
    tp_pct = sl_pct * 2.5                          # 2.5:1 reward/risk

    if trade_dir == "long":
        stop_loss_price  = round(last_price * (1.0 - sl_pct), 6)
        take_profit_price = round(last_price * (1.0 + tp_pct), 6)
    else:
        stop_loss_price  = round(last_price * (1.0 + sl_pct), 6)
        take_profit_price = round(last_price * (1.0 - tp_pct), 6)

    pos_id = f"SPK-{symbol}-{int(time.time() * 1000) % 10_000_000}"

    return SpikePosition(
        pos_id=pos_id,
        symbol=symbol,
        pair=pair,
        direction=trade_dir,
        entry_price=last_price,
        quantity=qty,
        position_size_usd=position_size,
        entry_utc=_now(),
        spike_z=round(z, 4),
        spike_score=round(score, 4),
        spike_real=is_real,
        current_price=last_price,
        stop_loss_price=stop_loss_price,
        take_profit_price=take_profit_price,
    )


def _try_open(spike: Dict[str, Any], state: SpikeEngineState, regime: RiskRegime) -> bool:
    """Evaluate and open a trade for one spike. Returns True if opened."""
    symbol = str(spike.get("symbol", "")).upper().strip()
    z      = float(spike.get("z_score", spike.get("spike_z_score", 0.0)) or 0.0)
    is_real = bool(spike.get("spike_real", spike.get("real", False)))

    # Regime gate — use regime-adjusted thresholds
    if not regime.allow_new:
        log.debug(f"[REGIME] {regime.name}: new positions halted — {regime.reason}")
        return False
    if abs(z) < regime.min_z:
        return False
    if REAL_ONLY and not is_real:
        return False

    ok, reason = state.can_open(symbol, regime)
    if not ok:
        log.debug(f"[GATE] {symbol}: {reason}")
        return False

    sp = _build_position(spike, state, regime)
    if sp is None:
        return False

    state.open_position(sp)

    record = {
        "event": "SPIKE_POSITION_OPENED",
        "ts": _now(),
        "mode": MODE,
        "regime": regime.name,
        **asdict(sp),
    }
    _append_jsonl(LEDGER_FILE, record)

    log.info(
        f"[OPEN] [{regime.name}] {sp.symbol} {sp.direction.upper()} "
        f"${sp.position_size_usd:.2f} @ ${sp.entry_price:.5f} "
        f"z={sp.spike_z:.2f} real={sp.spike_real} "
        f"SL={sp.stop_loss_price:.5f} TP={sp.take_profit_price:.5f}"
    )
    return True


def _update_positions(state: SpikeEngineState) -> None:
    """Fetch live prices and check stop-loss / take-profit for all open positions."""
    to_close: list[tuple[str, float, str]] = []

    for pos_id, sp in list(state.positions.items()):
        if sp.status != "OPEN":
            continue

        # Fetch current price
        price = _fetch_price(sp.symbol, sp.pair)
        if price is None or price <= 0:
            continue

        state.update_price(pos_id, price)

        # Check exits
        if sp.direction == "long":
            if price <= sp.stop_loss_price:
                to_close.append((pos_id, price, "stop_loss"))
            elif price >= sp.take_profit_price:
                to_close.append((pos_id, price, "take_profit"))
        else:
            if price >= sp.stop_loss_price:
                to_close.append((pos_id, price, "stop_loss"))
            elif price <= sp.take_profit_price:
                to_close.append((pos_id, price, "take_profit"))

    for pos_id, exit_price, reason in to_close:
        sp = state.close_position(pos_id, exit_price, reason)
        if sp:
            emoji = "✅" if sp.realized_pnl >= 0 else "❌"
            log.info(
                f"[CLOSE] {emoji} {sp.symbol} {reason.upper()} "
                f"PnL=${sp.realized_pnl:+.4f} @ ${sp.exit_price:.5f}"
            )
            _append_jsonl(LEDGER_FILE, {
                "event": "SPIKE_POSITION_CLOSED",
                "ts": _now(),
                "mode": MODE,
                **asdict(sp),
            })


def _inject_alpha_signals(state: SpikeEngineState) -> None:
    """Write current open spike positions as synthetic alpha signals for the unified executor."""
    signals = []
    for sp in state.positions.values():
        if sp.status != "OPEN":
            continue
        signals.append({
            "signal_id": sp.pos_id,
            "symbol": sp.symbol,
            "direction": sp.direction,
            "entry_price": sp.entry_price,
            "confidence_pct": min(0.99, 0.5 + sp.spike_z / 10.0),
            "expected_value_pct": abs(sp.spike_z) * 0.5,
            "bankroll_fraction": sp.position_size_usd / max(state.bankroll + sp.position_size_usd, 1.0),
            "signal_type": "spike_engine",
            "spike_real": sp.spike_real,
            "spike_z": sp.spike_z,
            "spike_score": sp.spike_score,
            "source": "spike_trade_engine",
        })
    _write_json(ALPHA_INJECT_FILE, {
        "generated_utc": _now(),
        "source": "spike_trade_engine",
        "signals": signals,
    })


# ─── WebSocket event handler ─────────────────────────────────────────────────

async def _on_spike_alert(data: Dict[str, Any], state: SpikeEngineState) -> None:
    spikes = data.get("spikes", [])
    if not spikes:
        return

    # Recompute regime on every alert — coherence state may have changed
    regime = _compute_regime()
    _write_json(RISK_REGIME_FILE, regime.to_dict())

    prev_regime = getattr(state, "_last_regime_name", None)
    if regime.name != prev_regime:
        log.info(
            f"[REGIME CHANGE] {prev_regime or '?'} → {regime.name} | "
            f"min_z={regime.min_z:.2f} max_pos={regime.max_positions} "
            f"risk={regime.risk_pct:.2f}% | {regime.reason}"
        )
        state._last_regime_name = regime.name  # type: ignore[attr-defined]

    opened = 0
    for spike in spikes:
        if _try_open(spike, state, regime):
            opened += 1

    if opened:
        log.info(f"[BATCH] Processed {len(spikes)} spikes → opened {opened} positions [{regime.name}]")
        _inject_alpha_signals(state)
    state.heartbeat({"last_spike_alert_utc": _now(), "last_batch_opened": opened, "regime": regime.name})


# ─── WebSocket listener loop ─────────────────────────────────────────────────

async def _ws_listener(state: SpikeEngineState) -> None:
    reconnect_delay = 3.0
    log.info(f"[WS] Connecting to {GW_URL}")

    while True:
        try:
            async with websockets.connect(GW_URL, ping_interval=20, ping_timeout=15) as ws:
                log.info("[WS] Connected to gateway — listening for spike_alert events")
                state.heartbeat({"ws_connected": True})
                # Write initial regime on connect
                regime = _compute_regime()
                _write_json(RISK_REGIME_FILE, regime.to_dict())
                log.info(f"[REGIME] Initial: {regime.name} | {regime.reason}")
                reconnect_delay = 3.0

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        if msg.get("type") == "spike_alert":
                            await _on_spike_alert(msg, state)
                        # Periodic price update (triggered on any message)
                        _update_positions(state)
                        state.heartbeat({"regime": getattr(state, "_last_regime_name", "NORMAL")})
                    except Exception as e:
                        log.debug(f"[WS] Message parse error: {e}")
        except Exception as exc:
            state.heartbeat({"ws_connected": False, "last_error": str(exc)})
            log.warning(f"[WS] Disconnected: {exc} — reconnecting in {reconnect_delay:.1f}s")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 1.5, 30.0)


# ─── Fallback polling loop (if websockets not available) ─────────────────────

async def _poll_loop(state: SpikeEngineState) -> None:
    """Fallback: poll the symbol mesh REST endpoint every 3s."""
    import urllib.request

    log.info("[POLL] WebSocket library unavailable — using REST polling fallback")
    while True:
        try:
            url = "http://127.0.0.1:8787/api/trading/symbol-mesh"
            with urllib.request.urlopen(url, timeout=6) as resp:
                data = json.loads(resp.read().decode())

            alerts = data.get("real_spike_alerts", [])
            top    = data.get("top_signals", [])

            candidates = alerts + [s for s in top if s.get("spike_real")]

            regime = _compute_regime()
            _write_json(RISK_REGIME_FILE, regime.to_dict())

            opened = 0
            for spike in candidates:
                spike.setdefault("z_score", spike.get("spike_z_score", 0.0))
                spike.setdefault("score", spike.get("spike_score", 0.0))
                spike.setdefault("real", spike.get("spike_real", False))
                if _try_open(spike, state, regime):
                    opened += 1

            _update_positions(state)
            state.heartbeat({"poll_mode": True, "last_opened": opened, "regime": regime.name})

        except Exception as e:
            log.debug(f"[POLL] Error: {e}")

        await asyncio.sleep(3.0)


# ─── Entry point ─────────────────────────────────────────────────────────────

async def main(mode_override: Optional[str] = None) -> None:
    global MODE
    if mode_override:
        MODE = mode_override

    log.info("=" * 60)
    log.info(f"  LumaTrader Spike Trade Engine")
    log.info(f"  Mode     : {MODE}")
    log.info(f"  Bankroll : ${BANKROLL:,.2f}")
    log.info(f"  Risk/trade: {RISK_PCT}%")
    log.info(f"  Max pos  : {MAX_POSITIONS}")
    log.info(f"  Min z    : {MIN_Z}")
    log.info(f"  Real only: {REAL_ONLY}")
    log.info(f"  Cooldown : {COOLDOWN_SEC}s")
    log.info(f"  Gateway  : {GW_URL}")
    log.info("=" * 60)

    state = SpikeEngineState()
    state.heartbeat({"startup": True})

    if _WS_AVAILABLE:
        await _ws_listener(state)
    else:
        log.warning("[INIT] websockets library not found — using REST polling fallback")
        await _poll_loop(state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LumaTrader Spike Trade Engine")
    parser.add_argument("--mode", choices=["paper", "live"], default=None)
    args = parser.parse_args()
    asyncio.run(main(mode_override=args.mode))
