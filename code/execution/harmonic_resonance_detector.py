"""
EchoLock™ Harmonic Resonance Detector
======================================
Detects phase-locked spike timing patterns in the live market feed.

Core concept (from EchoLock IP):
  When spike alerts arrive at harmonically related intervals (T, 2T, 3T …)
  the market is in a resonant state — signals carry higher information density
  and directional confidence.  The detector computes:

    Ω_r  — resonance omega (spread of inter-arrival times)
    φ    — current phase angle within the dominant period
    H    — harmonic depth (how many sub-harmonics detected)
    RS   — resonance score 0.0 → 1.0

  Grade ladder:
    NOISE     RS < 0.20  — random, no structure
    WEAK      RS < 0.40  — faint periodicity
    MODERATE  RS < 0.60  — detectable harmonic structure
    STRONG    RS < 0.80  — phase-locked, use confidence boost
    LOCK      RS ≥ 0.80  — full EchoLock state, max confidence

  Confidence multiplier fed to Spike Trade Engine:
    NOISE/WEAK    → 1.00  (no change)
    MODERATE      → 1.25
    STRONG        → 1.60
    LOCK          → 2.00

Usage:
    python code/execution/harmonic_resonance_detector.py
Outputs:
    out/harmonic/resonance_latest.json
    out/harmonic/resonance_history.jsonl  (rolling 2000 rows)
    out/harmonic/resonance_heartbeat.json
"""

from __future__ import annotations

import json
import logging
import math
import statistics
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Deque, List, Optional

# ─── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
OUT  = ROOT / "out"

FLEET_SUMMARY_FILE   = OUT / "symbol_states" / "_fleet_summary.json"
SPIKE_ALERTS_FILE    = OUT / "symbol_states" / "_real_spike_alerts.json"
COHERENCE_LATEST     = OUT / "coherence"    / "fleet_coherence_latest.json"

RESONANCE_OUT        = OUT / "harmonic"
RESONANCE_LATEST     = RESONANCE_OUT / "resonance_latest.json"
RESONANCE_HISTORY    = RESONANCE_OUT / "resonance_history.jsonl"
RESONANCE_HEARTBEAT  = RESONANCE_OUT / "resonance_heartbeat.json"

RESONANCE_OUT.mkdir(parents=True, exist_ok=True)

# ─── Config ───────────────────────────────────────────────────────────────────
POLL_SEC         = 2.0    # scan every 2 seconds
WINDOW_SIZE      = 60     # rolling window of spike event timestamps
MIN_EVENTS       = 6      # need at least 6 events to compute periodicity
MAX_PERIOD_SEC   = 120.0  # ignore periods longer than 2 min
MIN_PERIOD_SEC   = 1.0    # ignore sub-second noise
HARMONIC_DEPTH   = 4      # check up to 4th harmonic
CV_LOCK          = 0.15   # coefficient of variation → LOCK
CV_STRONG        = 0.30   # → STRONG
CV_MODERATE      = 0.50   # → MODERATE
CV_WEAK          = 0.75   # → WEAK
MAX_HISTORY_ROWS = 2000

