"""Apply the unchanged July model selection and fit to a later historical archive."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess

import REPLAY_EIA_CONSTRAINT_REVIEW as custody

ROOT = custody.ROOT
PLAN = ROOT / "config/eia_later_window_review_v1.json"
DEFAULT_OUTPUT = ROOT / "evidence/reproducibility/eia_constraint_later_window_20260921"


def run(output: Path) -> dict:
    plan = json.loads(PLAN.read_text())
    original = json.loads((ROOT / plan["original_plan"]).read_text())
    identities = dict(original["frozen_inputs"])
    identities[plan["new_input"]] = plan["new_input_sha256"]
    for relative, expected in identities.items():
        if custody.digest(ROOT / relative) != expected:
            raise ValueError(f"frozen input mismatch: {relative}")
    if output.exists():
        raise ValueError("refusing to overwrite a retained replay")
    old_panel = json.loads(gzip.decompress((ROOT / original["panel_path"]).read_bytes()))
    later_raw = gzip.decompress((ROOT / plan["new_input"]).read_bytes())
    if hashlib.sha256(later_raw).hexdigest() != plan["uncompressed_sha256"]:
        raise ValueError("later raw-input identity mismatch")
    later_rows = json.loads(later_raw)
    seen = {(row["respondent"], row["type"], row["period"]) for row in old_panel["rows"]}
    timezones = {row["respondent"]: row["timezone"] for row in old_panel["rows"]}
    combined = copy.deepcopy(old_panel)
    for row in later_rows:
        key = row["respondent"], row["type"], row["period"]
        if key in seen or row["type"] not in {"D", "DF"}:
            raise ValueError("duplicate or unexpected later observation")
        if row["timezone"] != timezones[row["respondent"]] or row["value-units"] != "megawatthours":
            raise ValueError("inconsistent aggregation timezone or unit")
        value = float(row["value"])
        if not math.isfinite(value) or value <= 0 or not plan["holdout_start"] <= row["period"] <= plan["holdout_end"]:
            raise ValueError("invalid later value or period")
        seen.add(key)
        combined["rows"].append({"respondent": row["respondent"], "respondent_name": row["respondent-name"], "timezone": row["timezone"], "type": row["type"], "period": row["period"], "value": value, "value_units": "megawatthours"})
    spec = importlib.util.spec_from_file_location("frozen_eia_residual", ROOT / "code/eia_grid_residual_moe_benchmark.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    protocol = module.load_protocol()
    protocol["splits"]["holdout_start"] = plan["holdout_start"]
    protocol["splits"]["holdout_end"] = plan["holdout_end"]
    features, diagnostics = module.build_feature_rows(combined, protocol)
    training = [row for row in features if row["split"] == "training"]
    development = [row for row in features if row["split"] == "development"]
    holdout = [row for row in features if row["split"] == "holdout"]
    selection_models, _ = module.fit_models(training)
    development_rows = module.predict_candidates(development, selection_models)
    leaderboard = module.aggregate_strategy(development_rows)
    selected = module.select_candidate(leaderboard)["strategy"]
    if selected != "xgboost_residual":
        raise ValueError("original model selection changed; no substitution allowed")
    final_models, _ = module.fit_models(training + development)
    rows = module.predict_candidates(holdout, final_models, selected_only=selected) + module.predict_baselines(holdout, final_models)
    comparisons = module.build_comparisons(rows, selected, protocol)
    counts = dict(sorted(Counter(row["respondent"] for row in holdout).items()))
    paired = [row for row in rows if row["strategy"] in {selected, "eia_day_ahead_forecast"}]
    report = {"schema": "eia_later_window_review.v1", "selected_candidate": selected, "development_leaderboard": leaderboard, "holdout_leaderboard": module.aggregate_strategy(rows), "baseline_comparisons": comparisons, "feature_diagnostics": diagnostics, "coverage_by_authority": counts, "total_paired_authority_days": len(holdout), "original_150_day_coverage_gate": bool(len(counts) >= 8 and min(counts.values()) >= 150), "promotion_gate_passed": False, "interpretation": plan["interpretation"], "overall": custody.paired_summary(paired, selected), "by_authority": {key: custody.paired_summary([row for row in paired if row["respondent"] == key], selected) for key in counts}, "by_month": {key: custody.paired_summary([row for row in paired if row["calendar_month"] == key], selected) for key in sorted({row["calendar_month"] for row in paired})}}
    output.mkdir(parents=True)
    custody.write_json(output / "benchmark.json", report)
    module.write_rows(output / "predictions.csv", development_rows + rows)
    (output / "predictions.csv.gz").write_bytes(gzip.compress((output / "predictions.csv").read_bytes(), mtime=0))
    (output / "predictions.csv").unlink()
    paths = list(identities) + [plan["original_plan"], str(PLAN.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT)), "code/ops/REPLAY_EIA_CONSTRAINT_REVIEW.py"]
    custody.write_json(output / "manifest.json", {"schema": "eia_later_window_manifest.v1", "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "inputs": {path: {"sha256": custody.digest(ROOT / path), "bytes": (ROOT / path).stat().st_size} for path in paths}, "outputs": {path.name: {"sha256": custody.digest(path), "bytes": path.stat().st_size} for path in sorted(output.iterdir()) if path.is_file()}, "environment_reference": "../eia_constraint_review_20260921/environment.json", "boundary": "Additional retrospective temporal test. No operational-incumbent, untouched-holdout, independent-validation or savings claim."})
    return custody.verify(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(custody.verify(args.run_dir) if args.verify else run(args.run_dir), indent=2))
