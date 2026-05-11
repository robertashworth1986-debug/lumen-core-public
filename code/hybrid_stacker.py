"""
hybrid_stacker.py
=========================================================================
LumenCore innovation #2: residual-stacked forecasters.

We define three new models and evaluate them against the same 80/20
walk-forward split as `master_universe_benchmark_v2`. Because we re-use
the cached raw CSVs in
    out/master_universe_v2/<UTC>/raw/*.csv
we can score the new models on every dataset of an existing frozen run
without rebuilding the universe.

Models added:
  j_sarima_plus_harmonic   SARIMA mean + harmonic-search on residuals
  k_linear_plus_harmonic   linear trend + harmonic-search on residuals
  l_router_oracle          family champion picked by the meta-router
                           (uses the already-trained out/meta_router/<UTC>/router.joblib)

For each dataset we compute RMSE of each new model on the same y_test
(last 20%, min 8) the v2 benchmark used. We then write:

    out/hybrid_stacker/<UTC>/results.csv          long-format rmse rows
    out/hybrid_stacker/<UTC>/scoreboard.csv       wins per strategy
    out/hybrid_stacker/<UTC>/eval.json            summary
    out/hybrid_stacker/<UTC>/stacker_summary.md   human-readable report
    out/hybrid_stacker/<UTC>/manifest.sha256.json

Run:
    python code/hybrid_stacker.py
    python code/hybrid_stacker.py --run-utc 20260505T121657Z
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

# Re-use the v1 model functions (already used by v2)
from master_universe_benchmark import (  # noqa: E402
    model_a_naive, model_b_linear_trend, model_d_harmonic_search,
)

V2_RUNS = ROOT / "out" / "master_universe_v2"
ROUTER_RUNS = ROOT / "out" / "meta_router"
OUT_BASE = ROOT / "out" / "hybrid_stacker"

FAMILIES = {
    "baseline":  ["a_naive", "b_linear_trend"],
    "harmonic":  ["c_harmonic_fixed12", "d_harmonic_search"],
    "neural":    ["e_mlp_untuned", "f_mlp_tuned"],
    "tree":      ["g_xgboost_lag", "h_lightgbm_lag"],
    "classical": ["i_sarima"],
}
MODEL_TO_FAMILY = {m: f for f, ms in FAMILIES.items() for m in ms}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def _sarima_fit_forecast(y_train: np.ndarray,
                         n_test: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (in_sample_fitted_values, out_of_sample_forecast)."""
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX
    except Exception:
        return y_train.copy(), model_a_naive(y_train, n_test)
    try:
        m = SARIMAX(
            y_train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12),
            enforce_stationarity=False, enforce_invertibility=False,
        ).fit(disp=False, maxiter=50)
        in_sample = np.asarray(m.fittedvalues, dtype=float)
        # SARIMAX returns NaN for the very first burn-in; replace with y_train
        bad = ~np.isfinite(in_sample)
        if bad.any():
            in_sample = in_sample.copy()
            in_sample[bad] = y_train[bad]
        oos = np.asarray(m.forecast(steps=n_test), dtype=float)
        return in_sample, oos
    except Exception:
        return y_train.copy(), model_a_naive(y_train, n_test)


def _linear_fit_forecast(y_train: np.ndarray,
                         n_test: int) -> tuple[np.ndarray, np.ndarray]:
    n = len(y_train)
    t = np.arange(n)
    A = np.vstack([t, np.ones(n)]).T
    slope, intercept = np.linalg.lstsq(A, y_train, rcond=None)[0]
    in_sample = slope * t + intercept
    t_oos = np.arange(n, n + n_test)
    oos = slope * t_oos + intercept
    return in_sample, oos


def model_j_sarima_plus_harmonic(y_train: np.ndarray, n_test: int) -> np.ndarray:
    """SARIMA mean + harmonic_search on the residual."""
    sarima_in, sarima_oos = _sarima_fit_forecast(y_train, n_test)
    resid = y_train - sarima_in
    if not np.isfinite(resid).all() or len(resid) < 24:
        return sarima_oos
    try:
        resid_oos = model_d_harmonic_search(resid, n_test)
    except Exception:
        return sarima_oos
    return sarima_oos + np.asarray(resid_oos, dtype=float)


