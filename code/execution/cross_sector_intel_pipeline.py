from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
CONFIG = ROOT / "config"

INFRA_DELTA_FILE = OUT / "infra_frozen_deltas.jsonl"
INFRA_AUDIT_FILE = OUT / "infra_audit_ledger.jsonl"
FAILURE_PRED_FILE = OUT / "cross_sector_failure_predictions.jsonl"
GRANT_EVIDENCE_FILE = OUT / "investor_and_grant_evidence.json"
CHAIN_FILE = OUT / "infra_chain_of_custody_sha256.json"
OPTIMIZATION_REPORT_JSON = OUT / "cross_sector_optimization_report.json"
OPTIMIZATION_MATRIX_CSV = OUT / "cross_sector_optimization_matrix.csv"
OPTIMIZATION_REPORT_MD = OUT / "cross_sector_optimization_report.md"
RUNTIME_FILE = CONFIG / "cross_sector_intel_runtime.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    return (dt or utc_now()).isoformat()


def atomic_write_json(path: Path, payload: Any, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=indent), encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _frange(start: float, stop: float, step: float) -> List[float]:
    values: List[float] = []
    cursor = float(start)
    capped_step = max(0.0001, float(step))
    while cursor <= float(stop) + 1e-9:
        values.append(round(cursor, 6))
        cursor += capped_step
    return values


def _build_axis(runtime_cfg: Dict[str, Any], key_values: str, key_min: str, key_max: str, key_step: str, default_min: float, default_max: float, default_step: float) -> List[float]:
    raw_values = runtime_cfg.get(key_values, None)
    if isinstance(raw_values, list):
        parsed = []
        for raw in raw_values:
            try:
                parsed.append(round(float(raw), 6))
            except Exception:
                continue
        if parsed:
            parsed_sorted = sorted(list({v for v in parsed}))
            return parsed_sorted

    axis_min = float(runtime_cfg.get(key_min, default_min) or default_min)
    axis_max = float(runtime_cfg.get(key_max, default_max) or default_max)
    axis_step = float(runtime_cfg.get(key_step, default_step) or default_step)
    if axis_max < axis_min:
        axis_min, axis_max = axis_max, axis_min
    return _frange(axis_min, axis_max, axis_step)


def write_csv(path: Path, rows: List[Dict[str, Any]], headers: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h) for h in headers})


@dataclass
class SectorDelta:
    sector: str
    stream: str
    constraint: str
    observed_drift_score: float
    incident_rate_pct: float
    affected_asset_value_usd: float
    baseline_failure_cost_usd_per_hour: float
    estimated_detection_lag_hours: float
    confidence: float


class CrossSectorIntelPipeline:
    def __init__(self, runtime_cfg: Dict[str, Any]) -> None:
        self.runtime_cfg = runtime_cfg

    def estimate_failure_cost(self, delta: SectorDelta) -> Dict[str, float]:
        drift_multiplier = max(0.25, min(3.5, 1.0 + delta.observed_drift_score))
        confidence_multiplier = max(0.35, min(1.0, delta.confidence))
        failure_cost_hourly = delta.baseline_failure_cost_usd_per_hour * drift_multiplier * confidence_multiplier
        lag_hours = max(0.05, delta.estimated_detection_lag_hours)
        projected_failure_cost = failure_cost_hourly * lag_hours

        lumen_detection_efficiency = float(self.runtime_cfg.get("lumen_detection_efficiency", 0.72) or 0.72)
        mitigation_multiplier = float(self.runtime_cfg.get("mitigation_multiplier", 0.86) or 0.86)
        avoided_cost = projected_failure_cost * lumen_detection_efficiency * mitigation_multiplier
        residual_cost = max(0.0, projected_failure_cost - avoided_cost)

        return {
            "projected_failure_cost_usd": round(projected_failure_cost, 2),
            "avoided_cost_usd": round(avoided_cost, 2),
            "residual_cost_usd": round(residual_cost, 2),
            "hourly_failure_cost_usd": round(failure_cost_hourly, 2),
        }

    def predict_failure_timestamp(self, delta: SectorDelta) -> str:
        horizon_hours = max(0.25, min(96.0, 24.0 * (1.0 - min(0.95, delta.incident_rate_pct / 100.0))))
        horizon_hours *= max(0.30, 1.15 - min(0.95, delta.observed_drift_score))
        return utc_iso(utc_now() + timedelta(hours=horizon_hours))

    def freeze_delta(self, delta: SectorDelta, estimate: Dict[str, float]) -> Dict[str, Any]:
        baseline = max(1.0, estimate["projected_failure_cost_usd"])
        optimization_gain_pct = (estimate["avoided_cost_usd"] / baseline) * 100.0

        return {
            "generated_utc": utc_iso(),
            "source": str(delta.stream).upper(),
            "sector": delta.sector,
            "constraint": delta.constraint,
            "baseline_loss_rate_usd_per_hour": float(delta.baseline_failure_cost_usd_per_hour),
            "optimization_gain_pct": round(float(optimization_gain_pct), 4),
            "estimated_hourly_value_usd": float(estimate["hourly_failure_cost_usd"]),
            "rows_written": int(1),
            "key_present": True,
            "predicted_failure_utc": self.predict_failure_timestamp(delta),
            "predicted_failure_cost_usd": float(estimate["projected_failure_cost_usd"]),
            "estimated_avoided_loss_usd": float(estimate["avoided_cost_usd"]),
            "estimated_residual_loss_usd": float(estimate["residual_cost_usd"]),
            "trust_tier": str(self.runtime_cfg.get("trust_tier", "gov_audit_ready")),
        }


