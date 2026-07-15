"""Alpha Intelligence Champion engine for LumenCore.

This module turns the Alpha/Omega/Harmonic/Echo naming system into a
reproducible benchmark and promotion pipeline. "Quantum" labels here mean
quantum-inspired signal features and cryptographic state locking; this module
does not claim to execute on quantum hardware.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

EPS = 1e-12


def _finite(values: Iterable[float]) -> list[float]:
    out = [float(v) for v in values if math.isfinite(float(v))]
    if not out:
        raise ValueError("at least one finite value is required")
    return out


def _unit_interval(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalize(values: Sequence[float]) -> list[float]:
    xs = _finite(values)
    lo, hi = min(xs), max(xs)
    span = hi - lo
    if span <= EPS:
        return [0.5 for _ in xs]
    return [(x - lo) / span for x in xs]


def _mean_abs_diff(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return statistics.fmean(abs(b - a) for a, b in zip(values, values[1:]))


def _lag_correlation(values: Sequence[float], lag: int = 1) -> float:
    if lag <= 0 or len(values) <= lag + 1:
        return 0.0
    a, b = values[:-lag], values[lag:]
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = math.sqrt(sum((x - ma) ** 2 for x in a))
    db = math.sqrt(sum((y - mb) ** 2 for y in b))
    return 0.0 if da * db <= EPS else max(-1.0, min(1.0, num / (da * db)))


def harmonic_coherence(values: Sequence[float], harmonics: int = 8) -> float:
    """Return spectral concentration in the strongest low-order harmonic."""
    xs = _finite(values)
    if len(xs) < 4:
        return 0.0
    mean = statistics.fmean(xs)
    centered = [x - mean for x in xs]
    total_energy = sum(x * x for x in centered)
    if total_energy <= EPS:
        return 1.0
    powers: list[float] = []
    limit = min(max(1, harmonics), len(xs) // 2)
    for k in range(1, limit + 1):
        real = sum(x * math.cos(2.0 * math.pi * k * i / len(xs)) for i, x in enumerate(centered))
        imag = sum(x * math.sin(2.0 * math.pi * k * i / len(xs)) for i, x in enumerate(centered))
        powers.append(real * real + imag * imag)
    return _unit_interval(max(powers, default=0.0) / (sum(powers) + EPS))


def bio_digital_echo(values: Sequence[float], decay: float = 0.82) -> list[float]:
    """Create a bounded recursive memory field from a numeric signal."""
    if not 0.0 <= decay < 1.0:
        raise ValueError("decay must satisfy 0 <= decay < 1")
    xs = _normalize(values)
    echo = 0.0
    field: list[float] = []
    for value in xs:
        echo = decay * echo + (1.0 - decay) * value
        field.append(_unit_interval(echo))
    return field


@dataclass(frozen=True)
class AlphaMetrics:
    stability: float
    coherence: float
    adaptability: float
    echo_integrity: float
    alpha_score: float
    omega_score: float
    alpha_omega_score: float


@dataclass(frozen=True)
class ChampionResult:
    champion_id: str
    metrics: AlphaMetrics
    quantum_alpha_lock: str
    ranking: tuple[tuple[str, float], ...]
    evidence_boundary: str


def measure_alpha(values: Sequence[float]) -> AlphaMetrics:
    xs = _finite(values)
    normalized = _normalize(xs)
    volatility = statistics.pstdev(normalized) if len(normalized) > 1 else 0.0
    stability = _unit_interval(1.0 - 2.0 * volatility)
    coherence = harmonic_coherence(normalized)
    adaptability = _unit_interval(_mean_abs_diff(normalized) * 2.0)
    echo = bio_digital_echo(normalized)
    echo_integrity = _unit_interval((1.0 + _lag_correlation(echo, 1)) / 2.0)

    # Alpha rewards decisive coherent adaptation; Omega rewards bounded persistence.
    alpha_score = _unit_interval(0.40 * coherence + 0.35 * adaptability + 0.25 * stability)
    omega_score = _unit_interval(0.55 * stability + 0.45 * echo_integrity)
    alpha_omega_score = _unit_interval(math.sqrt(alpha_score * omega_score))
    return AlphaMetrics(
        stability=stability,
        coherence=coherence,
        adaptability=adaptability,
        echo_integrity=echo_integrity,
        alpha_score=alpha_score,
        omega_score=omega_score,
        alpha_omega_score=alpha_omega_score,
    )


def quantum_alpha_lock(payload: Mapping[str, object]) -> str:
    """Return a deterministic SHA-256 lock for a benchmark state."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def select_champion(candidates: Mapping[str, Sequence[float]]) -> ChampionResult:
    if not candidates:
        raise ValueError("at least one candidate is required")
    scored = {name: measure_alpha(values) for name, values in candidates.items()}
    ranking = tuple(
        sorted(
            ((name, metrics.alpha_omega_score) for name, metrics in scored.items()),
            key=lambda item: (-item[1], item[0]),
        )
    )
    champion_id = ranking[0][0]
    metrics = scored[champion_id]
    lock_payload = {
        "schema": "alpha_intelligence_champion_v1",
        "champion_id": champion_id,
        "metrics": asdict(metrics),
        "ranking": ranking,
    }
    return ChampionResult(
        champion_id=champion_id,
        metrics=metrics,
        quantum_alpha_lock=quantum_alpha_lock(lock_payload),
        ranking=ranking,
        evidence_boundary=(
            "Quantum-inspired harmonic features and cryptographic locking only; "
            "no quantum-computing or biological-performance claim."
        ),
    )


def result_to_json(result: ChampionResult) -> str:
    payload = asdict(result)
    return json.dumps(payload, indent=2, sort_keys=True)
