"""
publish_evidence_bundle.py
==========================
Bundles a master_universe_v2 run into dashboard/evidence/ as a self-contained
deployable directory:

    dashboard/evidence/
        index.html             (the master_evidence.html dashboard)
        latest.txt             pointer to the latest run dir name
        runs/<UTC>/
            summary.json
            family_scoreboard.csv
            results.csv
            results_pivot.csv
            ci_pivot.csv
            UNDENIABLE_SCORECARD_V2.md
            manifest.sha256.json
            figs/*.png
            chart_manifest.sha256.json
        ledger.jsonl           copy of frozen_delta_ledger.jsonl

Once published, point a static web server (Caddy on lumen-core.ai or the
existing FastAPI dev gateway) at dashboard/ and the dashboard at
/evidence/ becomes immediately live.

Usage:
    python code/publish_evidence_bundle.py [RUN_DIR]
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "dashboard"
EVID = DASH / "evidence"
LEDGER = ROOT / "out" / "frozen_delta_ledger.jsonl"


def latest_run() -> Path:
    d = ROOT / "out" / "master_universe_v2"
    runs = sorted([p for p in d.iterdir() if p.is_dir()])
    if not runs:
        raise SystemExit("no runs found in out/master_universe_v2/")
    # Prefer the most recent COMPLETE run (one with summary.json).
    for r in reversed(runs):
        if (r / "summary.json").exists():
            return r
    return runs[-1]


def main() -> int:
    run = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else latest_run()
    utc = run.name
    print(f"[publish] source run: {run}")

    runs_root = EVID / "runs" / utc
    runs_root.mkdir(parents=True, exist_ok=True)

    # Copy small artifacts
    for name in [
        "summary.json", "family_scoreboard.csv", "results.csv",
        "results_pivot.csv", "ci_pivot.csv",
        "UNDENIABLE_SCORECARD_V2.md", "manifest.sha256.json",
    ]:
        src = run / name
        if src.exists():
            shutil.copy2(src, runs_root / name)

    # Copy figures
    figs_src = run / "figs"
    figs_dst = runs_root / "figs"
    if figs_src.exists():
        figs_dst.mkdir(exist_ok=True)
        for f in figs_src.iterdir():
            if f.is_file():
                shutil.copy2(f, figs_dst / f.name)

    # ---- Innovation packs (router / stacker / blender / calibration / anomaly) ----
    pack_specs = [
        ("router",     "meta_router",       ["eval.json", "router_summary.md",
                                              "manifest.sha256.json", "features.csv",
                                              "labels.csv"]),
        ("stacker",    "hybrid_stacker",    ["eval.json", "stacker_summary.md",
                                              "scoreboard.csv", "results.csv",
                                              "manifest.sha256.json"]),
        ("blender",    "stacking_blender",  ["eval.json", "blender_summary.md",
                                              "results.csv", "manifest.sha256.json"]),
        ("calibration","ci_calibration",    ["summary.json", "calibration_summary.md",
                                              "coverage.csv", "manifest.sha256.json"]),
        ("anomalies",  "anomaly_scanner",   ["summary.json", "anomaly_summary.md",
                                              "ranked.csv", "anomalies.csv",
                                              "manifest.sha256.json"]),
        ("regime",     "regime_shift_scanner", ["summary.json", "regime_summary.md",
                                                 "regimes.csv", "breakpoints.csv",
                                                 "manifest.sha256.json"]),
    ]
    for label, src_root, files in pack_specs:
        src_dir = ROOT / "out" / src_root / utc
        if not src_dir.exists():
            # fall back to most recent pack of this type
            base = ROOT / "out" / src_root
            if base.exists():
                cands = sorted(p for p in base.iterdir() if p.is_dir())
                if cands:
                    src_dir = cands[-1]
                    print(f"[publish] {label}: no pack at exact UTC, using {src_dir.name}")
                else:
                    print(f"[publish] (skip) no {label} pack under {base}")
                    continue
            else:
                print(f"[publish] (skip) no {label} pack at {base}")
                continue
        dst = runs_root / label
        dst.mkdir(exist_ok=True)
        for fname in files:
            sp = src_dir / fname
            if sp.exists():
                shutil.copy2(sp, dst / fname)
        print(f"[publish] {label} pack copied -> {dst}")

    # latest pointer
    (EVID / "latest.txt").write_text(utc, encoding="ascii")

    # index.html = the master_evidence dashboard, but rewritten so it
    # looks up runs in ./runs/<utc>/ instead of ../out/master_universe_v2/.
    src_html = (DASH / "master_evidence.html").read_text(encoding="utf-8")
    rewritten = src_html.replace(
        '"../out/master_universe_v2"', '"runs"'
    ).replace(
        'RUN_BASE + "/../frozen_delta_ledger.jsonl"',
        '"ledger.jsonl"',
    )
    (EVID / "index.html").write_text(rewritten, encoding="utf-8")

    # ledger
    if LEDGER.exists():
        shutil.copy2(LEDGER, EVID / "ledger.jsonl")

    print(f"[publish] wrote bundle to {EVID}")
    print(f"[publish] view locally:")
    print(f"  http://127.0.0.1:8787/evidence/")
    print(f"[publish] deploy by syncing the dashboard/evidence/ tree to")
    print(f"  https://lumen-core.ai/evidence/  (Caddy / Oracle VPS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
