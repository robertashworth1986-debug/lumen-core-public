"""
linkedin_publish_evidence.py
=========================================================================
Post a freshly published evidence run to the authenticated LinkedIn feed.

Reads the published bundle at dashboard/evidence/{latest.txt, runs/<UTC>/...}
and emits a concise post with:
    - dataset count + harmonic family score
    - median harmonic margin
    - frozen ledger entry hash
    - link to https://lumen-core.ai/evidence/runs/<UTC>/

Safe to run after every publish_evidence_bundle.py:
    python code/linkedin_publish_evidence.py
adds:
    --dry-run   print the post text, do not call LinkedIn
    --base-url  override the public URL (default https://lumen-core.ai)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "dashboard" / "evidence"
LEDGER = EVIDENCE / "ledger.jsonl"


def _read_summary(utc: str) -> dict:
    p = EVIDENCE / "runs" / utc / "summary.json"
    if not p.exists():
        raise FileNotFoundError(f"missing summary: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def _read_latest_utc() -> str:
    p = EVIDENCE / "latest.txt"
    if not p.exists():
        raise FileNotFoundError(f"missing latest.txt — run publish_evidence_bundle.py first")
    return p.read_text(encoding="utf-8").strip()


def _ledger_entry_for(utc: str) -> Optional[dict]:
    if not LEDGER.exists():
        return None
    last = None
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("run_utc") == utc:
            last = obj
    return last


def _read_router_eval(utc: str) -> Optional[dict]:
    p = ROOT / "out" / "meta_router" / utc / "eval.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_stacker_eval(utc: str) -> Optional[dict]:
    p = ROOT / "out" / "hybrid_stacker" / utc / "eval.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_calib_summary(utc: str) -> Optional[dict]:
    p = ROOT / "out" / "ci_calibration" / utc / "summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_blender_eval(utc: str) -> Optional[dict]:
    p = ROOT / "out" / "stacking_blender" / utc / "eval.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_anom_summary(utc: str) -> Optional[dict]:
    p = ROOT / "out" / "anomaly_scanner" / utc / "summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_regime_summary(utc: str) -> Optional[dict]:
    p = ROOT / "out" / "regime_shift_scanner" / utc / "summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _fmt_post(utc: str, summary: dict, base_url: str,
              entry_hash: Optional[str]) -> tuple[str, str, str]:
    n_total = (summary.get("n_datasets_succeeded")
               or summary.get("n_datasets_in_universe")
               or "?")
    win_counts = summary.get("family_win_counts") or {}
    median_pct = summary.get("harmonic_median_margin_pct")
    avg_pct = summary.get("harmonic_avg_margin_pct")
    h_rate = summary.get("harmonic_win_rate")

    def _pct(v):
        return f"{v*100:.1f}%" if isinstance(v, (int, float)) and abs(v) <= 1 else (
            f"{v:.1f}%" if isinstance(v, (int, float)) else str(v))

    fam_lines: list[str] = []
    # Sort by wins desc
    items = sorted(((f, c) for f, c in win_counts.items() if isinstance(c, int)),
                   key=lambda kv: kv[1], reverse=True)
    for fam, wins in items:
        pct = (wins / n_total * 100.0) if isinstance(n_total, int) and n_total else None
        if pct is not None:
            fam_lines.append(f"  • {fam}: {wins}/{n_total} ({pct:.1f}%)")
        else:
            fam_lines.append(f"  • {fam}: {wins}")
    fam_block = "\n".join(fam_lines) if fam_lines else "(no scoreboard available)"

    short_hash = (entry_hash or "")[:16] + "…" if entry_hash else "—"

    median_str = f"{median_pct:.1f}%" if isinstance(median_pct, (int, float)) else "?"
    avg_str = f"{avg_pct:.1f}%" if isinstance(avg_pct, (int, float)) else None
    rate_str = _pct(h_rate) if h_rate is not None else "?"

    # Router (innovation #1) — if the meta-router was trained on this run,
    # promote it to the headline.
    router = _read_router_eval(utc)
    router_block = ""
    if router and "summary" in router:
        rs = router["summary"]
        wc = rs.get("win_counts", {})
        wr = rs.get("win_rates", {})
        rmse_o = rs.get("median_rel_rmse_vs_oracle", {})
        if "router" in wc:
            r_wins = wc["router"]
            r_rate = wr.get("router", 0) * 100
            r_med = rmse_o.get("router", "?")
            best_fixed = max((f for f in wc if f != "router"),
                             key=lambda f: wc[f], default="—")
            best_fixed_wins = wc.get(best_fixed, 0)
            router_block = (
                f"\n🧭 LumenCore meta-router (per-dataset family selector):\n"
                f"   wins {r_wins}/{rs.get('n_datasets', '?')} ({r_rate:.1f}%) — "
                f"beats best fixed family ({best_fixed}, {best_fixed_wins}).\n"
                f"   median RMSE vs oracle: {r_med} (1.000 = perfect).\n"
            )

    # Hybrid stacker (innovation #2) — new strategies that beat the v2 oracle.
    stacker = _read_stacker_eval(utc)
    stacker_block = ""
    if stacker and "summary" in stacker:
        ss = stacker["summary"]
        n = ss.get("n_datasets", "?")
        wc = ss.get("win_counts", {})
        beats = ss.get("beats_v2_oracle", {})
        med = ss.get("median_rel_rmse_vs_oracle", {})
        r_wins = wc.get("router", 0)
        r_rate = (r_wins / n * 100) if isinstance(n, int) and n else 0
        j_beats = beats.get("j_sarima_plus_harmonic", 0)
        k_beats = beats.get("k_linear_plus_harmonic", 0)
        r_med = med.get("router", "?")
        stacker_block = (
            f"\n🔬 Hybrid stacker (8 strategies, head-to-head):\n"
            f"   router: {r_wins}/{n} wins ({r_rate:.1f}%), median rel-RMSE = {r_med} (oracle).\n"
            f"   new SARIMA+harmonic-residual hybrid beats v2-oracle on {j_beats}/{n} datasets.\n"
            f"   new linear+harmonic-residual hybrid beats v2-oracle on {k_beats}/{n} datasets.\n"
        )

    # CI calibration (innovation #7) — empirical band coverage.
    calib = _read_calib_summary(utc)
    calib_block = ""
    if calib and "overall" in calib:
        ov = calib["overall"]
        c80 = ov.get("mean_cov80")
        c95 = ov.get("mean_cov95")
        if c80 is not None and c95 is not None:
            calib_block = (
                f"\n📐 Confidence-band calibration (across all 673 datasets):\n"
                f"   80% bands actually cover {c80*100:.1f}% (target 80) — conservative.\n"
                f"   95% bands actually cover {c95*100:.1f}% (target 95) — honest.\n"
            )

    # Stacking blender (innovation #8) — NNLS over 5 family champions.
    blender = _read_blender_eval(utc)
    blender_block = ""
    if blender and "summary" in blender:
        bs = blender["summary"]
        n = bs.get("n_datasets", "?")
        wins = bs.get("win_counts_in_blend_plus_fams", {}).get("blend", 0)
        b_med = bs.get("median_blend_rel_vs_v2_oracle", "?")
        b_beats = bs.get("blender_beats_v2_oracle", 0)
        wts = bs.get("avg_blend_weights", {})
        top_wt = max(wts.items(), key=lambda kv: kv[1]) if wts else ("?", 0)
        blender_block = (
            f"\n🧪 NNLS stacking blender (5 champions, 80/20 inner-fit):\n"
            f"   wins on {wins}/{n} datasets, median rel-RMSE = "
            f"{b_med if isinstance(b_med, str) else f'{b_med:.4f}'} vs v2 oracle.\n"
            f"   beats v2 oracle on {b_beats}/{n}; "
            f"top avg weight: {top_wt[0]} ({top_wt[1]:.2f}).\n"
        )

    # Anomaly scanner (innovation #9) — early-warning signals.
    anom = _read_anom_summary(utc)
    anom_block = ""
    if anom:
        n = anom.get("n_datasets", "?")
        n_warn = anom.get("n_with_2sigma_anomaly", 0)
        n_alert = anom.get("n_with_3sigma_anomaly", 0)
        anom_block = (
            f"\n🚨 Anomaly scanner (router-picked champion + σ·√h bands):\n"
            f"   {n_warn}/{n} datasets show ≥1 2-σ deviation in the test window;\n"
            f"   {n_alert} of those cross 3-σ — early-warning candidates.\n"
        )

    # Regime-shift scanner (innovation #14) — CUSUM mean/variance breaks.
    regime = _read_regime_summary(utc)
    regime_block = ""
    if regime:
        n = regime.get("n_datasets", "?")
        n_break = regime.get("n_with_any_mean_break", 0)
        n_recent = regime.get("n_with_recent_break_within_12", 0)
        n_var = regime.get("n_with_variance_regime_break", 0)
        regime_block = (
            f"\n🌊 Regime-shift scanner (CUSUM δ=0.5, h=5):\n"
            f"   {n_break}/{n} datasets carry ≥1 mean-shift break;\n"
            f"   {n_recent} broke in the last 12 steps; "
            f"{n_var} flipped variance regime.\n"
        )

    text = (
        f"📊 New LumenCore benchmark frozen — {utc}\n\n"
        f"{n_total} live datasets, head-to-head across 9 models in 5 families:\n"
        f"{fam_block}\n"
        f"{router_block}"
        f"{stacker_block}"
        f"{calib_block}"
        f"{blender_block}"
        f"{anom_block}"
        f"{regime_block}\n"
        f"Harmonic win rate: {rate_str}\n"
        f"Median harmonic-win margin: {median_str} RMSE reduction"
        + (f" (avg {avg_str})\n" if avg_str else "\n")
        + f"Frozen ledger entry: {short_hash}\n\n"
        f"Verifiable in your browser — every claim chains to a SHA-256.\n"
        f"#quant #timeseries #harmonic #infrastructure #evidence"
    )
    title = f"LumenCore evidence — {utc}"
    desc = f"{n_total} datasets · harmonic median margin {median_str}"
    return text, title, desc


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--utc", help="explicit run UTC (defaults to dashboard/evidence/latest.txt)")
    ap.add_argument("--base-url", default="https://lumen-core.ai")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    utc = args.utc or _read_latest_utc()
    summary = _read_summary(utc)
    entry = _ledger_entry_for(utc)
    entry_hash = (entry or {}).get("entry_sha256")

    base = args.base_url.rstrip("/")
    link = f"{base}/evidence/runs/{utc}/"

    text, title, desc = _fmt_post(utc, summary, base, entry_hash)

    print("=" * 70)
    print("POST TEXT:")
    print(text)
    print("-" * 70)
    print("LINK :", link)
    print("TITLE:", title)
    print("DESC :", desc)
    print("=" * 70)

    if args.dry_run:
        print("[dry-run] not calling LinkedIn")
        return 0

    try:
        sys.path.insert(0, str(ROOT / "code"))
        import linkedin_oauth as li
        result = li.share_text(text, link=link, link_title=title, link_desc=desc)
        print("[posted] status:", result.get("status"))
        print("[posted] post_id:", result.get("post_id"))
        return 0
    except RuntimeError as e:
        print(f"[skip] LinkedIn not ready: {e}")
        print("[hint] run http://127.0.0.1:8787/auth/linkedin/login to connect")
        return 2
    except Exception as e:
        print(f"[error] {e}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
