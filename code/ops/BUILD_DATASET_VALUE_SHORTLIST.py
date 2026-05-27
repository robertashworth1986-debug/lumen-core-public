from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def find_latest_sweep_dir(ops_root: Path) -> Path:
    runs = [p for p in ops_root.glob("investor_proof_sweep_*") if p.is_dir()]
    if not runs:
        raise RuntimeError(f"No investor_proof_sweep_* directories found in {ops_root}")
    runs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return runs[0]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip("\r\n") + "\n", encoding="utf-8")


def quality_score(row: dict[str, Any]) -> float:
    sharpe_delta = max(to_float(row.get("sharpe_delta"), 0.0), 0.0)
    cagr_delta = max(to_float(row.get("cagr_delta"), 0.0), 0.0)
    edge_bps = max(to_float(row.get("edge_bps_per_bar"), 0.0), 0.0)
    strategy_win = min(max(to_float(row.get("strategy_win_rate"), 0.0), 0.0), 1.0)
    rows_count = max(to_int(row.get("rows"), 0), 0)
    span_years = max(to_float(row.get("span_years"), 0.0), 0.0)
    drawdown_delta = to_float(row.get("drawdown_delta"), 0.0)
    dd_improvement = max(-drawdown_delta, 0.0)

    sharpe_term = min(sharpe_delta / 8.0, 1.0)
    cagr_term = min(cagr_delta / 0.10, 1.0)
    edge_term = min(edge_bps / 2.5, 1.0)
    rows_term = min(rows_count / 2000.0, 1.0)
    span_term = min(span_years / 8.0, 1.0)
    dd_term = min(dd_improvement / 0.20, 1.0)

    score = (
        sharpe_term * 0.28
        + cagr_term * 0.26
        + edge_term * 0.18
        + rows_term * 0.10
        + span_term * 0.08
        + dd_term * 0.05
        + strategy_win * 0.05
    )
    return round(max(0.0, min(score, 1.0)), 6)


def estimate_dataset_value_usd(row: dict[str, Any], deploy_capital_usd: float) -> float:
    cagr_delta = max(to_float(row.get("cagr_delta"), 0.0), 0.0)
    edge_bps = max(to_float(row.get("edge_bps_per_bar"), 0.0), 0.0)

    # Annualized edge from per-bar basis points, using 252 bars/year as a conservative baseline.
    edge_rate_annual = (edge_bps / 10000.0) * 252.0
    edge_rate_annual = min(max(edge_rate_annual, 0.0), 0.50)
    cagr_value = deploy_capital_usd * cagr_delta
    edge_value = deploy_capital_usd * edge_rate_annual
    base_value = max(cagr_value, edge_value)

    score = quality_score(row)
    confidence_multiplier = 0.60 + (0.90 * score)
    return round(base_value * confidence_multiplier, 2)


def build_shortlist(rows: list[dict[str, Any]], deploy_capital_usd: float, min_value_usd: float) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for row in rows:
        est_value = estimate_dataset_value_usd(row, deploy_capital_usd)
        score = quality_score(row)
        ranked.append(
            {
                "series_name": str(row.get("series_name") or ""),
                "file_path": str(row.get("file_path") or ""),
                "column": str(row.get("column") or ""),
                "rows": to_int(row.get("rows"), 0),
                "span_years": round(to_float(row.get("span_years"), 0.0), 3),
                "sharpe_delta": round(to_float(row.get("sharpe_delta"), 0.0), 6),
                "cagr_delta": round(to_float(row.get("cagr_delta"), 0.0), 8),
                "edge_bps_per_bar": round(to_float(row.get("edge_bps_per_bar"), 0.0), 6),
                "strategy_win_rate": round(to_float(row.get("strategy_win_rate"), 0.0), 6),
                "drawdown_delta": round(to_float(row.get("drawdown_delta"), 0.0), 8),
                "quality_score": score,
                "estimated_dataset_value_usd": est_value,
                "worth_10k_plus": est_value >= 10000.0,
                "worth_threshold_met": est_value >= min_value_usd,
            }
        )

    ranked.sort(
        key=lambda r: (
            to_float(r.get("estimated_dataset_value_usd"), 0.0),
            to_float(r.get("quality_score"), 0.0),
            to_float(r.get("sharpe_delta"), 0.0),
        ),
        reverse=True,
    )
    return [r for r in ranked if to_float(r.get("estimated_dataset_value_usd"), 0.0) >= min_value_usd]


