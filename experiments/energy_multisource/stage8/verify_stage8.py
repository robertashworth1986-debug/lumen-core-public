"""Fail-closed packet verifier. Independently recomputes every paired metric.

Full prediction replay uses the producer; independent scalar spot checks test
formula and information boundaries. These are distinct forms of assurance.
"""
from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import json
import math
import tempfile
from pathlib import Path
from statistics import fmean

import numpy as np

try:
    from . import run_stage8 as producer
except ImportError:
    import run_stage8 as producer


def require(condition, message):
    if not condition:
        raise ValueError(message)


def equal(a, b, label):
    if a is None or b is None:
        require(a is b, label)
    else:
        require(math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9), label)


def quantile(values, q):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    low = int(pos)
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * (pos - low)


def check_manifest(root, expected_sha):
    require(len(expected_sha) == 64 and producer.sha(root / "MANIFEST.json") == expected_sha,
            "Externally supplied manifest digest mismatch")
    manifest = producer.strict_json(root / "MANIFEST.json")
    require(manifest.get("schema") == "lumencore.frozen_delta.manifest.v1", "Manifest schema")
    files = manifest["files"]
    require(isinstance(files, dict) and bool(files), "Empty manifest")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    require(actual == set(files) | {"MANIFEST.json"}, "Missing or unlisted packet files")
    for name, digest in files.items():
        p = root / name
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and not p.is_symlink(), "Unsafe manifest path")
        require(producer.sha(p) == digest, "Artifact hash mismatch: " + name)


def scalar_prediction(z, issue, horizon, season, delay, iqr):
    """Independent scalar reference: explicitly enumerate only available history."""
    at = issue - delay
    recent = [(j, float(z[j])) for j in range(max(0, issue - 3), min(at + 1, len(z))) if np.isfinite(z[j])]
    p = recent[-1][1] if recent else None
    window = [float(z[j]) for j in range(max(0, at - 4), at + 1) if np.isfinite(z[j])]
    median = quantile(window, .5) if p is not None and len(window) >= 3 else None
    slopes = [float(z[j] - z[j - 1]) for j in range(max(1, at - 3), at + 1)
              if np.isfinite(z[j]) and np.isfinite(z[j - 1])]
    trend = median + .5 * (horizon + delay) * max(-.1 * iqr, min(.1 * iqr, quantile(slopes, .5))) if median is not None and len(slopes) >= 2 else None
    s = issue + horizon - season
    seasonal = float(z[s]) if 0 <= s <= at and np.isfinite(z[s]) else None
    blend = .5 * p + .5 * median if p is not None and median is not None else None
    return [max(0, v) if v is not None else None for v in [p, seasonal, median, trend, blend]]


def verify_metrics(row, truth, predictions, mask, protocol):
    bi = protocol["methods"].index(row["baseline"])
    ci = protocol["methods"].index(row["candidate"])
    truth_ok = mask & np.isfinite(truth)
    base_ok = truth_ok & np.isfinite(predictions[:, bi])
    cand_ok = truth_ok & np.isfinite(predictions[:, ci])
    pair = base_ok & cand_ok
    indices = np.flatnonzero(pair)
    for key, value in dict(scheduled_count=int(mask.sum()), truth_count=int(truth_ok.sum()),
                           baseline_count=int(base_ok.sum()), candidate_count=int(cand_ok.sum()), pairs=len(indices)).items():
        require(row[key] == value, "Denominator mismatch: " + key)
    denom = row["truth_count"]
    for name, count in [("pair_coverage", len(indices)), ("baseline_coverage", int(base_ok.sum())), ("candidate_coverage", int(cand_ok.sum()))]:
        equal(row[name], count / denom if denom else 0, name)
    metrics = ["baseline_mae", "candidate_mae", "baseline_rmse", "candidate_rmse", "baseline_p95",
               "candidate_p95", "candidate_bias", "mae_delta_native", "mae_improvement_pct", "p95_regression_pct"]
    deltas = []
    if len(indices):
        b = [abs(float(truth[i]) - float(predictions[i, bi])) for i in indices]
        c = [abs(float(truth[i]) - float(predictions[i, ci])) for i in indices]
        bm, cm = fmean(b), fmean(c)
        bp, cp = quantile(b, .95), quantile(c, .95)
        values = [bm, cm, math.sqrt(fmean(v*v for v in b)), math.sqrt(fmean(v*v for v in c)), bp, cp,
                  fmean(float(predictions[i, ci]) - float(truth[i]) for i in indices), bm-cm,
                  100*(bm-cm)/bm if bm > 0 else None, 100*(cp-bp)/bp if bp > 0 else None]
        for name, value in zip(metrics, values):
            equal(row[name], value, name)
        for q in np.array_split(np.arange(len(truth)), 4):
            selected = q[pair[q]]
            deltas.append(fmean(abs(float(truth[i]) - float(predictions[i, bi])) -
                                abs(float(truth[i]) - float(predictions[i, ci])) for i in selected) if len(selected) >= 20 else None)
        status = "HOLD_INSUFFICIENT_SUPPORT"
        rule = protocol["decision_rules"]
        if len(indices) >= rule["min_pairs"] and row["pair_coverage"] >= rule["min_pair_coverage"]:
            if bm == 0:
                status = "HOLD_ZERO_BASELINE_ERROR"
            elif cm > bm:
                status = "REJECT_MAE_REGRESSION"
            elif values[8] >= rule["min_mae_improvement_pct"] and cp <= bp and sum(d is not None and d > 0 for d in deltas) >= 3:
                status = "DESCRIPTIVE_CANDIDATE_ONLY"
            else:
                status = "HOLD_THRESHOLD_OR_STABILITY"
    else:
        for name in metrics:
            require(row[name] is None, "No-pair metric must be null")
        status = "HOLD_INSUFFICIENT_SUPPORT"
    require(len(row["quartile_mae_deltas"]) == len(deltas), "Quartile count")
    for actual, expected in zip(row["quartile_mae_deltas"], deltas):
        equal(actual, expected, "Quartile delta")
    require(row["positive_quartiles"] == sum(d is not None and d > 0 for d in deltas), "Positive quartiles")
    require(row["status"] == status, "Decision mismatch")