# ─── Logging ─────────────────────────────────────────────────────────────────
log = logging.getLogger("HARMONIC")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _append_jsonl(path: Path, obj: Any, max_rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[str] = []
    if path.exists():
        existing = path.read_text(encoding="utf-8").splitlines()
    existing.append(json.dumps(obj, default=str))
    if len(existing) > max_rows:
        existing = existing[-max_rows:]
    path.write_text("\n".join(existing) + "\n", encoding="utf-8")

# ─── Core harmonic math ───────────────────────────────────────────────────────

def _compute_cv(intervals: list[float]) -> float:
    """Coefficient of variation of inter-arrival intervals (lower = more periodic)."""
    if len(intervals) < 2:
        return 1.0
    mean = statistics.mean(intervals)
    if mean <= 0:
        return 1.0
    stdev = statistics.pstdev(intervals)
    return stdev / mean


def _harmonic_depth(intervals: list[float], base_period: float) -> int:
    """
    Count how many harmonics T/n are present in the interval series.
    An interval I is near harmonic k if abs(I - base_period/k) < base_period * 0.15.
    """
    if base_period <= 0:
        return 0
    depth = 0
    for k in range(2, HARMONIC_DEPTH + 1):
        sub = base_period / k
        hits = sum(1 for iv in intervals if abs(iv - sub) < base_period * 0.15)
        if hits / max(len(intervals), 1) >= 0.20:
            depth += 1
    return depth


def _phase_angle(last_event_ts: float, dominant_period: float) -> float:
    """
    φ ∈ [0, 2π) — current position in the resonance cycle.
    φ ≈ 0/2π  → spike just fired (entry edge)
    φ ≈ π     → halfway, anticipate next
    """
    if dominant_period <= 0:
        return 0.0
    elapsed = time.time() - last_event_ts
    return (2 * math.pi * (elapsed % dominant_period) / dominant_period)


def _grade_and_multiplier(score: float) -> tuple[str, float]:
    if score >= 0.80:
        return "LOCK",     2.00
    elif score >= 0.60:
        return "STRONG",   1.60
    elif score >= 0.40:
        return "MODERATE", 1.25
    elif score >= 0.20:
        return "WEAK",     1.00
    else:
        return "NOISE",    1.00

# ─── State ───────────────────────────────────────────────────────────────────

@dataclass
class ResonanceState:
    spike_times:     Deque[float] = field(default_factory=lambda: deque(maxlen=WINDOW_SIZE))
    last_grade:      str = "NOISE"
    scan_count:      int = 0
    last_write_utc:  str = ""
    history_count:   int = 0


@dataclass
class ResonanceSnapshot:
    ts:                   str
    scan_n:               int
    grade:                str
    score:                float
    confidence_mult:      float
    dominant_period_sec:  float
    phi_rad:              float
    phi_deg:              float
    cv:                   float
    harmonic_depth:       int
    event_window_size:    int
    intervals_used:       int
    last_spike_age_sec:   float
    v8_grade:             str
    v8_omega:             float
    note:                 str


def _snapshot_to_dict(s: ResonanceSnapshot) -> dict:
    return asdict(s)

# ─── Main scan ────────────────────────────────────────────────────────────────

def _collect_spike_times(state: ResonanceState) -> None:
    """
    Pull recent spike event timestamps from fleet summary + alert file.
    Adds new timestamps to the rolling deque (deduped within 100ms).
    """
    summary = _load_json(FLEET_SUMMARY_FILE, {})
    top_signals: list[dict] = summary.get("top_signals", [])

    # Collect timestamps from real spikes in top_signals
    new_ts: list[float] = []
    for sig in top_signals:
        if not sig.get("spike_real"):
            continue
        raw_ts = sig.get("last_updated") or sig.get("ts")
        if not raw_ts:
            continue
        try:
            if isinstance(raw_ts, str):
                dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                t = dt.timestamp()
            else:
                t = float(raw_ts)
            new_ts.append(t)
        except Exception:
            pass

    # Also check alerts file
    alerts = _load_json(SPIKE_ALERTS_FILE, [])
    if isinstance(alerts, list):
        for a in alerts:
            raw_ts = a.get("ts") or a.get("detected_at")
            if not raw_ts:
                continue
            try:
                if isinstance(raw_ts, str):
                    dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                    t = dt.timestamp()
                else:
                    t = float(raw_ts)
                new_ts.append(t)
            except Exception:
                pass

    now = time.time()
    # Only accept timestamps within the last 5 minutes
    new_ts = [t for t in new_ts if (now - t) < 300]
    new_ts.sort()

    # Dedup against existing window (within 100ms)
    existing = set(round(t, 1) for t in state.spike_times)
    for t in new_ts:
        if round(t, 1) not in existing:
            state.spike_times.append(t)
            existing.add(round(t, 1))


def _scan(state: ResonanceState) -> ResonanceSnapshot:
    state.scan_count += 1
    now = time.time()

    # Pull V8 context
    coherence = _load_json(COHERENCE_LATEST, {})
    v8_grade = coherence.get("grade", "?")
    v8_omega = float(coherence.get("omega", 0.0))

    # Collect new spike events
    _collect_spike_times(state)

    times = sorted(state.spike_times)
    n = len(times)

    if n < MIN_EVENTS:
        snap = ResonanceSnapshot(
            ts=_now(), scan_n=state.scan_count,
            grade="NOISE", score=0.0, confidence_mult=1.0,
            dominant_period_sec=0.0, phi_rad=0.0, phi_deg=0.0,
            cv=1.0, harmonic_depth=0, event_window_size=n,
            intervals_used=0,
            last_spike_age_sec=round(now - times[-1], 2) if times else 9999.0,
            v8_grade=v8_grade, v8_omega=v8_omega,
            note=f"Waiting for events ({n}/{MIN_EVENTS})",
        )
        return snap

    # Compute inter-arrival intervals
    intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
    # Filter out gaps > MAX_PERIOD_SEC (burst gaps break structure)
    intervals = [iv for iv in intervals if MIN_PERIOD_SEC <= iv <= MAX_PERIOD_SEC]

    if len(intervals) < 3:
        snap = ResonanceSnapshot(
            ts=_now(), scan_n=state.scan_count,
            grade="NOISE", score=0.0, confidence_mult=1.0,
            dominant_period_sec=0.0, phi_rad=0.0, phi_deg=0.0,
            cv=1.0, harmonic_depth=0, event_window_size=n,
            intervals_used=0,
            last_spike_age_sec=round(now - times[-1], 2),
            v8_grade=v8_grade, v8_omega=v8_omega,
            note="Not enough valid intervals (large gaps dominate)",
        )
        return snap

    # Core metrics
    cv             = _compute_cv(intervals)
    dominant_period = statistics.median(intervals)
    h_depth        = _harmonic_depth(intervals, dominant_period)
    last_spike_age = now - times[-1]
    phi            = _phase_angle(times[-1], dominant_period)
    phi_deg        = math.degrees(phi)

    # Resonance score composition:
    #   40% from CV (lower = better)
    #   30% from harmonic depth
    #   20% from recency (spikes still arriving)
    #   10% from V8 coherence alignment (low omega = stable carrier)
    cv_score       = max(0.0, 1.0 - cv)
    harm_score     = min(1.0, h_depth / HARMONIC_DEPTH)
    recency_score  = max(0.0, 1.0 - last_spike_age / 30.0)  # decays to 0 over 30s
    v8_score       = max(0.0, 1.0 - min(v8_omega / 5.0, 1.0))  # 0 at omega=5

    score = (
        0.40 * cv_score +
        0.30 * harm_score +
        0.20 * recency_score +
        0.10 * v8_score
    )
    score = round(min(max(score, 0.0), 1.0), 4)

    grade, mult = _grade_and_multiplier(score)

    note = (
        f"cv={cv:.3f} H={h_depth} age={last_spike_age:.1f}s "
        f"T={dominant_period:.1f}s φ={phi_deg:.0f}°"
    )

    return ResonanceSnapshot(
        ts=_now(), scan_n=state.scan_count,
        grade=grade, score=score, confidence_mult=mult,
        dominant_period_sec=round(dominant_period, 3),
        phi_rad=round(phi, 4), phi_deg=round(phi_deg, 1),
        cv=round(cv, 4), harmonic_depth=h_depth,
        event_window_size=n, intervals_used=len(intervals),
        last_spike_age_sec=round(last_spike_age, 2),
        v8_grade=v8_grade, v8_omega=v8_omega,
        note=note,
    )


# ─── Main loop ───────────────────────────────────────────────────────────────

def _monitor_loop(state: ResonanceState) -> None:
    log.info("=" * 60)
    log.info("  EchoLock™ Harmonic Resonance Detector")
    log.info(f"  Window : {WINDOW_SIZE} events")
    log.info(f"  Poll   : {POLL_SEC}s")
    log.info(f"  Output : {RESONANCE_LATEST}")
    log.info("=" * 60)

    while True:
        t0 = time.time()
        try:
            snap = _scan(state)

            # Log on grade change or every 30 scans
            if snap.grade != state.last_grade or state.scan_count % 30 == 0:
                icon = {"LOCK": "🔒", "STRONG": "⚡", "MODERATE": "~",
                        "WEAK": "·", "NOISE": "○"}.get(snap.grade, "?")
                log.info(
                    f"[{snap.grade}] {icon} RS={snap.score:.3f} "
                    f"mult=×{snap.confidence_mult:.2f} {snap.note}"
                )
                state.last_grade = snap.grade

            d = _snapshot_to_dict(snap)

            # ── Outputs ──────────────────────────────────────────────────────
            _write_json(RESONANCE_LATEST, d)
            _append_jsonl(RESONANCE_HISTORY, d, MAX_HISTORY_ROWS)
            _write_json(RESONANCE_HEARTBEAT, {
                "updated_utc":      _now(),
                "scan_n":           snap.scan_n,
                "grade":            snap.grade,
                "score":            snap.score,
                "confidence_mult":  snap.confidence_mult,
                "dominant_period":  snap.dominant_period_sec,
                "phi_deg":          snap.phi_deg,
                "event_window":     snap.event_window_size,
                "status":           "running",
            })
            state.history_count += 1

        except Exception as exc:
            log.exception(f"[HARMONIC] Scan error: {exc}")

        elapsed = time.time() - t0
        sleep = max(0.0, POLL_SEC - elapsed)
        time.sleep(sleep)


def main() -> None:
    state = ResonanceState()
    _monitor_loop(state)


if __name__ == "__main__":
    main()
