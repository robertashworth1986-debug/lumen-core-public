from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "alpha_edge_lock"

SECTOR_MATRIX_PATH = ROOT / "out" / "sector_value_matrix.json"
LIVE_BREADTH_PATH = ROOT / "out" / "ops" / "live_breadth_value_panel_latest.json"
READINESS_PATH = ROOT / "out" / "ops" / "investor_metric_readiness_latest.json"
GRANT_FIT_PATH = ROOT / "out" / "ops" / "grant_submit_fit_pack" / "grant_submit_fit_pack_latest.json"

HEARTBEAT_LATEST_PATH = OUT_DIR / "alpha_edge_lock_engine_heartbeat_latest.json"

LABOR_HOUR_VALUE_USD = 150.0

SECTOR_PROBLEM_MAP: dict[str, tuple[str, str]] = {
    "energy": (
        "Grid instability and outage cascades",
        "keep power systems stable before failures propagate",
    ),
    "energy_lab": (
        "Energy R&D blind spots",
        "accelerate high-impact infrastructure innovation decisions",
    ),
    "market_data": (
        "Information latency in markets",
        "reduce delayed decisions and hidden risk accumulation",
    ),
    "broker": (
        "Execution friction in financial rails",
        "lower slippage, missed opportunities, and operational drag",
    ),
    "crypto_exec": (
        "Volatile execution and settlement gaps",
        "improve reliability of autonomous digital-asset operations",
    ),
    "weather": (
        "Extreme weather response lag",
        "trigger earlier resilience actions for vulnerable systems",
    ),
    "air_quality": (
        "Air-quality risk response delays",
        "protect health and productivity through earlier intervention",
    ),
    "rates": (
        "Interest-rate shock blindness",
        "preserve capital and planning stability under macro volatility",
    ),
    "macro": (
        "Macro regime transition risk",
        "adapt strategy before systemic drift becomes loss",
    ),
    "water": (
        "Water reliability and contamination risk",
        "detect and prioritize intervention windows earlier",
    ),
    "federal_data": (
        "Government data fragmentation",
        "convert fragmented telemetry into decision-grade evidence",
    ),
    "labor": (
        "Human time waste in repetitive operations",
        "free skilled time for high-value human judgment",
    ),
    "space": (
        "Space and satellite operation blind spots",
        "reduce downtime and mission risk through predictive alerts",
    ),
    "demographic": (
        "Population trend misalignment",
        "align planning with changing demand and risk footprints",
    ),
    "federal_contracts": (
        "Procurement cycle latency",
        "improve opportunity qualification and response speed",
    ),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:
        return default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def as_usd(value: Any) -> str:
    amount = safe_float(value, 0.0)
    if abs(amount) >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f}B"
    if abs(amount) >= 1_000_000:
        return f"${amount / 1_000_000:.2f}M"
    if abs(amount) >= 1_000:
        return f"${amount / 1_000:.1f}K"
    return f"${amount:,.2f}"


def problem_for_sector(sector: str) -> tuple[str, str]:
    key = str(sector or "").strip().lower()
    if key in SECTOR_PROBLEM_MAP:
        return SECTOR_PROBLEM_MAP[key]
    return (
        f"Operational instability in {key or 'unknown'} systems",
        "improve resilience and decision speed through autonomous detection",
    )


def grant_keywords_for_sector(sector: str) -> list[str]:
    key = str(sector or "").lower()
    if "energy" in key or "water" in key:
        return ["energy", "power", "transmission", "grid", "infrastructure", "de-foa"]
    if key in {"market_data", "broker", "rates", "macro", "crypto_exec"}:
        return ["ai", "innovation", "infrastructure", "founder", "builder"]
    if "federal" in key:
        return ["federal", "grant", "infrastructure", "gov"]
    if key in {"weather", "air_quality"}:
        return ["resilience", "infrastructure", "climate", "risk"]
    return ["infrastructure", "innovation", "ai"]


