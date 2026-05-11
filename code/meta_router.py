"""
meta_router.py
=========================================================================
LumenCore meta-router (innovation #1):

Per-dataset family selector. Trained from a frozen benchmark run, it
predicts which model family (baseline / classical / harmonic / neural /
tree) will produce the lowest test RMSE for a held-out dataset.

Inputs (default = latest published run):
    out/master_universe_v2/<UTC>/results.csv   — long-format RMSE per (dataset, model)
    out/master_universe_v2/<UTC>/raw/*.csv     — raw series with [date, value]

Outputs:
    out/meta_router/<UTC>/features.csv         — feature matrix
    out/meta_router/<UTC>/labels.csv           — winning family per dataset
    out/meta_router/<UTC>/router.joblib        — trained classifier
    out/meta_router/<UTC>/eval.json            — leave-one-dataset-out CV
    out/meta_router/<UTC>/router_summary.md    — human-readable summary
    out/meta_router/<UTC>/manifest.sha256.json

Fairness:
    - K-fold CV (default K=10) — the family label for any dataset comes from
      a model that never saw that dataset during training. No leakage.
    - Compares router-picked-family RMSE vs. each fixed-family RMSE on the
      held-out dataset, using the per-dataset family champion (best model
      within family) — same rule as the master benchmark scoreboard.

Run:
    python code/meta_router.py
    python code/meta_router.py --run-utc 20260505T121657Z
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "out" / "master_universe_v2"
OUT_BASE = ROOT / "out" / "meta_router"

FAMILIES = {
    "baseline":  ["a_naive", "b_linear_trend"],
    "harmonic":  ["c_harmonic_fixed12", "d_harmonic_search"],
    "neural":    ["e_mlp_untuned", "f_mlp_tuned"],
    "tree":      ["g_xgboost_lag", "h_lightgbm_lag"],
    "classical": ["i_sarima"],
}
MODEL_TO_FAMILY = {m: f for f, ms in FAMILIES.items() for m in ms}


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------
def _safe(x: float, fallback: float = 0.0) -> float:
    if x is None or not np.isfinite(x):
        return fallback
    return float(x)


def extract_features(y: np.ndarray) -> dict:
    """Cheap, signal-rich features that should let a small classifier
    distinguish smooth-trended (linear/SARIMA) from periodic (harmonic)
    from noisy/non-linear (tree)."""
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    n = len(y)
    feats: dict = {"n": n}
    if n < 12:
        return {**feats, **{k: 0.0 for k in
            ["mean","std","cv","skew","kurt","trend_r2","trend_slope",
             "season_strength","spectral_top1","spectral_top2","spectral_entropy",
             "ac1","ac12","frac_zero_cross","range_norm","monotone"]}}

    mean = float(np.mean(y))
    std = float(np.std(y))
    cv = std / abs(mean) if mean != 0 else 0.0
    # skew, kurt without scipy
    z = (y - mean) / (std + 1e-12)
    skew = float(np.mean(z**3))
    kurt = float(np.mean(z**4) - 3.0)

    # linear trend strength
    t = np.arange(n)
    A = np.vstack([t, np.ones(n)]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
    yhat = slope * t + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - mean) ** 2)) + 1e-12
    trend_r2 = 1.0 - ss_res / ss_tot
    trend_slope = float(slope) / (abs(mean) + 1e-12)

    # detrended for season + spectral
    resid = y - yhat

    # autocorrelations
    def _ac(lag: int) -> float:
        if lag >= n:
            return 0.0
        a = resid[:-lag] - resid[:-lag].mean()
        b = resid[lag:] - resid[lag:].mean()
        d = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
        return float(np.dot(a, b) / d)

    ac1 = _ac(1)
    ac12 = _ac(12)

    # season strength via 12-period STL-lite: var(seasonal_mean) / var(resid)
    if n >= 24:
        period = 12 if n >= 36 else max(2, n // 6)
        idx = np.arange(n) % period
        season_means = np.array([resid[idx == k].mean() for k in range(period)])
        season_full = season_means[idx]
        season_strength = float(np.var(season_full) / (np.var(resid) + 1e-12))
    else:
        season_strength = 0.0

    # spectral via real FFT on detrended series
    Y = np.fft.rfft(resid - resid.mean())
    P = np.abs(Y) ** 2
    if len(P) > 1:
        P_no_dc = P[1:]
        total = float(P_no_dc.sum()) + 1e-12
        order = np.argsort(P_no_dc)[::-1]
        top1 = float(P_no_dc[order[0]] / total)
        top2 = float(P_no_dc[order[1]] / total) if len(order) > 1 else 0.0
        p_norm = P_no_dc / total
        p_norm = p_norm[p_norm > 0]
        spectral_entropy = float(-np.sum(p_norm * np.log(p_norm)) / np.log(len(P_no_dc) + 1e-12))
    else:
        top1 = top2 = spectral_entropy = 0.0

    # zero-crossings of resid
    sign = np.sign(resid)
    zc = int(np.sum(sign[1:] != sign[:-1]))
    frac_zero_cross = zc / max(1, n - 1)

    range_norm = float((y.max() - y.min()) / (abs(mean) + 1e-12))
    monotone = float(np.mean(np.diff(y) > 0))

    return {
        **feats,
        "mean": _safe(mean),
        "std": _safe(std),
        "cv": _safe(cv),
        "skew": _safe(skew),
        "kurt": _safe(kurt),
        "trend_r2": _safe(trend_r2),
        "trend_slope": _safe(trend_slope),
        "season_strength": _safe(season_strength),
        "spectral_top1": _safe(top1),
        "spectral_top2": _safe(top2),
        "spectral_entropy": _safe(spectral_entropy),
        "ac1": _safe(ac1),
        "ac12": _safe(ac12),
        "frac_zero_cross": _safe(frac_zero_cross),
        "range_norm": _safe(range_norm),
        "monotone": _safe(monotone),
    }


# ---------------------------------------------------------------------------
# Build features + labels from a frozen benchmark run
# ---------------------------------------------------------------------------
def build_table(run_utc: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    run_dir = RUNS_DIR / run_utc
    raw_dir = run_dir / "raw"
    res_path = run_dir / "results.csv"
    if not res_path.exists():
        raise FileNotFoundError(res_path)
    if not raw_dir.exists():
        raise FileNotFoundError(raw_dir)

    res = pd.read_csv(res_path)
    res["family"] = res["model"].map(MODEL_TO_FAMILY)
    # Per-dataset, per-family champion = min RMSE within family
    fam_rmse = (res.dropna(subset=["family", "rmse"])
                   .groupby(["dataset", "family"])["rmse"].min()
                   .unstack("family"))
    # Drop datasets where any family is NaN (incomparable)
    fam_rmse = fam_rmse.dropna(how="any")
    fam_rmse["winner"] = fam_rmse.idxmin(axis=1)

    feat_rows = []
    for ds in fam_rmse.index:
        f = raw_dir / f"{ds}.csv"
        if not f.exists():
            continue
        try:
            df = pd.read_csv(f)
            y = df["value"].to_numpy(dtype=float)
        except Exception:
            continue
        feats = extract_features(y)
        feats["dataset"] = ds
        feat_rows.append(feats)
    features = pd.DataFrame(feat_rows).set_index("dataset")
    common = features.index.intersection(fam_rmse.index)
    features = features.loc[common].copy()
    fam_rmse = fam_rmse.loc[common].copy()
    labels = fam_rmse[["winner"]].copy()
    return features, labels, fam_rmse


# ---------------------------------------------------------------------------
# Train + eval router
# ---------------------------------------------------------------------------
def train_and_evaluate(features: pd.DataFrame,
                       labels: pd.DataFrame,
                       fam_rmse: pd.DataFrame,
                       n_splits: int = 10) -> dict:
    """K-fold CV: for each fold, train on the remaining folds, predict the
    family for held-out datasets, look up the actual RMSE for that family
    on each held-out dataset. Compare to: (a) each fixed family, (b) oracle.

    Uses LightGBM for speed (sklearn GBM is too slow at N=673 with LOO).
    """
    try:
        from sklearn.model_selection import KFold
    except ImportError as e:
        raise RuntimeError(f"sklearn required: {e}")

    # Pick fastest available classifier
    clf_factory = None
    clf_name = None
    try:
        from lightgbm import LGBMClassifier  # type: ignore
        def _mk():
            return LGBMClassifier(
                n_estimators=300, learning_rate=0.05, num_leaves=31,
                min_child_samples=10, random_state=42, verbose=-1,
            )
        clf_factory, clf_name = _mk, "lightgbm"
    except Exception:
        from sklearn.ensemble import RandomForestClassifier
        def _mk():
            return RandomForestClassifier(
                n_estimators=300, max_depth=None, n_jobs=-1, random_state=42,
            )
        clf_factory, clf_name = _mk, "random_forest"

    feat_cols = [c for c in features.columns if c != "n"]
    X_all = features[feat_cols].to_numpy(dtype=float)
    y_all = labels["winner"].to_numpy()
    ds_idx = list(features.index)
    fam_cols = list(fam_rmse.columns.drop("winner"))

    n = len(ds_idx)
    routed_rmse = np.zeros(n)
    routed_family: list[str] = [""] * n
    kf = KFold(n_splits=min(n_splits, n), shuffle=True, random_state=42)
    for tr_idx, te_idx in kf.split(X_all):
        clf = clf_factory()
        clf.fit(X_all[tr_idx], y_all[tr_idx])
        preds = clf.predict(X_all[te_idx])
        for j, i in enumerate(te_idx):
            routed_family[i] = preds[j]
            routed_rmse[i] = float(fam_rmse.iloc[i][preds[j]])

    # Per-family fixed
    per_fam_rmse = {f: fam_rmse[f].to_numpy(dtype=float) for f in fam_cols}
    oracle_rmse = fam_rmse[fam_cols].min(axis=1).to_numpy(dtype=float)

    # Win counts: who has the lowest RMSE on each dataset including the router?
    # Tie-handling: if multiple strategies achieve the min RMSE on a dataset
    # (router by construction ties with the family it picked), count all
    # tied strategies. The router gets credit when it picked correctly.
    rmse_by_strategy = {**per_fam_rmse, "router": routed_rmse}
    strategies = list(rmse_by_strategy.keys())
    stack = np.vstack([rmse_by_strategy[s] for s in strategies])  # (S, N)
    mins = stack.min(axis=0)
    tol = 1e-9
    win_counts = {s: int(np.sum(np.abs(rmse_by_strategy[s] - mins) <= tol))
                  for s in strategies}

    # Mean / median normalized RMSE (relative to oracle = 1.0)
    norm = lambda arr: arr / (oracle_rmse + 1e-12)
    rel = {s: norm(rmse_by_strategy[s]) for s in strategies}
    summary = {
        "n_datasets": len(ds_idx),
        "win_counts": win_counts,
        "win_rates": {s: round(win_counts[s] / len(ds_idx), 4) for s in strategies},
        "median_rel_rmse_vs_oracle": {s: round(float(np.median(rel[s])), 4) for s in strategies},
        "mean_rel_rmse_vs_oracle": {s: round(float(np.mean(rel[s])), 4) for s in strategies},
        "router_chose_correctly_pct": round(
            float(np.mean(np.array(routed_family) == y_all)) * 100, 2),
    }

    # Final classifier trained on all data (this is the production router)
    final_clf = clf_factory()
    final_clf.fit(X_all, y_all)
    try:
        feat_imp = dict(zip(feat_cols,
                            [round(float(v), 4) for v in final_clf.feature_importances_]))
    except Exception:
        feat_imp = {}

    return {
        "summary": {**summary, "classifier": clf_name, "cv_folds": min(n_splits, n)},
        "feature_importance": feat_imp,
        "feat_cols": feat_cols,
        "ds_idx": ds_idx,
        "routed_family": routed_family,
        "routed_rmse": routed_rmse.tolist(),
        "per_family_rmse": {k: v.tolist() for k, v in per_fam_rmse.items()},
        "oracle_rmse": oracle_rmse.tolist(),
        "_clf": final_clf,
    }


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------
def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_outputs(run_utc: str,
                  features: pd.DataFrame,
                  labels: pd.DataFrame,
                  result: dict) -> Path:
    out_dir = OUT_BASE / run_utc
    out_dir.mkdir(parents=True, exist_ok=True)

    features.to_csv(out_dir / "features.csv")
    labels.to_csv(out_dir / "labels.csv")

    # Save the final classifier
    try:
        import joblib
        joblib.dump({"clf": result["_clf"], "feat_cols": result["feat_cols"]},
                    out_dir / "router.joblib")
    except Exception as e:
        print(f"[warn] joblib save failed: {e}")

    eval_payload = {k: v for k, v in result.items() if k != "_clf"}
    (out_dir / "eval.json").write_text(json.dumps(eval_payload, indent=2),
                                       encoding="utf-8")

    s = result["summary"]
    md = []
    md.append(f"# LumenCore Meta-Router — Evidence (run {run_utc})")
    md.append("")
    md.append(f"Trained on **{s['n_datasets']}** datasets, {s.get('cv_folds', 10)}-fold cross-validated "
              f"using a `{s.get('classifier','?')}` classifier.")
    md.append("")
    md.append("## Strategy scoreboard (lowest RMSE per dataset)")
    md.append("")
    md.append("| Strategy | Wins | Win rate | Median RMSE vs oracle |")
    md.append("|---|---:|---:|---:|")
    for strat in sorted(s["win_counts"], key=lambda k: -s["win_counts"][k]):
        md.append(
            f"| {strat} | {s['win_counts'][strat]} | "
            f"{s['win_rates'][strat]*100:.1f}% | "
            f"{s['median_rel_rmse_vs_oracle'][strat]:.3f} |"
        )
    md.append("")
    md.append(f"**Router picks the correct family on {s['router_chose_correctly_pct']:.1f}% of held-out datasets.**")
    md.append("")
    md.append("## Top features driving family choice")
    md.append("")
    fi = sorted(result["feature_importance"].items(), key=lambda kv: -kv[1])[:8]
    md.append("| Feature | Importance |")
    md.append("|---|---:|")
    for k, v in fi:
        md.append(f"| {k} | {v:.3f} |")
    md.append("")
    md.append("Frozen by `code/meta_router.py`. Hashes in `manifest.sha256.json`.")
    (out_dir / "router_summary.md").write_text("\n".join(md), encoding="utf-8")

    # Manifest
    manifest = {}
    for p in sorted(out_dir.glob("*")):
        if p.is_file() and p.name != "manifest.sha256.json":
            manifest[p.name] = _sha256(p)
    (out_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2),
                                                  encoding="utf-8")
    return out_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-utc", default=None,
                    help="benchmark run UTC (default = latest)")
    args = ap.parse_args(argv)

    run_utc = args.run_utc
    if not run_utc:
        latest = (RUNS_DIR / "latest.txt")
        if latest.exists():
            run_utc = latest.read_text(encoding="utf-8").strip()
        else:
            dirs = sorted([p.name for p in RUNS_DIR.iterdir() if p.is_dir()])
            run_utc = dirs[-1] if dirs else None
    if not run_utc:
        print("no benchmark run found")
        return 2
    print(f"[meta-router] using benchmark run {run_utc}")

    t0 = time.time()
    features, labels, fam_rmse = build_table(run_utc)
    print(f"[meta-router] built {len(features)} (features, label) rows "
          f"({len(features.columns)-1} features)")

    result = train_and_evaluate(features, labels, fam_rmse)
    s = result["summary"]
    print(f"[meta-router] router correct family pick: {s['router_chose_correctly_pct']:.1f}%")
    print(f"[meta-router] strategy win counts: {s['win_counts']}")
    print(f"[meta-router] median RMSE / oracle: {s['median_rel_rmse_vs_oracle']}")

    out_dir = write_outputs(run_utc, features, labels, result)
    print(f"[meta-router] wrote {out_dir} ({time.time()-t0:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
