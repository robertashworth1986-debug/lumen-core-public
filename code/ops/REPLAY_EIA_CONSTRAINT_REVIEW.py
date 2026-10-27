"""Retain an inspectable replay of the existing, previously scored EIA protocol.

No candidates, thresholds, splits, or selection rules are changed. Supplemental
authority and month tables are descriptive diagnosis, never selection evidence.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "config/eia_constraint_replay_review_v1.json"
DEFAULT_OUTPUT = ROOT / "evidence/reproducibility/eia_constraint_review_20260921"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def paired_summary(rows: list[dict], candidate: str) -> dict:
    paired = defaultdict(dict)
    for row in rows:
        key = row["respondent"], row["target_date"]
        strategy = row["strategy"]
        if strategy in paired[key]:
            raise ValueError("duplicate prediction identity")
        paired[key][strategy] = row
    errors = {candidate: [], "eia_day_ahead_forecast": []}
    actuals = []
    for strategies in paired.values():
        if set(strategies) != set(errors):
            raise ValueError("candidate and official comparison must have identical keys")
        values = [float(strategies[s]["actual_mwh"]) for s in errors]
        if values[0] != values[1]:
            raise ValueError("paired actual values disagree")
        actuals.append(abs(values[0]))
        for strategy in errors:
            error = abs(float(strategies[strategy]["predicted_mwh"]) - values[0])
            if not math.isfinite(error) or not math.isfinite(values[0]):
                raise ValueError("nonfinite prediction or target")
            errors[strategy].append(error)
    if not actuals or sum(actuals) == 0:
        raise ValueError("empty or zero-demand comparison")
    scores = {}
    for strategy, values in errors.items():
        values = sorted(values)
        scores[strategy] = {
            "mae_mwh": statistics.mean(values),
            "wape_pct": 100 * sum(values) / sum(actuals),
            "p95_absolute_error_mwh_nearest_rank": values[math.ceil(.95 * len(values)) - 1],
        }
    baseline = scores["eia_day_ahead_forecast"]
    selected = scores[candidate]
    return {
        "paired_authority_days": len(actuals),
        "first_target": min(key[1] for key in paired),
        "last_target": max(key[1] for key in paired),
        "scores": scores,
        "relative_mae_reduction_pct": 100 * (baseline["mae_mwh"] - selected["mae_mwh"]) / baseline["mae_mwh"] if baseline["mae_mwh"] else None,
        "absolute_mae_reduction_mwh": baseline["mae_mwh"] - selected["mae_mwh"],
        "relative_p95_reduction_pct": 100 * (baseline["p95_absolute_error_mwh_nearest_rank"] - selected["p95_absolute_error_mwh_nearest_rank"]) / baseline["p95_absolute_error_mwh_nearest_rank"] if baseline["p95_absolute_error_mwh_nearest_rank"] else None,
    }


def verify(output: Path) -> dict:
    manifest = json.loads((output / "manifest.json").read_text())
    for category, base in [("inputs", ROOT), ("outputs", output)]:
        for relative, expected in manifest[category].items():
            path = base / relative
            if not path.resolve().is_relative_to(base.resolve()):
                raise ValueError("manifest path leaves its root")
            if digest(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
                raise ValueError(f"hash or size mismatch: {relative}")
    return {"verified": True, "input_count": len(manifest["inputs"]), "output_count": len(manifest["outputs"]), "manifest_sha256": digest(output / "manifest.json"), "boundary": "Hash consistency only; not independent validation."}


def run(output: Path) -> dict:
    plan = json.loads(PLAN.read_text())
    # Check every pre-run identity before materialization, fitting, or scoring.
    for relative, expected in plan["frozen_inputs"].items():
        if digest(ROOT / relative) != expected:
            raise ValueError(f"frozen input mismatch: {relative}")
    if output.exists():
        raise ValueError("refusing to overwrite a retained replay; use a new run directory")
    output.mkdir(parents=True)
    source = ROOT / "code/eia_grid_residual_moe_benchmark.py"
    spec = importlib.util.spec_from_file_location("frozen_eia_residual", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    protocol = module.load_protocol()
    raw = gzip.decompress((ROOT / plan["panel_path"]).read_bytes())
    if hashlib.sha256(raw).hexdigest() != protocol["frozen_panel"]["file_sha256"]:
        raise ValueError("uncompressed panel identity mismatch")
    materialized = ROOT / protocol["frozen_panel"]["path"]
    existed = materialized.exists()
    if existed and materialized.read_bytes() != raw:
        raise ValueError("existing materialized panel differs")
    materialized.parent.mkdir(parents=True, exist_ok=True)
    materialized.write_bytes(raw)
    try:
        panel = module.load_panel(protocol)
        report, rows = module.run_benchmark(panel, protocol)
    finally:
        if not existed:
            materialized.unlink()
    write_json(output / "benchmark.json", report)
    module.write_rows(output / "predictions.csv", rows)
    (output / "predictions.csv.gz").write_bytes(gzip.compress((output / "predictions.csv").read_bytes(), mtime=0))
    (output / "predictions.csv").unlink()
    selected = report["selection"]["selected_candidate"]
    paired_rows = [row for row in rows if row["split"] == "holdout" and row["strategy"] in {selected, "eia_day_ahead_forecast"}]
    summary = {
        "schema": "eia_constraint_replay_review.v1",
        "evidence_type": "author-operated historical public-data replay; previously inspected holdout",
        "selected_candidate": selected,
        "overall": paired_summary(paired_rows, selected),
        "by_authority": {authority: paired_summary([row for row in paired_rows if row["respondent"] == authority], selected) for authority in sorted({row["respondent"] for row in paired_rows})},
        "by_month": {month: paired_summary([row for row in paired_rows if row["calendar_month"] == month], selected) for month in sorted({row["calendar_month"] for row in paired_rows})},
        "original_promotion_gate": report["promotion_gate"],
        "interpretation": plan["interpretation"],
    }
    write_json(output / "constraint_summary.json", summary)
    write_json(output / "environment.json", {
        "python": sys.version, "platform": platform.platform(),
        "packages": {name: importlib.metadata.version(name) for name in ["numpy", "scipy", "pandas", "scikit-learn", "xgboost", "lightgbm", "joblib", "threadpoolctl"]},
        "thread_controls": {name: os.environ.get(name) for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONHASHSEED", "TZ"]},
        "authoritative_codecheck_environment": False,
        "reason": "This replay records its own environment; it does not replace the exact Python 3.11.9 CODECHECK container receipt.",
    })
    inputs = list(plan["frozen_inputs"]) + [str(PLAN.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT))]
    manifest = {
        "schema": "eia_constraint_replay_manifest.v1",
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "inputs": {path: {"sha256": digest(ROOT / path), "bytes": (ROOT / path).stat().st_size} for path in inputs},
        "outputs": {path.name: {"sha256": digest(path), "bytes": path.stat().st_size} for path in sorted(output.iterdir()) if path.is_file()},
        "boundary": "First-party hash freeze. No signature, independent validation, prospective forecast or realized savings is asserted.",
    }
    write_json(output / "manifest.json", manifest)
    return verify(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.run_dir) if args.verify else run(args.run_dir), indent=2))