def rank_grants_for_sector(sector: str, fit_payload: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    opportunities = fit_payload.get("opportunities", []) if isinstance(fit_payload, dict) else []
    if not isinstance(opportunities, list):
        return []

    keys = grant_keywords_for_sector(sector)
    ranked: list[tuple[tuple[int, int, float], dict[str, Any]]] = []
    for row in opportunities:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").lower()
        agency = str(row.get("agency") or "").lower()
        text = f"{title} {agency}"
        matches = sum(1 for key in keys if key in text)
        fit_status = str(row.get("fit_status") or "").upper()
        fit_rank = 0 if fit_status == "FIT_LIKELY" else 1 if fit_status == "MANUAL_CHECK" else 2
        days = safe_int(row.get("days_to_close"), 9999)
        award = safe_float(row.get("award_ceiling_usd"), 0.0)
        ranked.append(((-matches, fit_rank, days, -award), row))

    ranked.sort(key=lambda item: item[0])
    picks: list[dict[str, Any]] = []
    for _, row in ranked[: max(1, limit)]:
        picks.append(
            {
                "opp_num": row.get("opp_num"),
                "title": row.get("title"),
                "submit_url": row.get("submit_url"),
                "fit_status": row.get("fit_status"),
                "fit_reason": row.get("fit_reason"),
            }
        )
    return picks


def lock_grade(alpha_score: float, edge_score: float, confidence_pct: float) -> str:
    harmonic = 0.58 * alpha_score + 0.42 * edge_score
    if harmonic >= 85.0 and confidence_pct >= 45.0:
        return "A+"
    if harmonic >= 75.0 and confidence_pct >= 25.0:
        return "A"
    if harmonic >= 65.0 and confidence_pct >= 15.0:
        return "B"
    if harmonic >= 55.0:
        return "C"
    return "D"


def simulate_lock_confidence(
    alpha_score: float,
    edge_score: float,
    basis: str,
    sim_runs: int,
    alpha_threshold: float,
    edge_threshold: float,
    seed: int,
) -> dict[str, float]:
    rng = random.Random(seed)
    volatility = 0.08 if str(basis or "").upper() == "MEASURED" else 0.18

    alpha_hits = 0
    edge_hits = 0
    joint_hits = 0
    near_joint_hits = 0

    for _ in range(max(100, sim_runs)):
        alpha_sim = clamp(rng.gauss(alpha_score, max(1.0, alpha_score * volatility)))
        edge_sim = clamp(rng.gauss(edge_score, max(1.0, edge_score * volatility * 0.9)))

        alpha_ok = alpha_sim >= alpha_threshold
        edge_ok = edge_sim >= edge_threshold
        joint_ok = alpha_ok and edge_ok
        near_joint_ok = alpha_sim >= (alpha_threshold * 0.9) and edge_sim >= (edge_threshold * 0.9)

        if alpha_ok:
            alpha_hits += 1
        if edge_ok:
            edge_hits += 1
        if joint_ok:
            joint_hits += 1
        if near_joint_ok:
            near_joint_hits += 1

    runs = float(max(100, sim_runs))
    return {
        "alpha_hit_pct": round((alpha_hits / runs) * 100.0, 2),
        "edge_hit_pct": round((edge_hits / runs) * 100.0, 2),
        "joint_hit_pct": round((joint_hits / runs) * 100.0, 2),
        "near_joint_hit_pct": round((near_joint_hits / runs) * 100.0, 2),
    }


def build_problem_stack(
    sector_matrix: dict[str, Any],
    live_breadth: dict[str, Any],
    readiness: dict[str, Any],
    fit_pack: dict[str, Any],
    sim_runs: int,
    alpha_threshold: float,
    edge_threshold: float,
) -> list[dict[str, Any]]:
    rows = sector_matrix.get("sector_value_matrix", []) if isinstance(sector_matrix, dict) else []
    if not isinstance(rows, list):
        rows = []

    rows = [row for row in rows if isinstance(row, dict)]
    if not rows:
        return []

    max_year = max(safe_float(row.get("year"), 0.0) for row in rows) or 1.0
    max_hour = max(safe_float(row.get("hour"), 0.0) for row in rows) or 1.0

    headline = live_breadth.get("headline", {}) if isinstance(live_breadth, dict) else {}
    summary = readiness.get("summary", {}) if isinstance(readiness, dict) else {}
    signal = summary.get("signal_evidence", {}) if isinstance(summary, dict) else {}

    router_edge = clamp(safe_float(signal.get("router_edge_pct"), safe_float(headline.get("router_edge_pct"), 0.0)))
    harmonic_win = clamp(safe_float(signal.get("harmonic_win_rate_pct"), safe_float(headline.get("harmonic_win_rate_pct"), 0.0)))
    coverage = clamp(safe_float(signal.get("measured_coverage_pct"), safe_float(headline.get("measured_coverage_pct"), 0.0)))

    stack: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        sector = str(row.get("sector") or "unknown")
        problem, mission = problem_for_sector(sector)

        annual = safe_float(row.get("year", row.get("annual_exposure_usd")), 0.0)
        hourly = safe_float(row.get("hour"), 0.0)
        weekly = safe_float(row.get("week"), hourly * 24.0 * 7.0)
        upside = safe_float(row.get("modeled_annual_upside_usd"), 0.0)
        failure_count = safe_float(row.get("failure_count"), 0.0)
        basis = str(row.get("basis") or "ESTIMATED").upper()

        annual_norm = clamp((annual / max_year) * 100.0)
        hour_norm = clamp((hourly / max_hour) * 100.0)
        failure_norm = clamp(failure_count * 12.0)
        measured_bonus = 8.0 if basis == "MEASURED" else 0.0

        alpha_score = clamp(
            (annual_norm * 0.45)
            + (hour_norm * 0.20)
            + (router_edge * 0.20)
            + (harmonic_win * 0.15)
            + measured_bonus
        )
        edge_score = clamp(
            (hour_norm * 0.35)
            + (annual_norm * 0.20)
            + (coverage * 0.15)
            + (failure_norm * 0.20)
            + (router_edge * 0.10)
            + measured_bonus
        )
        harmonic_alpha_edge_score = round(clamp((alpha_score * 0.58) + (edge_score * 0.42)), 2)

        sim = simulate_lock_confidence(
            alpha_score=alpha_score,
            edge_score=edge_score,
            basis=basis,
            sim_runs=sim_runs,
            alpha_threshold=alpha_threshold,
            edge_threshold=edge_threshold,
            seed=7100 + idx,
        )

        confidence = safe_float(sim.get("joint_hit_pct"), 0.0)
        grade = lock_grade(alpha_score=alpha_score, edge_score=edge_score, confidence_pct=confidence)

        time_saved_hours_week = max(0.0, weekly / LABOR_HOUR_VALUE_USD)
        fte_equivalent = time_saved_hours_week / 40.0
        wealth_time_blend = round(
            (harmonic_alpha_edge_score * 0.55)
            + (min(100.0, confidence) * 0.30)
            + (min(100.0, (time_saved_hours_week / 100.0)) * 0.15),
            2,
        )

        stack.append(
            {
                "sector": sector,
                "problem_statement": problem,
                "mission_outcome": mission,
                "annual_exposure_usd": round(annual, 2),
                "modeled_annual_upside_usd": round(upside, 2),
                "hourly_value_usd": round(hourly, 2),
                "modeled_time_saved_hours_per_week": round(time_saved_hours_week, 2),
                "fte_hours_equivalent": round(fte_equivalent, 2),
                "alpha_lock_score": round(alpha_score, 2),
                "edge_lock_score": round(edge_score, 2),
                "harmonic_alpha_edge_score": harmonic_alpha_edge_score,
                "confidence_live_lock_pct": round(confidence, 2),
                "lock_grade": grade,
                "wealth_time_blend_score": wealth_time_blend,
                "evidence_basis": basis,
                "validation_mode": "backtest_and_live_guarded_proof",
                "recommended_grants": rank_grants_for_sector(sector=sector, fit_payload=fit_pack, limit=3),
                "sim": sim,
                "priority": "P0" if harmonic_alpha_edge_score >= 80.0 else "P1" if harmonic_alpha_edge_score >= 65.0 else "P2",
            }
        )

    stack.sort(
        key=lambda row: (
            safe_float(row.get("priority") == "P0"),
            safe_float(row.get("harmonic_alpha_edge_score"), 0.0),
            safe_float(row.get("confidence_live_lock_pct"), 0.0),
            safe_float(row.get("annual_exposure_usd"), 0.0),
        ),
        reverse=True,
    )

    for rank, row in enumerate(stack, start=1):
        row["rank"] = rank

    return stack


def render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Alpha and Edge Lock Engine")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append(f"Sim runs per sector: {payload.get('config', {}).get('sim_runs', 0)}")
    lines.append("")
    lines.append("## 3-Minute Challenge: Highest-Impact Human Problems")

    for row in payload.get("problem_stack", [])[:12]:
        if not isinstance(row, dict):
            continue
        lines.append(
            "- #{rank} {problem} | sector={sector} | alpha={alpha:.2f} edge={edge:.2f} confidence={conf:.2f}% | time={time:.1f}h/week | upside={upside}".format(
                rank=safe_int(row.get("rank"), 0),
                problem=row.get("problem_statement", "unknown"),
                sector=row.get("sector", "unknown"),
                alpha=safe_float(row.get("alpha_lock_score"), 0.0),
                edge=safe_float(row.get("edge_lock_score"), 0.0),
                conf=safe_float(row.get("confidence_live_lock_pct"), 0.0),
                time=safe_float(row.get("modeled_time_saved_hours_per_week"), 0.0),
                upside=as_usd(row.get("modeled_annual_upside_usd", 0.0)),
            )
        )

    lines.append("")
    lines.append("## Grade-A Locks")
    lines.append(f"- count: {payload.get('summary', {}).get('grade_a_locks', 0)}")
    lines.append(f"- alpha_threshold: {payload.get('config', {}).get('alpha_threshold', 0)}")
    lines.append(f"- edge_threshold: {payload.get('config', {}).get('edge_threshold', 0)}")
    lines.append("")
    lines.append("## Live Proof Posture")
    lines.append(f"- runtime_mode: {payload.get('live_posture', {}).get('runtime_mode', 'unknown')}")
    lines.append(f"- allow_live_orders: {payload.get('live_posture', {}).get('allow_live_orders', False)}")
    lines.append(f"- control_gate: {payload.get('live_posture', {}).get('controller_mode', 'unknown')}")
    lines.append("- policy: test in backtest, prove through guarded live alpha/edge locks with evidence chain")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_heartbeat(
    *,
    status: str,
    reason: str,
    run_tag: str,
    sim_runs: int,
    alpha_threshold: float,
    edge_threshold: float,
    summary: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_utc": now_iso(),
        "scope": "alpha_edge_lock_engine",
        "mode": "export",
        "status": str(status),
        "reason": str(reason),
        "run_tag": run_tag,
        "config": {
            "sim_runs": int(sim_runs),
            "alpha_threshold": float(alpha_threshold),
            "edge_threshold": float(edge_threshold),
        },
        "summary": summary if isinstance(summary, dict) else {},
        "artifacts": artifacts if isinstance(artifacts, dict) else {},
    }
    if error:
        payload["error"] = str(error)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    heartbeat_ts_path = OUT_DIR / f"alpha_edge_lock_engine_heartbeat_{run_tag}.json"
    heartbeat_text = json.dumps(payload, indent=2)
    heartbeat_ts_path.write_text(heartbeat_text, encoding="utf-8")
    HEARTBEAT_LATEST_PATH.write_text(heartbeat_text, encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build alpha and edge lock ranking engine for mission-control and investor challenge artifacts.")
    parser.add_argument("--sim-runs", type=int, default=5000, help="Monte Carlo runs per sector")
    parser.add_argument("--alpha-threshold", type=float, default=78.0, help="Alpha-lock threshold")
    parser.add_argument("--edge-threshold", type=float, default=72.0, help="Edge-lock threshold")
    parser.add_argument("--top-n", type=int, default=12, help="Top records in summary sections")
    args = parser.parse_args()

    sim_runs = max(100, int(args.sim_runs))
    alpha_threshold = float(args.alpha_threshold)
    edge_threshold = float(args.edge_threshold)
    tag = now_tag()

    write_heartbeat(
        status="running",
        reason="build_started",
        run_tag=tag,
        sim_runs=sim_runs,
        alpha_threshold=alpha_threshold,
        edge_threshold=edge_threshold,
    )

    try:
        sector_matrix = load_json(SECTOR_MATRIX_PATH, {})
        live_breadth = load_json(LIVE_BREADTH_PATH, {})
        readiness = load_json(READINESS_PATH, {})
        fit_pack = load_json(GRANT_FIT_PATH, {})

        problem_stack = build_problem_stack(
            sector_matrix=sector_matrix,
            live_breadth=live_breadth,
            readiness=readiness,
            fit_pack=fit_pack,
            sim_runs=sim_runs,
            alpha_threshold=alpha_threshold,
            edge_threshold=edge_threshold,
        )

        grade_a_locks = [
            row for row in problem_stack
            if str(row.get("lock_grade", "")).upper().startswith("A")
        ]

        live_posture = (
            ((live_breadth.get("metric_readiness", {}) or {}).get("runtime_gates", {}) or {})
            if isinstance(live_breadth, dict)
            else {}
        )
        controller_mode = (
            ((live_breadth.get("metric_readiness", {}) or {}).get("controller_gates", {}) or {}).get("mode")
            if isinstance(live_breadth, dict)
            else None
        )

        payload = {
            "generated_utc": now_iso(),
            "scope": "alpha_edge_lock_engine",
            "config": {
                "sim_runs": sim_runs,
                "alpha_threshold": alpha_threshold,
                "edge_threshold": edge_threshold,
                "labor_hour_value_usd": LABOR_HOUR_VALUE_USD,
            },
            "summary": {
                "problem_count": len(problem_stack),
                "grade_a_locks": len(grade_a_locks),
                "top_problem": (problem_stack[0].get("problem_statement") if problem_stack else None),
                "top_sector": (problem_stack[0].get("sector") if problem_stack else None),
                "top_harmonic_alpha_edge_score": (
                    problem_stack[0].get("harmonic_alpha_edge_score") if problem_stack else None
                ),
            },
            "live_posture": {
                "runtime_mode": live_posture.get("runtime_mode"),
                "allow_live_orders": live_posture.get("allow_live_orders"),
                "controller_mode": controller_mode,
                "policy": "backtest_and_live_guarded_proof",
            },
            "problem_stack": problem_stack,
            "top_problem_stack": problem_stack[: max(1, int(args.top_n))],
        }

        OUT_DIR.mkdir(parents=True, exist_ok=True)

        json_ts = OUT_DIR / f"alpha_edge_lock_engine_{tag}.json"
        md_ts = OUT_DIR / f"alpha_edge_lock_engine_{tag}.md"
        json_latest = OUT_DIR / "alpha_edge_lock_engine_latest.json"
        md_latest = OUT_DIR / "alpha_edge_lock_engine_latest.md"

        json_text = json.dumps(payload, indent=2)
        json_ts.write_text(json_text, encoding="utf-8")
        json_latest.write_text(json_text, encoding="utf-8")

        md_text = render_markdown(payload)
        md_ts.write_text(md_text, encoding="utf-8")
        md_latest.write_text(md_text, encoding="utf-8")

        write_heartbeat(
            status="ok",
            reason="build_complete",
            run_tag=tag,
            sim_runs=sim_runs,
            alpha_threshold=alpha_threshold,
            edge_threshold=edge_threshold,
            summary=payload.get("summary", {}),
            artifacts={
                "json_latest": str(json_latest),
                "json_timestamped": str(json_ts),
                "md_latest": str(md_latest),
                "md_timestamped": str(md_ts),
            },
        )

        print("BUILD_ALPHA_EDGE_LOCK_ENGINE")
        print(f"problems={payload['summary']['problem_count']}")
        print(f"grade_a_locks={payload['summary']['grade_a_locks']}")
        print(f"top_problem={payload['summary']['top_problem']}")
        print(f"json={json_latest}")
        print(f"md={md_latest}")
        return 0
    except Exception as exc:
        write_heartbeat(
            status="error",
            reason="build_failed",
            run_tag=tag,
            sim_runs=sim_runs,
            alpha_threshold=alpha_threshold,
            edge_threshold=edge_threshold,
            error=str(exc),
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
