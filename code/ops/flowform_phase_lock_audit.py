from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def latest_run_dir(path: Path) -> str | None:
    if not path.exists() or not path.is_dir():
        return None
    runs = sorted([p.name for p in path.iterdir() if p.is_dir()])
    if not runs:
        return None
    return runs[-1]


def choose_champions_csv(stack_root: Path) -> Path:
    candidates = [
        stack_root / "out" / "institutional_flow_strategy_champions.csv",
        stack_root.parent / "clean_data" / "institutional_flow_strategy_champions.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def load_champion_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        for r in reader:
            row = dict(r)
            row["institutional_score_f"] = safe_float(r.get("institutional_score"))
            row["test_sharpe_f"] = safe_float(r.get("test_sharpe"))
            row["wf_sharpe_mean_f"] = safe_float(r.get("wf_sharpe_mean"))
            row["test_vs_baseline_f"] = safe_float(r.get("test_vs_baseline"))
            row["is_live_tradable_b"] = str(r.get("is_live_tradable", "")).strip().lower() in {"1", "true", "yes", "y"}
            signal = " ".join([
                str(r.get("flow", "")),
                str(r.get("strategy", "")),
                str(r.get("algo", "")),
            ]).lower()
            row["phase_lock_tag"] = bool(re.search(r"harmonic|helix|spiral|fibonacci|reson|phase|gaussian", signal))
            row["phase_lock_potential_score"] = (
                row["institutional_score_f"]
                + (2.0 * row["test_sharpe_f"])
                + (0.5 * row["wf_sharpe_mean_f"])
            )
            rows.append(row)
    return rows


def compact_rows(rows: list[dict[str, Any]], n: int = 10) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows[: max(0, n)]:
        out.append(
            {
                "flow": r.get("flow", ""),
                "strategy": r.get("strategy", ""),
                "algo": r.get("algo", ""),
                "institutional_score": round(safe_float(r.get("institutional_score_f")), 6),
                "test_sharpe": round(safe_float(r.get("test_sharpe_f")), 6),
                "wf_sharpe_mean": round(safe_float(r.get("wf_sharpe_mean_f")), 6),
                "test_vs_baseline": round(safe_float(r.get("test_vs_baseline_f")), 6),
                "is_live_tradable": bool(r.get("is_live_tradable_b", False)),
                "phase_lock_tag": bool(r.get("phase_lock_tag", False)),
                "source_file": r.get("file", ""),
            }
        )
    return out


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_md(path: Path, report: dict[str, Any]) -> None:
    s = report.get("summary", {})
    active = report.get("active_champion", {})
    lines: list[str] = []
    lines.append("# Flowform Phase-Lock Audit")
    lines.append("")
    lines.append(f"Generated UTC: {report.get('generated_utc', '')}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- champions_rows: {s.get('champions_rows', 0)}")
    lines.append(f"- live_tradable_rows: {s.get('live_tradable_rows', 0)}")
    lines.append(f"- phase_lock_tagged_rows: {s.get('phase_lock_tagged_rows', 0)}")
    lines.append(f"- active_champion_in_rankings: {s.get('active_champion_in_rankings', False)}")
    lines.append(f"- active_rank_institutional: {s.get('active_rank_institutional', 'not_found')}")
    lines.append(f"- active_rank_test_sharpe: {s.get('active_rank_test_sharpe', 'not_found')}")
    lines.append("")

    lines.append("## Active Champion")
    lines.append(f"- flow: {active.get('flow', '')}")
    lines.append(f"- strategy: {active.get('strategy', '')}")
    lines.append(f"- algo: {active.get('algo', '')}")
    lines.append(f"- sharpe: {active.get('sharpe', '')}")
    lines.append(f"- vs_baseline: {active.get('vs_baseline', '')}")
    lines.append("")

    lines.append("## Top Institutional Candidates")
    lines.append("| flow | strategy | algo | institutional_score | test_sharpe |")
    lines.append("|---|---|---|---:|---:|")
    for r in report.get("top_institutional_candidates", []):
        lines.append(
            f"| {r.get('flow','')} | {r.get('strategy','')} | {r.get('algo','')} | {r.get('institutional_score',0)} | {r.get('test_sharpe',0)} |"
        )
    if not report.get("top_institutional_candidates"):
        lines.append("| none | - | - | 0 | 0 |")
    lines.append("")

    lines.append("## Top Phase-Lock Candidates")
    lines.append("| flow | strategy | algo | institutional_score | test_sharpe |")
    lines.append("|---|---|---|---:|---:|")
    for r in report.get("top_phase_lock_candidates", []):
        lines.append(
            f"| {r.get('flow','')} | {r.get('strategy','')} | {r.get('algo','')} | {r.get('institutional_score',0)} | {r.get('test_sharpe',0)} |"
        )
    if not report.get("top_phase_lock_candidates"):
        lines.append("| none | - | - | 0 | 0 |")
    lines.append("")

    hs = report.get("hybrid_stacker", {})
    lines.append("## Hybrid Stacker")
    lines.append(f"- run_utc: {hs.get('run_utc', '')}")
    lines.append(f"- n_datasets: {hs.get('n_datasets', 0)}")
    lines.append(f"- router_win_rate_pct: {hs.get('router_win_rate_pct', 0.0):.2f}%")
    lines.append(f"- j_sarima_plus_harmonic_wins: {hs.get('j_sarima_plus_harmonic_wins', 0)}")
    lines.append(f"- k_linear_plus_harmonic_wins: {hs.get('k_linear_plus_harmonic_wins', 0)}")
    lines.append(f"- k_beats_v2_oracle: {hs.get('k_beats_v2_oracle', 0)}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit top flowforms and hybrid harmonic phase-lock coverage.")
    parser.add_argument("--stack-root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--top-n", type=int, default=10)
    args = parser.parse_args()

    stack_root = Path(args.stack_root).resolve()
    top_n = max(1, int(args.top_n))

    champions_csv = choose_champions_csv(stack_root)
    active_path = stack_root / "adaptive_champion.json"

    hybrid_base = stack_root / "out" / "hybrid_stacker"
    master_base = stack_root / "out" / "master_universe_v2"

    run_utc = latest_run_dir(hybrid_base) or latest_run_dir(master_base)

    hybrid_eval = load_json(hybrid_base / run_utc / "eval.json") if run_utc else {}
    master_summary = load_json(master_base / run_utc / "summary.json") if run_utc else {}
    active = load_json(active_path)

    rows = load_champion_rows(champions_csv)
    live_rows = [r for r in rows if r.get("is_live_tradable_b")]
    phase_rows = [r for r in live_rows if r.get("phase_lock_tag")]

    by_inst = sorted(live_rows, key=lambda r: r.get("institutional_score_f", 0.0), reverse=True)
    by_sharpe = sorted(live_rows, key=lambda r: r.get("test_sharpe_f", 0.0), reverse=True)
    by_phase = sorted(phase_rows, key=lambda r: r.get("phase_lock_potential_score", 0.0), reverse=True)

    active_flow = str(active.get("flow", "") or "").strip().lower()
    active_strategy = str(active.get("strategy", "") or "").strip().lower()

    active_matches = [
        r for r in live_rows
        if str(r.get("flow", "")).strip().lower() == active_flow
        and str(r.get("strategy", "")).strip().lower() == active_strategy
    ]

    active_institutional_rank = None
    active_sharpe_rank = None
    active_best_institutional = None

    if active_matches:
        active_best_institutional = max(active_matches, key=lambda r: r.get("institutional_score_f", 0.0))
        for idx, r in enumerate(by_inst, start=1):
            if r is active_best_institutional:
                active_institutional_rank = idx
                break
        for idx, r in enumerate(by_sharpe, start=1):
            if r is active_best_institutional:
                active_sharpe_rank = idx
                break

    better_phase_candidates: list[dict[str, Any]]
    if active_best_institutional is None:
        better_phase_candidates = by_phase[:top_n]
    else:
        threshold = active_best_institutional.get("institutional_score_f", 0.0)
        better_phase_candidates = [r for r in by_phase if r.get("institutional_score_f", 0.0) > threshold][:top_n]

    model_list = master_summary.get("models", []) if isinstance(master_summary.get("models", []), list) else []
    families = master_summary.get("families", {}) if isinstance(master_summary.get("families", {}), dict) else {}

    hs_summary = hybrid_eval.get("summary", {}) if isinstance(hybrid_eval.get("summary", {}), dict) else {}
    hs_wins = hs_summary.get("win_counts", {}) if isinstance(hs_summary.get("win_counts", {}), dict) else {}
    hs_rates = hs_summary.get("win_rates", {}) if isinstance(hs_summary.get("win_rates", {}), dict) else {}
    hs_beats = hs_summary.get("beats_v2_oracle", {}) if isinstance(hs_summary.get("beats_v2_oracle", {}), dict) else {}

    report = {
        "generated_utc": now_iso(),
        "scope": {
            "stack_root": str(stack_root),
            "run_utc": run_utc,
            "champions_csv": str(champions_csv),
            "active_champion": str(active_path),
        },
        "summary": {
            "champions_rows": len(rows),
            "live_tradable_rows": len(live_rows),
            "phase_lock_tagged_rows": len(phase_rows),
            "active_champion_in_rankings": bool(active_matches),
            "active_rank_institutional": active_institutional_rank,
            "active_rank_test_sharpe": active_sharpe_rank,
            "better_phase_lock_candidates_count": len(better_phase_candidates),
        },
        "active_champion": {
            "flow": active.get("flow"),
            "strategy": active.get("strategy"),
            "algo": active.get("algo"),
            "sharpe": active.get("sharpe"),
            "vs_baseline": active.get("vs_baseline"),
            "match_count": len(active_matches),
        },
        "top_institutional_candidates": compact_rows(by_inst, n=top_n),
        "top_test_sharpe_candidates": compact_rows(by_sharpe, n=top_n),
        "top_phase_lock_candidates": compact_rows(by_phase, n=top_n),
        "better_phase_lock_candidates_than_active": compact_rows(better_phase_candidates, n=top_n),
        "benchmark_harmonic_coverage": {
            "models_count": len(model_list),
            "has_harmonic_search": "d_harmonic_search" in model_list,
            "has_harmonic_fixed12": "c_harmonic_fixed12" in model_list,
            "families_count": len(families.keys()),
            "has_harmonic_family": "harmonic" in families,
            "harmonic_family_models": families.get("harmonic", []),
            "n_datasets_succeeded": master_summary.get("n_datasets_succeeded", 0),
            "harmonic_win_rate": master_summary.get("harmonic_win_rate", 0.0),
        },
        "hybrid_stacker": {
            "run_utc": hybrid_eval.get("run_utc", run_utc),
            "n_datasets": hs_summary.get("n_datasets", 0),
            "router_win_rate_pct": safe_float(hs_rates.get("router", 0.0)) * 100.0,
            "j_sarima_plus_harmonic_wins": int(hs_wins.get("j_sarima_plus_harmonic", 0) or 0),
            "k_linear_plus_harmonic_wins": int(hs_wins.get("k_linear_plus_harmonic", 0) or 0),
            "k_beats_v2_oracle": int(hs_beats.get("k_linear_plus_harmonic", 0) or 0),
        },
    }

    out_dir = stack_root / "out" / "ops"
    tag = now_tag()

    json_path = out_dir / f"flowform_phase_lock_audit_{tag}.json"
    md_path = out_dir / f"flowform_phase_lock_audit_{tag}.md"
    latest_json = out_dir / "flowform_phase_lock_audit_latest.json"
    latest_md = out_dir / "flowform_phase_lock_audit_latest.md"

    write_json(json_path, report)
    write_md(md_path, report)
    write_json(latest_json, report)
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")

    manifest = {
        "generated_utc": report.get("generated_utc"),
        "summary": report.get("summary"),
        "artifacts": {
            "json": str(json_path),
            "markdown": str(md_path),
            "latest_json": str(latest_json),
            "latest_markdown": str(latest_md),
        },
    }
    manifest_path = out_dir / f"flowform_phase_lock_audit_manifest_{tag}.json"
    write_json(manifest_path, manifest)

    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