def markdown_report(summary: dict[str, Any], rows: list[dict[str, Any]], top_n: int) -> str:
    lines: list[str] = []
    lines.append("# Dataset Value Shortlist")
    lines.append("")
    lines.append(f"Generated UTC: {summary.get('generated_utc')}")
    lines.append(f"Source run: {summary.get('source_run_dir')}")
    lines.append(f"Deploy capital assumption USD: {summary.get('parameters', {}).get('deploy_capital_usd')}")
    lines.append(f"Minimum value threshold USD: {summary.get('parameters', {}).get('min_value_usd')}")
    lines.append("")
    lines.append("## Counts")
    lines.append(f"- Input backtested series: {summary.get('input_backtested_series', 0)}")
    lines.append(f"- Shortlisted series: {summary.get('shortlisted_series', 0)}")
    lines.append(f"- $10k+ series: {summary.get('worth_10k_plus_count', 0)}")
    lines.append("")
    lines.append("## Top Candidates")
    lines.append("| Rank | Series | Est Value USD | Quality | Sharpe Delta | CAGR Delta | Edge bps/bar |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|")
    for i, row in enumerate(rows[: max(1, top_n)], start=1):
        lines.append(
            "| "
            + str(i)
            + " | "
            + str(row.get("series_name") or "")[:90]
            + " | "
            + str(round(to_float(row.get("estimated_dataset_value_usd"), 0.0), 2))
            + " | "
            + str(round(to_float(row.get("quality_score"), 0.0), 4))
            + " | "
            + str(round(to_float(row.get("sharpe_delta"), 0.0), 4))
            + " | "
            + str(round(to_float(row.get("cagr_delta"), 0.0), 6))
            + " | "
            + str(round(to_float(row.get("edge_bps_per_bar"), 0.0), 4))
            + " |"
        )
    lines.append("")
    lines.append("## Evidence Paths")
    for k, v in (summary.get("evidence_paths") or {}).items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Build monetization shortlist for backtested datasets.")
    parser.add_argument("--root", default=str(root))
    parser.add_argument("--sweep-dir", default="", help="Optional explicit investor_proof_sweep run directory")
    parser.add_argument("--deploy-capital-usd", type=float, default=1_000_000.0)
    parser.add_argument("--min-value-usd", type=float, default=10_000.0)
    parser.add_argument("--top-n", type=int, default=25)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    workspace_root = root.parent
    ops_root = workspace_root / "out" / "ops"
    out_root = root / "out" / "ops" / "dataset_value_shortlist"
    out_root.mkdir(parents=True, exist_ok=True)

    sweep_dir = Path(args.sweep_dir).resolve() if str(args.sweep_dir).strip() else find_latest_sweep_dir(ops_root)
    walkforward_path = sweep_dir / "walkforward_results.csv"
    if not walkforward_path.exists():
        raise RuntimeError(f"Missing walkforward results CSV: {walkforward_path}")

    rows = read_csv_rows(walkforward_path)
    shortlist = build_shortlist(
        rows=rows,
        deploy_capital_usd=float(args.deploy_capital_usd),
        min_value_usd=float(args.min_value_usd),
    )

    tag = now_tag()
    run_json = out_root / f"dataset_value_shortlist_{tag}.json"
    run_csv = out_root / f"dataset_value_shortlist_{tag}.csv"
    run_md = out_root / f"dataset_value_shortlist_{tag}.md"

    latest_json = out_root / "dataset_value_shortlist_latest.json"
    latest_csv = out_root / "dataset_value_shortlist_latest.csv"
    latest_md = out_root / "dataset_value_shortlist_latest.md"

    summary = {
        "generated_utc": now_iso(),
        "scope": "dataset_value_shortlist",
        "source_run_dir": str(sweep_dir),
        "input_backtested_series": len(rows),
        "shortlisted_series": len(shortlist),
        "worth_10k_plus_count": len([r for r in shortlist if bool(r.get("worth_10k_plus"))]),
        "parameters": {
            "deploy_capital_usd": float(args.deploy_capital_usd),
            "min_value_usd": float(args.min_value_usd),
            "top_n": int(args.top_n),
        },
        "top_candidates": shortlist[: max(1, int(args.top_n))],
        "evidence_paths": {
            "source_walkforward_results_csv": rel(walkforward_path, workspace_root),
            "run_json": rel(run_json, workspace_root),
            "run_csv": rel(run_csv, workspace_root),
            "run_md": rel(run_md, workspace_root),
            "latest_json": rel(latest_json, workspace_root),
            "latest_csv": rel(latest_csv, workspace_root),
            "latest_md": rel(latest_md, workspace_root),
        },
    }

    fieldnames = [
        "series_name",
        "file_path",
        "column",
        "rows",
        "span_years",
        "sharpe_delta",
        "cagr_delta",
        "edge_bps_per_bar",
        "strategy_win_rate",
        "drawdown_delta",
        "quality_score",
        "estimated_dataset_value_usd",
        "worth_10k_plus",
        "worth_threshold_met",
    ]

    write_json(run_json, summary)
    write_csv(run_csv, shortlist, fieldnames)
    write_text(run_md, markdown_report(summary, shortlist, int(args.top_n)))

    write_json(latest_json, summary)
    write_csv(latest_csv, shortlist, fieldnames)
    write_text(latest_md, markdown_report(summary, shortlist, int(args.top_n)))

    print("BUILD_DATASET_VALUE_SHORTLIST")
    print(f"input_backtested_series={len(rows)}")
    print(f"shortlisted_series={len(shortlist)}")
    print(f"worth_10k_plus_count={summary['worth_10k_plus_count']}")
    print(f"json={latest_json}")
    print(f"csv={latest_csv}")
    print(f"md={latest_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