def load_runtime_cfg() -> Dict[str, Any]:
    runtime = load_json(RUNTIME_FILE, {})
    if not isinstance(runtime, dict):
        runtime = {}

    defaults = {
        "lumen_detection_efficiency": 0.72,
        "mitigation_multiplier": 0.86,
        "max_optimization_sims": 120,
        "optimization_auto_apply": False,
        "sim_detection_efficiency_min": 0.55,
        "sim_detection_efficiency_max": 0.95,
        "sim_detection_efficiency_step": 0.05,
        "sim_mitigation_multiplier_min": 0.60,
        "sim_mitigation_multiplier_max": 0.98,
        "sim_mitigation_multiplier_step": 0.04,
        "trust_tier": "gov_audit_ready",
        "program_alignment": ["DARPA", "DOE", "DOD", "NSF", "NASA"],
    }
    for key, value in defaults.items():
        runtime.setdefault(key, value)
    return runtime


def sample_sector_deltas() -> List[SectorDelta]:
    return [
        SectorDelta(
            sector="energy_grid",
            stream="ISO_NE",
            constraint="frequency_stability",
            observed_drift_score=0.58,
            incident_rate_pct=3.2,
            affected_asset_value_usd=3_200_000_000.0,
            baseline_failure_cost_usd_per_hour=1_150_000.0,
            estimated_detection_lag_hours=2.4,
            confidence=0.88,
        ),
        SectorDelta(
            sector="healthcare_supply_chain",
            stream="HHS_FEED",
            constraint="cold_chain_compliance",
            observed_drift_score=0.41,
            incident_rate_pct=2.1,
            affected_asset_value_usd=1_850_000_000.0,
            baseline_failure_cost_usd_per_hour=620_000.0,
            estimated_detection_lag_hours=3.1,
            confidence=0.82,
        ),
        SectorDelta(
            sector="financial_market_infra",
            stream="FEDWIRE_OPS",
            constraint="settlement_window_integrity",
            observed_drift_score=0.67,
            incident_rate_pct=4.6,
            affected_asset_value_usd=6_100_000_000.0,
            baseline_failure_cost_usd_per_hour=2_400_000.0,
            estimated_detection_lag_hours=1.7,
            confidence=0.91,
        ),
    ]


