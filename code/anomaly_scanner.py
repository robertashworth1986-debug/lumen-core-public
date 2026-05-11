"""
anomaly_scanner.py
=============================================================================
Innovation #9 — live anomaly / early-warning scanner.

For every frozen dataset:
  1. Reload raw CSV.
  2. Replicate the v2 split (y_train, y_test) — y_test = "recent observed".
  3. Load the meta-router; pick that dataset's predicted family.
  4. Fit the family champion on y_train, get point forecast P over n_test steps.
  5. Compute residual sigma σ from inner walk-forward (refit first 80% of y_train,
     score the rest) — same method used in forecast_api / ci_calibration.
  6. For each step t in 1..n_test, z[t] = (y_test[t] - P[t]) / (σ * sqrt(t)).
  7. Flag anomalies where |z| > 2 (outside 95% band).
  8. Rank datasets by max |z| over the test window.

Output:
  out/anomaly_scanner/<utc>/{
      anomalies.csv          per-dataset, per-step anomalies (only |z|>2 rows)
      ranked.csv             one row per dataset with max_abs_z, n_anomalies
      summary.json           overall counts
      anomaly_summary.md     top-20 markdown table
      manifest.sha256.json
  }
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
import joblib

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from master_universe_benchmark_v2 import (  # noqa: E402
    model_b_linear_trend, model_d_harmonic_search, model_f_mlp_tuned,
    model_h_lightgbm_lag, model_i_sarima,
)
from meta_router import extract_features  # noqa: E402

CHAMPIONS = {
    "baseline":  model_b_linear_trend,
    "harmonic":  model_d_harmonic_search,
    "neural":    model_f_mlp_tuned,
    "tree":      model_h_lightgbm_lag,
    "classical": model_i_sarima,
}


def _split(y: np.ndarray, test_frac: float = 0.2):
    n = len(y)
    n_test = max(8, int(n * test_frac))
    if n_test >= n - 24:
        n_test = max(8, n // 5)
    return y[: n - n_test], y[n - n_test:], n_test


def _residual_sigma(y_train: np.ndarray, fn) -> float:
    n = len(y_train)
    if n < 30:
        return float(np.std(y_train) or 1.0)
    cut = int(n * 0.8)
    inner_tr = y_train[:cut]; inner_te = y_train[cut:]
    if len(inner_te) < 4:
        return float(np.std(y_train) or 1.0)
    try:
        pred = fn(inner_tr, len(inner_te))
        s = float(np.std(inner_te - pred))
        if not np.isfinite(s) or s <= 0:
            return float(np.std(y_train) or 1.0)
        return s
    except Exception:
        return float(np.std(y_train) or 1.0)


def _scan_one(args):
    ds_name, raw_path, router_payload = args
    try:
        df = pd.read_csv(raw_path)
        y = df["value"].to_numpy(dtype=float)
        if len(y) < 30 or not np.all(np.isfinite(y)):
            return None
        # Optional period column for context
        period = df["period"].astype(str).tolist() if "period" in df.columns else None
    except Exception:
        return None

    y_tr, y_te, n_test = _split(y)

    # --- pick family via router ---
    feats = extract_features(y_tr)
    clf = router_payload["clf"]
    feat_cols = router_payload["feat_cols"]
    X = np.array([[feats[c] for c in feat_cols]])
    family = str(clf.predict(X)[0])
    if family not in CHAMPIONS:
        family = "classical"
    fn = CHAMPIONS[family]

    # --- forecast + sigma ---
    try:
        point = np.asarray(fn(y_tr, n_test), dtype=float)
        if point.shape != (n_test,) or not np.all(np.isfinite(point)):
            return None
    except Exception:
        return None
    sigma = _residual_sigma(y_tr, fn)

    t_idx = np.arange(1, n_test + 1, dtype=float)
    half = sigma * np.sqrt(t_idx)
    z = (y_te - point) / np.where(half > 0, half, 1.0)
    abs_z = np.abs(z)

    anomaly_rows = []
    test_periods = period[-n_test:] if period else [None] * n_test
    for t in range(n_test):
        if abs_z[t] > 2.0:  # outside 95% band
            anomaly_rows.append({
                "dataset": ds_name, "family": family,
                "t_offset_from_train_end": t + 1,
                "period": test_periods[t],
                "actual": float(y_te[t]), "forecast": float(point[t]),
                "sigma_t": float(half[t]), "z": float(z[t]),
            })

    return {
        "dataset": ds_name, "family": family,
        "n_test": n_test, "sigma": sigma,
        "max_abs_z": float(np.max(abs_z)),
        "argmax_t": int(np.argmax(abs_z)) + 1,
        "n_anomalies_2sigma": int(np.sum(abs_z > 2.0)),
        "n_anomalies_3sigma": int(np.sum(abs_z > 3.0)),
        "anomaly_rows": anomaly_rows,
    }


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    utc = os.environ.get("ANOM_UTC")
    if not utc:
        latest = ROOT / "out" / "master_universe_v2" / "latest.txt"
        utc = latest.read_text(encoding="utf-8").strip() if latest.exists() else None
    if not utc:
        print("FATAL: no ANOM_UTC and no latest.txt"); return 1

    raw_dir = ROOT / "out" / "master_universe_v2" / utc / "raw"
    if not raw_dir.exists():
        print(f"FATAL: {raw_dir} does not exist"); return 1

    router_path = ROOT / "out" / "meta_router" / utc / "router.joblib"
    if not router_path.exists():
        # fallback to most recent
        candidates = sorted((ROOT / "out" / "meta_router").glob("*/router.joblib"))
        if not candidates:
            print("FATAL: no router.joblib found"); return 1
        router_path = candidates[-1]
        print(f"[anom] using fallback router: {router_path}")
    router_payload = joblib.load(router_path)

    out_dir = ROOT / "out" / "anomaly_scanner" / utc
    out_dir.mkdir(parents=True, exist_ok=True)

    items = [(p.stem, p, router_payload) for p in sorted(raw_dir.glob("*.csv"))]
    print(f"[anom] scanning {len(items)} datasets...")

    t0 = time.time()
    try:
        from joblib import Parallel, delayed
        results = Parallel(n_jobs=-1, backend="loky", verbose=5)(
            delayed(_scan_one)(it) for it in items
        )
    except Exception as e:
        print(f"[anom] joblib failed: {e}; serial fallback")
        results = [_scan_one(it) for it in items]
    elapsed = time.time() - t0

    results = [r for r in results if r is not None]

    # ranked
    ranked = pd.DataFrame([{k: v for k, v in r.items() if k != "anomaly_rows"}
                           for r in results])
    ranked = ranked.sort_values("max_abs_z", ascending=False).reset_index(drop=True)
    ranked_path = out_dir / "ranked.csv"
    ranked.to_csv(ranked_path, index=False)

    # anomalies (long)
    anom_rows = [row for r in results for row in r["anomaly_rows"]]
    anom_df = pd.DataFrame(anom_rows)
    anom_path = out_dir / "anomalies.csv"
    anom_df.to_csv(anom_path, index=False)

    n_total = len(results)
    n_with_any = int((ranked["n_anomalies_2sigma"] > 0).sum())
    n_3sigma = int((ranked["n_anomalies_3sigma"] > 0).sum())
    summary = {
        "run_utc": utc,
        "elapsed_s": round(elapsed, 1),
        "n_datasets": n_total,
        "n_with_2sigma_anomaly": n_with_any,
        "n_with_3sigma_anomaly": n_3sigma,
        "total_anomaly_points": int(len(anom_df)),
        "method": ("router-picked family champion, residual_sigma_sqrt_h band, "
                   "z = (actual - point)/(sigma*sqrt(h))"),
        "thresholds": {"warn": 2.0, "alert": 3.0},
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    md = ["# Anomaly Scanner — early-warning evidence",
          f"**Run UTC:** `{utc}`  |  **Datasets:** {n_total}  "
          f"|  **Elapsed:** {elapsed:.1f}s",
          "",
          "## Method", "",
          "1. For each frozen dataset, the meta-router picks the family.",
          "2. The family champion is fit on `y_train` and forecasts `y_test`.",
          "3. Residual σ comes from inner walk-forward "
          "(refit on first 80% of train, score the rest).",
          "4. Step-`h` band half-width = `σ·√h`. "
          "z-score = `(actual − point) / band`.",
          "5. **Warn** at `|z|>2` (outside 95% band); **alert** at `|z|>3`.",
          "",
          "## Headline", "",
          f"- Datasets with **≥1 warning** in the test window: "
          f"**{n_with_any}/{n_total}** ({n_with_any/n_total*100:.1f}%)",
          f"- Datasets with **≥1 alert** (3-σ): **{n_3sigma}/{n_total}** "
          f"({n_3sigma/n_total*100:.1f}%)",
          f"- Total alert-grade points: {int((anom_df['z'].abs() > 3).sum()) if len(anom_df) else 0}",
          "",
          "## Top-20 most anomalous datasets", "",
          "| Rank | Dataset | Family | max\\|z\\| | step | n>2σ | n>3σ |",
          "|---:|---|---|---:|---:|---:|---:|"]
    for i, r in ranked.head(20).iterrows():
        md.append(f"| {i+1} | {r['dataset']} | {r['family']} "
                  f"| {r['max_abs_z']:.2f} | {r['argmax_t']} "
                  f"| {r['n_anomalies_2sigma']} | {r['n_anomalies_3sigma']} |")
    md.append("")
    md.append(f"_Generated by anomaly_scanner.py at {utc}_")
    md_path = out_dir / "anomaly_summary.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    manifest = {"run_utc": utc, "files": {p.name: sha256_file(p)
                                          for p in [ranked_path, anom_path,
                                                    out_dir / "summary.json",
                                                    md_path]}}
    (out_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2))

    print(f"[anom] {n_with_any}/{n_total} datasets have ≥1 2σ anomaly; "
          f"{n_3sigma} have ≥1 3σ alert")
    print(f"[anom] wrote {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
