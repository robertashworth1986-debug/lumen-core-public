"""One fixed, retrospective interval overlay. Not prospective evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import zipfile

import numpy as np

DAY = 86400
WINDOW = 28 * DAY
MIN_HIGH = 32
DELAY = 30 * 60
SOURCE_SHA = "a0c693328a3a614ee7646731b81497f7d5f4b33b5338c9fab0595797d1017a2d"
MANIFEST_SHA = "1c6fbd12624af70218f62f388660ba912185460d9cbfd40bdfcc15a5fad90a4d"
HERE = Path(__file__).resolve().parent


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def validate_protocol(protocol):
    expected = {"stations": ["41002", "42001", "44025", "46050", "46237"],
                "horizons_minutes": [60, 180, 360], "nominal_coverage": .9,
                "assumed_feedback_delay_minutes": DELAY//60,
                "history_window_days": WINDOW//DAY,
                "minimum_matured_high_regime_residuals": MIN_HIGH,
                "point_model": "delayed_blend_v01",
                "baseline_interval_method": "adaptive_scaled_28d",
                "candidate": "high_issue_conditional_radius_floor_v1",
                "fresh_holdout": False, "prospective_execution_allowed": False,
                "independent_validation": False}
    for key, value in expected.items():
        if type(protocol.get(key)) is not type(value) or protocol[key] != value:
            raise ValueError(f"Protocol/implementation mismatch: {key}")
    if protocol.get("scoring", {}).get("promotion_allowed") is not False:
        raise ValueError("Diagnostic cannot allow promotion")


def quantile_upper(values, probability=.9):
    a = np.asarray(values, dtype=float)
    if (a.ndim != 1 or not len(a) or not np.isfinite(a).all()
            or not 0 < probability < 1):
        raise ValueError("Invalid finite-rank quantile input")
    rank = min(len(a), max(1, math.ceil((len(a) + 1) * probability)))
    return float(np.partition(a, rank - 1)[rank - 1])


def overlay(at, target, truth, prediction, current, base_lo, base_hi, threshold, mean):
    arrays = [np.asarray(x) for x in [at, target, truth, prediction, current, base_lo, base_hi]]
    at, target, truth, prediction, current, base_lo, base_hi = arrays
    if not len(at) or any(x.ndim != 1 or len(x) != len(at) for x in arrays):
        raise ValueError("Mismatched or empty one-dimensional arrays")
    if (not np.isfinite(at).all() or not np.isfinite(target).all()
            or np.any(at != at.astype(np.int64)) or np.any(target != target.astype(np.int64))
            or np.any(np.diff(at) <= 0) or np.any(target <= at)):
        raise ValueError("Invalid timestamp chronology")
    if (not all(np.isfinite(x).all() for x in [prediction, current, base_lo, base_hi])
            or np.any(np.isinf(truth)) or np.any(truth[np.isfinite(truth)] < 0)
            or np.any(prediction < 0) or np.any(current < 0)
            or np.any(base_lo < 0) or np.any(base_lo > base_hi)
            or np.any(base_lo > prediction) or np.any(base_hi < prediction)
            or not math.isfinite(threshold) or threshold < 0
            or not math.isfinite(mean) or mean <= 0):
        raise ValueError("Invalid observations or interval parameters")
    high = current >= threshold
    scale = np.sqrt(1 + current / mean)
    error = np.abs(truth - prediction) / scale
    maturity = target + DELAY
    days = at.astype(np.int64) // DAY
    lo, hi = base_lo.copy(), base_hi.copy()
    counts = np.zeros(len(at), dtype=np.int64)
    latest = np.full(len(at), -1, dtype=np.int64)
    supported = np.zeros(len(at), dtype=bool)
    for day in np.unique(days):
        boundary = int(day) * DAY
        issued = np.flatnonzero(days == day)
        hist = np.flatnonzero(high & np.isfinite(truth)
                             & (at >= boundary - WINDOW) & (maturity < boundary))
        counts[issued] = len(hist)
        if len(hist):
            latest[issued] = int(maturity[hist].max())
        if len(hist) < MIN_HIGH:
            continue
        chosen = issued[high[issued]]
        supported[chosen] = True
        conditional_radius = quantile_upper(error[hist]) * scale[chosen]
        radius = np.maximum(base_hi[chosen] - prediction[chosen], conditional_radius)
        lo[chosen] = np.minimum(base_lo[chosen], np.maximum(0, prediction[chosen] - radius))
        hi[chosen] = np.maximum(base_hi[chosen], prediction[chosen] + radius)
    return {"lo": lo, "hi": hi, "calibration_n": counts,
            "latest_maturity": latest, "supported_high_issue": supported}


def metrics(truth, lo, hi, mask):
    n = int(mask.sum())
    if not n:
        return dict(n=0, coverage=None, interval_score=None, mean_width=None,
                    lower_misses=0, upper_misses=0)
    y, lower, upper = truth[mask], lo[mask], hi[mask]
    score = upper - lower + 20 * (np.maximum(lower-y, 0) + np.maximum(y-upper, 0))
    return dict(n=n, coverage=float(np.mean((lower <= y) & (y <= upper))),
                interval_score=float(score.mean()), mean_width=float((upper-lower).mean()),
                lower_misses=int((y < lower).sum()), upper_misses=int((y > upper).sum()))


def compare(y, base_lo, base_hi, result, mask):
    base = metrics(y, base_lo, base_hi, mask)
    candidate = metrics(y, result["lo"], result["hi"], mask)
    return {"baseline": base, "candidate": candidate,
            "coverage_change_percentage_points": 100*(candidate["coverage"]-base["coverage"]) if base["n"] else None,
            "interval_score_gain_pct": 100*(base["interval_score"]-candidate["interval_score"])/base["interval_score"] if base["n"] and base["interval_score"] else None,
            "width_change_pct": 100*(candidate["mean_width"]-base["mean_width"])/base["mean_width"] if base["n"] and base["mean_width"] else None}


def run(packet, out):
    protocol_path = HERE / "PROTOCOL.json"
    protocol = json.loads(protocol_path.read_text())
    validate_protocol(protocol)
    source = packet / "inputs/energy-stage4-ci.zip"
    results = packet / "results"
    if digest(source) != SOURCE_SHA or digest(results / "SHA256_MANIFEST.json") != MANIFEST_SHA:
        raise ValueError("Frozen input identity mismatch")
    manifest = json.loads((results / "SHA256_MANIFEST.json").read_text())
    for row in manifest["files"]:
        p = results / row["file"]
        if p.stat().st_size != row["bytes"] or digest(p) != row["sha256"]:
            raise ValueError("Frozen result inventory mismatch")
    if out.exists():
        raise ValueError("Output must be new; do not overwrite prior execution")
    out.mkdir(parents=True)
    records = []
    with zipfile.ZipFile(source) as archive:
        for station in protocol["stations"]:
            for horizon in protocol["horizons_minutes"]:
                cfg = json.loads(archive.read(f"results/calibration_{station}_{horizon}m.json"))
                with np.load(results / f"intervals_{station}_{horizon}m.npz", allow_pickle=False) as loaded:
                    a = {k: loaded[k] for k in loaded.files}
                at, target, truth, current, prediction = [a[k] for k in ["issue_epoch", "target_epoch", "truth", "current_proxy", "delayed_blend_v01"]]
                good = a["scored_mask"]
                if good.dtype != bool or np.any(target-at != horizon*60):
                    raise ValueError("Frozen mask or horizon invalid")
                prefix = "delayed_blend_v01_30m_"
                base_lo, base_hi = a[prefix+"lo"][:, 3], a[prefix+"hi"][:, 3]
                high = current >= cfg["high_activity_threshold"]
                result = overlay(at, target, truth, prediction, current, base_lo, base_hi,
                                 cfg["high_activity_threshold"], cfg["ridge"]["mean"][0])
                if not (np.array_equal(result["lo"][~high], base_lo[~high])
                        and np.array_equal(result["hi"][~high], base_hi[~high])):
                    raise ValueError("Ordinary issue bounds changed")
                months = at.astype("datetime64[s]").astype("datetime64[M]").astype(int) % 12 + 1
                hg = good & high
                alpha = a[prefix+"alpha"]
                row = {"station": station, "horizon_minutes": horizon,
                       "overall": compare(truth, base_lo, base_hi, result, good),
                       "high_at_issue": compare(truth, base_lo, base_hi, result, hg),
                       "ordinary_at_issue": compare(truth, base_lo, base_hi, result, good & ~high),
                       "months": {str(m): {"overall": compare(truth, base_lo, base_hi, result, good & (months == m)), "high_at_issue": compare(truth, base_lo, base_hi, result, hg & (months == m))} for m in range(1, 13)},
                       "high_issue_days": len(np.unique(at[hg] // DAY)),
                       "high_issue_7day_calendar_blocks": len(np.unique((at[hg] // DAY) // 7)),
                       "high_issues_supported": int((hg & result["supported_high_issue"]).sum()),
                       "high_issues_fallback": int((hg & ~result["supported_high_issue"]).sum()),
                       "high_issues_widened": int((hg & ((result["hi"] > base_hi) | (result["lo"] < base_lo))).sum()),
                       "original_high_cold_start_fraction": float(a[prefix+"cold"][hg].mean()) if hg.any() else None,
                       "original_high_alpha_floor_fraction": float((alpha[hg] <= .02).mean()) if hg.any() else None,
                       "original_high_alpha_ceiling_fraction": float((alpha[hg] >= .25).mean()) if hg.any() else None,
                       "ordinary_bounds_exactly_unchanged": True,
                       "promotion_allowed": False}
                records.append(row)
                np.savez_compressed(out / f"overlay_{station}_{horizon}m.npz", **result)
    summary = {"schema_version": "1.0", "classification": protocol["classification"],
               "protocol_sha256": digest(protocol_path), "runner_sha256": digest(__file__),
               "source_sha256": SOURCE_SHA, "stage6_manifest_sha256": MANIFEST_SHA,
               "python": platform.python_version(), "numpy": np.__version__,
               "cells": len(records), "paired_targets": sum(r["overall"]["baseline"]["n"] for r in records),
               "high_cells_at_or_above_90pct_before": sum(r["high_at_issue"]["baseline"]["coverage"] >= .9 for r in records),
               "high_cells_at_or_above_90pct_after": sum(r["high_at_issue"]["candidate"]["coverage"] >= .9 for r in records),
               "overall_interval_score_improved_cells": sum(r["overall"]["interval_score_gain_pct"] > 0 for r in records),
               "overall_interval_score_worsened_cells": sum(r["overall"]["interval_score_gain_pct"] < 0 for r in records),
               "median_high_coverage_before": float(np.median([r["high_at_issue"]["baseline"]["coverage"] for r in records])),
               "median_high_coverage_after": float(np.median([r["high_at_issue"]["candidate"]["coverage"] for r in records])),
               "median_overall_interval_score_gain_pct": float(np.median([r["overall"]["interval_score_gain_pct"] for r in records])),
               "median_overall_width_change_pct": float(np.median([r["overall"]["width_change_pct"] for r in records])),
               "promotion_allowed": False, "fresh_holdout": False, "prospective_execution_allowed": False,
               "interpretation": "Dependent retrospective diagnostic on already consumed 2025 observations. Assumed 30-minute latency, no actual retrieval/seal chronology. No conditional coverage guarantee, physical benefit, independent validation or promotion.",
               "records": records}
    (out / "result.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    output_manifest = [{"file": p.name, "bytes": p.stat().st_size, "sha256": digest(p)} for p in sorted(out.iterdir()) if p.is_file()]
    (out / "OUTPUT_MANIFEST.json").write_text(json.dumps(output_manifest, indent=2)+"\n")
    return {k: v for k, v in summary.items() if k != "records"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.packet, args.out), indent=2, allow_nan=False))
