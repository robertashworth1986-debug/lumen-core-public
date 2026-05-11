"""
regime_shift_scanner.py
==========================
Innovation #14 — detects sudden mean/variance regime breaks in every series of
the frozen 673-dataset universe.

Method (per dataset y):
    1. Standardize: y' = (y - rolling_mean(60)) / rolling_std(60)
    2. CUSUM statistic:
         S_t = max(0, S_{t-1} + (y'_t - delta))   (positive shift)
         T_t = max(0, T_{t-1} - (y'_t + delta))   (negative shift)
       with delta=0.5 (half a sigma drift threshold)
    3. Threshold h = 5 (≈99% specificity for unit-variance noise)
    4. A regime break is the first crossing of h, then S/T reset to 0
    5. Variance regime: rolling std ratio (last 30 / prior 30) > 1.75 or < 0.57

For each dataset we record:
    n_obs, n_mean_breaks_pos, n_mean_breaks_neg,
    last_break_t (or -1), last_break_dir, peak_cusum,
    n_var_regime_starts, var_ratio_last

Output:
    out/regime_shift_scanner/<utc>/
        regimes.csv            one row per dataset
        breakpoints.csv        one row per individual break
        summary.json
        regime_summary.md
        manifest.sha256.json

Joblib parallel; ~30s on 673 datasets.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))

V2_RUNS = ROOT / "out" / "master_universe_v2"
OUT_ROOT = ROOT / "out" / "regime_shift_scanner"

CUSUM_DELTA = 0.5    # half-sigma drift detector
CUSUM_H = 5.0        # decision threshold
WINDOW = 60          # rolling window for standardization
VAR_WIN = 30         # variance comparison window


def _resolve_run_utc() -> str:
    forced = os.environ.get("REGIME_UTC")
    if forced:
        return forced
    latest = V2_RUNS / "latest.txt"
    if latest.exists():
        return latest.read_text(encoding="utf-8").strip()
    runs = sorted([p.name for p in V2_RUNS.iterdir() if p.is_dir()])
    if not runs:
        raise SystemExit("no v2 runs found")
    return runs[-1]


def _scan_one(csv_path: Path) -> dict | None:
    try:
        df = pd.read_csv(csv_path)
        y = df["value"].to_numpy(dtype=float)
    except Exception:
        return None
    n = len(y)
    if n < WINDOW + 10:
        return None

    # 1. Rolling standardization
    s = pd.Series(y)
    mu = s.rolling(WINDOW, min_periods=WINDOW).mean()
    sigma = s.rolling(WINDOW, min_periods=WINDOW).std().replace(0, np.nan)
    z = ((s - mu) / sigma).to_numpy()
    z = np.where(np.isfinite(z), z, 0.0)

    # 2. CUSUM both directions
    S_pos = 0.0
    S_neg = 0.0
    peak_pos = 0.0
    peak_neg = 0.0
    breakpoints: list[dict] = []
    last_break_t = -1
    last_break_dir = None

    start = WINDOW  # before this z is undefined
    for t in range(start, n):
        zt = z[t]
        S_pos = max(0.0, S_pos + (zt - CUSUM_DELTA))
        S_neg = max(0.0, S_neg - (zt + CUSUM_DELTA))
        peak_pos = max(peak_pos, S_pos)
        peak_neg = max(peak_neg, S_neg)
        if S_pos > CUSUM_H:
            breakpoints.append({"t": t, "dir": "pos", "stat": float(S_pos)})
            last_break_t = t
            last_break_dir = "pos"
            S_pos = 0.0
        elif S_neg > CUSUM_H:
            breakpoints.append({"t": t, "dir": "neg", "stat": float(S_neg)})
            last_break_t = t
            last_break_dir = "neg"
            S_neg = 0.0

    # 3. Variance regime (last VAR_WIN vs prior VAR_WIN)
    var_ratio_last = None
    var_break = False
    if n >= 2 * VAR_WIN:
        last = y[-VAR_WIN:]
        prior = y[-2 * VAR_WIN:-VAR_WIN]
        sd_last = float(np.std(last) or 0.0)
        sd_prior = float(np.std(prior) or 0.0)
        if sd_prior > 0:
            var_ratio_last = round(sd_last / sd_prior, 3)
            var_break = (var_ratio_last > 1.75) or (var_ratio_last < 0.57)

    return {
        "row": {
            "dataset": csv_path.stem,
            "n_obs": int(n),
            "n_breaks_total": len(breakpoints),
            "n_breaks_pos": sum(1 for b in breakpoints if b["dir"] == "pos"),
            "n_breaks_neg": sum(1 for b in breakpoints if b["dir"] == "neg"),
            "last_break_t": int(last_break_t),
            "last_break_dir": last_break_dir or "",
            "peak_cusum_pos": round(peak_pos, 3),
            "peak_cusum_neg": round(peak_neg, 3),
            "var_ratio_last": var_ratio_last if var_ratio_last is not None else "",
            "var_regime_break": bool(var_break),
            "recent_break": bool(last_break_t >= n - 12),
        },
        "breaks": [
            {"dataset": csv_path.stem, **b} for b in breakpoints
        ],
    }


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    utc = _resolve_run_utc()
    raw_dir = V2_RUNS / utc / "raw"
    if not raw_dir.exists():
        raise SystemExit(f"raw dir missing: {raw_dir}")
    print(f"[regime] run={utc}")

    csvs = sorted(raw_dir.glob("*.csv"))
    print(f"[regime] {len(csvs)} datasets")

    t0 = time.time()
    results = Parallel(n_jobs=-1, backend="loky", verbose=0)(
        delayed(_scan_one)(p) for p in csvs)
    results = [r for r in results if r is not None]
    elapsed = time.time() - t0
    print(f"[regime] scanned {len(results)} datasets in {elapsed:.1f}s")

    rows = [r["row"] for r in results]
    breaks = [b for r in results for b in r["breaks"]]

    out_dir = OUT_ROOT / utc
    out_dir.mkdir(parents=True, exist_ok=True)

    df_rows = pd.DataFrame(rows)
    df_rows.to_csv(out_dir / "regimes.csv", index=False)

    df_breaks = pd.DataFrame(breaks)
    if df_breaks.empty:
        df_breaks = pd.DataFrame(columns=["dataset", "t", "dir", "stat"])
    df_breaks.to_csv(out_dir / "breakpoints.csv", index=False)

    n = len(df_rows)
    n_with_break = int((df_rows["n_breaks_total"] > 0).sum()) if n else 0
    n_recent = int(df_rows["recent_break"].sum()) if n else 0
    n_var = int(df_rows["var_regime_break"].sum()) if n else 0
    summary = {
        "run_utc": utc,
        "elapsed_s": round(elapsed, 1),
        "n_datasets": n,
        "n_with_any_mean_break": n_with_break,
        "frac_with_any_mean_break": round(n_with_break / n, 4) if n else 0.0,
        "n_with_recent_break_within_12": n_recent,
        "n_with_variance_regime_break": n_var,
        "total_mean_breaks": int(df_rows["n_breaks_total"].sum()) if n else 0,
        "params": {
            "cusum_delta": CUSUM_DELTA,
            "cusum_h": CUSUM_H,
            "window": WINDOW,
            "var_win": VAR_WIN,
            "var_ratio_thresholds": [0.57, 1.75],
        },
        "method": (
            "rolling-standardize 60 -> two-sided CUSUM (delta=0.5, h=5); "
            "variance regime = std(last 30) / std(prior 30) outside [0.57, 1.75]"
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = [
        "# Regime-shift scanner",
        f"- run: `{utc}`",
        f"- datasets: {n}",
        f"- with ≥1 mean-shift break: {n_with_break} ({summary['frac_with_any_mean_break']*100:.1f}%)",
        f"- with break in last 12 steps: {n_recent}",
        f"- with variance regime break: {n_var}",
        f"- total mean breaks across universe: {summary['total_mean_breaks']}",
        "",
        "Top 15 by peak CUSUM (positive direction):",
        "",
    ]
    if n:
        top_pos = df_rows.sort_values("peak_cusum_pos", ascending=False).head(15)
        md.append("| dataset | n_breaks | last_t | dir | peak+ | peak- |")
        md.append("|---|---:|---:|---|---:|---:|")
        for _, r in top_pos.iterrows():
            md.append(
                f"| `{r['dataset']}` | {r['n_breaks_total']} | "
                f"{r['last_break_t']} | {r['last_break_dir'] or '-'} | "
                f"{r['peak_cusum_pos']} | {r['peak_cusum_neg']} |")
    (out_dir / "regime_summary.md").write_text("\n".join(md), encoding="utf-8")

    # Manifest
    manifest = {
        "run_utc": utc,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "files": {},
    }
    for fname in ["regimes.csv", "breakpoints.csv", "summary.json", "regime_summary.md"]:
        fp = out_dir / fname
        manifest["files"][fname] = {
            "size_bytes": fp.stat().st_size,
            "sha256": _sha256(fp),
        }
    (out_dir / "manifest.sha256.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[regime] wrote {out_dir}")
    print(f"[regime] {n_with_break}/{n} datasets have mean-shift breaks; "
          f"{n_recent} recent; {n_var} variance regime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
