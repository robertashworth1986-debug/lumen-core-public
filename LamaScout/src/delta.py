from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from .settings import REP, utc_now


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_text(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return _sha256_bytes(payload)


def _numeric_keys(payload: Dict[str, Any]) -> List[str]:
    return [
        key for key, value in payload.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]


def compute_delta_metrics(current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
    if previous is None:
        return {
            "changes": {},
            "delta_size": 0,
            "energy": 0.0,
            "stability_score": 100.0,
        }

    keys = [key for key in _numeric_keys(current) if key in previous]
    if not keys:
        return {
            "changes": {},
            "delta_size": 0,
            "energy": 0.0,
            "stability_score": 100.0,
        }

    changes: Dict[str, Dict[str, float]] = {}
    total_energy = 0.0
    for key in keys:
        current_value = float(current.get(key, 0.0))
        previous_value = float(previous.get(key, 0.0))
        delta = abs(current_value - previous_value)
        if previous_value == 0.0:
            change_pct = 1.0 if delta > 0 else 0.0
        else:
            change_pct = abs(delta / previous_value)
        changes[key] = {
            "current": current_value,
            "previous": previous_value,
            "delta": delta,
            "change_pct": min(change_pct, 1.0),
        }
        total_energy += min(change_pct, 1.0)

    energy = min(100.0, total_energy / len(keys) * 100.0)
    stability_score = max(0.0, 100.0 - energy)
    delta_size = sum(1 for change in changes.values() if change["delta"] != 0.0)
    return {
        "changes": changes,
        "delta_size": delta_size,
        "energy": float(energy),
        "stability_score": float(stability_score),
    }


class DeltaEngine:
    def __init__(self, mirror_file: Path | None = None):
        self.path = mirror_file or (REP / "delta_history.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        try:
            if self.path.exists():
                return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save_history(self) -> None:
        self.path.write_text(json.dumps(self.history, indent=2), encoding="utf-8")

    def freeze(self, payload: Dict[str, Any], entity: str = "truth") -> Dict[str, Any]:
        checksum = hash_text(payload)
        previous = self.history[-1] if self.history else None
        metrics = compute_delta_metrics(payload, previous or {})
        record = {
            "entity": entity,
            "generated_utc": payload.get("generated_utc", utc_now()),
            "checksum": checksum,
            "previous_checksum": previous.get("checksum") if previous else None,
            "delta_size": metrics["delta_size"],
            "truth_energy": metrics["energy"],
            "stability_score": metrics["stability_score"],
            "changes": metrics["changes"],
        }
        self.history.append(record)
        self._save_history()
        return record

    def rolling_stats(self, length: int = 20) -> Dict[str, Any]:
        window = self.history[-length:]
        if not window:
            return {"history_length": 0, "average_energy": 0.0, "average_stability": 100.0}
        energies = [entry.get("truth_energy", 0.0) for entry in window]
        stabilities = [entry.get("stability_score", 100.0) for entry in window]
        return {
            "history_length": len(window),
            "average_energy": float(sum(energies) / len(energies)),
            "average_stability": float(sum(stabilities) / len(stabilities)),
        }