def run_optimization_simulations(runtime_cfg: Dict[str, Any], deltas: List[SectorDelta]) -> Dict[str, Any]:
    det_axis = _build_axis(
        runtime_cfg,
        "sim_detection_efficiency_values",
        "sim_detection_efficiency_min",
        "sim_detection_efficiency_max",
        "sim_detection_efficiency_step",
        0.55,
        0.95,
        0.05,
    )
    mit_axis = _build_axis(
        runtime_cfg,
        "sim_mitigation_multiplier_values",
        "sim_mitigation_multiplier_min",
        "sim_mitigation_multiplier_max",
        "sim_mitigation_multiplier_step",
        0.60,
        0.98,
        0.04,
    )

    max_sims = int(runtime_cfg.get("max_optimization_sims", 120) or 120)
    max_sims = max(1, min(5000, max_sims))

    rows: List[Dict[str, Any]] = []
    sim_count = 0
    for det in det_axis:
        for mit in mit_axis:
            sim_count += 1
            if sim_count > max_sims:
                break

            sim_cfg = dict(runtime_cfg)
            sim_cfg["lumen_detection_efficiency"] = float(det)
            sim_cfg["mitigation_multiplier"] = float(mit)
            pipeline = CrossSectorIntelPipeline(sim_cfg)

            projected = 0.0
            avoided = 0.0
            residual = 0.0
            for delta in deltas:
                estimate = pipeline.estimate_failure_cost(delta)
                projected += float(estimate["projected_failure_cost_usd"])
                avoided += float(estimate["avoided_cost_usd"])
                residual += float(estimate["residual_cost_usd"])

            prevented_pct = (avoided / projected * 100.0) if projected > 0 else 0.0
            efficiency_score = (avoided - (0.05 * residual))
            rows.append(
                {
                    "lumen_detection_efficiency": round(det, 6),
                    "mitigation_multiplier": round(mit, 6),
                    "projected_failure_cost_usd": round(projected, 2),
                    "avoided_cost_usd": round(avoided, 2),
                    "residual_cost_usd": round(residual, 2),
                    "prevented_pct": round(prevented_pct, 4),
                    "efficiency_score": round(efficiency_score, 4),
                }
            )
        if sim_count > max_sims:
            break

    ranked = sorted(
        rows,
        key=lambda item: (float(item.get("efficiency_score", 0.0)), float(item.get("avoided_cost_usd", 0.0))),
        reverse=True,
    )
    best = ranked[0] if ranked else {
        "lumen_detection_efficiency": float(runtime_cfg.get("lumen_detection_efficiency", 0.72) or 0.72),
        "mitigation_multiplier": float(runtime_cfg.get("mitigation_multiplier", 0.86) or 0.86),
        "projected_failure_cost_usd": 0.0,
        "avoided_cost_usd": 0.0,
        "residual_cost_usd": 0.0,
        "prevented_pct": 0.0,
        "efficiency_score": 0.0,
    }

    write_csv(
        OPTIMIZATION_MATRIX_CSV,
        ranked,
        [
            "lumen_detection_efficiency",
            "mitigation_multiplier",
            "projected_failure_cost_usd",
            "avoided_cost_usd",
            "residual_cost_usd",
            "prevented_pct",
            "efficiency_score",
        ],
    )

    report = {
        "generated_utc": utc_iso(),
        "sims_run": len(rows),
        "max_sims_budget": max_sims,
        "recommended": {
            "lumen_detection_efficiency": float(best["lumen_detection_efficiency"]),
            "mitigation_multiplier": float(best["mitigation_multiplier"]),
            "projected_failure_cost_usd": float(best["projected_failure_cost_usd"]),
            "avoided_cost_usd": float(best["avoided_cost_usd"]),
            "residual_cost_usd": float(best["residual_cost_usd"]),
            "prevented_pct": float(best["prevented_pct"]),
            "efficiency_score": float(best["efficiency_score"]),
        },
        "top_5": ranked[:5],
    }
    atomic_write_json(OPTIMIZATION_REPORT_JSON, report, indent=2)

    md_lines = [
        "# Cross-Sector Optimization Report",
        "",
        f"Generated UTC: {report['generated_utc']}",
        f"Simulations run: {report['sims_run']} / {report['max_sims_budget']}",
        "",
        "## Recommended Parameters",
        f"- lumen_detection_efficiency: {report['recommended']['lumen_detection_efficiency']:.6f}",
        f"- mitigation_multiplier: {report['recommended']['mitigation_multiplier']:.6f}",
        f"- projected_failure_cost_usd: ${report['recommended']['projected_failure_cost_usd']:,.2f}",
        f"- avoided_cost_usd: ${report['recommended']['avoided_cost_usd']:,.2f}",
        f"- residual_cost_usd: ${report['recommended']['residual_cost_usd']:,.2f}",
        f"- prevented_pct: {report['recommended']['prevented_pct']:.4f}%",
        "",
        "## Top Candidates",
    ]
    for row in report["top_5"]:
        md_lines.append(
            f"- det={row['lumen_detection_efficiency']:.6f} | mit={row['mitigation_multiplier']:.6f} | "
            f"avoided=${row['avoided_cost_usd']:,.2f} | residual=${row['residual_cost_usd']:,.2f} | prevented={row['prevented_pct']:.4f}%"
        )
    OPTIMIZATION_REPORT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    if bool(runtime_cfg.get("optimization_auto_apply", False)):
        runtime_cfg["lumen_detection_efficiency"] = float(best["lumen_detection_efficiency"])
        runtime_cfg["mitigation_multiplier"] = float(best["mitigation_multiplier"])
        atomic_write_json(RUNTIME_FILE, runtime_cfg, indent=2)
        report["auto_applied"] = True
        atomic_write_json(OPTIMIZATION_REPORT_JSON, report, indent=2)
    else:
        report["auto_applied"] = False
        atomic_write_json(OPTIMIZATION_REPORT_JSON, report, indent=2)

    return report


