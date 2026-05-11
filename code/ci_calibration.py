"""
ci_calibration.py
=============================================================================
Innovation #7 — confidence-interval calibration scoring.

For every dataset in a frozen master_universe_benchmark_v2 run:
  1. Reload raw y from raw/<ds>.csv
  2. Replicate the v2 walk-forward split exactly
  3. For each family champion, compute point forecast + residual-sigma bands
     using the same fast method as forecast_api (refit on first 80% of train,
     score on last 20%, sigma = std of residuals; band = point ± z * sigma * sqrt(t))
  4. Record empirical coverage: did each y_te[t] fall inside the 80% / 95% band?
  5. Aggregate per-model and per-family.

Output:
  out/ci_calibration/<utc>/
    coverage.csv          (per dataset, per model: n_test, in_80, in_95)
    summary.json          (overall + per-model + per-family coverage)
    calibration_summary.md
    manifest.sha256.json
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from master_universe_benchmark_v2 import (  # noqa: E402
    model_b_linear_trend, model_d_harmonic_search, model_f_mlp_tuned,
    model_h_lightgbm_lag, model_i_sarima,
)

CHAMPIONS = {
    "baseline":  ("b_linear_trend",     model_b_linear_trend),
    "harmonic":  ("d_harmonic_search",  model_d_harmonic_search),
    "neural":    ("f_mlp_tuned",        model_f_mlp_tuned),
    "tree":      ("h_lightgbm_lag",     model_h_lightgbm_lag),
    "classical": ("i_sarima",           model_i_sarima),
}

Z80 = 1.2816
Z95 = 1.96


def _split(y: np.ndarray, test_frac: float = 0.2):
    n = len(y)
    n_test = max(8, int(n * test_frac))
    if n_test >= n - 24:
        n_test = max(8, n // 5)
    return y[: n - n_test], y[n - n_test:], n_test


def _residual_sigma(y_train: np.ndarray, fn) -> float:
    """Refit on first 80%, score on last 20%, return sigma."""
    n = len(y_train)
    if n < 30:
        return float(np.std(y_train))
    cut = int(n * 0.8)
    inner_tr = y_train[:cut]
    inner_te = y_train[cut:]
    if len(inner_te) < 4:
        return float(np.std(y_train))
    try:
        pred = fn(inner_tr, len(inner_te))
        resid = inner_te - pred
        s = float(np.std(resid))
        if not np.isfinite(s) or s <= 0:
            return float(np.std(y_train))
        return s
    except Exception:
        return float(np.std(y_train))


def _evaluate_one(args):
    ds_name, raw_path = args
    try:
        df = pd.read_csv(raw_path)
        if "value" not in df.columns:
            return None
        y = df["value"].to_numpy(dtype=float)
        if len(y) < 30 or not np.all(np.isfinite(y)):
            return None
    except Exception:
        return None

    y_tr, y_te, n_test = _split(y)
    rows = []
    for fam, (mname, fn) in CHAMPIONS.items():
        try:
            pred = fn(y_tr, n_test)
            sigma = _residual_sigma(y_tr, fn)
            t_idx = np.arange(1, n_test + 1, dtype=float)
            half80 = Z80 * sigma * np.sqrt(t_idx)
            half95 = Z95 * sigma * np.sqrt(t_idx)
            in80 = int(np.sum(np.abs(y_te - pred) <= half80))
            in95 = int(np.sum(np.abs(y_te - pred) <= half95))
            rmse = float(np.sqrt(np.mean((y_te - pred) ** 2)))
            rows.append({
                "dataset": ds_name, "family": fam, "model": mname,
                "n_test": n_test, "rmse": rmse,
                "in80": in80, "in95": in95,
                "cov80": in80 / n_test, "cov95": in95 / n_test,
                "sigma": sigma,
            })
        except Exception as e:
            rows.append({"dataset": ds_name, "family": fam, "model": mname,
                         "error": str(e)[:80]})
    return rows


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    utc = os.environ.get("CALIB_UTC")
    if not utc:
        latest = ROOT / "out" / "master_universe_v2" / "latest.txt"
        utc = latest.read_text(encoding="utf-8").strip() if latest.exists() else None
    if not utc:
        print("FATAL: no CALIB_UTC and no latest.txt"); return 1

    raw_dir = ROOT / "out" / "master_universe_v2" / utc / "raw"
    if not raw_dir.exists():
        print(f"FATAL: {raw_dir} does not exist"); return 1

    out_dir = ROOT / "out" / "ci_calibration" / utc
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(raw_dir.glob("*.csv"))
    print(f"[calib] run {utc}: {len(raw_files)} datasets")

    items = [(p.stem, p) for p in raw_files]
    t0 = time.time()
    try:
        from joblib import Parallel, delayed
        results = Parallel(n_jobs=-1, backend="loky", verbose=5)(
            delayed(_evaluate_one)(it) for it in items
        )
    except Exception:
        results = [_evaluate_one(it) for it in items]
    elapsed = time.time() - t0

    rows = []
    for r in results:
        if r:
            rows.extend(r)
    df = pd.DataFrame(rows)
    cov_csv = out_dir / "coverage.csv"
    df.to_csv(cov_csv, index=False)

    valid = df.dropna(subset=["cov80", "cov95"]) if "cov80" in df.columns else df
    overall = {
        "n_datasets": len(items),
        "n_rows": len(valid),
        "mean_cov80": float(valid["cov80"].mean()) if len(valid) else None,
        "mean_cov95": float(valid["cov95"].mean()) if len(valid) else None,
        "median_cov80": float(valid["cov80"].median()) if len(valid) else None,
        "median_cov95": float(valid["cov95"].median()) if len(valid) else None,
    }
    by_family = {}
    if len(valid):
        g = valid.groupby("family").agg(
            n=("dataset", "count"),
            mean_cov80=("cov80", "mean"),
            mean_cov95=("cov95", "mean"),
            mean_rmse=("rmse", "mean"),
        ).reset_index()
        for _, r in g.iterrows():
            by_family[r["family"]] = {
                "n": int(r["n"]),
                "mean_cov80": float(r["mean_cov80"]),
                "mean_cov95": float(r["mean_cov95"]),
                "mean_rmse": float(r["mean_rmse"]),
            }

    summary = {
        "run_utc": utc,
        "elapsed_s": round(elapsed, 1),
        "method": "residual_sigma_sqrt_h (refit on first 80% of train, σ from residuals)",
        "z80": Z80, "z95": Z95,
        "overall": overall,
        "by_family": by_family,
    }
    sum_path = out_dir / "summary.json"
    sum_path.write_text(json.dumps(summary, indent=2))

    md = ["# CI Calibration — empirical coverage of 80/95 bands", "",
          f"**Run UTC:** `{utc}`",
          f"**Method:** {summary['method']}",
          f"**Datasets:** {len(items)}  |  **Elapsed:** {elapsed:.1f}s", "",
          "## Overall",
          f"- mean 80% band coverage:  **{overall['mean_cov80']:.3f}**  "
          f"(target 0.80)" if overall["mean_cov80"] is not None else "",
          f"- mean 95% band coverage:  **{overall['mean_cov95']:.3f}**  "
          f"(target 0.95)" if overall["mean_cov95"] is not None else "",
          "", "## By family", "",
          "| Family | n | mean 80% cov | mean 95% cov | mean RMSE |",
          "|---|---|---|---|---|"]
    for fam, v in sorted(by_family.items()):
        md.append(f"| {fam} | {v['n']} | {v['mean_cov80']:.3f} "
                  f"| {v['mean_cov95']:.3f} | {v['mean_rmse']:.3g} |")
    md.append("")
    md.append(f"_Generated by ci_calibration.py at {utc}_")
    md_path = out_dir / "calibration_summary.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    manifest = {"run_utc": utc, "files": {}}
    for p in [cov_csv, sum_path, md_path]:
        manifest["files"][p.name] = sha256_file(p)
    (out_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2))

    print(f"[calib] done. mean_cov80={overall['mean_cov80']}, "
          f"mean_cov95={overall['mean_cov95']}")
    print(f"[calib] wrote {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
