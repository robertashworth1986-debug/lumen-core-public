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

import json
import os
import shutil
import sys
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "dashboard"
EVID = DASH / "evidence"
V2_RUNS = ROOT / "out" / "master_universe_v2"
LEDGER = ROOT / "out" / "frozen_delta_ledger.jsonl"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append({str(k): str(v) if v is not None else "" for k, v in row.items()})
    return out


def _build_dataset_polish_audit(run: Path, utc: str, runs_root: Path) -> tuple[dict, list[dict]]:
    summary = _load_json(run / "summary.json")
    manifest = _load_json(run / "manifest.sha256.json")
    scoreboard_rows = _read_csv_rows(run / "family_scoreboard.csv")
    result_rows = _read_csv_rows(run / "results.csv")

    dataset_meta = summary.get("datasets", {}) if isinstance(summary.get("datasets", {}), dict) else {}
    manifest_files = manifest.get("files", {}) if isinstance(manifest.get("files", {}), dict) else {}

    succeeded = sorted({str(r.get("dataset", "")).strip() for r in scoreboard_rows if str(r.get("dataset", "")).strip()})
    result_by_dataset: dict[str, list[dict]] = {}
    for row in result_rows:
        ds = str(row.get("dataset", "")).strip()
        if not ds:
            continue
        result_by_dataset.setdefault(ds, []).append(row)

    audit_rows: list[dict] = []
    for ds in succeeded:
        meta = dataset_meta.get(ds, {}) if isinstance(dataset_meta.get(ds, {}), dict) else {}
        ds_results = result_by_dataset.get(ds, [])
        checks = {
            "metadata_present": bool(meta),
            "has_n_obs": int(meta.get("n_obs", 0) or 0) >= 30,
            "has_bounds": bool(str(meta.get("first", ""))) and bool(str(meta.get("last", ""))),
            "has_raw_sha": bool(str(meta.get("raw_sha256", ""))),
            "has_manifest_raw_entry": bool(
                manifest_files.get(f"raw/{ds}.csv") or manifest_files.get(f"raw\\{ds}.csv")
            ),
            "has_eval_rows": len(ds_results) > 0,
            "has_model_score": any(str(r.get("rmse", "")).strip() not in ("", "nan", "NaN") for r in ds_results),
            "has_winner": any(str(r.get("dataset", "")).strip() == ds and bool(str(r.get("winning_model", "")).strip()) for r in scoreboard_rows),
        }
        pass_count = sum(1 for ok in checks.values() if ok)
        total_checks = len(checks)
        polished = pass_count == total_checks
        tier = "polished" if polished else ("review" if pass_count >= total_checks - 2 else "incomplete")
        audit_rows.append(
            {
                "dataset": ds,
                "polish_tier": tier,
                "polish_score": round(pass_count / total_checks, 4),
                "checks_passed": pass_count,
                "checks_total": total_checks,
                "n_obs": int(meta.get("n_obs", 0) or 0),
                "raw_sha256": str(meta.get("raw_sha256", "")),
                "checks": checks,
            }
        )

    polished_count = sum(1 for r in audit_rows if r["polish_tier"] == "polished")
    audit_payload = {
        "generated_utc": utc,
        "scope": "dataset_polish_audit",
        "datasets_shipped": len(audit_rows),
        "polished_count": polished_count,
        "review_count": sum(1 for r in audit_rows if r["polish_tier"] == "review"),
        "incomplete_count": sum(1 for r in audit_rows if r["polish_tier"] == "incomplete"),
        "strict_polished_gate": True,
        "rows": audit_rows,
    }

    audit_json_path = runs_root / "dataset_polish_audit.json"
    audit_json_path.write_text(json.dumps(audit_payload, indent=2), encoding="utf-8")

    md_lines = [
        "# Dataset Polish Audit",
        "",
        f"Run UTC: {utc}",
        f"Datasets shipped: {len(audit_rows)}",
        f"Polished: {polished_count}",
        f"Review: {audit_payload['review_count']}",
        f"Incomplete: {audit_payload['incomplete_count']}",
        "",
        "A dataset is polished only if metadata, raw hash, manifest entry, score rows, and winner mapping are all present.",
        "",
        "| Dataset | Tier | Score | n_obs |",
        "|---|---|---:|---:|",
    ]
    for row in audit_rows:
        md_lines.append(
            f"| {row['dataset']} | {row['polish_tier']} | {row['polish_score']:.2f} | {row['n_obs']} |"
        )
    (runs_root / "dataset_polish_audit.md").write_text("\n".join(md_lines), encoding="utf-8")

    return audit_payload, audit_rows


