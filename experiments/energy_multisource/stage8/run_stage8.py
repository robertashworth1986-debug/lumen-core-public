"""Frozen, offline, multi-source stress deltas. No network or control interfaces.

The hashes bind inherited public inputs; they do not attest publication times.
Run with the repository's institutional Python 3.11 dependency lock.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import importlib.util
import json
import platform
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PROTOCOL = HERE / "PROTOCOL.json"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    content = json.dumps(value, indent=2, allow_nan=False) + "\n"
    if len(content.encode()) > 2 * 1024 * 1024:
        raise ValueError("JSON artifact exceeds 2 MiB; shard before writing")
    Path(path).write_text(content)


def strict_json(path):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError("Duplicate JSON key: " + key)
            out[key] = value
        return out
    def constant(value):
        raise ValueError("Nonfinite JSON number: " + value)
    return json.loads(Path(path).read_text(), object_pairs_hook=pairs,
                      parse_constant=constant)


def historical_parser():
    path = HERE.parent / "stage3" / "run_stage3.py"
    spec = importlib.util.spec_from_file_location("stage3_source_parser", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def regularize(t, x, cadence):
    """Right-closed means. An observation at a boundary belongs to that boundary."""
    t = np.asarray(t, dtype=np.int64)
    x = np.asarray(x, dtype=float)
    if len(t) != len(x) or not len(t) or np.any(np.diff(t) <= 0):
        raise ValueError("Source timestamp/shape contract")
    if cadence <= 0:
        raise ValueError("Invalid cadence")
    bucket = -((-t) // cadence) * cadence
    grid = np.arange(bucket[0], bucket[-1] + cadence, cadence, dtype=np.int64)
    index = (bucket - grid[0]) // cadence
    valid = np.isfinite(x) & (x >= 0)
    n = np.bincount(index[valid], minlength=len(grid))
    total = np.bincount(index[valid], weights=x[valid], minlength=len(grid))
    means = np.full(len(grid), np.nan)
    np.divide(total, n, out=means, where=n > 0)
    return grid, means, {"raw_rows": len(t), "rejected_measurements": int((~valid).sum()),
                         "buckets": len(grid), "empty_buckets": int((n == 0).sum())}


def acquire(inputs, out, protocol):
    """Only exact archive members are materialized; no general ZIP extraction."""
    paths = {name: inputs / name for name in protocol["sources"]}
    paths["eia_grid_validation_panel_20260713.json.gz"] = (
        inputs / "eia_grid_validation_panel_20260713.json.gz")
    for name, path in paths.items():
        if sha(path) != protocol["sources"][name]:
            raise ValueError("Frozen source hash mismatch: " + name)
    parser = historical_parser()
    series = []

    def add(sid, family, unit, t, x, source, extra=None):
        rule = protocol["families"][family]
        cadence = rule["cadence_seconds"]
        t, x, quality = regularize(t, x, cadence)
        if "cut" in rule:
            cut = int(dt.datetime.fromisoformat(rule["cut"]).replace(
                tzinfo=dt.timezone.utc).timestamp())
        else:
            cut = int(t[0] + rule["cut_fraction"] * (t[-1] - t[0]))
        cal = x[(t < cut) & np.isfinite(x)]
        if len(cal) < 100 or np.sum((t >= cut) & np.isfinite(x)) < 100:
            raise ValueError("Insufficient source support: " + sid)
        iqr = float(np.quantile(cal, .75) - np.quantile(cal, .25))
        adjacent = (t[1:] < cut) & np.isfinite(x[1:]) & np.isfinite(x[:-1])
        ramp = np.abs(x[1:] - x[:-1])[adjacent]
        if not len(ramp):
            raise ValueError("No calibration ramps: " + sid)
        meta = dict(id=sid, family=family, unit=unit, source_archive=source,
                    clock=rule["clock"], cut=cut, cadence_seconds=cadence,
                    calibration_count=len(cal), calibration_last_bucket=int(t[t < cut][-1]),
                    calibration_iqr=iqr, high_threshold=float(np.quantile(cal, .9)),
                    ramp_threshold=float(np.quantile(ramp, .9)), quality=quality,
                    source_detail=extra or {}, start=int(t[0]), end=int(t[-1]))
        np.savez_compressed(out / "normalized" / (sid + ".npz"), t=t, x=x)
        series.append(meta)

    eia = strict_json_gzip(paths["eia_grid_validation_panel_20260713.json.gz"])
    for sid in protocol["eia_regions"]:
        rows = sorted([r for r in eia["rows"] if r["respondent"] == sid and r["type"] == "D"],
                      key=lambda r: r["period"])
        if any(r["value_units"] != "megawatthours" for r in rows):
            raise ValueError("EIA unit mismatch")
        t = [int(dt.datetime.fromisoformat(r["period"]).replace(
            tzinfo=dt.timezone.utc).timestamp()) for r in rows]
        add("EIA_" + sid, "grid", "MWh", t, [r["value"] for r in rows],
            "eia_grid_validation_panel_20260713.json.gz",
            {"official_forecast_comparison": "Not used: archived DF values lack issue-time publication attestations."})
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        with zipfile.ZipFile(paths["energy-stage4-ci.zip"]) as z:
            if len(z.namelist()) != len(set(z.namelist())):
                raise ValueError("Duplicate archive member")
            for sid in protocol["ndbc_stations"]:
                ts, xs, details = [], [], []
                for year in (2023, 2025):
                    name = sid + "h" + str(year) + ".txt.gz"
                    p = temp / name
                    p.write_bytes(z.read("sources/" + name))
                    t, x, detail = parser.read_ndbc(p, year)
                    ts.append(t); xs.append(x); details.append(detail)
                add("NDBC_" + sid, "marine", "m2_s", np.concatenate(ts),
                    np.concatenate(xs), "energy-stage4-ci.zip", {"members": details})
        with zipfile.ZipFile(paths["utah-forge-gdr1683.zip"]) as z:
            if len(z.namelist()) != len(set(z.namelist())):
                raise ValueError("Duplicate archive member")
            member = "raw/Extended Circulation Test/Extended Circulation Test Data 08082024 to 09052024 (30 sec increment).xlsx"
            p = temp / "forge.xlsx"
            p.write_bytes(z.read(member))
            t, a = parser.xlsx_forge(p)
            for sid, spec in protocol["forge_channels"].items():
                add("FORGE_" + sid, "geothermal", spec["unit"], t, a[:, spec["column"]],
                    "utah-forge-gdr1683.zip", {"member": member, "sha256": sha(p), "column": spec["column"]})
    return series


def strict_json_gzip(path):
    with tempfile.NamedTemporaryFile(suffix=".json") as f:
        f.write(gzip.decompress(Path(path).read_bytes())); f.flush()
        return strict_json(Path(f.name))


def corrupt(x, cut_index, scenario, iqr):
    """Mutate an observation copy, never the outcome vector. No random global state."""
    z = x.copy()
    n = len(x) - cut_index
    rel = np.arange(n)
    a = z[cut_index:]
    delay = 0
    seed = 29 if scenario.endswith("s29") else 17
    rng = np.random.default_rng(seed)
    if scenario.startswith("missing") or scenario == "combined":
        p = .1 if scenario.startswith("missing10") else .3
        a[rng.random(n) < p] = np.nan
        delay = 3 if scenario == "combined" else 0
    elif scenario == "burst12":
        a[(rel % 120) < 12] = np.nan
    elif scenario.startswith("delay"):
        delay = int(scenario[5:])
    elif scenario.startswith("spike_"):
        a[rel % 97 == 0] += (5 if scenario == "spike_positive" else -5) * iqr
    elif scenario == "stuck12":
        for start in range(0, n, 120):
            a[start:start + 12] = z[cut_index + start - 1] if cut_index + start else np.nan
    elif scenario.startswith("bias_"):
        a += (.1 if scenario == "bias_positive" else -.1) * iqr
    elif scenario.startswith("drift_"):
        a += np.linspace(0, .5 if scenario == "drift_positive" else -.5, n) * iqr
    elif scenario.startswith("noise_"):
        a += rng.normal(0, .1 * iqr, n)
    elif scenario == "quantize":
        if iqr > 0:
            a[:] = np.round(a / (.1 * iqr)) * (.1 * iqr)
    elif scenario in ("gain110", "gain90"):
        a *= 1.1 if scenario == "gain110" else .9
    elif scenario == "outage":
        a[:] = np.nan
    elif scenario != "clean":
        raise ValueError("Unknown scenario: " + scenario)
    # Negative sensor anomalies remain anomalous observations, not missing truth.
    return z, delay


def predict(z, issue, horizon, seasonal_steps, delay, iqr):
    n = len(z)
    available = issue - delay
    last = np.maximum.accumulate(np.where(np.isfinite(z), np.arange(n), -1))
    at = np.clip(available, 0, n - 1)
    previous = last[at]
    fresh = (available >= 0) & (previous >= 0) & (issue - previous <= 3)
    p = np.where(fresh, z[np.maximum(previous, 0)], np.nan)
    window_idx = available[:, None] - np.arange(4, -1, -1)
    window = z[np.clip(window_idx, 0, n - 1)].copy()
    window[window_idx < 0] = np.nan
    count = np.isfinite(window).sum(axis=1)
    enough = fresh & (count >= 3)
    median = np.full(len(issue), np.nan)
    median[enough] = np.nanmedian(window[enough], axis=1)
    changes = np.diff(window, axis=1)
    has_slope = enough & (np.isfinite(changes).sum(axis=1) >= 2)
    slope = np.zeros(len(issue))
    slope[has_slope] = np.nanmedian(changes[has_slope], axis=1)
    trend = np.where(has_slope, median + .5 * (horizon + delay) * np.clip(slope, -.1 * iqr, .1 * iqr), np.nan)
    seasonal_idx = issue + horizon - seasonal_steps
    seasonal_valid = (seasonal_idx >= 0) & (seasonal_idx <= available)
    seasonal = np.where(seasonal_valid, z[np.clip(seasonal_idx, 0, n - 1)], np.nan)
    # Seasonal memory is intentionally independent of the latest-observation age.
    values = np.column_stack([p, seasonal, median, trend, .5 * p + .5 * median])
    values = np.maximum(values, 0)
    return values, previous


def score(truth, predictions, masks, metadata, protocol):
    rows = []
    for baseline in (0, 1):
        for candidate in (2, 3, 4):
            for slice_name, population in masks.items():
                actual = population & np.isfinite(truth)
                base_ok = actual & np.isfinite(predictions[:, baseline])
                cand_ok = actual & np.isfinite(predictions[:, candidate])
                paired = base_ok & cand_ok
                count = int(paired.sum())
                denom = int(actual.sum())
                row = dict(metadata, baseline=protocol["methods"][baseline],
                           candidate=protocol["methods"][candidate], slice=slice_name,
                           scheduled_count=int(population.sum()), truth_count=denom,
                           baseline_count=int(base_ok.sum()), candidate_count=int(cand_ok.sum()),
                           pairs=count, pair_coverage=count / denom if denom else 0,
                           candidate_coverage=int(cand_ok.sum()) / denom if denom else 0,
                           baseline_coverage=int(base_ok.sum()) / denom if denom else 0)
                for name in ("baseline_mae", "candidate_mae", "baseline_rmse", "candidate_rmse",
                             "baseline_p95", "candidate_p95", "candidate_bias", "mae_delta_native",
                             "mae_improvement_pct", "p95_regression_pct"):
                    row[name] = None
                row["positive_quartiles"] = 0
                row["quartile_mae_deltas"] = []
                row["status"] = "HOLD_INSUFFICIENT_SUPPORT"
                if count:
                    be = np.abs(truth[paired] - predictions[paired, baseline])
                    ce = np.abs(truth[paired] - predictions[paired, candidate])
                    b, c = float(be.mean()), float(ce.mean())
                    bp, cp = float(np.quantile(be, .95)), float(np.quantile(ce, .95))
                    row.update(baseline_mae=b, candidate_mae=c, baseline_rmse=float(np.sqrt(np.mean(be**2))),
                               candidate_rmse=float(np.sqrt(np.mean(ce**2))), baseline_p95=bp, candidate_p95=cp,
                               candidate_bias=float(np.mean(predictions[paired, candidate] - truth[paired])),
                               mae_delta_native=b - c, mae_improvement_pct=100 * (b - c) / b if b > 0 else None,
                               p95_regression_pct=100 * (cp - bp) / bp if bp > 0 else None)
                    # Time quartiles retain empty periods; never compact paired rows before partitioning.
                    deltas = []
                    for indices in np.array_split(np.arange(len(truth)), 4):
                        q = indices[paired[indices]]
                        d = float(np.mean(np.abs(truth[q] - predictions[q, baseline]) -
                                          np.abs(truth[q] - predictions[q, candidate]))) if len(q) >= 20 else None
                        deltas.append(d)
                    row["quartile_mae_deltas"] = deltas
                    row["positive_quartiles"] = sum(v is not None and v > 0 for v in deltas)
                    rule = protocol["decision_rules"]
                    if count >= rule["min_pairs"] and row["pair_coverage"] >= rule["min_pair_coverage"]:
                        if b == 0:
                            row["status"] = "HOLD_ZERO_BASELINE_ERROR"
                        elif c > b:
                            row["status"] = "REJECT_MAE_REGRESSION"
                        elif (row["mae_improvement_pct"] >= rule["min_mae_improvement_pct"]
                              and cp <= bp and row["positive_quartiles"] >= rule["required_positive_quartiles"]):
                            row["status"] = "DESCRIPTIVE_CANDIDATE_ONLY"
                        else:
                            row["status"] = "HOLD_THRESHOLD_OR_STABILITY"
                rows.append(row)
    return rows


def run(inputs, out):
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to overwrite a nonempty frozen run")
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("normalized", "arrays", "metrics", "code"):
        (out / sub).mkdir()
    protocol = strict_json(PROTOCOL)
    # Copy exact experiment inputs before scoring. Frozen outputs are append-only.
    shutil.copyfile(PROTOCOL, out / "PROTOCOL.json")
    for file in (HERE / "run_stage8.py", HERE / "verify_stage8.py", HERE / "test_stage8.py",
                 HERE.parent / "stage3" / "run_stage3.py"):
        shutil.copyfile(file, out / "code" / file.name)
    series = acquire(inputs, out, protocol)
    write_json(out / "SERIES.json", series)
    rows, index = [], []
    for meta in series:
        with np.load(out / "normalized" / (meta["id"] + ".npz"), allow_pickle=False) as data:
            t, x = data["t"], data["x"]
        rule = protocol["families"][meta["family"]]
        cut_idx = int(np.searchsorted(t, meta["cut"]))
        for scenario in protocol["scenarios"]:
            observed, delay = corrupt(x, cut_idx, scenario, meta["calibration_iqr"])
            for h in rule["horizon_steps"]:
                issue = np.arange(cut_idx, len(t) - h)
                truth = x[issue + h]
                predictions, previous = predict(observed, issue, h, rule["seasonal_steps"], delay, meta["calibration_iqr"])
                high = np.isfinite(x[issue]) & (x[issue] > meta["high_threshold"])
                ramp = np.isfinite(x[issue]) & np.isfinite(x[np.maximum(issue - 1, 0)]) & (
                    np.abs(x[issue] - x[np.maximum(issue - 1, 0)]) > meta["ramp_threshold"])
                masks = dict(all=np.ones(len(issue), bool), high_at_issue=high, ramp_at_issue=ramp)
                name = f"{meta['id']}__{scenario}__h{h}.npz"
                np.savez_compressed(out / "arrays" / name, issue=issue, target_index=issue + h,
                                    truth=truth, predictions=predictions, high=high, ramp=ramp,
                                    last_observed_index=previous)
                entry = dict(series=meta["id"], family=meta["family"], unit=meta["unit"], scenario=scenario,
                             horizon_steps=h, horizon_seconds=h * meta["cadence_seconds"], array_file="arrays/" + name)
                index.append(entry)
                cell_rows = score(truth, predictions, masks, entry, protocol)
                write_json(out / "metrics" / (Path(name).stem + ".json"), cell_rows)
                rows.extend(cell_rows)
        print(meta["id"], "complete", flush=True)
    write_json(out / "INDEX.json", index)
    with (out / "metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, list) else v for k, v in row.items()})
    status_counts = {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})}
    write_json(out / "SUMMARY.json", dict(schema="lumencore.frozen_delta.summary.v1",
        created_utc=dt.datetime.now(dt.timezone.utc).isoformat(), python=platform.python_version(), numpy=np.__version__,
        protocol_sha256=sha(PROTOCOL), series_count=len(series), scenario_count=len(protocol["scenarios"]),
        array_count=len(index), metric_records=len(rows), status_counts=status_counts,
        source_holds=protocol["retained_source_holds"], independent_validation=False,
        decision="RESEARCH_ONLY_NO_DEPLOYMENT_OR_FINANCIAL_CLAIM",
        denominator_note="Metric records share observations, methods and stress seeds; they are not independent trials."))
    files = {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file()}
    write_json(out / "MANIFEST.json", dict(schema="lumencore.frozen_delta.manifest.v1", files=files,
        note="Content integrity only; not a signature or independent timestamp. Pin the manifest SHA externally."))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    run(a.inputs, a.out)