def model_k_linear_plus_harmonic(y_train: np.ndarray, n_test: int) -> np.ndarray:
    """Linear trend + harmonic_search on the residual.

    Should beat plain harmonic when there's a non-stationary trend, and beat
    plain linear when there's seasonality.
    """
    lin_in, lin_oos = _linear_fit_forecast(y_train, n_test)
    resid = y_train - lin_in
    if len(resid) < 24:
        return lin_oos
    try:
        resid_oos = model_d_harmonic_search(resid, n_test)
    except Exception:
        return lin_oos
    return lin_oos + np.asarray(resid_oos, dtype=float)


# ---------------------------------------------------------------------------
# Eval
# ---------------------------------------------------------------------------
def _eval_split(y: np.ndarray, test_frac: float = 0.2) -> tuple[np.ndarray, np.ndarray]:
    """Replicate the master_universe_benchmark_v2 split exactly."""
    n = len(y)
    n_test = max(8, int(n * test_frac))
    if n_test >= n - 24:
        n_test = max(8, n // 5)
    return y[: n - n_test], y[n - n_test:]


def _rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def _load_router(run_utc: str):
    p = ROUTER_RUNS / run_utc / "router.joblib"
    if not p.exists():
        return None, None
    try:
        import joblib
        bundle = joblib.load(p)
        return bundle["clf"], bundle["feat_cols"]
    except Exception:
        return None, None


def _features_for_series(y: np.ndarray, feat_cols: list[str]) -> np.ndarray:
    from meta_router import extract_features
    feats = extract_features(y)
    row = [float(feats.get(c, 0.0)) for c in feat_cols]
    return np.array(row, dtype=float).reshape(1, -1)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def evaluate_run(run_utc: str) -> dict:
    run_dir = V2_RUNS / run_utc
    raw_dir = run_dir / "raw"
    res_path = run_dir / "results.csv"
    if not res_path.exists() or not raw_dir.exists():
        raise FileNotFoundError(f"missing v2 outputs for {run_utc}")

    res = pd.read_csv(res_path)
    res["family"] = res["model"].map(MODEL_TO_FAMILY)

    # Baseline matrix: per (dataset, family) min RMSE  (the v2 family champion)
    fam_rmse = (res.dropna(subset=["family", "rmse"])
                   .groupby(["dataset", "family"])["rmse"].min()
                   .unstack("family"))
    # Keep only datasets where every family has a value
    fam_rmse = fam_rmse.dropna(how="any")

    # Best of all 9 v2 models per dataset (the "v2 oracle")
    v2_best = res.dropna(subset=["rmse"]).groupby("dataset")["rmse"].min()

    router_clf, router_feat_cols = _load_router(run_utc)

    rows: list[dict] = []
    skipped: list[str] = []
    n = len(fam_rmse.index)
    t0 = time.time()
    for i, ds in enumerate(fam_rmse.index, 1):
        if i % 50 == 0 or i == n:
            print(f"[stacker] {i}/{n} ({time.time()-t0:.0f}s)", flush=True)
        f = raw_dir / f"{ds}.csv"
        if not f.exists():
            skipped.append(ds); continue
        try:
            df = pd.read_csv(f)
            y = df["value"].to_numpy(dtype=float)
        except Exception:
            skipped.append(ds); continue
        if len(y) < 30:
            skipped.append(ds); continue

        y_tr, y_te = _eval_split(y)
        n_test = len(y_te)

        # New models
        try:
            p_j = model_j_sarima_plus_harmonic(y_tr, n_test)
            rmse_j = _rmse(y_te, p_j)
        except Exception:
            rmse_j = float("nan")
        try:
            p_k = model_k_linear_plus_harmonic(y_tr, n_test)
            rmse_k = _rmse(y_te, p_k)
        except Exception:
            rmse_k = float("nan")

        # Router-oracle: ask the router which family, then look up that
        # family's already-computed RMSE on this dataset.
        rmse_router = float("nan")
        if router_clf is not None and router_feat_cols is not None:
            try:
                X = _features_for_series(y_tr, router_feat_cols)
                fam = router_clf.predict(X)[0]
                rmse_router = float(fam_rmse.loc[ds, fam])
            except Exception:
                pass

        rows.append({
            "dataset": ds,
            "n_train": len(y_tr),
            "n_test": n_test,
            "rmse_j_sarima_plus_harmonic": rmse_j,
            "rmse_k_linear_plus_harmonic": rmse_k,
            "rmse_l_router": rmse_router,
            "v2_best_rmse": float(v2_best.loc[ds]),
            "v2_best_family_classical": float(fam_rmse.loc[ds, "classical"]),
            "v2_best_family_harmonic": float(fam_rmse.loc[ds, "harmonic"]),
            "v2_best_family_tree": float(fam_rmse.loc[ds, "tree"]),
            "v2_best_family_baseline": float(fam_rmse.loc[ds, "baseline"]),
            "v2_best_family_neural": float(fam_rmse.loc[ds, "neural"]),
        })

    df = pd.DataFrame(rows)
    return {"results": df, "skipped": skipped, "elapsed_s": round(time.time() - t0, 1)}


def score(df: pd.DataFrame) -> dict:
    """Strategy-vs-strategy scoreboard. Each strategy has one RMSE per dataset.

    The "router" strategy is a meta-strategy that picks among the 5 v2 family
    champions. The two stacker models are new candidates.
    """
    strategies = {
        "router": df["rmse_l_router"].to_numpy(),
        "j_sarima_plus_harmonic": df["rmse_j_sarima_plus_harmonic"].to_numpy(),
        "k_linear_plus_harmonic": df["rmse_k_linear_plus_harmonic"].to_numpy(),
        "fixed_classical": df["v2_best_family_classical"].to_numpy(),
        "fixed_harmonic": df["v2_best_family_harmonic"].to_numpy(),
        "fixed_tree": df["v2_best_family_tree"].to_numpy(),
        "fixed_baseline": df["v2_best_family_baseline"].to_numpy(),
        "fixed_neural": df["v2_best_family_neural"].to_numpy(),
    }
    # Replace NaN with +inf so they never win, and also drop datasets where
    # all values are NaN.
    arrays = {}
    for k, v in strategies.items():
        a = np.array(v, dtype=float)
        a[~np.isfinite(a)] = np.inf
        arrays[k] = a
    n = len(df)
    # Oracle = best of the eight strategies per dataset
    stack = np.vstack(list(arrays.values()))
    oracle = stack.min(axis=0)
    # Win counts (with tie tolerance)
    mins = oracle
    tol = 1e-9
    win_counts = {k: int(np.sum(np.abs(arrays[k] - mins) <= tol)) for k in arrays}

    # Median relative RMSE vs oracle
    rel = {k: arrays[k] / (oracle + 1e-12) for k in arrays}
    median_rel = {k: round(float(np.median(rel[k][np.isfinite(rel[k])])), 4) for k in arrays}
    mean_rel = {k: round(float(np.mean(rel[k][np.isfinite(rel[k])])), 4) for k in arrays}

    # Beats-v2-oracle: new strategy strictly improves over the v2 best (best of 9 v2 models)
    v2_best = df["v2_best_rmse"].to_numpy(dtype=float)
    beats_v2 = {}
    for k in ("router", "j_sarima_plus_harmonic", "k_linear_plus_harmonic"):
        a = arrays[k]
        beats_v2[k] = int(np.sum(a < v2_best - 1e-9))

    return {
        "n_datasets": n,
        "win_counts": win_counts,
        "win_rates": {k: round(win_counts[k] / n, 4) for k in win_counts},
        "median_rel_rmse_vs_oracle": median_rel,
        "mean_rel_rmse_vs_oracle": mean_rel,
        "beats_v2_oracle": beats_v2,
    }


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_outputs(run_utc: str, df: pd.DataFrame, summary: dict, elapsed: float) -> Path:
    out_dir = OUT_BASE / run_utc
    out_dir.mkdir(parents=True, exist_ok=True)

    df.to_csv(out_dir / "results.csv", index=False)

    sb = pd.DataFrame({
        "strategy": list(summary["win_counts"].keys()),
        "wins": list(summary["win_counts"].values()),
        "win_rate": [summary["win_rates"][k] for k in summary["win_counts"]],
        "median_rel_rmse_vs_oracle": [summary["median_rel_rmse_vs_oracle"][k]
                                      for k in summary["win_counts"]],
        "mean_rel_rmse_vs_oracle": [summary["mean_rel_rmse_vs_oracle"][k]
                                    for k in summary["win_counts"]],
    }).sort_values("wins", ascending=False)
    sb.to_csv(out_dir / "scoreboard.csv", index=False)

    eval_payload = {"summary": summary, "elapsed_s": elapsed, "run_utc": run_utc}
    (out_dir / "eval.json").write_text(json.dumps(eval_payload, indent=2),
                                       encoding="utf-8")

    md: list[str] = []
    md.append(f"# LumenCore Hybrid Stacker — Evidence (run {run_utc})")
    md.append("")
    md.append(f"Evaluated on **{summary['n_datasets']}** datasets from the v2 frozen run, "
              f"using the same 80/20 walk-forward split.")
    md.append("")
    md.append("## Strategy scoreboard")
    md.append("")
    md.append("| Strategy | Wins | Win rate | Median RMSE / oracle |")
    md.append("|---|---:|---:|---:|")
    for _, row in sb.iterrows():
        md.append(f"| {row['strategy']} | {int(row['wins'])} | "
                  f"{row['win_rate']*100:.1f}% | {row['median_rel_rmse_vs_oracle']:.3f} |")
    md.append("")
    md.append("## Beats the v2 oracle (best of all 9 v2 models per dataset)")
    md.append("")
    md.append("| New model | Datasets where it strictly beats v2-best |")
    md.append("|---|---:|")
    for k, n in summary["beats_v2_oracle"].items():
        md.append(f"| {k} | {n} / {summary['n_datasets']} ({n/summary['n_datasets']*100:.1f}%) |")
    md.append("")
    md.append("Frozen by `code/hybrid_stacker.py`.")
    (out_dir / "stacker_summary.md").write_text("\n".join(md), encoding="utf-8")

    manifest = {}
    for p in sorted(out_dir.glob("*")):
        if p.is_file() and p.name != "manifest.sha256.json":
            manifest[p.name] = _sha256(p)
    (out_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2),
                                                  encoding="utf-8")
    return out_dir


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-utc", default=None)
    args = ap.parse_args(argv)

    run_utc = args.run_utc
    if not run_utc:
        latest = V2_RUNS / "latest.txt"
        if latest.exists():
            run_utc = latest.read_text(encoding="utf-8").strip()
        else:
            dirs = sorted(p.name for p in V2_RUNS.iterdir() if p.is_dir())
            run_utc = dirs[-1] if dirs else None
    if not run_utc:
        print("no benchmark run found")
        return 2

    print(f"[stacker] using benchmark run {run_utc}")
    eval_out = evaluate_run(run_utc)
    df = eval_out["results"]
    summary = score(df)
    print(f"[stacker] {len(df)} datasets, {len(eval_out['skipped'])} skipped")
    print(f"[stacker] win counts: {summary['win_counts']}")
    print(f"[stacker] median rel RMSE vs oracle: {summary['median_rel_rmse_vs_oracle']}")
    print(f"[stacker] beats v2 oracle: {summary['beats_v2_oracle']}")
    out_dir = write_outputs(run_utc, df, summary, eval_out["elapsed_s"])
    print(f"[stacker] wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
