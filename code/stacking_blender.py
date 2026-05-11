"""
stacking_blender.py
=============================================================================
Innovation #8 — non-negative least-squares stacking blender.

For each dataset:
  1. Inner-split y_train (first 80%) -> fit each family champion -> predict
     the inner holdout (last 20% of y_train). Stack -> X_holdout (n_h x 5).
  2. Solve NNLS on (X_holdout, y_holdout) -> weights w (>=0, sum to 1 after).
  3. Refit each champion on the full y_train, predict y_test (n_test) -> X_test.
  4. Blended forecast = X_test @ w.  RMSE vs actual.
  5. Compare blender vs:
       - router (predicted family champion's RMSE on test)
       - each fixed family champion
       - v2 oracle (min RMSE across original 9 models from results.csv)

Outputs (frozen):
  out/stacking_blender/<utc>/{
      results.csv, eval.json, blender_summary.md, manifest.sha256.json
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
from scipy.optimize import nnls

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

from master_universe_benchmark_v2 import (  # noqa: E402
    model_b_linear_trend, model_d_harmonic_search, model_f_mlp_tuned,
    model_h_lightgbm_lag, model_i_sarima,
)

# Family champions (one strongest model per family from the v2 leaderboard).
CHAMPIONS = [
    ("baseline",  "b_linear_trend",     model_b_linear_trend),
    ("harmonic",  "d_harmonic_search",  model_d_harmonic_search),
    ("neural",    "f_mlp_tuned",        model_f_mlp_tuned),
    ("tree",      "h_lightgbm_lag",     model_h_lightgbm_lag),
    ("classical", "i_sarima",           model_i_sarima),
]
FAMS = [c[0] for c in CHAMPIONS]


def _split(y: np.ndarray, test_frac: float = 0.2):
    n = len(y)
    n_test = max(8, int(n * test_frac))
    if n_test >= n - 24:
        n_test = max(8, n // 5)
    return y[: n - n_test], y[n - n_test:], n_test


def _safe_pred(fn, y_tr, n_test):
    try:
        p = np.asarray(fn(y_tr, n_test), dtype=float)
        if p.shape != (n_test,) or not np.all(np.isfinite(p)):
            return None
        return p
    except Exception:
        return None


def _fit_blender(X_holdout: np.ndarray, y_holdout: np.ndarray) -> np.ndarray:
    """NNLS, then renormalize to sum to 1. Falls back to equal weights."""
    try:
        w, _ = nnls(X_holdout, y_holdout)
        s = float(np.sum(w))
        if s > 0 and np.all(np.isfinite(w)):
            return w / s
    except Exception:
        pass
    return np.full(X_holdout.shape[1], 1.0 / X_holdout.shape[1])


def _evaluate_one(args):
    ds_name, raw_path = args
    try:
        df = pd.read_csv(raw_path)
        y = df["value"].to_numpy(dtype=float)
        if len(y) < 40 or not np.all(np.isfinite(y)):
            return None
    except Exception:
        return None

    y_tr, y_te, n_test = _split(y)

    # Inner split for blender weight learning.
    n_tr = len(y_tr)
    inner_cut = int(n_tr * 0.8)
    if inner_cut < 16 or n_tr - inner_cut < 4:
        return None
    y_tr_inner = y_tr[:inner_cut]
    y_tr_hold = y_tr[inner_cut:]
    n_hold = len(y_tr_hold)

    # --- Stage 1: predict holdout with each champion fit on inner train ---
    X_hold = np.zeros((n_hold, len(CHAMPIONS)))
    fail_inner = []
    for i, (_, _, fn) in enumerate(CHAMPIONS):
        p = _safe_pred(fn, y_tr_inner, n_hold)
        if p is None:
            fail_inner.append(i)
            X_hold[:, i] = float(np.mean(y_tr_inner))
        else:
            X_hold[:, i] = p

    # Solve blend weights.
    w = _fit_blender(X_hold, y_tr_hold)

    # --- Stage 2: refit on full y_train, predict test ---
    X_test = np.zeros((n_test, len(CHAMPIONS)))
    fam_rmse = {}
    for i, (fam, _, fn) in enumerate(CHAMPIONS):
        p = _safe_pred(fn, y_tr, n_test)
        if p is None:
            X_test[:, i] = float(np.mean(y_tr))
            fam_rmse[fam] = float("nan")
        else:
            X_test[:, i] = p
            fam_rmse[fam] = float(np.sqrt(np.mean((y_te - p) ** 2)))

    blend = X_test @ w
    rmse_blend = float(np.sqrt(np.mean((y_te - blend) ** 2)))

    return {
        "dataset": ds_name,
        "n_train": len(y_tr), "n_test": n_test, "n_hold": n_hold,
        "rmse_blend": rmse_blend,
        **{f"rmse_{fam}": fam_rmse[fam] for fam in FAMS},
        **{f"w_{fam}": float(w[i]) for i, fam in enumerate(FAMS)},
    }


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    utc = os.environ.get("BLEND_UTC")
    if not utc:
        latest = ROOT / "out" / "master_universe_v2" / "latest.txt"
        utc = latest.read_text(encoding="utf-8").strip() if latest.exists() else None
    if not utc:
        print("FATAL: no BLEND_UTC and no latest.txt"); return 1

    raw_dir = ROOT / "out" / "master_universe_v2" / utc / "raw"
    if not raw_dir.exists():
        print(f"FATAL: {raw_dir} does not exist"); return 1

    out_dir = ROOT / "out" / "stacking_blender" / utc
    out_dir.mkdir(parents=True, exist_ok=True)

    # Read v2 results to get the per-dataset oracle RMSE (across all 9 models).
    res = pd.read_csv(ROOT / "out" / "master_universe_v2" / utc / "results.csv")
    v2_oracle = (res.dropna(subset=["rmse"])
                    .groupby("dataset")["rmse"].min().to_dict())

    items = [(p.stem, p) for p in sorted(raw_dir.glob("*.csv"))]
    print(f"[blender] run {utc}: {len(items)} datasets")

    t0 = time.time()
    try:
        from joblib import Parallel, delayed
        results = Parallel(n_jobs=-1, backend="loky", verbose=5)(
            delayed(_evaluate_one)(it) for it in items
        )
    except Exception as e:
        print(f"[blender] joblib failed: {e}; falling back to serial")
        results = [_evaluate_one(it) for it in items]
    elapsed = time.time() - t0

    rows = [r for r in results if r is not None]
    df = pd.DataFrame(rows)
    df["rmse_v2_oracle"] = df["dataset"].map(v2_oracle)
    df["rel_blend_vs_oracle"] = df["rmse_blend"] / df["rmse_v2_oracle"]
    df["beats_v2_oracle"] = df["rmse_blend"] < df["rmse_v2_oracle"] * 0.999

    res_path = out_dir / "results.csv"
    df.to_csv(res_path, index=False)

    # Win counts: blend vs each fixed family on test
    fam_cols = [f"rmse_{f}" for f in FAMS]
    rmse_mat = df[["rmse_blend"] + fam_cols].to_numpy()
    strat_names = ["blend"] + FAMS
    mins = np.nanmin(rmse_mat, axis=1, keepdims=True)
    win_counts = {}
    for i, s in enumerate(strat_names):
        wins = int(np.sum(np.abs(rmse_mat[:, i:i+1] - mins) <= 1e-9))
        win_counts[s] = wins

    # Median rel-RMSE vs row-min (oracle of blend+5families)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel_to_row_min = rmse_mat / mins
    median_rel = {s: float(np.nanmedian(rel_to_row_min[:, i]))
                  for i, s in enumerate(strat_names)}

    # Median rel vs v2 oracle (the 9-model min)
    median_blend_vs_v2 = float(df["rel_blend_vs_oracle"].median())
    n_beat_v2 = int(df["beats_v2_oracle"].sum())

    # Average blend weights
    avg_weights = {f: float(df[f"w_{f}"].mean()) for f in FAMS}

    summary = {
        "run_utc": utc,
        "n_datasets": int(len(df)),
        "elapsed_s": round(elapsed, 1),
        "win_counts_in_blend_plus_fams": win_counts,
        "median_rel_rmse_in_blend_plus_fams": median_rel,
        "median_blend_rel_vs_v2_oracle": median_blend_vs_v2,
        "blender_beats_v2_oracle": n_beat_v2,
        "avg_blend_weights": avg_weights,
    }
    sum_path = out_dir / "eval.json"
    sum_path.write_text(json.dumps({"summary": summary}, indent=2))

    md = ["# Stacking Blender — Evidence",
          f"**Run UTC:** `{utc}`  |  **Datasets:** {len(df)}  "
          f"|  **Elapsed:** {elapsed:.1f}s",
          "",
          "## Method",
          "Inner-split y_train (80/20). Fit each of 5 family champions on inner-train, "
          "predict the inner holdout. Solve **non-negative least squares** "
          "(`scipy.optimize.nnls`) for blend weights `w >= 0`, renormalize to "
          "sum to 1. Refit champions on full y_train, predict y_test, blend with `w`.",
          "",
          "## Win counts (blend vs the 5 fixed family champions)", "",
          "| Strategy | Wins | Median rel-RMSE (1.0 = oracle of these 6) |",
          "|---|---:|---:|"]
    for s in strat_names:
        md.append(f"| {s} | {win_counts[s]} | {median_rel[s]:.4f} |")

    md += ["", "## Performance vs full v2 oracle (the min RMSE across all 9 v2 models)",
           f"- Median **rmse_blend / rmse_v2_oracle** = "
           f"**{median_blend_vs_v2:.4f}** (1.0 = matches oracle).",
           f"- Datasets where blend strictly beats v2 oracle (≥0.1% margin): "
           f"**{n_beat_v2}/{len(df)}**.",
           "",
           "## Average blend weights across all datasets", "",
           "| Family | Avg weight |", "|---|---:|"]
    for f, v in sorted(avg_weights.items(), key=lambda kv: -kv[1]):
        md.append(f"| {f} | {v:.3f} |")
    md.append("")
    md.append(f"_Generated by stacking_blender.py at {utc}_")
    md_path = out_dir / "blender_summary.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    manifest = {"run_utc": utc, "files": {p.name: sha256_file(p)
                                          for p in [res_path, sum_path, md_path]}}
    (out_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2))

    print(f"[blender] win_counts: {win_counts}")
    print(f"[blender] median rel-RMSE (in 6-strategy oracle): {median_rel}")
    print(f"[blender] median blend / v2_oracle: {median_blend_vs_v2:.4f}")
    print(f"[blender] beats v2 oracle on {n_beat_v2}/{len(df)} datasets")
    print(f"[blender] avg weights: {avg_weights}")
    print(f"[blender] wrote {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
