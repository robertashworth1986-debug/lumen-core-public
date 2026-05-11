#!/usr/bin/env python3
"""
fleet_coherence_monitor.py
──────────────────────────
LumaTrader V8 Perturbation Suite — Live Coherence Monitor

Continuously reads the symbol watcher fleet summary and computes the four
V8 coherence metrics, then scores the system against all 8 perturbation
classes in real time.

Metrics (from V8_PERTURBATION_SUITE spec)
──────────────────────────────────────────
  Ω  (omega)    — drift / z-score variance across fleet
  C  (coherence)— data coverage: symbols_with_data / total_watched
  S  (stability) — fraction of fleet NOT in active spike state
  E  (energy)   — aggregate spike intensity (Σ spike_scores)

Perturbation Detectors
──────────────────────
  P1 Noise       — Ω elevated, no directional bias in z_mean
  P2 Step shock  — sudden jump (>σ) in fleet mean_z over one interval
  P3 Dropout     — C drops sharply (data loss)
  P4 Latency     — fleet summary freshness_sec spikes above threshold
  P5 Saturation  — large fraction of symbols at max z-score clip
  P6 Drift       — slow linear trend in mean_z sustained >N windows
  P7 Burst       — E > burst_threshold (spike storm)
  P8 Resource    — active_spikes / total_watched > resource cap ratio

Outputs
───────
  out/coherence/fleet_coherence_latest.json   — latest snapshot
  out/coherence/fleet_coherence_history.jsonl — rolling audit trail
  out/coherence/coherence_heartbeat.json      — daemon health

Configuration (env vars)
────────────────────────
  COHERENCE_POLL_SEC        scan interval  (default: 4.0)
  COHERENCE_HISTORY_MAX     jsonl rows kept (default: 2000)
  COHERENCE_OMEGA_WARN      Ω warn threshold (default: 1.5)
  COHERENCE_OMEGA_FAIL      Ω fail threshold (default: 3.0)
  COHERENCE_C_WARN          C coverage warn  (default: 0.85)
  COHERENCE_C_FAIL          C coverage fail  (default: 0.60)
  COHERENCE_S_WARN          S stability warn (default: 0.90)
  COHERENCE_E_BURST         E burst threshold(default: 50.0)
  COHERENCE_LATENCY_WARN    freshness warn s (default: 8.0)
  COHERENCE_LATENCY_FAIL    freshness fail s (default: 20.0)
  COHERENCE_DRIFT_WINDOW    windows for P6   (default: 15)
  COHERENCE_SHOCK_SIGMA     z-jump σ for P2  (default: 2.0)

Usage
─────
  python code/execution/fleet_coherence_monitor.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
FLEET_SUMMARY  = ROOT / "out" / "symbol_states" / "_fleet_summary.json"
FLEET_ALERTS   = ROOT / "out" / "symbol_states" / "_real_spike_alerts.json"
OUT            = ROOT / "out" / "coherence"
OUT.mkdir(parents=True, exist_ok=True)

LATEST_FILE    = OUT / "fleet_coherence_latest.json"
HISTORY_FILE   = OUT / "fleet_coherence_history.jsonl"
HEARTBEAT_FILE = OUT / "coherence_heartbeat.json"

# ─── Config ───────────────────────────────────────────────────────────────────
POLL_SEC          = float(os.environ.get("COHERENCE_POLL_SEC",      "4.0"))
HISTORY_MAX       = int(os.environ.get("COHERENCE_HISTORY_MAX",    "2000"))
OMEGA_WARN        = float(os.environ.get("COHERENCE_OMEGA_WARN",   "1.5"))
OMEGA_FAIL        = float(os.environ.get("COHERENCE_OMEGA_FAIL",   "3.0"))
C_WARN            = float(os.environ.get("COHERENCE_C_WARN",       "0.85"))
C_FAIL            = float(os.environ.get("COHERENCE_C_FAIL",       "0.60"))
S_WARN            = float(os.environ.get("COHERENCE_S_WARN",       "0.90"))
E_BURST           = float(os.environ.get("COHERENCE_E_BURST",      "50.0"))
LATENCY_WARN      = float(os.environ.get("COHERENCE_LATENCY_WARN", "8.0"))
LATENCY_FAIL      = float(os.environ.get("COHERENCE_LATENCY_FAIL", "20.0"))
DRIFT_WINDOW      = int(os.environ.get("COHERENCE_DRIFT_WINDOW",   "15"))
SHOCK_SIGMA       = float(os.environ.get("COHERENCE_SHOCK_SIGMA",  "2.0"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [COHERENCE] %(levelname)s: %(message)s",
)
log = logging.getLogger("coherence")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ts() -> float:
    return time.time()

def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _append_history(record: Dict[str, Any]) -> None:
    """Append one record to history, pruning to HISTORY_MAX rows."""
    try:
        lines: List[str] = []
        if HISTORY_FILE.exists():
            lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        lines.append(json.dumps(record))
        if len(lines) > HISTORY_MAX:
            lines = lines[-HISTORY_MAX:]
        HISTORY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as e:
        log.debug(f"History write error: {e}")

def _safe(v: Any, default: float = 0.0) -> float:
    try:
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


# ─── Perturbation verdict ─────────────────────────────────────────────────────

@dataclass
class PerturbationResult:
    name: str
    class_id: str           # P1–P8
    description: str
    detected: bool
    severity: str           # "none" | "warn" | "fail"
    value: float
    threshold: float
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ─── Coherence snapshot ───────────────────────────────────────────────────────

@dataclass
class CoherenceSnapshot:
    ts: str
    # Primary V8 metrics
    omega: float        # drift — z-score variance
    C: float            # coverage coherence
    S: float            # stability
    E: float            # energy (aggregate spike intensity)
    # Supporting stats
    total_watched: int
    symbols_with_data: int
    active_spikes: int
    real_spikes: int
    mean_z: float       # mean z-score magnitude across fleet top signals
    freshness_sec: float
    # Aggregate score
    overall_pass: bool
    overall_grade: str  # "PASS" | "WARN" | "FAIL"
    # Per-perturbation results
    perturbations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ─── State for trend detection ────────────────────────────────────────────────

class CoherenceState:
    def __init__(self) -> None:
        # Rolling windows for trend/shock detection
        self.omega_history: Deque[float] = deque(maxlen=DRIFT_WINDOW + 5)
        self.mean_z_history: Deque[float] = deque(maxlen=DRIFT_WINDOW + 5)
        self.C_history: Deque[float]     = deque(maxlen=DRIFT_WINDOW + 5)
        self.E_history: Deque[float]     = deque(maxlen=DRIFT_WINDOW + 5)
        self.scan_count: int = 0
        self.last_snap: Optional[CoherenceSnapshot] = None


# ─── Metric extraction ────────────────────────────────────────────────────────

def _extract_metrics(
    summary: Dict[str, Any],
    freshness_sec: float,
) -> Tuple[float, float, float, float, float]:
    """
    Returns (omega, C, S, E, mean_z) from fleet summary.
    """
    total     = max(int(summary.get("total_watched", 0) or 0), 1)
    with_data = int(summary.get("symbols_with_data", 0) or 0)
    active    = int(summary.get("active_spikes", 0) or 0)
    real      = int(summary.get("real_spikes", 0) or 0)

    # C = data coverage
    C = with_data / total

    # S = stability = fraction of symbols NOT in spike state
    S = 1.0 - (active / max(with_data, 1))
    S = max(0.0, min(1.0, S))

    # E = aggregate energy from top signals
    top_signals: List[Dict] = summary.get("top_signals", [])
    scores = [_safe(sig.get("spike_score")) for sig in top_signals if sig.get("spike_real")]
    E = sum(scores)

    # Ω = z-score variance across top signals (spread in z-scores = drift)
    z_vals = [_safe(sig.get("spike_z_score")) for sig in top_signals]
    if len(z_vals) >= 2:
        n    = len(z_vals)
        mean = sum(z_vals) / n
        var  = sum((v - mean) ** 2 for v in z_vals) / n
        omega = math.sqrt(var)
        mean_z = abs(mean)
    elif len(z_vals) == 1:
        omega  = abs(z_vals[0])
        mean_z = abs(z_vals[0])
    else:
        omega  = 0.0
        mean_z = 0.0

    return omega, C, S, E, mean_z


# ─── Perturbation detectors ───────────────────────────────────────────────────

def _detect_p1_noise(omega: float, mean_z: float) -> PerturbationResult:
    """P1: Noise — Ω elevated but mean_z low (no directional bias)."""
    # High spread but low mean = random noise injection
    ratio = omega / max(mean_z, 0.1)
    detected = omega > OMEGA_WARN and ratio > 1.8
    sev = "none"
    if omega > OMEGA_FAIL:
        sev = "fail"
    elif omega > OMEGA_WARN:
        sev = "warn"
    return PerturbationResult(
        name="Noise Injection", class_id="P1", detected=detected, severity=sev,
        description="Gaussian noise on inputs/metrics",
        value=round(omega, 4), threshold=OMEGA_WARN,
        note=f"Ω={omega:.3f} mean_z={mean_z:.3f} spread_ratio={ratio:.2f}"
    )


def _detect_p2_shock(
    mean_z: float, state: CoherenceState
) -> PerturbationResult:
    """P2: Step shock — sudden jump in mean_z."""
    hist = list(state.mean_z_history)
    if len(hist) >= 3:
        baseline_mean = sum(hist[:-1]) / (len(hist) - 1)
        baseline_std  = math.sqrt(
            sum((v - baseline_mean) ** 2 for v in hist[:-1]) / max(len(hist) - 1, 1)
        )
        jump = abs(mean_z - baseline_mean)
        sigma_jump = jump / max(baseline_std, 0.01)
        detected = sigma_jump > SHOCK_SIGMA and jump > 1.0
        sev = "fail" if sigma_jump > SHOCK_SIGMA * 2 else ("warn" if detected else "none")
        return PerturbationResult(
            name="Step Shock", class_id="P2", detected=detected, severity=sev,
            description="Sudden jump in key parameter",
            value=round(sigma_jump, 3), threshold=SHOCK_SIGMA,
            note=f"jump={jump:.3f} ({sigma_jump:.1f}σ) from baseline={baseline_mean:.3f}"
        )
    return PerturbationResult(
        name="Step Shock", class_id="P2", detected=False, severity="none",
        description="Sudden jump in key parameter",
        value=0.0, threshold=SHOCK_SIGMA, note="Insufficient history"
    )


def _detect_p3_dropout(C: float, state: CoherenceState) -> PerturbationResult:
    """P3: Dropout — sudden drop in data coverage C."""
    hist = list(state.C_history)
    drop = 0.0
    if len(hist) >= 2:
        drop = max(0.0, hist[-2] - C) if len(hist) > 1 else 0.0
    detected = C < C_WARN or drop > 0.10
    sev = "fail" if C < C_FAIL else ("warn" if detected else "none")
    return PerturbationResult(
        name="Dropout / Missing Sensors", class_id="P3", detected=detected, severity=sev,
        description="Missing metrics / NaNs / sensor dropout",
        value=round(C, 4), threshold=C_WARN,
        note=f"coverage={C*100:.1f}% drop={drop*100:.1f}%"
    )


def _detect_p4_latency(freshness_sec: float) -> PerturbationResult:
    """P4: Latency jitter — fleet summary stale."""
    detected = freshness_sec > LATENCY_WARN
    sev = "fail" if freshness_sec > LATENCY_FAIL else ("warn" if detected else "none")
    return PerturbationResult(
        name="Latency Jitter", class_id="P4", detected=detected, severity=sev,
        description="Delayed updates / time-skips",
        value=round(freshness_sec, 2), threshold=LATENCY_WARN,
        note=f"fleet_age={freshness_sec:.1f}s"
    )


def _detect_p5_saturation(
    top_signals: List[Dict], omega: float
) -> PerturbationResult:
    """P5: Saturation — many symbols hitting max z-score clip."""
    Z_CLIP = 6.0  # Kraken ticker rarely produces z > 6 naturally
    clipped = sum(
        1 for s in top_signals if _safe(s.get("spike_z_score")) >= Z_CLIP
    )
    ratio = clipped / max(len(top_signals), 1)
    detected = ratio > 0.20 or (omega > OMEGA_FAIL and ratio > 0.05)
    sev = "fail" if ratio > 0.40 else ("warn" if detected else "none")
    return PerturbationResult(
        name="Saturation / Rail Clamp", class_id="P5", detected=detected, severity=sev,
        description="Sensor rail / clamped ranges",
        value=round(ratio, 4), threshold=0.20,
        note=f"clipped={clipped}/{len(top_signals)} ({ratio*100:.1f}%)"
    )


def _detect_p6_drift(state: CoherenceState) -> PerturbationResult:
    """P6: Adversarial drift — slow linear trend in mean_z over time."""
    hist = list(state.mean_z_history)
    if len(hist) < DRIFT_WINDOW:
        return PerturbationResult(
            name="Adversarial Drift", class_id="P6", detected=False, severity="none",
            description="Slow bias accumulating over time",
            value=0.0, threshold=0.0, note=f"Need {DRIFT_WINDOW} windows ({len(hist)} so far)"
        )
    # Simple linear regression slope
    n = len(hist)
    xs = list(range(n))
    x_mean = (n - 1) / 2.0
    y_mean = sum(hist) / n
    num = sum((xs[i] - x_mean) * (hist[i] - y_mean) for i in range(n))
    den = sum((xs[i] - x_mean) ** 2 for i in range(n))
    slope = num / max(den, 1e-9)
    # Slope per window in units of z-score / scan
    detected = abs(slope) > 0.05
    sev = "fail" if abs(slope) > 0.15 else ("warn" if detected else "none")
    return PerturbationResult(
        name="Adversarial Drift", class_id="P6", detected=detected, severity=sev,
        description="Slow bias accumulating over time",
        value=round(slope, 5), threshold=0.05,
        note=f"slope={slope:+.5f} z/scan over {n} windows"
    )


def _detect_p7_burst(E: float, state: CoherenceState) -> PerturbationResult:
    """P7: Burst events — spike storm (high aggregate energy)."""
    hist_E = list(state.E_history)
    baseline_E = sum(hist_E[:-1]) / max(len(hist_E) - 1, 1) if len(hist_E) > 1 else 0.0
    burst_ratio = E / max(baseline_E, 1.0)
    detected = E > E_BURST or burst_ratio > 3.0
    sev = "fail" if E > E_BURST * 2 else ("warn" if detected else "none")
    return PerturbationResult(
        name="Burst / Spike Storm", class_id="P7", detected=detected, severity=sev,
        description="Short spike storm (incident window)",
        value=round(E, 3), threshold=E_BURST,
        note=f"E={E:.2f} baseline={baseline_E:.2f} ratio={burst_ratio:.1f}×"
    )


def _detect_p8_resource(
    active_spikes: int, total_watched: int
) -> PerturbationResult:
    """P8: Resource constraint — active spike load as fraction of fleet capacity."""
    CAP_RATIO = 0.15  # >15% fleet simultaneously spiking = resource pressure
    ratio = active_spikes / max(total_watched, 1)
    detected = ratio > CAP_RATIO
    sev = "fail" if ratio > 0.25 else ("warn" if detected else "none")
    return PerturbationResult(
        name="Resource Constraint", class_id="P8", detected=detected, severity=sev,
        description="Energy budget / capacity cap exceeded",
        value=round(ratio, 4), threshold=CAP_RATIO,
        note=f"active={active_spikes}/{total_watched} ({ratio*100:.1f}%)"
    )


# ─── Grade aggregator ─────────────────────────────────────────────────────────

def _aggregate_grade(results: List[PerturbationResult]) -> Tuple[bool, str]:
    severities = [r.severity for r in results]
    if "fail" in severities:
        return False, "FAIL"
    if "warn" in severities:
        return True, "WARN"
    return True, "PASS"


# ─── Main scan ────────────────────────────────────────────────────────────────

def _scan(state: CoherenceState) -> Optional[CoherenceSnapshot]:
    """One coherence scan. Returns snapshot or None if fleet data unavailable."""
    if not FLEET_SUMMARY.exists():
        log.debug("Fleet summary not found — fleet may not be running")
        return None

    # Fleet summary freshness
    freshness_sec = max(0.0, _ts() - FLEET_SUMMARY.stat().st_mtime)
    summary = _load_json(FLEET_SUMMARY, {})
    if not isinstance(summary, dict):
        return None

    top_signals: List[Dict] = summary.get("top_signals", []) or []
    total_watched  = int(summary.get("total_watched", 0) or 0)
    symbols_with_data = int(summary.get("symbols_with_data", 0) or 0)
    active_spikes  = int(summary.get("active_spikes", 0) or 0)
    real_spikes    = int(summary.get("real_spikes", 0) or 0)

    # Compute V8 metrics
    omega, C, S, E, mean_z = _extract_metrics(summary, freshness_sec)

    # Update rolling history
    state.omega_history.append(omega)
    state.mean_z_history.append(mean_z)
    state.C_history.append(C)
    state.E_history.append(E)

    # Run all 8 perturbation detectors
    results = [
        _detect_p1_noise(omega, mean_z),
        _detect_p2_shock(mean_z, state),
        _detect_p3_dropout(C, state),
        _detect_p4_latency(freshness_sec),
        _detect_p5_saturation(top_signals, omega),
        _detect_p6_drift(state),
        _detect_p7_burst(E, state),
        _detect_p8_resource(active_spikes, total_watched),
    ]

    overall_pass, overall_grade = _aggregate_grade(results)

    snap = CoherenceSnapshot(
        ts=_now(),
        omega=round(omega, 5),
        C=round(C, 5),
        S=round(S, 5),
        E=round(E, 5),
        total_watched=total_watched,
        symbols_with_data=symbols_with_data,
        active_spikes=active_spikes,
        real_spikes=real_spikes,
        mean_z=round(mean_z, 5),
        freshness_sec=round(freshness_sec, 2),
        overall_pass=overall_pass,
        overall_grade=overall_grade,
        perturbations=[r.to_dict() for r in results],
    )
    state.last_snap = snap
    state.scan_count += 1
    return snap


# ─── Loop ─────────────────────────────────────────────────────────────────────

async def _monitor_loop(state: CoherenceState) -> None:
    log.info("=" * 60)
    log.info("  LumaTrader V8 Coherence Monitor")
    log.info(f"  Poll interval : {POLL_SEC}s")
    log.info(f"  Ω thresholds  : warn={OMEGA_WARN} fail={OMEGA_FAIL}")
    log.info(f"  C thresholds  : warn={C_WARN} fail={C_FAIL}")
    log.info(f"  E burst       : {E_BURST}")
    log.info(f"  Drift window  : {DRIFT_WINDOW} scans")
    log.info("=" * 60)

    _write_json(HEARTBEAT_FILE, {"status": "starting", "ts": _now()})

    while True:
        try:
            snap = _scan(state)
            if snap is not None:
                d = snap.to_dict()
                _write_json(LATEST_FILE, d)
                _append_history({"scan": state.scan_count, **d})

                # Heartbeat
                detected_count = sum(1 for p in snap.perturbations if p.get("detected"))
                _write_json(HEARTBEAT_FILE, {
                    "status": "running",
                    "ts": _now(),
                    "scan_count": state.scan_count,
                    "grade": snap.overall_grade,
                    "omega": snap.omega,
                    "C": snap.C,
                    "S": snap.S,
                    "E": snap.E,
                    "detected_perturbations": detected_count,
                    "freshness_sec": snap.freshness_sec,
                })

                # Log on grade change or perturbation detection
                grade_emoji = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(snap.overall_grade, "")
                active_p = [p["class_id"] for p in snap.perturbations if p.get("detected")]
                log.info(
                    f"{grade_emoji} [{snap.overall_grade}] "
                    f"Ω={snap.omega:.3f} C={snap.C:.3f} S={snap.S:.3f} E={snap.E:.2f} "
                    f"cov={snap.symbols_with_data}/{snap.total_watched} "
                    f"lag={snap.freshness_sec:.1f}s "
                    f"{'active: ' + ','.join(active_p) if active_p else 'no perturbations'}"
                )
            else:
                _write_json(HEARTBEAT_FILE, {
                    "status": "waiting_for_fleet",
                    "ts": _now(),
                    "scan_count": state.scan_count,
                    "hint": "Start symbol_watcher_fleet.py",
                })

        except Exception as e:
            log.warning(f"Scan error: {e}")

        await asyncio.sleep(POLL_SEC)


async def main() -> None:
    state = CoherenceState()
    await _monitor_loop(state)


if __name__ == "__main__":
    asyncio.run(main())
