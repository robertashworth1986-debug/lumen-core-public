from __future__ import annotations
import hashlib
import json
import math
import random
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import harmonic_mean, mean
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class KarmaComponent:
    name: str
    quality: float
    confidence: float
    freshness: float
    weight: float = 1.0
    details: Dict[str, Any] = field(default_factory=dict)

    def normalized(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    @property
    def quality_norm(self) -> float:
        return self.normalized(self.quality)

    @property
    def confidence_norm(self) -> float:
        return self.normalized(self.confidence)

    @property
    def freshness_norm(self) -> float:
        return self.normalized(self.freshness)

    def local_karma(self) -> float:
        values = [self.quality_norm, self.confidence_norm, self.freshness_norm]
        safe = [max(v, 1e-6) for v in values]
        return harmonic_mean(safe) * self.weight

    def karma_signature(self) -> str:
        payload = json.dumps({
            "name": self.name,
            "quality": self.quality,
            "confidence": self.confidence,
            "freshness": self.freshness,
            "weight": self.weight,
            **self.details,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class KarmaCase:
    case_id: str
    title: str
    status: str
    category: str
    components: List[KarmaComponent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "status": self.status,
            "category": self.category,
            "metadata": self.metadata,
            "components": [
                {
                    "name": c.name,
                    "quality": c.quality,
                    "confidence": c.confidence,
                    "freshness": c.freshness,
                    "weight": c.weight,
                    **c.details,
                }
                for c in self.components
            ],
        }

    def karma_points(self) -> List[float]:
        return [c.local_karma() for c in self.components]

    def karmuk_sum(self) -> float:
        points = self.karma_points()
        if not points:
            return 0.0
        return sum(points)

    def karmuk_moments(self) -> Dict[str, float]:
        points = sorted(self.karma_points())
        if not points:
            return {"median": 0.0, "q75": 0.0, "q90": 0.0, "q99": 0.0, "max": 0.0}
        return {
            "median": self._quantile(points, 0.5),
            "q75": self._quantile(points, 0.75),
            "q90": self._quantile(points, 0.9),
            "q99": self._quantile(points, 0.99),
            "max": points[-1],
        }

    def _quantile(self, values: List[float], q: float) -> float:
        if not values:
            return 0.0
        pos = (len(values) - 1) * q
        lo = math.floor(pos)
        hi = math.ceil(pos)
        if lo == hi:
            return values[int(pos)]
        frac = pos - lo
        return values[lo] * (1 - frac) + values[hi] * frac


class XinFitEngine:
    def __init__(self, cases: Iterable[KarmaCase] | None = None, runs: int = 1000, history_length: int = 30):
        self.cases: List[KarmaCase] = list(cases or [])
        self.runs = runs
        self.history_length = history_length
        self.history: List[Dict[str, Any]] = []

    @staticmethod
    def _safe_harmonic(values: List[float], floor: float = 1e-6) -> float:
        positive = [max(v, floor) for v in values if v is not None]
        if not positive:
            return 0.0
        return harmonic_mean(positive)

    @staticmethod
    def _quantiles(values: List[float], quantiles: List[float]) -> Dict[str, float]:
        sorted_values = sorted(values)
        if not sorted_values:
            return {f"q{int(q*100)}": 0.0 for q in quantiles}
        result = {}
        for q in quantiles:
            pos = (len(sorted_values) - 1) * q
            lo = math.floor(pos)
            hi = math.ceil(pos)
            if lo == hi:
                result[f"q{int(q*100)}"] = sorted_values[int(pos)]
            else:
                frac = pos - lo
                result[f"q{int(q*100)}"] = sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac
        return result

    def score_case(self, case: KarmaCase, weight_perturbation: Optional[float] = None) -> Dict[str, float]:
        points = case.karma_points()
        if weight_perturbation is not None:
            points = [p * (1 + weight_perturbation * random.uniform(-0.25, 0.25)) for p in points]
        case_strength = self._safe_harmonic(points) if points else 0.0
        moments = case.karmuk_moments()
        burst_energy = (moments["q90"] * 0.7 + moments["q99"] * 0.3) if points else 0.0
        constancy = min(1.0, mean(points) / (1.0 + statistics.pstdev(points) if len(points) > 1 else 1.0)) if points else 0.0
        return {
            "case_strength": round(case_strength, 4),
            "karmuk_sum": round(case.karmuk_sum(), 4),
            "burst_energy": round(burst_energy, 4),
            "constancy": round(constancy, 4),
            **moments,
        }

    def score_all(self) -> List[Dict[str, Any]]:
        scored = []
        for case in self.cases:
            metrics = self.score_case(case)
            scored.append({
                "case_id": case.case_id,
                "title": case.title,
                "status": case.status,
                "category": case.category,
                "evidence_count": len(case.components),
                **metrics,
            })
        return scored

    def rank_cases(self, descending: bool = True) -> List[Dict[str, Any]]:
        return sorted(self.score_all(), key=lambda r: (r["case_strength"], r["burst_energy"], r["karmuk_sum"]), reverse=descending)

    def run_monte_carlo(self) -> Dict[str, Any]:
        best_value = -math.inf
        best_config: Dict[str, Any] = {}
        ensemble_scores: List[float] = []
        for run in range(max(1, self.runs)):
            perturb = random.uniform(-0.15, 0.15)
            scored = [self.score_case(case, perturb)["case_strength"] for case in self.cases]
            value = sum(scored) + self._score_fractal_burst(scored)
            ensemble_scores.append(value)
            if value > best_value:
                best_value = value
                best_config = {"run": run, "perturb": round(perturb, 4), "value": round(value, 4)}
        return {
            "runs": self.runs,
            "best_value": round(best_value, 4),
            "best_config": best_config,
            "ensemble_mean": round(mean(ensemble_scores), 4) if ensemble_scores else 0.0,
            "ensemble_std": round(statistics.pstdev(ensemble_scores), 4) if len(ensemble_scores) > 1 else 0.0,
        }

    def _score_fractal_burst(self, strengths: List[float]) -> float:
        if not strengths:
            return 0.0
        q = self._quantiles(strengths, [0.75, 0.9, 0.99])
        return q["q75"] * 0.25 + q["q90"] * 0.35 + q["q99"] * 0.55

    def rolling_karma(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        self.history.append({"timestamp": timestamp, **summary})
        if len(self.history) > self.history_length:
            self.history = self.history[-self.history_length:]
        karmuk_values = [entry.get("overall_karmuk", 0.0) for entry in self.history]
        return {
            "history_length": len(karmuk_values),
            "rolling_mean": round(mean(karmuk_values), 4) if karmuk_values else 0.0,
            "rolling_std": round(statistics.pstdev(karmuk_values), 4) if len(karmuk_values) > 1 else 0.0,
            "max_karmuk": round(max(karmuk_values), 4) if karmuk_values else 0.0,
            "min_karmuk": round(min(karmuk_values), 4) if karmuk_values else 0.0,
        }

    def karmuk_moments(self) -> Dict[str, float]:
        all_strengths = [entry.get("case_strength", 0.0) for entry in self.history]
        return self._quantiles(all_strengths, [0.5, 0.75, 0.9, 0.99])

    def compound_karmuk(self, base: float, rate: float, periods: int) -> float:
        return base * ((1.0 + rate) ** max(periods, 1))

    def build_summary(self) -> Dict[str, Any]:
        ranked = self.rank_cases()
        overall_karmuk = round(sum(item["karmuk_sum"] for item in ranked), 4)
        monte = self.run_monte_carlo()
        rolling = self.rolling_karma({"overall_karmuk": overall_karmuk})
        moments = self.karmuk_moments()
        return {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "case_count": len(self.cases),
            "overall_karmuk": overall_karmuk,
            "case_rankings": ranked,
            "monte_carlo": monte,
            "rolling_karma": rolling,
            "karmuk_moments": moments,
            "karmuk_compound_1w": round(self.compound_karmuk(overall_karmuk, 0.05, 7), 4),
            "karmuk_compound_1m": round(self.compound_karmuk(overall_karmuk, 0.10, 30), 4),
            "notes": "XinFit karma engine: rolling karmuk sums, Monte Carlo burst search, harmonic evidence aggregation, and multi-fractile moments.",
        }

    def export(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.build_summary(), indent=2), encoding="utf-8")
        return path


def sample_karmuk_cases() -> List[KarmaCase]:
    return [
        KarmaCase(
            case_id="CASE-001",
            title="Westside Cold Case",
            status="Open",
            category="Unsolved Homicide",
            components=[
                KarmaComponent(name="Forensic DNA", quality=0.92, confidence=0.94, freshness=0.68, weight=1.2),
                KarmaComponent(name="Witness Testimony", quality=0.55, confidence=0.50, freshness=0.42, weight=0.8),
                KarmaComponent(name="Digital Trail", quality=0.76, confidence=0.78, freshness=0.73, weight=1.0),
            ],
        ),
        KarmaCase(
            case_id="CASE-002",
            title="North Bay Unknown",
            status="Cold",
            category="Missing Person",
            components=[
                KarmaComponent(name="Fiber Trace", quality=0.62, confidence=0.64, freshness=0.38, weight=0.9),
                KarmaComponent(name="Video Footage", quality=0.70, confidence=0.74, freshness=0.48, weight=1.1),
            ],
        ),
        KarmaCase(
            case_id="CASE-003",
            title="South Loop Homicide",
            status="Open",
            category="Unsolved Homicide",
            components=[
                KarmaComponent(name="Ballistic Evidence", quality=0.88, confidence=0.90, freshness=0.60, weight=1.1),
                KarmaComponent(name="Cell Tower", quality=0.72, confidence=0.76, freshness=0.52, weight=1.0),
                KarmaComponent(name="Forensic Audio", quality=0.65, confidence=0.67, freshness=0.45, weight=0.95),
            ],
        ),
    ]


if __name__ == "__main__":
    cases = sample_karmuk_cases()
    engine = XinFitEngine(cases=cases, runs=1200, history_length=30)
    summary = engine.build_summary()
    out = Path(__file__).resolve().parent / "output" / "karmuk_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"XinFit karma summary written to {out}")
