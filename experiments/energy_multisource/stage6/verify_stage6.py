"""Recompute Stage 6 evidence from pinned inputs and retained interval arrays.

This replays the retained algorithm and audits numerical/report consistency,
not independent validation of that algorithm. Reused 2025 stays diagnostic.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import itertools
import json
import math
from pathlib import Path
import zipfile

import numpy as np

_spec = importlib.util.spec_from_file_location("stage6_recompute", Path(__file__).with_name("run_stage6.py"))
s6 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s6)
IDENTITY = ["station", "horizon_minutes", "point_model", "interval_method", "feedback_delay_minutes"]
MIN_REGIME_N = 100  # inherited descriptive slice floor, not independent sample size
RECORD_FIELDS = set(IDENTITY) | {"paired_origin_sha256", "eligible_origins", "overall",
    "high_at_issue", "high_realized_target", "quarters", "months", "initial_radius_fraction",
    "alpha_at_bound_fraction", "current_activity_threshold", "promotion_allowed"}
COMPARISON_FIELDS = set(IDENTITY[:-1]) | {"n", "paired_origin_sha256", "interval_score_gain_pct",
    "ci7_day_pct", "ci14_day_pct", "coverage", "baseline_coverage", "width_change_pct",
    "high_at_issue_n", "high_at_issue_coverage", "promotion_allowed"}
CSV_FIELDS = IDENTITY + ["n", "coverage", "mean_width", "interval_score", "high_at_issue_n", "high_at_issue_coverage"]


def strict_json(path_or_text, *, text=False):
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise ValueError(f"Duplicate JSON key: {k}")
            obj[k] = v
        return obj
    def invalid(v):
        raise ValueError(f"Nonfinite JSON value: {v}")
    return json.loads(path_or_text if text else Path(path_or_text).read_text(encoding="utf-8"),
                      object_pairs_hook=unique, parse_constant=invalid)


def close(actual, expected, context):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"Metric schema mismatch: {context}")
        for key in expected:
            close(actual[key], expected[key], f"{context}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"Sequence schema mismatch: {context}")
        for i, value in enumerate(expected):
            close(actual[i], value, f"{context}[{i}]")
    elif isinstance(expected, bool):
        if type(actual) is not bool or actual is not expected:
            raise ValueError(f"Boolean identity mismatch: {context}")
    elif expected is None:
        if actual is not None:
            raise ValueError(f"Empty metric misrepresented: {context}")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if (isinstance(actual, bool) or not isinstance(actual, (int, float))
                or not math.isfinite(actual)
                or not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10)):
            raise ValueError(f"Recomputed metric mismatch: {context}")
    elif actual != expected:
        raise ValueError(f"Identity mismatch: {context}")


def index_cells(rows, comparison=False):
    expected = set(itertools.product(s6.STATIONS, s6.HORIZONS, s6.MODELS,
                                     s6.METHODS[1:] if comparison else s6.METHODS,
                                     [30] if comparison else s6.DELAYS))
    indexed = {}
    if not isinstance(rows, list):
        raise ValueError("Result records must be a list")
    for row in rows:
        if not isinstance(row, dict) or set(row) != (COMPARISON_FIELDS if comparison else RECORD_FIELDS):
            raise ValueError("Result record schema mismatch")
        if type(row["horizon_minutes"]) is not int or (not comparison and type(row["feedback_delay_minutes"]) is not int):
            raise ValueError("Result identity type mismatch")
        key = tuple(row.get(k, 30 if comparison and k == "feedback_delay_minutes" else None) for k in IDENTITY)
        if key not in expected or key in indexed:
            raise ValueError("Duplicate, unknown or malformed result cell")
        if row.get("promotion_allowed") is not False:
            raise ValueError("Reused results cannot authorize promotion")
        indexed[key] = row
    if set(indexed) != expected:
        raise ValueError("Missing required result cells")
    return indexed


def descriptive_slice(y, lo, hi, mask):
    n = int(mask.sum())
    hits = int(((lo <= y) & (y <= hi) & mask).sum())
    coverage = hits / n if n else None
    return {"n": n, "hits": hits, "misses": n - hits, "coverage": coverage,
            "coverage_deficit_percentage_points": max(0., 100 * (.9 - coverage)) if n else None,
            "state": ("INSUFFICIENT_REGIME_EVIDENCE" if n < MIN_REGIME_N else
                      "EMPIRICAL_TARGET_MISSED" if coverage < .9 else "TARGET_MET_DESCRIPTIVELY")}


def concentration(y, lo, hi, good, high):
    all_s = descriptive_slice(y, lo, hi, good)
    hi_s = descriptive_slice(y, lo, hi, good & high)
    low_s = descriptive_slice(y, lo, hi, good & ~high)
    high_miss = hi_s["misses"] / hi_s["n"] if hi_s["n"] else None
    low_miss = low_s["misses"] / low_s["n"] if low_s["n"] else None
    return {"overall": all_s, "high_at_issue": hi_s, "ordinary_at_issue": low_s,
            "high_issue_fraction": hi_s["n"] / all_s["n"] if all_s["n"] else None,
            "high_share_of_all_misses": hi_s["misses"] / all_s["misses"] if all_s["misses"] else None,
            "high_to_ordinary_miss_rate_ratio": high_miss / low_miss if high_miss is not None and low_miss else None}


def load_npz(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if (len(names) != len(set(names)) or len(names) != 31
                or sum(i.file_size for i in archive.infolist()) > 80_000_000):
            raise ValueError("NPZ member count or resource bound failed")
    with np.load(path, allow_pickle=False) as loaded:
        expected = {"issue_epoch", "target_epoch", "truth", "scored_mask", "current_proxy", *s6.MODELS}
        expected |= {f"{model}_{delay}m_{field}" for model in s6.MODELS for delay in s6.DELAYS
                     for field in ["lo", "hi", "cold", "latest", "alpha", "clipped"]}
        if set(loaded.files) != expected:
            raise ValueError("NPZ array inventory mismatch")
        return {k: loaded[k] for k in loaded.files}


def same_array(actual, expected, label):
    if actual.shape != expected.shape or not np.array_equal(actual, expected, equal_nan=True):
        raise ValueError(f"Frozen input or mask mismatch: {label}")


def verify_results(results: Path, source_zip: Path | None = None) -> dict:
    results = Path(results)
    source_zip = source_zip or results.parent / "inputs" / "energy-stage4-ci.zip"
    if source_zip.is_symlink() or source_zip.stat().st_size != s6.SOURCE_BYTES or s6.digest(source_zip) != s6.SOURCE_SHA:
        raise ValueError("Frozen source archive identity mismatch")
    summary = strict_json(results / "summary.json")
    for key, expected in {"schema_version": "1.0", "experiment": "stage6_interval_assurance_diagnostic_20260905",
            "protocol_commit": s6.PROTOCOL_COMMIT, "source_sha256": s6.SOURCE_SHA,
            "classification": "REUSED_2025_ENGINEERING_DIAGNOSTIC", "promotion_allowed": False,
            "interval_records": 240, "descriptive_comparisons": 90,
            "methods": s6.METHODS, "point_models": s6.MODELS}.items():
        close(summary.get(key), expected, key)
    records = index_cells(strict_json(results / "interval_metrics.json"))
    comparisons = index_cells(strict_json(results / "comparisons.json"), comparison=True)
    assessments, audits = [], []
    with zipfile.ZipFile(source_zip) as prior:
        if len(prior.namelist()) != len(set(prior.namelist())):
            raise ValueError("Duplicate frozen source members")
        for sid, horizon in itertools.product(s6.STATIONS, s6.HORIZONS):
            original = np.genfromtxt(io.BytesIO(prior.read(f"results/predictions_{sid}_{horizon}m.csv")),
                                     delimiter=",", names=True, dtype=float)
            cfg = strict_json(prior.read(f"results/calibration_{sid}_{horizon}m.json").decode(), text=True)
            a = load_npz(results / f"intervals_{sid}_{horizon}m.npz")
            at, target, y, current = (a[k] for k in ["issue_epoch", "target_epoch", "truth", "current_proxy"])
            for k, src in [("issue_epoch", "issue_epoch"), ("target_epoch", "target_epoch"),
                           ("truth", "truth"), ("current_proxy", "persistence"), *[(m, m) for m in s6.MODELS]]:
                same_array(a[k], original[src], k)
            if np.any(target - at != horizon * 60):
                raise ValueError("Target horizon mismatch")
            n = len(at)
            good = np.isfinite(y) & (at >= s6.START) & (target < s6.END)
            same_array(a["scored_mask"], good, "scored_mask")
            if a["scored_mask"].dtype != bool or at.dtype.kind not in "iu" or target.dtype.kind not in "iu":
                raise ValueError("Invalid mask or timestamp types")
            origin = hashlib.sha256(np.column_stack([at[good], target[good]]).astype("<i8").tobytes()).hexdigest()
            threshold = float(cfg["high_activity_threshold"])
            if not math.isfinite(threshold) or threshold < 0:
                raise ValueError("Invalid frozen regime threshold")
            high = current >= threshold
            months = at.astype("datetime64[s]").astype("datetime64[M]").astype(int) % 12 + 1
            max_replay_error = 0.
            for pi, model in enumerate(s6.MODELS):
                s6.validate_series(at, target, y, a[model], current)
                for delay in s6.DELAYS:
                    prefix = f"{model}_{delay}m_"
                    for field in ["cold", "latest", "alpha", "clipped"]:
                        if a[prefix + field].shape != (n,):
                            raise ValueError("Invalid interval metadata shape")
                    lo, hi = a[prefix + "lo"], a[prefix + "hi"]
                    if (lo.shape != (n, 4) or hi.shape != (n, 4) or np.any(lo < 0)
                            or np.any(lo > hi) or not np.isfinite(lo).all() or not np.isfinite(hi).all()):
                        raise ValueError("Invalid interval array")
                    latest = a[prefix + "latest"]
                    if (latest.dtype.kind not in "iu" or np.any(latest < -1)
                            or np.any(latest >= at // s6.DAY * s6.DAY)):
                        raise ValueError("Future or malformed interval feedback")
                    if (a[prefix + "cold"].dtype != bool or a[prefix + "clipped"].dtype != bool
                            or not np.isfinite(a[prefix + "alpha"]).all()
                            or np.any(a[prefix + "alpha"] < .02) or np.any(a[prefix + "alpha"] > .25)):
                        raise ValueError("Invalid feedback metadata")
                    replayed = s6.wrappers(at, target, y, a[model], current, cfg, delay * 60)
                    for field in ["lo", "hi", "cold", "latest", "alpha", "clipped"]:
                        saved, expected = a[prefix + field], replayed[field]
                        if field in ("cold", "latest", "clipped"):
                            same_array(saved, expected, f"interval replay {prefix}{field}")
                        elif not np.allclose(saved, expected, rtol=1e-10, atol=1e-10, equal_nan=False):
                            raise ValueError(f"Interval-generation replay mismatch: {prefix}{field}")
                    if delay == 30:
                        radius = original["router_radius" if pi == 0 else "blend_radius"]
                        if not np.allclose(hi[:, 0] - a[model], radius, rtol=1e-10, atol=1e-10):
                            raise ValueError("Legacy radius replay mismatch")
                        max_replay_error = max(max_replay_error, float(np.max(np.abs(hi[:, 0] - a[model] - radius))))
                    base = s6.metrics(y, lo[:, 0], hi[:, 0], good)
                    for mi, method in enumerate(s6.METHODS):
                        key = sid, horizon, model, method, delay
                        row, l, u = records[key], lo[:, mi], hi[:, mi]
                        close(row.get("paired_origin_sha256"), origin, "paired origins")
                        close(row.get("eligible_origins"), int(((at >= s6.START) & (target < s6.END)).sum()), "eligible origins")
                        close(row.get("current_activity_threshold"), threshold, "regime threshold")
                        for name, mask in {"overall": good, "high_at_issue": good & high,
                                           "high_realized_target": good & (y >= threshold)}.items():
                            close(row.get(name), s6.metrics(y, l, u, mask), f"{key}.{name}")
                        close(row.get("months"), {str(m): s6.metrics(y, l, u, good & (months == m)) for m in range(1, 13)}, "months")
                        close(row.get("quarters"), {str(q): s6.metrics(y, l, u, good & (((months - 1) // 3 + 1) == q)) for q in range(1, 5)}, "quarters")
                        close(row.get("initial_radius_fraction"), float(a[prefix + "cold"][good].mean()), "cold fraction")
                        close(row.get("alpha_at_bound_fraction"), float(a[prefix + "clipped"][good].mean()) if mi == 3 else None, "clipping fraction")
                        assessment = dict(zip(IDENTITY, key))
                        assessment.update(concentration(y, l, u, good, high))
                        assessment["months"] = {str(m): descriptive_slice(y, l, u, good & (months == m)) for m in range(1, 13)}
                        assessments.append(assessment)
                        if delay == 30 and mi:
                            comparison = comparisons[key]
                            bscore = s6.interval_score(y[good], lo[good, 0], hi[good, 0])
                            cscore = s6.interval_score(y[good], l[good], u[good])
                            actual = row["overall"]
                            for name, expected in {"n": int(good.sum()), "paired_origin_sha256": origin,
                                    "interval_score_gain_pct": float(100 * (bscore.mean() - cscore.mean()) / bscore.mean()),
                                    "coverage": actual["coverage"], "baseline_coverage": base["coverage"],
                                    "width_change_pct": float(100 * (actual["mean_width"] / base["mean_width"] - 1)),
                                    "high_at_issue_n": row["high_at_issue"]["n"],
                                    "high_at_issue_coverage": row["high_at_issue"]["coverage"]}.items():
                                close(comparison.get(name), expected, f"comparison.{name}")
                            seed = 20260906 + s6.STATIONS.index(sid)*100 + s6.HORIZONS.index(horizon)*10 + pi*4 + mi
                            for block in [7, 14]:
                                expected = s6.bootstrap_scores(at[good], bscore, cscore, block, seed)
                                close(comparison[f"ci{block}_day_pct"], expected, "descriptive block interval")
            audits.append({"station": sid, "horizon_minutes": horizon, "paired_origins": int(good.sum()),
                           "paired_origin_sha256": origin, "maximum_legacy_radius_replay_error": max_replay_error})
    if len(summary.get("cell_audits", [])) != 15:
        raise ValueError("Missing source audit cells")
    for actual, expected in zip(summary["cell_audits"], audits):
        close(actual, expected, "source audit")
    close(summary.get("paired_station_horizon_targets"), sum(a["paired_origins"] for a in audits), "paired total")
    with (results / "summary.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != CSV_FIELDS:
            raise ValueError("CSV header schema mismatch")
        csv_rows = list(reader)
    seen = set()
    for row in csv_rows:
        if set(row) != set(CSV_FIELDS) or any(value is None for value in row.values()):
            raise ValueError("CSV row schema mismatch")
        key = row["station"], int(row["horizon_minutes"]), row["point_model"], row["interval_method"], int(row["feedback_delay_minutes"])
        if key not in records or key in seen:
            raise ValueError("Duplicate or unexpected CSV cell")
        seen.add(key)
        for name in ["n", "coverage", "mean_width", "interval_score"]:
            close(float(row[name]), records[key]["overall"][name], f"CSV.{name}")
        for name in ["n", "coverage"]:
            close(float(row[f"high_at_issue_{name}"]), records[key]["high_at_issue"][name], f"CSV.high.{name}")
    if seen != set(records):
        raise ValueError("Incomplete CSV result grid")
    report = {"schema_version": "1.0", "status": "VERIFIED_NUMERICAL_REPORT_CONSISTENCY",
              "source_sha256": s6.SOURCE_SHA, "protocol_commit": s6.PROTOCOL_COMMIT,
              "interval_records_recomputed": len(records), "comparison_records_recomputed": len(comparisons),
              "arrays_checked": 15 * 31, "paired_station_horizon_targets": sum(a["paired_origins"] for a in audits),
              "interval_generation_replayed": True, "fresh_holdout": False, "promotion_allowed": False,
              "interval_algorithm_independently_validated": False,
              "independent_validation": False, "nominal_coverage": .9, "minimum_descriptive_slice_rows": MIN_REGIME_N,
              "interpretation": "Empirical slice states are retrospective diagnostics, not formal conditional coverage guarantees. Rows overlap and are dependent; 100 rows is a reporting floor, not an effective sample size.",
              "regime_assessments": assessments,
              "verifier_sha256": s6.digest(Path(__file__)), "metric_engine_sha256": s6.digest(Path(s6.__file__)),
              "result_manifest_sha256": s6.digest(results / "SHA256_MANIFEST.json")}
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    report["report_payload_sha256"] = hashlib.sha256(payload).hexdigest()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--source-zip", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Reuse the package's strict inventory check before trusting any report file.
    spec = importlib.util.spec_from_file_location("stage6_package_inventory", Path(__file__).with_name("package_stage6.py"))
    package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)
    package.verify_result_inventory(args.results)
    report = verify_results(args.results, args.source_zip)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: report[k] for k in ["status", "interval_records_recomputed", "comparison_records_recomputed", "arrays_checked", "promotion_allowed", "report_payload_sha256"]}))


if __name__ == "__main__":
    main()