def latest_run() -> Path:
    d = V2_RUNS
    runs = sorted([p for p in d.iterdir() if p.is_dir()])
    if not runs:
        raise SystemExit("no runs found in out/master_universe_v2/")
    # Prefer the most recent COMPLETE run (one with summary.json).
    for r in reversed(runs):
        if (r / "summary.json").exists():
            return r
    return runs[-1]


def _sync_root_dashboard_evidence(utc: str) -> None:
    """Mirror the published evidence bundle to the workspace-root dashboard."""
    mirror_evid = ROOT.parent / "dashboard" / "evidence"
    if mirror_evid.resolve(strict=False) == EVID.resolve(strict=False):
        return
    if not mirror_evid.parent.exists():
        print(f"[publish] root dashboard missing at {mirror_evid.parent} (skip mirror)")
        return

    src_run = EVID / "runs" / utc
    dst_run = mirror_evid / "runs" / utc
    dst_run.parent.mkdir(parents=True, exist_ok=True)
    if dst_run.exists():
        shutil.rmtree(dst_run)
    shutil.copytree(src_run, dst_run)

    mirror_evid.mkdir(parents=True, exist_ok=True)
    for name in ["index.html", "latest.txt", "ledger.jsonl"]:
        src = EVID / name
        if src.exists():
            shutil.copy2(src, mirror_evid / name)

    print(f"[publish] mirrored bundle -> {mirror_evid}")


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

    # Dataset-level polish gate for shipped benchmark artifacts.
    audit_payload, audit_rows = _build_dataset_polish_audit(run, utc, runs_root)
    require_polished = str(os.environ.get("PUBLISH_REQUIRE_POLISHED", "1")).strip().lower() not in (
        "0",
        "false",
        "no",
    )
    if require_polished:
        unpolished = [r for r in audit_rows if r.get("polish_tier") != "polished"]
        if unpolished:
            sample = ", ".join(r["dataset"] for r in unpolished[:8])
            raise SystemExit(
                f"[publish] blocked by polished-tier gate: {len(unpolished)} dataset(s) are not polished. Sample: {sample}"
            )
    print(
        f"[publish] dataset polish audit: {audit_payload['polished_count']}/{audit_payload['datasets_shipped']} polished"
    )

    # latest pointers
    (EVID / "latest.txt").write_text(utc, encoding="ascii")
    (V2_RUNS / "latest.txt").write_text(utc, encoding="ascii")

    # index.html = the master_evidence dashboard, but rewritten so it
    # looks up runs in ./runs/<utc>/ instead of ../out/master_universe_v2/.
    src_master = DASH / "master_evidence.html"
    if src_master.exists():
        src_html = src_master.read_text(encoding="utf-8")
        rewritten = src_html.replace(
            '"../out/master_universe_v2"', '"runs"'
        ).replace(
            'RUN_BASE + "/../frozen_delta_ledger.jsonl"',
            '"ledger.jsonl"',
        )
        (EVID / "index.html").write_text(rewritten, encoding="utf-8")
    else:
        # Fallback for stacks that already keep evidence/index.html in place.
        print(f"[publish] {src_master} missing; keeping existing evidence index.html")

    # ledger
    if LEDGER.exists():
        shutil.copy2(LEDGER, EVID / "ledger.jsonl")

    _sync_root_dashboard_evidence(utc)

    print(f"[publish] wrote bundle to {EVID}")
    print(f"[publish] view locally:")
    print(f"  http://127.0.0.1:8787/evidence/")
    print(f"[publish] deploy by syncing the dashboard/evidence/ tree to")
    print(f"  https://lumen-core.ai/evidence/  (Caddy / Oracle VPS)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
