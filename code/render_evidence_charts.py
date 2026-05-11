"""
render_evidence_charts.py
=========================
Generates matplotlib figures from a master_universe(_v2) run directory.

Outputs PNGs (1600px wide, 150 dpi) to <RUN_DIR>/figs/:
    01_family_wins_bar.png    -- family scoreboard headline bar
    02_per_dataset_rmse.png   -- top-N datasets, all model RMSE w/ 95% CI
    03_margin_histogram.png   -- distribution of margin% by winning family
    04_periodicity_vs_margin.png -- FFT top-peak height vs harmonic margin
    05_family_grid.png        -- per-family small-multiples win counts

Usage:
    python code/render_evidence_charts.py [RUN_DIR]
If no arg, picks the latest under out/master_universe_v2/ then v1.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
})

FAMILY_COLORS = {
    "harmonic":  "#7c3aed",   # violet
    "neural":    "#0ea5e9",   # sky blue
    "tree":      "#22c55e",   # green
    "classical": "#f59e0b",   # amber
    "baseline":  "#94a3b8",   # slate
}


def latest_run() -> Path:
    for sub in ("master_universe_v2", "master_universe"):
        d = ROOT / "out" / sub
        if d.exists():
            runs = sorted([p for p in d.iterdir() if p.is_dir()])
            if runs:
                return runs[-1]
    raise SystemExit("no run directories found")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def fig1_family_wins(fam_df: pd.DataFrame, out: Path) -> Path:
    counts = fam_df["winning_family"].value_counts()
    total = int(counts.sum())
    fams = list(counts.index)
    vals = [int(counts[f]) for f in fams]
    colors = [FAMILY_COLORS.get(f, "#64748b") for f in fams]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(fams, vals, color=colors, edgecolor="white", linewidth=2)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + total * 0.005,
                f"{v}\n({v/total*100:.1f}%)", ha="center", va="bottom",
                fontsize=11, fontweight="bold")
    ax.set_title(f"Family Win Counts — {total} live datasets, head-to-head")
    ax.set_ylabel("Datasets won")
    ax.set_ylim(0, max(vals) * 1.18)
    ax.grid(axis="y", alpha=0.25)
    p = out / "01_family_wins_bar.png"
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    return p


def fig2_per_dataset_rmse(res: pd.DataFrame, fam_df: pd.DataFrame, out: Path,
                          top_n: int = 30) -> Path:
    """Show top_n datasets ranked by harmonic margin, each with its 5-family
    best RMSE, normalized to the dataset's runner-up so relative wins compare."""
    if fam_df.empty:
        return out / "02_per_dataset_rmse.png"
    df = fam_df.dropna(subset=["margin_pct_vs_runner"]).copy()
    df = df.sort_values("margin_pct_vs_runner", ascending=False).head(top_n)
    fams = ["harmonic", "neural", "tree", "classical", "baseline"]

    fig, ax = plt.subplots(figsize=(11, max(6, top_n * 0.28)))
    y = np.arange(len(df))
    bar_h = 0.16
    for i, fam in enumerate(fams):
        col = f"{fam}_best"
        if col not in df.columns:
            continue
        vals = df[col].to_numpy(dtype=float)
        norm = df["winning_rmse"].to_numpy(dtype=float)
        rel = vals / np.where(norm == 0, np.nan, norm)
        ax.barh(y + (i - 2) * bar_h, rel, height=bar_h,
                color=FAMILY_COLORS[fam], label=fam, alpha=0.9,
                edgecolor="white", linewidth=0.5)
    ax.axvline(1.0, color="#111", linestyle="--", linewidth=1, alpha=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels(df["dataset"].tolist(), fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Relative RMSE (1.0 = winner; lower = better)")
    ax.set_title(f"Top {top_n} datasets by margin — all family bests")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(axis="x", alpha=0.25)
    p = out / "02_per_dataset_rmse.png"
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    return p


def fig3_margin_hist(fam_df: pd.DataFrame, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5.5))
    if not fam_df.empty:
        for fam, g in fam_df.dropna(subset=["margin_pct_vs_runner"]).groupby("winning_family"):
            ax.hist(g["margin_pct_vs_runner"], bins=20,
                    color=FAMILY_COLORS.get(fam, "#64748b"),
                    alpha=0.6, label=f"{fam} (n={len(g)})", edgecolor="white")
    ax.set_xlabel("RMSE reduction vs runner-up family (%)")
    ax.set_ylabel("Datasets")
    ax.set_title("Margin distribution — by winning family")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    p = out / "03_margin_histogram.png"
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    return p


def fig4_periodicity_vs_margin(fam_df: pd.DataFrame, raw_dir: Path,
                               out: Path) -> Path:
    pts_x, pts_y, pts_c, pts_lbl = [], [], [], []
    for _, r in fam_df.iterrows():
        ds = r["dataset"]
        f_csv = raw_dir / f"{ds}.csv"
        if not f_csv.exists():
            continue
        try:
            y = pd.read_csv(f_csv)["value"].dropna().to_numpy(float)
        except Exception:
            continue
        if len(y) < 30:
            continue
        yz = y - y.mean()
        if np.std(yz) == 0:
            continue
        fft = np.abs(np.fft.rfft(yz)) ** 2
        # exclude DC + lowest 1/n bin; take ratio of peak to mean -> peakiness
        if len(fft) <= 2:
            continue
        peakiness = float(fft[2:].max() / max(fft[2:].mean(), 1e-9))
        m = r["margin_pct_vs_runner"]
        if pd.isna(m):
            continue
        pts_x.append(peakiness)
        pts_y.append(m)
        pts_c.append(FAMILY_COLORS.get(r["winning_family"], "#64748b"))
        pts_lbl.append(r["winning_family"])

    fig, ax = plt.subplots(figsize=(10, 6))
    if pts_x:
        ax.scatter(pts_x, pts_y, c=pts_c, alpha=0.7, s=40,
                   edgecolor="white", linewidth=0.5)
        ax.set_xscale("log")
    ax.set_xlabel("Spectral peakiness (max/mean of FFT power, log scale)")
    ax.set_ylabel("Winner margin vs runner-up (%)")
    ax.set_title("Routing thesis: more periodic → harmonic margin grows")
    seen = set()
    handles = []
    for f, c in FAMILY_COLORS.items():
        if f in pts_lbl and f not in seen:
            handles.append(plt.Line2D([0], [0], marker="o", linestyle="",
                                      color=c, label=f, markersize=8))
            seen.add(f)
    if handles:
        ax.legend(handles=handles, loc="best")
    ax.grid(alpha=0.25)
    p = out / "04_periodicity_vs_margin.png"
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    return p


def fig5_family_grid(res: pd.DataFrame, fam_df: pd.DataFrame, out: Path) -> Path:
    fams = ["harmonic", "neural", "tree", "classical", "baseline"]
    fig, axes = plt.subplots(1, len(fams), figsize=(15, 4.5), sharey=True)
    total = len(fam_df)
    for ax, fam in zip(axes, fams):
        win = int((fam_df["winning_family"] == fam).sum()) if total else 0
        loss = total - win
        ax.bar(["wins", "losses"], [win, loss],
               color=[FAMILY_COLORS.get(fam, "#64748b"), "#e2e8f0"],
               edgecolor="white", linewidth=2)
        for j, v in enumerate([win, loss]):
            ax.text(j, v + total * 0.005, str(v),
                    ha="center", va="bottom", fontweight="bold")
        ax.set_title(f"{fam}\n{win}/{total} ({(win/total*100 if total else 0):.0f}%)")
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Per-family head-to-head record", fontsize=14, fontweight="bold")
    p = out / "05_family_grid.png"
    fig.tight_layout(); fig.savefig(p); plt.close(fig)
    return p


def main():
    run_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else latest_run()
    print(f"[chart] run_dir: {run_dir}")
    fam_path = run_dir / "family_scoreboard.csv"
    res_path = run_dir / "results.csv"
    if not fam_path.exists() or not res_path.exists():
        raise SystemExit(f"missing results in {run_dir}")
    fam_df = pd.read_csv(fam_path)
    res = pd.read_csv(res_path)
    raw_dir = run_dir / "raw"
    figs_dir = run_dir / "figs"; figs_dir.mkdir(exist_ok=True)

    out_files = []
    out_files.append(fig1_family_wins(fam_df, figs_dir))
    out_files.append(fig2_per_dataset_rmse(res, fam_df, figs_dir))
    out_files.append(fig3_margin_hist(fam_df, figs_dir))
    out_files.append(fig4_periodicity_vs_margin(fam_df, raw_dir, figs_dir))
    out_files.append(fig5_family_grid(res, fam_df, figs_dir))

    # Hash chart manifest
    chart_manifest = {"run_utc": run_dir.name, "figures": {}}
    for p in out_files:
        chart_manifest["figures"][p.name] = sha256_file(p)
    cm_path = figs_dir / "chart_manifest.sha256.json"
    cm_path.write_text(json.dumps(chart_manifest, indent=2))
    print(f"[chart] wrote {len(out_files)} figures + manifest")
    for p in out_files:
        print(f"  {p.name}  {sha256_file(p)[:12]}...")
    print(f"[chart] manifest: {cm_path}")


if __name__ == "__main__":
    main()
