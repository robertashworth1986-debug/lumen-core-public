from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import harmonic_mean
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class EvidenceComponent:
    name: str
    score: float
    confidence: float
    freshness: float
    details: Dict[str, Any] = field(default_factory=dict)

    def normalized_score(self) -> float:
        return max(0.0, min(1.0, self.score))

    def normalized_confidence(self) -> float:
        return max(0.0, min(1.0, self.confidence))

    def normalized_freshness(self) -> float:
        return max(0.0, min(1.0, self.freshness))


@dataclass
class CaseRecord:
    case_id: str
    title: str
    status: str
    category: str
    evidence: List[EvidenceComponent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "status": self.status,
            "category": self.category,
            "metadata": self.metadata,
            "evidence": [
                {
                    "name": c.name,
                    "score": c.score,
                    "confidence": c.confidence,
                    "freshness": c.freshness,
                    **c.details,
                }
                for c in self.evidence
            ],
        }


class HarmonicEvidenceEngine:
    def __init__(self, cases: Iterable[CaseRecord] | None = None):
        self.cases: List[CaseRecord] = list(cases or [])

    @staticmethod
    def _safe_harmonic(values: List[float], floor: float = 1e-6) -> float:
        positive = [max(v, floor) for v in values if v is not None]
        if not positive:
            return 0.0
        return harmonic_mean(positive)

    def add_case(self, case: CaseRecord) -> None:
        self.cases.append(case)

    def score_case(self, case: CaseRecord) -> Dict[str, float]:
        evidence_scores = [c.normalized_score() for c in case.evidence]
        evidence_confidence = [c.normalized_confidence() for c in case.evidence]
        evidence_freshness = [c.normalized_freshness() for c in case.evidence]

        completeness = self._safe_harmonic(evidence_scores) if evidence_scores else 0.0
        confidence = self._safe_harmonic(evidence_confidence) if evidence_confidence else 0.0
        freshness = self._safe_harmonic(evidence_freshness) if evidence_freshness else 0.0

        credibility = self._safe_harmonic([completeness, confidence, freshness])
        stability = max(0.0, min(1.0, (completeness + confidence + freshness) / 3.0))

        lead_quality = self._safe_harmonic([
            completeness * 0.5 + 0.5,
            confidence * 0.4 + 0.6,
            freshness * 0.3 + 0.7,
        ])

        case_strength = self._safe_harmonic([
            completeness * 0.6 + 0.4,
            confidence * 0.7 + 0.3,
            freshness * 0.5 + 0.5,
            stability,
        ])

        return {
            "case_strength": round(case_strength, 4),
            "credibility": round(credibility, 4),
            "stability": round(stability, 4),
            "lead_quality": round(lead_quality, 4),
            "completeness": round(completeness, 4),
            "confidence": round(confidence, 4),
            "freshness": round(freshness, 4),
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
                **metrics,
                "evidence_count": len(case.evidence),
                "raw_components": [c.name for c in case.evidence],
            })
        return scored

    def rank_cases(self, descending: bool = True) -> List[Dict[str, Any]]:
        scored = self.score_all()
        return sorted(scored, key=lambda row: row["case_strength"], reverse=descending)

    @staticmethod
    def hash_case(case: CaseRecord) -> str:
        payload = json.dumps(case.to_dict(), sort_keys=True).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def export_summary(self, output_path: Path) -> Path:
        payload = {
            "generated_utc": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "case_count": len(self.cases),
            "ranked_cases": self.rank_cases(),
            "categories": sorted({c.category for c in self.cases}),
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path


def sample_cold_case_data() -> List[CaseRecord]:
    return [
        CaseRecord(
            case_id="CASE-001",
            title="Westside Cold Case",
            status="Open",
            category="Unsolved Homicide",
            evidence=[
                EvidenceComponent(
                    name="Forensic DNA",
                    score=0.82,
                    confidence=0.92,
                    freshness=0.65,
                    details={"type": "DNA", "laboratory": "State Lab"},
                ),
                EvidenceComponent(
                    name="Witness Testimony",
                    score=0.45,
                    confidence=0.55,
                    freshness=0.30,
                    details={"source": "neighbor", "verified": False},
                ),
                EvidenceComponent(
                    name="Digital Footprint",
                    score=0.75,
                    confidence=0.80,
                    freshness=0.70,
                    details={"type": "phone location", "provider": "carrier"},
                ),
            ],
        ),
        CaseRecord(
            case_id="CASE-002",
            title="North Bay Unknown",
            status="Cold",
            category="Missing Person",
            evidence=[
                EvidenceComponent(
                    name="Forensic Trace",
                    score=0.58,
                    confidence=0.62,
                    freshness=0.40,
                    details={"type": "fiber", "laboratory": "Regional Lab"},
                ),
                EvidenceComponent(
                    name="Surveillance Video",
                    score=0.68,
                    confidence=0.70,
                    freshness=0.45,
                    details={"type": "camera", "location": "intersection"},
                ),
            ],
        ),
    ]
