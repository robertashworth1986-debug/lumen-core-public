from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out"
EXEC = OUT / "execution"

LEADERBOARD_CANDIDATES = [
    OUT / "full_beast_leaderboard.csv",
    ROOT / "full_beast_leaderboard.csv",
]

CHAMPION_CANDIDATES = [
    OUT / "adaptive_champion.json",
    ROOT / "adaptive_champion.json",
]

SUMMARY_CANDIDATES = [
    OUT / "full_beast_summary.json",
    ROOT / "full_beast_summary.json",
]

OUT_EDGE_REPORT = EXEC / "edge_truth_report.json"
OUT_EDGE_SNAPSHOT = OUT / "edge_truth_report.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def find_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def quality_score(
    *,
    top_sharpe: float,
    top_vs_baseline: float,
    positive_vs_baseline_ratio: float,
    robust_top_ratio: float,
    median_test_sharpe: float,
    train_test_gap_abs: float,
) -> tuple[float, list[str], list[str]]:
    score = 50.0
    wins: list[str] = []
    risks: list[str] = []

    if top_vs_baseline > 0:
        score += 18.0
        wins.append("Champion outperforms baseline on test window.")
    else:
        score -= 22.0
        risks.append("Champion underperforms baseline on test window.")

    if 0.5 <= top_sharpe <= 5.0:
        score += 12.0
        wins.append("Champion Sharpe is within a plausible institutional range.")
    elif top_sharpe > 8.0:
        score -= 26.0
        risks.append("Champion Sharpe is extreme (>8), likely unstable or overfit until proven otherwise.")
    elif top_sharpe < 0.0:
        score -= 18.0
        risks.append("Champion Sharpe is negative.")

    if positive_vs_baseline_ratio >= 0.55:
        score += 12.0
        wins.append("Majority of candidates beat baseline.")
    elif positive_vs_baseline_ratio < 0.40:
        score -= 10.0
        risks.append("Most candidates fail to beat baseline.")

    if robust_top_ratio >= 0.60:
        score += 8.0
        wins.append("Top-ranked cohort has broad baseline outperformance.")
    elif robust_top_ratio < 0.35:
        score -= 8.0
        risks.append("Top-ranked cohort lacks broad robustness.")

    if median_test_sharpe >= 0.8:
        score += 8.0
        wins.append("Median candidate Sharpe is healthy.")
    elif median_test_sharpe < 0.2:
        score -= 8.0
        risks.append("Median candidate Sharpe is weak.")

    if train_test_gap_abs > 2.0:
        score -= 8.0
        risks.append("Large train/test Sharpe gap suggests instability.")

    score = max(0.0, min(100.0, score))
    return round(score, 2), wins, risks


def verdict_for(score: float, hard_fail: bool) -> str:
    if hard_fail:
        return "FAIL"
    if score >= 70.0:
        return "PASS"
    if score >= 45.0:
        return "WATCH"
    return "FAIL"