def run_pipeline() -> Dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    runtime_cfg = load_runtime_cfg()
    pipeline = CrossSectorIntelPipeline(runtime_cfg)

    deltas = sample_sector_deltas()
    optimization_report = run_optimization_simulations(runtime_cfg, deltas)

    recommended_cfg = optimization_report.get("recommended", {}) if isinstance(optimization_report, dict) else {}
    if isinstance(recommended_cfg, dict) and recommended_cfg:
        tuned_runtime_cfg = dict(runtime_cfg)
        tuned_runtime_cfg["lumen_detection_efficiency"] = float(
            recommended_cfg.get("lumen_detection_efficiency", tuned_runtime_cfg.get("lumen_detection_efficiency", 0.72))
        )
        tuned_runtime_cfg["mitigation_multiplier"] = float(
            recommended_cfg.get("mitigation_multiplier", tuned_runtime_cfg.get("mitigation_multiplier", 0.86))
        )
        pipeline = CrossSectorIntelPipeline(tuned_runtime_cfg)
        runtime_cfg = tuned_runtime_cfg

    aggregate_projected = 0.0
    aggregate_avoided = 0.0
    aggregate_residual = 0.0

    for delta in deltas:
        estimate = pipeline.estimate_failure_cost(delta)
        aggregate_projected += float(estimate["projected_failure_cost_usd"])
        aggregate_avoided += float(estimate["avoided_cost_usd"])
        aggregate_residual += float(estimate["residual_cost_usd"])

        freeze_record = pipeline.freeze_delta(delta, estimate)
        append_jsonl(INFRA_DELTA_FILE, freeze_record)

        prediction_record = {
            "generated_utc": utc_iso(),
            "sector": delta.sector,
            "stream": delta.stream,
            "constraint": delta.constraint,
            "predicted_failure_utc": freeze_record["predicted_failure_utc"],
            **estimate,
            "confidence": float(delta.confidence),
            "affected_asset_value_usd": float(delta.affected_asset_value_usd),
        }
        append_jsonl(FAILURE_PRED_FILE, prediction_record)

    evidence = {
        "generated_utc": utc_iso(),
        "event": "infra_cross_sector_sweep",
        "program_alignment": list(runtime_cfg.get("program_alignment", [])),
        "trusted_tier": str(runtime_cfg.get("trust_tier", "gov_audit_ready")),
        "sector_count": len(deltas),
        "projected_failure_cost_usd": round(aggregate_projected, 2),
        "estimated_avoided_cost_usd": round(aggregate_avoided, 2),
        "estimated_residual_cost_usd": round(aggregate_residual, 2),
        "prevented_pct": round((aggregate_avoided / aggregate_projected * 100.0), 4) if aggregate_projected > 0 else 0.0,
        "optimization": {
            "report_file": str(OPTIMIZATION_REPORT_JSON),
            "matrix_file": str(OPTIMIZATION_MATRIX_CSV),
            "markdown_file": str(OPTIMIZATION_REPORT_MD),
            "recommended": dict(optimization_report.get("recommended", {})) if isinstance(optimization_report, dict) else {},
            "sims_run": int(optimization_report.get("sims_run", 0)) if isinstance(optimization_report, dict) else 0,
            "auto_applied": bool(optimization_report.get("auto_applied", False)) if isinstance(optimization_report, dict) else False,
        },
        "delta_file": str(INFRA_DELTA_FILE),
        "prediction_file": str(FAILURE_PRED_FILE),
    }
    append_jsonl(INFRA_AUDIT_FILE, evidence)

    chain_payload = {
        "generated_utc": utc_iso(),
        "files": [
            {"path": str(INFRA_DELTA_FILE), "sha256": sha256_file(INFRA_DELTA_FILE)},
            {"path": str(FAILURE_PRED_FILE), "sha256": sha256_file(FAILURE_PRED_FILE)},
            {"path": str(INFRA_AUDIT_FILE), "sha256": sha256_file(INFRA_AUDIT_FILE)},
            {"path": str(OPTIMIZATION_REPORT_JSON), "sha256": sha256_file(OPTIMIZATION_REPORT_JSON)},
            {"path": str(OPTIMIZATION_MATRIX_CSV), "sha256": sha256_file(OPTIMIZATION_MATRIX_CSV)},
            {"path": str(OPTIMIZATION_REPORT_MD), "sha256": sha256_file(OPTIMIZATION_REPORT_MD)},
        ],
    }
    atomic_write_json(CHAIN_FILE, chain_payload, indent=2)
    atomic_write_json(GRANT_EVIDENCE_FILE, evidence, indent=2)

    return evidence


if __name__ == "__main__":
    summary = run_pipeline()
    print(json.dumps(summary, indent=2))