def verify(root, inputs, expected_sha):
    check_manifest(root, expected_sha)
    protocol = producer.strict_json(root / "PROTOCOL.json")
    require(producer.sha(producer.PROTOCOL) == producer.sha(root / "PROTOCOL.json"), "Verifier protocol mismatch")
    for source in ["run_stage8.py", "verify_stage8.py", "test_stage8.py"]:
        require(producer.sha(producer.HERE / source) == producer.sha(root / "code" / source), "Verifier/producer code mismatch")
    require(producer.sha(producer.HERE.parent / "stage3" / "run_stage3.py") == producer.sha(root / "code/run_stage3.py"), "Parser mismatch")
    series = producer.strict_json(root / "SERIES.json")
    require(len(series) == 17 and len({s["id"] for s in series}) == 17, "Series coverage")
    # Authentic inputs and exact full normalization replay (same parser, not independent parsing).
    with tempfile.TemporaryDirectory() as td:
        temp = Path(td); (temp / "normalized").mkdir()
        replay_series = producer.acquire(inputs, temp, protocol)
        require(series == replay_series, "Source metadata replay mismatch")
        for s in series:
            name = s["id"] + ".npz"
            with np.load(root / "normalized" / name, allow_pickle=False) as a, np.load(temp / "normalized" / name, allow_pickle=False) as b:
                require(set(a.files) == {"t", "x"}, "Normalized columns")
                for k in a.files:
                    require(np.array_equal(a[k], b[k], equal_nan=True), "Normalized source mismatch")
    metadata = {s["id"]: s for s in series}
    index = producer.strict_json(root / "INDEX.json")
    expected = {(s["id"], scenario, h) for s in series for scenario in protocol["scenarios"]
                for h in protocol["families"][s["family"]]["horizon_steps"]}
    keys = [(r["series"], r["scenario"], r["horizon_steps"]) for r in index]
    require(len(keys) == len(set(keys)) and set(keys) == expected, "Array coverage/duplicates")
    metric_paths = [root / "metrics" / (Path(r["array_file"]).stem + ".json") for r in index]
    require(set(metric_paths) == set((root / "metrics").glob("*.json")), "Metric shard coverage")
    rows = [row for path in metric_paths for row in producer.strict_json(path)]
    groups = collections.defaultdict(list)
    for row in rows:
        groups[row["array_file"]].append(row)
    require(set(groups) == {r["array_file"] for r in index}, "Metric array coverage")
    with (root / "metrics.csv").open(newline="") as f:
        csv_rows = list(csv.DictReader(f))
    require(len(csv_rows) == len(rows), "CSV row count")
    for j, row in enumerate(rows):
        require(set(csv_rows[j]) == set(row), "CSV columns")
        for key, value in row.items():
            rendered = json.dumps(value) if isinstance(value, list) else ("" if value is None else str(value))
            require(csv_rows[j][key] == rendered, "CSV/JSON mismatch")
    normalized = {}
    for s in series:
        with np.load(root / "normalized" / (s["id"] + ".npz"), allow_pickle=False) as a:
            normalized[s["id"]] = (a["t"], a["x"])
    scalar_checks = 0
    for entry in index:
        meta = metadata[entry["series"]]
        t, x = normalized[meta["id"]]
        cut = int(np.searchsorted(t, meta["cut"]))
        h = entry["horizon_steps"]
        rule = protocol["families"][meta["family"]]
        issue = np.arange(cut, len(x) - h)
        z, delay = producer.corrupt(x, cut, entry["scenario"], meta["calibration_iqr"])
        replay, previous = producer.predict(z, issue, h, rule["seasonal_steps"], delay, meta["calibration_iqr"])
        require(entry["family"] == meta["family"] and entry["unit"] == meta["unit"] and
                entry["horizon_seconds"] == h * meta["cadence_seconds"], "Metric identity")
        with np.load(root / entry["array_file"], allow_pickle=False) as a:
            require(set(a.files) == {"issue", "target_index", "truth", "predictions", "high", "ramp", "last_observed_index"}, "Array schema")
            require(np.array_equal(a["issue"], issue), "Missing/duplicated/reordered issues")
            require(np.array_equal(a["target_index"], issue + h), "Exact horizon violation")
            require(np.array_equal(a["truth"], x[issue + h], equal_nan=True), "Ground truth mutation")
            require(np.array_equal(a["predictions"], replay, equal_nan=True), "Prediction replay mismatch")
            require(np.array_equal(a["last_observed_index"], previous), "Availability metadata mismatch")
            require(not np.isinf(a["predictions"]).any(), "Infinite prediction")
            high = np.isfinite(x[issue]) & (x[issue] > meta["high_threshold"])
            ramp = np.isfinite(x[issue]) & np.isfinite(x[issue-1]) & (np.abs(x[issue] - x[issue-1]) > meta["ramp_threshold"])
            require(np.array_equal(a["high"], high) and np.array_equal(a["ramp"], ramp), "Slice leakage/mismatch")
            # Evenly spaced deterministic positions plus the first 16 cover warmup/delay boundaries.
            positions = sorted(set(range(min(16, len(issue)))) | set(np.linspace(0, len(issue)-1, 32, dtype=int)))
            for pos in positions:
                scalar = scalar_prediction(z, int(issue[pos]), h, rule["seasonal_steps"], delay, meta["calibration_iqr"])
                for k, value in enumerate(scalar):
                    actual = None if np.isnan(a["predictions"][pos, k]) else float(a["predictions"][pos, k])
                    equal(actual, value, "Independent scalar prediction")
                    scalar_checks += 1
            group = groups[entry["array_file"]]
            expected_comparisons = {(b, c, s) for b in protocol["methods"][:2]
                                    for c in protocol["methods"][2:] for s in protocol["slices"]}
            actual_keys = [(r["baseline"], r["candidate"], r["slice"]) for r in group]
            require(len(actual_keys) == len(set(actual_keys)) and set(actual_keys) == expected_comparisons,
                    "Missing/duplicate planned comparisons")
            for row in group:
                require(all(row[k] == v for k, v in entry.items()), "Comparison identity mismatch")
                mask = {"all": np.ones(len(issue), bool), "high_at_issue": high, "ramp_at_issue": ramp}[row["slice"]]
                verify_metrics(row, a["truth"], a["predictions"], mask, protocol)
    summary = producer.strict_json(root / "SUMMARY.json")
    require(summary["series_count"] == len(series) and summary["array_count"] == len(index) and
            summary["metric_records"] == len(rows) and summary["scenario_count"] == len(protocol["scenarios"]), "Summary counts")
    require(summary["status_counts"] == dict(collections.Counter(r["status"] for r in rows)), "Summary decisions")
    require(summary["source_holds"] == protocol["retained_source_holds"] and summary["independent_validation"] is False,
            "Claim/source hold mismatch")
    return dict(status="PASS", manifest_sha256=expected_sha, source_hashes_verified=3,
                normalization_replayed_series=len(series), full_prediction_arrays_replayed=len(index),
                independent_scalar_predictions=scalar_checks, independently_recomputed_metric_records=len(rows),
                csv_records_reconciled=len(rows), assurance="Internal computational verification; no independent field validation.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", type=Path, required=True)
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--expected-manifest-sha256", required=True)
    ap.add_argument("--receipt", type=Path, required=True)
    a = ap.parse_args()
    require(not a.receipt.exists(), "Refusing to overwrite verification receipt")
    require(not a.receipt.resolve().is_relative_to(a.packet.resolve()), "Receipt must be outside immutable packet")
    result = verify(a.packet, a.inputs, a.expected_manifest_sha256)
    producer.write_json(a.receipt, result)
    print(json.dumps(result, indent=2))