def main() -> int:
    EXEC.mkdir(parents=True, exist_ok=True)

    leaderboard_path = find_existing(LEADERBOARD_CANDIDATES)
    champion_path = find_existing(CHAMPION_CANDIDATES)
    summary_path = find_existing(SUMMARY_CANDIDATES)

    if leaderboard_path is None:
        report = {
            "generated_utc": now_utc(),
            "verdict": "FAIL",
            "edge_quality_score": 0.0,
            "hard_fail": True,
            "hard_fail_reasons": ["full_beast_leaderboard.csv missing"],
            "wins": [],
            "risks": ["Unable to evaluate edge quality without leaderboard."],
            "sources": {
                "leaderboard_csv": None,
                "adaptive_champion_json": str(champion_path) if champion_path else None,
                "full_beast_summary_json": str(summary_path) if summary_path else None,
            },
        }
        OUT_EDGE_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        OUT_EDGE_SNAPSHOT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("EDGE TRUTH GUARD: FAIL (missing leaderboard)")
        return 1

    df = pd.read_csv(leaderboard_path)
    if df.empty:
        report = {
            "generated_utc": now_utc(),
            "verdict": "FAIL",
            "edge_quality_score": 0.0,
            "hard_fail": True,
            "hard_fail_reasons": ["leaderboard exists but is empty"],
            "wins": [],
            "risks": ["Unable to evaluate edge quality with zero candidates."],
            "sources": {
                "leaderboard_csv": str(leaderboard_path),
                "adaptive_champion_json": str(champion_path) if champion_path else None,
                "full_beast_summary_json": str(summary_path) if summary_path else None,
            },
        }
        OUT_EDGE_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        OUT_EDGE_SNAPSHOT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("EDGE TRUTH GUARD: FAIL (empty leaderboard)")
        return 1

    champion = load_json(champion_path, {}) if champion_path else {}
    summary = load_json(summary_path, {}) if summary_path else {}

    top_row = df.iloc[0].to_dict()

    top_test_sharpe = as_float(
        top_row.get("test_sharpe", summary.get("top_test_sharpe", champion.get("sharpe", 0.0))),
        0.0,
    )
    top_test_vs_baseline = as_float(
        top_row.get("test_vs_baseline", summary.get("top_test_vs_baseline", champion.get("vs_baseline", 0.0))),
        0.0,
    )

    pos_vs_series = pd.to_numeric(df.get("test_vs_baseline", pd.Series(dtype=float)), errors="coerce").dropna()
    sharpe_series = pd.to_numeric(df.get("test_sharpe", pd.Series(dtype=float)), errors="coerce").dropna()

    positive_vs_baseline_ratio = float((pos_vs_series > 0).mean()) if len(pos_vs_series) else 0.0
    median_test_sharpe = float(sharpe_series.median()) if len(sharpe_series) else 0.0

    top_slice = df.head(min(50, len(df))).copy()
    top_pos_vs = pd.to_numeric(top_slice.get("test_vs_baseline", pd.Series(dtype=float)), errors="coerce").dropna()
    robust_top_ratio = float((top_pos_vs > 0).mean()) if len(top_pos_vs) else 0.0

    train_test_gap_abs = 0.0
    if "train_sharpe" in df.columns and "test_sharpe" in df.columns:
        ttrain = pd.to_numeric(df["train_sharpe"], errors="coerce")
        ttest = pd.to_numeric(df["test_sharpe"], errors="coerce")
        gap = (ttrain - ttest).abs().dropna()
        if len(gap):
            train_test_gap_abs = float(gap.median())

    score, wins, risks = quality_score(
        top_sharpe=top_test_sharpe,
        top_vs_baseline=top_test_vs_baseline,
        positive_vs_baseline_ratio=positive_vs_baseline_ratio,
        robust_top_ratio=robust_top_ratio,
        median_test_sharpe=median_test_sharpe,
        train_test_gap_abs=train_test_gap_abs,
    )

    hard_fail_reasons: list[str] = []
    if top_test_sharpe > 8.0 and top_test_vs_baseline <= 0.0:
        hard_fail_reasons.append("Extreme Sharpe with non-positive baseline edge")
    if positive_vs_baseline_ratio < 0.25:
        hard_fail_reasons.append("Too few candidates beating baseline")

    hard_fail = len(hard_fail_reasons) > 0
    verdict = verdict_for(score, hard_fail)

    report = {
        "generated_utc": now_utc(),
        "verdict": verdict,
        "edge_quality_score": score,
        "hard_fail": hard_fail,
        "hard_fail_reasons": hard_fail_reasons,
        "champion": {
            "flow": str(top_row.get("flow", champion.get("flow", "unknown"))),
            "strategy": str(top_row.get("strategy", champion.get("strategy", "unknown"))),
            "algo": str(top_row.get("algo", summary.get("top_algo", "unknown"))),
            "test_sharpe": top_test_sharpe,
            "test_vs_baseline": top_test_vs_baseline,
            "institutional_score": as_float(top_row.get("institutional_score", summary.get("top_institutional_score", 0.0)), 0.0),
        },
        "cohort_metrics": {
            "candidate_count": int(len(df)),
            "positive_vs_baseline_ratio": round(positive_vs_baseline_ratio, 4),
            "robust_top_ratio": round(robust_top_ratio, 4),
            "median_test_sharpe": round(median_test_sharpe, 6),
            "median_abs_train_test_sharpe_gap": round(train_test_gap_abs, 6),
        },
        "wins": wins,
        "risks": risks,
        "sources": {
            "leaderboard_csv": str(leaderboard_path),
            "adaptive_champion_json": str(champion_path) if champion_path else None,
            "full_beast_summary_json": str(summary_path) if summary_path else None,
        },
    }

    OUT_EDGE_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    OUT_EDGE_SNAPSHOT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("EDGE TRUTH GUARD WRITTEN")
    print(OUT_EDGE_REPORT)
    print(OUT_EDGE_SNAPSHOT)
    print(f"Verdict: {verdict} | Score: {score}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
